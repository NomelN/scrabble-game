"""Le chevalet d'un joueur : au plus 7 tuiles."""

from __future__ import annotations

from .tiles import BLANK

RACK_SIZE = 7


class Rack:
    def __init__(self, tiles: list[str] | None = None) -> None:
        self.tiles: list[str] = list(tiles or [])

    def __len__(self) -> int:
        return len(self.tiles)

    def __contains__(self, letter: str) -> bool:
        return letter in self.tiles

    def add(self, tiles: list[str]) -> None:
        self.tiles.extend(tiles)

    def can_play(self, letters: list[str]) -> bool:
        """Vrai si le chevalet contient de quoi poser ``letters``.
        Une lettre en minuscule (joker incarnant une lettre) consomme un BLANK.
        """
        pool = list(self.tiles)
        for letter in letters:
            needed = BLANK if letter.islower() else letter
            if needed in pool:
                pool.remove(needed)
            elif BLANK in pool:  # repli : utiliser un joker
                pool.remove(BLANK)
            else:
                return False
        return True

    def remove(self, letters: list[str]) -> None:
        """Retire les tuiles jouées (un joker pour toute lettre minuscule)."""
        for letter in letters:
            needed = BLANK if letter.islower() else letter
            if needed in self.tiles:
                self.tiles.remove(needed)
            elif BLANK in self.tiles:
                self.tiles.remove(BLANK)
            else:
                raise ValueError(f"Tuile absente du chevalet : {letter!r}")

    def is_full(self) -> bool:
        return len(self.tiles) >= RACK_SIZE
