"""Validation et scoring d'un coup.

Un « coup » est une liste de `Placement` (tuiles posées ce tour-ci).
`validate_and_score` vérifie toutes les règles du Scrabble et calcule le
score, en distinguant clairement les différents motifs d'invalidité.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .board import Board, Placement, SIZE, CENTER, in_bounds
from .tiles import letter_value

BINGO_BONUS = 50  # « Scrabble » : 7 tuiles posées en un coup.
RACK_SIZE = 7


class InvalidMove(Exception):
    """Coup illégal. ``reason`` est un code stable exploitable par l'UI/l'IA."""

    def __init__(self, reason: str, detail: str = "") -> None:
        super().__init__(detail or reason)
        self.reason = reason
        self.detail = detail


@dataclass
class WordScore:
    word: str
    points: int
    cells: list[tuple[int, int]] = field(default_factory=list)


@dataclass
class MoveResult:
    words: list[WordScore]
    total: int
    is_bingo: bool

    @property
    def main_word(self) -> str:
        return self.words[0].word if self.words else ""


def _combined_letter(board: Board, placements_by_cell, row, col):
    """Lettre effective d'une case = tuile déjà présente ou tuile posée."""
    existing = board.letter_at(row, col)
    if existing is not None:
        return existing
    return placements_by_cell.get((row, col))


def validate_and_score(
    board: Board, placements: list[Placement], dictionary
) -> MoveResult:
    """Valide le coup et renvoie son score. Lève `InvalidMove` sinon.

    `dictionary` doit exposer ``__contains__`` (ex. un `set` de mots en
    majuscules, ou l'objet `Dictionary` de ce package).
    """
    if not placements:
        raise InvalidMove("empty", "Aucune tuile posée.")

    cells = {(p.row, p.col) for p in placements}
    if len(cells) != len(placements):
        raise InvalidMove("duplicate", "Deux tuiles sur la même case.")

    for p in placements:
        if not in_bounds(p.row, p.col):
            raise InvalidMove("out_of_bounds", f"Case hors plateau : {p}.")
        if not board.is_empty_at(p.row, p.col):
            raise InvalidMove("occupied", f"Case déjà occupée : {p}.")

    rows = {p.row for p in placements}
    coldict = {p.col for p in placements}
    if len(rows) == 1:
        orientation = "H"
    elif len(coldict) == 1:
        orientation = "V"
    else:
        raise InvalidMove("not_in_line", "Les tuiles doivent être alignées.")

    placements_by_cell = {(p.row, p.col): p.letter for p in placements}

    # Contiguïté : pas de trou dans la ligne entre la 1re et la dernière tuile.
    if orientation == "H":
        row = next(iter(rows))
        cmin, cmax = min(coldict), max(coldict)
        for c in range(cmin, cmax + 1):
            if _combined_letter(board, placements_by_cell, row, c) is None:
                raise InvalidMove("gap", "Le mot principal comporte un trou.")
    else:
        col = next(iter(coldict))
        rmin, rmax = min(rows), max(rows)
        for r in range(rmin, rmax + 1):
            if _combined_letter(board, placements_by_cell, r, col) is None:
                raise InvalidMove("gap", "Le mot principal comporte un trou.")

    # Connexion : 1er coup => centre ; sinon => toucher une tuile existante.
    if board.is_empty:
        if CENTER not in cells:
            raise InvalidMove("center", "Le premier mot doit passer par le centre.")
    else:
        if not _touches_existing(board, placements):
            raise InvalidMove("disconnected", "Le mot doit toucher une tuile existante.")

    # Extraction + scoring des mots (principal puis transversaux).
    words = _collect_words(board, placements, placements_by_cell, orientation)
    if not words:
        raise InvalidMove("too_short", "Un mot doit faire au moins 2 lettres.")

    for w in words:
        if w.word not in dictionary:
            raise InvalidMove("not_a_word", f"« {w.word} » absent du dictionnaire.")

    total = sum(w.points for w in words)
    is_bingo = len(placements) == RACK_SIZE
    if is_bingo:
        total += BINGO_BONUS

    return MoveResult(words=words, total=total, is_bingo=is_bingo)


def _touches_existing(board: Board, placements: list[Placement]) -> bool:
    for p in placements:
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            r, c = p.row + dr, p.col + dc
            if in_bounds(r, c) and board.letter_at(r, c) is not None:
                return True
    return False


def _collect_words(board, placements, placements_by_cell, orientation):
    """Renvoie les WordScore : le mot principal en tête, puis les transversaux
    formés par chaque tuile posée. Les mots d'une seule lettre sont ignorés."""
    words: list[WordScore] = []
    main_dir = (0, 1) if orientation == "H" else (1, 0)
    cross_dir = (1, 0) if orientation == "H" else (0, 1)

    anchor = placements[0]
    main = _read_word(board, placements_by_cell, anchor.row, anchor.col, main_dir)
    if main and len(main.word) >= 2:
        words.append(main)

    for p in placements:
        cross = _read_word(board, placements_by_cell, p.row, p.col, cross_dir)
        if cross and len(cross.word) >= 2:
            words.append(cross)

    return words


def _read_word(board, placements_by_cell, row, col, direction):
    """Lit le mot complet passant par (row, col) dans `direction`, en incluant
    les tuiles déjà sur le plateau, et calcule son score avec les bonus (les
    bonus ne s'appliquent qu'aux tuiles *nouvellement* posées)."""
    dr, dc = direction
    # Reculer jusqu'au début du mot.
    r, c = row, col
    while in_bounds(r - dr, c - dc) and _cell(board, placements_by_cell, r - dr, c - dc):
        r, c = r - dr, c - dc

    letters: list[str] = []
    cells: list[tuple[int, int]] = []
    points = 0
    word_mult = 1
    while in_bounds(r, c) and _cell(board, placements_by_cell, r, c):
        letter = _cell(board, placements_by_cell, r, c)
        is_new = (r, c) in placements_by_cell
        lp = letter_value(letter)
        if is_new:
            lp *= board.letter_multiplier(r, c)
            word_mult *= board.word_multiplier(r, c)
        points += lp
        letters.append(letter.upper())
        cells.append((r, c))
        r, c = r + dr, c + dc

    return WordScore(word="".join(letters), points=points * word_mult, cells=cells)


def _cell(board, placements_by_cell, row, col):
    existing = board.letter_at(row, col)
    if existing is not None:
        return existing
    return placements_by_cell.get((row, col))
