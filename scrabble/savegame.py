"""Sauvegarde / reprise d'une partie en cours (un seul emplacement).

On persiste l'état complet du jeu (`Game.to_dict`) plus le niveau d'IA, dans
``~/.scrabble/savegame.json``. Pur Python (testable via un chemin injecté).
"""

from __future__ import annotations

import json
from pathlib import Path

from .core.dictionary import Dictionary
from .core.game import Game

DEFAULT_PATH = Path.home() / ".scrabble" / "savegame.json"


def has_save(path: Path | str = DEFAULT_PATH) -> bool:
    return Path(path).is_file()


def save_game(game: Game, level: str, path: Path | str = DEFAULT_PATH) -> None:
    path = Path(path)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"level": level, "game": game.to_dict()}
        path.write_text(json.dumps(payload), encoding="utf-8")
    except OSError:
        pass  # une sauvegarde ratée ne doit jamais bloquer le jeu


def load_game(
    dictionary: Dictionary, path: Path | str = DEFAULT_PATH
) -> tuple[Game, str] | None:
    """Renvoie (partie, niveau) ou None si aucune sauvegarde exploitable."""
    path = Path(path)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        game = Game.from_dict(data["game"], dictionary)
        return game, data["level"]
    except (OSError, json.JSONDecodeError, KeyError, TypeError):
        return None


def clear_save(path: Path | str = DEFAULT_PATH) -> None:
    try:
        Path(path).unlink(missing_ok=True)
    except OSError:
        pass
