"""Portable fresh builds, frozen source pins and isolated native API evidence."""
import hashlib
import ctypes
import ctypes.util
import json
import math
import os
import platform
import re
import shutil
import subprocess
import tarfile
import tempfile
import zlib
from pathlib import Path, PurePosixPath

import numpy as np

from src.benchmarks import region
from src.benchmarks import expanded_drivers as new
from src.benchmarks.compact import save, sha
from src.benchmarks.persistent import run as persistent_run, validate
from src.features.timed_region import analyze, vector

ROOT = Path(__file__).resolve().parents[2]
SOURCE_PINS = ROOT / 'results/expanded_source_pins.json'
OLD_CASES = region.CASES + region.DEVELOPMENT
NEW_TRAIN = ['jsonparser', 'miniz', 'fastlz', 'frozen', 'yxml', 'mpack']
NEW_DEVELOPMENT = ['jsonh', 'libdeflate']
VARIANTS = {p: ['flat', 'nested'] if p in ['jsonparser', 'jsonh', 'frozen', 'yxml', 'mpack'] else ['pattern', 'random']
            for p in NEW_TRAIN + NEW_DEVELOPMENT}
TRAIN_CASES = OLD_CASES + [p + '_' + v for p in NEW_TRAIN for v in VARIANTS[p]]
DEVELOPMENT_CASES = [p + '_' + v for p in NEW_DEVELOPMENT for v in VARIANTS[p]]
PRIMARY_CASES = ['zlib_random', 'expat_nested', 'lua_numeric', 'lz4_random', 'jsmn_nested',
                 'bzip2_random', 'blake2_random', 'cjson_nested', 'inih_sections', 'tinyexpr_functions',
                 'parson_nested', 'picohttp_headers', 'sha256_random', 'monocypher_random', 'yyjson_nested',
                 'jsonparser_nested', 'miniz_random', 'fastlz_random', 'frozen_nested', 'yxml_nested', 'mpack_nested']
GATE_CASES = ['zlib_random', 'expat_nested', 'lz4_random', 'jsonparser_nested', 'miniz_random', 'mpack_nested']
MENU = region.MENU
ACTIVE = ['O3', 'O2', 'O3_no_vector']
PROTOCOL = {'blocks': 3, 'pairs': 24, 'cpu_batch_seconds': .20, 'control_tolerance': .03,
            'gain_floor': .03, 'bootstrap_replicates': 2000, 'bootstrap_seed': region.PROTOCOL['seed'],
            'order_seed': 20261012, 'method': 'micro', 'warmups': 3, 'minimum_invocation_seconds': .0001,
            'max_repetitions': 100000, 'gate': 'all six inputs pass CPU AND wall; one independent confirmation, no retry',
            'candidate_gate': 'CPU baseline must pass; independent CPU/wall candidate controls and effect order',
            'scope': '21 distinct training implementations; one preselected formal input each; 42 correctness inputs; two fresh development implementations/four inputs',
            'fit_policy': 'exclude every older, gate, confirmation and correctness clock; no missing-outcome imputation',
            'objective': 'warm native library API CPU time; independent wall confirmation; exclude startup/client I/O',
            'active_choices': ACTIVE, 'feature_count': 95}


def source_pins():
    return json.loads(SOURCE_PINS.read_text())


def input_bytes(case):
    return new.input_bytes(case) if case.split('_')[0] in new.DRIVERS else region.input_bytes(case)


def expected(case):
    value = new.oracle(case) if case.split('_')[0] in new.DRIVERS else region.oracle(case)
    return {'checksum': f'{region.feed(region.BASIS, value):016x}', 'values': 1}


class Toolchain:
    def __init__(self, directory=None):
        default = '/workspace/.neurocompiler/llvm19/root/usr/lib/llvm-19/bin'
        if not Path(default).is_dir(): default = '/usr/lib/llvm-19/bin'
        self.directory = Path(directory or os.environ.get('NEUROCOMPILER_LLVM19', default)).resolve()
        self.environment = dict(os.environ)
        # Private extracted Debian packages need their adjacent runtime libs.
        lib = self.directory.parents[2] / 'lib/x86_64-linux-gnu'
        if lib.is_dir(): self.environment['LD_LIBRARY_PATH'] = str(lib) + ':' + self.environment.get('LD_LIBRARY_PATH', '')
        self.metadata = {}
        for name in ['clang', 'opt', 'llvm-link', 'llvm-dis']:
            path = self.directory / name
            version = self.call([path, '--version']).decode().splitlines()[0]
            if not re.search(r'\b(?:version\s+)?19\.', version): raise ValueError('LLVM19 required: ' + version)
            self.metadata[name] = {'version': version, 'sha256': sha(path)}

    def call(self, args):
        return subprocess.run([str(a) for a in args], env=self.environment, capture_output=True,
                              check=True, timeout=240).stdout


def context(tools, cpu):
    available = sorted(os.sched_getaffinity(0))
    # Caller may already pin orchestration to a single core; kernel allowance
    # inherited by workers can be expanded within the actual cpuset.
    model = next((v.split(':', 1)[1].strip() for v in Path('/proc/cpuinfo').read_text().splitlines()
                  if v.startswith('model name')), platform.processor())
    flags = next((v.split(':', 1)[1].strip() for v in Path('/proc/cpuinfo').read_text().splitlines()
                  if v.startswith(('flags', 'Features'))), '')
    return {'architecture': platform.machine(), 'cpu_model': model, 'cpu_flags': flags,
            'kernel': platform.release(), 'tools': tools.metadata, 'native_cpu': cpu,
            'cpu_quota': Path('/sys/fs/cgroup/cpu.max').read_text().strip() if Path('/sys/fs/cgroup/cpu.max').exists() else None,
            'initial_affinity': available, 'source_rebuild': True, 'binary_reuse': False}


def safe_members(archive, prefix):
    for member in archive.getmembers():
        if not member.name.startswith(prefix + '/'): continue
        relative = PurePosixPath(member.name[len(prefix)+1:])
        if relative.is_absolute() or '..' in relative.parts: raise ValueError('Unsafe archive path')
        if member.issym() or member.islnk(): continue
        if member.isfile() and (relative.suffix in ['.c', '.h', '.inc'] or relative.name.upper().startswith(('LICENSE', 'COPYING'))):
            yield member, Path(*relative.parts)


def materialize(program, directory):
    pin = source_pins()[program]; archive_path = ROOT / pin['archive']
    if sha(archive_path) != pin['sha256']: raise ValueError('Pinned source changed')
    upstream = directory / 'upstream'; upstream.mkdir()
    with tarfile.open(archive_path) as archive:
        for member, relative in safe_members(archive, pin['root']):
            dest = upstream / relative; dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(archive.extractfile(member).read())
    flags = []; include = upstream
    recipes = {
        'zlib': [x + '.c' for x in ['adler32', 'crc32', 'compress', 'uncompr', 'deflate', 'trees', 'zutil', 'inflate', 'inftrees', 'inffast']],
        'expat': ['expat/lib/' + x + '.c' for x in ['xmlparse', 'xmlrole', 'xmltok']],
        'lz4': ['lib/lz4.c'], 'bzip2': [x + '.c' for x in ['blocksort', 'huffman', 'crctable', 'randtable', 'compress', 'decompress', 'bzlib']],
        'blake2': ['ref/blake2b-ref.c'], 'cjson': ['cJSON.c'], 'inih': ['ini.c'], 'tinyexpr': ['tinyexpr.c'],
        'parson': ['parson.c'], 'picohttp': ['picohttpparser.c'], 'sha256': ['sha256.c'],
        'monocypher': ['src/monocypher.c'], 'yyjson': ['src/yyjson.c'], 'jsmn': [],
        'jsonparser': ['json.c'], 'jsonh': [], 'frozen': ['frozen.c'], 'yxml': ['yxml.c'],
        'fastlz': ['fastlz.c'], 'miniz': ['miniz.c', 'miniz_tdef.c', 'miniz_tinfl.c'],
        'mpack': ['src/mpack/' + x + '.c' for x in ['mpack-common', 'mpack-expect', 'mpack-node', 'mpack-platform', 'mpack-reader', 'mpack-writer']],
        'libdeflate': ['lib/' + x + '.c' for x in ['adler32', 'crc32', 'deflate_compress', 'deflate_decompress',
                       'gzip_compress', 'gzip_decompress', 'zlib_compress', 'zlib_decompress', 'utils']] +
                      ['lib/' + ('x86' if platform.machine() == 'x86_64' else 'arm') + '/cpu_features.c'],
    }
    if program == 'lua':
        recipes[program] = [str(p.relative_to(upstream)) for p in sorted((upstream / 'src').glob('*.c')) if p.name not in ['lua.c', 'luac.c']]
        include = upstream / 'src'; flags = ['-DLUA_USE_LINUX']
    if program in ['lz4', 'blake2', 'monocypher', 'yyjson', 'mpack']:
        include = upstream / {'lz4': 'lib', 'blake2': 'ref', 'monocypher': 'src', 'yyjson': 'src', 'mpack': 'src/mpack'}[program]
    if program == 'expat':
        include = upstream / 'expat/lib'; (include / 'expat_config.h').write_text(region.EXPAT_CONFIG); flags = ['-DHAVE_EXPAT_CONFIG_H']
    if program == 'miniz':
        (include / 'miniz_export.h').write_text('#pragma once\n#define MINIZ_EXPORT\n')
        flags = ['-DMINIZ_NO_ARCHIVE_APIS', '-DMINIZ_NO_ZLIB_COMPATIBLE_NAMES']
    return [upstream / p for p in recipes[program]], include, flags


def compile_program(base, program, tools):
    directory = base / 'programs' / program; directory.mkdir(parents=True, exist_ok=False)
    sources, include, extra = materialize(program, directory)
    driver = directory / 'driver.c'; driver.write_text(new.DRIVERS.get(program) or region.DRIVERS[program]); sources.append(driver)
    units = []
    for i, source in enumerate(sources):
        unit = directory / f'unit{i}.bc'
        tools.call([tools.directory / 'clang', '-fPIC', '-march=native', '-ffp-contract=off', '-fno-discard-value-names',
                    '-O1', '-Xclang', '-disable-llvm-passes', *extra, '-I' + str(include), '-emit-llvm', '-c', source, '-o', unit]); units.append(unit)
    initial = directory / 'initial.bc'; tools.call([tools.directory / 'llvm-link', *units, '-o', initial])
    artifacts = {}
    for choice, args in {'reference_O0': ['-passes=default<O0>'], **MENU}.items():
        bc = directory / (choice + '.bc'); so = directory / (choice + '.so')
        tools.call([tools.directory / 'opt', *args, initial, '-o', bc])
        tools.call([tools.directory / 'clang', '-fPIC', '-march=native', '-ffp-contract=off', '-O3', '-Xclang',
                    '-disable-llvm-passes', '-shared', '-Wl,-Bsymbolic', bc, '-lm', '-ldl', '-o', so])
        artifacts[choice] = {'bc': str(bc.relative_to(base)), 'so': str(so.relative_to(base)), 'bc_sha256': sha(bc), 'so_sha256': sha(so)}
    parsed = {c: analyze(tools.call([tools.directory / 'llvm-dis', base / a['bc'], '-o', '-']).decode()) for c, a in artifacts.items() if c in MENU}
    features = {c: vector(parsed['O3'], parsed[c]) + [float(c == v) for v in list(MENU)[1:]] for c in list(MENU)[1:]}
    result = {'program': program, 'family': program, 'artifacts': artifacts,
              'aliases': {c: next(k for k in MENU if artifacts[c]['so_sha256'] == artifacts[k]['so_sha256']) for c in MENU},
              'features': features, 'sources': {str(p.relative_to(base)): sha(p) for p in directory.rglob('*') if p.suffix in ['.c', '.h']},
              'initial': str(initial.relative_to(base)), 'initial_sha256': sha(initial), 'source_pin': source_pins()[program]}
    save(directory / 'manifest.json', result); return result


def compile_worker(base, tools):
    path = base / 'persistent_library_worker.out'
    tools.call([tools.directory / 'clang', '-O2', '-Wall', '-Wextra', '-rdynamic', ROOT / 'src/benchmarks/persistent_library_worker.c', '-ldl', '-lm', '-o', path])
    return path


def resolved(base, m):
    out = {**m, 'input': str(base / m['input'])}
    out['artifacts'] = {c: {**a, 'so': str(base / a['so']), 'bc': str(base / a['bc'])} for c, a in m['artifacts'].items()}
    return out


def run(base, m, block, left='O3', right='O3', pairs=None, repetitions=None, seed=None):
    row = persistent_run(resolved(base, m), 'micro', base / 'persistent_library_worker.out', block,
                         PROTOCOL['order_seed'] if seed is None else seed, left, right,
                         pairs=PROTOCOL['pairs'] if pairs is None else pairs, repetitions=repetitions,
                         cpu=json.loads((base / 'declaration.json').read_text())['context']['native_cpu'])
    row['choice'] = right; return row


def verify_interoperability(base, m):
    if m['program'] not in ['miniz', 'fastlz', 'libdeflate', 'zlib', 'lz4']: return {}
    reports = {}
    for choice in ['reference_O0', *MENU]:
        with tempfile.TemporaryDirectory() as temp:
            stream = Path(temp) / 'compressed.dat'; env = {**os.environ, 'NC_VERIFY_STREAM': str(stream)}
            result = subprocess.run([str(base / 'persistent_library_worker.out'), str(base / m['artifacts'][choice]['so']),
                str(base / m['artifacts'][choice]['so']), str(base / m['input']), '1', '2', '1',
                str(json.loads((base / 'declaration.json').read_text())['context']['native_cpu']), 'micro'],
                env=env, capture_output=True, check=True, timeout=90)
            row = json.loads(result.stdout); validate(row, m, 2, 1, True, 'micro')
            data = stream.read_bytes(); original = (base / m['input']).read_bytes()
            if m['program'] == 'fastlz':
                plain = new.decode_fastlz(data, len(original)); decoder = 'Python FastLZ level-1'
            elif m['program'] == 'lz4':
                library = ctypes.util.find_library('lz4')
                if not library: raise ValueError('Independent system liblz4 required')
                lib = ctypes.CDLL(library); lib.LZ4_decompress_safe.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int, ctypes.c_int]
                buf = ctypes.create_string_buffer(len(original)); n = lib.LZ4_decompress_safe(data, buf, len(data), len(original))
                if n != len(original): raise ValueError('Independent LZ4 decode failed')
                plain = buf.raw; decoder = 'Independent system liblz4 decompressor'
            else:
                plain = zlib.decompress(data); decoder = 'Python system zlib'
            if plain != original: raise ValueError('Independent compressed-stream decoder mismatch')
            reports[choice] = {'decoder': decoder,
                               'compressed_sha256': hashlib.sha256(data).hexdigest(), 'plain_sha256': hashlib.sha256(plain).hexdigest()}
    return reports


def prepare_case(base, program, case):
    directory = base / 'inputs'; directory.mkdir(exist_ok=True); input_path = directory / (case + '.dat')
    input_path.write_bytes(input_bytes(case)); m = {**program, 'id': case, 'input': str(input_path.relative_to(base)),
        'input_sha256': sha(input_path), 'expected': expected(case), 'repetitions': 1}
    m['features'] = {c: v + region.input_features(input_path.read_bytes()) for c, v in program['features'].items()}
    m['correctness'] = {}
    for choice in MENU:
        row = run(base, m, 0, 'reference_O0', choice, pairs=2, repetitions=1); row['role'] = 'correctness'; m['correctness'][choice] = row
    m['interoperability'] = verify_interoperability(base, m)
    cal = run(base, m, 0, pairs=3, repetitions=1); m['calibration'] = cal
    duration = float(np.median([s[side]['cpu_seconds'] for s in cal['samples'] for side in ['left', 'right']]))
    m['eligible'] = duration >= PROTOCOL['minimum_invocation_seconds']
    n = max(2, min(PROTOCOL['max_repetitions'], math.ceil(PROTOCOL['cpu_batch_seconds'] / duration)))
    m['repetitions'] = min(PROTOCOL['max_repetitions'], n + n % 2)
    return m
