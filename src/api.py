# ----- required imports -----

from src.cache import get_cache, set_cache
from src.client import APIClient
import os

# ----- environment initialization -----

STEAM_KEY = os.getenv('STEAM_API_KEY')

# ----- class definitions -----

class SteamAPI:
    @staticmethod
    async def get_owned_games(steam_id):
        cache_key = f"steam_games:{steam_id}"
        if cached := await get_cache(cache_key):
            return cached
        
        async with APIClient() as client:
            data = await client.get(
                "https://api.steampowered.com/IPlayerService/GetOwnedGames/v1/",
                params={
                    'key': STEAM_KEY,
                    'steamid': steam_id,
                    'include_appinfo': 1,
                    'include_played_free_games': 0
                }
            )
        games = data['response'].get('games', [])
        await set_cache(cache_key, games)
        return games

    @staticmethod
    async def get_player_summaries(steam_ids):
        cache_key = f"player_summaries:{','.join(steam_ids)}"
        if cached := await get_cache(cache_key):
            return cached

        async with APIClient() as client:
            data = await client.get(
                "https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/",
                params={'key': STEAM_KEY, 'steamids': ','.join(steam_ids)}
            )

        players = data['response']['players']
        await set_cache(cache_key, players, ttl=300)
        return players

    @staticmethod
    async def get_game_details(appid: int):
        """Get detailed game information from Steam Store API"""
        cache_key = f"game_details:{appid}"
        if cached := await get_cache(cache_key):
            return cached

        async with APIClient() as client:
            try:
                data = await client.get(
                    f"https://store.steampowered.com/api/appdetails",
                    params={'appids': appid}
                )
                if str(appid) in data and data[str(appid)]['success']:
                    game_data = data[str(appid)]['data']
                    await set_cache(cache_key, game_data, ttl=86400)  # Cache for 24 hours
                    return game_data
            except Exception as e:
                print(f"Error fetching game details for {appid}: {e}")
        return None

    @staticmethod
    async def get_player_achievements(steam_id: str, appid: int):
        """Get player achievements for a specific game"""
        cache_key = f"achievements:{steam_id}:{appid}"
        if cached := await get_cache(cache_key):
            return cached

        async with APIClient() as client:
            try:
                data = await client.get(
                    "https://api.steampowered.com/ISteamUserStats/GetPlayerAchievements/v1/",
                    params={
                        'key': STEAM_KEY,
                        'steamid': steam_id,
                        'appid': appid
                    }
                )
                achievements = data.get('playerstats', {}).get('achievements', [])
                await set_cache(cache_key, achievements, ttl=3600)
                return achievements
            except Exception as e:
                print(f"Error fetching achievements: {e}")
                return []

    @staticmethod
    async def get_recently_played_games(steam_id: str):
        """Get recently played games for a user"""
        cache_key = f"recent_games:{steam_id}"
        if cached := await get_cache(cache_key):
            return cached

        async with APIClient() as client:
            data = await client.get(
                "https://api.steampowered.com/IPlayerService/GetRecentlyPlayedGames/v1/",
                params={
                    'key': STEAM_KEY,
                    'steamid': steam_id
                }
            )
        games = data['response'].get('games', [])
        await set_cache(cache_key, games, ttl=300)  # Cache for 5 minutes
        return games

    @staticmethod
    async def resolve_vanity_url(vanity_url: str) -> str:
        """Resolve Steam vanity URL to Steam ID"""
        cache_key = f"vanity:{vanity_url}"
        if cached := await get_cache(cache_key):
            return cached

        async with APIClient() as client:
            data = await client.get(
                "https://api.steampowered.com/ISteamUser/ResolveVanityURL/v1/",
                params={
                    'key': STEAM_KEY,
                    'vanityurl': vanity_url
                }
            )

        if data['response']['success'] == 1:
            steam_id = data['response']['steamid']
            await set_cache(cache_key, steam_id, ttl=86400)
            return steam_id
        return None