"""
Task 1.1: Verify benchmark instance identity: total - holding == fixed_cost.
No solver involved. Uses bench/optima.json and the dzn parser.
"""
import json
from pathlib import Path

import pytest

from api.hold.instance import parse_dzn

BENCH = Path(__file__).parent.parent.parent / "bench"
OPTIMA = json.loads((BENCH / "optima.json").read_text())
MEDIUM_DIR = BENCH / "instances" / "medium"

MEDIUM_INSTANCES = sorted(
    p.stem for p in MEDIUM_DIR.glob("*.dzn")
)


@pytest.mark.parametrize("name", MEDIUM_INSTANCES)
def test_identity(name: str) -> None:
    """total - holding == fixed_cost (sum_j c_j * sum_{i in ia[j]} d_i)."""
    assert name in OPTIMA, f"Instance {name!r} not in bench/optima.json"
    inst = parse_dzn(MEDIUM_DIR / f"{name}.dzn")
    recorded_total = OPTIMA[name]["total"]
    recorded_holding = OPTIMA[name]["holding"]
    expected_fixed = recorded_total - recorded_holding
    assert inst.fixed_cost == expected_fixed, (
        f"{name}: optima.json says total={recorded_total}, holding={recorded_holding}, "
        f"so fixed should be {expected_fixed}, but instance.fixed_cost={inst.fixed_cost}"
    )


def test_all_medium_instances_in_optima() -> None:
    """All 8 medium instances are present in bench/optima.json."""
    for name in MEDIUM_INSTANCES:
        assert name in OPTIMA, f"Instance {name!r} missing from bench/optima.json"
    assert len(MEDIUM_INSTANCES) == 8, f"Expected 8 medium instances, got {len(MEDIUM_INSTANCES)}"


def test_easy_instances_present() -> None:
    """3 easy instances are present."""
    easy_dir = BENCH / "instances" / "easy"
    easy = sorted(p.stem for p in easy_dir.glob("*.dzn"))
    assert len(easy) == 3, f"Expected 3 easy instances, got {len(easy)}: {easy}"
