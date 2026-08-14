"""Configurable Version 2 embedding network kept separate from Version 1."""

from __future__ import annotations

from typing import Sequence

import numpy as np
import torch
from torch import nn


def embedding_dimension_v2(cardinality: int, maximum: int = 48) -> int:
    return min(maximum, max(4, int(round(1.6 * np.sqrt(cardinality)))))


class FraudTabularNetworkV2(nn.Module):
    def __init__(
        self,
        numeric_size: int,
        cardinalities: Sequence[int],
        embedding_dimensions: Sequence[int],
        hidden_layers: Sequence[int] = (384, 192, 96),
        dropout: Sequence[float] = (0.30, 0.20, 0.10),
    ) -> None:
        super().__init__()
        if len(cardinalities) != len(embedding_dimensions):
            raise ValueError("Each categorical feature needs one embedding dimension")
        if len(hidden_layers) != len(dropout):
            raise ValueError("Every hidden layer needs one dropout value")
        self.embeddings = nn.ModuleList(
            [
                nn.Embedding(int(cardinality), int(dimension))
                for cardinality, dimension in zip(cardinalities, embedding_dimensions)
            ]
        )
        input_size = int(numeric_size) + sum(int(value) for value in embedding_dimensions)
        layers: list[nn.Module] = []
        previous = input_size
        for width, probability in zip(hidden_layers, dropout):
            layers.extend(
                [nn.Linear(previous, int(width)), nn.ReLU(), nn.Dropout(float(probability))]
            )
            previous = int(width)
        layers.append(nn.Linear(previous, 1))
        self.network = nn.Sequential(*layers)

    def forward(self, numeric: torch.Tensor, categorical: torch.Tensor) -> torch.Tensor:
        embedded = [
            layer(categorical[:, index]) for index, layer in enumerate(self.embeddings)
        ]
        return self.network(torch.cat([numeric, *embedded], dim=1)).squeeze(1)


def network_v2_from_config(config: dict) -> FraudTabularNetworkV2:
    return FraudTabularNetworkV2(
        numeric_size=int(config["numeric_size"]),
        cardinalities=[int(value) for value in config["cardinalities"]],
        embedding_dimensions=[int(value) for value in config["embedding_dimensions"]],
        hidden_layers=[int(value) for value in config["hidden_layers"]],
        dropout=[float(value) for value in config["dropout"]],
    )
