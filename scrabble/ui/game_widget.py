"""Écran de jeu (plateau / chevalet / barre d'actions) sous forme de widget.

Séparé du menu : `MainWindow` bascule entre `MenuWidget` et `GameWidget` via un
`QStackedWidget`. Le niveau d'IA est choisi dans le menu et passé à `start_game`.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from ..ai import make_ai
from ..core.game import Game
from .board_view import BoardView
from .controller import GameController
from .rack_view import RackView
from .widgets import BagWidget, gold_button, green_button


class GameWidget(QWidget):
    quit_to_menu = Signal()

    def __init__(self, dictionary, definitions, stats) -> None:
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._dictionary = dictionary
        self._definitions = definitions
        self._stats = stats
        self._controller: GameController | None = None

        # -- Bandeau du haut : « MOT : définition » ----------------------
        self._definition = QLabel("")
        self._definition.setWordWrap(True)
        self._definition.setTextFormat(Qt.TextFormat.RichText)
        self._definition.setMinimumHeight(52)
        self._definition.setStyleSheet(
            "background: qlineargradient(x1:0,y1:0,x2:0,y2:1,"
            " stop:0 #3d8fd6, stop:1 #2f76bd);"
            " color:#08243d; padding:10px 14px; font-size:15px;"
        )

        # -- En-tête : bouton Menu + statut ------------------------------
        menu_btn = gold_button("", "Menu")
        menu_btn.clicked.connect(self.quit_to_menu)
        self._status = QLabel("")
        self._status.setStyleSheet("font-weight:bold; color:#123;")
        self._comment = QLabel("")
        self._comment.setStyleSheet("font-style:italic; color:#1c4a6e;")
        header = QHBoxLayout()
        header.setContentsMargins(12, 6, 12, 6)
        header.addWidget(menu_btn)
        header.addStretch(1)
        header.addWidget(self._status)

        self._board_holder = QVBoxLayout()

        # -- Composition : Reprendre / Jouer -----------------------------
        recall_btn = gold_button("↩", "Reprendre")
        play_btn = green_button("Jouer")
        recall_btn.clicked.connect(lambda: self._act("recall"))
        play_btn.clicked.connect(lambda: self._act("commit"))
        compose = QHBoxLayout()
        compose.addStretch(1)
        compose.addWidget(recall_btn)
        compose.addWidget(play_btn)
        compose.addStretch(1)

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
        quit_btn.clicked.connect(self.quit_to_menu)

        bottom = QHBoxLayout()
        bottom.setContentsMargins(12, 6, 12, 6)
        bottom.addLayout(bag_box)
        bottom.addStretch(1)
        for b in (shuffle_btn, exchange_btn, pass_btn, quit_btn):
            bottom.addWidget(b)

        root = QVBoxLayout()
        root.setContentsMargins(0, 0, 0, 8)
        root.addWidget(self._definition)
        root.addLayout(header)
        root.addLayout(self._board_holder, stretch=1)
        root.addWidget(self._comment)
        root.addLayout(compose)
        root.addLayout(self._rack_holder)
        root.addLayout(bottom)
        self.setLayout(root)

    # -- Cycle de vie d'une partie ---------------------------------------
    def start_game(self, level: str) -> None:
        """(Re)démarre une partie avec le niveau d'IA donné (clé interne)."""
        self.shutdown()
        for holder in (self._board_holder, self._rack_holder):
            while holder.count():
                item = holder.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

        game = Game(["Joueur", "Ordinateur"], dictionary=self._dictionary,
                    ai_flags=[False, True])
        ai = make_ai(level)
        if level.startswith("deepseek") and not getattr(ai, "available", True):
            self._comment.setText("Clé DEEPSEEK_API_KEY absente : IA algorithmique.")
        else:
            self._comment.setText("")

        board_view = BoardView(game.board)
        rack_view = RackView()
        self._board_holder.addWidget(board_view)
        self._rack_holder.addWidget(rack_view,
                                    alignment=Qt.AlignmentFlag.AlignHCenter)

        self._controller = GameController(
            game, board_view, rack_view, ai_players={1: ai}, human_index=0,
            definitions=self._definitions, stats=self._stats,
        )
        self._controller.status_changed.connect(self._status.setText)
        self._controller.comment_changed.connect(self._comment.setText)
        self._controller.scores_changed.connect(self._show_scores)
        self._controller.bag_changed.connect(self._bag.set_count)
        self._controller.definition_changed.connect(self._show_definition)
        self._definition.setText("")
        self._controller.start()

    def shutdown(self) -> None:
        if self._controller is not None:
            self._controller.shutdown()

    # -- Affichage --------------------------------------------------------
    def _show_scores(self, scores: list) -> None:
        self._scores.setText("   ".join(f"{name}  {pts}" for name, pts in scores))

    def _show_definition(self, word: str, text: str) -> None:
        if text and text != "…":
            self._definition.setText(f"<b>{word}</b> : {text}")
        elif text == "…":
            self._definition.setText(f"<b>{word}</b> …")
        else:
            self._definition.setText(f"<b>{word}</b> — <i>définition indisponible</i>")

    def _act(self, method: str) -> None:
        if self._controller is not None:
            getattr(self._controller, method)()
