import sqlite3
import contextlib
from asyncio import TimeoutError
from datetime import datetime, timezone
from typing import Optional, Union

import discord
from discord import app_commands
from asqlite import Connection

from ._types import BotExports
from .core.bot import Interaction
from .core.paginators import PaginationSimple
from .core.errors import FailingConditionalError
from .core.helpers import respond, process_confirmation


PROMO = "\n-# Save time by creating a tag from an existing message."
MAX_CHARACTERS_REACHED = f"Tag content cannot exceed 2000 characters.{PROMO}"
TAG_MISSING = "Could not find a tag with that name."
TAG_ALREADY_EXISTS = f"A tag with that name already exists.{PROMO}"
TAG_NOT_FOUND = "No tags were found with said properties."
CONTENT_DELIMITER = app_commands.Range[str, 1, 2000]
TAG_DELIMITER = app_commands.Range[str, 1, 80]
PAGE_SIZE = 12


class TagEditModal(discord.ui.Modal, title="Edit Tag"):
    content = discord.ui.TextInput(
        label="Tag Content",
        required=True,
        style=discord.TextStyle.long,
        min_length=1,
        max_length=2000
    )

    def __init__(self, text: str) -> None:
        super().__init__()
        self.content.default = text

    async def on_submit(self, itx: Interaction) -> None:
        self.itx = itx
        self.text = str(self.content)
        self.stop()


class TagMakeModal(discord.ui.Modal, title="Create New Tag"):
    name = discord.ui.TextInput(
        label="Name",
        min_length=1,
        max_length=80,
        placeholder="The name of this tag."
    )

    content = discord.ui.TextInput(
        label="Content",
        style=discord.TextStyle.long,
        min_length=1,
        max_length=2000,
        placeholder="The content of this tag."
    )

    async def on_submit(self, itx: Interaction) -> None:
        name = str(self.name)
        content = str(self.content)

        async with itx.client.pool.acquire() as conn:
            await create_tag(itx, name, content, conn)


class MatchView(discord.ui.View):
    # ! Possibility of failing due to empty options on super init
    def __init__(
        self,
        itx: Interaction,
        options: list[discord.SelectOption]
    ) -> None:
        super().__init__(timeout=45.0)

        self.children[0].options = options
        self.itx = itx
        self.tag: Optional[str] = None

    async def on_timeout(self) -> None:
        self.children[0].disabled = True
        with contextlib.suppress(discord.NotFound):
            await self.itx.edit_original_response(view=self)

    async def interaction_check(self, itx: Interaction) -> bool:
        if itx.user.id == self.itx.user.id:
            return True
        await itx.response.send_message("This is not for you")
        return False

    @discord.ui.select(placeholder="Select what tag you meant")
    async def call(self, itx: Interaction, select: discord.ui.Select) -> None:
        await self.itx.delete_original_response()

        self.tag = select.values[0]
        self.itx = itx
        self.stop()


async def partial_match(
    itx: Interaction,
    word_input: str,
    conn: Connection
) -> list[sqlite3.Row]:
    query = (
        """
        SELECT name
        FROM tags
        WHERE LOWER(name) LIKE '%' || ? || '%'
        COLLATE NOCASE
        ORDER BY INSTR(name, ?)
        LIMIT 10
        """
    )

    word_input = word_input.lower()
    args = (word_input, word_input)

    return await conn.fetchall(query, args)


async def owned_partial_match(
    itx: Interaction,
    word_input: str,
    conn: Connection
) -> list[sqlite3.Row]:
    query = (
        """
        SELECT name
        FROM tags
        WHERE ownerID = ? AND LOWER(name) LIKE '%' || ? || '%'
        COLLATE NOCASE
        ORDER BY INSTR(name, ?)
        LIMIT 10
        """
    )

    word_input = word_input.lower()
    args = (itx.user.id, word_input, word_input)

    return await conn.fetchall(query, args)


async def transform(
    itx: Interaction,
    value: str,
    owned_tags_only: Optional[bool] = False
) -> tuple[bool, Interaction]:
    if owned_tags_only:
        meth = (
            partial_match if itx.client.is_owner(itx.user)
            else owned_partial_match
        )
    else:
        meth = partial_match

    async with itx.client.pool.acquire() as conn:
        tag_results = await meth(itx, value, conn)

    length = len(tag_results)
    if not length:
        raise FailingConditionalError(TAG_MISSING)

    if length == 1:
        return tag_results[0][0], itx

    options = [discord.SelectOption(label=tag) for (tag,) in tag_results]
    view = MatchView(itx, options)

    content = (
        f"**{length}** results for {value!r} were found, select one below."
    )
    await itx.response.send_message(content, view=view)
    await view.wait()

    if view.tag:
        return view.tag, view.itx

    raise FailingConditionalError("You didn't select a tag in time.")


@app_commands.context_menu(name="Tag Message")
async def create_tag_menu(itx: Interaction, message: discord.Message) -> None:
    cleaned = message.clean_content

    if message.attachments:
        attachments = "\n".join(
            attachment.url for attachment in message.attachments
        )
        cleaned = f"{cleaned}\n{attachments}" if cleaned else attachments

    elif not cleaned:
        return await itx.response.send_message(
            "This message has no content to tag."
        )

    if len(cleaned) > 2000:
        return await itx.response.send_message(MAX_CHARACTERS_REACHED)

    modal = TagMakeModal()
    modal.content.default = cleaned
    await itx.response.send_modal(modal)


async def all_tag_autocomplete(
    itx: Interaction,
    current: str
) -> list[app_commands.Choice[str]]:
    query = (
        """
        SELECT name
        FROM tags
        WHERE name LIKE '%' || ? || '%'
        COLLATE NOCASE
        ORDER BY INSTR(name, ?)
        LIMIT 25
        """
    )

    current = current.lower()
    async with itx.client.pool.acquire() as conn:
        rows = await conn.fetchall(query, (current, current))
    return [app_commands.Choice(name=row, value=row) for (row,) in rows]


async def all_owned_tag_autocomplete(
    itx: Interaction,
    current: str
) -> list[app_commands.Choice[str]]:
    query = (
        """
        SELECT name
        FROM tags
        WHERE ownerID = ? AND LOWER(name) LIKE '%' || ? || '%'
        COLLATE NOCASE
        ORDER BY INSTR(name, ?)
        LIMIT 25
        """
    )

    current = current.lower()
    async with itx.client.pool.acquire() as conn:
        all_tags = await conn.fetchall(query, (itx.user.id, current, current))

    return [app_commands.Choice(name=tag, value=tag) for (tag,) in all_tags]


async def get_tag_content(name: str, conn: Connection) -> str:
    res, = await conn.fetchone(
        "SELECT content FROM tags WHERE name = ?", (name,)
    )
    return res


async def create_tag(
    itx: Interaction,
    name: str,
    content: str,
    conn: Connection
) -> None:
    query = "INSERT INTO tags (name, content, ownerID) VALUES (?, ?, ?)"

    tr = conn.transaction()
    await tr.start()

    try:
        await conn.execute(query, (name, content, itx.user.id))
    except sqlite3.IntegrityError:
        await tr.rollback()
        await respond(itx, TAG_ALREADY_EXISTS)
    except Exception as e:
        itx.client.log_exception(e)
        await tr.rollback()
        await respond(itx, "Could not create tag.")
    else:
        await tr.commit()
        await respond(itx, f"Tag {name!r} successfully created.")


tag = app_commands.Group(
    name="tag",
    description="Tag text for later retrieval"
)


@tag.command(description=tag.description)
@app_commands.describe(name="The tag to retrieve.")
@app_commands.autocomplete(name=all_tag_autocomplete)
async def get(itx: Interaction, name: TAG_DELIMITER) -> None:
    async with itx.client.pool.acquire() as conn:
        name, itx = await transform(itx, name)
        content = await get_tag_content(name, conn)

        await itx.response.send_message(content)

        # update the usage
        await conn.execute(
            "UPDATE tags SET uses = uses + 1 WHERE name = $0", name
        )


@tag.command(description="Create a new tag owned by you")
@app_commands.describe(name="The tag name.", content="The tag content.")
async def create(
    itx: Interaction,
    name: TAG_DELIMITER,
    content: CONTENT_DELIMITER
) -> None:

    async with itx.client.pool.acquire() as conn:
        await create_tag(itx, name, content, conn)


@tag.command(description="Interactively make your own tag")
@app_commands.describe(name="The name of this tag.")
async def make(
    itx: Interaction,
    name: TAG_DELIMITER
) -> Optional[Union[discord.WebhookMessage, discord.Message]]:

    def check(msg: discord.Message) -> bool:
        return (
            msg.author.id == itx.user.id and
            msg.channel.id == itx.channel.id
        )

    await itx.response.send_message(
        "What about the tag's content?\n"
        "-# Type `abort` to end this process."
    )

    try:
        msg = await itx.client.wait_for("message", check=check, timeout=180.0)
    except TimeoutError:
        return await itx.followup.send("You took too long.")

    if msg.content == "abort":
        return await msg.reply("Aborted.")
    elif msg.content:
        cleaned = msg.clean_content
    else:
        # fast path I guess?
        cleaned = msg.content

    if msg.attachments:
        attachments = "\n".join(
            attachment.url for attachment in msg.attachments
        )
        cleaned = f"{cleaned}\n{attachments}" if cleaned else attachments

    if len(cleaned) > 2000:
        return await msg.reply(MAX_CHARACTERS_REACHED)

    async with itx.client.pool.acquire() as conn:
        await create_tag(itx, name, cleaned, conn)


@tag.command(description="Modifiy an existing tag that you own")
@app_commands.describe(
    name="The tag to edit.",
    content="The new content of the tag. If not given, a modal is opened."
)
@app_commands.autocomplete(name=all_owned_tag_autocomplete)
async def edit(
    itx: Interaction,
    name: TAG_DELIMITER,
    content: Optional[CONTENT_DELIMITER] = None
) -> None:
    if content is None:
        async with itx.client.pool.acquire() as conn:
            name, itx = await transform(itx, name, owned_tags_only=True)
            query = "SELECT content FROM tags WHERE name LIKE '%' || ? || '%'"
            tag_content, = await conn.fetchone(query, (name,))

        modal = TagEditModal(tag_content)
        await itx.response.send_modal(modal)
        await modal.wait()

        itx = modal.itx
        content = modal.text

    # ! Don't remove as it can skip to here if content not empty
    if itx.client.is_owner(itx.user):
        clause = "WHERE name = ?"
        args = (content, name)
    else:
        clause = "WHERE name = ? AND ownerID = ?"
        args = (content, name, itx.user.id)

    query = f"UPDATE tags SET content = ? {clause} RETURNING name"
    async with itx.client.pool.acquire() as conn, conn.transaction():
        val = await conn.fetchone(query, args)

    if val is None:
        return await itx.response.send_message(TAG_NOT_FOUND)

    await itx.response.send_message(
        f"Successfully edited tag named {name!r}."
    )


@tag.command(description="Remove a tag that you own")
@app_commands.describe(name="The tag to remove.")
@app_commands.autocomplete(name=all_owned_tag_autocomplete)
async def remove(itx: Interaction, name: TAG_DELIMITER) -> None:
    name, itx = await transform(itx, name, owned_tags_only=True)

    query = "DELETE FROM tags WHERE name = ? RETURNING rowid, name"
    async with itx.client.pool.acquire() as conn, conn.transaction():
        deleted_info = await conn.fetchone(query, (name,))

    if deleted_info is None:
        return await itx.response.send_message(TAG_MISSING)

    tag_id, name = deleted_info
    await itx.response.send_message(
        f"Deleted tag named {name!r} (ID {tag_id})."
    )


@tag.command(description="Remove a tag that you own by its ID")
@app_commands.describe(tag_id="The internal tag ID to delete.")
@app_commands.rename(tag_id="id")
async def remove_id(itx: Interaction, tag_id: int) -> None:

    clause = "rowid = $0"
    if itx.client.is_owner(itx.user):
        args = (tag_id,)
    else:
        args = (tag_id, itx.user.id)
        clause = f"{clause} AND ownerID = $1"

    query = f"DELETE FROM tags WHERE {clause} RETURNING rowid, name"
    async with itx.client.pool.acquire() as conn, conn.transaction():
        deleted_info = await conn.fetchone(query, *args)

    if deleted_info is None:
        return await itx.response.send_message(TAG_NOT_FOUND)

    rowid, name = deleted_info
    await itx.response.send_message(
        f"Deleted tag named {name!r} (ID {rowid})."
    )


async def _send_tag_info(
    itx: Interaction,
    tag_name: str,
    row: sqlite3.Row
) -> None:
    """Expects row in this format: rowid, uses, ownerID, time_created"""

    embed = discord.Embed(colour=discord.Colour.blurple())
    embed.set_footer(text="Tag created")

    rowid, uses, owner_id, time_created = row

    embed.title = tag_name
    embed.timestamp = datetime.fromtimestamp(time_created, tz=timezone.utc)

    user = (
        itx.client.get_user(owner_id)
        or (await itx.client.fetch_user(owner_id))
    )
    embed.set_author(name=user.name, icon_url=user.display_avatar.url)
    embed.add_field(name="Owner", value=f"<@{owner_id}>")
    embed.add_field(name="Uses", value=f"{uses:,}")

    query = (
        """
        SELECT (
            SELECT COUNT(*)
            FROM tags second
            WHERE (second.uses, second.rowid) >= (first.uses, first.rowid)
        ) AS rank,
        (
            SELECT COUNT(*)
            FROM tags
        ) AS total_tags
        FROM tags first
        WHERE first.rowid = $1
        """
    )

    async with itx.client.pool.acquire() as conn:
        rank, total_tags = await conn.fetchone(query, rowid)
    embed.add_field(name="Rank", value=f"{rank:,} / {total_tags:,}")

    await itx.response.send_message(embed=embed)


@tag.command(description="Retrieve info about a tag")
@app_commands.describe(name="The tag to retrieve information for.")
@app_commands.autocomplete(name=all_tag_autocomplete)
async def info(itx: Interaction, name: TAG_DELIMITER) -> None:
    query = (
        """
        SELECT rowid, uses, ownerID, time_created
        FROM tags
        WHERE name = ?
        """
    )

    async with itx.client.pool.acquire() as conn:
        name, itx = await transform(itx, name)
        record = await conn.fetchone(query, (name,))

    await _send_tag_info(itx, name, record)


@tag.command(description="Remove all tags made by a user")
@app_commands.describe(user="The user to remove all tags of.")
async def purge(itx: Interaction, user: Optional[discord.User]) -> None:
    user = user or itx.user

    if (itx.user.id != user.id) and (not itx.client.is_owner(itx.user)):
        return await itx.response.send_message(
            "You can only delete tags you own."
        )

    query = "SELECT COUNT(*) FROM tags WHERE ownerID = $0"
    async with itx.client.pool.acquire() as conn:
        count, = await conn.fetchone(query, user.id)

    if not count:
        return await itx.response.send_message(f"{user.name} has no tags.")

    message = (
        f"Upon approval, **{count}** tag(s) by {user.name} will be deleted."
    )
    val = await process_confirmation(itx, message)

    if not val:
        return

    query = "DELETE FROM tags WHERE ownerID = $0"
    async with itx.client.pool.acquire() as conn, conn.transaction():
        await conn.execute(query, user.id)

    await itx.followup.send(f"Removed all tags made by {user.name}.")


async def reusable_paginator_via(
    itx: Interaction,
    rows: tuple[str, int],
    em: discord.Embed
) -> None:
    """Can be used when you have a tuple containing the tag name and rowid."""

    total_pages = PaginationSimple.compute_total_pages(len(rows), PAGE_SIZE)
    paginator = PaginationSimple(itx, total_pages)

    async def get_page_part() -> discord.Embed:
        offset = (paginator.index - 1) * PAGE_SIZE

        em.description = "\n".join(
            f"{index}. {tag_name} (ID: {tag_id})"
            for index, (tag_name, tag_id) in enumerate(
                rows[offset:offset+PAGE_SIZE],
                start=offset+1
            )
        )

        return em.set_footer(
            text=f"Page {paginator.index} of {paginator.total_pages}"
        )

    paginator.get_page = get_page_part
    await paginator.navigate()


@tag.command(description="Search for a tag")
@app_commands.describe(query="The tag to search for.")
async def search(itx: Interaction, query: TAG_DELIMITER) -> None:

    sql = (
        """
        SELECT name, rowid
        FROM tags
        WHERE name LIKE '%' || ? || '%'
        COLLATE NOCASE
        ORDER BY INSTR(name, ?)
        LIMIT 60
        """
    )

    query = query.lower()
    async with itx.client.pool.acquire() as conn:
        rows = await conn.fetchall(sql, (query, query))

    if not rows:
        return await itx.response.send_message("No matching tags found.")

    em = discord.Embed(colour=discord.Colour.blurple())
    await reusable_paginator_via(itx, rows, em)


@tag.command(description="Transfer a tag to another member")
@app_commands.describe(
    tag="The tag to transfer.",
    user="Who to transfer the tag to."
)
@app_commands.autocomplete(tag=all_owned_tag_autocomplete)
async def transfer(
    itx: Interaction,
    user: discord.User,
    tag: TAG_DELIMITER
) -> None:
    if user.bot and (not itx.client.is_owner(itx.user)):
        return await itx.response.send_message(
            "You cannot transfer tags to bots."
        )

    query = "UPDATE tags SET ownerID = ? WHERE name = ? RETURNING rowid"
    async with itx.client.pool.acquire() as conn, conn.transaction():
        tag, itx = await transform(itx, tag, owned_tags_only=True)
        ret = await conn.fetchone(query, (user.id, tag))

    if ret is None:
        return await itx.response.send_message(TAG_MISSING)
    await itx.response.send_message(
        f"Tag named {tag!r} now belongs to {user.name}."
    )


@tag.command(name="all", description="List all tags ever made")
async def all_tags(itx: Interaction) -> None:

    query = "SELECT name, rowid FROM tags ORDER BY name"
    async with itx.client.pool.acquire() as conn:
        rows = await conn.fetchall(query)

    if not rows:
        return await itx.response.send_message("No tags exist!")

    em = discord.Embed(colour=discord.Colour.blurple())
    await reusable_paginator_via(itx, rows, em)


@tag.command(name="list", description="Show tags created by a specific user")
@app_commands.describe(user="The user to show the tags of.")
async def _list(itx: Interaction, user: Optional[discord.User]) -> None:
    user = user or itx.user

    query = "SELECT name, rowid FROM tags WHERE ownerID = $0 ORDER BY name"
    async with itx.client.pool.acquire() as conn:
        rows = await conn.fetchall(query, user.id)

    if not rows:
        return await itx.response.send_message(f"{user.name} has no tags.")

    em = discord.Embed(colour=discord.Colour.blurple())
    em.set_author(name=user.display_name, icon_url=user.display_avatar.url)
    await reusable_paginator_via(itx, rows, em)


@tag.command(description="Display a random tag")
async def random(itx: Interaction) -> None:
    query = "SELECT name, content FROM tags ORDER BY RANDOM() LIMIT 1"
    async with itx.client.pool.acquire() as conn:
        row = await conn.fetchone(query)

    if row is None:
        return await itx.response.send_message("No tags exist yet!")

    name, content = row

    await itx.response.send_message(content)


async def global_stats(itx: Interaction) -> None:
    top_tags_query = (
        """
        SELECT
            name,
            uses,
            COUNT(*) OVER () AS "Count",
            SUM(uses) OVER () AS "Total Uses"
        FROM tags
        ORDER BY uses DESC
        LIMIT 3
        """
    )

    top_data_query = (
        """
        WITH top_users AS (
            SELECT
                'user' AS source,
                userID AS identifier,
                SUM(cmd_count) AS metric
            FROM command_uses
            WHERE cmd_name LIKE '%tag%'
            GROUP BY userID
            ORDER BY cmd_count DESC
            LIMIT 3
        ),
        top_creators AS (
            SELECT
                'creator' AS source,
                ownerID AS identifier,
                COUNT(*) AS metric
            FROM tags
            GROUP BY ownerID
            ORDER BY COUNT(*) DESC
            LIMIT 3
        )
        SELECT source, identifier, metric FROM top_users
        UNION ALL
        SELECT source, identifier, metric FROM top_creators
        """
    )

    async with itx.client.pool.acquire() as conn:
        top_tags = await conn.fetchall(top_tags_query)
        top_data = await conn.fetchall(top_data_query)

    top_users = [row[1:] for row in top_data if row[0] == "user"]
    top_creators = [row[1:] for row in top_data if row[0] == "creator"]

    em = discord.Embed(title="Tag Stats", colour=discord.Colour.blurple())
    if not top_tags:
        em.description = "No tag stats to share."
    else:
        data = top_tags[0]
        em.description = f"{data[-2]:,} tags, {data[-1]:,} uses"

    if len(top_tags) < 3:
        top_tags.extend(
            (None, None, None, None)
            for _ in range(0, 3 - len(top_tags))
        )

    if len(top_users) < 3:
        top_users.extend(
            (None, None)
            for _ in range(0, 3 - len(top_users))
        )

    if len(top_creators) < 3:
        top_creators.extend(
            (None, None)
            for _ in range(0, 3 - len(top_creators))
        )

    def emojize(seq):
        emoji = 129351  # ord(":first_place:")
        for index, value in enumerate(seq):
            yield chr(emoji + index), value

    em.add_field(
        name="Top Tags",
        inline=False,
        value="\n".join(
            f"{emoji}: {name} ({uses} uses)" if name else f"{emoji}: Nothing!"
            for (emoji, (name, uses, _, _)) in emojize(top_tags)
        )
    ).add_field(
        name="Top Tag Users",
        inline=False,
        value="\n".join(
            f"{emoji}: <@{author_id}> ({uses} times)"
            if author_id
            else f"{emoji}: No one!"
            for (emoji, (author_id, uses)) in emojize(top_users)
        )
    ).add_field(
        name="Top Tag Creators",
        inline=False,
        value="\n".join(
            f"{emoji}: <@{owner_id}> ({count} tags)"
            if owner_id
            else f"{emoji}: No one!"
            for (emoji, (owner_id, count)) in emojize(top_creators)
        )
    ).set_footer(text="These stats are global.")

    await itx.response.send_message(embed=em)


async def member_stats(itx: Interaction, user: discord.abc.User) -> None:
    e = discord.Embed(colour=discord.Colour.blurple())
    e.set_author(name=str(user), icon_url=user.display_avatar.url)
    e.set_footer(text="These stats are user-specific.")

    query = (
        """
        WITH aggregate AS (
            SELECT
                COUNT(*) AS owned_tags,
                COALESCE(SUM(uses), 0) AS owned_tag_uses
            FROM tags
            WHERE ownerID = $0
        )

        SELECT
            CAST(TOTAL(cmd_count) AS INTEGER) AS total_cmd_count,
            aggregate.owned_tags,
            COALESCE(aggregate.owned_tag_uses, 0)
        FROM command_uses
        CROSS JOIN aggregate
        WHERE userID = $0 AND cmd_name LIKE '%tag%'
        """
    )

    second_query = (
        """
        SELECT name, uses
        FROM tags
        WHERE ownerID = $0
        ORDER BY uses DESC
        LIMIT 3
        """
    )

    async with itx.client.pool.acquire() as conn:
        count, owned_tags, owned_uses = await conn.fetchone(query, user.id)
        records = await conn.fetchall(second_query, user.id)

    e.add_field(name="Owned Tags", value=owned_tags).add_field(
        name="Owned Tag Uses", value=owned_uses
    ).add_field(name="Tag Command Uses", value=f"{count:,}")

    # fill with data to ensure that we have a minimum of 3
    if len(records) < 3:
        records.extend((None,) * 2 for _ in range(0, 3 - len(records)))

    emoji = 129351
    for offset, (name, uses) in enumerate(records):
        if name:
            value = f"{name} ({uses} uses)"
        else:
            value = "Nothing!"

        e.add_field(name=f"{chr(emoji + offset)} Owned Tag", value=value)

    await itx.response.send_message(embed=e)


@tag.command(description="Show tag statistics globally or for a member")
@app_commands.describe(
    member="The member to get stats about, displays global stats by default."
)
async def stats(itx: Interaction, member: Optional[discord.User]):
    if member:
        return await member_stats(itx, member)
    await global_stats(itx)


exports = BotExports([tag, create_tag_menu])