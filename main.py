import asyncio
from sys import version, platform
from logging import (
    FileHandler, 
    info as log_info
)

from discord.ext import commands
from discord.utils import setup_logging

from cogs.core.helpers import membed
from cogs.core.bot import C2C


bot = C2C()


# If you're on Windows, starting in aiohttp >3.10, 
# you need to need to override the event loop policy as shown
if platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


cogs = {
    "admin", 
    "context_exceptions", 
    "economy", 
    "interaction_exceptions", 
    "miscellaneous", 
    "moderation", 
    "tags"
}


def get_cog_name(cog_input: str) -> str:
    for cog in cogs:
        if cog_input.lower() in cog:
            return cog
    return None


async def handle_extension(ctx: commands.Context, cog_input: str, action: str):
    cog_name = get_cog_name(cog_input)
    if not cog_name:
        em = membed("Invalid cog name.").add_field(name="Cogs", value=f"{', '.join(cogs)}")
        return await ctx.reply(embed=em)

    embed = membed()
    ext_meth = getattr(bot, f"{action}_extension")

    try:
        await ext_meth(f"cogs.{cog_name}")
        embed.add_field(name=f"{action.title()}ed", value=f"cogs/{cog_name}.py")
    except commands.ExtensionFailed as e:
        bot.log_exception(e)
        embed.description = "The extension failed to load. See the logs for traceback."
    except Exception as e:
        embed.description = e.args[0]
    finally:
        await ctx.reply(embed=embed)


@commands.is_owner()
@bot.command(aliases=("rl",)) 
async def reload(ctx: commands.Context, cog_input: str) -> None:
    await handle_extension(ctx, cog_input, "reload")


@commands.is_owner()
@bot.command(aliases=("ul",))
async def unload(ctx: commands.Context, cog_input: str) -> None:
    await handle_extension(ctx, cog_input, "unload")


@commands.is_owner()
@bot.command(aliases=("l",))
async def load(ctx: commands.Context, cog_input: str) -> None:
    await handle_extension(ctx, cog_input, "load")

async def main():

    setup_logging(handler=FileHandler(filename='discord.log', encoding='utf-8', mode='w'))
    log_info(version)

    await bot.start(bot.TOKEN)


asyncio.run(main())
