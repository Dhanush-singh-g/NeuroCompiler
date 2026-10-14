"""Declared secondary check of the single confirmed training candidate."""
import json
import math
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.benchmarks.compact import save,sha,effect
from src.benchmarks.invocation import ROOT,BASE,NAME,PROTOCOL,TOOLS,tool,scheduler_ticks,validate_cell


def main():
    output=ROOT/'results/invocation_isolated_confirmation.json'
    declaration=ROOT/'results/invocation_isolated_declaration.json'
    if output.exists() or declaration.exists():raise ValueError('Existing confirmation; no retries')
    raw=json.loads((ROOT/f'results/{NAME}_train.json').read_text())
    m=raw['manifests']['expat_nested'];choice='O2'
    if not raw['diagnostics'][m['id']]['measurements'][choice]['cpu']['effect']['confirmed_gain']:
        raise ValueError('Training candidate not confirmed under primary protocol')
    worker=BASE/'isolated_library_worker.out'
    tool([TOOLS/'clang','-O2','-rdynamic',ROOT/'src/benchmarks/isolated_library_worker.c','-ldl','-lm','-o',worker])
    protocol={**PROTOCOL,'seed':20261101,'repetitions':min(100000,m['repetitions']*2),
        'pairing':'one DSO per fresh worker process; alternating process order; summed API clocks; three warmups',
        'scope':'post-study secondary confirmation; selected training winner; never fit or retune SL with these timings'}
    declared={'protocol':protocol,'case':m['id'],'candidate':choice,'training_sha256':sha(ROOT/f'results/{NAME}_train.json'),
        'worker_sha256':sha(worker),'source_sha256':{n:sha(ROOT/n) for n in ['src/benchmarks/isolated_library_worker.c','src/benchmarks/invocation_worker.c','scripts/confirm_invocation.py']}}
    save(declaration,declared);report={**declared,'records':[],'complete':False};save(output,report)
    rng=np.random.default_rng(protocol['seed'])
    def run(c):
        result=subprocess.run(['taskset','-c','2',str(worker),m['artifacts'][c]['so'],m['input'],str(protocol['repetitions'])],capture_output=True,check=True,timeout=60)
        row=json.loads(result.stdout)
        if row['mode']!='one_implementation' or row['repetitions']!=protocol['repetitions']:raise ValueError('Worker metadata mismatch')
        sample=row['sample']
        if {k:sample[k] for k in m['expected']}!=m['expected']:raise ValueError('Independent oracle output mismatch')
        if any(not math.isfinite(sample[k]) or sample[k]<=0 for k in ['cpu_seconds','wall_seconds']):raise ValueError('Invalid isolated clock')
        return sample
    for block in range(protocol['blocks']):
        for role,left,right in [('qualification','O3','O3'),('candidate_control',choice,choice),('effect','O3',choice)]:
            first=bool(rng.integers(2));samples=[];before=scheduler_ticks(2);begin=time.perf_counter_ns()
            for p in range(protocol['pairs']):
                left_first=(p%2==0)==first
                if left_first:a,b=run(left),run(right)
                else:b,a=run(right),run(left)
                samples.append({'pair':p,'left_first':left_first,'left':a,'right':b})
            after=scheduler_ticks(2)
            report['records'].append({'block':block,'role':role,'left':left,'right':right,'first':first,'samples':samples,
                'process_elapsed_seconds':(time.perf_counter_ns()-begin)*1e-9,'scheduler_delta':{k:after[k]-before[k] for k in before}})
            save(output,report);print('Isolated confirmation',block+1,role,flush=True)
    stats={}
    for clock in ['cpu','wall']:
        detail={}
        for role in ['qualification','candidate_control','effect']:
            rows=[r for r in report['records'] if r['role']==role]
            detail[role]=effect([{'left_seconds':[s['left'][clock+'_seconds'] for s in r['samples']],
                                 'right_seconds':[s['right'][clock+'_seconds'] for s in r['samples']]} for r in rows],protocol)
        s=detail['effect'];valid=detail['qualification']['control_pass'] and detail['candidate_control']['control_pass']
        detail['qualified']=bool(valid);detail['confirmed_gain']=bool(valid and s['interval'][0]>1.03 and all(v>1.03 for v in s['blocks']))
        stats[clock]=detail
    report['statistics']=stats;report['complete']=True;save(output,report)
    print(json.dumps({clock:{'qualified':v['qualified'],'confirmed_gain':v['confirmed_gain'],'effect':v['effect']} for clock,v in stats.items()},indent=2))


if __name__=='__main__':main()
