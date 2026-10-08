from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder


DATASET = Path("data/processed/sl_dataset.csv")
MODEL_PATH = Path("models/sl_model.joblib")


def main():

    df = pd.read_csv(DATASET)

    feature_columns = [
        f"feature_{i}"
        for i in range(56)
    ]

    X = df[
        feature_columns + ["pass_name"]
    ].copy()

    # Robust target:
    # log(runtime_before / runtime_after)
    raw_target = np.log(
        df["speedup"].to_numpy()
    )

    y = np.clip(
        raw_target,
        np.log(0.5),
        np.log(2.0),
    )

    preprocessing = ColumnTransformer(
        transformers=[
            (
                "pass",
                OneHotEncoder(
                    handle_unknown="ignore",
                    sparse_output=False,
                ),
                ["pass_name"],
            ),
        ],
        remainder="passthrough",
    )

    model = HistGradientBoostingRegressor(
     learning_rate=0.05,
     max_iter=250,
     max_leaf_nodes=15,
     min_samples_leaf=3,
     l2_regularization=0.1,
     random_state=42,
    )

    pipeline = Pipeline(
        [
            ("preprocessing", preprocessing),
            ("model", model),
        ]
    )

    pipeline.fit(X, y)

    predictions = pipeline.predict(X)

    mae = mean_absolute_error(
        y,
        predictions,
    )

    rmse = mean_squared_error(
        y,
        predictions,
        squared=False,
    )

    MODEL_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    joblib.dump(
        pipeline,
        MODEL_PATH,
    )

    print("Training samples:", len(df))
    print("Features:", len(feature_columns))
    print("Passes:", df["pass_name"].nunique())

    print()
    print("Training MAE:", round(mae, 6))
    print("Training RMSE:", round(rmse, 6))

    print()
    print("Model saved:")
    print(MODEL_PATH)


if __name__ == "__main__":
    main()
