import asyncio
from sys import version
from logging import FileHandler, info as log_info

from asqlite import create_pool
from discord.utils import setup_logging


async def main():
    file_handler = FileHandler(filename="discord.log", encoding="utf-8", mode="w")
    setup_logging(handler=file_handler)
    log_info(version)

    from src import admin, economy, miscellaneous, moderation, tags

    initial_exts = [admin, economy, miscellaneous, moderation, tags]

    from .core.bot import C2C

    pool = await create_pool(".\\database\\economy.db")
    client = C2C(pool, initial_exts)

    await client.start(client.token)


asyncio.run(main())
