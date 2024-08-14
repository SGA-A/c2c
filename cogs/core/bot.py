from pathlib import Path
from traceback import format_exception
from aiohttp import ClientSession, TCPConnector, DummyCookieJar
from json import load as json_load
from logging import error as logging_error

import discord
from discord import app_commands
from discord.ext import commands
from asqlite import create_pool


class C2C(commands.Bot):
    def __init__(self) -> None:
        flags = discord.MemberCacheFlags.none()
        flags.joined = True

        intents = discord.Intents.none()
        intents.message_content = True
        intents.emojis_and_stickers = True
        intents.guild_messages = True
        intents.guilds = True
        intents.members = True

        allowed_mentions = discord.AllowedMentions.none()

        with open('.\\config.json', 'r') as file:
            config: dict = json_load(file)
            for k, v in config.items():
                setattr(self, k, v)

        super().__init__(
            allowed_mentions=allowed_mentions,
            allowed_contexts=app_commands.AppCommandContext(guild=True),
            allowed_installs=app_commands.AppInstallationType(guild=True),
            case_insensitive=True,
            command_prefix=commands.when_mentioned_or(">"),
            intents=intents,
            max_messages=None,
            member_cache_flags=flags,
            owner_ids={992152414566232139, 546086191414509599},
            status=discord.Status.idle,
            strip_after_prefix=True
        )

        # Database and HTTP Connection
        self.pool = None
        self.session = None

        # Misc
        self.games = dict()
        self.time_launch = discord.utils.utcnow()

    def log_exception(self, error: Exception):
        formatted_traceback = ''.join(format_exception(type(error), error, error.__traceback__))
        logging_error(formatted_traceback)

    async def close(self):
        await self.pool.close()
        await self.session.close()
        await super().close()

    async def setup_hook(self):
        for file in Path("cogs").glob("**/*.py"):
            if "core" in file.parts:
                continue

            *tree, _ = file.parts
            try:
                await self.load_extension(f"{".".join(tree)}.{file.stem}")
            except commands.ExtensionError as e:
                self.log_exception(e)

        self.pool = await create_pool(".\\database\\economy.db")
        self.session = ClientSession(
            connector=TCPConnector(limit=30, loop=self.loop, limit_per_host=5), 
            cookie_jar=DummyCookieJar(loop=self.loop)
        )