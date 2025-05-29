# ----- now deprecated -----

# ----- required imports -----

import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import timedelta
import asyncpg
import aiohttp
from redis.asyncio import Redis

# ----- logger setup -----

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('BotOptimizations')

# ----- class definitions -----

class DatabaseConnectionPool:

    def __init__(self, dsn: str, max_size: int = 20):
        self.dsn = dsn
        self.max_size = max_size
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self):
        self.pool = await asyncpg.create_pool(
            dsn=self.dsn,
            min_size=5,
            max_size=self.max_size,
            command_timeout=60,
            server_settings={
                'application_name': 'discord-steam-bot',
                'statement_timeout': '15000'
            }
        )
        logger.info(f"Initialized DB pool with {self.max_size} connections")

    async def fetch_batch(self, query: str, args_list: List[List[Any]]) -> List[asyncpg.Record]:
        if not self.pool:
            raise RuntimeError("Database pool not initialized")

        async with self.pool.acquire() as conn:
            stmt = await conn.prepare(query)
            return await stmt.fetch(*args_list)

    async def execute_batch(self, query: str, args_list: List[List[Any]]):
        if not self.pool:
            raise RuntimeError("Database pool not initialized")

        async with self.pool.acquire() as conn:
            async with conn.transaction():
                await conn.executemany(query, args_list)

    async def close(self):
        if self.pool:
            await self.pool.close()
            logger.info("Database pool closed")

class SteamAPIOptimizer:
    
    def __init__(self, api_key: str, redis: Redis):
        self.base_url = "https://api.steampowered.com"
        self.api_key = api_key
        self.redis = redis
        self.session: Optional[aiohttp.ClientSession] = None
        self.rate_limit = 200  
        self.window_size = 300  

    async def create_session(self):
        self.session = aiohttp.ClientSession(
            base_url=self.base_url,
            timeout=aiohttp.ClientTimeout(total=30),
            headers={'Accept': 'application/json'}
        )

    async def fetch_player_summaries_batch(self, steam_ids: List[str]) -> Dict[str, Any]:

        if not self.session:
            raise RuntimeError("HTTP session not initialized")
        current = await self.redis.incr('steam:rate_limit')
        if current == 1:
            await self.redis.expire('steam:rate_limit', self.window_size)
        if current > self.rate_limit:
            raise RuntimeError("Steam API rate limit exceeded")
        url = "/ISteamUser/GetPlayerSummaries/v2/"
        params = {
            'key': self.api_key,
            'steamids': ','.join(steam_ids)
        }

        async with self.session.get(url, params=params) as response:
            response.raise_for_status()
            return await response.json()

    async def fetch_games_batch(self, steam_ids: List[str]) -> Dict[str, List[Dict]]:
        if not self.session:
            raise RuntimeError("HTTP session not initialized")

        tasks = []
        for steam_id in steam_ids:
            url = "/IPlayerService/GetOwnedGames/v1/"
            params = {
                'key': self.api_key,
                'steamid': steam_id,
                'include_appinfo': True,
                'include_played_free_games': True
            }
            tasks.append(self._fetch_with_retry(url, params))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        return {steam_id: result for steam_id, result in zip(steam_ids, results)}

    async def _fetch_with_retry(self, url: str, params: Dict, max_retries: int = 3) -> Any:
        for attempt in range(max_retries):
            try:
                async with self.session.get(url, params=params) as response:
                    response.raise_for_status()
                    return await response.json()
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                if attempt == max_retries - 1:
                    raise
                wait = 2 ** attempt + 0.1
                logger.warning(f"Retry {attempt+1} for {url} after {wait}s")
                await asyncio.sleep(wait)

    async def close(self):
        if self.session:
            await self.session.close()
            logger.info("HTTP session closed")

class CombinedOptimizer:
    
    def __init__(self, db_config: Dict, steam_api_key: str, redis_url: str):
        self.db_pool = DatabaseConnectionPool(**db_config)
        self.redis = Redis.from_url(redis_url, decode_responses=True)
        self.steam_client = SteamAPIOptimizer(steam_api_key, self.redis)

    async def initialize(self):
        await self.db_pool.connect()
        await self.steam_client.create_session()
        await self.redis.ping()  # Test Redis connection

    async def shutdown(self):
        await self.db_pool.close()
        await self.steam_client.close()
        await self.redis.close()

    async def update_player_data(self, steam_ids: List[str]):
        summary_task = self.steam_client.fetch_player_summaries_batch(steam_ids)
        games_task = self.steam_client.fetch_games_batch(steam_ids)
        summaries, games = await asyncio.gather(summary_task, games_task)
        summary_insert = """
            INSERT INTO player_summaries 
            (steam_id, username, avatar, last_updated)
            VALUES ($1, $2, $3, NOW())
            ON CONFLICT (steam_id) DO UPDATE SET
                username = EXCLUDED.username,
                avatar = EXCLUDED.avatar,
                last_updated = NOW()
        """
        game_insert = """
            INSERT INTO player_games
            (steam_id, appid, playtime, last_played)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (steam_id, appid) DO UPDATE SET
                playtime = EXCLUDED.playtime,
                last_played = EXCLUDED.last_played
        """
        summary_args = [
            (p['steamid'], p['personaname'], p['avatarfull'])
            for p in summaries['response']['players']
        ]
        game_args = []
        for steam_id in games:
            for game in games[steam_id].get('games', []):
                game_args.append((
                    steam_id,
                    game['appid'],
                    game.get('playtime_forever', 0),
                    game.get('rtime_last_played', None)
                ))
        await self.db_pool.execute_batch(summary_insert, summary_args)
        await self.db_pool.execute_batch(game_insert, game_args)
        logger.info(f"Updated {len(summary_args)} players and {len(game_args)} games")

# ----- execution code -----

async def main():
    config = {
        'db_config': {
            'dsn': 'postgres://user:pass@localhost:5432/steam_bot',
            'max_size': 15
        },
        'steam_api_key': 'YOUR_STEAM_KEY',
        'redis_url': 'redis://localhost:6379'
    }
    optimizer = CombinedOptimizer(**config)
    try:
        await optimizer.initialize()
        steam_ids = [f"7656119800000000{i:02d}" for i in range(1, 101)]
        await optimizer.update_player_data(steam_ids)
    finally:
        await optimizer.shutdown()

if __name__ == '__main__':
    asyncio.run(main())