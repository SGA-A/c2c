from typing import Any, Optional

import discord
from discord import app_commands

from ._types import BotExports
from .core.bot import Interaction
from .core.helpers import BaseView


class DevTools(BaseView):
    _last_result: Optional[Any] = None
    on_boarding = (
        "## Developer Panel\n"
        "Select the below options to get started.\n"
        "- **Quit**: Shut down the bot process gracefully.\n"
        "- **Sync**: Send a new command tree copy to Discord.\n"
        "- **Blanket**: Heavily nest the invocation channel with new lines."
    )

    def __init__(self, itx: Interaction) -> None:
        super().__init__(itx, self.on_boarding)
        self.last_clicked: Optional[discord.ui.Button] = None

    async def interaction_check(self, itx: Interaction):
        if itx.client.is_owner(itx.user):
            return True
        await itx.response.send_message(
            "You do not own this bot.",
            ephemeral=True
        )
        return False

    def disable_all(self, clicked: discord.ui.Button) -> None:
        self.reset_success(clicked)
        for item in self.children:
            item.disabled = True

    def reset_success(self, clicked: discord.ui.Button) -> None:
        clicked.style = discord.ButtonStyle.success
        if self.last_clicked:
            self.last_clicked.style = discord.ButtonStyle.secondary
        self.last_clicked = clicked

    @discord.ui.button(label="Quit")
    async def _quit(self, itx: Interaction, button: discord.ui.Button) -> None:
        self.disable_all(button)
        await itx.response.edit_message(view=self)
        await itx.client.close()

    @discord.ui.button(label="Sync")
    async def sync(self, itx: Interaction, button: discord.ui.Button) -> None:
        await itx.client.tree.sync(guild=None)

        self.reset_success(button)
        await itx.response.edit_message(view=self)

    @discord.ui.button(label="Blanket")
    async def blanket(self, itx: Interaction, btn: discord.ui.Button) -> None:
        await itx.channel.send(f".{'\n'*1900}\u200b")

        self.reset_success(btn)
        await self.itx.delete_original_response()
        await itx.response.send_message(self.on_boarding, view=self)

        self.itx = itx

    @discord.ui.button(emoji="<:terminatePages:1263923664433319957>")
    async def _stop(self, itx: Interaction, button: discord.ui.Button) -> None:
        self.stop()
        self.disable_all(button)
        await itx.response.edit_message(view=self)


@app_commands.command(description="Manage the bot")
async def devtools(itx: Interaction) -> None:
    view = DevTools(itx)
    await itx.response.send_message(view.on_boarding, view=view)


exports = BotExports([devtools])
