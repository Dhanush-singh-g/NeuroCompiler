"""Descriptive session counts, never research accuracy or held-out evaluation."""
import hashlib
import json

OUTCOMES = ('wins', 'losses', 'unchanged', 'no_clear_difference', 'inconclusive', 'blocked')


def session_scorecard(results, examples):
    known = {hashlib.sha256(e['source'].encode()).hexdigest():
             ('training_example' if e['id'] == 'sieve' else 'bundled_demo') for e in examples}
    groups = {name: {'inputs': 0, 'kept_o3': 0, 'changed_choice': 0,
                     'tested': 0, **dict.fromkeys(OUTCOMES, 0), 'unqualified_timings': 0}
              for name in ('training_example', 'bundled_demo', 'custom')}
    ranking_keys = ('best_O1','best_O2','best_O3','best_NeuroCompiler','best_shared',
                    'four_way_inconclusive','four_way_no_clear','four_way_identical')
    for group in groups.values():
        group.update(dict.fromkeys(ranking_keys,0))
    analyses, comparisons = {}, {}
    sources = set()
    for result in results:
        sources.add(result['source_sha256'])
        # Include model version; never combine different learned policies.
        key = json.dumps([result['input'], result['decision']['model_sha256']], sort_keys=True)
        if result['kind'] == 'analysis':
            analyses[key] = result
        elif result['kind'] == 'comparison':
            comparisons[key] = result
    for key, result in analyses.items():
        group = groups[known.get(result['source_sha256'], 'custom')]
        group['inputs'] += 1
        same = result['decision']['aliases'][result['decision']['choice']] == 'O3'
        group['kept_o3' if same else 'changed_choice'] += 1
        compared = comparisons.get(key)
        if not compared:
            continue
        group['tested'] += 1
        measurement = compared['measurement']
        if measurement['status'] == 'blocked':
            group['blocked'] += 1
            continue
        ranking = measurement.get('four_way')
        if ranking:
            if (ranking['status'] == 'reliable_winner' and ranking.get('controls_passed')
                    and ranking.get('complete_pair_coverage') and ranking['winner_options']):
                names = ranking['winner_options']
                group['best_'+names[0] if len(names)==1 else 'best_shared'] += 1
            else:
                key = {'reliable_winner':'four_way_inconclusive','inconclusive':'four_way_inconclusive','no_clear_winner':'four_way_no_clear',
                       'identical':'four_way_identical'}[ranking['status']]
                group[key] += 1
        clocks = measurement['summary']['clocks']
        qualified = all(clocks[c]['qualified'] for c in ('cpu', 'wall'))
        statuses = {clocks[c]['status'] for c in ('cpu', 'wall')}
        if not qualified:
            group['unqualified_timings'] += 1
        status = next(iter(statuses)) if len(statuses) == 1 else 'inconclusive'
        if not qualified and status != 'unchanged':
            status = 'inconclusive'
        outcome = {'faster':'wins', 'slower':'losses', 'unchanged':'unchanged',
                   'no_clear_difference':'no_clear_difference', 'inconclusive':'inconclusive'}[status]
        group[outcome] += 1
    totals = {key: sum(group[key] for group in groups.values()) for key in next(iter(groups.values()))}
    return {'schema':1, 'totals':totals, 'groups':groups, 'source_files':len(sources),
            'scope':'Current server session only. Repeats of an identical input/model/policy count once; the last completed comparison is used. Different arguments/stdin or learning modes are separate evaluations, not independent programs. Outcomes are demo observations, not accuracy or generalization.',
            'provenance_note':'Training example means the known bundled sieve source. Custom means unverified provenance, not a guaranteed unseen program. Other training-derived custom code is not automatically detected.',
            'quality_note':'Unchanged means identical O3 code, regardless of timing quality. Failed timing checks are also counted separately. Failed/cancelled workers are excluded; blocked completed correctness checks are included.'}
