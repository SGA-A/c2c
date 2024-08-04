from random import choice
from datetime import timedelta
from traceback import format_exception
from logging import error as log_error

from discord.ext.commands import Cog, Bot
from discord.utils import format_dt, utcnow
from discord import (
    app_commands, 
    AppCommandOptionType,
    Embed,
    Interaction
)

from .core.views import MessageDevelopers
from .core.constants import COOLDOWN_PROMPTS


class SlashExceptionHandler(Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self.view = MessageDevelopers()

    def cog_load(self):
        tree = self.bot.tree
        self._old_tree_error, tree.on_error = tree.on_error, self.on_app_command_error

    def cog_unload(self):
        self.bot.tree.on_error = self._old_tree_error

    async def on_app_command_error(
        self, 
        interaction: Interaction, 
        error: app_commands.AppCommandError
    ) -> None:

        if not interaction.response.is_done():
            await interaction.response.defer(thinking=True)
        
        embed = Embed(colour=0x2B2D31)
        error = getattr(error, "original", error)

        if isinstance(error, app_commands.errors.TransformerError):
            if error.type.value == AppCommandOptionType.user.value:
                embed.description = f"{error.value} is not a member of this server."
            else:
                embed.description = "An error occurred while processing your input."
            return await interaction.followup.send(embed=embed, view=self.view)

        if isinstance(error, app_commands.errors.CheckFailure):
            if not isinstance(error, app_commands.errors.CommandOnCooldown):
                return  # we already respond
            
            embed.title = choice(COOLDOWN_PROMPTS)
            after_cd = format_dt(utcnow() + timedelta(seconds=error.retry_after), style="R")
            embed.description = f"You can run this command again {after_cd}."
            return await interaction.followup.send(embed=embed, view=self.view)

        if isinstance(error, app_commands.errors.CommandNotFound):
            embed.description = "This command no longer exists!"
            return await interaction.followup.send(embed=embed, view=self.view)

        if isinstance(error, app_commands.errors.CommandAlreadyRegistered):
            embed.description = "Another command with this name already exists."
            return await interaction.followup.send(embed=embed, view=self.view)

        embed.title = "Something went wrong"
        embed.description = (
            "Seems like the bot has stumbled upon an unexpected error. "
            "Not to worry, these things happen from time to time. If this issue persists, "
            "please let us know about it. We're always here to help!"
        )
        await interaction.followup.send(embed=embed, view=self.view)

        formatted_traceback = ''.join(format_exception(type(error), error, error.__traceback__))
        log_error(formatted_traceback)


async def setup(bot: Bot):
    await bot.add_cog(SlashExceptionHandler(bot))
