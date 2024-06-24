from random import choice
from datetime import timedelta
from traceback import format_exception
from logging import error as log_error

from discord.ext import commands
from discord.utils import format_dt, utcnow
from discord import (
    app_commands, 
    AppCommandOptionType,
    Embed,
    Interaction
)

from .core.views import MessageDevelopers
from .core.constants import COOLDOWN_PROMPTS


class SlashExceptionHandler(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        bot.tree.error(coro=self.get_app_command_error)
        self.view = MessageDevelopers()

    async def get_app_command_error(
        self, 
        interaction: Interaction, 
        app_cmd_error: app_commands.AppCommandError
    ) -> None:

        if not interaction.response.is_done():
            await interaction.response.defer(thinking=True)
        
        embed = Embed(colour=0x2B2D31)

        if isinstance(app_cmd_error, app_commands.CheckFailure):

            if not isinstance(app_cmd_error, app_commands.CommandOnCooldown):
                return  # we already respond
            
            embed.title = choice(COOLDOWN_PROMPTS)
            after_cd = format_dt(utcnow() + timedelta(seconds=app_cmd_error.retry_after), style="R")
            embed.description = f"You can run this command again {after_cd}."
            return await interaction.followup.send(embed=embed, view=self.view)

        if isinstance(app_cmd_error, app_commands.TransformerError):

            if app_cmd_error.type.value == AppCommandOptionType.user.value:
                embed.description = f"{app_cmd_error.value} is not a member of this server."
            else:
                embed.description = "An app_cmd_error occurred while processing your input."
            return await interaction.followup.send(embed=embed, view=self.view)

        if isinstance(app_cmd_error, app_commands.CommandNotFound):
            embed.description = "This command no longer exists!"
            return await interaction.followup.send(embed=embed, view=self.view)

        if isinstance(app_cmd_error, app_commands.CommandAlreadyRegistered):
            embed.description = "Another command with this name already exists."
            return await interaction.followup.send(embed=embed, view=self.view)

        else:
            embed.title = "Something went wrong"
            embed.description = (
                "Seems like the bot has stumbled upon an unexpected error. "
                "Not to worry, these things happen from time to time. If this issue persists, "
                "please let us know about it. We're always here to help!"
            )
            await interaction.followup.send(embed=embed, view=self.view)

            formatted_traceback = ''.join(format_exception(type(app_cmd_error), app_cmd_error, app_cmd_error.__traceback__))
            log_error(formatted_traceback)


async def setup(bot: commands.Bot):
    await bot.add_cog(SlashExceptionHandler(bot))
