"""Replay the descriptive secondary order diagnostic without new timings."""
import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.benchmarks.broad import ROOT,sha,save


def main():
    source=ROOT/'results/broad_isolated_confirmation.json';s=json.loads(source.read_text());result={}
    for clock in ['cpu','wall']:
        result[clock]={}
        for role in ['qualification','candidate_control','effect']:
            rows=[r for r in s['records'] if r['role']==role]
            blocks=[];all_left=[];all_right=[]
            for row in rows:
                left=[];right=[]
                for sample in row['samples']:
                    value=math.log(sample['left'][clock+'_seconds']/sample['right'][clock+'_seconds'])
                    (left if sample['left_first'] else right).append(value)
                blocks.append(abs(float(np.median(left)-np.median(right))));all_left+=left;all_right+=right
            pooled=abs(float(np.median(all_left)-np.median(all_right)))
            result[clock][role]={'block_actual_start_order_log_differences':blocks,
                                'pooled_actual_start_order_log_difference':pooled,
                                'sensitivity_flag':bool(pooled>math.log1p(.03) or any(x>math.log1p(.03) for x in blocks))}
    report={'scope':'additional descriptive secondary aggregate-start-order diagnostic; no labels or selection changed',
            'secondary_sha256':sha(source),'details':result}
    path=ROOT/'results/broad_secondary_order_diagnostic.json'
    if path.exists():
        if json.loads(path.read_text())!=report:raise ValueError('Secondary order diagnostic changed')
    else:save(path,report)
    print('Verified descriptive secondary order diagnostic; no new timings')


if __name__=='__main__':main()
