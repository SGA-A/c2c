import discord
from typing import Callable, Optional


def membed(custom_description: str) -> discord.Embed:
    """Quickly create an embed with a custom description using the preset."""
    membedder = discord.Embed(colour=0x2F3136, description=custom_description)
    return membedder


class Pagination(discord.ui.View):
    
    def __init__(self, interaction: discord.Interaction, get_page: Callable) -> None:
        self.interaction = interaction
        self.get_page = get_page
        self.index = 1
        self.total_pages: Optional[int] = None
        super().__init__(timeout=45.0)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Make sure only original user that invoked interaction can interact"""
        if interaction.user == self.interaction.user:
            return True
        emb = membed("You have not created this interaction.")
        await interaction.response.send_message(embed=emb, ephemeral=True)  # type: ignore
        return False

    async def navigate(self) -> None:
        """Get through the paginator properly."""
        emb, self.total_pages = await self.get_page(self.index)
        if self.total_pages == 1:
            await self.interaction.response.send_message(embed=emb)  # type: ignore
        elif self.total_pages > 1:
            self.update_buttons()
            await self.interaction.response.send_message(embed=emb, view=self)  # type: ignore

    async def edit_page(self, interaction: discord.Interaction) -> None:
        """Update the page index in response to changes in the current page."""
        emb, self.total_pages = await self.get_page(self.index)
        self.update_buttons()
        await interaction.response.edit_message(embed=emb, view=self)  # type: ignore

    def update_buttons(self) -> None:
        """Disable or re-enable buttons based on position in paginator."""
        self.children[2].label = f"{self.index}/{self.total_pages}"  # type: ignore
        if self.index+1 > self.total_pages // 2:
            self.children[4].disabled = True  # type: ignore
        else:
            self.children[4].disabled = False  # type: ignore
            self.children[0].disabled = True  # type: ignore

        if self.index - 1:
            self.children[0].disabled = False  # type: ignore

        self.children[1].disabled = self.index == 1  # type: ignore
        self.children[3].disabled = self.index == self.total_pages  # type: ignore

    @discord.ui.button(label="FIRST", style=discord.ButtonStyle.green)
    async def first(self, interaction: discord.Interaction, button: discord.Button) -> None:
        self.index = 1
        await self.edit_page(interaction)

    @discord.ui.button(label="PREVIOUS", style=discord.ButtonStyle.green)
    async def previous(self, interaction: discord.Interaction, button: discord.Button) -> None:
        self.index -= 1
        await self.edit_page(interaction)

    @discord.ui.button(style=discord.ButtonStyle.gray, disabled=True)
    async def numeric(self, interaction: discord.Interaction, button: discord.Button) -> None:
        pass

    @discord.ui.button(label="NEXT", style=discord.ButtonStyle.green)
    async def next(self, interaction: discord.Interaction, button: discord.Button) -> None:
        self.index += 1
        await self.edit_page(interaction)

    @discord.ui.button(label="LAST", style=discord.ButtonStyle.green)
    async def last(self, interaction: discord.Interaction, button: discord.Button) -> None:
        self.index = self.total_pages
        await self.edit_page(interaction)

    async def on_timeout(self) -> None:
        try:
            for item in self.children:
                item.disabled = True
            message = await self.interaction.original_response()
            await message.edit(view=self)
        except discord.NotFound:
            pass

    @staticmethod
    def compute_total_pages(total_results: int, results_per_page: int) -> int:
        """Based off the total elements available in the iterable, determine how many pages there
        should be within the paginator."""
        return ((total_results - 1) // results_per_page) + 1
