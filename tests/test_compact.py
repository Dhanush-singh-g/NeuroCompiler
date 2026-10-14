import copy
import json
import math
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

from src.benchmarks.compact import (MENU, PROTOCOL, TRAIN_CASES, case_id, effect,
    measure_cell, save, scope, summarize, verify_manifest, verify_report)
from src.supervised.compact import (CHOICES, Regressor, Selector, cross_validate,
    features, program_weights, select_policy)


def manifest(case=TRAIN_CASES[0]):
    return {"id": case_id(case), "case": list(case), "split": "train",
            "program": f"benchmark://cbench-v1/{case[0]}", "features": [1] * 58,
            "artifacts": {c: {"elf_sha256": c} for c in MENU},
            "aliases": {c: c for c in MENU}}


def cell(m, choice="O3", role="qualification", block=0, ratio=1.):
    left = "O3" if role in ("qualification", "effect") else choice
    return {"case": m["id"], "choice": choice, "role": role, "block": block,
            "left": left, "right": choice, "first": True,
            "left_seconds": [.1 * ratio] * PROTOCOL["pairs"],
            "right_seconds": [.1] * PROTOCOL["pairs"]}


def report():
    manifests = {case_id(c): manifest(c) for c in TRAIN_CASES}
    profiles = {k: {"seconds": [.1] * PROTOCOL["profile_runs"], "eligible": True} for k in manifests}
    records = []
    for m in manifests.values():
        for b in range(PROTOCOL["blocks"]):
            records.append(cell(m, block=b))
            for i, c in enumerate(CHOICES):
                records.extend([cell(m, c, "candidate_control", b), cell(m, c, "effect", b, [.9, 1.05, 1.][i])])
    r = {"protocol": PROTOCOL, "split": "train", "complete": True,
         "manifests": manifests, "profiles": profiles, "records": records}
    r["labels"] = summarize(r)
    return r


def learning_rows(n=6):
    rows = []
    for i in range(n):
        for j in range(1 + (i == 0)):
            rows.append({"case": f"{i}_{j}", "program": f"program{i}", "features": [i + 1] * 56 + [j, 0],
                         "outcomes": {c: {"log_speedup": math.log(1.1 if c == CHOICES[0] else .98)} for c in MENU}})
    return rows


class TimingTests(unittest.TestCase):
    def test_complete_signed_targets(self):
        r = report()
        verify_report(r, artifacts=False)
        self.assertEqual(len(r["labels"]), len(TRAIN_CASES))
        self.assertAlmostEqual(r["labels"][0]["outcomes"][CHOICES[0]]["log_speedup"], math.log(.9))
        self.assertFalse(r["labels"][0]["outcomes"][CHOICES[0]]["confirmed_gain"])
        self.assertTrue(r["labels"][0]["outcomes"][CHOICES[1]]["confirmed_gain"])

    def test_bad_o3_control_excludes_entire_input(self):
        r = report()
        target = next(iter(r["manifests"]))
        for c in r["records"]:
            if c["case"] == target and c["role"] == "qualification":
                c["left_seconds"] = [.12] * PROTOCOL["pairs"]
        self.assertNotIn(target, {r["case"] for r in summarize(r)})

    def test_one_bad_candidate_control_excludes_entire_menu(self):
        r = report()
        c = next(c for c in r["records"] if c["role"] == "candidate_control")
        c["left_seconds"] = [.12] * PROTOCOL["pairs"]
        self.assertNotIn(c["case"], {r["case"] for r in summarize(r)})

    def test_missing_measurements_are_not_zero_targets(self):
        r = report()
        r["records"].pop()
        self.assertEqual(len(summarize(r)), len(TRAIN_CASES) - 1)
        with self.assertRaisesRegex(ValueError, "Missing complete-menu"):
            verify_report(r, artifacts=False)

    def test_raw_label_tampering_rejected(self):
        r = report()
        r["labels"][0]["outcomes"]["O3"]["log_speedup"] = .1
        with self.assertRaisesRegex(ValueError, "Labels"):
            verify_report(r, artifacts=False)

    def test_duplicate_and_nonpositive_timing_rejected(self):
        r = report()
        r["records"].append(r["records"][0])
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            verify_report(r, artifacts=False)
        r["records"].pop()
        r["records"][0]["left_seconds"][0] = 0
        with self.assertRaisesRegex(ValueError, "runtime"):
            verify_report(r, artifacts=False)

    def test_split_and_reserved_test_rejected(self):
        with self.assertRaises(ValueError):
            scope("test")
        m = manifest()
        m["case"] = ["susan", 0, 0]
        with self.assertRaisesRegex(ValueError, "split"):
            verify_manifest(m, "train", artifacts=False)

    def test_structural_checks_without_artifacts(self):
        m = manifest()
        verify_manifest(m, "train", artifacts=False)
        m["features"] = [1] * 57
        with self.assertRaisesRegex(ValueError, "features"):
            verify_manifest(m, "train", artifacts=False)
        m = manifest()
        m["aliases"][CHOICES[0]] = "O3"
        with self.assertRaisesRegex(ValueError, "alias"):
            verify_manifest(m, "train", artifacts=False)

    def test_alias_to_o3_is_exact_zero(self):
        r = report()
        ident = next(iter(r["manifests"]))
        m = r["manifests"][ident]
        m["artifacts"][CHOICES[0]]["elf_sha256"] = "O3"
        m["aliases"][CHOICES[0]] = "O3"
        r["records"] = [c for c in r["records"] if not (c["case"] == ident and c["choice"] == CHOICES[0])]
        rows = summarize(r)
        value = next(x for x in rows if x["case"] == ident)["outcomes"][CHOICES[0]]
        self.assertEqual(value["speedup"], 1.)
        self.assertEqual(value["log_speedup"], 0.)

    def test_paired_orders_and_warmups(self):
        calls = []
        def fake(m, choice, check_output=False):
            calls.append((choice, check_output))
            return .1
        with patch("src.benchmarks.compact.run", fake):
            c = measure_cell(manifest(), "O3", CHOICES[0], 0, "effect", True)
        self.assertEqual(calls[:2], [("O3", True), (CHOICES[0], True)])
        self.assertEqual([x[0] for x in calls[2:6]], ["O3", CHOICES[0], CHOICES[0], "O3"])
        self.assertEqual(len(c["left_seconds"]), PROTOCOL["pairs"])

    def test_bootstrap_is_deterministic_and_noise_rejected(self):
        m = manifest()
        cells = [cell(m, block=b) for b in range(PROTOCOL["blocks"])]
        self.assertEqual(effect(cells), effect(cells))
        cells[0]["left_seconds"] = [.2] * PROTOCOL["pairs"]
        self.assertFalse(effect(cells)["control_pass"])

    def test_atomic_json(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "result.json"
            save(path, {"complete": False})
            save(path, {"complete": True})
            self.assertEqual(json.loads(path.read_text()), {"complete": True})
            self.assertFalse(path.with_suffix(".json.tmp").exists())


class LearningTests(unittest.TestCase):
    def test_original_program_weight_is_equal(self):
        rows = learning_rows()
        weights = program_weights(rows)
        for p in {r["program"] for r in rows}:
            self.assertAlmostEqual(sum(w for r, w in zip(rows, weights) if r["program"] == p), 1.)

    def test_nested_folds_do_not_leak(self):
        cv = cross_validate(learning_rows())
        for result in cv.values():
            for f in result["folds"]:
                self.assertNotIn(f["held"], f["fit"])
                for inner in f["calibration"]:
                    self.assertNotIn(inner["held"], inner["fit"])
                    self.assertNotIn(f["held"], inner["fit"])
                    self.assertIn(inner["held"], f["fit"])
                    self.assertTrue(set(inner["fit"]).issubset(f["fit"]))

    def test_guards_can_select_supported_gain(self):
        rows = learning_rows()
        model = Selector("constant", True).fit(rows)
        self.assertEqual(model.choose(rows[0]["features"])["configuration"], CHOICES[0])

    def test_small_or_weak_effect_abstains(self):
        rows = learning_rows()
        for r in rows:
            for c in CHOICES:
                r["outcomes"][c]["log_speedup"] = math.log(1.02)
        model = Selector("ridge", True).fit(rows)
        self.assertEqual(model.choose(rows[0]["features"])["configuration"], "O3")
        with self.assertRaisesRegex(ValueError, "four"):
            Selector("constant", True).fit(learning_rows(3))

    def test_o3_policy_still_validates_features(self):
        model = Selector("O3").fit([])
        self.assertEqual(model.choose([0] * 58)["configuration"], "O3")
        for values in [[0] * 57, [float("nan")] * 58, [-1] * 58]:
            with self.assertRaises(ValueError):
                model.choose(values)

    def test_constant_features_have_finite_ridge_predictions(self):
        rows = learning_rows()
        for r in rows:
            r["features"] = [0] * 58
        reg = Regressor("ridge").fit(rows)
        self.assertTrue(all(np.isfinite(list(reg.scores([0] * 58).values()))))

    def test_raw_or_uncertain_policy_cannot_replace_o3(self):
        good = {"score": {"geomean": 1.1, "interval": [1.05, 1.15], "worst_program": 1.01}}
        uncertain = {"score": {"geomean": 1.05, "interval": [.99, 1.1], "worst_program": .98}}
        self.assertEqual(select_policy({"raw_ridge": good, "guarded_ridge": uncertain}), "O3")
        self.assertEqual(select_policy({"raw_ridge": good, "guarded_ridge": good}), "guarded_ridge")
        unsafe = copy.deepcopy(good)
        unsafe["score"]["worst_program"] = .95
        self.assertEqual(select_policy({"guarded_ridge": unsafe}), "O3")

    def test_missing_original_program_coverage_rejected(self):
        r = report()
        r["profiles"].pop(next(iter(r["profiles"])))
        with self.assertRaisesRegex(ValueError, "case coverage"):
            verify_report(r, artifacts=False)


if __name__ == "__main__":
    unittest.main()
