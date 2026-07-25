"""Fenêtre principale : bascule entre l'écran de **menu** et l'écran de **jeu**.

Le menu (dictionnaire, niveau, statistiques) lance une partie ; le jeu revient
au menu via « Menu » ou « Quitter ». Les statistiques sont persistées entre les
parties et rafraîchies au retour au menu.
"""

from __future__ import annotations

from PySide6.QtWidgets import QMainWindow, QStackedWidget

from .. import savegame
from ..core.dictionary import Dictionary
from ..definitions import Definitions
from ..stats import Stats
from . import theme
from .game_widget import GameWidget
from .menu import MenuWidget

_WINDOW_QSS = f"""
QMainWindow, QStackedWidget, MenuWidget, GameWidget {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 {theme.WINDOW_TOP.name()}, stop:1 {theme.WINDOW_BOTTOM.name()});
}}
QLabel {{ color: #123; }}
QComboBox {{
    background: white; border: 1px solid #9db6c8; border-radius: 6px;
    padding: 6px 8px; font-size: 15px;
}}
"""


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Scrabble")
        self.setStyleSheet(_WINDOW_QSS)

        self._dictionary = Dictionary.load_default()
        self._definitions = Definitions.load_default()
        self._stats = Stats.load()

        self._stack = QStackedWidget()
        self._menu = MenuWidget(dictionary_label="Français")
        self._game = GameWidget(self._dictionary, self._definitions, self._stats)
        self._stack.addWidget(self._menu)
        self._stack.addWidget(self._game)
        self.setCentralWidget(self._stack)

        self._menu.start_game.connect(self._start_game)
        self._menu.resume_game.connect(self._resume_game)
        self._game.quit_to_menu.connect(self._back_to_menu)

        self._show_menu()
        self.resize(720, 1040)

    def _show_menu(self) -> None:
        self._menu.refresh_stats(self._stats)
        self._menu.set_can_resume(savegame.has_save())
        self._stack.setCurrentWidget(self._menu)

    def _start_game(self, level: str) -> None:
        self._game.start_game(level)
        self._stack.setCurrentWidget(self._game)

    def _resume_game(self) -> None:
        loaded = savegame.load_game(self._dictionary)
        if loaded is None:
            self._show_menu()          # sauvegarde illisible : on reste au menu
            return
        game, level = loaded
        self._game.resume_game(game, level)
        self._stack.setCurrentWidget(self._game)

    def _back_to_menu(self) -> None:
        self._game.shutdown()
        self._show_menu()              # stats + bouton reprise à jour

    def closeEvent(self, event) -> None:  # noqa: N802 (API Qt)
        self._game.shutdown()
        super().closeEvent(event)


def run() -> int:
    """Point d'entrée de l'application graphique."""
    import sys
    from PySide6.QtWidgets import QApplication

    from ..config import load_env_files
    load_env_files()   # récupère DEEPSEEK_API_KEY depuis .env.local si présent

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()
