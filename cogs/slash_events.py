from random import choice
from datetime import timedelta
from traceback import print_exception

from discord.ext import commands
from discord.ui import View, Button
from discord.utils import format_dt, utcnow
from discord import Embed, Interaction, app_commands, AppCommandOptionType

from cogs.economy import membed


COOLDOWN_PROMPTS = (
    "Too spicy, take a breather..", 
    "Take a chill pill", 
    "Woah now, slow it down",
    "Let's slow it down here", 
    "Slow it down bud", 
    "Spam isn't cool fam", 
    "Hold your horses...",
    "Pump the brakes, speed racer", 
    "CHILL OUT, DAMN", 
    "Easy tiger, let's not rush", 
    "Slow down there cowboy", 
    "Whoa there, slow down", 
    "Cool your jets, space cadet",
    "Easy does it, turbo"
)


class MessageDevelopers(View):
    def __init__(self):
        super().__init__(timeout=60.0)

        self.add_item(
            Button(
                label="Contact a developer", 
                url="https://www.discordapp.com/users/546086191414509599"
            )
        )
        

class SlashExceptionHandler(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client
        client.tree.error(coro=self.__dispatch_to_app_command_handler)

    async def __dispatch_to_app_command_handler(
            self, interaction: Interaction, error: app_commands.AppCommandError):
        self.client.dispatch("app_command_error", interaction, error)

    @commands.Cog.listener("on_app_command_error")
    async def get_app_command_error(
        self, interaction: Interaction, error: app_commands.AppCommandError):
        
        if isinstance(error, app_commands.CheckFailure):

            if isinstance(error, app_commands.MissingRole):
                exception = membed(f"You're missing a required role: <@&{error.missing_role}>")

            elif isinstance(error, app_commands.MissingPermissions):
                exception = membed("You're missing some permissions required to use this command.")

            elif isinstance(error, app_commands.CommandOnCooldown):
                exception = Embed()
                exception.title = choice(COOLDOWN_PROMPTS)
                
                exception.colour = 0x2B2D31
                after_cd = format_dt(utcnow() + timedelta(seconds=error.retry_after), style="R")
                exception.description = f"You can run this command again {after_cd}."
            else:
                return  # we already respond
        elif isinstance(error, app_commands.TransformerError):
            if error.type.value == AppCommandOptionType.user.value:
                exception = membed(f"{error.value} is not a member of this server.")
            else:
                exception = membed("An error occurred while processing your input.")
        elif isinstance(error, app_commands.CommandNotFound):
            exception = membed("This command no longer exists!")

        elif isinstance(error, app_commands.CommandAlreadyRegistered):
            exception = membed("Another command with this name already exists.")
        else:
            print_exception(type(error), error, error.__traceback__)
            exception = Embed(colour=0x2B2D31)
            exception.title = "Something went wrong"
            exception.description = (
                "Seems like the bot has stumbled upon an unexpected error. "
                "Not to worry, these things happen from time to time. If this issue persists, "
                "please let us know about it. We're always here to help!"
            )

        if not interaction.response.is_done():
            return await interaction.response.send_message(embed=exception, view=MessageDevelopers())
        await interaction.followup.send(embed=exception, view=MessageDevelopers())


async def setup(client: commands.Bot):
    await client.add_cog(SlashExceptionHandler(client))
