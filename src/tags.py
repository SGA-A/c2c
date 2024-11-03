import contextlib
import sqlite3
from asyncio import TimeoutError
from datetime import datetime, timezone
from typing import Optional

import discord
from asqlite import Connection
from discord import app_commands

from ._types import BotExports, MaybeInteractionMessage
from .core.bot import Interaction
from .core.errors import FailingConditionalError
from .core.helpers import BaseView, send_prompt
from .core.paginators import PaginationSimple

PROMO = "\n-# Save time by creating a tag from an existing message."
MAX_CHARACTERS_REACHED = f"Tag content cannot exceed 2000 characters.{PROMO}"
TAG_NOT_FOUND = "No such tag exists with that name."
TAG_ALREADY_EXISTS = f"A tag with that name already exists.{PROMO}"
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
            resp = await create_tag(itx, name, content, conn)
        await itx.response.send_message(resp)


class MatchView(BaseView):

    def __init__(
        self,
        itx: Interaction,
        content: str,
        tag_rows: list[sqlite3.Row]
    ) -> None:
        super().__init__(itx, content)
        self.tag: Optional[sqlite3.Row] = None

        # Tag name = row[0]
        self.row_dict: dict[str, sqlite3.Row] = {
            row[0]: row for row in tag_rows
        }

        self.children[0].options = [
            discord.SelectOption(label=row[0])
            for row in tag_rows
        ]

    # Looping over children is unnecessary (only 1 child)
    async def on_timeout(self) -> None:
        self.children[0].disabled = True
        with contextlib.suppress(discord.NotFound):
            await self.itx.edit_original_response(view=self)

    @discord.ui.select(placeholder="Select what tag you meant")
    async def call(self, itx: Interaction, select: discord.ui.Select) -> None:
        self.tag = self.row_dict[select.values[0]]

        for option in select.options:
            option.default = option.value == self.tag

        await self.on_timeout()
        self.stop()

        # This needs to be below the on_timeout call
        self.itx = itx


# Must pass in interaction, see usage for info
async def partial_match(
    _: Interaction,
    word_input: str,
    conn: Connection,
    *extras: tuple[str, ...]
) -> list[sqlite3.Row]:

    extras = ", ".join(extras)
    extras = f", {extras}" if extras else ""

    query = (
        f"""
        SELECT name{extras}
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
    conn: Connection,
    *extras: tuple[str, ...]
) -> list[sqlite3.Row]:

    extras = ", ".join(extras)
    extras = f", {extras}" if extras else ""

    query = (
        f"""
        SELECT name{extras}
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
    owned_tags_only: Optional[bool] = False,
    *extras: tuple[str, ...]
) -> tuple[sqlite3.Row, Interaction]:
    if owned_tags_only:
        meth = (
            partial_match if itx.client.is_owner(itx.user)
            else owned_partial_match
        )
    else:
        meth = partial_match

    async with itx.client.pool.acquire() as conn:
        tag_rows = await meth(itx, value, conn, *extras)

    length = len(tag_rows)
    if not length:
        raise FailingConditionalError(TAG_NOT_FOUND)

    first_row = tag_rows[0]
    if (length == 1) or (first_row[0] == value):
        return first_row, itx

    content = f"{length} results for {value!r} found, select one below."
    view = MatchView(itx, content, tag_rows)

    await itx.response.send_message(content, view=view)

    await view.wait()
    if view.tag:
        return view.tag, view.itx

    raise FailingConditionalError("You didn't select a tag in time.")


@app_commands.context_menu(name="Tag Message")
async def tag_msg_menu(itx: Interaction, message: discord.Message) -> None:
    # Somehow you can use user apps on archived threads?
    # This check helps to avoid the error
    if message.thread and message.thread.archived:
        return

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


async def create_tag(
    itx: Interaction,
    name: str,
    content: str,
    conn: Connection
) -> str:
    query = "INSERT INTO tags (name, content, ownerID) VALUES (?, ?, ?)"

    tr = conn.transaction()
    await tr.start()

    try:
        await conn.execute(query, (name, content, itx.user.id))
    except sqlite3.IntegrityError:
        await tr.rollback()
        return TAG_ALREADY_EXISTS
    except Exception as e:
        itx.client.log_exception(e)
        await tr.rollback()
        return "Could not create tag."
    else:
        await tr.commit()
        return f"Tag {name!r} successfully created."


tag_group = app_commands.Group(
    name="tag",
    description="Tag text for later retrieval"
)


@tag_group.command(description=tag_group.description)
@app_commands.describe(name="The tag to retrieve.")
async def get(itx: Interaction, name: TAG_DELIMITER) -> None:
    tag_row, itx = await transform(itx, name, False, "content")
    await itx.response.send_message(tag_row[-1])

@tag_group.command(description="Create a new tag owned by you")
@app_commands.describe(
    name="The name of this tag.",
    content="The tag content. Starts an interactive session if empty."
)
async def create(
    itx: Interaction,
    name: TAG_DELIMITER,
    content: Optional[CONTENT_DELIMITER],
) -> MaybeInteractionMessage:

    if content:
        async with itx.client.pool.acquire() as conn:
            resp = await create_tag(itx, name, content, conn)
        return await itx.response.send_message(resp)

    def check(msg: discord.Message) -> bool:
        return (
            msg.author.id == itx.user.id and
            msg.channel.id == itx.channel.id
        )

    await itx.response.send_message(
        f"You've named the tag {name!r}. What about its content? "
        f"You can type `abort` to end the process."
    )

    try:
        msg = await itx.client.wait_for("message", check=check, timeout=180.0)
    except TimeoutError:
        return await itx.edit_original_response(content="You took too long.")

    if msg.content == "abort":
        return await msg.reply("Aborted.")
    elif msg.content:
        cleaned = msg.clean_content
    else:
        # Fast path I guess?
        cleaned = msg.content

    if msg.attachments:
        attachments = "\n".join(
            attachment.url for attachment in msg.attachments
        )
        cleaned = f"{cleaned}\n{attachments}" if cleaned else attachments

    if len(cleaned) > 2000:
        return await msg.reply(MAX_CHARACTERS_REACHED)

    async with itx.client.pool.acquire() as conn:
        resp = await create_tag(itx, name, cleaned, conn)
    await msg.reply(resp)


@tag_group.command(description="Modifiy an existing tag that you own")
@app_commands.rename(new_content="content")
@app_commands.describe(name="The tag to edit.")
async def edit(
    itx: Interaction,
    name: TAG_DELIMITER,
    new_content: Optional[CONTENT_DELIMITER]
) -> None:

    owned_unless_dev = not itx.client.is_owner(itx.user)
    ((name, tag_content), itx) = await transform(
        itx, name, owned_unless_dev, "content"
    )

    if new_content is None:
        modal = TagEditModal(title="Edit Tag")
        modal.content.default = tag_content
        await itx.response.send_modal(modal)
        await modal.wait()

        itx = modal.itx
        new_content = modal.text

    if owned_unless_dev:
        clause = "WHERE name = ? AND ownerID = ?"
        args = (new_content, name, itx.user.id)
    else:
        clause = "WHERE name = ?"
        args = (new_content, name)

    query = f"UPDATE tags SET content = ? {clause} RETURNING rowid"
    async with itx.client.pool.acquire() as conn, conn.transaction():
        rowid, = await conn.fetchone(query, args) or (0,)

    if rowid:
        return await itx.response.send_message(
            f"Successfully edited tag named {name!r} (ID {rowid})."
        )

    await itx.response.send_message(TAG_NOT_FOUND)


@tag_group.command(description="Remove a tag that you own")
@app_commands.describe(name="The tag to remove.")
async def remove(itx: Interaction, name: TAG_DELIMITER) -> None:
    ((name,), itx) = await transform(itx, name, owned_tags_only=True)

    # The WHERE ownerID = ? clause not needed because of above func
    query = "DELETE FROM tags WHERE name = ? RETURNING rowid"
    async with itx.client.pool.acquire() as conn, conn.transaction():
        tag_id, = await conn.fetchone(query, (name,)) or (0,)

    if tag_id:
        return await itx.response.send_message(
            f"Deleted tag named {name!r} (ID {tag_id})."
        )

    await itx.response.send_message(TAG_NOT_FOUND)


@tag_group.command(description="Remove a tag that you own by its ID")
@app_commands.describe(tag_id="The internal tag ID to delete.")
@app_commands.rename(tag_id="id")
async def remove_id(itx: Interaction, tag_id: int) -> None:

    if itx.client.is_owner(itx.user):
        args = (tag_id,)
        clause = "rowid = ?"
    else:
        args = (tag_id, itx.user.id)
        clause = "rowid = ? AND ownerID = ?"

    query = f"DELETE FROM tags WHERE {clause} RETURNING name"
    async with itx.client.pool.acquire() as conn, conn.transaction():
        name, = await conn.fetchone(query, args) or ("",)

    if name:
        return await itx.response.send_message(
            f"Deleted tag named {name!r} (ID {tag_id})."
        )

    await itx.response.send_message(
        f"You do not own a tag with ID {tag_id}."
    )


async def _send_tag_info(itx: Interaction, row: sqlite3.Row) -> None:
    """Expects row in this format: name, rowid, uses, ownerID, time_created"""

    embed = discord.Embed(colour=discord.Colour.blurple())
    embed.set_footer(text="Tag created")

    # Unpacking the row
    embed.title, rowid, uses, owner_id, time_created = row

    user = (
        itx.client.get_user(owner_id)
        or (await itx.client.fetch_user(owner_id))
    )
    embed.timestamp = datetime.fromtimestamp(time_created, tz=timezone.utc)
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


@tag_group.command(description="Retrieve info about a tag")
@app_commands.describe(name="The tag to retrieve information for.")
async def info(itx: Interaction, name: TAG_DELIMITER) -> None:

    # I know this retrieves alot of columns but limited to 10 results
    # So this should not be too hefty for the DB to manage
    row, itx = await transform(
        itx, name, False, "rowid", "uses", "ownerID", "time_created"
    )

    await _send_tag_info(itx, row)


@tag_group.command(description="Remove all tags made by a user")
@app_commands.describe(user="The user to remove all tags of.")
async def purge(itx: Interaction, user: Optional[discord.User]) -> None:
    user = user or itx.user

    if (itx.user.id != user.id) and (not itx.client.is_owner(itx.user)):
        return await itx.response.send_message(
            "You can only delete tags you own."
        )

    args = (user.id,)
    query = "SELECT COUNT(*) FROM tags WHERE ownerID = ?"
    async with itx.client.pool.acquire() as conn:
        count, = await conn.fetchone(query, args)

    if not count:
        return await itx.response.send_message(f"{user.name} has no tags.")

    val = await send_prompt(itx, f"Delete **{count}** tag(s) by {user.name}?")
    if not val:
        return

    query = "DELETE FROM tags WHERE ownerID = ?"
    async with itx.client.pool.acquire() as conn, conn.transaction():
        await conn.execute(query, args)

    await itx.followup.send(f"Removed all tags made by {user.name}.")


async def reusable_paginator_via(
    itx: Interaction,
    rows: tuple[str, int],
    e: discord.Embed
) -> None:
    """Can be used when you have a tuple containing the tag name and rowid."""

    total_pages = PaginationSimple.compute_total_pages(len(rows), PAGE_SIZE)
    paginator = PaginationSimple(itx, total_pages)

    async def get_page() -> list[discord.Embed]:
        offset = (paginator.index - 1) * PAGE_SIZE

        e.description = "\n".join(
            f"{index}. {tag_name} (ID: {tag_id})"
            for index, (tag_name, tag_id) in enumerate(
                rows[offset:offset+PAGE_SIZE],
                start=offset+1
            )
        )
        e.set_footer(text=f"Page {paginator.index} of {paginator.total_pages}")
        return [e]

    paginator.get_page = get_page
    await paginator.navigate()


@tag_group.command(description="Search for a tag")
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


@tag_group.command(description="Transfer a tag to another member")
@app_commands.describe(tag="The tag to give.", user="Who to give the tag to.")
async def transfer(
    itx: Interaction,
    user: discord.User,
    tag: TAG_DELIMITER
) -> None:
    if user.bot and (not itx.client.is_owner(itx.user)):
        return await itx.response.send_message(
            "You cannot transfer tags to bots."
        )

    # Only owned tags given to user in transform func
    ((tag,), itx) = await transform(itx, tag, True)  # Tuple in a tuple

    # So WHERE ownerID = ? in query clause is not needed
    query = "UPDATE tags SET ownerID = ? WHERE name = ? RETURNING rowid"
    async with itx.client.pool.acquire() as conn, conn.transaction():
        ret = await conn.fetchone(query, (user.id, tag))

    if ret is None:
        return await itx.response.send_message(TAG_NOT_FOUND)

    await itx.response.send_message(
        f"Tag named {tag!r} now belongs to {user.name}."
    )


@tag_group.command(name="all", description="List all tags ever made")
async def fetch_all(itx: Interaction) -> None:

    query = "SELECT name, rowid FROM tags ORDER BY name"
    async with itx.client.pool.acquire() as conn:
        rows = await conn.fetchall(query)

    if not rows:
        return await itx.response.send_message("No tags exist yet.")

    em = discord.Embed(colour=discord.Colour.blurple())
    await reusable_paginator_via(itx, rows, em)


@tag_group.command(name="list", description="Show tags made by a user")
@app_commands.describe(user="Whose tags to display.")
async def fetch_list(itx: Interaction, user: Optional[discord.User]) -> None:
    user = user or itx.user

    query = "SELECT name, rowid FROM tags WHERE ownerID = ? ORDER BY name"
    async with itx.client.pool.acquire() as conn:
        rows = await conn.fetchall(query, (user.id,))

    if not rows:
        return await itx.response.send_message(f"{user.name} has no tags.")

    em = discord.Embed(colour=discord.Colour.blurple())
    em.set_author(name=user.display_name, icon_url=user.display_avatar.url)
    await reusable_paginator_via(itx, rows, em)


@tag_group.command(description="Display a random tag")
async def random(itx: Interaction) -> None:
    query = "SELECT content FROM tags ORDER BY RANDOM() LIMIT 1"
    async with itx.client.pool.acquire() as conn:
        content, = await conn.fetchone(query) or ("No tags exist yet.",)

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
        name="Top Tags Used",
        inline=False,
        value="\n".join(
            f"{emoji}: {name} ({uses} uses)" if name else f"{emoji}: Nothing!"
            for (emoji, (name, uses, _, _)) in emojize(top_tags)
        )
    )

    em.add_field(
        name="Top Tag Command Users",
        inline=False,
        value="\n".join(
            f"{emoji}: <@{author_id}> ({uses} times)"
            if author_id
            else f"{emoji}: No one!"
            for (emoji, (author_id, uses)) in emojize(top_users)
        )
    )

    em.add_field(
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
        value = f"{name} ({uses} uses)" if name else "Nothing!"
        e.add_field(name=f"{chr(emoji + offset)} Owned Tag", value=value)

    await itx.response.send_message(embed=e)


@tag_group.command(description="Show tag statistics globally or for a member")
@app_commands.describe(member="Whose stats to see, or display global stats.")
async def stats(itx: Interaction, member: Optional[discord.User]) -> None:
    if member:
        return await member_stats(itx, member)
    await global_stats(itx)


@get.autocomplete("name")
@info.autocomplete("name")
async def all_tag_autocomplete(
    itx: Interaction,
    current: str
) -> list[app_commands.Choice[str]]:

    async with itx.client.pool.acquire() as conn:
        all_tags = await partial_match(itx, current, conn)

    return [app_commands.Choice(name=tag, value=tag) for (tag,) in all_tags]


@edit.autocomplete("name")
@remove.autocomplete("name")
@transfer.autocomplete("tag")
async def owned_tag_autocomplete(
    itx: Interaction,
    current: str
) -> list[app_commands.Choice[str]]:

    async with itx.client.pool.acquire() as conn:
        owned_tags = await owned_partial_match(itx, current, conn)

    return [app_commands.Choice(name=tag, value=tag) for (tag,) in owned_tags]


exports = BotExports([tag_group, tag_msg_menu])