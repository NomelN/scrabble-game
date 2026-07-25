"""Palette et helpers visuels — style « tuiles bois dorées sur fond bleu clair ».

Tout est dessiné (dégradés/vectoriel), sans aucune image externe : idéal pour
l'empaquetage store. Les couleurs sont calquées sur la maquette de référence.
"""

from __future__ import annotations

from PySide6.QtCore import QRectF
from PySide6.QtGui import QColor, QLinearGradient

# -- Dimensions ------------------------------------------------------------
CELL = 44          # taille d'une case du plateau (px)
GAP = 1            # fin séparateur entre cases
TILE_INSET = 2     # marge de la tuile dans sa case

# -- Fond de la fenêtre / du plateau --------------------------------------
WINDOW_TOP = QColor("#a9d5ef")
WINDOW_BOTTOM = QColor("#8bbfe4")
BOARD_BG = QColor("#2b3b4a")    # lignes/fond derrière les cases

# -- Cases du plateau ------------------------------------------------------
CELL_TOP = QColor("#ffffff")
CELL_BOTTOM = QColor("#e7edf1")
CELL_BORDER = QColor("#b9c3ca")

# Cases bonus : (haut, bas) pour un léger dégradé. Codes = `Board.premium_code`.
PREMIUM_GRADIENTS = {
    ".": (CELL_TOP, CELL_BOTTOM),
    "d": (QColor("#d0e9fa"), QColor("#b6ddf3")),   # lettre double  (LD, bleu clair)
    "t": (QColor("#4a9bd6"), QColor("#2f82c6")),   # lettre triple  (LT, bleu foncé)
    "D": (QColor("#d4abd0"), QColor("#c091bd")),   # mot double     (MD, mauve)
    "T": (QColor("#e2594b"), QColor("#cf4436")),   # mot triple     (MT, rouge)
}
CENTER_GRADIENT = (QColor("#d4abd0"), QColor("#c091bd"))  # étoile centrale
PREMIUM_LABEL = {"d": "LD", "t": "LT", "D": "MD", "T": "MT"}
PREMIUM_TEXT = QColor("#ffffff")          # texte des cases bonus
PREMIUM_TEXT_DARK = QColor("#12405f")     # texte sur LD (bleu très clair)

# -- Tuiles bois dorées ----------------------------------------------------
TILE_GOLD_TOP = QColor("#f8d15c")
TILE_GOLD_BOTTOM = QColor("#eaa62a")
TILE_HIGHLIGHT_EDGE = QColor("#fde9a6")   # liseré clair (biseau haut)
TILE_SHADOW_EDGE = QColor("#c6871a")      # liseré foncé (biseau bas)
TILE_TEXT = QColor("#1c1c1c")

# Couleurs « à plat » utilisées par les animations (flash « Scrabble »).
TILE_BG = QColor("#f2be44")               # teinte de base (retour d'animation)
TILE_HIGHLIGHT = QColor("#fff6c2")        # éclat du flash


def vgrad(rect: QRectF, top: QColor, bottom: QColor) -> QLinearGradient:
    """Dégradé vertical du haut vers le bas d'un rectangle (coordonnées scène)."""
    g = QLinearGradient(rect.left(), rect.top(), rect.left(), rect.bottom())
    g.setColorAt(0.0, top)
    g.setColorAt(1.0, bottom)
    return g


def gold_grad(rect: QRectF) -> QLinearGradient:
    return vgrad(rect, TILE_GOLD_TOP, TILE_GOLD_BOTTOM)
