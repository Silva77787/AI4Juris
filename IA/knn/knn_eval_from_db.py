import argparse
import os

import numpy as np
import psycopg
from sklearn.model_selection import StratifiedKFold
from sklearn.neighbors import KNeighborsClassifier
from sklearn.preprocessing import normalize
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score


def load_embeddings(db_dsn: str):
    with psycopg.connect(db_dsn) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT doc_id, label, embedding
                FROM public.dgsi_document_embeddings
            """)
            rows = cur.fetchall()

    doc_ids = []
    labels = []
    X = []

    for doc_id, label, emb in rows:
        doc_ids.append(doc_id)
        labels.append(label)
        X.append(emb)

    X = np.array(X, dtype=np.float32)
    labels = np.array(labels)

    return X, labels, doc_ids


def main():
    parser = argparse.ArgumentParser(description="Run KNN on document embeddings")
    parser.add_argument("--db-dsn", default=os.getenv("DGSISCRAPER_DB_DSN"))
    parser.add_argument("--k", type=int, default=7)
    parser.add_argument("--metric", default="cosine")
    parser.add_argument("--test-size", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=42)

    args = parser.parse_args()

    if not args.db_dsn:
        raise RuntimeError("DB DSN not provided")

    print("Loading embeddings from DB...")
    X, y, _ = load_embeddings(args.db_dsn)
    print(f"Loaded {len(X)} documents")

    # Remove minority classes
    min_samples = 50 
    unique, counts = np.unique(y, return_counts=True)
    label_counts = dict(zip(unique, counts))

    kept_labels = {lbl for lbl, c in label_counts.items() if c >= min_samples}
    removed_labels = {lbl for lbl, c in label_counts.items() if c < min_samples}

    if removed_labels:
        print(f"Removing minority classes (<{min_samples} samples): {sorted(removed_labels)}")

    mask = np.array([lbl in kept_labels for lbl in y])
    X = X[mask]
    y = y[mask]

    print(f"Remaining documents after filtering: {len(X)}")

    print("Applying L2 normalization...")
    X = normalize(X, norm="l2")

    skf = StratifiedKFold(
        n_splits=5,
        shuffle=True,
        random_state=args.seed,
    )

    accs = []
    reports = []

    fold = 1
    for train_idx, test_idx in skf.split(X, y):
        print(f"\nFold {fold}")

        X_train, X_test = X[train_idx], X[test_idx]
        y_train, y_test = y[train_idx], y[test_idx]

        knn = KNeighborsClassifier(
            n_neighbors=args.k,
            metric=args.metric,
            weights="distance",
        )
        knn.fit(X_train, y_train)

        y_pred = knn.predict(X_test)

        acc = accuracy_score(y_test, y_pred)
        accs.append(acc)

        print("Accuracy:", acc)
        print(classification_report(y_test, y_pred, digits=4))

        fold += 1

    print("\nCross-validation summary")
    print(f"Mean accuracy: {np.mean(accs):.4f}")
    print(f"Std accuracy:  {np.std(accs):.4f}")


if __name__ == "__main__":
    main()