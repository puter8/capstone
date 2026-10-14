"""Transfer a frozen sentence encoder's features to human-labeled F/H/C scores.

Only the regression heads are trained here. This is transfer learning, not
LLM pretraining or RLHF. The encoder is optional and loaded on first use so
the production application does not acquire a torch dependency on import.
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Protocol

import numpy as np
from sklearn.linear_model import Ridge

from ai.ml_baseline import AxisTrainingExample

AXES = ("Formality", "Humor", "Curiosity")
DEFAULT_ENCODER = "sentence-transformers/all-MiniLM-L6-v2"


class TextEncoder(Protocol):
    def encode(self, sentences: list[str], **kwargs) -> np.ndarray: ...


class EmbeddingAxisAdapter:
    def __init__(
        self, alpha: float = 1.0, *, encoder: TextEncoder | None = None,
        model_name: str = DEFAULT_ENCODER, cache_folder: str | Path | None = None,
        revision: str | None = None, local_files_only: bool = False,
    ) -> None:
        if not math.isfinite(alpha) or alpha <= 0:
            raise ValueError("alpha must be finite and positive")
        self.alpha = alpha
        self.encoder = encoder
        self.model_name = model_name
        self.cache_folder = str(cache_folder) if cache_folder is not None else None
        self.revision = revision
        self.local_files_only = local_files_only
        self.axis_models: dict[str, Ridge] = {}

    def _encode(self, texts: list[str]) -> np.ndarray:
        if self.encoder is None:
            from sentence_transformers import SentenceTransformer

            self.encoder = SentenceTransformer(
                self.model_name, cache_folder=self.cache_folder, device="cpu",
                revision=self.revision, local_files_only=self.local_files_only,
                trust_remote_code=False,
            )
        features = np.asarray(self.encoder.encode(
            texts, batch_size=32, convert_to_numpy=True,
            normalize_embeddings=True, show_progress_bar=False,
        ), dtype=np.float64)
        if features.ndim != 2 or features.shape[0] != len(texts) or features.shape[1] == 0:
            raise ValueError("encoder returned an invalid feature shape")
        if not np.isfinite(features).all():
            raise ValueError("encoder returned non-finite features")
        return features

    def fit(self, examples: list[AxisTrainingExample]) -> "EmbeddingAxisAdapter":
        if not examples:
            raise ValueError("at least one training example is required")
        for example in examples:
            if not example.utterance.strip():
                raise ValueError("training utterance cannot be blank")
            for axis in AXES:
                if axis in example.label:
                    value = example.label[axis]
                    if not math.isfinite(value) or not 0 <= value <= 100:
                        raise ValueError(f"invalid {axis} target: {value}")
        features = self._encode([e.utterance for e in examples])
        models = {}
        for axis in AXES:
            indices = [i for i, e in enumerate(examples) if axis in e.label]
            if indices:
                models[axis] = Ridge(alpha=self.alpha).fit(
                    features[indices], [examples[i].label[axis] for i in indices],
                )
        if not models:
            raise ValueError("no F/H/C labels are available")
        self.axis_models = models
        return self

    def predict_many(self, utterances: list[str]) -> list[dict[str, float | None]]:
        if not self.axis_models:
            raise RuntimeError("model is not fitted")
        if not utterances:
            return []
        features = self._encode(utterances)
        predictions = {a: model.predict(features) for a, model in self.axis_models.items()}
        # Match the existing Ridge baseline's clipping and rounding for comparison.
        return [
            {a: round(float(np.clip(predictions[a][i], 0, 100)) / 5) * 5
             if a in predictions else None for a in AXES}
            for i in range(len(utterances))
        ]

    def predict_partial(self, utterance: str) -> dict[str, float | None]:
        return self.predict_many([utterance])[0]

    @classmethod
    def from_artifact(cls, path: str | Path) -> "EmbeddingAxisAdapter":
        """Load only a trusted local artifact made by train_transfer_axis_models.

        Joblib uses pickle; never use this entrypoint for uploaded/untrusted files.
        The encoder must already exist locally, so loading cannot download code.
        """
        import joblib

        bundle = joblib.load(path)
        model = cls(alpha=bundle["alpha"], model_name=bundle["model_name"], local_files_only=True)
        model.axis_models = bundle["axis_models"]
        if not model.axis_models or set(model.axis_models) - set(AXES):
            raise ValueError("artifact does not contain valid F/H/C regression heads")
        return model
