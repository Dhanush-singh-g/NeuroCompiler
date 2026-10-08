import compiler_gym

from src.benchmarks.runtime import measure_runtime


def main():
    env = compiler_gym.make(
        "llvm-v0",
        benchmark="benchmark://cbench-v1/qsort",
    )

    env.reset()

    try:
        result = measure_runtime(
            env,
            warmup_runs=2,
            measurement_runs=5,
        )

        print("Raw runtimes:", result.runtimes)
        print("Median:", result.median)
        print("Mean:", result.mean)
        print("Std:", result.std)

        assert len(result.runtimes) == 5
        assert result.median > 0

        print("Runtime harness: PASS")

    finally:
        env.close()


if __name__ == "__main__":
    main()
