"""IA « DeepSeek » : une couche de *décision* et de *commentaire* posée sur le
générateur algorithmique.

Principe (important) :
- le cœur du jeu génère des coups **légaux** et **scorés** (`generate_moves`) ;
- DeepSeek se contente d'en **choisir un** et d'ajouter un commentaire.

Ainsi le LLM ne peut jamais produire un coup illégal ni un score faux. Si la
clé API est absente ou l'appel échoue, on retombe sur la sélection gloutonne
(le meilleur score) — le jeu reste jouable hors-ligne.

Aucune dépendance externe : l'appel HTTP utilise la bibliothèque standard.
La clé est lue dans la variable d'environnement ``DEEPSEEK_API_KEY``.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Callable

from .base import Action, ActionKind, AIPlayer, Candidate

# Endpoint compatible OpenAI de DeepSeek.
API_URL = "https://api.deepseek.com/chat/completions"
DEFAULT_MODEL = "deepseek-chat"

# Un « transport » = fonction (messages, model) -> texte de réponse. On l'isole
# pour pouvoir le remplacer par un faux dans les tests (aucun réseau requis).
Transport = Callable[[list[dict], str], str]

PERSONAS = {
    "easy": "Tu es un adversaire débutant et bon enfant. Tu joues des coups "
            "simples et tu commentes avec légèreté.",
    "medium": "Tu es un joueur de Scrabble correct et pragmatique. Tu vises un "
              "bon score sans trop réfléchir à long terme.",
    "hard": "Tu es un joueur de Scrabble expert et taquin. Tu vises le meilleur "
            "score et tu bloques l'adversaire quand c'est utile.",
}


class DeepSeekAI(AIPlayer):
    """Sélectionne un coup via DeepSeek parmi les meilleurs candidats générés."""

    max_len = 7
    search_limit = 4000

    def __init__(
        self,
        level: str = "medium",
        api_key: str | None = None,
        model: str = DEFAULT_MODEL,
        top_n: int = 8,
        transport: Transport | None = None,
        seed: int | None = None,
    ) -> None:
        super().__init__(seed=seed)
        self.level = level
        self.model = model
        self.top_n = top_n
        self.api_key = api_key if api_key is not None else os.getenv("DEEPSEEK_API_KEY")
        self._transport = transport or _http_transport(self.api_key)
        self.last_comment: str = ""  # dernier commentaire de l'IA (pour l'UI)

    @property
    def available(self) -> bool:
        """Vrai si l'IA peut réellement interroger DeepSeek (clé présente)."""
        return bool(self.api_key)

    def _select(self, candidates: list[Candidate]) -> Action:
        # On ne présente au modèle que les N meilleurs coups (par score).
        ranked = sorted(candidates, key=lambda c: c.result.total, reverse=True)
        shortlist = ranked[: self.top_n]

        chosen = self._greedy(shortlist)  # repli par défaut
        if self.available:
            try:
                idx, comment = self._ask_model(shortlist)
                if 0 <= idx < len(shortlist):
                    chosen = shortlist[idx]
                self.last_comment = comment
            except (urllib.error.URLError, TimeoutError, ValueError, KeyError):
                # Réseau coupé / réponse illisible : on garde le repli glouton.
                self.last_comment = ""

        return Action(ActionKind.PLAY, placements=chosen.placements,
                      result=chosen.result)

    @staticmethod
    def _greedy(shortlist: list[Candidate]) -> Candidate:
        return shortlist[0]

    def _ask_model(self, shortlist: list[Candidate]) -> tuple[int, str]:
        """Demande à DeepSeek de choisir un indice et de commenter. Renvoie
        ``(indice, commentaire)``. Lève en cas de réponse inexploitable."""
        options = "\n".join(
            f"{i}: {c.result.main_word} ({c.result.total} points"
            f"{', SCRABBLE !' if c.result.is_bingo else ''})"
            for i, c in enumerate(shortlist)
        )
        system = (
            PERSONAS.get(self.level, PERSONAS["medium"])
            + " On te donne une liste de coups légaux déjà calculés au Scrabble. "
            "Choisis-en UN SEUL selon ta personnalité. Réponds STRICTEMENT en JSON "
            'de la forme {"choix": <indice entier>, "commentaire": "<courte phrase en français>"}.'
        )
        user = f"Coups possibles :\n{options}\n\nQuel coup joues-tu ?"
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        raw = self._transport(messages, self.model)
        data = _parse_json_object(raw)
        return int(data["choix"]), str(data.get("commentaire", ""))


def _http_transport(api_key: str | None, timeout: float = 20.0) -> Transport:
    """Fabrique un transport HTTP réel vers l'API DeepSeek."""

    def call(messages: list[dict], model: str) -> str:
        if not api_key:
            raise ValueError("Clé API DeepSeek absente.")
        payload = json.dumps({
            "model": model,
            "messages": messages,
            "temperature": 0.7,
            "response_format": {"type": "json_object"},
        }).encode("utf-8")
        req = urllib.request.Request(
            API_URL, data=payload, method="POST",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        return body["choices"][0]["message"]["content"]

    return call


def _parse_json_object(text: str) -> dict:
    """Extrait le premier objet JSON d'une réponse texte (robuste aux ```json)."""
    text = text.strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError(f"Réponse sans JSON exploitable : {text!r}")
    return json.loads(text[start : end + 1])
