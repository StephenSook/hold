"""Every repository path the README names in backticks exists (globs must match). A judge-facing link
to a file that is not there is an unwired claim; this fails on it before it ships."""
from __future__ import annotations

import glob
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_PATH = re.compile(r"`([A-Za-z0-9_.][A-Za-z0-9_./*-]*(?:/[A-Za-z0-9_./*-]*|\.(?:md|json|py|yml|yaml|toml|txt|sh|svg|png)))`")


def readme_paths() -> list[str]:
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    found = sorted({m.group(1) for m in _PATH.finditer(text)})
    assert found, "the probe found no paths in README.md; the regex is broken, not the README"
    return found


def test_every_path_the_readme_names_exists() -> None:
    missing = [p for p in readme_paths() if not glob.glob(str(ROOT / p))]
    assert missing == [], f"README names paths that do not exist: {missing}"
