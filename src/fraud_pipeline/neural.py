"""Reusable neural architecture shared by training and FastAPI inference."""

from __future__ import annotations

from typing import Sequence

import numpy as np
import torch
from torch import nn


def embedding_dimension(cardinality: int) -> int:
    """Choose a compact deterministic embedding width, capped for deployment."""
    return min(32, max(4, int(round(np.sqrt(cardinality)))))


class FraudTabularNetwork(nn.Module):
    """Embedding-based classifier for mixed tabular fraud features."""

    def __init__(
        self,
        numeric_size: int,
        cardinalities: Sequence[int],
        embedding_dimensions: Sequence[int],
    ) -> None:
        super().__init__()
        if len(cardinalities) != len(embedding_dimensions):
            raise ValueError("Each categorical feature needs one embedding dimension")
        self.embeddings = nn.ModuleList(
            [
                nn.Embedding(int(cardinality), int(dimension))
                for cardinality, dimension in zip(cardinalities, embedding_dimensions)
            ]
        )
        input_size = int(numeric_size) + sum(int(d) for d in embedding_dimensions)
        self.network = nn.Sequential(
            nn.Linear(input_size, 256),
            nn.ReLU(),
            nn.Dropout(0.30),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Dropout(0.20),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Dropout(0.10),
            nn.Linear(64, 1),
        )

    def forward(self, numeric: torch.Tensor, categorical: torch.Tensor) -> torch.Tensor:
        embedded = [
            layer(categorical[:, index])
            for index, layer in enumerate(self.embeddings)
        ]
        combined = torch.cat([numeric, *embedded], dim=1)
        return self.network(combined).squeeze(1)


def network_from_config(config: dict) -> FraudTabularNetwork:
    """Recreate the architecture before loading a saved state dictionary."""
    return FraudTabularNetwork(
        numeric_size=int(config["numeric_size"]),
        cardinalities=[int(value) for value in config["cardinalities"]],
        embedding_dimensions=[int(value) for value in config["embedding_dimensions"]],
    )
