from random import choice
from datetime import timedelta
from traceback import print_exception

from discord import Embed
from discord.ext import commands
from discord.utils import format_dt, utcnow

from .core.views import MessageDevelopers
from .core.constants import COOLDOWN_PROMPTS


class ContextCommandHandler(commands.Cog):
    """The error handler for text-based commands that are called."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.err = commands.errors
        self.view = MessageDevelopers()

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, err: Exception):
        """The function that handles all the errors passed into the bot via text-based commands."""

        embed = Embed(colour=0x2B2D31)

        if isinstance(err, commands.errors.UserInputError):

            if isinstance(err, self.err.MissingRequiredArgument):
                embed.description = "Some required arguments are missing."
                return await ctx.reply(embed=embed, view=self.view)

            embed.description = "That didn't work. Check your inputs are valid."
            await ctx.reply(embed=embed, view=self.view)

        elif isinstance(err, self.err.CheckFailure):

            if isinstance(err, self.err.NotOwner):
                embed.description = "You do not own this bot."
                await ctx.reply(embed=embed, view=self.view)

            elif isinstance(err, self.err.MissingPermissions):
                embed.description = "You're missing permissions required to use this command."
                embed.add_field(
                    name=f"Missing Permissions ({len(err.missing_permissions)})", 
                    value="\n".join(err.replace('_', ' ').title() for err in err.missing_permissions)
                )
                await ctx.reply(embed=embed, view=self.view)

            elif isinstance(err, self.err.MissingRole):
                embed.description = "You're missing a role required to use this command."
                embed.add_field(name="Missing Role", value=f"<@&{err.missing_role}>")
                await ctx.reply(embed=embed, view=self.view)

        elif isinstance(err, self.err.CommandOnCooldown):
            embed.title = choice(COOLDOWN_PROMPTS)
            after_cd = format_dt(utcnow() + timedelta(seconds=err.retry_after), style="R")
            embed.description = f"You can run this command again {after_cd}."
            await ctx.send(embed=embed, view=self.view)

        elif isinstance(err, self.err.CommandNotFound):
            embed.description = "Could not find what you were looking for."
            await ctx.reply(embed=embed, view=self.view)

        else:
            print_exception(type(err), err, err.__traceback__)
            
            embed.title = "Something went wrong"
            embed.description = (
                "Seems like the bot has stumbled upon an unexpected error. "
                "Not to worry, these things happen from time to time. If this issue persists, "
                "please let us know about it. We're always here to help!"
            )
            
            await ctx.reply(embed=embed, view=self.view)


async def setup(bot: commands.Bot):
    """Setup function to initiate the cog."""
    await bot.add_cog(ContextCommandHandler(bot))
