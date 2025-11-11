# ----- required imports -----

import sqlite3
import aiosqlite
from typing import Optional, List, Dict, Any
from datetime import datetime
import os

# ----- database initialization -----

DB_PATH = os.getenv('DATABASE_PATH', './data/moe.db')

# ----- database schema -----

SCHEMA = """
-- Users table
CREATE TABLE IF NOT EXISTS users (
    discord_id INTEGER PRIMARY KEY,
    steam_id TEXT UNIQUE NOT NULL,
    steam_username TEXT,
    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    privacy_level TEXT DEFAULT 'public',
    timezone TEXT DEFAULT 'UTC'
);

-- Games cache table
CREATE TABLE IF NOT EXISTS user_games (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    steam_id TEXT NOT NULL,
    appid INTEGER NOT NULL,
    game_name TEXT,
    playtime_forever INTEGER DEFAULT 0,
    last_played TIMESTAMP,
    cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(steam_id, appid),
    FOREIGN KEY (steam_id) REFERENCES users(steam_id) ON DELETE CASCADE
);

-- Scheduled events table
CREATE TABLE IF NOT EXISTS game_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    game_name TEXT,
    game_appid INTEGER,
    scheduled_time TIMESTAMP NOT NULL,
    created_by INTEGER NOT NULL,
    participants TEXT,  -- JSON array of discord IDs
    status TEXT DEFAULT 'upcoming',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES users(discord_id)
);

-- Price tracking table
CREATE TABLE IF NOT EXISTS price_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    discord_id INTEGER NOT NULL,
    appid INTEGER NOT NULL,
    game_name TEXT,
    target_price REAL,
    current_price REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notified BOOLEAN DEFAULT 0,
    FOREIGN KEY (discord_id) REFERENCES users(discord_id) ON DELETE CASCADE
);

-- Achievement tracking table
CREATE TABLE IF NOT EXISTS user_achievements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    steam_id TEXT NOT NULL,
    appid INTEGER NOT NULL,
    achievement_name TEXT NOT NULL,
    achievement_id TEXT NOT NULL,
    unlock_time TIMESTAMP,
    rarity REAL,
    cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(steam_id, appid, achievement_id),
    FOREIGN KEY (steam_id) REFERENCES users(steam_id) ON DELETE CASCADE
);

-- User preferences table
CREATE TABLE IF NOT EXISTS user_preferences (
    discord_id INTEGER PRIMARY KEY,
    notification_type TEXT DEFAULT 'channel',  -- 'dm' or 'channel'
    preferred_genres TEXT,  -- JSON array
    playtime_threshold INTEGER DEFAULT 2,  -- hours to consider actively playing
    language TEXT DEFAULT 'en-US',
    FOREIGN KEY (discord_id) REFERENCES users(discord_id) ON DELETE CASCADE
);

-- Server settings table
CREATE TABLE IF NOT EXISTS server_settings (
    guild_id INTEGER PRIMARY KEY,
    notification_channel_id INTEGER,
    game_night_voice_channel_id INTEGER,
    min_players INTEGER DEFAULT 2,
    language TEXT DEFAULT 'en-US',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- LFG (Looking for Group) posts table
CREATE TABLE IF NOT EXISTS lfg_posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    discord_id INTEGER NOT NULL,
    appid INTEGER,
    game_name TEXT NOT NULL,
    description TEXT,
    players_needed INTEGER DEFAULT 1,
    scheduled_time TIMESTAMP,
    status TEXT DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (discord_id) REFERENCES users(discord_id)
);

-- Game metadata cache
CREATE TABLE IF NOT EXISTS game_metadata (
    appid INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    genres TEXT,  -- JSON array
    categories TEXT,  -- JSON array
    multiplayer_types TEXT,  -- JSON array: coop, competitive, multiplayer, local_coop
    release_date TEXT,
    metacritic_score INTEGER,
    steam_rating REAL,
    cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

# ----- class definitions -----

class Database:
    """Database manager for Moe bot"""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._ensure_data_dir()

    def _ensure_data_dir(self):
        """Create data directory if it doesn't exist"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

    async def initialize(self):
        """Initialize database with schema"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.executescript(SCHEMA)
            await db.commit()

    # ----- User Management -----

    async def register_user(self, discord_id: int, steam_id: str, steam_username: str = None) -> bool:
        """Register a new user"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """INSERT INTO users (discord_id, steam_id, steam_username)
                       VALUES (?, ?, ?)
                       ON CONFLICT(discord_id) DO UPDATE SET
                           steam_id=excluded.steam_id,
                           steam_username=excluded.steam_username,
                           updated_at=CURRENT_TIMESTAMP""",
                    (discord_id, steam_id, steam_username)
                )
                await db.commit()
                return True
        except Exception as e:
            print(f"Error registering user: {e}")
            return False

    async def unregister_user(self, discord_id: int) -> bool:
        """Unregister a user"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("DELETE FROM users WHERE discord_id = ?", (discord_id,))
                await db.commit()
                return True
        except Exception as e:
            print(f"Error unregistering user: {e}")
            return False

    async def get_user(self, discord_id: int) -> Optional[Dict[str, Any]]:
        """Get user by Discord ID"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM users WHERE discord_id = ?", (discord_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def get_steam_id(self, discord_id: int) -> Optional[str]:
        """Get Steam ID for a Discord user"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT steam_id FROM users WHERE discord_id = ?", (discord_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else None

    async def get_users_by_steam_ids(self, steam_ids: List[str]) -> List[Dict[str, Any]]:
        """Get multiple users by Steam IDs"""
        placeholders = ','.join('?' * len(steam_ids))
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                f"SELECT * FROM users WHERE steam_id IN ({placeholders})", steam_ids
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    # ----- Game Cache Management -----

    async def cache_user_games(self, steam_id: str, games: List[Dict[str, Any]]):
        """Cache user's game library"""
        async with aiosqlite.connect(self.db_path) as db:
            # Clear old cache
            await db.execute("DELETE FROM user_games WHERE steam_id = ?", (steam_id,))

            # Insert new games
            for game in games:
                await db.execute(
                    """INSERT INTO user_games (steam_id, appid, game_name, playtime_forever, last_played)
                       VALUES (?, ?, ?, ?, ?)""",
                    (
                        steam_id,
                        game.get('appid'),
                        game.get('name'),
                        game.get('playtime_forever', 0),
                        game.get('rtime_last_played')
                    )
                )
            await db.commit()

    async def get_user_games(self, steam_id: str) -> List[Dict[str, Any]]:
        """Get cached user games"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM user_games WHERE steam_id = ? ORDER BY playtime_forever DESC",
                (steam_id,)
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    # ----- Game Events Management -----

    async def create_game_event(
        self,
        guild_id: int,
        game_name: str,
        scheduled_time: datetime,
        created_by: int,
        game_appid: int = None,
        participants: List[int] = None
    ) -> int:
        """Create a new game event"""
        import json
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """INSERT INTO game_events
                   (guild_id, game_name, game_appid, scheduled_time, created_by, participants)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    guild_id,
                    game_name,
                    game_appid,
                    scheduled_time.isoformat(),
                    created_by,
                    json.dumps(participants or [])
                )
            )
            await db.commit()
            return cursor.lastrowid

    async def get_upcoming_events(self, guild_id: int) -> List[Dict[str, Any]]:
        """Get upcoming events for a guild"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """SELECT * FROM game_events
                   WHERE guild_id = ? AND status = 'upcoming' AND scheduled_time > datetime('now')
                   ORDER BY scheduled_time ASC""",
                (guild_id,)
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def update_event_status(self, event_id: int, status: str):
        """Update event status"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE game_events SET status = ? WHERE id = ?",
                (status, event_id)
            )
            await db.commit()

    # ----- Price Alerts Management -----

    async def add_price_alert(
        self,
        discord_id: int,
        appid: int,
        game_name: str,
        target_price: float = None,
        current_price: float = None
    ) -> int:
        """Add a price alert"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """INSERT INTO price_alerts
                   (discord_id, appid, game_name, target_price, current_price)
                   VALUES (?, ?, ?, ?, ?)""",
                (discord_id, appid, game_name, target_price, current_price)
            )
            await db.commit()
            return cursor.lastrowid

    async def get_user_alerts(self, discord_id: int) -> List[Dict[str, Any]]:
        """Get user's price alerts"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM price_alerts WHERE discord_id = ? AND notified = 0",
                (discord_id,)
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def get_all_active_alerts(self) -> List[Dict[str, Any]]:
        """Get all active price alerts"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM price_alerts WHERE notified = 0"
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def mark_alert_notified(self, alert_id: int):
        """Mark price alert as notified"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE price_alerts SET notified = 1 WHERE id = ?",
                (alert_id,)
            )
            await db.commit()

    # ----- LFG Posts Management -----

    async def create_lfg_post(
        self,
        guild_id: int,
        discord_id: int,
        game_name: str,
        description: str = None,
        players_needed: int = 1,
        appid: int = None,
        scheduled_time: datetime = None
    ) -> int:
        """Create a Looking For Group post"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """INSERT INTO lfg_posts
                   (guild_id, discord_id, game_name, description, players_needed, appid, scheduled_time)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    guild_id,
                    discord_id,
                    game_name,
                    description,
                    players_needed,
                    appid,
                    scheduled_time.isoformat() if scheduled_time else None
                )
            )
            await db.commit()
            return cursor.lastrowid

    async def get_active_lfg_posts(self, guild_id: int) -> List[Dict[str, Any]]:
        """Get active LFG posts for a guild"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """SELECT * FROM lfg_posts
                   WHERE guild_id = ? AND status = 'active'
                   ORDER BY created_at DESC""",
                (guild_id,)
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def close_lfg_post(self, post_id: int):
        """Close an LFG post"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE lfg_posts SET status = 'closed' WHERE id = ?",
                (post_id,)
            )
            await db.commit()

    # ----- Game Metadata Cache -----

    async def cache_game_metadata(self, appid: int, metadata: Dict[str, Any]):
        """Cache game metadata"""
        import json
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """INSERT INTO game_metadata
                   (appid, name, genres, categories, multiplayer_types, release_date, metacritic_score, steam_rating)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(appid) DO UPDATE SET
                       name=excluded.name,
                       genres=excluded.genres,
                       categories=excluded.categories,
                       multiplayer_types=excluded.multiplayer_types,
                       release_date=excluded.release_date,
                       metacritic_score=excluded.metacritic_score,
                       steam_rating=excluded.steam_rating,
                       cached_at=CURRENT_TIMESTAMP""",
                (
                    appid,
                    metadata.get('name'),
                    json.dumps(metadata.get('genres', [])),
                    json.dumps(metadata.get('categories', [])),
                    json.dumps(metadata.get('multiplayer_types', [])),
                    metadata.get('release_date'),
                    metadata.get('metacritic_score'),
                    metadata.get('steam_rating')
                )
            )
            await db.commit()

    async def get_game_metadata(self, appid: int) -> Optional[Dict[str, Any]]:
        """Get cached game metadata"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM game_metadata WHERE appid = ?", (appid,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    import json
                    data = dict(row)
                    data['genres'] = json.loads(data.get('genres', '[]'))
                    data['categories'] = json.loads(data.get('categories', '[]'))
                    data['multiplayer_types'] = json.loads(data.get('multiplayer_types', '[]'))
                    return data
                return None

    # ----- User Preferences -----

    async def set_user_preferences(
        self,
        discord_id: int,
        notification_type: str = None,
        preferred_genres: List[str] = None,
        playtime_threshold: int = None,
        language: str = None
    ):
        """Set user preferences"""
        import json
        async with aiosqlite.connect(self.db_path) as db:
            updates = []
            values = []

            if notification_type:
                updates.append("notification_type = ?")
                values.append(notification_type)
            if preferred_genres is not None:
                updates.append("preferred_genres = ?")
                values.append(json.dumps(preferred_genres))
            if playtime_threshold is not None:
                updates.append("playtime_threshold = ?")
                values.append(playtime_threshold)
            if language:
                updates.append("language = ?")
                values.append(language)

            if updates:
                values.append(discord_id)
                await db.execute(
                    f"""INSERT INTO user_preferences (discord_id) VALUES (?)
                        ON CONFLICT(discord_id) DO UPDATE SET {', '.join(updates)}""",
                    values
                )
                await db.commit()

    async def get_user_preferences(self, discord_id: int) -> Optional[Dict[str, Any]]:
        """Get user preferences"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM user_preferences WHERE discord_id = ?", (discord_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    import json
                    data = dict(row)
                    data['preferred_genres'] = json.loads(data.get('preferred_genres', '[]'))
                    return data
                return None

# ----- global database instance -----

db = Database()
