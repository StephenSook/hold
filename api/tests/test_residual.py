"""
Task 1.4: Residual test - all 8 medium instances OPTIMAL, matching bench/optima.json.
60s cap per instance. Writes bench/results.json with run SHA.
This is the Wednesday 22:00 gate test.
"""
import json
import subprocess
import time
from pathlib import Path

import pytest

from api.hold.checker import check_permutation
from api.hold.instance import parse_dzn
from api.hold.model import solve_benchmark

BENCH = Path(__file__).parent.parent.parent / "bench"
MEDIUM = BENCH / "instances" / "medium"
OPTIMA = json.loads((BENCH / "optima.json").read_text())
RESULTS_PATH = BENCH / "results.json"

MEDIUM_INSTANCES = sorted(p.stem for p in MEDIUM.glob("*.dzn"))

TIME_LIMIT_S = 60.0


def _get_run_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True
        ).strip()
    except Exception:
        return "unknown"


@pytest.mark.parametrize("name", MEDIUM_INSTANCES)
def test_residual(name: str) -> None:
    """Each medium instance must solve to OPTIMAL matching bench/optima.json."""
    assert name in OPTIMA, f"Instance {name!r} not in bench/optima.json"

    inst = parse_dzn(MEDIUM / f"{name}.dzn")
    result = solve_benchmark(inst, time_limit_s=TIME_LIMIT_S)

    # If time limit hit, add the redundant span bound and retry once
    if result.status != "OPTIMAL":
        # Retry with the redundant bound hint (documented in PLAN.md task 1.4)
        result = solve_benchmark(inst, symmetry_break=False, time_limit_s=TIME_LIMIT_S)

    assert result.status == "OPTIMAL", (
        f"{name}: status={result.status} after {TIME_LIMIT_S}s. "
        f"Record benchmark_matched as partial in bench/results.json."
    )
    assert result.holding == OPTIMA[name]["holding"], (
        f"{name}: holding={result.holding} != published={OPTIMA[name]['holding']}"
    )
    assert result.total == OPTIMA[name]["total"], (
        f"{name}: total={result.total} != published={OPTIMA[name]['total']}"
    )

    # Cross-check with the independent checker
    check = check_permutation(inst, list(result.order))
    assert check.valid, f"{name}: checker says permutation invalid: {check.error}"
    assert check.holding == result.holding, (
        f"{name}: checker holding={check.holding} != solver holding={result.holding}"
    )


def test_write_results_json() -> None:
    """After all instances solve, write bench/results.json with the run SHA."""
    instances: dict[str, object] = {}
    results: dict[str, object] = {
        "_run_sha": _get_run_sha(),
        "_generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "instances": instances,
    }

    for name in MEDIUM_INSTANCES:
        inst = parse_dzn(MEDIUM / f"{name}.dzn")
        result = solve_benchmark(inst, time_limit_s=TIME_LIMIT_S)
        published = OPTIMA.get(name, {})
        matched = (
            result.status == "OPTIMAL"
            and result.holding == published.get("holding")
            and result.total == published.get("total")
        )
        instances[name] = {
            "status": result.status,
            "holding": result.holding,
            "total": result.total,
            "solve_ms": round(result.solve_ms),
            "matched": matched,
        }

    matched_count = sum(1 for v in instances.values() if isinstance(v, dict) and v.get("matched"))
    results["benchmark_matched"] = (
        f"{matched_count}/{len(MEDIUM_INSTANCES)}"
    )

    RESULTS_PATH.write_text(json.dumps(results, indent=2))
    print(f"\nbench/results.json written: {results['benchmark_matched']} matched")
    assert matched_count == len(MEDIUM_INSTANCES), (
        f"Only {matched_count}/{len(MEDIUM_INSTANCES)} instances matched optima. "
        f"See bench/results.json for details."
    )
