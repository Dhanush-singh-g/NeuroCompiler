import io
import math
import tarfile
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

import numpy as np

from src.benchmarks.expanded import ACTIVE, PRIMARY_CASES, TRAIN_CASES, DEVELOPMENT_CASES, safe_members
from src.benchmarks.expanded_drivers import pack, decode_fastlz, xml_hash, sax
from src.supervised.expanded import Selector, cv
from src.benchmarks.expanded import Toolchain, ROOT, source_pins
from src.benchmarks.expanded_drivers import FROZEN
from src.benchmarks.region import BASIS, feed
from src.benchmarks.persistent import validate


class ExpandedTests(unittest.TestCase):
    def test_distinct_programs_and_closed_new_development(self):
        self.assertEqual(len(TRAIN_CASES), 42); self.assertEqual(len(PRIMARY_CASES), 21)
        self.assertEqual(len({c.split('_')[0] for c in PRIMARY_CASES}), 21)
        self.assertTrue(set(PRIMARY_CASES) <= set(TRAIN_CASES))
        self.assertFalse({c.split('_')[0] for c in TRAIN_CASES} & {c.split('_')[0] for c in DEVELOPMENT_CASES})

    def test_fastlz_literals_and_overlapping_backreference(self):
        self.assertEqual(decode_fastlz(b'\x02abc', 3), b'abc')
        self.assertEqual(decode_fastlz(b'\x00a\x20\x00', 4), b'aaaa')
        self.assertEqual(decode_fastlz(b'\x00a\xe0\x00\x00', 10), b'a' * 10)

    def test_fastlz_corrupt_and_oversize_streams_reject(self):
        for stream, limit in [(b'', 9), (b'\x20a', 9), (b'\x02a', 9), (b'\x00a\x20\xff', 9), (b'\x00a\x20\x00', 3)]:
            with self.assertRaises(ValueError): decode_fastlz(stream, limit)

    def test_messagepack_matches_specification_examples(self):
        self.assertEqual(pack({'a': [1, True, None]}), b'\x81\xa1a\x93\x01\xc3\xc0')
        self.assertEqual(pack(-1), b'\xff'); self.assertEqual(pack(128), b'\xd3' + (128).to_bytes(8, 'big', signed=True))

    def test_xml_oracle_normalizes_entities_but_detects_changed_content(self):
        self.assertEqual(xml_hash(b'<r>a&amp;b</r>'), xml_hash(b'<r>a&#38;b</r>'))
        self.assertNotEqual(xml_hash(b'<r>ab</r>'), xml_hash(b'<r>ba</r>'))
        self.assertNotEqual(xml_hash(b'<r><a/></r>'), xml_hash(b'<r><b/></r>'))

    def test_sax_oracle_detects_key_value_and_container_changes(self):
        self.assertNotEqual(sax({'a': [1]}), sax({'b': [1]}))
        self.assertNotEqual(sax([1]), sax([True])); self.assertNotEqual(sax([1]), sax({'a': 1}))

    def test_source_archive_traversal_rejects_and_links_are_not_materialized(self):
        for name, kind in [('root/../escape.c', tarfile.REGTYPE), ('root/link.h', tarfile.SYMTYPE)]:
            buffer = io.BytesIO()
            with tarfile.open(fileobj=buffer, mode='w') as archive:
                info = tarfile.TarInfo(name); info.type = kind; info.linkname = '/etc/passwd'; archive.addfile(info)
            buffer.seek(0)
            with tarfile.open(fileobj=buffer) as archive:
                if kind == tarfile.REGTYPE:
                    with self.assertRaises(ValueError): list(safe_members(archive, 'root'))
                else: self.assertEqual(list(safe_members(archive, 'root')), [])

    def test_selector_never_recommends_unmeasured_inline_setting(self):
        selector = Selector(); selector.mean = np.zeros(1); selector.scale = np.ones(1)
        class Model:
            def predict(self, x):
                self.seen = x.copy(); return np.full(len(x), math.log(1.1))
        selector.model = Model()
        m = {'aliases': {c: c for c in ['O3', 'O2', 'O3_no_vector', 'O3_large_inline']},
             'features': {'O2': [1.], 'O3_no_vector': [2.], 'O3_large_inline': [999.]}}
        self.assertIn(selector.choose(m)['choice'], ACTIVE)
        self.assertEqual(selector.model.seen.tolist(), [[1.], [2.]])

    def test_whole_program_cv_excludes_held_implementation(self):
        manifests = {}; labels = []
        for i in range(6):
            case = f'p{i}_input'; aliases = {c: c for c in ['O3', 'O2', 'O3_no_vector', 'O3_large_inline']}
            features = {'O2': [float(i), 1.], 'O3_no_vector': [float(i), 2.], 'O3_large_inline': [float(i), 3.]}
            outcomes = {c: {'interval': [1., 1.], 'log_speedup': 0., 'confirmed_gain': False} for c in ACTIVE}
            manifests[case] = {'features': features, 'aliases': aliases}
            labels.append({'case': case, 'program': f'p{i}', 'aliases': aliases, 'features': features, 'outcomes': outcomes})
        result = cv(labels, manifests, 10., False, .03, 'ridge', 3)
        self.assertTrue(result['eligible']); self.assertEqual(len(result['folds']), 6)
        for fold in result['folds']: self.assertNotIn(fold['held_program'], fold['train_programs'])

    def test_native_frozen_distinguishes_array_indices_from_numeric_object_keys(self):
        pin = source_pins()['frozen']; tools = Toolchain()
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            with tarfile.open(ROOT / pin['archive']) as archive:
                for name in ['frozen.c', 'frozen.h']:
                    (base / name).write_bytes(archive.extractfile(pin['root'] + '/' + name).read())
            driver = base / 'driver.c'; driver.write_text(FROZEN)
            library = base / 'fixture.so'; worker = base / 'worker'
            tools.call([tools.directory / 'clang', '-O2', '-fPIC', '-shared', '-I' + str(base), driver, base / 'frozen.c', '-o', library])
            tools.call([tools.directory / 'clang', '-O2', '-rdynamic', ROOT / 'src/benchmarks/persistent_library_worker.c', '-ldl', '-lm', '-o', worker])
            for value in [{'0': [1, True, None, {'x': 'hey'}], 'b': {'c': 2}}, [{'0': True}, False, 2, None, 'raw']]:
                data = base / 'input'; data.write_text(json.dumps(value, separators=(',', ':')))
                result = subprocess.run([str(worker), str(library), str(library), str(data), '1', '2', '1', '2', 'micro'], check=True, capture_output=True, timeout=20)
                expected = {'checksum': f'{feed(BASIS, sax(value)):016x}', 'values': 1}
                validate(json.loads(result.stdout), {'expected': expected}, 2, 1, True, 'micro')


if __name__ == '__main__': unittest.main()
