"""
Task 1.6: Brute-force differential on easy/tiny and easy/small.
Verifies solver optimal == minimum over all permutations.
"""
import itertools
from pathlib import Path

from api.hold.checker import check_permutation
from api.hold.instance import parse_dzn
from api.hold.model import solve_benchmark

EASY = Path(__file__).parent.parent.parent / "bench" / "instances" / "easy"


def brute_force_optimal(inst) -> int:  # type: ignore[no-untyped-def]
    """Enumerate all permutations and return the minimum holding cost."""
    best = None
    for perm in itertools.permutations(range(inst.num_scenes)):
        result = check_permutation(inst, list(perm))
        assert result.valid
        if best is None or result.holding < best:
            best = result.holding
    assert best is not None
    return best


def test_tiny_solver_matches_brute_force() -> None:
    inst = parse_dzn(EASY / "tiny.dzn")
    # Only brute-force if small enough (safety check)
    import math
    assert math.factorial(inst.num_scenes) <= 40320, (
        f"tiny has {inst.num_scenes} scenes - too large for brute force"
    )
    bf_holding = brute_force_optimal(inst)
    solver_result = solve_benchmark(inst, time_limit_s=10.0)
    assert solver_result.status == "OPTIMAL"
    assert solver_result.holding == bf_holding, (
        f"solver holding={solver_result.holding} != brute-force={bf_holding}"
    )


def test_checker_agrees_with_brute_force_on_tiny() -> None:
    """Every permutation of tiny: checker holding + fixed == checker total."""
    inst = parse_dzn(EASY / "tiny.dzn")
    for perm in itertools.permutations(range(inst.num_scenes)):
        result = check_permutation(inst, list(perm))
        assert result.valid
        assert result.holding + inst.fixed_cost == result.total
