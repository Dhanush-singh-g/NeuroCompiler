from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

TRAIN_PATH = Path("data/processed/sl_dataset.csv")
VAL_PATH = Path("data/processed/sl_validation.csv")
MODEL_PATH = Path("models/sl_model.joblib")

FEATURES = [f"feature_{i}" for i in range(56)]
INPUT_COLUMNS = FEATURES + ["pass_name"]


def evaluate():

    train = pd.read_csv(TRAIN_PATH)
    val = pd.read_csv(VAL_PATH)

    assert set(train.benchmark).isdisjoint(
        set(val.benchmark)
    ), "Benchmark leakage detected!"

    model = joblib.load(MODEL_PATH)

    # Predict without using measured runtime as input.
    val["predicted_log_speedup"] = model.predict(
        val[INPUT_COLUMNS]
    )

    # Actual speedup is used only for evaluation.
    val["actual_log_speedup"] = np.log(
        val["speedup"]
    )

    global_pass_scores = (
        train.groupby("pass_name")["log_speedup"]
        .median()
    )

    val["global_pass_score"] = (
        val["pass_name"].map(global_pass_scores)
    )

    results = []

    for benchmark, group in val.groupby("benchmark"):

        group = group.copy()

        actual = group.sort_values(
            "actual_log_speedup",
            ascending=False,
        )

        predicted = group.sort_values(
            "predicted_log_speedup",
            ascending=False,
        )

        global_ranked = group.sort_values(
            "global_pass_score",
            ascending=False,
        )

        correlation = spearmanr(
            group["predicted_log_speedup"],
            group["actual_log_speedup"],
        ).statistic

        actual_top4 = set(
            actual.head(4)["pass_name"]
        )

        predicted_top4 = set(
            predicted.head(4)["pass_name"]
        )

        recall_at_4 = (
            len(actual_top4 & predicted_top4) / 4
        )

        sl_top1 = predicted.iloc[0]
        global_top1 = global_ranked.iloc[0]
        oracle_top1 = actual.iloc[0]

        results.append({
            "benchmark": benchmark.split("/")[-1],
            "spearman": correlation,
            "recall_at_4": recall_at_4,
            "sl_top1_pass": sl_top1["pass_name"],
            "sl_top1_speedup": sl_top1["speedup"],
            "global_top1_pass": global_top1["pass_name"],
            "global_top1_speedup": global_top1["speedup"],
            "oracle_pass": oracle_top1["pass_name"],
            "oracle_speedup": oracle_top1["speedup"],
        })

        print("\n" + "=" * 65)
        print("BENCHMARK:", benchmark)
        print("=" * 65)

        print("\nActual top 5:")
        print(
            actual[
                ["pass_name", "speedup"]
            ].head(5).to_string(index=False)
        )

        print("\nModel predicted top 5:")
        print(
            predicted[
                [
                    "pass_name",
                    "predicted_log_speedup",
                    "speedup",
                ]
            ].head(5).to_string(index=False)
        )

        print("\nGlobal baseline top 5:")
        print(
            global_ranked[
                ["pass_name", "speedup"]
            ].head(5).to_string(index=False)
        )

    summary = pd.DataFrame(results)

    print("\n" + "=" * 65)
    print("VALIDATION SUMMARY")
    print("=" * 65)

    print(summary.to_string(index=False))

    print("\nAverage Spearman:",
          round(summary["spearman"].mean(), 4))

    print("Average Recall@4:",
          round(summary["recall_at_4"].mean(), 4))

    print("\nSL Top-1 geometric mean speedup:",
          round(
              np.exp(
                  np.log(summary["sl_top1_speedup"]).mean()
              ),
              4,
          ))

    print("Global Top-1 geometric mean speedup:",
          round(
              np.exp(
                  np.log(summary["global_top1_speedup"]).mean()
              ),
              4,
          ))

    print("Oracle Top-1 geometric mean speedup:",
          round(
              np.exp(
                  np.log(summary["oracle_speedup"]).mean()
              ),
              4,
          ))

    Path("results").mkdir(exist_ok=True)

    summary.to_csv(
        "results/sl_validation_summary.csv",
        index=False,
    )


if __name__ == "__main__":
    evaluate()
