import datetime
from discord.utils import format_dt
from traceback import print_exception
from discord import Embed, Interaction, Colour
from discord.ext import commands
from discord.app_commands import AppCommandError, CheckFailure, MissingRole, MissingPermissions
from discord.app_commands import CommandOnCooldown, CommandNotFound, CommandAlreadyRegistered, CommandInvokeError


class SlashExceptionHandler(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client
        client.tree.error(coro=self.__dispatch_to_app_command_handler)

    async def __dispatch_to_app_command_handler(self, interaction: Interaction,
                                                error: AppCommandError):
        self.client.dispatch("app_command_error", interaction, error)

    @commands.Cog.listener("on_app_command_error")
    async def get_app_command_error(self, interaction: Interaction,
                                    error: AppCommandError):

        if not interaction.response.is_done():  
            await interaction.response.defer(thinking=True)  

        if isinstance(error, CheckFailure):
            exception = Embed(title='Exception', colour=Colour.dark_embed())
            exception.set_thumbnail(url="https://i.imgur.com/zGtq4Dp.png")
            if isinstance(error, MissingRole):  # when a user has a missing role

                exception.description = f'{interaction.user.name}, you are missing a role.'

                exception.add_field(name='Required Role', value=f"<@&{error.missing_role}>", inline=False)

            elif isinstance(error, MissingPermissions):  # when a user has missing permissions

                exception.description = (f"{interaction.user.name}, you're missing "
                                         f"some permissions required to use this command.")
                exception.add_field(name='Required permissions',
                                    value=', '.join(error.missing_permissions).title())

            elif isinstance(error, CommandOnCooldown):  # when the command a user executes is on cooldown
                exception.title = "Take a breather.."
                exception.set_thumbnail(url=None)
                exception.colour = 0x2B2D31
                after_cd = datetime.datetime.now() + datetime.timedelta(seconds=error.retry_after)
                exception.description = f"You can run this command {format_dt(after_cd, style='R')}."
            else:
                exception.description = "Conditions needed to call this command were not met."

            return await interaction.followup.send(embed=exception)

        if isinstance(error, CommandNotFound):
            content = Embed(
                description=f"The commmand with name {error.name} was not found.\n"
                            f"It may have been recently removed or replaced with an alternative.",
                colour=Colour.dark_embed())
            content.set_thumbnail(url="https://i.imgur.com/zGtq4Dp.png")

            return await interaction.followup.send(content)

        if isinstance(error, CommandAlreadyRegistered):

            content = Embed(
                description=f"{interaction.user.name}, this command is registered already?\n"
                            f"This is an issue with the bot, usually resolving itself within a few minutes.",
                colour=Colour.dark_embed())
            content.set_thumbnail(url="https://i.imgur.com/zGtq4Dp.png")
            return await interaction.followup.send(content)

        if isinstance(error, CommandInvokeError):

            print_exception(type(error), error, error.__traceback__)

            return await interaction.followup.send(
                embed=Embed(description=f"An invalid process took place for this command.\n"
                                        f"50% chance its a issue on your end, 50% chance on our end.\n"
                                        f"**The bot developers were notified.** "
                                        f"[See their progress.](https://github.com/SGA-A/c2c/issues)",
                            colour=Colour.dark_embed()).set_thumbnail(url="https://i.imgur.com/zGtq4Dp.png"))

        else:
            print_exception(type(error), error, error.__traceback__)
            cause = error.__cause__ or error
            return await interaction.followup.send(cause)


async def setup(client: commands.Bot):
    await client.add_cog(SlashExceptionHandler(client))
