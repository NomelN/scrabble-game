"""Fenêtre principale — disposition verticale (plateau / chevalet / barre d'actions),
au style de la maquette : tuiles bois dorées, cases bonus colorées, fond bleu clair.

Le joueur humain (index 0) compose ses coups au clic ou au glisser-déposer ;
l'IA (index 1) joue automatiquement. Niveau d'IA réglable, DeepSeek compris.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox, QHBoxLayout, QLabel, QMainWindow, QVBoxLayout, QWidget,
)

from ..ai import make_ai
from ..core.dictionary import Dictionary
from ..core.game import Game
from . import theme
from .board_view import BoardView
from .controller import GameController
from .rack_view import RackView
from .widgets import BagWidget, gold_button, green_button

_LEVELS = {
    "Facile": "easy",
    "Moyen": "medium",
    "Expert": "hard",
    "DeepSeek (facile)": "deepseek-easy",
    "DeepSeek (moyen)": "deepseek-medium",
    "DeepSeek (expert)": "deepseek-hard",
}

_WINDOW_QSS = f"""
QMainWindow, QWidget#root {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 {theme.WINDOW_TOP.name()}, stop:1 {theme.WINDOW_BOTTOM.name()});
}}
QLabel {{ color: #123; }}
QComboBox {{
    background: white; border: 1px solid #9db6c8; border-radius: 6px; padding: 3px 6px;
}}
"""


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Scrabble")
        self.setStyleSheet(_WINDOW_QSS)
        self._dictionary = Dictionary.load_default()
        self._controller: GameController | None = None
        self._board_view: BoardView | None = None
        self._rack_view: RackView | None = None

        # -- En-tête : niveau IA + nouvelle partie + statut ---------------
        self._level_box = QComboBox()
        self._level_box.addItems(_LEVELS.keys())
        self._level_box.setCurrentText("Moyen")
        new_btn = gold_button("", "Nouvelle partie")
        new_btn.clicked.connect(self._new_game)

        self._status = QLabel("")
        self._status.setStyleSheet("font-weight:bold; color:#123;")
        self._comment = QLabel("")
        self._comment.setStyleSheet("font-style:italic; color:#1c4a6e;")

        header = QHBoxLayout()
        header.addWidget(QLabel("IA :"))
        header.addWidget(self._level_box)
        header.addWidget(new_btn)
        header.addStretch(1)
        header.addWidget(self._status)

        # -- Zone plateau (remplie dans _new_game) -----------------------
        self._board_holder = QVBoxLayout()

        # -- Composition : Reprendre / Jouer -----------------------------
        self._recall_btn = gold_button("↩", "Reprendre")
        self._play_btn = green_button("Jouer")
        self._recall_btn.clicked.connect(lambda: self._act("recall"))
        self._play_btn.clicked.connect(lambda: self._act("commit"))
        compose = QHBoxLayout()
        compose.addStretch(1)
        compose.addWidget(self._recall_btn)
        compose.addWidget(self._play_btn)
        compose.addStretch(1)

        # -- Chevalet (rempli dans _new_game) ----------------------------
        self._rack_holder = QVBoxLayout()

        # -- Barre du bas : sac + scores + actions -----------------------
        self._bag = BagWidget()
        self._scores = QLabel("")
        self._scores.setStyleSheet("color:#123; font-weight:bold;")
        bag_box = QHBoxLayout()
        bag_box.addWidget(self._bag)
        bag_box.addWidget(self._scores)

        shuffle_btn = gold_button("⟳", "Mélanger")
        exchange_btn = gold_button("⇅", "Échanger")
        pass_btn = gold_button("⏭", "Passer")
        quit_btn = gold_button("⏻", "Quitter")
        shuffle_btn.clicked.connect(lambda: self._act("shuffle_rack"))
        exchange_btn.clicked.connect(lambda: self._act("exchange_selected"))
        pass_btn.clicked.connect(lambda: self._act("pass_turn"))
        quit_btn.clicked.connect(self.close)

        bottom = QHBoxLayout()
        bottom.addLayout(bag_box)
        bottom.addStretch(1)
        for b in (shuffle_btn, exchange_btn, pass_btn, quit_btn):
            bottom.addWidget(b)

        # -- Assemblage vertical -----------------------------------------
        root = QVBoxLayout()
        root.addLayout(header)
        root.addLayout(self._board_holder, stretch=1)
        root.addWidget(self._comment)
        root.addLayout(compose)
        root.addLayout(self._rack_holder)
        root.addLayout(bottom)

        container = QWidget()
        container.setObjectName("root")
        container.setLayout(root)
        self.setCentralWidget(container)
        self.resize(720, 1040)

        self._new_game()

    # -- Construction d'une partie ---------------------------------------
    def _new_game(self) -> None:
        for holder in (self._board_holder, self._rack_holder):
            while holder.count():
                item = holder.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

        game = Game(["Joueur", "Ordinateur"], dictionary=self._dictionary,
                    ai_flags=[False, True])
        level = _LEVELS[self._level_box.currentText()]
        ai = make_ai(level)
        if level.startswith("deepseek") and not getattr(ai, "available", True):
            self._comment.setText("Clé DEEPSEEK_API_KEY absente : IA algorithmique.")
        else:
            self._comment.setText("")

        self._board_view = BoardView(game.board)
        self._rack_view = RackView()
        self._board_holder.addWidget(self._board_view)
        self._rack_holder.addWidget(self._rack_view,
                                    alignment=Qt.AlignmentFlag.AlignHCenter)

        self._controller = GameController(
            game, self._board_view, self._rack_view, ai_players={1: ai}, human_index=0,
        )
        self._controller.status_changed.connect(self._status.setText)
        self._controller.comment_changed.connect(self._comment.setText)
        self._controller.scores_changed.connect(self._show_scores)
        self._controller.bag_changed.connect(self._bag.set_count)
        self._controller.start()

    def _show_scores(self, scores: list) -> None:
        self._scores.setText(
            "   ".join(f"{name}  {pts}" for name, pts in scores)
        )

    # -- Boutons ----------------------------------------------------------
    def _act(self, method: str) -> None:
        if self._controller is not None:
            getattr(self._controller, method)()


def run() -> int:
    """Point d'entrée de l'application graphique."""
    import sys
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()
