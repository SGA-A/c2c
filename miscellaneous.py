from asyncio import sleep
from time import perf_counter
from PyDictionary import PyDictionary
import discord
from other.pagination import Pagination
import datetime
from random import choice
from psutil import cpu_percent, virtual_memory
from typing import Literal, Union, Optional
from math import log10, floor
from discord.ext import commands
from other.spshit import get_song_attributes
from discord import app_commands, Interaction, Object
from unicodedata import name


found_spotify = False


def membed(descriptioner: str) -> discord.Embed:
    """Quickly create an embed with a custom description using the preset."""
    membedder = discord.Embed(colour=0x2F3136,
                           description=descriptioner)
    return membedder


def round_to_sf(number, sf=2):
    """
    Round a number to a specified number of significant figures.
    """
    if number == 0:
        return 0.0

    order_of_magnitude = 10 ** (sf - int(floor(log10(abs(number)))) - 1)
    rounded_number = round(number * order_of_magnitude) / order_of_magnitude

    return rounded_number


def return_random_color():
    colors_crayon = {
        "warm pink": discord.Color.from_rgb(255, 204, 204),
        "warm orange": discord.Color.from_rgb(255, 232, 204),
        "warm yellow": discord.Color.from_rgb(242, 255, 204),
        "warm green": discord.Color.from_rgb(223, 255, 204),
        "warm blue": discord.Color.from_rgb(204, 255, 251),
        "warm purple": discord.Color.from_rgb(204, 204, 255),
        "polar ice": discord.Color.from_rgb(204, 255, 224),
        "polar pink": discord.Color.from_rgb(212, 190, 244),
        "unusual green": discord.Color.from_rgb(190, 244, 206),
        "sea blue": discord.Color.from_rgb(255, 203, 193),
        "pastel green": discord.Color.from_rgb(175, 250, 216),
        "lighter blue": discord.Color.from_rgb(131, 227, 255),
        "usual(?) green": discord.Color.from_rgb(191, 252, 198),
        "deep purple": discord.Color.from_rgb(80, 85, 252)
    }
    return choice(list(colors_crayon.values()))


class FeedbackModal(discord.ui.Modal, title='Submit feedback'):
    fb_title = discord.ui.TextInput(
        style=discord.TextStyle.short,
        label="Title",
        required=False,
        placeholder="Give your feedback a title.."
    )

    message = discord.ui.TextInput(
        style=discord.TextStyle.long,
        label='Description',
        required=True,
        placeholder="Provide the feedback here."
    )

    async def on_submit(self, interaction: discord.Interaction):
        channel = interaction.guild.get_channel(1122902104802070572)
        embed = discord.Embed(title=f'New Feedback: {self.fb_title.value or "Untitled"}',
                              description=self.message.value, colour=0x2F3136)

        embed.set_author(name=interaction.user)
        await channel.send(embed=embed)
        success = discord.Embed(colour=0x2F3136,
                                description=f"- Your response has been submitted.\n"
                                            f" - Developers will consider your feedback accordingly and compensation "
                                            f"will then be decided upfront.\n\n"
                                            f"*You may get a unique badge or other type of reward based on how "
                                            f"constructive and thoughtful your feedback is.*")
        await interaction.response.send_message(embed=success, ephemeral=True) # type: ignore

    async def on_error(self, interaction: discord.Interaction, error):
        return await interaction.response.send_message(f"we had trouble processing your feedback, try again later.") # type: ignore


class InviteButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60.0)
        self.add_item(discord.ui.Button(
            label="Invite Link",
            url="https://discord.com/api/oauth2/authorize?client_id=1047572530422108311&permissions=8&scope=applications.commands%20bot",
            style=discord.ButtonStyle.danger))


class Miscellaneous(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    def len_channels(self):
        total_channels = 0
        for guild in self.client.guilds:
            total_channels += len(guild.channels)
        return total_channels

    @commands.command(name='invite', description='link to invite c2c to your server.')
    @commands.guild_only()
    async def invite_bot(self, ctx):
        await ctx.send(embed=membed("The button component gives a direct link to invite me to your server.\n"
                                    "Bear in mind only the developers can invite the bot."), view=InviteButton())

    @commands.command(name='calculate', aliases=('c', 'calc'), description='compute a mathematical expression.')
    @commands.guild_only()
    async def calculator(self, ctx: commands.Context, *, expression):
        try:
            result = eval(expression)
            await ctx.reply(f'**{ctx.author.name}**, the answer is `{result}`', mention_author=False)
        except Exception as e:
            await ctx.reply(f'**Error:** {str(e)}', mention_author=False)

        await sleep(1)

    @commands.command()
    async def ping(self, ctx):
        start = perf_counter()
        message = await ctx.send("Ping...")
        end = perf_counter()
        duration = (end - start) * 1000
        await message.edit(content='REST: {0:.2f}ms **\U0000007c** '
                                   'WS: {1} ms'.format(duration, round(self.client.latency * 1000)))

    @app_commands.command(name='bored', description='find something to do if you\'re bored.')
    @app_commands.guilds(Object(id=829053898333225010), Object(id=780397076273954886))
    @app_commands.describe(activity_type='the type of activity to think of')
    async def prompt_act(self, interaction: discord.Interaction,
                         activity_type: Optional[Literal["education", "recreational", "social", "diy", "charity",
                                                         "cooking", "relaxation", "music", "busywork"]]):
        if activity_type is None:
            activity_type = ""
        else:
            activity_type = f"?type={activity_type}"
        async with self.client.session.get( # type: ignore
                f"http://www.boredapi.com/api/activity{activity_type}") as response:
            if response.status == 200:
                resp = await response.json()
                await interaction.response.send_message(f"{resp['activity']}.") # type: ignore
            else:
                await interaction.response.send_message( # type: ignore
                    embed=membed("An unsuccessful request was made. Try again later."))
    # fetches all of the emojis found within the client's internal cache.

    @app_commands.command(name='emojis', description='fetches all of the emojis c2c can access.')
    @app_commands.guilds(Object(id=829053898333225010), Object(id=780397076273954886))
    async def emojis_paginator(self, interaction: discord.Interaction):
        length = 10
        emotes_all = []
        for i in self.client.emojis:
            if i.animated:
                fmt = "<a:"
            else:
                fmt = "<:"
            needed = f"{i} (**{i.name}**) - `{fmt}{i.name}:{i.id}>`"
            emotes_all.append(needed)

        async def get_page_part(page: int):
            emb = discord.Embed(title="Emojis: c2c",
                                description="> This is a command that fetches **all** of the emojis found in the client's internal cache and their associated atributes.\n",
                                colour=0x2F3136)
            emb.set_thumbnail(url=self.client.user.avatar.url)
            offset = (page - 1) * length
            for user in emotes_all[offset:offset + length]:
                emb.description += f"{user}\n"
            emb.set_author(name=f"Requested by {interaction.user.name}",
                           icon_url=f"{interaction.user.avatar.url if interaction.user.avatar else None}")
            n = Pagination.compute_total_pages(len(emotes_all), length)
            emb.set_footer(text=f"This is page {page} of {n}")
            return emb, n

        await Pagination(interaction, get_page_part).navigate()

    @commands.command(name='spsearch', description='search for songs on spotify.', aliases=('sps', 'ss'))
    @commands.guild_only()
    async def search_sp(self, ctx, *, name_of_song):
        async with ctx.typing():
            song_emb = discord.Embed(colour=discord.Colour.from_rgb(79, 190, 78),
                                     timestamp=datetime.datetime.now(datetime.UTC))
            results = get_song_attributes(name_of_song)
            song_emb.set_thumbnail(url=results[0]['image_url'])
            song_emb.set_footer(icon_url=self.client.user.avatar.url,
                                text='duplicates may be displayed')
            lisr = []
            boarder = '<:blurpleL:1159506273771978837>'
            for index, result in enumerate(results, start=1):
                if 0 <= result['popularity'] <= 33:
                    rating = '(Unpopular \U00002b50)'
                elif 33 <= result['popularity'] <= 66:
                    rating = '(Quite Popular \U0001f31f )'
                else:
                    rating = '(Very Popular \U00002728)'
                lisr.append(f'\n### Result {index}:\n'
                            f'**Song Name**: {result['song_name']}\n'
                            f'**Artist(s)**: {', '.join(result['artists'])}\n'
                            f'**Track URL**: [Click Here]({result['external_urls']['spotify']})\n'
                            f'**Popularity**: {result['popularity']} {rating}')

            # noinspection PyUnboundLocalVariable
            song_emb.description = (f"## Search Results\n"
                                    f'> The **`popularity`** attribute may be difficult to understand. Type the command '
                                    f'[`>aboutpop`](https://www.google.com) to learn more about this attribute.'
                                    f"{f'\n{boarder*7}'.join(lisr)}")
            await ctx.send(embed=song_emb)

    @commands.command(name='aboutpop', description='explains how popularity is calculated.')
    @commands.guild_only()
    async def about_pop_attr(self, ctx: commands.Context):
        async with ctx.typing():
            embed = membed(
                "# How track popularity really is calculated\n"
                "> If you have no idea what this is, learn more by calling [`>spsearch`](https://www.google.com)\n\n"
                "- The popularity of a track is a value between **`0`** and **`100`**, with **`100`** being the most popular.\n"
                " - The popularity is calculated by algorithm and is based, in the most part, on the total number of plays "
                "the track has had and how recent those plays are.\n"
                " - Generally speaking, songs that are being played a lot now will have a higher popularity than songs "
                "that were played a lot in the past. \n"
                " - Duplicate tracks (e.g. the same track from a single and an album) are rated independently.\n\n"
                "**N.B**: The popularity value may lag actual popularity by a few days: the value is **not** "
                "updated in real time!")
            await ctx.send(embed=embed)

    @app_commands.command(name='inviter', description='generate a new server invite link.')
    @app_commands.guilds(Object(id=829053898333225010), Object(id=780397076273954886))
    @app_commands.checks.has_permissions(create_instant_invite=True)
    @app_commands.describe(invite_lifespan='the duration of which the invite should last, must be > 0.',
                           maximum_uses='how many uses the invite could be used for. 0 for unlimited uses.')
    async def gen_new_invite(self, interaction: discord.Interaction, invite_lifespan: int, maximum_uses: int):
        if invite_lifespan <= 0:
            return await interaction.response.send_message( # type: ignore
                embed=membed("The invite lifespan cannot be **less than or equal to 0**."))

        maximum_uses = abs(maximum_uses)
        day_to_sec = invite_lifespan * 86400
        invoker_channel = interaction.channel
        avatar = interaction.user.avatar or interaction.user.default_avatar
        generated_invite = await invoker_channel.create_invite(reason=f'Creation requested by {interaction.user.name}',
                                                               max_age=day_to_sec, max_uses=maximum_uses)
        match maximum_uses:
            case 0:
                maxim_usage = "No limit to maximum usage"
            case _:
                maxim_usage = f"Max usages set to {generated_invite.max_uses}"
        formatted_expiry = discord.utils.format_dt(generated_invite.expires_at, 'R')
        success = discord.Embed(title='Successfully generated new invite link',
                                description=f'**A new invite link was created.**\n- Invite channel set to {generated_invite.channel}\n'
                                            f'- {maxim_usage}\n'
                                            f'- Expires {formatted_expiry}\n'
                                            f'- Invite Link is: {generated_invite.url}',
                                colour=0x2F3136)
        success.set_author(name=f'Requested by {interaction.user.name}', icon_url=avatar.url)
        await interaction.response.send_message(embed=success) # type: ignore

    @app_commands.command(name='define', description='find the definition of any word of your choice.')
    @app_commands.guilds(Object(id=829053898333225010), Object(id=780397076273954886))
    @app_commands.checks.cooldown(1, 3, key=lambda i: i.user.id)
    @app_commands.describe(word='the term that is to be defined for you')
    async def define_word(self, interaction: discord.Interaction, word: str):
        try:
            the_dictionary = PyDictionary()
            choicer = word
            meaning = the_dictionary.meaning(f'{choicer.lower()}')
            for item in meaning.items():
                for thing in item:
                    if isinstance(thing, list):
                        unique_colour = return_random_color()
                        the_result = discord.Embed(title=f'Define: {choicer.lower()}',
                                                   description=f'This shows all the available definitions for the word {choicer}.',
                                                   colour=unique_colour)
                        for x in range(0, len(thing)):
                            the_result.add_field(name=f'Definition {x + 1}', value=f'{thing[x]}')
                        if len(the_result.fields) == 0:
                            the_result.add_field(name=f'Looks like no results were found.',
                                                 value=f'We couldn\'t find a definition for {choicer.lower()}.')
                        await interaction.response.send_message(embed=the_result) # type: ignore
                    else:
                        continue
        except AttributeError:
            await interaction.response.send_message(content=f'try again, but this time input an actual word.') # type: ignore

    @app_commands.command(name='randomfact', description='generates a random fact.')
    @app_commands.guilds(Object(id=829053898333225010), Object(id=780397076273954886))
    @app_commands.checks.cooldown(1, 5, key=lambda i: i.user.id)
    async def random_fact(self, interaction: Interaction):
        limit = 1
        api_url = 'https://api.api-ninjas.com/v1/facts?limit={}'.format(limit)
        parameters = {'X-Api-Key': self.client.NINJAS_API_KEY} # type: ignore
        async with self.client.session.get(api_url, params=parameters) as resp: # type: ignore
            text = await resp.json()
            the_fact = text[0].get('fact')
            await interaction.response.send_message(f"{the_fact}.") # type: ignore

    @app_commands.command(name='com', description='finds out what the most common letters in word(s) are.')
    @app_commands.guilds(Object(id=829053898333225010), Object(id=780397076273954886))
    @app_commands.describe(word='the word(s) to find the frequent letters of')
    async def common(self, interaction: Interaction, word: str):

        letters = []
        frequency = []

        for letter in word:
            if letter not in letters:
                letters.append(letter)
                frequency.append(1)
            else:
                i = letters.index(letter)
                frequency[i] += 1

        n = max(frequency)

        # Look for most common letter(s) and add to commons list
        commons = []
        counter = 0
        for m in frequency:
            if n == m:
                commons.append(letters[counter])
            counter += 1

        # Format most common letters
        commons.sort()
        answer = ''
        for letter in commons:
            answer = answer + letter + ' '

        # Remove extra space at the end of the string
        answer = answer[:-1]

        await interaction.response.send_message(embed=membed(f'The most common letter is {answer}.')) # type: ignore

    @app_commands.command(name='charinfo', description='show info about characters (max 25).')
    @app_commands.guilds(Object(id=829053898333225010), Object(id=780397076273954886))
    @app_commands.describe(characters='any written letters or symbols')
    async def charinfo(self, interaction: Interaction, *, characters: str):
        """Shows you information about a number of characters.
        Only up to 25 characters at a time.
        """

        def to_string(c):
            digit = f'{ord(c):x}'
            the_name = name(c, 'Name not found.')
            return f'`\\U{digit:>08}`: {the_name} - {c} \N{EM DASH} <http://www.fileformat.info/info/unicode/char/{digit}>'

        msg = '\n'.join(map(to_string, characters))
        if len(msg) > 2000:
            await interaction.response.send_message( # type: ignore
                content='the output is too long to display', ephemeral=True, delete_after=4.0)
            return
        await interaction.response.send_message(content=f'{msg}') # type: ignore

    @commands.command(name='spotify', aliases=('sp', 'spot'), description='display a user\'s spotify RP information.')
    @commands.guild_only()
    async def find_spotify_activity(self, ctx: commands.Context, *, username: Union[discord.Member, discord.User] = None):
        global found_spotify
        async with ctx.typing():
            if username is None:
                username = ctx.author
            if username.activities:
                found_spotify = False
                for activity in username.activities:
                    if str(activity).lower() == "spotify":
                        found_spotify = True
                        embed = discord.Embed(
                            title=f"{username.name}'s Spotify",
                            description=f"Listening to {activity.title}",
                            color=activity.colour)
                        duration = str(activity.duration)
                        final_duration = duration[3:7]
                        embed.set_thumbnail(url=activity.album_cover_url)
                        if username.avatar:
                            embed.set_author(name=f"{username.display_name}", icon_url=username.avatar.url)
                        else:
                            embed.set_author(name=f"{username.display_name}")
                        embed.add_field(name="Artist", value=activity.artist)
                        embed.add_field(name="Album", value=activity.album)
                        embed.add_field(name="Song Duration", value=final_duration)
                        embed.set_footer(text="Song started at {}".format(activity.created_at.strftime("%H:%M %p")))
                        embed.url = f"https://open.spotify.com/embed/track/{activity.track_id}"
                        return await ctx.send(embed=embed)
                if not found_spotify:
                    return await ctx.send(f"{username.display_name} is not listening to Spotify.")
            await ctx.send(f"{username.display_name} has no activity.")

    @app_commands.command(name='feedback', description='send your feedback to the c2c developers.')
    @app_commands.guilds(Object(id=829053898333225010), Object(id=780397076273954886))
    async def feedback(self, interaction: discord.Interaction):
        feedback_modal = FeedbackModal()
        await interaction.response.send_modal(feedback_modal) # type: ignore

    @app_commands.command(name='about', description='shows some stats related to the client.')
    @app_commands.guilds(Object(id=829053898333225010), Object(id=780397076273954886))
    @app_commands.checks.cooldown(1, 3, key=lambda i: i.user.id)
    async def about_the_bot(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True) # type: ignore
        amount = 0
        lenslash = len(await self.client.tree.fetch_commands(guild=interaction.guild))  # all interaction cmds
        lentxt = len(self.client.commands)
        amount += (lenslash+lentxt)
        branch = "<:arrowe:1180428600625877054>"
        embed = discord.Embed(title='About c2c',
                              description="c2c was made with creativity in mind. It is a custom bot designed for cc "
                                          "that provides a wide range of utility and other services.\n\n"
                                          "- We grow based on feedback, it's what empowers our community and without it"
                                          " the bot would not have been the same.\n"
                                          " - </feedback:1179817617767268353> is the medium through which we receive "
                                          "your feedback, although it doesn't have to be. Simply relaying your thoughts"
                                          " to the developers is enough as well!\n"
                                          " - We accept **any** requests or features to the bot, as a community-based "
                                          "bot thrives based on the user's needs. So yes, **your feedback matters.**\n",
                              timestamp=datetime.datetime.now(datetime.UTC),
                              colour=discord.Colour.from_rgb(145, 149, 213),
                              url=self.client.user.avatar.url)
        embed.add_field(name='Run on',
                        value=f'discord.py v{discord.__version__}')
        embed.add_field(name='Activity',
                        value=f'{self.client.activity.name or "No activity"}')
        embed.add_field(name='Internal Cache Ready',
                        value=f'{str(self.client.is_ready())}')
        embed.add_field(name=f'Process',
                        value=f'{branch}CPU: {cpu_percent()}%\n'
                              f'{branch}RAM: {virtual_memory().percent}%')
        embed.add_field(name='Servers',
                        value=f'{len(self.client.guilds)}\n'
                              f'{branch}{self.len_channels()} channels\n'
                              f'{branch}{len(self.client.emojis)} emojis\n'
                              f'{branch}{len(self.client.stickers)} stickers')
        embed.add_field(name='Users',
                        value=f'{branch}{len(self.client.users)} users\n'
                              f'{branch}{len(self.client.voice_clients)} voice')
        embed.add_field(name='Total Commands Available',
                        value=f'{amount} total\n'
                              f'{branch}{lentxt} (text-based)\n'
                              f'{branch}{lenslash} (slash-based)')
        embed.set_thumbnail(url=self.client.user.avatar.url)
        embed.set_author(name='made possible with discord.py:',
                         icon_url='https://media.discordapp.net/attachments/1124994990246985820/1146442046723330138/'
                                  '3aa641b21acded468308a37eef43d7b3.png?width=411&height=411',
                         url='https://discordpy.readthedocs.io/en/latest/index.html')
        await sleep(5)
        await interaction.followup.send(embed=embed, silent=True)

    @app_commands.command(name='tn', description="returns the time now in any given format.")
    @app_commands.guilds(Object(id=829053898333225010), Object(id=780397076273954886))
    @app_commands.rename(spec="mode")
    @app_commands.describe(spec='the mode of displaying the current time now')
    async def tn(self, interaction: discord.Interaction, spec: Literal["t - returns short time (format HH:MM)",
                 "T - return long time (format HH:MM:SS)", "d - returns short date (format DD/MM/YYYY)",
                 "D - returns long date (format DD Month Year)", "F - returns long date and time (format Day, DD Month Year HH:MM)",
                 "R - returns the relative time since now"] = None) -> None:
        speca = spec[0] if spec else None
        format_dt = discord.utils.format_dt(datetime.datetime.now(), style=speca)
        embed = discord.Embed(description=f'## Timestamp Conversion\n{format_dt}\n'
                                          f'- The epoch time in this format is: `{format_dt}`',
                              colour=return_random_color())
        if interaction.user.avatar: embed.set_thumbnail(url=interaction.user.avatar.url)
        await interaction.response.send_message(embed=embed, ephemeral=True) # type: ignore

    @commands.command(name='avatar', description='display a user\'s enlarged avatar.')
    async def avatar(self, ctx, *, username: Union[discord.Member, discord.User] = None):
        """Shows a user's enlarged avatar (if possible)."""
        embed = discord.Embed(colour=0x2F3136)
        username = username or ctx.author
        avatar = username.display_avatar.with_static_format('png')
        embed.set_author(name=str(username), url=avatar)
        embed.set_image(url=avatar)
        await ctx.send(embed=embed)


async def setup(client):
    await client.add_cog(Miscellaneous(client))
