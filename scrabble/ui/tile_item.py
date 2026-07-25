"""Tuile bois dorée, animable, dessinée dans la scène graphique.

`TileItem` est un `QGraphicsObject` : il possède des *propriétés Qt* (`scale`,
`opacity`, `pos`, `bg`) que `QPropertyAnimation` sait interpoler — c'est la
brique de base des animations. Le rendu imite une tuile en bois biseautée.
"""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt, Property
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QGraphicsObject

from ..core.tiles import letter_value
from . import theme


def tile_pixmap(letter: str, size: int = theme.CELL) -> QPixmap:
    """Rendu d'une tuile dorée en image — sert d'aperçu pendant un glisser."""
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    rect = QRectF(1, 1, size - 2, size - 2)
    p.setBrush(QBrush(theme.gold_grad(rect)))
    p.setPen(QPen(theme.TILE_SHADOW_EDGE, 1))
    p.drawRoundedRect(rect, 6, 6)
    p.setPen(QPen(theme.TILE_TEXT))
    p.setFont(QFont("Helvetica", int(size * 0.5), QFont.Weight.Bold))
    p.drawText(rect, Qt.AlignmentFlag.AlignCenter,
               letter.upper() if letter != "?" else " ")
    if letter_value(letter):
        p.setFont(QFont("Helvetica", int(size * 0.24), QFont.Weight.Bold))
        p.drawText(rect.adjusted(0, 0, -3, -2),
                   Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom,
                   str(letter_value(letter)))
    p.end()
    return pm


class TileItem(QGraphicsObject):
    def __init__(self, letter: str, size: int = theme.CELL) -> None:
        super().__init__()
        self._letter = letter
        self._size = size
        self._flash: QColor | None = None   # couleur de flash (bingo), sinon or
        self.setTransformOriginPoint(size / 2, size / 2)  # scale depuis le centre

    def boundingRect(self) -> QRectF:
        return QRectF(0, 0, self._size, self._size)

    # -- Propriété animable : couleur de flash (« Scrabble ») -------------
    def _get_bg(self) -> QColor:
        return self._flash or theme.TILE_BG

    def _set_bg(self, color: QColor) -> None:
        self._flash = color
        self.update()

    bg = Property(QColor, _get_bg, _set_bg)

    def clear_flash(self) -> None:
        self._flash = None
        self.update()

    # -- Rendu ------------------------------------------------------------
    def paint(self, painter: QPainter, option, widget=None) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(theme.TILE_INSET, theme.TILE_INSET,
                      self._size - 2 * theme.TILE_INSET,
                      self._size - 2 * theme.TILE_INSET)

        # Corps de la tuile : or dégradé, ou couleur de flash à plat.
        if self._flash is not None:
            painter.setBrush(QBrush(self._flash))
        else:
            painter.setBrush(QBrush(theme.gold_grad(rect)))
        painter.setPen(QPen(theme.TILE_SHADOW_EDGE, 1))
        painter.drawRoundedRect(rect, 6, 6)

        # Biseau : liseré clair en haut/gauche pour l'effet « relief ».
        painter.setPen(QPen(theme.TILE_HIGHLIGHT_EDGE, 1.5))
        painter.drawLine(rect.left() + 4, rect.top() + 2,
                         rect.right() - 4, rect.top() + 2)

        # Lettre (majuscule ; joker = espace).
        display = self._letter.upper() if self._letter != "?" else " "
        painter.setPen(QPen(theme.TILE_TEXT))
        painter.setFont(QFont("Helvetica", int(self._size * 0.5), QFont.Weight.Bold))
        painter.drawText(rect.adjusted(0, -2, -2, -2),
                         Qt.AlignmentFlag.AlignCenter, display)

        # Valeur en indice, en bas à droite (0 = joker, non affichée).
        value = letter_value(self._letter)
        if value:
            painter.setFont(QFont("Helvetica", int(self._size * 0.24), QFont.Weight.Bold))
            painter.drawText(rect.adjusted(0, 0, -4, -2),
                             Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom,
                             str(value))

    @property
    def letter(self) -> str:
        return self._letter
