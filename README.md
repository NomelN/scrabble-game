# Scrabble

Jeu de Scrabble **français** pour ordinateur (macOS/Windows/Linux) : mode solo
contre une IA à plusieurs niveaux, interface animée en **PySide6 (Qt)**, et
architecture prête pour un **multijoueur** ultérieur et une **publication sur
les stores** de bureau.

## Principe d'architecture

Le code est découplé en couches — c'est ce qui rend possibles à la fois l'IA,
le multijoueur et les animations sans se marcher dessus :

| Dossier | Rôle | Dépendances |
|---|---|---|
| `scrabble/core` | Règles du jeu (plateau, sac, scores, tours) | **Python pur** |
| `scrabble/ai` | Joueurs artificiels (facile / moyen / expert) | `core` |
| `scrabble/ui` | Interface Qt + animations | `core`, PySide6 |
| `scrabble/multiplayer` | Réseau (à venir) | `core` |
| `tests` | Tests du cœur et de l'IA | pytest |

Règle d'or : **aucune règle de jeu dans l'UI**, **aucune notion d'UI dans le core**.

## Démarrage

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"     # installe PySide6 + pytest
```

Lancer l'application (démo visuelle des animations) :

```bash
python -m scrabble
```

Lancer les tests du moteur :

```bash
pytest -q
```

## État actuel (v0.2)

- ✅ Cœur de jeu : plateau 15×15 avec cases bonus, sac FR (102 tuiles),
  validation des mots, scoring complet (lettres/mots ×2/×3, bonus « Scrabble » +50),
  jokers, machine à états des tours, fin de partie.
- ✅ IA algorithmique : niveaux **facile** et **moyen** opérationnels ; **expert** ébauché.
- ✅ IA **DeepSeek** (optionnelle) : choisit parmi les coups légaux générés et
  commente, avec **repli automatique** sur l'IA algorithmique si pas de clé.
- ✅ **Jeu jouable** Humain vs IA : **clic** ou **glisser-déposer** d'une tuile
  du chevalet vers une case (la lettre posée disparaît du chevalet),
  « Valider / Reprendre / Échanger / Passer ».
- ✅ **Joker** géré à la pose (une boîte de dialogue demande la lettre incarnée, 0 point).
- ✅ Vrai **dictionnaire** français (~311 500 mots, voir plus bas).
- ✅ Animations pilotées par les **événements** du jeu (pose avec rebond, flash
  « Scrabble », etc.).
- ✅ Tests : 21 tests verts (cœur, IA, DeepSeek en mock, contrôleur UI headless).
- 🔜 Écran de menu, IA experte (GADDAG), multijoueur.

### Note de performance

L'IA « moyen/expert » explore les coups en force brute : avec un chevalet plein
(7 tuiles, jokers compris) la recherche peut prendre quelques secondes. C'est
exactement ce que résoudra le passage à un GADDAG/DAWG (voir plus bas). Pour
l'instant, l'appel tourne dans un **thread** afin de ne pas figer l'interface.

## Dictionnaire

Le jeu utilise la liste **« Français GUTenberg »** (~311 500 mots après
normalisation), dérivée du dictionnaire **libre** de l'ABU. Elle est
téléchargée et normalisée pour le Scrabble (majuscules, sans accent, A–Z, 2–15
lettres) par :

```bash
python scripts/build_dictionary.py
```

Le fichier atterrit dans `scrabble/data/dictionnaire_fr.txt` et est chargé
automatiquement (`Dictionary.load_default()`). Sans ce fichier, le jeu retombe
sur un petit lexique de démonstration intégré.

Attribution / licence :
- Source : liste Français GUTenberg via le projet
  [openlexicon](https://github.com/chrplr/openlexicon) (dictionnaire ABU, libre).
- Le fichier est ignoré par git par défaut (3,3 Mo) ; tu peux le versionner en
  ajoutant l'attribution (retire la ligne correspondante du `.gitignore`).
- ⚠️ **Ne versionne jamais** une liste **ODS** (Officiel du Scrabble), sous copyright.

### Définitions des mots joués

Quand un mot est posé, l'appli affiche sa **définition** (bandeau du haut) et un
**badge de score** sur le plateau. Résolution : `data/definitions_fr.txt` (graine
versionnée) → cache local → **DeepSeek** en secours (si `DEEPSEEK_API_KEY`).
Les définitions ramenées par DeepSeek sont **mises en cache** dans
`data/definitions_cache.txt` (gitignoré), donc la couverture hors-ligne grandit
au fil des parties. Une définition n'a **aucun rôle dans les règles** (le mot
est déjà validé par le dictionnaire) — c'est un usage approprié de l'IA.

### Option ODS (développement local uniquement)

Pour développer avec le vrai **ODS8** (402 325 mots après normalisation) :

```bash
python scripts/build_dictionary_ods.py
```

⚠️ L'ODS est **sous copyright** : cette liste est réservée à un usage **local**.
Le fichier reste gitignoré (il ne part pas dans le dépôt). **Avant toute
publication**, repasse à la liste libre :

```bash
python scripts/build_dictionary.py
```

## IA DeepSeek (LLM)

DeepSeek n'invente **jamais** de coup : le cœur du jeu génère des coups légaux
et scorés, et le LLM se contente d'en **choisir un** (selon le niveau/persona)
et d'écrire un **commentaire**. La légalité et les scores restent garantis par
`core`. Voir `scrabble/ai/deepseek.py`.

Configuration : place ta clé dans l'environnement (jamais dans le code) —

```bash
export DEEPSEEK_API_KEY="sk-..."
```

Puis choisis un niveau « DeepSeek » dans le menu de l'IA. Sans clé (ou si le
réseau échoue), le jeu retombe silencieusement sur l'IA algorithmique. L'appel
utilise l'endpoint compatible OpenAI de DeepSeek via la bibliothèque standard
(aucune dépendance ajoutée).

## IA experte — note technique

Les niveaux facile/moyen utilisent un générateur de coups en **force brute
bornée** (voir `scrabble/ai/base.py`). Pour un niveau expert *fort et rapide*,
il faudra une structure de dictionnaire dédiée — **GADDAG** ou **DAWG** — qui
énumère tous les coups possibles efficacement (algorithme Appel & Jacobson).
Le reste du code n'a pas besoin de changer : seule la stratégie `HardAI._select`
et le générateur évoluent.

## Publication sur les stores

L'empaquetage passe par **Briefcase** (BeeWare), configuré dans `pyproject.toml` :

```bash
pip install briefcase
briefcase dev                 # lance l'app via Briefcase
briefcase create macOS
briefcase build macOS
briefcase package macOS       # .app / .pkg (signature + notarisation Apple requises)
```

Avant publication : remplacer `bundle = "com.example"` par ton identifiant réel,
ajouter une icône, et — pour le Mac App Store — un compte Apple Developer
(signature + notarisation).
