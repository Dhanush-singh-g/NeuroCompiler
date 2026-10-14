"""Separately declared aggregate-start-order sensitivity; no fitting feedback."""
import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.benchmarks.broad import ROOT,NAME,PROTOCOL,sha,save,verify


def main():
    output=ROOT/'results/broad_order_sensitivity.json'
    if output.exists():raise ValueError('Existing sensitivity report')
    declaration=ROOT/'results/broad_order_declaration.json';d=json.loads(declaration.read_text())
    if d['source_sha256']!=sha(Path(__file__)) or d['primary_declaration_sha256']!=sha(ROOT/'results/broad_declaration.json'):
        raise ValueError('Sensitivity declaration changed')
    details={};warnings={};bound=math.log1p(PROTOCOL['control_tolerance'])
    for split in ['train','development']:
        raw=json.loads((ROOT/f'results/{NAME}_{split}.json').read_text());verify(raw)
        groups={}
        for row in raw['records']:groups.setdefault((row['case'],row['choice'],row['role']),[]).append(row)
        details[split]={};warnings[split]={clock:{role:0 for role in ['qualification','candidate_control','effect']} for clock in ['cpu','wall']}
        for key,rows in groups.items():
            clocks={}
            for clock in ['cpu','wall']:
                all_left=[];all_right=[];blocks=[]
                for row in rows:
                    left=[];right=[]
                    for sample in row['samples']:
                        value=math.log(sample['left'][clock+'_seconds']/sample['right'][clock+'_seconds'])
                        (left if sample['left_first'] else right).append(value)
                    all_left+=left;all_right+=right
                    blocks.append(abs(float(np.median(left)-np.median(right))))
                actual=abs(float(np.median(all_left)-np.median(all_right)))
                flagged=actual>bound or any(v>bound for v in blocks)
                clocks[clock]={'pooled_actual_start_order_log_difference':actual,'block_log_differences':blocks,
                               'sensitivity_flag':flagged,'left_start_pairs':len(all_left),'right_start_pairs':len(all_right)}
                warnings[split][clock][key[2]]+=int(flagged)
            details[split]['/'.join(key)]={'repetitions':raw['manifests'][key[0]]['repetitions'],**clocks}
    report={'scope':d['scope'],'declaration_sha256':sha(declaration),'control_tolerance':PROTOCOL['control_tolerance'],
            'warnings':warnings,'details':details,'labels_changed':False,'selection_changed':False,
            'limitations':'aggregate starting order only; individual micro-invocation timings cannot be reconstructed; equal-count batches can already balance both micro-orders'}
    save(output,report);print(json.dumps(warnings,indent=2))


if __name__=='__main__':main()
