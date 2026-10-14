"""Static function/CFG features describing a candidate relative to O3.

Instruction counts are predictor inputs only. Native runtime remains the label.
SCCs describe cyclic CFG regions, not natural-loop nesting or dynamic hotness.
"""
import re
import subprocess
from collections import Counter
from pathlib import Path

import networkx as nx
import numpy as np

from src.benchmarks.compact import MENU, sha

METRICS = ["instructions", "blocks", "edges", "cyclic_blocks", "cyclic_instructions",
           "cyclic_regions", "load", "store", "call", "indirect_call", "phi",
           "branch", "compare", "integer", "floating", "divide", "shift", "gep",
           "select", "cast", "vector"]
OPS = set("ret br switch indirectbr invoke resume unreachable cleanupret catchret catchswitch callbr fneg add fadd sub fsub mul fmul udiv sdiv fdiv urem srem frem shl lshr ashr and or xor extractelement insertelement shufflevector extractvalue insertvalue alloca load store fence cmpxchg atomicrmw getelementptr trunc zext sext fptrunc fpext fptoui fptosi uitofp sitofp ptrtoint inttoptr bitcast addrspacecast icmp fcmp phi select call va_arg landingpad catchpad cleanuppad freeze".split())
NAME = r'(?:"[^"\n]+"|[-a-zA-Z$._0-9]+)'
FUNCTION = re.compile(r'^define\b.*?@(' + NAME + r')\(')
LABEL = re.compile(r'^(' + NAME + r'):\s*(?:;.*)?$')
TARGET = re.compile(r'\blabel\s+%(' + NAME + r')')
DIRECT = re.compile(r'@(' + NAME + r')\(')


def parse_ir(text):
    result = {}
    function, block = None, None
    for raw in text.splitlines():
        line = raw.strip()
        match = FUNCTION.match(line)
        if match:
            function = {"counts": Counter(), "blocks": {}, "edges": [], "calls": set()}
            result[match.group(1)] = function
            block = "__entry__"
            function["blocks"][block] = 0
            continue
        if line == "}":
            function = None
            continue
        if function is None:
            continue
        match = LABEL.match(line)
        if match:
            if block == "__entry__" and function["blocks"][block] == 0 and not function["edges"]:
                function["blocks"].pop(block)
            block = match.group(1)
            function["blocks"].setdefault(block, 0)
            continue
        for target in TARGET.findall(line):
            function["edges"].append((block, target))
        instruction = re.sub(r'^%' + NAME + r'\s*=\s*', '', line)
        words = instruction.split()
        while words and words[0] in ("tail", "musttail", "notail"):
            words.pop(0)
        if not words or words[0] not in OPS:
            continue
        op = words[0]
        counts = function["counts"]
        counts["instructions"] += 1
        function["blocks"][block] += 1
        for metric, members in {
            "load": {"load", "atomicrmw", "cmpxchg"}, "store": {"store", "atomicrmw", "cmpxchg"},
            "call": {"call", "invoke", "callbr"}, "phi": {"phi"}, "branch": {"br", "switch", "indirectbr"},
            "compare": {"icmp", "fcmp"}, "integer": {"add", "sub", "mul", "and", "or", "xor"},
            "floating": {"fadd", "fsub", "fmul", "fdiv", "frem", "fneg"},
            "divide": {"udiv", "sdiv", "fdiv", "urem", "srem", "frem"},
            "shift": {"shl", "lshr", "ashr"}, "gep": {"getelementptr"}, "select": {"select"},
            "cast": {"trunc", "zext", "sext", "fptrunc", "fpext", "fptoui", "fptosi", "uitofp", "sitofp", "ptrtoint", "inttoptr", "bitcast", "addrspacecast"},
        }.items():
            counts[metric] += op in members
        counts["vector"] += bool(re.search(r'<\d+ x ', instruction))
        if op in ("call", "invoke", "callbr"):
            targets = DIRECT.findall(instruction)
            if targets:
                function["calls"].add(targets[0])
            else:
                counts["indirect_call"] += 1
    if not result:
        raise ValueError("No defined functions in LLVM IR")
    for f in result.values():
        graph = nx.DiGraph()
        graph.add_nodes_from(f["blocks"])
        graph.add_edges_from(f["edges"])
        if set(graph) != set(f["blocks"]):
            raise ValueError("Unparsed CFG target")
        cyclic = [s for s in nx.strongly_connected_components(graph)
                  if len(s) > 1 or any(graph.has_edge(n, n) for n in s)]
        nodes = set().union(*cyclic) if cyclic else set()
        f["counts"].update({"blocks": len(graph), "edges": len(graph.edges),
            "cyclic_regions": len(cyclic), "cyclic_blocks": len(nodes),
            "cyclic_instructions": sum(f["blocks"][n] for n in nodes)})
    return result


def aggregate(functions, names):
    return np.asarray([sum(functions[n]["counts"][m] for n in names) for m in METRICS], dtype=float)


def summaries(functions, entrypoint="main"):
    reachable, pending = set(), [entrypoint] if entrypoint in functions else []
    indirect = False
    while pending:
        name = pending.pop()
        if name not in functions or name in reachable:
            continue
        reachable.add(name)
        f = functions[name]
        indirect |= bool(f["counts"]["indirect_call"])
        pending.extend(f["calls"])
    # Static direct-call reachability is a lower bound in the presence of
    # indirect calls. Preserve that uncertainty as a feature, never label it hot.
    return [aggregate(functions, functions), aggregate(functions, [entrypoint] if entrypoint in functions else []),
            aggregate(functions, reachable)], indirect


FEATURE_NAMES = ([f"o3_{scope}_{m}" for scope in ["module", "main", "direct_reachable"] for m in METRICS]
    + [f"delta_{scope}_{m}" for scope in ["module", "main", "direct_reachable"] for m in METRICS]
    + [f"absolute_function_delta_{m}" for m in METRICS]
    + ["changed_function_fraction", "o3_indirect_reachability", "candidate_indirect_reachability",
       "elf_size_delta", "log_input_bytes", "log_iterations"]
    + [f"choice_{c}" for c in list(MENU)[1:]])


def candidate_vector(base, candidate, choice, input_bytes, iterations, elf_delta=0., entrypoint="main"):
    bs, bi = summaries(base, entrypoint)
    cs, ci = summaries(candidate, entrypoint)
    x = [np.log1p(np.concatenate(bs)), (np.concatenate(cs) - np.concatenate(bs)) / (np.concatenate(bs) + 1)]
    differences = []
    changed = 0
    for name in sorted(set(base) | set(candidate)):
        a = aggregate(base, [name]) if name in base else np.zeros(len(METRICS))
        b = aggregate(candidate, [name]) if name in candidate else np.zeros(len(METRICS))
        changed += not np.array_equal(a, b)
        differences.append(np.abs(b - a))
    x.append(np.sum(differences, axis=0) / (bs[0] + 1))
    x.append(np.asarray([changed / max(len(base), 1), float(bi), float(ci), elf_delta,
                         np.log1p(input_bytes), np.log1p(iterations)]
                        + [float(choice == c) for c in list(MENU)[1:]]))
    values = np.concatenate(x)
    if values.shape != (len(FEATURE_NAMES),) or not np.isfinite(values).all():
        raise ValueError("Invalid candidate vector")
    return values.tolist()


def extract_manifest(manifest):
    from compiler_gym.third_party import llvm
    functions, hashes = {}, {}
    for choice in MENU:
        a = manifest["artifacts"][choice]
        path = Path(a["directory"]) / "program.bc"
        if sha(path) != a["bc_sha256"]:
            raise ValueError("Candidate bitcode changed")
        text = subprocess.check_output([str(llvm.opt_path().parent / "llvm-dis"), str(path), "-o", "-"], text=True)
        functions[choice] = parse_ir(text)
        hashes[choice] = sha(path)
    baseline_size = (Path(manifest["artifacts"]["O3"]["directory"]) / "a.out").stat().st_size
    values = {c: candidate_vector(functions["O3"], functions[c], c, *manifest["features"][-2:],
        ((Path(manifest["artifacts"][c]["directory"]) / "a.out").stat().st_size - baseline_size) / baseline_size)
        for c in list(MENU)[1:]}
    return {"features": values, "bc_sha256": hashes, "aliases": manifest["aliases"],
            "program": manifest["program"], "static_only": True}
