"""Versioned persistent isolated runner; prior experiments are read-only."""
import hashlib
import json
import math
import subprocess
import time
from pathlib import Path

import numpy as np

from src.benchmarks.polybench import ROOT,TOOLS,tool,scheduler_ticks
from src.benchmarks.compact import sha
from src.benchmarks.region import clock_effect,validate_cell as validate_fresh,run_cell as run_fresh

BASE=ROOT/'data/processed/persistent19/pilot_20261011'


def compile_worker():
    BASE.mkdir(parents=True,exist_ok=True);output=BASE/'persistent_library_worker.out'
    if output.exists():raise ValueError('Worker already exists')
    tool([TOOLS/'clang','-O2','-Wall','-Wextra','-rdynamic',ROOT/'src/benchmarks/persistent_library_worker.c',
          '-ldl','-lm','-o',output]);return output


def validate(row,m,pairs,repetitions,first,method):
    if method=='fresh':validate_fresh(row,m,pairs,repetitions,first);return
    kind='isolated_micro' if method=='micro' else 'isolated_batch'
    if row['granularity']!=kind or row['pairs']!=pairs or row['repetitions']!=repetitions or row['first']!=first:
        raise ValueError('Persistent worker metadata changed')
    if row['warmups_per_child']!=3 or row['left_pid']<=0 or row['right_pid']<=0 or row['left_pid']==row['right_pid']:
        raise ValueError('Implementations must run in separate children')
    if len(row['samples'])!=pairs:raise ValueError('Incomplete pairs')
    for p,s in enumerate(row['samples']):
        start=((p%2)==0)==first
        if s['pair']!=p or s['left_first']!=start:raise ValueError('Pair order changed')
        n=repetitions//2+int(repetitions%2 and start) if method=='micro' else repetitions*int(start)
        if (s['left_first_invocations'],s['right_first_invocations'])!=(n,repetitions-n):raise ValueError('Invocation ordering changed')
        traces=s['clock_trace']
        if len(traces)!=(repetitions if method=='micro' else 1) or any(len(t)!=4 for t in traces):raise ValueError('Incomplete invocation trace')
        if any(not math.isfinite(v) or v<=0 for t in traces for v in t):raise ValueError('Invalid trace clock')
        for side,offset in [('left',0),('right',2)]:
            sample=s[side]
            if {key:sample[key] for key in m['expected']}!=m['expected']:raise ValueError('Independent oracle mismatch')
            for field,index in [('cpu_seconds',offset),('wall_seconds',offset+1)]:
                if sample[field]!=sum(t[index] for t in traces):raise ValueError('Aggregate differs from retained invocation traces')


def run(m,method,worker,block,seed,left='O3',right='O3',pairs=24,repetitions=None,cpu=2):
    reps=m['repetitions'] if repetitions is None else repetitions
    cell_seed=seed+int(hashlib.sha256(f'{m["id"]}:{method}:{block}:{left}:{right}'.encode()).hexdigest()[:8],16)
    first=bool(np.random.default_rng(cell_seed).integers(2))
    if method=='fresh':
        if cpu!=2:raise ValueError('Frozen fresh collector supports CPU2 only')
        # Preserve the original collector/seed/order; same-file null control is
        # an explicit pilot change rather than editing its frozen experiment.
        row=run_fresh(m,left,right,block,'qualification',pairs=pairs,repetitions=reps)
        row['method']=method;return row
    before=scheduler_ticks(cpu);begin=time.perf_counter_ns()
    result=subprocess.run([str(worker),m['artifacts'][left]['so'],m['artifacts'][right]['so'],m['input'],
                           str(reps),str(pairs),str(int(first)),str(cpu),method],capture_output=True,check=True,timeout=310)
    row=json.loads(result.stdout);validate(row,m,pairs,reps,first,method)
    after=scheduler_ticks(cpu)
    row.update(case=m['id'],method=method,block=block,left=left,right=right,choice=right,role='qualification',
               process_elapsed_seconds=(time.perf_counter_ns()-begin)*1e-9,
               scheduler_delta={key:after[key]-before[key] for key in before})
    return row
