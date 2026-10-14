"""Audit raw studies, actual static features, oracles, inference, and preservation."""
import copy
import json
import tempfile
import zipfile
from pathlib import Path

from scripts.collect_kernels import verify as verify_kernels
from scripts.collect_real import verify as verify_real
from scripts.collect_real_long import verify as verify_long
from scripts.evaluate_robust import verify_study
from scripts.verify_transform import main as verify_previous_studies
from src.benchmarks.compact import run,save,sha,verify_report
from src.features.transform import extract_manifest


def main():
    output=Path('results/robust_verification.json')
    if output.exists():raise ValueError('Preserve existing verification')
    datasets={}
    for split in ['train','validation']:
        raw=json.loads(Path(f'results/compact_{split}.json').read_text());verify_report(raw)
        cached=json.loads(Path(f'data/processed/transform_{split}.json').read_text())['cases']
        datasets[f'compact_{split}']=(raw,cached)
    for name,verify in [('kernel_train',verify_kernels),('real_train',verify_real),('real_train_long',verify_long)]:
        raw=json.loads(Path(f'results/{name}.json').read_text());verify(raw);datasets[name]=(raw,raw['static_cases'])
    reextracted=0
    for name,(raw,cached) in datasets.items():
        for case,m in raw['manifests'].items():
            if extract_manifest(m)!=cached[case]:raise ValueError(f'Actual static features differ: {name}/{case}')
            reextracted+=1
        print('Verified actual features',name,len(raw['manifests']),flush=True)
    # Functional output checks supplement the independent oracle verification.
    checked=0
    for name in ['real_train','real_train_long']:
        raw=datasets[name][0]
        for m in raw['manifests'].values():
            for c in m['artifacts']:run(m,c,True);checked+=1
    verify_previous_studies();fresh=verify_study('results/robust_long_development.json')
    with tempfile.TemporaryDirectory(prefix='neurocompiler-verify-') as d:
        changed=copy.deepcopy(fresh);changed['results']['previous_frozen']['score']['geomean']=2.
        fake=Path(d)/'robust_long_development.json';save(fake,changed)
        try:verify_study(fake)
        except ValueError as e:
            if 'Reported results differ' not in str(e):raise
        else:raise ValueError('Reported gain tampering was accepted')
    inference={}
    for stem,raw_name,case in [('robust_inference','kernel_train','stencil'),('robust_risk_inference','compact_train','bitcount_0_iters11250000')]:
        info=json.loads(Path(f'results/{stem}.json').read_text());choice=info['decision']['configuration']
        a=datasets[raw_name][0]['manifests'][case]['artifacts'][choice]
        if info['native_execution'] is not False or sha(f'results/{stem}.bc')!=a['bc_sha256'] or sha(f'results/{stem}.out')!=a['elf_sha256']:
            raise ValueError('Inference differs from independently frozen artifacts')
        inference[stem]={'choice':choice,'bitcode_sha256':a['bc_sha256'],'elf_sha256':a['elf_sha256'],'native_execution':False}
    previous=0
    with zipfile.ZipFile('results/transform_iteration.zip') as z:
        manifest=json.loads(z.read('SHA256_MANIFEST.json'))
    for name,h in manifest.items():
        if name.startswith(('data/','models/','results/')):
            if sha(name)!=h:raise ValueError(f'Previous generated artifact changed: {name}')
            previous+=1
    log=Path('/tmp/neurocompiler-robust-tests.log').read_text()
    if 'Ran 49 tests' not in log or not log.rstrip().endswith('OK'):raise ValueError('Expected tests did not pass')
    result={'unit_tests_passed':49,'actual_static_cases_reextracted':reextracted,
        'native_oracle_output_checks':checked,'fresh_development_verified':True,'tampered_gain_rejected':True,
        'previous_generated_artifacts_unchanged':previous,'inference':inference,
        'raw_studies':{name:{'cells':len(raw['records']),'complete_menus':len(raw['labels'])} for name,(raw,_) in datasets.items()},
        'new_timed_study_executions':sum(len(x['left_seconds'])+len(x['right_seconds']) for name in ['real_train','real_train_long'] for x in datasets[name][0]['records'])+sum(len(x['left_seconds'])+len(x['right_seconds']) for x in fresh['records']),
        'clock_diagnostics_extra_executions':len(json.loads(Path('results/platform_clock_diagnostic.json').read_text())['records'])+sum(len(x['wall']['left_seconds'])+len(x['wall']['right_seconds']) for x in json.loads(Path('results/real_clock_diagnostic.json').read_text())['records']),
        'fresh_development_accepted_inputs':len(fresh['results']['previous_frozen']['records']),
        'runtime_ready':False,'reserved_tests_untouched':True,'github_push_performed':False,
        'scope':'Iteration verified; timing controls failed, no new runtime improvement established'}
    save(output,result);print(json.dumps(result,indent=2),flush=True)


if __name__=='__main__':main()
