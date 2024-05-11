from random import choice
from datetime import timedelta
from traceback import print_exception

from discord.ext import commands
from discord.utils import format_dt, utcnow
from discord import Interaction, app_commands, AppCommandOptionType

from .core.helpers import membed
from .core.views import MessageDevelopers
from .core.constants import COOLDOWN_PROMPTS


class SlashExceptionHandler(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        bot.tree.error(coro=self.__dispatch_to_app_command_handler)

    async def __dispatch_to_app_command_handler(
            self, 
            interaction: Interaction, 
            error: app_commands.AppCommandError
        ) -> None:
        self.bot.dispatch("app_command_error", interaction, error)

    @commands.Cog.listener("on_app_command_error")
    async def get_app_command_error(self, interaction: Interaction, error: app_commands.AppCommandError) -> None:

        if not interaction.response.is_done():
            await interaction.response.defer(thinking=True)

        embed = membed()

        if isinstance(error, app_commands.CheckFailure):

            if isinstance(error, app_commands.CommandOnCooldown):
                embed.title = choice(COOLDOWN_PROMPTS)
                after_cd = format_dt(utcnow() + timedelta(seconds=error.retry_after), style="R")
                embed.description = f"You can run this command again {after_cd}."
                return await interaction.followup.send(embed=embed)

            elif isinstance(error, app_commands.MissingRole):
                embed.description = "You're missing a role required to use this command."
                embed.add_field(name="Missing Role", value=f"<@&{error.missing_role}>")
                return await interaction.followup.send(embed=embed)
            
            else:
                return  # we already respond
            
        elif isinstance(error, app_commands.TransformerError):
            if error.type.value == AppCommandOptionType.user.value:
                embed.description = f"{error.value} is not a member of this server."
            else:
                embed.description = "An error occurred while processing your input."
        
        elif isinstance(error, app_commands.CommandNotFound):
            exception = membed("This command no longer exists!")

        elif isinstance(error, app_commands.CommandAlreadyRegistered):
            exception = membed("Another command with this name already exists.")
        
        else:
            print_exception(type(error), error, error.__traceback__)
            exception = membed(
                "Seems like the bot has stumbled upon an unexpected error. "
                "Not to worry, these things happen from time to time. If this issue persists, "
                "please let us know about it. We're always here to help!"
            )
            exception.title = "Something went wrong"

        await interaction.followup.send(embed=exception, view=MessageDevelopers())


async def setup(bot: commands.Bot):
    await bot.add_cog(SlashExceptionHandler(bot))
