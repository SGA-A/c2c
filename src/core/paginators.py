from __future__ import annotations

from typing import Callable, Optional

import discord

from .bot import Interaction
from .helpers import BaseView
from .transformers import RawIntegerTransformer

REFRESH = discord.PartialEmoji.from_str("<:refreshPages:1263923160433168414>")
FIRST = discord.PartialEmoji.from_str("<:firstPage:1263921815345041460>")
LEFT = discord.PartialEmoji.from_str("<:leftPage:1263922081696059404>")
RIGHT = discord.PartialEmoji.from_str("<:rightPage:1263923290959773706>")
LAST = discord.PartialEmoji.from_str("<:lastPage:1263921799633047573>")


class PaginatorInput(discord.ui.Modal):
    """Modal for users to pass in a valid page number."""

    def __init__(self, view: "Pagination") -> None:
        super().__init__(title="Input a Page")

        self.view = view
        self.page.placeholder = f"A number between 1 and {view.total_pages}."

    page = discord.ui.TextInput(label="Page", min_length=1, max_length=5)

    async def on_submit(self, itx: Interaction) -> None:

        true_page = RawIntegerTransformer().transform(itx, self.page.value)

        if isinstance(true_page, str):
            self.view.index = self.view.total_pages
        elif self.view.index == true_page:
            # Modal inputs only exist on non-refreshable paginators
            return await itx.response.edit_message(view=self)

        self.view.index = min(self.view.total_pages, true_page)
        await self.view.edit_page(itx)

    async def on_error(self, itx: Interaction, error: Exception) -> None:
        await self.view.on_error(itx, error, self)


class BasePaginator(BaseView):
    """
    The base paginator which all paginators should inherit from.

    You are expected to return a list of embeds even
    if you only return one embed in your custom function,
    though you can override this functionality.
    """

    def __init__(
        self,
        itx: Interaction,
        total_pages: Optional[int] = None,
        get_page: Optional[Callable] = None
    ) -> None:
        super().__init__(itx)

        self.index = 1
        self.total_pages = total_pages
        self.get_page = getattr(self, "get_page", get_page)

    @staticmethod
    def update_buttons(view: BasePaginator) -> None:
        is_first_page_check = view.index == 1
        is_last_page_check = view.index == view.total_pages

        view.children[0].disabled = is_first_page_check
        view.children[1].disabled = is_first_page_check
        view.children[3].disabled = is_last_page_check
        view.children[4].disabled = is_last_page_check

    @staticmethod
    def reset_index(
        view: BasePaginator,
        refreshed_data: list,
        length: Optional[int] = None
    ) -> BasePaginator:
        """
        Set the minimum page length in refresh pagination classes.

        Pass in `length` if it's not present in the paginator instance.

        This function returns the class instance for fluent-style chaining.
        """
        length = length or view.length
        view.total_pages = view.compute_total_pages(
            len(refreshed_data), length
        )
        view.index = min(view.index, view.total_pages)
        return view

    async def navigate(self, **kwargs) -> None:
        embs = await self.get_page()
        self.update_buttons(self)
        await self.itx.response.send_message(embeds=embs, view=self, **kwargs)

    async def edit_page(self, itx: Interaction) -> None:
        embs = await self.get_page()
        self.update_buttons(self)
        await itx.response.edit_message(embeds=embs, view=self)

    async def on_error(
        self,
        itx: Interaction,
        error: Exception,
        item: discord.ui.Item
    ) -> None:

        # We don't want to stop the view
        # for basic transformer / conditional errors
        if hasattr(error, "cause"):
            return await itx.response.send_message(
                error.cause, ephemeral=True
            )

        await super().on_error(itx, error, item)

    @staticmethod
    def compute_total_pages(total_results: int, results_per_page: int) -> int:
        return (((total_results - 1) // results_per_page) + 1) or 1


class Pagination(BasePaginator):
    """Pagination menu with support for direct queries to a specific page."""

    def __init__(
        self,
        itx: Interaction,
        total_pages: int,
        get_page: Optional[Callable] = None
    ) -> None:
        super().__init__(itx, total_pages, get_page)

    @staticmethod
    def update_buttons(view: Pagination) -> None:
        # Override parent method to update index button label too
        view.children[2].label = f"{view.index} / {view.total_pages}"

        is_first_page_check = view.index == 1
        is_last_page_check = view.index == view.total_pages

        view.children[0].disabled = is_first_page_check
        view.children[1].disabled = is_first_page_check
        view.children[3].disabled = is_last_page_check
        view.children[4].disabled = is_last_page_check

    @discord.ui.button(row=1, style=discord.ButtonStyle.primary, emoji=FIRST)
    async def first(self, itx: Interaction, _: discord.ui.Button) -> None:
        self.index = 1
        await self.edit_page(itx)

    @discord.ui.button(row=1, style=discord.ButtonStyle.primary, emoji=LEFT)
    async def previous(self, itx: Interaction, _: discord.ui.Button) -> None:
        self.index -= 1
        await self.edit_page(itx)

    @discord.ui.button(row=1)
    async def numeric(self, itx: Interaction, _: discord.ui.Button) -> None:
        modal = PaginatorInput(self)
        await itx.response.send_modal(modal)

    @discord.ui.button(row=1, style=discord.ButtonStyle.primary, emoji=RIGHT)
    async def next_page(self, itx: Interaction, _: discord.ui.Button) -> None:
        self.index += 1
        await self.edit_page(itx)

    @discord.ui.button(row=1, style=discord.ButtonStyle.primary, emoji=LAST)
    async def last_page(self, itx: Interaction, _: discord.ui.Button) -> None:
        self.index = self.total_pages
        await self.edit_page(itx)


class PaginationSimple(BasePaginator):
    """A regular pagination menu with no extra features."""

    def __init__(
        self,
        itx: Interaction,
        total_pages: int,
        get_page: Optional[Callable] = None
    ) -> None:
        super().__init__(itx, total_pages, get_page)

    @discord.ui.button(row=1, style=discord.ButtonStyle.primary, emoji=FIRST)
    async def first(self, itx: Interaction, _: discord.ui.Button) -> None:
        self.index = 1
        await self.edit_page(itx)

    @discord.ui.button(row=1, style=discord.ButtonStyle.primary, emoji=LEFT)
    async def previous(self, itx: Interaction, _: discord.ui.Button) -> None:
        self.index -= 1
        await self.edit_page(itx)

    @discord.ui.button(row=1, style=discord.ButtonStyle.primary, emoji=RIGHT)
    async def next_page(self, itx: Interaction, _: discord.ui.Button) -> None:
        self.index += 1
        await self.edit_page(itx)

    @discord.ui.button(row=1, style=discord.ButtonStyle.primary, emoji=LAST)
    async def last_page(self, itx: Interaction, _: discord.ui.Button) -> None:
        self.index = self.total_pages
        await self.edit_page(itx)


class RefreshPagination(BasePaginator):
    """Paginator for refreshing data, containing it's own refresh button."""

    def __init__(
        self,
        itx: Interaction,
        get_page: Optional[Callable] = None
    ) -> None:
        # Pagination size can change on refresh
        super().__init__(itx, None, get_page)

    # Override parent method to add new refresh parameter
    async def edit_page(self, itx: Interaction, refresh: bool = False) -> None:
        embs = await self.get_page(refresh)
        self.update_buttons(self)
        await itx.response.edit_message(embeds=embs, view=self)

    @discord.ui.button(row=2, style=discord.ButtonStyle.primary, emoji=FIRST)
    async def first(self, itx: Interaction, _: discord.ui.Button) -> None:
        self.index = 1
        await self.edit_page(itx)

    @discord.ui.button(row=2, style=discord.ButtonStyle.primary, emoji=LEFT)
    async def previous(self, itx: Interaction, _: discord.ui.Button) -> None:
        self.index -= 1
        await self.edit_page(itx)

    @discord.ui.button(row=2, emoji=REFRESH)
    async def refresh(self, itx: Interaction, _: discord.ui.Button) -> None:
        await self.edit_page(itx, refresh=True)

    @discord.ui.button(row=2, style=discord.ButtonStyle.primary, emoji=RIGHT)
    async def next_page(self, itx: Interaction, _: discord.ui.Button) -> None:
        self.index += 1
        await self.edit_page(itx)

    @discord.ui.button(row=2, style=discord.ButtonStyle.primary, emoji=LAST)
    async def last_page(self, itx: Interaction, _: discord.ui.Button) -> None:
        self.index = self.total_pages
        await self.edit_page(itx)


class PaginationItem(BasePaginator):
    """
    Pagination menu with forward and backward buttons only.

    Disabling logic has been stripped away.
    """

    def __init__(
        self,
        itx: Interaction,
        total_pages: int,
        get_page: Optional[Callable] = None
    ) -> None:
        super().__init__(itx, total_pages, get_page)

    # Override parent class response methods
    # Due to no button update logic required
    async def navigate(self, **kwargs) -> None:
        emb = await self.get_page()
        await self.itx.response.send_message(embeds=[emb], view=self, **kwargs)

    async def edit_page(self, itx: Interaction) -> None:
        emb = await self.get_page()
        await itx.response.edit_message(embeds=[emb], view=self)

    @discord.ui.button(row=2, emoji=LEFT)
    async def previous(self, itx: Interaction, _: discord.ui.Button) -> None:
        self.index = (self.index - 2) % self.total_pages + 1
        await self.edit_page(itx)

    @discord.ui.button(row=2, emoji=RIGHT)
    async def next_page(self, itx: Interaction, _: discord.ui.Button) -> None:
        self.index = (self.index % self.total_pages) + 1
        await self.edit_page(itx)
