from traceback import print_exception
from discord import Embed, Interaction
from discord.ext import commands
from discord.app_commands import AppCommandError, CheckFailure, MissingRole, MissingPermissions, CommandOnCooldown, CommandNotFound, CommandAlreadyRegistered, CommandInvokeError


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
        await interaction.response.defer(thinking=True)  # type: ignore
        if isinstance(error, CheckFailure):
            exception = Embed(title='Caught Exception of type CheckFailure',
                                      colour=0x2F3136)

            if isinstance(error, MissingRole):  # when a user has a missing role

                exception.description = (f'**{interaction.user.name}**, you are missing a role.\n\n'
                                         f'**Required Role**: <@&{error.missing_role}>')
                exception.set_footer(icon_url=self.client.user.avatar.url,
                                     text='you should already know why this error occurred!')

                return await interaction.followup.send(embed=exception)

            elif isinstance(error, MissingPermissions):  # when a user has missing permissions

                exception.description = (f"**{interaction.user.name}**, you lack some permissions required to use this "
                                         f"command.")
                exception.add_field(name='Required permissions',
                                    value=', '.join(error.missing_permissions))

                return await interaction.followup.send(embed=exception)

            elif isinstance(error, CommandOnCooldown):  # when the command a user executes is on cooldown
                exception.description = (f"**{interaction.user.name}**, this command is on cooldown!\n"
                                         f"you may use this command again after **{error.retry_after:.2f}** seconds.")

                return await interaction.followup.send(embed=exception)

        if isinstance(error, CommandNotFound):
            content = (
                f"**{interaction.user.name}**, the command of name **{error.name}** was not found (type {str(error.type)}). "
                f"it may have been recently removed or is replaced with an alternative.")

            return await interaction.followup.send(content)


        if isinstance(error, CommandAlreadyRegistered):

            content = (
                f"**{interaction.user.name}**, the command of name **{error.name}** is already registered "
                f"(possible overlook in function definitions)!\n"
                f"guild id this command was already registered at: `{error.guild_id}` (if `None` then it was a global "
                f"command).")

            return await interaction.followup.send(content)

        if isinstance(error, CommandInvokeError):
            content = (
                f"Unacceptable input for {interaction.command.name}, {interaction.user.name}.")

            print_exception(type(error), error, error.__traceback__)
            await interaction.followup.send(content)

        else:
            print_exception(type(error), error, error.__traceback__)
            cause = error.__cause__ or error
            return await interaction.followup.send(cause)


async def setup(client: commands.Bot):
    await client.add_cog(SlashExceptionHandler(client))
