"""Définitions courtes des mots joués — **local d'abord, DeepSeek en secours**.

Ordre de résolution :
1. fichier local (`data/definitions_fr.txt`, graine versionnée) ;
2. cache local (`data/definitions_cache.txt`, alimenté automatiquement) ;
3. DeepSeek, si une clé est disponible — le résultat est **mis en cache**, donc
   la couverture hors-ligne grandit au fil des parties.

⚠️ Une définition n'a **aucun rôle** dans les règles : le mot est déjà validé
par le dictionnaire. Elle est purement informative — l'imprécision est sans
conséquence sur le jeu. C'est pourquoi DeepSeek est ici un usage approprié.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Callable

_DATA = Path(__file__).resolve().parent / "data"
SEED_FILE = _DATA / "definitions_fr.txt"
CACHE_FILE = _DATA / "definitions_cache.txt"

API_URL = "https://api.deepseek.com/chat/completions"
DEFAULT_MODEL = "deepseek-v4-flash"   # deepseek-chat n'est plus supporté

# Transport = fonction (mot) -> texte de définition. Isolé pour les tests.
Transport = Callable[[str], str]


def _parse_file(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if "\t" in line:
                word, definition = line.split("\t", 1)
                out[word.strip().upper()] = definition.strip()
    return out


class Definitions:
    def __init__(
        self,
        local: dict[str, str] | None = None,
        api_key: str | None = None,
        transport: Transport | None = None,
        cache_path: Path | str = CACHE_FILE,
    ) -> None:
        self._local = local or {}
        self.api_key = api_key
        self._transport = transport
        self._cache_path = Path(cache_path)

    @property
    def remote_available(self) -> bool:
        return self._transport is not None or bool(self.api_key)

    def local_lookup(self, word: str) -> str | None:
        """Cherche uniquement en local (instantané, hors-ligne)."""
        return self._local.get(word.upper())

    def remote_lookup(self, word: str) -> str | None:
        """Demande la définition à DeepSeek (à appeler dans un thread : réseau).
        Met le résultat en cache local. Renvoie None si indisponible."""
        w = word.upper()
        if w in self._local:
            return self._local[w]
        transport = self._transport or (
            _http_transport(self.api_key) if self.api_key else None
        )
        if transport is None:
            return None
        try:
            text = transport(w).strip()
        except (urllib.error.URLError, TimeoutError, ValueError, KeyError):
            return None
        if not text:
            return None
        self._local[w] = text          # cache mémoire
        self._append_cache(w, text)    # cache disque
        return text

    def _append_cache(self, word: str, definition: str) -> None:
        try:
            self._cache_path.parent.mkdir(parents=True, exist_ok=True)
            with self._cache_path.open("a", encoding="utf-8") as f:
                f.write(f"{word}\t{definition}\n")
        except OSError:
            pass  # le cache est un confort, jamais bloquant

    @classmethod
    def load_default(cls) -> "Definitions":
        local = _parse_file(SEED_FILE)
        local.update(_parse_file(CACHE_FILE))  # le cache complète/écrase la graine
        return cls(local=local, api_key=os.getenv("DEEPSEEK_API_KEY"))


def _http_transport(api_key: str | None, timeout: float = 20.0) -> Transport:
    def call(word: str) -> str:
        if not api_key:
            raise ValueError("Clé API DeepSeek absente.")
        payload = json.dumps({
            "model": DEFAULT_MODEL,
            "messages": [
                {"role": "system", "content":
                    "Tu donnes des définitions TRÈS courtes en français (une seule "
                    "phrase, ~12 mots max), style dictionnaire. Réponds uniquement "
                    "par la définition, sans répéter le mot."},
                {"role": "user", "content": f"Définis le mot français : {word}"},
            ],
            "temperature": 0.3,
        }).encode("utf-8")
        req = urllib.request.Request(
            API_URL, data=payload, method="POST",
            headers={"Authorization": f"Bearer {api_key}",
                     "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        return body["choices"][0]["message"]["content"]

    return call
