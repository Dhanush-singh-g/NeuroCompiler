"""Independent native correctness, changed-evidence rejection, prior-data audit."""
import copy
import hashlib
import json
import sys
import zipfile
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.benchmarks.compact import save,sha
from src.benchmarks.invocation import ROOT,NAME,MENU,verify,run_cell


def main():
    out=ROOT/f'results/{NAME}_verification.json'
    if out.exists():raise ValueError('Existing verification; refusing overwrite')
    raw={split:json.loads((ROOT/f'results/{NAME}_{split}.json').read_text()) for split in ['train','development']}
    for r in raw.values():
        if not r['complete']:raise ValueError('Incomplete experiment')
        verify(r)
    native=0
    for r in raw.values():
        for m in r['manifests'].values():
            for c in MENU:run_cell(m,'reference_O0',c,0,'audit',pairs=1,repetitions=1);native+=1
    rejected={}
    for name,mutate in {
        'invocation_order':lambda r:r['records'][0]['samples'][0].update({'left_first_invocations':99999}),
        'reported_gain':lambda r:next(iter(r['diagnostics'].values()))['baseline_controls']['cpu'].update({'speedup':2.}),
        'input_features':lambda r:next(iter(next(iter(r['manifests'].values()))['features'].values())).__setitem__(-1,999.),
        'variant_artifact':lambda r:r['manifests'][list(r['manifests'])[1]]['artifacts']['O3'].update({'so_sha256':'bad'})
    }.items():
        bad=copy.deepcopy(raw['train']);mutate(bad)
        try:verify(bad)
        except ValueError:rejected[name]=True
        else:raise ValueError('Corruption accepted '+name)
    preserved=0
    with zipfile.ZipFile(ROOT/'results/paired_iteration.zip') as archive:
        if archive.testzip():raise ValueError('Previous archive CRC failure')
        for name in archive.namelist():
            if name.endswith('/') or not name.startswith(('results/','models/','data/')):continue
            path=ROOT/name
            if not path.is_file() or sha(path)!=hashlib.sha256(archive.read(name)).hexdigest():raise ValueError('Previous evidence changed '+name)
            preserved+=1
    report={'native_O0_candidate_comparisons':native,'tamper_rejected':rejected,
            'prior_generated_artifacts_unchanged':preserved,'reserved_test_executions':0,
            'source_sha256':{split:sha(ROOT/f'results/{NAME}_{split}.json') for split in raw}}
    save(out,report);print(json.dumps(report,indent=2))


if __name__=='__main__':main()
