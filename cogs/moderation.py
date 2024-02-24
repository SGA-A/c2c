from discord.ext import commands
from discord import app_commands
from time import perf_counter
import discord
from datetime import timedelta
from cogs.economy import membed, Confirm, active_sessions


class Moderation(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    @commands.command(name="close", description="Close the invocation thread")
    @commands.guild_only()
    async def close_thread(self, ctx: commands.Context):
        await ctx.message.delete()
        if isinstance(ctx.channel, discord.Thread):
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

    @commands.command(name='delay', description='Sets a slowmode for the invoker channel', aliases=('d',))
    @commands.has_permissions(manage_channels=True)
    async def set_delay(self, ctx: commands.Context, slowmode_in_seconds: int):
        """Sets a delay to which users can send messages. You must have the appropriate permissions."""
        slowmode_in_seconds = abs(slowmode_in_seconds)
        await ctx.channel.edit(slowmode_delay=slowmode_in_seconds)
        if slowmode_in_seconds:
            return await ctx.send(f'<:slowed:1195739862100353114> Slowmode set to {slowmode_in_seconds} seconds.')
        await ctx.send("<:normale:1195740534703136921> Disabled slowmode.")

    @commands.command(name="purge", description="Bulk-remove messages, excluding pins")
    @commands.has_permissions(manage_messages=True)
    @commands.guild_only()
    async def purge(self, ctx: commands.Context, purge_max_amount: int):
        """Purge an amount of messages. Pinned messages aren't removed."""
        await ctx.message.delete()
        purge_max_amount = min(purge_max_amount, 300)
        stop_at = discord.utils.utcnow() - timedelta(weeks=2)
        await ctx.channel.purge(limit=purge_max_amount, check=lambda msg: not msg.pinned, bulk=True, after=stop_at, oldest_first=False)

    async def do_boilerplate_role_checks(self, interaction: discord.Interaction, role: discord.Role, guild: discord.Guild, my_top: discord.Role) -> str | None:
        if not interaction.user.guild_permissions.manage_roles:
            return "You don't have permission to do this."

        if role.managed:
            return f"The role {role.name} is managed and cannot be assigned or removed."

        if role >= my_top:
            roles_beneath = [iter_role for iter_role in guild.roles if (iter_role < role) and (iter_role > my_top)]
            roles_beneath = [role.name for role in roles_beneath]

            return (
                f"The role '{role.name}' (pos {role.position}) is above my highest role '{my_top.name}' (pos {my_top.position}) meaning I cannot alter their roles.\n"
                "Please ensure my highest role is above the role you want assigned or removed.\n\n"
                f"{role.name} **<-- The role you wish to assign or remove**\n"
                f"{'\n'.join(roles_beneath) + '\n' if roles_beneath else ''}"
                f"{my_top.name} **<-- The bot's highest role**")

    roles = app_commands.Group(name="role", description="Role management commands", guild_only=True)

    @roles.command(name="add", description="Adds a role to the specified user")
    @app_commands.describe(user="The user to add the role to.", role="The role to add to this user.")
    async def add_role(self, interaction: discord.Interaction, user: discord.Member, role: discord.Role):
        
        if role in user.roles:
            return await interaction.response.send_message("That member already has this role.")

        guild = interaction.guild
        resp = await self.do_boilerplate_role_checks(interaction, role, guild, guild.me.top_role)
        if resp:
            return await interaction.response.send_message(resp)
        
        try:
            await user.add_roles(discord.Object(id=role.id))
            await interaction.response.send_message(embed=membed(f"Added {role.mention} to {user.mention}."))
        except discord.Forbidden:
            await interaction.response.send_message("I don't have the required permissions to do this.")
        
    @roles.command(name="remove", description="Removes a role from the specified user")
    @app_commands.describe(user="The user to remove the role from.", role="The role to remove from this user.")
    async def remove_role(self, interaction: discord.Interaction, user: discord.Member, role: discord.Role):
        
        if role not in user.roles:
            return await interaction.response.send_message("That member doesn't have this role.")

        guild = interaction.guild
        resp = await self.do_boilerplate_role_checks(interaction, role, guild, guild.me.top_role)
        
        if resp:
            return await interaction.response.send_message(resp)
    
        try:
            await user.remove_roles(discord.Object(id=role.id))
            await interaction.response.send_message(embed=membed(f"Removed {role.mention} from {user.mention}."))
        except discord.Forbidden:
            await interaction.response.send_message("I don't have the required permissions to remove roles from members.")

    @roles.command(name="all", description="Adds a role to all members")
    @app_commands.describe(role="The role to add to all members.")
    async def add_role_all(self, interaction: discord.Interaction, role: discord.Role):
        guild = interaction.guild

        users_without_it = {member for member in guild.members if role not in member.roles}
        
        how_many = len(users_without_it)
        if not how_many:
            return await interaction.response.send_message("Everybody has this role already.")

        resp = await self.do_boilerplate_role_checks(interaction, role, guild, guild.me.top_role)
        if resp:
            return await interaction.response.send_message(resp)
        
        active_sessions.update({interaction.user.id: 1})
        view = Confirm(interaction)
        confirm = discord.Embed()
        confirm.title = "Pending Confirmation"
        confirm.colour = role.colour
        confirm.description = f"This will add {role.mention} to **{how_many}** members.\nDo you want to continue?"
        
        await interaction.response.send_message(embed=confirm, view=view)
        msg = await interaction.original_response()

        await view.wait()
        if view.value is None:
            del active_sessions[interaction.user.id]

            confirm.colour = 0xD15E54
            confirm.title = "Cancelled"
            confirm.description = "You took too long.."
            return await msg.edit(content=None, embed=confirm, view=None)
        
        if view.value:
            start_time = perf_counter()
            try:
                for member in users_without_it:
                    await member.add_roles(discord.Object(id=role.id), atomic=True)
            except discord.Forbidden:
                await msg.edit(content="I don't have the required permissions to add roles to members.", embed=None)
                return
            except discord.HTTPException:
                await msg.edit(content="We are being rate-limited. Try again later.", embed=None)
            finally:
                end_time = perf_counter()
                confirm.colour = 0x70DEAA
                confirm.title = "Success"
                confirm.description = f"Added {role.mention} to **{how_many}** members."
                return await msg.edit(content=f"Took {end_time - start_time:.2f}s", embed=confirm, view=None)

        confirm.colour = 0xD15E54
        confirm.title = "Cancelled"
        confirm.description = "This role wasn't assigned to anyone."

        await msg.edit(content=None, embed=confirm, view=None)
    
    @roles.command(name="rall", description="Removes a role from all members")
    @app_commands.describe(role="The role to remove to all members.")
    async def remove_roles_all(self, interaction: discord.Interaction, role: discord.Role):
        guild = interaction.guild

        users_without_it = {member for member in guild.members if role in member.roles}
        
        how_many = len(users_without_it)
        if not how_many:
            return await interaction.response.send_message("Nobody has this role already.")

        resp = await self.do_boilerplate_role_checks(interaction, role, guild, guild.me.top_role)
        if resp: 
            return await interaction.response.send_message(resp)

        active_sessions.update({interaction.user.id: 1})
        view = Confirm(interaction)
        confirm = discord.Embed()
        confirm.title = "Pending Confirmation"
        confirm.colour = role.colour 
        confirm.description = f"This will remove {role.mention} from **{how_many}** members.\nDo you want to continue?"
        
        await interaction.response.send_message(embed=confirm, view=view)
        msg = await interaction.original_response()

        await view.wait()
        if view.value is None:
            del active_sessions[interaction.user.id]

            confirm.colour = 0xD15E54
            confirm.title = "Cancelled"
            confirm.description = "You took too long.."
            return await msg.edit(embed=confirm, view=None)
        
        if view.value:
            start_time = perf_counter()
            try:
                for member in users_without_it:
                    await member.remove_roles(discord.Object(id=role.id), atomic=True)
            except discord.Forbidden:
                return await msg.edit(content="I don't have the required permissions to remove roles to members.", embed=None, view=None)
            except discord.HTTPException:
                return await msg.edit(content="We are being rate-limited. Try again later.", embed=None, view=None)
            finally:
                end_time = perf_counter()
                confirm.colour = 0x70DEAA
                confirm.title = "Success"
                confirm.description = f"Removed {role.mention} from **{how_many}** members."
                return await msg.edit(content=f"Took {end_time - start_time:.2f}s", embed=confirm, view=None)

        confirm.colour = 0xD15E54
        confirm.title = "Cancelled"
        confirm.description = "This role wasn't removed from anyone."

        await msg.edit(embed=confirm, view=None)

async def setup(client):
    await client.add_cog(Moderation(client))
