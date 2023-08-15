import asyncio
import psutil
import os
from discord.ext.commands.context import Context
from discord.ext.commands._types import BotT
from discord.ext import commands
from discord.ext.commands import errors


class Events(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.process = psutil.Process(os.getpid())

    @commands.Cog.listener()
    async def on_command_error(self, ctx: Context[BotT], err: Exception):
        if isinstance(err, errors.MissingRequiredArgument) or isinstance(err, errors.BadArgument):
            await ctx.send("arguments are missing.")

        elif isinstance(err, errors.CheckFailure):
            await ctx.send("checks failed.")

        elif isinstance(err, errors.MaxConcurrencyReached):
            await ctx.send("you've reached max capacity of command usage at once, please finish the previous one.")

        elif isinstance(err, errors.CommandOnCooldown):
            await ctx.send(f"this command is on cooldown... try again in {err.retry_after:.2f} seconds.")

        elif isinstance(err, errors.CommandNotFound):
            await ctx.send("that command doesn't exist!")

        elif isinstance(err, errors.NotOwner):
            await ctx.send("the functionality of this command is limited to the owner of this bot.")
        else:
            await ctx.send(f"{err}")


async def setup(client):
    await client.add_cog(Events(client))
