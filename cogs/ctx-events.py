from traceback import print_exception
from discord import Embed, Colour
from discord.ext import commands
from discord.ext.commands import errors


def membed(custom_description: str) -> Embed:
    """Quickly create an embed with a custom description using the preset."""
    membedder = Embed(colour=Colour.dark_embed(),
                      description=custom_description).set_thumbnail(url="https://i.imgur.com/zGtq4Dp.png")
    return membedder


class ContextCommandHandler(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, err: Exception):

        if isinstance(err, errors.UserInputError):

            if isinstance(err, errors.MissingRequiredArgument):
                await ctx.reply(
                    embed=membed(f"## A required argument is missing.\n"
                                 f"- `{err.param.name}` of type **`{err.param.kind}`**."), mention_author=False)

            elif isinstance(err, errors.BadArgument):
                await ctx.reply(
                    embed=membed("## Bad arguments were encountered:\n"
                                 "A parsing or conversion failure has been encountered on an argument "
                                 "to pass into the command. The errors that occur to make this happen are entirely due "
                                 "to Discord limitations. Meaning you are attempting to do something that is not possible "
                                 "under the limits of the API. Check what your inputs are, and try again."))
            else:
                params = ctx.command.params
                await ctx.reply(
                    embed=membed(f"## <Invalid Input Type\n"
                                 f"We expect these arguments from you when calling this command: {', '.join(params.keys())}"))

        elif isinstance(err, errors.CheckFailure):

            if isinstance(err, errors.NotOwner):
                await ctx.reply(
                    embed=membed(
                        f"## Checks Failed\n"
                        f"You are not the owner of this bot."), mention_author=False)

            elif isinstance(err, errors.MissingPermissions):

                errorc = Embed(
                    description=f"## Missing Permissions\n"
                                f"You're missing some permissions required to use this command.",
                    colour=0x2F3136)
                errorc.add_field(name='Required permissions',
                                    value=', '.join(err.missing_permissions), inline=False)
                await ctx.reply(embed=errorc, mention_author=False)

            elif isinstance(err, errors.MissingRole):

                exception = Embed(description=f'## You need a required role', colour=0x2F3136)
                exception.add_field(name='Required Role', value=f"<@&{err.missing_role}>", inline=False)
                await ctx.reply(embed=exception, mention_author=False)

            elif isinstance(err, errors.NoPrivateMessage):
                embed = membed(
                    f"## Do not send private messages.\n"
                    f"Use my commands in a server, for example in {ctx.author.mutual_guilds[0].name}.")
                msg = await ctx.send(embed=embed)
                await msg.delete(delay=15.0)
                return
            else:
                await ctx.reply(
                    embed=membed(f"## Checks Failed\n"
                                 f"You have not met a prerequisite before executing this command."),
                mention_author=False)

        elif isinstance(err, errors.CommandOnCooldown):
            exception = membed(f"You're on cooldown to avoid overloading the bot.\n"
                               f"Try again after **{err.retry_after:.2f}** seconds.")
            await ctx.reply(embed=exception)

        elif isinstance(err, errors.CommandNotFound):
            await ctx.reply(f"The command requested for was not found.", mention_author=False)

        else:
            await ctx.reply(
                embed=membed(f"## <:alerte:1195682149253271613> Something went wrong\n"
                             f"An error was encountered. The developers have been notified."))
            print_exception(type(err), err, err.__traceback__)


async def setup(client):
    await client.add_cog(ContextCommandHandler(client))
