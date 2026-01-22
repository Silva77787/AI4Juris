import argparse
import json
import re
from pathlib import Path

PARTIAL_MARKERS = [
    "PARCIAL",
    "EM PARTE",
    "PARTE",
    "PARCIALMENTE",
    "PARCIALMETE", 
]

def norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().upper())


def has_any(s: str, terms: list[str]) -> bool:
    return any(t in s for t in terms)


def is_partial_row(row: dict) -> bool:
    """Return True if the row should be considered 'partial/mixed'.

    We use TWO signals:
      1) the original reason field (if present) contains 'parcial'
      2) the variant text itself contains any partial markers

    This makes the splitter robust even when 'reason' is missing.
    """
    reason = (row.get("reason") or "")
    if "parcial" in reason.lower():
        return True

    v = norm(row.get("variant") or "")
    return has_any(v, PARTIAL_MARKERS)


def main():
    ap = argparse.ArgumentParser(description="Split UNSURE variants into partial vs non-partial buckets")
    ap.add_argument("--unsure-in", required=True, help="Input JSON (list of objects) with UNSURE variants")
    ap.add_argument("--partial-out", required=True, help="Output JSON with only partial/mixed rows")
    ap.add_argument("--non-partial-out", required=True, help="Output JSON with the remaining rows")
    args = ap.parse_args()

    unsure_path = Path(args.unsure_in)
    unsure = json.loads(unsure_path.read_text(encoding="utf-8"))

    partial_rows: list[dict] = []
    non_partial_rows: list[dict] = []

    for row in unsure:
        if is_partial_row(row):
            partial_rows.append(row)
        else:
            non_partial_rows.append(row)

    Path(args.partial_out).write_text(
        json.dumps(partial_rows, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    Path(args.non_partial_out).write_text(
        json.dumps(non_partial_rows, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"unsure_in: {len(unsure)}")
    print(f"partial: {len(partial_rows)}")
    print(f"non_partial: {len(non_partial_rows)}")
    print(f"wrote partial: {args.partial_out}")
    print(f"wrote non_partial: {args.non_partial_out}")


if __name__ == "__main__":
    main()