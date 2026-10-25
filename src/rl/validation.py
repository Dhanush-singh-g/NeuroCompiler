"""Training-family cross-validation and advisory feature-range diagnostics.

None of these quantities is a calibrated confidence score or runtime estimate.
"""
import math
import numpy as np
from src.rl.offline import TransitionLearner


def range_profile(rows,model,digest):
    states=np.asarray([r['state'] for r in rows],dtype=float)
    return {'schema':1,'model_sha256':digest,'dataset_sha256':model['dataset_sha256'],
            'feature_names':model['feature_names'],'minimum':states.min(axis=0).tolist(),
            'maximum':states.max(axis=0).tolist(),'training_observations':len(states),
            'scope':'Observed training input-feature ranges only. Being within every range does not imply state/action coverage, calibrated confidence, or generalization.'}


def describe_support(features,profile):
    x=np.asarray(features,dtype=float);lo=np.asarray(profile['minimum']);hi=np.asarray(profile['maximum'])
    if x.shape!=lo.shape or hi.shape!=lo.shape or len(profile['feature_names'])!=len(x) or not all(np.isfinite(v).all() for v in (x,lo,hi)) or np.any(lo>hi):
        raise ValueError('Invalid training-range profile or input feature vector.')
    outside=[{'feature':profile['feature_names'][i],'value':float(x[i]),'minimum':float(lo[i]),'maximum':float(hi[i])}
             for i in range(len(x)) if x[i]<lo[i]-1e-9 or x[i]>hi[i]+1e-9]
    return {'status':'outside_training_ranges' if outside else 'within_training_ranges',
            'outside_fields':outside,'confidence_calibrated':False,'selection_changed':False,
            'scope':profile['scope']}


def family_validation(rows,actions,folds=4,seed=20261028):
    families=sorted({r['family'] for r in rows})
    if not 2<=folds<=len(families):raise ValueError('Need at least two family-disjoint folds.')
    ordered=list(np.random.default_rng(seed).permutation(families));reports=[];per_family={}
    for fold in range(folds):
        valid=set(ordered[fold::folds]);training=[r for r in rows if r['family'] not in valid]
        testing=[r for r in rows if r['family'] in valid]
        agent=TransitionLearner(actions,'instruction_count').fit(training)
        # Constant-action predictor uses training-family means, never validation labels.
        means={a:float(np.mean([np.mean([r['reward'] for r in training if r['family']==f and r['action']==a])
                              for f in families if f not in valid])) for a in actions}
        constant=max(actions,key=lambda a:means[a]);groups={}
        for row in testing:
            key=(row['program'],row['before_sha256'],tuple(row['state']))
            group=groups.setdefault(key,{'family':row['family'],'state':row['state'],'rewards':{}})
            old=group['rewards'].get(row['action'],row['reward'])
            if not math.isclose(old,row['reward'],abs_tol=1e-12):raise ValueError('Ambiguous repeated state/action reward.')
            group['rewards'][row['action']]=row['reward']
        for family in sorted(valid):
            observations=[g for g in groups.values() if g['family']==family]
            errors=[];mean_errors=[];zero_errors=[];regrets=[];constant_regrets=[];stop_regrets=[]
            for g in observations:
                if set(g['rewards'])!=set(actions):raise ValueError('Incomplete counterfactual action coverage.')
                decision=agent.choose(g['state'],'sl');truth=g['rewards'];best=max(truth.values())
                errors.extend(abs(decision['immediate_scores'][a]-truth[a]) for a in actions)
                mean_errors.extend(abs(means[a]-truth[a]) for a in actions)
                zero_errors.extend(abs(truth[a]) for a in actions)
                regrets.append(max(0.,best-truth[decision['action']]))
                constant_regrets.append(max(0.,best-truth[constant]));stop_regrets.append(max(0.,best-truth['STOP']))
            per_family[family]={'unique_probed_states':len(observations),'sl_mae':float(np.mean(errors)),
                'constant_reward_mae':float(np.mean(mean_errors)),'zero_reward_mae':float(np.mean(zero_errors)),
                'sl_mean_immediate_regret':float(np.mean(regrets)),
                'constant_action_mean_immediate_regret':float(np.mean(constant_regrets)),
                'stop_mean_immediate_regret':float(np.mean(stop_regrets)),
                'sl_tie_aware_best_action_fraction':float(np.mean(np.asarray(regrets)<1e-12)),
                'constant_tie_aware_best_action_fraction':float(np.mean(np.asarray(constant_regrets)<1e-12))}
        reports.append({'fold':fold,'training_families':sorted(set(families)-valid),'validation_families':sorted(valid),
                        'training_programs':sorted({r['program'] for r in training}),
                        'validation_programs':sorted({r['program'] for r in testing}),
                        'training_rows':len(training),'validation_rows':len(testing)})
    keys=[k for k in next(iter(per_family.values())) if k!='unique_probed_states']
    return {'folds':reports,'seed':seed,'families':len(families),'per_family':per_family,
            'family_balanced':{k:float(np.mean([f[k] for f in per_family.values()])) for k in keys},
            'scope':'Post-hoc diagnostic four-fold family-disjoint validation on training data, not a fresh final test or model-selection run. Identical state/action probes are collapsed. Metrics assess immediate SL rewards/actions, not long-term RL values, runtime or deployed-model confidence.'}


def family_interval(results,numerator,denominator,seed=20261029,draws=20000):
    """Exploratory percentile bootstrap over family means, never individual variants."""
    grouped=[]
    for family in sorted({r['family'] for r in results}):
        values=[math.log(r['counts'][numerator]/r['counts'][denominator]) for r in results if r['family']==family]
        grouped.append(float(np.mean(values)))
    data=np.asarray(grouped);rng=np.random.default_rng(seed)
    means=data[rng.integers(0,len(data),size=(draws,len(data)))].mean(axis=1)
    ratio=float(np.exp(data.mean()));interval=np.exp(np.quantile(means,[.025,.975]))
    return {'numerator':numerator,'denominator':denominator,'ratio':ratio,'interval95':interval.tolist(),
            'families':len(data),'seed':seed,'draws':draws,'method':'Family-cluster percentile bootstrap',
            'scope':'Exploratory, post-hoc, unadjusted interval from six authored families; not representative real-world sampling, runtime confidence, or confirmatory significance.'}
