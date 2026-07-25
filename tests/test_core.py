"""Tests du cœur de jeu (Python pur, aucune dépendance UI)."""

import pytest

from scrabble.core.board import Board, Placement
from scrabble.core.bag import Bag
from scrabble.core.dictionary import Dictionary
from scrabble.core.rack import Rack
from scrabble.core.rules import InvalidMove, validate_and_score
from scrabble.core.tiles import LETTER_COUNTS, TOTAL_TILES, letter_value


# -- Tuiles / sac ---------------------------------------------------------
def test_distribution_totals_102():
    assert TOTAL_TILES == 102
    assert LETTER_COUNTS["E"] == 15
    assert LETTER_COUNTS["?"] == 2


def test_bag_is_deterministic_with_seed():
    assert Bag(seed=1).draw(7) == Bag(seed=1).draw(7)


def test_bag_draw_reduces_count():
    bag = Bag(seed=0)
    bag.draw(7)
    assert len(bag) == TOTAL_TILES - 7


def test_blank_tile_is_worth_zero():
    assert letter_value("?") == 0
    assert letter_value("e") == 0   # joker incarnant un E
    assert letter_value("E") == 1


# -- Chevalet -------------------------------------------------------------
def test_rack_can_play_uses_blank_as_fallback():
    rack = Rack(["C", "H", "A", "?"])
    assert rack.can_play(["C", "H", "A", "t"])  # 't' via le joker
    rack.remove(["C", "H", "A", "t"])
    assert rack.tiles == []


# -- Placement & scoring --------------------------------------------------
def test_first_move_must_cross_center():
    board = Board()
    d = Dictionary.demo()
    off_center = [Placement(0, 0, "M"), Placement(0, 1, "O"), Placement(0, 2, "T")]
    with pytest.raises(InvalidMove) as exc:
        validate_and_score(board, off_center, d)
    assert exc.value.reason == "center"


def test_first_move_scores_with_center_double():
    board = Board()
    d = Dictionary.demo()
    # MOT posé horizontalement sur (7,7)-(7,9) ; centre = mot compte double.
    placements = [Placement(7, 7, "M"), Placement(7, 8, "O"), Placement(7, 9, "T")]
    res = validate_and_score(board, placements, d)
    assert res.main_word == "MOT"
    # M(2)+O(1)+T(1) = 4, ×2 (centre) = 8.
    assert res.total == 8


def test_rejects_unknown_word():
    board = Board()
    d = Dictionary.demo()
    placements = [Placement(7, 7, "X"), Placement(7, 8, "Y"), Placement(7, 9, "Z")]
    with pytest.raises(InvalidMove) as exc:
        validate_and_score(board, placements, d)
    assert exc.value.reason == "not_a_word"


def test_bingo_bonus_applied_for_seven_tiles():
    board = Board()
    d = Dictionary({"BONJOUR"})  # 7 lettres
    placements = [Placement(7, c, ch) for c, ch in zip(range(7, 14), "BONJOUR")]
    res = validate_and_score(board, placements, d)
    assert res.is_bingo
    assert res.total >= 50  # au moins le bonus « Scrabble »
