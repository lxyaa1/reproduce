"""Rebuild SES inputs with the paper authors' unmodified preprocessing functions.

No model calls or third-party Python packages are needed for data preparation.
"""

import argparse
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path


PROJECT = Path(__file__).resolve().parent
WORKSPACE = PROJECT.parent
AUTHOR_ROOT = WORKSPACE / "collaboration_MAS-main"


def fingerprint(path):
    return {"path": str(path.resolve()), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def save_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=4), encoding="utf-8")


def prepare(input_path, output_dir):
    input_path = input_path.resolve()
    output_dir = output_dir.resolve()
    source = AUTHOR_ROOT / "fact_code/filter_claim_data.py"
    examples_path = AUTHOR_ROOT / "fact_data/data_example.json"
    # Keep generated files separate from original data and author code.
    for protected in (input_path.parent, AUTHOR_ROOT.resolve()):
        if output_dir == protected or protected in output_dir.parents:
            raise ValueError("Output directory must be outside original data and author code.")

    records = []
    with input_path.open(encoding="utf-8") as stream:
        for line_no, line in enumerate(stream, 1):
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON at {input_path}:{line_no}; no rows silently skipped") from exc

    spec = importlib.util.spec_from_file_location("paper_author_filter", source)
    author = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(author)
    first_stage = author.filter_claim_data(records)

    # Use the same original function on each row to trace which passage survived.
    # This does not modify the filtering rule or repair duplicate-key overwrites.
    provenance = {}
    eligible_rows = 0
    overwritten_rows = []
    for line_no, record in enumerate(records, 1):
        if not author.filter_claim_data([record]):
            continue
        eligible_rows += 1
        key = str(record["claim_id"])
        if key in provenance:
            overwritten_rows.append({
                "claim_id": key,
                "previous_line": provenance[key]["source_line"],
                "replacement_line": line_no,
            })
        provenance[key] = {"source_line": line_no, "wiki_passage": record.get("wiki_passage")}

    output_dir.mkdir(parents=True, exist_ok=True)
    stage1_path = output_dir / "filtered_test_certain.json"
    final_path = output_dir / "filtered_test_certain_processed.json"
    author.save_json(first_stage, str(stage1_path))
    author.process_filtered_data(str(stage1_path), str(final_path))
    final = json.loads(final_path.read_text(encoding="utf-8"))
    examples = json.loads(examples_path.read_text(encoding="utf-8"))
    checks = {key: final.get(key) == value for key, value in examples.items()}

    combinations = Counter()
    evidence_counts = Counter()
    degenerate_ids = []
    for key, value in final.items():
        evidence = value["sentences_and_labels"]
        labels = sorted({entry["label"] for entry in evidence})
        combinations[" + ".join(labels)] += 1
        evidence_counts[len(evidence)] += 1
        if len(labels) < 2:
            degenerate_ids.append(key)
        if not 1 <= len(evidence) <= 6 or any(not entry["sentence"] for entry in evidence):
            raise ValueError(f"Unexpected final evidence structure for claim {key}")

    # Compare object content AND ordering with the earlier independent audit output.
    prior_path = WORKSPACE / "dataset_audit/filtered_test_certain_processed.json"
    prior_comparison = None
    if prior_path.exists():
        prior = json.loads(prior_path.read_text(encoding="utf-8"))
        prior_comparison = {"source": fingerprint(prior_path), "content_and_order_equal": list(final.items()) == list(prior.items())}

    report = {
        "mode": "author_code_unchanged",
        "scope": "Reconstructed from public code; identity with the paper's full evaluation cohort is unverified.",
        "input": fingerprint(input_path),
        "author_preprocessing": fingerprint(source),
        "author_examples": fingerprint(examples_path),
        "raw_passage_records": len(records),
        "raw_unique_claim_ids": len({str(x["claim_id"]) for x in records}),
        "eligible_passage_records_before_claim_id_overwrites": eligible_rows,
        "overwritten_eligible_records": len(overwritten_rows),
        "stage1_samples": len(first_stage),
        "final_samples": len(final),
        "target_label_counts": dict(Counter(x["labels"] for x in final.values())),
        "evidence_label_combinations": dict(combinations),
        "evidence_count_distribution": dict(sorted(evidence_counts.items())),
        "single_label_sample_ids_retained": degenerate_ids,
        "example_exact_matches": checks,
        "all_examples_match": all(checks.values()),
        "prior_audit_comparison": prior_comparison,
        "outputs": {"stage1": fingerprint(stage1_path), "final": fingerprint(final_path)},
    }
    save_json(output_dir / "source_records.json", {
        "input": fingerprint(input_path),
        "retained_records": {key: provenance[key] for key in final},
        "overwrite_events": overwritten_rows,
    })
    save_json(output_dir / "preprocessing_report.json", report)
    print(json.dumps({key: report[key] for key in (
        "raw_passage_records", "eligible_passage_records_before_claim_id_overwrites",
        "overwritten_eligible_records", "final_samples", "target_label_counts",
        "evidence_label_combinations", "single_label_sample_ids_retained", "all_examples_match",
    )}, ensure_ascii=False, indent=2))
    print(f"Prepared data: {final_path}")
    if not all(checks.values()):
        raise ValueError("Author examples did not all match; inspect preprocessing_report.json")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, help="Path to the original test.certain.jsonl")
    parser.add_argument("--output-dir", type=Path, default=PROJECT / "data/processed")
    args = parser.parse_args()
    if args.input is None:
        candidates = list((WORKSPACE.parent / "original_data/ambifc").rglob("test.certain.jsonl"))
        if len(candidates) != 1:
            parser.error("Expected exactly one test.certain.jsonl; specify --input explicitly.")
        args.input = candidates[0]
    prepare(args.input, args.output_dir)


if __name__ == "__main__":
    main()
