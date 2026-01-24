import json
import os
import argparse
from typing import Dict, Set, Tuple

from dgsi_scraper.retriever import DocumentRetriever


def load_ids_from_json(path: str) -> Dict[int, str]:
    """
    Load document IDs and their canonical class from decision_ids_by_class_ALLSOURCES.json

    Returns:
        dict {doc_id: class_label}
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    ids_by_class = data.get("ids_by_class", {})
    doc_id_to_class = {}

    for class_label, items in ids_by_class.items():
        for item in items:
            doc_id = int(item["id"])
            doc_id_to_class[doc_id] = class_label

    return doc_id_to_class


def ensure_embeddings_table(conn) -> None:
    """Create the document-level embeddings table if it does not exist."""
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS public.dgsi_document_embeddings (
              doc_id        BIGINT PRIMARY KEY,
              label         TEXT NOT NULL,
              embedding     REAL[] NOT NULL,
              embedding_dim INT  NOT NULL,
              model_name    TEXT,
              created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            """
        )
    conn.commit()


def index_embeddings_for_ids(
    retriever: DocumentRetriever,
    doc_id_to_class: Dict[int, str],
    batch_size: int = 50,
    model_name: str = "",
):
    """
    Generate and store embeddings for a specific set of document IDs.
    """
    conn = retriever.get_connection()
    ensure_embeddings_table(conn)

    try:
        with conn.cursor() as cur:
            doc_ids = list(doc_id_to_class.keys())
            cur.execute(
                """
                SELECT id, text_plain
                FROM dgsi_documents
                WHERE id = ANY(%s)
                """,
                (doc_ids,),
            )
            rows = cur.fetchall()

        total = len(rows)
        print(f"Found {total} documents to index")

        indexed = 0

        for i in range(0, total, batch_size):
            batch = rows[i : i + batch_size]
            print(
                f"Processing batch {i // batch_size + 1} / {(total + batch_size - 1) // batch_size}"
            )

            updates = []

            for doc_id, text in batch:
                if not text or not text.strip():
                    continue

                embedding = retriever.generate_embedding(text)
                emb_list = embedding.tolist()
                emb_dim = len(emb_list)
                label = doc_id_to_class.get(int(doc_id))
                if not label:
                    continue
                updates.append((int(doc_id), label, emb_list, emb_dim))

            with conn.cursor() as cur:
                for doc_id, label, embedding, emb_dim in updates:
                    cur.execute(
                        """
                        INSERT INTO public.dgsi_document_embeddings
                          (doc_id, label, embedding, embedding_dim, model_name)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (doc_id) DO UPDATE SET
                          label = EXCLUDED.label,
                          embedding = EXCLUDED.embedding,
                          embedding_dim = EXCLUDED.embedding_dim,
                          model_name = EXCLUDED.model_name;
                        """,
                        (doc_id, label, embedding, emb_dim, model_name),
                    )

            conn.commit()
            indexed += len(updates)
            print(f"Indexed {indexed} / {total}")

        print("Embedding indexing completed.")

    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(
        description="Index embeddings only for documents with mapped decision classes"
    )
    parser.add_argument(
        "--db-dsn",
        type=str,
        default=os.getenv("DGSISCRAPER_DB_DSN"),
        help="PostgreSQL connection string",
    )
    parser.add_argument(
        "--decision-json",
        type=str,
        required=True,
        help="Path to decision_ids_by_class_ALLSOURCES.json",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Batch size for embedding generation",
    )

    args = parser.parse_args()

    if not args.db_dsn:
        raise RuntimeError("Database DSN not provided")

    print("Loading decision IDs...")
    doc_id_to_class = load_ids_from_json(args.decision_json)
    print(f"Total unique documents to index: {len(doc_id_to_class)}")

    retriever = DocumentRetriever(
        db_dsn=args.db_dsn,
    )

    index_embeddings_for_ids(
        retriever=retriever,
        doc_id_to_class=doc_id_to_class,
        batch_size=args.batch_size,
    )


if __name__ == "__main__":
    main()