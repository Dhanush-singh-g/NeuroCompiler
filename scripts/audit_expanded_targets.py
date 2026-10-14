"""Independent seed/order replay of the fixed logical-CPU screen."""
import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import screen_expanded_targets as screen
from scripts.audit_expanded import actual_order
from src.benchmarks.compact import save, sha


def main():
    output = screen.e.ROOT/'results/expanded_target_verification.json'
    if output.exists(): raise ValueError('Existing screen audit')
    declaration, base = screen.check(); raw = json.loads(screen.OUT.read_text()); confirmation = json.loads(screen.CONFIRM.read_text())
    screen.verify(raw); screen.verify(confirmation, True)
    if not raw['complete'] or not confirmation['complete']: raise ValueError('Incomplete screen')
    m = json.loads((base/'preflight.json').read_text())['manifests']; groups = 0; rows_checked = 0
    for result, confirm in [(raw, False), (confirmation, True)]:
        for row in result['records']:
            value = screen.SEED + row['target_cpu']*1000 + int(confirm)*100
            value += int(hashlib.sha256(f'{row["case"]}:micro:{row["block"]}:O3:O3'.encode()).hexdigest()[:8], 16)
            if row['first'] != bool(np.random.default_rng(value).integers(2)): raise ValueError('Declared target seed differs')
            rows_checked += 1
        for cpu, target in result['summary']['targets'].items():
            for case, stats in target['statistics'].items():
                rows = [r for r in result['records'] if r['target_cpu'] == int(cpu) and r['case'] == case]
                for clock, s in stats.items(): actual_order(rows, s, clock); groups += 1
    rejected = {}
    mutations = {'wrong_cpu': lambda r: r['records'][0].update(target_cpu=2),
                 'missing_pair': lambda r: r['records'][0]['samples'].pop(),
                 'missing_trace': lambda r: r['records'][0]['samples'][0]['clock_trace'].pop(),
                 'false_selection': lambda r: r['summary'].update(selected_cpu=2),
                 'clock_tamper': lambda r: r['records'][0]['samples'][0]['right'].update(cpu_seconds=9.)}
    for name, change in mutations.items():
        bad = copy.deepcopy(raw); change(bad)
        with patch.object(screen, 'check', return_value=(declaration, base)):
            try: screen.verify(bad)
            except (ValueError, TypeError): rejected[name] = True
            else: raise ValueError('Corrupt screen accepted: '+name)
    hashes = {'screen': sha(screen.OUT), 'confirmation': sha(screen.CONFIRM), 'original_failed_gate': sha(base/'gate.json')}
    for flags in [[], ['--confirmation']]:
        subprocess.run([sys.executable, str(screen.e.ROOT/'scripts/screen_expanded_targets.py'), *flags, '--resume'], check=True)
    if hashes != {'screen': sha(screen.OUT), 'confirmation': sha(screen.CONFIRM), 'original_failed_gate': sha(base/'gate.json')}:
        raise ValueError('Completed checks changed evidence')
    save(output, {'native_null_cells': rows_checked, 'independent_actual_order_groups': groups, 'declared_seeds_checked': rows_checked,
                  'tamper_rejected': rejected, 'source_sha256_unchanged': hashes, 'selected_cpu': raw['summary']['selected_cpu'],
                  'independently_confirmed_cpu': confirmation['summary']['selected_cpu'], 'fit_targets': 0})
    print(json.dumps(json.loads(output.read_text()), indent=2))


if __name__ == '__main__': main()
