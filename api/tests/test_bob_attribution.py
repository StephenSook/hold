"""
Task 0.14: Attribution tests.
Verifies docs/bob-evidence/ATTRIBUTION.md exists and contains a valid trailer count.
"""
import re
from pathlib import Path

ATTRIBUTION_PATH = Path(__file__).parent.parent.parent / "docs" / "bob-evidence" / "ATTRIBUTION.md"
EVIDENCE_PATH = Path(__file__).parent.parent.parent / "docs" / "bob-evidence" / "bob-usage-evidence.json"


def test_attribution_file_exists() -> None:
    assert ATTRIBUTION_PATH.exists(), f"ATTRIBUTION.md not found at {ATTRIBUTION_PATH}"


def test_attribution_has_bob_trailer_count() -> None:
    text = ATTRIBUTION_PATH.read_text()
    match = re.search(r"Bob-authored commits.*?\|\s*(\d+)", text)
    assert match, "ATTRIBUTION.md must contain a 'Bob-authored commits' row with an integer count"
    count = int(match.group(1))
    assert count >= 0, f"Bob-authored commit count must be non-negative, got {count}"


def test_attribution_lists_five_modes() -> None:
    text = ATTRIBUTION_PATH.read_text()
    for mode in ["solver-engine", "agent-runtime", "mobile-shell", "frontend", "evidence-writer"]:
        assert mode in text, f"ATTRIBUTION.md must mention mode '{mode}'"


def test_evidence_json_exists() -> None:
    assert EVIDENCE_PATH.exists(), f"bob-usage-evidence.json not found at {EVIDENCE_PATH}"


def test_evidence_json_has_required_fields() -> None:
    import json
    data = json.loads(EVIDENCE_PATH.read_text())
    for field in ["generated_at", "workspace", "task_count", "total_cost_usd"]:
        assert field in data, f"bob-usage-evidence.json missing field '{field}'"
    assert data["task_count"] >= 0
    assert data["total_cost_usd"] >= 0
