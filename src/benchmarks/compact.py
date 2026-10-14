"""Frozen complete-menu experiments against LLVM 10 opt -O3.

Builds and correctness checks happen outside blocking native timings. No
CompilerGym Runtime observations or instruction counts are used as targets.
"""
import hashlib
import json
import math
import subprocess
import time
from pathlib import Path

import numpy as np

from configs.benchmarks import TRAIN_BENCHMARKS, VALIDATION_BENCHMARKS

MENU = {
    "O3": [["-O3"]],
    "mem2reg_loop_rotate_licm_O3": [["-mem2reg", "-loop-rotate", "-licm"], ["-O3"]],
    "O3_gvn_dce": [["-O3"], ["-gvn", "-dce"]],
    "instcombine_O3": [["-instcombine"], ["-O3"]],
}
CODEGEN = ["-O3", "-Xclang", "-disable-llvm-passes"]
SEED = 20261010
TRAIN_CASES = [("bitcount", 0, 1125000), ("bitcount", 0, 11250000),
               ("blowfish", 3, 0), ("bzip2", 11, 0), ("crc32", 1, 0),
               ("dijkstra", 10, 0), ("gsm", 5, 0), ("jpeg-c", 14, 0),
               ("patricia", 19, 0), ("qsort", 19, 0), ("stringsearch", 3, 0),
               ("tiff2bw", 2, 0)]
VALIDATION_CASES = [("jpeg-d", 2, 0), ("jpeg-d", 16, 0),
                    ("tiffdither", 2, 0), ("tiffdither", 10, 0),
                    ("stringsearch2", 0, 0)]
PROTOCOL = {"menu": MENU, "seed": SEED, "blocks": 4, "pairs": 10,
            "warmups_per_executable_per_cell": 1, "cpu": 2,
            "control_tolerance": .03, "gain_floor": .03,
            "profile_runs": 3, "duration_seconds": [.025, .5],
            "codegen": CODEGEN, "bootstrap_replicates": 2000,
            "menu_selection": "prior training search; conditional grouped CV",
            "timer": "perf_counter_ns around blocking subprocess.run including launch"}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    tmp.replace(path)


def case_id(case):
    name, index, iterations = case
    return f"{name}_{index}" + (f"_iters{iterations}" if iterations else "")


def scope(split):
    if split == "train":
        return TRAIN_CASES
    if split == "validation":
        return VALIDATION_CASES
    raise ValueError("Reserved test programs are not available to this experiment")


def run(manifest, name, check_output=False):
    artifact = manifest["artifacts"][name]
    directory = Path(artifact["directory"])
    # Every invocation has the same output cleanup; it is outside the timer.
    for output in manifest["outputs"]:
        (directory / output).unlink(missing_ok=True)
    command = ["taskset", "-c", str(PROTOCOL["cpu"]), "./a.out", *manifest["arguments"]]
    begin = time.perf_counter_ns()
    result = subprocess.run(command, cwd=directory, capture_output=True, timeout=300, check=True)
    elapsed = (time.perf_counter_ns() - begin) / 1e9
    if check_output:
        actual = {"stdout": hashlib.sha256(result.stdout).hexdigest(),
                  "files": {f: sha(directory / f) for f in manifest["outputs"]}}
        if actual != manifest["expected_output"]:
            raise ValueError(f"Output mismatch: {manifest['id']} / {name}")
    return elapsed


def freeze(case, directory, split):
    import compiler_gym
    from compiler_gym.third_party import llvm

    name, index, iterations = case
    program = f"benchmark://cbench-v1/{name}"
    allowed = TRAIN_BENCHMARKS if split == "train" else VALIDATION_BENCHMARKS
    if program not in allowed or case not in scope(split):
        raise ValueError("Case outside frozen split")
    directory = Path(directory).resolve()
    directory.mkdir(parents=True, exist_ok=False)
    with compiler_gym.make("llvm-v0") as env:
        env.reset(benchmark=f"{program}?dataset={index}")
        features = [int(x) for x in env.observation["Autophase"]]
        initial = directory / "initial.bc"
        env.write_bitcode(initial)
        config = env.benchmark.proto.dynamic_config
        arguments = list(config.run_cmd.argument)
        if arguments.pop(0) != "./a.out":
            raise ValueError("Unsupported runtime command")
        if iterations:
            if name != "bitcount" or arguments != ["1125000"]:
                raise ValueError("Unexpected bitcount command")
            arguments = [str(iterations)]
        inputs = {str(Path(a).resolve()): sha(a) for a in arguments if Path(a).is_file()}
        features += [sum(Path(a).stat().st_size for a in inputs), iterations]
        manifest = {"id": case_id(case), "case": list(case), "program": program,
                    "split": split, "features": features, "arguments": arguments,
                    "inputs": inputs, "source": str(initial), "source_sha256": sha(initial),
                    "outputs": list(config.run_cmd.outfile), "artifacts": {}, "aliases": {},
                    "expected_output": None}
        if [list(c.argument) for c in config.pre_run_cmd] != [["echo", "1", ">_finfo_dataset"]]:
            raise ValueError("Unsupported setup command")
        for choice, stages in MENU.items():
            dest = directory / choice
            dest.mkdir()
            current = initial
            for i, flags in enumerate(stages):
                output = dest / f"stage{i}.bc"
                subprocess.run([str(llvm.opt_path()), *flags, str(current), "-o", str(output)],
                               check=True, capture_output=True, timeout=120)
                current = output
            bc = dest / "program.bc"
            bc.write_bytes(current.read_bytes())
            build = [str(llvm.clang_path()) if a == "$CC" else str(bc) if a == "$IN" else a
                     for a in config.build_cmd.argument]
            subprocess.run([*build, *CODEGEN, "-o", "a.out"], cwd=dest, check=True,
                           capture_output=True, timeout=120)
            (dest / "_finfo_dataset").write_text("1\n")
            artifact = {"directory": str(dest), "bc_sha256": sha(bc), "elf_sha256": sha(dest / "a.out"),
                        "build": [*build, *CODEGEN, "-o", "a.out"]}
            manifest["artifacts"][choice] = artifact
            # The first O3 invocation establishes the byte-exact reference.
            if choice == "O3":
                result = subprocess.run(["./a.out", *arguments], cwd=dest, capture_output=True,
                                        check=True, timeout=300)
                manifest["expected_output"] = {"stdout": hashlib.sha256(result.stdout).hexdigest(),
                    "files": {f: sha(dest / f) for f in manifest["outputs"]}}
            run(manifest, choice, check_output=True)
            run(manifest, choice, check_output=True)
            manifest["aliases"][choice] = next(
                k for k, a in manifest["artifacts"].items() if a["elf_sha256"] == artifact["elf_sha256"])
    save(directory / "manifest.json", manifest)
    return manifest


def verify_manifest(m, split, artifacts=True):
    if m["case"] not in [list(c) for c in scope(split)] or m["split"] != split:
        raise ValueError("Manifest split/case mismatch")
    if m["id"] != case_id(m["case"]) or m["program"] != f"benchmark://cbench-v1/{m['case'][0]}":
        raise ValueError("Manifest program mismatch")
    x = np.asarray(m["features"], dtype=float)
    if x.shape != (58,) or not np.isfinite(x).all() or (x < 0).any():
        raise ValueError("Invalid static features")
    if list(m["artifacts"]) != list(MENU) or set(m["aliases"]) != set(MENU):
        raise ValueError("Incomplete menu")
    for name, a in m["artifacts"].items():
        alias = next(k for k, v in m["artifacts"].items() if v["elf_sha256"] == a["elf_sha256"])
        if m["aliases"][name] != alias:
            raise ValueError("Invalid executable alias")
        if artifacts and (sha(Path(a["directory"]) / "program.bc") != a["bc_sha256"] or
                          sha(Path(a["directory"]) / "a.out") != a["elf_sha256"]):
            raise ValueError("Frozen artifact changed")
    if artifacts:
        if sha(m["source"]) != m["source_sha256"] or any(sha(p) != h for p, h in m["inputs"].items()):
            raise ValueError("Frozen source/input changed")


def measure_cell(manifest, left, right, block, role, first, protocol=PROTOCOL):
    # Immutable executables are built once. Same-executable controls measure
    # the timer noise rather than a second compiler build.
    run(manifest, left, True)
    run(manifest, right, True)
    a, b = [], []
    for pair in range(protocol["pairs"]):
        left_first = (pair % 2 == 0) == first
        if left_first:
            ta, tb = run(manifest, left), run(manifest, right)
        else:
            tb, ta = run(manifest, right), run(manifest, left)
        a.append(ta)
        b.append(tb)
    return {"case": manifest["id"], "choice": right if role == "effect" else left,
            "block": block, "role": role, "left": left, "right": right,
            "first": first, "left_seconds": a, "right_seconds": b}


def effect(cells, protocol=PROTOCOL):
    if len(cells) != protocol["blocks"]:
        raise ValueError("Incomplete timing blocks")
    logs = np.log(np.asarray([c["left_seconds"] for c in cells]) /
                  np.asarray([c["right_seconds"] for c in cells]))
    if logs.shape != (protocol["blocks"], protocol["pairs"]) or not np.isfinite(logs).all():
        raise ValueError("Invalid timings")
    rng = np.random.default_rng(protocol["seed"])
    blocks, pairs = logs.shape
    ib = rng.integers(blocks, size=(protocol["bootstrap_replicates"], blocks))
    ip = rng.integers(pairs, size=(*ib.shape, pairs))
    boot = np.median(np.median(logs[ib[..., None], ip], axis=2), axis=1)
    interval = np.exp(np.quantile(boot, [.025, .975])).tolist()
    medians = np.exp(np.median(logs, axis=1)).tolist()
    even = logs[:, ::2].reshape(-1)
    odd = logs[:, 1::2].reshape(-1)
    bias = abs(float(np.median(even) - np.median(odd)))
    tol = protocol["control_tolerance"]
    control = (all(1/(1+tol) <= x <= 1+tol for x in medians)
               and interval[0] >= 1/(1+tol) and interval[1] <= 1+tol
               and bias <= math.log1p(tol))
    return {"log_speedup": float(np.median(np.median(logs, axis=1))),
            "speedup": float(np.exp(np.median(np.median(logs, axis=1)))),
            "interval": interval, "blocks": medians, "order_log_difference": bias,
            "control_pass": bool(control)}


def summarize(report, protocol=PROTOCOL):
    rows = []
    for ident, manifest in report["manifests"].items():
        if not report["profiles"][ident]["eligible"]:
            continue
        records = [r for r in report["records"] if r["case"] == ident]
        qualification = [r for r in records if r["role"] == "qualification"]
        if len(qualification) != protocol["blocks"]:
            continue
        q = effect(qualification, protocol)
        if not q["control_pass"]:
            continue
        stats = {"O3": {"log_speedup": 0., "speedup": 1., "confirmed_gain": False}}
        complete = True
        for choice in MENU:
            alias = manifest["aliases"][choice]
            if alias in stats:
                stats[choice] = stats[alias].copy()
                continue
            outcomes = [r for r in records if r["choice"] == alias and r["role"] == "effect"]
            controls = [r for r in records if r["choice"] == alias and r["role"] == "candidate_control"]
            if len(outcomes) != protocol["blocks"] or len(controls) != protocol["blocks"]:
                complete = False
                break
            s, c = effect(outcomes, protocol), effect(controls, protocol)
            if not c["control_pass"]:
                complete = False
                break
            floor = 1 + protocol["gain_floor"]
            s["confirmed_gain"] = bool(s["interval"][0] > floor and all(x > floor for x in s["blocks"]))
            s["candidate_control"] = c
            stats[choice] = s
        if complete:
            rows.append({"case": ident, "program": manifest["program"], "features": manifest["features"],
                         "outcomes": stats, "o3_control": q})
    return rows


def verify_report(report, artifacts=True, completed=True):
    if report["protocol"] != PROTOCOL or report["split"] not in ("train", "validation"):
        raise ValueError("Changed protocol/split")
    if completed and not report["complete"]:
        raise ValueError("Incomplete experiment")
    expected = {case_id(c) for c in scope(report["split"])}
    if completed and (set(report["manifests"]) != expected or set(report["profiles"]) != expected):
        raise ValueError("Incomplete case coverage")
    for key, m in report["manifests"].items():
        if key != m["id"]:
            raise ValueError("Manifest key mismatch")
        verify_manifest(m, report["split"], artifacts)
    seen = set()
    for r in report["records"]:
        key = (r["case"], r["role"], r["choice"], r["block"])
        if key in seen:
            raise ValueError("Duplicate timing record")
        seen.add(key)
        m = report["manifests"][r["case"]]
        if not report["profiles"][r["case"]]["eligible"] or r["block"] not in range(PROTOCOL["blocks"]):
            raise ValueError("Timing outside eligible scope")
        if r["role"] == "qualification":
            expected_pair = ("O3", "O3", "O3")
        elif r["role"] == "candidate_control":
            expected_pair = (r["choice"], r["choice"], r["choice"])
        elif r["role"] == "effect":
            expected_pair = ("O3", r["choice"], r["choice"])
        else:
            raise ValueError("Unknown timing role")
        if (r["left"], r["right"], r["choice"]) != expected_pair or r["choice"] not in MENU:
            raise ValueError("Invalid paired comparison")
        if m["aliases"][r["choice"]] != r["choice"] or (r["role"] != "qualification" and r["choice"] == "O3"):
            raise ValueError("Unexpected alias measurement")
        for field in ("left_seconds", "right_seconds"):
            values = np.asarray(r[field], dtype=float)
            if values.shape != (PROTOCOL["pairs"],) or not np.isfinite(values).all() or (values <= 0).any():
                raise ValueError("Invalid runtime data")
    for ident, profile in report["profiles"].items():
        times = profile["seconds"]
        if len(times) != PROTOCOL["profile_runs"] or not np.isfinite(times).all() or any(t <= 0 for t in times):
            raise ValueError("Invalid duration samples")
        eligible = PROTOCOL["duration_seconds"][0] <= float(np.median(times)) <= PROTOCOL["duration_seconds"][1]
        if len(times) != PROTOCOL["profile_runs"] or profile["eligible"] != eligible:
            raise ValueError("Invalid duration qualification")
        if completed and eligible:
            q = [r for r in report["records"] if r["case"] == ident and r["role"] == "qualification"]
            if len(q) != PROTOCOL["blocks"]:
                raise ValueError("Missing qualification")
            if effect(q)["control_pass"]:
                unique = set(report["manifests"][ident]["aliases"].values()) - {"O3"}
                for choice in unique:
                    for role in ("effect", "candidate_control"):
                        if sum(r["case"] == ident and r["choice"] == choice and r["role"] == role for r in report["records"]) != PROTOCOL["blocks"]:
                            raise ValueError("Missing complete-menu measurements")
    if completed and report["labels"] != summarize(report):
        raise ValueError("Labels do not match raw timings")
