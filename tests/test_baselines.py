from src.benchmarks.baselines import measure_optimization_level


BENCHMARK = "benchmark://cbench-v1/qsort"


def main():

    print("Benchmark:", BENCHMARK)

    results = {}

    for level in ["O0", "O2", "O3"]:

        print(f"\nMeasuring -{level}...")

        result = measure_optimization_level(
            BENCHMARK,
            level,
            warmup_runs=2,
            measurement_runs=5,
        )

        results[level] = result

        print("Raw:", result.runtimes)
        print("Median:", result.median)
        print("Std:", result.std)

    print("\n==============================")
    print("RESULTS")
    print("==============================")

    for level, result in results.items():
        print(
            f"-{level}: "
            f"{result.median:.6f} seconds"
        )

    o0_o3_speedup = (
        results["O0"].median /
        results["O3"].median
    )

    print(
        f"\n-O3 speedup over -O0: "
        f"{o0_o3_speedup:.3f}x"
    )


if __name__ == "__main__":
    main()
