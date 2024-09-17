from io import StringIO
from traceback import format_exc
from textwrap import indent, dedent
from contextlib import redirect_stdout
from typing import Any, Optional

import asyncio
import discord

from discord.ext import commands

from .core.bot import C2C
from .core.helpers import membed
from .core.constants import CURRENCY


class Admin(commands.Cog):
    """Developer tools relevant to maintainence of the bot. Only available for use by the bot developers."""

    def __init__(self, bot: C2C):
        self.bot = bot
        self._last_result: Optional[Any] = None

    async def cog_check(self, ctx: commands.Context) -> bool:
        return ctx.author.id in self.bot.owner_ids

    async def interaction_check(self, interaction: discord.Interaction[C2C]):
        if interaction.user.id in self.bot.owner_ids:
            return True
        await interaction.response.send_message(
            embed=membed("You do not own this bot.")
        )
        return False

    @staticmethod
    def cleanup_code(content: str) -> str:
        """Automatically removes code blocks from the code."""
        # remove ```py\n```
        if content.startswith("```") and content.endswith("```"):
            return "\n".join(content.split("\n")[1:-1])

        # remove `foo`
        return content.strip("` \n")

    @commands.command(description="Adjust a user's robux directly")
    async def config(
        self,
        ctx: commands.Context,
        configuration: str,
        amount: int,
        user: discord.User | discord.Member = commands.Author,
        medium: str = "wallet"
    ) -> None:
        if configuration.startswith("a"):
            output = f"Added {CURRENCY} **{amount:,}** to {user.name}!"
            query = f"UPDATE accounts SET {medium} = {medium} + ? WHERE userID = ?"

        elif configuration.startswith("r"):
            output = f"Deducted {CURRENCY} **{amount:,}** from {user.name}!"
            query = f"UPDATE accounts SET {medium} = {medium} - ? WHERE userID = ?"

        else:
            output = f"Set {CURRENCY} **{amount:,}** to {user.name}!"
            query = f"UPDATE accounts SET {medium} = ? WHERE userID = ?"

        async with self.bot.pool.acquire() as conn, conn.transaction():
            await conn.execute(query, (amount, user.id))

        await ctx.send(output)

    @commands.command(description="Sync the bot tree for changes", aliases=("sy",))
    async def sync(self, ctx: commands.Context) -> None:
        """Sync the bot's tree globally."""
        await self.bot.tree.sync(guild=None)
        await ctx.send("\U00002705")

    @commands.command(name="eval", description="Evaluates arbitrary code")
    async def evaluate(
        self, ctx: commands.Context, *, script_body: str
    ) -> Optional[discord.Message]:
        """Evaluates arbitrary code."""

        env = {
            "bot": self.bot,
            "ctx": ctx,
            "channel": ctx.channel,
            "author": ctx.author,
            "guild": ctx.guild,
            "message": ctx.message,
            "_": self._last_result,
            "discord": discord,
            "asyncio": asyncio,
        }

        env.update(globals())

        script_body = self.cleanup_code(script_body)
        stdout = StringIO()

        to_compile = f'async def func():\n{indent(script_body, "  ")}'

        try:
            exec(to_compile, env)
        except Exception as e:
            return await ctx.send(f"```py\n{e.__class__.__name__}: {e}\n```")

        func = env["func"]
        try:
            with redirect_stdout(stdout):
                ret = await func()  # return value
        except Exception:
            value = stdout.getvalue()
            await ctx.send(f"```py\n{value}{format_exc()}\n```")
        else:
            value = stdout.getvalue()
            try:
                await ctx.message.add_reaction("\U00002705")
            except discord.HTTPException:
                pass

            if ret is None:
                if value:
                    try:
                        await ctx.send(f"```py\n{value}\n```")
                    except discord.HTTPException:
                        return await ctx.send(
                            embed=membed("Output too long to display.")
                        )
            else:
                self._last_result = ret
                await ctx.send(f"```py\n{value}{ret}\n```")

    @commands.command(description="Sends newlines to clear a channel", aliases=("b",))
    async def blank(self, ctx: commands.Context):
        """Clear out the channel."""
        await ctx.send(f".{'\n'*1900}-# Blanked out the channel.")

    async def send_role_guide(self):
        channel = self.bot.get_partial_messageable(1254883155882672249)
        original = channel.get_partial_message(1254901254530924644)

        role_content_pt1 = (
            """
            # Role Guide
            Roles are similar to ranks or accessories that you can add to your profile.
            There are a few self-assignable roles that you can pick up in <id:customize> by clicking on the buttons.

            There are also roles that are given out based on how active you are within the server on a weekly basis:
            - <@&1190772029830471781>: Given to users that sent at least 50 messages in the last week.
            - <@&1190772182591209492>: Given to users that sent at least 150 messages in the last week.

            Other miscellaneous roles for your knowledge:
            - <@&893550756953735278>: The people who manage the server.
            - <@&1148209142465581098>: The role for a backup account, granted administrator permissions.
            - <@&1273655614085664828>: The role verified server members can obtain.
            - <@&1140197893261758505>: Given to people who had their message on the legacy starboard.
            - <@&1121426143598354452>: Given on a per-user basis, granting certain privileges.
            - <@&1150848144440053780>: Bots that only need read access to bot command channels.
            - <@&1150848206008238151>: Bots that require full read access throughout the server.
            """
        )

        await original.edit(content=dedent(role_content_pt1))

    @commands.command(name="quit", description="Quits the bot gracefully", aliases=("q",))
    async def close(self, ctx: commands.Context) -> None:
        """Quits the bot gracefully."""
        await ctx.send("\U00002705")
        await self.bot.close()


async def setup(bot: C2C):
    """Setup for cog."""
    await bot.add_cog(Admin(bot))
