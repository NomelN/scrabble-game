"""Interface commune des IA, générateur de coups et fabrique de niveaux.

Le générateur propose des coups *candidats* ; chacun est validé par le cœur
du jeu (`validate_and_score`), donc tout coup renvoyé est légal par
construction. Les niveaux ne diffèrent que par la *sélection* parmi ces
candidats — c'est ce qui rend l'ajout de nouveaux niveaux trivial.
"""

from __future__ import annotations

import itertools
import random
from dataclasses import dataclass
from enum import Enum, auto

from ..core.board import Board, Placement, SIZE, CENTER, in_bounds
from ..core.rules import InvalidMove, MoveResult, validate_and_score
from ..core.tiles import BLANK


class ActionKind(Enum):
    PLAY = auto()
    EXCHANGE = auto()
    PASS = auto()


@dataclass
class Action:
    kind: ActionKind
    placements: list[Placement] | None = None
    tiles: list[str] | None = None
    # Rempli pour un coup PLAY : utile pour trier/afficher.
    result: MoveResult | None = None


@dataclass
class Candidate:
    placements: list[Placement]
    result: MoveResult


# --------------------------------------------------------------------------
# Générateur de coups
# --------------------------------------------------------------------------
def _anchors(board: Board) -> list[tuple[int, int]]:
    """Cases vides où un mot peut commencer : le centre (plateau vide) ou
    toute case vide adjacente à une tuile déjà posée."""
    if board.is_empty:
        return [CENTER]
    anchors = []
    for r in range(SIZE):
        for c in range(SIZE):
            if board.letter_at(r, c) is not None:
                continue
            for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                if in_bounds(r + dr, c + dc) and board.letter_at(r + dr, c + dc):
                    anchors.append((r, c))
                    break
    return anchors


def _rack_options(rack_tiles: list[str], length: int):
    """Permutations distinctes de ``length`` tuiles du chevalet. Un joker (BLANK)
    est développé en chacune des 26 lettres possibles (minuscule = 0 point)."""
    seen = set()
    for combo in itertools.permutations(rack_tiles, length):
        # Développe les jokers.
        pools = [
            [chr(ord("a") + i) for i in range(26)] if t == BLANK else [t]
            for t in combo
        ]
        for concrete in itertools.product(*pools):
            key = tuple(concrete)
            if key in seen:
                continue
            seen.add(key)
            yield list(concrete)


def generate_moves(
    board: Board,
    rack_tiles: list[str],
    dictionary,
    max_len: int = 7,
    limit: int | None = None,
) -> list[Candidate]:
    """Énumère des coups légaux. ``max_len`` borne le nombre de tuiles posées
    (le baisser accélère et « affaiblit » l'IA) ; ``limit`` arrête la recherche
    dès que ce nombre de candidats est atteint.

    ⚠️ Générateur volontairement simple (force brute bornée) : parfait pour les
    niveaux facile/moyen. Pour un niveau *expert* rapide et fort, il faudra le
    remplacer par un algorithme à base de GADDAG/DAWG (voir README).
    """
    candidates: list[Candidate] = []
    anchors = _anchors(board)
    orientations = [(0, 1), (1, 0)]  # horizontal, vertical
    n = min(max_len, len(rack_tiles))

    for length in range(1, n + 1):
        for letters in _rack_options(rack_tiles, length):
            for (dr, dc) in orientations:
                for (ar, ac) in anchors:
                    placements = _lay(board, ar, ac, dr, dc, letters)
                    if placements is None:
                        continue
                    try:
                        res = validate_and_score(board, placements, dictionary)
                    except InvalidMove:
                        continue
                    candidates.append(Candidate(placements, res))
                    if limit is not None and len(candidates) >= limit:
                        return candidates
    return candidates


def _lay(board, ar, ac, dr, dc, letters):
    """Pose ``letters`` à partir de l'ancre en sautant les cases occupées.
    Renvoie la liste des `Placement` (seulement sur cases vides) ou None si
    ça sort du plateau."""
    placements = []
    r, c = ar, ac
    for letter in letters:
        while in_bounds(r, c) and board.letter_at(r, c) is not None:
            r, c = r + dr, c + dc
        if not in_bounds(r, c):
            return None
        placements.append(Placement(r, c, letter))
        r, c = r + dr, c + dc
    return placements


# --------------------------------------------------------------------------
# Stratégies par niveau
# --------------------------------------------------------------------------
class AIPlayer:
    """Base : décide d'une action pour le joueur courant d'une partie."""

    #: borne du nombre de tuiles posées explorées (règle vitesse/force)
    max_len = 7
    #: nb max de candidats générés avant de trancher
    search_limit: int | None = None

    def __init__(self, seed: int | None = None) -> None:
        self._rng = random.Random(seed)

    def choose(self, game) -> Action:
        rack = game.current_player.rack.tiles
        candidates = generate_moves(
            game.board, rack, game.dictionary,
            max_len=self.max_len, limit=self.search_limit,
        )
        if candidates:
            return self._select(candidates)
        # Aucun coup : échanger si possible, sinon passer.
        if not game.bag.is_empty and rack:
            k = min(len(rack), 7)
            return Action(ActionKind.EXCHANGE, tiles=list(rack[:k]))
        return Action(ActionKind.PASS)

    def _select(self, candidates: list[Candidate]) -> Action:  # pragma: no cover
        raise NotImplementedError


class EasyAI(AIPlayer):
    """Facile : joue un coup court, peu optimal (score plutôt bas)."""

    max_len = 3
    search_limit = 200

    def _select(self, candidates):
        candidates.sort(key=lambda c: c.result.total)
        # Prend parmi les coups les plus faibles, avec un peu d'aléatoire.
        pool = candidates[: max(1, len(candidates) // 3)]
        c = self._rng.choice(pool)
        return Action(ActionKind.PLAY, placements=c.placements, result=c.result)


class MediumAI(AIPlayer):
    """Moyen : joue le meilleur coup immédiat qu'il trouve (glouton)."""

    max_len = 7
    search_limit = 3000

    def _select(self, candidates):
        best = max(candidates, key=lambda c: c.result.total)
        return Action(ActionKind.PLAY, placements=best.placements, result=best.result)


class HardAI(MediumAI):
    """Expert (ébauche) : pour l'instant identique au niveau moyen mais sans
    borne de longueur. Objectif v2 : recherche GADDAG + heuristique de position
    (garder de bonnes lettres, viser les cases bonus, bloquer l'adversaire)."""

    search_limit = 20000


_LEVELS = {"easy": EasyAI, "medium": MediumAI, "hard": HardAI}


def make_ai(level: str, seed: int | None = None) -> AIPlayer:
    """Fabrique une IA à partir d'un nom de niveau : ``easy`` / ``medium`` / ``hard``."""
    try:
        return _LEVELS[level](seed=seed)
    except KeyError:
        raise ValueError(f"Niveau inconnu : {level!r} (attendu : {list(_LEVELS)}).")
