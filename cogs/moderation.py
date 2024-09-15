from re import compile
from typing import Generator, Optional
from datetime import timedelta, datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands, tasks

from .core.errors import FailingConditionalError, CustomTransformerError
from .core.helpers import membed, process_confirmation
from .core.paginators import PaginationItem
from .core.bot import C2C


UPLOAD_FILE_DESCRIPTION = "A file to upload alongside the thread."


def do_boilerplate_role_checks(r: discord.Role, g: discord.Guild) -> None:

    if r.managed:
        raise FailingConditionalError(
            f"The role {r.name!r} is managed and cannot be assigned or removed."
        )
    if r >= g.me.top_role:
        roles_beneath = (
            iter_role.name
            for iter_role in g.roles
            if (iter_role < r) and (iter_role > g.me.top_role)
        )

        rpos, rname = r.position, r.name
        mpos, mname = g.me.top_role.position, g.me.top_role.name

        resp = (
            f"The role {rname!r} (pos {rpos}) is above my highest role {mname!r} (pos {mpos}) "
            f"meaning I cannot alter their roles.\n"
            f"Please ensure my highest role is above the role you want assigned or removed.\n\n"
            f"{rname} **<-- The role you wish to assign or remove**\n"
            f"{'\n'.join(roles_beneath)}\n"
            f"{mname} **<-- The bot's highest role**"
        )

        raise FailingConditionalError(resp)


class TimeConverter(app_commands.Transformer):
    time_regex = compile(r"(\d{1,5}(?:[.,]?\d{1,5})?)([smhd])")
    time_dict = {"h": 3600, "s": 1, "m": 60, "d": 86_400}

    async def transform(self, _: discord.Interaction, argument: str) -> int:
        matches = self.time_regex.findall(argument.lower())
        time = 0
        for v, k in matches:
            try:
                time += self.time_dict[k]*float(v)
            except KeyError:
                raise CustomTransformerError(
                    argument,
                    self.type,
                    self,
                    f"{k} is an invalid time-key! d/h/m/s are valid."
                )
            except ValueError:
                raise CustomTransformerError(
                    argument,
                    self.type,
                    self,
                    f"{v} is not a number."
                )
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
        success.description = f"Added {role.name!r} to **{count:,}** member(s)."
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
        success.description = f"Removed {new_role.name!r} from **{count:,}** member(s)."
        await interaction.followup.send(embed=success)

    @app_commands.command(name="add", description="Adds a role to a member")
    @app_commands.describe(
        user="The member to add a role to.",
        role="The role to add to this member."
    )
    async def add_role(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        role: discord.Role
    ) -> None:

        if role in user.roles:
            return await interaction.response.send_message(
                embed=membed(f"{user.display_name} already has {role.name!r}.")
            )

        do_boilerplate_role_checks(role, interaction.guild)
        await user.add_roles(
            discord.Object(id=role.id),
            reason=f"Requested by {interaction.user} (ID: {interaction.user.id})"
        )

        await interaction.response.send_message(embed=membed(f"Added {role.name!r} to {user.display_name}."))

    @app_commands.command(name="remove", description="Removes a role from a member")
    @app_commands.describe(
        member="The user to remove the role from.",
        role="The role to remove from this user."
    )
    async def remove_role(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        role: discord.Role
    ) -> None:

        if role not in member.roles:
            return await interaction.response.send_message(
                embed=membed(f"{member.display_name} does not have {role.name!r}.")
            )

        do_boilerplate_role_checks(role, interaction.guild)
        await member.remove_roles(
            discord.Object(id=role.id),
            reason=f"Requested by {interaction.user} (ID: {interaction.user.id})"
        )

        await interaction.response.send_message(
            embed=membed(f"Removed {role.name!r} from {member.display_name}.")
        )

    @app_commands.command(name="custom", description="Add or remove multiple roles from a member")
    @app_commands.describe(
        member="The user to add/remove roles to.",
        roles="Precede role name with +/- to add or remove. Separate each with spaces."
    )
    async def custom_role(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        roles: str
    ) -> None:
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

        their_roles = set(member.roles)
        added_roles = added_roles.difference(their_roles)
        removed_roles = removed_roles.intersection(their_roles)

        if (not added_roles) and (not removed_roles):
            await interaction.followup.send(embed=membed("No changes were made."))
            return

        embed = membed().set_thumbnail(url=member.display_avatar.url)
        embed.title = f"Role Changes: {member.display_name}"

        custom_reason = f"Custom request by {interaction.user.name} (ID: {interaction.user.id})"
        if added_roles:
            await member.add_roles(*added_roles, reason=custom_reason)
            embed.add_field(name="Added", value="\n".join(role.mention for role in added_roles) or "\u200b")

        if removed_roles:
            await member.remove_roles(*removed_roles, reason=custom_reason)
            embed.add_field(name="Removed", value="\n".join(role.mention for role in removed_roles) or "\u200b")

        await interaction.followup.send(embed=embed)

    @app_commands.command(name="all", description="Adds a role to all members")
    @app_commands.describe(role="The role to add to all members.")
    async def add_role_to_all(
        self,
        interaction: discord.Interaction,
        role: discord.Role
    ) -> None:
        await interaction.response.defer(thinking=True)

        do_boilerplate_role_checks(role, interaction.guild)
        yielded_users = (member for member in interaction.guild.members if role not in member.roles)

        value = await process_confirmation(
            interaction,
            prompt=f"This will add {role.name!r} to all members."
        )

        if not value:
            return
        await self.bulk_add_roles(interaction, yielded_users, role)

    @app_commands.command(name="rall", description="Removes a role from all members")
    @app_commands.describe(role="The role to remove from all members.")
    async def remove_roles_all(
        self,
        interaction: discord.Interaction,
        role: discord.Role
    ) -> None:
        await interaction.response.defer(thinking=True)

        do_boilerplate_role_checks(role, interaction.guild)
        yielded_users = (member for member in interaction.guild.members if role in member.roles)

        value = await process_confirmation(
            interaction,
            prompt=f"This will remove {role.name!r} from all members."
        )

        if not value:
            return
        await self.bulk_remove_roles(interaction, yielded_users, role)

    @app_commands.command(name="allroles", description="Lists all roles in the server")
    async def all_roles(self, interaction: discord.Interaction) -> None:
        emb, length = membed(), 12

        paginator = PaginationItem(interaction)
        paginator.total_pages = paginator.compute_total_pages(len(interaction.guild.roles), length)

        async def get_page_part() -> discord.Embed:
            offset = length - (paginator.index * length) - 1

            emb.description = "\n".join(
                f"<@&{role.id}> \U00002014 {role.id}"
                for role in interaction.guild.roles[offset:offset-length:-1]
            )

            return emb.set_footer(text=f"Page {paginator.index} of {paginator.total_pages}")

        paginator.get_page = get_page_part
        await paginator.navigate()

    @app_commands.command(name="info", description="Check info for a role")
    @app_commands.describe(role="The role to check info for.")
    async def role_info(self, interaction: discord.Interaction, role: discord.Role) -> None:
        await interaction.response.defer(thinking=True)

        how_many_owns = len(role.members)
        proportion = (how_many_owns / len(interaction.guild.members)) * 100
        fmt_d = discord.utils.format_dt(role.created_at, "D")
        fmt_r = discord.utils.format_dt(role.created_at, "R")

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
    async def remove_bot_roles(
        self,
        interaction: discord.Interaction,
        role: discord.Role
    ) -> None:
        await interaction.response.defer(thinking=True)

        do_boilerplate_role_checks(role, interaction.guild)
        yielded_users = (
            member
            for member in interaction.guild.members
            if (member.bot) and (role in member.roles)
        )

        value = await process_confirmation(
            interaction,
            prompt=f"This will remove {role.name!r} from all bots."
        )

        if not value:
            return
        await self.bulk_remove_roles(interaction, yielded_users, role)

    @app_commands.command(name="humans", description="Add a role to all server humans")
    @app_commands.describe(role="The role to add to all humans.")
    async def add_human_roles(
        self,
        interaction: discord.Interaction,
        role: discord.Role
    ) -> None:
        await interaction.response.defer(thinking=True)

        do_boilerplate_role_checks(role, interaction.guild)
        yielded_users = (
            member
            for member in interaction.guild.members
            if (not member.bot) and (role not in member.roles)
        )

        value = await process_confirmation(
            interaction,
            prompt=f"This will add {role.name!r} to all humans in this server."
        )

        if not value:
            return
        await self.bulk_add_roles(interaction, yielded_users, role)

    @app_commands.command(description="Remove a role from all server humans")
    @app_commands.describe(role="The role to remove from all humans.")
    async def removehumans(
        self,
        interaction: discord.Interaction,
        role: discord.Role
    ) -> None:
        await interaction.response.defer(thinking=True)

        do_boilerplate_role_checks(role, interaction.guild)
        yielded_users = (
            member
            for member in interaction.guild.members
            if (not member.bot) and (role in member.roles)
        )

        value = await process_confirmation(
            interaction,
            prompt=f"This will remove {role.name!r} from all humans in this server."
        )

        if not value:
            return
        await self.bulk_remove_roles(interaction, yielded_users, role)

    @app_commands.command(name="in", description="Adds a role to all members in a base role")
    @app_commands.describe(
        base_role="The role members need to get the new role.",
        new_role="The new role to add to all members in the base role."
    )
    async def add_role_in(
        self,
        interaction: discord.Interaction,
        base_role: discord.Role,
        new_role: discord.Role
    ) -> None:
        await interaction.response.defer(thinking=True)

        do_boilerplate_role_checks(new_role, interaction.guild)
        yielded_users = (member for member in new_role.members if base_role in member.roles)

        value = await process_confirmation(
            interaction,
            prompt=f"This will add {new_role.name!r} to all members with {base_role.name!r}."
        )

        if not value:
            return
        await self.bulk_add_roles(interaction, yielded_users, new_role)

    @app_commands.command(name="rin", description="Removes a role from all members in a base role")
    @app_commands.describe(
        base_role="The role members need to lose a role.",
        role="The role to remove from all members in the base role."
    )
    async def remove_role_in(
        self,
        interaction: discord.Interaction,
        base_role: discord.Role,
        role: discord.Role
    ) -> None:
        await interaction.response.defer(thinking=True)

        do_boilerplate_role_checks(role, interaction.guild)
        yielded_users = (member for member in role.members if base_role in member.roles)

        value = await process_confirmation(
            interaction,
            prompt=f"This will remove {role.name!r} from all members with {base_role.name!r}."
        )

        if not value:
            return
        await self.bulk_remove_roles(interaction, yielded_users, role)

class Moderation(commands.Cog):
    """Moderation tools for your servers, available to server managers."""
    GUILD_CONTEXT = app_commands.AppCommandContext(
        guild=True,
        private_channel=False,
        dm_channel=False
    )
    GUILD_INSTALL = app_commands.AppInstallationType(guild=True, user=False)

    def __init__(self, bot: C2C) -> None:
        self.bot = bot

        self.purge_from_here_cmd = app_commands.ContextMenu(
            name='Purge Up To Here',
            callback=self.purge_from_here,
            allowed_contexts=self.GUILD_CONTEXT,
            allowed_installs=self.GUILD_INSTALL
        )

        roles = RoleManagement(
            name="role",
            description="Role management commands",
            default_permissions=discord.Permissions(manage_roles=True),
            allowed_contexts=self.GUILD_CONTEXT,
            allowed_installs=self.GUILD_INSTALL
        )

        self.bot.tree.add_command(self.purge_from_here_cmd)
        self.bot.tree.add_command(roles)

    @app_commands.default_permissions(manage_messages=True)
    async def purge_from_here(
        self,
        interaction: discord.Interaction,
        message: discord.Message
    ) -> None:
        await interaction.response.defer()
        await interaction.delete_original_response()

        try:
            await interaction.channel.purge(after=discord.Object(id=message.id))
        except discord.HTTPException:
            await interaction.followup.send(embed=membed("Could not purge this channel."))

    @tasks.loop()
    async def check_for_role(self) -> None:
        async with self.bot.pool.acquire() as conn:
            next_task = await conn.fetchone('SELECT * FROM tasks ORDER BY end_time LIMIT 1')

        if next_task is None:
            self.check_for_role.cancel()
            return

        mod_to, role_id, end_time, in_guild = next_task
        timestamp = datetime.fromtimestamp(end_time, tz=timezone.utc)
        await discord.utils.sleep_until(timestamp)

        mem = self.bot.get_guild(in_guild).get_member(mod_to)

        try:
            await mem.remove_roles(discord.Object(id=role_id), reason="Temporary role expiry")
        except discord.HTTPException:
            pass
        finally:
            async with self.bot.pool.acquire() as conn, conn.transaction():
                await conn.execute('DELETE FROM tasks WHERE mod_to = $0', mod_to)

    temprole = app_commands.Group(
        name="temprole",
        description="Manage roles containing an expiry attribute.",
        default_permissions=discord.Permissions(manage_roles=True),
        allowed_contexts=GUILD_CONTEXT,
        allowed_installs=GUILD_INSTALL
    )

    @temprole.command(name="add", description="Adds a temporary role")
    @app_commands.describe(user="The user to add the role to.", role="The role to add to this user.", duration="When this role should be removed e.g. 1d 7h 19m 4s.")
    async def add_temp_role(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        duration: app_commands.Transform[int, TimeConverter],
        role: discord.Role
    ) -> None:

        if role in user.roles:
            return await interaction.response.send_message(embed=membed("That member already has this role."))

        do_boilerplate_role_checks(role, interaction.guild)

        minutes, seconds = divmod(duration, 60)
        hours, minutes = divmod(minutes, 60)
        days, hours = divmod(hours, 24)

        time_components = (
            (int(days), "days"),
            (int(hours), "hours"),
            (int(minutes), "minutes"),
            (int(seconds), "seconds")
        )

        temprole_reason = f"Temporary role requested by {interaction.user} (ID: {interaction.user.id})"
        try:
            await user.add_roles(discord.Object(id=role.id), reason=temprole_reason)
        except discord.Forbidden:
            embed = membed("I'm missing permissions required for this command.")
            embed.add_field(name="Missing Permissions (1)", value="Manage Roles")
            return await interaction.response.send_message(embed=embed)

        embed = discord.Embed(colour=role.colour)
        embed.title = "Temporary role added"
        embed.description = f"Granted {user.mention} the {role.mention} role for "
        embed.description += " and ".join(f"{quantity} {unit}" for quantity, unit in time_components if quantity)
        await interaction.response.send_message(embed=embed)

        # Scheduling task
        timestamp = (discord.utils.utcnow() + timedelta(seconds=duration)).timestamp()

        query = "INSERT INTO tasks VALUES ($0, $1, $2, $3)"
        async with self.bot.pool.acquire() as conn, conn.transaction():
            await conn.execute(query, user.id, role.id, timestamp, interaction.guild.id)

        if self.check_for_role.is_running():
            return self.check_for_role.restart()
        self.check_for_role.start()

    @app_commands.command(description='Upload a new forum thread')
    @app_commands.describe(
        name="The name of the thread.",
        forum="What forum this thread should be in.",
        description="The content of the message to send with the thread.",
        tags="The tags to apply to the thread, seperated by speech marks.",
        file=UPLOAD_FILE_DESCRIPTION,
        file2=UPLOAD_FILE_DESCRIPTION,
        file3=UPLOAD_FILE_DESCRIPTION
    )
    @app_commands.default_permissions(manage_guild=True)
    async def post(
        self,
        interaction: discord.Interaction,
        forum: discord.ForumChannel,
        name: str,
        tags: str,
        description: Optional[str],
        file: Optional[discord.Attachment],
        file2: Optional[discord.Attachment],
        file3: Optional[discord.Attachment]
    ) -> None:
        await interaction.response.defer(thinking=True)

        files = [
            await param_value.to_file()
            for param_name, param_value in iter(interaction.namespace)
            if param_name.startswith("fi") and param_value
        ]

        tag_sep = [s for s in tags.split('"') if s.strip()]
        applicable_tags = [
            tag_obj
            for tag in tag_sep
            if (tag_obj := discord.utils.find(lambda t: t.name.lower() == tag.lower(), forum.available_tags))
        ]

        thread, _ = await forum.create_thread(
            name=name,
            content=description,
            files=files,
            applied_tags=applicable_tags
        )

        await interaction.followup.send(ephemeral=True, embed=membed(f"Created thread: {thread.jump_url}."))


async def setup(bot: C2C):
    await bot.add_cog(Moderation(bot))
