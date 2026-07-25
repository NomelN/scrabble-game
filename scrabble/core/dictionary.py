"""Dictionnaire de validation des mots (ODS français).

⚠️ Licence : l'ODS (Officiel du Scrabble) est protégé. Ne versionne pas de
liste sous copyright dans ce dépôt. Deux options légales :
  1. une liste sous licence libre (ex. lexiques ouverts) placée dans
     `scrabble/data/dictionnaire_fr.txt` (un mot par ligne, en MAJUSCULES) ;
  2. le petit dictionnaire de démonstration ci-dessous, suffisant pour
     développer et tester l'application.

`Dictionary` expose `__contains__`, donc s'utilise directement dans les règles.
"""

from __future__ import annotations

from pathlib import Path

# Petit lexique de démonstration (à remplacer par un vrai fichier de mots).
_DEMO_WORDS = {
    "AS", "BAR", "CHAT", "CHATS", "DE", "ET", "EAU", "JEU", "JEUX", "LE",
    "LES", "MOT", "MOTS", "NON", "OR", "OUI", "PARI", "PARIS", "RAT", "RATS",
    "ROI", "ROIS", "SCRABBLE", "TE", "TES", "TABLE", "TABLES", "UN", "VIE",
    "ZUT", "ARBRE", "ARBRES", "TU", "OS", "SI", "NE", "SA", "TA", "MA",
}


class Dictionary:
    def __init__(self, words: set[str]) -> None:
        # On normalise en majuscules pour comparer sans se soucier de la casse.
        self._words = {w.strip().upper() for w in words if w.strip()}

    def __contains__(self, word: str) -> bool:
        return word.upper() in self._words

    def __len__(self) -> int:
        return len(self._words)

    @classmethod
    def demo(cls) -> "Dictionary":
        """Dictionnaire minimal pour développer sans fichier externe."""
        return cls(_DEMO_WORDS)

    @classmethod
    def from_file(cls, path: str | Path) -> "Dictionary":
        """Charge un fichier « un mot par ligne »."""
        text = Path(path).read_text(encoding="utf-8")
        return cls(set(text.splitlines()))

    @classmethod
    def load_default(cls) -> "Dictionary":
        """Charge `data/dictionnaire_fr.txt` s'il existe, sinon le lexique démo."""
        default = Path(__file__).resolve().parent.parent / "data" / "dictionnaire_fr.txt"
        if default.exists():
            return cls.from_file(default)
        return cls.demo()
