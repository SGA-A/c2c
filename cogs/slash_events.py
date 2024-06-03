from random import choice
from datetime import timedelta
from traceback import format_exc

from discord.ext import commands
from discord.utils import format_dt, utcnow
from discord import Interaction, app_commands, AppCommandOptionType, Embed

from .core.views import MessageDevelopers
from .core.constants import COOLDOWN_PROMPTS


class SlashExceptionHandler(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        bot.tree.error(coro=self.get_app_command_error)
        self.kwargs = {"embed": Embed(colour=0x2B2D31), "view": MessageDevelopers()}
        self.console_logs_channel = bot.get_partial_messageable(1152342672405704754, guild_id=829053898333225010)

    async def get_app_command_error(
        self, 
        interaction: Interaction, 
        error: app_commands.AppCommandError
    ) -> None:

        if not interaction.response.is_done():
            await interaction.response.defer(thinking=True)
        
        embed = self.kwargs["embed"]
        embed.title = None

        if isinstance(error, app_commands.CheckFailure):

            if not isinstance(error, app_commands.CommandOnCooldown):
                return  # we already respond
            
            embed.title = choice(COOLDOWN_PROMPTS)
            after_cd = format_dt(utcnow() + timedelta(seconds=error.retry_after), style="R")
            embed.description = f"You can run this command again {after_cd}."
            return await interaction.followup.send(**self.kwargs)
            
        elif isinstance(error, app_commands.TransformerError):

            if error.type.value == AppCommandOptionType.user.value:
                embed.description = f"{error.value} is not a member of this server."
            else:
                embed.description = "An error occurred while processing your input."
            return await interaction.followup.send(**self.kwargs)
        
        elif isinstance(error, app_commands.CommandNotFound):
            embed.description = "This command no longer exists!"
            return await interaction.followup.send(**self.kwargs)

        elif isinstance(error, app_commands.CommandAlreadyRegistered):
            embed.description = "Another command with this name already exists."
            return await interaction.followup.send(**self.kwargs)
        
        else:
            embed.description = (
                "Seems like the bot has stumbled upon an unexpected error. "
                "Not to worry, these things happen from time to time. If this issue persists, "
                "please let us know about it. We're always here to help!"
            )
            embed.title = "Something went wrong"

            await interaction.followup.send(**self.kwargs)

            exc = format_exc().split("The above exception", maxsplit=1)[0]
            
            try:
                await self.console_logs_channel.send(f'```py\n{exc}\n```')
            except Exception:
                pass


async def setup(bot: commands.Bot):
    await bot.add_cog(SlashExceptionHandler(bot))
