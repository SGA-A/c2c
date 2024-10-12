import asyncio
import logging
from sys import version

from aiohttp import ClientSession, DummyCookieJar
from asqlite import create_pool
from discord.utils import setup_logging


async def main():
    file_handler = logging.FileHandler(
        filename="discord.log",
        encoding="utf-8",
        mode="w"
    )
    setup_logging(handler=file_handler)
    logging.info(version)

    from src import admin, economy, miscellaneous, moderation, tags

    initial_exts = [admin, economy, miscellaneous, moderation, tags]

    from .core.bot import C2C

    async with ClientSession(cookie_jar=DummyCookieJar()) as session:
        async with create_pool(".\\database\\economy.db") as pool:
            async with C2C(pool, session, initial_exts) as client:
                await client.start(client.token)


asyncio.run(main())
