from __future__ import annotations

import os
import argparse
from collections import Counter

import numpy as np
import psycopg
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import StratifiedKFold
from sklearn.svm import LinearSVC
from sklearn.metrics import classification_report, accuracy_score, f1_score, confusion_matrix

import json
from typing import Dict, List, Tuple, Optional


def load_texts_and_labels(
    db_dsn: str,
    table: str,
    text_col: str,
    label_col: str,
    id_col: str | None = None,
    where: str | None = None,
    limit: int | None = None,
):
    """
    Loads (id?), label, text from Postgres.
    Returns: ids (or None), texts (list[str]), labels (np.ndarray[str])

    NOTE: This is the generic loader (label comes from DB).
          If you want to restrict to a curated subset of doc_ids and labels from a JSON,
          use `load_texts_and_labels_from_ids_json`.
    """
    cols = []
    if id_col:
        cols.append(id_col)
    cols += [label_col, text_col]

    sql = f"SELECT {', '.join(cols)} FROM {table}"
    if where:
        sql += f" WHERE {where}"
    if limit:
        sql += f" LIMIT {int(limit)}"

    with psycopg.connect(db_dsn) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()

    ids: list = []
    texts: list[str] = []
    labels: list[str] = []

    for row in rows:
        if id_col:
            _id, lab, txt = row
            ids.append(_id)
        else:
            lab, txt = row

        if txt is None:
            txt = ""
        txt = str(txt)

        if not txt.strip():
            continue

        labels.append(str(lab))
        texts.append(txt)

    labels_arr = np.array(labels, dtype=object)
    ids_out = ids if id_col else None

    return ids_out, texts, labels_arr


def filter_minority_classes(texts, labels, min_count: int):
    c = Counter(labels)
    keep = {lab for lab, n in c.items() if n >= min_count}
    removed = sorted([lab for lab, n in c.items() if n < min_count])

    new_texts = []
    new_labels = []
    for t, y in zip(texts, labels):
        if y in keep:
            new_texts.append(t)
            new_labels.append(y)

    return new_texts, np.array(new_labels, dtype=object), removed


# --- Helper functions for loading from ids_json ---
def load_ids_and_labels_from_json(ids_json_path: str) -> dict[int, str]:
    """Return mapping {doc_id: label} from the decision_ids_by_class JSON.

    Expected shape (based on your file):
      {
        "ids_by_class": {
          "LABEL_A": [{"id": 123, ...}, ...],
          "LABEL_B": [{"id": 456, ...}, ...]
        }
      }

    If the JSON has a slightly different shape, adapt here.
    """
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
            # If duplicates exist, keep the first label encountered (should not happen ideally)
            id_to_label.setdefault(doc_id_int, str(label))

    if not id_to_label:
        raise ValueError("No doc ids were parsed from ids_json")

    return id_to_label


def load_texts_and_labels_from_ids_json(
    db_dsn: str,
    table: str,
    text_col: str,
    id_col: str,
    ids_json_path: str,
    where: str | None = None,
    limit: int | None = None,
    chunk_size: int = 2000,
):
    """Load texts from DB restricted to doc ids in JSON; labels come from JSON.

    Returns: doc_ids(list[int]), texts(list[str]), labels(np.ndarray[str])
    """
    id_to_label = load_ids_and_labels_from_json(ids_json_path)
    target_ids = list(id_to_label.keys())

    # Apply optional LIMIT at the id-list level (deterministic order by id)
    if limit is not None:
        target_ids = sorted(target_ids)[: int(limit)]

    base_where = f"{id_col} = ANY(%s)"
    if where:
        # user-provided where is appended with AND
        base_where = f"({where}) AND ({base_where})"

    sql = f"SELECT {id_col}, {text_col} FROM {table} WHERE {base_where}"

    doc_ids: list[int] = []
    texts: list[str] = []
    labels: list[str] = []

    with psycopg.connect(db_dsn) as conn:
        with conn.cursor() as cur:
            # query in chunks to avoid huge parameter payloads
            for i in range(0, len(target_ids), chunk_size):
                chunk = target_ids[i : i + chunk_size]
                cur.execute(sql, (chunk,))
                rows = cur.fetchall()

                for _id, txt in rows:
                    if txt is None:
                        txt = ""
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


def main():
    ap = argparse.ArgumentParser(description="TF-IDF + Linear SVM evaluation from Postgres")
    ap.add_argument("--db-dsn", default=os.getenv("DGSISCRAPER_DB_DSN"), help="Postgres DSN (env DGSISCRAPER_DB_DSN)")
    ap.add_argument("--table", default="public.dgsi_documents", help="Source table with text + label")
    ap.add_argument("--text-col", default="text_plain", help="Text column name (e.g., text_plain)")
    ap.add_argument("--label-col", default="label", help="Label column name (canonical class)")
    ap.add_argument("--id-col", default="id", help="ID column name (optional). Use '' to disable.")
    ap.add_argument(
        "--ids-json",
        default=None,
        help="Path to decision_ids_by_class_ALLSOURCES.json; if set, restricts docs to those ids and uses labels from JSON.",
    )
    ap.add_argument("--where", default=None, help="Optional SQL WHERE (without 'WHERE')")
    ap.add_argument("--limit", type=int, default=None, help="Optional LIMIT")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--folds", type=int, default=5)
    ap.add_argument("--min-class-count", type=int, default=0, help="Drop classes with <N samples (0 disables)")

    # TF-IDF params
    ap.add_argument("--ngram-max", type=int, default=3, help="Use ngrams (1..N)")
    ap.add_argument("--min-df", type=int, default=5)
    ap.add_argument("--max-df", type=float, default=0.90)
    ap.add_argument("--max-features", type=int, default=0, help="0 disables")
    ap.add_argument("--sublinear-tf", action="store_true", default=True)
    ap.add_argument("--no-sublinear-tf", dest="sublinear_tf", action="store_false")

    # Model params
    ap.add_argument("--class-weight", default="balanced", choices=["balanced", "none"])
    ap.add_argument("--C", type=float, default=1.0)

    # Outputs
    ap.add_argument("--print-confusion", action="store_true", help="Print confusion matrix (can be large)")

    args = ap.parse_args()

    if not args.db_dsn:
        raise SystemExit("Missing --db-dsn and env DGSISCRAPER_DB_DSN is not set")

    id_col = args.id_col.strip() if args.id_col is not None else None
    if id_col == "":
        id_col = None

    if args.ids_json:
        if id_col is None:
            raise SystemExit("--ids-json requires --id-col (cannot be disabled)")
        print("Loading texts from DB restricted to ids_json; labels come from JSON...")
        ids, texts, labels = load_texts_and_labels_from_ids_json(
            db_dsn=args.db_dsn,
            table=args.table,
            text_col=args.text_col,
            id_col=id_col,
            ids_json_path=args.ids_json,
            where=args.where,
            limit=args.limit,
        )
        print(f"Loaded N={len(texts)} documents from ids_json subset")
    else:
        print("Loading texts + labels from DB...")
        ids, texts, labels = load_texts_and_labels(
            db_dsn=args.db_dsn,
            table=args.table,
            text_col=args.text_col,
            label_col=args.label_col,
            id_col=id_col,
            where=args.where,
            limit=args.limit,
        )
        print(f"Loaded N={len(texts)} documents")

    if args.min_class_count and args.min_class_count > 0:
        texts, labels, removed = filter_minority_classes(texts, labels, args.min_class_count)
        print(f"Removing minority classes (<{args.min_class_count} samples): {removed}")
        print(f"Remaining documents after filtering: {len(texts)}")

    # Basic label distribution
    dist = Counter(labels)
    print("\nLabel distribution (top 20):")
    for lab, n in dist.most_common(20):
        print(f"  {lab:15s} {n}")

    # Vectorizer
    max_features = None if args.max_features <= 0 else args.max_features
    vectorizer = TfidfVectorizer(
        ngram_range=(1, args.ngram_max),
        min_df=args.min_df,
        max_df=args.max_df,
        max_features=max_features,
        sublinear_tf=args.sublinear_tf,
        strip_accents=None,
        lowercase=True,
    )

    # CV
    skf = StratifiedKFold(n_splits=args.folds, shuffle=True, random_state=args.seed)

    fold_acc = []
    fold_f1_macro = []
    fold_f1_weighted = []

    labels_unique = np.unique(labels)

    for fold_i, (train_idx, test_idx) in enumerate(skf.split(np.zeros(len(labels)), labels), start=1):
        print(f"\nFold {fold_i}")

        X_train_text = [texts[i] for i in train_idx]
        X_test_text = [texts[i] for i in test_idx]
        y_train = labels[train_idx]
        y_test = labels[test_idx]

        # Fit TF-IDF on TRAIN only (crucial)
        X_train = vectorizer.fit_transform(X_train_text)
        X_test = vectorizer.transform(X_test_text)

        cw = None if args.class_weight == "none" else "balanced"

        clf = LinearSVC(C=args.C, class_weight=cw, random_state=args.seed)
        clf.fit(X_train, y_train)

        y_pred = clf.predict(X_test)

        acc = accuracy_score(y_test, y_pred)
        f1m = f1_score(y_test, y_pred, average="macro", zero_division=0)
        f1w = f1_score(y_test, y_pred, average="weighted", zero_division=0)

        fold_acc.append(acc)
        fold_f1_macro.append(f1m)
        fold_f1_weighted.append(f1w)

        print(f"Accuracy: {acc:.4f}")
        print(f"F1 macro:  {f1m:.4f}")
        print(f"F1 wght:   {f1w:.4f}\n")

        print(classification_report(y_test, y_pred, labels=labels_unique, zero_division=0))

        if args.print_confusion:
            cm = confusion_matrix(y_test, y_pred, labels=labels_unique)
            print("Confusion matrix (rows=true, cols=pred):")
            print(labels_unique)
            print(cm)

    print("\nCross-validation summary")
    print(f"Mean accuracy: {float(np.mean(fold_acc)):.4f}  (std {float(np.std(fold_acc)):.4f})")
    print(f"Mean F1 macro:  {float(np.mean(fold_f1_macro)):.4f}  (std {float(np.std(fold_f1_macro)):.4f})")
    print(f"Mean F1 wght:   {float(np.mean(fold_f1_weighted)):.4f}  (std {float(np.std(fold_f1_weighted)):.4f})")


if __name__ == "__main__":
    main()