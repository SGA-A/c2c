import discord
from traceback import print_exception
from typing import Optional, Callable


def membed(custom_description: str) -> discord.Embed:
    """Quickly create an embed with a custom description using the preset."""
    membedder = discord.Embed(colour=0x2F3136, description=custom_description)
    return membedder


class PaginatorInput(discord.ui.Modal):
    def __init__(self, their_view: discord.ui.View):
        self.their_view = their_view
        super().__init__(title="Input a Page", timeout=45.0)

    page_num = discord.ui.TextInput(
        style=discord.TextStyle.short,
        label='Page',
        required=True,
        min_length=1,
        max_length=2
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.edit_message(view=self.their_view)

    async def on_error(self, interaction: discord.Interaction, error):
        self.stop()
        await interaction.response.send_message("Something went wrong.")
        print_exception(type(error), error, error.__traceback__)


class Pagination(discord.ui.View):
    """Pagination menu with support for direct queries to a specific page."""
    
    def __init__(self, interaction: discord.Interaction, get_page: Optional[Callable] = None) -> None:
        self.interaction = interaction
        self.get_page = get_page
        self.index = 1
        self.total_pages: Optional[int] = None
        super().__init__(timeout=45.0)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Make sure only original user that invoked interaction can interact"""
        if interaction.user == self.interaction.user:
            return True
        emb = membed("You cannot interact with this menu")
        await interaction.response.send_message(embed=emb, ephemeral=True)
        return False

    async def on_timeout(self) -> None:
        try:
            for item in self.children:
                item.disabled = True
            message = await self.interaction.original_response()
            await message.edit(view=self)
        except discord.NotFound:
            pass

    async def navigate(self) -> None:
        """Get through the paginator properly."""
        emb, self.total_pages = await self.get_page(self.index)
        if self.total_pages == 1:
            self.stop()
            await self.interaction.response.send_message(embed=emb)
        elif self.total_pages > 1:
            self.update_buttons()
            await self.interaction.response.send_message(embed=emb, view=self)

    async def edit_page(self, interaction: discord.Interaction) -> None:
        """Update the page index in response to changes in the current page."""
        emb, self.total_pages = await self.get_page(self.index)
        self.update_buttons()
        if interaction.response.is_done():
            message = await interaction.original_response()
            return await interaction.followup.edit_message(
                message_id=message.id, embed=emb, view=self)
        await interaction.response.edit_message(embed=emb, view=self)

    def update_buttons(self) -> None:
        """Disable or re-enable buttons based on position in paginator."""

        self.children[2].label = f"{self.index} / {self.total_pages}"

        self.children[0].disabled = self.index <= 2
        self.children[1].disabled = self.index == 1
        self.children[3].disabled = self.index == self.total_pages
        self.children[4].disabled = self.index >= self.total_pages - 1

    @discord.ui.button(style=discord.ButtonStyle.blurple, emoji=discord.PartialEmoji.from_str("<:start:1212509961943252992>"), row=1)
    async def first(self, interaction: discord.Interaction, _: discord.Button) -> None:
        self.index = 1
        await self.edit_page(interaction)

    @discord.ui.button(style=discord.ButtonStyle.blurple, emoji=discord.PartialEmoji.from_str("<:left:1212498142726066237>"), row=1)
    async def previous(self, interaction: discord.Interaction, _: discord.Button) -> None:
        self.index -= 1
        await self.edit_page(interaction)

    @discord.ui.button(style=discord.ButtonStyle.gray, row=1)
    async def numeric(self, interaction: discord.Interaction, _: discord.Button) -> None:
        modal = PaginatorInput(their_view=self)
        await interaction.response.send_modal(modal)
        await modal.wait()
        val = modal.page_num.value

        if val is None:
            return
        
        try:
            val = abs(int(val))
        except ValueError:
            return await interaction.followup.send(
                embed=membed("You need to provide a real value."), ephemeral=True)

        if not val:
            return await interaction.followup.send(
                embed=membed("You need to type a positive value."),
                ephemeral=True)

        self.index = min(self.total_pages, val) 
        await self.edit_page(interaction)

    @discord.ui.button(style=discord.ButtonStyle.blurple, emoji=discord.PartialEmoji.from_str("<:right:1212498140620394548>"), row=1)
    async def next_page(self, interaction: discord.Interaction, _: discord.Button) -> None:
        self.index += 1
        await self.edit_page(interaction)

    @discord.ui.button(style=discord.ButtonStyle.blurple, emoji=discord.PartialEmoji.from_str("<:final:1212509960483643392>"), row=1)
    async def last_page(self, interaction: discord.Interaction, _: discord.Button) -> None:
        self.index = self.total_pages
        await self.edit_page(interaction)

    @staticmethod
    def compute_total_pages(total_results: int, results_per_page: int) -> int:
        """Based off the total elements available in the iterable, determine how many pages there
        should be within the paginator."""
        return ((total_results - 1) // results_per_page) + 1


class PaginationSimple(discord.ui.View):
    """Pagination menu soon with support for refreshing the pagination."""
    
    def __init__(self, interaction: discord.Interaction, get_page: Optional[Callable] = None) -> None:
        self.interaction = interaction
        self.get_page = get_page
        self.index = 1
        self.total_pages: Optional[int] = None
        super().__init__(timeout=45.0)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Make sure only original user that invoked interaction can interact"""
        if interaction.user == self.interaction.user:
            return True
        emb = membed("You cannot interact with this menu")
        await interaction.response.send_message(embed=emb, ephemeral=True)
        return False

    async def on_timeout(self) -> None:
        try:
            for item in self.children:
                item.disabled = True
            message = await self.interaction.original_response()
            await message.edit(view=self)
        except discord.NotFound:
            pass

    async def navigate(self) -> None:
        """Get through the paginator properly."""
        emb, self.total_pages = await self.get_page(self.index)
        if self.total_pages == 1:
            self.stop()
            await self.interaction.response.send_message(embed=emb)
        elif self.total_pages > 1:
            self.update_buttons()
            await self.interaction.response.send_message(embed=emb, view=self)

    async def edit_page(self, interaction: discord.Interaction) -> None:
        """Update the page index in response to changes in the current page."""
        emb, self.total_pages = await self.get_page(self.index)
        self.update_buttons()
        if interaction.response.is_done():
            message = await interaction.original_response()
            return await interaction.followup.edit_message(
                message_id=message.id, embed=emb, view=self)
        await interaction.response.edit_message(embed=emb, view=self)

    def update_buttons(self) -> None:
        """Disable or re-enable buttons based on position in paginator."""

        self.children[0].disabled = self.index <= 2
        self.children[1].disabled = self.index == 1
        self.children[2].disabled = self.index == self.total_pages
        self.children[3].disabled = self.index >= self.total_pages - 1

    @discord.ui.button(style=discord.ButtonStyle.blurple, emoji=discord.PartialEmoji.from_str("<:start:1212509961943252992>"), row=1)
    async def first(self, interaction: discord.Interaction, _: discord.Button) -> None:
        self.index = 1
        await self.edit_page(interaction)

    @discord.ui.button(style=discord.ButtonStyle.blurple, emoji=discord.PartialEmoji.from_str("<:left:1212498142726066237>"), row=1)
    async def previous(self, interaction: discord.Interaction, _: discord.Button) -> None:
        self.index -= 1
        await self.edit_page(interaction)

    @discord.ui.button(style=discord.ButtonStyle.blurple, emoji=discord.PartialEmoji.from_str("<:right:1212498140620394548>"), row=1)
    async def next_page(self, interaction: discord.Interaction, _: discord.Button) -> None:
        self.index += 1
        await self.edit_page(interaction)

    @discord.ui.button(style=discord.ButtonStyle.blurple, emoji=discord.PartialEmoji.from_str("<:final:1212509960483643392>"), row=1)
    async def last_page(self, interaction: discord.Interaction, _: discord.Button) -> None:
        self.index = self.total_pages
        await self.edit_page(interaction)

    @staticmethod
    def compute_total_pages(total_results: int, results_per_page: int) -> int:
        """Based off the total elements available in the iterable, determine how many pages there
        should be within the paginator."""
        return ((total_results - 1) // results_per_page) + 1


class PaginationItem(discord.ui.View):
    """Pagination menu with support for direct queries to a specific page."""
    
    def __init__(self, interaction: discord.Interaction, get_page: Optional[Callable] = None) -> None:
        self.interaction = interaction
        self.get_page = get_page
        self.index = 1
        self.total_pages: Optional[int] = None
        super().__init__(timeout=45.0)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Make sure only original user that invoked interaction can interact"""
        if interaction.user == self.interaction.user:
            return True
        emb = membed(
            f"This shop menu is controlled by {self.interaction.user.mention}, you will have to run the original command yourself.")
        await interaction.response.send_message(embed=emb, ephemeral=True)
        return False

    async def on_timeout(self) -> None:
        try:
            for item in self.children:
                item.disabled = True
            message = await self.interaction.original_response()
            await message.edit(view=self)
        except discord.NotFound:
            pass

    async def navigate(self) -> None:
        """Get through the paginator properly."""
        emb, self.total_pages = await self.get_page(self.index)
        if self.total_pages == 1:
            self.stop()
            return await self.interaction.response.send_message(embed=emb)
        await self.interaction.response.send_message(embed=emb, view=self)

    async def edit_page(self, interaction: discord.Interaction) -> None:
        """Update the page index in response to changes in the current page."""
        emb, self.total_pages = await self.get_page(self.index)
        if interaction.response.is_done():
            message = await interaction.original_response()
            return await interaction.followup.edit_message(
                message_id=message.id, embed=emb, view=self)
        await interaction.response.edit_message(embed=emb, view=self)

    @discord.ui.button(style=discord.ButtonStyle.grey, emoji=discord.PartialEmoji.from_str("<:left:1212498142726066237>"), row=2)
    async def previous(self, interaction: discord.Interaction, _: discord.Button) -> None:
        
        if self.index - 1 < 1:
            self.index = self.total_pages
        else:
            self.index -= 1
        await self.edit_page(interaction)

    @discord.ui.button(style=discord.ButtonStyle.grey, emoji=discord.PartialEmoji.from_str("<:right:1212498140620394548>"), row=2)
    async def next_page(self, interaction: discord.Interaction, _: discord.Button) -> None:
        if self.index + 1 > self.total_pages:
            self.index = 1
        else:
            self.index += 1
        await self.edit_page(interaction)

    @staticmethod
    def compute_total_pages(total_results: int, results_per_page: int) -> int:
        """Based off the total elements available in the iterable, determine how many pages there
        should be within the paginator."""
        return ((total_results - 1) // results_per_page) + 1
