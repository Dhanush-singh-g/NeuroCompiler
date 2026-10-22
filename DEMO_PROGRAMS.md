# NeuroCompiler — Copy-and-paste demo programs

This pack contains **seven working C programs and three intentional diagnostic programs** for the live app on `presentation/live-explorer`. Each example gives the exact web-app inputs and expected behavior.

## How to use this pack

1. Start the live application using [PRESENTATION.md](PRESENTATION.md).
2. Copy only the contents of a `c` code block into the source editor, or save it as a `.c` file and use **Open .c file**.
3. Expand **Program input & workload**. Set **all three fields** exactly as listed: arguments, standard input, and iterations descriptor. Clear fields marked blank; do not leave input from a previous example.
4. Click **Analyze & predict**. This compiles and predicts without executing the program.
5. To run a working example, open **Live comparison**, confirm the trusted-code checkbox, and click **Run live comparison**.
6. Inspect the output, compare CPU/WALL views, inspect LLVM IR, and download the report or model-selected bitcode.

The iterations descriptor is a model feature; it does not control execution. Repetition-based examples read their actual workload from **command-line arguments**. Enter only the argument value, not a program name.

**Expected timing behavior:** short examples should be inconclusive. Larger examples may also be inconclusive if the O3 self-control or other quality checks fail. A correct output, identical binary, O3 recommendation, or failed timing control is a valid outcome. None of these examples promises a speedup or a particular learned choice.

## Quick reference

| # | Program | Arguments | Standard input | Iterations descriptor | Expected stdout |
| --- | --- | --- | --- | ---: | --- |
| 1 | Your first C input | Blank | `21 34` | 0 | `55` |
| 2 | Fibonacci with standard input | Blank | `20` | 0 | `6765` |
| 3 | Insertion sort with duplicates and negative values | Blank | Blank | 0 | `-3 0 2 2 7 9` |
| 4 | Byte histogram | `1200` | Blank | 1200 | `10106072816` |
| 5 | Integer mixing | `800` | Blank | 800 | `1663895971514` |
| 6 | Matrix arithmetic | `240` | Blank | 240 | `3859164095` |
| 7 | Prime sieve / training example | `1600` | Blank | 1600 | `25765905600` |

All expected outputs below include a final newline. Start with program 1, then try 4 or 5 for a larger workload. Programs 8–10 are deliberately diagnostic; they should not produce successful benchmark results.

## 1. Your first C input

Checks that text entered in the web app really reaches `scanf`. Try input `10 15` afterward: expected output becomes `25`. This program is too short for meaningful timing.

- **Command-line arguments:** blank
- **Standard input:** `21 34` followed by Enter
- **Iterations descriptor:** `0`

```c
#include <stdio.h>

int main(void) {
    long a, b;
    if (scanf("%ld %ld", &a, &b) != 2) return 1;
    printf("%ld\n", a + b);
    return 0;
}
```

**Expected stdout:**

```text
55
```

## 2. Fibonacci with standard input

Checks an input-dependent loop. Input `0` prints `0`; input `10` prints `55`; input `20` prints `6765`. Inputs above 40 intentionally return a nonzero status. This is a functional example, not a performance benchmark.

- **Command-line arguments:** blank
- **Standard input:** `20` followed by Enter
- **Iterations descriptor:** `0`

```c
#include <stdio.h>
#include <stdint.h>
#include <inttypes.h>

int main(void) {
    unsigned n;
    if (scanf("%u", &n) != 1 || n > 40) return 1;
    uint32_t a = 0, b = 1;
    for (unsigned i = 0; i < n; ++i) {
        uint32_t next = a + b;
        a = b;
        b = next;
    }
    printf("%" PRIu32 "\n", a);
    return 0;
}
```

**Expected stdout:**

```text
6765
```

## 3. Insertion sort with duplicates and negative values

Checks sorting, duplicates, negative values, and deterministic formatted output. No input is required. The compiler may fold much of this fixed-size calculation; that is normal. This program is too short for useful timing.

- **Command-line arguments:** blank
- **Standard input:** blank
- **Iterations descriptor:** `0`

```c
#include <stdio.h>

int main(void) {
    int values[] = {9, -3, 7, 0, 2, 2};
    unsigned count = sizeof values / sizeof values[0];
    for (unsigned i = 1; i < count; ++i) {
        int value = values[i];
        unsigned j = i;
        while (j > 0 && values[j - 1] > value) {
            values[j] = values[j - 1];
            --j;
        }
        values[j] = value;
    }
    for (unsigned i = 0; i < count; ++i)
        printf("%s%d", i ? " " : "", values[i]);
    putchar('\n');
    return 0;
}
```

**Expected stdout:**

```text
-3 0 2 2 7 9
```

## 4. Byte histogram

A larger integer workload with array initialization, data-dependent indexing, and a checksum. Inspect instruction counts and pipeline aliases. No particular pipeline is guaranteed to differ or run faster.

- **Command-line arguments:** `1200`
- **Standard input:** blank
- **Iterations descriptor:** `1200`

```c
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

/* A self-contained, deterministic workload. Print only the checksum. */
int main(int argc, char **argv) {
    unsigned rounds = argc > 1 ? (unsigned)strtoul(argv[1], 0, 10) : 1200;
    static unsigned char data[65536];
    uint32_t state = 2026u;
    for (unsigned i = 0; i < sizeof data; ++i) {
        state = state * 1664525u + 1013904223u;
        data[i] = (unsigned char)(state >> 24);
    }
    uint64_t checksum = 0;
    for (unsigned r = 0; r < rounds; ++r) {
        unsigned counts[256] = {0};
        for (unsigned i = 0; i < sizeof data; ++i)
            ++counts[(data[i] + r) & 255u];
        for (unsigned i = 0; i < 256; ++i)
            checksum += (uint64_t)counts[i] * (i + 1u);
    }
    printf("%llu\n", (unsigned long long)checksum);
    return 0;
}
```

**Expected stdout:**

```text
10106072816
```

## 5. Integer mixing

A larger workload dominated by unsigned integer arithmetic and dependencies. Unsigned wraparound is intentional. Matching O0 and candidate checksums are the main functional check.

- **Command-line arguments:** `800`
- **Standard input:** blank
- **Iterations descriptor:** `800`

```c
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

int main(int argc, char **argv) {
    unsigned rounds = argc > 1 ? (unsigned)strtoul(argv[1], 0, 10) : 800;
    uint32_t x = 0x12345678u;
    uint64_t checksum = 0;
    for (unsigned r = 0; r < rounds; ++r) {
        for (unsigned i = 0; i < 32768; ++i) {
            x ^= x >> 15;
            x *= 0x2c1b3c6du;
            x ^= x >> 12;
            x += i + r;
        }
        checksum += x;
    }
    printf("%llu\n", (unsigned long long)checksum);
    return 0;
}
```

**Expected stdout:**

```text
1663895971514
```

## 6. Matrix arithmetic

Exercises nested loops and floating-point arithmetic under default strict math settings. No fast-math or native-CPU flags are added by this app. Output checks must pass before timing.

- **Command-line arguments:** `240`
- **Standard input:** blank
- **Iterations descriptor:** `240`

```c
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

int main(int argc, char **argv) {
    unsigned rounds = argc > 1 ? (unsigned)strtoul(argv[1], 0, 10) : 240;
    static double a[64][64], b[64][64], c[64][64];
    for (unsigned i = 0; i < 64; ++i)
        for (unsigned j = 0; j < 64; ++j) {
            a[i][j] = (double)((i * 13u + j * 7u) & 255u) / 256.0;
            b[i][j] = (double)((i * 3u + j * 11u) & 255u) / 256.0;
        }
    uint64_t checksum = 0;
    for (unsigned r = 0; r < rounds; ++r) {
        for (unsigned i = 0; i < 64; ++i)
            for (unsigned j = 0; j < 64; ++j) {
                double sum = 0;
                for (unsigned k = 0; k < 64; ++k)
                    sum += a[i][k] * b[k][j];
                c[i][j] = sum;
            }
        checksum += (uint64_t)(c[r % 64][(r * 7) % 64] * 1000000.0);
        a[r % 64][r % 64] += .000001;
    }
    printf("%llu\n", (unsigned long long)checksum);
    return 0;
}
```

**Expected stdout:**

```text
3859164095
```

## 7. Prime sieve / training example

This is the existing synthetic **training workload**, included to make the model workflow easy to demonstrate. It is not an unseen-program evaluation or evidence of generalization. The checked cloud prediction used O3→GVN→DCE, but do not require that decision on another host: binary sizes, aliases, and feature values can change.

- **Command-line arguments:** `1600`
- **Standard input:** blank
- **Iterations descriptor:** `1600`

```c
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
static uint32_t random_word(uint32_t *s) { *s=*s*1664525u+1013904223u; return *s; }
int main(int argc, char **argv) {
  unsigned iterations=argc>1?(unsigned)strtoul(argv[1],0,10):1;
  uint32_t state=1234567u; uint64_t checksum=0;
unsigned char a[16384];for(unsigned k=0;k<iterations;k++){
      for(unsigned i=0;i<16384;i++)a[i]=1;
      for(unsigned i=2;i*i<16384;i++)if(a[i])for(unsigned j=i*i;j<16384;j+=i)a[j]=0;
      for(unsigned i=2;i<16384;i++)if(a[i])checksum+=i+k;}
 printf("%llu\n",(unsigned long long)checksum); return 0; }
```

**Expected stdout:**

```text
25765905600
```

## 8. Intentional compile error

Use this to demonstrate readable compiler diagnostics and recovery. Set arguments and stdin blank; descriptor `0`. Click **Analyze & predict**. The missing semicolon must cause a visible compiler error. There should be no new successful prediction or native timing.

```c
#include <stdio.h>

int main(void) {
    puts("This program intentionally has a syntax error")
    return 0;
}
```

To recover, add the missing semicolon after `puts(...)` and analyze again. The fixed program prints `This program intentionally has a syntax error`.

## 9. Intentional output mismatch

Use this to demonstrate that the app blocks timing when outputs differ. Set arguments and stdin blank; descriptor `0`. Static analysis should succeed. Then allow trusted execution and run the comparison.

The O0 reference prints `reference`; optimized candidates print `optimized`. The app should report an output mismatch and collect **no benchmark timing cells**. This difference is explicitly caused by the preprocessor macro, not a discovered compiler correctness bug.

```c
#include <stdio.h>

int main(void) {
#ifdef __OPTIMIZE__
    puts("optimized");
#else
    puts("reference");
#endif
    return 0;
}
```

## 10. Intentional timeout

Optional diagnostic only: this program never finishes. Set arguments and stdin blank; descriptor `0`. Analysis should succeed because it does not execute the program. The live comparison should stop with the two-second program timeout; it must not report a speedup. You can also use **Cancel** while a job is running.

```c
int main(void) {
    volatile unsigned counter = 0;
    for (;;) {
        ++counter;
    }
}
```

## Suggested presentation sequence

1. **Program 1:** prove real stdin works and show output `55`.
2. **Program 7:** show a familiar training example, model scores, feature contributions, and actual LLVM pass pipelines.
3. **Program 4 or 5:** run a larger workload and discuss measured ratios alongside their quality checks.
4. **Program 9:** show that correctness checking blocks an invalid comparison.
5. Download Markdown/JSON and model-selected bitcode. Explain that prediction happens before measurement and that the approved policy remains O3.

## Scope and verification

The seven working examples were compiled and executed on 22 October 2026 using the app’s pinned x86_64 Linux LLVM10 toolchain. Each was executed twice under the O0 reference and each of the four app pipelines: **70 native executions**, all with matching output. These were functional output checks; no new formal performance study or model training was performed. The three diagnostic behaviors were checked separately.

The first five entries in the built-in example picker already cover sieve, histogram, integer mixing, matrix arithmetic, and simple stdin. The Fibonacci and sorting programs are additional copy-and-paste examples in this document; this change does not add new picker entries.

These are presentation examples, not a new held-out research dataset. Model predictions remain experimental and reliable learned improvement over O3 remains unproven. If you change repetition arguments, update the descriptor too; the listed checksum then no longer necessarily applies. Reduce workloads if they exceed the app’s two-second execution limit, and treat short/noisy measurements as inconclusive.
