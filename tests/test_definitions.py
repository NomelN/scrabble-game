"""Tests du fournisseur de définitions (local + secours DeepSeek, sans réseau)."""

from scrabble.definitions import Definitions


def test_local_lookup_from_seed_file():
    d = Definitions.load_default()
    assert d.local_lookup("WEB") is not None
    assert d.local_lookup("web") is not None          # insensible à la casse
    assert d.local_lookup("ZZZZZINCONNU") is None


def test_remote_lookup_uses_transport_and_caches(tmp_path):
    calls = []

    def fake(word):
        calls.append(word)
        return "  une définition inventée  "

    cache = tmp_path / "cache.txt"
    d = Definitions(local={}, transport=fake, cache_path=cache)
    assert d.remote_available
    assert d.remote_lookup("BIDULE") == "une définition inventée"
    # Mise en cache : mémoire (pas de 2e appel) + disque.
    assert d.remote_lookup("BIDULE") == "une définition inventée"
    assert calls == ["BIDULE"]
    assert "BIDULE\tune définition inventée" in cache.read_text(encoding="utf-8")


def test_no_remote_without_key():
    d = Definitions(local={"MOT": "un mot"}, api_key=None)
    assert d.remote_available is False
    assert d.remote_lookup("INCONNU") is None


def test_remote_lookup_survives_transport_error():
    def boom(word):
        raise TimeoutError("réseau coupé")

    d = Definitions(local={}, transport=boom)
    assert d.remote_lookup("MOT") is None            # repli silencieux
