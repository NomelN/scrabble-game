"""Tests d'intégration : machine à états de la partie + IA."""

from scrabble.ai import ActionKind, make_ai
from scrabble.core.board import Placement
from scrabble.core.dictionary import Dictionary
from scrabble.core.game import EventType, Game


def _rigged_game():
    """Partie déterministe dont le chevalet du joueur 0 permet de jouer 'MOT'."""
    game = Game(["Alice", "Bob"], dictionary=Dictionary.demo(), seed=42)
    game.players[0].rack.tiles = list("MOTABCE")
    return game


def test_play_updates_score_and_advances_turn():
    game = _rigged_game()
    res = game.play([Placement(7, 7, "M"), Placement(7, 8, "O"), Placement(7, 9, "T")])
    assert res.main_word == "MOT"
    assert game.players[0].score == res.total
    assert game.current == 1                      # au tour de Bob
    assert len(game.players[0].rack) == 7         # chevalet recomplété
    assert any(e.type == EventType.MOVE_PLAYED for e in game.events)


def test_pass_turn_emits_event_and_advances():
    game = _rigged_game()
    game.pass_turn()
    assert game.current == 1
    assert game.events[-1].type == EventType.PASSED


def test_ai_levels_build():
    for level in ("easy", "medium", "hard"):
        assert make_ai(level, seed=0) is not None


def test_ai_chooses_a_legal_action_on_empty_board():
    game = Game(["IA", "Humain"], dictionary=Dictionary.demo(),
                ai_flags=[True, False], seed=7)
    # Chevalet garantissant au moins un mot du lexique démo ('MOT').
    game.players[0].rack.tiles = list("MOTLESA")
    ai = make_ai("medium", seed=7)
    action = ai.choose(game)
    assert action.kind in (ActionKind.PLAY, ActionKind.EXCHANGE, ActionKind.PASS)
    if action.kind is ActionKind.PLAY:
        # Le coup proposé doit être réellement jouable.
        res = game.play(action.placements)
        assert res.total > 0
