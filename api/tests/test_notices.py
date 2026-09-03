"""docs/THIRD_PARTY_NOTICES.md is generated from the installed metadata; a dependency installed
without regenerating it is a stale notice (round seven, finding 4)."""
from __future__ import annotations

import re
from importlib.metadata import distributions
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _norm(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def test_every_installed_distribution_has_a_notices_row() -> None:
    installed = sorted({_norm(d.metadata["Name"]) for d in distributions() if d.metadata["Name"]} - {"hold"})
    assert len(installed) > 50
    notices = (ROOT / "docs" / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")
    rows = {_norm(m.group(1).strip()) for m in re.finditer(r"^\| ([^|]+) \|", notices, re.M)}
    missing = [n for n in installed if n not in rows]
    assert missing == [], missing
