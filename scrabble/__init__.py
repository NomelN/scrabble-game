"""Jeu de Scrabble — package racine.

Architecture volontairement découplée :
- `core`  : règles du jeu, 100 % Python pur, aucune dépendance UI (testable).
- `ai`    : joueurs artificiels (plusieurs niveaux), ne dépendent que de `core`.
- `ui`    : interface PySide6 (Qt), observe l'état de `core` et l'anime.
- `multiplayer` : réseau (ajouté plus tard), échange des coups via `core`.
"""

__version__ = "0.1.0"
