"""Bibliothèque d'animations réutilisables (Qt).

Chaque fonction renvoie une animation *prête à lancer* (`start()`), ou la
lance directement. On s'appuie sur `QPropertyAnimation` et les groupes
(`QParallelAnimationGroup`, `QSequentialAnimationGroup`) pour orchestrer les
effets. C'est ici qu'on ajoute de nouveaux effets sans toucher au reste.
"""

from __future__ import annotations

from PySide6.QtCore import (
    QEasingCurve, QParallelAnimationGroup, QPointF, QPropertyAnimation,
    QSequentialAnimationGroup, QObject,
)
from PySide6.QtGui import QColor

from . import theme
from .tile_item import TileItem

# On garde une référence aux animations en cours : sinon le ramasse-miettes
# de Python peut les détruire avant la fin et l'animation « saute ».
_alive: set[QObject] = set()


def _keep(anim: QObject) -> None:
    _alive.add(anim)
    anim.finished.connect(lambda: _alive.discard(anim))


def drop_in(tile: TileItem, target: QPointF, duration: int = 260) -> None:
    """Pose d'une tuile : elle apparaît en fondu, grandit et « rebondit »
    légèrement à l'atterrissage. Utilisé à chaque lettre posée."""
    tile.setPos(target)
    tile.setOpacity(0.0)
    tile.setScale(0.4)

    group = QParallelAnimationGroup()

    fade = QPropertyAnimation(tile, b"opacity")
    fade.setStartValue(0.0)
    fade.setEndValue(1.0)
    fade.setDuration(duration)

    scale = QPropertyAnimation(tile, b"scale")
    scale.setStartValue(0.4)
    scale.setEndValue(1.0)
    scale.setDuration(duration)
    scale.setEasingCurve(QEasingCurve.Type.OutBack)  # le petit rebond

    group.addAnimation(fade)
    group.addAnimation(scale)
    _keep(group)
    group.start()


def bingo_flash(tiles: list[TileItem], stagger: int = 90) -> None:
    """« Scrabble ! » : les tuiles s'illuminent en cascade puis reviennent à l'or.
    Effet spectaculaire réservé au bonus de 50 points."""
    sequence = QSequentialAnimationGroup()
    for tile in tiles:
        flash = QPropertyAnimation(tile, b"bg")
        flash.setDuration(stagger * 2)
        flash.setKeyValueAt(0.0, QColor(theme.TILE_BG))
        flash.setKeyValueAt(0.5, QColor(theme.TILE_HIGHLIGHT))
        flash.setKeyValueAt(1.0, QColor(theme.TILE_BG))
        # À la fin, on rétablit le dégradé doré (sort du mode « flash à plat »).
        flash.finished.connect(tile.clear_flash)
        par = QParallelAnimationGroup()
        par.addAnimation(flash)
        sequence.addAnimation(par)  # chaque tuile démarre après la précédente
    _keep(sequence)
    sequence.start()


def slide_out(tile: TileItem, dx: float = 0, dy: float = -60,
              duration: int = 220) -> QPropertyAnimation:
    """Glissement + fondu d'une tuile hors de sa position (échange / défausse)."""
    anim = QPropertyAnimation(tile, b"pos")
    anim.setDuration(duration)
    anim.setStartValue(tile.pos())
    anim.setEndValue(tile.pos() + QPointF(dx, dy))
    anim.setEasingCurve(QEasingCurve.Type.InCubic)

    fade = QPropertyAnimation(tile, b"opacity")
    fade.setDuration(duration)
    fade.setStartValue(1.0)
    fade.setEndValue(0.0)

    group = QParallelAnimationGroup()
    group.addAnimation(anim)
    group.addAnimation(fade)
    _keep(group)
    group.start()
    return anim


def pulse_turn(item, duration: int = 400) -> None:
    """Petite pulsation d'échelle pour signaler « c'est ton tour »."""
    anim = QPropertyAnimation(item, b"scale")
    anim.setDuration(duration)
    anim.setKeyValueAt(0.0, 1.0)
    anim.setKeyValueAt(0.5, 1.12)
    anim.setKeyValueAt(1.0, 1.0)
    anim.setEasingCurve(QEasingCurve.Type.InOutSine)
    _keep(anim)
    anim.start()
