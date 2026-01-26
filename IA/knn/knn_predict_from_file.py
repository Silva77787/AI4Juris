from __future__ import annotations

import argparse
import os
from functools import lru_cache
from typing import List, Tuple

import numpy as np
from sklearn.neighbors import KNeighborsClassifier
from sklearn.preprocessing import normalize

from dgsi_scraper.knn_eval_from_db import load_embeddings
from dgsi_scraper.retriever import DocumentRetriever


def _require_db_dsn(db_dsn: str | None) -> str:
    if db_dsn and db_dsn.strip():
        return db_dsn
    env = os.getenv("DGSISCRAPER_DB_DSN")
    if env and env.strip():
        return env
    raise RuntimeError(
        "DB DSN not provided. Pass --db-dsn or set DGSISCRAPER_DB_DSN env var."
    )


@lru_cache(maxsize=8)
def _get_training_matrix(db_dsn: str) -> Tuple[np.ndarray, np.ndarray, List[int]]:
    """Load labeled embeddings from DB and L2-normalize.

    Returns:
      X: float32 [N, D] normalized
      y: str [N]
      doc_ids: list[int] length N
    """
    X, y, doc_ids = load_embeddings(db_dsn)
    X = np.asarray(X, dtype=np.float32)
    X = normalize(X, norm="l2")
    y = np.asarray(y)
    return X, y, doc_ids


@lru_cache(maxsize=8)
def _get_retriever(db_dsn: str) -> DocumentRetriever:
    """Cache the embedding model inside DocumentRetriever."""
    return DocumentRetriever(db_dsn=db_dsn)


@lru_cache(maxsize=32)
def _get_knn_model(db_dsn: str, k: int, metric: str) -> KNeighborsClassifier:
    """Fit and cache KNN over the DB embeddings."""
    X, y, _ = _get_training_matrix(db_dsn)

    # KNN expects metric='cosine' to operate on vectors; we already L2-normalize.
    knn = KNeighborsClassifier(
        n_neighbors=int(k),
        metric=str(metric),
        weights="distance",
    )
    knn.fit(X, y)
    return knn


def predict_label_from_text(
    text: str,
    *,
    db_dsn: str | None = None,
    k: int = 9,
    metric: str = "cosine",
) -> str:
    """Predict a single decision label for an input text.

    This is the function you should call from the API.

    Returns:
      predicted_label (str)
    """
    db_dsn = _require_db_dsn(db_dsn)

    if not text or not text.strip():
        raise ValueError("Empty text")

    retriever = _get_retriever(db_dsn)
    q = retriever.generate_embedding(text, use_chunking=True).astype(np.float32)
    q = normalize(q.reshape(1, -1), norm="l2")

    knn = _get_knn_model(db_dsn, int(k), str(metric))
    pred = knn.predict(q)[0]
    return str(pred)


def predict_label_from_file(
    path: str,
    *,
    db_dsn: str | None = None,
    k: int = 9,
    metric: str = "cosine",
    encoding: str = "utf-8",
) -> str:
    """Convenience wrapper for local testing."""
    with open(path, "r", encoding=encoding, errors="ignore") as f:
        text = f.read()
    return predict_label_from_text(
        text,
        db_dsn=db_dsn,
        k=k,
        metric=metric,
    )


def main() -> None:
    p = argparse.ArgumentParser("Predict decision label for a .txt using KNN from DB")
    p.add_argument("--db-dsn", default=os.getenv("DGSISCRAPER_DB_DSN"))
    p.add_argument("--file", required=True, help="Path to txt file")
    p.add_argument("--k", type=int, default=7)
    p.add_argument("--metric", default="cosine")
    args = p.parse_args()

    label = predict_label_from_file(
        args.file,
        db_dsn=args.db_dsn,
        k=args.k,
        metric=args.metric,
    )
    print(label)


if __name__ == "__main__":
    main()