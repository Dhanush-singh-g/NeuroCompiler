"""Read-only preflight; exit 2 when unchanged-code measurements are unstable."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.benchmarks.polybench import ROOT,verify
from src.benchmarks.compact import save


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--study',type=Path,default=ROOT/'results/polybench_train.json')
    p.add_argument('--output',type=Path)
    args=p.parse_args()
    raw=json.loads(args.study.read_text())
    labels,diagnostics=verify(raw)
    rows={k:{'o3_control_pass':v['o3_control']['control_pass'],
              'interval':v['o3_control']['interval'],
              'complete_menu_qualified':v['accepted']} for k,v in diagnostics.items()}
    trials=[t for c in raw['records'] for side in ['left','right'] for t in c[side+'_trials']]
    passed=sum(v['o3_control_pass'] for v in rows.values())
    result={'ready':bool(rows) and passed==len(rows),'study_complete':raw['complete'],
            'correct_programs':len(raw['manifests']),'o3_controls_passed':passed,
            'controls_attempted':len(rows),'qualified_programs':len(labels),
            'timed_executions':len(trials),'positive_steal_trials':
                sum(t['scheduler_delta']['steal']>0 for t in trials),
            'programs':rows,'action':'Use a runner that passes unchanged-code controls before collecting labels.'}
    if args.output:
        if args.output.exists() and json.loads(args.output.read_text())!=result:
            raise ValueError('Refusing to replace different readiness evidence')
        save(args.output,result)
    print(json.dumps(result,indent=2))
    return 0 if result['ready'] else 2


if __name__=='__main__':sys.exit(main())
