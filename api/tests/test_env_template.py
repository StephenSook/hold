"""The config template and the shipped code agree: every variable in .env.example is read by api/ or scripts/
(or by a named library, verified against the installed package), and every variable the code reads is in the
template. Config templates are where plan-tier claims survive after the prose is fixed."""
from __future__ import annotations

import importlib.util
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / ".env.example"
LIBRARY_READ = {"GOOGLE_GENAI_USE_ENTERPRISE": "google.genai"}  # read by the library, never by our code
_READ = re.compile(r"(?:environ\.get|environ\[|getenv|env_value)\(\s*[\"']([A-Z_]+)[\"']")


def template_vars() -> set[str]:
    return {m.group(1) for m in re.finditer(r"^([A-Z_]+)=", TEMPLATE.read_text(encoding="utf-8"), re.MULTILINE)}


def code_vars() -> set[str]:
    found: set[str] = set()
    for folder in ("api", "scripts"):
        for path in (ROOT / folder).rglob("*.py"):
            found.update(_READ.findall(path.read_text(encoding="utf-8")))
    assert found, "the probe found no environment reads; the regex is broken, not the code"
    return found


def test_every_template_variable_is_read_by_code_or_a_named_library() -> None:
    assert template_vars() - code_vars() - set(LIBRARY_READ) == set()


def test_every_variable_the_code_reads_is_in_the_template() -> None:
    assert code_vars() - template_vars() == set()


def test_library_read_variables_are_read_by_the_installed_library() -> None:
    for name, module in LIBRARY_READ.items():
        spec = importlib.util.find_spec(module)
        assert spec and spec.submodule_search_locations
        package = Path(next(iter(spec.submodule_search_locations)))
        assert any(name in p.read_text(encoding="utf-8", errors="ignore") for p in package.rglob("*.py")), f"{module} never reads {name}"
