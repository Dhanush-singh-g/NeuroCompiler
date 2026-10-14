"""Pinned scientific-kernel corpus, LLVM 19, and raw scheduler-aware timings.

Native kernel latency is the objective. Zero observed steal is diagnostic only;
no trials are deleted, delay-adjusted, or substituted into training labels.
"""
import hashlib
import json
import math
import os
import re
import subprocess
import tarfile
import time
import urllib.request
from pathlib import Path

import numpy as np

from src.benchmarks.compact import effect, save, sha
from src.features.transform import candidate_vector, parse_ir

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "data/processed/polybench-c-3.2"
TOOLS = Path(os.environ.get("NEUROCOMPILER_LLVM19", "/workspace/.neurocompiler/llvm19/root/usr/lib/llvm-19/bin"))
LIB = TOOLS.parents[2] / "lib/x86_64-linux-gnu"
URL = "https://www.cs.colostate.edu/~pouchet/software/polybench/download/polybench-c-3.2.tar.gz"
ARCHIVE_SHA = "1caddda5806dbe5556e0bbb4e367846a2470e6c677e5d872bdb16ace36a571f7"
MENU = {
    "O3": "default<O3>", "O2": "default<O2>", "Os": "default<Os>",
    "instcombine_O3": "function(instcombine<max-iterations=10>),default<O3>",
    "O3_unroll": "default<O3>,function(loop-unroll)",
    "O3_cleanup": "default<O3>,function(gvn,dce)",
}
INPUT_FIXES = {
    "cholesky": ("A[i][j] = 1.0 / n;", "A[i][j] = (i == j ? 2.0 : 1.0 / n);"),
    "trisolv": ("A[i][j] = ((DATA_TYPE) i*j) / n;", "A[i][j] = (i == j ? 2.0 : 1.0 / n);"),
    "trmm": ("*alpha = 32412;", "*alpha = 1.0 / ((DATA_TYPE) ni * ni);"),
    "gramschmidt": ("A[i][j] = ((DATA_TYPE) i*j) / ni;", "A[i][j] = (i == j ? 2.0 : 1.0 / ni);"),
    "lu": ("A[i][j] = ((DATA_TYPE) (i+1)*(j+1)) / n;", "A[i][j] = (i == j ? 2.0 : 1.0 / n);"),
    "ludcmp": ("A[i][j] = ((DATA_TYPE) (i+1)*(j+1)) / n;", "A[i][j] = (i == j ? 2.0 : 1.0 / (n+1));"),
}
INPUT_FIXES = {name: list(replacement) for name, replacement in INPUT_FIXES.items()}
DEVELOPMENT_INPUT_FIXES = {"fdtd-apml": [
    "  /* Initialize array(s). */",
    "  /* Initialize the upstream uninitialized live-in Bza, outside the timer. */\n"
    "  for (int nc_z=0; nc_z<=cz; ++nc_z)\n"
    "    for (int nc_y=0; nc_y<=cym; ++nc_y)\n"
    "      for (int nc_x=0; nc_x<=cxm; ++nc_x)\n"
    "        (POLYBENCH_ARRAY(Bza))[nc_z][nc_y][nc_x]=0.0;\n"
    "  /* Initialize array(s). */"]}
PROTOCOL = {
    "version": 2, "toolchain": "LLVM 19.1.7", "dataset": "SMALL_DATASET",
    "menu": MENU, "blocks": 3, "pairs": 8, "cpu": 2, "seed": 20261021,
    "control_tolerance": .03, "gain_floor": .03, "bootstrap_replicates": 2000,
    "batch_target_seconds": .015, "max_repetitions": 100000,
    "objective": "in-process CLOCK_MONOTONIC kernel seconds, fresh inputs per invocation",
    "floating_point": "strict, -ffp-contract=off, no fast-math",
    "scheduler": "all trials retained; /proc/stat cpu2 steal delta diagnostic only",
    "splits": {"train": ["datamining", "linear-algebra"],
               "development": ["stencils"], "reserved_test": ["medley"]},
    "correctness": "full live-out bitwise hash and finite-value check, O0 reference",
    "input_fixes": INPUT_FIXES,
}


def tool(command):
    env = dict(os.environ)
    env["LD_LIBRARY_PATH"] = str(LIB) + ":" + env.get("LD_LIBRARY_PATH", "")
    return subprocess.run([str(x) for x in command], env=env, capture_output=True,
                          check=True, timeout=180).stdout


def experiment_name(name):
    if not re.fullmatch(r"[a-z][a-z0-9_]{0,63}", name):
        raise ValueError("Experiment name must be a safe lowercase identifier")
    return name


def fetch():
    archive = ROOT / "data/processed/polybench-c-3.2.tar.gz"
    if not archive.exists():
        archive.parent.mkdir(parents=True, exist_ok=True)
        data = urllib.request.urlopen(URL, timeout=60).read(1024*1024)
        if hashlib.sha256(data).hexdigest() != ARCHIVE_SHA:
            raise ValueError("PolyBench archive checksum mismatch")
        archive.write_bytes(data)
    if sha(archive) != ARCHIVE_SHA:
        raise ValueError("PolyBench archive changed")
    # Python 3.10 lacks tarfile's data filter. Validate paths and reject links.
    with tarfile.open(archive) as tar:
        for item in tar.getmembers():
            path = (archive.parent / item.name).resolve()
            if not path.is_relative_to(archive.parent.resolve()) or item.issym() or item.islnk():
                raise ValueError("Unsafe archive member")
            if not (item.isdir() or item.isfile()):
                raise ValueError("Unsupported archive member")
            if item.isfile() and path.exists():
                if path.read_bytes() != tar.extractfile(item).read():
                    raise ValueError("Materialized PolyBench source changed")
            elif not path.exists():
                tar.extract(item, archive.parent)
    return archive


def inventory():
    fetch()
    paths = (CORPUS / "utilities/benchmark_list").read_text().splitlines()
    if len(paths) != 30 or len(set(paths)) != 30:
        raise ValueError("Unexpected PolyBench corpus")
    result = []
    for relative in paths:
        p = Path(relative)
        if p.parts[0] == "medley":
            split = "reserved_test"
        elif p.parts[0] == "stencils":
            split = "development"
        else:
            split = "train"
        result.append({"id": p.stem, "path": relative, "split": split,
                       "family": "/".join(p.parts[:-2]),
                       "sha256": sha(CORPUS / p), "header_sha256": sha((CORPUS / p).with_suffix('.h'))})
    return result


def scheduler_ticks(cpu=2):
    for line in Path("/proc/stat").read_text().splitlines():
        fields = line.split()
        if fields[0] == f"cpu{cpu}":
            return {"user": int(fields[1]), "system": int(fields[3]),
                    "idle": int(fields[4]), "steal": int(fields[8])}
    raise ValueError("Timing CPU unavailable")


def static_features(artifacts):
    parsed = {c: parse_ir(tool([TOOLS / "llvm-dis", artifacts[c]["bc"], "-o", "-"]).decode())
              for c in MENU}
    base_size = Path(artifacts["O3"]["elf"]).stat().st_size
    return {c: candidate_vector(parsed["O3"], parsed[c], c, 0, 1,
            (Path(artifacts[c]["elf"]).stat().st_size-base_size)/base_size,
            entrypoint="nc_benchmark_main")[:-3] for c in MENU if c != "O3"}


def trial(elf, repetitions):
    before = scheduler_ticks()
    start = time.perf_counter_ns()
    output = subprocess.run(["taskset", "-c", "2", str(elf), str(repetitions)],
                            capture_output=True, check=True, timeout=180)
    elapsed = (time.perf_counter_ns()-start)*1e-9
    after = scheduler_ticks()
    row = json.loads(output.stdout)
    if row["repetitions"] != repetitions or row["values"] < 1 or not (
            math.isfinite(row["kernel_seconds"]) and row["kernel_seconds"] > 0):
        raise ValueError("Invalid worker result")
    row.update({"process_elapsed_seconds": elapsed,
                "scheduler_delta": {k: after[k]-before[k] for k in before}})
    if any(v < 0 for v in row["scheduler_delta"].values()):
        raise ValueError("Scheduler counter regressed")
    return row


def build(item, directory):
    if item["split"] == "reserved_test":
        raise ValueError("Reserved tests may not be built or timed")
    directory = Path(directory).resolve()
    directory.mkdir(parents=True, exist_ok=False)
    source = CORPUS / item["path"]
    text = source.read_text()
    fix = INPUT_FIXES.get(item["id"])
    if fix:
        before, after = fix
        init_end = text.index("/* DCE code.")
        if text[:init_end].count(before) != 1:
            raise ValueError("Input adapter no longer matches pinned initializer")
        text = text[:init_end].replace(before, after) + text[init_end:]
    development_fix = DEVELOPMENT_INPUT_FIXES.get(item["id"])
    if development_fix:
        if item["split"] != "development" or text.count(development_fix[0]) != 1:
            raise ValueError("Development initialization adapter mismatch")
        text = text.replace(*development_fix)
    prepared = directory / "benchmark.c"
    prepared.write_text(text)
    flags = ["-ffp-contract=off", "-fno-discard-value-names", "-DSMALL_DATASET",
             "-I" + str(CORPUS / "utilities"), "-I" + str(source.parent)]
    tool([TOOLS / "clang", *flags, "-O1", "-Xclang", "-disable-llvm-passes",
          "-DPOLYBENCH_TIME", "-DPOLYBENCH_DUMP_ARRAYS", "-Dmain=nc_benchmark_main",
          "-Dfprintf=nc_sink_fprintf", "-emit-llvm", "-c", prepared, "-o", directory / "initial.bc"])
    # Support and measurement objects are identical and outside pass selection.
    tool([TOOLS / "clang", *flags, "-O3", "-Dpolybench_timer_start=nc_unused_start",
          "-Dpolybench_timer_stop=nc_unused_stop", "-Dpolybench_timer_print=nc_unused_print",
          "-c", CORPUS / "utilities/polybench.c", "-o", directory / "support.o"])
    tool([TOOLS / "clang", "-O2", "-ffp-contract=off", "-c",
          ROOT / "src/benchmarks/polybench_worker.c", "-o", directory / "worker.o"])
    artifacts = {}
    for choice, pipeline in {"reference_O0": "default<O0>", **MENU}.items():
        bc, elf = directory / f"{choice}.bc", directory / f"{choice}.out"
        tool([TOOLS / "opt", "-passes=" + pipeline, directory / "initial.bc", "-o", bc])
        tool([TOOLS / "clang", "-O3", "-Xclang", "-disable-llvm-passes", "-ffp-contract=off",
              bc, directory / "support.o", directory / "worker.o", "-lm", "-o", elf])
        artifacts[choice] = {"bc": str(bc), "elf": str(elf), "bc_sha256": sha(bc), "elf_sha256": sha(elf)}
    # Native O0 comparison independently tests transformation correctness.
    reference = trial(artifacts["reference_O0"]["elf"], 1)
    expected = {k: reference[k] for k in ["checksum", "values"]}
    checks = {}
    for choice in MENU:
        checks[choice] = []
        for _ in range(2):
            row = trial(artifacts[choice]["elf"], 1)
            if {k: row[k] for k in expected} != expected:
                raise ValueError(f"O0 live-out mismatch: {item['id']} {choice}")
            checks[choice].append(row)
    calibration = checks["O3"][-1]
    reps = min(PROTOCOL["max_repetitions"], max(1, math.ceil(
        PROTOCOL["batch_target_seconds"] / calibration["kernel_seconds"])))
    # Drop the old menu's three one-hot features; LLVM19 models are independent.
    vectors = static_features(artifacts)
    manifest = {**item, "artifacts": artifacts, "features": vectors, "repetitions": reps,
                "prepared_source_sha256": sha(prepared), "input_adapter": list(fix) if fix else None,
                "development_input_adapter": development_fix,
                "expected": expected, "checks": checks, "o0_check": reference,
                "initial_sha256": sha(directory / "initial.bc"),
                "worker_sha256": sha(ROOT / "src/benchmarks/polybench_worker.c"),
                "aliases": {c: next(k for k in MENU if artifacts[k]["elf_sha256"] ==
                            artifacts[c]["elf_sha256"]) for c in MENU}}
    save(directory / "manifest.json", manifest)
    return manifest


def cell(manifest, choice, block, role):
    left = choice if role == "candidate_control" else "O3"
    right = "O3" if role == "qualification" else choice
    # Alternating execution order, deterministic starting-order randomization.
    seed = PROTOCOL["seed"] + int(hashlib.sha256(
        f"{manifest['id']}:{choice}:{role}:{block}".encode()).hexdigest()[:8], 16)
    first = bool(np.random.default_rng(seed).integers(2))
    lrows, rrows = [], []
    for pair in range(PROTOCOL["pairs"]):
        left_first = (pair % 2 == 0) == first
        order = [left, right] if left_first else [right, left]
        measured = []
        for c in order:
            row = trial(manifest["artifacts"][c]["elf"], manifest["repetitions"])
            if {k: row[k] for k in manifest["expected"]} != manifest["expected"]:
                raise ValueError("Timed output mismatch")
            measured.append(row)
        # Names are identical in unchanged controls. Use logical order rather
        # than comparing names, which would incorrectly keep A always first.
        a, b = measured if left_first else measured[::-1]
        lrows.append(a); rrows.append(b)
    return {"case": manifest["id"], "choice": choice, "block": block,
            "role": role, "first": first, "left": left, "right": right,
            "left_seconds": [r["kernel_seconds"] for r in lrows],
            "right_seconds": [r["kernel_seconds"] for r in rrows],
            "left_trials": lrows, "right_trials": rrows}


def outcomes(report):
    accepted, diagnostics = [], {}
    for ident, m in report["manifests"].items():
        records = [c for c in report["records"] if c["case"] == ident]
        qcells = [c for c in records if c["role"] == "qualification"]
        if len(qcells) != PROTOCOL["blocks"]:
            continue
        q = effect(qcells, PROTOCOL)
        stats = {"O3": {"log_speedup": 0., "speedup": 1., "interval": [1., 1.], "confirmed_gain": False}}
        valid = q["control_pass"]
        for choice in MENU:
            alias = m["aliases"][choice]
            if alias in stats:
                stats[choice] = dict(stats[alias]); continue
            ec = [c for c in records if c["choice"] == alias and c["role"] == "effect"]
            cc = [c for c in records if c["choice"] == alias and c["role"] == "candidate_control"]
            if len(ec) != PROTOCOL["blocks"] or len(cc) != PROTOCOL["blocks"]:
                valid = False; continue
            s, control = effect(ec, PROTOCOL), effect(cc, PROTOCOL)
            floor = 1 + PROTOCOL["gain_floor"]
            s["confirmed_gain"] = bool(s["interval"][0] > floor and all(x > floor for x in s["blocks"]))
            s["candidate_control"] = control
            stats[choice] = s
            valid &= control["control_pass"]
        diagnostics[ident] = {"o3_control": q, "outcomes": stats, "accepted": bool(valid)}
        if valid:
            accepted.append({"case": ident, "family": m["family"], "features": m["features"], "outcomes": stats})
    return accepted, diagnostics


def verify(report):
    # JSON represents initializer tuples as lists.
    if report["protocol"] != json.loads(json.dumps(PROTOCOL)) or report["inventory"] != inventory():
        raise ValueError("Changed corpus or measurement protocol")
    if report["split"] == "development" and report.get("development_input_fixes") != DEVELOPMENT_INPUT_FIXES:
        raise ValueError("Changed development initialization protocol")
    expected = {i["id"] for i in report["inventory"] if i["split"] == report["split"]}
    items = {i["id"]: i for i in report["inventory"]}
    if set(report["manifests"]) & set(report["failures"]) or not (
            set(report["manifests"]) | set(report["failures"])) <= expected:
        raise ValueError("Invalid corpus coverage")
    if report["complete"] and set(report["manifests"]) | set(report["failures"]) != expected:
        raise ValueError("Incomplete corpus coverage")
    seen = set()
    for ident,m in report["manifests"].items():
        if any(m[k] != v for k,v in items[ident].items()):
            raise ValueError("Changed case identity")
        if m["split"] != report["split"] or m["split"] == "reserved_test":
            raise ValueError("Invalid split")
        for a in m["artifacts"].values():
            if sha(a["bc"]) != a["bc_sha256"] or sha(a["elf"]) != a["elf_sha256"]:
                raise ValueError("Changed native artifact")
        directory = Path(m["artifacts"]["O3"]["bc"]).parent
        expected_source = (CORPUS / m["path"]).read_text()
        fix = INPUT_FIXES.get(m["id"])
        if fix:
            expected_source = expected_source.replace(*fix)
        development_fix = DEVELOPMENT_INPUT_FIXES.get(m["id"])
        if development_fix:
            expected_source = expected_source.replace(*development_fix)
        if (directory / "benchmark.c").read_text() != expected_source or sha(
                directory / "benchmark.c") != m["prepared_source_sha256"]:
            raise ValueError("Changed benchmark or input adapter")
        if sha(directory / "initial.bc") != m["initial_sha256"] or sha(
                ROOT / "src/benchmarks/polybench_worker.c") != m["worker_sha256"]:
            raise ValueError("Changed initial module or instrumentation")
        if not isinstance(m["repetitions"], int) or not 1 <= m["repetitions"] <= PROTOCOL["max_repetitions"]:
            raise ValueError("Invalid batch repetitions")
        aliases = {c: next(k for k in MENU if m["artifacts"][k]["elf_sha256"] ==
                          m["artifacts"][c]["elf_sha256"]) for c in MENU}
        if aliases != m["aliases"]:
            raise ValueError("Changed executable aliases")
        if m["features"] != static_features(m["artifacts"]):
            raise ValueError("Changed static transformation features")
        if {k:m["o0_check"][k] for k in m["expected"]} != m["expected"]:
            raise ValueError("O0 output reference mismatch")
    for c in report["records"]:
        m = report["manifests"][c["case"]]
        key = (c["case"], c["choice"], c["block"], c["role"])
        if key in seen or c["block"] not in range(PROTOCOL["blocks"]):
            raise ValueError("Duplicate or invalid cell")
        seen.add(key)
        choice, role = c["choice"], c["role"]
        if choice not in MENU or m["aliases"][choice] != choice:
            raise ValueError("Invalid measured choice")
        if role == "qualification":
            pair = ("O3", "O3")
            if choice != "O3":
                raise ValueError("Non-O3 qualification")
        elif role == "candidate_control" and choice != "O3":
            pair = (choice, choice)
        elif role == "effect" and choice != "O3":
            pair = ("O3", choice)
        else:
            raise ValueError("Invalid timing role")
        if (c["left"], c["right"]) != pair or not isinstance(c["first"], bool):
            raise ValueError("Changed pair ordering")
        for side in ["left", "right"]:
            rows = c[side + "_trials"]
            if len(rows) != PROTOCOL["pairs"] or [r["kernel_seconds"] for r in rows] != c[side + "_seconds"]:
                raise ValueError("Timing vector does not bind raw trials")
            for r in rows:
                if {k: r[k] for k in m["expected"]} != m["expected"] or r["repetitions"] != m["repetitions"]:
                    raise ValueError("Timed correctness mismatch")
                if not math.isfinite(r["kernel_seconds"]) or r["kernel_seconds"] <= 0:
                    raise ValueError("Invalid kernel duration")
                if not math.isfinite(r["process_elapsed_seconds"]) or r["process_elapsed_seconds"] < r["kernel_seconds"]:
                    raise ValueError("Invalid process duration")
                if any(v < 0 for v in r["scheduler_delta"].values()):
                    raise ValueError("Invalid scheduler evidence")
    if report["complete"]:
        expected_cells = set()
        for ident,m in report["manifests"].items():
            for block in range(PROTOCOL["blocks"]):
                expected_cells.add((ident,"O3",block,"qualification"))
                for choice in MENU:
                    if choice != "O3" and m["aliases"][choice] == choice:
                        for role in ["candidate_control","effect"]:
                            expected_cells.add((ident,choice,block,role))
        if seen != expected_cells:
            raise ValueError("Incomplete timing cell coverage")
    labels, diagnostics = outcomes(report)
    if "accepted" in report and report["accepted"] != labels:
        raise ValueError("Changed accepted labels")
    if "diagnostics" in report and report["diagnostics"] != diagnostics:
        raise ValueError("Changed effect diagnostics")
    return labels, diagnostics
