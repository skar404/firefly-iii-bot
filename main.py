import os
import asyncio
from typing import Dict, Any

import aiohttp
from aiohttp import hdrs
from dotenv import load_dotenv

load_dotenv()

TOKEN: str = os.getenv('token')
HOST: str = os.getenv('host')


async def _requests(method: str, url: str, headers: Dict[str, str], body: Any = None):
    kwargs = {}
    if body:
        kwargs['body'] = body

    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.request(method=method, url=url, **kwargs) as r:
            return await r.json()


async def create_transaction(body: Any):
    await _requests(
        hdrs.METH_POST,
        f'{HOST}api/v1/transactions',
        headers={
            'Authorization' f'Bearer {TOKEN}'
            'accept': 'application/vnd.api+json'
        }
    )


async def main():
    print()


if __name__ == '__main__':
    asyncio.run(main())
