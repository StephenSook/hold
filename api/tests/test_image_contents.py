"""
What the deployed image must contain for its own published commands to work.

`run_residual` is exposed by the MCP server on the deployed origin, and the README and the judge
walkthrough both invite a reader to call it on a published benchmark instance. That tool reads two
things: bench/optima.json and bench/instances/medium/<name>.dzn.

.dockerignore excluded bench/instances to keep the image small, which was reasonable while the
benchmark was a local and CI concern and stopped being reasonable the moment the tool went public.
The failure mode was quiet in the worst way: optima.json shipped, so listing the known instances
worked and only solving one failed, and the MCP protocol reports a tool exception as "Error
executing tool run_residual" with no detail. It looked like a solver problem for some time.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
BENCH = ROOT / "bench"


def _dockerignore_rules() -> list[str]:
    text = (ROOT / ".dockerignore").read_text(encoding="utf-8")
    return [line.strip() for line in text.splitlines() if line.strip() and not line.lstrip().startswith("#")]


def _instances() -> list[str]:
    optima = json.loads((BENCH / "optima.json").read_text(encoding="utf-8"))
    return sorted(k for k in optima if not k.startswith("_"))


def test_the_benchmark_instances_are_not_excluded_from_the_image() -> None:
    """A rule here removes the files the deployed run_residual reads."""
    offending = [r for r in _dockerignore_rules() if "bench" in r]
    assert offending == [], (
        f".dockerignore excludes benchmark material {offending}, so run_residual raises on the "
        "deployed service while working locally"
    )


@pytest.mark.parametrize("name", _instances())
def test_every_published_optimum_has_a_readable_instance(name: str) -> None:
    """optima.json is the list the tool offers a caller, so every name on it must be solvable."""
    path = BENCH / "instances" / "medium" / f"{name}.dzn"
    assert path.is_file(), f"{name} is offered by run_residual but {path.relative_to(ROOT)} is missing"
    assert path.stat().st_size > 0
