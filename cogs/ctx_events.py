from traceback import print_exception
from datetime import timedelta

from discord.utils import format_dt, utcnow
from discord.ext import commands
from discord import Embed

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
        embed = Embed(colour=0x2B2D31)

        if isinstance(err, commands.errors.UserInputError):

            if isinstance(err, self.err.MissingRequiredArgument):
                embed.description = "Some required arguments are missing."
                return await ctx.reply(embed=embed, view=contact_view)
            
            embed.description = "That didn't work. Check your inputs are valid."
            await ctx.reply(embed=embed, view=contact_view)

        elif isinstance(err, self.err.CheckFailure):

            if isinstance(err, self.err.NotOwner):
                embed.description = "You do not own this bot."
                await ctx.reply(embed=embed, view=contact_view)

            elif isinstance(err, self.err.MissingPermissions):
                embed.description = f"You're missing {len(err.missing_permissions)} permission(s) required to use this command."
                embed.add_field(
                    name="Missing Permissions", 
                    value="\n".join(err.title() for err in err.missing_permissions)
                )
                await ctx.reply(embed=embed, view=contact_view)

            elif isinstance(err, self.err.MissingRole):
                embed.description = "You're missing a role required to use this command.")
                embed.add_field(name="Missing Role", value=f"<@&{err.missing_role}>")
                await ctx.reply(embed=embed, view=contact_view)

        elif isinstance(err, self.err.CommandOnCooldown):
            after_cd = format_dt(utcnow() + timedelta(seconds=err.retry_after), style="R")
            embed.description = f"You're on a cooldown. Try again {after_cd}."
            await ctx.reply(embed=embed, view=contact_view)

        elif isinstance(err, self.err.CommandNotFound):
            embed.description = "Could not find what you were looking for."
            await ctx.reply(embed=embed, view=contact_view)

        else:
            print_exception(type(err), err, err.__traceback__)
            
            embed.title = "Something went wrong"
            embed.description = (
                "Seems like the bot has stumbled upon an unexpected error. "
                "Not to worry, these things happen from time to time. If this issue persists, "
                "please let us know about it. We're always here to help!"
            )
            
            await ctx.reply(embed=embed, view=contact_view)


async def setup(bot: commands.Bot):
    """Setup function to initiate the cog."""
    await bot.add_cog(ContextCommandHandler(bot))
