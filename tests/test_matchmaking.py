# ----- required imports -----

import pytest
from src.matchmaking import MatchmakingEngine

# ----- test fixtures -----

@pytest.fixture
def matchmaking_engine():
    return MatchmakingEngine()

# ----- tests -----

def test_library_overlap_calculation(matchmaking_engine):
    """Test library overlap calculation"""
    games1 = [
        {'appid': 570, 'name': 'Dota 2'},
        {'appid': 730, 'name': 'CS:GO'},
        {'appid': 440, 'name': 'TF2'}
    ]

    games2 = [
        {'appid': 570, 'name': 'Dota 2'},
        {'appid': 730, 'name': 'CS:GO'}
    ]

    overlap = matchmaking_engine._calculate_library_overlap(games1, games2)

    # 2 shared games out of 3 total unique = 0.666...
    assert overlap > 0.6
    assert overlap < 0.7

def test_playtime_similarity(matchmaking_engine):
    """Test playtime similarity calculation"""
    games1 = [
        {'appid': 570, 'name': 'Dota 2', 'playtime_forever': 1000},
        {'appid': 730, 'name': 'CS:GO', 'playtime_forever': 500}
    ]

    games2 = [
        {'appid': 570, 'name': 'Dota 2', 'playtime_forever': 1200},
        {'appid': 730, 'name': 'CS:GO', 'playtime_forever': 400}
    ]

    similarity = matchmaking_engine._calculate_playtime_similarity(games1, games2)

    # Similar playtimes should yield high similarity
    assert similarity > 0.7

def test_empty_games_lists(matchmaking_engine):
    """Test with empty game lists"""
    games1 = []
    games2 = []

    overlap = matchmaking_engine._calculate_library_overlap(games1, games2)
    assert overlap == 0.0

    similarity = matchmaking_engine._calculate_playtime_similarity(games1, games2)
    assert similarity == 0.0

def test_no_shared_games(matchmaking_engine):
    """Test with no shared games"""
    games1 = [
        {'appid': 570, 'name': 'Dota 2', 'playtime_forever': 1000}
    ]

    games2 = [
        {'appid': 730, 'name': 'CS:GO', 'playtime_forever': 500}
    ]

    similarity = matchmaking_engine._calculate_playtime_similarity(games1, games2)
    assert similarity == 0.0

def test_format_compatibility_message(matchmaking_engine):
    """Test compatibility message formatting"""
    compatibility = {
        'score': 85.5,
        'shared_games': 42,
        'library_overlap': 67.3,
        'playtime_similarity': 82.1
    }

    message = matchmaking_engine.format_compatibility_message(
        "User1",
        "User2",
        compatibility
    )

    assert "85.5%" in message
    assert "42 shared games" in message
    assert "67.3%" in message
    assert "82.1%" in message
    assert "User1" in message
    assert "User2" in message
