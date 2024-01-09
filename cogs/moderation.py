from discord import abc, Thread, HTTPException, NotFound, Forbidden, Member
from discord.ext import commands


class Moderation(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    @staticmethod
    async def lock_and_close(thread: Thread, user: abc.User) -> None:

        await thread.edit(
            locked=True,
            archived=True,
            reason=f'Requested by {user} (ID: {user.id})'
        )

    @commands.command(name="close", description="close the invocation thread.")
    @commands.guild_only()
    async def close_thread(self, ctx: commands.Context):
        await ctx.message.delete()
        if isinstance(ctx.channel, Thread):
            permissions = ctx.channel.permissions_for(ctx.author)

            if permissions.manage_threads or (ctx.channel.owner_id == ctx.author.id):

                await ctx.send("This thread has been auto-archived and locked due to lack of use.\n"
                               "It may be re-opened if needed by contacting an admin.")
                await ctx.channel.edit(
                    locked=True,
                    archived=True,
                    reason=f'Marked as closed by {ctx.author} (ID: {ctx.author.id})'
                )
                return
            return await ctx.reply("You don't have the necessary permissions.", mention_author=False)
        else:
            await ctx.reply("This is not a thread.", mention_author=False)

    @commands.command(name="kick", description="kicks a user from the invocation server.")
    @commands.has_permissions(kick_members=True)
    @commands.guild_only()
    async def kick(self, ctx: commands.Context, user_to_kick: Member):
        """Kicks a member. This member must be mentioned. You must have the appropriate permissions."""
        try:
            await user_to_kick.kick(reason=f'Requested by {ctx.author.name}.')
            await ctx.message.add_reaction('<:successful:1183089889269530764>')
        except Forbidden:
            return await ctx.send(f"You are missing permissions required to ban a user.")
        except HTTPException:
            return await ctx.send("Failed to kick this user.")

    @commands.command(name="ban", description="bans a user from the invocation server.")
    @commands.has_permissions(ban_members=True)
    @commands.guild_only()
    async def ban(self, ctx: commands.Context, user_to_ban: Member):
        try:
            await user_to_ban.ban(delete_message_seconds=604800, reason=f"Requested by {ctx.author.name}.")
            await ctx.message.add_reaction('<:successful:1183089889269530764>')
        except NotFound:
            return await ctx.send("Could not find that user.")
        except Forbidden:
            return await ctx.send(f"You are missing permissions required to ban a user.")
        except HTTPException:
            return await ctx.send("Failed to ban this user.")

    @commands.command(name='setdelay', description='sets slowmode for the invoker channel.')
    @commands.has_permissions(manage_channels=True)
    async def set_delay(self, ctx: commands.Context, slowmode_in_seconds: int):
        """Sets a delay to which users can send messages. You must have the appropriate permissions."""

        await ctx.channel.edit(slowmode_delay=slowmode_in_seconds)
        await ctx.message.add_reaction('<:successful:1183089889269530764>')

    @commands.command(name="cc", description="create a text channel to the invoker guild.")
    @commands.has_permissions(manage_channels=True)
    @commands.guild_only()
    async def add_channel(self, ctx: commands.Context, channel_name: str):
        """Creates a channel. You must have the appropriate permissions."""
        await ctx.guild.create_text_channel(channel_name, category=ctx.channel.category)
        await ctx.send(f"New channel created with name '{channel_name}'.")

    @commands.command(name="rc", description="delete a channel from the invoker guild.")
    @commands.has_permissions(manage_channels=True)
    @commands.guild_only()
    async def rc(self, ctx: commands.Context, channel_to_delete: abc.GuildChannel):
        """Removes a channel specified. You must have the appropriate permissions."""
        await channel_to_delete.delete(reason=f'Requested by {ctx.author.name}')
        await ctx.send(f"Deleted channel with name {channel_to_delete.name}.")

    @commands.command(name="purge", description="bulk remove an amount of messages, excluding pins.")
    @commands.has_permissions(manage_messages=True)
    @commands.guild_only()
    async def purge(self, ctx: commands.Context, purge_max_amount: int):
        """Purge an amount of messages. Pinned messages aren't removed."""

        dltd = await ctx.channel.purge(limit=purge_max_amount + 1, check=lambda msg: not msg.pinned, bulk=True)
        await ctx.send(content=f'Successfully deleted **{len(dltd)-1}** message(s).', delete_after=7.5, silent=True)


async def setup(client):
    await client.add_cog(Moderation(client))
