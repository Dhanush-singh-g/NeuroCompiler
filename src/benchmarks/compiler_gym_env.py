import compiler_gym


def create_env(benchmark="benchmark://cbench-v1/qsort"):
    """
    Create and reset a CompilerGym LLVM environment.
    """
    env = compiler_gym.make(
        "llvm-v0",
        benchmark=benchmark,
    )

    env.reset()
    return env


def get_autophase_features(env):
    """
    Return the static AutoPhase feature vector for the current LLVM state.
    """
    features = env.observation["Autophase"]
    return features


def print_environment_info(env):
    print("Benchmark:", env.benchmark)
    print("LLVM actions:", env.action_space.n)

    features = get_autophase_features(env)

    print("AutoPhase feature count:", len(features))
    print("AutoPhase features:")
    print(features)


if __name__ == "__main__":
    env = create_env()

    try:
        print_environment_info(env)
    finally:
        env.close()
