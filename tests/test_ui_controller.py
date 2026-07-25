"""Test d'intégration du branchement UI ↔ partie ↔ IA (mode headless).

On force la plateforme Qt « offscreen » : aucune fenêtre n'est réellement
affichée, mais toute la logique de contrôle et les animations s'exécutent.
"""

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

QtWidgets = pytest.importorskip("PySide6.QtWidgets")

from scrabble.ai import make_ai
from scrabble.core.dictionary import Dictionary
from scrabble.core.game import EventType, Game
from scrabble.ui.board_view import BoardView
from scrabble.ui.controller import GameController
from scrabble.ui.rack_view import RackView


@pytest.fixture(scope="module")
def qapp():
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    yield app


def test_human_plays_then_ai_responds(qapp):
    game = Game(["Toi", "Ordi"], dictionary=Dictionary.demo(),
                ai_flags=[False, True], seed=3)
    game.players[0].rack.tiles = list("MOTABCE")

    board_view = BoardView(game.board)
    rack_view = RackView()
    ai = make_ai("medium", seed=3)
    controller = GameController(game, board_view, rack_view,
                                ai_players={1: ai}, human_index=0)
    controller.sync_ai = True   # l'IA jouera sans thread
    controller.start()

    # L'humain compose « MOT » sur la ligne centrale.
    for i, (r, c) in enumerate([(7, 7), (7, 8), (7, 9)]):
        rack_view.select(i)
        controller.place_at(r, c)
    assert controller.pending_count == 3

    controller.commit()

    # Le coup humain a marqué des points et un événement a été émis.
    assert game.players[0].score > 0
    assert any(e.type == EventType.MOVE_PLAYED and e.player == 0
               for e in game.events)

    # L'IA a joué à son tour (un événement pour le joueur 1 existe), et la main
    # est revenue à l'humain (ou la partie est finie).
    assert any(e.player == 1 for e in game.events)
    assert game.current == 0 or game.is_over


def test_placed_letter_disappears_from_rack(qapp):
    game = Game(["Toi", "Ordi"], dictionary=Dictionary.demo(),
                ai_flags=[False, True], seed=3)
    game.players[0].rack.tiles = list("MOTABCE")

    board_view = BoardView(game.board)
    rack_view = RackView()
    controller = GameController(game, board_view, rack_view,
                                ai_players={1: make_ai("easy")}, human_index=0)
    controller.start()

    # Pose via glisser-déposer (chemin `place_index_at`, indice 0 = 'M').
    controller.place_index_at(7, 7, 0)
    assert (7, 7) in controller.placed_cells
    assert 0 in rack_view._used            # la case du chevalet est vidée

    # « Reprendre » la fait réapparaître.
    controller.recall()
    assert rack_view._used == set()


def test_blank_tile_is_resolved_to_a_letter(qapp):
    game = Game(["Toi", "Ordi"], dictionary=Dictionary.demo(),
                ai_flags=[False, True], seed=3)
    game.players[0].rack.tiles = list("M?TABCE")  # index 1 = joker

    board_view = BoardView(game.board)
    rack_view = RackView()
    controller = GameController(
        game, board_view, rack_view, ai_players={1: make_ai("easy")},
        human_index=0, blank_resolver=lambda: "O",   # le joker devient un 'O'
    )
    controller.sync_ai = True
    controller.start()

    for idx, (r, c) in zip((0, 1, 2), [(7, 7), (7, 8), (7, 9)]):
        rack_view.select(idx)
        controller.place_at(r, c)
    controller.commit()

    # « MOT » validé ; le joker (O) vaut 0 → M(2)+O(0)+T(1) = 3, ×2 (centre) = 6.
    assert any(e.type == EventType.MOVE_PLAYED and e.payload["result"].main_word == "MOT"
               for e in game.events)
    assert game.players[0].score == 6


def _fresh(qapp, letters="MOTABCE", seed=3):
    game = Game(["Toi", "Ordi"], dictionary=Dictionary.demo(),
                ai_flags=[False, True], seed=seed)
    game.players[0].rack.tiles = list(letters)
    board_view = BoardView(game.board)
    rack_view = RackView()
    controller = GameController(game, board_view, rack_view,
                                ai_players={1: make_ai("easy")}, human_index=0)
    controller.sync_ai = True
    controller.start()
    return game, board_view, rack_view, controller


def test_placed_tile_can_be_moved(qapp):
    game, board_view, rack_view, controller = _fresh(qapp)
    controller.place_index_at(7, 7, 0)                 # pose 'M' au centre
    assert (7, 7) in controller.placed_cells
    controller.move_pending(7, 7, 7, 9)                # déplace vers (7,9)
    assert (7, 9) in controller.placed_cells
    assert (7, 7) not in controller.placed_cells
    assert board_view.has_pending_at(7, 9)
    assert not board_view.has_pending_at(7, 7)


def test_placed_tile_can_return_to_rack(qapp):
    game, board_view, rack_view, controller = _fresh(qapp)
    controller.place_index_at(7, 7, 0)
    assert controller.pending_count == 1
    controller.return_to_rack(7, 7, 0)                 # ramène au chevalet
    assert controller.pending_count == 0
    assert not board_view.has_pending_at(7, 7)
    assert rack_view._used == set()                    # plus aucune case vidée


def test_rack_mapping_has_no_centering_offset(qapp):
    """La scène du chevalet est ancrée à gauche : x_écran == x_scène, donc
    l'index d'une tuile == sa position visible (corrige le bug des doublons)."""
    from PySide6.QtCore import QPoint
    rack = RackView()
    rack.setGeometry(0, 0, 640, 60)
    rack.resize(640, 60)
    rack.set_letters(list("OEOGIGA"))
    rack.show()
    qapp.processEvents()
    for x in (25, 125, 325):
        assert abs(rack.mapToScene(QPoint(x, 0)).x() - x) < 1.0


def test_duplicate_letters_only_one_hidden(qapp):
    """Poser UN exemplaire d'une lettre en double ne masque QUE celui-ci."""
    game, board_view, rack_view, controller = _fresh(qapp, letters="OEOGIGA")
    # Pose un seul O (index 0) et un seul G (index 3).
    controller.place_index_at(7, 7, 0)
    controller.place_index_at(7, 8, 3)
    assert rack_view._used == {0, 3}                 # seuls ces deux masqués
    visibles = [s.letter for i, s in enumerate(controller._slots)
                if i not in rack_view._used]
    assert visibles == ["E", "O", "I", "G", "A"]     # l'autre O et l'autre G restent
    assert len(visibles) == 5


def test_rack_reorder(qapp):
    game, board_view, rack_view, controller = _fresh(qapp, letters="ABCDEFG")
    before = [s.letter for s in controller._slots]
    controller.reorder(0, 3)                           # déplace 'A' en position 3
    after = [s.letter for s in controller._slots]
    assert after != before
    assert set(after) == set(before)                   # mêmes lettres, ordre changé
    assert after[3] == "A"


def test_illegal_move_is_reverted(qapp):
    game = Game(["Toi", "Ordi"], dictionary=Dictionary.demo(),
                ai_flags=[False, True], seed=5)
    game.players[0].rack.tiles = list("XYZABCE")

    board_view = BoardView(game.board)
    rack_view = RackView()
    controller = GameController(game, board_view, rack_view,
                                ai_players={1: make_ai("easy")}, human_index=0)
    controller.sync_ai = True
    controller.start()

    # « XYZ » n'est pas dans le lexique démo → coup refusé.
    for i, (r, c) in enumerate([(7, 7), (7, 8), (7, 9)]):
        rack_view.select(i)
        controller.place_at(r, c)
    controller.commit()

    assert game.players[0].score == 0        # rien marqué
    # Les tuiles restent posées pour être corrigées (on ne perd pas le coup).
    assert controller.pending_count == 3
    assert game.current == 0                 # toujours au tour de l'humain
