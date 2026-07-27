"""Écran de menu : dictionnaire, niveau, nouvelle partie, statistiques, aide.

Inspiré des menus d'applis de Scrabble : un titre, deux sélecteurs, un gros
bouton d'action, la section « Mes statistiques » (persistées) et un accès à
l'aide. `MenuWidget` émet `start_game(level_key)` quand on lance une partie.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QGridLayout, QHBoxLayout, QLabel, QMessageBox, QVBoxLayout, QWidget,
)

from ..stats import Stats
from .widgets import StyledComboBox, gold_button

# Libellé affiché -> clé interne pour make_ai.
LEVELS = {
    "Facile": "easy",
    "Moyen": "medium",
    "Expert": "hard",
    "DeepSeek (facile)": "deepseek-easy",
    "DeepSeek (moyen)": "deepseek-medium",
    "DeepSeek (expert)": "deepseek-hard",
}

_RULES = (
    "But : marquer le plus de points en formant des mots sur le plateau.\n\n"
    "• Chaque tuile vaut le nombre indiqué en indice.\n"
    "• Cases bonus : LD/LT doublent/triplent une lettre, MD/MT le mot entier.\n"
    "• Le premier mot passe par l'étoile centrale ; les suivants s'y raccordent.\n"
    "• Poser ses 7 tuiles d'un coup = « Scrabble » : +50 points.\n"
    "• Glisse ou clique tes lettres, puis « Jouer ». « Reprendre » annule.\n"
    "• Bloqué ? « Échanger » des lettres ou « Passer » ton tour.\n"
    "• Le joker (tuile vide) prend la lettre de ton choix, pour 0 point."
)


class MenuWidget(QWidget):
    start_game = Signal(str)   # clé de niveau (ex. "medium")
    resume_game = Signal()     # reprendre la partie sauvegardée

    def __init__(self, dictionary_label: str = "Français") -> None:
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        title = QLabel("SCRABBLE")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(
            "font-size:44px; font-weight:800; color:#f7d05c; letter-spacing:2px;"
        )

        self._dict_box = StyledComboBox()
        self._dict_box.addItem(dictionary_label)
        self._level_box = StyledComboBox()
        self._level_box.addItems(LEVELS.keys())
        self._level_box.setCurrentText("Moyen")

        self._resume_btn = gold_button("", "Reprendre ma Partie")
        self._resume_btn.setMinimumHeight(56)
        self._resume_btn.clicked.connect(self.resume_game)
        self._resume_btn.setVisible(False)   # affiché seulement s'il y a une sauvegarde

        play_btn = gold_button("", "Nouvelle partie")
        play_btn.setMinimumHeight(56)
        play_btn.clicked.connect(
            lambda: self.start_game.emit(LEVELS[self._level_box.currentText()])
        )

        help_btn = gold_button("", "Comment jouer")
        help_btn.clicked.connect(self._show_rules)

        # -- Section statistiques ----------------------------------------
        self._stat_values: dict[str, QLabel] = {}
        stats_box = QGridLayout()
        stats_box.setColumnStretch(1, 1)
        stats_title = QLabel("Mes statistiques")
        stats_title.setStyleSheet("font-size:18px; font-weight:bold; color:#0b2a45;")
        rows = ["Victoires", "Score moyen /coup", "Bingos",
                "Meilleur score", "Meilleur mot"]
        for i, name in enumerate(rows):
            label = QLabel(name)
            label.setStyleSheet("color:#123;")
            value = QLabel("—")
            value.setStyleSheet("font-weight:bold; color:#0b2a45;")
            stats_box.addWidget(label, i, 0)
            stats_box.addWidget(value, i, 1)
            self._stat_values[name] = value

        # -- Assemblage ---------------------------------------------------
        root = QVBoxLayout()
        root.setContentsMargins(28, 24, 28, 24)
        root.addWidget(title)
        root.addSpacing(18)
        root.addWidget(self._field("Dictionnaire", self._dict_box))
        root.addWidget(self._field("Niveau", self._level_box))
        root.addSpacing(6)
        root.addWidget(self._resume_btn)
        root.addWidget(play_btn)
        root.addSpacing(20)
        root.addWidget(stats_title)
        root.addLayout(stats_box)
        root.addStretch(1)
        root.addWidget(help_btn)
        self.setLayout(root)

    @staticmethod
    def _field(label: str, widget: QWidget) -> QWidget:
        box = QVBoxLayout()
        box.setContentsMargins(0, 0, 0, 0)
        title = QLabel(label)
        title.setStyleSheet("font-size:16px; font-weight:bold; color:#0b2a45;")
        box.addWidget(title)
        box.addWidget(widget)
        holder = QWidget()
        holder.setLayout(box)
        return holder

    def set_can_resume(self, can_resume: bool) -> None:
        """Affiche « Reprendre ma Partie » seulement si une sauvegarde existe."""
        self._resume_btn.setVisible(can_resume)

    def refresh_stats(self, stats: Stats) -> None:
        """Met à jour l'affichage depuis l'objet Stats (après chaque partie)."""
        v = self._stat_values
        v["Victoires"].setText(
            f"{stats.games_won}/{stats.games_played} "
            f"({stats.win_rate * 100:.1f}%)" if stats.games_played else "—"
        )
        v["Score moyen /coup"].setText(
            f"{stats.avg_score_per_move:.2f}" if stats.total_moves else "—"
        )
        v["Bingos"].setText(str(stats.bingos))
        v["Meilleur score"].setText(str(stats.best_game_score))
        v["Meilleur mot"].setText(
            f"{stats.best_word_points} | {stats.best_word}" if stats.best_word else "—"
        )

    def _show_rules(self) -> None:
        QMessageBox.information(self, "Comment jouer", _RULES)
