"""Distribution et valeurs des lettres — Scrabble français (102 tuiles).

Le joker (lettre blanche) est représenté par le caractère ``BLANK`` ('?').
Quand un joker est posé sur le plateau, il prend l'apparence d'une lettre
mais garde une valeur de 0 point.
"""

from __future__ import annotations

# Caractère représentant une tuile blanche (joker) dans le sac / le chevalet.
BLANK = "?"

# Valeur en points de chaque lettre (français).
LETTER_VALUES: dict[str, int] = {
    BLANK: 0,
    **dict.fromkeys("EAINORSTUL", 1),
    **dict.fromkeys("DGMB", 2),
    **dict.fromkeys("CP", 3),
    **dict.fromkeys("FHV", 4),
    **dict.fromkeys("JQ", 8),
    **dict.fromkeys("KWXYZ", 10),
}

# Nombre de tuiles de chaque lettre dans le sac (total = 102).
LETTER_COUNTS: dict[str, int] = {
    BLANK: 2,
    "E": 15, "A": 9, "I": 8, "N": 6, "O": 6, "R": 6, "S": 6, "T": 6,
    "U": 6, "L": 5, "D": 3, "M": 3, "G": 2, "B": 2, "C": 2, "P": 2,
    "F": 2, "H": 2, "V": 2, "J": 1, "Q": 1, "K": 1, "W": 1, "X": 1,
    "Y": 1, "Z": 1,
}

TOTAL_TILES = sum(LETTER_COUNTS.values())  # 102


def letter_value(letter: str) -> int:
    """Valeur d'une lettre. Une lettre minuscule = joker posé (0 point)."""
    if letter.islower():
        return 0
    return LETTER_VALUES[letter]
