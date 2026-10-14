"""Protect fixed budgets, program separation and order validation."""
import copy
import math
import unittest
from unittest.mock import patch

from scripts import measure_persistent as pilot
from scripts import confirm_persistent as confirmation
from scripts import study_persistent as study


class PersistentStudyTests(unittest.TestCase):
    def test_every_pilot_case_method_block_occurs_once(self):
        schedule = pilot.plan()
        cells = {(r['case'], r['method'], r['block']) for r in schedule}
        self.assertEqual(len(cells), 72)
        self.assertEqual(cells, {(c, m, b) for c in pilot.CASES for m in pilot.METHODS for b in range(3)})

    def test_failed_confirmation_does_not_schedule_probe(self):
        self.assertEqual(confirmation.schedule('probe', None), [])
        result = confirmation.summarize('probe', {'method': None})
        self.assertEqual(result['status'], 'not_run'); self.assertEqual(result['fit_targets'], 0)

    def test_probe_is_one_preselected_case_with_all_three_roles(self):
        schedule = confirmation.schedule('probe', 'micro')
        self.assertEqual(len(schedule), 9)
        self.assertEqual({r['case'] for r in schedule}, {'blake2_random'})
        for block in range(3):
            self.assertEqual({r['role'] for r in schedule if r['block'] == block}, {r[0] for r in confirmation.ROLES})

    def test_probe_rejects_gain_when_either_self_control_or_effect_order_fails(self):
        rows = [{'role': role} for role, _, _ in confirmation.ROLES]
        good = {'control_pass': True, 'order_pass': True, 'interval': [1.1, 1.2], 'blocks': [1.15] * 3}
        def evaluate(bad_role, bad_field):
            def fake_effect(group, clock):
                return {**good, **({bad_field: False} if group[0]['role'] == bad_role else {})}
            with patch.object(confirmation, 'clock_effect', side_effect=fake_effect):
                return confirmation.summarize('probe', {'method': 'micro', 'records': rows})
        for role, field in [('qualification', 'control_pass'), ('candidate_control', 'control_pass'), ('effect', 'order_pass')]:
            self.assertFalse(evaluate(role, field)['passed'])

    def test_candidate_schedule_never_measures_failed_baseline_or_binary_alias(self):
        manifests = {
            'a': {'aliases': {'O3': 'O3', 'O2': 'O2', 'O3_no_vector': 'O3', 'O3_large_inline': 'O2'}},
            'b': {'aliases': {c: c for c in study.region.MENU}}}
        raw = {'split': 'train', 'manifests': manifests, 'records': [
            {'case': case, 'role': 'qualification', 'ok': case == 'a'} for case in manifests for _ in range(3)]}
        with patch.object(study, 'clock_effect', side_effect=lambda rows, clock: {'control_pass': rows[0]['ok']}):
            schedule = study.candidate_schedule({}, raw)
        self.assertEqual(len(schedule), 6)
        self.assertEqual({r['case'] for r in schedule}, {'a'})
        self.assertEqual({r['choice'] for r in schedule}, {'O2'})
        self.assertTrue(all(r['left'] == r['right'] for r in schedule if r['role'] == 'candidate_control'))

    def test_development_measures_only_frozen_prediction(self):
        manifests = {'a': {'aliases': {c: c for c in study.region.MENU}}}
        raw = {'split': 'development', 'manifests': manifests, 'records': [{'case': 'a', 'role': 'qualification'}] * 3,
               'decisions': {'a': {'choice': 'O2'}}}
        with patch.object(study, 'clock_effect', return_value={'control_pass': True}):
            schedule = study.candidate_schedule({}, raw)
        self.assertEqual({r['choice'] for r in schedule}, {'O2'})
        raw['decisions']['a']['choice'] = 'O3'
        with patch.object(study, 'clock_effect', return_value={'control_pass': True}):
            self.assertEqual(study.candidate_schedule({}, raw), [])


if __name__ == '__main__': unittest.main()
