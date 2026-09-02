"""
Task 1.6: Symmetry-break tests.
Solve tiny with symmetry_break=True and False; both must give OPTIMAL with equal cost.
"""
from pathlib import Path

from api.hold.instance import parse_dzn
from api.hold.model import solve_benchmark

EASY = Path(__file__).parent.parent.parent / "bench" / "instances" / "easy"


def test_symmetry_break_gives_same_cost_as_no_break() -> None:
    inst = parse_dzn(EASY / "tiny.dzn")
    r_off = solve_benchmark(inst, symmetry_break=False, time_limit_s=10.0)
    r_on = solve_benchmark(inst, symmetry_break=True, time_limit_s=10.0)
    assert r_off.status == "OPTIMAL"
    assert r_on.status == "OPTIMAL"
    assert r_off.holding == r_on.holding, (
        f"symmetry_break changed cost: off={r_off.holding} on={r_on.holding}"
    )


def test_symmetry_break_small() -> None:
    inst = parse_dzn(EASY / "small.dzn")
    r_off = solve_benchmark(inst, symmetry_break=False, time_limit_s=30.0)
    r_on = solve_benchmark(inst, symmetry_break=True, time_limit_s=30.0)
    assert r_off.status == "OPTIMAL"
    assert r_on.status == "OPTIMAL"
    assert r_off.holding == r_on.holding
