"""Independent arithmetic checks for the frozen instruction-count evidence.

Hashes establish consistency, not signatures or independent correctness proof.
No compilation, submitted-code execution, model selection, or retraining here.
"""
import hashlib
import json
import math
from pathlib import Path


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(condition,message):
    if not condition:raise ValueError('Evidence audit: '+message)


def close(actual,expected,message):
    require(math.isfinite(float(actual)) and math.isclose(actual,expected,rel_tol=1e-10,abs_tol=1e-12),message)


def summarize(results,label):
    families={r['family'] for r in results}
    ratios=[r['counts']['O3']/r['counts'][label] for r in results]
    grouped=[sum(math.log(r['counts']['O3']/r['counts'][label]) for r in results if r['family']==f)/
             sum(r['family']==f for r in results) for f in families]
    return {'fewer':sum(r['counts'][label]<r['counts']['O3'] for r in results),
            'equal':sum(r['counts'][label]==r['counts']['O3'] for r in results),
            'more':sum(r['counts'][label]>r['counts']['O3'] for r in results),
            'geomean_O3_over_candidate':math.exp(sum(map(math.log,ratios))/len(ratios)),
            'family_balanced_geomean_O3_over_candidate':math.exp(sum(grouped)/len(grouped))}


def audit(root,refit=False):
    root=Path(root);load=lambda name:json.loads((root/name).read_text())
    frozen=load('generalization_frozen.json');model=load('sequential_model.json')
    data=load('sequential_training.json');declaration=load('generalization_declaration.json')
    split=load('generalization_split.json');report=load('generalization_results.json')
    bindings={'model_sha256':'sequential_model.json','dataset_sha256':'sequential_training.json',
              'declaration_sha256':'generalization_declaration.json','split_sha256':'generalization_split.json'}
    for key,name in bindings.items():require(digest(root/name)==frozen[key],'Changed frozen artifact: '+name)
    require(data['declaration']==declaration,'Dataset declaration differs from the frozen declaration.')
    require(report['frozen']==frozen,'Evaluation uses another model/split.')
    require(digest(root/'sequential_evaluation.json')==report['evaluation_report_sha256'],'Original evaluation report changed.')
    original=load('sequential_evaluation.json')
    require(all(report[k]==original[k] for k in original),'Published report differs from original evaluation.')
    require(model['dataset_sha256']==frozen['dataset_sha256'] and model['context_id']==frozen['declaration_sha256'],
            'Model training context mismatch.')
    require(model['split_sha256']==frozen['split_sha256'],'Model split mismatch.')
    require(model['objective']==declaration['objective']=='instruction_count','Wrong reward objective.')
    for key in ('actions','feature_names','horizon'):require(model[key]==declaration[key],'Model/declaration '+key+' mismatch.')
    close(model['gamma'],declaration['learning']['gamma'],'Gamma mismatch.')
    programs={r['id']:r for r in split['programs']}
    require(len(programs)==len(split['programs']),'Duplicate source identifiers.')
    require(len({r['source_sha256'] for r in programs.values()})==len(programs),'Duplicate source hashes.')
    train={k:v for k,v in programs.items() if v['split']=='train'}
    test={k:v for k,v in programs.items() if v['split']=='test'}
    require(not {r['family'] for r in train.values()} & {r['family'] for r in test.values()},'Family leakage.')
    rows=data['rows'];require(len(rows)==model['training_rows'],'Training row count mismatch.')
    require(sorted({r['program'] for r in rows})==sorted(train)==model['training_programs'],'Training program coverage mismatch.')
    require(sorted({r['family'] for r in rows})==model['training_families'],'Training family count mismatch.')
    width=len(model['feature_names']);actions=list(model['actions'])
    for r in rows:
        source=train.get(r['program']);require(source is not None and r['split']=='train','Held-out/unknown training program.')
        require(r['family']==source['family'] and r['source_sha256']==source['source_sha256'],'Training source/family mismatch.')
        require(r['context_id']==model['context_id'] and r['objective']=='instruction_count','Mixed training context/objective.')
        require(r['transform_verified'] is True and r['native_semantic_validation'] is True,'Missing training checks.')
        require(r['correctness_inputs']==declaration['correctness_inputs'],'Wrong training correctness inputs.')
        require(r['action'] in actions and type(r['done']) is bool,'Unknown action/terminal marker.')
        for key in ('state','next_state'):
            require(len(r[key])==width and all(math.isfinite(v) for v in r[key]),'Invalid finite training features.')
        for key in ('before_instructions','after_instructions'):
            require(type(r[key]) is int and r[key]>=0,'Invalid instruction count.')
        close(r['state'][0],math.log1p(r['before_instructions']),'Before feature/count mismatch.')
        close(r['next_state'][0],math.log1p(r['after_instructions']),'After feature/count mismatch.')
        close(r['next_state'][-1],r['state'][-1]-1,'Transition does not consume one step.')
        expected_done=r['action']=='STOP' or r['next_state'][-1]==0
        require(r['done']==expected_done,'Horizon/STOP termination mismatch.')
        require(r['next_actions']==([] if expected_done else actions),'Wrong next-action mask.')
        for action in actions:
            index=model['feature_names'].index('count_'+action)
            close(r['next_state'][index],r['state'][index]+(r['action']==action),'Invalid action history transition.')
        reward=0 if r['action']=='STOP' else math.log((r['before_instructions']+1)/(r['after_instructions']+1))-.001
        close(r['reward'],reward,'Reward does not follow the declared count objective.')
    results=report['results']
    require(len(results)==len(test)==report['programs'],'Test count mismatch.')
    require({r['id'] for r in results}==set(test),'Missing/extra test programs.')
    require(len({r['family'] for r in results})==report['independent_families'],'Test family count mismatch.')
    labels=set(report['summary'])
    for r in results:
        source=test[r['id']]
        require(r['family']==source['family'] and r['source_sha256']==source['source_sha256'] and r['split']=='test','Test source/split mismatch.')
        require(r['inputs']==declaration['correctness_inputs'],'Wrong test inputs.')
        require(set(r['counts'])==labels==set(r['native_checks']),'Missing candidate/check coverage.')
        require(all(type(c) is int and c>0 for c in r['counts'].values()),'Invalid candidate counts.')
        require(all(v is True for v in r['native_checks'].values()),'Failed/missing reported native check.')
        for mode in ('sl','rl','hybrid'):
            seq=r['traces'][mode]
            require(seq['model_sha256']==frozen['model_sha256'] and seq['dataset_sha256']==frozen['dataset_sha256'],'Wrong rollout model/data.')
            require(seq['policy_final_instructions']==r['counts'][mode+'_raw'],'Raw policy count mismatch.')
            best=min(c['instructions'] for c in seq['checkpoints'])
            require(best==seq['best_policy_instructions'],'Checkpoint minimum mismatch.')
            expected=min(best,r['counts']['O3'])
            require(seq['final_instructions']==expected==r['counts'][mode+'_guarded'],'Guarded count mismatch.')
            require((seq['selection']['applied']=='O3')==(r['counts']['O3']<=best),'Guard tie/fallback rule mismatch.')
    require(report['all_output_checks_passed'] is True and report['runtime_evaluated'] is False,'Wrong evidence scope.')
    for label in labels:
        expected=summarize(results,label)
        for key,value in expected.items():close(report['summary'][label][key],value,'Incorrect aggregate '+label+'/'+key)
    for label,item in report['derived_controls'].items():
        baseline=label.removesuffix('_terminal_guarded')
        derived=[]
        for r in results:
            count=min(r['counts'][baseline],r['counts']['O3'])
            require(item['counts'][r['id']]==count,'Incorrect derived baseline count.')
            derived.append({**r,'counts':{**r['counts'],label:count}})
        expected=summarize(derived,label)
        for key,value in item['summary'].items():close(value,expected[key],'Incorrect derived aggregate '+label+'/'+key)
    if refit:
        from src.rl.offline import TransitionLearner
        import numpy as np
        params=declaration['learning']
        learner=TransitionLearner(actions,'instruction_count',gamma=params['gamma'],iterations=params['iterations'],ridge=params['ridge']).fit(rows)
        for key in ('center','scale'):
            require(np.allclose(getattr(learner,key),model[key],rtol=1e-10,atol=1e-12),'Refit '+key+' differs.')
        for key in ('immediate','q'):
            require(all(np.allclose(getattr(learner,key)[a],model[key][a],rtol=1e-10,atol=1e-12) for a in actions),'Refit '+key+' differs.')
    return {'status':'consistent','model_sha256':frozen['model_sha256'],'dataset_sha256':frozen['dataset_sha256'],
            'training_programs':len(train),'training_families':len(model['training_families']),
            'training_rows':len(rows),'test_programs':len(test),'test_families':report['independent_families'],
            'weights_refit_checked':bool(refit),
            'scope':'Checks frozen hashes, split/reward/feature consistency and report arithmetic. Does not independently prove native correctness, calibrated confidence, or runtime gains.'}
