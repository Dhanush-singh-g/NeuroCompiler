"""Verify raw fresh-development coverage and recompute all reported outcomes."""
import json
from pathlib import Path

import joblib
import numpy as np

from src.benchmarks.compact import effect,sha,verify_report
from src.supervised.compact import grouped_score
from src.supervised.frozen import predictions_equal


def verify_study(path):
    r=json.loads(Path(path).read_text())
    p=r['protocol'];runtime=p['runtime']
    model_path=Path('models/sl_transform_policy_bundle.joblib' if 'policy' in Path(path).name else 'models/sl_transform_bundle.joblib')
    if sha(model_path)!=p['model_sha256'] or sha('data/processed/transform_validation.json')!=p['static_sha256']:
        raise ValueError('Model/static data changed')
    source=Path('results/compact_validation.json')
    if sha(source)!=p['source_sha256']:raise ValueError('Source changed')
    old=json.loads(source.read_text());verify_report(old)
    b=joblib.load(model_path);static=json.loads(Path('data/processed/transform_validation.json').read_text())
    for source_path,h in b['provenance'].items():
        if sha(source_path)!=h:raise ValueError('Training source changed')
    decisions={case:{name:m.choose(s) for name,m in b['models'].items()} for case,s in static['cases'].items()}
    if not predictions_equal(decisions,r['decisions']):raise ValueError('Frozen decisions differ')
    if not r['complete']:raise ValueError('Incomplete study')
    expected_runtime=dict(old['protocol'])
    precision='confirmation' in Path(path).name
    if precision:expected_runtime.update(pairs=40,control_tolerance=.01,gain_floor=.01,seed=20261013)
    if runtime!=expected_runtime:raise ValueError('Measurement protocol changed')
    if p['seed']!=(20261013 if precision else 20261012) or p['selected']!=b['selected'] or p['experimental']!=b['experimental']:
        raise ValueError('Schedule/policy metadata changed')
    seen=set();eligible=[k for k,v in old['profiles'].items() if v['eligible']]
    for x in r['records']:
        key=(x['case'],x['choice'],x['role'],x['block'])
        if key in seen:raise ValueError('Duplicate cell')
        seen.add(key)
        if x['case'] not in eligible or x['block'] not in range(runtime['blocks']):raise ValueError('Invalid scope/block')
        chosen={d['configuration'] for d in decisions[x['case']].values()}
        if x['role']=='qualification' and x['choice']=='O3':pair=('O3','O3')
        elif x['role']=='candidate_control' and x['choice'] in chosen-{'O3'}:pair=(x['choice'],x['choice'])
        elif x['role']=='effect' and x['choice'] in chosen-{'O3'}:pair=('O3',x['choice'])
        else:raise ValueError('Unexpected measured choice')
        if (x['left'],x['right'])!=pair or type(x['first']) is not bool:raise ValueError('Invalid execution order/pair')
        for t in (x['left_seconds'],x['right_seconds']):
            if len(t)!=runtime['pairs'] or not np.isfinite(t).all() or any(v<=0 for v in t):raise ValueError('Invalid timings')
    stat=lambda cells:effect(cells,runtime)
    for case in eligible:
        q=[x for x in r['records'] if x['case']==case and x['role']=='qualification']
        if len(q)!=runtime['blocks']:raise ValueError('Missing qualification')
        if stat(q)['control_pass']:
            for choice in {d['configuration'] for d in decisions[case].values()}-{'O3'}:
                for role in ('effect','candidate_control'):
                    if sum(x['case']==case and x['choice']==choice and x['role']==role for x in r['records'])!=runtime['blocks']:
                        raise ValueError('Missing candidate blocks')
    results={}
    for name in b['models']:
        outcomes=[];excluded=[]
        for case in eligible:
            q=stat([x for x in r['records'] if x['case']==case and x['role']=='qualification'])
            c=decisions[case][name]['configuration']
            if not q['control_pass']:excluded.append(case);continue
            if c=='O3':s={'log_speedup':0.,'speedup':1.,'confirmed_gain':False}
            else:
                ctrl=stat([x for x in r['records'] if x['case']==case and x['choice']==c and x['role']=='candidate_control'])
                if not ctrl['control_pass']:excluded.append(case);continue
                s=stat([x for x in r['records'] if x['case']==case and x['choice']==c and x['role']=='effect'])
                s['confirmed_gain']=s['interval'][0]>1+runtime['gain_floor'] and all(v>1+runtime['gain_floor'] for v in s['blocks'])
                s['candidate_control']=ctrl
            outcomes.append({'case':case,'program':old['manifests'][case]['program'],'choice':c,**s})
        results[name]={'records':outcomes,'excluded':excluded,'score':grouped_score(outcomes),
            'changes':sum(x['choice']!='O3' for x in outcomes),'confirmed_gains':sum(x['confirmed_gain'] for x in outcomes)}
    if results!=r['results']:raise ValueError('Reported results differ from raw evidence')
    print('Verified',path,len(r['records']),'cells')
    return r


def main():
    for name in ['transform_development','transform_policy_development','transform_policy_confirmation']:
        path=Path(f'results/{name}.json')
        if path.exists():verify_study(path)


if __name__=='__main__':main()
