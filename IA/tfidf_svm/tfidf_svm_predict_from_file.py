from __future__ import annotations

import argparse
from pathlib import Path
from functools import lru_cache
from typing import Tuple, Optional

from joblib import load


def _read_text_file(path: str) -> str:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Input file not found: {path}")
    try:
        return p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return p.read_text(encoding="latin-1")


@lru_cache(maxsize=8)
def _load_artifacts(vectorizer_path: str, svm_path: str):
    """
    Cached loader so the API doesn't reload models on every request.
    Keyed by the *paths* to allow multiple prefixes/envs.
    """
    vectorizer = load(vectorizer_path)
    clf = load(svm_path)
    return vectorizer, clf


def predict_label_from_text(
    text: str,
    *,
    artifacts_dir: str = "models",
    prefix: str = "tfidf_svm_min100_cv5",
) -> str:
    """
    Predict a DGSI decision label from raw text using TF-IDF + LinearSVC artifacts.

    Artifacts expected:
      - {artifacts_dir}/{prefix}.vectorizer.joblib
      - {artifacts_dir}/{prefix}.svm.joblib
    """
    if not text or not text.strip():
        raise ValueError("Empty text: cannot predict label.")

    vec_path = str(Path(artifacts_dir) / f"{prefix}.vectorizer.joblib")
    svm_path = str(Path(artifacts_dir) / f"{prefix}.svm.joblib")

    vectorizer, clf = _load_artifacts(vec_path, svm_path)

    X = vectorizer.transform([text])
    y = clf.predict(X)[0]
    return str(y)


def predict_label_from_file(
    file_path: str,
    *,
    artifacts_dir: str = "models",
    prefix: str = "tfidf_svm_min100_cv5",
) -> str:
    """
    Predict label from a .txt file path (used by API or CLI).
    """
    text = _read_text_file(file_path)
    return predict_label_from_text(text, artifacts_dir=artifacts_dir, prefix=prefix)


def main(argv: Optional[list[str]] = None) -> None:
    ap = argparse.ArgumentParser(
        description="Predict DGSI decision label for a local .txt file using TF-IDF + LinearSVC artifacts."
    )
    ap.add_argument("--file", required=True, help="Path to a .txt file (plain text acórdão)")
    ap.add_argument(
        "--artifacts-dir",
        default="models",
        help="Directory containing the saved artifacts (joblib files). Default: models",
    )
    ap.add_argument(
        "--prefix",
        default="tfidf_svm_min100_cv5",
        help="Artifacts prefix. Default: tfidf_svm_min100_cv5",
    )

    args = ap.parse_args(argv)

    label = predict_label_from_file(
        args.file,
        artifacts_dir=args.artifacts_dir,
        prefix=args.prefix,
    )
    print(label)


if __name__ == "__main__":
    main()