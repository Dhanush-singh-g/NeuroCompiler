"""Versioned broader native-library study; original evidence remains immutable."""
import ctypes
import ctypes.util
import hashlib
import json
import math
import re
import shutil
import subprocess
import tarfile
import time
from pathlib import Path

import numpy as np

from src.benchmarks.compact import effect,save,sha
from src.benchmarks.polybench import ROOT,TOOLS,tool,scheduler_ticks
from src.benchmarks.real import SOURCES as OLD_SOURCES,input_bytes as old_input,oracle_stdout,EXPAT_CONFIG
from src.features.transform import candidate_vector,parse_ir
import bz2
import configparser
import io

NAME='broad_native_20261011'
BASE=ROOT/'data/processed/broad19'/NAME
MENU={'O3':['-passes=default<O3>'], 'O2':['-passes=default<O2>'], 'Os':['-passes=default<Os>'],
      'O3_no_vector':['-passes=default<O3>','-vectorize-loops=false','-vectorize-slp=false'],
      'O3_small_inline':['-passes=default<O3>','-inline-threshold=50'],
      'O3_large_inline':['-passes=default<O3>','-inline-threshold=1000'],
      'O3_no_unroll':['-passes=default<O3>','-disable-loop-unrolling']}
PROGRAMS=['zlib','expat','lua','lz4','jsmn','bzip2','blake2','cjson','inih','tinyexpr']
CASES=['zlib_pattern','zlib_random','expat_flat','expat_nested','lua_numeric','lua_tables',
       'lz4_pattern','lz4_random','jsmn_flat','jsmn_nested','bzip2_pattern','bzip2_random',
       'blake2_pattern','blake2_random','cjson_flat','cjson_nested','inih_flat','inih_sections',
       'tinyexpr_arithmetic','tinyexpr_functions']
DEVELOPMENT=['parson_flat','parson_nested','picohttp_short','picohttp_headers']
from src.benchmarks.invocation import PROTOCOL as PRIOR_PROTOCOL
PROTOCOL={**PRIOR_PROTOCOL,'version':2,'menu':MENU,
    'scope':'ten original training programs with two inputs each; parson and picohttpparser entire-program development holdouts',
    'features':'153 static IR metrics, six candidate indicators, four input descriptors; no runtime prediction features',
    'sampling':'all formal timings collected anew; prior bitcode reused with pinned identical source; prior runtime labels excluded',
    'selection':'whole-program CV, Ridge and random forest; utility>0, worst program>=0.97, >=1 confirmed gain; otherwise O3',
    'secondary_budget':'one strongest confirmed training candidate by CPU lower bound; one isolated study; never fit secondary labels'}
MASK=(1<<64)-1
BASIS=1469598103934665603
PRIME=1099511628211

COMMON=r'''#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
extern void polybench_timer_start(void),polybench_timer_stop(void),nc_emit_u64(uint64_t);
#define START() do {polybench_timer_start();__asm__ __volatile__("" ::: "memory");} while(0)
#define STOP() do {__asm__ __volatile__("" ::: "memory");polybench_timer_stop();} while(0)
static unsigned char *input;static size_t length;
static void prepare(int argc,char **argv) {
 if(argc!=3||strcmp(argv[2],"1"))exit(2);
 if(input)return;FILE *f=fopen(argv[1],"rb");if(!f)exit(2);
 if(fseek(f,0,SEEK_END))exit(2);long n=ftell(f);if(n<1)exit(2);rewind(f);
 input=malloc((size_t)n+1);if(!input)exit(2);
 if(fread(input,1,(size_t)n,f)!=(size_t)n)exit(2);fclose(f);input[n]=0;length=n;
}
'''
DRIVERS={
'zlib':COMMON+r'''#include "zlib.h"
int nc_benchmark_main(int argc,char **argv) {
 prepare(argc,argv);uLong bound=compressBound(length);uLongf size=bound,out=length;
 unsigned char *packed=malloc(bound),*plain=malloc(length);if(!packed||!plain)return 2;
 START();int a=compress2(packed,&size,input,length,6);int b=uncompress(plain,&out,packed,size);STOP();
 if(a!=Z_OK||b!=Z_OK||out!=length||memcmp(plain,input,length))return 3;
 nc_emit_u64((uint64_t)size*33u+packed[size/2]);free(packed);free(plain);return 0;
}
''',
'expat':COMMON+r'''#include "expat.h"
static void start(void *p,const XML_Char *name,const XML_Char **attributes) {
 uint64_t *s=p;*s+=17;while(*name)*s=*s*33u+(unsigned char)*name++;
 for(;*attributes;attributes++)for(const char *q=*attributes;*q;q++)*s=*s*33u+(unsigned char)*q;
}
static void text(void *p,const XML_Char *q,int n) {
 uint64_t *s=p;for(int i=0;i<n;i++)*s=*s*33u+(unsigned char)q[i];
}
int nc_benchmark_main(int argc,char **argv) {
 prepare(argc,argv);uint64_t sum=0;START();XML_Parser p=XML_ParserCreate(NULL);if(!p)return 3;
 if(!XML_SetHashSalt(p,1))return 3;XML_SetUserData(p,&sum);
 XML_SetElementHandler(p,start,NULL);XML_SetCharacterDataHandler(p,text);
 int rc=XML_Parse(p,(const char *)input,(int)length,1);XML_ParserFree(p);STOP();
 if(rc!=XML_STATUS_OK)return 4;nc_emit_u64(sum);return 0;
}
''',
'lua':COMMON+r'''#include "lua.h"
#include "lauxlib.h"
#include "lualib.h"
int nc_benchmark_main(int argc,char **argv) {
 prepare(argc,argv);START();lua_State *p=luaL_newstate();if(!p)return 3;luaL_openlibs(p);
 if(luaL_loadbuffer(p,(const char *)input,length,"frozen_input")||lua_pcall(p,0,1,0))return 4;
 if(!lua_isinteger(p,-1))return 5;uint64_t sum=(uint64_t)lua_tointeger(p,-1);lua_close(p);STOP();
 nc_emit_u64(sum);return 0;
}
''',
'lz4':COMMON+r'''#include "lz4.h"
int nc_benchmark_main(int argc,char **argv) {
 prepare(argc,argv);int bound=LZ4_compressBound((int)length);
 char *packed=malloc(bound),*plain=malloc(length);if(!packed||!plain)return 2;
 START();int size=LZ4_compress_default((const char *)input,packed,(int)length,bound);
 int out=size>0?LZ4_decompress_safe(packed,plain,size,(int)length):-1;STOP();
 if(size<1||out!=(int)length||memcmp(plain,input,length))return 3;
 nc_emit_u64((uint64_t)size*33u+(unsigned char)packed[size/2]);free(packed);free(plain);return 0;
}
''',
'jsmn':COMMON+r'''#define JSMN_STRICT
#define JSMN_PARENT_LINKS
#include "jsmn.h"
int nc_benchmark_main(int argc,char **argv) {
 prepare(argc,argv);jsmntok_t *t=malloc((length+1)*sizeof(*t));if(!t)return 2;
 jsmn_parser p;jsmn_init(&p);START();int n=jsmn_parse(&p,(const char *)input,length,t,(unsigned)(length+1));STOP();
 if(n<1)return 3;uint64_t sum=UINT64_C(1469598103934665603);
 for(int i=0;i<n;i++) {
  sum=(sum^(uint64_t)t[i].type)*UINT64_C(1099511628211);
  sum=(sum^(uint64_t)t[i].start)*UINT64_C(1099511628211);
  sum=(sum^(uint64_t)t[i].end)*UINT64_C(1099511628211);
 }
 nc_emit_u64(sum);free(t);return 0;
}
''',
'xxhash':COMMON+r'''#include "xxhash.h"
int nc_benchmark_main(int argc,char **argv) {
 prepare(argc,argv);START();uint64_t sum=XXH64(input,length,0);STOP();nc_emit_u64(sum);return 0;
}
'''}


def legacy_input_bytes(case):
    if case in CASES[:6]:return old_input(case)
    if case.startswith('jsmn_'):
        data=[{'id':i,'name':f'entry{i}','values':[i,i*13,True,None]} for i in range(2500)]
        if case.endswith('nested'):data={'records':data,'nested':[[[i]] for i in range(1000)]}
        return json.dumps(data,separators=(',',':')).encode()
    size=2*1024*1024 if case.startswith('lz4_') else 4*1024*1024
    if case.endswith('pattern'):
        phrase=b'NeuroCompiler library workload 0123456789\n'
        return (phrase*(size//len(phrase)+1))[:size]
    if case.endswith('random'):
        # A seed freezes the workload; variants remain grouped by original program.
        return np.random.default_rng(20261031).integers(0,256,size,dtype=np.uint8).tobytes()
    raise ValueError('Unregistered input')


def input_features(data):
    counts=np.bincount(np.frombuffer(data,dtype=np.uint8),minlength=256);p=counts[counts>0]/len(data)
    return [math.log1p(len(data)),float(-np.sum(p*np.log2(p))/8),
            float(sum(counts[32:127])/len(data)),float(counts[0]/len(data))]


def json_tokens(data):
    text=data.decode('ascii');json.loads(text);tokens=[];stack=[]
    pattern=r'"(?:[^"\\]|\\.)*"|[{}\[\]]|true|false|null|-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?'
    for match in re.finditer(pattern,text):
        value=match.group()
        if value in ('{','['):
            stack.append(len(tokens));tokens.append([1 if value=='{' else 2,match.start(),None])
        elif value in ('}',']'):tokens[stack.pop()][2]=match.end()
        elif value.startswith('"'):tokens.append([3,match.start()+1,match.end()-1])
        else:tokens.append([4,match.start(),match.end()])
    if stack:raise ValueError('Incomplete JSON oracle')
    return tokens


def xxh64(data,seed=0):
    """Independent Python implementation of the published XXH64 algorithm."""
    p1,p2,p3,p4,p5=11400714785074694791,14029467366897019727,1609587929392839161,9650029242287828579,2870177450012600261
    def rot(x,n):return ((x<<n)|(x>>(64-n)))&MASK
    def rnd(a,b):return rot((a+b*p2)&MASK,31)*p1&MASK
    def merge(a,b):return ((a^rnd(0,b))*p1+p4)&MASK
    pos=0;n=len(data)
    if n>=32:
        v=[(seed+p1+p2)&MASK,(seed+p2)&MASK,seed&MASK,(seed-p1)&MASK]
        while pos<=n-32:
            for j in range(4):v[j]=rnd(v[j],int.from_bytes(data[pos+8*j:pos+8*j+8],'little'))
            pos+=32
        result=sum(rot(x,k) for x,k in zip(v,[1,7,12,18]))&MASK
        for x in v:result=merge(result,x)
    else:result=(seed+p5)&MASK
    result=(result+n)&MASK
    while pos+8<=n:
        result=rot(result^rnd(0,int.from_bytes(data[pos:pos+8],'little')),27)
        result=(result*p1+p4)&MASK;pos+=8
    if pos+4<=n:
        result=rot(result^(int.from_bytes(data[pos:pos+4],'little')*p1&MASK),23)
        result=(result*p2+p3)&MASK;pos+=4
    while pos<n:
        result=rot(result^(data[pos]*p5&MASK),11)*p1&MASK;pos+=1
    result^=result>>33;result=result*p2&MASK;result^=result>>29;result=result*p3&MASK
    return result^(result>>32)


def legacy_oracle(case):
    if case in CASES[:6]:return int(oracle_stdout(case,1))
    data=input_bytes(case)
    if case.startswith('xxhash_'):return xxh64(data)
    if case.startswith('jsmn_'):
        value=BASIS
        for token in json_tokens(data):
            for field in token:value=(value^field)*PRIME&MASK
        return value
    if case.startswith('lz4_'):
        path=ctypes.util.find_library('lz4')
        if not path:raise ValueError('Independent system LZ4 oracle unavailable')
        lib=ctypes.CDLL(path);lib.LZ4_compressBound.argtypes=[ctypes.c_int]
        lib.LZ4_compress_default.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_int,ctypes.c_int]
        lib.LZ4_decompress_safe.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_int,ctypes.c_int]
        bound=lib.LZ4_compressBound(len(data));packed=ctypes.create_string_buffer(bound)
        size=lib.LZ4_compress_default(data,packed,len(data),bound);plain=ctypes.create_string_buffer(len(data))
        out=lib.LZ4_decompress_safe(packed,plain,size,len(data))
        if size<1 or out!=len(data) or plain.raw!=data:raise ValueError('LZ4 oracle round trip failed')
        return size*33+packed.raw[size//2]
    raise ValueError('Unregistered oracle')


def pins():
    result={k:{**v,'archive':str(ROOT/'data/processed/real_sources'/v['archive'])} for k,v in OLD_SOURCES.items()}
    result.update(json.loads((ROOT/'results/invocation_source_pins.json').read_text()))
    result.update(json.loads((ROOT/'results/broad_source_pins.json').read_text()))
    return result


def sources_for(program,directory):
    pin=pins()[program];archive=Path(pin['archive'])
    if sha(archive)!=pin['sha256']:raise ValueError('Pinned source archive changed')
    if program=='zlib':names=[f'{x}.c' for x in ['adler32','crc32','compress','uncompr','deflate','trees','zutil','inflate','inftrees','inffast']];sub=''
    elif program=='lua':names=None;sub='src/'
    elif program=='expat':names=['xmlparse.c','xmlrole.c','xmltok.c'];sub='expat/lib/'
    elif program=='lz4':names=['lz4.c'];sub='lib/'
    elif program=='xxhash':names=['xxhash.c'];sub=''
    elif program=='bzip2':names=[x+'.c' for x in ['blocksort','huffman','crctable','randtable','compress','decompress','bzlib']];sub=''
    elif program=='blake2':names=['blake2b-ref.c'];sub='ref/'
    elif program=='cjson':names=['cJSON.c'];sub=''
    elif program=='inih':names=['ini.c'];sub=''
    elif program=='tinyexpr':names=['tinyexpr.c'];sub=''
    elif program=='parson':names=['parson.c'];sub=''
    elif program=='picohttp':names=['picohttpparser.c'];sub=''
    else:names=[];sub=''
    dest=directory/'upstream';dest.mkdir()
    prefix=pin['root']+'/'+sub
    with tarfile.open(archive) as t:
        members=[m for m in t.getmembers() if m.isfile() and m.name.startswith(prefix)
                 and '/' not in m.name[len(prefix):] and m.name.endswith(('.c','.h'))]
        for member in members:
            relative=member.name[len(prefix):]
            if relative in ('','..') or not re.fullmatch(r'[A-Za-z0-9_.-]+',relative):raise ValueError('Unsafe source member')
            (dest/relative).write_bytes(t.extractfile(member).read())
    if names is None:names=sorted(p.name for p in dest.glob('*.c') if p.name not in ('lua.c','luac.c'))
    flags=['-DLUA_USE_LINUX'] if program=='lua' else []
    if program=='expat':(dest/'expat_config.h').write_text(EXPAT_CONFIG);flags=['-DHAVE_EXPAT_CONFIG_H']
    return [dest/n for n in names],dest,flags


def compile_program(program,worker_path):
    directory=BASE/'programs'/program;directory.mkdir(parents=True,exist_ok=False)
    sources,include,extra=sources_for(program,directory)
    driver=directory/'driver.c';driver.write_text(DRIVERS[program]);sources.append(driver)
    frontend=['-fPIC','-march=native','-ffp-contract=off','-fno-discard-value-names','-O1','-Xclang','-disable-llvm-passes']
    initial=directory/'initial.bc';artifacts={}
    from src.benchmarks.invocation import BASE as PRIOR_BASE, PROGRAMS as PRIOR_PROGRAMS
    prior=None
    if program in PRIOR_PROGRAMS:
        prior=json.loads((PRIOR_BASE/'programs'/program/'manifest.json').read_text())
        if sha(prior['initial'])!=prior['initial_sha256']:raise ValueError('Prior initial bitcode changed')
        for p,h in prior['sources'].items():
            if sha(p)!=h:raise ValueError('Prior upstream source changed')
            candidate=driver if Path(p).name=='driver.c' else include/Path(p).name
            if not candidate.is_file() or sha(candidate)!=h:raise ValueError('New/prior source differs')
        shutil.copy2(prior['initial'],initial)
    else:
        units=[]
        for i,source in enumerate(sources):
            out=directory/f'unit{i}.bc';tool([TOOLS/'clang',*frontend,*extra,'-I'+str(include),'-emit-llvm','-c',source,'-o',out]);units.append(out)
        tool([TOOLS/'llvm-link',*units,'-o',initial])
    for c,args in {'reference_O0':['-passes=default<O0>'],**MENU}.items():
        bc=directory/(c+'.bc');so=directory/(c+'.so');tool([TOOLS/'opt',*args,initial,'-o',bc])
        tool([TOOLS/'clang','-fPIC','-march=native','-ffp-contract=off','-O3','-Xclang','-disable-llvm-passes',
              '-shared','-Wl,-Bsymbolic',bc,'-lm','-ldl','-o',so])
        artifacts[c]={'bc':str(bc),'so':str(so),'bc_sha256':sha(bc),'so_sha256':sha(so)}
        if c!='reference_O0':
            copy=directory/(c+'_copy.so');shutil.copy2(so,copy)
            artifacts[c+'_copy']={**artifacts[c],'so':str(copy)}
    aliases={c:next(k for k in MENU if artifacts[c]['so_sha256']==artifacts[k]['so_sha256']) for c in MENU}
    m={'program':program,'artifacts':artifacts,'aliases':aliases,'worker':str(worker_path),'worker_sha256':sha(worker_path),
       'worker_source_sha256':sha(ROOT/'src/benchmarks/invocation_worker.c'),
       'source_pin':pins()[program],'initial':str(initial),'initial_sha256':sha(initial),
       'sources':{str(p):sha(p) for p in [driver,*include.glob('*')] if p.is_file()}}
    m['features']=extract_features(m);save(directory/'manifest.json',m);return m


def extract_features(m):
    parsed={c:parse_ir(tool([TOOLS/'llvm-dis',m['artifacts'][c]['bc'],'-o','-']).decode()) for c in MENU}
    base_size=Path(m['artifacts']['O3']['so']).stat().st_size
    extra=input_features(Path(m['input']).read_bytes()) if 'input' in m else []
    return {c:candidate_vector(parsed['O3'],parsed[c],c,0,1,
        (Path(m['artifacts'][c]['so']).stat().st_size-base_size)/base_size,entrypoint='nc_benchmark_main')[:-3]
        +[float(c==other) for other in list(MENU)[1:]]+extra for c in MENU if c!='O3'}


def compile_worker():
    BASE.mkdir(parents=True,exist_ok=True);path=BASE/'invocation_worker.out'
    tool([TOOLS/'clang','-O2','-rdynamic',ROOT/'src/benchmarks/invocation_worker.c','-ldl','-lm','-o',path]);return path


def check_declaration():
    path=ROOT/'results/broad_declaration.json'
    d=json.loads(path.read_text())
    if d['protocol']!=PROTOCOL or d['source_pins']!=pins():raise ValueError('Changed declared experiment')
    for name,digest in d['source_sha256'].items():
        if sha(ROOT/name)!=digest or sha(BASE/'declared_sources'/name)!=digest:
            raise ValueError('Frozen source changed '+name)
    return d


def validate_cell(row,m,pairs,repetitions,first,placement=False):
    if row['granularity']!='one_invocation' or row['pairs']!=pairs or row['repetitions']!=repetitions or row['first']!=first:
        raise ValueError('Worker metadata changed')
    if len(row['samples'])!=pairs:raise ValueError('Incomplete raw pairs')
    if placement and row['left_entry_address']==row['right_entry_address']:raise ValueError('Control shares code placement')
    for p,s in enumerate(row['samples']):
        start=((p%2)==0)==first
        counts=(repetitions//2+int(repetitions%2 and start),repetitions//2+int(repetitions%2 and not start))
        if s['pair']!=p or s['left_first']!=start or (s['left_first_invocations'],s['right_first_invocations'])!=counts:
            raise ValueError('Invocation ordering changed')
        for side in ['left','right']:
            value=s[side]
            if {k:value[k] for k in m['expected']}!=m['expected']:raise ValueError('Output differs from independent oracle')
            if any(not math.isfinite(value[k]) or value[k]<=0 for k in ['cpu_seconds','wall_seconds']):raise ValueError('Invalid native clock')


def run_cell(m,left,right,block,role,pairs=None,repetitions=None):
    pairs=PROTOCOL['pairs'] if pairs is None else pairs
    repetitions=m['repetitions'] if repetitions is None else repetitions
    seed=PROTOCOL['seed']+int(hashlib.sha256(f"{m['id']}:{left}:{right}:{role}:{block}".encode()).hexdigest()[:8],16)
    first=bool(np.random.default_rng(seed).integers(2));before=scheduler_ticks(PROTOCOL['cpu']);begin=time.perf_counter_ns()
    cmd=['taskset','-c',str(PROTOCOL['cpu']),m['worker'],m['artifacts'][left]['so'],m['artifacts'][right]['so'],
         str(repetitions),str(pairs),str(int(first))]
    if 'input' in m:cmd.append(m['input'])
    result=subprocess.run(cmd,capture_output=True,check=True,timeout=240)
    after=scheduler_ticks(PROTOCOL['cpu']);row=json.loads(result.stdout)
    validate_cell(row,m,pairs,repetitions,first,placement=role in ('qualification','candidate_control'))
    row.update({'case':m['id'],'left':left,'right':right,'choice':right if role=='effect' else left,
        'role':role,'block':block,'process_elapsed_seconds':(time.perf_counter_ns()-begin)*1e-9,
        'scheduler_delta':{k:after[k]-before[k] for k in before}})
    return row


def prepare_case(case,program):
    m=dict(program);m['id']=case;m['family']=m['program'];m['split']='train' if case in CASES else 'development'
    directory=BASE/'inputs';directory.mkdir(exist_ok=True);path=directory/(case+'.dat');path.write_bytes(input_bytes(case))
    m.update({'input':str(path),'input_sha256':sha(path),'repetitions':1})
    m['features']={c:v+input_features(path.read_bytes()) for c,v in program['features'].items()}
    m['oracle_value_hex']=f'{oracle(case):016x}'
    m['expected']={'checksum':f'{(BASIS^int(m["oracle_value_hex"],16))*PRIME&MASK:016x}','values':1}
    m['correctness']={c:run_cell(m,'reference_O0',c,0,'correctness',pairs=1,repetitions=1) for c in MENU}
    m['calibration']=run_cell(m,'O3','O3_copy',0,'calibration',pairs=3,repetitions=1)
    cal=m['calibration'];duration=float(np.median([s[t]['cpu_seconds'] for s in cal['samples'] for t in ['left','right']]))
    m['eligible']=duration>=PROTOCOL['minimum_cpu_seconds_per_invocation']
    m['repetitions']=min(PROTOCOL['max_repetitions'],max(1,math.ceil(PROTOCOL['batch_target_cpu_seconds']/duration)))
    return m


def clock_effect(rows,clock):
    if clock not in ('cpu','wall'):raise ValueError('Unknown clock')
    return effect([{'left_seconds':[s['left'][clock+'_seconds'] for s in r['samples']],
                    'right_seconds':[s['right'][clock+'_seconds'] for s in r['samples']]} for r in rows],PROTOCOL)


def summarize(raw):
    labels=[];diagnostics={}
    for case,m in raw['manifests'].items():
        rows=[r for r in raw['records'] if r['case']==case];q=[r for r in rows if r['role']=='qualification']
        if len(q)!=PROTOCOL['blocks']:continue
        controls={clock:clock_effect(q,clock) for clock in ['cpu','wall']}
        stats={'O3':{'speedup':1.,'log_speedup':0.,'interval':[1.,1.],'confirmed_gain':False}}
        measurements={}
        for c in raw.get('active_choices',{}).get(case,list(MENU)):
            alias=m['aliases'][c]
            if alias in stats:stats[c]=dict(stats[alias]);continue
            cc=[r for r in rows if r['role']=='candidate_control' and r['choice']==alias]
            ec=[r for r in rows if r['role']=='effect' and r['choice']==alias]
            if len(cc)!=PROTOCOL['blocks'] or len(ec)!=PROTOCOL['blocks']:continue
            detail={}
            for clock in ['cpu','wall']:
                control=clock_effect(cc,clock);s=clock_effect(ec,clock)
                valid=controls[clock]['control_pass'] and control['control_pass']
                s['qualified']=bool(valid);s['confirmed_gain']=bool(valid and s['interval'][0]>1.03 and all(v>1.03 for v in s['blocks']))
                detail[clock]={'effect':s,'control':control}
            measurements[c]=detail
            if detail['cpu']['effect']['qualified']:stats[c]=detail['cpu']['effect']
        diagnostics[case]={'baseline_controls':controls,'measurements':measurements}
        if controls['cpu']['control_pass']:
            labels.append({'case':case,'family':m['program'],'program':m['program'],'aliases':m['aliases'],
                'features':m['features'],'outcomes':stats})
    return labels,diagnostics


# New implementations have independent semantic oracles. Timers bracket library
# work; result traversal/round-trip validation stays outside them where possible.
HASH_C=r'''
static uint64_t feed(uint64_t h,uint64_t v){return (h^v)*UINT64_C(1099511628211);}
static uint64_t string_hash(uint64_t h,const char *s,size_t n){h=feed(h,n);for(size_t i=0;i<n;i++)h=feed(h,(unsigned char)s[i]);return h;}
'''
DRIVERS.update({
'bzip2':COMMON+r'''#include "bzlib.h"
int nc_benchmark_main(int argc,char **argv){
 prepare(argc,argv);unsigned int bound=(unsigned int)(length+length/100+601),size=bound,out=(unsigned int)length;
 char *packed=malloc(bound),*plain=malloc(length);if(!packed||!plain)return 2;
 START();int a=BZ2_bzBuffToBuffCompress(packed,&size,(char *)input,(unsigned int)length,6,0,30);
 int b=BZ2_bzBuffToBuffDecompress(plain,&out,packed,size,0,0);STOP();
 if(a!=BZ_OK||b!=BZ_OK||out!=length||memcmp(plain,input,length))return 3;
 nc_emit_u64((uint64_t)size*33u+(unsigned char)packed[size/2]);free(packed);free(plain);return 0;
}
''',
'blake2':COMMON+HASH_C+r'''#include "blake2.h"
int nc_benchmark_main(int argc,char **argv){prepare(argc,argv);unsigned char digest[64];
 START();int rc=blake2b(digest,sizeof(digest),input,length,NULL,0);STOP();if(rc)return 3;
 uint64_t h=UINT64_C(1469598103934665603);for(int i=0;i<64;i++)h=feed(h,digest[i]);nc_emit_u64(h);return 0;}
''',
'inih':COMMON+HASH_C+r'''#include "ini.h"
static int handler(void *p,const char *section,const char *name,const char *value){uint64_t *h=p;
 *h=string_hash(*h,section,strlen(section));*h=string_hash(*h,name,strlen(name));*h=string_hash(*h,value,strlen(value));return 1;}
int nc_benchmark_main(int argc,char **argv){prepare(argc,argv);uint64_t h=UINT64_C(1469598103934665603);
 START();int rc=ini_parse_string((const char *)input,handler,&h);STOP();if(rc)return 3;nc_emit_u64(h);return 0;}
''',
'tinyexpr':COMMON+r'''#include "tinyexpr.h"
#include <math.h>
static char *text;static char **expressions;static size_t count;
static void prepare_expressions(void){if(text)return;text=malloc(length+1);expressions=malloc((length+1)*sizeof(char *));
 if(!text||!expressions)exit(2);memcpy(text,input,length+1);expressions[count++]=text;
 for(size_t i=0;i<length;i++)if(text[i]=='\n'){text[i]=0;if(i+1<length)expressions[count++]=text+i+1;}}
int nc_benchmark_main(int argc,char **argv){prepare(argc,argv);prepare_expressions();uint64_t sum=0;
 START();for(size_t i=0;i<count;i++){int error=0;double v=te_interp(expressions[i],&error);
 if(error||!isfinite(v)||v<0||v>1e12)return 3;sum+=(uint64_t)v;}STOP();nc_emit_u64(sum);return 0;}
''',
'cjson':COMMON+HASH_C+r'''#include "cJSON.h"
static uint64_t walk(uint64_t h,const cJSON *v){
 if(cJSON_IsNull(v))return feed(h,1);
 if(cJSON_IsBool(v))return feed(feed(h,2),cJSON_IsTrue(v));
 if(cJSON_IsNumber(v))return feed(feed(h,3),(uint64_t)(int64_t)v->valuedouble);
 if(cJSON_IsString(v))return string_hash(feed(h,4),v->valuestring,strlen(v->valuestring));
 if(cJSON_IsArray(v)){h=feed(h,5);h=feed(h,(uint64_t)cJSON_GetArraySize(v));for(const cJSON *p=v->child;p;p=p->next)h=walk(h,p);return h;}
 if(cJSON_IsObject(v)){h=feed(h,6);h=feed(h,(uint64_t)cJSON_GetArraySize(v));for(const cJSON *p=v->child;p;p=p->next){h=string_hash(h,p->string,strlen(p->string));h=walk(h,p);}return h;}
 exit(3);}
int nc_benchmark_main(int argc,char **argv){prepare(argc,argv);START();cJSON *v=cJSON_ParseWithLength((const char *)input,length+1);STOP();
 if(!v)return 3;uint64_t h=walk(UINT64_C(1469598103934665603),v);cJSON_Delete(v);nc_emit_u64(h);return 0;}
''',
'parson':COMMON+HASH_C+r'''#include "parson.h"
static uint64_t walk(uint64_t h,const JSON_Value *v){
 switch(json_value_get_type(v)){
 case JSONNull:return feed(h,1);
 case JSONBoolean:return feed(feed(h,2),json_value_get_boolean(v));
 case JSONNumber:return feed(feed(h,3),(uint64_t)(int64_t)json_value_get_number(v));
 case JSONString:{const char *s=json_value_get_string(v);return string_hash(feed(h,4),s,strlen(s));}
 case JSONArray:{JSON_Array *a=json_value_get_array(v);size_t n=json_array_get_count(a);h=feed(feed(h,5),n);
  for(size_t i=0;i<n;i++)h=walk(h,json_array_get_value(a,i));return h;}
 case JSONObject:{JSON_Object *o=json_value_get_object(v);size_t n=json_object_get_count(o);h=feed(feed(h,6),n);
  for(size_t i=0;i<n;i++){const char *s=json_object_get_name(o,i);h=string_hash(h,s,strlen(s));h=walk(h,json_object_get_value(o,s));}return h;}
 default:exit(3);}}
int nc_benchmark_main(int argc,char **argv){prepare(argc,argv);START();JSON_Value *v=json_parse_string((const char *)input);STOP();
 if(!v)return 3;uint64_t h=walk(UINT64_C(1469598103934665603),v);json_value_free(v);nc_emit_u64(h);return 0;}
''',
'picohttp':COMMON+HASH_C+r'''#include "picohttpparser.h"
static size_t *offsets,*sizes,count;
typedef struct {const char *method,*path;size_t method_n,path_n,n;int version,consumed;struct phr_header headers[64];} parsed;
static void prepare_requests(void){if(offsets)return;offsets=malloc((length+1)*sizeof(size_t));sizes=malloc((length+1)*sizeof(size_t));
 if(!offsets||!sizes)exit(2);size_t off=0;while(off<length){char *end=strstr((char *)input+off,"\r\n\r\n");if(!end)exit(2);
  size_t n=(size_t)(end-(char *)input-off)+4;offsets[count]=off;sizes[count++]=n;off+=n;}}
int nc_benchmark_main(int argc,char **argv){prepare(argc,argv);prepare_requests();parsed *out=malloc(count*sizeof(*out));if(!out)return 2;
 START();for(size_t i=0;i<count;i++){parsed *p=out+i;p->n=64;p->consumed=phr_parse_request((const char *)input+offsets[i],sizes[i],
  &p->method,&p->method_n,&p->path,&p->path_n,&p->version,p->headers,&p->n,0);}STOP();
 uint64_t h=UINT64_C(1469598103934665603);for(size_t i=0;i<count;i++){parsed *p=out+i;if(p->consumed!=(int)sizes[i])return 3;
  h=feed(h,p->version);h=string_hash(h,p->method,p->method_n);h=string_hash(h,p->path,p->path_n);h=feed(h,p->n);
  for(size_t j=0;j<p->n;j++){h=string_hash(h,p->headers[j].name,p->headers[j].name_len);h=string_hash(h,p->headers[j].value,p->headers[j].value_len);}}
 nc_emit_u64(h);free(out);return 0;}
'''})


def input_bytes(case):
    program=case.split('_')[0]
    if program in ['zlib','expat','lua','lz4','jsmn']:return legacy_input_bytes(case)
    if program in ['blake2','bzip2']:
        size=4*1024*1024 if program=='blake2' else 256*1024
        if case.endswith('random'):return np.random.default_rng(20261102).integers(0,256,size,dtype=np.uint8).tobytes()
        if case.endswith('pattern'):
            phrase=b'Broader independently pinned native library corpus 0123456789\n'
            return (phrase*(size//len(phrase)+1))[:size]
    if program in ['cjson','parson']:
        data=[{'id':i,'name':f'item{i}','values':[i,i*7,True,None]} for i in range(3000)]
        if case.endswith('nested'):data={'records':data,'meta':{'enabled':False,'groups':[[i,i+1] for i in range(1000)]}}
        return json.dumps(data,separators=(',',':')).encode()
    if program=='inih':
        count=1 if case.endswith('flat') else 50
        return ''.join(f'[section{s}]\n'+''.join(f'key{i} = value{s}_{i}\n' for i in range(5000//count)) for s in range(count)).encode()
    if program=='tinyexpr':
        if case.endswith('arithmetic'):return ''.join(f'({i}+17)*13+({i}%97)\n'.replace(f'({i}%97)',str(i%97)) for i in range(1,5001)).encode()
        return ''.join(f'sqrt({i*i})+pow({i%50+1},2)+abs(-{i%37})\n' for i in range(1,5001)).encode()
    if program=='picohttp':
        headers=2 if case.endswith('short') else 20
        return ''.join(f'GET /resource/{i}?v={i%17} HTTP/1.1\r\nHost: example.test\r\n'+
          ''.join(f'X-Field-{j}: value{i}_{j}\r\n' for j in range(headers))+ '\r\n' for i in range(2000)).encode()
    raise ValueError('Unregistered broader input '+case)


def feed(h,v):return (h^(v&MASK))*PRIME&MASK


def string_hash(h,s):
    b=s.encode() if isinstance(s,str) else s
    h=feed(h,len(b))
    for value in b:h=feed(h,value)
    return h


def semantic_json(value,h=BASIS):
    if value is None:return feed(h,1)
    if isinstance(value,bool):return feed(feed(h,2),int(value))
    if isinstance(value,int):return feed(feed(h,3),value)
    if isinstance(value,str):return string_hash(feed(h,4),value)
    if isinstance(value,list):
        h=feed(feed(h,5),len(value))
        for child in value:h=semantic_json(child,h)
        return h
    if isinstance(value,dict):
        h=feed(feed(h,6),len(value))
        for key,child in value.items():h=semantic_json(child,string_hash(h,key))
        return h
    raise ValueError('Unsupported JSON semantic value')


def oracle(case):
    program=case.split('_')[0];data=input_bytes(case)
    if program in ['zlib','expat','lua','lz4','jsmn']:return legacy_oracle(case)
    if program=='bzip2':
        packed=bz2.compress(data,compresslevel=6)
        if bz2.decompress(packed)!=data:raise ValueError('Independent BZip2 round trip failed')
        return len(packed)*33+packed[len(packed)//2]
    if program=='blake2':
        h=BASIS
        for byte in hashlib.blake2b(data).digest():h=feed(h,byte)
        return h
    if program in ['cjson','parson']:return semantic_json(json.loads(data))
    if program=='inih':
        cfg=configparser.ConfigParser(interpolation=None);cfg.optionxform=str;cfg.read_file(io.StringIO(data.decode()))
        h=BASIS
        for section in cfg.sections():
            for key,value in cfg.items(section):
                for field in [section,key,value]:h=string_hash(h,field)
        return h
    if program=='tinyexpr':
        if case.endswith('arithmetic'):return sum((i+17)*13+i%97 for i in range(1,5001))
        return sum(i+(i%50+1)**2+i%37 for i in range(1,5001))
    if program=='picohttp':
        h=BASIS
        for request in data.decode('ascii').split('\r\n\r\n')[:-1]:
            first,*headers=request.split('\r\n');method,path,version=first.split(' ')
            if version!='HTTP/1.1':raise ValueError('Unexpected request version')
            h=string_hash(string_hash(feed(h,1),method),path);h=feed(h,len(headers))
            for header in headers:
                name,value=header.split(':',1);h=string_hash(string_hash(h,name),value.strip())
        return h
    raise ValueError('Unregistered broader oracle')


def verify(raw,artifacts=True):
    if raw['protocol']!=PROTOCOL or raw['source_pins']!=pins():raise ValueError('Protocol/source pins changed')
    declaration=ROOT/'results/broad_declaration.json'
    if artifacts:check_declaration()
    if artifacts and raw['declaration_sha256']!=sha(declaration):raise ValueError('Declaration changed')
    allowed=CASES if raw['split']=='train' else DEVELOPMENT
    if not set(raw['manifests']).isdisjoint(raw['failures']) or not (set(raw['manifests'])|set(raw['failures']))<=set(allowed):
        raise ValueError('Invalid corpus coverage')
    if raw['complete'] and set(raw['manifests'])|set(raw['failures'])!=set(allowed):raise ValueError('Incomplete corpus')
    verified_programs={};seen=set()
    for case,m in raw['manifests'].items():
        if case!=m['id'] or case.split('_')[0]!=m['program'] or m['split']!=raw['split']:raise ValueError('Changed original program grouping')
        if artifacts:
            if Path(m['input']).read_bytes()!=input_bytes(case) or sha(m['input'])!=m['input_sha256']:raise ValueError('Frozen input changed')
            expected={'checksum':f'{(BASIS^oracle(case))*PRIME&MASK:016x}','values':1}
            if expected!=m['expected'] or m['oracle_value_hex']!=f'{oracle(case):016x}':raise ValueError('Independent oracle changed')
            shared={k:m[k] for k in ['artifacts','aliases','worker','worker_sha256','worker_source_sha256','source_pin','initial','initial_sha256','sources']}
            if m['program'] not in verified_programs:
                if sha(m['worker'])!=m['worker_sha256'] or sha(ROOT/'src/benchmarks/invocation_worker.c')!=m['worker_source_sha256']:raise ValueError('Worker changed')
                if m['source_pin']!=pins()[m['program']] or sha(m['source_pin']['archive'])!=m['source_pin']['sha256']:raise ValueError('Source archive changed')
                if sha(m['initial'])!=m['initial_sha256'] or any(sha(p)!=h for p,h in m['sources'].items()):raise ValueError('Compiled source changed')
                driver=Path(m['initial']).parent/'driver.c'
                if driver.read_text()!=DRIVERS[m['program']]:raise ValueError('Driver changed')
                for a in m['artifacts'].values():
                    if sha(a['bc'])!=a['bc_sha256'] or sha(a['so'])!=a['so_sha256']:raise ValueError('Native artifact changed')
                if extract_features(m)!=m['features']:raise ValueError('Static features changed')
                verified_programs[m['program']]={'shared':shared,'features':{c:v[:-4] for c,v in m['features'].items()}}
            else:
                stored=verified_programs[m['program']]
                if stored['shared']!=shared or m['features']!={c:v+input_features(Path(m['input']).read_bytes()) for c,v in stored['features'].items()}:
                    raise ValueError('Input variant changed shared program/feature evidence')
        for c in MENU:
            a=next(k for k in MENU if m['artifacts'][c]['so_sha256']==m['artifacts'][k]['so_sha256'])
            if m['aliases'][c]!=a or m['artifacts'][c+'_copy']['so_sha256']!=m['artifacts'][c]['so_sha256']:raise ValueError('Executable alias/copy changed')
        if set(m['correctness'])!=set(MENU):raise ValueError('Incomplete correctness coverage')
        for c,row in m['correctness'].items():
            if row['left']!='reference_O0' or row['right']!=c or row['role']!='correctness':raise ValueError('Changed correctness comparison')
            validate_cell(row,m,1,1,row['first'])
        cal=m['calibration'];validate_cell(cal,m,3,1,cal['first'])
        duration=float(np.median([s[t]['cpu_seconds'] for s in cal['samples'] for t in ['left','right']]))
        reps=min(PROTOCOL['max_repetitions'],max(1,math.ceil(PROTOCOL['batch_target_cpu_seconds']/duration)))
        if m['repetitions']!=reps or m['eligible']!=(duration>=PROTOCOL['minimum_cpu_seconds_per_invocation']):raise ValueError('Calibration/admission changed')
    for r in raw['records']:
        m=raw['manifests'][r['case']];c=r['choice'];role=r['role'];key=(r['case'],c,role,r['block'])
        if key in seen or not m['eligible'] or r['block'] not in range(PROTOCOL['blocks']):raise ValueError('Invalid timing coverage')
        seen.add(key)
        expected=('O3','O3_copy') if role=='qualification' else ((c,c+'_copy') if role=='candidate_control' else ('O3',c))
        if role not in ('qualification','candidate_control','effect') or (r['left'],r['right'])!=expected:raise ValueError('Changed comparison')
        if c not in MENU or m['aliases'][c]!=c or (role=='qualification' and c!='O3'):raise ValueError('Invalid candidate')
        validate_cell(r,m,PROTOCOL['pairs'],m['repetitions'],r['first'],placement=role!='effect')
        seed=PROTOCOL['seed']+int(hashlib.sha256(f"{m['id']}:{r['left']}:{r['right']}:{role}:{r['block']}".encode()).hexdigest()[:8],16)
        if r['first']!=bool(np.random.default_rng(seed).integers(2)):raise ValueError('Declared timing order changed')
        if not math.isfinite(r['process_elapsed_seconds']) or r['process_elapsed_seconds']<=0 or any(v<0 for v in r['scheduler_delta'].values()):raise ValueError('Invalid scheduler/process evidence')
    labels,diagnostics=summarize(raw)
    if raw['split']=='development' and 'frozen_decisions' in raw:
        active={case:['O3',d['choice']] if d['choice']!='O3' else ['O3'] for case,d in raw['frozen_decisions'].items()}
        if raw.get('active_choices')!=active or set(active)!=set(raw['manifests']):raise ValueError('Frozen development scope changed')
    if raw['complete']:
        expected=set()
        for case,m in raw['manifests'].items():
            if not m['eligible']:continue
            for block in range(PROTOCOL['blocks']):expected.add((case,'O3','qualification',block))
            if not diagnostics[case]['baseline_controls']['cpu']['control_pass']:continue
            for c in raw.get('active_choices',{}).get(case,list(MENU)):
                if c!='O3' and m['aliases'][c]==c:
                    for block in range(PROTOCOL['blocks']):
                        for role in ['candidate_control','effect']:expected.add((case,c,role,block))
        if seen!=expected:raise ValueError('Incomplete/extra timing records')
    if 'labels' in raw and raw['labels']!=labels:raise ValueError('Reported labels changed')
    if 'diagnostics' in raw and raw['diagnostics']!=diagnostics:raise ValueError('Reported measurements changed')
    return labels,diagnostics
