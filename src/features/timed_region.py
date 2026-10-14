"""Static CFG analysis of library work between external timer calls.

Direct callees of active instructions contribute their entire bodies. This is
not dynamic hotness: cold/error paths remain, and indirect targets are unknown.
Instructions reachable both inside and outside the interval are excluded from
the lower-bound counts and reported explicitly. Block order is immaterial.
"""
import re
from collections import Counter

import networkx as nx
import numpy as np

from src.features.transform import METRICS, OPS, NAME, FUNCTION, LABEL, TARGET, DIRECT, parse_ir, aggregate

GROUPS = {
    'load': {'load', 'atomicrmw', 'cmpxchg'}, 'store': {'store', 'atomicrmw', 'cmpxchg'},
    'call': {'call', 'invoke', 'callbr'}, 'phi': {'phi'}, 'branch': {'br', 'switch', 'indirectbr'},
    'compare': {'icmp', 'fcmp'}, 'integer': {'add', 'sub', 'mul', 'and', 'or', 'xor'},
    'floating': {'fadd', 'fsub', 'fmul', 'fdiv', 'frem', 'fneg'},
    'divide': {'udiv', 'sdiv', 'fdiv', 'urem', 'srem', 'frem'}, 'shift': {'shl', 'lshr', 'ashr'},
    'gep': {'getelementptr'}, 'select': {'select'},
    'cast': set('trunc zext sext fptrunc fpext fptoui fptosi uitofp sitofp ptrtoint inttoptr bitcast addrspacecast'.split()),
}
START, STOP = 'polybench_timer_start', 'polybench_timer_stop'


def analyze(text, entrypoint='nc_benchmark_main'):
    functions = parse_ir(text)
    if entrypoint not in functions:
        raise ValueError('Missing timed entrypoint')
    blocks, current, reading = {}, None, False
    for raw in text.splitlines():
        line = raw.strip()
        match = FUNCTION.match(line)
        if match:
            reading = match.group(1) == entrypoint
            if reading:
                current = '__entry__'; blocks[current] = []
            continue
        if line == '}': reading = False
        if not reading: continue
        match = LABEL.match(line)
        if match:
            if current == '__entry__' and not blocks[current]: blocks.pop(current)
            current = match.group(1); blocks.setdefault(current, [])
            continue
        instruction = re.sub(r'^%' + NAME + r'\s*=\s*', '', line)
        words = instruction.split()
        while words and words[0] in ('tail', 'musttail', 'notail'): words.pop(0)
        if words and words[0] in OPS:
            op = words[0]; direct = DIRECT.findall(instruction) if op in GROUPS['call'] else []
            blocks[current].append((op, instruction, direct[0] if direct else None))
    markers = [item[2] for items in blocks.values() for item in items]
    if START not in markers or STOP not in markers:
        raise ValueError('Missing timer boundaries; refuse whole-function fallback')
    edges = functions[entrypoint]['edges']
    successors = {b: {y for x, y in edges if x == b} for b in blocks}
    pending, visited, states = [(next(iter(blocks)), False)], set(), {}
    while pending:
        block, active = pending.pop()
        if (block, active) in visited: continue
        visited.add((block, active))
        for i, (_, _, call) in enumerate(blocks[block]):
            if call == START: active = True; continue
            if call == STOP: active = False; continue
            states.setdefault((block, i), set()).add(active)
        pending.extend((target, active) for target in successors[block])
    counts, active_blocks, calls = Counter(), Counter(), set()
    ambiguous = 0
    for (block, i), phases in states.items():
        ambiguous += len(phases) > 1
        if phases != {True}: continue
        op, instruction, call = blocks[block][i]
        counts['instructions'] += 1; active_blocks[block] += 1
        for metric, members in GROUPS.items(): counts[metric] += op in members
        counts['vector'] += bool(re.search(r'<\d+ x ', instruction))
        if op in GROUPS['call']:
            if call: calls.add(call)
            elif 'asm ' not in instruction: counts['indirect_call'] += 1
    graph = nx.DiGraph(); graph.add_nodes_from(active_blocks)
    graph.add_edges_from((x, y) for x, y in edges if x in active_blocks and y in active_blocks)
    cyclic = [s for s in nx.strongly_connected_components(graph)
              if len(s) > 1 or any(graph.has_edge(n, n) for n in s)]
    nodes = set().union(*cyclic) if cyclic else set()
    counts.update(blocks=len(graph), edges=len(graph.edges), cyclic_regions=len(cyclic),
                  cyclic_blocks=len(nodes), cyclic_instructions=sum(active_blocks[b] for b in nodes))
    reachable, pending = set(), list(calls)
    indirect = bool(counts['indirect_call'])
    while pending:
        name = pending.pop()
        if name == entrypoint: raise ValueError('Recursive timed entrypoint unsupported')
        if name not in functions or name in reachable: continue
        reachable.add(name); f = functions[name]
        indirect |= bool(f['counts']['indirect_call']); pending.extend(f['calls'])
    entry = np.asarray([counts[m] for m in METRICS], dtype=float)
    closure = entry + aggregate(functions, reachable)
    if not counts['instructions']: raise ValueError('Empty timed region')
    return {'entry': entry.tolist(), 'closure': closure.tolist(), 'direct_callees': sorted(calls),
            'reachable_functions': sorted(reachable), 'indirect_lower_bound': indirect,
            'ambiguous_instructions': ambiguous}


FEATURE_NAMES = ([f'o3_{s}_{m}' for s in ['timed_entry', 'timed_closure'] for m in METRICS]
                 + [f'delta_{s}_{m}' for s in ['timed_entry', 'timed_closure'] for m in METRICS]
                 + ['o3_indirect_lower_bound', 'candidate_indirect_lower_bound',
                    'o3_log_ambiguous_instructions', 'candidate_log_ambiguous_instructions'])


def vector(base, candidate):
    a = np.asarray(base['entry'] + base['closure']); b = np.asarray(candidate['entry'] + candidate['closure'])
    values = np.concatenate([np.log1p(a), (b-a)/(a+1),
                             [float(base['indirect_lower_bound']), float(candidate['indirect_lower_bound']),
                              np.log1p(base['ambiguous_instructions']), np.log1p(candidate['ambiguous_instructions'])]])
    if values.shape != (len(FEATURE_NAMES),) or not np.isfinite(values).all():
        raise ValueError('Invalid timed-region features')
    return values.tolist()
