"""Frozen real-program policies and timing-aware development uncertainty."""
import argparse
import json
import random
from pathlib import Path

import joblib
import numpy as np

from src.benchmarks.compact import PROTOCOL,effect,measure_cell,save,sha,verify_report
from src.features.transform import FEATURE_NAMES
from src.supervised.compact import grouped_score
from src.supervised.frozen import predictions_equal

RUNTIME={**PROTOCOL,'pairs':40,'control_tolerance':.01,'gain_floor':.01,'seed':20261016}


def load_frozen(prefix):
    model_path=Path(f'models/sl_{prefix}_bundle.joblib');source=Path('results/compact_validation.json')
    static_path=Path('data/processed/transform_validation.json')
    bundle=joblib.load(model_path);old=json.loads(source.read_text());verify_report(old)
    static=json.loads(static_path.read_text())
    if static['source_sha256']!=sha(source) or static['feature_names']!=FEATURE_NAMES or bundle['feature_names']!=FEATURE_NAMES:
        raise ValueError('Feature provenance changed')
    for path,h in bundle['provenance'].items():
        if sha(path)!=h:raise ValueError('Training provenance changed')
    programs={m['program'] for m in old['manifests'].values()}
    if any(programs&set(m.programs) for m in bundle['models'].values()):raise ValueError('Fitted development program')
    decisions={case:{name:m.choose(s) for name,m in bundle['models'].items()} for case,s in static['cases'].items()}
    protocol={'runtime':RUNTIME,'schedule_seed':20261016,'model_path':str(model_path),
        'model_sha256':sha(model_path),'source_sha256':sha(source),'static_sha256':sha(static_path),
        'selected':bundle['selected'],'experimental':bundle['experimental'],'risk_policy':bundle.get('risk_policy','O3'),
        'scope':'Previously observed development; all decisions frozen before fresh controls and effects; reserved test untouched'}
    return bundle,old,decisions,protocol


def timing_score(outcomes,records):
    score=grouped_score(outcomes)
    if not outcomes:
        return {**score,'interval':None,'interval_scope':'no accepted outcomes'}
    # Resample original programs, then blocks and pairs for each fixed input.
    # Inputs within a program are averaged, never counted as new programs.
    rng=np.random.default_rng(20261016);n=4000;draws={}
    for o in outcomes:
        if o['choice']=='O3':draws[o['case']]=np.zeros(n);continue
        cells=[x for x in records if x['case']==o['case'] and x['role']=='effect' and x['choice']==o['choice']]
        logs=np.log(np.asarray([c['left_seconds'] for c in cells])/np.asarray([c['right_seconds'] for c in cells]))
        blocks,pairs=logs.shape;ib=rng.integers(blocks,size=(n,blocks));ip=rng.integers(pairs,size=(n,blocks,pairs))
        draws[o['case']]=np.median(np.median(logs[ib[...,None],ip],axis=2),axis=1)
    programs=sorted({o['program'] for o in outcomes})
    group=np.stack([np.mean([draws[o['case']] for o in outcomes if o['program']==p],axis=0) for p in programs],axis=1)
    sample=rng.integers(len(programs),size=(n,len(programs)))
    boot=np.mean(group[np.arange(n)[:,None],sample],axis=1)
    return {**score,'point_only_interval':score['interval'],'interval':np.exp(np.quantile(boot,[.025,.975])).tolist(),
        'interval_scope':'original-program resampling plus within-input paired block/pair resampling; fixed observed inputs, conditional on controls and adaptive prior design',
        'timing_uncertainty_included':True}


def derive(r,old,bundle):
    stat=lambda cells:effect(cells,RUNTIME);eligible=[c for c,v in old['profiles'].items() if v['eligible']];results={}
    for name in bundle['models']:
        outcomes=[];excluded=[]
        for case in eligible:
            q=stat([x for x in r['records'] if x['case']==case and x['role']=='qualification'])
            c=r['decisions'][case][name]['configuration']
            if not q['control_pass']:excluded.append({'case':case,'reason':'O3 control failed'});continue
            if c=='O3':s={'log_speedup':0.,'speedup':1.,'confirmed_gain':False}
            else:
                ctrl=stat([x for x in r['records'] if x['case']==case and x['choice']==c and x['role']=='candidate_control'])
                if not ctrl['control_pass']:excluded.append({'case':case,'reason':'candidate control failed'});continue
                s=stat([x for x in r['records'] if x['case']==case and x['choice']==c and x['role']=='effect'])
                s['confirmed_gain']=s['interval'][0]>1.01 and all(v>1.01 for v in s['blocks']);s['candidate_control']=ctrl
            outcomes.append({'case':case,'program':old['manifests'][case]['program'],'choice':c,**s})
        results[name]={'records':outcomes,'excluded':excluded,'score':timing_score(outcomes,r['records']),
            'changes':sum(x['choice']!='O3' for x in outcomes),'confirmed_gains':sum(x['confirmed_gain'] for x in outcomes)}
    return results


def verify_study(path):
    path=Path(path);prefix=path.stem.removesuffix('_development')
    if prefix not in ['robust','robust_long']:raise ValueError('Unknown frozen study')
    bundle,old,decisions,protocol=load_frozen(prefix);r=json.loads(path.read_text())
    if not r['complete'] or r['protocol']!=protocol or not predictions_equal(decisions,r['decisions']):raise ValueError('Frozen study changed')
    eligible=[c for c,p in old['profiles'].items() if p['eligible']];seen=set()
    for x in r['records']:
        key=(x['case'],x['choice'],x['role'],x['block'])
        if key in seen:raise ValueError('Duplicate frozen cell')
        seen.add(key)
        if x['case'] not in eligible or x['block'] not in range(4):raise ValueError('Invalid scope/block')
        chosen={d['configuration'] for d in decisions[x['case']].values()}-{'O3'}
        if x['role']=='qualification' and x['choice']=='O3':pair=('O3','O3')
        elif x['role']=='candidate_control' and x['choice'] in chosen:pair=(x['choice'],x['choice'])
        elif x['role']=='effect' and x['choice'] in chosen:pair=('O3',x['choice'])
        else:raise ValueError('Unexpected frozen choice')
        if (x['left'],x['right'])!=pair or type(x['first']) is not bool:raise ValueError('Invalid order or comparison')
        for a in [x['left_seconds'],x['right_seconds']]:
            if len(a)!=40 or not np.isfinite(a).all() or min(a)<=0:raise ValueError('Invalid frozen timing')
    for case in eligible:
        q=[x for x in r['records'] if x['case']==case and x['role']=='qualification']
        if len(q)!=4:raise ValueError('Missing frozen controls')
        if effect(q,RUNTIME)['control_pass']:
            for c in {d['configuration'] for d in decisions[case].values()}-{'O3'}:
                for role in ['candidate_control','effect']:
                    if sum(x['case']==case and x['choice']==c and x['role']==role for x in r['records'])!=4:raise ValueError('Missing frozen effects')
    if r['results']!=derive(r,old,bundle):raise ValueError('Reported results differ from raw data')
    return r


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--prefix',choices=['robust','robust_long'],default='robust_long')
    p.add_argument('--resume',action='store_true');args=p.parse_args();output=Path(f'results/{args.prefix}_development.json')
    bundle,old,decisions,protocol=load_frozen(args.prefix)
    if output.exists():
        if not args.resume:p.error('Preserve frozen study; use --resume')
        r=json.loads(output.read_text())
        if r['protocol']!=protocol or not predictions_equal(decisions,r['decisions']):raise ValueError('Frozen choices changed')
        if r['complete']:verify_study(output);print('Completed frozen study verified; no repeated timing');return
    else:
        r={'protocol':protocol,'decisions':decisions,'complete':False,'records':[],'results':{}};save(output,r)
    rng=random.Random(protocol['schedule_seed']);done={(x['case'],x['choice'],x['role'],x['block']) for x in r['records']}
    eligible=[c for c,p in old['profiles'].items() if p['eligible']]
    for phase in ['qualification','predictions']:
        for block in range(4):
            jobs=[]
            for case in eligible:
                if phase=='qualification':jobs.append((case,'O3','O3','qualification'))
                elif effect([x for x in r['records'] if x['case']==case and x['role']=='qualification'],RUNTIME)['control_pass']:
                    for c in sorted({d['configuration'] for d in decisions[case].values()}-{'O3'}):
                        jobs.extend([(case,c,c,'candidate_control'),(case,'O3',c,'effect')])
            rng.shuffle(jobs)
            for case,left,right,role in jobs:
                first=rng.choice([True,False]);choice=right if role=='effect' else left;key=(case,choice,role,block)
                if key in done:continue
                r['records'].append(measure_cell(old['manifests'][case],left,right,block,role,first,RUNTIME));done.add(key);save(output,r)
                print('CELL',len(done),case,choice,role,flush=True)
    r['results']=derive(r,old,bundle);r['complete']=True;save(output,r);verify_study(output)
    print(json.dumps({name:{'score':v['score'],'confirmed_gains':v['confirmed_gains'],'excluded':v['excluded']} for name,v in r['results'].items()},indent=2))


if __name__=='__main__':main()
