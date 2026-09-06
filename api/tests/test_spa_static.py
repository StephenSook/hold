"""
The server must serve every file the built web app asks for, not only assets/.

This test exists because production broke in exactly the gap it covers. Vite emits
registerSW.js, sw.js, manifest.webmanifest, favicon.svg and the PWA icons at the ROOT of
web/dist, beside index.html. Only /assets was mounted, so each of those fell through to the SPA
catch-all and was answered with index.html and content-type text/html. The browser parsed HTML
as JavaScript and threw on every route, while CI stayed green: nothing between a correct build
and a correct server was under test.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.main import _dist_file, app

ROOT = Path(__file__).resolve().parents[2]
DIST = ROOT / "web" / "dist"

client = TestClient(app)

# The files Vite writes at the root of dist. index.html is excluded: it is the fallback itself.
# registerSW.js is not here any more. The app registers the worker through useRegisterSW, so
# the file is no longer emitted, and leaving it in this tuple made one case skip on every run
# for a reason that had stopped being temporary. Its successor state is asserted below.
ROOT_FILES = ("sw.js", "manifest.webmanifest", "favicon.svg", "icon-192.png")


needs_build = pytest.mark.skipif(
    not (DIST / "index.html").is_file(),
    reason="web/dist is not built; run npm run build in web/. The CI web job builds it.",
)


@needs_build
@pytest.mark.parametrize("name", ROOT_FILES)
def test_a_root_file_is_served_as_itself_and_not_as_index_html(name: str) -> None:
    """Each is served from disk. Before the fix every one of these answered with HTML."""
    assert (DIST / name).is_file(), f"{name} is not in this build, so this case would assert nothing"
    response = client.get(f"/{name}")
    assert response.status_code == 200
    assert not response.text.lstrip().lower().startswith("<!doctype html>"), (
        f"/{name} answered with the SPA fallback; the browser will parse HTML as its content type"
    )


@needs_build
def test_the_module_entry_is_javascript() -> None:
    """The one request whose failure is fatal: the entry module."""
    entry = next((p for p in (DIST / "assets").glob("index-*.js")), None)
    assert entry is not None, "no assets/index-*.js in the build"
    response = client.get(f"/assets/{entry.name}")
    assert response.status_code == 200
    assert "html" not in response.headers.get("content-type", "")


@needs_build
def test_an_unknown_route_still_gets_the_app() -> None:
    """A HashRouter path, a deep link, a typo: all of them are the app."""
    response = client.get("/not-a-real-path")
    assert response.status_code == 200
    assert response.text.lstrip().lower().startswith("<!doctype html>")


@needs_build
@pytest.mark.parametrize(
    "attempt",
    ["../pyproject.toml", "../../etc/passwd", "..%2f..%2fpyproject.toml", "assets/../../pyproject.toml"],
)
def test_a_path_that_escapes_dist_is_refused(attempt: str) -> None:
    """Serving from a user-supplied path is only safe with the containment check that refuses these."""
    response = client.get(f"/{attempt}")
    # Either the app answers, or the router rejects the shape. It must never be the file.
    assert "[project]" not in response.text
    assert "root:x:" not in response.text


# ---------------------------------------------------------------------------
# The decision itself, with a dist injected. These need no build, so they run in CI, where the
# pytest job does not build the web app and every test above would otherwise skip.
# ---------------------------------------------------------------------------


def test_a_file_at_the_root_of_dist_is_found(tmp_path: Path) -> None:
    (tmp_path / "registerSW.js").write_text("export {}", encoding="utf-8")
    found = _dist_file("registerSW.js", dist=tmp_path)
    assert found is not None and found.name == "registerSW.js"


def test_a_file_in_a_subdirectory_is_found(tmp_path: Path) -> None:
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "index-abc.js").write_text("export {}", encoding="utf-8")
    assert _dist_file("assets/index-abc.js", dist=tmp_path) is not None


def test_a_path_that_names_nothing_falls_through(tmp_path: Path) -> None:
    assert _dist_file("board", dist=tmp_path) is None
    assert _dist_file("", dist=tmp_path) is None


def test_a_directory_is_not_a_file(tmp_path: Path) -> None:
    (tmp_path / "assets").mkdir()
    assert _dist_file("assets", dist=tmp_path) is None


@pytest.mark.parametrize("escape", ["../secret.txt", "../../secret.txt", "assets/../../secret.txt"])
def test_a_path_that_escapes_dist_is_refused_by_the_decision(tmp_path: Path, escape: str) -> None:
    """The containment check is the only thing making a user-supplied path safe to serve."""
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (tmp_path / "secret.txt").write_text("do not serve me", encoding="utf-8")
    assert _dist_file(escape, dist=dist) is None


def test_a_symlink_out_of_dist_is_refused(tmp_path: Path) -> None:
    """resolve() follows the link, so containment is checked on the real path, not the name."""
    dist = tmp_path / "dist"
    dist.mkdir()
    (tmp_path / "secret.txt").write_text("do not serve me", encoding="utf-8")
    try:
        (dist / "link.txt").symlink_to(tmp_path / "secret.txt")
    except (OSError, NotImplementedError):
        pytest.skip("this filesystem does not support symlinks")
    assert _dist_file("link.txt", dist=dist) is None


def test_the_api_is_never_shadowed_by_a_file() -> None:
    """/api routes are registered before the catch-all and stay that way."""
    response = client.get("/api/status")
    assert response.status_code == 200
    assert response.json()["headline_source"] == "docs/FACTS.json"


@pytest.mark.parametrize("path", ["/", "/judge", "/icon-192.png"])
def test_head_is_answered_on_the_paths_a_link_checker_asks_about(path: str) -> None:
    """
    A FastAPI route declared with @app.get accepts only GET. Starlette adds HEAD beside GET on its
    own routes and FastAPI does not, so the site root, the judge page and every static asset
    answered 405 to a HEAD request while every browser saw a working site.

    That is what a link unfurler, an uptime monitor and most link checkers send first, so the one
    URL printed on the README read as broken to everything that checks a link without opening it.
    """
    assert client.head(path).status_code != 405


@needs_build
def test_register_sw_is_not_emitted() -> None:
    """
    The retired half of the rule above. The worker is registered through useRegisterSW, so Vite
    writes no registerSW.js, and a request for it correctly falls through to the SPA.

    This is asserted rather than skipped. A guard whose condition has dissolved has to state the
    state that replaced it, or it goes quiet and nobody learns that the file came back.
    """
    assert not (DIST / "registerSW.js").exists(), (
        "registerSW.js is being emitted again; put it back in ROOT_FILES so it is served as itself"
    )
