from discord.ext import commands
from discord import app_commands
from time import perf_counter
import discord
from datetime import timedelta
from other.pagination import Pagination
from cogs.economy import membed, Confirm, active_sessions, APP_GUILDS_ID


class Moderation(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    async def bulk_add_roles(
            self, interaction: discord.Interaction, users_without_it: set, role: discord.Role, how_many: int) -> str | None:
        if not interaction.response.is_done():
            await interaction.response.defer(thinking=True)
        start_time = perf_counter()
        try:
            for member in users_without_it:
                await member.add_roles(discord.Object(id=role.id), atomic=True)
        except discord.Forbidden:
            return "I don't have the required permissions to add roles to members."
        except discord.HTTPException:
            return "We are being rate-limited. Try again later"
        finally:
            end_time = perf_counter()
            success = discord.Embed()
            success.colour = 0x54CD68
            success.title = "Success"
            success.description = f"Added {role.mention} to **{how_many}** members."
            await interaction.followup.send(
                content=f"Took {end_time - start_time:.2f}s", embed=success)
            return None

    async def bulk_remove_roles(
            self, interaction: discord.Interaction, targets: set, new_role: discord.Role, how_many: int) -> str | None:
        start_time = perf_counter()
        
        if not interaction.response.is_done():
            await interaction.response.defer(thinking=True)
        
        try:
            for member in targets:
                await member.remove_roles(discord.Object(id=new_role.id), atomic=True)
        except discord.Forbidden:
            return "I don't have the required permissions to remove roles from members."
        except discord.HTTPException:
            return "We are being rate-limited. Try again later."
        finally:
            end_time = perf_counter()
            success = discord.Embed()
            success.colour = 0x54CD68
            success.title = "Success"
            success.description = f"Removed {new_role.mention} from **{how_many}** members."
            await interaction.followup.send(
                content=f"Took {end_time - start_time:.2f}s", embed=success)
            return None
    
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

    roles = app_commands.Group(name="role", description="Role management commands", guild_only=True, guild_ids=APP_GUILDS_ID)

    @roles.command(name="add", description="Adds a role to the specified member")
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

    @roles.command(name="remove", description="Removes a role from the specified member")
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
        await interaction.response.defer(thinking=True)
        
        guild = interaction.guild
        users_without_it = {member for member in guild.members if role not in member.roles}
        
        how_many = len(users_without_it)
        if not how_many:
            return await interaction.followup.send("Everybody has this role already.")

        resp = await self.do_boilerplate_role_checks(interaction, role, guild, guild.me.top_role)
        if resp:
            return await interaction.followup.send(resp)
        
        active_sessions.update({interaction.user.id: 1})
        view = Confirm(interaction)
        confirm = discord.Embed()
        confirm.title = "Pending Confirmation"
        confirm.colour = role.colour
        confirm.description = f"This will add {role.mention} to **{how_many}** members.\nDo you want to continue?"
        
        await interaction.followup.send(embed=confirm, view=view)
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
            await msg.edit(content=None, embed=membed("Adding roles... (This may take a while)"))
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
        await interaction.response.defer(thinking=True)

        guild = interaction.guild
        users_without_it = {member for member in guild.members if role in member.roles}

        how_many = len(users_without_it)
        if not how_many:
            return await interaction.followup.send("Nobody has this role already.")

        resp = await self.do_boilerplate_role_checks(interaction, role, guild, guild.me.top_role)
        if resp: 
            return await interaction.followup.send(resp)

        active_sessions.update({interaction.user.id: 1})
        view = Confirm(interaction)
        confirm = discord.Embed()
        confirm.title = "Pending Confirmation"
        confirm.colour = role.colour 
        confirm.description = f"This will remove {role.mention} from **{how_many}** members.\nDo you want to continue?"
        
        await interaction.followup.send(embed=confirm, view=view)
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
            await msg.edit(content=None, embed=membed("Removing roles... (This may take a while)"))
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

    @roles.command(name="allroles", description="Lists all roles in the server")
    async def all_roles(self, interaction: discord.Interaction):

        guild_roles = interaction.guild.roles
        guild_roles = sorted(guild_roles, reverse=True)
        guild_roles = [(role.mention, role.id) for role in guild_roles]

        async def get_page_part(page: int):
            emb = discord.Embed(
                color=0x7B87DD,
                description=""
            )

            length = 20
            offset = (page - 1) * length

            for role_attr in guild_roles[offset:offset + length]:
                emb.description += f"{role_attr[0]} {role_attr[1]}\n"
            n = Pagination.compute_total_pages(len(guild_roles), length)
            return emb, n

        await Pagination(interaction, get_page_part).navigate()
    
    @roles.command(name="info", description="Check info for a role")
    @app_commands.describe(role="The role to check info for.")
    async def role_info(self, interaction: discord.Interaction, role: discord.Role):
        await interaction.response.defer(thinking=True)

        how_many_owns = len(role.members)
        proportion = (how_many_owns / len(interaction.guild.members)) * 100

        time_since_creation = discord.utils.utcnow() - role.created_at
        diff = time_since_creation.total_seconds()
        
        minutes = divmod(diff, 60)[0]
        hours, minutes = divmod(minutes, 60)
        days, hours = divmod(hours, 24)
        months, days = divmod(days, 30)
        years, months = divmod(months, 12)
        
        order = []
        # Only include months and years if they are greater than 0
        if years:
            order.append(f"{int(years)} years")
        if months:
            order.append(f"{int(months)} months")
        order.extend([f"{int(days)} days", f"and {int(hours)} hours"])

        about = discord.Embed()
        
        about.colour = role.colour
        about.title = "Role Info"
        about.description = (
            f"**Name**: {role.name}\n"
            f"**Members**: {len(role.members)} ({proportion:.1f}% of members)\n"
            f"**Colour**: {role.colour}\n"
            f"**Created** {' '.join(order)} ago"
        )
        about.set_footer(text=f"ID: {role.id}")
        await interaction.followup.send(embed=about)

    @roles.command(name="removebots", description="Removes a role from all bots")
    @app_commands.describe(role="The role to remove from all bots.")
    async def remove_bots(self, interaction: discord.Interaction, role: discord.Role):
        await interaction.response.defer(thinking=True)

        guild = interaction.guild
        bots = {member for member in guild.members if member.bot}

        users_without_it = {member for member in bots if role in member.roles}
        count = len(users_without_it)
        
        if not count:
            return await interaction.followup.send("No bots have this role.")

        resp = await self.do_boilerplate_role_checks(interaction, role, guild, guild.me.top_role)
        if resp:
            return await interaction.followup.send(resp)

        resp = await self.bulk_remove_roles(interaction, targets=users_without_it, new_role=role, how_many=count)
        if resp:
            return await interaction.followup.send(resp)
        
    @roles.command(name="humans", description="Adds a role to all humans")
    @app_commands.describe(role="The role to add to all humans.")
    async def add_humans(self, interaction: discord.Interaction, role: discord.Role):
        await interaction.response.defer(thinking=True)

        guild = interaction.guild
        users_without_it = {member for member in guild.members if (not member.bot) and (role not in member.roles)}
        count = len(users_without_it)
        
        if not count:
            return await interaction.followup.send("All humans have this role already.")

        resp = await self.do_boilerplate_role_checks(interaction, role, guild, guild.me.top_role)
        if resp:
            return await interaction.followup.send(resp)

        resp = await self.bulk_add_roles(interaction, users_without_it, role, count)
        if resp:
            return await interaction.followup.send(resp)

    @roles.command(name="removehumans", description="Removes a role from all humans")
    @app_commands.describe(role="The role to remove from all humans.")
    async def remove_humans(self, interaction: discord.Interaction, role: discord.Role):
        await interaction.response.defer(thinking=True)
        
        guild = interaction.guild
        users_without_it = {member for member in guild.members if (not member.bot) and (role in member.roles)}

        how_many = len(users_without_it)
        if not how_many:
            return await interaction.followup.send("No humans have this role.")

        resp = await self.do_boilerplate_role_checks(interaction, role, guild, guild.me.top_role)
        if resp:
            return await interaction.followup.send(resp)

        resp = await self.bulk_remove_roles(interaction, users_without_it, role, how_many)
        if resp:
            return await interaction.followup.send(resp)
        

    @roles.command(name="in", description="Adds a role to all members currently in a base role")
    @app_commands.describe(base_role="The role that members need to get a new role.", new_role="The new role to add to all members in the base role.")
    async def add_role_in(self, interaction: discord.Interaction, base_role: discord.Role, new_role: discord.Role):
        await interaction.response.defer(thinking=True)

        has_role = set(base_role.members)
        has_not_got_new = set(new_role.members)
        users_without_it = has_role.difference(has_not_got_new)
        print(users_without_it)
        
        how_many = len(users_without_it)
        if not how_many:
            return await interaction.followup.send("Nobody in the base role doesn't have the new role already.")
        
        guild = interaction.guild
        resp = await self.do_boilerplate_role_checks(interaction, new_role, guild, guild.me.top_role)
        if resp:
            return await interaction.followup.send(resp)

        resp = await self.bulk_add_roles(interaction, users_without_it, new_role, how_many)
        if resp:
            return await interaction.followup.send(resp)
        
    @roles.command(name="rin", description="Removes a role from all members currently in a base role")
    @app_commands.describe(base_role="The role that members need to get a new role.", new_role="The new role to add to all members in the base role.")
    async def remove_role_in(self, interaction: discord.Interaction, base_role: discord.Role, new_role: discord.Role):
        await interaction.response.defer(thinking=True)

        has_role = set(base_role.members)
        has_got_new = set(new_role.members)
        users_with_both = has_role.intersection(has_got_new)
        how_many = len(users_with_both)

        if not how_many:
            return await interaction.followup.send("Nobody in the base role has the new role.")

        guild = interaction.guild
        resp = await self.do_boilerplate_role_checks(interaction, new_role, guild, guild.me.top_role)
        if resp:
            return await interaction.followup.send(resp)
    
        resp = await self.bulk_remove_roles(interaction, users_with_both, new_role, how_many)
        if resp:
            return await interaction.followup.send(resp)


async def setup(client):
    await client.add_cog(Moderation(client))
