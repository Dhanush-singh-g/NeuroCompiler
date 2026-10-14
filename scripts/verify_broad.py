"""Independent correctness/provenance, CV replay and changed-evidence checks."""
import copy
import hashlib
import json
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

import joblib
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.benchmarks.broad import *
from src.supervised.broad import NativeSelector,program_cv
from src.supervised.frozen import predictions_equal

def check_secondary(report, declaration, manifest):
    if not report['complete'] or any(report[k] != v for k, v in declaration.items()):
        raise ValueError('Secondary declaration mismatch')
    protocol = declaration['protocol']
    expected = manifest['expected']
    choice=declaration['candidate']
    roles = [('qualification', 'O3', 'O3'), ('candidate_control', choice, choice), ('effect', 'O3', choice)]
    records = report['records']
    if len(records) != protocol['blocks'] * len(roles):
        raise ValueError('Incomplete secondary coverage')
    rng = np.random.default_rng(protocol['seed'])
    for record, (block, role, left, right) in zip(records, [(b, *r) for b in range(protocol['blocks']) for r in roles]):
        first = bool(rng.integers(2))
        if any(record[k] != v for k, v in {'block': block, 'role': role, 'left': left, 'right': right, 'first': first}.items()):
            raise ValueError('Secondary cell/order mismatch')
        if len(record['samples']) != protocol['pairs']:
            raise ValueError('Incomplete secondary pair count')
        for p, row in enumerate(record['samples']):
            if row['pair'] != p or row['left_first'] != ((p % 2 == 0) == first):
                raise ValueError('Secondary pair order mismatch')
            for side in ['left', 'right']:
                sample = row[side]
                if {k: sample[k] for k in expected} != expected:
                    raise ValueError('Secondary oracle mismatch')
                if any(not math.isfinite(sample[k]) or sample[k] <= 0 for k in ['cpu_seconds', 'wall_seconds']):
                    raise ValueError('Invalid secondary clocks')
    statistics = {}
    for clock in ['cpu', 'wall']:
        detail = {}
        for role, _, _ in roles:
            rows = [r for r in records if r['role'] == role]
            detail[role] = effect([{'left_seconds': [s['left'][clock + '_seconds'] for s in r['samples']],
                                   'right_seconds': [s['right'][clock + '_seconds'] for s in r['samples']]} for r in rows], protocol)
        measured = detail['effect']
        valid = detail['qualification']['control_pass'] and detail['candidate_control']['control_pass']
        detail['qualified'] = bool(valid)
        detail['confirmed_gain'] = bool(valid and measured['interval'][0] > 1 + protocol['gain_floor']
                                        and all(v > 1 + protocol['gain_floor'] for v in measured['blocks']))
        statistics[clock] = detail
    if statistics != report['statistics']:
        raise ValueError('Secondary derived statistics changed')
    return len(records) * protocol['pairs'] * 2


def main():
    output=ROOT/f'results/{NAME}_verification.json'
    if output.exists():raise ValueError('Existing verification')
    raw={s:json.loads((ROOT/f'results/{NAME}_{s}.json').read_text()) for s in ['train','development']}
    for r in raw.values():
        if not r['complete']:raise ValueError('Incomplete study')
        verify(r)
    train=raw['train'];labels=train['labels'];declaration=check_declaration()
    selection_path=ROOT/f'results/{NAME}_selection.json';selected=json.loads(selection_path.read_text())
    model_path=ROOT/f'models/sl_{NAME}_bundle.joblib'
    if selected['training_sha256']!=sha(ROOT/f'results/{NAME}_train.json') or selected['model_sha256']!=sha(model_path):
        raise ValueError('Model binding changed')
    replayed={}
    for name,experiment in selected['experiments'].items():
        parameters=experiment['parameters']
        if parameters not in declaration['parameters']:raise ValueError('Undeclared model')
        actual={'parameters':parameters,**program_cv(labels,train['manifests'],*parameters)}
        a,b=copy.deepcopy(actual),copy.deepcopy(experiment)
        for collection in ['records','unscorable']:
            if len(a.get(collection,[]))!=len(b.get(collection,[])):raise ValueError('CV coverage mismatch')
            for x,y in zip(a.get(collection,[]),b.get(collection,[])):
                if not predictions_equal(x['scores'],y['scores']):raise ValueError('CV prediction mismatch '+name)
                x['scores']=y['scores']={}
        if a!=b:raise ValueError('CV replay mismatch '+name)
        replayed[name]=actual
    if len(replayed)!=16 or {tuple(e['parameters']) for e in replayed.values()}!={tuple(p) for p in declaration['parameters']}:
        raise ValueError('Incomplete model menu')
    accepted=[k for k,v in replayed.items() if v['eligible'] and v['score']['utility']>0
              and v['score']['worst_original_program']>=.97 and v['score']['confirmed_workloads']>=1]
    chosen=max(accepted,key=lambda k:replayed[k]['score']['utility']) if accepted else None
    if selected['experimental']!=chosen or selected['cv_certified']!=bool(chosen):raise ValueError('Invalid selection')
    bundle=joblib.load(model_path)
    if bundle['default']!='O3' or bundle['training_sha256']!=selected['training_sha256']:raise ValueError('Invalid bundle')
    if chosen:
        fitted=NativeSelector(*replayed[chosen]['parameters']).fit(labels)
        for r in raw.values():
            for m in r['manifests'].values():
                if not predictions_equal(fitted.choose(m),bundle['experimental'].choose(m)):raise ValueError('Serialized model mismatch')
    elif bundle['experimental'] is not None:raise ValueError('Unqualified selector stored')
    sources=0;reused=0;native=0
    for r in raw.values():
        seen=set()
        for case,m in r['manifests'].items():
            for c in MENU:run_cell(m,'reference_O0',c,0,'audit',pairs=1,repetitions=1);native+=1
            program=m['program']
            if program in seen:continue
            seen.add(program);pin=m['source_pin'];subdir={'lua':'src/','expat':'expat/lib/','lz4':'lib/','blake2':'ref/'}.get(program,'')
            with tarfile.open(pin['archive']) as archive:
                for source,digest in m['sources'].items():
                    p=Path(source)
                    if sha(p)!=digest:raise ValueError('Source manifest changed')
                    if p.name=='driver.c':expected=DRIVERS[program].encode()
                    elif program=='expat' and p.name=='expat_config.h':expected=EXPAT_CONFIG.encode()
                    else:expected=archive.extractfile(pin['root']+'/'+subdir+p.name).read()
                    if p.read_bytes()!=expected:raise ValueError('Source provenance changed '+source)
                    sources+=1
            from src.benchmarks.invocation import BASE as PRIOR_BASE,PROGRAMS as PRIOR_PROGRAMS
            if program in PRIOR_PROGRAMS:
                prior=json.loads((PRIOR_BASE/'programs'/program/'manifest.json').read_text())
                if m['initial_sha256']!=prior['initial_sha256']:raise ValueError('Reused bitcode changed')
                reused+=1
    rejected={}
    mutations={
      'invocation_counts':lambda r:r['records'][0]['samples'][0].update({'left_first_invocations':99999}),
      'reported_gain':lambda r:next(iter(r['diagnostics'].values()))['baseline_controls']['cpu'].update({'speedup':2.}),
      'input_features':lambda r:next(iter(next(iter(r['manifests'].values()))['features'].values())).__setitem__(-1,999.),
      'variant_artifact':lambda r:r['manifests'][list(r['manifests'])[1]]['artifacts']['O3'].update({'so_sha256':'bad'}),
      'correctness_output':lambda r:next(iter(next(iter(r['manifests'].values()))['correctness'].values()))['samples'][0]['right'].update({'checksum':'bad'}),
    }
    for name,mutate in mutations.items():
        bad=copy.deepcopy(train);mutate(bad)
        try:verify(bad)
        except ValueError:rejected[name]=True
        else:raise ValueError('Primary corruption accepted '+name)
    secondary_path=ROOT/'results/broad_isolated_confirmation.json';secondary=json.loads(secondary_path.read_text())
    if secondary['training_sha256']!=selected['training_sha256']:raise ValueError('Secondary training binding changed')
    secondary_count=0;secondary_rejected={}
    eligible=[]
    for case,d in train['diagnostics'].items():
        for c,v in d['measurements'].items():
            if v['cpu']['effect']['confirmed_gain']:eligible.append((-v['cpu']['effect']['interval'][0],case,c))
    if secondary.get('status')=='not_run':
        if eligible or not secondary['complete'] or secondary['records']:raise ValueError('Invalid secondary omission')
    else:
        d=json.loads((ROOT/'results/broad_isolated_declaration.json').read_text());_,case,choice=min(eligible)
        if (d['case'],d['candidate'])!=(case,choice):raise ValueError('Changed secondary selection')
        m=train['manifests'][case]
        for key,value in {'training_sha256':sha(ROOT/f'results/{NAME}_train.json'),
                          'candidate_artifact_sha256':m['artifacts'][choice]['so_sha256'],
                          'baseline_artifact_sha256':m['artifacts']['O3']['so_sha256'],'input_sha256':m['input_sha256']}.items():
            if d[key]!=value:raise ValueError('Secondary binding changed')
        for name,digest in d['source_sha256'].items():
            if sha(ROOT/name)!=digest:raise ValueError('Secondary source changed')
        if sha(BASE/'isolated_library_worker.out')!=d['worker_sha256']:raise ValueError('Secondary worker changed')
        secondary_count=check_secondary(secondary,d,m)
        for name,mutate in {
          'missing_pair':lambda r:r['records'][0]['samples'].pop(),
          'pair_order':lambda r:r['records'][0]['samples'][0].update({'left_first':not r['records'][0]['samples'][0]['left_first']}),
          'oracle':lambda r:r['records'][0]['samples'][0]['left'].update({'checksum':'bad'}),
          'gain':lambda r:r['statistics']['cpu'].update({'confirmed_gain':not r['statistics']['cpu']['confirmed_gain']}),
        }.items():
            bad=copy.deepcopy(secondary);mutate(bad)
            try:check_secondary(bad,d,m)
            except ValueError:secondary_rejected[name]=True
            else:raise ValueError('Secondary corruption accepted '+name)
    preserved=0
    with zipfile.ZipFile(ROOT/'results/invocation_iteration.zip') as archive:
        if archive.testzip():raise ValueError('Prior archive CRC failure')
        if sha(ROOT/'results/invocation_iteration.zip')!=declaration['prior_artifact_sha256']:raise ValueError('Prior archive changed')
        for name in archive.namelist():
            if not name.startswith(('results/','models/','data/')):continue
            path=ROOT/name
            if not path.is_file() or sha(path)!=hashlib.sha256(archive.read(name)).hexdigest():raise ValueError('Prior evidence changed '+name)
            preserved+=1
    exported=ROOT/'results/broad_export';e=json.loads((exported/'manifest.json').read_text())
    m=raw['development']['manifests']['parson_flat']
    for key,value in {'model_sha256':sha(model_path),'training_sha256':selected['training_sha256'],
                      'selection_sha256':sha(selection_path),'static_only':True,'cv_certified':selected['cv_certified']}.items():
        if e[key]!=value:raise ValueError('Export binding changed')
    for name,source in {'program.bc':m['artifacts']['O3']['bc'],'candidate.so':m['artifacts']['O3']['so'],
                        'invocation_worker.out':m['worker'],'input.dat':m['input']}.items():
        if sha(exported/name)!=sha(source) or sha(exported/name)!=e['files_sha256'][name]:raise ValueError('Export changed')
    if e['decision']['choice']!='O3' or e['expected']!=m['expected'] or e['experimental']:raise ValueError('Export decision changed')
    result=subprocess.run(['taskset','-c','2',str(exported/'invocation_worker.out'),str(exported/'candidate.so'),
                           str(exported/'candidate.so'),'1','1','0',str(exported/'input.dat')],capture_output=True,check=True,timeout=60)
    row=json.loads(result.stdout)
    for sample in row['samples']:
        for side in ['left','right']:
            if {k:sample[side][k] for k in m['expected']}!=m['expected']:raise ValueError('Export oracle mismatch')
    export_status='CV-qualified experimental selector available' if chosen else 'unqualified experimental export rejected'
    if not chosen:
        denied=ROOT/'results/broad_experimental_rejected'
        if denied.exists():raise ValueError('Rejection path exists')
        result=subprocess.run([sys.executable,str(ROOT/'scripts/optimize_broad.py'),'--case','parson_flat','--experimental','--output',str(denied)],capture_output=True,timeout=60)
        if result.returncode!=1 or b'No CV-qualified experimental model' not in result.stderr or denied.exists():raise ValueError('Unqualified export accepted')
    report={'native_O0_candidate_comparisons':native,'source_files_checked':sources,'reused_initial_bitcode_verified':reused,
            'whole_program_CV_variants_replayed':len(replayed),'primary_tamper_rejected':rejected,
            'secondary_worker_outputs_checked':secondary_count,'secondary_tamper_rejected':secondary_rejected,
            'prior_generated_files_unchanged':preserved,'default_export_independent_oracle':True,
            'experimental_export_status':export_status,'reserved_test_executions':0,
            'source_sha256':{s:sha(ROOT/f'results/{NAME}_{s}.json') for s in raw},'secondary_sha256':sha(secondary_path)}
    save(output,report);print(json.dumps(report,indent=2))


if __name__=='__main__':main()

