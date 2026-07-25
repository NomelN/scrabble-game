"""Vue du plateau : une `QGraphicsScene` de 15×15 cases + les tuiles posées.

- La vue se **met à l'échelle** pour tenir dans l'espace disponible (aucun
  défilement) ; le mapping souris reste correct car Qt applique la transformation.
- Les tuiles « en attente » (coup en cours) sont **re-déplaçables** au glisser :
  vers une autre case, ou vers le chevalet (retour).
"""

from __future__ import annotations

from PySide6.QtCore import QMimeData, QPoint, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QDrag, QFont, QPen
from PySide6.QtWidgets import QGraphicsScene, QGraphicsView

from ..core.board import Board, SIZE, CENTER
from . import theme
from .animations import drop_in
from .tile_item import TileItem, tile_pixmap

_STEP = theme.CELL + theme.GAP
#: format MIME commun aux glisser (chevalet et plateau).
TILE_MIME = "application/x-scrabble-tile"


class BoardView(QGraphicsView):
    #: clic simple sur une case (row, col) — pose de la tuile sélectionnée.
    cell_clicked = Signal(int, int)
    #: une tuile du chevalet est lâchée sur une case (row, col, indice).
    tile_dropped = Signal(int, int, int)
    #: une tuile *déjà posée* est déplacée d'une case à une autre.
    pending_moved = Signal(int, int, int, int)  # from_row, from_col, to_row, to_col

    def __init__(self, board: Board) -> None:
        self._board = board
        self._scene = QGraphicsScene()
        super().__init__(self._scene)
        self.setRenderHints(self.renderHints())
        self.setFrameShape(QGraphicsView.Shape.NoFrame)
        self.setBackgroundBrush(QBrush(theme.WINDOW_BOTTOM))
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setAcceptDrops(True)
        self._tiles: dict[tuple[int, int], TileItem] = {}     # tuiles posées
        self._pending: dict[tuple[int, int], TileItem] = {}   # en attente
        self._press_cell: tuple[int, int] | None = None
        self._press_pos: QPoint | None = None
        self._dragging = False
        self._draw_grid()
        self.setSceneRect(0, 0, SIZE * _STEP, SIZE * _STEP)

    # -- Mise à l'échelle responsive (pas de scroll) ----------------------
    def _fit(self) -> None:
        self.fitInView(self.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def resizeEvent(self, event) -> None:  # noqa: N802 (API Qt)
        super().resizeEvent(event)
        self._fit()

    def showEvent(self, event) -> None:  # noqa: N802 (API Qt)
        super().showEvent(event)
        self._fit()

    def hasHeightForWidth(self) -> bool:  # noqa: N802 (API Qt)
        return True

    # -- Cases -------------------------------------------------------------
    def _cell_at(self, view_point) -> tuple[int, int] | None:
        pt = self.mapToScene(view_point)
        col, row = int(pt.x() // _STEP), int(pt.y() // _STEP)
        return (row, col) if 0 <= row < SIZE and 0 <= col < SIZE else None

    # -- Souris : clic pour poser + amorce de glisser d'une tuile posée ----
    def mousePressEvent(self, event) -> None:  # noqa: N802 (API Qt)
        self._dragging = False
        self._press_cell = self._cell_at(event.position().toPoint())
        self._press_pos = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802 (API Qt)
        if (self._press_cell is not None and not self._dragging
                and event.buttons() & Qt.MouseButton.LeftButton
                and self._press_cell in self._pending):
            moved = (event.position().toPoint() - self._press_pos).manhattanLength()
            from PySide6.QtWidgets import QApplication
            if moved >= QApplication.startDragDistance():
                self._dragging = True
                self._start_pending_drag(self._press_cell)
                return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802 (API Qt)
        # Clic simple (sans glisser) sur une case : pose la tuile sélectionnée.
        if not self._dragging and self._press_cell is not None:
            if self._cell_at(event.position().toPoint()) == self._press_cell:
                self.cell_clicked.emit(*self._press_cell)
        self._press_cell = None
        self._dragging = False
        super().mouseReleaseEvent(event)

    def _start_pending_drag(self, cell: tuple[int, int]) -> None:
        tile = self._pending[cell]
        drag = QDrag(self)
        mime = QMimeData()
        mime.setData(TILE_MIME, f"board:{cell[0]},{cell[1]}".encode("ascii"))
        drag.setMimeData(mime)
        pm = tile_pixmap(tile.letter)
        drag.setPixmap(pm)
        drag.setHotSpot(QPoint(pm.width() // 2, pm.height() // 2))
        drag.exec(Qt.DropAction.MoveAction)

    # -- Réception d'un glisser -------------------------------------------
    def dragEnterEvent(self, event) -> None:  # noqa: N802 (API Qt)
        if event.mimeData().hasFormat(TILE_MIME):
            event.acceptProposedAction()

    def dragMoveEvent(self, event) -> None:  # noqa: N802 (API Qt)
        if event.mimeData().hasFormat(TILE_MIME):
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:  # noqa: N802 (API Qt)
        if not event.mimeData().hasFormat(TILE_MIME):
            return
        cell = self._cell_at(event.position().toPoint())
        if cell is None:
            return
        payload = bytes(event.mimeData().data(TILE_MIME)).decode("ascii")
        kind, _, rest = payload.partition(":")
        if kind == "rack":
            self.tile_dropped.emit(cell[0], cell[1], int(rest))
        elif kind == "board":
            fr, fc = (int(x) for x in rest.split(","))
            self.pending_moved.emit(fr, fc, cell[0], cell[1])
        event.acceptProposedAction()

    # -- Dessin de la grille ----------------------------------------------
    def _draw_grid(self) -> None:
        for r in range(SIZE):
            for c in range(SIZE):
                code = self._board.premium_code(r, c)
                is_center = (r, c) == CENTER
                top, bottom = (theme.CENTER_GRADIENT if is_center
                               else theme.PREMIUM_GRADIENTS[code])
                cell_rect = QRectF(c * _STEP, r * _STEP, theme.CELL, theme.CELL)
                self._scene.addRect(
                    cell_rect,
                    QPen(theme.CELL_BORDER, 1),
                    QBrush(theme.vgrad(cell_rect, top, bottom)),
                )
                self._draw_cell_label(r, c, code, is_center)

    def _draw_cell_label(self, r: int, c: int, code: str, is_center: bool) -> None:
        if is_center:
            star = self._scene.addText("★", QFont("Helvetica", 18))
            star.setDefaultTextColor(theme.PREMIUM_TEXT)
            tr = star.boundingRect()
            star.setPos(c * _STEP + (theme.CELL - tr.width()) / 2,
                        r * _STEP + (theme.CELL - tr.height()) / 2)
            return
        label = theme.PREMIUM_LABEL.get(code)
        if not label:
            return
        text = self._scene.addText(label, QFont("Helvetica", 10, QFont.Weight.Bold))
        text.setDefaultTextColor(theme.PREMIUM_TEXT_DARK if code == "d"
                                 else theme.PREMIUM_TEXT)
        tr = text.boundingRect()
        text.setPos(c * _STEP + (theme.CELL - tr.width()) / 2,
                    r * _STEP + (theme.CELL - tr.height()) / 2)

    def cell_pos(self, row: int, col: int) -> QPointF:
        return QPointF(col * _STEP, row * _STEP)

    # -- Tuiles posées (définitives) --------------------------------------
    def place_tile(self, row: int, col: int, letter: str, animate: bool = True) -> TileItem:
        tile = TileItem(letter)
        self._scene.addItem(tile)
        self._tiles[(row, col)] = tile
        if animate:
            drop_in(tile, self.cell_pos(row, col))
        else:
            tile.setPos(self.cell_pos(row, col))
        return tile

    def tiles_at(self, cells: list[tuple[int, int]]) -> list[TileItem]:
        return [self._tiles[c] for c in cells if c in self._tiles]

    # -- Tuiles « en attente » (coup en cours) ----------------------------
    def place_pending(self, row: int, col: int, letter: str) -> TileItem:
        tile = TileItem(letter)
        tile.setOpacity(0.85)
        self._scene.addItem(tile)
        tile.setPos(self.cell_pos(row, col))
        self._pending[(row, col)] = tile
        return tile

    def move_pending_tile(self, old: tuple[int, int], new: tuple[int, int]) -> None:
        tile = self._pending.pop(old)
        tile.setPos(self.cell_pos(*new))
        self._pending[new] = tile

    def remove_pending_at(self, cell: tuple[int, int]) -> None:
        tile = self._pending.pop(cell, None)
        if tile is not None:
            self._scene.removeItem(tile)

    def has_pending_at(self, row: int, col: int) -> bool:
        return (row, col) in self._pending

    def clear_pending(self) -> None:
        for tile in self._pending.values():
            self._scene.removeItem(tile)
        self._pending.clear()
