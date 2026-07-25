"""Tests de sérialisation d'une partie et de la sauvegarde/reprise."""

from scrabble.core.board import Placement
from scrabble.core.dictionary import Dictionary
from scrabble.core.game import Game
from scrabble import savegame


def _game_with_a_move():
    game = Game(["Joueur", "Ordinateur"], dictionary=Dictionary.demo(),
                ai_flags=[False, True], seed=1)
    game.players[0].rack.tiles = list("MOTABCE")
    game.play([Placement(7, 7, "M"), Placement(7, 8, "O"), Placement(7, 9, "T")])
    return game


def test_game_roundtrip_preserves_state():
    game = _game_with_a_move()
    data = game.to_dict()
    restored = Game.from_dict(data, Dictionary.demo())

    assert restored.board.letter_at(7, 7) == "M"
    assert restored.board.letter_at(7, 9) == "T"
    assert restored.current == game.current
    assert restored.players[0].score == game.players[0].score
    assert restored.players[0].rack.tiles == game.players[0].rack.tiles
    assert restored.bag.to_list() == game.bag.to_list()
    assert restored.players[1].is_ai is True


def test_save_load_clear(tmp_path):
    path = tmp_path / "save.json"
    assert savegame.has_save(path) is False

    game = _game_with_a_move()
    savegame.save_game(game, "medium", path)
    assert savegame.has_save(path) is True

    loaded = savegame.load_game(Dictionary.demo(), path)
    assert loaded is not None
    restored, level = loaded
    assert level == "medium"
    assert restored.board.letter_at(7, 8) == "O"

    savegame.clear_save(path)
    assert savegame.has_save(path) is False
    assert savegame.load_game(Dictionary.demo(), path) is None


def test_load_corrupt_returns_none(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{ pas du json valide", encoding="utf-8")
    assert savegame.load_game(Dictionary.demo(), path) is None
