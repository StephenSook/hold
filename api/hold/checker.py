"""
Task 1.5: Independent checker for talent scheduling solutions.

Plain Python, no OR-Tools. Recomputes holding and total from a permutation
and validates permutation correctness. This is the source of truth for
violations per PLAN.md Decision D13.

Used in:
- test_checker.py: agreement with solver on 8/8 medium instances
- test_residual.py: cross-check on every solved instance
- Phase 2+: legality violation enumeration (extended in checker.py at task 2.9)
"""
from __future__ import annotations

from dataclasses import dataclass

from api.hold.instance import Instance


@dataclass(frozen=True)
class CheckResult:
    valid: bool
    holding: int
    total: int
    error: str | None = None


def check_permutation(instance: Instance, perm: list[int]) -> CheckResult:
    """
    Recompute holding and total from a permutation of scene indices.

    perm[p] = scene index at position p (same convention as scene_at in the model).

    Returns CheckResult with valid=False and error set if the permutation is
    structurally invalid (wrong length, duplicates, out-of-range indices).
    """
    n = instance.num_scenes

    # --- Validate permutation structure ---
    if len(perm) != n:
        return CheckResult(
            valid=False,
            holding=0,
            total=0,
            error=f"permutation length {len(perm)} != num_scenes {n}",
        )

    if len(set(perm)) != n:
        duplicates = [i for i in range(n) if perm.count(i) > 1]
        return CheckResult(
            valid=False,
            holding=0,
            total=0,
            error=f"permutation contains duplicates: {duplicates[:5]}",
        )

    if set(perm) != set(range(n)):
        out_of_range = [x for x in perm if x < 0 or x >= n]
        return CheckResult(
            valid=False,
            holding=0,
            total=0,
            error=f"permutation has out-of-range indices: {out_of_range[:5]}",
        )

    # --- Build position map: pos[scene] = position in schedule ---
    pos = [0] * n
    for position, scene in enumerate(perm):
        pos[scene] = position

    # --- Compute holding cost ---
    holding = 0
    for actor in range(instance.num_actors):
        in_scenes = [i for i in range(n) if instance.ia[actor][i] == 1]
        if not in_scenes:
            continue

        first_pos = min(pos[i] for i in in_scenes)
        last_pos = max(pos[i] for i in in_scenes)

        # Hold cost: scenes NOT featuring this actor that fall within their window
        for i in range(n):
            if instance.ia[actor][i] == 1:
                continue  # actor is working, no hold cost
            if first_pos <= pos[i] <= last_pos:
                holding += instance.c[actor] * instance.d[i]

    total = holding + instance.fixed_cost

    return CheckResult(valid=True, holding=holding, total=total)
