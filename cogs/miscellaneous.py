from time import perf_counter
from PyDictionary import PyDictionary
import discord
from xml.etree.ElementTree import fromstring
from other.pagination import Pagination
from io import BytesIO
import datetime
from random import choice
from github import Github
from re import compile as compile_it
from psutil import Process, cpu_count
from time import time
from typing import Literal, Union, Optional
from discord.ext import commands
from other.spshit import get_song_attributes
from discord import app_commands, Interaction, Object
from unicodedata import name

ARROW = "<:arrowe:1180428600625877054>"
found_spotify = False
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


def was_called_in_a_nsfw_channel(interaction: discord.Interaction):
    return interaction.channel.is_nsfw()


def extract_attributes(post_element, mode: Literal["image", "tag"]):
    if mode == "image":
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

    tag_name = post_element.get("name")
    tag_type = post_element.get("type")

    return {
        "name": tag_name,
        "tag_type": tag_type
    }


def format_dt(dt: datetime.datetime, style: Optional[str] = None) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)

    if style is None:
        return f'<t:{int(dt.timestamp())}>'
    return f'<t:{int(dt.timestamp())}:{style}>'


def format_relative(dt: datetime.datetime) -> str:
    return format_dt(dt, 'R')


def parse_xml(xml_content, mode: Literal["image", "tag"]):
    if mode == "image":
        root = fromstring(xml_content)
        result = root.findall(".//post")
    else:
        root = fromstring(xml_content)
        result = root.findall(".//tag")

    extracted_data = [extract_attributes(res, mode=mode) for res in result]
    return extracted_data


def extract_domain(website):
    dp = compile_it(r'https://(nekos\.pro|nekos\.best)')
    match = dp.match(website)
    return match.group(1)


def membed(descriptioner: str) -> discord.Embed:
    """Quickly create an embed with a custom description using the preset."""
    membedder = discord.Embed(colour=0x2F3136, description=descriptioner)
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
        embed.set_author(name=interaction.user.name,
                         icon_url=interaction.user.display_avatar.url)

        await channel.send(embed=embed)
        success = discord.Embed(colour=0x2F3136,
                                description=f"## <:dispatche:1195745709463441429> Your response has been submitted.\n"
                                            f"- Developers will consider your feedback accordingly within a few days.\n"
                                            f"- From there, compensation will be decided upfront.\n\n"
                                            f"You may get a unique badge or other type of reward based on how "
                                            f"constructive and thoughtful your feedback is.")
        await interaction.response.send_message(embed=success, ephemeral=True)  # type: ignore

    async def on_error(self, interaction: discord.Interaction, error):
        return await interaction.response.send_message(  # type: ignore
            f"<:warning_nr:1195732155544911882> Something went wrong.")


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
        perms.manage_messages = True
        perms.manage_webhooks = True
        perms.embed_links = True
        perms.read_message_history = True
        perms.attach_files = True
        perms.add_reactions = True
        perms.voice()
        perms.create_instant_invite = True
        perms.manage_threads = True

        self.add_item(discord.ui.Button(
            label="Invite Link",
            emoji="<:addbote:1195744267872768100>",
            url=discord.utils.oauth_url(self.client.user.id, permissions=perms)))


class Miscellaneous(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client
        self.process = Process()
        self.ctx_menu = app_commands.ContextMenu(
            name='Extract Image Source',
            callback=self.extract_source)
        # self.ctx_menu.error(self.my_cool_context_menu_error)
        self.client.tree.add_command(self.ctx_menu)

    async def cog_check(self, ctx: commands.Context) -> bool:
        return ctx.guild is not None

    async def cog_unload(self) -> None:
        self.client.tree.remove_command(self.ctx_menu.name, type=self.ctx_menu.type)

    async def get_word_info(self, word):
        url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
        async with self.client.session.get(url) as response:  # type: ignore
            return await response.json()

    async def retrieve_via_kona(self, tag_pattern: Optional[str], tags: Optional[str],
                                limit=5, page=1, mode=Literal["image", "tag"]):
        """Returns a list of dictionaries for you to iterate through and fetch their attributes"""
        if mode == "image":
            base_url = "https://konachan.net/post.xml"
            params = {"limit": limit, "page": page, "tags": tags}
        else:
            base_url = "https://konachan.net/tag.xml"
            params = {"name": tag_pattern, "page": page, "order": "count", "limit": 20}

        async with self.client.session.get(base_url, params=params) as response:  # type: ignore
            if response.status == 200:
                posts_xml = await response.text()
                data = parse_xml(posts_xml, mode=mode)  # type: ignore
            else:
                data = response.status
        return data

    @commands.command(name='invite', description='link to invite c2c to your server.')
    async def invite_bot(self, ctx):
        await ctx.send(embed=membed("The button component gives a direct link to invite me to your server.\n"
                                    "Remember that only developers can invite the bot."),
                       view=InviteButton(self.client))

    @commands.command(name='calculate', aliases=('c', 'calc'), description='compute a string / math expression.')
    async def calculator(self, ctx: commands.Context, *, expression):

        try:
            result = eval(expression) or "Invalid"
            await ctx.reply(f'<:resultce:1195746711495249931> **{ctx.author.name}**, the result is `{result}`',
                            mention_author=False)
        except Exception as e:
            await ctx.reply(f'<:warning_nr:1195732155544911882> **Error:** {str(e)}', mention_author=False)

    @commands.command(name='ping', description='checks latency of the bot.')
    async def ping(self, ctx):
        start = perf_counter()
        message = await ctx.send("<:latencye:1195741921482641579> Ping...")
        end = perf_counter()
        duration = (end - start) * 1000
        await message.edit(content='<:latencye:1195741921482641579> REST: {0:.2f}ms **\U0000007c** '
                                   'WS: {1} ms'.format(duration, round(self.client.latency * 1000)))

    @app_commands.guilds(Object(id=829053898333225010), Object(id=780397076273954886))
    async def extract_source(self, interaction: discord.Interaction, message: discord.Message):

        await interaction.response.send_message("Looking into it..")
        msg = await interaction.original_response()
        images = set()
        counter = 0

        if message.embeds:
            for embed in message.embeds:
                if embed.image:
                    counter += 1
                    images.add(f"**{counter}**. [`{embed.image.height}x{embed.image.width}`]({embed.image.url})")
        for attr in message.attachments:
            counter += 1
            images.add(f"**{counter}**. [`{attr.height}x{attr.width}`]({attr.url})")

        if counter:
            embed = discord.Embed(title=f"Found {counter} images from {message.author.name}",
                                  description="\n".join(images),
                                  colour=0x2B2D31)
            return await msg.edit(content=None, embed=embed)
        await msg.edit(content="Could not find anything. Sorry.")

    @app_commands.command(name='bored', description="find something to do.")
    @app_commands.guilds(Object(id=829053898333225010), Object(id=780397076273954886))
    @app_commands.describe(activity_type='the type of activity to think of')
    async def prompt_act(self, interaction: discord.Interaction,
                         activity_type: Optional[Literal[
                             "education", "recreational", "social", "diy",
                             "charity", "cooking", "relaxation", "music", "busywork"]]):
        if activity_type is None:
            activity_type = ""
        else:
            activity_type = f"?type={activity_type}"
        async with self.client.session.get(  # type: ignore
                f"http://www.boredapi.com/api/activity{activity_type}") as response:
            if response.status == 200:
                resp = await response.json()
                await interaction.response.send_message(f"{resp['activity']}.")  # type: ignore
            else:
                await interaction.response.send_message(  # type: ignore
                    embed=membed("An unsuccessful request was made. Try again later."))

    @app_commands.command(name='kona', description='retrieve nsfw posts from konachan.', nsfw=True)
    @app_commands.guilds(Object(id=829053898333225010), Object(id=780397076273954886))
    @app_commands.describe(tags='the tags to base searches upon', page='the page to look through under a tag')
    async def kona_fetch(self, interaction: discord.Interaction, tags: Optional[str], page: Optional[int]):

        if tags is None:
            tags = "original"
        if page is None:
            page = 1

        tagviewing = ', '.join(tags.split(' '))

        posts_xml = await self.retrieve_via_kona(tags=tags, limit=3, page=page, mode="image",  # type: ignore
                                                 tag_pattern=None)

        if isinstance(posts_xml, int):
            return await interaction.response.send_message(  # type: ignore
                embed=membed(f"The [konachan website](https://konachan.net/help) returned an erroneous status code of "
                             f"`{posts_xml}`: {rmeaning.setdefault(posts_xml, "the cause of the error is not known")}."
                             f"\nYou should try again later to see if the service improves."))

        if len(posts_xml) == 0:
            await interaction.response.defer(thinking=True, ephemeral=True)  # type: ignore
            tagsearch = self.client.tree.get_app_command(  # type: ignore
                'tagsearch', guild=discord.Object(id=interaction.guild.id))

            """You can use the below code to make your commands mentionable, even if they are out of sync"""
            if tagsearch is None:
                await self.client.tree._update_cache(  # type: ignore
                    await self.client.tree.fetch_commands(
                        guild=discord.Object(id=interaction.guild.id)), guild=discord.Object(id=interaction.guild.id))
                tagsearch = self.client.tree.get_app_command(  # type: ignore
                    'tagsearch', guild=discord.Object(id=interaction.guild.id))

            return await interaction.followup.send(  # type: ignore
                embed=membed(f"## No posts found.\n"
                             f"- There are a few known causes:\n"
                             f" - Entering an invalid tag name.\n"
                             f" - Accessing some posts under the `copyright` tag.\n"
                             f" - There are no posts found under this tag.\n"
                             f" - The page requested exceeds the max length.\n"
                             f"- You can find a tag by using {tagsearch.mention} "
                             f"or [the website.](https://konachan.net/tag)"))

        attachments = set()
        descriptionerfyrd = set()
        for result in posts_xml:
            tindex = posts_xml.index(result) + 1
            descriptionerfyrd.add(f'**[{tindex}]** *Post by {result['author']}*\n'
                                  f'- Created <t:{result['created_at']}:R>\n'
                                  f'- [File URL (source)]({result['file_url']})\n'
                                  f'- [File URL (jpeg)]({result['jpeg_url']})\n'
                                  f'- Made by {result['source'] or '*Unknown User*'}\n'
                                  f'- Tags: {result['tags']}')
            attachments.add(f"**[{tindex}]**\n{result['jpeg_url']}")

        embed = discord.Embed(title='Results',
                              description=f'- Retrieval is based on the following filters:\n'
                                          f' - **Tags**: {tagviewing}\n'
                                          f' - **Page**: {page}\n\n',
                              colour=discord.Colour.from_rgb(255, 233, 220))

        embed.set_author(icon_url=interaction.user.display_avatar.url, name=interaction.user.name)
        embed.description += "\n\n".join(descriptionerfyrd)
        await interaction.channel.send(content=f"__Attachments "
                                               f"for {interaction.user.mention}__\n\n" + "\n".join(attachments),
                                       delete_after=30.0)
        await interaction.response.send_message(embed=embed)  # type: ignore

    @app_commands.command(name='tagsearch', description='retrieve tags from konachan.', nsfw=True)
    @app_commands.guilds(Object(id=829053898333225010), Object(id=780397076273954886))
    @app_commands.describe(tag_pattern="the pattern to use to find match results")
    async def tag_fetch(self, interaction: discord.Interaction, tag_pattern: str):

        embed = discord.Embed(title='Results', colour=discord.Colour.dark_embed())
        embed.set_author(icon_url=interaction.user.display_avatar.url, name=interaction.user.name,
                         url=interaction.user.display_avatar.url)

        tags_xml = await self.retrieve_via_kona(tag_pattern=tag_pattern, mode="tag", tags=None)  # type: ignore

        if isinstance(tags_xml, int):
            return await interaction.response.send_message(  # type: ignore
                embed=membed(f"The [konachan website](https://konachan.net/help) returned an erroneous status code of "
                             f"`{tags_xml}`: {rmeaning.setdefault(tags_xml, "the cause of the error is not known")}."
                             f"\nYou should try again later to see if the service improves."), ephemeral=True)

        if len(tags_xml) == 0:
            return await interaction.response.send_message(  # type: ignore
                embed=membed(f"## No tags found.\n"
                             f"- There is only one known cause:\n"
                             f" - No matching tags exist yet under the given tag pattern."), ephemeral=True)

        type_of_tag = {
            0: "`general`",
            1: "`artist`",
            2: "`N/A`",
            3: "`copyright`",
            4: "`character`"
        }

        descriptionerfyrd = set()
        pos = 0
        for result in tags_xml:
            descriptionerfyrd.add(f'{pos}. '
                                  f'{result['name']} '
                                  f'({type_of_tag.setdefault(int(result['tag_type']), "Unknown Tag Type")})')
        embed.set_footer(text="Some tags here don't have any posts.")
        embed.description = "\n".join(descriptionerfyrd)
        await interaction.response.send_message(embed=embed)  # type: ignore

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
                                description="> This is a command that fetches **all** of the emojis found"
                                            " in the client's internal cache and their associated atributes.\n",
                                colour=0x2F3136)
            emb.set_thumbnail(url=self.client.user.avatar.url)
            offset = (page - 1) * length
            for user in emotes_all[offset:offset + length]:
                emb.description += f"{user}\n"
            emb.set_author(name=interaction.user.name,
                           icon_url=interaction.user.display_avatar.url)
            n = Pagination.compute_total_pages(len(emotes_all), length)
            emb.set_footer(text=f"This is page {page} of {n}")
            return emb, n

        await Pagination(interaction, get_page_part).navigate()

    @commands.command(name='spsearch', description='search for songs on spotify.', aliases=('sps', 'ss'))
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
            song_emb.description = (f'## Search Results\n'
                                    f'> The **`popularity`** attribute may be difficult to understand. '
                                    f'Type the command [`>aboutpop`](https://www.google.com) to learn more '
                                    f'about this attribute.'
                                    f'{f'\n{boarder * 7}'.join(lisr)}')
            await ctx.send(embed=song_emb)

    @commands.command(name='aboutpop', description='explains how popularity is calculated.')
    async def about_pop_attr(self, ctx: commands.Context):
        async with ctx.typing():
            embed = membed(
                "# How track popularity really is calculated\n"
                "> If you have no idea what this is, learn more by calling [`>spsearch`](https://www.google.com)\n\n"
                "- The popularity of a track is a value between **`0`** and **`100`**, with "
                "**`100`** being the most popular.\n - The popularity is calculated by algorithm and is based, "
                "in the most part, on the total number of plays "
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
            return await interaction.response.send_message(  # type: ignore
                embed=membed("The invite lifespan cannot be **less than or equal to 0**."))

        maximum_uses = abs(maximum_uses)
        invite_lifespan *= 86400

        generated_invite = await interaction.channel.create_invite(
            reason=f'Creation requested by {interaction.user.name}',
            max_age=invite_lifespan, max_uses=maximum_uses)

        match maximum_uses:
            case 0:
                maxim_usage = "No limit to maximum usage"
            case _:
                maxim_usage = f"Max usages set to {generated_invite.max_uses}"
        formatted_expiry = discord.utils.format_dt(generated_invite.expires_at, 'R')
        success = discord.Embed(title='Successfully generated new invite link',
                                description=f'**A new invite link was created.**\n'
                                            f'- Invite channel set to {generated_invite.channel}\n'
                                            f'- {maxim_usage}\n'
                                            f'- Expires {formatted_expiry}\n'
                                            f'- Invite Link is: {generated_invite.url}',
                                colour=0x2F3136)
        success.set_author(name=interaction.user.name,
                           icon_url=interaction.user.display_avatar.url)
        await interaction.response.send_message(embed=success)  # type: ignore

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
                                                   description=f'<:dictionarye:1195748221994160220> This shows '
                                                               f'all the available definitions for the word {choicer}.',
                                                   colour=unique_colour)
                        for x in range(0, len(thing)):
                            if "(" in thing[x]:
                                thing[x] += ")"
                            the_result.add_field(name=f'Definition {x + 1}', value=f'{thing[x]}')
                        if len(the_result.fields) == 0:
                            the_result.add_field(name=f'Looks like no results were found.',
                                                 value=f'We couldn\'t find a definition for {choicer.lower()}.')
                        return await interaction.response.send_message(embed=the_result)  # type: ignore
                    else:
                        continue
        except AttributeError:
            await interaction.response.send_message(  # type: ignore
                content=f'try again, but this time input an actual word.')

    @app_commands.command(name='randomfact', description='generates a random fact.')
    @app_commands.guilds(Object(id=829053898333225010), Object(id=780397076273954886))
    @app_commands.checks.cooldown(1, 5, key=lambda i: i.user.id)
    async def random_fact(self, interaction: Interaction):
        limit = 1
        api_url = 'https://api.api-ninjas.com/v1/facts?limit={}'.format(limit)
        parameters = {'X-Api-Key': self.client.NINJAS_API_KEY}  # type: ignore
        async with self.client.session.get(api_url, params=parameters) as resp:  # type: ignore
            text = await resp.json()
            the_fact = text[0].get('fact')
            await interaction.response.send_message(f"{the_fact}.")  # type: ignore

    @app_commands.command(name="image", description="manipulate a user's avatar.")
    @app_commands.describe(user="the user to apply the manipulation to",
                           endpoint="what kind of manipulation sorcery to use")
    @app_commands.guilds(Object(id=829053898333225010), Object(id=780397076273954886))
    async def image_manip(self, interaction: discord.Interaction,
                          user: Optional[discord.User],
                          endpoint: Optional[
                              Literal[
                                  "abstract", "balls", "billboard", "bonks", "bubble", "canny", "clock",
                                  "cloth", "contour", "cow", "cube", "dilate", "fall", "fan", "flush", "gallery",
                                  "globe", "half-invert", "hearts", "infinity", "laundry", "lsd", "optics", "parapazzi"
                              ]]):
        start = time()
        await interaction.response.send_message("Loading..")  # type: ignore
        msg = await interaction.original_response()
        user = user or interaction.user
        endpoint = endpoint or "abstract"

        params = {'image_url': user.display_avatar.url}
        headers = {'Authorization': f'Bearer {self.client.JEYY_API_KEY}'}  # type: ignore
        api_url = f"https://api.jeyy.xyz/v2/image/{endpoint}"

        async with self.client.session.get(api_url, params=params, headers=headers) as response:  # type: ignore
            if response.status == 200:
                buffer = BytesIO(await response.read())
                end = time()
                diff = round(end - start, ndigits=2)
                return await msg.edit(content=f"Done. Took `{diff}s`.",
                                      attachments=[discord.File(buffer, f'{endpoint}.gif')])
            await msg.edit(content="The API we are using could not handle your request right now. Try again later.")

    @app_commands.command(name="image2", description="manipulate a user's avatar (continued).")
    @app_commands.describe(user="the user to apply the manipulation to",
                           endpoint="what kind of manipulation sorcery to use")
    @app_commands.guilds(Object(id=829053898333225010), Object(id=780397076273954886))
    async def image2_manip(self, interaction: discord.Interaction,
                           user: Optional[discord.User],
                           endpoint: Optional[
                              Literal[
                                  "minecraft", "patpat", "plates", "pyramid", "radiate", "rain", "ripped", "ripple",
                                  "shred", "wiggle", "warp", "wave"]]):
        start = time()
        await interaction.response.send_message("Loading..")  # type: ignore
        msg = await interaction.original_response()
        user = user or interaction.user
        endpoint = endpoint or "wave"

        params = {'image_url': user.display_avatar.url}
        headers = {'Authorization': f'Bearer {self.client.JEYY_API_KEY}'}  # type: ignore
        api_url = f"https://api.jeyy.xyz/v2/image/{endpoint}"

        async with self.client.session.get(api_url, params=params, headers=headers) as response:  # type: ignore
            if response.status == 200:
                buffer = BytesIO(await response.read())
                end = time()
                diff = round(end - start, ndigits=2)
                return await msg.edit(content=f"Done. Took `{diff}s`.",
                                      attachments=[discord.File(buffer, f'{endpoint}.gif')])
            await msg.edit(content="The API we are using could not handle your request right now. Try again later.")

    @app_commands.command(name="locket", description="insert photos into a heart-shaped locket.")
    @app_commands.describe(user="the user to add to the locket", user2="the second user to add to the locket")
    @app_commands.guilds(Object(id=829053898333225010), Object(id=780397076273954886))
    async def locket_manip(self, interaction: discord.Interaction,
                           user: Optional[discord.User], user2: discord.User):
        start = time()

        await interaction.response.send_message("Loading..")  # type: ignore
        msg = await interaction.original_response()

        user = user or interaction.user

        params = {'image_url': user.display_avatar.url, 'image_url_2': user2.display_avatar.url}
        headers = {'Authorization': f'Bearer {self.client.JEYY_API_KEY}'}  # type: ignore
        api_url = f"https://api.jeyy.xyz/v2/image/heart_locket"

        async with self.client.session.get(api_url, params=params, headers=headers) as response:  # type: ignore
            if response.status == 200:
                buffer = BytesIO(await response.read())
                end = time()
                diff = round(end - start, ndigits=2)
                return await msg.edit(content=f"Done. Took `{diff}s`.",
                                      attachments=[discord.File(buffer, f'heart_locket.gif')])
            await msg.edit(content="The API we are using could not handle your request right now. Try again later.")

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

        await interaction.response.send_message(embed=membed(f'The most common letter is {answer}.'))  # type: ignore

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
            return (f'[`\\U{digit:>08}`](http://www.fileformat.info/info/unicode/char/{digit}): {the_name} '
                    f'**\N{EM DASH}** {c}')

        msg = '\n'.join(map(to_string, characters))
        if len(msg) > 2000:
            return await interaction.response.send_message('Output too long to display.')  # type: ignore
        await interaction.response.send_message(msg, suppress_embeds=True)  # type: ignore

    @commands.command(name='spotify', aliases=('sp', 'spot'), description="fetch spotify RP information.")
    async def find_spotify_activity(self, ctx: commands.Context, *,
                                    username: Union[discord.Member, discord.User] = None):
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
                            title=f"{username.name}'s on Spotify <:spotifya:1195655823834230875>",
                            description=f"Listening to {activity.title}",
                            color=activity.colour)
                        embed.set_thumbnail(url=activity.album_cover_url)
                        embed.set_author(name=username.name, icon_url=username.display_avatar.url)
                        embed.add_field(name="Artist", value=activity.artist)
                        embed.add_field(name="Album", value=activity.album)
                        embed.add_field(name="Song Duration", value=str(activity.duration)[3:7])
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
        await interaction.response.send_modal(feedback_modal)  # type: ignore

    @app_commands.command(name='about', description='shows stats related to the client.')
    @app_commands.guilds(Object(id=829053898333225010), Object(id=780397076273954886))
    @app_commands.checks.cooldown(1, 10, key=lambda i: i.guild.id)
    async def about_the_bot(self, interaction: discord.Interaction):

        await interaction.response.defer(thinking=True)  # type: ignore
        amount = 0
        lenslash = len(await self.client.tree.fetch_commands(guild=Object(id=interaction.guild.id))) + 1
        lentxt = len(self.client.commands)
        amount += (lenslash + lentxt)

        username = 'SGA-A'
        token = self.client.gitoken  # type: ignore
        repository_name = 'c2c'

        g = Github(username, token)

        repo = g.get_repo(f'{username}/{repository_name}')

        commits = repo.get_commits()[:3]
        revision = list()

        for commit in commits:
            revision.append(
                f"[`{commit.sha[:6]}`]({commit.html_url}) {commit.commit.message.splitlines()[0]} "
                f"({format_relative(commit.commit.author.date)})")

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

        embed.add_field(name='<:membersb:1195752573555183666> Members',
                        value=f'{total_members} total\n{total_unique} unique')
        embed.add_field(name='<:channelb:1195752572116541590> Channels',
                        value=f'{text + voice} total\n{text} text\n{voice} voice')
        embed.add_field(name='<:processb:1195752570069713047> Process',
                        value=f'{memory_usage:.2f} MiB\n{cpu_usage:.2f}% CPU')
        embed.add_field(name='<:serversb:1195752568303927377> Guilds',
                        value=f'{guilds} total\n'
                              f'{ARROW}{len(self.client.emojis)} emojis\n'
                              f'{ARROW}{len(self.client.stickers)} stickers')
        embed.add_field(name='<:cmdsb:1195752574821879872> Commands',
                        value=f'{amount} total\n'
                              f'{ARROW}{lentxt} (prefix)\n'
                              f'{ARROW}{lenslash} (slash)')
        embed.add_field(name='<:uptimeb:1195752565208522812> Uptime',
                        value=f"{int(days)}d {int(hours)}h "
                              f"{int(minutes)}m {int(seconds)}s")
        embed.set_footer(text=f'Made with discord.py v{discord.__version__}', icon_url='http://i.imgur.com/5BFecvA.png')
        await interaction.followup.send(embed=embed)

    @app_commands.command(name='char', description="retrieve sfw or nsfw anime images.")
    @app_commands.guilds(Object(id=829053898333225010), Object(id=780397076273954886))
    @app_commands.describe(filter_by='what type of image to retrieve')
    async def get_via_nekos(self, interaction: discord.Interaction,
                            filter_by: Optional[
                                Literal[
                                    "neko", "kitsune", "waifu", "husbando", "ai", "ass", "boobs", "creampie",
                                    "paizuri", "pussy", "random", "ecchi", "fucking"]]):

        await interaction.response.send_message("Loading..")  # type: ignore
        msg = await interaction.original_response()

        api_urls = {
            "neko": ("https://nekos.best/api/v2/neko", 'https://nekos.pro/api/neko'),
            "kitsune": ("https://nekos.best/api/v2/kitsune",),
            "waifu": ("https://nekos.best/api/v2/waifu",),
            "husbando": ("https://nekos.best/api/v2/husbando",),
            "ai": "https://nekos.pro/api/ai",
            "ass": "https://nekos.pro/api/ass",
            "boobs": "https://nekos.pro/api/boobs",
            "creampie": "https://nekos.pro/api/creampie",
            "paizuri": "https://nekos.pro/api/paizuri",
            "pussy": "https://nekos.pro/api/pussy",
            "random": "https://nekos.pro/api/random",
            "ecchi": "https://nekos.pro/api/ecchi",
            "fucking": "https://nekos.pro/api/fucking"
        }

        if filter_by is None:
            filter_by = "neko"
        api_urls = api_urls.get(filter_by)

        if (isinstance(api_urls, str)) and (not interaction.channel.is_nsfw()):
            return await msg.edit(
                content=None,
                embed=membed("This API endpoint **must** be used within an NSFW channel."))
        elif isinstance(api_urls, tuple):
            api_urls = choice(api_urls)
        else:
            pass

        async with self.client.session.get(api_urls) as resp:  # type: ignore
            if resp.status != 200:
                return await msg.edit(
                    content=None, embed=membed("The request failed, you should try again later."))
            embed = discord.Embed(colour=discord.Colour.from_rgb(243, 157, 30))

            data = await resp.json()
            if (extract_domain(api_urls) == "nekos.pro") and (not api_urls.endswith("ai")):  # ai doesnt have any params
                embed.set_author(name=f"{data.setdefault('character_name', 'Unknown Source')}")
                embed.set_image(url=data["url"])
                embed.set_footer(text=f"ID: {data['id']}")
            elif extract_domain(api_urls) == "nekos.best":
                fm = data["results"][0]
                embed.set_author(name=f"{fm['artist_name']}")
                embed.set_image(url=fm["url"])
            else:
                embed.set_image(url=data["url"])
                embed.set_footer(text=f"ID: {data['id']}")

            await msg.edit(content=None, embed=embed)

    @commands.command(name="pickupline", description="get pick up lines to use.", aliases=('pul',))
    @commands.guild_only()
    async def pick_up_lines(self, ctx: commands.Context):
        async with ctx.typing():
            async with self.client.session.get(f"https://api.popcat.xyz/pickuplines") as resp:  # type: ignore
                if resp.status != 200:
                    return await ctx.send("The request failed, you should try again later.")
                data = await resp.json()
                await ctx.reply(data["pickupline"])  # type: ignore

    @commands.command(name="wyr", description="get 'would you rather' questions.")
    @commands.guild_only()
    async def would_yr(self, ctx: commands.Context):
        async with ctx.typing():
            async with self.client.session.get(f"https://api.popcat.xyz/wyr") as resp:  # type: ignore
                if resp.status != 200:
                    return await ctx.send("The request failed, you should try again later.")
                data = await resp.json()
                await ctx.reply(f'Would you rather:\n'
                                f'1. {data["ops1"].capitalize()} or..\n'
                                f'2. {data["ops2"].capitalize()}')

    @commands.command(name="alert", description="real incoming iphone alerts.")
    @commands.guild_only()
    async def alert_iph(self, ctx: commands.Context, *, custom_text: str):
        async with ctx.typing():
            custom_text = '+'.join(custom_text.split(' '))
            async with self.client.session.get(  # type: ignore
                    f"https://api.popcat.xyz/alert?text={custom_text}") as resp:
                if resp.status != 200:
                    return await ctx.send("The service is currently not available, try again later.")
                await ctx.send(resp.url)

    @app_commands.command(name='tn', description="get time now in a chosen format.")
    @app_commands.guilds(Object(id=829053898333225010), Object(id=780397076273954886))
    @app_commands.rename(spec="mode")
    @app_commands.describe(spec='the mode of displaying the current time now')
    async def tn(self, interaction: discord.Interaction, spec: Optional[
        Literal["t - returns short time (format HH:MM)", "T - return long time (format HH:MM:SS)",
                "d - returns short date (format DD/MM/YYYY)",
                "D - returns long date (format DD Month Year)",
                "F - returns long date and time (format Day, DD Month Year HH:MM)",
                "R - returns the relative time since now"]]) -> None:

        speca = spec[0] if spec else None
        format_dtime = discord.utils.format_dt(datetime.datetime.now(), style=speca)
        embed = discord.Embed(description=f'## <:watchb:1195754643209334906> Timestamp Conversion\n{format_dtime}\n'
                                          f'- The epoch time in this format is: `{format_dtime}`',
                              colour=return_random_color())
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        await interaction.response.send_message(embed=embed, ephemeral=True)  # type: ignore

    @commands.command(name='avatar', description='display a user\'s enlarged avatar.')
    async def avatar(self, ctx, *, username: Union[discord.Member, discord.User] = None):
        """Shows a user's enlarged avatar (if possible)."""
        embed = discord.Embed(colour=0x2F3136)
        username = username or ctx.author
        avatar = username.display_avatar.with_static_format('png')
        embed.set_author(name=username.name, url=avatar)
        embed.set_image(url=avatar)
        await ctx.send(embed=embed)


async def setup(client):
    await client.add_cog(Miscellaneous(client))
