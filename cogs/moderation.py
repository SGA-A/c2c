import discord
from discord.ext import commands
from discord import app_commands

def is_help_thread():
    def predicate(ctx) -> bool:
        return isinstance(ctx.channel, discord.Thread) and ctx.channel.parent_id == 1147176894903627888

    return commands.check(predicate)


def can_close_threads(ctx) -> bool:
    if not isinstance(ctx.channel, discord.Thread):
        return False

    permissions = ctx.channel.permissions_for(ctx.author)
    return ctx.channel.parent_id == 1147176894903627888 and (
        permissions.manage_threads or ctx.channel.owner_id == ctx.author.id
    )


class Moderation(commands.Cog):
    def __init__(self, client):
        self.client = client

    # noinspection PyMethodMayBeStatic
    async def mark_as_solved(self, thread: discord.Thread, user: discord.abc.User) -> None:

        await thread.edit(
            locked=True,
            archived=True,
            reason=f'Marked as solved by {user} (ID: {user.id})',
        )

    @commands.command(name='cc')
    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    async def add_channel(self, ctx, channel_name):
        """Creates a channel. You must have the appropriate permissions."""
        await ctx.guild.create_text_channel(channel_name)
        await ctx.message.add_reaction('\u2705')

    @commands.command(name='close')
    @is_help_thread()
    async def closed(self, ctx):
        """Marks a thread as solved."""

        assert isinstance(ctx.channel, discord.Thread)

        if can_close_threads(ctx):
            await ctx.message.add_reaction('\u2705')
            await self.mark_as_solved(ctx.channel, ctx.author)

    @app_commands.command(name="kick", description="kicks a user from the invocation server.")
    @app_commands.checks.has_permissions(kick_members=True)
    @app_commands.guilds(discord.Object(id=829053898333225010), discord.Object(id=780397076273954886))
    @app_commands.describe(user='the mentioned user to kick from the server')
    async def kick(self, interaction: discord.Interaction, user: discord.Member):
        """Kicks a member. This member must be mentioned. You must have the appropriate permissions."""
        await interaction.response.send_message(content=f'{user.name} has been kicked.')
        await user.kick()

    @app_commands.command(name="ban", description="bans a user from the invocation server.")
    @app_commands.checks.has_permissions(ban_members=True)
    @app_commands.guilds(discord.Object(id=829053898333225010), discord.Object(id=780397076273954886))
    @app_commands.describe(user='the mentioned user to ban from the server')
    async def ban(self, interaction: discord.Interaction, user: discord.Member):
        await interaction.response.send_message(content=f'{user.name} has been banned.')
        await user.ban()

    @commands.command(name='setdelay')
    @commands.has_permissions(manage_channels=True)
    async def set_delay(self, ctx, seconds: int):
        """Sets a delay to which users can send messages. You must have the appropriate permissions."""

        await ctx.channel.edit(slowmode_delay=seconds)
        await ctx.message.add_reaction('\u2705')

    @commands.command(name='rc', aliases=['dc'])
    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    async def rc(self, ctx, channel: discord.TextChannel):
        """Removes a channel specified. You must have the appropriate permissions."""
        await channel.delete()
        await ctx.message.add_reaction('\u2705')

    @app_commands.command(name="purge", description="bulk remove an amount of messages, excluding pins.")
    @app_commands.checks.has_permissions(manage_messages=True)
    @app_commands.guilds(discord.Object(id=829053898333225010), discord.Object(id=780397076273954886))
    @app_commands.describe(amount='the amount of messages to purge')
    async def purge(self, interaction: discord.Interaction, amount: int):
        """Purge an amount of messages. Pinned messages aren't removed."""
        check_func = lambda msg: not msg.pinned
        await interaction.response.send_message(content=f"{amount} messages will now be purged.", ephemeral=True,
                                                delete_after=6.0)
        await interaction.channel.purge(limit=amount, check=check_func, bulk=True)


async def setup(client):
    await client.add_cog(Moderation(client))