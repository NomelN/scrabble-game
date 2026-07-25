"""Tests de l'IA DeepSeek — sans aucun accès réseau (transport factice)."""

from scrabble.ai import ActionKind
from scrabble.ai.deepseek import DeepSeekAI, _parse_json_object
from scrabble.core.board import Board, Placement
from scrabble.core.dictionary import Dictionary


def _candidates():
    """Deux coups légaux sur plateau vide : 'MOT' puis 'TABLE'."""
    from scrabble.ai.base import generate_moves
    board = Board()
    d = Dictionary.demo()
    cands = generate_moves(board, list("MOTABLE"), d, max_len=5, limit=500)
    assert cands, "le lexique démo doit produire au moins un coup"
    return cands


def test_parse_json_handles_code_fences():
    data = _parse_json_object('```json\n{"choix": 2, "commentaire": "ok"}\n```')
    assert data["choix"] == 2


def test_deepseek_uses_model_choice():
    calls = {}

    def fake_transport(messages, model):
        calls["messages"] = messages
        return '{"choix": 1, "commentaire": "Je tente ce coup."}'

    ai = DeepSeekAI(level="medium", api_key="test-key", transport=fake_transport)
    cands = _candidates()
    action = ai._select(cands)
    assert action.kind is ActionKind.PLAY
    assert ai.last_comment == "Je tente ce coup."
    assert "messages" in calls  # le modèle a bien été interrogé


def test_deepseek_falls_back_when_no_key():
    # Sans clé : pas d'appel réseau, sélection gloutonne (meilleur score).
    ai = DeepSeekAI(level="hard", api_key=None)
    assert ai.available is False
    cands = _candidates()
    action = ai._select(cands)
    best = max(c.result.total for c in cands)
    assert action.result.total == best


def test_deepseek_falls_back_on_transport_error():
    def boom(messages, model):
        raise TimeoutError("réseau coupé")

    ai = DeepSeekAI(level="medium", api_key="k", transport=boom)
    action = ai._select(_candidates())
    assert action.kind is ActionKind.PLAY  # repli, pas de crash
