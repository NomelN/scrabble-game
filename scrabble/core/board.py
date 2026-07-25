"""Le plateau 15×15 : cases bonus, placement, extraction et scoring des mots.

Convention interne :
- une case vide vaut ``None`` ;
- une lettre normale est stockée en MAJUSCULE ;
- un joker posé est stocké en minuscule (sa valeur = 0, cf. `tiles.letter_value`).
"""

from __future__ import annotations

from dataclasses import dataclass

from .tiles import letter_value

SIZE = 15
CENTER = (7, 7)

# Disposition standard des cases bonus (symétrique) :
#   T = mot compte triple   D = mot compte double
#   t = lettre compte triple  d = lettre compte double
#   . = case normale        (le centre est un mot double)
_LAYOUT = [
    "T..d...T...d..T",
    ".D...t...t...D.",
    "..D...d.d...D..",
    "d..D...d...D..d",
    "....D.....D....",
    ".t...t...t...t.",
    "..d...d.d...d..",
    "T..d...D...d..T",
    "..d...d.d...d..",
    ".t...t...t...t.",
    "....D.....D....",
    "d..D...d...D..d",
    "..D...d.d...D..",
    ".D...t...t...D.",
    "T..d...T...d..T",
]

# Multiplicateurs par case, dérivés de la disposition ci-dessus.
_LETTER_MULT = {".": 1, "d": 2, "t": 3, "D": 1, "T": 1}
_WORD_MULT = {".": 1, "d": 1, "t": 1, "D": 2, "T": 3}


@dataclass(frozen=True)
class Placement:
    """Une tuile posée lors d'un coup : ligne, colonne, lettre.

    ``letter`` est en majuscule pour une lettre normale, en minuscule
    pour un joker (qui « incarne » cette lettre mais vaut 0 point).
    """

    row: int
    col: int
    letter: str


class Board:
    def __init__(self) -> None:
        self._grid: list[list[str | None]] = [
            [None] * SIZE for _ in range(SIZE)
        ]

    # -- Accès de base ----------------------------------------------------
    def letter_at(self, row: int, col: int) -> str | None:
        return self._grid[row][col]

    def is_empty_at(self, row: int, col: int) -> bool:
        return self._grid[row][col] is None

    @property
    def is_empty(self) -> bool:
        return all(cell is None for line in self._grid for cell in line)

    def letter_multiplier(self, row: int, col: int) -> int:
        return _LETTER_MULT[_LAYOUT[row][col]]

    def word_multiplier(self, row: int, col: int) -> int:
        return _WORD_MULT[_LAYOUT[row][col]]

    def premium_code(self, row: int, col: int) -> str:
        """Code brut de la case ('.', 'd', 't', 'D', 'T') — utile pour l'UI."""
        return _LAYOUT[row][col]

    # -- Placement --------------------------------------------------------
    def commit(self, placements: list[Placement]) -> None:
        """Écrit définitivement les tuiles sur le plateau (après validation)."""
        for p in placements:
            self._grid[p.row][p.col] = p.letter


def in_bounds(row: int, col: int) -> bool:
    return 0 <= row < SIZE and 0 <= col < SIZE
