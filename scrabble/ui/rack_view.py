"""Chevalet du joueur : tuiles cliquables, glissables et **réorganisables**.

Interactions :
- clic sur une tuile → sélection (puis clic sur une case pour poser) ;
- glisser une tuile vers une case du plateau → pose ;
- glisser une tuile *dans* le chevalet → réordonne les lettres ;
- lâcher sur le chevalet une tuile venant du plateau → la ramène au chevalet.

Une tuile utilisée dans le coup en cours **disparaît** du chevalet (case vidée).
"""

from __future__ import annotations

from PySide6.QtCore import QMimeData, QPoint, QRectF, Qt, Signal
from PySide6.QtGui import (
    QBrush, QColor, QDrag, QFont, QPainter, QPainterPath, QPen,
)
from PySide6.QtWidgets import QApplication, QGraphicsScene, QGraphicsView

from ..core.tiles import letter_value
from . import theme
from .board_view import TILE_MIME
from .tile_item import tile_pixmap

_SLOT = theme.CELL + 6


class RackView(QGraphicsView):
    #: une tuile est cliquée (indice) — sélection pour la pose au clic.
    tile_selected = Signal(int)
    #: réordonner : déplacer la tuile d'indice `frm` vers la position `to`.
    reorder_requested = Signal(int, int)
    #: ramener au chevalet la tuile posée en (row, col), à la position `to`.
    return_requested = Signal(int, int, int)

    def __init__(self) -> None:
        self._scene = QGraphicsScene()
        super().__init__(self._scene)
        self.setFrameShape(QGraphicsView.Shape.NoFrame)
        self.setBackgroundBrush(QBrush(theme.WINDOW_BOTTOM))
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        # Ancrage haut-gauche : sinon la scène est centrée dans la vue et le
        # mapping « position souris -> index de tuile » est décalé (bug doublons).
        self.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.setFixedHeight(_SLOT + 16)
        # Largeur figée à 7 tuiles (chevalet plein) ; le widget lui-même est
        # centré par la mise en page, sans recentrer la *scène* (index exact).
        self.setFixedWidth(7 * _SLOT + 4)
        self.setAcceptDrops(True)
        self._letters: list[str] = []
        self._selected: int | None = None
        self._used: set[int] = set()          # indices posés (donc masqués)
        self._press_index: int | None = None
        self._press_pos: QPoint | None = None
        #: fournit la taille (px écran) d'une case du plateau, pour que l'image
        #: de glisser colle exactement aux cases (évite le chevauchement visuel).
        self._cell_size_provider = None

    def set_cell_size_provider(self, provider) -> None:
        self._cell_size_provider = provider

    def _drag_tile_size(self) -> int:
        if self._cell_size_provider is not None:
            return self._cell_size_provider()
        return theme.CELL

    # -- État --------------------------------------------------------------
    def set_letters(self, letters: list[str]) -> None:
        self._letters = list(letters)
        self._selected = None
        self._used = set()
        self._redraw()

    def set_used(self, used: set[int]) -> None:
        self._used = set(used)
        if self._selected in self._used:
            self._selected = None
        self._redraw()

    def selected_index(self) -> int | None:
        return self._selected

    def select(self, index: int) -> None:
        if 0 <= index < len(self._letters) and index not in self._used:
            self._selected = index
            self._redraw()

    def clear_selection(self) -> None:
        self._selected = None
        self._redraw()

    def _index_at(self, view_x: float) -> int:
        idx = int(self.mapToScene(QPoint(int(view_x), 0)).x() // _SLOT)
        return max(0, min(idx, len(self._letters)))

    # -- Souris : clic (sélection) + amorce de glisser --------------------
    def mousePressEvent(self, event) -> None:  # noqa: N802 (API Qt)
        idx = int(self.mapToScene(event.position().toPoint()).x() // _SLOT)
        if 0 <= idx < len(self._letters) and idx not in self._used:
            self._press_index = idx
            self._press_pos = event.position().toPoint()
            self._selected = idx
            self._redraw()
            self.tile_selected.emit(idx)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802 (API Qt)
        if self._press_index is None or not (event.buttons() & Qt.MouseButton.LeftButton):
            return super().mouseMoveEvent(event)
        if (event.position().toPoint() - self._press_pos).manhattanLength() \
                >= QApplication.startDragDistance():
            self._start_drag(self._press_index)
            self._press_index = None

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802 (API Qt)
        self._press_index = None
        super().mouseReleaseEvent(event)

    def _start_drag(self, index: int) -> None:
        drag = QDrag(self)
        mime = QMimeData()
        mime.setData(TILE_MIME, f"rack:{index}".encode("ascii"))
        drag.setMimeData(mime)
        pm = tile_pixmap(self._letters[index], self._drag_tile_size(), alpha=0.85)
        drag.setPixmap(pm)
        drag.setHotSpot(QPoint(pm.width() // 2, pm.height() // 2))
        drag.exec(Qt.DropAction.MoveAction)

    # -- Réception d'un glisser (réordonner / ramener) --------------------
    def dragEnterEvent(self, event) -> None:  # noqa: N802 (API Qt)
        if event.mimeData().hasFormat(TILE_MIME):
            event.acceptProposedAction()

    def dragMoveEvent(self, event) -> None:  # noqa: N802 (API Qt)
        if event.mimeData().hasFormat(TILE_MIME):
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:  # noqa: N802 (API Qt)
        if not event.mimeData().hasFormat(TILE_MIME):
            return
        target = self._index_at(event.position().toPoint().x())
        payload = bytes(event.mimeData().data(TILE_MIME)).decode("ascii")
        kind, _, rest = payload.partition(":")
        if kind == "rack":
            self.reorder_requested.emit(int(rest), target)
        elif kind == "board":
            r, c = (int(x) for x in rest.split(","))
            self.return_requested.emit(r, c, target)
        event.acceptProposedAction()

    # -- Rendu -------------------------------------------------------------
    def _redraw(self) -> None:
        self._scene.clear()
        # sceneRect fixe ancré en (0,0) : garantit x_écran == x_scène, donc
        # l'index calculé (x // _SLOT) correspond exactement à la tuile visible.
        self.setSceneRect(0, 0, max(1, len(self._letters)) * _SLOT, _SLOT + 12)
        for i, letter in enumerate(self._letters):
            rect = QRectF(i * _SLOT + 3, 6, theme.CELL, theme.CELL)
            if i in self._used:
                empty = QPainterPath()
                empty.addRoundedRect(rect, 6, 6)
                self._scene.addPath(
                    empty,
                    QPen(QColor("#6f9bbd"), 1, Qt.PenStyle.DashLine),
                    QBrush(QColor("#7fb0d6")),
                )
                continue
            self._draw_gold_tile(rect, letter, selected=i == self._selected)

    def _draw_gold_tile(self, rect: QRectF, letter: str, selected: bool) -> None:
        path = QPainterPath()
        path.addRoundedRect(rect, 6, 6)
        self._scene.addPath(
            path,
            QPen(QColor("#ffffff") if selected else theme.TILE_SHADOW_EDGE,
                 2.5 if selected else 1),
            QBrush(theme.gold_grad(rect)),
        )
        self._scene.addLine(
            rect.left() + 5, rect.top() + 3, rect.right() - 5, rect.top() + 3,
            QPen(theme.TILE_HIGHLIGHT_EDGE, 1.5),
        )
        display = letter.upper() if letter != "?" else " "
        text = self._scene.addText(display, QFont("Helvetica", 20, QFont.Weight.Bold))
        text.setDefaultTextColor(theme.TILE_TEXT)
        tr = text.boundingRect()
        text.setPos(rect.left() + (theme.CELL - tr.width()) / 2,
                    rect.top() + (theme.CELL - tr.height()) / 2 - 1)
        val = letter_value(letter)
        if val:
            v = self._scene.addText(str(val), QFont("Helvetica", 10, QFont.Weight.Bold))
            v.setDefaultTextColor(theme.TILE_TEXT)
            v.setPos(rect.right() - 15, rect.bottom() - 19)
