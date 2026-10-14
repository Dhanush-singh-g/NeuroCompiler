"""One declared longer-duration study following a rejected noisy pilot.

Three fixed first inputs, not selected using any candidate effects. No retries
after a completed attempt. Reuses the exact pilot source BC and executables.
"""
import argparse
import copy
import hashlib
import json
import random
import subprocess
from pathlib import Path

import numpy as np

from scripts.collect_real import verify as verify_pilot
from src.benchmarks.compact import MENU,PROTOCOL,effect,measure_cell,run,save,sha,summarize
from src.benchmarks.real import REAL_PROTOCOL,verify_real
from src.features.transform import FEATURE_NAMES,extract_manifest

CASES=['zlib_pattern','expat_flat','lua_numeric']
RUNTIME={**PROTOCOL,'pairs':20,'duration_seconds':[.15,1.],'seed':20261015}
LONG_PROTOCOL={**REAL_PROTOCOL,'cases':CASES,'runtime':RUNTIME,'seed':20261015,
    'scope':'training only; three upstream programs, one fixed first input each',
    'calibration':'O3 only; start at pilot iterations; at most 3 corrections targeting 250 ms; cap 1000000',
    'reason':'Pilot unchanged controls failed. New duration and pair budget declared before any candidate effects; not a retry of the old protocol.'}


def verify(r,complete=True):
    if r['protocol']!=LONG_PROTOCOL or r['feature_names']!=FEATURE_NAMES:raise ValueError('Long protocol changed')
    pilot_path=Path('results/real_train.json')
    if r['pilot_sha256']!=sha(pilot_path):raise ValueError('Pilot changed')
    pilot=json.loads(pilot_path.read_text());verify_pilot(pilot)
    if complete and (not r['complete'] or set(r['manifests'])!=set(CASES)):raise ValueError('Incomplete long study')
    if set(r['profiles'])!=set(r['manifests']) or set(r['static_cases'])!=set(r['manifests']):raise ValueError('Metadata coverage')
    for case,m in r['manifests'].items():
        verify_real(m,RUNTIME['duration_seconds'])
        old=pilot['manifests'][case]
        mutable={'arguments','features','calibration','eligible','expected_output'}
        if {k:v for k,v in m.items() if k not in mutable}!={k:v for k,v in old.items() if k not in mutable}:raise ValueError('Pilot artifacts changed')
        if m['calibration'][0]['iterations']!=int(old['arguments'][-1]):raise ValueError('Calibration initial workload changed')
        if r['profiles'][case]!={'eligible':m['eligible'],'seconds':m['calibration'][-1]['seconds']}:raise ValueError('Profile changed')
        s=r['static_cases'][case]
        if s['program']!=m['program'] or s['aliases']!=m['aliases'] or s['static_only'] is not True or s['bc_sha256']!={c:a['bc_sha256'] for c,a in m['artifacts'].items()}:
            raise ValueError('Static provenance changed')
        if set(s['features'])!=set(MENU)-{'O3'} or any(np.asarray(v).shape!=(len(FEATURE_NAMES),) or not np.isfinite(v).all() for v in s['features'].values()):
            raise ValueError('Invalid long static vector')
    seen=set()
    for x in r['records']:
        key=(x['case'],x['choice'],x['role'],x['block'])
        if key in seen:raise ValueError('Duplicate long cell')
        seen.add(key);m=r['manifests'][x['case']]
        if not m['eligible'] or x['block'] not in range(RUNTIME['blocks']):raise ValueError('Invalid long scope')
        if x['role']=='qualification' and x['choice']=='O3':pair=('O3','O3')
        elif x['role']=='candidate_control' and x['choice']!='O3':pair=(x['choice'],x['choice'])
        elif x['role']=='effect' and x['choice']!='O3':pair=('O3',x['choice'])
        else:raise ValueError('Invalid long role')
        if (x['left'],x['right'])!=pair or type(x['first']) is not bool or m['aliases'][x['choice']]!=x['choice']:raise ValueError('Invalid long comparison')
        for a in [x['left_seconds'],x['right_seconds']]:
            if len(a)!=RUNTIME['pairs'] or not np.isfinite(a).all() or min(a)<=0:raise ValueError('Invalid long times')
    if complete:
        for case,m in r['manifests'].items():
            if not m['eligible']:continue
            q=[x for x in r['records'] if x['case']==case and x['role']=='qualification']
            if len(q)!=RUNTIME['blocks']:raise ValueError('Missing long controls')
            if effect(q,RUNTIME)['control_pass']:
                for c in set(m['aliases'].values())-{'O3'}:
                    for role in ['effect','candidate_control']:
                        if sum(x['case']==case and x['choice']==c and x['role']==role for x in r['records'])!=RUNTIME['blocks']:raise ValueError('Missing long candidate cells')
        if r['labels']!=summarize(r,RUNTIME):raise ValueError('Long labels differ from raw data')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--resume',action='store_true');args=p.parse_args()
    path=Path('results/real_train_long.json');pilot_path=Path('results/real_train.json')
    pilot=json.loads(pilot_path.read_text());verify_pilot(pilot)
    if path.exists():
        if not args.resume:p.error('Preserve long study; use --resume')
        r=json.loads(path.read_text());verify(r,r['complete'])
        if r['complete']:print('Completed longer study verified; no repeats');return
    else:
        r={'protocol':LONG_PROTOCOL,'pilot_sha256':sha(pilot_path),'feature_names':FEATURE_NAMES,
           'complete':False,'manifests':{},'profiles':{},'records':[],'labels':[],'static_cases':{}};save(path,r)
    for case in CASES:
        if case in r['manifests']:continue
        m=copy.deepcopy(pilot['manifests'][case]);cal=[]
        for step in range(4):
            run(m,'O3');times=[run(m,'O3') for _ in range(3)];duration=float(np.median(times))
            cal.append({'iterations':int(m['arguments'][-1]),'seconds':times})
            if .15<=duration<=1. or step==3:break
            count=max(1,min(1000000,int(int(m['arguments'][-1])*.25/duration)))
            m['arguments'][-1]=str(count);m['features'][-1]=count
        m['calibration']=cal;m['eligible']=.15<=duration<=1.
        reference=subprocess.run(['./a.out',*m['arguments']],cwd=m['artifacts']['O3']['directory'],capture_output=True,check=True,timeout=300)
        m['expected_output']={'stdout':hashlib.sha256(reference.stdout).hexdigest(),'files':{}}
        for choice in m['artifacts']:run(m,choice,True);run(m,choice,True)
        r['manifests'][case]=m;r['profiles'][case]={'eligible':m['eligible'],'seconds':cal[-1]['seconds']}
        r['static_cases'][case]=extract_manifest(m);save(path,r)
        print('PROFILE',case,m['arguments'],m['eligible'],flush=True)
    rng=random.Random(LONG_PROTOCOL['seed']);done={(x['case'],x['choice'],x['role'],x['block']) for x in r['records']}
    for phase in ['qualification','candidates']:
        for block in range(RUNTIME['blocks']):
            jobs=[]
            for case,m in r['manifests'].items():
                if not m['eligible']:continue
                if phase=='qualification':jobs.append((case,'O3','O3','qualification'))
                elif effect([x for x in r['records'] if x['case']==case and x['role']=='qualification'],RUNTIME)['control_pass']:
                    for c in dict.fromkeys(m['aliases'].values()):
                        if c!='O3':jobs.extend([(case,c,c,'candidate_control'),(case,'O3',c,'effect')])
            rng.shuffle(jobs)
            for case,left,right,role in jobs:
                first=rng.choice([True,False]);choice=right if role=='effect' else left;key=(case,choice,role,block)
                if key in done:continue
                r['records'].append(measure_cell(r['manifests'][case],left,right,block,role,first,RUNTIME));done.add(key);save(path,r)
                print('CELL',len(done),case,choice,role,flush=True)
    r['labels']=summarize(r,RUNTIME);r['complete']=True;verify(r);save(path,r)
    print('COMPLETE',len(r['labels']),'qualified real menus',flush=True)


if __name__=='__main__':main()
