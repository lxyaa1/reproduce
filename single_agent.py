"""One-sample Agent_all smoke test through MASFactory (no automatic batch run)."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from datetime import datetime, timezone
from urllib.parse import urlsplit

PROJECT = Path(__file__).resolve().parent
MASFACTORY_SOURCE = Path(os.getenv("MASFACTORY_SOURCE", str(PROJECT.parents[2] / "MASFactory-main")))
if (MASFACTORY_SOURCE / "masfactory").is_dir():
    sys.path.insert(0, str(MASFACTORY_SOURCE))

import masfactory
from masfactory import LegacyOpenAIModel, MessageFormatter, SingleAgent

MODEL = "gpt-4o-2024-08-06"
INSTRUCTION = "You are tasked with evaluating the truth of a given claim. You must base your judgment solely on available evidence and previous conversation information. Do not use any knowledge or information from your own model-based understanding or internal training data. Your judgment should rely entirely on the facts and evidence presented, and you should not infer beyond what is directly supported by those sources. "
OUTPUT_REQUIREMENTS = "Please strictly follow this format:\nResult: <Your answer from one of these three options: supporting, neutral, refuting>\nExplanation: <Brief explanation of why you made this choice>"


def make_prompt(sample: dict) -> str:
    # Agent_all's unpublished concatenation is reconstructed using newlines.
    # Only text enters the model; evidence labels and the gold answer stay outside.
    return str({
        "instruction": INSTRUCTION,
        "claim": sample["claim"],
        "evidence": "\n".join(item["sentence"] for item in sample["sentences_and_labels"]),
        "previous conversation information": [],
        "Output requirements": OUTPUT_REQUIREMENTS,
    })


class PaperFormatter(MessageFormatter):
    """Keep the author's Python-dict prompt and Result/Explanation response."""

    def __init__(self):
        super().__init__()
        self._is_input_formatter = self._is_output_formatter = True
        self._agent_introducer = OUTPUT_REQUIREMENTS

    def dump(self, message):
        if isinstance(message, str):
            return message
        # The prompt already contains the original output requirements.
        return message["MESSAGE TO YOU"]

    def format(self, message: str) -> dict:
        match = re.fullmatch(
            r"\s*Result:\s*(supporting|neutral|refuting)\s*\nExplanation:\s*(\S[\s\S]*)",
            message, re.IGNORECASE,
        )
        if not match:
            raise ValueError("Model output does not match Result/Explanation format")
        return {"judgement": match[1].lower(), "explanation": match[2].strip()}


def make_agent(model) -> SingleAgent:
    return SingleAgent(
        name="Agent_all", model=model, instructions="", prompt_template="{paper_prompt}",
        formatters=PaperFormatter(), hide_unused_fields=True, max_retries=1,
        model_settings={"max_tokens": 512},
    )


class RecordedModel(LegacyOpenAIModel):
    messages = None
    raw_response = None

    def invoke(self, messages, tools, settings=None, **kwargs):
        self.messages = messages
        # One generation attempt; also disable the SDK's own retries below.
        return super().invoke(messages, tools, settings, max_retries=1, **kwargs)

    def _parse_response(self, response):
        self.raw_response = response
        return super()._parse_response(response)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--claim-id", default="7467")
    parser.add_argument("--input", type=Path, default=PROJECT / "data/processed/filtered_test_certain_processed.json")
    parser.add_argument("--dry-run", action="store_true", help="Print the prompt without API access")
    args = parser.parse_args()
    data_bytes = args.input.read_bytes()
    sample = json.loads(data_bytes)[args.claim_id]
    prompt = make_prompt(sample)
    if args.dry_run:
        print(prompt)
        return 0

    key_name = next((name for name in ("OPEN_API_KEY", "OPENAI_API_KEY") if os.getenv(name)), None)
    if key_name is None:
        raise RuntimeError("Set OPEN_API_KEY or OPENAI_API_KEY before running")
    base_url = os.getenv("OPENAI_BASE_URL") or None
    report = {
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "claim_id": args.claim_id, "baseline": "Agent_all", "requested_model": MODEL,
        "endpoint_hostname": urlsplit(base_url or "https://api.openai.com/v1").hostname,
        "key_environment_variable": key_name,
        "masfactory_module": masfactory.__file__,
        "adapter": "LegacyOpenAIModel (Chat Completions)",
        "input_sha256": hashlib.sha256(data_bytes).hexdigest(),
        "evidence_count": len(sample["sentences_and_labels"]),
        "gold_label": sample["labels"],
        "settings": {"max_tokens": 512, "temperature": "not explicitly set"},
        "reproduction_notes": [
            "Agent_all concatenates all evidence texts with newlines; original standalone baseline code was not supplied.",
            "Original instruction, dict-string prompt, empty history and Result/Explanation requirements are preserved.",
            "Smoke test caps output at 512 tokens; original API helper has no explicit cap.",
            "Evaluation uses exact label equality rather than the author's substring comparison.",
            "A gateway's returned model name alone cannot independently authenticate its upstream model.",
        ],
    }
    model = None
    try:
        model = RecordedModel(MODEL, api_key=os.environ[key_name], base_url=base_url, timeout=35.0, max_retries=0)
        result = make_agent(model).invoke({"paper_prompt": prompt})
        report.update(status="success", **result, correct=result["judgement"] == sample["labels"])
    except Exception as exc:
        # Never serialize credentials, request headers or unrestricted exception bodies.
        cause = exc
        if hasattr(exc, "last_attempt"):
            cause = exc.last_attempt.exception() or exc
        report.update(status="error", error_type=type(cause).__name__, http_status=getattr(cause, "status_code", None))
        body = getattr(cause, "body", None)
        error = body.get("error", body) if isinstance(body, dict) else None
        if isinstance(error, dict):
            for field in ("code", "type", "message"):
                value = error.get(field)
                if isinstance(value, (str, int)):
                    value = str(value).replace(os.environ[key_name], "[REDACTED]")
                    report[f"provider_error_{field}"] = value[:800]
        elif isinstance(body, str):
            report["provider_error_message"] = body.replace(os.environ[key_name], "[REDACTED]")[:800]
    if model is not None:
        report["messages"] = model.messages
        raw = model.raw_response
        if raw is not None:
            report.update(
                returned_model=raw.model, raw_response=raw.choices[0].message.content,
                finish_reason=raw.choices[0].finish_reason,
                usage=raw.usage.model_dump() if raw.usage else None,
                system_fingerprint=getattr(raw, "system_fingerprint", None),
            )
    report["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
    output_dir = PROJECT / "results"
    output_dir.mkdir(exist_ok=True)
    output = output_dir / f"smoke_agent_all_{args.claim_id}_{datetime.now(timezone.utc):%Y%m%dT%H%M%S%fZ}.json"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k not in ("messages", "reproduction_notes")}, ensure_ascii=False, indent=2))
    print(f"Saved: {output}")
    return 0 if report["status"] == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
