"""Écran de jeu (plateau / chevalet / barre d'actions) sous forme de widget.

Séparé du menu : `MainWindow` bascule entre `MenuWidget` et `GameWidget` via un
`QStackedWidget`. Le niveau d'IA est choisi dans le menu et passé à `start_game`.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from .. import savegame
from ..ai import make_ai
from ..core.game import Game
from .board_view import BoardView
from .controller import GameController
from .dialogs import (
    ConfirmDialog, EndGameSummaryDialog, ExchangeDialog, GameOverDialog,
)
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
        self._level = "medium"

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
        exchange_btn.clicked.connect(self._on_exchange)
        pass_btn.clicked.connect(self._on_pass)
        quit_btn.clicked.connect(self._on_quit)

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
        """Démarre une nouvelle partie avec le niveau d'IA donné (clé interne)."""
        game = Game(["Joueur", "Ordinateur"], dictionary=self._dictionary,
                    ai_flags=[False, True])
        self._install(game, level)

    def resume_game(self, game: Game, level: str) -> None:
        """Reprend une partie sauvegardée (état déjà restauré dans `game`)."""
        self._install(game, level)

    def _install(self, game: Game, level: str) -> None:
        self.shutdown()
        self._level = level
        for holder in (self._board_holder, self._rack_holder):
            while holder.count():
                item = holder.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

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
        self._controller.turn_finished.connect(self._on_turn_finished)
        self._controller.game_over.connect(self._on_game_over)
        self._definition.setText("")
        self._controller.start()
        self._save_state()             # sauvegarde l'état initial (reprise possible)

    def _on_turn_finished(self) -> None:
        if self._controller is None:
            return
        if self._controller.game.is_over:
            savegame.clear_save()      # plus rien à reprendre
        else:
            self._save_state()

    def _on_game_over(self, details: dict) -> None:
        """Fin de partie : diffère l'affichage pour laisser le tour se dénouer
        proprement (le signal est émis au milieu de `_after_turn`)."""
        savegame.clear_save()          # partie terminée : plus rien à reprendre
        QTimer.singleShot(0, lambda: self._show_game_over(details))

    def _show_game_over(self, details: dict) -> None:
        EndGameSummaryDialog.show_summary(self, details)
        choice = GameOverDialog.ask(self, details)
        if choice == GameOverDialog.REPLAY:
            self.start_game(self._level)
        elif choice == GameOverDialog.QUIT:
            self.quit_to_menu.emit()
        # « Plateau » : on ferme les dialogues et on laisse le plateau visible.

    def _save_state(self) -> None:
        if self._controller is not None and not self._controller.game.is_over:
            savegame.save_game(self._controller.game, self._level)

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

    # -- Dialogues (échanger / passer / quitter) -------------------------
    def _on_exchange(self) -> None:
        if self._controller is None:
            return
        selected = ExchangeDialog.get_selection(self, self._controller.rack_letters())
        if selected:
            self._controller.exchange_by_indices(selected)

    def _on_pass(self) -> None:
        if self._controller is None:
            return
        if ConfirmDialog.ask(self, "Passer ?", "Voulez-vous vraiment passer votre tour ?"):
            self._controller.pass_turn()

    def _on_quit(self) -> None:
        if ConfirmDialog.ask(self, "Quitter",
                             "Effacer cette partie et revenir au menu principal ?"):
            savegame.clear_save()      # « Quitter » abandonne la partie
            self.quit_to_menu.emit()
