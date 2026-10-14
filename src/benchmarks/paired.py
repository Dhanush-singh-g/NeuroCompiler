"""Native-CPU service-time SL with independent wall-latency confirmation.

CPU time is a distinct objective. All clock samples remain intact. Neither
steal filtering nor minima are used to turn CPU gains into wall-time claims.
"""
import hashlib
import json
import math
import subprocess
import time
from pathlib import Path

import numpy as np

from src.benchmarks.compact import effect,save,sha
from src.benchmarks.polybench import ROOT,TOOLS,CORPUS,inventory,tool,scheduler_ticks,DEVELOPMENT_INPUT_FIXES
from src.features.transform import candidate_vector,parse_ir

MENU={
    'O3': ['-passes=default<O3>'],
    'O2': ['-passes=default<O2>'],
    'O3_no_vector': ['-passes=default<O3>','-vectorize-loops=false','-vectorize-slp=false'],
    'O3_no_unroll': ['-passes=default<O3>','-unroll-threshold-aggressive=0','-unroll-runtime=false'],
    'O3_interchange': ['-passes=default<O3>','-enable-loopinterchange=true'],
    'O3_interleave1': ['-passes=default<O3>','-force-vector-interleave=1'],
    'O3_no_slp': ['-passes=default<O3>','-vectorize-slp=false'],
    'instcombine_O3': ['-passes=function(instcombine<max-iterations=10>),default<O3>'],
}
PILOT_CASES=['correlation','gemm','durbin']
PROTOCOL={'version':2,'objective':'CLOCK_THREAD_CPUTIME_ID native kernel service time',
    'secondary':'CLOCK_MONOTONIC native kernel wall latency, independently qualified',
    'menu':MENU,'blocks':3,'pairs':24,'cpu':2,'seed':20261024,
    'control_tolerance':.03,'gain_floor':.03,'bootstrap_replicates':2000,
    'batch_target_cpu_seconds':.040,'max_repetitions':100000,
    'minimum_o3_cpu_seconds_per_invocation':.000020,
    'target':'clang -march=native, strict FP, -ffp-contract=off, PIC shared kernels',
    'pairing':'persistent process, alternating logical A/B, fresh inputs, two warmups',
    'placement_control':'identical O3 DSO copied to a second path and loaded separately',
    'qualification':'per-program O3 controls; no relaunch/retry to achieve passing status',
    'scheduler':'retain every trial; steal increments span worker process',
    'pilot_cases':PILOT_CASES,'reserved_tests':'medley and existing cBench final tests stay closed'}


def worker(directory):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    elf=directory/'paired_worker.out'
    tool([TOOLS/'clang','-O2','-rdynamic',ROOT/'src/benchmarks/paired_worker.c','-ldl','-lm','-o',elf])
    return elf


def run_cell(m,left,right,block,role,pairs=None,repetitions=None):
    pairs=PROTOCOL['pairs'] if pairs is None else pairs
    repetitions=m['repetitions'] if repetitions is None else repetitions
    seed=PROTOCOL['seed']+int(hashlib.sha256(f"{m['id']}:{right}:{role}:{block}".encode()).hexdigest()[:8],16)
    first=bool(np.random.default_rng(seed).integers(2))
    before=scheduler_ticks(PROTOCOL['cpu']);begin=time.perf_counter_ns()
    command=['taskset','-c',str(PROTOCOL['cpu']),m['worker'],m['artifacts'][left]['so'],
             m['artifacts'][right]['so'],str(repetitions),str(pairs),str(int(first))]
    result=subprocess.run(command,capture_output=True,check=True,timeout=240)
    elapsed=(time.perf_counter_ns()-begin)*1e-9;after=scheduler_ticks(PROTOCOL['cpu'])
    row=json.loads(result.stdout)
    if row['repetitions']!=repetitions or row['pairs']!=pairs or row['first']!=first:
        raise ValueError('Worker command/result mismatch')
    for p,s in enumerate(row['samples']):
        if s['pair']!=p or s['left_first']!=((p%2==0)==first):raise ValueError('Pair ordering mismatch')
        for side in ['left','right']:
            t=s[side]
            if {k:t[k] for k in m['expected']}!=m['expected']:raise ValueError('Output mismatch')
            if any(not math.isfinite(t[k]) or t[k]<=0 for k in ['cpu_seconds','wall_seconds']):
                raise ValueError('Invalid native clocks')
    if len(row['samples'])!=pairs:raise ValueError('Incomplete paired samples')
    row.update({'case':m['id'],'choice':right if role=='effect' else left,
        'left':left,'right':right,'block':block,'role':role,'process_elapsed_seconds':elapsed,
        'scheduler_delta':{k:after[k]-before[k] for k in before}})
    return row


def build(item,directory,worker_path):
    if item['split']=='reserved_test':raise ValueError('Reserved benchmark')
    # Use already verified, explicitly adapted source, never change upstream.
    previous=json.loads((ROOT/f"results/polybench_{item['split']}.json").read_text())['manifests'][item['id']]
    old_source=Path(previous['artifacts']['O3']['bc']).parent/'benchmark.c'
    if sha(old_source)!=previous['prepared_source_sha256']:raise ValueError('Source adapter changed')
    directory=Path(directory).resolve();directory.mkdir(parents=True,exist_ok=False)
    source=directory/'benchmark.c';source.write_bytes(old_source.read_bytes())
    flags=['-fPIC','-march=native','-ffp-contract=off','-fno-discard-value-names','-DSMALL_DATASET',
           '-I'+str(CORPUS/'utilities'),'-I'+str((CORPUS/item['path']).parent)]
    initial=directory/'initial.bc'
    tool([TOOLS/'clang',*flags,'-O1','-Xclang','-disable-llvm-passes','-DPOLYBENCH_TIME',
        '-DPOLYBENCH_DUMP_ARRAYS','-Dmain=nc_benchmark_main','-Dfprintf=nc_sink_fprintf',
        '-emit-llvm','-c',source,'-o',initial])
    support=directory/'support.o'
    tool([TOOLS/'clang',*flags,'-O3','-Dpolybench_timer_start=nc_unused_start',
        '-Dpolybench_timer_stop=nc_unused_stop','-Dpolybench_timer_print=nc_unused_print',
        '-c',CORPUS/'utilities/polybench.c','-o',support])
    artifacts={}
    for choice,args in {'reference_O0':['-passes=default<O0>'],**MENU}.items():
        bc,so=directory/f'{choice}.bc',directory/f'{choice}.so'
        tool([TOOLS/'opt',*args,initial,'-o',bc])
        tool([TOOLS/'clang',*flags,'-O3','-Xclang','-disable-llvm-passes','-shared',
              '-Wl,-Bsymbolic',bc,support,'-lm','-o',so])
        artifacts[choice]={'bc':str(bc),'so':str(so),'bc_sha256':sha(bc),'so_sha256':sha(so)}
    copy=directory/'O3_copy.so';copy.write_bytes(Path(artifacts['O3']['so']).read_bytes())
    artifacts['O3_copy']={**artifacts['O3'],'so':str(copy)}
    m={**item,'artifacts':artifacts,'worker':str(worker_path),'worker_sha256':sha(worker_path),
       'worker_source_sha256':sha(ROOT/'src/benchmarks/paired_worker.c'),
       'source_sha256':sha(source),'initial_sha256':sha(initial),'support_sha256':sha(support),
       'expected':previous['expected'],'repetitions':1,'correctness':{}}
    for c in MENU:
        m['correctness'][c]=run_cell(m,'reference_O0',c,0,'correctness',pairs=1,repetitions=1)
    cal=run_cell(m,'O3','O3_copy',0,'calibration',pairs=3,repetitions=1)
    durations=[s['left']['cpu_seconds'] for s in cal['samples']]+[s['right']['cpu_seconds'] for s in cal['samples']]
    baseline=float(np.median(durations))
    m['repetitions']=min(PROTOCOL['max_repetitions'],max(1,math.ceil(PROTOCOL['batch_target_cpu_seconds']/baseline)))
    m['calibration']=cal;m['eligible']=baseline>=PROTOCOL['minimum_o3_cpu_seconds_per_invocation']
    parsed={c:parse_ir(tool([TOOLS/'llvm-dis',artifacts[c]['bc'],'-o','-']).decode()) for c in MENU}
    base_size=Path(artifacts['O3']['so']).stat().st_size
    m['features']={c:candidate_vector(parsed['O3'],parsed[c],c,0,1,
         (Path(artifacts[c]['so']).stat().st_size-base_size)/base_size,entrypoint='nc_benchmark_main')[:-3]
         +[float(c==other) for other in list(MENU)[1:]] for c in MENU if c!='O3'}
    m['aliases']={c:next(k for k in MENU if artifacts[c]['so_sha256']==artifacts[k]['so_sha256']) for c in MENU}
    save(directory/'manifest.json',m);return m


def clock_effect(cells,clock):
    if clock not in ('cpu','wall'):raise ValueError('Unknown native clock')
    arrays=[{'left_seconds':[s['left'][clock+'_seconds'] for s in c['samples']],
             'right_seconds':[s['right'][clock+'_seconds'] for s in c['samples']]} for c in cells]
    return effect(arrays,PROTOCOL)


def extract_features(m):
    parsed={c:parse_ir(tool([TOOLS/'llvm-dis',m['artifacts'][c]['bc'],'-o','-']).decode()) for c in MENU}
    base_size=Path(m['artifacts']['O3']['so']).stat().st_size
    return {c:candidate_vector(parsed['O3'],parsed[c],c,0,1,
        (Path(m['artifacts'][c]['so']).stat().st_size-base_size)/base_size,entrypoint='nc_benchmark_main')[:-3]
        +[float(c==other) for other in list(MENU)[1:]] for c in MENU if c!='O3'}


def summarize(report):
    labels,diagnostics=[],{}
    for ident,m in report['manifests'].items():
        if not m['eligible']:continue
        rows=[r for r in report['records'] if r['case']==ident]
        qc=[r for r in rows if r['role']=='qualification']
        if len(qc)!=PROTOCOL['blocks']:continue
        cpu,wall=clock_effect(qc,'cpu'),clock_effect(qc,'wall')
        stats={'O3':{'log_speedup':0.,'speedup':1.,'interval':[1.,1.],'confirmed_gain':False}}
        valid=cpu['control_pass'];wall_valid=wall['control_pass']
        for c in report.get('active_choices',{}).get(ident,list(MENU)):
            alias=m['aliases'][c]
            if alias in stats:stats[c]=dict(stats[alias]);continue
            ec=[r for r in rows if r['role']=='effect' and r['choice']==alias]
            cc=[r for r in rows if r['role']=='candidate_control' and r['choice']==alias]
            if len(ec)!=PROTOCOL['blocks'] or len(cc)!=PROTOCOL['blocks']:valid=False;continue
            s,ctrl=clock_effect(ec,'cpu'),clock_effect(cc,'cpu')
            w,wctrl=clock_effect(ec,'wall'),clock_effect(cc,'wall')
            s['candidate_control']=ctrl;s['wall_effect']=w;s['wall_control']=wctrl
            floor=1+PROTOCOL['gain_floor']
            s['confirmed_gain']=bool(s['interval'][0]>floor and all(v>floor for v in s['blocks']))
            s['confirmed_wall_gain']=bool(wall['control_pass'] and wctrl['control_pass'] and
                w['interval'][0]>floor and all(v>floor for v in w['blocks']))
            stats[c]=s;valid &= ctrl['control_pass'];wall_valid &= wctrl['control_pass']
        diagnostics[ident]={'cpu_control':cpu,'wall_control':wall,'outcomes':stats,
                           'cpu_menu_qualified':bool(valid),'wall_menu_qualified':bool(valid and wall_valid)}
        if valid:labels.append({'case':ident,'family':m['family'],'features':m['features'],'outcomes':stats})
    return labels,diagnostics


def verify(report,artifacts=True):
    if report['protocol']!=PROTOCOL or report['inventory']!=inventory():raise ValueError('Protocol/corpus changed')
    items={i['id']:i for i in report['inventory'] if i['split']==report['split']}
    if set(report['manifests']) & set(report['failures']) or not (
        set(report['manifests']) | set(report['failures'])) <= set(items):raise ValueError('Invalid case coverage')
    if report['complete'] and set(report['manifests']) | set(report['failures'])!=set(items):
        raise ValueError('Incomplete corpus coverage')
    seen=set()
    for ident,m in report['manifests'].items():
        if any(m[k]!=v for k,v in items[ident].items()):raise ValueError('Changed benchmark identity')
        if artifacts:
            if sha(m['worker'])!=m['worker_sha256'] or sha(ROOT/'src/benchmarks/paired_worker.c')!=m['worker_source_sha256']:
                raise ValueError('Worker changed')
            d=Path(m['artifacts']['O3']['bc']).parent
            for name,key in [('benchmark.c','source_sha256'),('initial.bc','initial_sha256'),('support.o','support_sha256')]:
                if sha(d/name)!=m[key]:raise ValueError('Build input changed')
            old=json.loads((ROOT/f"results/polybench_{m['split']}.json").read_text())['manifests'][ident]
            if m['source_sha256']!=old['prepared_source_sha256']:raise ValueError('Unpinned input adaptation')
            for a in m['artifacts'].values():
                if sha(a['bc'])!=a['bc_sha256'] or sha(a['so'])!=a['so_sha256']:raise ValueError('Native artifact changed')
            if extract_features(m)!=m['features']:raise ValueError('Static feature evidence changed')
        expected_aliases={c:next(k for k in MENU if m['artifacts'][c]['so_sha256']==m['artifacts'][k]['so_sha256']) for c in MENU}
        if m['aliases']!=expected_aliases or m['artifacts']['O3_copy']['so_sha256']!=m['artifacts']['O3']['so_sha256']:
            raise ValueError('Invalid executable alias/placement control')
        if not isinstance(m['repetitions'],int) or not 1<=m['repetitions']<=PROTOCOL['max_repetitions']:
            raise ValueError('Invalid repetitions')
    for r in report['records']:
        m=report['manifests'][r['case']];role=r['role'];choice=r['choice']
        key=(r['case'],choice,r['role'],r['block'])
        if key in seen or not m['eligible'] or r['block'] not in range(PROTOCOL['blocks']):raise ValueError('Invalid/duplicate timing cell')
        seen.add(key)
        if role=='qualification':pair=('O3','O3_copy');expected_choice='O3'
        elif role=='candidate_control':pair=(choice,choice);expected_choice=choice
        elif role=='effect':pair=('O3',choice);expected_choice=choice
        else:raise ValueError('Invalid role')
        if (r['left'],r['right'])!=pair or choice!=expected_choice or choice not in MENU or m['aliases'][choice]!=choice:
            raise ValueError('Changed paired comparison')
        if r['pairs']!=PROTOCOL['pairs'] or r['repetitions']!=m['repetitions'] or len(r['samples'])!=PROTOCOL['pairs']:
            raise ValueError('Incomplete trial count')
        if not isinstance(r['first'],bool) or not math.isfinite(r['process_elapsed_seconds']) or r['process_elapsed_seconds']<=0:
            raise ValueError('Invalid process timing metadata')
        for p,s in enumerate(r['samples']):
            if s['pair']!=p or s['left_first']!=((p%2==0)==r['first']):raise ValueError('Pair ordering changed')
            for side in ['left','right']:
                t=s[side]
                if {k:t[k] for k in m['expected']}!=m['expected']:raise ValueError('Timed output changed')
                if any(not math.isfinite(t[k]) or t[k]<=0 for k in ['wall_seconds','cpu_seconds']):
                    raise ValueError('Invalid clock duration')
        if any(v<0 for v in r['scheduler_delta'].values()):raise ValueError('Invalid scheduler evidence')
    if report['split']=='development' and 'frozen_decisions' in report:
        expected_active={ident:['O3',d['choice']] if d['choice']!='O3' else ['O3']
                         for ident,d in report['frozen_decisions'].items()}
        if report.get('active_choices')!=expected_active or set(expected_active)!=set(report['manifests']):
            raise ValueError('Frozen development scope changed')
    labels,diagnostics=summarize(report)
    if report['complete']:
        expected=set()
        for ident,m in report['manifests'].items():
            if not m['eligible']:continue
            for block in range(PROTOCOL['blocks']):expected.add((ident,'O3','qualification',block))
            q=diagnostics.get(ident)
            if q and q['cpu_control']['control_pass']:
                for c in report.get('active_choices',{}).get(ident,list(MENU)):
                    if c!='O3' and m['aliases'][c]==c:
                        for block in range(PROTOCOL['blocks']):
                            for role in ['candidate_control','effect']:expected.add((ident,c,role,block))
        if seen!=expected:raise ValueError('Incomplete/extra candidate timing coverage')
    if 'labels' in report and labels!=report['labels']:raise ValueError('Reported labels changed')
    if 'diagnostics' in report and diagnostics!=report['diagnostics']:raise ValueError('Reported effects changed')
    return labels,diagnostics
