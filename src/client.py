# ----- required imports -----

from aiohttp import ClientSession, TCPConnector
from aiohttp_retry import RetryClient, ExponentialRetry
import asyncio

# ----- class definitions -----

class APIClient:
    def __init__(self):
        self.connector = TCPConnector(
            limit=100,
            limit_per_host=20,
            enable_cleanup_closed=True
        )
        self.retry_options = ExponentialRetry(
            attempts=3,
            factor=2,
            statuses={429, 500, 502, 503, 504}
        )

    async def __aenter__(self):
        self.session = ClientSession(connector=self.connector)
        self.retry_client = RetryClient(
            client_session=self.session,
            retry_options=self.retry_options
        )
        return self

    async def __aexit__(self, *args):
        await self.retry_client.close()
        await self.session.close()

    async def get(self, url, params=None):
        async with self.retry_client.get(url, params=params) as response:
            response.raise_for_status()
            return await response.json()