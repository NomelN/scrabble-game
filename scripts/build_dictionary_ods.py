"""Installe la liste **ODS8** (Officiel du Scrabble) depuis un dépôt GitHub.

⚠️⚠️ USAGE LOCAL / DÉVELOPPEMENT UNIQUEMENT ⚠️⚠️
L'ODS est **sous copyright** (Larousse / FISF). Cette liste ne doit PAS être
redistribuée ni incluse dans une application publiée (stores, releases). Le
fichier généré est gitignoré, donc il ne part pas dans le dépôt.

AVANT DE PUBLIER : reviens à la liste libre en lançant
    python scripts/build_dictionary.py     (liste « Français GUTenberg », libre)

Source utilisée : https://github.com/Thecoolsim/French-Scrabble-ODS8 (411 430 mots).
"""

from __future__ import annotations

import unicodedata
import urllib.request
from pathlib import Path

SOURCE_URL = (
    "https://raw.githubusercontent.com/Thecoolsim/French-Scrabble-ODS8/"
    "main/French%20ODS%20dictionary.txt"
)
DEST = Path(__file__).resolve().parent.parent / "scrabble" / "data" / "dictionnaire_fr.txt"

LIGATURES = {"Œ": "OE", "Æ": "AE"}


def strip_accents(word: str) -> str:
    for lig, repl in LIGATURES.items():
        word = word.replace(lig, repl)
    decomposed = unicodedata.normalize("NFD", word)
    return "".join(c for c in decomposed if unicodedata.category(c) != "Mn")


def main() -> None:
    print("⚠️  Liste ODS sous copyright — usage local uniquement (voir docstring).")
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
    print(f"{len(words)} mots ODS écrits dans {DEST}")
    print("Rappel : `python scripts/build_dictionary.py` pour repasser en liste libre.")


if __name__ == "__main__":
    main()
