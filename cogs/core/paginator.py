from typing import Callable

import discord
from discord.ext import commands

from .helpers import membed, determine_exponent, economy_check


NOT_YOUR_MENU = membed("This menu is not for you.")

# Button emojis
GO_FIRST_PAGE_EMOJI = discord.PartialEmoji.from_str("<:start:1212509961943252992>")
MOVE_LEFT_EMOJI = discord.PartialEmoji.from_str("<:left:1212498142726066237>")
MOVE_RIGHT_EMOJI = discord.PartialEmoji.from_str("<:right:1212498140620394548>")
GO_LAST_PAGE_EMOJI = discord.PartialEmoji.from_str("<:final:1212509960483643392>")


async def button_response(interaction: discord.Interaction, **kwargs) -> None | discord.Message:
    if interaction.response.is_done():
        return await interaction.edit_original_response(**kwargs)
    return await interaction.response.edit_message(**kwargs)


class PaginatorInput(discord.ui.Modal):
    def __init__(self, their_view: 'Pagination'):
        self.interaction: discord.Interaction | None = None
        self.page_num.placeholder = f"A number between 1 and {their_view.total_pages}."
        super().__init__(title="Input a Page", timeout=45.0)

    page_num = discord.ui.TextInput(
        label='Page',
        min_length=1,
        max_length=4
    )

    async def on_submit(self, interaction: discord.Interaction):
        self.interaction = interaction
        self.stop()


class Pagination(discord.ui.View):
    """Pagination menu with support for direct queries to a specific page."""
    
    def __init__(self, interaction: discord.Interaction, get_page: Callable | None = None) -> None:
        self.interaction = interaction
        self.get_page = get_page
        self.index = 1
        self.total_pages: int | None = None
        super().__init__(timeout=45.0)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Make sure only original user that invoked interaction can interact"""
        if interaction.user == self.interaction.user:
            return True
        await interaction.response.send_message(embed=NOT_YOUR_MENU, ephemeral=True)
        return False

    async def on_timeout(self) -> None:

        for item in self.children:
            item.disabled = not(hasattr(item, "url") and item.url)

        try:
            await self.interaction.edit_original_response(view=self)
        except discord.NotFound:
            pass

    async def navigate(self, **kwargs) -> None:
        """Get through the paginator properly."""
        emb, self.total_pages = await self.get_page(self.index)
        
        kwargs.update({"embed": emb})

        if isinstance(emb, list):
            del kwargs["embed"]
            kwargs.update({"embeds": emb})
        
        if self.total_pages == 1:
            self.stop()
        elif self.total_pages > 1:
            kwargs.update({"view": self})
            self.update_buttons()
        
        await self.interaction.response.send_message(**kwargs)

    async def edit_page(self, interaction: discord.Interaction) -> None:
        """Update the page index in response to changes in the current page."""

        emb, self.total_pages = await self.get_page(self.index)
        self.update_buttons()
        kwargs = {"view": self}
        kwargs.update({"embeds" if isinstance(emb, list) else "embed": emb})

        await button_response(interaction, **kwargs)

    def update_buttons(self) -> None:
        """Disable or re-enable buttons based on position in paginator."""

        self.children[2].label = f"{self.index} / {self.total_pages}"

        is_first_item_check = self.index == 1
        is_last_item_check = self.index == self.total_pages

        self.children[0].disabled = is_first_item_check
        self.children[1].disabled = is_first_item_check
        self.children[3].disabled = is_last_item_check
        self.children[4].disabled = is_last_item_check

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

        val = await determine_exponent(modal.interaction, modal.page_num.value)
        
        if val is None:
            return
        
        if isinstance(val, str):
            return await modal.interaction.response.send_message(
                ephemeral=True, 
                embed=membed("Invalid page number.")
            )

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

    @staticmethod
    def compute_total_pages(total_results: int, results_per_page: int) -> int:
        """
        Based off the total elements available in the iterable, 
        determine how many pages there should be within the paginator."""
        return ((total_results - 1) // results_per_page) + 1


class PaginationSimple(discord.ui.View):
    """A regular pagination menu with no extra features."""

    def __init__(self, ctx, invoker_id: int, get_page: Callable | None = None) -> None:
        self.ctx: commands.Context | discord.Interaction = ctx
        self.invoker_id = invoker_id
        self.get_page = get_page
        self.index = 1
        self.total_pages: int | None = None
        super().__init__(timeout=45.0)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Make sure only original user that invoked interaction can interact"""
        if interaction.user.id == self.invoker_id:
            return True
        await interaction.response.send_message(embed=NOT_YOUR_MENU, ephemeral=True)
        return False

    async def on_timeout(self) -> None:
        for item in self.children:
            item.disabled = True

        try:
            await self.message.edit(view=self)
        except discord.NotFound:
            pass

    async def navigate(self) -> None:
        """Get through the paginator properly."""
        emb, self.total_pages = await self.get_page(self.index)
        kwargs = {"embed": emb, "view": self}

        match self.total_pages:
            case 1:
                self.stop()
                del kwargs["view"]
            case _:
                self.update_buttons()

        # is it an interaction?
        if hasattr(self.ctx, "response"):
            await self.ctx.response.send_message(**kwargs)

            if self.is_finished():
                return
            self.message = await self.ctx.original_response()
            return

        if self.is_finished():
            return await self.ctx.send(**kwargs)
        self.message = await self.ctx.send(**kwargs)

    async def edit_page(self, interaction: discord.Interaction) -> None:
        """Update the page index in response to changes in the current page."""
    
        emb, self.total_pages = await self.get_page(self.index)
        self.update_buttons()
        await button_response(interaction, embed=emb, view=self)

    def update_buttons(self) -> None:
        """Disable or re-enable buttons based on position in paginator."""

        is_first_item_check = self.index == 1
        is_last_item_check = self.index == self.total_pages

        self.children[0].disabled = is_first_item_check
        self.children[1].disabled = is_first_item_check
        self.children[2].disabled = is_last_item_check
        self.children[3].disabled = is_last_item_check

    @discord.ui.button(style=discord.ButtonStyle.blurple, emoji=GO_FIRST_PAGE_EMOJI, row=0)
    async def first(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        self.index = 1
        await self.edit_page(interaction)

    @discord.ui.button(style=discord.ButtonStyle.blurple, emoji=MOVE_LEFT_EMOJI, row=0)
    async def previous(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        self.index -= 1
        await self.edit_page(interaction)

    @discord.ui.button(style=discord.ButtonStyle.blurple, emoji=MOVE_RIGHT_EMOJI, row=0)
    async def next_page(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        self.index += 1
        await self.edit_page(interaction)

    @discord.ui.button(style=discord.ButtonStyle.blurple, emoji=GO_LAST_PAGE_EMOJI, row=0)
    async def last_page(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        self.index = self.total_pages
        await self.edit_page(interaction)

    @staticmethod
    def compute_total_pages(total_results: int, results_per_page: int) -> int:
        return ((total_results - 1) // results_per_page) + 1


class RefreshPagination(discord.ui.View):
    """Based on `PaginationSimple`, but with an option to refresh the data being paginated."""
    def __init__(self, interaction: discord.Interaction, get_page: Callable | None = None) -> None:
        self.interaction = interaction
        self.get_page = get_page
        self.index = 1
        self.total_pages: int | None = None
        super().__init__(timeout=45.0)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Make sure only original user that invoked interaction can interact"""
        return await economy_check(interaction, self.interaction.user)

    async def on_timeout(self) -> None:
        for item in self.children:
            item.disabled = True

        try:
            await self.interaction.edit_original_response(view=self)
        except discord.NotFound:
            pass

    async def navigate(self) -> None:
        """Get through the paginator properly."""
        emb, self.total_pages = await self.get_page(self.index)
        kwargs = {"embed": emb, "view": self}

        match self.total_pages:
            case 1:
                self.stop()
                del kwargs["view"]
            case _:
                self.update_buttons()

        await self.interaction.response.send_message(**kwargs)

    async def edit_page(self, interaction: discord.Interaction, force_refresh: bool | None = False) -> None:
        """Update the page index in response to changes in the current page."""
        emb, self.total_pages = await self.get_page(self.index, force_refresh)

        self.update_buttons()
        await button_response(interaction, embed=emb, view=self)

    def update_buttons(self) -> None:
        """Disable or re-enable buttons based on position in paginator."""
        is_first_item_check = self.index == 1
        is_last_item_check = self.index == self.total_pages
        
        self.children[0].disabled = is_first_item_check
        self.children[1].disabled = is_first_item_check
        self.children[3].disabled = is_last_item_check
        self.children[4].disabled = is_last_item_check

    @discord.ui.button(style=discord.ButtonStyle.blurple, emoji=GO_FIRST_PAGE_EMOJI, row=1)
    async def first(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        self.index = 1
        await self.edit_page(interaction)

    @discord.ui.button(style=discord.ButtonStyle.blurple, emoji=MOVE_LEFT_EMOJI, row=1)
    async def previous(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        self.index -= 1
        await self.edit_page(interaction)

    @discord.ui.button(emoji="<:refreshicon:1205432056369389590>", row=1)
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

    @staticmethod
    def compute_total_pages(total_results: int, results_per_page: int) -> int:
        return ((total_results - 1) // results_per_page) + 1


class PaginationItem(discord.ui.View):
    """
    Pagination menu with forward and backward buttons only.
    
    Disabling logic has been stripped away.
    """
    
    def __init__(self, interaction: discord.Interaction, get_page: Callable | None = None) -> None:
        self.interaction = interaction
        self.get_page = get_page
        self.index = 1
        self.total_pages: int | None = None
        super().__init__(timeout=45.0)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Make sure only original user that invoked interaction can interact"""
        return await economy_check(interaction, self.interaction.user)

    async def on_timeout(self) -> None:
        for item in self.children:
            item.disabled = True

        try:
            await self.interaction.edit_original_response(view=self)
        except discord.NotFound:
            pass

    async def navigate(self, **kwargs) -> None:
        """Get through the paginator properly."""
        emb, self.total_pages = await self.get_page(self.index)
        kwargs.update({"embed": emb, "view": self})

        await self.interaction.response.send_message(**kwargs)

    async def edit_page(self, interaction: discord.Interaction) -> None:
        """Update the page index in response to changes in the current page."""        
        emb, self.total_pages = await self.get_page(self.index)
        await button_response(interaction, embed=emb, view=self)

    @discord.ui.button(style=discord.ButtonStyle.grey, emoji=MOVE_LEFT_EMOJI, row=2)
    async def previous(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        self.index = (self.index - 2) % self.total_pages + 1
        await self.edit_page(interaction)

    @discord.ui.button(style=discord.ButtonStyle.grey, emoji=MOVE_RIGHT_EMOJI, row=2)
    async def next_page(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        self.index = (self.index % self.total_pages) + 1
        await self.edit_page(interaction)

    @staticmethod
    def compute_total_pages(total_results: int, results_per_page: int) -> int:
        """Based off the total elements available in the iterable, determine how many pages there
        should be within the paginator."""
        return ((total_results - 1) // results_per_page) + 1


class RefreshSelectPagination(PaginationItem):
    """
    A pagination menu that has its pages changed 
    each time a different select menu option is selected.

    You should instantiate the select menu first before this view.

    Inherits from the `PaginationItem` class.
    """

    def __init__(
        self, 
        interaction: discord.Interaction, 
        select: discord.ui.Select, 
        get_page: Callable | None = None
    ) -> None:
        
        super().__init__(interaction, get_page=get_page)
        self.add_item(select)


class RefreshSelectPaginationExtended(RefreshPagination):
    """
    Similar to `RefreshSelectPagination`, but with a refresh button as well.
    
    The conditions for it apply to this one as well.

    Inherits from the `RefreshPagination` class.
    """

    def __init__(
        self, 
        interaction: discord.Interaction,
        select: discord.ui.Select, 
        get_page: Callable | None = None
    ) -> None:
        
        super().__init__(interaction, get_page=get_page)
        self.add_item(select)

    async def navigate(self) -> None:
        """Get through the paginator properly."""
        emb, self.total_pages = await self.get_page(self.index)
        self.update_buttons()

        await self.interaction.response.send_message(embed=emb, view=self)
    

