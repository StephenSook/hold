"""
Task 1.5: Independent checker tests.
Verifies checker agrees with solver on 8/8 medium instances.
Verifies checker rejects invalid permutations.
"""
from pathlib import Path

import pytest

from api.hold.checker import check_permutation
from api.hold.instance import parse_dzn
from api.hold.model import solve_benchmark

MEDIUM = Path(__file__).parent.parent.parent / "bench" / "instances" / "medium"
MEDIUM_INSTANCES = sorted(p.stem for p in MEDIUM.glob("*.dzn"))


@pytest.mark.parametrize("name", MEDIUM_INSTANCES)
def test_checker_agrees_with_solver(name: str) -> None:
    inst = parse_dzn(MEDIUM / f"{name}.dzn")
    result = solve_benchmark(inst, time_limit_s=60.0)
    assert result.status == "OPTIMAL"
    perm = list(result.order)
    check = check_permutation(inst, perm)
    assert check.valid, f"{name}: checker says invalid: {check.error}"
    assert check.holding == result.holding, (
        f"{name}: checker holding={check.holding} != solver holding={result.holding}"
    )
    assert check.total == result.total, (
        f"{name}: checker total={check.total} != solver total={result.total}"
    )


def test_checker_rejects_duplicate_scene() -> None:
    inst = parse_dzn(MEDIUM / "film116.dzn")
    bad_perm = list(range(inst.num_scenes))
    bad_perm[5] = bad_perm[3]  # duplicate
    result = check_permutation(inst, bad_perm)
    assert not result.valid
    assert result.error is not None
    assert "duplicate" in result.error.lower()


def test_checker_rejects_wrong_length() -> None:
    inst = parse_dzn(MEDIUM / "film116.dzn")
    short_perm = list(range(inst.num_scenes - 1))
    result = check_permutation(inst, short_perm)
    assert not result.valid
    assert "length" in (result.error or "").lower()


def test_checker_rejects_out_of_range() -> None:
    inst = parse_dzn(MEDIUM / "film116.dzn")
    bad_perm = list(range(inst.num_scenes))
    bad_perm[0] = inst.num_scenes + 99  # out of range
    result = check_permutation(inst, bad_perm)
    assert not result.valid


def test_checker_identity_on_trivial_order() -> None:
    """Identity permutation (shoot in order 0..N-1) is always valid."""
    inst = parse_dzn(MEDIUM / "film116.dzn")
    perm = list(range(inst.num_scenes))
    result = check_permutation(inst, perm)
    assert result.valid
    assert result.total == result.holding + inst.fixed_cost
