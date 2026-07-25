"""Chargement des variables d'environnement depuis un fichier `.env.local`.

Petit chargeur sans dépendance externe : lit `.env.local` puis `.env` (à la
racine du projet et dans le dossier courant) et remplit `os.environ` pour les
clés non déjà définies. Accepte les formats ``CLE=valeur`` et ``CLE: valeur``.

Utilisé pour récupérer `DEEPSEEK_API_KEY` sans avoir à l'exporter manuellement.
⚠️ `.env.local` doit rester **gitignoré** (il contient des secrets).
"""

from __future__ import annotations

import os
from pathlib import Path

_ENV_NAMES = (".env.local", ".env", "env.local")


def load_env_files() -> None:
    """Charge les fichiers d'environnement s'ils existent (idempotent)."""
    roots = [Path(__file__).resolve().parent.parent, Path.cwd()]
    seen: set[Path] = set()
    for root in roots:
        for name in _ENV_NAMES:
            path = root / name
            if path.is_file() and path not in seen:
                seen.add(path)
                _apply(path)


def _apply(path: Path) -> None:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):].strip()
        if "=" in line:
            key, _, value = line.partition("=")
        elif ":" in line:
            key, _, value = line.partition(":")
        else:
            continue
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        # On n'écrase pas une variable déjà positionnée dans l'environnement.
        if key and key not in os.environ:
            os.environ[key] = value
