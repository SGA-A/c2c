import asyncio
import sqlite3
import datetime
from typing import (
    Annotated, 
    Optional, 
    Callable
)

import discord
from discord import app_commands
from discord.ext import commands
from asqlite import ProxiedConnection as asqlite_Connection

from .core.helpers import membed
from .core.constants import APP_GUILDS_IDS
from .core.paginator import PaginationSimple
from .core.views import Confirm


TAG_NOT_FOUND_SIMPLE_RESPONSE = "Tag not found, it may have been deleted when you called the command."
TAG_NOT_FOUND_RESPONSE = (
    "Could not find any tag with these properties.\n"
    "- You can't modify the tag if it doesn't belong to you.\n"
    "- You also can't modify a tag that doesn't exist, obviously."
)


class TagName(commands.clean_content):
    def __init__(self, *, lower: bool = False) -> None:
        self.lower: bool = lower
        super().__init__()

    async def convert(self, ctx: commands.Context, argument: str) -> str:
        converted = await super().convert(ctx, argument)
        lower = converted.lower().strip()

        if not lower:
            raise commands.BadArgument('Missing tag name.')

        if len(lower) > 80:
            raise commands.BadArgument('Tag name is a maximum of 80 characters.')

        first_word, _, _ = lower.partition(' ')

        # get tag command.
        root: commands.GroupMixin = ctx.bot.get_command('tag')  # type: ignore
        if first_word in root.all_commands:
            raise commands.BadArgument('This tag name starts with a reserved word.')

        return converted.strip() if not self.lower else lower


class TagEditModal(discord.ui.Modal, title='Edit Tag'):
    content = discord.ui.TextInput(
        label='Tag Content', 
        required=True, 
        style=discord.TextStyle.long, 
        min_length=1, 
        max_length=2000
    )

    def __init__(self, text: str) -> None:
        super().__init__()
        self.content.default = text

    async def on_submit(self, interaction: discord.Interaction) -> None:
        self.interaction = interaction
        self.text = str(self.content)
        self.stop()


class TagMakeModal(discord.ui.Modal, title='Create New Tag'):
    name = discord.ui.TextInput(
        label='Name', 
        required=True, 
        max_length=100, 
        min_length=1, 
        placeholder="The name of this tag."
    )
    
    content = discord.ui.TextInput(
        label='Content', 
        required=True, 
        style=discord.TextStyle.long, 
        min_length=1, 
        max_length=2000,
        placeholder="The content of this tag."
    )

    def __init__(
        self, 
        cog, 
        ctx: commands.Context, 
        conn: asqlite_Connection
    ) -> None:

        super().__init__()
        self.cog: Tags = cog
        self.ctx = ctx
        self.conn = conn

    async def on_submit(self, interaction: discord.Interaction) -> None:
        name = str(self.name)
        try:
            name = await TagName().convert(self.ctx, name)
        except commands.BadArgument as e:
            return await interaction.response.send_message(embed=membed(str(e)), ephemeral=True)
        
        if self.cog.is_tag_being_made(name):
            return await interaction.response.send_message(
                embed=membed('This tag is already being made by someone else.'), 
                ephemeral=True
            )

        self.ctx.interaction = interaction
        content = str(self.content)
        if len(content) > 2000:
            return await interaction.response.send_message(
                embed=membed('Tag content must be a maximum of 2000 characters.'), 
                ephemeral=True
            )
        
        await self.cog.create_tag(self.ctx, name, content, conn=self.conn)


async def send_boilerplate_confirm(ctx: commands.Context, custom_description: str) -> bool:
    confirm = Confirm(controlling_user=ctx.author.id)

    confirmation = membed(custom_description)
    confirmation.title = "Pending Confirmation"
    msg = await ctx.send(embed=confirmation, view=confirm)
    
    await confirm.wait()
    if confirm.value is None:
        for item in confirm.children:
            item.disabled = True

        confirmation.title = "Timed out"
        confirmation.description = f"~~{confirmation.description}~~"
        confirmation.colour = discord.Colour.brand_red()
    
    await msg.edit(embed=confirmation, view=confirm)
    return confirm.value


class MatchWord(discord.ui.Button):
    """
    Represents a button in the user interface for a single word.

    It is a generic button that, upon clicked, returns the word pressed for later use.
    """
    
    def __init__(self, word: str) -> None:
        super().__init__(label=word)

    async def callback(self, interaction: discord.Interaction) -> None:
        self.view.chosen_word = self.label
        self.view.stop()

        if hasattr(self.view, "interaction"):
            self.view.interaction = interaction


class Tags(commands.Cog):

    def __init__(self, bot: commands.Bot) -> None:
        
        self.bot: commands.Bot = bot

        # ownerID: set(name)
        self._reserved_tags_being_made: set[str] = set()

    async def partial_match_for(
        self,
        ctx: commands.Context, 
        word_input: str, 
        tag_results: list[sqlite3.Row],
        match_view: Optional[discord.ui.View] = None
    ) -> None | str:
        """
        If the user types part of an name, get the tag name and its content indicated.

        This implementation is similar to the implementation for economy item matching, but the 
        slight differences meant a polymorphised version had to be made.

        This will only return the tag name, not its content.

        This does not consider whether or not the invoker actually owns this tag.

        This is known as partial matching for words.
        """

        length = len(tag_results)
        if not length:
            await ctx.send(
                ephemeral=True,
                embed=membed("No tag found with this pattern. Check the spelling.")
            )
            return
        
        if length == 1:
            return tag_results[0][0]

        match_view = match_view or discord.ui.View(timeout=15.0)
        match_view.chosen_word = 0  # default is a falsey value

        for resulting_word in tag_results:
            match_view.add_item(MatchWord(word=resulting_word[0]))
        
        msg = await ctx.send(
            view=match_view,
            embed=membed(
                "There is more than one tag with that name pattern.\n"
                "Select one of the following tags:"
            ).set_author(name=f"Search: {word_input}", icon_url=ctx.author.display_avatar.url)
        )

        await match_view.wait()
        await msg.delete()

        if match_view.chosen_word:
            return match_view.chosen_word

        await ctx.send(embed=membed("No result selected, cancelled this request."))
        return None

    async def partial_match_including_interaction(
        self,
        ctx: commands.Context, 
        word_input: str, 
        tag_results: list[sqlite3.Row]
    ) -> tuple[None | str, discord.Interaction]:
        """
        Same as `partial_match_for()`, but when a button is clicked, return the interaction associated with it.

        ## Returns
        A tuple containing the actual value and the interaction created.
        """

        mv = discord.ui.View(timeout=15.0)
        mv.interaction = None

        ret = await self.partial_match_for(ctx, word_input, tag_results, mv)
        return ret, mv.interaction

    async def non_owned_partial_matching(
        self, 
        ctx: commands.Context, 
        word_input: str, 
        conn: asqlite_Connection,
        meth: Optional[Callable] = None
    ):
        """Partial matching for every existing tag"""

        tag_names = await conn.fetchall(
            """
            SELECT name
            FROM tags
            WHERE LOWER(name) LIKE LOWER($0) 
            LIMIT 10
            """, f"%{word_input}%"
        )

        meth = meth or self.partial_match_for
        name = await meth(ctx, word_input, tag_results=tag_names)
        return name

    async def owned_partial_matching(
        self, 
        ctx: commands.Context, 
        word_input: str, 
        conn: asqlite_Connection,
        meth: Optional[Callable] = None
    ) -> tuple | str | None:
        """Partial matching for tags that are owned by the invoker"""

        tag_names = await conn.fetchall(
            """
            SELECT name
            FROM tags
            WHERE ownerID = $0 AND LOWER(name) LIKE LOWER($1)
            LIMIT 10
            """, ctx.author.id, f"%{word_input}%", 
        )

        meth = meth or self.partial_match_for
        return await meth(ctx, word_input, tag_results=tag_names)

    async def non_aliased_tag_autocomplete(self, _: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        
        async with self.bot.pool.acquire() as conn:
    
            query = (
                """
                SELECT name
                FROM tags
                WHERE LOWER(name) LIKE '%' || $0 || '%'
                ORDER BY name DESC
                LIMIT 12
                """
            )

            results: list[tuple[str]] = await conn.fetchall(query, current.lower())
            return [app_commands.Choice(name=a, value=a) for a, in results]
        
    async def owned_non_aliased_tag_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        
        async with self.bot.pool.acquire() as conn:

            query = (
                """
                SELECT name
                FROM tags
                WHERE ownerID = $0 AND LOWER(name) LIKE '%' || $1 || '%'
                ORDER BY name DESC
                LIMIT 12
                """
            )
            
            all_tags: list[tuple[str]] = await conn.fetchall(query, interaction.user.id, current.lower())
            return [app_commands.Choice(name=tag, value=tag) for tag, in all_tags]


    async def get_tag_content(self, name: str, conn: asqlite_Connection):
        
        res = await conn.fetchone(
            """
            SELECT content
            FROM tags
            WHERE LOWER(name) = $0
            """, name.lower()
        )

        if res is None:
            raise RuntimeError(TAG_NOT_FOUND_SIMPLE_RESPONSE)

        return res[0]

    async def create_tag(
            self, 
            ctx: commands.Context, 
            name: str, 
            content: str, 
            conn: asqlite_Connection
        ) -> None:

        query = (
            """
            INSERT INTO tags (name, content, ownerID, created_at)
            VALUES ($0, $1, $2, $3)
            """
        )

        # since I'm checking for the exception type and acting on it, I need
        # to use the manual transaction blocks

        tr = conn.transaction()
        await tr.start()
        timestamp = datetime.datetime.now(tz=datetime.timezone.utc).timestamp()

        try:
            await conn.execute(query, name, content, ctx.author.id, timestamp)
        except sqlite3.IntegrityError:
            await tr.rollback()
            await ctx.send(embed=membed(f"A tag named {name!r} already exists."))
        except Exception as e:
            print(e)
            await tr.rollback()
            await ctx.send(embed=membed("Could not create tag."))
        else:
            await tr.commit()
            await ctx.send(embed=membed(f'Tag {name!r} successfully created.'))

    def is_tag_being_made(self, name: str) -> bool:
        return name.lower() in self._reserved_tags_being_made

    def add_in_progress_tag(self, name: str) -> None:
        self._reserved_tags_being_made.add(name.lower())

    def remove_in_progress_tag(self, name: str) -> None:
        self._reserved_tags_being_made.discard(name.lower())
            
    @commands.hybrid_group(description="Tag text for later retrieval", fallback='get')
    @app_commands.guilds(*APP_GUILDS_IDS)
    @app_commands.describe(name='The tag to retrieve.')
    @app_commands.autocomplete(name=non_aliased_tag_autocomplete)
    async def tag(self, ctx: commands.Context, *, name: str):
        async with self.bot.pool.acquire() as conn:
            
            name = await self.non_owned_partial_matching(ctx, name, conn)
            if name is None:
                return

            try:
                content = await self.get_tag_content(name, conn)
            except RuntimeError as r:
                return await ctx.send(embed=membed(r))

            await ctx.send(
                content=content, 
                reference=ctx.message.reference
            )

            # update the usage
            await conn.execute("UPDATE tags SET uses = uses + 1 WHERE name = $0", name)
    
    @tag.command(description="Create a new tag owned by you", aliases=('add',))
    @app_commands.guilds(*APP_GUILDS_IDS)
    @app_commands.describe(name='The tag name.', content='The tag content.')
    async def create(
        self, 
        ctx: commands.Context, 
        name: Annotated[str, TagName], 
        *, 
        content: Annotated[str, commands.clean_content]
    ) -> discord.Message | None:

        if self.is_tag_being_made(name):
            return await ctx.send(embed=membed('This tag is currently being made by someone.'))

        if len(content) > 2000:
            return await ctx.send(embed=membed('Tag content is a maximum of 2000 characters.'))

        async with self.bot.pool.acquire() as conn:
            await self.create_tag(ctx, name, content, conn=conn)
    
    @tag.command(description="Interactively make your own tag", ignore_extra=True)
    @app_commands.guilds(*APP_GUILDS_IDS)
    async def make(self, ctx: commands.Context):

        async with self.bot.pool.acquire() as conn:

            if ctx.interaction is not None:
                modal = TagMakeModal(self, ctx, conn=conn)
                return await ctx.interaction.response.send_modal(modal)

            await ctx.send(embed=membed("Hello. What would you like the tag's name to be?"))

            converter = TagName()
            original = ctx.message

            def check(msg):
                return msg.author == ctx.author and ctx.channel == msg.channel

            try:
                name = await self.bot.wait_for('message', timeout=25.0, check=check)
            except asyncio.TimeoutError:
                return await ctx.send(embed=membed('You took too long.'))

            try:
                ctx.message = name
                name = await converter.convert(ctx, name.content)
            except commands.BadArgument as e:
                return await ctx.send(embed=membed(f'{e}'))            
            finally:
                ctx.message = original

            if self.is_tag_being_made(name):
                return await ctx.send(embed=membed("This tag is currently being made by someone."))

            # it's technically kind of expensive to do two queries like this
            # i.e. one to check if it exists and then another that does the insert
            # while also checking if it exists due to the constraints,
            # however for UX reasons I might as well do it.

            row = await conn.fetchone("SELECT 1 FROM tags WHERE LOWER(name)=$0", name.lower())

            if row is not None:
                return await ctx.send(
                    embed=membed(
                        "A tag with that name already exists.\n"
                        f"Redo the command `{ctx.prefix}tag make` to retry."
                    )
                )

            self.add_in_progress_tag(name)
            await ctx.send(
                embed=membed(
                    "What about the tag's content?\n"
                    "You can type `abort` to abort this process."
                )
            )

            try:
                msg = await self.bot.wait_for('message', check=check, timeout=120.0)
            except asyncio.TimeoutError:
                self.remove_in_progress_tag(name)
                return await ctx.reply(embed=membed('You took too long.'))

            if msg.content == 'abort':
                self.remove_in_progress_tag(name)
                return await msg.reply(embed=membed('Aborted.'))
            elif msg.content:
                clean_content = await commands.clean_content().convert(ctx, msg.content)
            else:
                # fast path I guess?
                clean_content = msg.content

            if msg.attachments:
                clean_content = f'{clean_content}\n{msg.attachments[0].url}'

            if len(clean_content) > 2000:
                self.remove_in_progress_tag(name)
                return await msg.reply(embed=membed('Tag content is a maximum of 2000 characters.'))

            try:
                await self.create_tag(ctx, name, clean_content, conn=conn)
            finally:
                self.remove_in_progress_tag(name)

    @tag.command(description="Modifiy an existing tag that you own")
    @app_commands.guilds(*APP_GUILDS_IDS)
    @app_commands.describe(
        name='The tag to edit.',
        content='The new content of the tag, if not given then a modal is opened.',
    )
    @app_commands.autocomplete(name=owned_non_aliased_tag_autocomplete)
    async def edit(
        self,
        ctx: commands.Context,
        name: str,
        *,
        content: Annotated[Optional[str], commands.clean_content] = None,
    ):

        if content is None:
            async with self.bot.pool.acquire() as conn:
                name = await self.owned_partial_matching(
                    ctx, 
                    word_input=name, 
                    conn=conn, 
                    meth=self.partial_match_including_interaction
                )

                if not (all(name)):
                    return
                name, interaction = name

                content_row: Optional[tuple[str]] = await conn.fetchone(
                    "SELECT content FROM tags WHERE name = $0", name
                )

            modal = TagEditModal(content_row[0])
            await interaction.response.send_modal(modal)
            await modal.wait()
            ctx.interaction = modal.interaction
            content = modal.text

        if len(content) > 2000:
            return await ctx.send(ephemeral=True, embed=membed('Tag content can only be up to 2000 characters.'))

        async with self.bot.pool.acquire() as conn:
            
            val = await conn.fetchone(
                """
                UPDATE tags 
                SET content = $0 
                WHERE LOWER(name) = $1 AND ownerID = $2 
                RETURNING name
                """, content, name, ctx.author.id
            )

            if val is None:
                return await ctx.send(embed=membed(TAG_NOT_FOUND_RESPONSE))
        
            await conn.commit()
            await ctx.send(embed=membed(f'Successfully edited tag named {name!r}.'))

    @tag.command(description="Remove a tag that you own", aliases=('delete',))
    @app_commands.guilds(*APP_GUILDS_IDS)
    @app_commands.describe(name='The tag to remove')
    @app_commands.autocomplete(name=owned_non_aliased_tag_autocomplete)
    async def remove(self, ctx: commands.Context, *, name: Annotated[str, TagName]):

        async with self.bot.pool.acquire() as conn:

            bypass_owner_check = ctx.author.id in self.bot.owner_ids
            clause = "name=$0"

            if bypass_owner_check:
                name = await self.owned_partial_matching(ctx, name, conn)
                if name is None:
                    return
                args = (name,)
            else:
                name = await self.non_owned_partial_matching(ctx, name, conn)
                if name is None:
                    return
                
                args = (name, ctx.author.id)
                clause = f"{clause} AND ownerID=$1"

            query = f"DELETE FROM tags WHERE {clause} RETURNING rowid, name"
            deleted_info = await conn.fetchone(query, *args)

            if deleted_info is None:
                return await ctx.send(ephemeral=True, embed=membed(TAG_NOT_FOUND_SIMPLE_RESPONSE))
            await ctx.send(embed=membed(f'Tag named {deleted_info[1]!r} (ID {deleted_info[0]}) successfully deleted.'))

    @tag.command(description="Remove a tag that you own by its ID", aliases=('delete_id',))
    @app_commands.guilds(*APP_GUILDS_IDS)
    @app_commands.describe(tag_id='The internal tag ID to delete.')
    @app_commands.rename(tag_id='id')
    async def remove_id(self, ctx: commands.Context, tag_id: int):

        bypass_owner_check = ctx.author.id in self.bot.owner_ids
        clause = 'rowid=$0'

        if bypass_owner_check:
            args = (tag_id,)
        else:
            args = (tag_id, ctx.author.id)
            clause = f'{clause} AND ownerID=$1'

        async with self.bot.pool.acquire() as conn:
            query = f'DELETE FROM tags WHERE {clause} RETURNING rowid, name'
            deleted_info = await conn.fetchone(query, *args)

            if deleted_info is None:
                return await ctx.send(embed=membed(TAG_NOT_FOUND_RESPONSE), ephemeral=True)
            await ctx.send(embed=membed(f'Tag named {deleted_info[1]!r} (ID {deleted_info[0]}) successfully deleted.'))

    async def _send_tag_info(
        self, 
        ctx: commands.Context, 
        conn: asqlite_Connection, 
        tag_name: str, 
        row: sqlite3.Row
    ) -> None:
        """Expects row in this format: rowid, uses, ownerID, created_at"""

        embed = discord.Embed(colour=discord.Colour.blurple())

        rowid, uses, owner_id, created_at = row

        embed.title = tag_name
        embed.timestamp = datetime.datetime.fromtimestamp(created_at, tz=datetime.timezone.utc)
        embed.set_footer(text='Tag created')

        user = self.bot.get_user(owner_id) or (await self.bot.fetch_user(owner_id))
        embed.set_author(name=str(user), icon_url=user.display_avatar.url)

        embed.add_field(name='Owner', value=f'<@{owner_id}>')
        embed.add_field(name='Uses', value=f"` {uses:,} `")

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
            WHERE first.rowid=$1
            """
        )

        rank = await conn.fetchone(query, rowid)
        if rank is not None:
            embed.add_field(name='Rank', value=f"` {rank[0]:,} / {rank[1]:,} `")

        await ctx.send(embed=embed)

    @tag.command(description="Retrieve info about a tag", aliases=('owner',))
    @app_commands.guilds(*APP_GUILDS_IDS)
    @app_commands.describe(name='The tag to retrieve information for.')
    @app_commands.autocomplete(name=non_aliased_tag_autocomplete)
    async def info(self, ctx: commands.Context, *, name: Annotated[str, TagName]):
        
        async with self.bot.pool.acquire() as conn:
            
            name = await self.non_owned_partial_matching(ctx, name, conn)
            if not name:
                return
            
            record = await conn.fetchone(
                """
                SELECT rowid, uses, ownerID, created_at
                FROM tags
                WHERE name = $0
                """, name
            )
            
            if record is None:
                return await ctx.send(embed=membed(TAG_NOT_FOUND_SIMPLE_RESPONSE))

            await self._send_tag_info(ctx, conn, tag_name=name, row=record)

    @tag.command(description="Remove all tags made by a user")
    @app_commands.guilds(*APP_GUILDS_IDS)
    @app_commands.describe(user='The user to remove all tags of. Defaults to your own.')
    async def purge(self, ctx: commands.Context, user: Optional[discord.Member] = commands.Author):

        if (ctx.author.id != user.id) and (ctx.author.id not in self.bot.owner_ids):
            return await ctx.send(embed=membed("Only bot developers can do this."))

        async with self.bot.pool.acquire() as conn:
            conn: asqlite_Connection

            row: tuple[int] = await conn.fetchone("SELECT COUNT(*) FROM tags WHERE ownerID=$0", user.id)
            count = row[0]

            if not count:
                return await ctx.send(embed=membed(f"{user.mention} has no tags."))

            val = await send_boilerplate_confirm(
                ctx, 
                custom_description=f"Upon approval, **{count}** tags by {user.mention} will be deleted."
            )
 
            if val:
                query = "DELETE FROM tags WHERE ownerID=$0"
                await conn.execute(query, user.id)
                await conn.commit()

                await ctx.send(embed=membed(f"Removed all tags by {user.mention}."))

    async def reusable_paginator_via(self, ctx, *, results: tuple, length: Optional[int] = 12, em: discord.Embed):
        """Only use this when you have a tuple containing the tag name and rowid in this order."""

        async def get_page_part(page: int):
            """Helper function to determine what page of the paginator we're on."""

            offset = (page - 1) * length
            em.description = ""
            for index, tag in enumerate(results[offset:offset+length], start=offset+1):
                em.description += f'{index}. {tag[0]} (ID: {tag[1]})\n'

            n = paginator.compute_total_pages(len(results), length)
            em.set_footer(text=f"Page {page} of {n}")
            return em, n
        
        paginator = PaginationSimple(
            ctx, 
            invoker_id=ctx.author.id, 
            get_page=get_page_part
        )
        await paginator.navigate()

    @tag.command(description="Search for a tag")
    @app_commands.guilds(*APP_GUILDS_IDS)
    @app_commands.describe(query='The tag name to search for.')
    async def search(self, ctx: commands.Context, *, query: Annotated[str, commands.clean_content]):

        async with self.bot.pool.acquire() as conn:

            sql = (
                """
                SELECT name, rowid
                FROM tags
                WHERE name LIKE '%' || $0 || '%'
                LIMIT 100
                """
            )

            results = await conn.fetchall(sql, query)

        if not results:
            return await ctx.send(embed=membed('No tags found.'))
        
        await self.reusable_paginator_via(
            ctx,
            results=results, 
            em=discord.Embed(colour=discord.Colour.blurple())
        )

    @tag.command(description="Transfer a tag to another member")
    @app_commands.guilds(*APP_GUILDS_IDS)
    @app_commands.describe(member='The member to transfer the tag to.', tag="The tag to transfer.")
    @app_commands.autocomplete(tag=owned_non_aliased_tag_autocomplete)
    async def transfer(self, ctx: commands.Context, member: discord.Member, *, tag: Annotated[str, TagName]):

        if member.bot:
            return await ctx.send(embed=membed('You cannot transfer tags to bots.'))

        async with self.bot.pool.acquire() as conn:
            conn: asqlite_Connection

            tag = await self.owned_partial_matching(ctx, tag, conn)
            if not tag:
                return
            
            row = await conn.fetchone("SELECT rowid FROM tags WHERE name=$0 AND ownerID=$1", tag, ctx.author.id)

            if row is None:
                return await ctx.send(embed=membed(TAG_NOT_FOUND_SIMPLE_RESPONSE))

            await conn.execute("UPDATE tags SET ownerID = $0 WHERE rowid = $1", member.id, row[0])
            await conn.commit()

            await ctx.send(embed=membed(f'Successfully transferred tag ownership to {member.mention}.'))

    @tag.command(name="all", description="List all tags ever made")
    @app_commands.guilds(*APP_GUILDS_IDS)
    async def all_tags(self, ctx: commands.Context):

        async with self.bot.pool.acquire() as conn:
            query = (
                """
                SELECT name, rowid
                FROM tags
                ORDER BY name
                """
            )

            rows = await conn.fetchall(query)
            if not rows:
                return await ctx.send(embed=membed('No tags exist!'))

            em = discord.Embed(colour=discord.Colour.blurple())
            await self.reusable_paginator_via(
                ctx,
                results=rows, 
                em=em
            )
    
    @tag.command(name="list", description="Display all tags you made")
    @app_commands.describe(member='The member to list tags of. Defaults to show yours.')
    async def _list(self, ctx: commands.Context, *, member: discord.User = commands.Author):
        async with self.bot.pool.acquire() as conn:
            conn: asqlite_Connection
            query = (
                """
                SELECT name, rowid
                FROM tags
                WHERE ownerID=$0
                ORDER BY name
                """
            )

            rows = await conn.fetchall(query, member.id)
            if not rows:
                return await ctx.send(embed=membed(f"{member.mention} has no tags."))
        
            em = discord.Embed(colour=discord.Colour.blurple())
            em.set_author(name=member.display_name, icon_url=member.display_avatar.url)
            await self.reusable_paginator_via(
                ctx, 
                results=rows, 
                em=em
            )

    @commands.hybrid_command()
    @app_commands.guilds(*APP_GUILDS_IDS)
    @app_commands.describe(member='The member to list the tags of. Defaults to your own.')
    async def tags(self, ctx: commands.Context, *, member: discord.User = commands.Author):
        """An alias for tag list command."""
        await ctx.invoke(self._list, member=member)

    @tag.command(description="Display a random tag")
    @app_commands.guilds(*APP_GUILDS_IDS)
    async def random(self, ctx: commands.Context):
        async with self.bot.pool.acquire() as conn:

            row = await conn.fetchone(
                """
                SELECT name, content
                FROM tags
                ORDER BY RANDOM()
                LIMIT 1
                """
            )

            if row is None:
                return await ctx.send(embed=membed('No tags exist yet!'))
            
            name, content = row

            await ctx.send(f"Random tag found: {name}")
            await ctx.send(content=content)


async def setup(bot: commands.Bot):
    await bot.add_cog(Tags(bot))
