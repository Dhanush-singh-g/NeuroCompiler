"""Isolated job process for live compilation and optional trusted-code execution.

Resource limits and process-group cancellation bound accidents. This is NOT a
security sandbox: use only your own trusted programs on a local machine.
"""
import hashlib
import json
import math
import os
import platform
import resource
import signal
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from src.benchmarks.compact import MENU, CODEGEN
from src.presentation.model import predict

ROOT = Path(__file__).resolve().parents[2]
PAIRS, BLOCKS = 12, 3


def now():
    return datetime.now(timezone.utc).isoformat()


def save(path, value):
    path = Path(path)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')
    temporary.replace(path)


def digest(value):
    return hashlib.sha256(value).hexdigest()


class JobError(Exception):
    pass


def progress(root, stage, message, percent):
    save(root / 'state.json', {'status': 'running', 'stage': stage, 'message': message, 'percent': percent})


def command(argv, cwd, timeout=20):
    try:
        result = subprocess.run(list(map(str, argv)), cwd=cwd, stdin=subprocess.DEVNULL,
                                capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired as error:
        raise JobError('Compilation exceeded its time limit.') from error
    if result.returncode:
        raise JobError(result.stderr.decode(errors='replace')[-10000:] or 'Compilation failed.')
    return result.stdout.decode(errors='replace')


def analyze(root, request):
    tools = Path(request['llvm_bin'])
    source = root / 'input.c'
    source.write_text(request['source'])
    progress(root, 'compile', 'Compiling C to LLVM bitcode', 12)
    frontend = ['-O1', '-Xclang', '-disable-llvm-passes']
    # Match the historical frontend while discovering, rather than hardcoding,
    # the host GCC include directory. Do not use native CPU or fast-math flags.
    gcc_include = command(['gcc', '-print-file-name=include'], root).strip()
    if not Path(gcc_include).is_dir():
        raise JobError('GCC headers are missing. Install build-essential.')
    frontend += ['-isystem', gcc_include, '-isystem', '/usr/include/x86_64-linux-gnu',
                 '-isystem', '/usr/include']
    initial = root / 'initial.bc'
    command([tools/'clang', *frontend, '-emit-llvm', '-c', source, '-o', initial], root)
    # A separate O0 build provides the output reference; compilation executes
    # no submitted program. Reference is only run after explicit execution.
    command([tools/'clang', '-O0', *frontend[3:], source, '-lm', '-o', root/'reference'], root)
    irs, sizes, aliases, artifacts = {}, {}, {}, {}
    for index, (choice, stages) in enumerate(MENU.items()):
        progress(root, 'pipelines', f'Building pipeline {index+1} of {len(MENU)}', 22 + index*12)
        directory = root / choice
        directory.mkdir()
        current = initial
        for step, flags in enumerate(stages):
            output = directory / f'stage{step}.bc'
            command([tools/'opt', *flags, current, '-o', output], root)
            current = output
        final = directory / 'program.bc'
        final.write_bytes(current.read_bytes())
        command([tools/'clang', final, *CODEGEN, '-lm', '-o', directory/'program'], root)
        ir = command([tools/'llvm-dis', final, '-o', '-'], root)
        (directory/'program.ll').write_text(ir)
        irs[choice] = ir
        sizes[choice] = (directory/'program').stat().st_size
        artifact = {'elf_sha256': digest((directory/'program').read_bytes()),
                    'bitcode_sha256': digest(final.read_bytes()), 'executable_bytes': sizes[choice],
                    'ir_bytes': len(ir.encode()), 'passes': stages}
        artifacts[choice] = artifact
        aliases[choice] = next(c for c, a in artifacts.items() if a['elf_sha256'] == artifact['elf_sha256'])
    progress(root, 'predict', 'Extracting features and freezing the model decision', 85)
    decision = predict(irs, sizes, aliases, len(request['stdin'].encode()), request['iterations'])
    result = {
        'schema': 1, 'kind': 'analysis', 'id': root.name, 'created_at': now(),
        'source_sha256': digest(source.read_bytes()), 'source_bytes': source.stat().st_size,
        'arguments': request['arguments'], 'stdin_bytes': len(request['stdin'].encode()),
        'iterations_descriptor': request['iterations'], 'decision': decision,
        'prediction_frozen_at': now(), 'native_execution': False, 'artifacts': artifacts,
        'compiler': request['compiler'], 'toolchain_sha256': request['toolchain_sha256'],
        'host': {'system': platform.system(), 'machine': platform.machine(),
                 'cpu': platform.processor(), 'platform': platform.platform()},
        'measurement': None,
        'input': {k: request[k] for k in ('source', 'arguments', 'stdin', 'iterations')},
        'reference_sha256': digest((root/'reference').read_bytes()),
    }
    save(root/'result.json', result)
    return result


def limits():
    resource.setrlimit(resource.RLIMIT_CPU, (3, 3))
    resource.setrlimit(resource.RLIMIT_AS, (768*1024*1024, 768*1024*1024))
    resource.setrlimit(resource.RLIMIT_FSIZE, (65536, 65536))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_NOFILE, (32, 32))
    if hasattr(os, 'sched_setaffinity'):
        allowed = os.sched_getaffinity(0)
        os.sched_setaffinity(0, {min(allowed)})


def execute(executable, request, work):
    # Worker is single-threaded, so the POSIX preexec limit hook runs without
    # the multi-threaded HTTP process's locks. No shell or user compile flags.
    with tempfile.TemporaryDirectory(prefix='invocation-', dir=work) as scratch:
        with tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as errors:
            before = resource.getrusage(resource.RUSAGE_CHILDREN)
            start = time.perf_counter_ns()
            process = subprocess.Popen([str(executable), *request['arguments']], cwd=scratch,
                                       stdin=subprocess.PIPE, stdout=output, stderr=errors,
                                       preexec_fn=limits, env={'PATH': '/usr/bin:/bin', 'LANG': 'C', 'LC_ALL': 'C'})
            try:
                process.communicate(request['stdin'].encode(), timeout=2)
            except subprocess.TimeoutExpired as error:
                process.kill()
                process.wait()
                raise JobError('Program exceeded the 2 second limit. Reduce its workload or fix the loop.') from error
            wall = (time.perf_counter_ns()-start)/1e9
            after = resource.getrusage(resource.RUSAGE_CHILDREN)
            cpu = after.ru_utime + after.ru_stime - before.ru_utime - before.ru_stime
            output.seek(0); errors.seek(0)
            stdout, stderr = output.read(65537), errors.read(65537)
            if process.returncode:
                raise JobError(f'Program exited with status {process.returncode}. ' + stderr.decode(errors='replace')[:2000])
            if len(stdout) > 65536 or len(stderr) > 65536:
                raise JobError('Program output exceeded 64 KiB. Print a short deterministic checksum.')
            return {'wall': wall, 'cpu': max(cpu, 1e-9), 'stdout_sha256': digest(stdout),
                    'stdout_bytes': len(stdout), 'stdout_preview': stdout.decode(errors='replace')[:2000]}


def pair_summary(samples, control=False):
    clocks = {}
    for clock in ('cpu', 'wall'):
        ratios = np.array([math.log(s['baseline'][clock]/s['candidate'][clock]) for s in samples])
        boot = np.random.default_rng(20261022).choice(ratios, size=(2000, len(ratios)), replace=True).mean(axis=1)
        interval = np.exp(np.quantile(boot, [.025, .975])).tolist()
        blocks = [float(np.exp(np.mean([r for r,s in zip(ratios,samples) if s['block'] == b]))) for b in range(BLOCKS)]
        order_differences = []
        for block in [None, *range(BLOCKS)]:
            groups = [[r for r,s in zip(ratios,samples) if s['candidate_first'] == first
                       and (block is None or s['block'] == block)] for first in (False, True)]
            order_differences.append(float(abs(np.mean(groups[0])-np.mean(groups[1]))))
        durations = {side: np.asarray([s[side][clock] for s in samples]) for side in ('baseline','candidate')}
        medians = {side: float(np.median(values)) for side, values in durations.items()}
        # Evaluate repeatability within each implementation. Pooling two sides
        # would incorrectly call a large true speed difference "noise".
        cv = max(float(np.std(values)/np.mean(values)) for values in durations.values())
        order_ok = max(order_differences) <= math.log(1.03)
        stable = min(medians.values()) >= .01 and cv <= .10 and order_ok
        null_ok = interval[0] >= 1/1.03 and interval[1] <= 1.03 and all(1/1.03 <= b <= 1.03 for b in blocks)
        clocks[clock] = {'speedup': float(np.exp(ratios.mean())), 'interval': interval,
                         'block_ratios': blocks, 'median_seconds': medians['candidate'],
                         'baseline_median_seconds': medians['baseline'], 'coefficient_of_variation': cv,
                         'max_order_log_difference': max(order_differences), 'order_ok': order_ok,
                         'stable': stable, 'qualified': stable and (null_ok if control else True)}
    return {'clocks': clocks, 'qualified': all(c['qualified'] for c in clocks.values()), 'samples': samples}


def compare(root, request):
    analysis_root = Path(request['analysis_root'])
    result = json.loads((analysis_root/'result.json').read_text())
    original = json.loads((analysis_root/'request.json').read_text())
    if digest((analysis_root/'input.c').read_bytes()) != result['source_sha256']:
        raise JobError('Source changed after prediction; analyze again.')
    if digest((analysis_root/'reference').read_bytes()) != result['reference_sha256']:
        raise JobError('Correctness reference changed after prediction; analyze again.')
    if any(original[k] != result['input'][k] for k in ('source','arguments','stdin','iterations')):
        raise JobError('Input changed after prediction; analyze again.')
    executables = {c: analysis_root/c/'program' for c in MENU}
    for c, path in executables.items():
        if digest(path.read_bytes()) != result['artifacts'][c]['elf_sha256']:
            raise JobError('Compiled artifact changed after prediction; analyze again.')
    result.update({'kind': 'comparison', 'id': root.name, 'analysis_id': analysis_root.name,
                   'native_execution': True, 'measurement_started_at': now(), 'created_at': now()})
    progress(root, 'correctness', 'Checking deterministic output against the O0 reference', 8)
    checks, expected = {}, None
    for label, executable in [('O0 reference', analysis_root/'reference'), *executables.items()]:
        invocations = [execute(executable, original, root) for _ in range(2)]
        if expected is None:
            expected = invocations[0]['stdout_sha256']
        checks[label] = {'passed': all(i['stdout_sha256'] == expected for i in invocations),
                         'stdout_sha256': invocations[0]['stdout_sha256'],
                         'invocation_sha256': [i['stdout_sha256'] for i in invocations],
                         'stdout_preview': invocations[0]['stdout_preview'], 'invocations': 2}
    result['correctness'] = {'passed': all(c['passed'] for c in checks.values()), 'checks': checks,
                              'scope': 'Exit code and exact stdout for two executions on ONE supplied input. Not proof for all inputs; file side effects are not checked.'}
    if not result['correctness']['passed']:
        result['measurement'] = {'status': 'blocked', 'reason': 'Output mismatch or nondeterministic program; no timings collected.'}
        return result
    canonical = [c for c in MENU if result['decision']['aliases'][c] == c and c != 'O3']
    cells = {}
    for cell_index, choice in enumerate(['O3', *canonical]):
        samples = []
        progress(root, 'measure', f'Measuring {choice}: balanced paired runs', 25+int(65*cell_index/(1+len(canonical))))
        for index in range(PAIRS):
            first = bool(index % 2)
            pair = {}
            for side in (['candidate', 'baseline'] if first else ['baseline', 'candidate']):
                actual = choice if side == 'candidate' else 'O3'
                invocation = execute(executables[actual], original, root)
                if invocation['stdout_sha256'] != expected:
                    raise JobError('Output changed during measurement. Timings are invalid.')
                pair[side] = {clock: invocation[clock] for clock in ('cpu', 'wall')}
            samples.append({'block': index//4, 'candidate_first': first, **pair})
        cells[choice] = pair_summary(samples, control=choice == 'O3')
    for choice in MENU:
        if choice not in cells:
            canonical_choice = result['decision']['aliases'][choice]
            cells[choice] = {'alias_of': canonical_choice, **cells[canonical_choice]}
    for choice, cell in cells.items():
        qualified = cells['O3']['qualified'] and cell['qualified']
        if choice == 'O3' or result['decision']['aliases'][choice] == 'O3':
            cell['verdict'] = 'same_binary' if qualified else 'inconclusive'
        elif not qualified:
            cell['verdict'] = 'inconclusive'
        elif all(c['interval'][0] > 1.03 for c in cell['clocks'].values()):
            cell['verdict'] = 'faster_in_demo'
        elif all(c['interval'][1] < 1/1.03 for c in cell['clocks'].values()):
            cell['verdict'] = 'slower_in_demo'
        else:
            cell['verdict'] = 'no_clear_difference'
    result['measurement'] = {
        'status': 'completed', 'cells': cells, 'self_control_passed': cells['O3']['qualified'],
        'pairs_per_distinct_cell': PAIRS, 'blocks': BLOCKS,
        'timer': 'Whole process wall time and child CPU service time, including startup; not library API time.',
        'quality_rule': 'Both clocks: >=10 ms median, <=10% duration CV, <=3% pooled/every-block starting-order difference. O3 null: 95% paired-bootstrap interval and every block within reciprocal 3%.',
        'interval_scope': 'Exploratory paired bootstrap of 12 pairs; does not capture cross-machine or full systematic uncertainty.',
        'scope': 'Presentation experiment only. Not the frozen research protocol, new training data, or proof of learned generalization. All samples retained.',
    }
    return result


def main():
    root = Path(sys.argv[1]).resolve()
    request = json.loads((root/'request.json').read_text())
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(JobError('Job exceeded its 120 second total limit.')))
    signal.alarm(120)
    try:
        result = analyze(root, request) if request['operation'] == 'analyze' else compare(root, request)
        save(root/'result.json', result)
        save(root/'state.json', {'status': 'completed', 'stage': 'complete', 'percent': 100, 'message': 'Experiment complete'})
    except Exception as error:
        save(root/'state.json', {'status': 'failed', 'stage': 'error', 'percent': 100, 'message': str(error)[:10000]})
        # Terminate descendants too, including an accidental fork on timeout.
        os.killpg(os.getpgrp(), signal.SIGKILL)
    finally:
        signal.alarm(0)


if __name__ == '__main__':
    main()
