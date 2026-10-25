"""Post-hoc equal-checkpoint baseline and expanded-input correctness audit.

Reads retained artifacts from the already-opened synthetic evaluation. This is
not a new untouched-program test, and never trains or changes the model.
"""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.rl.evidence import audit,digest,summarize
from src.rl.validation import family_interval
from src.presentation.server import toolchain
from src.presentation.worker import command,save
from src.features.transform import parse_ir,aggregate
from src.hybrid.sequential import select_checkpoint
from train_generalization import native_output
ROOT=Path(__file__).resolve().parents[1]
INPUTS=['0','2','7','11','31']


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--artifacts',type=Path,required=True,help='Retained evaluation directory from the frozen run.')
    p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    if args.output.exists():p.error('Use a fresh output directory; no overwrites.')
    integrity=audit(ROOT/'presentation');config=toolchain();tools=Path(config['llvm_bin'])
    model=json.loads((ROOT/'presentation/sequential_model.json').read_text())
    if model['toolchain_sha256']!=config['toolchain_sha256']:raise ValueError('Compiler context changed.')
    original=json.loads((ROOT/'presentation/generalization_results.json').read_text())
    args.output.mkdir(parents=True)
    save(args.output/'declaration.json',{'model_sha256':integrity['model_sha256'],
      'source_report_sha256':digest(ROOT/'presentation/generalization_results.json'),
      'correctness_inputs':INPUTS,'checkpoint_rule':'All five states (initial and four transforms) plus O3, O3 wins ties.',
      'model_or_hyperparameter_changes':False,
      'implementation_sha256':{name:digest(ROOT/name) for name in ('scripts/audit_checkpoint_baselines.py','src/rl/validation.py','src/rl/evidence.py')},
      'scope':'Post-hoc audit of already-opened examples; no new unseen-program or runtime study.'})
    results=[];checks=0
    def count(path):
        return int(aggregate(parse_ir(command([tools/'llvm-dis',path,'-o','-'],ROOT)),
                             parse_ir(command([tools/'llvm-dis',path,'-o','-'],ROOT)))[0])
    for row in original['results']:
        source=args.artifacts/row['id'];directory=args.output/row['id'];directory.mkdir()
        if digest(source/'source.c')!=row['source_sha256']:raise ValueError('Retained source changed.')
        if count(source/'O3.bc')!=row['counts']['O3']:raise ValueError('Retained O3 count changed.')
        expected={arg:native_output(source/'gcc-reference',arg) for arg in INPUTS}
        if any(native_output(source/'clang-reference',arg)!=expected[arg] for arg in INPUTS):raise ValueError('Reference mismatch.')
        additional={};details={};native={}
        for method in ('fixed','random'):
            checkpoints=[{'path':source/method/f'state{i}.bc','instructions':count(source/method/f'state{i}.bc'),
                          'actions':row['traces'][method][:i],'step':i} for i in range(5)]
            if checkpoints[-1]['instructions']!=row['counts'][method]:raise ValueError('Retained terminal count changed.')
            selected=select_checkpoint(checkpoints,{'path':source/'O3.bc','instructions':row['counts']['O3'],'step':0})
            label=method+'_checkpoint_guarded';exe=directory/label
            command([tools/'clang',selected['path'],'-O3','-Xclang','-disable-llvm-passes','-lm','-o',exe],ROOT)
            passed={arg:native_output(exe,arg)==expected[arg] for arg in INPUTS};checks+=len(passed)
            if not all(passed.values()):raise ValueError('Checkpoint output mismatch: '+row['id']+'/'+method)
            additional[label]=selected['instructions'];native[label]=passed
            details[method]={'checkpoint_counts':[c['instructions'] for c in checkpoints],
                             'selected_step':selected['step'],'selected_kind':selected['applied'],
                             'bitcode_sha256':digest(selected['path']),'executable_sha256':digest(exe)}
        for label in row['counts']:
            exe=source/('program_'+label)
            passed={arg:native_output(exe,arg)==expected[arg] for arg in INPUTS};checks+=len(passed)
            if not all(passed.values()):raise ValueError('Additional input mismatch: '+row['id']+'/'+label)
            native[label]={'inputs':passed,'executable_sha256':digest(exe)}
        results.append({'id':row['id'],'family':row['family'],'counts':{**row['counts'],**additional},
                        'baseline_checkpoints':details,'additional_input_checks':native})
        print(row['id'],additional,'expanded checks passed',flush=True)
    summary={label:summarize(results,label) for label in ('fixed_checkpoint_guarded','random_checkpoint_guarded')}
    report={'schema':1,'model_sha256':integrity['model_sha256'],'source_report_sha256':digest(ROOT/'presentation/generalization_results.json'),
            'results':results,'summary':summary,'candidate_output_checks':checks,'correctness_inputs':INPUTS,
            'intervals':{'hybrid_vs_O3':family_interval(results,'O3','hybrid_guarded'),
                         'hybrid_vs_fixed_equal_guard':family_interval(results,'fixed_checkpoint_guarded','hybrid_guarded')},
            'runtime_evaluated':False,
            'scope':'Post-hoc audit on the same six authored families. Equal checkpoint guards isolate deterministic selection from learning. Additional input checks are not semantic proof. Intervals are exploratory family-cluster estimates, not confirmatory runtime or real-world evidence.'}
    save(args.output/'report.json',report)
    print(json.dumps({'summary':summary,'intervals':report['intervals'],'candidate_output_checks':checks},indent=2))

if __name__=='__main__':main()
