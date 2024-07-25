from os import environ
from asyncio import run
from sys import version
from pathlib import Path
from typing import Literal
from traceback import format_exception
from aiohttp import ClientSession, DummyCookieJar, TCPConnector
from logging import (
    INFO, 
    FileHandler, 
    error as log_error, 
    info as log_info
)

from discord import (
    AllowedMentions, 
    Embed, 
    Intents,
    MemberCacheFlags, 
    Status, 
    utils
)
from dotenv import load_dotenv
from asqlite import create_pool
from discord.ext import commands
from discord.utils import setup_logging

from cogs.core.helpers import membed


# Search for a specific term in this project using Ctrl + Shift + F


class C2C(commands.Bot):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

        # Database and HTTP Connection
        self.pool = None
        self.session = None

        # Misc
        self.games = dict()
        self.time_launch = None

    def log_exception(self, error):
        formatted_traceback = ''.join(format_exception(type(error), error, error.__traceback__))
        log_error(formatted_traceback)

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

        self.pool = await create_pool("C:\\Users\\georg\\Documents\\c2c\\database\\economy.db")

        self.time_launch = utils.utcnow()
        self.session = ClientSession(
            connector=TCPConnector(limit=30, loop=self.loop, limit_per_host=5), 
            cookie_jar=DummyCookieJar(loop=self.loop)
        )

flags = MemberCacheFlags.none()
flags.joined = True

intents = Intents.none()
intents.message_content = True
intents.emojis_and_stickers = True
intents.guild_messages = True
intents.guilds = True
intents.members = True


bot = C2C(
    allowed_mentions=AllowedMentions.none(),
    case_insensitive=True,
    command_prefix=commands.when_mentioned_or(">"),
    intents=intents,
    max_messages=None,
    max_ratelimit_timeout=30.0,
    member_cache_flags=flags,
    owner_ids={992152414566232139, 546086191414509599},
    status=Status.idle,
    strip_after_prefix=True
)


class MyHelp(commands.MinimalHelpCommand):

    def __init__(self) -> None:
        super().__init__()

    async def command_callback(self, ctx: commands.Context, /, *, command: str | None = None) -> None:
        """Shows help about the bot, a command, or a category"""
        async with ctx.typing():
            return await super().command_callback(ctx, command=command)

    async def send_command_help(self, command: commands.Command):
        docstring = command.callback.__doc__ or 'No explanation found for this command.'
        embed = membed(f"## {bot.user.mention} {command.qualified_name}\n```Syntax: {self.get_command_signature(command)}```\n{docstring}")

        alias = command.aliases
        if alias:
            embed.add_field(name="Aliases", value=', '.join(alias))
        embed.set_footer(text="Usage Syntax: <required> [optional]")
        await self.context.send(embed=embed)

    def add_subcommand_formatting(self, command: commands.Command) -> None:
        fmt = '{0} {1} \N{EN DASH} {2}' if command.description else '{0} {1}'
        self.paginator.add_line(fmt.format(bot.user.mention, command.qualified_name, command.description))

    async def send_pages(self):
        await self.context.send(embed=membed(self.paginator.pages[0]))

    async def on_help_command_error(self, ctx: commands.Context, error: commands.CommandError) -> None:
        await ctx.send(str(error.original))


bot.help_command = MyHelp()


cogs = {
    "admin", 
    "ctx_events", 
    "economy", 
    "miscellaneous", 
    "moderation", 
    "slash_events", 
    "tags"
}

classnames = Literal[
    "Economy", 
    "Moderation", 
    "Utility", 
    "Owner", 
    "Tags"
]


def get_cog_name(*, shorthand: str) -> str:
    # Match the shortened name with the full cog name
    matches = [cog for cog in cogs if shorthand.lower() in cog]
    if len(matches) >= 1:
        return matches[0]
    return None


@bot.command(name="test")
async def testit(ctx: commands.Context) -> None:
    embed = Embed()
    embed.title = "Your balance"
    embed.add_field(name="Field 1", value="240,254,794")
    embed.add_field(name="Field 2", value="693,201,329")
    embed.add_field(name="\U0000200b", value="\U0000200b")
    embed.add_field(name="Field 3", value="1,000,000,000")
    embed.add_field(name="Field 4", value="1,000,000,000")
    embed.add_field(name="\U0000200b", value="\U0000200b")
    embed.set_footer(text="This embed is used within DMO!")
    await ctx.send(embed=embed)


@commands.is_owner()
@bot.command(name='reload', aliases=("rl",)) 
async def reload_cog(ctx: commands.Context, cog_input: str) -> None:

    cog_name = get_cog_name(shorthand=cog_input)
    if cog_name is None:
        return await ctx.reply(embed=membed("This extension does not exist."))

    embed = membed()
    try:
        await bot.reload_extension(f"cogs.{cog_name}")
        embed.add_field(name="Reloaded", value=f"cogs/{cog_name}.py")
    except commands.ExtensionNotLoaded:
        embed.description = "That extension has not been loaded in yet."
    except commands.NoEntryPointError:
        embed.description = "The extension does not have a setup function."
    except commands.ExtensionFailed as e:
        bot.log_exception(e)
        embed.description = "The extension failed to load. See the logs for traceback."
    finally:
        await ctx.reply(embed=embed)


@commands.is_owner()
@bot.command(name='unload', aliases=("ul",))
async def unload_cog(ctx: commands.Context, cog_input: str) -> None:

    cog_name = get_cog_name(shorthand=cog_input)
    if cog_name is None:
        return await ctx.reply(embed=membed("This extension does not exist."))
    
    embed = membed()
    try:
        await bot.unload_extension(f"cogs.{cog_name}")
        embed.add_field(name="Unloaded", value=f"cogs/{cog_name}.py")
    except commands.ExtensionNotLoaded:
        embed.description = "That extension has not been loaded in yet."
    
    await ctx.reply(embed=embed)


@commands.is_owner()
@bot.command(name='load', aliases=("l",))
async def load_cog(ctx: commands.Context, cog_input: str) -> None:
    
    cog_name = get_cog_name(shorthand=cog_input)
    if cog_name is None:
        return await ctx.reply(embed=membed("This extension does not exist."))
    
    embed = membed()
    try:
        await bot.load_extension(f"cogs.{cog_name}")
        embed.add_field(name="Loaded", value=f"cogs/{cog_name}.py")
    except commands.ExtensionAlreadyLoaded:
        embed.description = "That extension is already loaded."
    except commands.NoEntryPointError:
        embed.description = "The extension does not have a setup function."
    except commands.ExtensionFailed as e:
        bot.log_exception(e)
        embed.description = "The extension failed to load. See the logs for traceback."

    await ctx.reply(embed=embed)


async def main():

    setup_logging(
        level=INFO,
        handler=FileHandler(filename='discord.log', encoding='utf-8', mode='w')
    )
    log_info(version)
    load_dotenv()
    
    TOKEN = environ.get("BOT_TOKEN")
    bot.WEBHOOK_URL = environ.get("WEBHOOK_URL")
    bot.GITHUB_TOKEN = environ.get("GITHUB_TOKEN")
    bot.JEYY_API_KEY = environ.get("JEYY_API_KEY")
    bot.NINJAS_API_KEY = environ.get("NINJAS_API_KEY")
    bot.GOOGLE_CUSTOM_SEARCH_API_KEY = environ.get("GOOGLE_CUSTOM_SEARCH_API_KEY")
    bot.GOOGLE_CUSTOM_SEARCH_ENGINE = environ.get("GOOGLE_CUSTOM_SEARCH_ENGINE")

    await bot.start(TOKEN)


run(main())
