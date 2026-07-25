"""Dialogues stylés : confirmation (Passer / Quitter) et échange de lettres.

Look de la maquette : carte blanche arrondie centrée sur un fond assombri, deux
boutons dorés « Annuler » / « Confirmer ».
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
)

from ..core.tiles import letter_value
from .widgets import gold_button

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
