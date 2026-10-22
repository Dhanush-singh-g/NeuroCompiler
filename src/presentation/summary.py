"""Plain-language comparisons with a clear separation of identity and timing."""


def decision_diagnostics(scores, aliases, choice):
    distinct = [c for c in scores if c != 'O3' and aliases[c] == c]
    if not distinct:
        code = 'identical_menu'
        reason = 'All four pipelines produced the same executable. This menu offers no different code for NeuroCompiler to select.'
    elif choice == 'O3':
        code = 'baseline_preferred'
        reason = 'Different executables exist, but the model does not predict enough benefit to switch from O3.'
    else:
        code = 'alternative_selected'
        reason = 'The model selected a different executable before measuring runtime. Run the comparison to check that prediction.'
    return {'code': code, 'explanation': reason, 'distinct_executables': len(distinct)+1,
            'different_from_o3': aliases[choice] != 'O3'}


def failure_reasons(stat, control=False):
    reasons = []
    if min(stat['median_seconds'], stat['baseline_median_seconds']) < .01:
        reasons.append('Program is too short (under 10 ms). Increase actual work, not just the iterations descriptor.')
    if stat['coefficient_of_variation'] > .10:
        reasons.append('Repeated runtimes vary by more than 10%.')
    if not stat['order_ok']:
        reasons.append('Starting order changes the result by more than 3%.')
    if control and (stat['interval'][0] < 1/1.03 or stat['interval'][1] > 1.03
                    or any(not 1/1.03 <= b <= 1.03 for b in stat['block_ratios'])):
        reasons.append('Identical O3 runs differ beyond the 3% control bound.')
    return reasons


def comparison_summary(decision, cells):
    choice = decision['choice']
    same = decision['aliases'][choice] == 'O3'
    clocks = {}
    for clock in ('cpu', 'wall'):
        selected, baseline = cells[choice]['clocks'][clock], cells['O3']['clocks'][clock]
        qualified = cells['O3']['qualified'] and cells[choice]['qualified']
        ratio = 1. if same else selected['speedup']
        delta = (1/ratio-1)*100
        interval = [0., 0.] if same else [(1/selected['interval'][1]-1)*100,
                                                        (1/selected['interval'][0]-1)*100]
        if same:
            status, headline = 'unchanged', 'NeuroCompiler kept the O3 executable.'
        elif not qualified:
            status, headline = 'inconclusive', 'The measured difference is not reliable yet.'
        elif cells[choice]['verdict'] == 'faster_in_demo':
            status, headline = 'faster', f'NeuroCompiler used {-delta:.1f}% less time than O3 in this demo.'
        elif cells[choice]['verdict'] == 'slower_in_demo':
            status, headline = 'slower', f'NeuroCompiler used {delta:.1f}% more time than O3 in this demo.'
        else:
            status, headline = 'no_clear_difference', 'No clear performance difference from O3.'
        candidates = [(c, s['clocks'][clock]['speedup']) for c,s in cells.items()
                      if cells['O3']['qualified'] and s['qualified'] and not s.get('alias_of')]
        # Reference O3 is 1 by definition; its self-control ratio is noise,
        # never an improvement/regression of choosing the baseline itself.
        candidates = [(c, 1. if c == 'O3' else r) for c,r in candidates]
        best = max(candidates, key=lambda item:item[1]) if candidates else None
        reasons = [*failure_reasons(baseline, control=True),
                   *([] if same else failure_reasons(selected))]
        if not qualified and not reasons:
            reasons.append('The other clock failed quality checks; both clocks must pass.')
        clocks[clock] = {
            'preferred_choice': choice if status == 'faster' else 'O3' if status == 'slower' else None,
            'status': status, 'headline': headline, 'qualified': qualified,
            'same_executable': same, 'time_change_percent': delta,
            'time_change_interval_percent': interval, 'speedup': ratio,
            'baseline_ms': selected['baseline_geometric_seconds']*1000,
            'neurocompiler_ms': selected['candidate_geometric_seconds']*1000,
            'failure_reasons': list(dict.fromkeys(reasons)),
            'best_measured_choice': best[0] if best else None,
            'gap_to_best_percent': max(0., (best[1]/ratio-1)*100) if best and (same or qualified) else None,
            'scope': 'Best means fastest qualified point estimate in this tested menu, selected after timing; not the model prediction or a proven global optimum.',
        }
    return {'choice': choice, 'clocks': clocks}
