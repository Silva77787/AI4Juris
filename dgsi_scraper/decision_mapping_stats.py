import json
import argparse
from collections import Counter
import csv
from typing import Any, Dict, List


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="Aggregated decision mapping JSON")
    ap.add_argument("--stats-out", default="decision_mapping_stats.json")
    ap.add_argument("--unsure-out", default="decision_mapping_unsure.json")
    ap.add_argument(
        "--canon-csv-out",
        default=None,
        help="Optional CSV output for non-UNSURE variants (columns: variant,mapped_to,count)",
    )
    ap.add_argument(
        "--canon-map-out",
        default=None,
        help="Optional .txt/.py output containing a DECISION_CANON_MAP snippet for non-UNSURE variants",
    )
    args = ap.parse_args()

    with open(args.input, encoding="utf-8") as f:
        data = json.load(f)

    total_variants = len(data)
    total_weight = sum(d.get("count", 1) for d in data)

    by_label = Counter()
    by_label_weighted = Counter()

    unsure = []
    non_unsure_rows: List[Dict[str, Any]] = []
    canon_map: Dict[str, str] = {}

    for d in data:
        label = d.get("mapped_to", "UNSURE")
        count = d.get("count", 1)

        by_label[label] += 1
        by_label_weighted[label] += count

        if label == "UNSURE":
            unsure.append(d)
        else:
            # Best-effort: accommodate slightly different key names in aggregated JSON
            variant = (
                d.get("decision")
                or d.get("variant")
                or d.get("text")
                or d.get("raw")
                or ""
            )
            variant = str(variant).strip()
            if variant:
                non_unsure_rows.append({"variant": variant, "mapped_to": label, "count": count})
                canon_map[variant] = label

    stats = {
        "total_variants": total_variants,
        "total_weighted_occurrences": total_weight,
        "by_label": dict(by_label),
        "by_label_weighted": dict(by_label_weighted),
        "unsure_variants": len(unsure),
        "unsure_weighted_occurrences": sum(d.get("count", 1) for d in unsure),
        "unsure_ratio_variants": round(len(unsure) / total_variants, 4),
        "unsure_ratio_weighted": round(
            sum(d.get("count", 1) for d in unsure) / total_weight, 4
        ),
    }

    # write stats
    with open(args.stats_out, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    # write unsure only
    with open(args.unsure_out, "w", encoding="utf-8") as f:
        json.dump(unsure, f, ensure_ascii=False, indent=2)

    # optional: write non-UNSURE variants CSV
    if args.canon_csv_out:
        with open(args.canon_csv_out, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["variant", "mapped_to", "count"])
            w.writeheader()
            # stable, useful ordering: by mapped_to then by descending count then variant
            for row in sorted(
                non_unsure_rows,
                key=lambda r: (r["mapped_to"], -int(r.get("count", 1)), r["variant"]),
            ):
                w.writerow(row)

    # optional: write a DECISION_CANON_MAP snippet (ready to paste)
    if args.canon_map_out:
        # group variants by canonical label
        by_canon: Dict[str, List[Dict[str, Any]]] = {}
        for row in non_unsure_rows:
            by_canon.setdefault(row["mapped_to"], []).append(row)

        lines: List[str] = []
        lines.append("DECISION_CANON_MAP = {")
        for canon in sorted(by_canon.keys()):
            lines.append(f"    # {canon}")
            rows = sorted(by_canon[canon], key=lambda r: (-int(r.get("count", 1)), r["variant"]))
            for r in rows:
                v = r["variant"].replace('\\', '\\\\').replace('"', '\\"')
                lines.append(f"    \"{v}\": \"{canon}\",  # {r.get('count', 1)}")
            lines.append("")
        lines.append("}")
        with open(args.canon_map_out, "w", encoding="utf-8") as f:
            f.write("\n".join(lines).rstrip() + "\n")

    print("Decision Mapping Statistics")
    print(f"Total variants: {total_variants}")
    print(f"Total weighted occurrences: {total_weight}")
    print(f"UNSURE variants: {stats['unsure_variants']} "
          f"({stats['unsure_ratio_variants']*100:.2f}%)")
    print(f"UNSURE weighted occurrences: {stats['unsure_weighted_occurrences']} "
          f"({stats['unsure_ratio_weighted']*100:.2f}%)")
    print()
    print(f"Saved stats to:  {args.stats_out}")
    print(f"Saved UNSURE to: {args.unsure_out}")
    if args.canon_csv_out:
        print(f"Saved non-UNSURE CSV to: {args.canon_csv_out}")
    if args.canon_map_out:
        print(f"Saved DECISION_CANON_MAP snippet to: {args.canon_map_out}")


if __name__ == "__main__":
    main()