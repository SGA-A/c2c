import sqlite3
from asyncio import TimeoutError
from datetime import datetime, timezone
from typing import Annotated, Callable, Literal

import discord
from discord import app_commands
from discord.ext import commands
from asqlite import ProxiedConnection as asqlite_Connection

from .core.views import send_boilerplate_confirm
from .core.helpers import membed, send_message
from .core.constants import LIMITED_INSTALLS, LIMITED_CONTEXTS
from .core.paginator import PaginationSimple


MAX_CHARACTERS_EXCEEDED_RESPONSE = "Tag content cannot exceed 2000 characters."
TIMED_OUT_RESPONSE = "You took too long."
TAG_NOT_FOUND_SIMPLE_RESPONSE = "Tag not found, it may have been deleted when you called the command."
TAG_BEING_MADE_RESPONSE = "This tag is already being made by someone right now!"
TAG_ALREADY_EXISTS_RESPONSE = "A tag with that name already exists.\n-# Restart the process via `>tag make` or the context menu."
TAG_NOT_FOUND_RESPONSE = (
    "Could not find any tag with these properties.\n"
    "- You can't modify the tag if it doesn't belong to you.\n"
    "- You also can't modify a tag that doesn't exist, obviously."
)


class TagName(commands.clean_content):
    def __init__(self, *, lower: bool = False) -> None:
        self.lower: bool = lower
        super().__init__()

    async def convert(self, ctx: commands.Context | discord.Interaction, argument: str) -> str:
        converted = await super().convert(ctx, argument)
        lower = converted.lower().strip()

        if not lower:
            raise commands.BadArgument('Missing tag name.')

        if len(lower) > 80:
            raise commands.BadArgument('Tag name is a maximum of 80 characters.')

        first_word, _, _ = lower.partition(' ')

        # get tag command
        bot = getattr(ctx, "bot", None) or ctx.client
        root: commands.GroupMixin = bot.get_command('tag')  # type: ignore
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
        max_length=80, 
        min_length=1, 
        placeholder="The name of this tag."
    )

    content = discord.ui.TextInput(
        label='Content', 
        style=discord.TextStyle.long, 
        min_length=1, 
        max_length=2000,
        placeholder="The content of this tag."
    )

    def __init__(self, cog: "Tags") -> None:
        super().__init__()
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction) -> None:
        name = str(self.name)
        try:
            name = await TagName().convert(interaction, name)
        except commands.BadArgument as e:
            return await interaction.response.send_message(embed=membed(str(e)), ephemeral=True)

        if self.cog.is_tag_being_made(name):
            return await interaction.response.send_message(embed=membed(TAG_BEING_MADE_RESPONSE))

        content = str(self.content)
        if len(content) > 2000:
            return await interaction.response.send_message(embed=membed(MAX_CHARACTERS_EXCEEDED_RESPONSE))

        async with interaction.client.pool.acquire() as conn:
            await self.cog.create_tag(interaction, name, content, conn)


class TagLeaderboard(PaginationSimple):
    length = 6
    options = [
        discord.SelectOption(label="Tag Usage", description="How much a tag has been used."),
        discord.SelectOption(label="Tags Created", description="Who creates the most tags."),
        discord.SelectOption(label="Tags Used", description="Who uses the most tags.")
    ]
    podium_pos = {1: "### \U0001f947", 2: "\U0001f948", 3: "\U0001f949"}

    def __init__(self, ctx: commands.Context, chosen_stat: str):
        super().__init__(ctx, invoker_id=ctx.author.id, get_page=self.get_page_part)
        self.chosen_stat = chosen_stat

        self.lb = discord.Embed(title=f"Leaderboard: {chosen_stat}", colour=discord.Colour.blurple())
        self.lb.timestamp = discord.utils.utcnow()

        self.data = []

        for option in self.children[-1].options:
            option.default = option.value == chosen_stat

    async def get_page_part(self, page: int):
        offset = (page - 1) * self.length
        self.lb.description = "\n".join(self.data[offset:offset + self.length])

        n = self.compute_total_pages(len(self.data), self.length)
        self.lb.set_footer(text=f"Page {page} of {n}")
        return self.lb, n

    async def create_lb(self) -> None:
        if self.chosen_stat == "Tag Usage":
            async with self.ctx.bot.pool.acquire() as conn:
                data = await conn.fetchall(
                    """
                    SELECT 
                        name AS identifier,
                        uses AS metric
                    FROM tags
                    ORDER BY uses DESC
                    """
                )

            if not data:
                self.data = []
                return

            self.data = (
                f"{self.podium_pos.get(i, '\U0001f539')} ` {tag_usage:,} ` \U00002014 {tag_name}" 
                for i, (tag_name, tag_usage) in enumerate(data, start=1)
            )
            return

        elif self.chosen_stat == "Tags Created":

            data = (
                """
                SELECT 
                    ownerID AS identifier,
                    COUNT(*) AS metric
                FROM tags
                GROUP BY ownerID
                ORDER BY COUNT(*) DESC
                """
            )

        else:  # Tags Used

            data = (
                """
                SELECT 
                    userID AS identifier,
                    SUM(cmd_count) AS metric
                FROM command_uses
                WHERE cmd_name LIKE '%tag%'
                GROUP BY userID
                ORDER BY cmd_count DESC
                """
            )

        async with self.ctx.bot.pool.acquire() as conn:
            conn: asqlite_Connection
            data = await conn.fetchall(data)

        if not data:
            self.data = []

        self.data = []
        for i, mdata in enumerate(data, start=1):
            tag_owner, tag_count = mdata
            memobj = self.ctx.bot.get_user(tag_owner) or await self.ctx.bot.fetch_user(tag_owner)
            self.data.append(f"{self.podium_pos.get(i, "\U0001f539")} ` {tag_count:,} ` \U00002014 {memobj.name}")

    @discord.ui.select(row=0, options=options)
    async def tag_lb_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.chosen_stat = select.values[0]

        for option in select.options:
            option.default = option.value == self.chosen_stat

        await self.create_lb()
        self.index = 1

        async def get_page_part(page: int):
            offset = (page - 1) * self.length
            self.lb.description = "\n".join(self.data[offset:offset + self.length])

            n = self.compute_total_pages(len(self.data), self.length)
            self.lb.set_footer(text=f"Page {page} of {n}")
            return self.lb, n
        self.get_page = get_page_part

        await self.edit_page(interaction)


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
    """Commands to interface with the global tag system, available for everyone."""

    def __init__(self, bot: commands.Bot) -> None:
        
        self.bot: commands.Bot = bot

        # ownerID: set(name)
        self._reserved_tags_being_made: set[str] = set()
        self.create_tag_menu = app_commands.ContextMenu(
            name="Tag Message",
            callback=self.create_tag_menu_callback,
            allowed_contexts=app_commands.AppCommandContext(guild=True, private_channel=True),
            allowed_installs=app_commands.AppInstallationType(guild=True, user=True)
        )
        self.bot.tree.add_command(self.create_tag_menu)

    async def cog_unload(self) -> None:
        self.bot.tree.remove_command(self.create_tag_menu)

    async def create_tag_menu_callback(self, interaction: discord.Interaction, message: discord.Message):
        if not message.content:
            return await interaction.response.send_message(embed=membed("This message has no content to tag."))

        interaction.message = message
        clean_content = await commands.clean_content().convert(interaction, message.content)

        if message.attachments:
            attachments_refs = "\n".join(attachment.url for attachment in message.attachments)
            clean_content = f"{clean_content}\n{attachments_refs}"

        if len(clean_content) > 2000:
            return await interaction.response.send_message(embed=membed(MAX_CHARACTERS_EXCEEDED_RESPONSE))

        modal = TagMakeModal(self)
        modal.content.default = clean_content
        await interaction.response.send_modal(modal)

    async def partial_match_for(
        self,
        ctx: commands.Context, 
        word_input: str, 
        tag_results: list[sqlite3.Row],
        match_view: discord.ui.View | None = None
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
        meth: Callable | None = None
    ):
        """Partial matching for every existing tag"""

        tag_names = await conn.fetchall(
            """
            SELECT name
            FROM tags
            WHERE LOWER(name) LIKE $0 
            LIMIT 10
            """, f"%{word_input.lower()}%"
        )

        meth = meth or self.partial_match_for
        name = await meth(ctx, word_input, tag_results=tag_names)
        return name

    async def owned_partial_matching(
        self, 
        ctx: commands.Context, 
        word_input: str, 
        conn: asqlite_Connection,
        meth: Callable | None = None
    ) -> tuple | str | None:
        """Partial matching for tags that are owned by the invoker"""

        tag_names = await conn.fetchall(
            """
            SELECT name
            FROM tags
            WHERE ownerID = $0 AND LOWER(name) LIKE $1
            LIMIT 10
            """, ctx.author.id, f"%{word_input.lower()}%"
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
        res = await conn.fetchone("SELECT content FROM tags WHERE name = $0", name)
        if res is None:
            raise RuntimeError(TAG_NOT_FOUND_SIMPLE_RESPONSE)
        return res[0]

    async def create_tag(
        self, 
        ctx: commands.Context | discord.Interaction, 
        name: str, 
        content: str, 
        conn: asqlite_Connection
    ) -> None:

        query = "INSERT INTO tags (name, content, ownerID) VALUES ($0, $1, $2)"

        # since I'm checking for the exception type and acting on it, I need
        # to use the manual transaction blocks

        tr = conn.transaction()
        await tr.start()

        try:
            author: discord.Member | discord.User = getattr(ctx, "author", None) or ctx.user
            await conn.execute(query, name, content, author.id)
        except sqlite3.IntegrityError:
            await tr.rollback()
            await send_message(ctx, embed=membed(f"A tag named {name!r} already exists."))
        except Exception as e:
            self.bot.log_exception(e)
            await tr.rollback()
            await send_message(ctx, embed=membed("Could not create tag."))
        else:
            await tr.commit()
            await send_message(ctx, embed=membed(f'Tag {name!r} successfully created.'))

    def is_tag_being_made(self, name: str) -> bool:
        return name in self._reserved_tags_being_made

    def add_in_progress_tag(self, name: str) -> None:
        self._reserved_tags_being_made.add(name)

    def remove_in_progress_tag(self, name: str) -> None:
        self._reserved_tags_being_made.discard(name)

    @commands.hybrid_group(description="Tag text for later retrieval", fallback='get')
    @app_commands.describe(name='The tag to retrieve.')
    @app_commands.autocomplete(name=non_aliased_tag_autocomplete)
    @app_commands.allowed_installs(**LIMITED_INSTALLS)
    @app_commands.allowed_contexts(**LIMITED_CONTEXTS)
    async def tag(self, ctx: commands.Context, *, name: str):
        async with self.bot.pool.acquire() as conn:
            name = await self.non_owned_partial_matching(ctx, name, conn)
            if name is None:
                return

            try:
                content = await self.get_tag_content(name, conn)
            except RuntimeError as r:
                return await ctx.send(embed=membed(r))

            await ctx.send(content, reference=ctx.message.reference)

            # update the usage
            await conn.execute("UPDATE tags SET uses = uses + 1 WHERE name = $0", name)
    
    @tag.command(description="Create a new tag owned by you", aliases=('add',))
    @app_commands.describe(name='The tag name.', content='The tag content.')
    @app_commands.allowed_installs(**LIMITED_INSTALLS)
    @app_commands.allowed_contexts(**LIMITED_CONTEXTS)
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
            await self.create_tag(ctx, name, content, conn)

    @tag.command(description="Interactively make your own tag", ignore_extra=True)
    @app_commands.allowed_installs(**LIMITED_INSTALLS)
    @app_commands.allowed_contexts(**LIMITED_CONTEXTS)
    async def make(self, ctx: commands.Context):

        if ctx.interaction is not None:
            return await ctx.interaction.response.send_modal(TagMakeModal(self))

        await ctx.send(embed=membed("Hello. What would you like the tag's name to be?"))

        converter = TagName()
        original = ctx.message

        def check(msg):
            return msg.author == ctx.author and ctx.channel == msg.channel

        try:
            name = await self.bot.wait_for("message", timeout=180.0, check=check)
        except TimeoutError:
            return await ctx.send(embed=membed(TIMED_OUT_RESPONSE))

        try:
            ctx.message = name
            name = await converter.convert(ctx, name.content)
        except commands.BadArgument as e:
            return await ctx.send(embed=membed(str(e)))
        finally:
            ctx.message = original

        if self.is_tag_being_made(name):
            return await ctx.send(embed=membed(TAG_BEING_MADE_RESPONSE))

        # it's technically kind of expensive to do two queries like this
        # i.e. one to check if it exists and then another that does the insert
        # while also checking if it exists due to the constraints,
        # however for UX reasons I might as well do it.

        async with self.bot.pool.acquire() as conn:
            row = await conn.fetchone("SELECT 1 FROM tags WHERE name = $0", name)

        if row is not None:
            return await ctx.send(embed=membed(TAG_ALREADY_EXISTS_RESPONSE))

        self.add_in_progress_tag(name)
        await ctx.send(
            embed=membed(
                "What about the tag's content?\n"
                "-# Type `abort` to end this process."
            )
        )

        try:
            msg = await self.bot.wait_for('message', check=check, timeout=120.0)
        except TimeoutError:
            self.remove_in_progress_tag(name)
            return await ctx.reply(embed=membed(TIMED_OUT_RESPONSE))

        if msg.content == 'abort':
            self.remove_in_progress_tag(name)
            return await msg.reply(embed=membed('Aborted.'))
        elif msg.content:
            clean_content = await commands.clean_content().convert(ctx, msg.content)
        else:
            # fast path I guess?
            clean_content = msg.content

        if msg.attachments:
            attachments_refs = "\n".join(attachment.url for attachment in msg.attachments)
            clean_content = f'{clean_content}\n{attachments_refs}'

        if len(clean_content) > 2000:
            self.remove_in_progress_tag(name)
            return await msg.reply(embed=membed(MAX_CHARACTERS_EXCEEDED_RESPONSE))

        conn = await self.bot.pool.acquire()
        try:
            await self.create_tag(ctx, name, clean_content, conn)
        finally:
            self.remove_in_progress_tag(name)
            await self.bot.pool.release(conn)

    @tag.command(description="Modifiy an existing tag that you own")
    @app_commands.describe(
        name='The tag to edit.',
        content='The new content of the tag, if not given then a modal is opened.',
    )
    @app_commands.autocomplete(name=owned_non_aliased_tag_autocomplete)
    @app_commands.allowed_installs(**LIMITED_INSTALLS)
    @app_commands.allowed_contexts(**LIMITED_CONTEXTS)
    async def edit(
        self,
        ctx: commands.Context,
        name: str,
        *,
        content: Annotated[str | None, commands.clean_content] = None,
    ):

        if content is None:

            async with self.bot.pool.acquire() as conn:
                name, interaction = await self.owned_partial_matching(
                    ctx, 
                    word_input=name, 
                    conn=conn, 
                    meth=self.partial_match_including_interaction
                )
            if name is None:
                return
            
            interaction = interaction or ctx.interaction
            if interaction is None:
                return await ctx.send(
                    embed=membed(
                        "## Missing content to edit with\n"
                        "- Since you prefer the use of text commands for this, try to broaden your input.\n"
                        "  - Pass in a smaller part of the tag name, and if there's more than one match, you'll get a list of suggestions.\n"
                        "  - From there, you can select what you want to edit and it will work just fine.\n"
                        "  - Try not to make it too vague though, otherwise the relevant one you want won't appear!\n"
                        "- You can also type in the content of that field in the command name itself.\n"
                        "- Regardless, you should know that because of this, tag names with more than one word need to be enclosed with speech quotes like \"this tag\"."
                    ).set_image(url="https://i.imgur.com/5sPCTCZ.png")
                )

            async with self.bot.pool.acquire() as conn:
                content_row = await conn.fetchone(
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
                WHERE name = $1 AND ownerID = $2 
                RETURNING name
                """, content, name, ctx.author.id
            )

            if val is None:
                return await ctx.send(ephemeral=True, embed=membed(TAG_NOT_FOUND_RESPONSE))
        
            await conn.commit()
            await ctx.send(embed=membed(f'Successfully edited tag named {name!r}.'))

    @tag.command(description="Remove a tag that you own", aliases=('delete',))
    @app_commands.describe(name='The tag to remove')
    @app_commands.autocomplete(name=owned_non_aliased_tag_autocomplete)
    @app_commands.allowed_installs(**LIMITED_INSTALLS)
    @app_commands.allowed_contexts(**LIMITED_CONTEXTS)
    async def remove(self, ctx: commands.Context, *, name: Annotated[str, TagName]):

        async with self.bot.pool.acquire() as conn:

            bypass_owner_check = ctx.author.id in self.bot.owner_ids
            clause = "name = $0"

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
                clause = f"{clause} AND ownerID = $1"

            query = f"DELETE FROM tags WHERE {clause} RETURNING rowid, name"
            deleted_info = await conn.fetchone(query, *args)

            if deleted_info is None:
                return await ctx.send(ephemeral=True, embed=membed(TAG_NOT_FOUND_SIMPLE_RESPONSE))
            await ctx.send(embed=membed(f'Tag named {deleted_info[1]!r} (ID {deleted_info[0]}) successfully deleted.'))

    @tag.command(description="Remove a tag that you own by its ID", aliases=('delete_id',))
    @app_commands.describe(tag_id='The internal tag ID to delete.')
    @app_commands.rename(tag_id='id')
    @app_commands.allowed_installs(**LIMITED_INSTALLS)
    @app_commands.allowed_contexts(**LIMITED_CONTEXTS)
    async def remove_id(self, ctx: commands.Context, tag_id: int):

        bypass_owner_check = ctx.author.id in self.bot.owner_ids
        clause = 'rowid = $0'

        if bypass_owner_check:
            args = (tag_id,)
        else:
            args = (tag_id, ctx.author.id)
            clause = f'{clause} AND ownerID = $1'

        async with self.bot.pool.acquire() as conn:
            query = f'DELETE FROM tags WHERE {clause} RETURNING rowid, name'
            deleted_info = await conn.fetchone(query, *args)

            if deleted_info is None:
                return await ctx.send(ephemeral=True, embed=membed(TAG_NOT_FOUND_RESPONSE))
            await ctx.send(embed=membed(f'Tag named {deleted_info[1]!r} (ID {deleted_info[0]}) successfully deleted.'))

    async def _send_tag_info(
        self, 
        ctx: commands.Context, 
        conn: asqlite_Connection, 
        tag_name: str, 
        row: sqlite3.Row
    ) -> None:
        """Expects row in this format: rowid, uses, ownerID, created_at"""

        embed = discord.Embed(colour=discord.Colour.blurple()).set_footer(text='Tag created')

        rowid, uses, owner_id, created_at = row

        embed.title = tag_name
        embed.timestamp = datetime.fromtimestamp(created_at, tz=timezone.utc)

        user = self.bot.get_user(owner_id) or (await self.bot.fetch_user(owner_id))
        embed.set_author(
            name=str(user), 
            icon_url=user.display_avatar.url
        ).add_field(
            name='Owner', 
            value=f'<@{owner_id}>'
        ).add_field(
            name='Uses', 
            value=f"{uses:,}"
        )

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
            embed.add_field(name='Rank', value=f"{rank[0]:,} / {rank[1]:,}")

        await ctx.send(embed=embed)

    @tag.command(description="Retrieve info about a tag", aliases=('owner',))
    @app_commands.describe(name='The tag to retrieve information for.')
    @app_commands.autocomplete(name=non_aliased_tag_autocomplete)
    @app_commands.allowed_installs(**LIMITED_INSTALLS)
    @app_commands.allowed_contexts(**LIMITED_CONTEXTS)
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
                return await ctx.send(ephemeral=True, embed=membed(TAG_NOT_FOUND_SIMPLE_RESPONSE))

            await self._send_tag_info(ctx, conn, tag_name=name, row=record)

    @tag.command(description="Remove all tags made by a user")
    @app_commands.describe(user='The user to remove all tags of. Defaults to your own.')
    @app_commands.allowed_installs(**LIMITED_INSTALLS)
    @app_commands.allowed_contexts(**LIMITED_CONTEXTS)
    async def purge(self, ctx: commands.Context, user: discord.User = commands.Author):

        if (ctx.author.id != user.id) and (ctx.author.id not in self.bot.owner_ids):
            return await ctx.send(embed=membed("You can only delete tags you own."))

        async with self.bot.pool.acquire() as conn:
            count, = await conn.fetchone("SELECT COUNT(*) FROM tags WHERE ownerID = $0", user.id)

        if not count:
            return await ctx.send(embed=membed(f"{user.name} has no tags."))

        val = await send_boilerplate_confirm(ctx, f"Upon approval, **{count}** tag(s) by {user.name} will be deleted.")
        if val:
            async with self.bot.pool.acquire() as conn:
                await conn.execute("DELETE FROM tags WHERE ownerID = $0", user.id)
                await conn.commit()

            await ctx.reply(embed=membed(f"Removed all tags by {user.name}."))

    async def reusable_paginator_via(self, ctx, rows: tuple, em: discord.Embed, length: int = 12):
        """Only use this when you have a tuple containing the tag name and rowid in this order."""

        async def get_page_part(page: int):
            """Helper function to determine what page of the paginator we're on."""

            offset = (page - 1) * length
            em.description = "\n".join(
                f'{index}. {tag[0]} (ID: {tag[1]})'
                for index, tag in enumerate(rows[offset:offset+length], start=offset+1)
            )

            n = PaginationSimple.compute_total_pages(len(rows), length)
            em.set_footer(text=f"Page {page} of {n}")
            return em, n

        await PaginationSimple(ctx, ctx.author.id, get_page_part).navigate()

    @tag.command(description="Search for a tag")
    @app_commands.describe(query='The tag name to search for.')
    @app_commands.allowed_installs(**LIMITED_INSTALLS)
    @app_commands.allowed_contexts(**LIMITED_CONTEXTS)
    async def search(self, ctx: commands.Context, *, query: Annotated[str, commands.clean_content]):

        sql = (
            """
            SELECT name, rowid
            FROM tags
            WHERE LOWER(name) LIKE '%' || $0 || '%'
            LIMIT 100
            """
        )

        async with self.bot.pool.acquire() as conn:
            rows = await conn.fetchall(sql, query.lower())

        if not rows:
            return await ctx.send(embed=membed('No tags found.'))

        em = discord.Embed(colour=discord.Colour.blurple())
        await self.reusable_paginator_via(ctx, rows, em)

    @tag.command(description="Transfer a tag to another member")
    @app_commands.describe(member='The member to transfer the tag to.', tag="The tag to transfer.")
    @app_commands.autocomplete(tag=owned_non_aliased_tag_autocomplete)
    @app_commands.allowed_installs(**LIMITED_INSTALLS)
    @app_commands.allowed_contexts(**LIMITED_CONTEXTS)
    async def transfer(self, ctx: commands.Context, member: discord.User, *, tag: Annotated[str, TagName]):

        if member.bot:
            return await ctx.send(embed=membed('You cannot transfer tags to bots.'))

        async with self.bot.pool.acquire() as conn:
            conn: asqlite_Connection

            tag = await self.owned_partial_matching(ctx, tag, conn)
            if not tag:
                return

            ret = await conn.execute(
                """
                UPDATE tags 
                SET ownerID = $2 
                WHERE name = $0 AND ownerID = $1
                RETURNING rowid
                """, tag, ctx.author.id, member.id
            )

            if ret is None:
                return await ctx.send(ephemeral=True, embed=membed(TAG_NOT_FOUND_SIMPLE_RESPONSE))
            await conn.commit()
        await ctx.send(embed=membed(f'Successfully transferred tag ownership to {member.name}.'))

    @tag.command(name="all", description="List all tags ever made")
    @app_commands.allowed_installs(**LIMITED_INSTALLS)
    @app_commands.allowed_contexts(**LIMITED_CONTEXTS)
    async def all_tags(self, ctx: commands.Context):
        async with self.bot.pool.acquire() as conn:
            rows = await conn.fetchall("SELECT name, rowid FROM tags ORDER BY name")

        if not rows:
            return await ctx.send(embed=membed('No tags exist!'))

        em = discord.Embed(colour=discord.Colour.blurple())
        await self.reusable_paginator_via(ctx, rows, em)

    @tag.command(name="list", description="Display all tags you made")
    @app_commands.describe(member='The member to list tags of. Defaults to show yours.')
    @app_commands.allowed_installs(**LIMITED_INSTALLS)
    @app_commands.allowed_contexts(**LIMITED_CONTEXTS)
    async def _list(self, ctx: commands.Context, *, member: discord.User = commands.Author):
        query = "SELECT name, rowid FROM tags WHERE ownerID = $0 ORDER BY name"
        async with self.bot.pool.acquire() as conn:
            rows = await conn.fetchall(query, member.id)

        if not rows:
            return await ctx.send(embed=membed(f"{member.name} has no tags."))

        em = discord.Embed(colour=discord.Colour.blurple())
        em.set_author(name=member.display_name, icon_url=member.display_avatar.url)
        await self.reusable_paginator_via(ctx, rows, em)

    @commands.hybrid_command(description="List tags of a member or your own")
    @app_commands.describe(member='The member to list the tags of. Defaults to your own.')
    @app_commands.allowed_installs(**LIMITED_INSTALLS)
    @app_commands.allowed_contexts(**LIMITED_CONTEXTS)
    async def tags(self, ctx: commands.Context, *, member: discord.User = commands.Author):
        await ctx.invoke(self._list, member=member)

    @tag.command(description="Display a random tag")
    @app_commands.allowed_installs(**LIMITED_INSTALLS)
    @app_commands.allowed_contexts(**LIMITED_CONTEXTS)
    async def random(self, ctx: commands.Context):
        async with self.bot.pool.acquire() as conn:
            row = await conn.fetchone("SELECT name, content FROM tags ORDER BY RANDOM() LIMIT 1")

        if row is None:
            return await ctx.send(embed=membed('No tags exist yet!'))

        name, content = row

        await ctx.send(f"Random tag found: {name}")
        await ctx.send(content)

    async def global_stats(self, ctx: commands.Context) -> None:

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

        async with self.bot.pool.acquire() as conn:
            conn: asqlite_Connection
            top_tags = await conn.fetchall(top_tags_query)
            top_data = await conn.fetchall(top_data_query)

        top_users = [row[1:] for row in top_data if row[0] == 'user']
        top_creators = [row[1:] for row in top_data if row[0] == 'creator']

        em = discord.Embed(title="Tag Stats", colour=discord.Colour.blurple())
        if not top_tags:
            em.description = "No tag stats to share."
        else:
            data = top_tags[0]
            em.description = f"{data[-2]:,} tags, {data[-1]:,} uses"

        if len(top_tags) < 3:
            top_tags.extend((None, None, None, None) for _ in range(0, 3 - len(top_tags)))
        if len(top_users) < 3:
            top_users.extend((None, None) for _ in range(0, 3 - len(top_users)))
        if len(top_creators) < 3:
            top_creators.extend((None, None) for _ in range(0, 3 - len(top_creators)))

        def emojize(seq):
            emoji = 129351  # ord(':first_place:')
            for index, value in enumerate(seq):
                yield chr(emoji + index), value

        em.add_field(
            name='Top Tags', 
            inline=False,
            value='\n'.join(
                f'{emoji}: {name} ({uses} uses)' if name else f'{emoji}: Nothing!'
                for (emoji, (name, uses, _, _)) in emojize(top_tags)
            )
        ).add_field(
            name='Top Tag Users', 
            inline=False,
            value='\n'.join(
                f'{emoji}: <@{author_id}> ({uses} times)' if author_id else f'{emoji}: No one!'
                for (emoji, (author_id, uses)) in emojize(top_users)
            )
        ).add_field(
            name='Top Tag Creators', 
            inline=False,
            value='\n'.join(
                f'{emoji}: <@{owner_id}> ({count} tags)' if owner_id else f'{emoji}: No one!'
                for (emoji, (owner_id, count)) in emojize(top_creators)
            )
        ).set_footer(text="These stats are global.")

        await ctx.send(embed=em)
        del top_data, top_users, top_creators, top_tags, top_tags_query, top_data_query

    async def member_stats(self, ctx: commands.Context, user: discord.abc.User):
        e = discord.Embed(colour=discord.Colour.blurple())
        e.set_author(
            name=str(user), 
            icon_url=user.display_avatar.url
        ).set_footer(text='These stats are user-specific.')

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

        async with self.bot.pool.acquire() as conn:
            count, owned_tags, owned_uses = await conn.fetchone(query, user.id) 

            query = (
                """
                SELECT name, uses
                FROM tags
                WHERE ownerID = $0
                ORDER BY uses DESC
                LIMIT 3
                """
            )

            records = await conn.fetchall(query, user.id)

        e.add_field(
            name='Owned Tags', 
            value=owned_tags
        ).add_field(
            name='Owned Tag Uses', 
            value=owned_uses
        ).add_field(name='Tag Command Uses', value=f"{count:,}")

        # fill with data to ensure that we have a minimum of 3
        if len(records) < 3:
            records.extend((None,)*2 for i in range(0, 3 - len(records)))

        emoji = 129351
        for offset, (name, uses) in enumerate(records):
            if name:
                value = f'{name} ({uses} uses)'
            else:
                value = 'Nothing!'

            e.add_field(name=f'{chr(emoji + offset)} Owned Tag', value=value)

        await ctx.send(embed=e)

    @tag.command(description="Show tag statistics globally or for a member")
    @app_commands.describe(member="The member to get stats about, defaults to displaying global stats.")
    @app_commands.allowed_installs(**LIMITED_INSTALLS)
    @app_commands.allowed_contexts(**LIMITED_CONTEXTS)
    async def stats(self, ctx: commands.Context, member: discord.User | None = None):
        if member:
            return await self.member_stats(ctx, member)
        await self.global_stats(ctx)

    @tag.command(description="Rank tags based on various stats", aliases=('lb',))
    @app_commands.describe(stat="The stat you want to see.")
    @app_commands.allowed_installs(**LIMITED_INSTALLS)
    @app_commands.allowed_contexts(**LIMITED_CONTEXTS)
    async def leaderboard(self, ctx: commands.Context, stat: Literal["Tag Usage", "Tags Created", "Tags Used"]):
        lb_view = TagLeaderboard(ctx, stat)

        await lb_view.create_lb()
        await lb_view.navigate()


async def setup(bot: commands.Bot):
    await bot.add_cog(Tags(bot))
