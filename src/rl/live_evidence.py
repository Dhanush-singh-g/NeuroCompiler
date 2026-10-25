"""Validate the additional diagnostic artifacts before presenting their claims."""
import json
from pathlib import Path
from src.rl.evidence import audit,digest,require,close,summarize
from src.rl.validation import family_interval,range_profile

ROOT=Path(__file__).resolve().parents[2]


def audit_live(root=None):
    root=Path(root or ROOT/'presentation');load=lambda name:json.loads((root/name).read_text())
    base=audit(root);manifest=load('credibility_manifest.json')
    require(manifest['model_sha256']==base['model_sha256'],'Diagnostic manifest model mismatch.')
    for name,expected in manifest['artifacts'].items():
        require(Path(name).name==name,'Diagnostic manifest path must name a local artifact.')
        require(digest(root/name)==expected,'Changed diagnostic artifact: '+name)
    for declaration in ('generalization_declaration.json','validation_declaration.json','checkpoint_audit_declaration.json'):
        data=load(declaration)
        for name,expected in data['implementation_sha256'].items():
            require(digest(ROOT/name)==expected,'Declared implementation changed: '+name)
    validation=load('model_validation.json');profile=load('training_support.json')
    baseline=load('checkpoint_baseline_audit.json');weights=load('weights_audit.json')
    require(validation['declaration']==load('validation_declaration.json'),'Validation declaration mismatch.')
    for value in (validation['declaration'],profile,baseline,weights):
        require(value['model_sha256']==base['model_sha256'],'Diagnostic model mismatch.')
    require(weights['dataset_sha256']==base['dataset_sha256'] and weights['status']=='consistent','Coefficient replay context/status mismatch.')
    require(validation['declaration']['dataset_sha256']==base['dataset_sha256']==profile['dataset_sha256'],
            'Diagnostic dataset mismatch.')
    model=load('sequential_model.json');rows=load('sequential_training.json')['rows']
    require(profile==range_profile(rows,model,base['model_sha256']),'Training-range bounds do not match the dataset.')
    all_families=set(model['training_families']);seen=set()
    for fold in validation['folds']:
        train=set(fold['training_families']);valid=set(fold['validation_families'])
        require(not train&valid and train|valid==all_families,'Cross-validation family leakage/coverage error.')
        require(not seen&valid,'Repeated validation family.')
        require(not set(fold['training_programs'])&set(fold['validation_programs']),'Cross-validation program leakage.')
        seen.update(valid)
    require(seen==all_families==set(validation['per_family']),'Incomplete validation families.')
    for key,value in validation['family_balanced'].items():
        close(value,sum(f[key] for f in validation['per_family'].values())/len(all_families),'Wrong family-balanced validation '+key)
    original=load('generalization_results.json');require(baseline['source_report_sha256']==digest(root/'generalization_results.json'),
                                                       'Baseline audit uses another original evaluation.')
    require(baseline['runtime_evaluated'] is False,'Baseline audit is not a runtime study.')
    lookup={r['id']:r for r in original['results']};checks=0
    require(len(baseline['results'])==len(lookup),'Baseline audit program count mismatch.')
    for result in baseline['results']:
        previous=lookup[result['id']]
        require(result['family']==previous['family'],'Baseline audit family mismatch.')
        require(all(result['counts'][k]==v for k,v in previous['counts'].items()),'Original candidate counts changed.')
        require(set(result['additional_input_checks'])==set(result['counts']),'Missing expanded-input check coverage.')
        for method in ('fixed','random'):
            trace=result['baseline_checkpoints'][method]['checkpoint_counts']
            require(len(trace)==5 and trace[-1]==previous['counts'][method],'Incomplete baseline checkpoint sequence.')
            require(result['counts'][method+'_checkpoint_guarded']==min(*trace,result['counts']['O3']),
                    'Baseline guard did not use all checkpoints and O3.')
        for record in result['additional_input_checks'].values():
            inputs=record.get('inputs',record)
            require(set(inputs)==set(baseline['correctness_inputs']) and all(v is True for v in inputs.values()),
                    'Missing/failed expanded-input checks.')
            checks+=len(inputs)
    require(checks==baseline['candidate_output_checks'],'Expanded check count mismatch.')
    for label,values in baseline['summary'].items():
        expected=summarize(baseline['results'],label)
        for key,value in values.items():close(value,expected[key],'Wrong equal-checkpoint aggregate.')
    for label,interval in baseline['intervals'].items():
        expected=family_interval(baseline['results'],interval['numerator'],interval['denominator'],
                                 seed=interval['seed'],draws=interval['draws'])
        close(interval['ratio'],expected['ratio'],'Wrong family interval ratio.')
        for actual,want in zip(interval['interval95'],expected['interval95']):close(actual,want,'Wrong family bootstrap interval.')
    groups={}
    for row in rows:
        key=(row['family'],row['program'],row['before_sha256'],tuple(row['state']))
        groups.setdefault(key,{})[row['action']]=row['reward']
    stop_by_family={}
    for key,rewards in groups.items():
        stop_by_family.setdefault(key[0],[]).append(rewards['STOP']>=max(rewards.values())-1e-12)
    stop_fraction=sum(sum(v)/len(v) for v in stop_by_family.values())/len(stop_by_family)
    return {'integrity':base,'diagnostic_manifest_sha256':digest(root/'credibility_manifest.json'),
            'coefficient_refit_checked':weights['weights_refit_checked'],
            'validation':{'families':validation['families'],'folds':len(validation['folds']),
                          'family_balanced':validation['family_balanced'],'always_stop_best_immediate_fraction':stop_fraction,'scope':validation['scope']},
            'equal_checkpoint_baselines':baseline['summary'],'intervals':baseline['intervals'],
            'additional_correctness_inputs':baseline['correctness_inputs'],
            'additional_candidate_output_checks':checks,'runtime_evaluated':False,
            'scope':'Post-hoc diagnostics and integrity checks. No new final-test programs, no model retuning, no proven RL-specific or runtime advantage.'}
