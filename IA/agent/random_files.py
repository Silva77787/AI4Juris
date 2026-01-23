
import random
import json
import argparse
from pathlib import Path
from typing import Dict, List, Any


def load_ids_by_class(json_path: Path) -> Dict[str, List[Dict[str, Any]]]:
	with json_path.open("r", encoding="utf-8") as f:
		data = json.load(f)
	# expect top-level key `ids_by_class`
	ids_by_class = data.get("ids_by_class")
	if ids_by_class is None:
		raise ValueError(f"JSON file {json_path} does not contain 'ids_by_class' key")
	return ids_by_class


def extract_random_ids(ids_by_class: Dict[str, List[Dict[str, Any]]], total: int) -> List[Dict[str, Any]]:
	# Validate classes have at least one id
	empty_classes = [c for c, items in ids_by_class.items() if not items]
	if empty_classes:
		raise ValueError(f"The following classes have no ids available: {empty_classes}")

	# First, pick one id from each class
	chosen = []
	chosen_ids = set()
	for cls, items in ids_by_class.items():
		item = random.choice(items)
		chosen.append({"class": cls, "id": item.get("id"), "source": item.get("source"), "variant": item.get("variant")})
		chosen_ids.add(item.get("id"))

	remaining = max(0, total - len(chosen))

	# Build flat pool of candidates that are not already chosen
	pool = []
	for cls, items in ids_by_class.items():
		for item in items:
			if item.get("id") not in chosen_ids:
				pool.append({"class": cls, "id": item.get("id"), "source": item.get("source"), "variant": item.get("variant")})

	if remaining > len(pool):
		raise ValueError(f"Requested total={total} but only {len(chosen)+len(pool)} unique ids available")

	if remaining > 0:
		extra = random.sample(pool, remaining)
		chosen.extend(extra)

	# Shuffle final list to avoid class-ordered output
	random.shuffle(chosen)
	return chosen


def main():
	parser = argparse.ArgumentParser(description="Extract random ids from decision_ids_by_class JSON ensuring at least one id per class")
	parser.add_argument("--json", "-j", default=None, help="Path to decision_ids_by_class JSON (defaults to agent/decision_ids_by_class_ALLSOURCES.json)")
	parser.add_argument("--n", "-n", type=int, default=100, help="Total number of ids to extract (must be >= number of classes)")
	parser.add_argument("--out", "-o", default=None, help="Optional output file to write selected ids as JSON")
	args = parser.parse_args()

	base = Path(__file__).parent
	json_path = Path(args.json) if args.json else base / "decision_ids_by_class_ALLSOURCES.json"
	if not json_path.exists():
		raise FileNotFoundError(f"JSON file not found: {json_path}")

	ids_by_class = load_ids_by_class(json_path)

	# Quick validation: total must be at least number of classes
	num_classes = len([c for c in ids_by_class.keys()])
	if args.n < num_classes:
		raise ValueError(f"--n ({args.n}) must be at least the number of classes ({num_classes}) to guarantee one per class")

	selected = extract_random_ids(ids_by_class, args.n)

	# Print a small summary
	counts = {}
	for item in selected:
		counts[item["class"]] = counts.get(item["class"], 0) + 1

	print(f"Selected {len(selected)} ids (requested {args.n})")
	for cls, cnt in sorted(counts.items()):
		print(f" - {cls}: {cnt}")

	if args.out:
		out_path = Path(args.out)
		with out_path.open("w", encoding="utf-8") as f:
			json.dump(selected, f, ensure_ascii=False, indent=2)
		print(f"Wrote selected ids to {out_path}")
	else:
		# default: print JSON to stdout
		print(json.dumps(selected, ensure_ascii=False, indent=2))


if __name__ == "__main__":
	main()

