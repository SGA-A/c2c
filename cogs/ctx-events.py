from traceback import print_exception
from discord import Embed
from discord.ext import commands
from discord.ext.commands import errors

class ContextCommandHandler(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, err: Exception):
        if isinstance(err, errors.MissingRequiredArgument):
            await ctx.reply(f"some required arguments are missing, which includes `{err.param.name}` of type **`{err.param.kind}`**.", mention_author=False)
        elif isinstance(err, errors.BadArgument):
            await ctx.reply("bad argument: a parsing or conversion failure has been encountered on an argument to pass into the command.")
        elif isinstance(err, errors.CheckFailure):
            if isinstance(err, errors.NotOwner):
                await ctx.reply(f"**{ctx.author.name}**, you are not the owner of this bot.", mention_author=False)
            elif isinstance(err, errors.MissingPermissions):
                await ctx.reply(f"**{ctx.author.name}**, you are missing the following permissions, {' '.join(err.missing_permissions)}", mention_author=False)
            elif isinstance(err, errors.MissingRole):
                await ctx.reply(f"**{ctx.author.name}**, you are missing the following role: <@&{err.missing_role}>", mention_author=False)
            elif isinstance(err, errors.NSFWChannelRequired):
                await ctx.reply(f"**{ctx.author.name}**, the channel you are currently in (<#{err.channel.id}>) **does not have the required NSFW setting.**", mention_author=False)
            elif isinstance(err, errors.NoPrivateMessage):
                embed = Embed(
                    description=f"## <:warningYellow:1159512635218342009> {ctx.author.name}, Do not send DMs here.\n"
                                f"- **Your messages are being monitored by the OAuth2 Bot API for event calls.**\n"
                                f" - *This is also the reason why you received this DM in the first place.*\n"
                                f"- You should use my commands in a server e.g. {ctx.author.mutual_guilds[0].name}",
                    colour=0x2F3136)
                msg = await ctx.send(embed=embed)
                await msg.delete(delay=15.0)
                return
            else:
                await ctx.reply(f"You have not met a prerequisite before executing this command.")

        elif isinstance(err, errors.MaxConcurrencyReached):
            await ctx.reply(f"**{ctx.author.name}**, you've reached max capacity of command usage at once, "
                            f"please finish the previous one first.", mention_author=False)

        elif isinstance(err, errors.CommandOnCooldown):
            if ctx.author.id in self.client.owner_ids:
                ctx.command.reset_cooldown(ctx)
                return await ctx.reply(f"The internal cooldown for {ctx.command.name} has been "
                                       f"reset for you, you may now call the command again.")
            await ctx.reply(f"**{ctx.author.name}**, this command is on cooldown... try again in {err.retry_after:.2f} seconds.", mention_author=False)

        elif isinstance(err, errors.CommandNotFound):
            await ctx.reply(f"**{ctx.author.name}**, the command you requested for was not found.", mention_author=False)

        else:
            await ctx.reply(f"{err.__cause__}", mention_author=False)
            print_exception(type(err), err, err.__traceback__)


async def setup(client):
    await client.add_cog(ContextCommandHandler(client))
