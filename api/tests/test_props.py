"""
Task 1.6: Hypothesis property tests for the checker and solver.
"""
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from api.hold.checker import check_permutation
from api.hold.instance import parse_dzn

EASY = Path(__file__).parent.parent.parent / "bench" / "instances" / "easy"
MEDIUM = Path(__file__).parent.parent.parent / "bench" / "instances" / "medium"


@given(st.data())
@settings(max_examples=50, deadline=5000)
def test_valid_permutation_always_valid(data: st.DataObject) -> None:
    """Any valid permutation of film116 always parses as valid."""
    inst = parse_dzn(MEDIUM / "film116.dzn")
    perm = data.draw(st.permutations(list(range(inst.num_scenes))))
    result = check_permutation(inst, perm)
    assert result.valid
    assert result.holding >= 0
    assert result.total >= 0


@given(st.data())
@settings(max_examples=50, deadline=5000)
def test_holding_plus_fixed_equals_total(data: st.DataObject) -> None:
    """holding + fixed_cost == total for all valid permutations."""
    inst = parse_dzn(MEDIUM / "film116.dzn")
    perm = data.draw(st.permutations(list(range(inst.num_scenes))))
    result = check_permutation(inst, perm)
    assert result.valid
    assert result.holding + inst.fixed_cost == result.total


@given(st.data())
@settings(max_examples=30, deadline=5000)
def test_cost_never_below_zero(data: st.DataObject) -> None:
    """Holding cost is always non-negative."""
    inst = parse_dzn(EASY / "tiny.dzn")
    perm = data.draw(st.permutations(list(range(inst.num_scenes))))
    result = check_permutation(inst, perm)
    assert result.holding >= 0
