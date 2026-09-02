"""
Task 1.3: CP-SAT benchmark model for the talent scheduling problem.

Shape locked by PLAN.md decisions D1-D3 and task 1.3 spec:
- pos[i]: position of scene i in the schedule (0..N-1)
- scene_at[p]: scene at position p (inverse of pos)
- AddInverse(pos, scene_at) + AddAllDifferent(pos)
- per-actor first_j, last_j
- onset[j][i]: BoolVar, 1 iff scene i is in actor j's call window
- objective: holding = sum_j sum_{i not in ia[j]} c[j]*d[i]*onset[j][i]
- symmetry_break: bool parameter (benchmark model only)

This module is the benchmark model only.
The extended model with legality rules lives in solve.py (tasks 2.7 and 2.8).
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import NamedTuple

from ortools.sat.python import cp_model

from api.hold.instance import Instance


class SolveResult(NamedTuple):
    status: str            # "OPTIMAL", "FEASIBLE", "INFEASIBLE", "UNKNOWN"
    holding: int           # variable holding cost (0 if not solved)
    total: int             # holding + fixed_cost
    solve_ms: float        # wall-clock milliseconds
    order: tuple[int, ...] # scene indices in optimal order (empty if not solved)


@dataclass
class BenchmarkModel:
    """
    CP-SAT model for the talent scheduling benchmark.
    Instantiated once per instance, solved once.
    """
    instance: Instance
    symmetry_break: bool = False

    def solve(self, time_limit_s: float = 60.0) -> SolveResult:
        inst = self.instance
        n = inst.num_scenes
        j_count = inst.num_actors

        model = cp_model.CpModel()

        # --- Variables ---
        pos = [model.new_int_var(0, n - 1, f"pos_{i}") for i in range(n)]
        scene_at = [model.new_int_var(0, n - 1, f"sat_{p}") for p in range(n)]
        model.add_inverse(pos, scene_at)
        model.add_all_different(pos)

        obj_terms: list = []

        for actor in range(j_count):
            in_scenes = [i for i in range(n) if inst.ia[actor][i] == 1]
            if not in_scenes:
                continue

            first_j = model.new_int_var(0, n - 1, f"first_{actor}")
            last_j = model.new_int_var(0, n - 1, f"last_{actor}")

            # Actor must appear in all their scenes
            for i in in_scenes:
                model.add(first_j <= pos[i])
                model.add(pos[i] <= last_j)

            # onset[actor][i] for scenes where actor does NOT appear
            for i in range(n):
                if inst.ia[actor][i] == 1:
                    continue  # actor is working, not a hold cost

                coeff = inst.c[actor] * inst.d[i]
                if coeff == 0:
                    continue

                onset = model.new_bool_var(f"on_{actor}_{i}")

                # onset = 1  iff  first_j <= pos[i] AND pos[i] <= last_j
                # Reify via two auxiliary bools
                ge_first = model.new_bool_var(f"ge_{actor}_{i}")
                le_last = model.new_bool_var(f"le_{actor}_{i}")

                model.add(pos[i] >= first_j).only_enforce_if(ge_first)
                model.add(pos[i] < first_j).only_enforce_if(ge_first.negated())
                model.add(pos[i] <= last_j).only_enforce_if(le_last)
                model.add(pos[i] > last_j).only_enforce_if(le_last.negated())

                model.add_bool_and([ge_first, le_last]).only_enforce_if(onset)
                model.add_bool_or([ge_first.negated(), le_last.negated()]).only_enforce_if(
                    onset.negated()
                )

                obj_terms.append(coeff * onset)

        # --- Objective ---
        if obj_terms:
            model.minimize(sum(obj_terms))
        else:
            model.minimize(model.new_constant(0))

        # --- Symmetry break (benchmark model only, not the extended model) ---
        if self.symmetry_break and n >= 2:
            # Break symmetry on the first two positions: pos[0] < pos[1]
            # Valid when scene 0 and scene 1 are interchangeable (same actor set).
            # Safe conservative form: only apply when actor membership is identical.
            ia_0 = inst.ia[0] if j_count > 0 else ()
            # Instead use a simpler lexicographic break on scene_at:
            # Fix scene_at[0] to the smallest-index scene that appears in the
            # same actor group as scene_at[1] - this is complex, so use a simple
            # position-fixing break: pos of the first scene <= pos of the last scene
            # This is always valid (trivially true if num_scenes==1).
            if n > 1:
                model.add(scene_at[0] < scene_at[n - 1])

        # --- Solve ---
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = time_limit_s
        solver.parameters.num_workers = 1  # single worker for benchmark model

        t0 = time.perf_counter()
        status_code = solver.solve(model)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        status_map = {
            cp_model.OPTIMAL: "OPTIMAL",
            cp_model.FEASIBLE: "FEASIBLE",
            cp_model.INFEASIBLE: "INFEASIBLE",
            cp_model.UNKNOWN: "UNKNOWN",
            cp_model.MODEL_INVALID: "MODEL_INVALID",
        }
        status_str = status_map.get(status_code, "UNKNOWN")

        if status_code in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            holding_val = int(round(solver.objective_value))
            total_val = holding_val + inst.fixed_cost
            order = tuple(int(solver.value(scene_at[p])) for p in range(n))
        else:
            holding_val = 0
            total_val = 0
            order = ()

        return SolveResult(
            status=status_str,
            holding=holding_val,
            total=total_val,
            solve_ms=elapsed_ms,
            order=order,
        )


def solve_benchmark(
    instance: Instance,
    symmetry_break: bool = False,
    time_limit_s: float = 60.0,
) -> SolveResult:
    """Convenience wrapper: solve a single benchmark instance."""
    return BenchmarkModel(instance=instance, symmetry_break=symmetry_break).solve(
        time_limit_s=time_limit_s
    )
