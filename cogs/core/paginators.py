from typing import Callable

import discord
from discord.ext import commands

from .helpers import membed, economy_check, edit_response, respond
from .transformers import RawIntegerTransformer


NOT_YOUR_MENU = membed("This menu is not for you.")
GO_FIRST_PAGE_EMOJI = discord.PartialEmoji.from_str("<:firstPage:1263921815345041460>")
MOVE_LEFT_EMOJI = discord.PartialEmoji.from_str("<:leftPage:1263922081696059404>")
MOVE_RIGHT_EMOJI = discord.PartialEmoji.from_str("<:rightPage:1263923290959773706>")
GO_LAST_PAGE_EMOJI = discord.PartialEmoji.from_str("<:finalPage:1263921799633047573>")


class PaginatorInput(discord.ui.Modal):
    """Modal for users to pass in a valid page number."""

    def __init__(self, their_view: 'Pagination'):
        self.interaction: discord.Interaction | None = None
        self.page_num.placeholder = f"A number between 1 and {their_view.total_pages}."
        super().__init__(title="Input a Page", timeout=45.0)

    page_num = discord.ui.TextInput(label='Page', min_length=1, max_length=5)

    async def on_submit(self, interaction: discord.Interaction):
        self.interaction = interaction
        self.stop()


class BasePaginator(discord.ui.View):
    """The base paginator which (most) paginators inherit properties from."""

    def __init__(self, interaction: discord.Interaction, get_page: Callable | None = None):
        super().__init__(timeout=90.0)
        self.interaction = interaction
        self.get_page = get_page
        self.index = 1
        self.total_pages: int | None = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return await economy_check(interaction, self.interaction.user.id)

    async def on_timeout(self) -> None:
        for item in self.children:
            item.disabled = True

        try:
            await self.interaction.edit_original_response(view=self)
        except discord.HTTPException:
            pass

    async def on_error(self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item) -> None:
        if hasattr(error, "cause"):  # CustomTransformerError
            return await interaction.response.send_message(error.cause)

        try:
            await self.interaction.delete_original_response()
        except discord.HTTPException:
            pass

        self.stop()
        await respond(interaction, embed=membed("Something went wrong."))
        await super().on_error(interaction, error, item)

    @staticmethod
    def compute_total_pages(total_results: int, results_per_page: int) -> int:
        return (((total_results - 1) // results_per_page) + 1) or 1


class Pagination(BasePaginator):
    """Pagination menu with support for direct queries to a specific page."""

    def __init__(self, interaction, get_page, total_pages: int) -> None:
        super().__init__(interaction, get_page)
        self.total_pages = total_pages

    async def navigate(self, **kwargs) -> None:
        embs = await self.get_page(self.index)

        if self.total_pages == 1:
            return await respond(self.interaction, embeds=embs, **kwargs)
        self.update_buttons()
        await respond(self.interaction, embeds=embs, view=self, **kwargs)

    async def edit_page(self, interaction: discord.Interaction) -> None:
        embs  = await self.get_page(self.index)
        self.update_buttons()
        await edit_response(interaction, embeds=embs, view=self)

    def update_buttons(self) -> None:
        self.children[2].label = f"{self.index} / {self.total_pages}"

        is_first_page_check = self.index == 1
        is_last_page_check = self.index == self.total_pages

        self.children[0].disabled = is_first_page_check
        self.children[1].disabled = is_first_page_check
        self.children[3].disabled = is_last_page_check
        self.children[4].disabled = is_last_page_check

    @discord.ui.button(style=discord.ButtonStyle.blurple, emoji=GO_FIRST_PAGE_EMOJI, row=1)
    async def first(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        self.index = 1
        await self.edit_page(interaction)

    @discord.ui.button(style=discord.ButtonStyle.blurple, emoji=MOVE_LEFT_EMOJI, row=1)
    async def previous(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        self.index -= 1
        await self.edit_page(interaction)

    @discord.ui.button(style=discord.ButtonStyle.gray, row=1)
    async def numeric(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        modal = PaginatorInput(their_view=self)
        await interaction.response.send_modal(modal)

        val = await modal.wait()
        if val:
            return

        val = RawIntegerTransformer(reject_shorthands=True).transform(interaction, modal.page_num.value)
        self.index = min(self.total_pages, val)
        await self.edit_page(modal.interaction)

    @discord.ui.button(style=discord.ButtonStyle.blurple, emoji=MOVE_RIGHT_EMOJI, row=1)
    async def next_page(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        self.index += 1
        await self.edit_page(interaction)

    @discord.ui.button(style=discord.ButtonStyle.blurple, emoji=GO_LAST_PAGE_EMOJI, row=1)
    async def last_page(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        self.index = self.total_pages
        await self.edit_page(interaction)


class PaginationSimple(discord.ui.View):
    """
    A regular pagination menu with no extra features.

    Supports hybrids and everything in between.
    """

    def __init__(self, ctx, invoker_id: int, total_pages: int, get_page: Callable | None = None) -> None:
        self.ctx: commands.Context | discord.Interaction = ctx
        self.invoker_id = invoker_id
        self.get_page = get_page
        self.index = 1
        self.total_pages = total_pages
        super().__init__(timeout=45.0)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return await economy_check(interaction, self.invoker_id)

    async def on_timeout(self) -> None:
        edit_meth = getattr(self.message, "edit", None) or self.ctx.edit_original_response

        for item in self.children:
            item.disabled = True

        try:
            await edit_meth(view=self)
        except discord.HTTPException:
            pass

    async def navigate(self):
        emb = await self.get_page(self.index)
        respond_meth = getattr(self.ctx, "send", None) or self.ctx.response.send_message

        if self.total_pages == 1:
            self.stop()
            return await respond_meth(embed=emb)

        self.update_buttons()
        self.message = await respond_meth(embed=emb, view=self)

    async def edit_page(self, interaction: discord.Interaction) -> None:
        emb = await self.get_page(self.index)
        self.update_buttons()
        await edit_response(interaction, embed=emb, view=self)

    def update_buttons(self) -> None:
        is_first_page_check = self.index == 1
        is_last_page_check = self.index == self.total_pages

        self.children[0].disabled = is_first_page_check
        self.children[1].disabled = is_first_page_check
        self.children[2].disabled = is_last_page_check
        self.children[3].disabled = is_last_page_check

    @discord.ui.button(style=discord.ButtonStyle.blurple, emoji=GO_FIRST_PAGE_EMOJI, row=1)
    async def first(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        self.index = 1
        await self.edit_page(interaction)

    @discord.ui.button(style=discord.ButtonStyle.blurple, emoji=MOVE_LEFT_EMOJI, row=1)
    async def previous(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        self.index -= 1
        await self.edit_page(interaction)

    @discord.ui.button(style=discord.ButtonStyle.blurple, emoji=MOVE_RIGHT_EMOJI, row=1)
    async def next_page(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        self.index += 1
        await self.edit_page(interaction)

    @discord.ui.button(style=discord.ButtonStyle.blurple, emoji=GO_LAST_PAGE_EMOJI, row=1)
    async def last_page(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        self.index = self.total_pages
        await self.edit_page(interaction)

    @staticmethod
    def compute_total_pages(total_results: int, results_per_page: int) -> int:
        return BasePaginator.compute_total_pages(total_results, results_per_page)


class RefreshPagination(BasePaginator):
    """Paginator with support for refreshing data, containing it's own refresh button."""

    def __init__(self, interaction: discord.Interaction, get_page: Callable | None = None) -> None:
        super().__init__(interaction, get_page)

    async def navigate(self) -> None:
        emb = await self.get_page(self.index)
        self.update_buttons()
        await self.interaction.response.send_message(embed=emb, view=self)

    def reset_index(self, refreshed_data: list, length: int | None = None):
        """
        Set the minimum page length in refresh pagination classes.

        Pass in `length` if it's not present in the paginator instance.

        This function returns the class instance to allow for fluent-style chaining.

        This should not be used within select callbacks that refresh data.
        """
        length = length or self.length
        self.total_pages = self.compute_total_pages(len(refreshed_data), length)
        self.index = min(self.index, self.total_pages)
        return self

    async def edit_page(self, interaction: discord.Interaction, force_refresh: bool | None = False) -> None:
        emb = await self.get_page(force_refresh)
        self.update_buttons()
        await edit_response(interaction, embed=emb, view=self)

    def update_buttons(self) -> None:
        is_first_page_check = self.index == 1
        is_last_page_check = self.index == self.total_pages

        self.children[0].disabled = is_first_page_check
        self.children[1].disabled = is_first_page_check
        self.children[3].disabled = is_last_page_check
        self.children[4].disabled = is_last_page_check

    @discord.ui.button(style=discord.ButtonStyle.blurple, emoji=GO_FIRST_PAGE_EMOJI, row=1)
    async def first(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        self.index = 1
        await self.edit_page(interaction)

    @discord.ui.button(style=discord.ButtonStyle.blurple, emoji=MOVE_LEFT_EMOJI, row=1)
    async def previous(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        self.index -= 1
        await self.edit_page(interaction)

    @discord.ui.button(emoji=discord.PartialEmoji.from_str("<:refreshPages:1263923160433168414>"), row=1)
    async def refresh_paginator(self, interaction: discord.Interaction, _: discord.ui.Button):
        await self.edit_page(interaction, force_refresh=True)

    @discord.ui.button(style=discord.ButtonStyle.blurple, emoji=MOVE_RIGHT_EMOJI, row=1)
    async def next_page(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        self.index += 1
        await self.edit_page(interaction)

    @discord.ui.button(style=discord.ButtonStyle.blurple, emoji=GO_LAST_PAGE_EMOJI, row=1)
    async def last_page(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        self.index = self.total_pages
        await self.edit_page(interaction)


class PaginationItem(BasePaginator):
    """
    Pagination menu with forward and backward buttons only.

    Disabling logic has been stripped away.
    """

    def __init__(self, interaction: discord.Interaction, get_page: Callable | None = None):
        super().__init__(interaction, get_page)

    async def navigate(self) -> None:
        emb = await self.get_page(self.index)
        await self.interaction.response.send_message(embed=emb, view=self)

    async def edit_page(self, interaction: discord.Interaction) -> None:
        emb = await self.get_page(self.index)
        await edit_response(interaction, embed=emb, view=self)

    @discord.ui.button(style=discord.ButtonStyle.grey, emoji=MOVE_LEFT_EMOJI, row=2)
    async def previous(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        self.index = (self.index - 2) % self.total_pages + 1
        await self.edit_page(interaction)

    @discord.ui.button(style=discord.ButtonStyle.grey, emoji=MOVE_RIGHT_EMOJI, row=2)
    async def next_page(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        self.index = (self.index % self.total_pages) + 1
        await self.edit_page(interaction)
