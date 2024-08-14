"""The administrative cog. Only for use by the bot owners."""
from re import findall
from io import StringIO
from traceback import format_exc
from textwrap import indent, dedent
from contextlib import redirect_stdout
from typing import Any, Literal

import asyncio
import discord

from discord import app_commands
from discord.ext import commands

from .core.bot import C2C
from .core.helpers import membed
from .core.constants import CURRENCY, LIMITED_CONTEXTS, LIMITED_INSTALLS


GUILD_MESSAGEABLE = (
    discord.ForumChannel | 
    discord.TextChannel | 
    discord.VoiceChannel | 
    discord.StageChannel
)


class Admin(commands.Cog):
    """Developer tools relevant to maintainence of the bot. Only available for use by the bot developers."""
    def __init__(self, bot: C2C):
        self.bot = bot
        self._last_result: Any | None = None

    async def cog_check(self, ctx: commands.Context) -> bool:
        if ctx.author.id in self.bot.owner_ids:
            return True
        return False

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id in self.bot.owner_ids:
            return True
        await interaction.response.send_message(embed=membed("You do not own this bot."))
        return False

    @staticmethod
    def cleanup_code(content: str) -> str:
        """Automatically removes code blocks from the code."""
        # remove ```py\n```
        if content.startswith('```') and content.endswith('```'):
            return '\n'.join(content.split('\n')[1:-1])

        # remove `foo`
        return content.strip('` \n')

    @commands.command(name='uptime', description='Returns the time the bot has been active for', aliases=('u',))
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

    @app_commands.command(description="Adjust a user's robux directly")
    @app_commands.describe(
        configuration='Whether to add, remove, or specify robux.',
        amount='The amount of robux to modify. Supports Shortcuts (exponents only).',
        user='The member to modify the balance of. Defaults to you.',
        is_private='Whether or not the response is only visible to you. Defaults to False.',
        medium='The type of balance to modify. Defaults to the wallet.'
    )
    @app_commands.allowed_contexts(**LIMITED_CONTEXTS)
    @app_commands.allowed_installs(**LIMITED_INSTALLS)
    async def config(
        self, 
        interaction: discord.Interaction,
        configuration: Literal["add", "remove", "make"], 
        amount: int,
        user: discord.User | None = None,
        is_private: bool = False,
        medium: Literal["wallet", "bank"] = "wallet"
    ) -> None:
        """Generates or deducts a given amount of robux to the mentioned user."""

        user = user or interaction.user
        embed = membed()

        if configuration.startswith("a"):
            embed.description = f"Added {CURRENCY} **{amount:,}** to {user.mention}!"
            query = f"UPDATE accounts SET {medium} = {medium} + $0 WHERE userID = $1"

        elif configuration.startswith("r"):
            embed.description = f"Deducted {CURRENCY} **{amount:,}** from {user.mention}!"
            query = f"UPDATE accounts SET {medium} = {medium} - $0 WHERE userID = $1"

        else:
            embed.description = f"Set {CURRENCY} **{amount:,}** to {user.mention}!"
            query = f"UPDATE accounts SET {medium} = $0 WHERE userID = $1"

        async with self.bot.pool.acquire() as conn, conn.transaction():
            await conn.execute(query, amount, user.id)

        await interaction.response.send_message(embed=embed, ephemeral=is_private)

    @commands.command(description='Sync the bot tree for changes', aliases=("sy",))
    async def sync(self, ctx: commands.Context) -> None:
        """Sync the bot's tree to either the guild or globally, varies from time to time."""
        await self.bot.tree.sync(guild=None)

        self.bot.fetched_tree = True
        await ctx.send("\U00002705")

    @commands.command(name='eval', description='Evaluates arbitrary code')
    async def evaluate(self, ctx: commands.Context, *, script_body: str) -> None | discord.Message:
        """Evaluates arbitrary code."""

        env = {
            'bot': self.bot,
            'ctx': ctx,
            'channel': ctx.channel,
            'author': ctx.author,
            'guild': ctx.guild,
            'message': ctx.message,
            '_': self._last_result,
            'discord': discord,
            'asyncio': asyncio
        }

        env.update(globals())

        script_body = self.cleanup_code(script_body)
        stdout = StringIO()

        to_compile = f'async def func():\n{indent(script_body, "  ")}'

        try:
            exec(to_compile, env)
        except Exception as e:
            return await ctx.send(f'```py\n{e.__class__.__name__}: {e}\n```')

        func = env['func']
        try:
            with redirect_stdout(stdout):
                ret = await func()  # return value
        except Exception:
            value = stdout.getvalue()
            await ctx.send(f'```py\n{value}{format_exc()}\n```')
        else:
            value = stdout.getvalue()
            try:
                await ctx.message.add_reaction('\U00002705')
            except discord.HTTPException:
                pass

            if ret is None:  # if nothing is returned
                if value:
                    try:
                        await ctx.send(f'```py\n{value}\n```')
                    except discord.HTTPException:
                        return await ctx.send(embed=membed("Output too long to display."))
            else:
                self._last_result = ret
                await ctx.send(f'```py\n{value}{ret}\n```')

    @commands.command(description='Sends newlines to clear a channel', aliases=('b',))
    async def blank(self, ctx: commands.Context):
        """Clear out the channel."""
        await ctx.send(
            """
            .
            \n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n
            \n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n
            \n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n
            \n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n
            \n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n
            \n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n
            \n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n
            \n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n
            \n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n
            \n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n
            \n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n
            \n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n
            \n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n
            \n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n
            \n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n
            \n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n
            \n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n
            \n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n
            \n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n
            \n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n
            \n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n
            \n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n
            \n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n
            \n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n
            \n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n
            \n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n
            \n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n
            \n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n
            \n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n
            \n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n
            \n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n
            \n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n
            \n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n
            \n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n
            \n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n
            \n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n
            \n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n
            \n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n
            \n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n
            \n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n
            \n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n
            \n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n
            \n> Blanked out.
            """
        )

    @commands.command(description='Update the rules channel for cc', aliases=('ur',))
    async def urules(self, _: commands.Context):
        """Push an update to the rules channel."""
        original = (
            self.bot.get_partial_messageable(902138223571116052)
            .get_partial_message(1245691538319736863)
        )

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
            "Abide by Discord\'s [terms of service](<https://discord.com/terms>) and [community guidelines](<https://discord.com/guidelines/>) at all times.\n\n"
            "**That's all.** Thanks for reading, now go have fun!"
        )

        await original.edit(content=rule_content)

    async def send_role_guide(self):
        message1 = (
            self.bot.get_partial_messageable(1254883155882672249)
            .get_partial_message(1254901254530924644)
        )

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
            - <@&912057500914843680>: Grants administrator permissions over the server.
            - <@&914565377961369632>: The role verified server members can obtain.
            - <@&1140197893261758505>: Given to people who had their message on the legacy starboard.
            - <@&1121426143598354452>: Given on a per-user basis, granting certain privileges.
            - <@&1150848144440053780>: Bots that only need read access to bot command channels.
            - <@&1150848206008238151>: Bots that require full read access throughout the server.
            """
        )
        
        await message1.edit(content=dedent(role_content_pt1))

    async def send_channel_guide(self):
        message = (
            self.bot.get_partial_messageable(1254882974327898192)
            .get_partial_message(1254901539898921093)
        )
        channel_content_pt1 = (
            """
            # Channel Guide
            We made this because there are some channels that may cause confusion.
            To start, all of the channels that contain the word "theory" in them can be read as a "general" channel:
            > <#1119991877010202744> is equivalent to general
            > <#1145008097300066336> is equivalent to general-2
            > <#1160547937420582942> is equivalent to general-nsfw
            And so on. The theme of the server is "theorized", which is why channels follow this naming convention.

            Apart from these three, most of the channels should be straightforward to understand.
            -# Still lost? Any other queries? Let a <@&893550756953735278> know.
            """
        )

        await message.edit(content=dedent(channel_content_pt1))
    
    async def send_bot_guide(self):
        message = (
            self.bot.get_partial_messageable(1254883337386852503)
            .get_partial_message(1254900969033175072)
        )
        channel_content_pt1 = (
            f"""
            # Meet c2c ({self.bot.user.mention})
            c2c is a private custom bot, exclusive to this server.
            We recently verified the bot meaning it is public, anyone can add it. However, we won't expose the bot to the app directory or bot listing sites.
            Since it's got no other public server, we've decided to drop all internal cooldowns when you run commands. So while every other popular bots cool down, you just get hotter.
            ## What's it all about?
            Here are some of the things that make c2c great.
            - Vast economy system: make money in a simulated game of life, made personalized to your liking
            - Utility functions: a world clock (`@me wc`) and searching images across the internet
            - Fun comamnds: image manipulation on any user, or even ship yourself with another potential partner
            - Global tag system: tag text important to you for later retrieval anywhere on the platform
            - Miscellaneous functionality: anime related commands amongst other useful developer tools
            ## Our mission
            We're always finding new things to add to our bot, to make it better for every single one of you. 
            It's a bespoke bot, tailored to your needs. Anyone in this server can request a feature for the bot and it will get implemented if there's a genuine desire and valid reason behind it.
            -# Message a director for feedback. Your bot, your rules.
            """
        )

        await message.edit(content=dedent(channel_content_pt1))

    @commands.command(description='Update the information channel for cc', aliases=('ui',))
    async def uinfo(self, _: commands.Context):
        """Push to update the welcome and info embed within its respective channel."""
        await self.send_role_guide()

    @commands.command(name='quit', description='Quits the bot gracefully', aliases=('q',))
    async def close(self, ctx: commands.Context) -> None:
        """Quits the bot gracefully."""
        await ctx.send("\U00002705")
        await self.bot.close()

    @app_commands.command(description='Repeat what you typed')
    @app_commands.allowed_installs(**LIMITED_INSTALLS)
    @app_commands.allowed_contexts(**LIMITED_CONTEXTS)
    @app_commands.describe(
        message='What you want me to say.', 
        channel='What channel to send it in.'
    )
    async def repeat(
        self, 
        interaction: discord.Interaction, 
        message: str,
        channel: GUILD_MESSAGEABLE | None = None
    ) -> None:
        """Repeat what you typed, also converting emojis based on whats inside two equalities."""

        matches = findall(r'<(.*?)>', message)

        for match in matches:
            emoji = discord.utils.get(self.bot.emojis, name=match)
            if emoji:
                message = message.replace(f'<{match}>', f"{emoji}")
                continue
            return await interaction.response.send_message(
                ephemeral=True, 
                embed=membed("Could not find that emoji.")
            )

        await interaction.response.send_message(
            ephemeral=True, 
            delete_after=3.0, 
            embed=membed(f"Sent this message to {channel.mention}.")
        )

    @commands.command(description="Dispatch customizable quarterly updates")
    async def hook(self, _: commands.Context):
        pass  # custom command logic goes here


async def setup(bot: C2C):
    """Setup for cog."""
    await bot.add_cog(Admin(bot))
