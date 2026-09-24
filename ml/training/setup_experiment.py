#!/usr/bin/env python3
"""
FLIP v3.0 — MLflow Experiment Setup & Data Prep
Sets up the MLflow experiment, registers model schema, and generates
synthetic training data for local dev/CI.

Usage:
    python ml/training/setup_experiment.py [--synthetic-samples 5000]
"""

from __future__ import annotations

import argparse
import os
import random
from pathlib import Path

import mlflow
import numpy as np
import pandas as pd

TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
EXPERIMENT_NAME = "flip-fusion-v1"

LABELS = [
    "healthy",
    "drought_stress",
    "nutrient_deficiency",
    "pest_infestation",
    "waterlogging",
    "harvest_ready",
]

LABEL_WEIGHTS = [0.40, 0.15, 0.15, 0.10, 0.10, 0.10]  # Realistic imbalance


def setup_mlflow_experiment() -> str:
    """Create or get the FLIP MLflow experiment."""
    mlflow.set_tracking_uri(TRACKING_URI)

    experiment = mlflow.get_experiment_by_name(EXPERIMENT_NAME)
    if experiment:
        print(f"[Setup] Using existing experiment: {EXPERIMENT_NAME} (id={experiment.experiment_id})")
        return experiment.experiment_id

    experiment_id = mlflow.create_experiment(
        EXPERIMENT_NAME,
        artifact_location="s3://mlflow-artifacts/flip-fusion-v1",
        tags={
            "project": "FLIP",
            "model_type": "sensor_fusion",
            "version": "v1",
        },
    )
    print(f"[Setup] Created experiment: {EXPERIMENT_NAME} (id={experiment_id})")
    return experiment_id


def generate_synthetic_data(n_samples: int = 5000) -> pd.DataFrame:
    """Generate realistic synthetic sensor + label data for dev/CI."""
    np.random.seed(42)
    random.seed(42)

    labels = np.random.choice(LABELS, size=n_samples, p=LABEL_WEIGHTS)
    records = []

    for label in labels:
        base = {
            "healthy": {"temp": 28, "humidity": 65, "soil_moist": 55, "ph": 6.5, "n": 40},
            "drought_stress": {"temp": 36, "humidity": 30, "soil_moist": 15, "ph": 6.2, "n": 35},
            "nutrient_deficiency": {"temp": 29, "humidity": 60, "soil_moist": 50, "ph": 5.5, "n": 10},
            "pest_infestation": {"temp": 30, "humidity": 70, "soil_moist": 50, "ph": 6.5, "n": 38},
            "waterlogging": {"temp": 26, "humidity": 90, "soil_moist": 95, "ph": 6.0, "n": 20},
            "harvest_ready": {"temp": 32, "humidity": 50, "soil_moist": 40, "ph": 6.8, "n": 15},
        }[label]

        record = {
            "temp_avg_7d": base["temp"] + np.random.normal(0, 2),
            "temp_std_7d": abs(np.random.normal(2, 0.5)),
            "humidity_avg_7d": np.clip(base["humidity"] + np.random.normal(0, 8), 10, 100),
            "soil_moisture_avg_7d": np.clip(base["soil_moist"] + np.random.normal(0, 5), 0, 100),
            "soil_ph_avg": np.clip(base["ph"] + np.random.normal(0, 0.3), 4, 9),
            "nitrogen_ppm": np.clip(base["n"] + np.random.normal(0, 5), 0, 100),
            "phosphorus_ppm": np.clip(20 + np.random.normal(0, 5), 0, 100),
            "potassium_ppm": np.clip(180 + np.random.normal(0, 20), 50, 300),
            "rainfall_mm_7d": max(0, np.random.exponential(10)),
            "light_lux_avg": np.clip(25000 + np.random.normal(0, 5000), 5000, 50000),
            "soil_temp_delta": np.random.normal(0, 1.5),
            "vapor_pressure_deficit": abs(np.random.normal(1.2, 0.4)),
            "crop_water_stress_index": np.random.uniform(0, 1),
            "days_since_last_rain": np.random.randint(0, 30),
            "growing_degree_days": np.random.uniform(100, 1200),
            # Synthetic image embeddings (PCA of ResNet features)
            **{f"img_embed_{i}": np.random.normal(0, 1) for i in range(128)},
            "label": label,
        }
        records.append(record)

    return pd.DataFrame(records)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--synthetic-samples", type=int, default=5000)
    parser.add_argument("--output-dir", default="data/training")
    args = parser.parse_args()

    # Setup MLflow
    exp_id = setup_mlflow_experiment()
    print(f"[Setup] Experiment ID: {exp_id}")

    # Generate synthetic data
    print(f"[Setup] Generating {args.synthetic_samples} synthetic samples...")
    df = generate_synthetic_data(args.synthetic_samples)

    # Split train/val/test: 70/15/15
    n = len(df)
    df = df.sample(frac=1, random_state=42).reset_index(drop=True)
    train_end = int(n * 0.70)
    val_end = int(n * 0.85)

    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)

    df.iloc[:train_end].to_parquet(output / "train.parquet", index=False)
    df.iloc[train_end:val_end].to_parquet(output / "val.parquet", index=False)
    df.iloc[val_end:].to_parquet(output / "holdout.parquet", index=False)

    print(f"[Setup] Saved: train={train_end}, val={val_end - train_end}, test={n - val_end}")
    print(f"[Setup] Label distribution:\n{df['label'].value_counts().to_string()}")
    print(f"[Setup] Done! Files in: {output.resolve()}")


if __name__ == "__main__":
    main()
