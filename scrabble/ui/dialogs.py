"""Dialogues stylés : confirmation (Passer / Quitter) et échange de lettres.

Look de la maquette : carte blanche arrondie centrée sur un fond assombri, deux
boutons dorés « Annuler » / « Confirmer ».
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton, QVBoxLayout,
    QWidget,
)

from ..core.tiles import BLANK, letter_value
from .widgets import gold_button, green_button

_OVERLAY_QSS = "#overlay { background: rgba(8, 20, 32, 0.55); }"
_CARD_QSS = "#card { background: white; border-radius: 18px; }"

# Chiffres en indice pour afficher la valeur des tuiles (E₁, D₂, …).
_SUB = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")

_TILE_QSS = """
QPushButton {
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #f8d15c, stop:1 #eaa62a);
    border: 1px solid #c6871a; border-radius: 8px;
    color: #1c1c1c; font-size: 22px; font-weight: bold;
    min-width: 48px; min-height: 56px;
}
QPushButton:checked {
    border: 3px solid #2f76bd;
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #ffe07a, stop:1 #f2b23c);
}
"""

# Tuile décorative (non cliquable), pour l'écran de fin de partie.
_TILE_LABEL_QSS = """
QLabel {
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #f8d15c, stop:1 #eaa62a);
    border: 1px solid #c6871a; border-radius: 8px;
    color: #1c1c1c; font-size: 22px; font-weight: bold;
}
"""


def _tile_label(letter: str) -> QLabel:
    """Petite tuile décorative affichant une lettre et sa valeur (E₁, F₄, …)."""
    value = letter_value(letter)
    text = ("" if letter == BLANK else letter.upper())
    if value:
        text += str(value).translate(_SUB)
    label = QLabel(text or " ")
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    label.setFixedSize(48, 56)
    label.setStyleSheet(_TILE_LABEL_QSS)
    return label


class _OverlayDialog(QDialog):
    """Dialogue plein écran (assombri) avec une carte blanche centrée."""

    def __init__(self, parent) -> None:
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setModal(True)

        self._overlay = QWidget(self)
        self._overlay.setObjectName("overlay")
        self._overlay.setStyleSheet(_OVERLAY_QSS)

        self._card = QWidget()
        self._card.setObjectName("card")
        self._card.setStyleSheet(_CARD_QSS)
        self._card.setMaximumWidth(460)

        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(self._card)
        row.addStretch(1)
        overlay_layout = QVBoxLayout(self._overlay)
        overlay_layout.addStretch(1)
        overlay_layout.addLayout(row)
        overlay_layout.addStretch(1)

        self._card_layout = QVBoxLayout(self._card)
        self._card_layout.setContentsMargins(24, 20, 24, 20)
        self._card_layout.setSpacing(14)

    def showEvent(self, event) -> None:  # noqa: N802 (API Qt)
        parent = self.parentWidget()
        if parent is not None:
            self.setGeometry(parent.window().geometry())
        self._overlay.setGeometry(0, 0, self.width(), self.height())
        super().showEvent(event)

    # -- Blocs réutilisables ---------------------------------------------
    def _add_title(self, text: str) -> None:
        title = QLabel(text)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size:22px; font-weight:bold; color:#333;")
        self._card_layout.addWidget(title)
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color:#d0d0d0;")
        self._card_layout.addWidget(line)

    def _add_message(self, text: str) -> None:
        msg = QLabel(text)
        msg.setWordWrap(True)
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg.setStyleSheet("font-size:16px; color:#333;")
        self._card_layout.addWidget(msg)

    def _add_buttons(self) -> None:
        cancel = gold_button("", "Annuler")
        confirm = gold_button("", "Confirmer")
        cancel.clicked.connect(self.reject)
        confirm.clicked.connect(self.accept)
        row = QHBoxLayout()
        row.setSpacing(14)
        row.addWidget(cancel)
        row.addWidget(confirm)
        self._card_layout.addSpacing(6)
        self._card_layout.addLayout(row)


class ConfirmDialog(_OverlayDialog):
    def __init__(self, parent, title: str, message: str) -> None:
        super().__init__(parent)
        self._add_title(title)
        self._card_layout.addSpacing(6)
        self._add_message(message)
        self._card_layout.addSpacing(6)
        self._add_buttons()

    @classmethod
    def ask(cls, parent, title: str, message: str) -> bool:
        return cls(parent, title, message).exec() == QDialog.DialogCode.Accepted


class ExchangeDialog(_OverlayDialog):
    def __init__(self, parent, letters: list[str]) -> None:
        super().__init__(parent)
        self._buttons: list[QPushButton] = []
        self._add_title("Échanger des lettres")
        self._add_message("Touchez les lettres que vous souhaitez échanger :")

        tiles = QHBoxLayout()
        tiles.setSpacing(6)
        tiles.addStretch(1)
        for letter in letters:
            button = self._tile_button(letter)
            tiles.addWidget(button)
            self._buttons.append(button)
        tiles.addStretch(1)
        self._card_layout.addSpacing(6)
        self._card_layout.addLayout(tiles)
        self._card_layout.addSpacing(6)
        self._add_buttons()

    @staticmethod
    def _tile_button(letter: str) -> QPushButton:
        value = letter_value(letter)
        label = ("" if letter == "?" else letter.upper())
        if value:
            label += str(value).translate(_SUB)
        button = QPushButton(label or " ")
        button.setCheckable(True)
        button.setStyleSheet(_TILE_QSS)
        return button

    def selected_indices(self) -> list[int]:
        return [i for i, b in enumerate(self._buttons) if b.isChecked()]

    @classmethod
    def get_selection(cls, parent, letters: list[str]) -> list[int] | None:
        dialog = cls(parent, letters)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return dialog.selected_indices()
        return None


class BlankLetterDialog(_OverlayDialog):
    """Choix de la lettre représentée par un joker (« tuile neutre »).

    Remplace le `QInputDialog` natif par une grille de tuiles A–Z au look de
    l'appli : on touche la lettre voulue, ce qui valide directement.
    """

    _COLUMNS = 6

    def __init__(self, parent) -> None:
        super().__init__(parent)
        self._chosen: str | None = None
        self._card.setMaximumWidth(400)
        self._add_title("Choisir une lettre")
        self._add_message("Ce joker représentera la lettre :")

        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(8)
        for i in range(26):
            letter = chr(ord("A") + i)
            button = QPushButton(letter)
            button.setStyleSheet(_TILE_QSS)
            button.setMinimumSize(44, 52)
            button.clicked.connect(lambda _=False, l=letter: self._pick(l))
            grid.addWidget(button, i // self._COLUMNS, i % self._COLUMNS)
        self._card_layout.addSpacing(6)
        self._card_layout.addLayout(grid)

        cancel = gold_button("", "Annuler")
        cancel.clicked.connect(self.reject)
        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(cancel)
        row.addStretch(1)
        self._card_layout.addSpacing(6)
        self._card_layout.addLayout(row)

    def _pick(self, letter: str) -> None:
        self._chosen = letter
        self.accept()

    @classmethod
    def get_letter(cls, parent) -> str | None:
        dialog = cls(parent)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return dialog._chosen
        return None


class EndGameSummaryDialog(_OverlayDialog):
    """Récapitulatif du décompte final : qui a fini, tuiles restantes, scores.

    Réplique la maquette « L'iPhone a fini en premier » : titre, tuiles
    restantes de l'adversaire, puis les scores finaux avec l'ajustement
    (par ex. « Joueur : 343 (350 - 7) »).
    """

    def __init__(self, parent, details: dict) -> None:
        super().__init__(parent)
        names = details["names"]
        finisher = details["finisher"]
        remaining = details["remaining"]
        human = details["human_index"]

        if finisher is None:
            self._add_title("Partie bloquée")
            self._card_layout.addSpacing(6)
            self._add_message("Six tours sans marquer : la partie s'arrête.")
            # On montre les tuiles encore en main de chaque joueur.
            for i, name in enumerate(names):
                if remaining[i]:
                    self._add_message(f"Il restait à {name} :")
                    self._add_tiles(remaining[i])
        else:
            self._add_title(f"{names[finisher]} a fini en premier")
            self._card_layout.addSpacing(6)
            # Tuiles restantes des adversaires (celles qui pèsent sur le score).
            others = [i for i in range(len(names)) if i != finisher and remaining[i]]
            for i in others:
                lead = ("Il vous restait les lettres suivantes quand "
                        f"{names[finisher]} a terminé :"
                        if i == human
                        else f"Il restait à {names[i]} les lettres suivantes :")
                self._add_message(lead)
                self._add_tiles(remaining[i])
            if not others:
                self._add_message(f"{names[finisher]} a posé toutes ses lettres.")

        self._card_layout.addSpacing(6)
        self._add_message("Scores finaux :")
        self._add_scoreboard(details)
        self._card_layout.addSpacing(6)
        self._add_ok_button()

    def _add_tiles(self, letters: list[str]) -> None:
        row = QHBoxLayout()
        row.setSpacing(8)
        row.addStretch(1)
        for letter in letters:
            row.addWidget(_tile_label(letter))
        row.addStretch(1)
        self._card_layout.addLayout(row)

    def _add_scoreboard(self, details: dict) -> None:
        names = details["names"]
        before = details["scores_before"]
        after = details["scores_after"]
        lines = []
        for i, name in enumerate(names):
            delta = after[i] - before[i]
            if delta > 0:
                adj = f"({before[i]} + {delta})"
            elif delta < 0:
                adj = f"({before[i]} - {abs(delta)})"
            else:
                adj = f"({before[i]})"
            lines.append(f"{name} : {after[i]} {adj}")
        board = QLabel("\n".join(lines))
        board.setAlignment(Qt.AlignmentFlag.AlignCenter)
        board.setStyleSheet("font-size:17px; color:#333;")
        self._card_layout.addWidget(board)

    def _add_ok_button(self) -> None:
        ok = gold_button("", "OK")
        ok.clicked.connect(self.accept)
        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(ok)
        row.addStretch(1)
        self._card_layout.addSpacing(6)
        self._card_layout.addLayout(row)

    @classmethod
    def show_summary(cls, parent, details: dict) -> None:
        cls(parent, details).exec()


class GameOverDialog(_OverlayDialog):
    """« Partie terminée » : annonce le gagnant et propose Rejouer / Plateau / Quitter."""

    REPLAY = "replay"
    BOARD = "board"
    QUIT = "quit"

    def __init__(self, parent, details: dict) -> None:
        super().__init__(parent)
        self._choice = self.BOARD          # fermer la carte = voir le plateau
        names = details["names"]
        winner = details["winner"]
        human = details["human_index"]

        self._add_title("Partie terminée")
        self._card_layout.addSpacing(6)
        if winner is None:
            headline = "Match nul !"
        elif winner == human:
            headline = "Vous avez gagné ! 🎉"
        else:
            headline = f"{names[winner]} a gagné."
        self._add_message(headline)
        self._add_message("Une petite revanche 😉 ?")
        self._card_layout.addSpacing(6)
        self._add_choice_buttons()

    def _add_choice_buttons(self) -> None:
        replay = green_button("Rejouer !")
        board = gold_button("", "Plateau")
        quit_btn = gold_button("", "Quitter")
        replay.clicked.connect(lambda: self._pick(self.REPLAY))
        board.clicked.connect(lambda: self._pick(self.BOARD))
        quit_btn.clicked.connect(lambda: self._pick(self.QUIT))

        self._card_layout.addWidget(replay)
        row = QHBoxLayout()
        row.setSpacing(14)
        row.addWidget(board)
        row.addWidget(quit_btn)
        self._card_layout.addLayout(row)

    def _pick(self, choice: str) -> None:
        self._choice = choice
        self.accept()

    @classmethod
    def ask(cls, parent, details: dict) -> str:
        dialog = cls(parent, details)
        dialog.exec()
        return dialog._choice
