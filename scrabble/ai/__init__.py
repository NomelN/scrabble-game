"""Joueurs artificiels. Chaque niveau = une stratégie de choix de coup.

L'IA ne dépend que de `core`. Elle décide d'une *action* (jouer / échanger /
passer) ; c'est la partie (`Game`) qui l'applique et émet les événements.

Deux familles d'IA :
- **algorithmique** : ``easy`` / ``medium`` / ``hard`` — hors-ligne, gratuite ;
- **DeepSeek** : ``deepseek-easy`` / ``deepseek-medium`` / ``deepseek-hard`` —
  choisit parmi les coups générés et commente (repli algorithmique si pas de clé).
"""

from .base import Action, ActionKind, AIPlayer, make_ai as _make_algorithmic


def make_ai(level: str, seed: int | None = None, **kwargs):
    """Fabrique une IA à partir d'un nom de niveau.

    - ``easy`` / ``medium`` / ``hard``            → IA algorithmique
    - ``deepseek`` ou ``deepseek-<niveau>``       → IA DeepSeek (LLM)

    ``kwargs`` est transmis à `DeepSeekAI` (``api_key``, ``model``, ``transport``…).
    """
    if level.startswith("deepseek"):
        from .deepseek import DeepSeekAI
        sub = level.split("-", 1)[1] if "-" in level else "medium"
        return DeepSeekAI(level=sub, seed=seed, **kwargs)
    return _make_algorithmic(level, seed=seed)


__all__ = ["Action", "ActionKind", "AIPlayer", "make_ai"]
