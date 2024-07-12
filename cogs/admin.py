"""The administrative cog. Only for use by the bot owners."""
from re import findall
from io import StringIO
from traceback import format_exc
from textwrap import indent, dedent
from contextlib import redirect_stdout

from typing import (
    Any, 
    Literal,
    Optional 
)

import asyncio
import discord

from discord import app_commands
from discord.ext import commands
from asqlite import Connection as asqlite_Connection

from .core.helpers import membed, determine_exponent
from .core.constants import CURRENCY, LIMITED_CONTEXTS, LIMITED_INSTALLS


class InviteButton(discord.ui.View):
    def __init__(self) -> None:
        super().__init__()

        perms = discord.Permissions(
            read_message_history=True,
            read_messages=True,
            send_messages_in_threads=True,
            send_messages=True,
            manage_channels=True,
            manage_messages=True,
            manage_roles=True,
            manage_threads=True,
            create_instant_invite=True,
            external_emojis=True,
            embed_links=True,
            attach_files=True,
            add_reactions=True,
            connect=True,
            speak=True,
            move_members=True,
            deafen_members=True
        )

        self.add_item(
            discord.ui.Button(
                label="Invite",
                url=discord.utils.oauth_url(
                    client_id=1047572530422108311, 
                    permissions=perms
                )
            )
        )


class Owner(commands.Cog):
    """Developer tools relevant to maintainence of the bot. Only available for use by the bot developers."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._last_result: Optional[Any] = None

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

    @app_commands.command(name="config", description="Adjust a user's robux directly")
    @app_commands.describe(
        configuration='Whether to add, remove, or specify robux.',
        amount='The amount of robux to modify. Supports Shortcuts (exponents only).',
        user='The member to modify the balance of. Defaults to you.',
        is_private='Whether or not the response is only visible to you. Defaults to False.',
        medium='The type of balance to modify. Defaults to the wallet.'
    )
    @app_commands.allowed_contexts(guilds=True)
    @app_commands.allowed_installs(guilds=True)
    async def config(
        self, 
        interaction: discord.Interaction,
        configuration: Literal["add", "remove", "make"], 
        amount: str,
        user: Optional[discord.User],
        is_private: Optional[bool] = False,
        medium: Optional[Literal["wallet", "bank"]] = "wallet"
    ) -> None:
        """Generates or deducts a given amount of robux to the mentioned user."""
        
        user = user or interaction.user
        real_amount = await determine_exponent(
            interaction=interaction, 
            rinput=amount
        )
        if real_amount is None:
            return

        embed = membed()
        if isinstance(real_amount, str):
            embed.description = "Shorthands are not supported here."
            return await interaction.response.send_message(ephemeral=True, embed=embed)

        async with self.bot.pool.acquire() as conn:
            conn: asqlite_Connection

            if configuration.startswith("a"):
                embed.description = f"Added {CURRENCY} **{real_amount:,}** to {user.mention}!"
                query = (
                    f"""
                    UPDATE accounts 
                    SET {medium} = {medium} + $0
                    WHERE userID = $1
                    """
                )

            elif configuration.startswith("r"):
                embed.description = f"Deducted {CURRENCY} **{real_amount:,}** from {user.mention}!"
                query = (
                    f"""
                    UPDATE accounts 
                    SET {medium} = {medium} - $0
                    WHERE userID = $1
                    """
                )

            else:
                embed.description = f"Set {CURRENCY} **{real_amount:,}** to {user.mention}!"
                query = (
                    f"""
                    UPDATE accounts 
                    SET {medium} = $0
                    WHERE userID = $1
                    """
                )

            await conn.execute(query, real_amount, user.id)
            await conn.commit()

            await interaction.response.send_message(embed=embed, ephemeral=is_private)

    @commands.command(name='sync', description='Sync the bot tree for changes', aliases=("sy",))
    async def sync_tree(self, ctx: commands.Context) -> None:
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
                    except discord.HTTPException as e:
                        return await ctx.send(e)
            else:
                self._last_result = ret
                await ctx.send(f'```py\n{value}{ret}\n```')

    @commands.command(name='blank', description='Sends newlines to clear a channel', aliases=('b',))
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

    @commands.command(name='urules', description='Update the rules channel for cc', aliases=('ur',))
    async def push_update3(self, ctx: commands.Context):
        """Push an update to the rules channel."""
        original = (
            self.bot.get_partial_messageable(902138223571116052)
            .get_partial_message(1245691538319736863)
        )
        
        rule_content = (
            "1. <:e1_comfy:1150361201352659066> **Be Respectful!** "
            "Treat others the way you would want to be treated, and avoid offensive language or behaviour.\n"
            "2. <:pepe_blanket:798869466648674356> **Be mindful of others!** "
            "Refrain from excessive messages, links, or images that disrupt the flow of conversation.\n"
            "3. <:threadwhite:1169704299509596190> **Stay on topic.** "
            "Keep discussions relevant to the designated channels to maintain a focused "
            "and organized environment. Innapropriate content is subject to removal!\n"
            "4. <:Polarizer:1171491374756012152> **Keep our server safe.** "
            "Any form of content that suggests normalization or justification of NSFW content should not escape the "
            "boundaries of <#1160547937420582942>, sanctions will be upheld for such cases.\n"
            "5. <:discordthinking:1173681144718446703> **Adhere to the Terms of Service.** "
            "Abide by Discord\'s [terms of service](<https://discord.com/terms>) and [community guidelines](<https://discord.com/guidelines/>) at all times.\n\n"
            "**That's all.** Thanks for reading, now go have fun! <a:anime_salute:1170379416845692928>"
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

            We have a leveling system that gives you roles. These are based on how many messages you send in the server excluding slash commands[**\U000000b9**](<https://discord.com/channels/829053898333225010/1121094935802822768/1166397053329477642>), provided by <@437808476106784770>.
            Check your rank by calling </rank:873658940360126466> in any bot command channel. At every 20 levels, you get a role that grants a set of unique perks and permissions. If you reached a previous milestone role, it will be replaced with your new one.
            - <@&923931646783287337>: Granted ability to make public and private threads, also able to become a DJ.
            - <@&923931729016795266>: Granted ability to use the soundboard, these sounds can be external if you are a Nitro member.
            - <@&923931772020985866>: Granted access to the audit log, and a 1.2x XP boost.
            - <@&923931819571810305>: Granted ability to send polls anywhere on the server.
            - <@&923931862001414284>: Granted either admin permissions, a high value reward in our economy, or a developer voicenote.
            """
        )
        _ = (
            """
            Other miscellaneous roles for your knowledge:
            - <@&893550756953735278>: The people who manage the server.
            - <@&1148209142465581098>: The role for a backup account, granted all server permissions.
            - <@&912057500914843680>: A possible role to obtain when you reach level 100.
            - <@&1121405863194787851>: Given out to those who abuse the XP system, via spam or other methods.
            - <@&914565377961369632>: The role only the verified crew have upon joining the server.
            - <@&1140197893261758505>: Given to people who had their message on the legacy starboard.
            - <@&1121426143598354452>: Given on a per-user basis, granting certain privileges.
            - <@&990900517301522432>: Grants access to music commands, unlocked at level 20.
            - <@&1121405585712234506>: A role obtainable when reaching level 60.
            - <@&1150848144440053780>: Bots that only need read access to bot command channels.
            - <@&1150848206008238151>: Bots that require full read access throughout the server.
            """
        )
        
        await message1.edit(content=dedent(role_content_pt1))
        # await channel.send(content=dedent(role_content_pt2))

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
            -# Still lost? Let a <@&893550756953735278> know.
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
            - Temporary voice channels: slide into <#1220483928666935396> and manage it with the `/voice` subcommands
            - Fun comamnds: image manipulation on any user, or even ship yourself with another potential partner
            - Global tag system: tag text important to you for later retrieval anywhere on the platform
            - Miscellaneous functionality: anime related commands amongst other useful developer tools
            ## Our mission
            We're always finding new things to add to our bot, to make it better for every single one of you. 
            It's a bespoke bot, tailored to your needs. Anyone in this server can request a feature for the bot and it will get implemented if there's a genuine desire and valid reason behind it.
            -# You can message a director to submit feedback. Your bot, your rules.
            """
        )

        await message.edit(content=dedent(channel_content_pt1))

    @commands.command(name='uinfo', description='Update the information channel for cc', aliases=('ui',))
    async def push_update2(self, _: commands.Context):
        """Push to update the welcome and info embed within its respective channel."""
        await self.send_bot_guide()

    @commands.command(name='quit', description='Quits the bot gracefully', aliases=('q',))
    async def quit_client(self, ctx: commands.Context) -> None:
        """Quits the bot gracefully."""
        await ctx.send("\U00002705")
        await self.bot.close()

    @commands.command(name='invite', description='Links the invite for c2c', aliases=('i',))
    async def invite_bot(self, ctx: commands.Context) -> None:
        content = membed("Remember, only developers can invite the bot.")
        await ctx.send(embed=content, view=InviteButton())

    @commands.hybrid_command(name='repeat', description='Repeat what you typed', aliases=('say',))
    @app_commands.allowed_installs(**LIMITED_INSTALLS)
    @app_commands.allowed_contexts(**LIMITED_CONTEXTS)
    @app_commands.describe(
        message='What you want me to say.', 
        channel='What channel i should send in.'
    )
    async def repeat(
        self, 
        ctx: commands.Context, 
        channel: Optional[discord.abc.GuildChannel] = commands.CurrentChannel, 
        *, 
        message: str
    ) -> None:
        """Repeat what you typed, also converting emojis based on whats inside two equalities."""

        if not ctx.interaction:
            await ctx.message.delete()

        matches = findall(r'<(.*?)>', message)

        for match in matches:
            emoji = discord.utils.get(self.bot.emojis, name=match)
            if emoji:
                message = message.replace(f'<{match}>', f"{emoji}")
                continue
            if ctx.interaction:
                return await ctx.send(ephemeral=True, embed=membed("Could not find that emoji."))
            return

        await channel.send(message)
        if ctx.interaction:
            await ctx.send(
                delete_after=3.0, 
                ephemeral=True, 
                embed=membed(f"Sent this message to {channel.mention}.")
            )

    @commands.command(name="uforuma", description="Update the forum announcement", aliases=("ufa",))
    async def upload2(self, ctx: commands.Context):
        msg = (
            self.bot.get_partial_messageable(1147203137195745431)
            .get_partial_message(1147203137195745431)
        )
        a = membed(
            "> **What are Forum Channels?**\n\n"
            "Forum Channels are designed to allow conversations to coexist without people talking over each other.\n\n"
            "> **What is this channel for?**\n\n"
            "The channel is based on uploading media and sharing your thoughts about it.\n\n"
            "> **Where do I start?!**\n\n"
            "- Refresh your memory of the Post Guidelines\n"
            "- Engage in an existing thread, or create your own, talk about whatever you like\n"
            "- Include some tags in your posts to give people an idea of what your post is all about\n\n"
            "And that's it!"
        )
        a.title = "FAQ"
        a.set_thumbnail(url="https://i.imgur.com/Udo4MDP.png")

        await msg.edit(embed=a)

    async def do_via_webhook(self, kwargs: dict, edit_message_id: Optional[int] = None) -> None:
        """`edit_message_id` must be an ID that is in the same channel this webhook is designated in."""
        webhook = discord.Webhook.from_url(url=self.bot.WEBHOOK_URL, session=self.bot.session)
        webhook = await webhook.fetch()

        if edit_message_id:
            del kwargs["silent"]
            return await webhook.edit_message(edit_message_id, **kwargs)
        
        await webhook.send(**kwargs)

    @commands.command(name='dispatch-webhook', description="Dispatch customizable quarterly updates", aliases=('dw',))
    async def dispatch_webhook(self, ctx: commands.Context):
        all_ems = [
            discord.Embed(
                colour=discord.Colour.from_rgb(3, 102, 214),
                title='Changelog',
                description=(
                    "Changes taken place between <t:1711929600:d> - <t:1719705600:d> are noted here.\n\n"
                    "- ~~Added new colour roles~~ Superseded[**\U000000b2**](https://discord.com/channels/829053898333225010/1124782048041762867/1241137977225248873)\n"
                    "- ~~Changed the colour of some colour roles~~ Superseded[**\U000000b2**](https://discord.com/channels/829053898333225010/1124782048041762867/1241137977225248873)\n"
                    "- Changed the default colour for <@&914565377961369632>\n"
                    "- Emojified the topic of all non-archived channels\n"
                    "- Added new tasks to complete in Server Onboarding\n"
                    "- Removed more redundant permissions from bots\n"
                    "- Cleaned the pinned messages of most channels\n"
                    "- Added a requirement to include tags upon creating a post\n"
                    "- Simplified the guidelines thread for the forum (https://discord.com/channels/829053898333225010/1147203137195745431)\n"
                    "- Added a policy to never close threads that are inactive, only lock them\n"
                    "- Kicked more bots off the server\n"
                    "- Renamed some channels for consistency\n"
                    "- Disabled some custom AutoMod rules\n"
                    "- Added some new chatbots\n"
                    "- Improve the onboarding question selection\n"
                    "- Change how channel opt in works[**\U000000b9**](https://discord.com/channels/829053898333225010/1124782048041762867)\n"
                    "- Removed the developer channel opt in, and deleted its respective channel"
                )
            )
        ]

        second_em = membed(
            "### Breaking change to channel opt-in[**\U000000b9**](https://discord.com/channels/829053898333225010/1124782048041762867)\n"
            "You'll now no longer see these opt in channels if you do not select them. "
            "When selected, you will get **roles** that allow you to see the channel instead of joining it. "
            "This means less clutter, more of the stuff you're interested in. "
            "There's also a new option allowing you to see the server archives.\n"
            "### The Colour Role Wipeout[**\U000000b2**](https://discord.com/channels/829053898333225010/1124782048041762867/1241137977225248873)\n"
            "Since it received little to no usage, the deed had to be done. "
            "We are bringing the functionality back however in the form of a slash command. "
            "We'll reveal more details about it later before it's released."
        )
        second_em.title = "Index"

        second_em.set_footer(
            icon_url=ctx.guild.icon.url, 
            text="End of Q2. Next quarterly update due: 30th September 2024"
        )
        all_ems.append(second_em)

        kwargs = {"embeds": all_ems, "silent": True, "content": None}
        await self.do_via_webhook(kwargs, edit_message_id=1241137977225248873)


async def setup(bot: commands.Bot):
    """Setup for cog."""
    await bot.add_cog(Owner(bot))
