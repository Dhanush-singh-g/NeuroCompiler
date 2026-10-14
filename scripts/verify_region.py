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
from src.benchmarks.region import *
from src.supervised.region import NativeSelector,program_cv
from src.supervised.frozen import predictions_equal


def check_actual_order(rows, statistics, clock):
    """Independently reconstruct actual-side strata, without clock_effect."""
    groups={True:[],False:[]};differences=[]
    for row in sorted(rows,key=lambda r:r['block']):
        local={True:[],False:[]}
        for sample in row['samples']:
            value=math.log(sample['left'][clock+'_seconds']/sample['right'][clock+'_seconds'])
            side=sample['left_first'];local[side].append(value);groups[side].append(value)
        differences.append(abs(float(np.median(local[True])-np.median(local[False]))))
    pooled=abs(float(np.median(groups[True])-np.median(groups[False])))
    passed=pooled<=math.log1p(PROTOCOL['control_tolerance']) and all(v<=math.log1p(PROTOCOL['control_tolerance']) for v in differences)
    if statistics['order_pass']!=passed or statistics['order_log_difference']!=pooled or statistics['block_order_log_differences']!=differences:
        raise ValueError('Actual-side order reconstruction failed')


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
    order_groups=0
    for study in raw.values():
        for case,diagnostic in study['diagnostics'].items():
            groups=[('O3','qualification',diagnostic['baseline_controls'])]
            for choice,measurement in diagnostic['measurements'].items():
                groups += [(choice,'candidate_control',{clock:measurement[clock]['control'] for clock in ['cpu','wall']}),
                           (choice,'effect',{clock:measurement[clock]['effect'] for clock in ['cpu','wall']})]
            for choice,role,statistics in groups:
                rows=[row for row in study['records'] if row['case']==case and row['choice']==choice and row['role']==role]
                for clock in ['cpu','wall']:check_actual_order(rows,statistics[clock],clock);order_groups+=1
    ablation=json.loads((ROOT/'results/region_feature_ablation.json').read_text())
    if ablation['training_sha256']!=selected['training_sha256'] or ablation['declaration_sha256']!=sha(ROOT/'results/region_declaration.json'):
        raise ValueError('Ablation binding changed')
    if ablation['studies']['timed']['feature_count']!=95 or ablation['studies']['whole_entry']['feature_count']!=160:
        raise ValueError('Ablation feature coverage changed')
    for view in ablation['studies'].values():
        if {tuple(e['parameters']) for e in view['experiments']}!={tuple(p) for p in declaration['parameters']} or view['selection_changed']:
            raise ValueError('Changed ablation scope')
    for experiment in ablation['studies']['timed']['experiments']:
        expected=next(v for v in replayed.values() if v['parameters']==experiment['parameters'])
        actual,wanted=copy.deepcopy(experiment),copy.deepcopy(expected)
        for collection in ['records','unscorable']:
            if len(actual.get(collection,[]))!=len(wanted.get(collection,[])):raise ValueError('Ablation coverage changed')
            for x,y in zip(actual.get(collection,[]),wanted.get(collection,[])):
                if not predictions_equal(x['scores'],y['scores']):raise ValueError('Ablation predictions changed')
                x['scores']=y['scores']={}
        if actual!=wanted:raise ValueError('Timed-feature ablation differs from primary CV')
    sources=0;reused=0;native=0
    for r in raw.values():
        seen=set()
        for case,m in r['manifests'].items():
            for c in MENU:run_cell(m,'reference_O0',c,0,'audit',pairs=1,repetitions=1);native+=1
            program=m['program']
            if program in seen:continue
            seen.add(program);pin=m['source_pin'];subdir={'lua':'src/','expat':'expat/lib/','lz4':'lib/','blake2':'ref/','monocypher':'src/','yyjson':'src/'}.get(program,'')
            with tarfile.open(pin['archive']) as archive:
                for source,digest in m['sources'].items():
                    p=Path(source)
                    if sha(p)!=digest:raise ValueError('Source manifest changed')
                    if p.name=='driver.c':expected=DRIVERS[program].encode()
                    elif program=='expat' and p.name=='expat_config.h':expected=EXPAT_CONFIG.encode()
                    else:expected=archive.extractfile(pin['root']+'/'+subdir+p.name).read()
                    if p.read_bytes()!=expected:raise ValueError('Source provenance changed '+source)
                    sources+=1
            from src.benchmarks.broad import BASE as PRIOR_BASE
            PRIOR_PROGRAMS=PROGRAMS[:-1]
            if program in PRIOR_PROGRAMS:
                prior=json.loads((PRIOR_BASE/'programs'/program/'manifest.json').read_text())
                if m['initial_sha256']!=prior['initial_sha256']:raise ValueError('Reused bitcode changed')
                reused+=1
    rejected={}
    mutations={
      'repetitions':lambda r:r['records'][0]['samples'][0]['left'].update({'repetitions':99999}),
      'process_order':lambda r:r['records'][0]['samples'][0].update({'left_first':not r['records'][0]['samples'][0]['left_first']}),
      'missing_pair':lambda r:r['records'][0]['samples'].pop(),
      'reported_gain':lambda r:next(iter(r['diagnostics'].values()))['baseline_controls']['cpu'].update({'speedup':2.}),
      'reported_order':lambda r:next(iter(r['diagnostics'].values()))['baseline_controls']['cpu'].update({'block_order_log_differences':[99.,99.,99.]}),
      'input_features':lambda r:next(iter(next(iter(r['manifests'].values()))['features'].values())).__setitem__(-1,999.),
      'variant_artifact':lambda r:r['manifests'][list(r['manifests'])[1]]['artifacts']['O3'].update({'so_sha256':'bad'}),
      'correctness_output':lambda r:next(iter(next(iter(r['manifests'].values()))['correctness'].values()))['samples'][0]['right'].update({'checksum':'bad'}),
    }
    for name,mutate in mutations.items():
        bad=copy.deepcopy(train);mutate(bad)
        try:verify(bad)
        except ValueError:rejected[name]=True
        else:raise ValueError('Primary corruption accepted '+name)
    preserved=0
    with zipfile.ZipFile(ROOT/'results/broad_iteration.zip') as archive:
        if archive.testzip():raise ValueError('Prior archive CRC failure')
        if sha(ROOT/'results/broad_iteration.zip')!=declaration['prior_artifact_sha256']:raise ValueError('Prior archive changed')
        for name in archive.namelist():
            if not name.startswith(('results/','models/','data/')):continue
            path=ROOT/name
            if not path.is_file() or sha(path)!=hashlib.sha256(archive.read(name)).hexdigest():raise ValueError('Prior evidence changed '+name)
            preserved+=1
    exported=ROOT/'results/region_export';e=json.loads((exported/'manifest.json').read_text())
    m=raw['development']['manifests']['yyjson_flat']
    for key,value in {'model_sha256':sha(model_path),'training_sha256':selected['training_sha256'],
                      'selection_sha256':sha(selection_path),'static_only':True,'cv_certified':selected['cv_certified']}.items():
        if e[key]!=value:raise ValueError('Export binding changed')
    for name,source in {'program.bc':m['artifacts']['O3']['bc'],'candidate.so':m['artifacts']['O3']['so'],
                        'isolated_library_worker.out':m['worker'],'input.dat':m['input']}.items():
        if sha(exported/name)!=sha(source) or sha(exported/name)!=e['files_sha256'][name]:raise ValueError('Export changed')
    if e['decision']['choice']!='O3' or e['expected']!=m['expected'] or e['experimental']:raise ValueError('Export decision changed')
    result=subprocess.run(['taskset','-c','2',str(exported/'isolated_library_worker.out'),str(exported/'candidate.so'),
                           str(exported/'input.dat'),'1'],capture_output=True,check=True,timeout=60)
    row=json.loads(result.stdout)
    if row['mode']!='one_implementation' or row['repetitions']!=1:raise ValueError('Export worker mismatch')
    if {k:row['sample'][k] for k in m['expected']}!=m['expected']:raise ValueError('Export oracle mismatch')
    export_status='CV-qualified experimental selector available' if chosen else 'unqualified experimental export rejected'
    if not chosen:
        denied=ROOT/'results/region_experimental_rejected'
        if denied.exists():raise ValueError('Rejection path exists')
        result=subprocess.run([sys.executable,str(ROOT/'scripts/optimize_region.py'),'--case','yyjson_flat','--experimental','--output',str(denied)],capture_output=True,timeout=60)
        if result.returncode!=1 or b'No CV-qualified experimental model' not in result.stderr or denied.exists():raise ValueError('Unqualified export accepted')
    report={'native_O0_candidate_comparisons':native,'source_files_checked':sources,'reused_initial_bitcode_verified':reused,
            'whole_program_CV_variants_replayed':len(replayed),'primary_tamper_rejected':rejected,
            'actual_side_clock_groups_independently_checked':order_groups,'ablation_parameters_and_primary_CV_checked':True,
            'prior_generated_files_unchanged':preserved,'default_export_independent_oracle':True,
            'experimental_export_status':export_status,'reserved_test_executions':0,
            'source_sha256':{s:sha(ROOT/f'results/{NAME}_{s}.json') for s in raw}}
    save(output,report);print(json.dumps(report,indent=2))


if __name__=='__main__':main()

