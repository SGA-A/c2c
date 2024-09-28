from io import BytesIO
from unicodedata import name
from datetime import datetime, timezone
from typing import Callable, Literal, Optional
from xml.etree.ElementTree import fromstring, Element

import discord
from pytz import timezone as pytz_timezone
from discord import app_commands
from psutil import cpu_count


from ._types import BotExports
from .core.bot import Interaction
from .core.helpers import membed, number_to_ordinal, total_commands_used_by_user
from .core.paginators import Pagination, RefreshPagination


GH_PARAMS = {"per_page": 3}
FACTS_ENDPOINT = 'https://api.api-ninjas.com/v1/facts'
COMMITS_ENDPOINT = "https://api.github.com/repos/SGA-A/c2c/commits"
TEXT_RAN = "6,231"  # goodbye prefix commands
USER_ENTRY = discord.Member | discord.User
ARROW = "<:Arrow:1263919893762543717>"
API_EXCEPTION = "The API fucked up, try again later."
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


def format_dt(dt: datetime, style: Optional[str] = None) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    if style is None:
        return f'<t:{int(dt.timestamp())}>'
    return f'<t:{int(dt.timestamp())}:{style}>'


def format_relative(dt: datetime) -> str:
    return format_dt(dt, 'R')


def extract_post_xml(raw_xml: list[Element], offset: int, length: int):
    return (
        (
            img_metadata.get("jpeg_url"),
            img_metadata.get("author"),
            img_metadata.get("created_at")
        )
        for img_metadata in raw_xml[offset:offset+length]
    )


def parse_xml(xml_content, mode: Literal["post", "tag"]):
    return fromstring(xml_content).findall(f".//{mode}")


class CommandUsage(RefreshPagination):
    length = 12
    def __init__(
        self,
        itx: Interaction,
        viewing: discord.Member | discord.User,
        get_page: Optional[Callable] = None,
    ) -> None:
        super().__init__(itx, get_page)
        self.viewing = viewing
        self.usage_embed = discord.Embed(
            title=f"{viewing.display_name}'s Command Usage",
            colour=0x2B2D31
        )
        self.usage_data = []  # commands list
        self.children[-1].default_values = [discord.Object(id=self.viewing.id)]

    async def fetch_data(self):
        async with self.itx.client.pool.acquire() as conn:
            self.usage_data = await conn.fetchall(
                """
                SELECT cmd_name, cmd_count
                FROM command_uses
                WHERE userID = $0
                ORDER BY cmd_count DESC
                """, self.viewing.id
            )
            if not self.usage_data:
                self.usage_embed.description = None
                self.total, self.total_pages = 0, 1
                return

            self.total = await total_commands_used_by_user(self.viewing.id, conn)
        self.total_pages = self.compute_total_pages(len(self.usage_data), self.length)

    @discord.ui.select(cls=discord.ui.UserSelect, placeholder="Select a registered user", row=0)
    async def user_select(self, itx: Interaction, select: discord.ui.UserSelect):
        self.viewing = select.values[0]
        self.index = 1

        self.usage_embed.title = f"{self.viewing.display_name}'s Command Usage"
        select.default_values = [discord.Object(id=self.viewing.id)]

        await self.fetch_data()
        await self.edit_page(itx)


async def fetch_commits(itx: Interaction):
    gh_headers = {
        "Authorization": f"token {itx.client.gh_token}",
        "Accept": "application/vnd.github.v3+json"
    }

    async with itx.client.session.get(
        url=COMMITS_ENDPOINT,
        headers=gh_headers,
        params=GH_PARAMS
    ) as resp:
        if resp.status == 200:
            return await resp.json()
        return []


async def tag_search_autocomplete(
    itx: Interaction,
    current: str
) -> list[app_commands.Choice[str]]:
    tags_xml = await retrieve_via_kona(
        itx,
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
        for tag_xml in tags_xml if (tag_name:= tag_xml.get("name"))
    ]


async def retrieve_via_kona(itx: Interaction, /, **params) -> int | list[Element]:
    """Returns a list of dictionaries for you to iterate through and fetch their attributes"""
    mode = params.pop("mode")
    base_url = f"https://konachan.net/{mode}.xml"

    async with itx.client.session.get(base_url, params=params) as resp:
        if resp.status != 200:
            return resp.status

        return parse_xml(mode=mode, xml_content=(await resp.text()))


async def format_gif_api_response(
    itx: Interaction,
    api_url: str,
    params: dict,
    headers: dict,
    /
) -> None:
    async with itx.client.session.get(api_url, params=params, headers=headers) as resp:
        if resp.status != 200:
            await itx.followup.send(API_EXCEPTION)
            return
        initial_bytes = await resp.read()

    buffer = BytesIO(initial_bytes)
    await itx.followup.send(file=discord.File(buffer, 'clip.gif'))


@app_commands.guild_only()
@app_commands.guild_install()
@app_commands.command(description="Show information about the server and its members")
async def serverinfo(itx: Interaction) -> None:
    await itx.response.defer(thinking=True)

    guild = itx.guild
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

    await itx.followup.send(embed=serverinfo)


@app_commands.command(description="See your total command usage")
@app_commands.describe(user="Whose command usage to display. Defaults to you.")
async def usage(itx: Interaction, user: Optional[USER_ENTRY] = None):
    user = user or itx.user

    paginator = CommandUsage(itx, viewing=user)
    await paginator.fetch_data()

    async def get_page_part(force_refresh: bool = None) -> discord.Embed:
        if force_refresh:
            await paginator.fetch_data()
            paginator.index = min(paginator.index, paginator.total_pages)

        if not paginator.usage_data:
            return paginator.usage_embed.set_footer(text="Empty")

        offset = (paginator.index - 1) * paginator.length
        paginator.usage_embed.description = f"> Total: {paginator.total:,}\n\n"
        paginator.usage_embed.description += "\n".join(
            f"` {cmd_data[1]:,} ` \U00002014 {cmd_data[0]}"
            for cmd_data in paginator.usage_data[offset:offset + paginator.length]
        )

        return paginator.usage_embed.set_footer(text=f"Page {paginator.index} of {paginator.total_pages}")

    paginator.get_page = get_page_part
    await paginator.navigate()


@app_commands.command(description='Calculate an expression')
@app_commands.describe(expression='The expression to evaluate.')
async def calc(itx: Interaction, expression: str) -> None:
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

    await itx.response.send_message(embed=output)


@app_commands.command(description='Checks latency of the bot')
async def ping(itx: Interaction) -> None:
    await itx.response.send_message(f"{itx.client.latency * 1000:.0f}ms")


@app_commands.context_menu(name="Extract Embed Colour")
async def embed_colour_menu(itx: Interaction, message: discord.Message) -> None:

    all_embeds = [
        discord.Embed(
            colour=embed.colour,
            description=f"{embed.colour} - [`{embed.colour.value}`](https:/www.google.com)"
        ) for embed in message.embeds
    ]

    if all_embeds:
        return await itx.response.send_message(ephemeral=True, embeds=all_embeds)

    await itx.response.send_message(
        ephemeral=True,
        embed=membed("No embeds were found within this message.")
    )


anime = app_commands.Group(name='anime', description="Surf through anime images and posts.")


@anime.command(name='kona', description='Retrieve posts from Konachan')
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
    itx: Interaction,
    tag1: str,
    tag2: str = None,
    tag3: str = None,
    private: bool = True,
    length: app_commands.Range[int, 1, 10] = 3,
    maximum: app_commands.Range[int, 1, 1000] = 30,
    page: app_commands.Range[int, 1] = 1
) -> None:
    await itx.response.defer(thinking=True, ephemeral=private)
    tagviewing = ' '.join(val for _, val in itx.namespace if isinstance(val, str))

    posts_xml: list[Element] = await retrieve_via_kona(
        itx,
        tags=tagviewing,
        limit=maximum,
        page=page,
        mode="post"
    )

    if isinstance(posts_xml, int):
        embed = membed("Failed to make this request.")
        embed.title = f"{posts_xml}. That's an error."
        return await itx.followup.send(embed=embed)

    if not len(posts_xml):
        embed = membed(
            "There are a few known causes:\n"
            "- Entering an invalid tag name\n"
            "- Posts aren't available under this tag\n"
            "- Page number exceeds maximum available under this tag\n"
            "-# You can find a tag by using the [website.](https://konachan.net/tag)"
        )
        embed.title = "No posts found."
        return await itx.followup.send(embed=embed)

    total_pages = Pagination.compute_total_pages(len(posts_xml), length)
    paginator = Pagination(itx, total_pages)

    async def get_page_part() -> list[discord.Embed]:
        offset = (paginator.index - 1) * length
        return [
            discord.Embed(
                title=author,
                colour=0x2B2D31,
                url=jpeg_url,
                timestamp=datetime.fromtimestamp(int(created_at), tz=timezone.utc)
            ).set_image(url=jpeg_url)
            for (jpeg_url, author, created_at) in extract_post_xml(posts_xml, offset, length)
        ]

    paginator.get_page = get_page_part
    await paginator.navigate(ephemeral=private)


@app_commands.command(description='Queries a random fact')
async def randomfact(itx: Interaction) -> None:
    api_params = {'X-Api-Key': itx.client.ninja_api}

    async with itx.client.session.get(url=FACTS_ENDPOINT, params=api_params) as resp:
        if resp.status != 200:
            return await itx.response.send_message(API_EXCEPTION)
        text = await resp.json()
    await itx.response.send_message(text[0]['fact'])


@app_commands.command(description="Manipulate a user's avatar")
@app_commands.describe(
    user="The user to apply the manipulation to. Defaults to you.",
    endpoint="What kind of manipulation sorcery to use."
)
async def image(
    itx: Interaction,
    user: Optional[USER_ENTRY],
    endpoint: Literal[
        "abstract", "balls", "billboard", "bonks", "bubble", "canny", "clock",
        "cloth", "contour", "cow", "cube", "dilate", "fall", "fan", "flush", "gallery",
        "globe", "half-invert", "hearts", "infinity", "laundry", "lsd", "optics", "parapazzi"
    ]
) -> None:
    await itx.response.defer(thinking=True)

    user = user or itx.user
    params = {'image_url': user.display_avatar.url}
    headers = {'Authorization': f'Bearer {itx.client.j_api}'}
    api_url = f"https://api.jeyy.xyz/v2/image/{endpoint}"

    await format_gif_api_response(itx, api_url, params, headers)


@app_commands.command(description="Manipulate a user's avatar further")
@app_commands.describe(
    user="The user to apply the manipulation to. Defaults to you.",
    endpoint="What kind of manipulation sorcery to use."
)
async def image2(
    itx: Interaction,
    user: Optional[USER_ENTRY],
    endpoint: Literal[
        "minecraft", "patpat", "plates", "pyramid",
        "radiate", "rain", "ripped", "ripple",
        "shred", "wiggle", "warp", "wave"
    ]
) -> None:
    await itx.response.defer(thinking=True)

    user = user or itx.user
    params = {'image_url': user.display_avatar.url}
    headers = {'Authorization': f'Bearer {itx.client.j_api}'}
    api_url = f"https://api.jeyy.xyz/v2/image/{endpoint}"

    await format_gif_api_response(itx, api_url, params, headers)


@app_commands.command(description='Show information about characters')
@app_commands.describe(characters='Any written letters or symbols.')
async def charinfo(itx: Interaction, characters: app_commands.Range[str, 1, 25]) -> None:
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
        return await itx.response.send_message('Output too long to display.', ephemeral=True)
    await itx.response.send_message(msg, suppress_embeds=True)


@app_commands.command(description='Learn more about the bot')
async def about(itx: Interaction) -> None:

    commits = await fetch_commits(itx)
    revision = '\n'.join(
        f"[`{commit['sha'][:6]}`]({commit['html_url']}) "
        f"{commit['commit']['message'].splitlines()[0]} "
        f"({format_relative(datetime.fromisoformat(commit['commit']['author']['date']))})"
        for commit in commits
    )

    embed = discord.Embed(
        title='Official Bot Server Invite',
        description=f"Latest Changes:\n{revision}",
        url='https://discord.gg/W3DKAbpJ5E'
    )

    embed.timestamp, embed.colour = discord.utils.utcnow(), discord.Colour.blurple()
    embed.set_author(name="inter_geo", icon_url="https://tinyurl.com/m1m2m3ma")

    total_members, total_unique = 0, len(itx.client.users)
    text, voice, guilds = 0, 0, 0

    for guild in itx.client.guilds:
        guilds += 1
        if guild.unavailable:
            continue

        total_members += guild.member_count or 0
        for channel in guild.channels:
            if isinstance(channel, discord.TextChannel):
                text += 1
            elif isinstance(channel, discord.VoiceChannel):
                voice += 1

    memory_usage = itx.client.process.memory_full_info().uss / 1024 ** 2
    cpu_usage = itx.client.process.cpu_percent() / cpu_count()

    diff = embed.timestamp - itx.client.time_launch
    minutes, seconds = divmod(diff.total_seconds(), 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)

    async with itx.client.pool.acquire() as conn:
        slash_ran, total_ran = await conn.fetchone(
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
                slash_commands.total_sum,
                total_commands.total_sum
            FROM
                slash_commands,
                total_commands
            """
        )

    embed.add_field(
        name='<:Members:1263922150125994054> Members',
        value=f'{total_members} total\n{total_unique} unique'
    )

    embed.add_field(
        name='<:searchChannels:1263923406592540802> Channels',
        value=f'{text + voice} total\n{text} text\n{voice} voice'
    )

    embed.add_field(
        name='<:Process:1263923016803418203> Process',
        value=f'{memory_usage:.2f} MiB\n{cpu_usage:.2f}% CPU'
    )

    embed.add_field(
        name='<:Servers:1263923465409400832> Guilds',
        value=(
            f'{guilds} total\n'
            f'{ARROW}{len(itx.client.emojis)} emojis\n'
            f'{ARROW}{len(itx.client.stickers)} stickers'
        )
    )

    embed.add_field(
        name='<:slashCommands:1263923524213538917> Commands Run',
        value=(
            f"{total_ran:,} total\n"
            f"{ARROW} {slash_ran:,} slash\n"
            f"{ARROW} {TEXT_RAN} text"
        )
    )

    embed.add_field(
        name='<:Uptime:1263923835602993183> Uptime',
        value=f"{int(days)}d {int(hours)}h {int(minutes)}m {int(seconds)}s"
    )

    embed.set_footer(
        text=f'Made with discord.py v{discord.__version__}',
        icon_url='http://i.imgur.com/5BFecvA.png'
    )

    await itx.response.send_message(embed=embed)


@app_commands.command(description="Display a visual sunmap of the world")
async def worldclock(itx: Interaction) -> None:
    await itx.response.defer(thinking=True)

    clock = discord.Embed(
        title="UTC",
        colour=0x2AA198,
        timestamp=discord.utils.utcnow()
    )

    for location, tz in EMBED_TIMEZONES.items():
        time_there = datetime.now(tz=pytz_timezone(tz))
        clock.add_field(name=location, value=f"```prolog\n{time_there:%I:%M %p}```")

    sunmap = (
        f"https://www.timeanddate.com/scripts/sunmap.php?iso={clock.timestamp:'%Y%m%dT%H%M'}"
    )

    clock.description = (
        f"```prolog\n{clock.timestamp:%I:%M %p, %A} "
        f"{number_to_ordinal(int(f"{clock.timestamp:%d}"))} {clock.timestamp:%Y}```"
    )
    clock.add_field(
        name="Legend",
        inline=False,
        value=(
            "\U00002600\U0000fe0f = The Sun's position directly overhead in relation to an observer.\n"
            "\U0001f315 = The Moon's position at its zenith in relation to an observer."
        )
    )

    clock.set_image(url=sunmap).set_author(
        icon_url="https://i.imgur.com/CIl9Dyp.png",
        name="All formats given in 12h notation"
    )

    clock.set_footer(text="Sunmap image courtesy of timeanddate.com")

    await itx.followup.send(embed=clock)


exports = BotExports(
    [
        serverinfo, usage, calc,
        ping, anime, randomfact,
        image, image2, charinfo,
        about, worldclock, embed_colour_menu
    ]
)