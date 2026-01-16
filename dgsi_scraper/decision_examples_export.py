import os
import re
import json
import argparse
from typing import Optional, Dict, Any, Iterable, Tuple, List

try:
    import psycopg
except Exception:
    psycopg = None


DECISION_RE_LIST = [
    re.compile(r"(?im)^\s*Decis[aã]o\s*:\s*(.+?)\s*$"),
    re.compile(r"(?is)\bDecis[aã]o\s*:\s*(.{3,200}?)\n"),
    re.compile(r"(?im)^\s*Decis[aã]o\s*[-–—]\s*(.+?)\s*$"),
]

WHITESPACE_RE = re.compile(r"\s+")
TRAILING_PUNCT_RE = re.compile(r"[ \t\r\n]+$")


def normalize_decision(s: str) -> str:
    s = s.strip()
    s = WHITESPACE_RE.sub(" ", s)
    s = re.sub(r"(?i)^\s*decis[aã]o\s*[:\-–—]\s*", "", s).strip()
    s = s.replace("\u00a0", " ").strip() 
    s = TRAILING_PUNCT_RE.sub("", s)
    return s


def extract_decision_from_text(text_plain: str) -> Optional[str]:
    if not text_plain:
        return None
    for rx in DECISION_RE_LIST:
        m = rx.search(text_plain)
        if m:
            val = m.group(1).strip()
            val = normalize_decision(val)
            if val:
                return val
    return None


def connect():
    dsn = os.getenv("DGSISCRAPER_DB_DSN")
    if not dsn:
        raise RuntimeError(
            "Missing env var DGSISCRAPER_DB_DSN (ex: postgresql://dgsi:dgsi@localhost:5433/dgsi)"
        )
    if psycopg is None:
        raise RuntimeError("psycopg not installed. Install with: pip install 'psycopg[binary]'")
    return psycopg.connect(dsn)


def iter_docs(
    conn,
    batch_size: int,
    sources: Optional[set[str]] = None,
) -> Iterable[Tuple[int, Optional[str], Optional[str], Optional[str]]]:
    """
    Yields (id, source, decision_extra, text_plain)
    decision_extra = extra->>'Decisão'
    """
    where = ""
    params = []
    if sources:
        where = "WHERE source = ANY(%s)"
        params.append(list(sources))

    last_id = 0
    while True:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT id, source, extra->>'Decisão' AS decision_extra, text_plain
                FROM dgsi_documents
                {where}
                AND id > %s
                ORDER BY id
                LIMIT %s
                """ if where else
                """
                SELECT id, source, extra->>'Decisão' AS decision_extra, text_plain
                FROM dgsi_documents
                WHERE id > %s
                ORDER BY id
                LIMIT %s
                """,
                (params[0], last_id, batch_size) if sources else (last_id, batch_size),
            )
            rows = cur.fetchall()

        if not rows:
            break

        for (doc_id, source, decision_extra, text_plain) in rows:
            yield doc_id, source, decision_extra, text_plain
            last_id = doc_id



def main():
    ap = argparse.ArgumentParser(
        description="Export example rulings (full/partial text) per canonical decision class, using the SAME decision extraction logic as decision_rank.py."
    )
    ap.add_argument(
        "--classes",
        type=str,
        default="IMPROCEDENTE,PROCEDENTE,PROVIDO,CONFIRMADA,REVOGADA,ANULADA,ALTERADA,NULIDADE,CONCEDIDA,NEGADA,RESOLVIDO,REENVIO,INUTILIDADE,DECRETADA",
        help="Comma-separated canonical class tokens to search for (default: the 14 project classes).",
    )
    ap.add_argument("--per-class", type=int, default=1, help="How many examples to collect per class.")
    ap.add_argument("--batch-size", type=int, default=500, help="Rows fetched per batch.")
    ap.add_argument("--sources", type=str, default=None, help="Comma-separated sources to include (e.g. dgsi_stj,dgsi_sta). Default: all.")
    ap.add_argument("--max-docs", type=int, default=None, help="Optional cap for quick tests.")
    ap.add_argument("--max-chars", type=int, default=8000, help="Max chars of text_plain to store per example (ignored if --full-text).")
    ap.add_argument("--full-text", action="store_true", help="Store full text_plain (can be huge).")
    ap.add_argument("--json-out", type=str, default="decision_examples.json", help="JSON output path.")
    ap.add_argument("--show-progress-every", type=int, default=5000, help="Print progress every N docs.")

    args = ap.parse_args()

    sources = None
    if args.sources:
        sources = {s.strip() for s in args.sources.split(",") if s.strip()}

    class_tokens = [c.strip().upper() for c in args.classes.split(",") if c.strip()]

    examples: Dict[str, List[Dict[str, Any]]] = {c: [] for c in class_tokens}

    stats = {
        "total_docs_seen": 0,
        "decision_from_extra": 0,
        "decision_from_text": 0,
        "missing_decision": 0,
        "matched_docs": 0,
        "per_class_target": args.per_class,
        "classes": class_tokens,
        "found_by_class": {c: 0 for c in class_tokens},
        "missing_by_class": [],
    }

    conn = connect()


    try:
        remaining = set(class_tokens)

        for (doc_id, source_val, decision_extra, text_plain) in iter_docs(conn, args.batch_size, sources=sources):
            stats["total_docs_seen"] += 1
            if args.max_docs and stats["total_docs_seen"] >= args.max_docs:
                break

            if not remaining:
                break

            decision = None
            decision_src = None

            if decision_extra:
                d = normalize_decision(decision_extra)
                if d:
                    decision = d
                    decision_src = "extra"
                    stats["decision_from_extra"] += 1

            if not decision:
                d = extract_decision_from_text(text_plain or "")
                if d:
                    decision = d
                    decision_src = "text"
                    stats["decision_from_text"] += 1

            if not decision:
                stats["missing_decision"] += 1
                continue

            dec_up = normalize_decision(decision).upper()

            if not dec_up or " " in dec_up:
                continue

            if dec_up not in remaining:
                continue

            matched_class = dec_up

            if not args.full_text and text_plain:
                stored_text = text_plain[: args.max_chars]
            else:
                stored_text = text_plain

            examples[matched_class].append(
                {
                    "id": doc_id,
                    "source": source_val,
                    "class": matched_class,
                    "decision_extracted": decision,
                    "decision_source": decision_src,
                    "text_plain": stored_text,
                }
            )

            stats["matched_docs"] += 1
            stats["found_by_class"][matched_class] = len(examples[matched_class])

            if len(examples[matched_class]) >= args.per_class:
                remaining.discard(matched_class)

        for c in class_tokens:
            if len(examples[c]) == 0:
                stats["missing_by_class"].append(c)
    finally:
        conn.close()

    out = {
        "stats": stats,
        "examples": examples,
    }

    os.makedirs(os.path.dirname(args.json_out) or ".", exist_ok=True)
    with open(args.json_out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print("\nExport stats")
    for k, v in stats.items():
        if k in ("classes", "found_by_class", "missing_by_class"):
            continue
        print(f"{k}: {v}")

    print("\nExamples collected per class")
    for c in class_tokens:
        print(f"{c}: {len(examples[c])}")

    if stats["missing_by_class"]:
        print("\nMissing classes (no example found):")
        for c in stats["missing_by_class"]:
            print(f"- {c}")

    print(f"\nSaved JSON: {args.json_out}")


if __name__ == "__main__":
    main()