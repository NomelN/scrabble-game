"""Le sac de tuiles : pioche et échange de lettres."""

from __future__ import annotations

import random

from .tiles import LETTER_COUNTS


class Bag:
    """Sac de lettres mélangé. Optionnellement déterministe via ``seed``
    (utile pour les tests et pour rejouer une partie à l'identique)."""

    def __init__(self, seed: int | None = None) -> None:
        self._rng = random.Random(seed)
        self._tiles: list[str] = [
            letter for letter, count in LETTER_COUNTS.items() for _ in range(count)
        ]
        self._rng.shuffle(self._tiles)

    def __len__(self) -> int:
        return len(self._tiles)

    @property
    def is_empty(self) -> bool:
        return not self._tiles

    def draw(self, n: int) -> list[str]:
        """Pioche jusqu'à ``n`` tuiles (moins s'il n'en reste pas assez)."""
        n = min(n, len(self._tiles))
        drawn, self._tiles = self._tiles[:n], self._tiles[n:]
        return drawn

    def exchange(self, tiles: list[str]) -> list[str]:
        """Rend des tuiles au sac et en repioche autant. Les tuiles rendues
        ne peuvent pas être repiochées immédiatement (on pioche d'abord)."""
        new_tiles = self.draw(len(tiles))
        self._tiles.extend(tiles)
        self._rng.shuffle(self._tiles)
        return new_tiles
