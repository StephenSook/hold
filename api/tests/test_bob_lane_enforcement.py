"""
Task 0.14: Lane-enforcement tests.
Parses mode regexes from .bob/custom_modes.yaml using stdlib re only (no PyYAML).
Tests the full allow/refuse matrix from PLAN.md Lanes section.
"""
import re
from pathlib import Path


def _load_regexes() -> dict[str, str]:
    """Parse fileRegex values from custom_modes.yaml without PyYAML.

    YAML double-quoted strings use \\\\ to represent a single backslash.
    After capturing the raw text between quotes, we collapse \\\\\\\\ -> \\\\
    so the regex patterns work correctly in Python.
    """
    yaml_text = (Path(__file__).parent.parent.parent / ".bob" / "custom_modes.yaml").read_text()
    result: dict[str, str] = {}
    current_slug: str | None = None
    for line in yaml_text.splitlines():
        slug_match = re.match(r"\s+- slug:\s+(\S+)", line)
        if slug_match:
            current_slug = slug_match.group(1)
        regex_match = re.match(r'\s+fileRegex:\s+"(.+)"', line)
        if regex_match and current_slug:
            # Unescape YAML double-quoted string: \\\\ -> \\
            raw = regex_match.group(1)
            result[current_slug] = raw.replace("\\\\", "\\")
    return result


REGEXES = _load_regexes()


def allows(mode: str, path: str) -> bool:
    return bool(re.match(REGEXES[mode], path))


# --- Required matrix from PLAN.md task 0.14 ---

def test_frontend_refuses_api_hold_model() -> None:
    assert not allows("frontend", "api/hold/model.py")


def test_frontend_refuses_web_android() -> None:
    assert not allows("frontend", "web/android/x")


def test_frontend_refuses_docs_bob_evidence() -> None:
    assert not allows("frontend", "docs/bob-evidence/x")


def test_frontend_allows_web_src_board() -> None:
    assert allows("frontend", "web/src/board/x.tsx")


def test_frontend_allows_docs_design() -> None:
    assert allows("frontend", "docs/design/x")


def test_solver_engine_allows_api_tests() -> None:
    assert allows("solver-engine", "api/tests/test_x.py")


def test_solver_engine_allows_api_routes() -> None:
    assert allows("solver-engine", "api/routes/status.py")


def test_solver_engine_refuses_web_src() -> None:
    assert not allows("solver-engine", "web/src/x")


def test_mobile_shell_allows_native() -> None:
    assert allows("mobile-shell", "web/src/native/notify.ts")


def test_mobile_shell_refuses_board() -> None:
    assert not allows("mobile-shell", "web/src/board/x")


def test_evidence_writer_allows_readme() -> None:
    assert allows("evidence-writer", "README.md")


def test_evidence_writer_allows_facts() -> None:
    assert allows("evidence-writer", "docs/FACTS.json")


def test_evidence_writer_allows_specs() -> None:
    assert allows("evidence-writer", "specs/001/spec.md")


def test_evidence_writer_refuses_docs_design() -> None:
    assert not allows("evidence-writer", "docs/design/x")


def test_widening_frontend_to_docs_breaks_evidence_refusal() -> None:
    """Confirm that if frontend regex were widened to match docs/, the
    docs/bob-evidence/x refusal would fail. This test documents the invariant."""
    widened = r"^web/(?!android/|ios/|src/native/|capacitor\.config\.ts$)|^docs/"
    # With the widened regex, docs/bob-evidence/x WOULD match
    assert bool(re.match(widened, "docs/bob-evidence/x")), (
        "widened regex should match docs/bob-evidence/x - "
        "this confirms the real regex correctly refuses it"
    )
    # Confirm the real frontend regex does NOT match docs/bob-evidence/x
    assert not allows("frontend", "docs/bob-evidence/x"), (
        "real frontend regex must refuse docs/bob-evidence/x"
    )


def test_solver_engine_allows_pyproject_toml() -> None:
    assert allows("solver-engine", "pyproject.toml")


def test_solver_engine_allows_uv_lock() -> None:
    assert allows("solver-engine", "uv.lock")


def test_agent_runtime_allows_main_py() -> None:
    assert allows("agent-runtime", "api/main.py")


def test_mobile_shell_allows_capacitor_config() -> None:
    assert allows("mobile-shell", "web/capacitor.config.ts")
