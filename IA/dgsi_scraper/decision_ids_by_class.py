import os
import re
import json
import argparse
from typing import Optional, Iterable, Tuple, Dict, List

import psycopg

from dgsi_scraper.decision_map_llm import DECISION_CANON_MAP


DECISION_RE_LIST = [
    re.compile(r"(?im)^\s*Decis[aã]o\s*:\s*(.+?)\s*$"),
    re.compile(r"(?is)\bDecis[aã]o\s*:\s*(.{3,200}?)\n"),
    re.compile(r"(?im)^\s*Decis[aã]o\s*[-–—]\s*(.+?)\s*$"),
]

WHITESPACE_RE = re.compile(r"\s+")
TRAILING_PUNCT_RE = re.compile(r"[ \t\r\n]+$")


def normalize_decision(s: str) -> str:
    s = (s or "").strip()
    s = WHITESPACE_RE.sub(" ", s)
    s = re.sub(r"(?i)^\s*decis[aã]o\s*[:\-–—]\s*", "", s).strip()
    s = s.replace("\u00a0", " ").strip()
    s = TRAILING_PUNCT_RE.sub("", s)
    return s.upper()


def extract_decision_from_text(text_plain: str) -> Optional[str]:
    if not text_plain:
        return None
    for rx in DECISION_RE_LIST:
        m = rx.search(text_plain)
        if m:
            val = normalize_decision(m.group(1))
            if val:
                return val
    return None


def connect():
    dsn = os.getenv("DGSISCRAPER_DB_DSN")
    if not dsn:
        raise RuntimeError("Missing env var DGSISCRAPER_DB_DSN (ex: postgresql://dgsi:dgsi@localhost:5433/dgsi)")
    return psycopg.connect(dsn)


def iter_docs(conn, batch_size: int, sources: Optional[set[str]] = None) -> Iterable[Tuple[int, str, Optional[str], Optional[str]]]:
    """
    Yields (id, source, decision_extra, text_plain)
    decision_extra = extra->>'Decisão'
    """
    params = []
    if sources:
        where = "WHERE source = ANY(%s) AND id > %s"
        params.append(list(sources))
    else:
        where = "WHERE id > %s"

    last_id = 0
    while True:
        with conn.cursor() as cur:
            if sources:
                cur.execute(
                    f"""
                    SELECT id, source, extra->>'Decisão' AS decision_extra, text_plain
                    FROM dgsi_documents
                    {where}
                    ORDER BY id
                    LIMIT %s
                    """,
                    (params[0], last_id, batch_size),
                )
            else:
                cur.execute(
                    f"""
                    SELECT id, source, extra->>'Decisão' AS decision_extra, text_plain
                    FROM dgsi_documents
                    {where}
                    ORDER BY id
                    LIMIT %s
                    """,
                    (last_id, batch_size),
                )
            rows = cur.fetchall()

        if not rows:
            break

        for doc_id, source, decision_extra, text_plain in rows:
            yield doc_id, source, decision_extra, text_plain
            last_id = doc_id


def main():
    ap = argparse.ArgumentParser(description="Collect doc IDs per canonical decision class (14) using decision_rank logic.")
    ap.add_argument("--batch-size", type=int, default=500)
    ap.add_argument("--sources", type=str, default=None, help="Comma-separated sources (e.g. dgsi_stj,dgsi_sta). Default: all.")
    ap.add_argument("--per-class", type=int, default=50, help="How many doc IDs to collect per class.")
    ap.add_argument("--json-out", type=str, default="dgsi_scraper/output/decision_ids_by_class.json")
    ap.add_argument("--max-docs", type=int, default=None, help="Optional cap for quick tests.")
    args = ap.parse_args()

    sources = None
    if args.sources:
        sources = {s.strip() for s in args.sources.split(",") if s.strip()}

    # classes alvo (as 14)
    target_classes = sorted(set(DECISION_CANON_MAP.values()))

    out: Dict[str, List[Dict[str, object]]] = {c: [] for c in target_classes}
    stats = {
        "total_docs_seen": 0,
        "decision_from_extra": 0,
        "decision_from_text": 0,
        "missing_decision": 0,
        "unmapped_variant": 0,
        "matched_docs": 0,
        "per_class_target": args.per_class,
        "found_by_class": {c: 0 for c in target_classes},
    }

    def done_all() -> bool:
        return all(stats["found_by_class"][c] >= args.per_class for c in target_classes)

    conn = connect()
    try:
        for doc_id, source, decision_extra, text_plain in iter_docs(conn, args.batch_size, sources=sources):
            stats["total_docs_seen"] += 1
            if args.max_docs and stats["total_docs_seen"] >= args.max_docs:
                break
            if done_all():
                break

            decision_variant = None

            if decision_extra:
                decision_variant = normalize_decision(decision_extra)
                if decision_variant:
                    stats["decision_from_extra"] += 1

            if not decision_variant:
                decision_variant = extract_decision_from_text(text_plain)
                if decision_variant:
                    stats["decision_from_text"] += 1

            if not decision_variant:
                stats["missing_decision"] += 1
                continue

            canon = DECISION_CANON_MAP.get(decision_variant)
            if not canon:
                stats["unmapped_variant"] += 1
                continue

            if stats["found_by_class"][canon] >= args.per_class:
                continue

            out[canon].append({"id": doc_id, "source": source, "variant": decision_variant})
            stats["found_by_class"][canon] += 1
            stats["matched_docs"] += 1

    finally:
        conn.close()

    os.makedirs(os.path.dirname(args.json_out), exist_ok=True)
    with open(args.json_out, "w", encoding="utf-8") as f:
        json.dump({"stats": stats, "ids_by_class": out}, f, ensure_ascii=False, indent=2)

    print("\nExport stats")
    for k, v in stats.items():
        if k != "found_by_class":
            print(f"{k}: {v}")

    print("\nFound per class")
    for c in target_classes:
        print(f"{c}: {stats['found_by_class'][c]}")

    print(f"\nSaved JSON: {args.json_out}")


if __name__ == "__main__":
    main()