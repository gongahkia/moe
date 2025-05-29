from cache import get_cache, set_cache
from client import APIClient
import os

STEAM_KEY = os.getenv('STEAM_API_KEY')

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