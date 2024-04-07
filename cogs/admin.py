"""The administrative cog. Only for use by the bot owners."""
from random import randint
from datetime import timedelta, datetime
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
    get_profile_key_value, 
    modify_profile,
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


class Owner(commands.Cog):
    """Cog containing commands only executable by the bot owners. Contains debugging tools."""
    def __init__(self, client: commands.Bot):
        self.client = client
        self._last_result: Optional[Any] = None

    async def cog_check(self, ctx: commands.Context) -> bool:
        return ctx.author.id in self.client.owner_ids

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
        diff = datetime.now() - self.client.time_launch
        minutes, seconds = divmod(diff.total_seconds(), 60)
        hours, minutes = divmod(minutes, 60)
        days, hours = divmod(hours, 24)
        
        await ctx.send(
            content=(
                f"**Uptime**: {int(days)} days, {int(hours)} hours, "
                f"{int(minutes)} minutes and {int(seconds)} seconds."
            )
        )

    @commands.command(name="p_n", description="Send payouts to eligible members")
    async def rewards_user_roles(self, ctx: commands.Context):
        """Send a weekly payout to users that are eligible."""
        await ctx.message.delete()

        pinned_if_any = get_profile_key_value("weeklyr msg id")
        if pinned_if_any is not None:
            
            try:
                already_pinned = await ctx.fetch_message(pinned_if_any)
                await already_pinned.unpin(reason="Outdated weekly reward announcement")  # unpin if stored
            
            except discord.HTTPException:
                msg = await ctx.send(
                    mention_author=True,
                    content=(
                        "**[WARNING]:** Previous weekly reward announcement was detected, but"
                        " could not be found in the invoker channel. Make sure you are calling "
                        "this command in the same channel it was sent in."
                    )
                )

                return await msg.edit(content=f"{msg.content}\n\nCancelled the payout operation.")

        if ctx.guild.id != 829053898333225010:
            return await ctx.send("This command is to be called only within **cc**.")
        
        active_members = ctx.guild.get_role(1190772029830471781).members
        activated_members = ctx.guild.get_role(1190772182591209492).members

        eligible = len(active_members) + len(activated_members)
        actual = 0

        async with self.client.pool_connection.acquire() as conn:
            conn: asqlite_Connection
            payouts = {}
            economy = self.client.get_cog("Economy")

            async with conn.transaction():
                for member in activated_members:
                    if await economy.can_call_out(member, conn):
                        continue
                    amt_activated = randint(1_100_000_000, 2_100_000_000)
                    await economy.update_bank_new(member, conn, amt_activated)
                    payouts.update(
                        {f"{member.mention}": (amt_activated, ctx.guild.get_role(1190772182591209492).mention)})
                    actual += 1

                for member in active_members:
                    if await economy.can_call_out(member, conn):
                        continue
                    amt_active = randint(200000000, 1100000000)
                    await economy.update_bank_new(member, conn, amt_active)
                    payouts.update({f"{member.mention}": (amt_active, ctx.guild.get_role(1190772029830471781).mention)})
                    actual += 1

            dt_now = datetime.now()
            payday = discord.Embed(
                colour=discord.Colour.dark_embed(),
                description=(
                    "## Weekly Rewards (for week "
                    f"{dt_now.isocalendar().week} of {dt_now.year})\n"
                    "These are the users who were eligible to claim this week's activity "
                    "rewards. Entries that contained users not registered as of "
                    f"{discord.utils.format_dt(dt_now, style="t")} today were "
                    f"ignored. Considering this, `{eligible}` user(s) were eligible,"
                    f" but `{actual}` user(s) were given these rewards.\n"
                )
            )

            payday_notes = []
            for member, payout in payouts.items():  # all members that got paid
                payday_notes.append(
                    f"- {member} walked away with \U000023e3 **{payout[0]:,}** from being {payout[1]}."
                )

            payday.description += '\n'.join(payday_notes)
            unpinned = await ctx.send(embed=payday)
            await unpinned.pin(reason="Latest weekly rewards announcement")
            modify_profile("update", "weeklyr msg id", unpinned.id)  # store to unpin later

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
        ephemeral: Optional[bool] = True,
        deposit_mode: Optional[Literal["wallet", "bank"]] = "wallet"
    ) -> None:
        """Generates or deducts a given amount of robux to the mentioned user."""
        
        member = member or interaction.user
        real_amount = determine_exponent(amount)

        async with self.client.pool_connection.acquire() as conn:
            conn: asqlite_Connection
            
            embed = discord.Embed(
                title='Success', 
                colour=discord.Colour.random(), 
                timestamp=discord.utils.utcnow()
            )

            economy = self.client.get_cog("Economy")

            if configuration.startswith("a"):
                new_amount = await economy.update_bank_new(member, conn, +int(real_amount), deposit_mode)

                embed.description = (
                    f"- Added {CURRENCY}{int(real_amount):,} robux to **{member.display_name}**'s balance.\n"
                    f"- **{member.display_name}**'s new **`{deposit_mode}`** balance is {CURRENCY}{new_amount[0]:,}."
                )
                embed.set_footer(text="configuration type: ADD_TO")
            elif configuration.startswith("r"):

                new_amount = await economy.update_bank_new(member, conn, -int(real_amount), deposit_mode)

                embed.description = (
                    f"- Deducted {CURRENCY}{int(real_amount):,} robux from **{member.display_name}**'s balance.\n"
                    f"- **{member.display_name}**'s new **`{deposit_mode}`** balance is {CURRENCY}{new_amount[0]:,}."
                )
                embed.set_footer(text="configuration type: REMOVE_FROM")
            else:
                new_amount = await economy.change_bank_new(member, conn, real_amount, deposit_mode)
                
                embed.description = (
                    f"- \U0000279c **{member.display_name}**'s "
                    f"**`{deposit_mode}`** balance has been changed to {CURRENCY}{real_amount:,}.\n"
                    f"- **{member.display_name}**'s new **`{deposit_mode}`** balance is {CURRENCY}{new_amount[0]:,}."
                )
                
                embed.set_footer(text="configuration type: ALTER_TO")

            await conn.commit()
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_author(name=f"Requested by {interaction.user.name}", icon_url=interaction.user.avatar.url)

            await interaction.response.send_message(embed=embed, ephemeral=ephemeral)

    @commands.command(name='cthr', aliases=('ct', 'create_thread'), description='Use a preset to create forum channels')
    async def create_thread(self, ctx: commands.Context, thread_name: str):
        """Create a forum channel quickly with only name of thread required as argument."""
        if not isinstance(ctx.channel, discord.TextChannel):
            await ctx.send(
                "You need to be in a text channel.", 
                delete_after=5.0
            )

        thread = await ctx.channel.create_thread(
            name=thread_name, 
            auto_archive_duration=10080, 
            message=discord.Object(ctx.message.id)
        )

        await thread.send(
            content=f"Created {thread.mention}.",
            delete_after=5.0
        )

    @commands.command(name='sync', description='Sync the client tree for changes', aliases=("sy",))
    async def sync_tree(self, ctx: commands.Context) -> None:
        """Sync the client's tree to either the guild or globally, varies from time to time."""
        print("syncing")
        
        # Application command synchronization - uncomment stmts when syncing globally
        # ctx.bot.tree.copy_global_to(guild=discord.Object(id=780397076273954886))
        # ctx.bot.tree.copy_global_to(guild=discord.Object(id=829053898333225010))
        
        # ctx.bot.tree.remove_command('balance', guild=discord.Object(id=780397076273954886))
        # ctx.bot.tree.remove_command('balance', guild=discord.Object(id=829053898333225010))

        await self.client.tree.sync(guild=discord.Object(id=780397076273954886))
        await self.client.tree.sync(guild=discord.Object(id=829053898333225010))

        await self.client.tree.sync(guild=None)
        await ctx.message.add_reaction('<:successful:1183089889269530764>')

    @commands.command(name='eval', description='Evaluates arbitrary code')
    async def eval(self, ctx: commands.Context, *, script_body: str):
        """Evaluates arbitrary code."""

        env = {
            'client': self.client,
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
                ret = await func()
        except Exception:
            value = stdout.getvalue()
            await ctx.send(f'```py\n{value}{format_exc()}\n```')
        else:
            value = stdout.getvalue()
            try:
                await ctx.message.add_reaction('<:successful:1183089889269530764>')
            except discord.HTTPException:
                pass

            if ret is None:
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

    @commands.command(name='regex', description='Load automod match_regex rules')
    async def automod_regex(self, ctx):
        """Automod regex rules and their patterns."""
        await ctx.guild.create_automod_rule(
            name='new rule by c2c',
            event_type=discord.AutoModRuleEventType.message_send,
            actions=[discord.AutoModRuleAction(duration=timedelta(minutes=5.0))],
            trigger=discord.AutoModTrigger(
                regex_patterns=["a", "b", "c", "d", "e"]
            )
        )
        await ctx.message.add_reaction('<:successful:1183089889269530764>')

    @commands.command(name='mentions', description='Load automod mass_mentions rules')
    async def automod_mentions(self, ctx):
        """Automod mentioning rules"""
        await ctx.guild.create_automod_rule(
            name='new rule by c2c',
            event_type=discord.AutoModRuleEventType.message_send,
            actions=[discord.AutoModRuleAction(duration=timedelta(minutes=5.0))],
            trigger=discord.AutoModTrigger(mention_limit=5)
        )
        await ctx.message.add_reaction('<:successful:1183089889269530764>')

    @commands.command(name='keyword', description='Load automod by_keyword rules')
    async def automod_keyword(self, ctx, the_word):
        """Automod keyword rules"""
        await ctx.guild.create_automod_rule(
            name='new rule by c2c',
            event_type=discord.AutoModRuleEventType.message_send,
            actions=[discord.AutoModRuleAction(duration=timedelta(minutes=5.0))],
            trigger=discord.AutoModTrigger(keyword_filter=[f'{the_word}']),
        )

        await ctx.message.add_reaction('<:successful:1183089889269530764>')

    @commands.command(name='update', description='Update channel information')
    async def push_update(self, ctx):
        """Push an update directly to the info channel."""

        await ctx.message.delete()
        channel = await self.client.fetch_channel(1121445944576188517)
        original = await channel.fetch_message(1142392804446830684)

        embed = discord.Embed(
            title='Update Schedule',
            colour=discord.Colour.from_rgb(101, 242, 171),
            description=(
                'This embed will post any changes to the server in the near future.\n\n'
                '- Add more custom role colours\n'
                '- Remove more redundant bots\n'
                '- Add new tasks to complete in Server Onboarding\n'
                '- Add emotes to the channel topic of every channel\n'
                '- Pick a more suitable role colour for <@&914565377961369632>'
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

    @commands.command(name='update3', description='Modify rules and guidelines')
    async def push_update3(self, ctx: commands.Context):
        """Push an update to the rules channel."""
        await ctx.message.delete()
        channel = self.client.get_partial_messageable(902138223571116052)
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

    @commands.command(name='update2', description='Edit the welcome message for the server')
    async def push_update2(self, ctx):
        """Push to update the welcome and info embed within its respective channel."""
        await ctx.message.delete()
        channel = await self.client.fetch_channel(1121445944576188517)
        original = await channel.fetch_message(1140952278862401657)
        a = "C:\\Users\\georg\\Downloads\\Media\\rsz_tic.png"
        that_file = discord.File(a, filename="image.png")
        
        intro = discord.Embed(colour=discord.Colour.from_rgb(31, 16, 3))
        intro.set_image(url="attachment://image.png")
        
        embed = discord.Embed(
            title="Origins",
            colour=0x2B2D31,
            description=(
                """
                **What is this server all about?!**
                This is another hangout to theorize your day-to-day discussions. 
                The server was created on the **6th of April 2021** to provide 
                a space that fosters a chill and mature community that can talk 
                about anything and everything.

                **What does cc actually stand for?** 
                We don't know either, our guess is something along the lines
                of a collective community, this being the aim by the server to date.
                
                We hope you enjoy your stay, and we wish you a wonderful journey.
                And don't forget; you're here forever.
                """
            )
        )

        embed.set_thumbnail(url="https://i.imgur.com/7RufohA.png")
        tbp = "\U0000279c"

        roles = discord.Embed(
            title="Server Roles",
            colour=0x2B2D31,
            description=(
                f"""
                - <@&893550756953735278>
                  - People who manage and moderate cc.

                - <@&1140197893261758505>
                  - People who have a high rating on the legacy starboard.

                - <@&1121426143598354452>
                  - People with access to private features.

                - <@&990900517301522432>
                  - People with full music control over music bots.

                - <@&1168204249096785980>
                  - People with access to new features on {self.client.user.mention}\n
                - Other custom roles
                  - <@&1124762696110309579> and <@&1047576437177200770>.
                  - Reaching **Level 40** to make your own!
                """
            )
        )
        
        roles.set_thumbnail(url="https://i.imgur.com/ufnRnNx.png")

        ranks = discord.Embed(
            title="Level Roles & Perks",
            colour=0x2B2D31,
            description=(
                f"""
                Your activity in the server will not be left unrewarded! 
                Level up by participating in text channels. 
                The more active you are, the higher levels attained and the better perks you receive.
                <@&923930948909797396>

                <@&923931088613699584>
                {tbp} \U000023e3 **335,000,000**

                <@&923931156125204490>
                {tbp} Your own custom channel

                <@&923931553791348756>
                {tbp} Request a feature for {self.client.user.mention}

                <@&923931585953280050>
                {tbp} \U000023e3 **1,469,000,000**

                <@&923931646783287337>
                {tbp} \U000023e3 **17,555,000,000**, 5 \U0001f3c6

                <@&923931683311456267>
                {tbp} \U000023e3 **56,241,532,113**
                {tbp} 3,500 free EXP

                <@&923931729016795266>
                {tbp} Request a feature for {self.client.user.mention}
                {tbp} Your own custom role

                <@&923931772020985866>
                {tbp} \U000023e3 **72,681,998,999**, 64 \U0001f3c6

                <@&923931819571810305>
                {tbp} The Personal Token of Appreciation

                <@&923931862001414284>
                {tbp} See Appendix 1
                """
            )
        )
        ranks.set_thumbnail(url="https://i.imgur.com/2V5LM2s.png")

        second_embed = discord.Embed(
            title="The Appendix 1",
            colour=0x2B2D31,
            description=(
                """
                If you somehow manage to reach **<@&923931862001414284>**, out of 6 events, 1 will take place. 
                A dice will be rolled and the outcome will ultimately depend on a dice roll.
                1. Your level of experience and wisdom will prove you worthy of receiving <@&912057500914843680>, a role only members of high authority can attain.

                2. Your familiarity with this server will allow you to get 1 Month of Discord Nitro immediately when available.

                3. This is a karma roll. you will receive nothing.

                4. For the sake of nonplus, this event will not be disclosed until it is received.

                5. This is a karma roll. you will receive nothing.

                6. This is a special one: a face reveal or a voice reveal by the owner. The choice will be made by another dice roll.

                **Notes**
                You cannot earn EXP while executing slash commands.
                Refer to this message for details: https://discord.com/channels/829053898333225010/1121094935802822768/1166397053329477642
                """
            )
        )
        second_embed.set_thumbnail(url="https://i.imgur.com/aoECtze.png")
        second_embed.set_footer(
            text=(
                "Reminder: the perks from all roles are one-time use only and cannot be reused or recycled."
            )
        )
        
        try:
            await original.edit(
                attachments=[that_file], 
                embeds=[intro, embed, ranks, roles, second_embed]
            )

        except discord.HTTPException as err:
            await ctx.send(str(err))

    @commands.command(name='update4', description='Update the progress tracker')
    async def override_economy(self, ctx):
        """Update the progress tracker on the Economy system."""
        await ctx.message.delete()
        channel = await self.client.fetch_channel(1124782048041762867)
        original = await channel.fetch_message(1166793975466831894)
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
                " making it possible!"))
        await original.edit(embed=temporary)

    @commands.command(name='quit', description='Quits the bot gracefully', aliases=('q',))
    async def quit_client(self, ctx):
        """Quits the bot gracefully."""
        await ctx.message.add_reaction('<:successful:1183089889269530764>')
        utility_cog = self.client.get_cog("Utility")
        await utility_cog.wf.close()
        await self.client.session.close()
        await self.client.pool_connection.close()
        await self.client.http.close()
        await self.client.close()

    @commands.hybrid_command(name='repeat', description='Repeat what you typed', aliases=('say',))
    @app_commands.guilds(*APP_GUILDS_ID)
    @app_commands.describe(
        message='what you want me to say', 
        channel='what channel i should send in'
    )
    async def repeat(
        self, 
        ctx: commands.Context, 
        channel: Optional[
            Union[
                discord.TextChannel, discord.VoiceChannel,
                discord.ForumChannel, discord.Thread]], 
        *, message: str) -> None:
        """Repeat what you typed, also converting emojis based on whats inside two equalities."""

        if not ctx.interaction:
            await ctx.message.delete()

        matches = findall(r'<(.*?)>', message)

        for match in matches:
            emoji = discord.utils.get(self.client.emojis, name=match)
            if emoji:
                message = message.replace(f'<{match}>', f"{emoji}")
                continue
            if ctx.interaction:
                return await ctx.send("Could not find that emoji.", ephemeral=True)
            return

        channel = channel or ctx.channel
        await channel.send(message)
        if ctx.interaction:
            await ctx.send(f"Done. Sent this message to {channel.mention}.", ephemeral=True)

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

        forum: discord.ForumChannel = self.client.get_channel(FORUM_ID)
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
            embed=membed(f"Your thread was created here: {thread.jump_url}.")
        )

async def setup(client):
    """Setup for cog."""
    await client.add_cog(Owner(client))
    
