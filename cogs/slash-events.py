from traceback import print_exception

import discord
from discord import Embed, Interaction
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

        if not interaction.response.is_done(): # type: ignore
            await interaction.response.defer(thinking=True) # type: ignore

        if isinstance(error, CheckFailure):
            exception = Embed(title='Exception', colour=0x2F3136)

            if isinstance(error, MissingRole):  # when a user has a missing role

                exception.description = f'{interaction.user.name}, you are missing a role.'

                exception.add_field(name='Required Role', value=f"<@&{error.missing_role}>", inline=False)

            elif isinstance(error, MissingPermissions):  # when a user has missing permissions

                exception.description = (f"{interaction.user.name}, you're missing "
                                         f"some permissions required to use this command.")
                exception.add_field(name='Required permissions',
                                    value=', '.join(error.missing_permissions))


            elif isinstance(error, CommandOnCooldown):  # when the command a user executes is on cooldown
                exception.description = (f"- **{interaction.user.name}**, you're on cooldown.\n"
                                         f" - You may use this command again after **{error.retry_after:.2f}** seconds.")

            else:
                exception.description = "Certain conditions needed to call this command were not met."

            # if isinstance(interaction.response.type, discord.InteractionResponseType.deferred_channel_message,) or if isinstance(interaction.response)
            return await interaction.followup.send(embed=exception)

        if isinstance(error, CommandNotFound):
            content = (
                f"- The commmand with name {error.name} was not found.\n"
                f"- It may have been recently removed or has been replaced with an alternative.")

            return await interaction.followup.send(content)


        if isinstance(error, CommandAlreadyRegistered):

            content = (
                f"- **{interaction.user.name}**, the command of name **{error.name}** is already registered.\n"
                f" - This may be a possible overlook in the function definitions (bot issue)\n"
                f" - The command is already registered at the guild with ID: `{error.guild_id}` (if `None` then it was a global "
                f"command).")

            return await interaction.followup.send(content)

        if isinstance(error, CommandInvokeError):

            print_exception(type(error), error, error.__traceback__)

            await interaction.followup.send(
                embed=Embed(description=f"## An invalid process for {interaction.command.name} took place.\n"
                                        f"- This is more likely a problem with the bot itself as the error was not "
                                        f"handled by the command itself.\n"
                                        f"- Regardless, you should check your input was valid before filing a report to "
                                        f"the c2c developers."))
        else:
            print_exception(type(error), error, error.__traceback__)
            cause = error.__cause__ or error
            return await interaction.followup.send(cause)


async def setup(client: commands.Bot):
    await client.add_cog(SlashExceptionHandler(client))
