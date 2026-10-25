"""Four display entries; identity-aware head-to-head demo ranking."""
import itertools
import math

LABELS = ('O1', 'O2', 'O3', 'NeuroCompiler')


def four_way_summary(options, aliases, controls, pairs):
    groups = {}
    for label, artifact in options.items():
        groups.setdefault(aliases[artifact], []).append(label)
    observations = {name:{c:[] for c in ('cpu','wall')} for name in groups}
    for record in [*({'left':k,'right':k,'cell':v} for k,v in controls.items()), *pairs]:
        for sample in record['cell']['samples']:
            for side, name in [('baseline',record['left']),('candidate',record['right'])]:
                for clock in ('cpu','wall'):
                    observations[name][clock].append(sample[side][clock])
    times = {name:{c:math.exp(sum(map(math.log,values))/len(values))*1000
                  for c,values in clocks.items()} for name,clocks in observations.items()}
    controls_ok = all(cell['qualified'] for cell in controls.values())
    expected = {frozenset(pair) for pair in itertools.combinations(groups,2)}
    coverage = {frozenset((p['left'],p['right'])) for p in pairs}
    complete = coverage == expected and len(pairs) == len(expected)
    pairs_ok = complete and all(p['cell']['qualified'] for p in pairs)
    winners = []
    if len(groups)>1 and controls_ok:
        for candidate in groups:
            if any(times[candidate][c] > min(t[c] for t in times.values()) for c in ('cpu','wall')):
                continue
            wins = True
            seen = set()
            for pair in pairs:
                if candidate not in (pair['left'],pair['right']):
                    continue
                seen.update((pair['left'],pair['right']))
                if not pair['cell']['qualified']:
                    wins = False; break
                for stat in pair['cell']['clocks'].values():
                    # Interval is left time / right time.
                    wins &= stat['interval'][1] < 1/1.03 if candidate == pair['left'] else stat['interval'][0] > 1.03
            if wins and complete and seen == set(groups):
                winners.append(candidate)
    winner = winners[0] if len(winners)==1 else None
    status = ('identical' if len(groups)==1 else 'reliable_winner' if winner else
              'no_clear_winner' if controls_ok and pairs_ok else 'inconclusive')
    clocks = {}
    for clock in ('cpu','wall'):
        fastest = min(times,key=lambda name:times[name][clock])
        nc = aliases[options['NeuroCompiler']]
        clocks[clock] = {
            'options':{label:{'artifact':artifact,'canonical':aliases[artifact],
                              'runtime_ms':times[aliases[artifact]][clock],
                              'same_as':[other for other in groups[aliases[artifact]] if other!=label],
                              'qualified':controls[aliases[artifact]]['qualified']}
                       for label,artifact in options.items()},
            'fastest_observed_options':groups[fastest],
            'observed_nc_gap_percent':(times[nc][clock]/times[fastest][clock]-1)*100,
        }
    return {'status':status,'winner_options':groups[winner] if winner else [],'clocks':clocks,
            'distinct_executables':len(groups),'controls_passed':controls_ok,
            'all_pairs_qualified':pairs_ok,'head_to_head_cells':len(pairs),
            'complete_pair_coverage':complete,
            'scope':'Fastest observed is an aggregate geometric-mean point estimate. A reliable demo winner must also pass self-controls and direct adjusted-interval comparisons against every distinct competitor on both clocks with speedup lower bounds above 1.03x. This is not a universal optimum or model validation.'}
