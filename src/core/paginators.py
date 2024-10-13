from typing import Callable, Optional, Self

import discord

from .bot import Interaction
from .helpers import BaseView, edit_response, respond
from .transformers import RawIntegerTransformer

REFRESH = discord.PartialEmoji.from_str("<:refreshPages:1263923160433168414>")
FIRST = discord.PartialEmoji.from_str("<:firstPage:1263921815345041460>")
LEFT = discord.PartialEmoji.from_str("<:leftPage:1263922081696059404>")
RIGHT = discord.PartialEmoji.from_str("<:rightPage:1263923290959773706>")
FINAL = discord.PartialEmoji.from_str("<:finalPage:1263921799633047573>")


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

        self.view.index = min(self.view.total_pages, true_page)
        await self.view.edit_page(itx)

    async def on_error(self, itx: Interaction, error: Exception) -> None:
        await self.view.on_error(itx, error, self)


class BasePaginator(BaseView):
    """The base paginator which all paginators should inherit from."""

    def __init__(
        self,
        itx: Interaction,
        get_page: Optional[Callable] = None
    ) -> None:
        super().__init__(itx)

        self.index = 1
        self.get_page = get_page
        self.total_pages: Optional[int] = None

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
    """
    Pagination menu with support for direct queries to a specific page.

    You are expected to return a list of embeds even
    if you only return one embed in your custom function.
    """

    def __init__(
        self,
        itx: Interaction,
        total_pages: int,
        get_page: Optional[Callable] = None
    ) -> None:
        super().__init__(itx, get_page)

        # Pagination size is fixed
        self.total_pages = total_pages

    async def navigate(self, **kwargs) -> None:
        embs = await self.get_page()

        if self.total_pages == 1:
            return await respond(self.itx, embeds=embs, **kwargs)

        self.update_buttons()
        await respond(self.itx, embeds=embs, view=self, **kwargs)

    async def edit_page(self, itx: Interaction) -> None:
        embs  = await self.get_page()
        self.update_buttons()
        await edit_response(itx, embeds=embs, view=self)

    def update_buttons(self) -> None:
        self.children[2].label = f"{self.index} / {self.total_pages}"

        is_first_page_check = self.index == 1
        is_last_page_check = self.index == self.total_pages

        self.children[0].disabled = is_first_page_check
        self.children[1].disabled = is_first_page_check
        self.children[3].disabled = is_last_page_check
        self.children[4].disabled = is_last_page_check

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

    @discord.ui.button(row=1, style=discord.ButtonStyle.primary, emoji=FINAL)
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
        super().__init__(itx, get_page)

        # Pagination size is fixed
        self.total_pages = total_pages

    async def navigate(self) -> None:
        emb = await self.get_page()

        if self.total_pages == 1:
            self.stop()
            return await self.itx.response.send_message(embed=emb)

        self.update_buttons()
        await self.itx.response.send_message(embed=emb, view=self)

    async def edit_page(self, itx: Interaction) -> None:
        emb = await self.get_page()
        self.update_buttons()
        await itx.response.edit_message(embed=emb, view=self)

    def update_buttons(self) -> None:
        is_first_page_check = self.index == 1
        is_last_page_check = self.index == self.total_pages

        self.children[0].disabled = is_first_page_check
        self.children[1].disabled = is_first_page_check
        self.children[2].disabled = is_last_page_check
        self.children[3].disabled = is_last_page_check

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

    @discord.ui.button(row=1, style=discord.ButtonStyle.primary, emoji=FINAL)
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
        super().__init__(itx, get_page)

    async def navigate(self) -> None:
        emb = await self.get_page()
        self.update_buttons()
        await self.itx.response.send_message(embed=emb, view=self)

    def reset_index(
        self,
        refreshed_data: list,
        length: Optional[int] = None
    ) -> Self:
        """
        Set the minimum page length in refresh pagination classes.

        Pass in `length` if it's not present in the paginator instance.

        This function returns the class instance for fluent-style chaining.

        This should not be used within select callbacks that refresh data.
        """
        length = length or self.length
        self.total_pages = self.compute_total_pages(
            len(refreshed_data), length
        )
        self.index = min(self.index, self.total_pages)
        return self

    async def edit_page(
        self,
        itx: Interaction,
        force_refresh: Optional[bool] = False
    ) -> None:
        emb = await self.get_page(force_refresh)
        self.update_buttons()
        await edit_response(itx, embed=emb, view=self)

    def update_buttons(self) -> None:
        is_first_page_check = self.index == 1
        is_last_page_check = self.index == self.total_pages

        self.children[0].disabled = is_first_page_check
        self.children[1].disabled = is_first_page_check
        self.children[3].disabled = is_last_page_check
        self.children[4].disabled = is_last_page_check

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
        await self.edit_page(itx, force_refresh=True)

    @discord.ui.button(row=2, style=discord.ButtonStyle.primary, emoji=RIGHT)
    async def next_page(self, itx: Interaction, _: discord.ui.Button) -> None:
        self.index += 1
        await self.edit_page(itx)

    @discord.ui.button(row=2, style=discord.ButtonStyle.primary, emoji=FINAL)
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
        super().__init__(itx, get_page)

        # Pagination size is fixed
        self.total_pages = total_pages

    async def navigate(self) -> None:
        emb = await self.get_page()
        await self.itx.response.send_message(embed=emb, view=self)

    async def edit_page(self, itx: Interaction) -> None:
        emb = await self.get_page()
        await edit_response(itx, embed=emb, view=self)

    @discord.ui.button(row=2, emoji=LEFT)
    async def previous(self, itx: Interaction, _: discord.ui.Button) -> None:
        self.index = (self.index - 2) % self.total_pages + 1
        await self.edit_page(itx)

    @discord.ui.button(row=2, emoji=RIGHT)
    async def next_page(self, itx: Interaction, _: discord.ui.Button) -> None:
        self.index = (self.index % self.total_pages) + 1
        await self.edit_page(itx)
