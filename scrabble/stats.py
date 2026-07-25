"""Statistiques du joueur, persistées en JSON entre les parties.

Pur Python (aucune dépendance UI/Qt) → testable. Le chemin par défaut est
``~/.scrabble/stats.json`` ; on peut en injecter un autre (tests).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

DEFAULT_PATH = Path.home() / ".scrabble" / "stats.json"


@dataclass
class Stats:
    games_played: int = 0
    games_won: int = 0
    total_moves: int = 0        # coups « posés » du joueur (pour la moyenne)
    total_points: int = 0       # somme des points de ces coups
    bingos: int = 0             # nombre de « Scrabble » réalisés
    best_game_score: int = 0    # meilleur score total sur une partie
    best_word_points: int = 0   # meilleur coup (points)
    best_word: str = ""         # mot correspondant

    _path: Path | None = None   # non sérialisé (préfixe _)

    # -- Dérivés (affichage) ---------------------------------------------
    @property
    def win_rate(self) -> float:
        return self.games_won / self.games_played if self.games_played else 0.0

    @property
    def avg_score_per_move(self) -> float:
        return self.total_points / self.total_moves if self.total_moves else 0.0

    # -- Enregistrement ---------------------------------------------------
    def record_move(self, points: int, word: str, is_bingo: bool) -> None:
        self.total_moves += 1
        self.total_points += points
        if is_bingo:
            self.bingos += 1
        if points > self.best_word_points:
            self.best_word_points = points
            self.best_word = word

    def record_game_end(self, human_score: int, won: bool) -> None:
        self.games_played += 1
        if won:
            self.games_won += 1
        self.best_game_score = max(self.best_game_score, human_score)

    # -- Persistance ------------------------------------------------------
    def to_dict(self) -> dict:
        d = asdict(self)
        d.pop("_path", None)
        return d

    def save(self) -> None:
        if self._path is None:
            return
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(json.dumps(self.to_dict(), indent=2),
                                  encoding="utf-8")
        except OSError:
            pass  # les stats ne doivent jamais bloquer le jeu

    @classmethod
    def load(cls, path: Path | str = DEFAULT_PATH) -> "Stats":
        path = Path(path)
        data: dict = {}
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                data = {}
        fields = {f for f in cls.__dataclass_fields__ if not f.startswith("_")}
        stats = cls(**{k: v for k, v in data.items() if k in fields})
        stats._path = path
        return stats
