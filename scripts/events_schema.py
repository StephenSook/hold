#!/usr/bin/env python
"""Write rules/events.schema.json from the Pydantic event models (task 4.1). Hand edits fail CI."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api.hold.schemas import SetEvent, VerdictEvent  # noqa: E402

OUT = ROOT / "rules" / "events.schema.json"


def render() -> str:
    schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "HOLD Kafka payloads",
        "description": "Messages on hold.set-events (SetEvent, plus job_id when the API mirrors its own event) and hold.verdicts (VerdictEvent). Generated from api/hold/schemas.py by scripts/events_schema.py; hand edits fail CI.",
        "definitions": {"SetEvent": SetEvent.model_json_schema(), "VerdictEvent": VerdictEvent.model_json_schema()},
    }
    return json.dumps(schema, indent=2) + "\n"


if __name__ == "__main__":
    OUT.write_text(render(), encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")
