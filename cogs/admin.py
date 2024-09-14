from re import findall
from io import StringIO
from traceback import format_exc
from textwrap import indent, dedent
from contextlib import redirect_stdout
from typing import Any, Optional

import asyncio
import discord

from discord import app_commands
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
        if ctx.author.id in self.bot.owner_ids:
            return True
        return False

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

    @commands.command(
        name="uptime",
        description="Returns the time the bot has been active for",
        aliases=("u",)
    )
    async def uptime(self, ctx: commands.Context):
        """Returns uptime in terms of days, hours, minutes and seconds"""
        diff = discord.utils.utcnow() - self.bot.time_launch
        minutes, seconds = divmod(diff.total_seconds(), 60)
        hours, minutes = divmod(minutes, 60)
        days, hours = divmod(hours, 24)

        uptime = (
            f"{int(days)} days, {int(hours)} hours, "
            f"{int(minutes)} minutes and {int(seconds)} seconds."
        )
        await ctx.reply(content=uptime)

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

    @commands.command(description="Update the rules channel for cc", aliases=("ur",))
    async def urules(self, _: commands.Context):
        """Push an update to the rules channel."""
        channel = self.bot.get_partial_messageable(902138223571116052)
        original = channel.get_partial_message(1245691538319736863)

        rule_content = (
            "1. <:comfyCat:1263920108015849593> **Be Respectful!** "
            "Treat others the way you would want to be treated, and avoid offensive language or behaviour.\n"
            "2. <:pepeBlanket:1263926092465573939> **Be mindful of others!** "
            "Refrain from excessive messages, links, or images that disrupt the flow of conversation.\n"
            "3. <:Thread:1263923709203320955> **Stay on topic.** "
            "Keep discussions relevant to the designated channels to maintain a focused "
            "and organized environment. Innapropriate content is subject to removal!\n"
            "4. <:Polarizer:1263922970095784007> **Keep our server safe.** "
            "Any form of content that suggests normalization or justification of NSFW content should not escape the "
            "boundaries of <#1160547937420582942>, sanctions will be upheld for such cases.\n"
            "5. <:discordThinking:1263921476369645609> **Adhere to the Terms of Service.** "
            "Abide by Discord's [terms of service](<https://discord.com/terms>) and [community guidelines](<https://discord.com/guidelines/>) at all times.\n\n"
            "**That's all.** Thanks for reading, now go have fun!"
        )

        await original.edit(content=rule_content)

    async def send_role_guide(self):
        channel = self.bot.get_partial_messageable(1254883155882672249)
        original = channel.get_partial_message(1254901254530924644)

        role_content_pt1 = """
            # Role Guide
            Roles are similar to ranks or accessories that you can add to your profile.
            There are a few self-assignable roles that you can pick up in <id:customize> by clicking on the buttons.

            There are also roles that are given out based on how active you are within the server on a weekly basis:
            - <@&1190772029830471781>: Given to users that sent at least 50 messages in the last week.
            - <@&1190772182591209492>: Given to users that sent at least 150 messages in the last week.

            Other miscellaneous roles for your knowledge:
            - <@&893550756953735278>: The people who manage the server.
            - <@&1148209142465581098>: The role for a backup account, granted administrator permissions.
            - <@&912057500914843680>: Grants administrator permissions over the server.
            - <@&914565377961369632>: The role verified server members can obtain.
            - <@&1140197893261758505>: Given to people who had their message on the legacy starboard.
            - <@&1121426143598354452>: Given on a per-user basis, granting certain privileges.
            - <@&1150848144440053780>: Bots that only need read access to bot command channels.
            - <@&1150848206008238151>: Bots that require full read access throughout the server.
            """

        await original.edit(content=dedent(role_content_pt1))

    @commands.command(description="Update the information channel for cc", aliases=("ui",))
    async def uinfo(self, _: commands.Context):
        """Push to update the welcome and info embed within its respective channel."""
        await self.send_role_guide()

    @commands.command(name="quit", description="Quits the bot gracefully", aliases=("q",))
    async def close(self, ctx: commands.Context) -> None:
        """Quits the bot gracefully."""
        await ctx.send("\U00002705")
        await self.bot.close()

    @app_commands.command(description="Repeat what you typed and mask this command use")
    @app_commands.describe(message="What you want me to say.")
    async def repeat(
        self,
        interaction: discord.Interaction[C2C],
        message: app_commands.Range[str, 1, 2000]
    ) -> None:
        """Repeat what you typed, also converting emojis based on whats inside two equalities."""

        matches = findall(r"<(.*?)>", message)

        for match in matches:
            emoji = discord.utils.get(self.bot.emojis, name=match)
            if emoji:
                message = message.replace(f"<{match}>", f"{emoji}")
                continue
            return await interaction.response.send_message("Emoji not found.", ephemeral=True)

        await interaction.channel.send(message)
        await interaction.response.send_message("\U00002705", ephemeral=True)


async def setup(bot: C2C):
    """Setup for cog."""
    await bot.add_cog(Admin(bot))
