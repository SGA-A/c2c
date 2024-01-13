from discord.ext import commands
from discord import Thread



class Moderation(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    @commands.command(name="close", description="close the invocation thread.")
    @commands.guild_only()
    async def close_thread(self, ctx: commands.Context):
        await ctx.message.delete()
        if isinstance(ctx.channel, Thread):
            permissions = ctx.channel.permissions_for(ctx.author)

            if permissions.manage_threads or (ctx.channel.owner_id == ctx.author.id):

                await ctx.send("<:padlocke:1195739398323581011> This thread has been auto-archived "
                               "and locked due to lack of use.\nIt may be re-opened if needed by contacting an admin.")
                await ctx.channel.edit(
                    locked=True,
                    archived=True,
                    reason=f'Marked as closed by {ctx.author} (ID: {ctx.author.id})'
                )
                return
            return await ctx.reply(
                "<:warning_nr:1195732155544911882> You don't have the required permissions.",
                mention_author=False)
        else:
            await ctx.reply("<:warning_nr:1195732155544911882> This is not a thread.", mention_author=False)

    @commands.command(name='delay', description='sets slowmode for the invoker channel.', aliases=('d',))
    @commands.has_permissions(manage_channels=True)
    async def set_delay(self, ctx: commands.Context, slowmode_in_seconds: int):
        """Sets a delay to which users can send messages. You must have the appropriate permissions."""
        slowmode_in_seconds = abs(slowmode_in_seconds)
        await ctx.channel.edit(slowmode_delay=slowmode_in_seconds)
        if slowmode_in_seconds:
            return await ctx.send(f'<:slowed:1195739862100353114> Slowmode set to {slowmode_in_seconds} seconds.')
        await ctx.send("<:normale:1195740534703136921> Disabled slowmode.")


    @commands.command(name="purge", description="bulk-remove messages, excluding pins.")
    @commands.has_permissions(manage_messages=True)
    @commands.guild_only()
    async def purge(self, ctx: commands.Context, purge_max_amount: int):
        """Purge an amount of messages. Pinned messages aren't removed."""

        dltd = await ctx.channel.purge(limit=purge_max_amount + 1, check=lambda msg: not msg.pinned, bulk=True)
        await ctx.send(content=f'Successfully deleted **{len(dltd)-1}** message(s).', delete_after=7.5, silent=True)


async def setup(client):
    await client.add_cog(Moderation(client))
