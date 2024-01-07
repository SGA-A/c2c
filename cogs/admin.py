from discord.ext import commands
import io
from cogs.economy import CURRENCY, determine_exponent, Economy, get_profile_key_value, modify_profile
from random import randint
from datetime import timedelta, datetime
from textwrap import indent
from contextlib import redirect_stdout
from traceback import format_exc
from typing import Optional, Any, Literal
import discord
from discord import Object
from asqlite import Connection as asqlite_Connection
import asyncio
from discord import app_commands


BANK_TABLE_NAME = 'bank'


class Administrate(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client
        self._last_result: Optional[Any] = None

    async def cog_check(self, ctx: commands.Context) -> bool:
        return (ctx.author.id in self.client.owner_ids) and (ctx.guild is not None)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id in self.client.owner_ids

    def return_custom_emoji(self, emoji_name):
        emoji = discord.utils.get(self.client.emojis, name=emoji_name)
        return emoji

    @staticmethod
    async def fetch_fst_msg(ctx: commands.Context, *, channel_id: discord.TextChannel.id) -> discord.Message | None:
        """Fetch the first message of a given channel"""

        channel = await ctx.guild.fetch_channel(channel_id)
        dtls = None

        async for message in channel.history(limit=1, oldest_first=True):
            dtls = message
            break  # Exit the loop after retrieving the first message

        return dtls
    @staticmethod
    def cleanup_code(content: str) -> str:
        """Automatically removes code blocks from the code."""
        # remove ```py\n```
        if content.startswith('```') and content.endswith('```'):
            return '\n'.join(content.split('\n')[1:-1])

        # remove `foo`
        return content.strip('` \n')

    @commands.command(name='firstmsg', description='fetch the first message of a channel.')
    async def first_message_fetchit(self, ctx: commands.Context):
        await ctx.message.delete()
        msg = await self.fetch_fst_msg(ctx, channel_id=ctx.channel.id)

        if msg is not None:
            pinver = await ctx.send(f"\U00002728 First message of"
                                    f" {ctx.channel.mention} by {msg.author.name}: {msg.jump_url}")
            try:
                await pinver.pin(reason='A special message to remember.')
            except discord.HTTPException:
                pass
            return
        await ctx.send(f"sadly i could not fetch the first message for {ctx.channel.mention} :(")

    @commands.command(name='uptime', description='returns the time the bot has been active for.')
    async def uptime(self, ctx: commands.Context):
        diff = datetime.now() - self.client.time_launch  # type: ignore
        minutes, seconds = divmod(diff.total_seconds(), 60)
        hours, minutes = divmod(minutes, 60)
        days, hours = divmod(hours, 24)
        await ctx.send(content=f"**Uptime**: {int(days)} days, {int(hours)} hours, "
                               f"{int(minutes)} minutes and {int(seconds)} seconds.")

    @commands.command(name="payout-now", description="send payouts to eligible members.",
                      aliases=('p_n', 'p-n'))
    async def rewards_user_roles(self, ctx: commands.Context):
        await ctx.message.delete()

        if ctx.guild.id == 829053898333225010:
            active_role = ctx.guild.get_role(1190772029830471781)
            activated_role = ctx.guild.get_role(1190772182591209492)

            active_members = active_role.members
            activated_members = activated_role.members

            eligible = len(active_members) + len(activated_members)  # i.e total users
            actual = 0

            async with self.client.pool_connection.acquire() as conn:  
                conn: asqlite_Connection
                payouts = dict()
                for member in active_members:  # active member rewards
                    if await Economy.can_call_out(member, conn):
                        continue
                    amt_active = randint(200000000, 1100000000)
                    await Economy.update_bank_new(member, conn, amt_active)
                    payouts.update({f"{member.mention}": (amt_active, active_role.mention)})
                    actual += 1

                for member in activated_members:  # activated member rewards
                    if await Economy.can_call_out(member, conn):
                        continue
                    amt_activated = randint(1_100_000_000, 2_100_000_000)
                    await Economy.update_bank_new(member, conn, amt_activated)
                    payouts.update({f"{member.mention}": (amt_activated, activated_role.mention)})
                    actual += 1

                dt_now = datetime.now()
                payday = discord.Embed(colour=discord.Colour.dark_embed(),
                                       description=f"## Weekly Rewards (for week {dt_now.isocalendar().week} of {dt_now.year})\n"
                                                   f"These are the users who were eligible to claim this week's activity "
                                                   f"rewards. Entries that contained users not registered as of "
                                                   f"{discord.utils.format_dt(dt_now, style="t")} today were "
                                                   f"ignored. Considering this, `{eligible}` user(s) were eligible,"
                                                   f" but `{actual}` user(s) were given these rewards.\n")

                payday_notes = set()
                for member, payout in payouts.items():  #  all members that got paid
                    payday_notes.add(f"- {member} walked away with \U000023e3 **{payout[0]:,}** from being {payout[1]}.")

                pinned_if_any = get_profile_key_value(f"weeklyr msg id")
                if pinned_if_any is not None:
                    try:
                        already_pinned = await ctx.fetch_message(pinned_if_any)
                        await already_pinned.unpin(reason="Outdated weekly reward announcement")  # unpin if stored
                    except discord.NotFound | discord.HTTPException:
                        await ctx.reply(content="**[WARNING]:** Previous weekly reward announcement was detected, but"
                                                " could not be found in the invoker channel. Make sure you are "
                                                "calling this command in the same channel it was sent in.",
                                        mention_author=True)

                payday.description += '\n'.join(payday_notes)
                unpinned = await ctx.send(embed=payday)
                await unpinned.pin(reason="Latest weekly rewards announcement")
                modify_profile("update", f"weeklyr msg id", unpinned.id)  # store to unpin later
        else:
            await ctx.send("This command is to be only in **cc**.")

    @app_commands.command(name="config",
                          description="adjust a user's robux directly.")
    @app_commands.guilds(discord.Object(id=829053898333225010), discord.Object(id=780397076273954886))
    @app_commands.describe(configuration='the type of mode used for modifying robux',
                           amount='the amount of robux to modify. Supports Shortcuts (exponents only).',
                           member='the member to modify the balance of',
                           ephemeral='whether the response is hidden or not from others.',
                           deposit_mode='the type of balance to modify through')
    @app_commands.rename(ephemeral='is_hidden', member='user', deposit_mode='medium')
    async def config(self, interaction: discord.Interaction,
                     configuration: Literal["add", "remove", "make"], amount: str, member: discord.Member,
                     ephemeral: bool,
                     deposit_mode: Literal["bank", "wallet"]):
        """Generates or deducts a given amount of robux to the mentioned user."""


        avatar = member.display_avatar or member.default_avatar
        real_amount = determine_exponent(amount)
        async with self.client.pool_connection.acquire() as conn: 
            conn: asqlite_Connection
            users = await Economy.get_bank_data_new(member, conn)

            if configuration == "add":

                match deposit_mode:
                    case "bank":
                        new_amount = users[2] + int(real_amount)
                        await Economy.update_bank_new(member, conn, +int(real_amount), deposit_mode)
                    case _:
                        new_amount = users[1] + int(real_amount)
                        await Economy.update_bank_new(member, conn, +int(real_amount))

                total = (users[1] + users[2]) + int(real_amount)
                embed2 = discord.Embed(title='Success',
                                       description=f"\U0000279c added {CURRENCY}{int(real_amount):,} "
                                                   f"robux to **{member.display_name}**'s balance.\n"
                                                   f"\U0000279c **{member.display_name}**'s new "
                                                   f"**`{deposit_mode}`** balance is {CURRENCY}{new_amount:,}.\n"
                                                   f"\U0000279c **{member.display_name}**'s total balance now "
                                                   f"is {CURRENCY}{total:,}",
                                       colour=discord.Colour.dark_green(), timestamp=datetime.now())
                embed2.set_thumbnail(url=avatar.url)
                embed2.set_author(name=f"Requested by {interaction.user.name}", icon_url=interaction.user.avatar.url,
                                  url='https://www.youtube.com/watch?v=dQw4w9WgXcQ')
                embed2.set_footer(text=f"configuration type: ADD_TO")

                await interaction.response.send_message(embed=embed2, ephemeral=ephemeral) 

            if configuration == "remove":

                match deposit_mode:
                    case "bank":
                        new_amount = users[2] - int(real_amount)
                        await Economy.update_bank_new(member, conn, -int(real_amount), deposit_mode)
                    case _:
                        new_amount = users[1] - int(real_amount)
                        await Economy.update_bank_new(member, conn, -int(real_amount))

                total = (users[1] + users[2]) - int(real_amount)
                embed3 = discord.Embed(title='Success',
                                       description=f"\U0000279c deducted {CURRENCY}{int(real_amount):,} "
                                                   f"robux from **{member.display_name}**'s balance.\n"
                                                   f"\U0000279c **{member.display_name}**'s new "
                                                   f"**`{deposit_mode}`** balance is {CURRENCY}{new_amount:,}.\n"
                                                   f"\U0000279c **{member.display_name}**'s total balance now "
                                                   f"is {CURRENCY}{total:,}",
                                       colour=discord.Colour.dark_red(), timestamp=datetime.now())
                embed3.set_author(name=f"Requested by {interaction.user.name}", icon_url=interaction.user.avatar.url,
                                  url='https://www.youtube.com/watch?v=dQw4w9WgXcQ')
                embed3.set_thumbnail(url=avatar.url)
                embed3.set_footer(text=f"configuration type: REMOVE_FROM")

                await interaction.response.send_message(embed=embed3, ephemeral=ephemeral) 

            if configuration == "make":
                change = int(
                    real_amount) - users[1]  # if amount to change to was 5000 and wallet_amt was 6000, new = -1000
                await Economy.update_bank_new(member, conn, +change, deposit_mode)
                embed4 = discord.Embed(title='Success',
                                       description=f"\U0000279c **{member.display_name}**'s "
                                                   f"**`{deposit_mode}`** balance has been "
                                                   f"changed to {CURRENCY}{abs(users[1] + change):,}.",
                                       colour=discord.Colour.dark_purple(), timestamp=datetime.now())
                embed4.set_footer(text=f"configuration type: ALTER_TO")
                embed4.set_thumbnail(url=avatar.url)
                embed4.set_author(name=f"Requested by {interaction.user.name}", icon_url=interaction.user.avatar.url,
                                  url='https://www.youtube.com/watch?v=dQw4w9WgXcQ')
                await interaction.response.send_message(embed=embed4, ephemeral=ephemeral) 

    @app_commands.command(name='pin', description='pin a message in any channel.')
    @app_commands.guilds(Object(id=829053898333225010), Object(id=780397076273954886))
    @app_commands.describe(message_id='the ID of the message to be pinned',
                           reason='the reason for pinning this message',
                           channel_name="the channel to fetch the pinned message from")
    async def pin_it(self, interaction: discord.Interaction, channel_name: Optional[discord.abc.GuildChannel],
                     message_id: str, reason: Optional[str]):

        try:

            if channel_name is None:
                channel_name = interaction.channel

            channel = await self.client.fetch_channel(channel_name.id)
            message = await channel.fetch_message(int(message_id))

            await message.pin(reason=f'Requested by {interaction.user.name}.') if reason is None else await message.pin(
                reason=f"Provided by {interaction.user.name}: {reason}")

            await interaction.response.send_message( 
                f"successfully pinned the message of id {message_id} sent by {message.author.name}.\n\n",
                ephemeral=True, delete_after=3.0)

        except discord.NotFound:

            await interaction.response.send_message( 
                'failed to pin message, it was not found or was deleted.')

        except discord.HTTPException:

            await interaction.response.send_message( 
                'failed to pin message, probably due to the channel reaching the 50 pin quota.',
                ephemeral=True, delete_after=3.0)

    @commands.command(name='cthr', aliases=['ct', 'create_thread'], description='preset to create forum channels.')
    async def create_thread(self, ctx: commands.Context, thread_name: str):
        if isinstance(ctx.channel, discord.TextChannel):
            thread = await ctx.channel.create_thread(name=thread_name, auto_archive_duration=10080, message=discord.Object(ctx.message.id))
            await thread.send("Your thread has been created, with name **{0}**".format(thread_name))
        else:
            await ctx.send("Invalid channel: you must be in a text channel to call this command.")

    @app_commands.command(name='react',
                          description='force-react to messages with any reaction.')
    @app_commands.guilds(Object(id=829053898333225010), Object(id=780397076273954886))
    @app_commands.describe(message_id='the ID of the message to react to:',
                           emote='the name of the emoji to react with, e.g., KarenLaugh')
    async def react(self, interaction: discord.Interaction, message_id: str, emote: str):
        b = await interaction.guild.fetch_channel(interaction.channel.id)
        c = await b.fetch_message(int(message_id))
        emoji = self.return_custom_emoji(emote)  # a function to return a custom emoji
        await c.add_reaction(emoji)
        await interaction.response.send_message( 
            content='the emoji has been added to the message', ephemeral=True, delete_after=3.0)

    @commands.command(name='sync', description='sync client tree for changes.', aliases=("sy",))
    async def sync_tree(self, ctx: commands.Context) -> None:
        print("syncing")
        # Application command synchronization
        # ctx.bot.tree.copy_global_to(guild=discord.Object(id=780397076273954886))
        # ctx.bot.tree.copy_global_to(guild=discord.Object(id=829053898333225010))
        await ctx.bot.tree.sync(guild=discord.Object(id=780397076273954886))
        await ctx.bot.tree.sync(guild=discord.Object(id=829053898333225010))
        # await ctx.bot.tree.sync(guild=None)
        await ctx.message.add_reaction('<:successful:1183089889269530764>')

    @commands.command(name='unload', description='unloads a file from the client.')
    async def unload(self, ctx: commands.Context, cog_name: str):
        await self.client.unload_extension(cog_name)
        await ctx.send(f'`cogs.{cog_name}` has been unloaded.', ephemeral=True, delete_after=4.0)

    @commands.command(name='load', description='loads a file to the client.')
    async def load(self, ctx: commands.Context, cog_name: str):
        await self.client.load_extension(cog_name)
        await ctx.send(f'`cogs.{cog_name}` has been loaded.', delete_after=4.0)

    @commands.command(name='reload', description='reload a file to the client.')
    async def reload(self, ctx: commands.Context, cog_name: str):
        await self.client.reload_extension(cog_name)
        await ctx.send(f'`cogs.{cog_name}` has been reloaded.', delete_after=4.0)

    @commands.command(name='eval', description='evaluates arbitrary code.')
    async def eval(self, ctx, *, script_body: str):
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
        except Exception as e:
            value = stdout.getvalue()
            await ctx.send(f'```py\n{value}{format_exc()}\n```')
        else:
            value = stdout.getvalue()
            try:
                await ctx.message.add_reaction('<:successful:1183089889269530764>')
            except:
                pass

            if ret is None:
                if value:
                    await ctx.send(f'```py\n{value}\n```')
            else:
                self._last_result = ret
                await ctx.send(f'```py\n{value}{ret}\n```')

    @commands.command(name='blank', description='newlines to clear a channel.')
    async def blank(self, ctx):
        await ctx.send(
            ".\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\nCleared.")

    @commands.command(name='regex', description='load automod match_regex rules.')
    async def automod_regex(self, ctx):
        await ctx.guild.create_automod_rule(name='new rule by cxc',
                                            event_type=discord.AutoModRuleEventType.message_send,
                                            trigger=discord.AutoModTrigger(regex_patterns=["a", "b", "c", "d", "e"]),
                                            actions=[
                                                discord.AutoModRuleAction(duration=timedelta(minutes=5.0))])
        await ctx.message.add_reaction('<:successful:1183089889269530764>')

    @commands.command(name='mentions', description='load automod mass_mentions rules.')
    async def automod_mentions(self, ctx):
        await ctx.guild.create_automod_rule(name='new rule by cxc',
                                            event_type=discord.AutoModRuleEventType.message_send,
                                            trigger=discord.AutoModTrigger(mention_limit=5),
                                            actions=[
                                                discord.AutoModRuleAction(duration=timedelta(minutes=5.0))])
        await ctx.message.add_reaction('<:successful:1183089889269530764>')

    @commands.command(name='keyword', description='load automod by_keyword rules.')
    async def automod_keyword(self, ctx, the_word):
        await ctx.guild.create_automod_rule(name='new rule by cxc',
                                            event_type=discord.AutoModRuleEventType.message_send,
                                            trigger=discord.AutoModTrigger(keyword_filter=[f'{the_word}']),
                                            actions=[
                                                discord.AutoModRuleAction(duration=timedelta(minutes=5.0))])
        await ctx.message.add_reaction('<:successful:1183089889269530764>')

    @commands.command(name='update', description='preset to update channel info.')
    async def push_update(self, ctx):

        await ctx.message.delete()
        channel = await self.client.fetch_channel(1121445944576188517)
        original = await channel.fetch_message(1142392804446830684)

        embed = discord.Embed(title='Update Schedule',
                              description=f'This embed will post any **changes to the server** in the near future. This '
                                          f'includes any feature updates within the server and any other optimization '
                                          f'changes.\n',
                              colour=discord.Colour.from_rgb(101, 242, 171))
        embed.add_field(name="There's nothing here yet.",
                        value="There are no planned changes for the server right now.")
        embed.set_footer(text='Check back later for any known scheduled updates..',  # replace 'more' w/ 'any known'
                         icon_url='https://pa1.narvii.com/6025/9497042b3aad0518f08dd2bfefb0e2262f4a7149_hq.gif')
        await original.edit(embed=embed)

    @commands.command(name='update3', description='preset to modify rules and guidelines.')
    async def push_update3(self, ctx):
        await ctx.message.delete()
        channel = await self.client.fetch_channel(902138223571116052)
        original = await channel.fetch_message(1140258074297376859)
        r = discord.Embed(title="Rules & Guidelines",
                          description='We look forward to seeing you become a regular here! '
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
                                      '[Discord Terms of Service](https://discord.com/terms)',
                          colour=discord.Colour.from_rgb(208, 189, 196))
        r.set_footer(icon_url='https://cdn.discordapp.com/emojis/1170379416845692928.gif?size=160&quality=lossless',
                     text='thanks for reading and respecting our guidelines! now go have fun!')

        await original.edit(embed=r)

    @commands.command(name='update2', description='preset to edit welcome banner.')
    async def push_update2(self, ctx):
        await ctx.message.delete()
        channel = await self.client.fetch_channel(1121445944576188517)
        original = await channel.fetch_message(1140952278862401657)
        a = "C:\\Users\\georg\\Downloads\\Media\\attachments\\rsz_tic.png"
        that_file = discord.File(a, filename="image.png")
        intro = discord.Embed(colour=discord.Colour.from_rgb(31, 16, 3))
        intro.set_image(url="attachment://image.png")
        embed = discord.Embed(description="# <:dscbday:1174417905006428190> Origins.\n"
                                          "This is yet another hangout to theorize your day-to-day discussions. The "
                                          "server was created on the **6th of April 2021** to provide a space that "
                                          "that fosters a chill and mature community that can talk about "
                                          "anything and everything.\n\n"
                                          "You might be asking: what does cc actually stand for? Truthfully speaking, "
                                          "we don't know either, but our best guess is something along the lines of a "
                                          "*collective community*, this being the aim by the server to date.\n\n"
                                          "We hope you enjoy your stay, and we wish you a wonderful journey.\n"
                                          "And don't forget; you're here forever.",
                              colour=discord.Colour.from_rgb(70, 55, 230))
        tbp = "<:e2_bluedot:1153776233499336764>"

        roles = discord.Embed(description=f"# <:ismember:1180267726179143863> Server Roles Information.\n"
                                          f"- <@&893550756953735278>\n"
                                          f" - People who manage and moderate cc.\n\n"
                                          f"- <@&1140197893261758505>\n"
                                          f" - People who have a high rating on the <#1121097762537222235>.\n\n"
                                          f"- <@&1047575848980594758>\n"
                                          f" - People who joined Discord in 2019.\n\n"
                                          f"- <@&1121426143598354452>\n"
                                          f" - People with access to private features.\n\n"
                                          f"- <@&990900517301522432>\n"
                                          f" - People with full music control over music bots.\n\n"
                                          f"- <@&1168204249096785980>\n"
                                          f" - People with access to new features on {self.client.user.mention}.\n\n"
                                          f"- **Other custom roles**\n"
                                          f" - <@&1124762696110309579>, <@&1047576437177200770>, <@&1150354605000118352"
                                          f">, <@&1150353118324871198>, <@&1150354158843596822>, <@&992155455067525140>"
                                          f", <@&1144268897709723700>.\n"
                                          f" - You can make your own custom role by reaching **Level 40**.",
                              colour=discord.Colour.from_rgb(101, 96, 243))

        ranks = discord.Embed(description=f'# <:extlink:1174417919581630526> Level Roles & Perks.\n'
                                          f'Your activity in the server will not be left unrewarded! Level up by participating in '
                                          f'text channels. The more active you are, the higher levels attained and the better perks'
                                          f' you receive.\n\n'
                                          f'<@&923930948909797396>\n\n'
                                          f'<@&923931088613699584>\n'
                                          f'{tbp} \U000023e3 **335,000,000**\n\n'
                                          f'<@&923931156125204490>\n'
                                          f'{tbp} Your own custom channel\n\n'
                                          f'<@&923931553791348756>\n'
                                          f'{tbp} Request a feature for {self.client.user.mention}\n\n'
                                          f'<@&923931585953280050>\n'
                                          f'{tbp} \U000023e3 **1,469,000,000**\n\n'
                                          f'<@&923931615208546313>\n'
                                          f'{tbp} Access to a custom snipe command\n\n'
                                          f'<@&923931646783287337>\n'
                                          f'{tbp} \U000023e3 **17,555,000,000**, 5 \U0001f3c6\n\n'
                                          f'<@&923931683311456267>\n'
                                          f'{tbp} \U000023e3 **56,241,532,113**\n'
                                          f'{tbp} 3,500 free EXP\n\n'
                                          f'<@&923931729016795266>\n'
                                          f'{tbp} Request a feature for {self.client.user.mention}\n'
                                          f'{tbp} Your own custom role\n\n'
                                          f'<@&923931772020985866>\n'
                                          f'{tbp} \U000023e3 **72,681,998,999**, 64 \U0001f3c6\n\n'
                                          f'<@&923931819571810305>\n'
                                          f'{tbp} The Personal Token of Appreciation\n\n'
                                          f'<@&923931862001414284>\n'
                                          f' {tbp} *A random privilege, see Appendix 1 for details*',
                              colour=discord.Colour.from_rgb(69, 105, 233))
        second_embed = discord.Embed(description='# The Appendix 1.'
                                                 '\nIf you somehow manage to reach **<@&923931862001414284>**, '
                                                 'out of 6 events, 1 will '
                                                 'take place. A dice will be rolled and the outcome will ultimately depend '
                                                 'on a dice roll.\n\n'
                                                 '## Event 1:\n'
                                                 '\U0000279c Your level of experience and wisdom will prove you worthy of'
                                                 ' receiving <@&912057500914843680>, a role only members of high authority '
                                                 'can attain.\n'
                                                 '## Event 2:\n'
                                                 '\U0000279c Your familiarity with this server will allow you to get '
                                                 '1 Month of Discord Nitro immediately when available.\n'
                                                 '## Event 3:\n'
                                                 '\U0000279c This is a karma roll. you will receive **nothing.**\n'
                                                 '## Event 4:\n'
                                                 '\U0000279c For the sake of nonplus, **this event will not be disclosed'
                                                 ' until it is received.**\n'
                                                 '## Event 5:\n'
                                                 '\U0000279c This is a karma roll. you will receive **nothing.**\n'
                                                 '## Event 6:\n'
                                                 '\U0000279c This is a special one, only one '
                                                 'could occur: a face reveal'
                                                 ' or a voice reveal by the owner. the choice will be made by '
                                                 'another dice roll (yes, another one).\n\n'
                                                 '# Side Note:\n'
                                                 'To remove the possibility of advantage, you cannot earn EXP '
                                                 '**while executing slash commands**.\n'
                                                 'Refer to this message for more information: https://discord.com'
                                                 '/channels/829053898333225010/1121094935802822768/1166397053329477642',
                                     colour=discord.Colour.from_rgb(103, 2, 50))
        second_embed.set_footer(text='Reminder: the perks from all roles are one-time use only and cannot be reused or '
                                     'recycled.')
        try:
            await original.edit(attachments=[that_file], embeds=[intro, embed, ranks, roles, second_embed])
        except discord.HTTPException as err:
            ch = self.client.fetch_channel(1124090797613142087)
            await ch.send(err.__cause__)

    @commands.command(name='update4', description='updates the progress tracker.')
    async def override_economy(self, ctx):
        await ctx.message.delete()
        channel = await self.client.fetch_channel(1124782048041762867)
        original = await channel.fetch_message(1166793975466831894)
        temporary = discord.Embed(title="Temporary Removal of the Economy System",
                                  description="as the title states, we have removed the Economy System in c2c (**for now**). <a:aaaaa:944505181150773288>\n\n"
                                              "the reason being is the vast amount of bugs and inefficiencies in the system "
                                              "which has been eating on the limited resources we have available to keep the bot running.\n\n"
                                              "not to fret though! it will be back in a completley new state! we have many exciting plans in store over the "
                                              "upcoming years for the bot, but right now <@992152414566232139> and <@546086191414509599> (but mostly <@992152414566232139>) are working on patching "
                                              "all of the major issues that are in the Economy System. we hope to bring back this part of the system by **__late 2024__** but we cannot make any promises!\n\n"
                                              "we plan to modify every single command currently available under this category and add more that are to come, hence this is a extensive programme that will **require a lot of time**. "
                                              "This is made hindered by the current academic situation both the developers are in at this time, so please bear with us and we will not dissapoint (especially with <@992152414566232139> <a:ehe:928612599132749834>)!",
                                  colour=discord.Colour.from_rgb(102, 127, 163))
        temporary.add_field(name="Roadmap",
                            value='to make it certain, here is an outline of what we will be doing over the next year. the arrows beneath these commitments will change indicating the progress of each section.\n'
                                  '<:redA:1166790106422722560> - **Not Started**\n'
                                  '<:yelA:1166790134801379378> - **In Progress**\n'
                                  '<:join:1163901334412611605> - **Completed**\n\n'
                                  '<:join:1163901334412611605> **December 2023 (late)**: start of full rehaul of every command that currently exists.\n'
                                  '<:yelA:1166790134801379378> **July 2024 (early)**: new commands/essential functions to the Economy system added.\n'
                                  '<:redA:1166790106422722560> **August 2024 (late)**: economy system fully operational and ready for use.')
        temporary.add_field(name="Acknowledgement",
                            value="<a:e1_imhappy:1144654614046724117> <@992152414566232139> (<@&1047576437177200770>) - contributing to **87.5**% of the full programme, making it possible in the first place (will write the code).\n"
                                  "<a:catPat:1143936898449027082> <@546086191414509599> (<@&1124762696110309579>) - contributing to **12.5**% of the full programme (will make ideas for new commands)\n\n"
                                  "we would not be able to recover the Economy System without <@992152414566232139>, she is the literal backbone of its revival! thank her for making it possible!")
        await original.edit(embed=temporary)

    @commands.command(name='ccil', description='sends invite for cc.')
    async def preset_ccil(self, ctx):
        await ctx.message.delete()
        await ctx.send("**Permanent Invite Link** - discord.gg/W3DKAbpJ5E\n"
                       "This link ***will never*** expire, but note that it can "
                       "be disabled by an Administrator without notice.", silent=True)

    @app_commands.command(name='edit', description='edit a message from me.')
    @app_commands.guilds(Object(id=829053898333225010), Object(id=780397076273954886))
    @app_commands.describe(msg='The ID of the message to edit', new_content='The new content to replace it with')
    async def edit_msg(self, interaction: discord.Interaction, msg: str, new_content: str):
        await interaction.response.defer(thinking=True) 
        a = await self.client.fetch_guild(interaction.guild.id)
        b = await a.fetch_channel(interaction.channel.id)
        c = await b.fetch_message(int(msg))
        await c.edit(content=new_content)
        await interaction.followup.send(content="The edits have been made", ephemeral=True, delete_after=3.0)

    @commands.command(name='quit', description='quits the bot gracefully.')
    async def quit_client(self, ctx):
        await ctx.message.add_reaction('<:successful:1183089889269530764>')
        await self.client.session.close() 
        await self.client.pool_connection.close() 
        await self.client.http.close()
        await self.client.close()

    @commands.command(name='say', description='repeat what you typed.')
    async def say(self, ctx, *, text_to_say):
        """Makes the bot say what you want it to say."""
        await ctx.message.delete()
        await ctx.send(f"{text_to_say}")

    @app_commands.command(name='repeat', description='repeat what you typed (slash ver).')
    @app_commands.guilds(Object(id=829053898333225010), Object(id=780397076273954886))
    @app_commands.describe(message='what should i say?', channel='what channel should i say it in?')
    async def repeat(self, interaction: discord.Interaction, message: str, channel: discord.TextChannel):

        if channel:
            if channel.id != interaction.channel.id:
                ch = await self.client.fetch_channel(channel.id)
                await ch.send(message)
                return await interaction.response.send_message( 
                    f"Done. Sent to <#{channel.id}>.", ephemeral=True)
            else:
                return await interaction.response.send_message( 
                    "Point of giving a channel that is the same as the one you're in?", ephemeral=True)
        else:
            ch = await self.client.fetch_channel(interaction.channel.id)
            await ch.send(message)
            return await interaction.response.send_message("Done.", ephemeral=True) 


async def setup(client):
    await client.add_cog(Administrate(client))
