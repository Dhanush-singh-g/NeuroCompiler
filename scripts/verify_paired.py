"""Audit both clock studies, native transformations, and immutable prior data."""
import argparse
import copy
import hashlib
import json
import sys
import zipfile
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.benchmarks.compact import save,sha
from src.benchmarks.polybench import ROOT,experiment_name
from src.benchmarks.paired import MENU,run_cell,verify


def main():
    p=argparse.ArgumentParser();p.add_argument('--name',default='paired_native_20261011',type=experiment_name)
    args=p.parse_args();reports={s:json.loads((ROOT/f'results/{args.name}_{s}.json').read_text())
                              for s in ['train','development']}
    for r in reports.values():
        if not r['complete']:raise ValueError('Incomplete experiment')
        verify(r)
    native=0
    for report in reports.values():
        for m in report['manifests'].values():
            for c in MENU:
                run_cell(m,'reference_O0',c,0,'verification',pairs=1,repetitions=1);native+=1
    tests={}
    for name,mutate in {
        'pair_order':lambda r:r['records'][0]['samples'][0].update({'left_first':not r['records'][0]['samples'][0]['left_first']}),
        'reported_gain':lambda r:next(iter(r['diagnostics'].values()))['cpu_control'].update({'speedup':2.}),
        'static_features':lambda r:next(iter(next(iter(r['manifests'].values()))['features'].values())).__setitem__(0,999999.)
    }.items():
        bad=copy.deepcopy(reports['train']);mutate(bad)
        try:verify(bad)
        except ValueError:tests[name]=True
        else:raise ValueError('Corruption accepted: '+name)
    preserved=0;creation_logs={}
    prior=ROOT/'results/polybench_iteration.zip'
    with zipfile.ZipFile(prior) as archive:
        if archive.testzip():raise ValueError('Prior snapshot CRC failure')
        for name in archive.namelist():
            if not name.startswith(('results/','models/','data/')) or name.endswith('/'):continue
            path=ROOT/name
            if not path.is_file():raise ValueError('Prior evidence missing: '+name)
            original=archive.read(name)
            if sha(path)!=hashlib.sha256(original).hexdigest():
                # The old snapshot captured its redirected stdout while empty.
                # Validate its later completion report against the actual archive;
                # do not alter either file or exempt any measurement/model data.
                if name!='results/polybench_snapshot.log' or original!=b'':
                    raise ValueError('Prior evidence changed: '+name)
                expected={'files':len(json.loads(archive.read('snapshot_manifest.json'))['sha256']),
                          'bytes':prior.stat().st_size,'sha256':sha(prior)}
                if json.loads(path.read_text())!=expected:raise ValueError('Invalid prior snapshot completion log')
                creation_logs[name]={'archived_empty':True,'completion_report_verified':expected}
            else:preserved+=1
    result={'native_O0_candidate_comparisons':native,'tamper_rejected':tests,
            'prior_generated_artifacts_unchanged':preserved,'reserved_test_executions':0,
            'prior_archive_creation_logs':creation_logs,
            'studies_sha256':{s:sha(ROOT/f'results/{args.name}_{s}.json') for s in reports}}
    output=ROOT/f'results/{args.name}_verification.json'
    if output.exists():raise ValueError('Existing verification; refusing overwrite')
    save(output,result);print(json.dumps(result,indent=2))


if __name__=='__main__':main()
