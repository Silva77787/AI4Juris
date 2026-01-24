from __future__ import annotations

import os
import json
import argparse
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter
from typing import Dict, List, Tuple, Optional

import numpy as np
import psycopg
from joblib import dump
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC
from sklearn.metrics import classification_report, accuracy_score, f1_score
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import Pipeline



# JSON -> {doc_id: label}

def load_ids_and_labels_from_json(ids_json_path: str) -> dict[int, str]:
    with open(ids_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    ids_by_class = data.get("ids_by_class")
    if not isinstance(ids_by_class, dict):
        raise ValueError("ids_json does not contain an 'ids_by_class' dict")

    id_to_label: dict[int, str] = {}
    for label, entries in ids_by_class.items():
        if not isinstance(entries, list):
            continue
        for item in entries:
            if not isinstance(item, dict):
                continue
            doc_id = item.get("id")
            if doc_id is None:
                continue
            try:
                doc_id_int = int(doc_id)
            except Exception:
                continue
            # keep first occurrence
            id_to_label.setdefault(doc_id_int, str(label))

    if not id_to_label:
        raise ValueError("No doc ids were parsed from ids_json")

    return id_to_label



# DB -> load texts for ids
# labels come from JSON

def load_texts_from_db_for_ids(
    db_dsn: str,
    table: str,
    id_col: str,
    text_col: str,
    id_to_label: dict[int, str],
    where: str | None = None,
    limit: int | None = None,
    chunk_size: int = 2000,
) -> tuple[list[int], list[str], np.ndarray]:
    target_ids = list(id_to_label.keys())
    if limit is not None:
        target_ids = sorted(target_ids)[: int(limit)]

    base_where = f"{id_col} = ANY(%s)"
    if where:
        base_where = f"({where}) AND ({base_where})"

    sql = f"SELECT {id_col}, {text_col} FROM {table} WHERE {base_where}"

    doc_ids: list[int] = []
    texts: list[str] = []
    labels: list[str] = []

    with psycopg.connect(db_dsn) as conn:
        with conn.cursor() as cur:
            for i in range(0, len(target_ids), chunk_size):
                chunk = target_ids[i : i + chunk_size]
                cur.execute(sql, (chunk,))
                rows = cur.fetchall()

                for _id, txt in rows:
                    if txt is None:
                        continue
                    txt = str(txt)
                    if not txt.strip():
                        continue

                    try:
                        _id_int = int(_id)
                    except Exception:
                        continue

                    lab = id_to_label.get(_id_int)
                    if lab is None:
                        continue

                    doc_ids.append(_id_int)
                    texts.append(txt)
                    labels.append(lab)

    if not texts:
        raise ValueError(
            "No texts loaded. Check: table/columns, id values in JSON, and WHERE clause."
        )

    return doc_ids, texts, np.array(labels, dtype=object)


def filter_minority_classes(
    texts: list[str], labels: np.ndarray, min_count: int
) -> tuple[list[str], np.ndarray, list[str]]:
    c = Counter(labels)
    keep = {lab for lab, n in c.items() if n >= min_count}
    removed = sorted([lab for lab, n in c.items() if n < min_count])

    new_texts: list[str] = []
    new_labels: list[str] = []
    for t, y in zip(texts, labels):
        if y in keep:
            new_texts.append(t)
            new_labels.append(y)

    return new_texts, np.array(new_labels, dtype=object), removed


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Train TF-IDF + LinearSVC on curated DGSI subset (ids+labels from JSON), save artifacts to models/"
    )
    ap.add_argument("--db-dsn", default=os.getenv("DGSISCRAPER_DB_DSN"), help="Postgres DSN (env DGSISCRAPER_DB_DSN)")
    ap.add_argument("--table", default="public.dgsi_documents", help="Table containing text_plain and id")
    ap.add_argument("--id-col", default="id")
    ap.add_argument("--text-col", default="text_plain")
    ap.add_argument("--ids-json", required=True, help="Path to decision_ids_by_class_ALLSOURCES.json")
    ap.add_argument("--where", default=None, help="Optional SQL WHERE (without 'WHERE')")
    ap.add_argument("--limit", type=int, default=None, help="Optional LIMIT applied to ids list")
    ap.add_argument("--min-class-count", type=int, default=100, help="Drop classes with <N samples")

    # TF-IDF params
    ap.add_argument("--ngram-max", type=int, default=3)
    ap.add_argument("--min-df", type=int, default=5)
    ap.add_argument("--max-df", type=float, default=0.90)
    ap.add_argument("--max-features", type=int, default=0, help="0 disables")
    ap.add_argument("--sublinear-tf", action="store_true", default=True)
    ap.add_argument("--no-sublinear-tf", dest="sublinear_tf", action="store_false")
    ap.add_argument("--lowercase", action="store_true", default=True)

    # SVM params
    ap.add_argument("--C", type=float, default=1.0)
    ap.add_argument("--class-weight", default="balanced", choices=["balanced", "none"])
    ap.add_argument("--seed", type=int, default=42)

    # Cross-validation (evaluation)
    ap.add_argument("--cv-folds", type=int, default=5, help="Stratified K-folds for CV evaluation")
    ap.add_argument("--no-cv", dest="do_cv", action="store_false", help="Skip CV evaluation")
    ap.set_defaults(do_cv=True)

    # Output
    ap.add_argument("--out-dir", default="models", help="Directory to write artifacts")
    ap.add_argument("--prefix", default="tfidf_svm", help="Filename prefix for artifacts")
    ap.add_argument("--save-report", action="store_true", help="Also write a training report txt")

    args = ap.parse_args()

    if not args.db_dsn:
        raise SystemExit("Missing --db-dsn and env DGSISCRAPER_DB_DSN is not set")

    out_dir = Path(args.out_dir)
    ensure_dir(out_dir)

    # 1) Load curated ids + labels
    id_to_label = load_ids_and_labels_from_json(args.ids_json)

    # 2) Load texts from DB restricted to those ids
    doc_ids, texts, labels = load_texts_from_db_for_ids(
        db_dsn=args.db_dsn,
        table=args.table,
        id_col=args.id_col,
        text_col=args.text_col,
        id_to_label=id_to_label,
        where=args.where,
        limit=args.limit,
    )

    print(f"Loaded N={len(texts)} documents (from ids_json subset)")

    # 3) Filter minority classes (default 100 to match your earlier KNN filtering)
    if args.min_class_count and args.min_class_count > 0:
        texts, labels, removed = filter_minority_classes(texts, labels, args.min_class_count)
        print(f"Removed classes (<{args.min_class_count}): {removed}")
        print(f"Remaining N={len(texts)}")

    # 4) Distribution
    dist = Counter(labels)
    print("\nLabel distribution (top 20):")
    for lab, n in dist.most_common(20):
        print(f"  {lab:15s} {n}")

    # 5) Define model (vectorizer + LinearSVC)
    max_features = None if args.max_features <= 0 else args.max_features
    cw = None if args.class_weight == "none" else "balanced"

    pipeline = Pipeline(
        steps=[
            (
                "tfidf",
                TfidfVectorizer(
                    ngram_range=(1, args.ngram_max),
                    min_df=args.min_df,
                    max_df=args.max_df,
                    max_features=max_features,
                    sublinear_tf=args.sublinear_tf,
                    lowercase=args.lowercase,
                ),
            ),
            ("svm", LinearSVC(C=args.C, class_weight=cw, random_state=args.seed)),
        ]
    )

    # 6) Cross-validation evaluation (this is the meaningful metric)
    cv_summary: dict[str, float] | None = None
    y_pred_all: np.ndarray | None = None

    if args.do_cv and args.cv_folds and args.cv_folds > 1:
        skf = StratifiedKFold(n_splits=int(args.cv_folds), shuffle=True, random_state=int(args.seed))
        y_true_all: list[str] = []
        y_pred_all_list: list[str] = []

        fold_acc: list[float] = []
        fold_f1m: list[float] = []
        fold_f1w: list[float] = []

        for fold_idx, (tr_idx, te_idx) in enumerate(skf.split(texts, labels), start=1):
            X_tr = [texts[i] for i in tr_idx]
            y_tr = labels[tr_idx]
            X_te = [texts[i] for i in te_idx]
            y_te = labels[te_idx]

            pipeline.fit(X_tr, y_tr)
            y_hat = pipeline.predict(X_te)

            acc = accuracy_score(y_te, y_hat)
            f1m = f1_score(y_te, y_hat, average="macro", zero_division=0)
            f1w = f1_score(y_te, y_hat, average="weighted", zero_division=0)

            fold_acc.append(float(acc))
            fold_f1m.append(float(f1m))
            fold_f1w.append(float(f1w))

            y_true_all.extend(list(y_te))
            y_pred_all_list.extend(list(y_hat))

            print(f"\nFold {fold_idx}")
            print(f"Accuracy: {acc:.4f}")

        y_pred_all = np.array(y_pred_all_list, dtype=object)
        y_true_np = np.array(y_true_all, dtype=object)

        cv_summary = {
            "folds": float(args.cv_folds),
            "accuracy_mean": float(np.mean(fold_acc)),
            "accuracy_std": float(np.std(fold_acc)),
            "f1_macro_mean": float(np.mean(fold_f1m)),
            "f1_macro_std": float(np.std(fold_f1m)),
            "f1_weighted_mean": float(np.mean(fold_f1w)),
            "f1_weighted_std": float(np.std(fold_f1w)),
        }

        print("\nCross-validation summary")
        print(f"Mean accuracy: {cv_summary['accuracy_mean']:.4f}")
        print(f"Std accuracy:  {cv_summary['accuracy_std']:.4f}")
        print(f"Mean F1 macro: {cv_summary['f1_macro_mean']:.4f}")
        print(f"Mean F1 wght:  {cv_summary['f1_weighted_mean']:.4f}")

        # Detailed CV report (aggregated over all folds)
        cv_report_text = classification_report(y_true_np, y_pred_all, zero_division=0)

    else:
        cv_report_text = "(CV disabled)\n"

    # 7) Train final model on ALL data and save it
    pipeline.fit(texts, labels)

    # Extract and save components (keep your artifact format)
    vectorizer: TfidfVectorizer = pipeline.named_steps["tfidf"]
    clf: LinearSVC = pipeline.named_steps["svm"]

    # 7) Save artifacts
    vec_path = out_dir / f"{args.prefix}.vectorizer.joblib"
    svm_path = out_dir / f"{args.prefix}.svm.joblib"
    meta_path = out_dir / f"{args.prefix}.metadata.json"

    dump(vectorizer, vec_path)
    dump(clf, svm_path)

    metadata = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "db_table": args.table,
        "id_col": args.id_col,
        "text_col": args.text_col,
        "ids_json": args.ids_json,
        "where": args.where,
        "limit": args.limit,
        "n_docs": int(len(texts)),
        "label_distribution": {k: int(v) for k, v in dist.items()},
        "tfidf": {
            "ngram_range": [1, int(args.ngram_max)],
            "min_df": int(args.min_df),
            "max_df": float(args.max_df),
            "max_features": None if max_features is None else int(max_features),
            "sublinear_tf": bool(args.sublinear_tf),
            "lowercase": bool(args.lowercase),
        },
        "svm": {
            "model": "LinearSVC",
            "C": float(args.C),
            "class_weight": None if cw is None else str(cw),
            "random_state": int(args.seed),
        },
        "cv_metrics": cv_summary,
        "artifacts": {
            "vectorizer": str(vec_path),
            "svm": str(svm_path),
        },
    }

    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    print("\nSaved artifacts:")
    print(f"  Vectorizer: {vec_path}")
    print(f"  SVM:        {svm_path}")
    print(f"  Metadata:   {meta_path}")

    if args.save_report:
        report_path = out_dir / f"{args.prefix}.cv_report.txt"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("Cross-validation report (aggregated over folds)\n")
            if cv_summary is not None:
                f.write(f"Folds: {int(args.cv_folds)}\n")
                f.write(f"Accuracy mean: {cv_summary['accuracy_mean']:.6f}\n")
                f.write(f"Accuracy std:  {cv_summary['accuracy_std']:.6f}\n")
                f.write(f"F1 macro mean: {cv_summary['f1_macro_mean']:.6f}\n")
                f.write(f"F1 macro std:  {cv_summary['f1_macro_std']:.6f}\n")
                f.write(f"F1 wght mean:  {cv_summary['f1_weighted_mean']:.6f}\n")
                f.write(f"F1 wght std:   {cv_summary['f1_weighted_std']:.6f}\n\n")
            f.write(cv_report_text)
        print(f"  Report:     {report_path}")


if __name__ == "__main__":
    main()