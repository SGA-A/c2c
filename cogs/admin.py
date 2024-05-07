"""The administrative cog. Only for use by the bot owners."""
from datetime import datetime
from re import findall
from textwrap import indent
from contextlib import redirect_stdout
from traceback import format_exc

from typing import (
    Optional, 
    Any, 
    Literal, 
    Union
)

import asyncio
import io
import discord

from discord import app_commands
from discord.ext import commands
from asqlite import Connection as asqlite_Connection

from cogs.economy import (
    CURRENCY, 
    determine_exponent, 
    APP_GUILDS_ID, 
    membed
)


FORUM_ID = 1147176894903627888
UPLOAD_FILE_DESCRIPTION = "A file to upload alongside the thread."
FORUM_TAG_IDS = {
    'game': 1147178989329322024, 
    'political': 1147179277343793282, 
    'meme': 1147179514825297960, 
    'anime/manga': 1147179594869387364, 
    'reposts': 1147179787949969449, 
    'career': 1147180119887192134, 
    'rant': 1147180329057140797, 
    'information': 1147180466210873364, 
    'criticism': 1147180700022345859, 
    'health': 1147180978356363274, 
    'advice': 1147181072065515641, 
    'showcase': 1147181147370049576, 
    'coding': 1147182042744901703, 
    'general discussion': 1147182171140923392
}


class InviteButton(discord.ui.View):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot: commands.Bot = bot

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

        self.add_item(
            discord.ui.Button(
                label="Invite",
                url=discord.utils.oauth_url(self.bot.user.id, permissions=perms)
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
        
        await ctx.send(
            content=(
                f"**Uptime**: {int(days)} days, {int(hours)} hours, "
                f"{int(minutes)} minutes and {int(seconds)} seconds."
            )
        )

    @app_commands.command(name="config", description="Adjust a user's robux directly")
    @app_commands.default_permissions(administrator=True)
    @app_commands.guilds(*APP_GUILDS_ID)
    @app_commands.describe(
        configuration='Whether to add, remove, or specify robux.',
        amount='The amount of robux to modify. Supports Shortcuts (exponents only).',
        member='The member to modify the balance of.',
        ephemeral='Whether or not the response is only visible to you.',
        deposit_mode='The type of balance to modify.')
    @app_commands.rename(ephemeral='is_hidden', member='user', deposit_mode='medium')
    async def config(
        self, 
        interaction: discord.Interaction,
        configuration: Literal["add", "remove", "make"], 
        amount: str,
        member: Optional[discord.Member],
        ephemeral: Optional[bool] = False,
        deposit_mode: Optional[Literal["wallet", "bank"]] = "wallet"
    ) -> None:
        """Generates or deducts a given amount of robux to the mentioned user."""
        
        member = member or interaction.user
        real_amount = await determine_exponent(
            interaction=interaction, 
            rinput=amount
        )
        if real_amount is None:
            return
        embed = membed()
        
        if isinstance(real_amount, str):
            embed.description = "This shortcut is not supported here."
            return await interaction.response.send_message(embed=embed)

        async with self.bot.pool.acquire() as conn:
            conn: asqlite_Connection

            if configuration.startswith("a"):
                query = (
                    f"""
                    UPDATE `bank` 
                    SET `{deposit_mode}` = `{deposit_mode}` + ?
                    WHERE userID = ?
                    """
                )

                embed.description = f"Added {CURRENCY} **{real_amount:,}** to {member.mention}!"
            elif configuration.startswith("r"):
                query = (
                    f"""
                    UPDATE `bank` 
                    SET `{deposit_mode}` = `{deposit_mode}` - ?
                    WHERE userID = ?
                    """
                )
                embed.description = f"Deducted {CURRENCY} **{real_amount:,}** from {member.mention}!"
            else:
                query = (
                    f"""
                    UPDATE `bank` 
                    SET `{deposit_mode}` = ?
                    WHERE userID = ?
                    """
                )
                embed.description = f"Set {CURRENCY} **{real_amount:,}** to {member.mention}!"

            await conn.execute(query, (real_amount, member.id))
            await conn.commit()

            await interaction.response.send_message(embed=embed, ephemeral=ephemeral)

    @commands.command(name='threader', aliases=('ct', 'cthr'), description='Create a thread in a text channel')
    async def create_thread(self, ctx: commands.Context, thread_name: str):
        """Create a forum channel quickly with only name of thread required as argument."""
        if not isinstance(ctx.channel, discord.TextChannel):
            await ctx.send(content="You need to be in a text channel.", delete_after=5.0)

        await ctx.channel.create(
            name=thread_name, 
            auto_archive_duration=10080, 
            message=discord.Object(ctx.message.id)
        )

    @commands.command(name='sync', description='Sync the bot tree for changes', aliases=("sy",))
    async def sync_tree(self, ctx: commands.Context) -> None:
        """Sync the bot's tree to either the guild or globally, varies from time to time."""

        for guild_id in APP_GUILDS_ID:
            synced = await self.bot.tree.sync(guild=discord.Object(id=guild_id))
        
        self.bot.command_count = len(synced) + len(self.bot.commands) + 1

        await self.bot.tree.sync(guild=None)
        await ctx.message.add_reaction('<:successful:1183089889269530764>')

    @commands.command(name='eval', description='Evaluates arbitrary code')
    async def eval(self, ctx: commands.Context, *, script_body: str):
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
                    await ctx.send(f'```py\n{value}\n```')
            else:
                self._last_result = ret
                await ctx.send(f'```py\n{value}{ret}\n```')

    @commands.command(name='blank', description='Sends newlines to clear a channel')
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

    @commands.command(name='uschedule', description='Update the planned changes tracker in cc', aliases=('us', 'usched'))
    async def push_update(self, ctx):
        """Push an update directly to the info channel."""

        await ctx.message.delete()
        channel = await self.bot.fetch_channel(1121445944576188517)
        original = await channel.fetch_message(1142392804446830684)

        embed = discord.Embed(
            title='Update Schedule',
            colour=discord.Colour.from_rgb(101, 242, 171),
            description=(
                'This embed will post any changes to the server in the near future.\n'
                '- ~~Add more custom role colours~~ **DONE**\n'
                '- Remove more redundant bots\n'
                '- ~~Add new tasks to complete in Server Onboarding~~ **DONE**\n'
                '- ~~Add emotes to the channel topic of every channel~~ **DONE**\n'
                '- ~~Pick a more suitable role colour for The Crew~~ **DONE**'
            )
        )

        # embed.add_field(
        #     name="There's nothing here yet.", 
        #     value="There are no planned changes for the server right now."
        # )

        # replace 'more' w/ 'any known'
        embed.set_footer(
            text='Check back later for more scheduled updates..', 
            icon_url=('https://pa1.narvii.com/6025/9497042b3aad0518f08dd2bfefb0e2262f4a7149_hq.gif')
        )

        await original.edit(embed=embed)

    @commands.command(name='urules', description='Update the rules channel for cc', aliases=('ur',))
    async def push_update3(self, ctx: commands.Context):
        """Push an update to the rules channel."""
        await ctx.message.delete()
        channel = self.bot.get_partial_messageable(902138223571116052)
        original = channel.get_partial_message(1140258074297376859)
        
        r = discord.Embed()
        r.title = "Rules & Guidelines"
        r.description=(
            'We look forward to seeing you become a regular here! '
            'However, ensure that you are familiar with our Server Guidelines!\n\n'
            'Your entrance into the server confirms you accept the following rules as '
            'well as agreement to any other rules that are implied elsewhere.\n'
            '# 1. <:e1_comfy:1150361201352659066> Be Respectful!\n'
            'Treat others the way you would want to be treated, '
            'and avoid offensive language or behaviour.\n'
            '# 2. <:pepe_blanket:798869466648674356> Be mindful of others!\n'
            'Refrain from excessive messages, links, or images that '
            'disrupt the flow of conversation.\n'
            '# 3. <:threadwhite:1169704299509596190> Stay on topic.\n'
            'Keep discussions relevant to the designated channels to maintain a focused '
            'and organized environment. Innapropriate content is subject to removal!\n'
            '# 4. <:Polarizer:1171491374756012152> Keep our server safe!\n'
            'Any form of content that suggests normalization or '
            'justification of NSFW content should not escape the '
            'boundaries of <#1160547937420582942>, sanctions will be upheld for such cases.\n'
            '# 5. <:discordthinking:1173681144718446703> Adhere to the Terms of Service.\n'
            'Abide by Discord\'s terms of service and community guidelines at all times:\n'
            '[Discord Community Guidelines](https://discord.com/guidelines/)\n'
            '[Discord Terms of Service](https://discord.com/terms)'
        )
        r.colour = discord.Colour.from_rgb(208, 189, 196)
        r.set_footer(
            icon_url='https://cdn.discordapp.com/emojis/1170379416845692928.gif?size=160&quality=lossless',
            text='Thanks for reading and respecting our guidelines! Now go have fun!'
        )

        await original.edit(embed=r)

    @commands.command(name='uinfo', description='Update the information channel for cc')
    async def push_update2(self, ctx):
        """Push to update the welcome and info embed within its respective channel."""
        await ctx.message.delete()
        channel = await self.bot.fetch_channel(1121445944576188517)
        original = await channel.fetch_message(1140952278862401657)
        a = "C:\\Users\\georg\\Downloads\\Media\\rsz_tic.png"
        that_file = discord.File(a, filename="image.png")
        
        intro = discord.Embed(colour=discord.Colour.from_rgb(31, 16, 3))
        intro.set_image(url="attachment://image.png")
        
        embed = discord.Embed(
            title="Origins",
            colour=0x2B2D31,
            description=(
                "**What is this server all about?!**\n"
                "This is another hangout to theorize your day-to-day discussions.\n"
                "The server was created on the **6th of April 2021** to provide "
                "a space that fosters a chill and mature community that can talk "
                "about anything and everything.\n\n"
                "**What does cc actually stand for?**\n"
                "We don't know either, our guess is something along the lines "
                "of a collective community, this being the aim of the server to date.\n\n"
                "We hope you enjoy your stay, and we wish you a wonderful journey.\n"
                "And don't forget; you're here forever."
            )
        )
        embed.set_thumbnail(url="https://i.imgur.com/7RufohA.png")

        roles = discord.Embed(
            title="Server Roles",
            colour=0x2B2D31,
            description=(
                "- <@&893550756953735278>\n"
                "  - People who manage and moderate cc.\n\n"
                "- <@&1140197893261758505>\n"
                "  - People who have a high rating on the legacy starboard.\n\n"
                "- <@&1121426143598354452>\n"
                "  - People with access to private features.\n\n"
                "- <@&990900517301522432>\n"
                "  - People with full music control over music bots.\n\n"
                "- Other custom roles\n"
                "  - <@&1124762696110309579> and <@&1047576437177200770>.\n"
                "  - Reach **Level 40** to make your own!"
            )
        )
        
        roles.set_thumbnail(url="https://i.imgur.com/ufnRnNx.png")

        ranks = discord.Embed(
            title="Level Roles & Perks",
            colour=0x2B2D31,
            description=(
                "Your activity in the server will not be left unrewarded!\n"
                "Level up by participating in text channels.\n"
                "The more active you are, the higher levels attained and the better perks you receive.\n\n"
                "- <@&923930948909797396>\n\n"
                "- <@&923931088613699584>\n"
                "  - \U000023e3 **335,000,000**\n\n"
                "- <@&923931156125204490>\n"
                "  - Your own custom channel\n\n"
                "- <@&923931553791348756>\n"
                " - Request a feature for <@1047572530422108311>\n\n"
                "- <@&923931585953280050>\n"
                "  - \U000023e3 **1,469,000,000**\n\n"
                "- <@&923931646783287337>\n"
                "  - \U000023e3 **17,555,000,000**, 5 \U0001f3c6\n\n"
                "- <@&923931683311456267>\n"
                "  - \U000023e3 **56,241,532,113**\n"
                "  - 3,500 free EXP\n\n"
                "- <@&923931729016795266>\n"
                "  - Request a feature for <@1047572530422108311>\n"
                "  - Your own custom role\n\n"
                "- <@&923931772020985866>\n"
                "  - \U000023e3 **72,681,998,999**, 64 \U0001f3c6\n\n"
                "- <@&923931819571810305>\n"
                "  - The Personal Token of Appreciation\n\n"
                "- <@&923931862001414284>\n"
                "  - See Appendix 1"
            )
        )
        ranks.set_thumbnail(url="https://i.imgur.com/2V5LM2s.png")

        second_embed = discord.Embed(
            title="The Appendix 1",
            colour=0x2B2D31,
            description=(
                "If you somehow manage to reach **<@&923931862001414284>**, out of 6 events, 1 will take place.\n"
                "A dice will be rolled and the outcome will ultimately depend on a dice roll.\n\n"
                "1. Your level of experience and wisdom will prove you worthy of receiving <@&912057500914843680>, a role only members of high authority can attain.\n"
                "2. Your familiarity with this server will allow you to get 1 Month of Discord Nitro immediately when available.\n"
                "3. This is a karma roll, you will receive nothing.\n"
                "4. For the sake of nonplus, this event will not be disclosed until it is received.\n"
                "5. This is a karma roll, you will receive nothing.\n"
                "6. This is a special one: a face reveal or a voice reveal by the owner. The choice will be made by another dice roll.\n\n"
                "**Notes**\n"
                "You cannot earn EXP while executing slash commands.\n"
                "Refer to this message for details: https://discord.com/channels/829053898333225010/1121094935802822768/1166397053329477642"
            )
        )
        
        second_embed.set_thumbnail(url="https://i.imgur.com/aoECtze.png")
        second_embed.set_footer(text="Reminder: the perks from all roles are one-time use only and cannot be reused or recycled.")
        
        try:
            await original.edit(
                attachments=[that_file], 
                embeds=[intro, embed, ranks, roles, second_embed]
            )

        except discord.HTTPException as err:
            await ctx.send(str(err))

    @commands.command(name='utracker', description='Update the economy system tracker', aliases=('ut',))
    async def override_economy(self, ctx: commands.Context):
        """Update the progress tracker on the Economy system."""
        
        await ctx.message.delete()
        channel = self.bot.get_partial_messageable(1124782048041762867)
        original = channel.get_partial_message(1166793975466831894)
        
        temporary = discord.Embed(
            title="Temporary Removal of the Economy System",
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
                " <@992152414566232139> "
                "<a:ehe:928612599132749834>)!"),
            colour=discord.Colour.from_rgb(102, 127, 163))
        
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
                'fully operational and ready for use.'))
        
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
        content = membed("Remember that only developers can invite the bot.")
        await ctx.send(embed=content, view=InviteButton(self.bot))

    @commands.hybrid_command(name='repeat', description='Repeat what you typed', aliases=('say',))
    @app_commands.guilds(*APP_GUILDS_ID)
    @app_commands.describe(
        message='what you want me to say', 
        channel='what channel i should send in'
    )
    async def repeat(
        self, 
        ctx: commands.Context, 
        channel: Optional[Union[discord.TextChannel, discord.VoiceChannel, discord.ForumChannel, discord.Thread]], 
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
                return await ctx.send("Could not find that emoji.", ephemeral=True)
            return

        channel = channel or ctx.channel
        await channel.send(message)
        if ctx.interaction:
            await ctx.send(content=f"Sent this message to {channel.mention}.", ephemeral=True)

    @app_commands.command(name='upload', description='Upload a new forum thread')
    @app_commands.guilds(*APP_GUILDS_ID)
    @app_commands.describe(
        name="The name of the thread.",
        description="The content of the message to send with the thread.",
        file=UPLOAD_FILE_DESCRIPTION,
        file2=UPLOAD_FILE_DESCRIPTION,
        file3=UPLOAD_FILE_DESCRIPTION,
        tags="The tags to apply to the thread, seperated by spaces."
    )
    @app_commands.default_permissions(manage_guild=True)
    async def create_new_thread(
        self, 
        interaction: discord.Interaction, 
        name: str, 
        description: Optional[str], 
        tags: str, 
        file: Optional[discord.Attachment], 
        file2: Optional[discord.Attachment],
        file3: Optional[discord.Attachment]) -> None:

        await interaction.response.defer(thinking=True)

        forum: discord.ForumChannel = self.bot.get_channel(FORUM_ID)
        tags = tags.lower().split()
        
        files = [
            await param_value.to_file() 
            for param_name, param_value in iter(interaction.namespace) 
            if param_name.startswith("f") and param_value
        ]

        applicable_tags = [forum.get_tag(tag_id) for tagname in tags if (tag_id := FORUM_TAG_IDS.get(tagname)) is not None]
    
        thread, _ = await forum.create_thread(
            name=name,
            content=description,
            files=files,
            applied_tags=applicable_tags
        )

        await interaction.followup.send(
            ephemeral=True, 
            embed=membed(f"Your thread was created here: {thread.jump_url}.")
        )

    @commands.command(name="uforuma", description="Update the forum announcement", aliases=("ufa",))
    async def upload2(self, ctx: commands.Context):
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


async def setup(bot: commands.Bot):
    """Setup for cog."""
    await bot.add_cog(Owner(bot))
    
