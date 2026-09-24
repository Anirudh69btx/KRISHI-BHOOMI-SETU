#!/usr/bin/env python3
"""
FLIP v3.0 — ML Training Pipeline Evaluation Script
Evaluates a trained fusion model against holdout test set and logs
all metrics + confusion matrix + feature importances to MLflow.

Usage:
    python ml/training/evaluate.py \
        --model-uri runs:/<run_id>/model \
        --test-data data/holdout.parquet \
        --experiment flip-fusion-v1
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import mlflow
import mlflow.sklearn
import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

# ── Config ────────────────────────────────────────────────────────────────────
TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
EXPERIMENT_NAME = "flip-fusion-v1"

TARGET_LABELS = [
    "healthy",
    "drought_stress",
    "nutrient_deficiency",
    "pest_infestation",
    "waterlogging",
    "harvest_ready",
]

FEATURE_COLUMNS = [
    # Sensor features
    "temp_avg_7d",
    "temp_std_7d",
    "humidity_avg_7d",
    "soil_moisture_avg_7d",
    "soil_ph_avg",
    "nitrogen_ppm",
    "phosphorus_ppm",
    "potassium_ppm",
    "rainfall_mm_7d",
    "light_lux_avg",
    # Derived features
    "soil_temp_delta",
    "vapor_pressure_deficit",
    "crop_water_stress_index",
    "days_since_last_rain",
    "growing_degree_days",
    # Image embeddings (placeholder — 128-dim PCA of ResNet)
    *[f"img_embed_{i}" for i in range(128)],
]


def load_model(model_uri: str):
    """Load model from MLflow model registry."""
    mlflow.set_tracking_uri(TRACKING_URI)
    model = mlflow.sklearn.load_model(model_uri)
    return model


def load_test_data(path: str) -> tuple[pd.DataFrame, pd.Series]:
    """Load holdout test dataset."""
    df = pd.read_parquet(path)
    required_cols = FEATURE_COLUMNS + ["label"]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns in test data: {missing}")

    X = df[FEATURE_COLUMNS]
    y = df["label"]
    return X, y


def evaluate_model(model, X: pd.DataFrame, y: pd.Series) -> dict:
    """Run evaluation and compute all metrics."""
    y_pred = model.predict(X)

    has_proba = hasattr(model, "predict_proba")
    y_proba = model.predict_proba(X) if has_proba else None

    metrics = {
        "accuracy": float(accuracy_score(y, y_pred)),
        "f1_macro": float(f1_score(y, y_pred, average="macro", zero_division=0)),
        "f1_weighted": float(f1_score(y, y_pred, average="weighted", zero_division=0)),
        "precision_macro": float(precision_score(y, y_pred, average="macro", zero_division=0)),
        "recall_macro": float(recall_score(y, y_pred, average="macro", zero_division=0)),
        "test_sample_count": len(y),
    }

    if y_proba is not None and len(TARGET_LABELS) > 2:
        try:
            metrics["roc_auc_ovr"] = float(
                roc_auc_score(y, y_proba, multi_class="ovr", average="macro")
            )
        except Exception:
            pass

    report = classification_report(
        y, y_pred, target_names=TARGET_LABELS, output_dict=True, zero_division=0
    )
    cm = confusion_matrix(y, y_pred, labels=TARGET_LABELS).tolist()

    return {"metrics": metrics, "report": report, "confusion_matrix": cm}


def log_to_mlflow(
    model_uri: str,
    results: dict,
    run_name: str = "evaluation",
) -> str:
    """Log evaluation results to MLflow and return run_id."""
    mlflow.set_tracking_uri(TRACKING_URI)
    mlflow.set_experiment(EXPERIMENT_NAME)

    with mlflow.start_run(run_name=run_name) as run:
        # Log scalar metrics
        mlflow.log_metrics(results["metrics"])
        mlflow.log_param("model_uri", model_uri)
        mlflow.log_param("target_labels", ",".join(TARGET_LABELS))

        # Log classification report as JSON artifact
        report_path = Path("/tmp/classification_report.json")
        report_path.write_text(json.dumps(results["report"], indent=2))
        mlflow.log_artifact(str(report_path), artifact_path="evaluation")

        # Log confusion matrix
        cm_path = Path("/tmp/confusion_matrix.json")
        cm_path.write_text(
            json.dumps(
                {
                    "labels": TARGET_LABELS,
                    "matrix": results["confusion_matrix"],
                },
                indent=2,
            )
        )
        mlflow.log_artifact(str(cm_path), artifact_path="evaluation")

        run_id = run.info.run_id

    print(f"[Evaluate] MLflow run: {run_id}")
    print(f"[Evaluate] Metrics: {json.dumps(results['metrics'], indent=2)}")
    return run_id


def main():
    parser = argparse.ArgumentParser(description="FLIP Model Evaluation")
    parser.add_argument("--model-uri", required=True, help="MLflow model URI")
    parser.add_argument("--test-data", required=True, help="Path to holdout .parquet")
    parser.add_argument("--run-name", default="evaluation", help="MLflow run name")
    args = parser.parse_args()

    print(f"[Evaluate] Loading model from: {args.model_uri}")
    model = load_model(args.model_uri)

    print(f"[Evaluate] Loading test data from: {args.test_data}")
    X_test, y_test = load_test_data(args.test_data)

    print(f"[Evaluate] Running evaluation on {len(X_test)} samples...")
    results = evaluate_model(model, X_test, y_test)

    print("[Evaluate] Logging to MLflow...")
    run_id = log_to_mlflow(args.model_uri, results, run_name=args.run_name)

    # Exit with non-zero if accuracy below threshold
    acc = results["metrics"]["accuracy"]
    threshold = float(os.getenv("FLIP_MIN_ACCURACY_THRESHOLD", "0.75"))
    if acc < threshold:
        print(f"[Evaluate] FAIL: accuracy {acc:.3f} < threshold {threshold:.3f}")
        raise SystemExit(1)

    print(f"[Evaluate] PASS: accuracy {acc:.3f} >= threshold {threshold:.3f}")
    print(f"[Evaluate] Run ID: {run_id}")


if __name__ == "__main__":
    main()
