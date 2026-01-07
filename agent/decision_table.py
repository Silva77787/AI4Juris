# db_extras.py
import os
import gzip
import hashlib
from datetime import datetime, timezone
import psycopg
from typing import Any, Iterable, Optional

DB_DSN = os.getenv("DGSISCRAPER_DB_DSN")
DB_ENABLED = bool(DB_DSN)

class DecisionRow:
    id: int
    document_id: int
    decision_index: int
    decision_sha256: str
    decision_text: str
    created_at: str

def db_connect():
    if not DB_ENABLED:
        raise RuntimeError("DGSISCRAPER_DB_DSN is not set.")
    if psycopg is None:
        raise RuntimeError("psycopg is not installed. Install with: pip install 'psycopg[binary]'")
    return psycopg.connect(DB_DSN)


def gzip_bytes(s: str) -> bytes:
    return gzip.compress(s.encode("utf-8"))


def sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def ensure_decision_table(conn) -> None:
    """
    A table to store big text chunks linked to dgsi_documents(id).
    - ON DELETE CASCADE: if a document is removed, chunks go too.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS dgsi_document_decision (
              id BIGSERIAL PRIMARY KEY,
              document_id BIGINT NOT NULL REFERENCES dgsi_documents(id) ON DELETE CASCADE,
              decision_index INT NOT NULL,
              decision_sha256 TEXT NOT NULL,
              decision_text TEXT NOT NULL,
              decision_gzip BYTEA,
              created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
              UNIQUE (document_id, decision_index)
            );
            """
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS dgsi_document_decision_document_id_idx "
            "ON dgsi_document_decision(document_id);"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS dgsi_document_decision_sha_idx "
            "ON dgsi_document_decision(decision_sha256);"
        )
    conn.commit()


def insert_decision(
    conn,
    document_id: int,
    decision_text: str,
    decision_index: int = 0,
    store_gzip: bool = True,
) -> int:
    """
    Inserts/updates a decision for a given dgsi_documents.id.
    Returns the decision row id.
    """
    decision_hash = sha256_hex(decision_text)
    decision_gz = gzip_bytes(decision_text) if store_gzip else None
    created_at = datetime.now(timezone.utc)

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO dgsi_document_decision (
              document_id, decision_index, decision_sha256, decision_text, decision_gzip, created_at
            ) VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (document_id, decision_index) DO UPDATE SET
              decision_sha256 = EXCLUDED.decision_sha256,
              decision_text = EXCLUDED.decision_text,
              decision_gzip = EXCLUDED.decision_gzip,
              created_at = EXCLUDED.created_at
            RETURNING id;
            """,
            (document_id, decision_index, decision_hash, decision_text, decision_gz, created_at),
        )
        row_id = int(cur.fetchone()[0])
    conn.commit()
    return row_id

def get_decision(
    conn,
    document_id: int,
    query: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    order: str = "decision_index",
) -> list[DecisionRow]:
    """
    Fetch decisions for a document_id.

    If query is provided, filters decisions where decision_text matches query (case-insensitive).
    """
    if order not in {"decision_index", "created_at", "id"}:
        raise ValueError("order must be one of: decision_index, created_at, id")

    params: list[Any] = [document_id]
    where = "WHERE document_id = %s"

    if query:
        # Simple substring search. If you want fast full-text search, see note below.
        where += " AND decision_text ILIKE %s"
        params.append(f"%{query}%")

    sql = f"""
        SELECT id, document_id, decision_index, decision_sha256, decision_text, created_at::text
        FROM dgsi_document_decision
        {where}
        ORDER BY {order} ASC
        LIMIT %s OFFSET %s;
    """
    params.extend([limit, offset])

    out: list[DecisionRow] = []
    with conn.cursor() as cur:
        cur.execute(sql, tuple(params))
        for row in cur.fetchall():
            out.append(
                DecisionRow(
                    id=int(row[0]),
                    document_id=int(row[1]),
                    decision_index=int(row[2]),
                    decision_sha256=str(row[3]),
                    decision_text=str(row[4]),
                    created_at=str(row[5]),
                )
            )
    return out
