import json
import logging

import winloop
from aiohttp import ClientSession, DummyCookieJar
from asqlite import create_pool
from discord.utils import setup_logging


async def main():
    with open(".\\config.json", "r") as f:
        config: dict[str, str] = json.load(f)

    setup_logging(handler=logging.FileHandler("discord.log", "w"))

    from src import admin, economy, miscellaneous, moderation, tags
    initial_exts = [admin, economy, miscellaneous, moderation, tags]

    from .core.bot import C2C

    async with ClientSession(cookie_jar=DummyCookieJar()) as session:
        async with create_pool(".\\database\\economy.db") as pool:
            async with C2C(pool, config, session, initial_exts) as client:
                await client.start(config["client_token"])


winloop.run(main())
