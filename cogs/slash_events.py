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

from .core.errors import CustomTransformerError, FailingConditionalError
from .core.views import MessageDevelopers
from .core.constants import COOLDOWN_PROMPTS


BASE_ERROR = app_commands.AppCommandError
UNHANDLED_CHECKS = (FailingConditionalError, app_commands.CommandOnCooldown)


class SlashExceptionHandler(Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self.view = MessageDevelopers()

    def cog_load(self):
        tree = self.bot.tree
        self._old_tree_error, tree.on_error = tree.on_error, self.on_app_command_error

    def cog_unload(self):
        self.bot.tree.on_error = self._old_tree_error

    def handle_unknown_exception(self, error: BASE_ERROR, embed: Embed):
        formatted_traceback = ''.join(format_exception(type(error), error, error.__traceback__))
        log_error(formatted_traceback)

        embed.title = "Something went wrong"
        embed.description = (
            "Seems like the bot has stumbled upon an unexpected error.\n"
            "Not to worry, these happen from time to time. If this issue persists, "
            "please let us know about it. We're always here to help!"
        )

    def handle_transformer_error(self, error: BASE_ERROR, embed: Embed):
        if isinstance(error, CustomTransformerError):
            embed.description = error.cause
        elif error.type.value == AppCommandOptionType.user.value:
            embed.description = f"{error.value} is not a member of this server."
        else:
            embed.description = "An error occurred while processing your input."

    def handle_check_failure(self, error: BASE_ERROR, embed: Embed):
        try:
            embed.description = error.cause
        except AttributeError:
            embed.title = choice(COOLDOWN_PROMPTS)
            cooldown_resets = utcnow() + timedelta(seconds=error.retry_after)
            after_cd = format_dt(cooldown_resets, style="R")
            embed.description = f"You can run this command again {after_cd}."

    async def on_app_command_error(self, interaction: Interaction, error: BASE_ERROR) -> None:

        if not interaction.response.is_done():
            await interaction.response.defer(thinking=True)

        embed = Embed(colour=0x2B2D31)
        error = getattr(error, "original", error)

        if isinstance(error, app_commands.TransformerError):
            self.handle_transformer_error(error, embed)
        elif isinstance(error, app_commands.CheckFailure):
            if not isinstance(error, UNHANDLED_CHECKS):
                return
            self.handle_check_failure(error, embed)
        elif isinstance(error, app_commands.CommandNotFound):
            embed.description = "This command no longer exists!"
        else:
            self.handle_unknown_exception(error, embed)
        await interaction.followup.send(embed=embed, view=self.view)


async def setup(bot: Bot):
    await bot.add_cog(SlashExceptionHandler(bot))
