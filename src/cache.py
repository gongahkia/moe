from aiocache import RedisCache
from aiocache.serializers import JsonSerializer

cache = RedisCache(
    endpoint='localhost',
    port=6379,
    namespace="discord_steam_bot",
    serializer=JsonSerializer(),
    timeout=5
)

async def get_cache(key):
    return await cache.get(key)

async def set_cache(key, value, ttl=3600):
    await cache.set(key, value, ttl=ttl)