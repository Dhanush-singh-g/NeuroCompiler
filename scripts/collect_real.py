"""Collect pinned real-program training menus without revisiting failed cells."""
import argparse
import json
import random
from pathlib import Path

import numpy as np

from src.benchmarks.compact import MENU,PROTOCOL,effect,measure_cell,save,summarize
from src.benchmarks.real import CASES,REAL_PROTOCOL,freeze_real,verify_real
from src.features.transform import FEATURE_NAMES,extract_manifest


def verify(r,complete=True):
    if r['protocol']!=REAL_PROTOCOL or r['feature_names']!=FEATURE_NAMES:raise ValueError('Real protocol changed')
    if complete and (not r['complete'] or set(r['manifests'])!=set(CASES)):raise ValueError('Incomplete real scope')
    if set(r['profiles'])!=set(r['manifests']) or set(r['static_cases'])!=set(r['manifests']):raise ValueError('Case metadata missing')
    for case,m in r['manifests'].items():
        if case!=m['id']:raise ValueError('Manifest key mismatch')
        verify_real(m)
        if r['profiles'][case]!={'eligible':m['eligible'],'seconds':m['calibration'][-1]['seconds']}:raise ValueError('Duration profile changed')
        s=r['static_cases'][case]
        if s['program']!=m['program'] or s['aliases']!=m['aliases'] or s['static_only'] is not True or s['bc_sha256']!={c:a['bc_sha256'] for c,a in m['artifacts'].items()}:
            raise ValueError('Static provenance changed')
        if set(s['features'])!=set(MENU)-{'O3'} or any(np.asarray(v).shape!=(len(FEATURE_NAMES),) or not np.isfinite(v).all() for v in s['features'].values()):
            raise ValueError('Invalid real static vector')
    seen=set()
    for x in r['records']:
        key=(x['case'],x['choice'],x['role'],x['block'])
        if key in seen:raise ValueError('Duplicate timing cell')
        seen.add(key);m=r['manifests'][x['case']]
        if not m['eligible'] or x['block'] not in range(PROTOCOL['blocks']):raise ValueError('Timing outside eligible scope')
        if x['role']=='qualification' and x['choice']=='O3':pair=('O3','O3')
        elif x['role']=='candidate_control' and x['choice']!='O3':pair=(x['choice'],x['choice'])
        elif x['role']=='effect' and x['choice']!='O3':pair=('O3',x['choice'])
        else:raise ValueError('Unexpected timing role')
        if (x['left'],x['right'])!=pair or type(x['first']) is not bool or m['aliases'][x['choice']]!=x['choice']:raise ValueError('Invalid paired choice')
        for a in (x['left_seconds'],x['right_seconds']):
            if len(a)!=PROTOCOL['pairs'] or not np.isfinite(a).all() or min(a)<=0:raise ValueError('Invalid native timing')
    if complete:
        for case,m in r['manifests'].items():
            if not m['eligible']:continue
            q=[x for x in r['records'] if x['case']==case and x['role']=='qualification']
            if len(q)!=PROTOCOL['blocks']:raise ValueError('Missing initial controls')
            if effect(q)['control_pass']:
                for c in set(m['aliases'].values())-{'O3'}:
                    for role in ['candidate_control','effect']:
                        if sum(x['case']==case and x['choice']==c and x['role']==role for x in r['records'])!=PROTOCOL['blocks']:raise ValueError('Missing candidate cells')
        if r['labels']!=summarize(r):raise ValueError('Real labels differ from raw timings')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--resume',action='store_true');args=p.parse_args()
    path=Path('results/real_train.json')
    if path.exists():
        if not args.resume:p.error('Preserve frozen data; use --resume')
        r=json.loads(path.read_text());verify(r,r['complete'])
        if r['complete']:print('Completed real training verified; no repeated timing');return
    else:
        r={'protocol':REAL_PROTOCOL,'complete':False,'manifests':{},'profiles':{},'records':[],
           'labels':[],'feature_names':FEATURE_NAMES,'static_cases':{}};save(path,r)
    for case in CASES:
        if case in r['manifests']:continue
        print('BUILD',case,flush=True);m=freeze_real(case,Path('data/processed/real_train')/case)
        r['manifests'][case]=m;r['profiles'][case]={'eligible':m['eligible'],'seconds':m['calibration'][-1]['seconds']}
        r['static_cases'][case]=extract_manifest(m);save(path,r)
        print('PROFILE',case,m['features'],m['eligible'],'distinct executables',len(set(m['aliases'].values())),flush=True)
    rng=random.Random(REAL_PROTOCOL['seed']);done={(x['case'],x['choice'],x['role'],x['block']) for x in r['records']}
    for phase in ['qualification','candidates']:
        for block in range(PROTOCOL['blocks']):
            jobs=[]
            for case,m in r['manifests'].items():
                if not m['eligible']:continue
                if phase=='qualification':jobs.append((case,'O3','O3','qualification'))
                else:
                    q=[x for x in r['records'] if x['case']==case and x['role']=='qualification']
                    if not effect(q)['control_pass']:continue
                    for c in dict.fromkeys(m['aliases'].values()):
                        if c!='O3':jobs.extend([(case,c,c,'candidate_control'),(case,'O3',c,'effect')])
            rng.shuffle(jobs)
            for case,left,right,role in jobs:
                first=rng.choice([True,False]);choice=right if role=='effect' else left;key=(case,choice,role,block)
                if key in done:continue
                r['records'].append(measure_cell(r['manifests'][case],left,right,block,role,first));done.add(key);save(path,r)
                print('CELL',len(done),case,choice,role,flush=True)
    r['labels']=summarize(r);r['complete']=True;verify(r);save(path,r)
    print('COMPLETE',len(r['labels']),'inputs',len({x['program'] for x in r['labels']}),'original real programs',flush=True)


if __name__=='__main__':main()
