"""Independent, deterministic synthetic training kernels, never final tests.

Iterations are calibrated using only O3 duration before candidate effects.
These small kernels expand transformation contexts, not real-world coverage.
"""
import subprocess
from pathlib import Path

from src.benchmarks.compact import CODEGEN, MENU, run, save, sha

PRELUDE = """#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
static uint32_t random_word(uint32_t *s) { *s=*s*1664525u+1013904223u; return *s; }
int main(int argc, char **argv) {
  unsigned iterations=argc>1?(unsigned)strtoul(argv[1],0,10):1;
  uint32_t state=1234567u; uint64_t checksum=0;
"""
KERNELS = {
    "integer_reduction": """uint32_t a[16384]; for(unsigned i=0;i<16384;i++) a[i]=random_word(&state);
      for(unsigned k=0;k<iterations;k++){uint64_t total=0;
      for(unsigned i=0;i<16384;i++) total+=(uint64_t)(a[i]^(k*33u))*((i&7)+1u);
      checksum^=total;}""",
    "stencil": """double a[128][128],b[128][128];
      for(unsigned y=0;y<128;y++)for(unsigned x=0;x<128;x++)a[y][x]=b[y][x]=(random_word(&state)&1023)*.001;
      for(unsigned k=0;k<iterations;k++) {
       for(unsigned y=1;y<127;y++)for(unsigned x=1;x<127;x++)
        b[y][x]=.2*(a[y][x]+a[y-1][x]+a[y+1][x]+a[y][x-1]+a[y][x+1]);
       for(unsigned y=1;y<127;y++)for(unsigned x=1;x<127;x++)a[y][x]=b[y][x];}
      for(unsigned y=0;y<128;y++)for(unsigned x=0;x<128;x++)checksum+=(uint64_t)(a[y][x]*1000000);""",
    "matrix_product": """double a[48][48],b[48][48],c[48][48];
      for(unsigned y=0;y<48;y++)for(unsigned x=0;x<48;x++){a[y][x]=(random_word(&state)&255)*.001;b[y][x]=(random_word(&state)&255)*.001;}
      for(unsigned k=0;k<iterations;k++){
       for(unsigned y=0;y<48;y++)for(unsigned x=0;x<48;x++){
        double sum=0;for(unsigned j=0;j<48;j++)sum+=a[y][j]*b[j][x];c[y][x]=sum;}
       checksum+=(uint64_t)(c[k%48][(k*7)%48]*1000000);a[k%48][k%48]+=.000001;}
      for(unsigned y=0;y<48;y++)for(unsigned x=0;x<48;x++)checksum+=(uint64_t)(c[y][x]*1000000);""",
    "sparse_gather": """uint32_t a[65536],index[65536];
      for(unsigned i=0;i<65536;i++){a[i]=random_word(&state);index[i]=random_word(&state)&65535;}
      for(unsigned k=0;k<iterations;k++){uint64_t total=0;for(unsigned i=0;i<65536;i++)total+=a[index[i]]^(k+i);checksum^=total;}""",
    "polynomial": """double a[8192];for(unsigned i=0;i<8192;i++)a[i]=(random_word(&state)&1023)*.0001;
      for(unsigned k=0;k<iterations;k++){double sum=0;for(unsigned i=0;i<8192;i++){
       double x=a[i]+(k&7)*.00001;sum+=((((((.3*x+.2)*x+.1)*x+.7)*x+.4)*x+.9)*x+.8);}
       checksum+=(uint64_t)(sum*1000000);}""",
    "insertion_sort": """uint32_t a[256];for(unsigned k=0;k<iterations;k++){
      for(unsigned i=0;i<256;i++)a[i]=random_word(&state);
      for(unsigned i=1;i<256;i++){uint32_t value=a[i];unsigned j=i;while(j&&a[j-1]>value){a[j]=a[j-1];j--;}a[j]=value;}
      for(unsigned i=0;i<256;i++)checksum+=(uint64_t)a[i]*(i+1);}""",
    "hash_chain": """uint32_t x=state;for(unsigned k=0;k<iterations;k++){
      for(unsigned i=0;i<16384;i++){x^=x<<13;x^=x>>17;x^=x<<5;x+=i*33u;}checksum+=x;}""",
    "sieve": """unsigned char a[16384];for(unsigned k=0;k<iterations;k++){
      for(unsigned i=0;i<16384;i++)a[i]=1;
      for(unsigned i=2;i*i<16384;i++)if(a[i])for(unsigned j=i*i;j<16384;j+=i)a[j]=0;
      for(unsigned i=2;i<16384;i++)if(a[i])checksum+=i+k;}""",
}
SUFFIX = '\n printf("%llu\\n",(unsigned long long)checksum); return 0; }\n'
FRONTEND = ["-O1", "-Xclang", "-disable-llvm-passes", "-isystem",
            "/usr/lib/gcc/x86_64-linux-gnu/14/include", "-isystem",
            "/usr/include/x86_64-linux-gnu", "-isystem", "/usr/include"]
KERNEL_PROTOCOL = {"cases": list(KERNELS), "menu": MENU, "blocks": 4, "pairs": 10,
                   "cpu": 2, "control_tolerance": .03, "gain_floor": .03,
                   "calibration": "O3 only; initial iterations 512; at most 3 multiplicative duration corrections targeting 80 ms",
                   "seed": 20261011, "scope": "synthetic training only", "frontend": FRONTEND}


def freeze_kernel(name, directory):
    from compiler_gym.third_party import llvm
    if name not in KERNELS:
        raise ValueError("Unknown kernel")
    directory = Path(directory).resolve()
    directory.mkdir(parents=True, exist_ok=False)
    source = directory / "source.c"
    source.write_text(PRELUDE + KERNELS[name] + SUFFIX)
    initial = directory / "initial.bc"
    subprocess.run([str(llvm.clang_path()), *FRONTEND,
                    "-emit-llvm", "-c", str(source), "-o", str(initial)], check=True, capture_output=True)
    m = {"id": name, "program": f"kernel://{name}", "split": "train", "arguments": ["512"],
         "features": [0, 512], "inputs": {}, "outputs": [], "expected_output": None,
         "source": str(initial), "source_sha256": sha(initial), "c_source": str(source),
         "c_sha256": sha(source), "artifacts": {}, "aliases": {}}
    for choice, stages in MENU.items():
        dest = directory / choice
        dest.mkdir()
        current = initial
        for i, flags in enumerate(stages):
            output = dest / f"stage{i}.bc"
            subprocess.run([str(llvm.opt_path()), *flags, str(current), "-o", str(output)], check=True, capture_output=True)
            current = output
        bc = dest / "program.bc"
        bc.write_bytes(current.read_bytes())
        subprocess.run([str(llvm.clang_path()), str(bc), *CODEGEN, "-o", "a.out"], cwd=dest, check=True, capture_output=True)
        m["artifacts"][choice] = {"directory": str(dest), "bc_sha256": sha(bc), "elf_sha256": sha(dest / "a.out")}
        m["aliases"][choice] = next(c for c,a in m["artifacts"].items() if a["elf_sha256"]==m["artifacts"][choice]["elf_sha256"])
    calibration = []
    for step in range(4):
        run(m, "O3")
        times = [run(m, "O3") for _ in range(3)]
        import numpy as np
        duration = float(np.median(times))
        calibration.append({"iterations": int(m["arguments"][0]), "seconds": times})
        if .025 <= duration <= .5 or step == 3:
            break
        iterations = max(1, min(2000000, int(int(m["arguments"][0]) * .08 / duration)))
        m["arguments"] = [str(iterations)]
        m["features"][-1] = iterations
    m["calibration"] = calibration
    m["eligible"] = .025 <= duration <= .5
    reference = subprocess.run(["./a.out", *m["arguments"]], cwd=m["artifacts"]["O3"]["directory"],
                               capture_output=True, check=True)
    import hashlib
    m["expected_output"] = {"stdout": hashlib.sha256(reference.stdout).hexdigest(), "files": {}}
    for choice in MENU:
        run(m, choice, True)
        run(m, choice, True)
    save(directory / "manifest.json", m)
    return m


def verify_kernel(m):
    if m["id"] not in KERNELS or m["program"] != f"kernel://{m['id']}" or m["split"] != "train":
        raise ValueError("Kernel scope mismatch")
    if sha(m["source"]) != m["source_sha256"] or sha(m["c_source"]) != m["c_sha256"]:
        raise ValueError("Kernel source changed")
    if Path(m["c_source"]).read_text() != PRELUDE + KERNELS[m["id"]] + SUFFIX:
        raise ValueError("Kernel definition changed")
    if list(m['artifacts']) != list(MENU) or set(m['aliases']) != set(MENU):
        raise ValueError('Incomplete kernel menu')
    calibration=m['calibration']
    import numpy as np
    if not calibration or len(calibration)>4 or any(len(c['seconds'])!=3 or not np.isfinite(c['seconds']).all() or any(t<=0 for t in c['seconds']) for c in calibration):
        raise ValueError('Invalid duration calibration')
    if m['arguments']!=[str(calibration[-1]['iterations'])] or m['features']!=[0,calibration[-1]['iterations']]:
        raise ValueError('Kernel workload metadata changed')
    if m['eligible'] != (.025<=float(np.median(calibration[-1]['seconds']))<=.5):
        raise ValueError('Kernel eligibility changed')
    for c,a in m["artifacts"].items():
        if sha(Path(a["directory"])/"program.bc") != a["bc_sha256"] or sha(Path(a["directory"])/"a.out") != a["elf_sha256"]:
            raise ValueError("Frozen kernel changed")
        alias = next(k for k,v in m["artifacts"].items() if v["elf_sha256"] == a["elf_sha256"])
        if m["aliases"][c] != alias:
            raise ValueError("Kernel alias changed")
