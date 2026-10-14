"""A bounded, declared training-only method comparison, with no fit labels."""
import argparse
import datetime
import hashlib
import json
import shutil
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.benchmarks.compact import save,sha
from src.benchmarks.region import ROOT,NAME,PROTOCOL,check_declaration,oracle,BASIS,PRIME,MASK
from src.benchmarks.persistent import BASE,compile_worker,run,validate,clock_effect

CASES=['zlib_random','expat_nested','lz4_random','bzip2_random','blake2_random','cjson_flat','tinyexpr_arithmetic','sha256_random']
METHODS=['fresh','batch','micro'];SEED=20261104
PILOT_PROTOCOL={key:PROTOCOL[key] for key in ['blocks','pairs','cpu','control_tolerance','gain_floor','bootstrap_replicates','seed']}
PILOT_PROTOCOL.update(scope='eight opened training inputs, three null-control methods; no model fitting',
    controls='same exact O3 path in separate worker processes; no co-resident DSO',
    ordering='fixed Latin method rotations; persistent micro alternates after each API invocation; fresh/batch alternate batches',
    order_qualification='actual pooled starting side AND each block <= log(1.03), independently on CPU and wall',
    repetitions='prior calibration rounded up to even, held equal across all methods; all raw pairs/traces retained')
DECLARATION=ROOT/'results/persistent_declaration.json'
OUTPUT=ROOT/'results/persistent_pilot.json'


def source_manifest():
    names=['src/benchmarks/persistent.py','src/benchmarks/persistent_library_worker.c',
           'src/benchmarks/invocation_worker.c','src/benchmarks/isolated_library_worker.c',
           'src/benchmarks/region.py','src/benchmarks/compact.py','src/benchmarks/polybench.py',
           'scripts/measure_persistent.py']
    return {name:sha(ROOT/name) for name in names}


def plan():
    # Latin rotations distribute the method order across cases and blocks.
    order=[];rng=np.random.default_rng(SEED)
    for block in range(PROTOCOL['blocks']):
        indices=list(rng.permutation(len(CASES)))
        for i in indices:
            for j in range(len(METHODS)):
                order.append({'case':CASES[i],'method':METHODS[(i+block+j)%3],'block':block})
    return order


def check_declaration_local():
    declared=json.loads(DECLARATION.read_text())
    if declared['source_sha256']!=source_manifest() or declared['schedule']!=plan() or declared['protocol']!=PILOT_PROTOCOL:raise ValueError('Frozen pilot code/schedule changed')
    for name,digest in declared['source_sha256'].items():
        if sha(BASE/'declared_sources'/name)!=digest:raise ValueError('Frozen source copy changed')
    if sha(declared['worker'])!=declared['worker_sha256']:raise ValueError('Worker changed')
    if sha(ROOT/f'results/{NAME}_train.json')!=declared['prior_training_sha256']:raise ValueError('Prior raw study changed')
    for m in declared['manifests'].values():
        for path,digest in [(m['input'],m['input_sha256']),(m['artifacts']['O3']['so'],m['artifacts']['O3']['so_sha256']),(m['worker'],m['worker_sha256'])]:
            if sha(path)!=digest:raise ValueError('Pinned pilot input/artifact changed')
    return declared


def summarize(raw):
    stats={};coverage={}
    for method in METHODS:
        stats[method]={};coverage[method]={clock:0 for clock in ['cpu','wall']}
        for case in CASES:
            rows=[r for r in raw['records'] if r['case']==case and r['method']==method]
            if len(rows)!=PROTOCOL['blocks']:continue
            values={clock:clock_effect(rows,clock) for clock in ['cpu','wall']};stats[method][case]=values
            for clock,s in values.items():coverage[method][clock]+=int(s['control_pass'])
    # Pilot chooses methods only, not configurations or learners. Larger count,
    # then micro > batch > fresh on ties. Independent confirmation is still
    # needed before treating any method as ready for a new performance study.
    eligible=[m for m in METHODS if min(coverage[m].values())>=6]
    selected=max(eligible,key=lambda m:(min(coverage[m].values()),METHODS.index(m))) if eligible else None
    return {'statistics':stats,'coverage':coverage,'selected_method':selected,
            'fit_targets':0,'scope':'training-only method qualification; no O3 gain/model claim; no samples filtered'}


def verify(raw):
    declared=check_declaration_local()
    if raw['declaration_sha256']!=sha(DECLARATION) or raw['manifests']!=declared['manifests']:raise ValueError('Pilot binding changed')
    if len(raw['records'])>len(declared['schedule']):raise ValueError('Extra cells')
    if raw['complete'] and len(raw['records'])!=len(declared['schedule']):raise ValueError('Incomplete schedule')
    for row,item in zip(raw['records'],declared['schedule']):
        if any(row[k]!=v for k,v in item.items()):raise ValueError('Schedule changed')
        m=raw['manifests'][row['case']]
        validate(row,m,PROTOCOL['pairs'],m['repetitions'],row['first'],row['method'])
        if row['left']!='O3' or row['right']!='O3' or row['role']!='qualification':raise ValueError('Pilot comparison changed')
        if row['method']=='fresh':
            seed=PROTOCOL['seed']+int(hashlib.sha256(f'{m["id"]}:O3:O3:qualification:{row["block"]}'.encode()).hexdigest()[:8],16)
        else:seed=SEED+int(hashlib.sha256(f'{m["id"]}:{row["method"]}:{row["block"]}:O3:O3'.encode()).hexdigest()[:8],16)
        if row['first']!=bool(np.random.default_rng(seed).integers(2)):raise ValueError('Start side changed')
    if raw['complete'] and raw.get('summary')!=summarize(raw):raise ValueError('Pilot statistics changed')
    return declared


def declare():
    if DECLARATION.exists() or OUTPUT.exists():raise ValueError('Existing pilot declaration/results')
    check_declaration();source=ROOT/f'results/{NAME}_train.json';previous=json.loads(source.read_text());manifests={}
    for case in CASES:
        m=dict(previous['manifests'][case]);m['repetitions']+=m['repetitions']%2
        for key,digest in [(m['input'],m['input_sha256']),(m['artifacts']['O3']['so'],m['artifacts']['O3']['so_sha256']),(m['worker'],m['worker_sha256'])]:
            if sha(key)!=digest:raise ValueError('Pinned native input/artifact changed')
        expected={'checksum':f'{(BASIS^oracle(case))*PRIME&MASK:016x}','values':1}
        if expected!=m['expected']:raise ValueError('Independent oracle differs')
        manifests[case]=m
    worker=compile_worker();hashes=source_manifest()
    for name in hashes:
        dest=BASE/'declared_sources'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/name,dest)
    save(DECLARATION,{'declared_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'protocol':PILOT_PROTOCOL,
         'pilot_seed':SEED,'schedule':plan(),'manifests':manifests,'prior_training_sha256':sha(source),
         'source_sha256':hashes,'worker':str(worker),'worker_sha256':sha(worker),
         'changes':'same O3 file in both fresh or isolated persistent processes; even prior-calibrated repetitions; no new calibration',
         'selection':'at least 6/8 CPU and 6/8 wall controls; maximum minimum coverage; micro,batch,fresh tie preference',
         'confirmation_budget':'one selected method, same eight training inputs, one new independent three-block control study; no substitutions/retries',
         'secondary_probe_budget':'if confirmation passes >=6/8 both clocks, one preselected blake2_random/no-vector effect+two self-controls; training headroom only, never model labels',
         'data_policy':'all raw request traces retained; no filtering/refitting; no development/test programs executed'})
    print('Declared 72 cells, three methods, eight training cases; no label fitting')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--declare',action='store_true');parser.add_argument('--resume',action='store_true');args=parser.parse_args()
    if args.declare:declare();return
    declared=check_declaration_local()
    if OUTPUT.exists():
        if not args.resume:raise ValueError('Existing pilot; use --resume')
        raw=json.loads(OUTPUT.read_text());verify(raw)
        if raw['complete']:print('Verified complete pilot; no new timings');return
    else:
        raw={'declaration_sha256':sha(DECLARATION),'manifests':declared['manifests'],'records':[],'complete':False};save(OUTPUT,raw)
    for item in declared['schedule'][len(raw['records']):]:
        m=raw['manifests'][item['case']]
        row=run(m,item['method'],declared['worker'],item['block'],SEED,repetitions=m['repetitions'])
        raw['records'].append(row);save(OUTPUT,raw);print('Pilot',item['block']+1,item['case'],item['method'],flush=True)
    raw['summary']=summarize(raw);raw['complete']=True;verify(raw);save(OUTPUT,raw)
    print(json.dumps({k:raw['summary'][k] for k in ['coverage','selected_method']},indent=2))


if __name__=='__main__':main()
