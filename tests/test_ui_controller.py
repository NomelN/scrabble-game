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


def test_move_shows_score_badge_and_definition(qapp):
    from scrabble.definitions import Definitions
    game = Game(["Toi", "Ordi"], dictionary=Dictionary.demo(),
                ai_flags=[False, True], seed=3)
    game.players[0].rack.tiles = list("MOTABCE")
    board_view = BoardView(game.board)
    rack_view = RackView()
    # Définitions locales déterministes (aucun réseau).
    defs = Definitions(local={"MOT": "suite de lettres"}, api_key=None)
    captured = []
    controller = GameController(game, board_view, rack_view,
                                ai_players={1: make_ai("easy")}, human_index=0,
                                definitions=defs)
    controller.sync_ai = True
    controller.definition_changed.connect(lambda w, t: captured.append((w, t)))
    controller.start()

    for i, (r, c) in enumerate([(7, 7), (7, 8), (7, 9)]):
        rack_view.select(i)
        controller.place_at(r, c)
    controller.commit()

    # Badge de score affiché sur le plateau.
    assert board_view._badge_items, "le badge de score doit être affiché"
    # Définition (locale) émise pour le mot joué.
    assert ("MOT", "suite de lettres") in captured


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


def test_drag_pixmap_matches_board_scale(qapp):
    """L'image de glisser du chevalet est dimensionnée à la case du plateau
    (sinon le fantôme déborde sur les cases voisines → chevauchement visuel)."""
    game, board_view, rack_view, controller = _fresh(qapp, letters="MARELLE")
    board_view.resize(560, 560)
    board_view.show()
    qapp.processEvents()
    provider = rack_view._cell_size_provider
    assert provider is not None
    size = provider()
    assert isinstance(size, int) and size > 0
    assert size == board_view.screen_cell_size()


def test_marelle_all_seven_tiles_place_distinctly(qapp):
    """Deux L et deux E (MARELLE) se posent sur 7 cases distinctes, sans conflit."""
    game, board_view, rack_view, controller = _fresh(qapp, letters="MARELLE")
    for idx, col in enumerate(range(4, 11)):
        controller.place_index_at(7, col, idx)
    assert controller.pending_count == 7
    assert len(controller.placed_cells) == 7          # aucune case en double
    assert board_view.has_pending_at(7, 8) and board_view.has_pending_at(7, 9)  # les 2 L


def test_rack_reorder(qapp):
    game, board_view, rack_view, controller = _fresh(qapp, letters="ABCDEFG")
    before = [s.letter for s in controller._slots]
    controller.reorder(0, 3)                           # déplace 'A' en position 3
    after = [s.letter for s in controller._slots]
    assert after != before
    assert set(after) == set(before)                   # mêmes lettres, ordre changé
    assert after[3] == "A"


def test_threaded_ai_turn_completes_without_crash(qapp):
    """Le tour de l'IA en mode threadé (worker QRunnable) se termine proprement,
    et couper la partie en plein calcul ne fait pas planter (garde anti-segfault)."""
    from PySide6.QtCore import QEventLoop, QTimer
    game, board_view, rack_view, controller = _fresh(qapp, letters="MOTABCE")
    controller.sync_ai = False              # passe par le thread

    for i, (r, c) in enumerate([(7, 7), (7, 8), (7, 9)]):
        rack_view.select(i)
        controller.place_at(r, c)
    controller.commit()                     # déclenche le tour IA threadé

    # Laisse le worker + ses callbacks s'exécuter sur la boucle d'événements.
    loop = QEventLoop()
    QTimer.singleShot(800, loop.quit)
    loop.exec()

    assert any(e.player == 1 for e in game.events)   # l'IA a bien joué
    # Couper la partie pendant/aprés le thread ne doit rien casser.
    controller.shutdown()
    QTimer.singleShot(50, loop.quit)
    loop.exec()
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


def test_resumed_game_renders_existing_tiles(qapp):
    """Au démarrage, le contrôleur réaffiche les tuiles déjà posées (reprise)."""
    from scrabble.core.board import Placement
    game = Game(["Toi", "Ordi"], dictionary=Dictionary.demo(),
                ai_flags=[False, True], seed=1)
    game.players[0].rack.tiles = list("MOTABCE")
    game.play([Placement(7, 7, "M"), Placement(7, 8, "O"), Placement(7, 9, "T")])
    board_view = BoardView(game.board)
    rack_view = RackView()
    controller = GameController(game, board_view, rack_view,
                                ai_players={1: make_ai("easy")}, human_index=0)
    controller.sync_ai = True
    controller.start()
    for cell in [(7, 7), (7, 8), (7, 9)]:
        assert cell in board_view._tiles


def test_exchange_by_indices(qapp):
    """Échanger des tuiles précises du chevalet (via la boîte d'échange)."""
    game, board_view, rack_view, controller = _fresh(qapp, letters="MOTABCE")
    controller.exchange_by_indices([0, 1])          # échange M, O
    assert any(e.type == EventType.EXCHANGED for e in game.events)
    assert len(game.players[0].rack.tiles) == 7     # main complète après échange


def test_exchange_dialog_selection(qapp):
    from scrabble.ui.dialogs import ExchangeDialog
    dlg = ExchangeDialog(None, list("MOTABCE"))
    assert len(dlg._buttons) == 7
    dlg._buttons[0].setChecked(True)
    dlg._buttons[3].setChecked(True)
    assert dlg.selected_indices() == [0, 3]
