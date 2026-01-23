import os
import re
import json
import argparse
from collections import Counter
from typing import Optional, Dict, Any, Iterable, Tuple

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
        raise RuntimeError("Missing env var DGSISCRAPER_DB_DSN (ex: postgresql://dgsi:dgsi@localhost:5433/dgsi)")
    if psycopg is None:
        raise RuntimeError("psycopg not installed. Install with: pip install 'psycopg[binary]'")
    return psycopg.connect(dsn)


def iter_docs(conn, batch_size: int, sources: Optional[set[str]] = None) -> Iterable[Tuple[int, Optional[str], Optional[str], Optional[str]]]:
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
                (params[0], last_id, batch_size) if sources else (last_id, batch_size)
            )
            rows = cur.fetchall()

        if not rows:
            break

        for (doc_id, source, decision_extra, text_plain) in rows:
            yield doc_id, source, decision_extra, text_plain
            last_id = doc_id


def main():
    ap = argparse.ArgumentParser(description="Rank all 'Decisão' classes from dgsi_documents.")
    ap.add_argument("--batch-size", type=int, default=500, help="Rows fetched per batch.")
    ap.add_argument("--sources", type=str, default=None, help="Comma-separated sources to include (e.g. dgsi_stj,dgsi_sta). Default: all.")
    ap.add_argument("--max-docs", type=int, default=None, help="Optional cap for quick tests.")
    ap.add_argument("--csv-out", type=str, default="decision_ranking.csv", help="CSV output path.")
    ap.add_argument("--json-out", type=str, default="decision_ranking.json", help="JSON output path.")
    ap.add_argument("--show-top", type=int, default=50, help="Print top N to stdout.")
    args = ap.parse_args()

    sources = None
    if args.sources:
        sources = {s.strip() for s in args.sources.split(",") if s.strip()}

    conn = connect()
    counts = Counter()
    stats = {
        "total_docs_seen": 0,
        "decision_from_extra": 0,
        "decision_from_text": 0,
        "missing_decision": 0,
    }

    try:
        for (doc_id, source, decision_extra, text_plain) in iter_docs(conn, args.batch_size, sources=sources):
            stats["total_docs_seen"] += 1
            if args.max_docs and stats["total_docs_seen"] >= args.max_docs:
                break

            decision = None

            if decision_extra:
                decision = normalize_decision(decision_extra)
                if decision:
                    stats["decision_from_extra"] += 1

            if not decision:
                decision = extract_decision_from_text(text_plain)
                if decision:
                    stats["decision_from_text"] += 1

            if not decision:
                stats["missing_decision"] += 1
                continue

            counts[decision] += 1

    finally:
        conn.close()

    ranking = [{"decision": k, "count": v} for k, v in counts.most_common()]

    with open(args.csv_out, "w", encoding="utf-8") as f:
        f.write("decision,count\n")
        for row in ranking:
            decision = row["decision"].replace('"', '""')
            f.write(f"\"{decision}\",{row['count']}\n")

    with open(args.json_out, "w", encoding="utf-8") as f:
        json.dump({"stats": stats, "ranking": ranking}, f, ensure_ascii=False, indent=2)

    print("\nDecision extraction stats")
    for k, v in stats.items():
        print(f"{k}: {v}")
    print(f"\nUnique decisions: {len(counts)}")

    top_n = min(args.show_top, len(ranking))
    print(f"\nTop {top_n}")
    for i in range(top_n):
        print(f"{i+1:>2}. {ranking[i]['count']:>6}  |  {ranking[i]['decision']}")

    print(f"\nSaved CSV:  {args.csv_out}")
    print(f"Saved JSON: {args.json_out}")

if __name__ == "__main__":
    main()