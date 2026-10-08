from src.benchmarks.paired_runtime import measure_paired_pass


BENCHMARK = "benchmark://cbench-v1/qsort"

PASSES = [
    "-instcombine",
    "-inline",
    "-constprop",
    "-gvn",
    "-licm",
]


def main():

    print("Benchmark:", BENCHMARK)
    print()

    print(
        f"{'Pass':18}"
        f"{'Base(ms)':>12}"
        f"{'Pass(ms)':>12}"
        f"{'Speedup':>12}"
        f"{'Change':>12}"
    )

    print("-" * 66)

    for pass_name in PASSES:

        result = measure_paired_pass(
            BENCHMARK,
            pass_name,
            pairs=10,
            warmup_runs=1,
        )

        print(
            f"{pass_name:18}"
            f"{result.median_baseline * 1000:12.3f}"
            f"{result.median_transformed * 1000:12.3f}"
            f"{result.median_speedup:12.4f}"
            f"{result.improvement_percent:11.2f}%"
        )

        print(
            "  pair speedups:",
            " ".join(
                f"{x:.3f}"
                for x in result.speedups
            ),
        )


if __name__ == "__main__":
    main()
