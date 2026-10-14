"""Describe qualification failures and scheduler observations, without filtering.

Scheduler steal is supporting context, not a causal proof or an exclusion rule.
This report never changes the declared gates, labels, selection or raw records.
"""
import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.benchmarks.region import ROOT,NAME,PROTOCOL,verify,save,sha


def reasons(s):
    tol=PROTOCOL['control_tolerance'];result=[]
    if any(not 1/(1+tol)<=x<=1+tol for x in s['blocks']):result.append('null_block_outside_bound')
    if s['interval'][0]<1/(1+tol) or s['interval'][1]>1+tol:result.append('null_interval_outside_bound')
    if s['order_log_difference']>math.log1p(tol):result.append('pooled_actual_order')
    if any(x>math.log1p(tol) for x in s['block_order_log_differences']):result.append('within_block_actual_order')
    return result


def main():
    output=ROOT/'results/region_timing_diagnosis.json'
    if output.exists():raise ValueError('Existing diagnosis')
    details={};scheduler={};coverage={};sources={}
    for split in ['train','development']:
        path=ROOT/f'results/{NAME}_{split}.json';raw=json.loads(path.read_text())
        if not raw['complete']:raise ValueError('Incomplete study')
        _,diagnostics=verify(raw);sources[split]=sha(path)
        coverage[split]={clock:{'baseline_pass':0,'candidate_targets_measured':0,'candidate_targets_qualified':0,
                                'confirmed_gains':0} for clock in ['cpu','wall']}
        details[split]={}
        for case,d in diagnostics.items():
            detail={'baseline':{},'candidates':{}}
            for clock,s in d['baseline_controls'].items():
                coverage[split][clock]['baseline_pass']+=s['control_pass']
                detail['baseline'][clock]={'pass':s['control_pass'],'failed_gates':reasons(s)}
            for candidate,measurement in d['measurements'].items():
                detail['candidates'][candidate]={}
                for clock,v in measurement.items():
                    s=v['effect'];c=coverage[split][clock]
                    c['candidate_targets_measured']+=1;c['candidate_targets_qualified']+=s['qualified'];c['confirmed_gains']+=s['confirmed_gain']
                    detail['candidates'][candidate][clock]={'qualified':s['qualified'],
                        'candidate_control_failures':reasons(v['control']),'effect_order_pass':s['order_pass']}
            details[split][case]=detail
        scheduler[split]={}
        for block in range(PROTOCOL['blocks']):
            cells=[row for row in raw['records'] if row['role']=='qualification' and row['block']==block]
            steal=[];ratio=[]
            for row in cells:
                ticks=row['scheduler_delta'];steal.append(ticks['steal']/max(sum(ticks.values()),1))
                ratio += [s[side]['wall_seconds']/s[side]['cpu_seconds'] for s in row['samples'] for side in ['left','right']]
            scheduler[split][str(block)]={'cells':len(cells),'median_observed_steal_fraction':float(np.median(steal)) if steal else None,
                                          'median_wall_cpu_ratio':float(np.median(ratio)) if ratio else None}
    report={'source_sha256':sources,'coverage':coverage,'baseline_scheduler_by_block':scheduler,'details':details,
            'labels_changed':False,'raw_samples_filtered':0,
            'limits':'Steal fractions use the recorded user/system/idle/steal tick subset and are approximate context. Correlation is not causal attribution. No failed control is retried or admitted.'}
    save(output,report);print(json.dumps({'coverage':coverage,'scheduler':scheduler},indent=2))


if __name__=='__main__':main()
