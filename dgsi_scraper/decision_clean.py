import csv
import json
import re
import argparse
from typing import Dict, List

DATE_RE = re.compile(r"^\d{2}/\d{2}/\d{4}$")
ONLY_SYMBOLS_RE = re.compile(r"^[\W_]+$")

def uppercase_ratio(s: str) -> float:
    letters = [c for c in s if c.isalpha()]
    if not letters:
        return 0.0
    upper = sum(1 for c in letters if c.isupper())
    return upper / len(letters)


def is_valid_decision(decision: str, max_len: int, min_upper_ratio: float) -> bool:
    s = decision.strip()

    if len(s) < 3:
        return False

    if len(s) > max_len:
        return False

    if DATE_RE.match(s):
        return False

    if ONLY_SYMBOLS_RE.match(s):
        return False

    if uppercase_ratio(s) < min_upper_ratio:
        return False

    return True


def normalize_decision(s: str) -> str:
    s = re.sub(r"\s+", " ", s.strip())
    s = re.sub(r"[;,.]+$", "", s)
    return s


def main():
    ap = argparse.ArgumentParser(description="Clean and filter decision classes.")
    ap.add_argument("--input", default="decision_ranking.csv", help="Input CSV from decision_rank.py")
    ap.add_argument("--csv-out", default="decision_classes_clean.csv")
    ap.add_argument("--json-out", default="decision_classes_clean.json")
    ap.add_argument("--max-len", type=int, default=120)
    ap.add_argument("--min-upper-ratio", type=float, default=0.8)
    ap.add_argument("--seeds-out", default="decision_seeds.csv", help="Output CSV with 1-token decisions (seed classes)")
    ap.add_argument("--variants-out", default="decision_variants.csv", help="Output CSV with 2+ token decisions (variant classes)")
    args = ap.parse_args()

    kept: List[Dict] = []
    removed = {
        "too_short": 0,
        "too_long": 0,
        "date": 0,
        "symbols": 0,
        "not_caps": 0,
    }

    with open(args.input, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            decision = row["decision"]
            count = int(row["count"])

            s = decision.strip()

            if len(s) < 3:
                removed["too_short"] += count
                continue

            if len(s) > args.max_len:
                removed["too_long"] += count
                continue

            if DATE_RE.match(s):
                removed["date"] += count
                continue

            if ONLY_SYMBOLS_RE.match(s):
                removed["symbols"] += count
                continue

            if uppercase_ratio(s) < args.min_upper_ratio:
                removed["not_caps"] += count
                continue

            s = normalize_decision(s)
            kept.append({"decision": s, "count": count})

    kept.sort(key=lambda x: x["count"], reverse=True)

    # Write CSV
    with open(args.csv_out, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["decision", "count"])
        for r in kept:
            writer.writerow([r["decision"], r["count"]])

    # Split kept decisions into 1-token seeds vs 2+ token variants
    seeds = []
    variants = []
    for r in kept:
        token_count = len(r["decision"].split())
        if token_count == 1:
            seeds.append(r)
        else:
            variants.append(r)

    # Write seeds CSV
    with open(args.seeds_out, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["decision", "count"])
        for r in seeds:
            writer.writerow([r["decision"], r["count"]])

    # Write variants CSV
    with open(args.variants_out, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["decision", "count"])
        for r in variants:
            writer.writerow([r["decision"], r["count"]])

    # Write JSON (with stats)
    out = {
        "params": {
            "max_len": args.max_len,
            "min_upper_ratio": args.min_upper_ratio,
        },
        "kept_classes": len(kept),
        "seed_classes": len(seeds),
        "variant_classes": len(variants),
        "removed_counts": removed,
        "classes": kept,
    }

    with open(args.json_out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print("Decision cleaning summary\n")
    print(f"Kept classes: {len(kept)}")
    print(f"Seed classes (1 token): {len(seeds)}")
    print(f"Variant classes (2+ tokens): {len(variants)}")
    print("Removed (weighted by frequency):")
    for k, v in removed.items():
        print(f"  {k}: {v}")

    print(f"\nSaved CSV:  {args.csv_out}")
    print(f"Saved JSON: {args.json_out}")
    print(f"Saved SEEDS CSV:  {args.seeds_out}")
    print(f"Saved VARIANTS CSV: {args.variants_out}")


if __name__ == "__main__":
    main()