from logging import error as log_error
from traceback import format_exception

from discord import Embed
from discord.ext import commands

from .core.views import MessageDevelopers


class ContextCommandHandler(commands.Cog):
    """The error handler for text-based commands that are called."""
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.view = MessageDevelopers()

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, err: Exception):
        """The function that handles all the errors passed into the bot via text-based commands."""

        embed = Embed(colour=0x2B2D31)
        err = getattr(err, "original", err)

        if isinstance(err, commands.CommandNotFound):
            embed.description = "Could not find what you were looking for."
            return await ctx.send(embed=embed, view=self.view)

        if isinstance(err, commands.UserInputError):

            if isinstance(err, commands.MissingRequiredArgument):
                embed.description = "Some required arguments are missing."
                return await ctx.send(embed=embed, view=self.view)

            embed.description = "That didn't work. Check your inputs are valid."
            return await ctx.send(embed=embed, view=self.view)

        if isinstance(err, commands.CheckFailure):
            if isinstance(err, commands.MissingPermissions):
                embed.description = "You're missing permissions required to use this command."
                embed.add_field(
                    name=f"Missing Permissions ({len(err.missing_permissions)})", 
                    value="\n".join(err.replace('_', ' ').title() for err in err.missing_permissions)
                )
                return await ctx.send(embed=embed, view=self.view)

            if isinstance(err, commands.MissingRole):
                embed.description = "You're missing a role required to use this command."
                embed.add_field(name="Missing Role", value=f"<@&{err.missing_role}>")
                return await ctx.send(embed=embed, view=self.view)
            return

        embed.title = "Something went wrong"
        embed.description = (
            "Seems like the bot has stumbled upon an unexpected error. "
            "Not to worry, these things happen from time to time. If this issue persists, "
            "please let us know about it. We're always here to help!"
        )
        await ctx.send(embed=embed, view=self.view)

        formatted_traceback = ''.join(format_exception(type(err), err, err.__traceback__))
        log_error(formatted_traceback)


async def setup(bot: commands.Bot):
    """Setup function to initiate the cog."""
    await bot.add_cog(ContextCommandHandler(bot))
