"""Fail a runtime-readiness check when recorded unchanged controls fail.

    python -m scripts.check_timing --study results/real_train_long.json

This inspects a completed study without repeating measurements or widening
thresholds. Exit 2 means this study cannot establish runtime readiness.
"""
import argparse
import json
from pathlib import Path

from src.benchmarks.compact import effect,save,sha


def inspect(path):
    path=Path(path);r=json.loads(path.read_text())
    if path.name=='real_train.json':
        from scripts.collect_real import verify
        verify(r)
    elif path.name=='real_train_long.json':
        from scripts.collect_real_long import verify
        verify(r)
    else:raise ValueError('Use a verified real training study')
    runtime=r['protocol']['runtime'];controls={}
    for case,m in r['manifests'].items():
        if not m['eligible']:continue
        q=[x for x in r['records'] if x['case']==case and x['role']=='qualification']
        controls[case]=effect(q,runtime)
    return {'source_sha256':sha(path),'source':str(path),'controls':controls,
        'runtime_ready':bool(controls) and all(s['control_pass'] for s in controls.values()),
        'accepted_baseline_cases':sum(s['control_pass'] for s in controls.values()),
        'rule':'Every eligible unchanged O3 control must meet the declared block, interval, and order-bias checks',
        'scope':'Readiness of these recorded timings, not a statement about future machine performance'}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--study',type=Path,required=True)
    p.add_argument('--output',type=Path);args=p.parse_args();r=inspect(args.study)
    if args.output:
        if args.output.exists():p.error('Preserve existing readiness report')
        save(args.output,r)
    print(json.dumps(r,indent=2));raise SystemExit(0 if r['runtime_ready'] else 2)


if __name__=='__main__':main()
