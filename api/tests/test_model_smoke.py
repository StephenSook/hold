"""
Task 1.3: Smoke test for the CP-SAT benchmark model.
film116: OPTIMAL, holding=373, total=804.
"""
from pathlib import Path

from api.hold.instance import parse_dzn
from api.hold.model import solve_benchmark

MEDIUM = Path(__file__).parent.parent.parent / "bench" / "instances" / "medium"


def test_film116_optimal() -> None:
    inst = parse_dzn(MEDIUM / "film116.dzn")
    result = solve_benchmark(inst, symmetry_break=False)
    assert result.status == "OPTIMAL", f"Expected OPTIMAL, got {result.status}"
    assert result.holding == 110, f"Expected holding=373, got {result.holding}"
    assert result.total == 541, f"Expected total=804, got {result.total}"
    print(f"\nfilm116: holding={result.holding} total={result.total} solve_ms={result.solve_ms:.0f}")


def test_film116_order_is_valid_permutation() -> None:
    inst = parse_dzn(MEDIUM / "film116.dzn")
    result = solve_benchmark(inst)
    assert result.status == "OPTIMAL"
    assert len(result.order) == inst.num_scenes
    assert set(result.order) == set(range(inst.num_scenes))
