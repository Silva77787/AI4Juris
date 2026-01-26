import os
import argparse
from collections import Counter, defaultdict
from typing import List, Tuple, Dict, Any, Optional

import numpy as np

import psycopg
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score


def ensure_clusters_table(conn) -> None:
    """
    Store clustering assignments. PK is (run_id, doc_id) so you can compare runs.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS public.dgsi_document_clusters (
              run_id      TEXT NOT NULL,
              doc_id      BIGINT NOT NULL,
              true_label  TEXT NOT NULL,
              cluster_id  INT  NOT NULL,
              created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
              PRIMARY KEY (run_id, doc_id)
            );
            """
        )
        # Helpful indexes for analysis
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS dgsi_document_clusters_run_idx
            ON public.dgsi_document_clusters (run_id);
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS dgsi_document_clusters_run_cluster_idx
            ON public.dgsi_document_clusters (run_id, cluster_id);
            """
        )
    conn.commit()


def fetch_embeddings(
    conn,
    limit: Optional[int] = None,
    where_label_in: Optional[List[str]] = None,
) -> Tuple[List[int], List[str], np.ndarray]:
    """
    Fetch (doc_id, label, embedding[]) from public.dgsi_document_embeddings.
    Returns:
      doc_ids: list[int]
      labels: list[str]
      X: np.ndarray shape (N, D), dtype float32
    """
    sql = """
        SELECT doc_id, label, embedding
        FROM public.dgsi_document_embeddings
    """
    params: List[Any] = []
    clauses: List[str] = []

    if where_label_in:
        clauses.append("label = ANY(%s)")
        params.append(where_label_in)

    if clauses:
        sql += " WHERE " + " AND ".join(clauses)

    sql += " ORDER BY doc_id ASC"

    if limit is not None and limit > 0:
        sql += " LIMIT %s"
        params.append(limit)

    with conn.cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()

    if not rows:
        return [], [], np.empty((0, 0), dtype=np.float32)

    doc_ids: List[int] = []
    labels: List[str] = []

    # embedding is REAL[] in Postgres -> comes as Python list[float]
    # Build array efficiently
    emb_list: List[np.ndarray] = []
    for doc_id, label, emb in rows:
        if emb is None:
            continue
        doc_ids.append(int(doc_id))
        labels.append(str(label))
        emb_list.append(np.asarray(emb, dtype=np.float32))

    X = np.vstack(emb_list) if emb_list else np.empty((0, 0), dtype=np.float32)
    return doc_ids, labels, X


def l2_normalize(X: np.ndarray, eps: float = 1e-12) -> np.ndarray:
    norms = np.linalg.norm(X, axis=1, keepdims=True)
    norms = np.maximum(norms, eps)
    return X / norms


def compute_purity(labels: List[str], cluster_ids: np.ndarray) -> Dict[int, Dict[str, Any]]:
    """
    For each cluster, compute dominant label + purity.
    purity(cluster) = max_label_count / cluster_size
    """
    cluster_to_counts: Dict[int, Counter] = defaultdict(Counter)
    for y, c in zip(labels, cluster_ids.tolist()):
        cluster_to_counts[int(c)][y] += 1

    out: Dict[int, Dict[str, Any]] = {}
    for c, ctr in cluster_to_counts.items():
        total = sum(ctr.values())
        top_label, top_count = ctr.most_common(1)[0]
        out[c] = {
            "size": total,
            "top_label": top_label,
            "top_count": top_count,
            "purity": (top_count / total) if total else 0.0,
            "label_counts": dict(ctr),
        }
    return out


def upsert_clusters(
    conn,
    run_id: str,
    doc_ids: List[int],
    labels: List[str],
    cluster_ids: np.ndarray,
    batch_size: int = 2000,
) -> None:
    """
    Insert/Update assignments in public.dgsi_document_clusters.
    """
    assert len(doc_ids) == len(labels) == len(cluster_ids)

    with conn.cursor() as cur:
        for i in range(0, len(doc_ids), batch_size):
            chunk_doc_ids = doc_ids[i : i + batch_size]
            chunk_labels = labels[i : i + batch_size]
            chunk_clusters = cluster_ids[i : i + batch_size].tolist()

            rows = [
                (run_id, int(did), str(lab), int(cid))
                for did, lab, cid in zip(chunk_doc_ids, chunk_labels, chunk_clusters)
            ]

            cur.executemany(
                """
                INSERT INTO public.dgsi_document_clusters (run_id, doc_id, true_label, cluster_id)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (run_id, doc_id) DO UPDATE SET
                  true_label = EXCLUDED.true_label,
                  cluster_id = EXCLUDED.cluster_id;
                """,
                rows,
            )
    conn.commit()


def main():
    parser = argparse.ArgumentParser(description="Run KMeans over dgsi_document_embeddings and store clusters in Postgres.")
    parser.add_argument("--db-dsn", type=str, default=os.getenv("DGSISCRAPER_DB_DSN"), help="PostgreSQL DSN")
    parser.add_argument("--run-id", type=str, required=True, help="Identifier for this clustering run (e.g., kmeans14_l2_r42)")
    parser.add_argument("--k", type=int, default=7, help="Number of clusters (default 7)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--normalize", type=str, choices=["none", "l2"], default="l2", help="Vector normalization before KMeans")
    parser.add_argument("--limit", type=int, default=0, help="Optional limit of rows (0 means no limit)")
    parser.add_argument("--silhouette", action="store_true", help="Compute silhouette score (can take a bit)")
    parser.add_argument("--label-filter", type=str, default="NEGADA,IMPROCEDENTE,CONFIRMADA,PROCEDENTE,REVOGADA,PROVIDO,CONCEDIDA", help="Comma-separated labels to include (optional)")
    args = parser.parse_args()

    if not args.db_dsn:
        raise RuntimeError("Missing DB DSN. Set DGSISCRAPER_DB_DSN or pass --db-dsn.")

    limit = args.limit if args.limit and args.limit > 0 else None
    label_filter = [x.strip() for x in args.label_filter.split(",") if x.strip()] or None

    conn = psycopg.connect(args.db_dsn)
    try:
        ensure_clusters_table(conn)

        print("Fetching embeddings from public.dgsi_document_embeddings ...")
        doc_ids, labels, X = fetch_embeddings(conn, limit=limit, where_label_in=label_filter)
        if X.size == 0:
            raise RuntimeError("No embeddings found to cluster (X is empty).")

        print(f"Loaded N={X.shape[0]} embeddings with D={X.shape[1]}.")

        if args.normalize == "l2":
            print("Applying L2 normalization ...")
            X = l2_normalize(X)

        print(f"Running KMeans(k={args.k}, seed={args.seed}) ...")
        km = KMeans(n_clusters=args.k, random_state=args.seed, n_init="auto")
        cluster_ids = km.fit_predict(X)

        if args.silhouette:
            # silhouette needs at least 2 clusters and not all points identical; KMeans should ensure clusters, but guard anyway.
            try:
                s = silhouette_score(X, cluster_ids, metric="euclidean")
                print(f"Silhouette score: {s:.4f}")
            except Exception as e:
                print(f"Silhouette score failed: {e}")

        purity = compute_purity(labels, cluster_ids)

        # Summaries
        print("\nCluster purity summary (top label per cluster)")
        for c in sorted(purity.keys()):
            info = purity[c]
            print(
                f"cluster={c:02d} size={info['size']:4d} "
                f"top_label={info['top_label']:<12s} purity={info['purity']:.3f}"
            )

        # Save assignments
        print("\nWriting cluster assignments to public.dgsi_document_clusters")
        upsert_clusters(conn, args.run_id, doc_ids, labels, cluster_ids)

    finally:
        conn.close()


if __name__ == "__main__":
    main()