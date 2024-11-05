import sqlite3
from datetime import datetime, timezone
from io import BytesIO
from typing import Callable, Generator, Literal, Optional
from unicodedata import name
from xml.etree.ElementTree import Element, fromstring

import discord
from discord import app_commands
from psutil import cpu_count
from pytz import timezone as pytz_timezone

from ._types import BotExports
from .core.bot import Interaction
from .core.helpers import commands_used_by, membed, send_prompt, to_ord
from .core.paginators import Pagination, RefreshPagination

BASE = "http://www.fileformat.info/info/unicode/char/"
GH_PARAMS = {"per_page": 3}
FACTS_ENDPOINT = "https://api.api-ninjas.com/v1/facts"
COMMITS_ENDPOINT = "https://api.github.com/repos/SGA-A/c2c/commits"
TEXT_RAN = 6231  # goodbye prefix commands
ARROW = "<:Arrow:1263919893762543717>"
API_EXCEPTION = "The API fucked up, try again later."
API_ENDPOINTS = Literal[
    "abstract", "balls", "billboard", "bonks",
    "bubble", "canny", "clock", "cloth", "contour",
    "cow", "cube", "dilate", "fall",
    "fan", "flush", "gallery", "globe",
    "half-invert", "hearts", "infinity",
    "laundry", "lsd", "optics", "parapazzi"
]
MORE_API_ENDPOINTS = Literal[
    "minecraft", "patpat", "plates", "pyramid",
    "radiate", "rain", "ripped", "ripple",
    "shred", "wiggle", "warp", "wave"
]
EMBED_TIMEZONES = {
    "Pacific": "US/Pacific",
    "Mountain": "US/Mountain",
    "Central": "US/Central",
    "Eastern": "US/Eastern",
    "Britain": "Europe/London",
    "Sydney": "Australia/Sydney",
    "Japan": "Asia/Tokyo",
    "Germany": "Europe/Berlin",
    "India": "Asia/Kolkata"
}


def from_epoch(timestamp: int) -> datetime:
    return datetime.fromtimestamp(timestamp, tz=timezone.utc)


def format_dt(dt: datetime, style: Optional[str] = None) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return discord.utils.format_dt(dt, style)


def relative(dt: datetime) -> str:
    return format_dt(dt, "R")


def parse_posts(
    raw_xml: list[Element],
    offset: int,
    length: int
) -> Generator[tuple[str, str, str], None, None]:
    return (
        (
            img_metadata.get("id"),
            img_metadata.get("jpeg_url"),
            img_metadata.get("author"),
            img_metadata.get("created_at")
        )
        for img_metadata in raw_xml[offset:offset+length]
    )


def parse_xml(mode: Literal["post", "tag"], xml: str, /) -> list[Element]:
    return fromstring(xml).findall(f".//{mode}")


class CommandUsage(RefreshPagination):
    length = 12
    def __init__(
        self,
        itx: Interaction,
        viewing: discord.abc.User,
        get_page: Optional[Callable] = None,
    ) -> None:
        super().__init__(itx, get_page)

        self.viewing = viewing
        self.embed = membed()
        self.embed.title = f"{viewing.display_name}'s Command Usage"
        self.data = []  # commands list

        user_select: discord.ui.UserSelect = self.children[-1]
        user_select.default_values = [discord.Object(id=self.viewing.id)]

    async def fetch_data(self) -> None:
        async with self.itx.client.pool.acquire() as conn:
            self.data = await conn.fetchall(
                """
                SELECT cmd_name, cmd_count
                FROM command_uses
                WHERE userID = $0
                ORDER BY cmd_count DESC
                """, self.viewing.id
            )
            if not self.data:
                self.embed.description = None
                self.total, self.total_pages = 0, 1
                return

            self.total = await commands_used_by(self.viewing.id, conn)
        self.total_pages = self.compute_total_pages(
            len(self.data), self.length
        )

    @discord.ui.select(
        cls=discord.ui.UserSelect,
        placeholder="Select a registered user",
        row=0
    )
    async def user_select(
        self,
        itx: Interaction,
        select: discord.ui.UserSelect
    ) -> None:
        self.viewing = select.values[0]
        self.index = 1

        self.embed.title = f"{self.viewing.display_name}'s Command Usage"
        select.default_values = [discord.Object(id=self.viewing.id)]

        await self.fetch_data()
        await self.edit_page(itx)


class KonaPagination(Pagination):
    book = "\U0001f516"
    icon_url = "https://i.imgur.com/AlDBkyA.png"

    def __init__(
        self,
        itx: Interaction,
        total_pages: int,
        get_page: Optional[Callable] = None
    ) -> None:
        super().__init__(itx, total_pages, get_page)

        self.url_dict: dict[str, str] = {}
        self.dropdown: discord.ui.Select = self.children[-1]

    async def navigate(self, **kwargs) -> None:
        embeds = await self.get_page()
        self.dropdown.max_values = len(embeds)
        self.refresh_options(embeds)

        if self.total_pages == 1:
            await self.itx.followup.send(embeds=embeds, **kwargs)

        self.update_buttons(self)
        await self.itx.followup.send(embeds=embeds, view=self, **kwargs)

    async def edit_page(self, itx: Interaction) -> None:
        embeds = await self.get_page()
        self.dropdown.max_values = len(embeds)

        # Remove previous image IDs and their URLs
        self.url_dict = {}
        self.refresh_options(embeds)

        self.update_buttons(self)
        await itx.response.edit_message(embeds=embeds, view=self)

    def refresh_options(self, embeds: list[discord.Embed]) -> None:
        self.dropdown.options = self.dropdown.options or [
            discord.SelectOption(label=f"x{i}", emoji="\U0001f194")
            for i, _ in enumerate(embeds)
        ]

        for em, opt in zip(embeds, self.dropdown.options, strict=True):
            opt.value, opt.label = em.footer.text, em.footer.text
            self.url_dict[opt.label] = em.image.url

    @discord.ui.select(row=2, placeholder="Select images to bookmark")
    async def dropdown_callback(
        self,
        itx: Interaction,
        select: discord.ui.Select
    ) -> None:

        query = (
            """
            INSERT INTO bookmarks (userID, bookmarkID, bookmark)
            VALUES (?, ?, ?)
            """
        )

        args = [
            (itx.user.id, int(img_id), self.url_dict[img_id])
            for img_id in select.values
        ]

        async with itx.client.pool.acquire() as conn, conn.transaction():
            try:
                await conn.executemany(query, args)
            except sqlite3.IntegrityError:
                pass

        await itx.response.send_message("\U00002705", ephemeral=True)


async def fetch_commits(itx: Interaction) -> str:
    gh_headers = {
        "Authorization": f"token {itx.client.gh_token}",
        "Accept": "application/vnd.github.v3+json"
    }

    async with itx.client.session.get(
        url=COMMITS_ENDPOINT,
        headers=gh_headers,
        params=GH_PARAMS
    ) as resp:
        commits = await resp.json() if resp.status == 200 else []

    revision = "\n".join(
        f"[`{c['sha'][:6]}`]({c['html_url']}) "
        f"{c['commit']['message'].splitlines()[0]} "
        f"({relative(datetime.fromisoformat(c['commit']['author']['date']))})"
        for c in commits
    ) or ""

    return revision


async def tag_autocomplete(
    itx: Interaction,
    current: str
) -> list[app_commands.Choice[str]]:

    current = current.lower()
    tags_xml = await kona(
        itx,
        name=current,
        mode="tag",
        page=1,
        order="count",
        limit=25
    )

    # http status code was returned (when != 200 OK)
    if isinstance(tags_xml, int):
        return []

    return [
        app_commands.Choice(name=tag_name, value=tag_name)
        for tag_xml in tags_xml if (tag_name:= tag_xml.get("name"))
    ]


async def kona(itx: Interaction, **params) -> int | list[Element]:
    """
    Returns a list of dict-like elements for
    you to iterate through and fetch their attributes.
    """

    mode = params.pop("mode")
    base_url = f"https://konachan.net/{mode}.xml"

    async with itx.client.session.get(base_url, params=params) as resp:
        if resp.status != 200:
            return resp.status

        return parse_xml(mode, await resp.text())


async def format_gif_api_response(
    itx: Interaction,
    url: str,
    param: dict,
    header: dict,
    /
) -> None:
    async with itx.client.session.get(url, params=param, headers=header) as r:
        if r.status != 200:
            await itx.followup.send(API_EXCEPTION)
            return
        initial_bytes = await r.read()

    buffer = BytesIO(initial_bytes)
    await itx.followup.send(file=discord.File(buffer, "clip.gif"))


@app_commands.command(description="See your total command usage")
@app_commands.describe(user="Whose command usage to display.")
async def usage(
    itx: Interaction,
    user: Optional[discord.User]
) -> None:
    user = user or itx.user

    paginator = CommandUsage(itx, viewing=user)
    await paginator.fetch_data()

    async def get_page(refresh: bool = False) -> list[discord.Embed]:
        if refresh:
            await paginator.fetch_data()
            paginator.index = min(paginator.index, paginator.total_pages)

        if not paginator.data:
            paginator.embed.description = None
            return [paginator.embed.set_footer(text="Empty")]

        offset = (paginator.index - 1) * paginator.length
        desc = "\n".join(
            f"` {usage:,} ` \U00002014 {cmd_name}"
            for cmd_name, usage in paginator.data[
                offset:offset + paginator.length
            ]
        )

        paginator.embed.description = f"> Total: {paginator.total:,}\n\n{desc}"

        return [
            paginator.embed.set_footer(
                text=f"Page {paginator.index} of {paginator.total_pages}"
            )
        ]

    paginator.get_page = get_page
    await paginator.navigate()


@app_commands.command(description="Calculate an expression")
@app_commands.describe(expression="The expression to evaluate.")
async def calc(itx: Interaction, expression: str) -> None:
    try:
        expression = expression.replace("^", "**").replace(",", "_")
        result = eval(expression)

        result = (
            f"{result:,}" if isinstance(result, (int, float))
            else "Invalid Equation"
        )
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


@app_commands.command(description="Checks latency of the bot")
async def ping(itx: Interaction) -> None:
    await itx.response.send_message(f"{itx.client.latency * 1000:.0f}ms")


bookmark_group = app_commands.Group(
    name="bookmarks",
    description="Manage your kona bookmarks"
)


kona_group = app_commands.Group(
    name="kona",
    description="Surf through kona images and posts"
)


kona_group.add_command(bookmark_group)


@kona_group.command(name="search", description="Retrieve posts from Konachan")
@app_commands.describe(
    tag1="A tag to base your search on.",
    tag2="A tag to base your search on.",
    tag3="A tag to base your search on." ,
    private="Hide the results from others. Defaults to True.",
    per_page="The maximum number of images to display at once. Defaults to 3.",
    maximum="The maximum number of images to retrieve. Defaults to 30.",
    page="The page number to look through."
)
@app_commands.autocomplete(
    tag1=tag_autocomplete,
    tag2=tag_autocomplete,
    tag3=tag_autocomplete
)
async def kona_search(
    itx: Interaction,
    tag1: str,
    tag2: Optional[str],
    tag3: Optional[str],
    private: bool = True,
    per_page: app_commands.Range[int, 1, 10] = 3,
    maximum: app_commands.Range[int, 1, 1000] = 30,
    page: app_commands.Range[int, 1] = 1
) -> Optional[discord.WebhookMessage]:
    await itx.response.defer(thinking=True, ephemeral=private)

    tag_args = (arg for _, arg in itx.namespace if isinstance(arg, str))
    tagviewing = " ".join(tag_args)

    xml: list[Element] = await kona(
        itx,
        tags=tagviewing,
        limit=maximum,
        page=page,
        mode="post"
    )

    if isinstance(xml, int):
        return await itx.followup.send(API_EXCEPTION)

    # If the list of raw XML is empty
    if not xml:
        resp = (
            "## No posts found\n"
            "There are a few known causes:\n"
            "- Entering an invalid tag name\n"
            "- Posts aren't available under this tag\n"
            "- Page number exceeds maximum available under this tag\n"
            "-# Find a tag by using the [website.](<https://konachan.net/tag>)"
        )
        return await itx.followup.send(resp, ephemeral=True)

    total_pages = Pagination.compute_total_pages(len(xml), per_page)
    paginator = KonaPagination(itx, total_pages)

    async def get_page() -> list[discord.Embed]:
        offset = (paginator.index - 1) * per_page

        return [
            discord.Embed(
                title=author,
                colour=0x2B2D31,
                url=url,
                timestamp=from_epoch(int(created))
            ).set_image(url=url).set_footer(
                text=f"{img_id}", icon_url=paginator.icon_url
            )
            for (img_id, url, author, created) in parse_posts(
                xml, offset, per_page
            )
        ]

    paginator.get_page = get_page
    await paginator.navigate(ephemeral=private)


@bookmark_group.command(name="remove", description="Remove a kona bookmark")
@app_commands.describe(bookmark_id="The bookmark ID to remove.")
async def remove_bookmark(
    itx: Interaction,
    bookmark_id: app_commands.Range[int, 1, 10_000_000]
) -> None:

    query = (
        """
        DELETE
        FROM bookmarks
        WHERE userID = ? AND bookmarkID = ?
        """
    )

    async with itx.client.pool.acquire() as conn, conn.transaction():
        await conn.execute(query, (itx.user.id, bookmark_id))
    await itx.response.send_message("\U00002705", ephemeral=True)


@bookmark_group.command(name="list", description="List your kona bookmarks")
@app_commands.describe(
    per_page="The amount to images to display at once on each page.",
    private="Hide your bookmarks from others. Defaults to True."
)
async def list_bookmarks(
    itx: Interaction,
    per_page: app_commands.Range[int, 1, 10] = 3,
    private: bool = True
) -> None:

    query = "SELECT bookmarkID, bookmark FROM bookmarks WHERE userID = ?"
    async with itx.client.pool.acquire() as conn:
        bookmarks = await conn.fetchall(query, (itx.user.id,))

    if not bookmarks:
        return await itx.response.send_message(
            "You have no bookmarks.", ephemeral=private
        )

    total_pages = Pagination.compute_total_pages(len(bookmarks), per_page)
    paginator = Pagination(itx, total_pages)

    async def get_page() -> list[discord.Embed]:
        offset = (paginator.index - 1) * per_page
        return [
            membed().set_image(
                url=image_url
            ).set_footer(icon_url=KonaPagination.icon_url, text=image_id)
            for image_id, image_url in bookmarks[offset:offset+per_page]
        ]

    paginator.get_page = get_page
    await paginator.navigate(ephemeral=private)


@bookmark_group.command(description="Delete all of your kona bookmarks")
async def clear(itx: Interaction) -> None:

    query = "SELECT COUNT(*) FROM bookmarks WHERE userID = ?"
    async with itx.client.pool.acquire() as conn:
        count, = await conn.fetchone(query, (itx.user.id,))

    if not count:
        return await itx.response.send_message("You have no bookmarks!")

    prompt = f"You are about to erase **{count:,}** bookmarks. Continue?"
    confirmed = await send_prompt(itx, prompt)
    if not confirmed:
        return

    query = "DELETE FROM bookmarks WHERE userID = ? RETURNING COUNT(*)"
    async with itx.client.pool.acquire() as conn, conn.transaction():
        deleted, = await conn.fetchone(query, (itx.user.id,))

    resp = (
        f"**{deleted:,}** bookmarks erased successfully."
        if deleted else
        "You have no bookmarks to erase."
    )

    await itx.followup.send(resp)


@app_commands.command(description="Queries a random fact")
async def randomfact(itx: Interaction) -> None:
    params = {"X-Api-Key": itx.client.ninja_api}

    async with itx.client.session.get(FACTS_ENDPOINT, params=params) as resp:
        if resp.status != 200:
            return await itx.response.send_message(API_EXCEPTION)
        text = await resp.json()
    await itx.response.send_message(text[0]["fact"])


@app_commands.command(description="Manipulate a user's avatar")
@app_commands.describe(
    user="The user to apply the manipulation to. Defaults to you.",
    endpoint="What kind of manipulation sorcery to use."
)
async def image(
    itx: Interaction,
    endpoint: API_ENDPOINTS,
    user: Optional[discord.User]
) -> None:
    await itx.response.defer(thinking=True)

    user = user or itx.user
    params = {"image_url": user.display_avatar.url}
    headers = {"Authorization": f"Bearer {itx.client.j_api}"}
    api_url = f"https://api.jeyy.xyz/v2/image/{endpoint}"

    await format_gif_api_response(itx, api_url, params, headers)


@app_commands.command(description="Manipulate a user's avatar further")
@app_commands.describe(
    user="The user to apply the manipulation to. Defaults to you.",
    endpoint="What kind of manipulation sorcery to use."
)
async def image2(
    itx: Interaction,
    endpoint: MORE_API_ENDPOINTS,
    user: Optional[discord.User]
) -> None:
    await itx.response.defer(thinking=True)

    user = user or itx.user
    params = {"image_url": user.display_avatar.url}
    headers = {"Authorization": f"Bearer {itx.client.j_api}"}
    api_url = f"https://api.jeyy.xyz/v2/image/{endpoint}"

    await format_gif_api_response(itx, api_url, params, headers)


@app_commands.command(description="Show information about characters")
@app_commands.describe(characters="Any written letters or symbols.")
async def charinfo(
    itx: Interaction,
    characters: app_commands.Range[str, 1, 25]
) -> None:

    def to_string(c):
        digit = f"{ord(c):x}"
        the_name = name(c, "Name not found.")
        c = "\\`" if c == "`" else c
        return (
            f"[`\\U{digit:>08}`]({BASE}{digit}): "
            f"{the_name} **\N{EM DASH}** {c}"
        )

    msg = "\n".join(map(to_string, characters))
    if len(msg) > 2000:
        return await itx.response.send_message(
            "Output too long to display.",
            ephemeral=True
        )
    await itx.response.send_message(msg, suppress_embeds=True)


@app_commands.command(description="Learn more about the bot")
async def about(itx: Interaction) -> None:

    revision = await fetch_commits(itx)

    embed = discord.Embed(
        title="Official Bot Server Invite",
        description=f"Latest Changes:\n{revision}",
        url="https://discord.gg/W3DKAbpJ5E"
    )

    embed.timestamp = discord.utils.utcnow()
    embed.colour = discord.Colour.blurple()
    embed.set_author(
        name="inter_geo",
        icon_url="https://tinyurl.com/m1m2m3ma"
    )

    memory_usage = itx.client.process.memory_full_info().uss / 1024 ** 2
    cpu_usage = itx.client.process.cpu_percent() / cpu_count()

    diff = embed.timestamp - itx.client.time_launch
    minutes, seconds = divmod(diff.total_seconds(), 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)

    async with itx.client.pool.acquire() as conn:
        slash_ran, = await conn.fetchone(
            """
            SELECT SUM(cmd_count)
            FROM command_uses
            WHERE cmd_name LIKE '/%'
            """
        )

    embed.add_field(
        name="<:Process:1263923016803418203> Process",
        value=f"{memory_usage:.2f} MiB\n{cpu_usage:.2f}% CPU"
    )

    embed.add_field(
        name="<:slashCommands:1263923524213538917> Commands Run",
        value=(
            f"{TEXT_RAN+slash_ran:,} total\n"
            f"{ARROW} {slash_ran:,} slash\n"
            f"{ARROW} {TEXT_RAN:,} text"
        )
    )

    embed.add_field(
        name="<:Uptime:1263923835602993183> Uptime",
        value=f"{int(days)}d {int(hours)}h {int(minutes)}m {int(seconds)}s"
    )

    embed.set_footer(
        text=f"Made with discord.py v{discord.__version__}",
        icon_url="http://i.imgur.com/5BFecvA.png"
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
        clock.add_field(
            name=location,
            value=f"```prolog\n{time_there:%I:%M %p}```"
        )

    sunmap = (
        f"https://www.timeanddate.com/scripts/"
        f"sunmap.php?iso={clock.timestamp:'%Y%m%dT%H%M'}"
    )

    clock.description = (
        f"```prolog\n{clock.timestamp:%I:%M %p, %A} "
        f"{to_ord(int(f"{clock.timestamp:%d}"))} {clock.timestamp:%Y}```"
    )

    clock.add_field(
        name="Legend",
        inline=False,
        value=(
            "\U00002600\U0000fe0f = The Sun's position "
            "directly overhead in relation to an observer.\n"

            "\U0001f315 = The Moon's position "
            "at its zenith in relation to an observer."
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
        usage, calc, worldclock,
        ping, kona_group, randomfact,
        image, image2, charinfo,
        about
    ]
)