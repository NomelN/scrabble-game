"""Petits widgets dessinés : sac de tuiles et boutons dorés (style maquette)."""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import (
    QBrush, QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen,
)
from PySide6.QtWidgets import QPushButton, QWidget

from . import theme


class BagWidget(QWidget):
    """Sac bleu avec le nombre de tuiles restantes (comme le « 88 » de la maquette)."""

    def __init__(self) -> None:
        super().__init__()
        self._count = 0
        self.setFixedSize(58, 62)

    def set_count(self, count: int) -> None:
        self._count = count
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 (API Qt)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        # Corps du sac (poche arrondie, dégradé bleu).
        body = QRectF(8, 16, w - 16, h - 20)
        grad = QLinearGradient(0, body.top(), 0, body.bottom())
        grad.setColorAt(0.0, QColor("#3d6f9e"))
        grad.setColorAt(1.0, QColor("#274c73"))
        path = QPainterPath()
        path.addRoundedRect(body, 14, 16)
        p.setPen(QPen(QColor("#1c3a57"), 1))
        p.setBrush(QBrush(grad))
        p.drawPath(path)

        # Col resserré du sac.
        neck = QPainterPath()
        neck.moveTo(w / 2 - 12, 18)
        neck.lineTo(w / 2 - 6, 6)
        neck.lineTo(w / 2 + 6, 6)
        neck.lineTo(w / 2 + 12, 18)
        p.setBrush(QBrush(QColor("#325d86")))
        p.drawPath(neck)

        # Nombre de tuiles restantes.
        p.setPen(QPen(QColor("#ffffff")))
        p.setFont(QFont("Helvetica", 15, QFont.Weight.Bold))
        p.drawText(body, Qt.AlignmentFlag.AlignCenter, str(self._count))
        p.end()


_GOLD_QSS = """
QPushButton {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #f8d15c, stop:1 #eaa62a);
    border: 1px solid #c6871a;
    border-radius: 12px;
    color: #1c1c1c;
    font-weight: bold;
    padding: 8px 12px;
}
QPushButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #ffe07a, stop:1 #f2b23c);
}
QPushButton:pressed {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #e9bf45, stop:1 #d99a24);
}
QPushButton:disabled {
    background: #cbd3d8;
    border-color: #b3bcc2;
    color: #7a848b;
}
"""

# Bouton d'action « fort » (Jouer) en vert.
_GREEN_QSS = """
QPushButton {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #6fd06f, stop:1 #3fa64f);
    border: 1px solid #2f8a3d;
    border-radius: 12px; color: white; font-weight: bold; padding: 8px 12px;
}
QPushButton:hover { background: #57c261; }
QPushButton:disabled { background: #cbd3d8; border-color: #b3bcc2; color: #7a848b; }
"""


def gold_button(icon: str, label: str) -> QPushButton:
    """Bouton doré avec une icône (glyphe) au-dessus d'un libellé."""
    btn = QPushButton(f"{icon}\n{label}" if icon else label)
    btn.setStyleSheet(_GOLD_QSS)
    btn.setMinimumWidth(84)
    return btn


def green_button(label: str) -> QPushButton:
    btn = QPushButton(label)
    btn.setStyleSheet(_GREEN_QSS)
    return btn
