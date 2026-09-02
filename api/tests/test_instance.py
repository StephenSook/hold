"""
Task 1.2: dzn parser tests.
Verified parameters for film116: 19 scenes, 8 actors,
c=[10,4,5,5,5,40,4,20], d[8]=2 (0-indexed, i.e. scene 9 in 1-indexed).
"""
from pathlib import Path

import pytest

from api.hold.instance import Instance, parse_dzn

BENCH = Path(__file__).parent.parent.parent / "bench"
MEDIUM_DIR = BENCH / "instances" / "medium"
EASY_DIR = BENCH / "instances" / "easy"


def test_film116_num_scenes() -> None:
    inst = parse_dzn(MEDIUM_DIR / "film116.dzn")
    assert inst.num_scenes == 19


def test_film116_num_actors() -> None:
    inst = parse_dzn(MEDIUM_DIR / "film116.dzn")
    assert inst.num_actors == 8


def test_film116_c_values() -> None:
    inst = parse_dzn(MEDIUM_DIR / "film116.dzn")
    assert list(inst.c) == [10, 4, 5, 5, 5, 40, 4, 20]


def test_film116_d9_is_2() -> None:
    """d[8] (0-indexed) = 2; this is scene 9 in 1-indexed notation."""
    inst = parse_dzn(MEDIUM_DIR / "film116.dzn")
    assert inst.d[8] == 2


def test_film116_fixed_cost_positive() -> None:
    inst = parse_dzn(MEDIUM_DIR / "film116.dzn")
    assert inst.fixed_cost > 0


def test_film116_ia_dimensions() -> None:
    inst = parse_dzn(MEDIUM_DIR / "film116.dzn")
    assert len(inst.ia) == inst.num_actors
    for row in inst.ia:
        assert len(row) == inst.num_scenes
    # All values are 0 or 1
    for row in inst.ia:
        for val in row:
            assert val in (0, 1)


def test_instance_is_frozen() -> None:
    inst = parse_dzn(MEDIUM_DIR / "film116.dzn")
    with pytest.raises(Exception):
        inst.num_scenes = 99  # type: ignore[misc]


def test_all_medium_instances_parse() -> None:
    for path in sorted(MEDIUM_DIR.glob("*.dzn")):
        inst = parse_dzn(path)
        assert inst.num_scenes > 0
        assert inst.num_actors > 0
        assert len(inst.c) == inst.num_actors
        assert len(inst.d) == inst.num_scenes


def test_easy_tiny_parses() -> None:
    inst = parse_dzn(EASY_DIR / "tiny.dzn")
    assert inst.num_scenes >= 1
    assert inst.num_actors >= 1
