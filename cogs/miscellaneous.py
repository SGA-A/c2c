from asyncio import sleep
from time import perf_counter
from PyDictionary import PyDictionary
import discord
from xml.etree.ElementTree import fromstring
from other.pagination import Pagination
import datetime
from random import choice
from github import Github
from psutil import Process, cpu_count
from typing import Literal, Union, Optional
from discord.ext import commands
from other.spshit import get_song_attributes
from discord import app_commands, Interaction, Object
from unicodedata import name

ARROW = "<:arrowe:1180428600625877054>"
found_spotify = False


def was_called_in_a_nsfw_channel(interaction: discord.Interaction):
    return interaction.channel.is_nsfw()


def extract_attributes(post_element):
    author = post_element.get("author")
    created_at = post_element.get("created_at")
    file_url = post_element.get("file_url")
    jpeg_url = post_element.get("jpeg_url")
    preview_url = post_element.get("preview_url")
    source = post_element.get("source")
    tags = post_element.get("tags")

    return {
        "author": author,
        "created_at": created_at,
        "file_url": file_url,
        "jpeg_url": jpeg_url,
        "preview_url": preview_url,
        "source": source,
        "tags": tags,
    }


def format_dt(dt: datetime.datetime, style: Optional[str] = None) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)

    if style is None:
        return f'<t:{int(dt.timestamp())}>'
    return f'<t:{int(dt.timestamp())}:{style}>'


def format_relative(dt: datetime.datetime) -> str:
    return format_dt(dt, 'R')


def parse_xml(xml_content):
    root = fromstring(xml_content)
    posts = root.findall(".//post")

    extracted_data = [extract_attributes(post) for post in posts]
    return extracted_data


def membed(descriptioner: str) -> discord.Embed:
    """Quickly create an embed with a custom description using the preset."""
    membedder = discord.Embed(colour=0x2F3136,
                           description=descriptioner)
    return membedder


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
        avatar = interaction.user.avatar or interaction.user.default_avatar
        embed.set_author(name=f"Submitted by {interaction.user.name}", icon_url=avatar.url)

        await channel.send(embed=embed)
        success = discord.Embed(colour=0x2F3136,
                                description=f"- Your response has been submitted.\n"
                                            f" - Developers will consider your feedback accordingly within a few days.\n"
                                            f" - From there, compensation will be decided upfront.\n\n"
                                            f"You may get a unique badge or other type of reward based on how "
                                            f"constructive and thoughtful your feedback is.")
        await interaction.response.send_message(embed=success, ephemeral=True) 

    async def on_error(self, interaction: discord.Interaction, error):
        return await interaction.response.send_message(f"we had trouble processing your feedback, try again later.") 


class InviteButton(discord.ui.View):
    def __init__(self, client: commands.Bot):
        super().__init__(timeout=60.0)
        self.client: commands.Bot = client

        perms = discord.Permissions.none()
        perms.read_messages = True
        perms.external_emojis = True
        perms.send_messages = True
        perms.manage_roles = True
        perms.manage_channels = True
        perms.ban_members = True
        perms.kick_members = True
        perms.manage_messages = True
        perms.embed_links = True
        perms.read_message_history = True
        perms.attach_files = True
        perms.add_reactions = True
        perms.voice()
        perms.create_instant_invite = True
        perms.manage_threads = True

        self.add_item(discord.ui.Button(
            label="Invite Link",
            url=discord.utils.oauth_url(self.client.user.id, permissions=perms)))


class Miscellaneous(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client
        self.process = Process()

    async def get_word_info(self, word):
        url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
        async with self.client.session.get(url) as response:  
            return await response.json()

    async def make_a_kona(self, limit=5, page=1, tags=""):
        """Returns a list of dictionaries for you to iterate through and fetch their attributes"""

        base_url = "https://konachan.net/post.xml"
        params = {"limit": limit, "page": page, "tags": tags}

        async with self.client.session.get(base_url, params=params) as response:  
            status = response.status
            if status == 200:
                posts_xml = await response.text()
                data = parse_xml(posts_xml)
            else:
                data = status
        return data

    @commands.command(name='invite', description='link to invite c2c to your server.')
    @commands.guild_only()
    async def invite_bot(self, ctx):
        await ctx.send(embed=membed("The button component gives a direct link to invite me to your server.\n"
                                    "Remember that only developers can invite the bot."), view=InviteButton(self.client))

    @commands.command(name='calculate', aliases=('c', 'calc'), description='compute a string / math expression.')
    @commands.guild_only()
    async def calculator(self, ctx: commands.Context, *, expression):
        try:
            result = eval(expression) or "Invalid"
            await ctx.reply(f'**{ctx.author.name}**, the answer is `{result}`', mention_author=False)
        except Exception as e:
            await ctx.reply(f'**Error:** {str(e)}', mention_author=False)

    @commands.command(name='ping', description='checks latency of the bot.')
    async def ping(self, ctx):
        start = perf_counter()
        message = await ctx.send("Ping...")
        end = perf_counter()
        duration = (end - start) * 1000
        await message.edit(content='REST: {0:.2f}ms **\U0000007c** '
                                   'WS: {1} ms'.format(duration, round(self.client.latency * 1000)))

    @app_commands.command(name='bored', description="find something to do.")
    @app_commands.guilds(Object(id=829053898333225010), Object(id=780397076273954886))
    @app_commands.describe(activity_type='the type of activity to think of')
    async def prompt_act(self, interaction: discord.Interaction,
                         activity_type: Optional[Literal["education", "recreational", "social", "diy", "charity",
                                                         "cooking", "relaxation", "music", "busywork"]]):
        if activity_type is None:
            activity_type = ""
        else:
            activity_type = f"?type={activity_type}"
        async with self.client.session.get( 
                f"http://www.boredapi.com/api/activity{activity_type}") as response:
            if response.status == 200:
                resp = await response.json()
                await interaction.response.send_message(f"{resp['activity']}.") 
            else:
                await interaction.response.send_message( 
                    embed=membed("An unsuccessful request was made. Try again later."))

    @app_commands.command(name='kona', description='fetch images from the konachan website.')
    @app_commands.guilds(Object(id=829053898333225010), Object(id=780397076273954886))
    @app_commands.check(was_called_in_a_nsfw_channel)
    @app_commands.describe(tags='the tags to base searches upon, seperated by a space', page='the page to look through under a tag')
    async def kona_fetch(self, interaction: discord.Interaction, tags: Optional[str], page: Optional[int]):

        if page is None:
            page = 1

        if tags is None:
            tags = "original"
        tagviewing = ', '.join(tags.split(' '))

        embed = discord.Embed(title='Results',
                              description=f'- Retrieval is based on the following filters:\n'
                                          f' - **Tags**: {tagviewing}\n'
                                          f' - **Page**: {page}\n\n',
                              colour=discord.Colour.from_rgb(255, 233, 220))

        avatar = interaction.user.avatar or interaction.user.default_avatar
        embed.set_author(icon_url=avatar.url, name=f'Requested by {interaction.user.name}',
                         url=avatar.url)

        posts_xml = await self.make_a_kona(limit=3, page=page, tags=tags)

        if isinstance(posts_xml, int):  # meaning it did not return a status code of 200: OK

            rmeaning = {
                403: "Forbidden - Access was denied",
                404: "Not Found",
                420: "Invalid Record - The record could not be saved",
                421: "User Throttled - User is throttled, try again later",
                422: "Locked - The resource is locked and cannot be modified",
                423: "Already Exists - The resource already exists",
                424: "Invalid Parameters - The given parameters were invalid",
                500: "Internal Server Error - Some unknown error occured on the konachan website's server",
                503: "Service Unavailable - The konachan website currently cannot handle the request"
            }

            return await interaction.response.send_message(  
                embed=membed(f"The [konachan website](https://konachan.net/help) returned an erroneous status code of "
                             f"`{posts_xml}`: {rmeaning.setdefault(posts_xml, "the cause of the error is not known")}."
                             f"\nYou should try again later to see if the service improves."))

        if len(posts_xml) == 0:
            return await interaction.response.send_message(  
                embed=membed(f"## No results found.\n"
                             f"- This is often due to entering an invalid tag name.\n"
                             f" - There are millions of tags that are available to base your search on. By default, "
                             f"if you don't input a tag, the search defaults to the tag with name `original`.\n"
                             f" - You can find a tag of your choice [on the website.](https://konachan.net/tag)"))

        attachments = set()
        descriptionerfyrd = set()
        for result in posts_xml:
            tindex = posts_xml.index(result)+1
            result['source'] = result['source'] or '*Unknown User*'
            descriptionerfyrd.add(f'**[{tindex}]** *Post by {result['author']}*\n'
                                  f'- Created <t:{result['created_at']}:R>\n'
                                  f'- [File URL (source)]({result['file_url']})\n'
                                  f'- [File URL (jpeg)]({result['jpeg_url']})\n'
                                  f'- Made by {result['source']}\n'
                                  f'- Tags: {result['tags']}')
            attachments.add(f"**[{tindex}]**\n{result['jpeg_url']}")

        embed.description += "\n\n".join(descriptionerfyrd)
        await interaction.channel.send(content=f"__Attachments for {interaction.user.mention}__\n\n" + "\n".join(attachments))
        await interaction.response.send_message(embed=embed) 


    @app_commands.command(name='emojis', description='fetch all the emojis c2c can access.')
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

    @app_commands.command(name='inviter', description='creates a server invite link.')
    @app_commands.guilds(Object(id=829053898333225010), Object(id=780397076273954886))
    @app_commands.checks.has_permissions(create_instant_invite=True)
    @app_commands.describe(invite_lifespan='the duration of which the invite should last, must be > 0.',
                           maximum_uses='how many uses the invite could be used for. 0 for unlimited uses.')
    async def gen_new_invite(self, interaction: discord.Interaction, invite_lifespan: int, maximum_uses: int):
        if invite_lifespan <= 0:
            return await interaction.response.send_message( 
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
        await interaction.response.send_message(embed=success) 

    @app_commands.command(name='define', description='define any word of choice.')
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
                            if "(" in thing[x]:
                                thing[x] += ")"
                            the_result.add_field(name=f'Definition {x + 1}', value=f'{thing[x]}')
                        if len(the_result.fields) == 0:
                            the_result.add_field(name=f'Looks like no results were found.',
                                                 value=f'We couldn\'t find a definition for {choicer.lower()}.')
                        await interaction.response.send_message(embed=the_result) 
                    else:
                        continue
        except AttributeError:
            await interaction.response.send_message(content=f'try again, but this time input an actual word.') 

    @app_commands.command(name='randomfact', description='generates a random fact.')
    @app_commands.guilds(Object(id=829053898333225010), Object(id=780397076273954886))
    @app_commands.checks.cooldown(1, 5, key=lambda i: i.user.id)
    async def random_fact(self, interaction: Interaction):
        limit = 1
        api_url = 'https://api.api-ninjas.com/v1/facts?limit={}'.format(limit)
        parameters = {'X-Api-Key': self.client.NINJAS_API_KEY} 
        async with self.client.session.get(api_url, params=parameters) as resp: 
            text = await resp.json()
            the_fact = text[0].get('fact')
            await interaction.response.send_message(f"{the_fact}.") 

    @app_commands.command(name='com', description='finds most common letters in sentences.')
    @app_commands.guilds(Object(id=829053898333225010), Object(id=780397076273954886))
    @app_commands.describe(word='the sentence(s) to find the frequent letters of')
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

        commons = []
        counter = 0
        for m in frequency:
            if n == m:
                commons.append(letters[counter])
            counter += 1

        commons.sort()
        answer = ''
        for letter in commons:
            answer = answer + letter + ' '

        answer = answer[:-1]

        await interaction.response.send_message(embed=membed(f'The most common letter is {answer}.')) 

    @app_commands.command(name='charinfo', description='show info on characters (max 25).')
    @app_commands.guilds(Object(id=829053898333225010), Object(id=780397076273954886))
    @app_commands.describe(characters='any written letters or symbols')
    async def charinfo(self, interaction: Interaction, *, characters: str):
        """Shows you information about a number of characters.
        Only up to 25 characters at a time.
        """

        def to_string(c):
            digit = f'{ord(c):x}'
            the_name = name(c, 'Name not found.')
            c = '\\`' if c == '`' else c
            return f'[`\\U{digit:>08}`](http://www.fileformat.info/info/unicode/char/{digit}): {the_name} **\N{EM DASH}** {c}'

        msg = '\n'.join(map(to_string, characters))
        if len(msg) > 2000:
            return await interaction.response.send_message('Output too long to display.')
        await interaction.response.send_message(msg, suppress_embeds=True)

    @commands.command(name='spotify', aliases=('sp', 'spot'), description="fetch spotify RP information.")
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

    @app_commands.command(name='feedback', description='send feedback to the c2c developers.')
    @app_commands.guilds(Object(id=829053898333225010), Object(id=780397076273954886))
    async def feedback(self, interaction: discord.Interaction):
        feedback_modal = FeedbackModal()
        await interaction.response.send_modal(feedback_modal) 

    @app_commands.command(name='about', description='shows stats related to the client.')
    @app_commands.guilds(Object(id=829053898333225010), Object(id=780397076273954886))
    @app_commands.checks.cooldown(1, 3, key=lambda i: i.user.id)
    async def about_the_bot(self, interaction: discord.Interaction):

        await interaction.response.defer(thinking=True) # type: ignore
        amount = 0
        lenslash = len(await self.client.tree.fetch_commands(guild=Object(id=interaction.guild.id)))+1
        lentxt = len(self.client.commands)
        amount += (lenslash+lentxt)

        username = 'SGA-A'
        token = 'youshallnotpass'
        repository_name = 'c2c'

        g = Github(username, token)

        repo = g.get_repo(f'{username}/{repository_name}')

        commits = repo.get_commits()[:3]
        revision = list()

        for commit in commits:
            revision.append(f"[`{commit.sha[:6]}`]({commit.url}) {commit.commit.message} {format_relative(commit.commit.author.date)}")

        embed = discord.Embed(description=f'Latest Changes:\n'
                                          f'{"\n".join(revision)}')
        embed.title = 'Official Bot Server Invite'
        embed.url = 'https://discord.gg/W3DKAbpJ5E'
        embed.colour = discord.Colour.blurple()

        geo = self.client.get_user(546086191414509599)
        embed.set_author(name=geo.name, icon_url=geo.display_avatar.url)

        total_members = 0
        total_unique = len(self.client.users)

        text = 0
        voice = 0
        guilds = 0

        for guild in self.client.guilds:
            guilds += 1
            if guild.unavailable:
                continue

            total_members += guild.member_count or 0
            for channel in guild.channels:
                if isinstance(channel, discord.TextChannel):
                    text += 1
                elif isinstance(channel, discord.VoiceChannel):
                    voice += 1

        memory_usage = self.process.memory_full_info().uss / 1024 ** 2
        cpu_usage = self.process.cpu_percent() / cpu_count()
        embed.timestamp = discord.utils.utcnow()

        diff = datetime.datetime.now() - self.client.time_launch  # type: ignore
        minutes, seconds = divmod(diff.total_seconds(), 60)
        hours, minutes = divmod(minutes, 60)
        days, hours = divmod(hours, 24)

        embed.add_field(name='Members', value=f'{total_members} total\n{total_unique} unique')
        embed.add_field(name='Channels', value=f'{text + voice} total\n{text} text\n{voice} voice')
        embed.add_field(name='Process', value=f'{memory_usage:.2f} MiB\n{cpu_usage:.2f}% CPU')
        embed.add_field(name='Guilds',
                        value=f'{len(self.client.guilds)}\n'
                              f'{ARROW}{guilds} channels\n'
                              f'{ARROW}{len(self.client.emojis)} emojis\n'
                              f'{ARROW}{len(self.client.stickers)} stickers')
        embed.add_field(name='Commands',
                        value=f'{amount} total\n'
                              f'{ARROW}{lentxt} (prefix)\n'
                              f'{ARROW}{lenslash} (slash)')
        embed.add_field(name='Uptime',
                        value=f"{int(days)}d {int(hours)}h "
                              f"{int(minutes)}m {int(seconds)}s")
        embed.set_footer(text=f'Made with discord.py v{discord.__version__}', icon_url='http://i.imgur.com/5BFecvA.png')
        await interaction.followup.send(embed=embed)

    @app_commands.command(name='char', description="retrieve sfw anime images.")
    @app_commands.guilds(Object(id=829053898333225010), Object(id=780397076273954886))
    @app_commands.describe(filter_by='what type of image ')
    async def get_via_nekos(self, interaction: discord.Interaction,
                            filter_by: Optional[Literal["neko", "kitsune", "waifu", "husbando"]]):

        if filter_by is None:
            filter_by = "neko"

        async with self.client.session.get(f"https://nekos.best/api/v2/{filter_by}") as resp: # type: ignore
            if resp.status != 200:
                return await interaction.response.send_message( # type: ignore
                    "The request failed, you should try again later.")
            data = await resp.json()
            await interaction.response.send_message(data["results"][0]["url"])  # type: ignore
    
    @app_commands.command(name='tn', description="get time now in a chosen format.")
    @app_commands.guilds(Object(id=829053898333225010), Object(id=780397076273954886))
    @app_commands.rename(spec="mode")
    @app_commands.describe(spec='the mode of displaying the current time now')
    async def tn(self, interaction: discord.Interaction, spec: Literal["t - returns short time (format HH:MM)",
                 "T - return long time (format HH:MM:SS)", "d - returns short date (format DD/MM/YYYY)",
                 "D - returns long date (format DD Month Year)", "F - returns long date and time (format Day, DD Month Year HH:MM)",
                 "R - returns the relative time since now"] = None) -> None:
        speca = spec[0] if spec else None
        format_dtime = discord.utils.format_dt(datetime.datetime.now(), style=speca)
        embed = discord.Embed(description=f'## Timestamp Conversion\n{format_dtime}\n'
                                          f'- The epoch time in this format is: `{format_dtime}`',
                              colour=return_random_color())
        if interaction.user.avatar: embed.set_thumbnail(url=interaction.user.avatar.url)
        await interaction.response.send_message(embed=embed, ephemeral=True) 

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
