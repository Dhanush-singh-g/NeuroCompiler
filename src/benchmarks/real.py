"""Pinned upstream applications with deterministic training-only workloads."""
import hashlib
import subprocess
import tarfile
from pathlib import Path

import numpy as np

from src.benchmarks.compact import CODEGEN, MENU, PROTOCOL, run, save, sha
from src.benchmarks.kernels import FRONTEND

ROOT = Path("data/processed/real_sources")
SOURCES = {
    "zlib": {"archive": "zlib-1.3.1.tar.gz", "root": "zlib-1.3.1",
        "url": "https://zlib.net/fossils/zlib-1.3.1.tar.gz",
        "sha256": "9a93b2b7dfdac77ceba5a558a580e74667dd6fede4585b91eefb60f03b72df23"},
    "lua": {"archive": "lua-5.4.8.tar.gz", "root": "lua-5.4.8",
        "url": "https://www.lua.org/ftp/lua-5.4.8.tar.gz",
        "sha256": "4f18ddae154e793e46eeab727c59ef1c0c0c2b744e7b94219710d76f530629ae"},
    "expat": {"archive": "expat-2.7.3.tar.gz", "root": "libexpat-R_2_7_3",
        "url": "https://codeload.github.com/libexpat/libexpat/tar.gz/refs/tags/R_2_7_3",
        "sha256": "7c853a76f7c2a562c3edfd84ca47e487d9eff3966786191dfb60cc441daf82d6"},
}
CASES = ["zlib_pattern", "zlib_random", "expat_flat", "expat_nested", "lua_numeric", "lua_tables"]
REAL_PROTOCOL = {"cases": CASES, "sources": SOURCES, "runtime": PROTOCOL,
    "frontend": FRONTEND, "scope": "training only; three original upstream programs, two inputs each",
    "calibration": "O3 only; initial iterations 1; at most three corrections targeting 80 ms; cap 1000000",
    "seed": 20261014, "correctness": "byte-exact stdout; internal zlib round-trip; XML parse and Lua execution must succeed"}

COMMON = r'''#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned char *read_input(const char *path, size_t *length) {
 FILE *f=fopen(path,"rb"); if(!f)exit(2);
 if(fseek(f,0,SEEK_END))exit(2); long n=ftell(f); if(n<1)exit(2); rewind(f);
 unsigned char *p=malloc((size_t)n+1); if(!p)exit(2);
 if(fread(p,1,(size_t)n,f)!=(size_t)n)exit(2); fclose(f); p[n]=0; *length=(size_t)n; return p;
}
'''
DRIVERS = {
"zlib": COMMON + r'''#include "zlib.h"
int main(int argc,char **argv) {
 if(argc!=3)return 2; unsigned n=(unsigned)strtoul(argv[2],0,10); if(!n)return 2;
 size_t length; unsigned char *input=read_input(argv[1],&length);
 uLong bound=compressBound((uLong)length); unsigned char *packed=malloc(bound),*plain=malloc(length);
 if(!packed||!plain)return 2; uint64_t sum=0;
 for(unsigned i=0;i<n;i++) {
  uLongf size=bound,output=length;
  if(compress2(packed,&size,input,length,6)!=Z_OK)return 3;
  if(uncompress(plain,&output,packed,size)!=Z_OK||output!=length||memcmp(input,plain,length))return 4;
  sum+=(uint64_t)size*33u+packed[size/2];
 }
 printf("%llu\n",(unsigned long long)sum); free(input);free(packed);free(plain);return 0;
}
''',
"expat": COMMON + r'''#include "expat.h"
static void start(void *p,const XML_Char *name,const XML_Char **attributes) {
 uint64_t *sum=p; *sum+=17; while(*name)*sum=*sum*33u+(unsigned char)*name++;
 for(;*attributes;attributes++)for(const char *s=*attributes;*s;s++)*sum=*sum*33u+(unsigned char)*s;
}
static void text(void *p,const XML_Char *s,int n) {
 uint64_t *sum=p; for(int i=0;i<n;i++)*sum=*sum*33u+(unsigned char)s[i];
}
int main(int argc,char **argv) {
 if(argc!=3)return 2; unsigned n=(unsigned)strtoul(argv[2],0,10); if(!n)return 2;
 size_t length; unsigned char *input=read_input(argv[1],&length); uint64_t total=0;
 for(unsigned i=0;i<n;i++) {
  uint64_t sum=0; XML_Parser parser=XML_ParserCreate(NULL);if(!parser)return 3;
  if(!XML_SetHashSalt(parser,1))return 3;
  XML_SetUserData(parser,&sum); XML_SetElementHandler(parser,start,NULL); XML_SetCharacterDataHandler(parser,text);
  if(XML_Parse(parser,(const char *)input,(int)length,1)!=XML_STATUS_OK)return 4;
  total+=sum; XML_ParserFree(parser);
 }
 printf("%llu\n",(unsigned long long)total); free(input);return 0;
}
''',
"lua": COMMON + r'''#include "lua.h"
#include "lauxlib.h"
#include "lualib.h"
int main(int argc,char **argv) {
 if(argc!=3)return 2; unsigned n=(unsigned)strtoul(argv[2],0,10); if(!n)return 2;
 size_t length; unsigned char *input=read_input(argv[1],&length); uint64_t total=0;
 for(unsigned i=0;i<n;i++) {
  lua_State *state=luaL_newstate();if(!state)return 3;luaL_openlibs(state);
  if(luaL_loadbuffer(state,(const char *)input,length,"frozen_input")||lua_pcall(state,0,1,0))return 4;
  if(!lua_isinteger(state,-1))return 5;total+=(uint64_t)lua_tointeger(state,-1);lua_close(state);
 }
 printf("%llu\n",(unsigned long long)total);free(input);return 0;
}
''',
}
EXPAT_CONFIG = "\n".join(["#define BYTEORDER 1234", "#define XML_CONTEXT_BYTES 1024", "#define XML_GE 1"] +
    [f"#define {name} 1" for name in ["HAVE_STDINT_H", "HAVE_STDLIB_H", "HAVE_STRING_H", "HAVE_UNISTD_H",
     "HAVE_SYS_TYPES_H", "HAVE_SYS_STAT_H", "HAVE_FCNTL_H", "XML_DTD", "XML_NS", "XML_DEV_URANDOM"]]) + "\n"


def input_bytes(case):
    if case == "zlib_pattern": return (b"NeuroCompiler deterministic compression input 0123456789\n" * 3000)
    if case == "zlib_random":
        state=1234567; data=bytearray()
        for _ in range(131072):
            state=(state*1664525+1013904223)&0xffffffff;data.append(state>>24)
        return bytes(data)
    if case == "expat_flat":
        return ("<root>"+"".join(f'<item id="{i}" class="entry">payload {i} &amp; text</item>' for i in range(3000))+"</root>").encode()
    if case == "expat_nested":
        return ("<root>"+"<section>"*40+"".join(f'<item id="{i}"><name>entry{i}</name><value>{i*13}</value></item>' for i in range(2000))+"</section>"*40+"</root>").encode()
    if case == "lua_numeric":
        return b"local sum=0; for i=1,180000 do sum=(sum+i*17+(i%97))%1000000007 end; return sum\n"
    if case == "lua_tables":
        return b"local a={}; for i=1,12000 do a[i]=(i*7919)%100003 end; table.sort(a); local sum=0; for i,v in ipairs(a) do sum=(sum+v*i)%1000000007 end; return sum\n"
    raise ValueError("Unregistered real workload")


def oracle_stdout(case,iterations):
    """Independent Python/library result for the fixed deterministic inputs.

    Zlib compares a system-library encoding and checks its decompression;
    XML uses Python's Expat binding; Lua scripts use direct Python arithmetic.
    This check runs outside timings and supplements candidate/O3 agreement.
    """
    mask=(1<<64)-1
    if case.startswith('zlib_'):
        import zlib
        data=input_bytes(case);packed=zlib.compress(data,6)
        if zlib.decompress(packed)!=data:raise ValueError('Independent zlib round trip failed')
        value=len(packed)*33+packed[len(packed)//2]
    elif case.startswith('expat_'):
        from xml.parsers import expat
        box=[0];parser=expat.ParserCreate();parser.ordered_attributes=True
        def start(name,attributes):
            box[0]=(box[0]+17)&mask
            for text in [name,*attributes]:
                for c in text:box[0]=(box[0]*33+ord(c))&mask
        def text(value):
            for c in value:box[0]=(box[0]*33+ord(c))&mask
        parser.StartElementHandler=start;parser.CharacterDataHandler=text
        parser.Parse(input_bytes(case),True);value=box[0]
    elif case=='lua_numeric':
        value=0
        for i in range(1,180001):value=(value+i*17+i%97)%1000000007
    elif case=='lua_tables':
        a=sorted((i*7919)%100003 for i in range(1,12001))
        value=sum(v*i for i,v in enumerate(a,1))%1000000007
    else:raise ValueError('Unregistered oracle workload')
    return f'{value*iterations&mask}\n'.encode()


def prepare_program(name):
    """Compile the pinned upstream implementation and explicit driver once."""
    from compiler_gym.third_party import llvm
    spec=SOURCES[name];archive=ROOT/spec['archive']
    if sha(archive)!=spec['sha256']:raise ValueError("Upstream archive checksum mismatch")
    upstream=ROOT/spec['root']
    if not upstream.exists():
        with tarfile.open(archive) as t:t.extractall(ROOT,filter='data')
    directory=(Path('data/processed/real_build')/name).resolve()
    initial=directory/'initial.bc';metadata=directory/'build.json'
    if metadata.exists():
        m=__import__('json').loads(metadata.read_text())
        if sha(initial)!=m['initial_sha256'] or any(sha(p)!=h for p,h in m['sources'].items()):raise ValueError('Source build changed')
        if (directory/'driver.c').read_text()!=DRIVERS[name]:raise ValueError('Driver changed')
        return initial,m
    directory.mkdir(parents=True,exist_ok=True)
    driver=directory/'driver.c';driver.write_text(DRIVERS[name])
    flags=[]
    if name=='zlib':
        sources=[upstream/f'{x}.c' for x in ['adler32','crc32','compress','uncompr','deflate','trees','zutil','inflate','inftrees','inffast']]
        includes=[upstream]
    elif name=='lua':
        sources=sorted(p for p in (upstream/'src').glob('*.c') if p.name not in ['lua.c','luac.c'])
        includes=[upstream/'src'];flags=['-DLUA_USE_LINUX']
    else:
        lib=upstream/'expat/lib';sources=[lib/f'{x}.c' for x in ['xmlparse','xmlrole','xmltok']]
        (directory/'expat_config.h').write_text(EXPAT_CONFIG);includes=[directory,lib];flags=['-DHAVE_EXPAT_CONFIG_H']
    dependencies=set(sources+[driver])
    for folder in includes:
        dependencies.update(folder.glob('*.h'))
        # Expat includes implementation .c files textually from xmltok.c.
        if folder != directory:dependencies.update(folder.glob('*.c'))
    verify_upstream_files(name,dependencies)
    sources.append(driver);objects=[]
    for i,source in enumerate(sources):
        out=directory/f'unit{i}.bc'
        subprocess.run([str(llvm.clang_path()),*FRONTEND,*flags,*[f'-I{p.resolve()}' for p in includes],
            '-emit-llvm','-c',str(source.resolve()),'-o',str(out)],capture_output=True,check=True,timeout=120)
        objects.append(out)
    linker=Path(llvm.opt_path()).with_name('llvm-link')
    subprocess.run([str(linker),*[str(p) for p in objects],'-o',str(initial)],capture_output=True,check=True,timeout=120)
    m={'program':name,'archive_sha256':sha(archive),'initial_sha256':sha(initial),
       'sources':{str(p.resolve()):sha(p) for p in sorted(dependencies)},'flags':flags,'frontend':FRONTEND}
    save(metadata,m);return initial,m


def verify_upstream_files(name,paths):
    spec=SOURCES[name];archive=ROOT/spec['archive'];upstream=(ROOT/spec['root']).resolve()
    if sha(archive)!=spec['sha256']:raise ValueError('Pinned archive changed')
    paths={Path(p) for p in paths}
    for folder in {p.parent for p in paths if p.resolve().is_relative_to(upstream)}:
        paths.update(folder.glob('*.c'));paths.update(folder.glob('*.h'))
    with tarfile.open(archive) as t:
        for p in map(Path,paths):
            if not p.resolve().is_relative_to(upstream):continue
            member=f"{spec['root']}/{p.resolve().relative_to(upstream).as_posix()}"
            original=t.extractfile(member)
            if original is None or p.read_bytes()!=original.read():raise ValueError('Materialized source differs from pinned archive')


def freeze_real(case,directory):
    from compiler_gym.third_party import llvm
    if case not in CASES:raise ValueError('Case outside training protocol')
    name=case.split('_')[0];original,build=prepare_program(name)
    directory=Path(directory).resolve();directory.mkdir(parents=True,exist_ok=False)
    initial=directory/'initial.bc';initial.write_bytes(original.read_bytes())
    inp=directory/'input.dat';inp.write_bytes(input_bytes(case))
    m={'id':case,'program':f'real://{name}','split':'train','arguments':[str(inp),'1'],
       'features':[inp.stat().st_size,1],'inputs':{str(inp):sha(inp)},'outputs':[],
       'source':str(initial),'source_sha256':sha(initial),'build_source':build,'artifacts':{},'aliases':{},'expected_output':None}
    for choice,stages in MENU.items():
        dest=directory/choice;dest.mkdir();current=initial
        for i,flags in enumerate(stages):
            out=dest/f'stage{i}.bc'
            subprocess.run([str(llvm.opt_path()),*flags,str(current),'-o',str(out)],capture_output=True,check=True,timeout=180)
            current=out
        bc=dest/'program.bc';bc.write_bytes(current.read_bytes())
        subprocess.run([str(llvm.clang_path()),str(bc),*CODEGEN,'-lm','-ldl','-o','a.out'],cwd=dest,capture_output=True,check=True,timeout=120)
        m['artifacts'][choice]={'directory':str(dest),'bc_sha256':sha(bc),'elf_sha256':sha(dest/'a.out')}
        m['aliases'][choice]=next(c for c,a in m['artifacts'].items() if a['elf_sha256']==m['artifacts'][choice]['elf_sha256'])
    calibration=[]
    for step in range(4):
        run(m,'O3');times=[run(m,'O3') for _ in range(3)];duration=float(np.median(times))
        calibration.append({'iterations':int(m['arguments'][-1]),'seconds':times})
        if .025<=duration<=.5 or step==3:break
        count=max(1,min(1000000,int(int(m['arguments'][-1])*.08/duration)))
        m['arguments'][-1]=str(count);m['features'][-1]=count
    m['calibration']=calibration;m['eligible']=.025<=duration<=.5
    result=subprocess.run(['./a.out',*m['arguments']],cwd=m['artifacts']['O3']['directory'],capture_output=True,check=True,timeout=300)
    m['expected_output']={'stdout':hashlib.sha256(result.stdout).hexdigest(),'files':{}}
    if result.stdout!=oracle_stdout(case,int(m['arguments'][-1])):raise ValueError('O3 differs from independent workload oracle')
    for choice in MENU:run(m,choice,True);run(m,choice,True)
    save(directory/'manifest.json',m);return m


def verify_real(m,duration_bounds=(.025,.5)):
    case=m['id'];name=case.split('_')[0]
    if case not in CASES or m['program']!=f'real://{name}' or m['split']!='train':raise ValueError('Real program scope changed')
    inp=Path(m['arguments'][0])
    if inp.read_bytes()!=input_bytes(case) or m['inputs']!={str(inp):sha(inp)}:raise ValueError('Real input changed')
    if sha(m['source'])!=m['source_sha256']:raise ValueError('Real source BC changed')
    build=m['build_source']
    if build['archive_sha256']!=SOURCES[name]['sha256'] or any(sha(p)!=h for p,h in build['sources'].items()):raise ValueError('Upstream source changed')
    if build['program']!=name or build['initial_sha256']!=m['source_sha256'] or build['frontend']!=FRONTEND:raise ValueError('Build provenance changed')
    verify_upstream_files(name,build['sources'])
    driver=next(Path(p) for p in build['sources'] if Path(p).name=='driver.c')
    if driver.read_text()!=DRIVERS[name]:raise ValueError('Real driver changed')
    if name=='expat' and (driver.parent/'expat_config.h').read_text()!=EXPAT_CONFIG:raise ValueError('Expat configuration changed')
    cal=m['calibration']
    if not 1<=len(cal)<=4 or any(type(c['iterations']) is not int or not 1<=c['iterations']<=1000000
        or len(c['seconds'])!=3 or not np.isfinite(c['seconds']).all() or min(c['seconds'])<=0 for c in cal):raise ValueError('Invalid calibration')
    if m['arguments'][-1]!=str(cal[-1]['iterations']) or m['features']!=[inp.stat().st_size,cal[-1]['iterations']]:raise ValueError('Workload metadata changed')
    if m['eligible']!=(duration_bounds[0]<=float(np.median(cal[-1]['seconds']))<=duration_bounds[1]):raise ValueError('Eligibility changed')
    if m['expected_output']!={'stdout':hashlib.sha256(oracle_stdout(case,cal[-1]['iterations'])).hexdigest(),'files':{}}:
        raise ValueError('Output reference differs from independent oracle')
    if list(m['artifacts'])!=list(MENU) or set(m['aliases'])!=set(MENU):raise ValueError('Incomplete real menu')
    for c,a in m['artifacts'].items():
        if sha(Path(a['directory'])/'program.bc')!=a['bc_sha256'] or sha(Path(a['directory'])/'a.out')!=a['elf_sha256']:raise ValueError('Real executable changed')
        if m['aliases'][c]!=next(k for k,v in m['artifacts'].items() if v['elf_sha256']==a['elf_sha256']):raise ValueError('Real alias changed')
