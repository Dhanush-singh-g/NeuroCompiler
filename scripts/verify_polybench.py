"""Verify corpus, native outputs, frozen artifacts, and prior evidence."""
import copy
import hashlib
import json
import sys
import zipfile
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.benchmarks.polybench import ROOT,MENU,trial,verify
from src.benchmarks.compact import save,sha


def main():
    reports={split:json.loads((ROOT/f'results/polybench_{split}.json').read_text())
             for split in ['train','development']}
    labels,diagnostics=verify(reports['train'])
    verify(reports['development'])
    if reports['development']['records']:
        raise ValueError('This iteration freezes development timing until readiness')
    checks=0
    for raw in reports.values():
        for m in raw['manifests'].values():
            for choice in ['reference_O0',*MENU]:
                row=trial(m['artifacts'][choice]['elf'],1)
                if {k:row[k] for k in m['expected']}!=m['expected']:
                    raise ValueError('Independent native output verification failed')
                checks+=1
    bad=copy.deepcopy(reports['train'])
    first=next(iter(bad['diagnostics']))
    bad['diagnostics'][first]['outcomes']['O3']['speedup']=2.
    try:verify(bad)
    except ValueError:gain_tamper_rejected=True
    else:raise ValueError('Invented gain accepted')
    bad=copy.deepcopy(reports['train'])
    bad['records'][0]['left_trials'][0]['kernel_seconds']*=2
    try:verify(bad)
    except ValueError:timing_tamper_rejected=True
    else:raise ValueError('Tampered raw timing accepted')
    unchanged=0
    with zipfile.ZipFile(ROOT/'results/robust_iteration.zip') as archive:
        if archive.testzip():raise ValueError('Prior snapshot CRC mismatch')
        for name in archive.namelist():
            if not name.startswith(('results/','models/','data/')) or name.endswith('/'):
                continue
            path=ROOT/name
            if path.exists():
                if sha(path)!=hashlib.sha256(archive.read(name)).hexdigest():
                    raise ValueError(f'Prior generated evidence changed: {name}')
                unchanged+=1
    result={'training_correct_programs':len(reports['train']['manifests']),
            'development_correct_programs':len(reports['development']['manifests']),
            'accepted_new_training_programs':len(labels),'native_output_checks':checks,
            'reported_gain_tamper_rejected':gain_tamper_rejected,
            'raw_timing_tamper_rejected':timing_tamper_rejected,
            'prior_generated_artifacts_unchanged':unchanged,
            'reserved_test_programs':2,'reserved_test_executions':0,
            'source_sha256':{split:sha(ROOT/f'results/polybench_{split}.json') for split in reports}}
    output=ROOT/'results/polybench_verification.json'
    if output.exists():raise ValueError('Existing verification; refusing overwrite')
    save(output,result)
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
