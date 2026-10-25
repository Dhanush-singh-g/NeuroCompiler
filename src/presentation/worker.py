"""Isolated job process for live compilation and optional trusted-code execution.

Resource limits and process-group cancellation bound accidents. This is NOT a
security sandbox: use only your own trusted programs on a local machine.
"""
import hashlib
import itertools
import json
import math
import os
import platform
import signal
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from src.benchmarks.compact import MENU, CODEGEN
from src.presentation.model import predict, MODEL_PATH
from src.presentation.summary import comparison_summary
from src.presentation.four_way import four_way_summary
from src.hybrid.sequential import rollout, MODEL_PATH as SEQUENTIAL_MODEL_PATH
from src.hybrid.support import attach_support
from src.rl.llvm_environment import ACTIONS, FEATURE_NAMES as SEQUENTIAL_FEATURE_NAMES
from src.features.transform import parse_ir, summaries, METRICS

ROOT = Path(__file__).resolve().parents[2]
PAIRS, BLOCKS = 12, 3
_order_rng = np.random.default_rng(20261022)
PAIR_ORDER = [bool(value) for _ in range(BLOCKS)
              for value in _order_rng.permutation([False, False, True, True])]


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
    command(['gcc', '-std=c11', '-O2', '-Wall', '-Wextra', ROOT/'src/presentation/native_runner.c',
             '-o', root/'native-runner'], root)
    irs, sizes, aliases, artifacts = {}, {}, {}, {}
    def build(choice, stages, codegen, input_bc=None):
        directory = root / choice
        directory.mkdir()
        current = initial if input_bc is None else input_bc
        for step, flags in enumerate(stages):
            output = directory / f'stage{step}.bc'
            command([tools/'opt', *flags, current, '-o', output], root)
            current = output
        final = directory / 'program.bc'
        final.write_bytes(current.read_bytes())
        command([tools/'clang', final, *codegen, '-lm', '-o', directory/'program'], root)
        ir = command([tools/'llvm-dis', final, '-o', '-'], root)
        (directory/'program.ll').write_text(ir)
        irs[choice] = ir
        sizes[choice] = (directory/'program').stat().st_size
        artifacts[choice] = {'elf_sha256': digest((directory/'program').read_bytes()),
                            'bitcode_sha256': digest(final.read_bytes()), 'executable_bytes': sizes[choice],
                            'ir_bytes': len(ir.encode()), 'passes': stages, 'codegen':codegen}
        aliases[choice] = next(c for c,a in artifacts.items() if a['elf_sha256']==artifacts[choice]['elf_sha256'])
    for index,(choice,stages) in enumerate(MENU.items()):
        progress(root,'pipelines',f'Building model candidate {index+1} of 4',20+index*10)
        build(choice,stages,CODEGEN)
    progress(root,'predict','Freezing the model decision before baseline comparison',65)
    decision = predict(irs, sizes, dict(aliases), len(request['stdin'].encode()), request['iterations'])
    mode=request.get('policy_mode','legacy')
    if mode!='legacy':
        progress(root,'predict',f'Applying trained {mode} instruction-count policy',65)
        sequential,final_bc=rollout(tools,initial,root/'sequential_episode',mode,request['toolchain_sha256'],
            baseline={'instructions':decision['metrics']['O3']['instructions'],'path':root/'O3/program.bc','step':0})
        attach_support(sequential,tools,root/'sequential_episode',root/'support_diagnostics')
        build('LearnedPolicy',[],CODEGEN,input_bc=final_bc)
        artifacts['LearnedPolicy']['passes']=(MENU['O3'] if sequential['selection']['applied']=='O3' else
            [ACTIONS[action] for action in sequential['selected_actions']])
        counts,_indirect=summaries(parse_ir(irs['LearnedPolicy']))
        decision['metrics']['LearnedPolicy']=dict(zip(METRICS,map(int,counts[0])))
        decision.update(choice='LearnedPolicy',policy=mode+'_instruction_count',mode=mode,sequential=sequential,
                        model_sha256=sequential['model_sha256'],model_source_sha256=sequential['model_sha256'],
                        scores={},explanations={},vectors={},feature_count=len(SEQUENTIAL_FEATURE_NAMES),aliases=dict(aliases),
                        reason='A trained '+mode+' policy proposed passes; a static checkpoint/O3 guard selected the emitted artifact before native execution.',
                        diagnostics={'recommendation_notes':['Instruction-count objective, not runtime-trained. Static checkpoint/O3 guard prevents count regressions, not runtime regressions. Synthetic evaluation is not real-world qualification.']})
    prediction_frozen = now()
    for index,choice in enumerate(('O1','O2')):
        progress(root,'baselines',f'Building {choice} comparison baseline; prediction already frozen',75+index*10)
        build(choice,[[f'-{choice}']],[f'-{choice}','-Xclang','-disable-llvm-passes'])
    comparison_metrics = dict(decision['metrics'])
    for choice in ('O1','O2'):
        totals,indirect = summaries(parse_ir(irs[choice]))
        comparison_metrics[choice] = {**dict(zip(METRICS,map(int,totals[0]))),
                                      'indirect_reachability':bool(indirect)}
    result = {
        'schema': 1, 'kind': 'analysis', 'id': root.name, 'created_at': now(),
        'source_sha256': digest(source.read_bytes()), 'source_bytes': source.stat().st_size,
        'arguments': request['arguments'], 'stdin_bytes': len(request['stdin'].encode()),
        'iterations_descriptor': request['iterations'], 'decision': decision,
        'prediction_frozen_at': prediction_frozen, 'native_execution': False, 'artifacts': artifacts,
        'comparison_baselines_built_at': now(),
        'compiler': request['compiler'], 'toolchain_sha256': request['toolchain_sha256'],
        'host': {'system': platform.system(), 'machine': platform.machine(),
                 'cpu': platform.processor(), 'platform': platform.platform()},
        'measurement': None,
        'input': {**{k: request[k] for k in ('source', 'arguments', 'stdin', 'iterations')},'policy_mode':mode},
        'comparison_options': {'O1':'O1','O2':'O2','O3':'O3','NeuroCompiler':decision['choice']},
        'artifact_aliases':aliases, 'comparison_metrics':comparison_metrics,
        'reference_sha256': digest((root/'reference').read_bytes()),
        'runner_sha256': digest((root/'native-runner').read_bytes()),
        'runner_source_sha256': digest((ROOT/'src/presentation/native_runner.c').read_bytes()),
    }
    save(root/'result.json', result)
    return result


def execute(executable, request, work):
    analysis = executable.parent if executable.name == 'reference' else executable.parent.parent
    runner = analysis/'native-runner'
    if not runner.is_file():
        raise JobError('Timing helper is missing. Analyze the program again.')
    with tempfile.TemporaryDirectory(prefix='invocation-', dir=work) as scratch:
        with tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as errors, tempfile.TemporaryFile() as timing:
            process = subprocess.Popen([str(runner), str(timing.fileno()), str(executable), *request['arguments']], cwd=scratch,
                                       stdin=subprocess.PIPE, stdout=output, stderr=errors,
                                       pass_fds=(timing.fileno(),),
                                       env={'PATH': '/usr/bin:/bin', 'LANG': 'C', 'LC_ALL': 'C'})
            try:
                process.communicate(request['stdin'].encode(), timeout=2)
            except subprocess.TimeoutExpired as error:
                process.kill()
                process.wait()
                raise JobError('Program exceeded the 2 second limit. Reduce its workload or fix the loop.') from error
            output.seek(0); errors.seek(0)
            stdout, stderr = output.read(65537), errors.read(65537)
            if process.returncode:
                raise JobError(f'Native timing helper exited with status {process.returncode}. ' + stderr.decode(errors='replace')[:2000])
            timing.seek(0)
            measured = json.loads(timing.read(2048))
            if measured['exit_code']:
                raise JobError(f"Program exited with status {measured['exit_code']}. " + stderr.decode(errors='replace')[:2000])
            if any(not math.isfinite(measured[c]) or measured[c] < 0 for c in ('cpu','wall')):
                raise JobError('Invalid native timing result.')
            if len(stdout) > 65536 or len(stderr) > 65536:
                raise JobError('Program output exceeded 64 KiB. Print a short deterministic checksum.')
            return {'wall': measured['wall'], 'cpu': max(measured['cpu'], 1e-9),
                    'cpu_id': measured['cpu_id'], 'stdout_sha256': digest(stdout),
                    'stdout_bytes': len(stdout), 'stdout_preview': stdout.decode(errors='replace')[:2000]}


def pair_summary(samples, control=False, family_size=1):
    clocks = {}
    for clock in ('cpu', 'wall'):
        ratios = np.array([math.log(s['baseline'][clock]/s['candidate'][clock]) for s in samples])
        boot = np.random.default_rng(20261022).choice(ratios, size=(8000, len(ratios)), replace=True).mean(axis=1)
        interval = np.exp(np.quantile(boot, [.025/family_size, 1-.025/family_size])).tolist()
        blocks = [float(np.exp(np.mean([r for r,s in zip(ratios,samples) if s['block'] == b]))) for b in range(BLOCKS)]
        order_differences = []
        for block in [None, *range(BLOCKS)]:
            groups = [[r for r,s in zip(ratios,samples) if s['candidate_first'] == first
                       and (block is None or s['block'] == block)] for first in (False, True)]
            order_differences.append(float(abs(np.mean(groups[0])-np.mean(groups[1]))))
        durations = {side: np.asarray([s[side][clock] for s in samples]) for side in ('baseline','candidate')}
        medians = {side: float(np.median(values)) for side, values in durations.items()}
        geometric = {side: float(np.exp(np.log(values).mean())) for side, values in durations.items()}
        # Evaluate repeatability within each implementation. Pooling two sides
        # would incorrectly call a large true speed difference "noise".
        cv = max(float(np.std(values)/np.mean(values)) for values in durations.values())
        order_ok = max(order_differences) <= math.log(1.03)
        stable = min(medians.values()) >= .01 and cv <= .10 and order_ok
        null_ok = interval[0] >= 1/1.03 and interval[1] <= 1.03 and all(1/1.03 <= b <= 1.03 for b in blocks)
        clocks[clock] = {'speedup': float(np.exp(ratios.mean())), 'interval': interval,
                         'block_ratios': blocks, 'median_seconds': medians['candidate'],
                         'baseline_median_seconds': medians['baseline'], 'coefficient_of_variation': cv,
                         'baseline_geometric_seconds': geometric['baseline'],
                         'candidate_geometric_seconds': geometric['candidate'],
                         'max_order_log_difference': max(order_differences), 'order_ok': order_ok,
                         'stable': stable, 'qualified': stable and (null_ok if control else True)}
    return {'clocks': clocks, 'qualified': all(c['qualified'] for c in clocks.values()), 'samples': samples}


def compare(root, request):
    analysis_root = Path(request['analysis_root'])
    result = json.loads((analysis_root/'result.json').read_text())
    original = json.loads((analysis_root/'request.json').read_text())
    model_path=SEQUENTIAL_MODEL_PATH if result['decision'].get('sequential') else MODEL_PATH
    if digest(model_path.read_bytes()) != result['decision']['model_sha256']:
        raise JobError('Model changed after prediction; analyze again.')
    if digest((analysis_root/'input.c').read_bytes()) != result['source_sha256']:
        raise JobError('Source changed after prediction; analyze again.')
    if digest((analysis_root/'reference').read_bytes()) != result['reference_sha256']:
        raise JobError('Correctness reference changed after prediction; analyze again.')
    if digest((analysis_root/'native-runner').read_bytes()) != result['runner_sha256']:
        raise JobError('Timing helper changed after prediction; analyze again.')
    if (any(original[k] != result['input'][k] for k in ('source','arguments','stdin','iterations'))
            or original.get('policy_mode','legacy') != result['input'].get('policy_mode','legacy')):
        raise JobError('Input changed after prediction; analyze again.')
    executables = {c: analysis_root/c/'program' for c in result['artifacts']}
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
    options = result['comparison_options']
    aliases = result['artifact_aliases']
    canonical = list(dict.fromkeys(['O3', *[aliases[c] for c in options.values()]]))
    combinations = list(itertools.combinations(canonical,2))
    family_size = 2*(len(canonical)+len(combinations))
    controls, pairs, cells = {}, [], {}
    tasks = [(c,c,True) for c in canonical]+[(a,b,False) for a,b in combinations]
    # Fixed shuffled cell order, independently balanced starting order per block.
    order = np.random.default_rng(20261025).permutation(len(tasks))
    for cell_index,position in enumerate(order):
        left,right,is_control = tasks[position]
        samples = []
        progress(root,'measure',f'Four-way comparison: cell {cell_index+1} of {len(tasks)} ({left} / {right})',25+int(65*cell_index/len(tasks)))
        for index in range(PAIRS):
            first = PAIR_ORDER[index]
            pair = {}
            for side in (['candidate','baseline'] if first else ['baseline','candidate']):
                actual = right if side=='candidate' else left
                invocation = execute(executables[actual],original,root)
                if invocation['stdout_sha256'] != expected:
                    raise JobError('Output changed during measurement. Timings are invalid.')
                pair[side] = {field:invocation[field] for field in ('cpu','wall','cpu_id')}
            samples.append({'block':index//4,'candidate_first':first,**pair})
        cell = pair_summary(samples,control=is_control,family_size=family_size)
        if is_control:
            controls[left] = cell
        else:
            pairs.append({'left':left,'right':right,'cell':cell})
    cells['O3'] = controls['O3']
    for pair in pairs:
        if pair['left']=='O3':
            cells[pair['right']] = pair['cell']
    for artifact in options.values():
        if artifact not in cells:
            cells[artifact] = {'alias_of':aliases[artifact],**cells[aliases[artifact]]}
    for choice,cell in cells.items():
        canonical_choice = aliases[choice]
        qualified = controls['O3']['qualified'] and controls[canonical_choice]['qualified'] and cell['qualified']
        # Joint qualification includes the candidate's identical-code self-control.
        cell['qualified'] = qualified
        if canonical_choice=='O3':
            cell['verdict'] = 'same_binary' if qualified else 'inconclusive'
        elif not qualified:
            cell['verdict'] = 'inconclusive'
        elif all(c['interval'][0]>1.03 for c in cell['clocks'].values()):
            cell['verdict'] = 'faster_in_demo'
        elif all(c['interval'][1]<1/1.03 for c in cell['clocks'].values()):
            cell['verdict'] = 'slower_in_demo'
        else:
            cell['verdict'] = 'no_clear_difference'
    result['measurement'] = {
        'protocol': 'live-four-way-v3',
        'status': 'completed', 'cells': cells, 'self_control_passed': cells['O3']['qualified'],
        'self_controls':controls, 'head_to_head':pairs, 'display_options':options,
        'interval_family_size':family_size, 'bootstrap_replicates':8000,
        'pairs_per_distinct_cell': PAIRS, 'blocks': BLOCKS,
        'candidate_first_schedule': PAIR_ORDER,
        'timer': 'Native fork/exec/wait4 process wall and child CPU time, including executable startup. Python launch/setup is excluded. Not library API time.',
        'quality_rule': 'Both clocks: >=10 ms median, <=10% duration CV, <=3% pooled/every-block starting-order difference. Every executable self-control: multiplicity-adjusted bootstrap interval and every block within reciprocal 3%.',
        'interval_scope': 'Exploratory 8000-replicate bootstrap of 12 pairs, Bonferroni tail adjustment across all cells and both clocks. Does not capture full systematic or cross-machine uncertainty.',
        'scope': 'Presentation experiment only. Not the frozen research protocol, new training data, or proof of learned generalization. All samples retained.',
    }
    result['measurement']['summary'] = comparison_summary(result['decision'], cells)
    result['measurement']['four_way'] = four_way_summary(options,aliases,controls,pairs)
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
