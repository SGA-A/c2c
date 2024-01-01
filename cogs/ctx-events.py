from traceback import print_exception
from discord import Embed
from discord.ext import commands
from discord.ext.commands import errors


def membed(custom_description: str) -> Embed:
    """Quickly create an embed with a custom description using the preset."""
    membedder = Embed(colour=0x2F3136,
                           description=custom_description)
    return membedder


class ContextCommandHandler(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, err: Exception):

        if isinstance(err, errors.MissingRequiredArgument):
            print_exception(type(err), err, err.__traceback__)
            await ctx.reply(
                embed=membed(f"## A required argument is missing.\n"
                             f"- `{err.param.name}` of type **`{err.param.kind}`**."), mention_author=False)

        elif isinstance(err, errors.BadArgument):
            print_exception(type(err), err, err.__traceback__)
            await ctx.reply(
                embed=membed("## Bad arguments were encountered:\n"
                             "A parsing or conversion failure has been encountered on an argument "
                             "to pass into the command. This is an issue with the bot, you should report this to the "
                             "c2c developers."))

        elif isinstance(err, errors.CheckFailure):

            if isinstance(err, errors.NotOwner):
                await ctx.reply(f"You are not the owner of this bot.", mention_author=False)

            elif isinstance(err, errors.MissingPermissions):

                errorc = Embed(
                    description=f"You're missing some permissions required to use this command.", colour=0x2F3136)
                errorc.add_field(name='Required permissions',
                                    value=', '.join(err.missing_permissions), inline=False)
                await ctx.reply(embed=errorc, mention_author=False)

            elif isinstance(err, errors.MissingRole):

                exception = Embed(description=f'## You are missing a role.', colour=0x2F3136)
                exception.add_field(name='Required Role', value=f"<@&{err.missing_role}>", inline=False)
                await ctx.reply(embed=exception, mention_author=False)

            elif isinstance(err, errors.NoPrivateMessage):
                embed = membed(
                    f"## <:warningYellow:1159512635218342009> {ctx.author.name}, Do not send DMs here.\n"
                    f"- **Your messages are being monitored by the OAuth2 Bot API for event calls.**\n"
                    f" - *This is also the reason why you received this DM in the first place.*\n"
                    f"- You should use my commands in a server e.g. {ctx.author.mutual_guilds[0].name}")
                msg = await ctx.send(embed=embed)
                await msg.delete(delay=15.0)
                return
            else:
                await ctx.reply(f"You have not met a prerequisite before executing this command.")

        elif isinstance(err, errors.MaxConcurrencyReached):
            await ctx.reply(f"You've reached max capacity of command usage at once, "
                            f"please finish the previous one first.", mention_author=False)

        elif isinstance(err, errors.CommandOnCooldown):
            if ctx.author.id in self.client.owner_ids:
                ctx.command.reset_cooldown(ctx)
                return await ctx.reply(f"The internal cooldown for {ctx.command.name} has been "
                                       f"reset for you, you may now call the command again.")
            await ctx.reply(f"This command is on cooldown... try again in {err.retry_after:.2f} seconds.",
                            mention_author=False)

        elif isinstance(err, errors.CommandNotFound):
            await ctx.reply(f"The command requested for was not found.",
                            mention_author=False)
        else:
            print_exception(type(err), err, err.__traceback__)


async def setup(client):
    await client.add_cog(ContextCommandHandler(client))
