import compiler_gym

from configs.passes import CURATED_PASSES


BENCHMARK = "benchmark://cbench-v1/qsort"


def main():

    env = compiler_gym.make(
        "llvm-v0",
        benchmark=BENCHMARK,
    )

    action_names = list(env.action_space.names)

    print("Curated pass count:", len(CURATED_PASSES))
    print()

    for pass_name in CURATED_PASSES:

        assert pass_name in action_names, (
            f"{pass_name} does not exist in CompilerGym action space"
        )

        action_id = action_names.index(pass_name)

        # Reset before each pass so every pass is tested
        # independently from the same initial program.
        env.reset()

        before = env.observation["IrInstructionCount"]

        observation, reward, done, info = env.step(action_id)

        after = env.observation["IrInstructionCount"]

        print(
            f"{action_id:3} "
            f"{pass_name:20} "
            f"{before:5} -> {after:5}"
        )

    env.close()

    print()
    print("All curated passes: PASS")


if __name__ == "__main__":
    main()
