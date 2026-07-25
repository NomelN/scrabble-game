"""Télécharge et normalise le dictionnaire français pour le Scrabble.

Source : liste « Français GUTenberg » (336 531 mots), dérivée du dictionnaire
libre de l'ABU, hébergée par le projet openlexicon.
https://github.com/chrplr/openlexicon

Normalisation appliquée (les tuiles de Scrabble sont sans accent) :
- passage en MAJUSCULES, suppression des accents (É→E, Ç→C, Œ→OE, Æ→AE) ;
- on ne conserve que les mots de 2 à 15 lettres composés uniquement de A–Z ;
- dédoublonnage et tri.

Usage :
    python scripts/build_dictionary.py

Le fichier est écrit dans `scrabble/data/dictionnaire_fr.txt` (ignoré par git
par défaut, cf. .gitignore).
"""

from __future__ import annotations

import unicodedata
import urllib.request
from pathlib import Path

SOURCE_URL = (
    "https://raw.githubusercontent.com/chrplr/openlexicon/master/"
    "datasets-info/Liste-de-mots-francais-Gutenberg/liste.de.mots.francais.frgut.txt"
)
DEST = Path(__file__).resolve().parent.parent / "scrabble" / "data" / "dictionnaire_fr.txt"

LIGATURES = {"Œ": "OE", "Æ": "AE"}


def strip_accents(word: str) -> str:
    for lig, repl in LIGATURES.items():
        word = word.replace(lig, repl)
    decomposed = unicodedata.normalize("NFD", word)
    return "".join(c for c in decomposed if unicodedata.category(c) != "Mn")


def main() -> None:
    print(f"Téléchargement depuis {SOURCE_URL} …")
    with urllib.request.urlopen(SOURCE_URL, timeout=60) as resp:
        raw = resp.read().decode("utf-8")

    words = set()
    for line in raw.splitlines():
        w = strip_accents(line.strip().upper())
        if 2 <= len(w) <= 15 and w.isalpha() and w.isascii():
            words.add(w)

    DEST.parent.mkdir(parents=True, exist_ok=True)
    DEST.write_text("\n".join(sorted(words)) + "\n", encoding="utf-8")
    print(f"{len(words)} mots écrits dans {DEST}")


if __name__ == "__main__":
    main()
