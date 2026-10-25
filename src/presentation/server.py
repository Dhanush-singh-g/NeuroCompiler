"""Local-only live application with serialized compiler jobs and explicit execution."""
import argparse
import hashlib
import json
import os
import re
import secrets
import shlex
import signal
import subprocess
import sys
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

from src.presentation.model import ROOT, load_model
from src.presentation.worker import save
from src.presentation.scorecard import session_scorecard
from src.hybrid.sequential import load_agent
from src.rl.live_evidence import audit_live

ASSETS = {'index.html': 'text/html', 'app.js': 'application/javascript', 'style.css': 'text/css', 'favicon.svg':'image/svg+xml'}
RESEARCH_ASSETS = {'index.html', 'app.js', 'style.css', 'data.json', 'results.js',
                   'reports/EXPANDED_SL.md', 'reports/PERSISTENT_SL.md', 'reports/FINAL_ASSESSMENT.md'}
ID = re.compile(r'^[a-f0-9]{16}$')


def toolchain(directory=None):
    candidates = [directory, os.environ.get('NEUROCOMPILER_LLVM10'),
                  ROOT/'.presentation/toolchain/bin',
                  Path(os.environ.get('COMPILER_GYM_SITE_DATA', '/nonexistent'))/'llvm-v0/bin',
                  '/workspace/.neurocompiler/compiler-gym-data/llvm-v0/bin']
    selected = next((Path(p).resolve() for p in candidates if p and (Path(p)/'clang').is_file()), None)
    if not selected:
        raise ValueError('LLVM10 tools not found. Run bash scripts/setup_presentation.sh, or set NEUROCOMPILER_LLVM10 to their bin directory.')
    manifest = json.loads((ROOT/'presentation/toolchain.json').read_text())
    hashes = {}
    for name, expected in manifest['binaries'].items():
        path = selected/name
        if not path.is_file():
            raise ValueError(f'Missing tool: {name}')
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError(f'{name} differs from the pinned LLVM10 model toolchain. Use the supplied installer.')
        hashes[name] = actual
    version = subprocess.run([str(selected/'clang'), '--version'], capture_output=True, text=True, timeout=10)
    if version.returncode or 'clang version 10.' not in version.stdout:
        raise ValueError('LLVM10 cannot start. On Ubuntu22.04 install libtinfo5 and build-essential. '+version.stderr[:1000])
    return {'llvm_bin': str(selected), 'compiler': version.stdout.splitlines()[0], 'toolchain_sha256': hashes}


def validate_input(data):
    if not isinstance(data, dict):
        raise ValueError('Expected a JSON object.')
    source, stdin, arguments = data.get('source'), data.get('stdin', ''), data.get('arguments', '')
    if not isinstance(source, str) or not source.strip() or len(source.encode()) > 49152 or '\x00' in source:
        raise ValueError('Enter a C program, up to 48 KiB, without NUL bytes.')
    if not isinstance(stdin, str) or len(stdin.encode()) > 8192 or '\x00' in stdin:
        raise ValueError('Standard input must be text up to 8 KiB without NUL bytes.')
    if not isinstance(arguments, str) or len(arguments) > 1024 or '\x00' in arguments:
        raise ValueError('Arguments must be text up to 1 KiB without NUL bytes.')
    try:
        args = shlex.split(arguments)
    except ValueError as error:
        raise ValueError('Arguments contain an unmatched quotation mark.') from error
    if len(args) > 16 or any(len(arg) > 256 for arg in args):
        raise ValueError('Use at most 16 arguments, each up to 256 characters.')
    iterations = data.get('iterations', 0)
    if type(iterations) is not int or not 0 <= iterations <= 1_000_000_000:
        raise ValueError('Iterations descriptor must be an integer from 0 to 1,000,000,000.')
    mode=data.get('policy_mode','legacy')
    if mode not in ('legacy','sl','rl','hybrid'):raise ValueError('Unknown learning mode.')
    return {'source': source, 'stdin': stdin, 'arguments': args, 'iterations': iterations,'policy_mode':mode}


def markdown_report(result):
    decision = result['decision']
    lines = ['# NeuroCompiler — Live Experiment Report', '',
             f"Created: {result['created_at']}", '',
             f"Experimental prediction: **{decision['choice']}**. Approved policy: **O3**.", '',
             ('The model decision was frozen before native execution. The experimental model failed research deployment gates.' if not decision.get('sequential') else 'The sequential model decision was frozen before native execution. Its objective is instruction count, not measured runtime; deployment qualification is unproven.'), '',
             f"Prediction time: {result['prediction_frozen_at']}",
             f"Compiler: {result['compiler']}",
             f"Static fields per candidate: {decision['feature_count']}",
             f"Source SHA256: {result['source_sha256']}",
             f"Portable model SHA256: {decision['model_sha256']}",
             f"Original model SHA256: {decision['model_source_sha256']}", '',
             '## Prediction scores', '', '| Pipeline | Predicted log speedup | Binary alias |', '| --- | ---: | --- |']
    if decision.get('sequential'):
        lines=lines[:-4]
        seq=decision['sequential']
        if seq.get('input_support'):
            support=seq['input_support']
            lines += ['## Model input ranges','',f"Status: {support['status']}; outside-range steps: {support['outside_steps']}/{support['evaluated_steps']}.",
                      'This is an advisory training-feature range check, not calibrated confidence. Within-range inputs can still be unfamiliar. The check does not change pass selection.','']
        if seq.get('selection'):
            lines += ['## Static instruction-count guard','',
                      f"Raw learned terminal count: {seq['policy_final_instructions']}. Best learned checkpoint: {seq['best_policy_instructions']}.",
                      f"Emitted artifact: {seq['selection']['applied']}; selected actions: {', '.join(seq['selected_actions']) or '(none / O3 fallback)' }.",
                      'The guard compares static counts against O3 and prefers O3 on ties. It is not learned and does not protect execution time.','']
        lines += ['## Sequential learning policy','',f"Mode: {seq['mode']}; objective: instruction_count. Training: {seq['training_rows']} transitions / {seq['training_programs']} synthetic programs.",f"IR instructions: {seq['initial_instructions']} initial -> {seq['final_instructions']} selected. O3: {decision['metrics']['O3']['instructions']}.",'', '| Action | Before IR count | After IR count | Q estimate |', '| --- | ---: | ---: | ---: |']
        for step in seq['trace']:lines.append(f"| {step['action']} | {step['before_instructions']} | {step['after_instructions']} | {step['q_score']:.5f} |")
    for choice, score in decision['scores'].items():
        lines.append(f"| {choice} | {score:.6f} | {decision['aliases'][choice]} |")
    lines += ['', 'Scores are model outputs, not confidence estimates or measured speedups. Sequential Q scores estimate the declared instruction-count reward, not runtime.', '']
    measurement = result.get('measurement')
    if measurement and measurement['status'] == 'completed':
        ranking = measurement.get('four_way')
        if ranking:
            lines += ['## O1 / O2 / O3 / NeuroCompiler', '',
                      f"Four-way status: **{ranking['status']}**.",
                      'Reliable demo preference: '+(' / '.join(ranking['winner_options']) or 'None')+'.','',
                      '| Entry | Actual pipeline | CPU time (ms) | Wall time (ms) |',
                      '| --- | --- | ---: | ---: |']
            for label,entry in ranking['clocks']['cpu']['options'].items():
                wall=ranking['clocks']['wall']['options'][label]
                lines.append(f"| {label} | {entry['artifact']} | {entry['runtime_ms']:.3f} | {wall['runtime_ms']:.3f} |")
            lines += ['', 'Times are pooled geometric means with equal observations per distinct executable. Identical entries share measurements. Inference/compilation overhead is excluded.',
                      '', ranking['scope'], '', f"Interval family size: {measurement['interval_family_size']}; bootstrap replicates: {measurement['bootstrap_replicates']}.", '']
            lines += ['### Executable self-controls', '', '| Executable | Both clocks qualified | CPU interval | Wall interval |', '| --- | --- | --- | --- |']
            for artifact,cell in measurement['self_controls'].items():
                intervals=[f"[{cell['clocks'][c]['interval'][0]:.4f}, {cell['clocks'][c]['interval'][1]:.4f}]" for c in ('cpu','wall')]
                lines.append(f"| {artifact} | {cell['qualified']} | {intervals[0]} | {intervals[1]} |")
            lines += ['', '### Direct head-to-head comparisons', '', '| Left / right executable | CPU left/right ratio [adjusted interval] | Wall left/right ratio [adjusted interval] | Qualified |', '| --- | --- | --- | --- |']
            for pair in measurement['head_to_head']:
                values=[]
                for c in ('cpu','wall'):
                    stat=pair['cell']['clocks'][c]
                    values.append(f"{stat['speedup']:.4f} [{stat['interval'][0]:.4f}, {stat['interval'][1]:.4f}]")
                lines.append(f"| {pair['left']} / {pair['right']} | {values[0]} | {values[1]} | {pair['cell']['qualified']} |")
            lines.append('')
        lines += ['## Live comparison', '',
                  f"O3 self-control passed: {measurement['self_control_passed']}", '',
                  'The table retains raw paired ratios. The O3 row is an identical-code null control, not a learned gain/loss. For the unchanged O3 executable the comparison reference is 1 by definition.', '',
                  '| Pipeline | CPU ratio [bootstrap interval] | Wall ratio [bootstrap interval] | Interpretation |',
                  '| --- | --- | --- | --- |']
        for choice, cell in measurement['cells'].items():
            values = []
            for clock in ('cpu','wall'):
                stat = cell['clocks'][clock]
                values.append(f"{stat['speedup']:.3f} [{stat['interval'][0]:.3f}, {stat['interval'][1]:.3f}]")
            lines.append(f"| {choice} | {values[0]} | {values[1]} | {cell['verdict']} |")
        lines += ['', measurement['timer'], '', measurement['quality_rule'], '', measurement['interval_scope'], '', measurement['scope']]
        if measurement.get('summary'):
            lines += ['', '## NeuroCompiler versus O3', '']
            for clock, summary in measurement['summary']['clocks'].items():
                lines += [f"### {clock.upper()}", '', summary['headline'], '',
                          f"Time change: {summary['time_change_percent']:+.2f}% (positive means more time).",
                          f"Both-clock measurement qualification: {summary['qualified']}.",
                          f"Demo preference over the other comparator: {summary.get('preferred_choice') or 'None (unchanged, inconclusive, or no clear advantage)' }.",
                          'Identical executables have zero code change; the null control ratio is not a learned speedup.' if summary['same_executable'] else 'Unqualified point estimates must not be treated as reliable gains or losses.', '']
                if summary['best_measured_choice']:
                    lines += [f"Fastest qualified point estimate: {summary['best_measured_choice']}.",
                              f"Gap to that point estimate: {summary['gap_to_best_percent']:.2f}% more time." if summary['gap_to_best_percent'] is not None else 'Gap unavailable.', '', summary['scope'], '']
                for reason in summary['failure_reasons']:
                    lines.append('- '+reason)
                lines.append('')
    elif measurement:
        lines += ['## Execution blocked', '', measurement['reason']]
    else:
        lines += ['Native execution: **not performed**. No performance claim follows from static inference.']
    if 'correctness' in result:
        lines += ['', f"Correctness checks passed: {result['correctness']['passed']}", '', result['correctness']['scope']]
    lines += ['', '## Research status', '',
              'The legacy mode uses the earlier LLVM10 model; sequential modes use separately trained instruction-count proxy models. No later LLVM19 study or reserved holdout is changed. Submitted code is not used to retrain. Generalizable runtime improvement over O3 is unproven.',
              '', 'Download the JSON report for all raw paired samples, features, attributions, hashes, and compiler pipelines.', '']
    return '\n'.join(lines)


class Application:
    def __init__(self, config, runs=None):
        self.evidence=audit_live()
        self.config = config
        self.runs = Path(runs or ROOT/'.presentation/runs')
        self.runs.mkdir(parents=True, exist_ok=True)
        self.token = secrets.token_urlsafe(32)
        self.lock = threading.RLock()
        self.jobs, self.active = {}, None

    def status(self, job_id):
        if not ID.fullmatch(job_id) or job_id not in self.jobs:
            raise KeyError('Unknown experiment; analyze the program again after a server restart.')
        item = self.jobs[job_id]
        root = self.runs/job_id
        state = json.loads((root/'state.json').read_text())
        process = item['process']
        if state['status'] != 'running' and process.poll() is None:
            try:
                process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                return {'id':job_id, 'status':'running', 'stage':'finalize', 'percent':99,
                        'message':'Finalizing experiment'}
        if process.poll() is not None:
            # A submitted program may accidentally leave descendants behind.
            # The worker has its own session; terminate only that job's group.
            if not item.get('group_cleaned'):
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                item['group_cleaned'] = True
            if state['status'] == 'running':
                state.update(status='failed', stage='error', message='Worker stopped unexpectedly. Check its local worker.log.', percent=100)
                save(root/'state.json', state)
            if self.active == job_id:
                self.active = None
            if not item['log'].closed:
                item['log'].close()
        payload = {'id': job_id, **state}
        if state['status'] == 'completed':
            payload['result'] = json.loads((root/'result.json').read_text())
        return payload

    def submit(self, data):
        if not isinstance(data, dict):
            raise ValueError('Expected a JSON object.')
        with self.lock:
            if self.active:
                self.status(self.active)
            if self.active:
                raise RuntimeError('Another experiment is running. Wait or cancel it first.')
            if len(self.jobs) >= 30:
                raise RuntimeError('This session has 30 experiments. Download your reports and restart the server.')
            operation = data.get('operation', 'analyze')
            if operation == 'analyze':
                request = {**validate_input(data), **self.config, 'operation': operation}
            elif operation == 'compare':
                if data.get('trusted_code') is not True:
                    raise ValueError('Confirm that this is your own trusted code before execution.')
                analysis_id = data.get('analysis_id')
                if not isinstance(analysis_id, str):
                    raise ValueError('Analyze your program first.')
                previous = self.status(analysis_id)
                if previous['status'] != 'completed' or previous['result']['kind'] != 'analysis':
                    raise ValueError('A completed static analysis is required.')
                request = {'operation': operation, 'analysis_root': str(self.runs/analysis_id)}
            else:
                raise ValueError('Unknown operation.')
            job_id = uuid.uuid4().hex[:16]
            root = self.runs/job_id
            root.mkdir()
            save(root/'request.json', request)
            save(root/'state.json', {'status':'running', 'stage':'queued', 'message':'Starting experiment', 'percent':2})
            log = (root/'worker.log').open('wb')
            environment = dict(os.environ, OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1', PYTHONUNBUFFERED='1')
            try:
                process = subprocess.Popen([sys.executable, '-m', 'src.presentation.worker', str(root)],
                                           cwd=ROOT, stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                                           env=environment, start_new_session=True)
            except Exception:
                log.close()
                raise
            self.jobs[job_id] = {'process':process, 'log':log}
            self.active = job_id
            return self.status(job_id)

    def cancel(self, job_id):
        with self.lock:
            state = self.status(job_id)
            if state['status'] == 'running':
                process = self.jobs[job_id]['process']
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait(timeout=5)
                save(self.runs/job_id/'state.json', {'status':'cancelled','stage':'cancelled','message':'Experiment cancelled','percent':100})
            return self.status(job_id)

    def close(self):
        with self.lock:
            if self.active:
                self.cancel(self.active)


class Handler(BaseHTTPRequestHandler):
    server_version = 'NeuroCompiler'

    @property
    def app(self):
        return self.server.app

    def valid_origin(self):
        port = self.server.server_port
        hosts = {f'127.0.0.1:{port}', f'localhost:{port}'}
        host = self.headers.get('Host', '')
        origin = self.headers.get('Origin')
        return host in hosts and (origin is None or origin == 'http://'+host)

    def send(self, status, body, kind='application/json', filename=None):
        if not isinstance(body, bytes):
            body = (json.dumps(body, allow_nan=False) if kind == 'application/json' else body).encode()
        self.send_response(status)
        self.send_header('Content-Type', kind+'; charset=utf-8' if kind.startswith(('text/','application/json','application/javascript')) else kind)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'")
        if filename:
            self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
        self.end_headers()
        if self.command != 'HEAD':
            self.wfile.write(body)

    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        if not self.valid_origin():
            return self.send(403, {'error':'Local same-origin requests only.'})
        path = unquote(urlsplit(self.path).path)
        if path == '/api/session':
            model = load_model()
            return self.send(200, {'token':self.app.token, 'compiler':self.app.config['compiler'],
                                  'model': {k:model[k] for k in ('name','policy','approved_policy','deployment_qualified',
                                           'training_rows','real_training_programs','synthetic_training_programs',
                                           'limitations','historical_cv','source_model_sha256')},
                                  'sequential_model':{k:load_agent()[1][k] for k in ('objective','training_rows','training_programs','limitations','algorithm','feature_names','horizon')},
                                  'examples':json.loads((ROOT/'presentation/examples.json').read_text())})
        if path == '/api/evidence':
            try:
                return self.send(200,audit_live())
            except (ValueError,KeyError,OSError) as error:
                return self.send(409,{'error':'Evidence files are inconsistent. Update all presentation artifacts together. '+str(error)})
        if path == '/api/generalization':
            report=json.loads((ROOT/'presentation/generalization_results.json').read_text())
            keys=('objective','runtime_evaluated','frozen','programs','independent_families',
                  'summary','derived_controls','all_output_checks_passed','scope')
            return self.send(200,{k:report[k] for k in keys})
        if path == '/api/health':
            return self.send(200, {'status':'ready','compiler':self.app.config['compiler'],'approved_policy':'O3','live':True,
                                   'comparison_entries':['O1','O2','O3','NeuroCompiler']})
        if path == '/api/jobs':
            with self.app.lock:
                return self.send(200, {'jobs':[self.app.status(i) for i in reversed(self.app.jobs)]})
        if path == '/api/scorecard':
            with self.app.lock:
                states = [self.app.status(i) for i in self.app.jobs]
                results = [s['result'] for s in states if s['status'] == 'completed']
            examples = json.loads((ROOT/'presentation/examples.json').read_text())
            return self.send(200, session_scorecard(results, examples))
        match = re.fullmatch(r'/api/jobs/([a-f0-9]{16})(?:/(report\.md|report\.json|selected\.bc|approved\.bc|ir/[A-Za-z0-9_]+))?', path)
        if match:
            try:
                with self.app.lock:
                    state = self.app.status(match[1])
                suffix = match[2]
                if not suffix:
                    return self.send(200, state)
                if state['status'] != 'completed':
                    return self.send(409, {'error':'Experiment has not completed.'})
                result = state['result']
                if suffix == 'report.json':
                    return self.send(200, result, filename=f'neurocompiler-{match[1]}.json')
                if suffix == 'report.md':
                    return self.send(200, markdown_report(result), 'text/markdown', f'neurocompiler-{match[1]}.md')
                if suffix in ('selected.bc', 'approved.bc'):
                    choice = result['decision']['choice'] if suffix == 'selected.bc' else 'O3'
                    analysis_id = result.get('analysis_id', match[1])
                    contents = (self.app.runs/analysis_id/choice/'program.bc').read_bytes()
                    if hashlib.sha256(contents).hexdigest() != result['artifacts'][choice]['bitcode_sha256']:
                        return self.send(409, {'error':'Bitcode changed after prediction. Analyze again.'})
                    return self.send(200, contents, 'application/octet-stream', f'neurocompiler-{choice}-{match[1]}.bc')
                choice = suffix.split('/')[1]
                if choice not in result['artifacts']:
                    raise KeyError('Unknown pipeline.')
                analysis_id = result.get('analysis_id', match[1])
                asset = self.app.runs/analysis_id/choice/'program.ll'
                return self.send(200, asset.read_bytes(), 'text/plain')
            except KeyError as error:
                return self.send(404, {'error':str(error)})
        asset = 'index.html' if path == '/' else path.lstrip('/')
        if asset == 'favicon.ico':
            asset = 'favicon.svg'
        directory = ROOT/'presentation'
        kind = ASSETS.get(asset)
        if path.startswith('/research/'):
            asset = path.removeprefix('/research/') or 'index.html'
            directory = ROOT/'dashboard'
            if asset in RESEARCH_ASSETS:
                kind = {'js':'application/javascript','css':'text/css','json':'application/json','md':'text/markdown'}.get(asset.split('.')[-1], 'text/html')
            else:
                kind = None
        target = directory/asset
        if kind and not target.is_symlink() and target.resolve().is_relative_to(directory.resolve()) and target.is_file():
            return self.send(200, target.read_bytes(), kind)
        self.send(404, {'error':'Not found.'})

    def do_POST(self):
        if not self.valid_origin() or not secrets.compare_digest(self.headers.get('X-NeuroCompiler-Token', ''), self.app.token):
            return self.send(403, {'error':'Local session token required. Reload the application.'})
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 262144 or self.headers.get('Transfer-Encoding'):
                raise ValueError('Request size must be between 1 and 262144 bytes.')
            if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
                raise ValueError('Use application/json.')
            self.connection.settimeout(5)
            data = json.loads(self.rfile.read(length))
            path = urlsplit(self.path).path
            if path == '/api/jobs':
                return self.send(202, self.app.submit(data))
            match = re.fullmatch(r'/api/jobs/([a-f0-9]{16})/cancel', path)
            if match:
                return self.send(200, self.app.cancel(match[1]))
            return self.send(404, {'error':'Not found.'})
        except (ValueError, UnicodeError) as error:
            self.send(400, {'error':str(error)})
        except KeyError as error:
            self.send(404, {'error':str(error)})
        except RuntimeError as error:
            self.send(409, {'error':str(error)})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8000)
    parser.add_argument('--llvm-bin', type=Path)
    parser.add_argument('--check', action='store_true', help='Verify compiler, headers, model and feature extraction; then exit.')
    args = parser.parse_args()
    if sys.platform != 'linux' or os.uname().machine != 'x86_64':
        parser.error('The live compiler supports x86_64 Linux. On Windows use WSL2 Ubuntu22.04.')
    try:
        config = toolchain(args.llvm_bin)
        load_model()
        load_agent()
        if args.check:
            audit_live()
            with __import__('tempfile').TemporaryDirectory() as scratch:
                root = Path(scratch)
                request = {**config, 'source':'#include <stdio.h>\nint main(void){puts("ready");return 0;}\n',
                           'arguments':[], 'stdin':'', 'iterations':0, 'operation':'analyze'}
                # Normal worker process, same path as a real user job. No program execution.
                save(root/'request.json', request)
                process = subprocess.run([sys.executable,'-m','src.presentation.worker',str(root)], cwd=ROOT,
                                         start_new_session=True, env=dict(os.environ,OPENBLAS_NUM_THREADS='1'), timeout=120)
                state = json.loads((root/'state.json').read_text())
                if process.returncode or state['status'] != 'completed':
                    raise ValueError(state['message'])
            print('Ready: LLVM10, C headers, legacy SL (156 fields), SL/RL/hybrid (30 fields), O1/O2/O3 baselines and static count guard. No input executed.')
            return
        app = Application(config)
        server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
        server.app = app
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        parser.error(str(error))
    print(f'NeuroCompiler live application listening on 127.0.0.1:{server.server_port}', flush=True)
    print('Trusted local code only. Programs execute on this computer; this is not a security sandbox.', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        app.close()
        server.server_close()


if __name__ == '__main__':
    main()
