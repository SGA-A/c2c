from io import BytesIO
from unicodedata import name
from time import perf_counter
from datetime import datetime, timezone
from typing import Callable, Literal
from xml.etree.ElementTree import fromstring

import discord
from pytz import timezone as pytz_timezone
from discord.ext import commands
from discord import app_commands
from psutil import Process, cpu_count

from cogs.economy import total_commands_used_by_user, USER_ENTRY
from .core.helpers import membed, number_to_ordinal
from .core.paginator import Pagination, RefreshPagination
from .core.constants import LIMITED_CONTEXTS, LIMITED_INSTALLS

ARROW = "<:Arrow:1263919893762543717>"
API_EXCEPTION = "The API fucked up, try again later."
UPLOAD_FILE_DESCRIPTION = "A file to upload alongside the thread."
EMBED_TIMEZONES = {
    'Pacific': 'US/Pacific',
    'Mountain': 'US/Mountain',
    'Central': 'US/Central',
    'Eastern': 'US/Eastern',
    'Britain': 'Europe/London',
    'Sydney': 'Australia/Sydney',
    'Japan': 'Asia/Tokyo',
    'Germany': 'Europe/Berlin',
    'India': 'Asia/Kolkata'
}


def extract_attributes(post_element, mode: Literal["post", "tag"]) -> dict | str:
    if mode == "post":
        keys_to_extract = {"created_at", "jpeg_url", "author"}
        data = {key: post_element.get(key) for key in keys_to_extract}
    else:
        data = post_element.get("name")

    del post_element
    return data


def format_dt(dt: datetime, style: str | None = None) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    if style is None:
        return f'<t:{int(dt.timestamp())}>'
    return f'<t:{int(dt.timestamp())}:{style}>'


def format_relative(dt: datetime) -> str:
    return format_dt(dt, 'R')


def parse_xml(xml_content, mode: Literal["post", "tag"]):
    result = fromstring(xml_content).findall(f".//{mode}")

    extracted_data = [extract_attributes(res, mode=mode) for res in result]
    return extracted_data


class ImageSourceButton(discord.ui.Button):
    def __init__(self, url: str = "https://www.google.com") -> None:
        super().__init__(url=url, label="Source", row=1)


class CommandUsage(RefreshPagination):
    length = 12
    def __init__(
        self, 
        interaction: discord.Interaction, 
        viewing: discord.Member | discord.User,
        get_page: Callable | None = None,
    ) -> None:
        super().__init__(interaction, get_page)
        self.viewing = viewing
        self.usage_embed = discord.Embed(title=f"{viewing.display_name}'s Command Usage", colour=0x2B2D31)
        self.usage_data = []  # commands list
        self.children[-1].default_values = [discord.Object(id=self.viewing.id)]

    async def fetch_data(self):
        async with self.interaction.client.pool.acquire() as conn:
            self.usage_data = await conn.fetchall(
                """
                SELECT cmd_name, cmd_count
                FROM command_uses
                WHERE userID = $0
                ORDER BY cmd_count DESC
                """, self.viewing.id
            )
            if not self.usage_data:
                self.usage_embed.description = (
                    "This user has never used any bot commands before.\n"
                    "Or, they have not used the bot since the rewrite (<t:1712935339:R>)."
                )
                self.total = 0
                return

            self.total = await total_commands_used_by_user(self.viewing.id, conn)

    @discord.ui.select(cls=discord.ui.UserSelect, placeholder="Select a registered user", row=0)
    async def user_select(self, interaction: discord.Interaction, select: discord.ui.UserSelect):
        self.viewing = select.values[0]
        self.index = 1
        select.default_values = [discord.Object(id=self.viewing.id)]

        await self.fetch_data()
        self.usage_embed.title = f"{self.viewing.display_name}'s Command Usage"

        await self.edit_page(interaction)


class Utility(commands.Cog):
    """Helpful commands to ease the experience on Discord, available for everyone."""
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.process = Process()

        self.cog_context_menus = {
            app_commands.ContextMenu(
                name='Extract Image Source',
                callback=self.extract_source,
                allowed_contexts=app_commands.AppCommandContext(guild=True, private_channel=True),
                allowed_installs=app_commands.AppInstallationType(guild=True, user=True)
            ),
            app_commands.ContextMenu(
                name='Extract Embed Colour',
                callback=self.embed_colour,
                allowed_contexts=app_commands.AppCommandContext(guild=True, private_channel=True),
                allowed_installs=app_commands.AppInstallationType(guild=True, user=True)
            ),
            app_commands.ContextMenu(
                name="View User Avatar",
                callback=self.view_avatar,
                allowed_contexts=app_commands.AppCommandContext(guild=True, private_channel=True),
                allowed_installs=app_commands.AppInstallationType(guild=True, user=True)
            ),
            app_commands.ContextMenu(
                name="View User Banner",
                callback=self.view_banner,
                allowed_contexts=app_commands.AppCommandContext(guild=True, private_channel=True),
                allowed_installs=app_commands.AppInstallationType(guild=True, user=True)
            )
        }

        for context_menu in self.cog_context_menus:
            self.bot.tree.add_command(context_menu)

    async def cog_unload(self) -> None:
        for context_menu in self.cog_context_menus:
            self.bot.tree.remove_command(context_menu)

    async def fetch_commits(self):
        async with self.bot.session.get(
            url="https://api.github.com/repos/SGA-A/c2c/commits",
            headers={"Authorization": f"token {self.bot.GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
        ) as response:
            if response.status == 200:
                commits = await response.json()
                return commits[:3]
            return []

    async def tag_search_autocomplete(self, _: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        tags_xml = await self.retrieve_via_kona(
            name=current.lower(), 
            mode="tag",
            page=1,
            order="count",
            limit=25
        )

        if isinstance(tags_xml, int):  # http exception
            return []

        return [
            app_commands.Choice(name=tag_name, value=tag_name)
            for tag_name in tags_xml if current.lower() in tag_name.lower()
        ]

    async def retrieve_via_kona(self, **params) -> int | str:
        """Returns a list of dictionaries for you to iterate through and fetch their attributes"""
        mode = params.pop("mode")
        base_url = f"https://konachan.net/{mode}.xml"

        async with self.bot.session.get(base_url, params=params) as response:
            if response.status != 200:
                return response.status

            posts_xml = await response.text()
        return parse_xml(posts_xml, mode=mode)

    async def format_gif_api_response(
        self, 
        interaction: discord.Interaction, 
        start: float, 
        api_url: str, 
        **attrs
    ) -> None | discord.WebhookMessage:
        
        async with self.bot.session.get(api_url, **attrs) as response:
            if response.status != 200:
                return await interaction.followup.send(embed=membed(API_EXCEPTION))
            buffer = BytesIO(await response.read())
        end = perf_counter()
        await interaction.followup.send(f"Took ~{end-start:.2f} seconds", file=discord.File(buffer, 'clip.gif'))
        await interaction.followup.send(f"Took ~{end-start:.2f} seconds", file=discord.File(buffer, 'clip.gif'))

    @app_commands.command(name='serverinfo', description="Show information about the server and its members")
    @app_commands.guild_install()
    @app_commands.allowed_contexts(**LIMITED_CONTEXTS)
    async def display_server_info(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(thinking=True)

        guild = interaction.guild
        total_bots = 0

        for member in guild.members:
            if not member.bot:
                continue
            total_bots += 1

        tn_full, tn_relative = (
            discord.utils.format_dt(guild.created_at), 
            discord.utils.format_dt(guild.created_at, style="R")
        )

        serverinfo = discord.Embed(title=guild.name, colour=guild.me.color)
        serverinfo.description = (
            f"\U00002726 Owner: {guild.owner.name}\n"
            f"\U00002726 Maximum File Size: {guild.filesize_limit / 1_000_000}MB\n"
            f"\U00002726 Role Count: {len(guild.roles)-1}\n"
        )
        serverinfo.set_thumbnail(url=guild.icon.url)
        serverinfo.add_field(
            name="Created",
            value=f"{tn_full} ({tn_relative})",
        )

        if guild.description:
            serverinfo.add_field(
                name="Server Description",
                value=guild.description,
                inline=False
            )

        animated_emojis = sum(1 for emoji in guild.emojis if emoji.animated)

        serverinfo.add_field(
            name="Member Info",
            value=(
                f"\U00002023 Humans: {guild.member_count-total_bots:,}\n"
                f"\U00002023 Bots: {total_bots:,}\n"
                f"\U00002023 Total: {guild.member_count:,}\n"
            )
        ).add_field(
            name="Channel Info",
            value=(
                f"\U00002023 <:categoryCh:1263920042056089680> {len(guild.categories)}\n"
                f"\U00002023 <:textChannel:1263923690056319137> {len(guild.text_channels)}\n"
                f"\U00002023 <:voiceChannel:1263924105967566968> {len(guild.voice_channels)}"
            )
        ).add_field(
            name="Emojis",
            value=(
                f"\U00002023 Static: {len(guild.emojis)-animated_emojis}/{guild.emoji_limit}\n"
                f"\U00002023 Animated: {animated_emojis}/{guild.emoji_limit}"
            )
        )

        await interaction.followup.send(embed=serverinfo)

    @app_commands.describe(user="Whose command usage to display. Defaults to you.")
    @app_commands.command(name="usage", description="See your total command usage")
    @app_commands.allowed_installs(**LIMITED_INSTALLS)
    @app_commands.allowed_contexts(**LIMITED_CONTEXTS)
    async def view_user_usage(self, interaction: discord.Interaction, user: USER_ENTRY | None = None):
        user = user or interaction.user

        paginator = CommandUsage(interaction, viewing=user)
        await paginator.fetch_data()

        async def get_page_part(force_refresh: bool = None) -> discord.Embed:
            if force_refresh:
                await paginator.fetch_data()

            paginator.reset_index(paginator.usage_data)
            if not paginator.usage_data:
                paginator.usage_embed.set_footer(text="Empty")
                return paginator.usage_embed

            offset = (paginator.index - 1) * paginator.length
            paginator.usage_embed.description = f"> Total: {paginator.total:,}\n\n"
            paginator.usage_embed.description += "\n".join(
                f"` {cmd_data[1]:,} ` \U00002014 {cmd_data[0]}"
                for cmd_data in paginator.usage_data[offset:offset + paginator.length]
            )
            paginator.usage_embed.set_footer(text=f"Page {paginator.index} of {paginator.total_pages}")
            return paginator.usage_embed

        paginator.get_page = get_page_part
        await paginator.navigate()

    @app_commands.command(name='calc', description='Calculate an expression')
    @app_commands.describe(expression='The expression to evaluate.')
    @app_commands.allowed_installs(**LIMITED_INSTALLS)
    @app_commands.allowed_contexts(**LIMITED_CONTEXTS)
    async def calculator(self, interaction: discord.Interaction, expression: str) -> None:
        try:
            expression = expression.replace('^', '**').replace(',', '_')

            # Evaluate the expression
            result = eval(expression)

            # Format the result with commas for thousands separator
            result = f"{result:,}" if isinstance(result, (int, float)) else "Invalid Equation"
        except Exception:
            result = "Invalid Equation"

        output = membed(
            f"""
            \U0001f4e5 **Input:**
            ```py\n{expression}```
            \U0001f4e4 **Output:**
            ```\n{result}```
            """
        )

        await interaction.response.send_message(embed=output)

    @commands.command(name='ping', description='Checks latency of the bot')
    async def ping(self, ctx: commands.Context) -> None:
        msg_content = "Pong!"
        msg = await ctx.send(msg_content)
        msg_content += f" `{self.bot.latency * 1000:.0f}ms`"
        await msg.edit(content=msg_content)

    async def extract_source(
        self, 
        interaction: discord.Interaction, 
        message: discord.Message
    ) -> None:

        images = set()
        counter = 0

        if message.embeds:
            for embed in message.embeds:
                for asset in (embed.image, embed.thumbnail):
                    if not asset:
                        continue
                    images.add(f"**{counter}**. [`{embed.image.height}x{embed.image.width}`]({embed.image.url})")
        
        for attr in message.attachments:
            images.add(f"**{counter}**. [`{attr.height}x{attr.width}`]({attr.url})")

        embed = membed()
        if not counter:
            embed.description = "Could not find any attachments."
            return await interaction.response.send_message(embed=embed, ephemeral=True)
        
        embed.title = f"Found {counter} images from {message.author.name}"
        embed.description="\n".join(images)
        embed.set_thumbnail(url=message.author.display_avatar.url)
        
        await interaction.response.send_message(ephemeral=True, embed=embed)

    async def embed_colour(self, interaction: discord.Interaction, message: discord.Message) -> None:

        all_embeds = [
            discord.Embed(
                colour=embed.colour, 
                description=f"{embed.colour} - [`{embed.colour.value}`](https:/www.google.com)"
            ) for embed in message.embeds
        ]

        if all_embeds:
            return await interaction.response.send_message(ephemeral=True, embeds=all_embeds)

        await interaction.response.send_message(
            ephemeral=True, 
            embed=membed("No embeds were found within this message.")
        )

    anime = app_commands.Group(
        name='anime', 
        description="Surf through anime images and posts.", 
        nsfw=False,
        allowed_contexts=app_commands.AppCommandContext(guild=True, private_channel=True),
        allowed_installs=app_commands.AppInstallationType(guild=True, user=True)
    )

    @anime.command(name='kona', description='Retrieve NSFW posts from Konachan')
    @app_commands.rename(length="max_images")
    @app_commands.describe(
        tag1='A tag to base your search on.', 
        tag2='A tag to base your search on.',
        tag3='A tag to base your search on.' ,
        private='Hide the results from others. Defaults to True.',
        length='The maximum number of images to display at once. Defaults to 3.',
        maximum='The maximum number of images to retrieve. Defaults to 30.',
        page='The page number to look through.'
    )
    @app_commands.autocomplete(
        tag1=tag_search_autocomplete, 
        tag2=tag_search_autocomplete, 
        tag3=tag_search_autocomplete
    )
    async def kona_fetch(
        self, 
        interaction: discord.Interaction, 
        tag1: str, 
        tag2: str = None,
        tag3: str = None,
        private: bool = True,
        length: app_commands.Range[int, 1, 10] = 3,
        maximum: app_commands.Range[int, 1, 9999] = 30,
        page: app_commands.Range[int, 1] = 1
    ) -> None:

        tags = filter(lambda x: isinstance(x[1], str), iter(interaction.namespace))
        tagviewing = ' '.join(val for _, val in tags)

        posts_xml = await self.retrieve_via_kona(
            tags=tagviewing, 
            limit=maximum, 
            page=page, 
            mode="post"
        )

        if isinstance(posts_xml, int):
            embed = membed("Failed to make this request.")
            embed.title = f"{posts_xml}. That's an error."
            return await interaction.response.send_message(embed=embed)

        if not len(posts_xml):
            embed = membed(
                "- There are a few known causes:\n"
                " - Entering an invalid tag name.\n"
                " - Accessing some posts under the `copyright` tag.\n"
                " - There are no posts found under this tag.\n"
                " - The page requested exceeds the max length.\n"
                "- You can find a tag by using [the website.](https://konachan.net/tag)"
            )
            embed.title = "No posts found."
            return await interaction.response.send_message(ephemeral=True, embed=embed)

        additional_notes = [
            (
                f"{result['jpeg_url']}",
                f"{result['author']}",
                result['created_at']
            )
            for result in posts_xml
        ]

        async def get_page_part(page: int):
            embeds = []

            offset = (page - 1) * length

            for (jpeg_url, author, created_at) in additional_notes[offset:offset + length]:
                embed = membed().set_image(url=jpeg_url)
                embed.title, embed.url = author, jpeg_url
                embed.timestamp = datetime.fromtimestamp(int(created_at), tz=timezone.utc)
                embeds.append(embed)

            n = Pagination.compute_total_pages(len(additional_notes), length)
            return embeds, n

        await Pagination(interaction, get_page=get_page_part).navigate(ephemeral=private)

    @anime.command(name='char', description="Retrieve SFW or NSFW anime images")
    @app_commands.describe(filter_by='The type of image to retrieve.')
    async def get_via_nekos(
        self, 
        interaction: discord.Interaction, 
        filter_by: Literal["neko", "kitsune", "waifu", "husbando"] = "neko"
    ) -> None:

        async with self.bot.session.get(f"https://nekos.best/api/v2/{filter_by}") as resp:
            if resp.status != 200:
                return await interaction.response.send_message(embed=membed(API_EXCEPTION))
            data = await resp.json()

        data = data["results"][0]
        embed = discord.Embed(colour=0xFF9D2C)
        embed.set_image(url=data["url"]).set_author(name=f"{data["artist_name"]}")

        img_view = discord.ui.View().add_item(ImageSourceButton(url=data["url"]))
        await interaction.response.send_message(embed=embed, view=img_view)

    @app_commands.command(name='emojis', description='Fetch all the emojis c2c can access')
    @app_commands.allowed_contexts(**LIMITED_CONTEXTS)
    @app_commands.allowed_installs(**LIMITED_INSTALLS)
    async def emojis_paginator(self, interaction: discord.Interaction) -> None:
        length = 8
        emb = membed()
        emb.title = "Emojis"

        async def get_page_part(page: int):
            offset = (page - 1) * length

            emb.description = "\n".join(
                f"{emoji} (**{emoji.name}**) \U00002014 `{emoji}`" 
                for emoji in self.bot.emojis[offset:offset+length]
            )
            n = Pagination.compute_total_pages(len(self.bot.emojis), length)
            return emb, n

        await Pagination(interaction, get_page_part).navigate()

    @app_commands.command(name='randomfact', description='Queries a random fact')
    @app_commands.allowed_contexts(**LIMITED_CONTEXTS)
    @app_commands.allowed_installs(**LIMITED_INSTALLS)
    async def random_fact(self, interaction: discord.Interaction) -> None:
        async with self.bot.session.get(
            url='https://api.api-ninjas.com/v1/facts', 
            params={'X-Api-Key': self.bot.NINJAS_API_KEY}
        ) as resp:
            if resp.status != 200:
                return await interaction.response.send_message(embed=membed(API_EXCEPTION))
            text = await resp.json()
        await interaction.response.send_message(embed=membed(f"{text[0]['fact']}."))

    @app_commands.command(name="image", description="Manipulate a user's avatar")
    @app_commands.describe(
        user="The user to apply the manipulation to. Defaults to you.", 
        endpoint="What kind of manipulation sorcery to use."
    )
    @app_commands.allowed_contexts(**LIMITED_CONTEXTS)
    @app_commands.allowed_installs(**LIMITED_INSTALLS)
    async def image_manip(
        self, 
        interaction: discord.Interaction, 
        endpoint: Literal[
            "abstract", "balls", "billboard", "bonks", "bubble", "canny", "clock",
            "cloth", "contour", "cow", "cube", "dilate", "fall", "fan", "flush", "gallery",
            "globe", "half-invert", "hearts", "infinity", "laundry", "lsd", "optics", "parapazzi"
        ],
        user: discord.User | None = None
    ) -> None:

        start = perf_counter()
        await interaction.response.defer(thinking=True)

        user = user or interaction.user
        params = {'image_url': user.display_avatar.url}
        headers = {'Authorization': f'Bearer {self.bot.JEYY_API_KEY}'}
        api_url = f"https://api.jeyy.xyz/v2/image/{endpoint}"

        await self.format_gif_api_response(
            interaction,
            start=start,
            api_url=api_url,
            params=params,
            headers=headers
        )

    @app_commands.command(name="image2", description="Manipulate a user's avatar further")
    @app_commands.describe(
        user="The user to apply the manipulation to. Defaults to you.",
        endpoint="What kind of manipulation sorcery to use."
    )
    @app_commands.allowed_contexts(**LIMITED_CONTEXTS)
    @app_commands.allowed_installs(**LIMITED_INSTALLS)
    async def image2_manip(
        self, 
        interaction: discord.Interaction,
        endpoint: Literal[
            "minecraft", "patpat", "plates", "pyramid", 
            "radiate", "rain", "ripped", "ripple",
            "shred", "wiggle", "warp", "wave"
        ],
        user: discord.User | None = None
    ):

        start = perf_counter()
        await interaction.response.defer(thinking=True)

        user = user or interaction.user
        params = {'image_url': user.display_avatar.url}
        headers = {'Authorization': f'Bearer {self.bot.JEYY_API_KEY}'}
        api_url = f"https://api.jeyy.xyz/v2/image/{endpoint}"

        await self.format_gif_api_response(
            interaction,
            start=start,
            api_url=api_url,
            params=params,
            headers=headers
        )

    @app_commands.command(name='charinfo', description='Show information about characters')
    @app_commands.allowed_contexts(**LIMITED_CONTEXTS)
    @app_commands.allowed_installs(**LIMITED_INSTALLS)
    @app_commands.describe(characters='Any written letters or symbols.')
    async def charinfo(self, interaction: discord.Interaction, characters: str) -> None:
        """
        Shows you information about a number of characters.
        Only up to 25 characters at a time.
        """

        def to_string(c):
            digit = f'{ord(c):x}'
            the_name = name(c, 'Name not found.')
            c = '\\`' if c == '`' else c
            return (
                f'[`\\U{digit:>08}`](http://www.fileformat.info/info/unicode/char/{digit}): {the_name} '
                f'**\N{EM DASH}** {c}'
            )

        msg = '\n'.join(map(to_string, characters))
        if len(msg) > 2000:
            return await interaction.response.send_message(
                ephemeral=True, 
                embed=membed('Output too long to display.')
            )
        await interaction.response.send_message(msg, suppress_embeds=True)

    @app_commands.command(name='about', description='Learn more about the bot')
    @app_commands.allowed_contexts(**LIMITED_CONTEXTS)
    @app_commands.allowed_installs(**LIMITED_INSTALLS)
    async def about_the_bot(self, interaction: discord.Interaction) -> None:

        commits = await self.fetch_commits()
        to_iso = datetime.fromisoformat
        revision = [
            f"[`{commit['sha'][:6]}`]({commit['html_url']}) {commit['commit']['message'].splitlines()[0]} "
            f"({format_relative(to_iso(commit['commit']['author']['date']))})"
            for commit in commits
        ]

        embed = discord.Embed(
            title='Official Bot Server Invite',
            description=f"Latest Changes:\n{'\n'.join(revision)}", 
            url='https://discord.gg/W3DKAbpJ5E'
        ).set_author(name="inter_geo", icon_url="https://tinyurl.com/m1m2m3ma")
        embed.timestamp, embed.colour = discord.utils.utcnow(), discord.Colour.blurple()

        total_members, total_unique = 0, len(self.bot.users)
        text, voice, guilds = 0, 0, 0

        for guild in self.bot.guilds:
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

        diff = embed.timestamp - self.bot.time_launch
        minutes, seconds = divmod(diff.total_seconds(), 60)
        hours, minutes = divmod(minutes, 60)
        days, hours = divmod(hours, 24)

        async with interaction.client.pool.acquire() as conn:
            slash_ran, total_ran, text_ran = await conn.fetchone(
                """
                WITH slash_commands AS (
                    SELECT SUM(cmd_count) AS total_sum 
                    FROM command_uses
                    WHERE cmd_name LIKE '/%'
                ),
                total_commands AS (
                    SELECT SUM(cmd_count) AS total_sum
                    FROM command_uses
                )
                SELECT 
                    slash_commands.total_sum AS slash_commands_sum,
                    total_commands.total_sum AS total_commands_sum,
                    (total_commands.total_sum - slash_commands.total_sum) AS text_commands_sum
                FROM 
                    slash_commands, 
                    total_commands
                """
            )

        embed.add_field(
            name='<:Members:1263922150125994054> Members',
            value=f'{total_members} total\n{total_unique} unique'
        ).add_field(
            name='<:searchChannels:1263923406592540802> Channels', 
            value=f'{text + voice} total\n{text} text\n{voice} voice'
        ).add_field(
            name='<:Process:1263923016803418203> Process', 
            value=f'{memory_usage:.2f} MiB\n{cpu_usage:.2f}% CPU'
        ).add_field(
            name='<:Servers:1263923465409400832> Guilds', 
            value=(
                f'{guilds} total\n'
                f'{ARROW}{len(self.bot.emojis)} emojis\n'
                f'{ARROW}{len(self.bot.stickers)} stickers'
            )
        ).add_field(
            name='<:slashCommands:1263923524213538917> Commands Run', 
            value=(
                f"{total_ran:,} total\n"
                f"{ARROW} {slash_ran:,} slash\n"
                f"{ARROW} {text_ran:,} text"
            )
        ).add_field(
            name='<:Uptime:1263923835602993183> Uptime', 
            value=f"{int(days)}d {int(hours)}h {int(minutes)}m {int(seconds)}s"
        ).set_footer(
            text=f'Made with discord.py v{discord.__version__}', 
            icon_url='http://i.imgur.com/5BFecvA.png'
        )

        await interaction.response.send_message(embed=embed)

    async def view_avatar(self, interaction: discord.Interaction, username: discord.User) -> None:
        avatar_url = username.display_avatar.with_static_format('png').url
        embed = membed().set_image(url=avatar_url).set_author(
            name=username.display_name, 
            icon_url=avatar_url
        )

        img_view = discord.ui.View().add_item(ImageSourceButton(url=embed.author.icon_url))
        await interaction.response.send_message(embed=embed, view=img_view)

    async def view_banner(self, interaction: discord.Interaction, username: discord.User) -> None:
        username = await self.bot.fetch_user(username.id)
        embed = membed().set_author(
            name=username.display_name, 
            icon_url=username.display_avatar.url
        )

        if not username.banner:
            embed.description = "This user does not have a banner."
            return await interaction.response.send_message(embed=embed)

        embed.set_image(url=username.banner.with_static_format('png'))
        img_view = discord.ui.View().add_item(ImageSourceButton(url=embed.image.url))

        await interaction.response.send_message(embed=embed, view=img_view)

    @app_commands.command(name='post', description='Upload a new forum thread')
    @app_commands.guild_install()
    @app_commands.allowed_contexts(guilds=True)
    @app_commands.describe(
        name="The name of the thread.",
        forum="What forum this thread should be in.",
        description="The content of the message to send with the thread.",
        tags="The tags to apply to the thread, seperated by speech marks.",
        file=UPLOAD_FILE_DESCRIPTION,
        file2=UPLOAD_FILE_DESCRIPTION,
        file3=UPLOAD_FILE_DESCRIPTION
    )
    @app_commands.default_permissions(manage_guild=True)
    async def create_new_thread(
        self, 
        interaction: discord.Interaction, 
        forum: discord.ForumChannel,
        name: str, 
        tags: str, 
        description: str | None = None, 
        file: discord.Attachment | None = None, 
        file2: discord.Attachment | None = None,
        file3: discord.Attachment | None = None
    ) -> None:
        await interaction.response.defer(thinking=True)

        files = [
            await param_value.to_file() 
            for param_name, param_value in iter(interaction.namespace) 
            if param_name.startswith("fi") and param_value
        ]

        tag_sep = [s for s in tags.split('"') if s.strip()]
        applicable_tags = [
            tag_obj 
            for tag in tag_sep 
            if (tag_obj := discord.utils.find(lambda t: t.name.lower() == tag.lower(), forum.available_tags))
        ]

        thread, _ = await forum.create_thread(
            name=name,
            content=description,
            files=files,
            applied_tags=applicable_tags
        )

        await interaction.followup.send(ephemeral=True, embed=membed(f"Created thread: {thread.jump_url}."))
        del files, tag_sep, applicable_tags

    @commands.command(name="worldclock", description="See the world clock and the visual sunmap", aliases=('wc',))
    async def worldclock(self, ctx: commands.Context):
        async with ctx.typing():
            clock = discord.Embed(
                title="UTC", 
                colour=0x2AA198, 
                timestamp=discord.utils.utcnow()
            ).set_author(
                icon_url="https://i.imgur.com/CIl9Dyp.png",
                name="All formats given in 12h notation"
            ).set_footer(text="Sunmap image courtesy of timeanddate.com")

            for location, tz in EMBED_TIMEZONES.items():
                time_there = datetime.now(tz=pytz_timezone(tz))
                clock.add_field(name=location, value=f"```prolog\n{time_there:%I:%M %p}```")

            clock.description = f"```prolog\n{clock.timestamp:%I:%M %p, %A} {number_to_ordinal(int(f"{clock.timestamp:%d}"))} {clock.timestamp:%Y}```"
            clock.add_field(
                name="Legend",
                inline=False,
                value=(
                    "☀️ = The Sun's position directly overhead in relation to an observer.\n"
                    "🌕 = The Moon's position at its zenith in relation to an observer."
                )
            ).set_image(url=f"https://www.timeanddate.com/scripts/sunmap.php?iso={clock.timestamp:'%Y%m%dT%H%M'}")
            await ctx.send(embed=clock)


async def setup(bot: commands.Bot):
    await bot.add_cog(Utility(bot))
