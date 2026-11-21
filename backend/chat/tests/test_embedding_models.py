"""The ONNX models must reproduce the vectors of the former sentence-transformers/torch
stack, or existing Qdrant indexes would silently stop matching new queries.
Reference values were captured from sentence-transformers 5.7 / torch 2.15."""

import pytest
from huggingface_hub import try_to_load_from_cache

from chat.embedding_models import (
    DEFAULT_EMBEDDING_MODEL,
    EMBEDDING_REVISION,
    RERANKER_MODEL,
    RERANKER_REVISION,
    OnnxCrossEncoder,
    OnnxEmbedder,
)


def _require_cached(repo, revision):
    # shortcut: skips where the models were never downloaded (CI), run locally or in the image
    path = try_to_load_from_cache(repo, "onnx/model.onnx", revision=revision)
    if not isinstance(path, str):
        pytest.skip(f"{repo} ONNX model not in the local HF cache")


def test_embedder_matches_former_torch_vectors():
    _require_cached(DEFAULT_EMBEDDING_MODEL, EMBEDDING_REVISION)
    vectors = OnnxEmbedder().encode(
        ["La politique de contrôle d'accès doit être revue chaque année.", "ok"]
    )
    assert vectors.shape == (2, 384)
    assert vectors[0][:6] == pytest.approx(
        [-0.3861, 0.11672, -0.07101, -0.11334, 0.05368, 0.19934], abs=1e-4
    )
    assert vectors[1][:6] == pytest.approx(
        [0.1302, -0.0867, 0.10374, 0.0367, -0.06669, -0.15705], abs=1e-4
    )


def test_reranker_matches_former_torch_scores():
    _require_cached(RERANKER_MODEL, RERANKER_REVISION)
    query = "how often is the access policy reviewed?"
    scores = OnnxCrossEncoder().predict(
        [
            (query, "The access control policy is reviewed every year."),
            (query, "Backups are tested quarterly."),
        ]
    )
    assert list(scores) == pytest.approx([8.5251, -7.9884], abs=1e-3)
