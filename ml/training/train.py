"""
FLIP v3.0 — ML Training Script
Orchestrates training of CrossAttentionFusion with MLflow tracking,
followed by Conformal PredictionSet calibration (>= 95% coverage).
Usage:
  python -m ml.training.train --epochs 10 --batch-size 32
"""

from __future__ import annotations

import argparse
import os

import lightning as L
from lightning.pytorch.callbacks import EarlyStopping, ModelCheckpoint
from lightning.pytorch.loggers import MLFlowLogger
import torch
from torch.utils.data import DataLoader, Dataset

from ml.models.fusion.model import CrossAttentionFusion, DEFAULT_DISEASE_CLASSES


class SyntheticFarmDataset(Dataset):
    """Synthetic dataset for testing multi-modal ML training & conformal calibration."""

    def __init__(self, size: int = 500):
        self.size = size
        self.soil = torch.randn(size, 8)
        self.weather = torch.randn(size, 24, 6)
        self.image = torch.randn(size, 3, 64, 64)
        self.satellite = torch.randn(size, 5)
        # Synthetic classification label (0 to num_classes - 1)
        self.label = torch.randint(0, len(DEFAULT_DISEASE_CLASSES), (size,))
        # Synthetic continuous regression target
        self.target = (
            self.soil[:, 0:1] * 2.0
            + self.weather[:, -1, 0:1] * 1.5
            + torch.randn(size, 1) * 0.1
        )

    def __len__(self) -> int:
        return self.size

    def __getitem__(self, idx: int) -> dict[str, torch.Tensor]:
        return {
            "soil": self.soil[idx],
            "weather": self.weather[idx],
            "image": self.image[idx],
            "satellite": self.satellite[idx],
            "label": self.label[idx],
            "target": self.target[idx],
        }


def main():
    parser = argparse.ArgumentParser(description="Train FLIP Fusion Model")
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--mlflow-uri", default=os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000"))
    args = parser.parse_args()

    train_data = SyntheticFarmDataset(size=800)
    val_data = SyntheticFarmDataset(size=200)
    cal_data = SyntheticFarmDataset(size=200)

    train_loader = DataLoader(train_data, batch_size=args.batch_size, shuffle=True)
    val_loader = DataLoader(val_data, batch_size=args.batch_size, shuffle=False)
    cal_loader = DataLoader(cal_data, batch_size=args.batch_size, shuffle=False)

    model = CrossAttentionFusion(
        soil_dim=8,
        weather_dim=6,
        weather_seq_len=24,
        sat_dim=5,
        d_model=64,
        n_heads=2,
        lr=args.lr,
    )

    mlf_logger = None
    try:
        mlf_logger = MLFlowLogger(
            experiment_name="farm-cross-attention-fusion",
            tracking_uri=args.mlflow_uri,
        )
    except Exception as exc:
        print(f"MLflow connection skipped: {exc}")

    callbacks = [
        EarlyStopping(monitor="val_loss", patience=5, mode="min"),
        ModelCheckpoint(dirpath="checkpoints", monitor="val_loss", mode="min"),
    ]

    trainer = L.Trainer(
        max_epochs=args.epochs,
        accelerator="auto",
        logger=mlf_logger,
        callbacks=callbacks,
        enable_progress_bar=True,
    )

    print("🚀 Starting training...")
    trainer.fit(model, train_loader, val_loader)
    print("✅ Training complete.")

    print("🔬 Running Conformal PredictionSet calibration (coverage >= 95%)...")
    model.calibrate_classification(cal_loader)
    model.calibrate_regression(cal_loader)
    print("✅ Conformal calibration complete.")

    # Sample inference
    sample = cal_data[0]
    res_cls = model.predict_classification_conformal(
        soil=sample["soil"].unsqueeze(0),
        weather=sample["weather"].unsqueeze(0),
        image=sample["image"].unsqueeze(0),
        satellite=sample["satellite"].unsqueeze(0),
    )
    print(f"📊 Sample Classification Prediction Set: {res_cls['prediction_set']}")
    print(f"   Target Coverage: {res_cls['coverage_target'] * 100}%")


if __name__ == "__main__":
    main()
