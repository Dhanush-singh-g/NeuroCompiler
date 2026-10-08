import copy
import subprocess
import tempfile
from pathlib import Path

import compiler_gym

from compiler_gym.datasets import Benchmark

from src.benchmarks.runtime import measure_runtime


LLVM_OPT = Path.home() / ".local/share/compiler_gym/llvm-v0/bin/opt"


def optimize_bitcode(input_bc: Path, output_bc: Path, level: str):
    """
    Optimize LLVM bitcode using the exact LLVM toolchain bundled
    with CompilerGym.
    """

    if level not in {"O0", "O1", "O2", "O3", "Os"}:
        raise ValueError(f"Unsupported optimization level: {level}")

    if level == "O0":
        output_bc.write_bytes(input_bc.read_bytes())
        return

    subprocess.run(
        [
            str(LLVM_OPT),
            f"-{level}",
            str(input_bc),
            "-o",
            str(output_bc),
        ],
        check=True,
    )


def benchmark_with_replaced_program(original_benchmark, bitcode_path: Path):
    """
    Clone a CompilerGym benchmark while preserving its runtime/build
    configuration and replacing only the LLVM bitcode.
    """

    proto = copy.deepcopy(original_benchmark.proto)

    with open(bitcode_path, "rb") as f:
        bitcode = f.read()

    # Replace only the program contents.
    proto.program.contents = bitcode

    # Give the generated benchmark a unique URI.
    proto.uri = (
        f"benchmark://neurocompiler/"
        f"{original_benchmark.uri.path}-{bitcode_path.stem}"
    )

    return Benchmark(proto)


def measure_optimization_level(
    benchmark_uri: str,
    level: str,
    warmup_runs: int = 2,
    measurement_runs: int = 5,
):
    """
    Measure one LLVM optimization level using the original benchmark's
    runtime configuration.
    """

    env = compiler_gym.make(
        "llvm-v0",
        benchmark=benchmark_uri,
    )

    env.reset()

    try:
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)

            original_bc = tmp / "original.bc"
            optimized_bc = tmp / f"{level}.bc"

            env.write_bitcode(str(original_bc))

            optimize_bitcode(
                original_bc,
                optimized_bc,
                level,
            )

            generated_benchmark = benchmark_with_replaced_program(
                env.benchmark,
                optimized_bc,
            )

            test_env = compiler_gym.make(
                "llvm-v0",
                benchmark=generated_benchmark,
            )

            test_env.reset()

            try:
                result = measure_runtime(
                    test_env,
                    warmup_runs=warmup_runs,
                    measurement_runs=measurement_runs,
                )

                return result

            finally:
                test_env.close()

    finally:
        env.close()
