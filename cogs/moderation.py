from re import compile
from typing import Generator
from datetime import timedelta, datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands, tasks

from .core.errors import FailingConditionalError
from .core.helpers import membed, process_confirmation
from .core.paginators import PaginationItem
from .core.bot import C2C


def do_boilerplate_role_checks(role: discord.Role, guild: discord.Guild, my_top: discord.Role) -> None:

    if role.managed:
        raise FailingConditionalError(
            f"The role {role.mention} is managed and cannot be assigned or removed."
        )
    if role >= my_top:
        roles_beneath = (
            iter_role.name 
            for iter_role in guild.roles 
            if (iter_role < role) and (iter_role > my_top)
        )
    
        raise FailingConditionalError(
            f"""
            The role '{role.mention}' (pos {role.position}) is above my highest role '{my_top.mention}' (pos {my_top.position}) meaning I cannot alter their roles.
            Please ensure my highest role is above the role you want assigned or removed.

            {role.name} **<-- The role you wish to assign or remove**
            {'\n'.join(roles_beneath)}
            {my_top.name} **<-- The bot's highest role**
            """
        )


class TimeConverter(app_commands.Transformer):
    time_regex = compile(r"(\d{1,5}(?:[.,]?\d{1,5})?)([smhd])")
    time_dict = {"h": 3600, "s": 1, "m": 60, "d": 86400}

    async def transform(self, _: discord.Interaction, argument: str) -> int:
        matches = self.time_regex.findall(argument.lower())
        time = 0
        for v, k in matches:
            try:
                time += self.time_dict[k]*float(v)
            except (KeyError, ValueError):
                continue
        return time


class RoleManagement(app_commands.Group):

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.guild.me.guild_permissions.manage_roles:
            return True
        
        embed = membed("I'm missing permissions required for this command.")
        embed.add_field(name="Missing Permissions (1)", value="Manage Roles")
        await interaction.response.send_message(embed=embed)

    async def bulk_add_roles(
        self, 
        interaction: discord.Interaction, 
        users_without_it: Generator[discord.Member, None, None],
        role: discord.Role
    ) -> None:

        count = 0
        bulk = f"Bulk role-add requested by {interaction.user} (ID: {interaction.user.id})"
        
        try:
            for count, member in enumerate(users_without_it):
                await member.add_roles(discord.Object(id=role.id), reason=bulk, atomic=True)
        except discord.HTTPException:
            raise FailingConditionalError("The process has been ratelimited, try again later.")

        success = discord.Embed(title="Success", colour=0x54CD68)
        success.description = f"Added {role.mention} to **{count:,}** members."
        await interaction.followup.send(embed=success)

    async def bulk_remove_roles(
        self, 
        interaction: discord.Interaction, 
        targets: Generator[discord.Member, None, None], 
        new_role: discord.Role
    ) -> None:
        count = 0
        bulk = f"Bulk role-remove requested by {interaction.user} (ID: {interaction.user.id})"
        
        try:
            for count, member in enumerate(targets, start=1):
                await member.remove_roles(discord.Object(id=new_role.id), reason=bulk, atomic=True)
        except discord.HTTPException:
            raise FailingConditionalError("The process has been ratelimited, try again later.")

        success = discord.Embed()
        success.colour = 0x54CD68
        success.title = "Success"
        success.description = f"Removed {new_role.mention} from **{count:,}** members."
        await interaction.followup.send(embed=success)

    @app_commands.command(name="add", description="Adds a role to the specified member")
    @app_commands.describe(user="The user to add the role to.", role="The role to add to this user.")
    async def add_role(self, interaction: discord.Interaction, user: discord.Member, role: discord.Role):

        if role in user.roles:
            return await interaction.response.send_message(
                embed=membed(f"{user.mention} already has {role.mention}.")
            )

        do_boilerplate_role_checks(role, interaction.guild)

        await user.add_roles(
            discord.Object(id=role.id), 
            reason=f"Requested by {interaction.user} (ID: {interaction.user.id})"
        )

        await interaction.response.send_message(embed=membed(f"Added {role.mention} to {user.mention}."))

    @app_commands.command(name="remove", description="Removes a role from a member")
    @app_commands.describe(user="The user to remove the role from.", role="The role to remove from this user.")
    async def remove_role(self, interaction: discord.Interaction, user: discord.Member, role: discord.Role):
        
        if role not in user.roles:
            return await interaction.response.send_message(
                embed=membed(f"{user.mention} does not have {role.mention}.")
            )

        do_boilerplate_role_checks(role, interaction.guild)

        await user.remove_roles(
            discord.Object(id=role.id), 
            reason=f"Requested by {interaction.user} (ID: {interaction.user.id})"
        )

        await interaction.response.send_message(embed=membed(f"Removed {role.mention} from {user.mention}."))

    @app_commands.command(name="custom", description="Add or remove multiple roles from a user")
    @app_commands.describe(
        user="The user to add/remove roles to.",
        roles="Precede role name with +/- to add or remove. Separate each with spaces."
    )
    async def custom_role(self, interaction: discord.Interaction, user: discord.Member, roles: str):
        await interaction.response.defer()

        pattern = compile(r'([+-])([^+-]+)')
        role_changes = pattern.findall(roles)
        
        added_roles, removed_roles = set(), set()

        for switch, role_name in role_changes:
            role_name = role_name.strip()
            
            rolemention = discord.utils.find(
                lambda r: r.name.lower() == role_name.lower(), 
                interaction.guild.roles
            )

            if (rolemention is None) or rolemention.managed:
                continue

            if switch == "+":
                added_roles.add(rolemention)
            else:
                removed_roles.add(rolemention)

        their_roles = set(user.roles)
        added_roles = added_roles.difference(their_roles)
        removed_roles = removed_roles.intersection(their_roles)

        if (not added_roles) and (not removed_roles):
            return await interaction.followup.send(embed=membed("No changes were made."))

        embed = membed().set_thumbnail(url=user.display_avatar.url)
        embed.title = f"Role Changes: {user.display_name}"

        custom_reason = f"Custom request by {interaction.user.name} (ID: {interaction.user.id})"
        if added_roles:
            await user.add_roles(*added_roles, reason=custom_reason)
            embed.add_field(name="Added", value="\n".join(role.mention for role in added_roles) or "\u200b")

        if removed_roles:
            await user.remove_roles(*removed_roles, reason=custom_reason)
            embed.add_field(name="Removed", value="\n".join(role.mention for role in removed_roles) or "\u200b")

        await interaction.followup.send(embed=embed)

    @app_commands.command(name="all", description="Adds a role to all server members")
    @app_commands.describe(role="The role to add to all server members.")
    async def add_role_to_all(self, interaction: discord.Interaction, role: discord.Role):
        await interaction.response.defer(thinking=True)
        
        guild = interaction.guild
        yielded_users = (member for member in guild.members if role not in member.roles)

        do_boilerplate_role_checks(role, guild)

        value = await process_confirmation(
            interaction, 
            prompt=f"This will add {role.mention} to all members."
        )
        
        if not value:
            return
        await self.bulk_add_roles(interaction, yielded_users, role)
    
    @app_commands.command(name="rall", description="Removes a role from all server members")
    @app_commands.describe(role="The role to remove to all server members.")
    async def remove_roles_all(self, interaction: discord.Interaction, role: discord.Role):
        await interaction.response.defer(thinking=True)

        guild = interaction.guild
        yielded_users = (member for member in guild.members if role in member.roles)

        do_boilerplate_role_checks(role, guild)

        value = await process_confirmation(
            interaction, 
            prompt=f"This will remove {role.mention} from all members."
        )

        if not value:
            return
        await self.bulk_remove_roles(interaction, yielded_users, role)

    @app_commands.command(name="allroles", description="Lists all roles in the server")
    async def all_roles(self, interaction: discord.Interaction):

        guild_roles = sorted(interaction.guild.roles[1:], reverse=True)
        guild_roles = [
            f"{role.mention} \U00002014 {role.id}" 
            for role in guild_roles
        ] + [f"@everyone \U00002014 {interaction.guild.id}"]

        emb = membed()
        length = 12

        async def get_page_part(page: int):
            offset = (page - 1) * length
            emb.description = "\n".join(guild_roles[offset:offset + length])

            n = PaginationItem.compute_total_pages(len(guild_roles), length)
            emb.set_footer(text=f"Page {page} of {n}")
            return emb, n

        await PaginationItem(interaction, get_page=get_page_part).navigate()
    
    @app_commands.command(name="info", description="Check info for a role")
    @app_commands.describe(role="The role to check info for.")
    async def role_info(self, interaction: discord.Interaction, role: discord.Role):
        await interaction.response.defer(thinking=True)

        how_many_owns = len(role.members)
        proportion = (how_many_owns / len(interaction.guild.members)) * 100
        fmt_d, fmt_r = discord.utils.format_dt(role.created_at, "D"), discord.utils.format_dt(role.created_at, "R")

        about = discord.Embed(color=role.colour).set_footer(text=f"ID: {role.id}")
        about.title = "Role Info"
        about.description = (
            f"- **Name**: {role.name}\n"
            f"- **Members**: {len(role.members)} ({proportion:.1f}% of members)\n"
            f"- **Colour**: {role.colour}\n"
            f"- **Created**: {fmt_d} ({fmt_r})"
        )
        await interaction.followup.send(embed=about)

    @app_commands.command(name="removebots", description="Removes a role from all bots")
    @app_commands.describe(role="The role to remove from all bots.")
    async def remove_bot_roles(self, interaction: discord.Interaction, role: discord.Role):
        await interaction.response.defer(thinking=True)

        guild = interaction.guild
        yielded_users = (
            member 
            for member in guild.members 
            if (member.bot) and (role in member.roles)
        )
        
        do_boilerplate_role_checks(role, guild)

        value = await process_confirmation(
            interaction, 
            prompt=f"This will remove {role.mention} from all bots."
        )

        if not value:
            return
        await self.bulk_remove_roles(interaction, yielded_users, role)

    @app_commands.command(name="humans", description="Add a role to all humans in the server")
    @app_commands.describe(role="The role to add to all humans.")
    async def add_human_roles(self, interaction: discord.Interaction, role: discord.Role):
        await interaction.response.defer(thinking=True)

        guild = interaction.guild
        yielded_users = (
            member 
            for member in guild.members 
            if (not member.bot) and (role not in member.roles)
        )
        
        do_boilerplate_role_checks(role, guild)

        value = await process_confirmation(
            interaction, 
            prompt=f"This will add {role.mention} to all humans in this server."
        )

        if not value:
            return
        await self.bulk_add_roles(interaction, yielded_users, role)

    @app_commands.command(description="Remove a role from all humans in the server")
    @app_commands.describe(role="The role to remove from all humans.")
    async def removehumans(self, interaction: discord.Interaction, role: discord.Role):
        await interaction.response.defer(thinking=True)

        guild = interaction.guild
        yielded_users = (
            member 
            for member in guild.members 
            if (not member.bot) and (role in member.roles)
        )

        do_boilerplate_role_checks(role, guild)

        value = await process_confirmation(
            interaction, 
            prompt=f"This will remove {role.mention} from all humans in this server."
        )

        if not value:
            return
        await self.bulk_remove_roles(interaction, yielded_users, role)

    @app_commands.command(name="in", description="Adds a role to all members currently in a base role")
    @app_commands.describe(base_role="The role members need to get the new role.", new_role="The new role to add to all members in the base role.")
    async def add_role_in(self, interaction: discord.Interaction, base_role: discord.Role, new_role: discord.Role):
        await interaction.response.defer(thinking=True)

        yielded_users = (member for member in new_role.members if base_role in member.roles)

        do_boilerplate_role_checks(new_role, interaction.guild)
        
        value = await process_confirmation(
            interaction, 
            prompt=f"This will add {new_role.mention} to all server members."
        )

        if not value:
            return
        await self.bulk_add_roles(interaction, yielded_users, new_role)

    @app_commands.command(name="rin", description="Removes a role from all members currently in a base role")
    @app_commands.describe(base_role="The role members need to lose a role.", new_role="The role to remove from all members in the base role.")
    async def remove_role_in(self, interaction: discord.Interaction, base_role: discord.Role, new_role: discord.Role):
        await interaction.response.defer(thinking=True)

        yielded_users = (member for member in new_role.members if base_role in member.roles)

        do_boilerplate_role_checks(new_role, interaction.guild)

        value = await process_confirmation(
            interaction, 
            prompt=f"This will remove {new_role.mention} from all users."
        )

        if not value:
            return
        await self.bulk_remove_roles(interaction, yielded_users, new_role)

class Moderation(commands.Cog):
    """Moderation tools for your servers, available to server managers."""
    def __init__(self, bot: C2C) -> None:
        self.bot = bot
        mod_context = app_commands.AppCommandContext(guild=True)
        mod_install = app_commands.AppInstallationType(guild=True)

        self.purge_from_here_cmd = app_commands.ContextMenu(
            name='Purge Up To Here',
            callback=self.purge_from_here,
            allowed_contexts=mod_context,
            allowed_installs=mod_install
        )
        
        roles = RoleManagement(
            name="role", 
            description="Role management commands",
            default_permissions=discord.Permissions(manage_roles=True),
            allowed_contexts=mod_context,
            allowed_installs=mod_install
        )
        
        self.bot.tree.add_command(self.purge_from_here_cmd)
        self.bot.tree.add_command(roles)

    @app_commands.default_permissions(manage_messages=True)
    async def purge_from_here(self, interaction: discord.Interaction, message: discord.Message):

        await interaction.response.defer(ephemeral=True)
        try:
            count = await interaction.channel.purge(after=discord.Object(id=message.id))
            msg: discord.WebhookMessage = await interaction.followup.send(embed=membed(f"Deleted **{len(count)}** messages."))
        except Exception:
            msg: discord.WebhookMessage = await interaction.followup.send(
                embed=membed("Could not purge this channel, this may be a DM or I'm missing permissions.")
            )
        finally:
            await msg.delete(delay=3.0)

    @tasks.loop()
    async def check_for_role(self):
        # sqlite implicitly orders by end_time in ascending order 
        async with self.bot.pool.acquire() as conn:
            next_task = await conn.fetchone('SELECT * FROM tasks ORDER BY end_time LIMIT 1')

        if next_task is None:
            self.check_for_role.cancel()
            return
        
        mod_to, role_id, end_time, in_guild = next_task
        timestamp = datetime.fromtimestamp(end_time, tz=timezone.utc)
        await discord.utils.sleep_until(timestamp)

        guild = self.bot.get_guild(in_guild)
        mem: discord.Member = guild.get_member(mod_to)

        try:
            guild = await mem.remove_roles(
                discord.Object(id=role_id),
                reason="Temporary role has expired"
            )
        except discord.HTTPException:
            pass
        finally:
            async with self.bot.pool.acquire() as conn:
                await conn.execute('DELETE FROM tasks WHERE mod_to = $0', mod_to)
                await conn.commit()

    @commands.has_permissions(manage_threads=True)
    @commands.command(description="Close a given thread or invocation thread", aliases=('cl',))
    async def close(self, ctx: commands.Context, thread: discord.abc.GuildChannel = commands.CurrentChannel):

        if not isinstance(thread, discord.Thread):
            return await ctx.reply(embed=membed("This is not a thread."))

        await ctx.message.delete()

        message = membed("This thread is now closed due to lack of use.").add_field(
            name="Want to re-open this thread?",
            value="Contact any human with the <@&893550756953735278> role."
        )

        await thread.send(embed=message)

        close_reason = f'Marked as closed by {ctx.author} (ID: {ctx.author.id})'
        await thread.edit(locked=True, archived=True, reason=close_reason)

    @commands.has_permissions(manage_channels=True)
    @commands.command(description='Sets a slowmode for the invoker channel', aliases=('d',))
    async def delay(self, ctx: commands.Context, slowmode_in_seconds: int):
        """Sets a delay to which users can send messages."""
        slowmode_in_seconds = abs(slowmode_in_seconds)
        await ctx.channel.edit(slowmode_delay=slowmode_in_seconds)
        if slowmode_in_seconds:
            return await ctx.send(embed=membed(f'Slowmode set to **{slowmode_in_seconds}** seconds.'))
        await ctx.send(embed=membed("Disabled slowmode."))

    temprole = app_commands.Group(
        name="temprole", 
        description="Manage roles containing an expiry attribute.", 
        default_permissions=discord.Permissions(manage_roles=True),
        allowed_contexts=app_commands.AppCommandContext(guild=True, dm_channel=False, private_channel=False),
        allowed_installs=app_commands.AppInstallationType(guild=True, user=False)
    )

    @temprole.command(name="add", description="Adds a temporary role")
    @app_commands.describe(user="The user to add the role to.", role="The role to add to this user.", duration="When this role should be removed e.g. 1d 7h 19m 4s.")
    async def add_temp_role(self, interaction: discord.Interaction, user: discord.Member, duration: app_commands.Transform[int, TimeConverter], role: discord.Role):

        if not duration:
            return await interaction.response.send_message(embed=membed("Use a valid duration format e.g. 1d 7h 19m 4s."))

        if role in user.roles:
            return await interaction.response.send_message(embed=membed("That member already has this role."))

        guild = interaction.guild
        do_boilerplate_role_checks(role, guild)

        minutes, seconds = divmod(duration, 60)
        hours, minutes = divmod(minutes, 60)
        days, hours = divmod(hours, 24)

        time_components = (
            (int(days), "days"),
            (int(hours), "hours"),
            (int(minutes), "minutes"),
            (int(seconds), "seconds")
        )

        # Sending message
        success = discord.Embed(colour=role.colour)
        success.title = "Temporary role added"
        success.description = f"Granted {user.mention} the {role.mention} role for "
        success.description += ' and '.join(f"{quantity} {unit}" for quantity, unit in time_components if quantity)

        temprole_reason = f"Temporary role requested by {interaction.user} (ID: {interaction.user.id})"
        await user.add_roles(discord.Object(id=role.id), reason=temprole_reason)
        await interaction.response.send_message(embed=success)

        # Scheduling task
        timestamp = (discord.utils.utcnow() + timedelta(seconds=duration)).timestamp()

        async with self.bot.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO tasks (mod_to, role_id, end_time, in_guild) 
                VALUES ($0, $1, $2, $3)
                """, user.id, role.id, timestamp, guild.id
            )

            await conn.commit()

        if self.check_for_role.is_running():
            self.check_for_role.restart()
            return
        self.check_for_role.start()


async def setup(bot: C2C):
    await bot.add_cog(Moderation(bot))
