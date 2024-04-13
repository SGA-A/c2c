from traceback import print_exception
from datetime import timedelta

from discord.utils import format_dt, utcnow
from discord.ext import commands
from discord import Embed

from .economy import membed
from .slash_events import MessageDevelopers


class ContextCommandHandler(commands.Cog):
    """The error handler for text-based commands that are called."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.err = commands.errors

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, err: Exception):
        """The function that handles all the errors passed into the bot via text-based commands."""
        contact_view = MessageDevelopers()
        
        if isinstance(err, commands.errors.UserInputError):

            if isinstance(err, self.err.MissingRequiredArgument):
                return await ctx.reply(
                    embed=membed("Some required arguments are missing."),
                    view=contact_view
                )

            await ctx.reply(
                embed=membed("That didn't work. Check your inputs are valid."), 
                view=contact_view
            )

        elif isinstance(err, self.err.CheckFailure):

            if isinstance(err, self.err.NotOwner):
                await ctx.reply(
                    embed=membed("You do not own this bot."), 
                    view=contact_view, 
                    mention_author=False
                )

            elif isinstance(err, self.err.MissingPermissions):
                errorc = membed("You're missing some permissions required to use this command.")
                await ctx.reply(
                    embed=errorc, 
                    view=contact_view, 
                    mention_author=False)

            elif isinstance(err, self.err.MissingRole):

                embed = membed(f"You're missing a required role: <@&{err.missing_role}>")
                await ctx.reply(
                    embed=embed, 
                    mention_author=False, 
                    view=contact_view
                )

        elif isinstance(err, self.err.CommandOnCooldown):
            after_cd = format_dt(
                utcnow() + timedelta(seconds=err.retry_after), 
                style="R"
            )

            await ctx.reply(
                embed=membed(f"You're on a cooldown. Try again {after_cd}."),
                mention_author=False,
                view=contact_view
            )

        elif isinstance(err, self.err.CommandNotFound):
            await ctx.reply(
                embed=membed("Could not find what you were looking for."),
                mention_author=False,
                view=contact_view
            )

        else:
            print_exception(type(err), err, err.__traceback__)
            
            error = Embed(colour=0x2B2D31)
            error.title = "Something went wrong"
            error.description = (
                "Seems like the bot has stumbled upon an unexpected error. "
                "Not to worry, these things happen from time to time. If this issue persists, "
                "please let us know about it. We're always here to help!"
            )
            
            await ctx.reply(
                embed=error, 
                mention_author=False, 
                view=contact_view
            )


async def setup(bot: commands.Bot):
    """Setup function to initiate the cog."""
    await bot.add_cog(ContextCommandHandler(bot))
