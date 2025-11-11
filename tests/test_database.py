# ----- required imports -----

import pytest
import asyncio
import os
import tempfile
from src.database import Database

# ----- test fixtures -----

@pytest.fixture
async def test_db():
    """Create a temporary test database"""
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    temp_file.close()

    db = Database(temp_file.name)
    await db.initialize()

    yield db

    # Cleanup
    os.unlink(temp_file.name)

# ----- tests -----

@pytest.mark.asyncio
async def test_user_registration(test_db):
    """Test user registration"""
    success = await test_db.register_user(
        discord_id=123456789,
        steam_id="76561198000000000",
        steam_username="TestUser"
    )

    assert success is True

    # Verify user was registered
    user = await test_db.get_user(123456789)
    assert user is not None
    assert user['steam_id'] == "76561198000000000"
    assert user['steam_username'] == "TestUser"

@pytest.mark.asyncio
async def test_user_unregistration(test_db):
    """Test user unregistration"""
    # Register user first
    await test_db.register_user(
        discord_id=123456789,
        steam_id="76561198000000000"
    )

    # Unregister
    success = await test_db.unregister_user(123456789)
    assert success is True

    # Verify user was removed
    user = await test_db.get_user(123456789)
    assert user is None

@pytest.mark.asyncio
async def test_get_steam_id(test_db):
    """Test getting Steam ID from Discord ID"""
    await test_db.register_user(
        discord_id=123456789,
        steam_id="76561198000000000"
    )

    steam_id = await test_db.get_steam_id(123456789)
    assert steam_id == "76561198000000000"

@pytest.mark.asyncio
async def test_cache_user_games(test_db):
    """Test caching user games"""
    steam_id = "76561198000000000"

    games = [
        {'appid': 570, 'name': 'Dota 2', 'playtime_forever': 10000},
        {'appid': 730, 'name': 'CS:GO', 'playtime_forever': 5000}
    ]

    await test_db.cache_user_games(steam_id, games)

    # Retrieve cached games
    cached_games = await test_db.get_user_games(steam_id)

    assert len(cached_games) == 2
    assert cached_games[0]['appid'] == 570
    assert cached_games[0]['playtime_forever'] == 10000

@pytest.mark.asyncio
async def test_create_game_event(test_db):
    """Test creating a game event"""
    from datetime import datetime, timedelta

    # Register a user first
    await test_db.register_user(
        discord_id=123456789,
        steam_id="76561198000000000"
    )

    scheduled_time = datetime.now() + timedelta(days=1)

    event_id = await test_db.create_game_event(
        guild_id=987654321,
        game_name="Dota 2",
        scheduled_time=scheduled_time,
        created_by=123456789,
        game_appid=570
    )

    assert event_id is not None
    assert event_id > 0

@pytest.mark.asyncio
async def test_price_alerts(test_db):
    """Test price alert system"""
    # Register user
    await test_db.register_user(
        discord_id=123456789,
        steam_id="76561198000000000"
    )

    # Add price alert
    alert_id = await test_db.add_price_alert(
        discord_id=123456789,
        appid=570,
        game_name="Dota 2",
        target_price=9.99,
        current_price=19.99
    )

    assert alert_id is not None

    # Get user alerts
    alerts = await test_db.get_user_alerts(123456789)
    assert len(alerts) == 1
    assert alerts[0]['game_name'] == "Dota 2"
    assert alerts[0]['target_price'] == 9.99

@pytest.mark.asyncio
async def test_lfg_posts(test_db):
    """Test LFG post creation and retrieval"""
    # Register user
    await test_db.register_user(
        discord_id=123456789,
        steam_id="76561198000000000"
    )

    # Create LFG post
    post_id = await test_db.create_lfg_post(
        guild_id=987654321,
        discord_id=123456789,
        game_name="Dota 2",
        description="Need 1 more for ranked",
        players_needed=1
    )

    assert post_id is not None

    # Get active posts
    posts = await test_db.get_active_lfg_posts(987654321)
    assert len(posts) == 1
    assert posts[0]['game_name'] == "Dota 2"
