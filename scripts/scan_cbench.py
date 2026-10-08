import csv
from pathlib import Path

import compiler_gym

from src.benchmarks.baselines import measure_optimization_level


OUTPUT = Path("results/cbench_baselines.csv")

WARMUPS = 2
MEASUREMENTS = 5


def main():
    env = compiler_gym.make("llvm-v0")

    dataset = env.datasets["benchmark://cbench-v1"]
    benchmarks = list(dataset.benchmark_uris())

    env.close()

    rows = []

    print(f"Found {len(benchmarks)} cBench benchmarks")

    for i, benchmark in enumerate(benchmarks, start=1):

        benchmark = str(benchmark)

        print("\n" + "=" * 70)
        print(f"[{i}/{len(benchmarks)}] {benchmark}")
        print("=" * 70)

        row = {
            "benchmark": benchmark,
            "o0_median": None,
            "o2_median": None,
            "o3_median": None,
            "o3_std": None,
            "o3_speedup_vs_o0": None,
            "status": "FAILED",
            "error": "",
        }

        try:
            results = {}

            for level in ["O0", "O2", "O3"]:

                print(f"  Measuring -{level}...")

                result = measure_optimization_level(
                    benchmark,
                    level,
                    warmup_runs=WARMUPS,
                    measurement_runs=MEASUREMENTS,
                )

                results[level] = result

                print(
                    f"    median={result.median:.6f}s "
                    f"std={result.std:.6f}s"
                )

            row["o0_median"] = results["O0"].median
            row["o2_median"] = results["O2"].median
            row["o3_median"] = results["O3"].median
            row["o3_std"] = results["O3"].std

            row["o3_speedup_vs_o0"] = (
                results["O0"].median /
                results["O3"].median
            )

            row["status"] = "OK"

            print(
                "  O3 speedup vs O0:",
                f"{row['o3_speedup_vs_o0']:.3f}x",
            )

        except Exception as exc:

            row["error"] = str(exc)

            print("  FAILED:", exc)

        rows.append(row)

        # Save after every benchmark so progress is not lost.
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)

        with OUTPUT.open("w", newline="") as f:

            writer = csv.DictWriter(
                f,
                fieldnames=rows[0].keys(),
            )

            writer.writeheader()
            writer.writerows(rows)

    print("\nFinished.")
    print("Results:", OUTPUT)


if __name__ == "__main__":
    main()
