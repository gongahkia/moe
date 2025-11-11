# ----- required imports -----

from typing import List, Dict, Any, Optional
from src.client import APIClient
from src.cache import get_cache, set_cache
import asyncio

# ----- class definitions -----

class PriceTracker:
    """Track game prices and deals using IsThereAnyDeal API"""

    def __init__(self):
        self.base_url = "https://api.isthereanydeal.com"
        # IsThereAnyDeal doesn't require API key for basic features

    async def get_game_price(self, game_title: str) -> Optional[Dict[str, Any]]:
        """Get current price for a game"""
        cache_key = f"price:{game_title}"
        if cached := await get_cache(cache_key):
            return cached

        try:
            # First, search for the game to get its plain ID
            async with APIClient() as client:
                search_data = await client.get(
                    f"{self.base_url}/v01/search/search/",
                    params={'q': game_title, 'limit': 1}
                )

                if not search_data.get('data', {}).get('results'):
                    return None

                plain_id = search_data['data']['results'][0]['plain']

                # Get price data
                price_data = await client.get(
                    f"{self.base_url}/v01/game/prices/",
                    params={
                        'plains': plain_id,
                        'region': 'us',
                        'country': 'US'
                    }
                )

                result = price_data.get('data', {}).get(plain_id, {})
                await set_cache(cache_key, result, ttl=900)  # Cache for 15 minutes
                return result

        except Exception as e:
            print(f"Error fetching price data: {e}")
            return None

    async def get_current_deals(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get current game deals"""
        cache_key = f"deals:current:{limit}"
        if cached := await get_cache(cache_key):
            return cached

        try:
            async with APIClient() as client:
                deals = await client.get(
                    f"{self.base_url}/v01/deals/list/",
                    params={
                        'region': 'us',
                        'country': 'US',
                        'limit': limit
                    }
                )

                result = deals.get('data', {}).get('list', [])
                await set_cache(cache_key, result, ttl=900)
                return result

        except Exception as e:
            print(f"Error fetching deals: {e}")
            return []

    async def get_price_history(
        self,
        game_title: str
    ) -> Optional[Dict[str, Any]]:
        """Get historical price data for a game"""
        cache_key = f"price_history:{game_title}"
        if cached := await get_cache(cache_key):
            return cached

        try:
            async with APIClient() as client:
                # Search for game
                search_data = await client.get(
                    f"{self.base_url}/v01/search/search/",
                    params={'q': game_title, 'limit': 1}
                )

                if not search_data.get('data', {}).get('results'):
                    return None

                plain_id = search_data['data']['results'][0]['plain']

                # Get historical data
                history = await client.get(
                    f"{self.base_url}/v01/game/history/",
                    params={
                        'plains': plain_id,
                        'region': 'us'
                    }
                )

                result = history.get('data', {}).get(plain_id, {})
                await set_cache(cache_key, result, ttl=3600)  # Cache for 1 hour
                return result

        except Exception as e:
            print(f"Error fetching price history: {e}")
            return None

    async def check_price_alerts(
        self,
        alerts: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Check if any price alerts should trigger

        Args:
            alerts: List of price alert dicts with game_name, target_price

        Returns:
            List of triggered alerts
        """
        triggered = []

        for alert in alerts:
            game_name = alert.get('game_name')
            target_price = alert.get('target_price')

            if not game_name or target_price is None:
                continue

            current_price_data = await self.get_game_price(game_name)

            if current_price_data:
                # Get lowest current price across all stores
                prices = current_price_data.get('list', [])
                if prices:
                    lowest_price = min(
                        p.get('price_new', float('inf')) for p in prices
                    )

                    if lowest_price <= target_price:
                        triggered.append({
                            **alert,
                            'current_price': lowest_price,
                            'store': prices[0].get('shop', {}).get('name', 'Unknown')
                        })

        return triggered

    async def get_deals_for_games(
        self,
        game_titles: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Get current deals for a specific list of games

        Args:
            game_titles: List of game names

        Returns:
            List of deals for those games
        """
        deals_info = []

        # Fetch price info for each game in parallel
        tasks = [self.get_game_price(title) for title in game_titles]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for title, price_data in zip(game_titles, results):
            if isinstance(price_data, Exception) or not price_data:
                continue

            prices = price_data.get('list', [])
            if not prices:
                continue

            # Find best deal
            best_deal = min(
                prices,
                key=lambda x: x.get('price_new', float('inf'))
            )

            # Check if it's actually a deal (on sale)
            if best_deal.get('price_cut', 0) > 0:
                deals_info.append({
                    'game': title,
                    'original_price': best_deal.get('price_old'),
                    'current_price': best_deal.get('price_new'),
                    'discount_percent': best_deal.get('price_cut'),
                    'store': best_deal.get('shop', {}).get('name', 'Unknown'),
                    'url': best_deal.get('url')
                })

        return deals_info

    def format_deal_message(self, deal: Dict[str, Any]) -> str:
        """Format a deal into a nice Discord message"""
        game = deal.get('game', 'Unknown Game')
        original = deal.get('original_price', 0)
        current = deal.get('current_price', 0)
        discount = deal.get('discount_percent', 0)
        store = deal.get('store', 'Unknown Store')

        return (
            f"**{game}**\n"
            f"💰 ~~${original:.2f}~~ → **${current:.2f}** ({discount}% OFF)\n"
            f"🏪 {store}"
        )

# ----- global price tracker instance -----

price_tracker = PriceTracker()
