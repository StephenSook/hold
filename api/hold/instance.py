"""
Task 1.2: MiniZinc .dzn parser for talent scheduling instances.

Parses a .dzn file into an Instance dataclass.
No MiniZinc runtime required; uses stdlib re only.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Instance:
    """
    A talent scheduling benchmark instance.

    num_scenes: number of scenes (N)
    num_actors: number of actors (J)
    ia: ia[j][i] = 1 if actor j appears in scene i (J x N matrix)
    c: c[j] = actor j's day rate (length J)
    d: d[i] = duration of scene i in eighths-of-a-page (length N)
    """
    name: str
    num_scenes: int
    num_actors: int
    ia: tuple[tuple[int, ...], ...]  # frozen: (J x N)
    c: tuple[int, ...]               # frozen: (J,)
    d: tuple[int, ...]               # frozen: (N,)

    @property
    def fixed_cost(self) -> int:
        """sum_j c_j * sum_{i in ia[j]} d_i  (the unavoidable working cost)."""
        total = 0
        for j in range(self.num_actors):
            for i in range(self.num_scenes):
                if self.ia[j][i] == 1:
                    total += self.c[j] * self.d[i]
        return total


def parse_dzn(path: Path) -> Instance:
    """Parse a MiniZinc .dzn talent scheduling instance file."""
    text = path.read_text()

    def get_int(key: str) -> int:
        m = re.search(rf"{key}\s*=\s*(\d+)\s*;", text)
        if not m:
            raise ValueError(f"Key '{key}' not found in {path}")
        return int(m.group(1))

    def get_int_array(key: str) -> list[int]:
        m = re.search(rf"{key}\s*=\s*\[([^\]]+)\]\s*;", text, re.DOTALL)
        if not m:
            raise ValueError(f"Key '{key}' not found in {path}")
        return [int(x.strip()) for x in m.group(1).split(",") if x.strip()]

    num_scenes = get_int("numScenes")
    num_actors = get_int("numActors")
    c = get_int_array("c")
    d = get_int_array("d")

    if len(c) != num_actors:
        raise ValueError(f"c length {len(c)} != numActors {num_actors}")
    if len(d) != num_scenes:
        raise ValueError(f"d length {len(d)} != numScenes {num_scenes}")

    # Parse ia matrix: rows separated by | inside [ | ... | ... | ]
    ia_match = re.search(r"ia\s*=\s*\[(\|[^\]]+)\]\s*;", text, re.DOTALL)
    if not ia_match:
        raise ValueError(f"'ia' matrix not found in {path}")
    ia_text = ia_match.group(1)
    rows = [r.strip() for r in ia_text.split("|") if r.strip()]
    ia: list[tuple[int, ...]] = []
    for row in rows:
        vals = tuple(int(x.strip()) for x in row.split(",") if x.strip())
        if vals:
            ia.append(vals)

    if len(ia) != num_actors:
        raise ValueError(f"ia has {len(ia)} rows, expected numActors={num_actors}")
    for j, row in enumerate(ia):
        if len(row) != num_scenes:
            raise ValueError(
                f"ia row {j} has {len(row)} entries, expected numScenes={num_scenes}"
            )

    return Instance(
        name=path.stem,
        num_scenes=num_scenes,
        num_actors=num_actors,
        ia=tuple(ia),
        c=tuple(c),
        d=tuple(d),
    )
