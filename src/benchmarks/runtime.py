from dataclasses import dataclass
from typing import List

import numpy as np


@dataclass
class RuntimeResult:
    runtimes: List[float]
    median: float
    mean: float
    minimum: float
    maximum: float
    std: float


def measure_runtime(
    env,
    warmup_runs: int = 2,
    measurement_runs: int = 5,
) -> RuntimeResult:
    """
    Measure the runtime of the current LLVM state.

    Parameters
    ----------
    env:
        Active CompilerGym LLVM environment.

    warmup_runs:
        Number of executions discarded before measurement.

    measurement_runs:
        Number of measured executions.

    Returns
    -------
    RuntimeResult
        Runtime statistics for the current LLVM state.
    """

    if not env.observation["IsBuildable"]:
        raise RuntimeError(
            f"Benchmark is not buildable: {env.benchmark}"
        )

    if not env.observation["IsRunnable"]:
        raise RuntimeError(
            f"Benchmark is not runnable: {env.benchmark}"
        )

    env.runtime_warmup_runs_count = warmup_runs
    env.runtime_observation_count = measurement_runs

    runtimes = np.asarray(
        env.observation["Runtime"],
        dtype=float,
    )

    if len(runtimes) == 0:
        raise RuntimeError(
            f"No runtime measurements returned for {env.benchmark}"
        )

    return RuntimeResult(
        runtimes=runtimes.tolist(),
        median=float(np.median(runtimes)),
        mean=float(np.mean(runtimes)),
        minimum=float(np.min(runtimes)),
        maximum=float(np.max(runtimes)),
        std=float(np.std(runtimes)),
    )
