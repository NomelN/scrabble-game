"""Tests de la persistance et du calcul des statistiques."""

from scrabble.stats import Stats


def test_record_moves_and_derived_values():
    s = Stats()
    s.record_move(8, "MOT", is_bingo=False)
    s.record_move(30, "BOXEE", is_bingo=False)
    s.record_move(70, "SEPAREZ", is_bingo=True)
    assert s.total_moves == 3
    assert s.bingos == 1
    assert s.best_word_points == 70
    assert s.best_word == "SEPAREZ"
    assert abs(s.avg_score_per_move - (8 + 30 + 70) / 3) < 1e-9


def test_record_game_end_and_winrate():
    s = Stats()
    s.record_game_end(120, won=True)
    s.record_game_end(90, won=False)
    assert s.games_played == 2
    assert s.games_won == 1
    assert abs(s.win_rate - 0.5) < 1e-9
    assert s.best_game_score == 120


def test_save_and_load_roundtrip(tmp_path):
    path = tmp_path / "stats.json"
    s = Stats.load(path)          # part de zéro
    s.record_move(50, "AZALEE", is_bingo=True)
    s.record_game_end(200, won=True)
    s.save()

    again = Stats.load(path)
    assert again.games_played == 1
    assert again.games_won == 1
    assert again.bingos == 1
    assert again.best_word == "AZALEE"
    assert again.best_game_score == 200


def test_load_missing_file_is_empty(tmp_path):
    s = Stats.load(tmp_path / "absent.json")
    assert s.games_played == 0
    assert s.best_word == ""
