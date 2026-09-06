"""
Adversarial properties for the two surfaces in this change that take untrusted input.

_dist_file() turns a path segment from an HTTP URL into a file on disk. surface_text() strips
markup so a claims guard can read an SVG's prose. Both are places where being almost right is
indistinguishable from being right until somebody attacks them, so they are attacked here with
generated input rather than with the handful of cases a person thinks of.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from api.hold.claims import FORBIDDEN, surface_text
from api.main import _dist_file

SETTINGS = settings(max_examples=400, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])

# A path is built from tokens, not from characters, because the shapes that break a containment
# check are tokens: "..", a separator, an encoded separator, a null byte. Sampling characters
# produces mostly noise and almost never a traversal.
TOKEN = st.sampled_from(
    [
        "..", ".", "/", "\\", "%2e%2e", "%2f", "..%2f", "....//", "~", "assets", "index.html",
        "secret.txt", "sibling", "\x00", "\n", "..;", "..\\", "%00", "\u202e", "\uff0e\uff0e",
        "\u2024\u2024", "e\u0301", "\ufb01", " ", "", "a" * 60,
    ]
)
SEGMENT = st.lists(TOKEN, min_size=0, max_size=8).map("".join)


@pytest.fixture
def dist(tmp_path: Path) -> Path:
    root = tmp_path / "dist"
    (root / "assets").mkdir(parents=True)
    (root / "index.html").write_text("app", encoding="utf-8")
    (root / "assets" / "index-abc.js").write_text("export {}", encoding="utf-8")
    (tmp_path / "secret.txt").write_text("do not serve me", encoding="utf-8")
    (tmp_path / "sibling").mkdir()
    (tmp_path / "sibling" / "also-secret.txt").write_text("nor me", encoding="utf-8")
    return root


@SETTINGS
@given(segment=SEGMENT)
def test_no_path_segment_ever_escapes_dist(dist: Path, segment: str) -> None:
    """The property the whole route rests on: whatever comes back is inside dist, or nothing does."""
    try:
        found = _dist_file(segment, dist=dist)
    except Exception as exc:  # a crash is a denial of service on the one judged origin
        pytest.fail(f"_dist_file raised {type(exc).__name__} on {segment!r}: {exc}")
    if found is None:
        return
    resolved = found.resolve()
    assert resolved.is_relative_to(dist.resolve()), f"{segment!r} escaped to {resolved}"
    assert resolved.is_file(), f"{segment!r} returned a non-file: {resolved}"


@SETTINGS
@given(depth=st.integers(min_value=1, max_value=12), tail=st.sampled_from(["secret.txt", "sibling/also-secret.txt", ""]))
def test_traversal_of_any_depth_is_refused(dist: Path, depth: int, tail: str) -> None:
    """Every traversal shape, at every depth, in both separator styles."""
    for sep in ("/", "\\"):
        attempt = sep.join([".."] * depth) + (sep + tail if tail else "")
        found = _dist_file(attempt, dist=dist)
        if found is not None:
            assert found.resolve().is_relative_to(dist.resolve()), f"{attempt!r} escaped"
            assert "secret" not in found.read_text(encoding="utf-8", errors="replace")


def test_a_directory_is_never_served(dist: Path) -> None:
    assert _dist_file("assets", dist=dist) is None
    assert _dist_file("assets/", dist=dist) is None
    assert _dist_file(".", dist=dist) is None


def test_a_symlink_pointing_out_of_dist_is_refused(dist: Path) -> None:
    """resolve() follows the link, so containment is decided on the real path, not on the name."""
    try:
        (dist / "escape.txt").symlink_to(dist.parent / "secret.txt")
    except (OSError, NotImplementedError):
        pytest.skip("this filesystem does not support symlinks")
    assert _dist_file("escape.txt", dist=dist) is None


def test_a_symlink_inside_dist_still_works(dist: Path) -> None:
    """Containment must not become 'refuse every link': a link that stays inside is legitimate."""
    try:
        (dist / "alias.html").symlink_to(dist / "index.html")
    except (OSError, NotImplementedError):
        pytest.skip("this filesystem does not support symlinks")
    assert _dist_file("alias.html", dist=dist) is not None


# ---------------------------------------------------------------------------
# The claims guard reads an SVG by stripping tags. A forbidden name that survives rendering must
# survive the strip, or the guard is decorative.
# ---------------------------------------------------------------------------

VENDORS = ["watsonx", "granite", "openai", "anthropic"]


# The surrounding text is punctuation and space, never word characters: "watsonx0" is a
# different token and the guard is right to ignore it. The property is about a name a viewer
# reads as a name, not about any substring.
_AROUND = st.text(alphabet=st.sampled_from(list(" .,;:!?()[]{}/-\n\t")), max_size=12)


@given(vendor=st.sampled_from(VENDORS), before=_AROUND, after=_AROUND)
@settings(max_examples=200, deadline=None)
def test_a_vendor_name_in_a_text_node_always_survives_the_strip(vendor: str, before: str, after: str) -> None:
    """Whatever surrounds it, a name a viewer would read is a name the guard must see."""
    svg = f'<svg xmlns="http://www.w3.org/2000/svg"><text x="0" y="0">{before}{vendor}{after}</text></svg>'
    assert FORBIDDEN.search(_strip(svg)), f"the guard cannot see {vendor!r} in a text node"


def _strip(svg: str) -> str:
    """surface_text() operates on a Path, so the same extraction is applied to a string here."""
    from api.hold.claims import _svg_prose

    return _svg_prose(svg)


@pytest.mark.parametrize(
    "svg",
    [
        '<svg><g class="watsonx-box"><rect/></g></svg>',
        '<svg><rect id="granite" fill="#fff"/></svg>',
        '<svg><path d="M0 0 L10 10" data-note="openai"/></svg>',
        '<svg><!-- watsonx was considered and rejected --><text>fine</text></svg>',
        # These four defeated the regex that used to do this job. It stopped at the first ">",
        # so a ">" inside an attribute value leaked the rest of the tag into the prose, and a
        # stylesheet or a script was kept whole. A font-family is not a claim.
        '<svg><text foo="&gt;" class="watsonx">hello</text></svg>',
        '<svg><rect data="a&gt;b" id="claude"/></svg>',
        '<svg><style>.box { font-family: watsonx; }</style><text>ok</text></svg>',
        '<svg><script>var x = "claude"</script><text>ok</text></svg>',
    ],
)
def test_a_vendor_name_that_is_only_markup_is_not_a_claim(svg: str) -> None:
    """A class, an id, an attribute, a comment, a stylesheet or a script is not read by a viewer."""
    assert not FORBIDDEN.search(_strip(svg)), f"markup was read as prose: {svg}"


@pytest.mark.parametrize(
    "svg",
    [
        '<svg><text>Verdicts come from watsonx.</text></svg>',
        '<svg><g><rect/></g>granite runs the solver</svg>',
        '<svg><text>a <tspan>claude</tspan> model</text></svg>',
        '<svg><desc>openai is used here</desc><text>ok</text></svg>',
    ],
)
def test_a_vendor_name_a_viewer_would_read_is_always_a_claim(svg: str) -> None:
    """Tail text, nested spans and the description are all read. None may slip through."""
    assert FORBIDDEN.search(_strip(svg)), f"a real claim was missed: {svg}"


@pytest.mark.parametrize(
    "svg",
    [
        # defs looks like a block nobody reads. Its contents are drawn wherever a use element
        # references them, so a claim parked in defs is a claim on screen. Excluding defs left a
        # hole exactly the size of "put it in defs and reference it".
        '<svg><defs><text id="t">watsonx</text></defs><use href="#t"/></svg>',
        '<svg><defs><g id="g"><text>granite</text></g></defs><use href="#g"/></svg>',
        '<svg><defs><marker id="m"><text>openai</text></marker></defs></svg>',
    ],
)
def test_a_claim_parked_in_defs_is_still_a_claim(svg: str) -> None:
    assert FORBIDDEN.search(_strip(svg)), f"a name inside defs was invisible to the guard: {svg}"


def test_unparseable_markup_is_not_a_free_pass() -> None:
    """Broken markup over-reports rather than under-reports: silence would be the wrong default."""
    assert FORBIDDEN.search(_strip('<svg><text>watsonx'))


def test_the_real_diagram_is_readable_prose_after_stripping() -> None:
    """The guard must actually extract words from the shipped diagram, not an empty string."""
    root = Path(__file__).resolve().parents[2]
    text = surface_text(root / "docs" / "architecture.svg")
    assert "<" not in text, "markup survived the strip"
    assert len(text.split()) > 80, "the strip produced almost no prose, so the guard reads nothing"
