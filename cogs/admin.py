"""The administrative cog. Only for use by the bot owners."""
from re import findall
from textwrap import indent, dedent
from datetime import datetime
from traceback import format_exc
from contextlib import redirect_stdout

from typing import (
    Optional, 
    Any, 
    Literal, 
    Union
)

import io
import asyncio
import discord

from discord import app_commands
from discord.ext import commands
from asqlite import Connection as asqlite_Connection

from .core.helpers import membed, determine_exponent
from .core.constants import CURRENCY, APP_GUILDS_IDS


class InviteButton(discord.ui.View):
    def __init__(self) -> None:
        super().__init__()

        perms = discord.Permissions.none()

        perms.read_message_history = True
        perms.read_messages = True
        perms.send_messages_in_threads = True
        perms.send_messages = True
        
        perms.manage_channels = True
        perms.manage_messages = True
        perms.manage_roles = True
        perms.manage_threads = True

        perms.create_instant_invite = True
        perms.external_emojis = True
        
        perms.embed_links = True
        perms.attach_files = True
        perms.add_reactions = True

        perms.connect = True
        perms.speak = True
        perms.move_members = True
        perms.deafen_members = True

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
    """Cog containing commands only executable by the bot owners. Contains debugging tools."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._last_result: Optional[Any] = None

    async def cog_check(self, ctx: commands.Context) -> bool:
        if ctx.author.id in self.bot.owner_ids:
            return True
        await ctx.send(embed=membed("You do not own this bot."))
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

    @commands.command(name='uptime', description='Returns the time the bot has been active for')
    async def uptime(self, ctx: commands.Context):
        """Returns uptime in terms of days, hours, minutes and seconds"""
        diff = datetime.now() - self.bot.time_launch
        minutes, seconds = divmod(diff.total_seconds(), 60)
        hours, minutes = divmod(minutes, 60)
        days, hours = divmod(hours, 24)
        
        uptime_embed = membed(
            f"{int(days)} days, {int(hours)} hours, "
            f"{int(minutes)} minutes and {int(seconds)} seconds."
        )
        uptime_embed.title = "Uptime"
        await ctx.send(embed=uptime_embed)

    @app_commands.command(name="config", description="Adjust a user's robux directly")
    @app_commands.guilds(*APP_GUILDS_IDS)
    @app_commands.describe(
        configuration='Whether to add, remove, or specify robux.',
        amount='The amount of robux to modify. Supports Shortcuts (exponents only).',
        user='The member to modify the balance of. Defaults to you.',
        is_private='Whether or not the response is only visible to you. Defaults to False.',
        medium='The type of balance to modify. Defaults to the wallet.'
    )
    async def config(
        self, 
        interaction: discord.Interaction,
        configuration: Literal["add", "remove", "make"], 
        amount: str,
        user: Optional[discord.Member],
        is_private: Optional[bool] = True,
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
            embed.description = "Shortcuts are not supported here."
            return await interaction.response.send_message(embed=embed)

        async with self.bot.pool.acquire() as conn:
            conn: asqlite_Connection

            if configuration.startswith("a"):
                query = (
                    f"""
                    UPDATE `bank` 
                    SET `{medium}` = `{medium}` + ?
                    WHERE userID = ?
                    """
                )

                embed.description = f"Added {CURRENCY} **{real_amount:,}** to {user.mention}!"
            elif configuration.startswith("r"):
                query = (
                    f"""
                    UPDATE `bank` 
                    SET `{medium}` = `{medium}` - ?
                    WHERE userID = ?
                    """
                )
                embed.description = f"Deducted {CURRENCY} **{real_amount:,}** from {user.mention}!"
            else:
                query = (
                    f"""
                    UPDATE `bank` 
                    SET `{medium}` = ?
                    WHERE userID = ?
                    """
                )
                embed.description = f"Set {CURRENCY} **{real_amount:,}** to {user.mention}!"

            await conn.execute(query, (real_amount, user.id))
            await conn.commit()

            await interaction.response.send_message(embed=embed, ephemeral=is_private)

    @commands.command(name='threader', aliases=('ct', 'cthr'), description='Create a thread in a text channel')
    async def create_thread(self, ctx: commands.Context, thread_name: str):
        """Create a forum channel quickly with only name of thread required as argument."""
        if not isinstance(ctx.channel, discord.TextChannel):
            await ctx.send(delete_after=5.0, embed=membed("You need to be in a text channel to use this."))

        await ctx.channel.create(
            name=thread_name, 
            auto_archive_duration=10080, 
            message=discord.Object(ctx.message.id)
        )

    @commands.command(name='sync', description='Sync the bot tree for changes', aliases=("sy",))
    async def sync_tree(self, ctx: commands.Context) -> None:
        """Sync the bot's tree to either the guild or globally, varies from time to time."""

        for guild_id in APP_GUILDS_IDS:
            synced = await self.bot.tree.sync(guild=discord.Object(id=guild_id))
        
        self.bot.command_count = len(synced) + len(self.bot.commands) + 1

        await self.bot.tree.sync(guild=None)
        await ctx.message.add_reaction('<:successful:1183089889269530764>')

    @commands.command(name='eval', description='Evaluates arbitrary code')
    async def evaluate(self, ctx: commands.Context, *, script_body: str) -> Union[None | discord.Message]:
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
            'io': io,
            'asyncio': asyncio
        }

        env.update(globals())

        script_body = self.cleanup_code(script_body)
        stdout = io.StringIO()

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
                await ctx.message.add_reaction('<:successful:1183089889269530764>')
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
    async def blank(self, ctx):
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
        await ctx.message.delete()
        channel = self.bot.get_partial_messageable(902138223571116052)
        original = channel.get_partial_message(1245691538319736863)
        
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
            "**That's all.** You can go have fun now! <a:anime_salute:1170379416845692928>"
        )

        await original.edit(content=rule_content, suppress=True)

    async def send_first_note(self, channel: discord.TextChannel):
        the_msg = await channel.fetch_message(1245737782530281575)

        info_content = (
            "## Background\n"
            "This is another hangout to theorize your day-to-day discussions. "
            "cc was created on the **6th of April 2021** to provide "
            "a space that fosters a chill and mature community that can talk "
            "about anything and everything. The server is topicless, you initiate anything of your choosing. "
            "Since we emphasise on this, we don't moderate our members at all, "
            "but minute exceptions do apply for genuinely serious [rule violations.](https://discord.com/channels/829053898333225010/902138223571116052/1140258074297376859)\n\n"
            "We hope you enjoy your stay, and we wish you a wonderful journey.\n"
            "And don't forget; you're here forever."
        )
        
        await the_msg.edit(content=info_content, suppress=True)

    async def send_second_note(self, channel: discord.TextChannel):
        the_msg = await channel.fetch_message(1245737784711446630)
        role_content = (
            """
            ## Roles\n
            Roles are similar to ranks or accessories that you can add to your profile.
            There are a handful of self-assignable roles that you can pick up in <id:customize> by clicking on the buttons:
            > - <@&1240739021366362143>: Assuming you're interested in developing on Discord, this role is for you. These give you access to monthly(ish) announcements on their API.
            > - <@&1240739146272870422>: You can pick this role up and get access to Twitter announcements made by HoYoverse for Genshin Impact.
            > - <@&1240738847856263371>: Want to see what 2021 \U00002014 2022 was like here? With this role, you'll get to see all of the archives.

            There are also roles that are given out based on how active you are within the server on a weekly basis.
            > - <@&1190772029830471781>: Given to users that sent at least 50 messages in the last week.
            > - <@&1190772182591209492>: Given to users that sent at least 150 messages in the last week.

            We have a leveling system that gives you roles. These are based on how many messages you send in the server excluding slash commands[**\U000000b9**](https://discord.com/channels/829053898333225010/1121094935802822768/1166397053329477642), provided by <@437808476106784770>.
            > - Check your rank by calling this command in any bot command channel: </rank:873658940360126466>.
            > - For every minute that you send a message in a text channel, you get a random amount of XP.
            > - The XP required to reach the next level increases significantly as you level up.
            > - At every 20 levels, you get a role that grants a set of unique perks and permissions.

            The diagram below provides an illustration of all the perks attainable.
            """
        )
        
        await the_msg.edit(content=dedent(role_content), suppress=True)

    async def send_final_note(self, channel: discord.TextChannel):
        the_msg = await channel.fetch_message(1245737791904813119)
        invite_content = (
            """
            ## Invite Link\n
            Want to invite your friends to the server?
            Send them this permanent invite link: https://discord.gg/W3DKAbpJ5E
            As always, thanks for sticking around!
            """
        )

        await the_msg.edit(content=dedent(invite_content))

    @commands.command(name='uinfo', description='Update the information channel for cc')
    async def push_update2(self, ctx: commands.Context):
        """Push to update the welcome and info embed within its respective channel."""
        destination = self.bot.get_partial_messageable(
            id=1121445944576188517, 
            guild_id=829053898333225010, 
            type=discord.ChannelType.text
        )

        await self.send_second_note(channel=destination)
        await self.send_final_note(channel=destination)

    @commands.command(name='utracker', description='Update the economy system tracker', aliases=('ut',))
    async def override_economy(self, ctx: commands.Context):
        """Update the progress tracker on the Economy system."""
        
        await ctx.message.delete()
        channel = self.bot.get_partial_messageable(1124782048041762867)
        original = channel.get_partial_message(1166793975466831894)
        
        temporary = discord.Embed(
            title="Temporary Removal of the Economy System",
            colour=discord.Colour.from_rgb(102, 127, 163),
            description=(
                "as the title states, we have removed the Economy System in c2c "
                "(**for now**). <a:aaaaa:944505181150773288>\n\nthe reason being is "
                "the vast amount of bugs and inefficiencies in the system which has "
                "been eating on the limited resources we have available to keep the "
                "bot running.\n\nnot to fret though! it will be back in a completley new"
                " state! we have many exciting plans in store over the upcoming years for"
                " the bot, but right now <@992152414566232139> and <@546086191414509599>"
                " (but mostly <@992152414566232139>) are working on patching all of the "
                "major issues that are in the Economy System. we hope to bring back this"
                " part of the system by **__late 2024__** but we cannot make any promises"
                "!\n\nwe plan to modify every single command currently available under "
                "this category and add more that are to come, hence this is a extensive "
                "programme that will **require a lot of time**. This is made hindered by"
                " the current academic situation both the developers are in at this time,"
                " so please bear with us and we will not dissapoint (especially with"
                " <@992152414566232139> <a:ehe:928612599132749834>)!"
            )
        )
        
        temporary.add_field(
            name="Roadmap",
            value=(
                'to make it certain, here is an outline of what we will be doing over'
                ' the next year.'
                ' the arrows beneath these commitments will change '
                'indicating the progress of each section.\n'
                '<:redA:1166790106422722560> - **Not Started**\n'
                '<:yelA:1166790134801379378> - **In Progress**\n'
                '<:join:1163901334412611605> - **Completed**\n\n'
                '<:join:1163901334412611605> **December 2023 (late)**: start of full rehaul of '
                'every command that currently exists.\n<:yelA:1166790134801379378> **July 2024 '
                '(early)**: new commands/essential functions to the Economy system added.\n<:red'
                'A:1166790106422722560> **August 2024 (late)**: economy system '
                'fully operational and ready for use.'
            )
        )
        
        temporary.add_field(
            name="Acknowledgement",
            value=(
                "<a:e1_imhappy:1144654614046724117> <@992152414566232139> "
                "(<@&1047576437177200770>) - contributing to **87.5**% of the "
                "full programme,"
                "making it possible in the first place (will write the code).\n"
                "<a:catPat:1143936898449027082> <@546086191414509599> (<@&1124762696110309579>)"
                " - contributing to **12.5**% of the full programme (will make ideas for new "
                "commands)\n\nwe would not be able to recover the Economy System without "
                "<@992152414566232139>, she is the literal backbone of its revival! thank her for"
                " making it possible!"
            )
        )
        
        await original.edit(embed=temporary)

    @commands.command(name='quit', description='Quits the bot gracefully', aliases=('q',))
    async def quit_client(self, ctx):
        """Quits the bot gracefully."""
        await ctx.message.add_reaction('<:successful:1183089889269530764>')
        await self.bot.pool.close()
        await self.bot.session.close()
        utility_cog = self.bot.get_cog("Utility")
        await utility_cog.wf.close()
        await self.bot.close()

    @commands.command(name='invite', description='Links the invite for c2c')
    async def invite_bot(self, ctx: commands.Context) -> None:
        content = membed("Remember, only developers can invite the bot.")
        await ctx.send(embed=content, view=InviteButton())

    @commands.hybrid_command(name='repeat', description='Repeat what you typed', aliases=('say',))
    @app_commands.guilds(*APP_GUILDS_IDS)
    @app_commands.describe(
        message='What you want me to say.', 
        channel='What channel i should send in.'
    )
    async def repeat(
        self, 
        ctx: commands.Context, 
        channel: Optional[
            Union[
                discord.TextChannel, 
                discord.VoiceChannel, 
                discord.ForumChannel, 
                discord.Thread
            ]
        ] = commands.CurrentChannel, 
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
            await ctx.send(ephemeral=True, embed=membed(f"Sent this message to {channel.mention}."))

    @commands.command(name="uforuma", description="Update the forum announcement", aliases=("ufa",))
    async def upload2(self, ctx: commands.Context):
        await ctx.message.delete()

        channel: discord.PartialMessageable = self.bot.get_partial_messageable(1147203137195745431)
        msg = channel.get_partial_message(1147203137195745431)
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

    @commands.command(name='dispatch-webhook', aliases=('dw',), description="Dispatch customizable quarterly updates")
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
                    "- Improve the onboarding question selection\n"
                    "- Change how channel opt in works[**\U000000b9**](https://discord.com/channels/829053898333225010/1124782048041762867)"
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
            text="More to come in Q2.."
        )
        all_ems.append(second_em)

        content = (
            "Changes are cumulative, any new changes are added as edits."
        )
        kwargs = {"embeds": all_ems, "silent": True, "content": content}
        await self.do_via_webhook(kwargs, edit_message_id=1241137977225248873)
        await ctx.message.add_reaction('<:successful:1183089889269530764>')


async def setup(bot: commands.Bot):
    """Setup for cog."""
    await bot.add_cog(Owner(bot))
