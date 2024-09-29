from re import compile
from typing import Generator, Optional

import discord
from discord import app_commands

from ._types import BotExports
from .core.errors import FailingConditionalError
from .core.helpers import membed, process_confirmation
from .core.paginators import PaginationItem
from .core.bot import Interaction


ROLE_INPUT_REGEX = compile(r'([+-])([^+-]+)')
UPLOAD_FILE_DESCRIPTION = "A file to upload alongside the thread."
GUILD_INSTALL = app_commands.AppInstallationType(guild=True, user=False)
GUILD_CONTEXT = app_commands.AppCommandContext(
    guild=True,
    private_channel=False,
    dm_channel=False
)


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


class RoleManagement(app_commands.Group):

    async def interaction_check(self, itx: Interaction) -> bool:
        if itx.guild.me.guild_permissions.manage_roles:
            return True

        embed = membed("I'm missing permissions required for this command.")
        embed.add_field(name="Missing Permissions (1)", value="Manage Roles")
        await itx.response.send_message(embed=embed)
        return False

    async def bulk_add_roles(
        self,
        itx: Interaction,
        users_without_it: Generator[discord.Member, None, None],
        role: discord.Role
    ) -> None:

        count = 0
        bulk = f"Bulk role-add requested by {itx.user} (ID: {itx.user.id})"
        role_obj = discord.Object(id=role.id)

        try:
            for count, member in enumerate(users_without_it):
                await member.add_roles(role_obj, reason=bulk, atomic=True)
        except discord.HTTPException:
            raise FailingConditionalError("The process has been ratelimited, try again later.")

        await itx.followup.send(f"Added {role.name!r} to **{count:,}** member(s).")

    async def bulk_remove_roles(
        self,
        itx: Interaction,
        targets: Generator[discord.Member, None, None],
        new_role: discord.Role
    ) -> None:
        count = 0
        bulk = f"Bulk role-remove requested by {itx.user} (ID: {itx.user.id})"
        role_obj = discord.Object(id=new_role.id)

        try:
            for count, member in enumerate(targets, start=1):
                await member.remove_roles(role_obj, reason=bulk, atomic=True)
        except discord.HTTPException:
            raise FailingConditionalError("The process has been ratelimited, try again later.")

        await itx.followup.send(f"Removed {new_role.name!r} from **{count:,}** member(s).")

    @app_commands.command(name="add", description="Add a role to a member")
    @app_commands.describe(
        user="The member to add a role to.",
        role="The role to add to this member."
    )
    async def add_role(
        self,
        itx: Interaction,
        user: discord.Member,
        role: discord.Role
    ) -> None:

        if role in user.roles:
            return await itx.response.send_message(f"{user.display_name} already has {role.name!r}.")

        do_boilerplate_role_checks(role, itx.guild)
        await user.add_roles(
            discord.Object(id=role.id),
            reason=f"Requested by {itx.user} (ID: {itx.user.id})"
        )

        await itx.response.send_message(f"Added {role.name!r} to {user.display_name}.")

    @app_commands.command(name="remove", description="Remove a role from a member")
    @app_commands.describe(
        member="The user to remove the role from.",
        role="The role to remove from this user."
    )
    async def remove_role(
        self,
        itx: Interaction,
        member: discord.Member,
        role: discord.Role
    ) -> None:

        if role not in member.roles:
            return await itx.response.send_message(f"{member.display_name} does not have {role.name!r}.")

        do_boilerplate_role_checks(role, itx.guild)
        await member.remove_roles(
            discord.Object(id=role.id),
            reason=f"Requested by {itx.user} (ID: {itx.user.id})"
        )

        await itx.response.send_message(f"Removed {role.name!r} from {member.display_name}.")

    @app_commands.command(name="custom", description="Add or remove multiple roles from a member")
    @app_commands.describe(
        member="The user to add/remove roles to.",
        roles="Precede role name with +/- to add or remove. Separate each with spaces."
    )
    async def custom_role(
        self,
        itx: Interaction,
        member: discord.Member,
        roles: str
    ) -> None:
        await itx.response.defer()

        role_changes = ROLE_INPUT_REGEX.findall(roles)

        added_roles, removed_roles = set(), set()

        for switch, role_name in role_changes:
            role_name = role_name.strip()

            rolemention = discord.utils.find(
                lambda r: r.name.lower() == role_name.lower(),
                itx.guild.roles
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
            await itx.followup.send("No changes were made.")
            return

        embed = membed().set_thumbnail(url=member.display_avatar.url)
        embed.title = f"Role Changes: {member.display_name}"

        custom_reason = f"Custom request by {itx.user.name} (ID: {itx.user.id})"
        if added_roles:
            await member.add_roles(*added_roles, reason=custom_reason)
            embed.add_field(name="Added", value="\n".join(role.mention for role in added_roles) or "\u200b")

        if removed_roles:
            await member.remove_roles(*removed_roles, reason=custom_reason)
            embed.add_field(name="Removed", value="\n".join(role.mention for role in removed_roles) or "\u200b")

        await itx.followup.send(embed=embed)

    @app_commands.command(name="all", description="Add a role to all members")
    @app_commands.describe(role="The role to add to all members.")
    async def add_role_to_all(
        self,
        itx: Interaction,
        role: discord.Role
    ) -> None:
        await itx.response.defer(thinking=True)

        do_boilerplate_role_checks(role, itx.guild)
        yielded_users = (member for member in itx.guild.members if role not in member.roles)

        value = await process_confirmation(itx, f"This will add {role.name!r} to all members.")

        if not value:
            return
        await self.bulk_add_roles(itx, yielded_users, role)

    @app_commands.command(name="rall", description="Remove a role from all members")
    @app_commands.describe(role="The role to remove from all members.")
    async def remove_roles_all(
        self,
        itx: Interaction,
        role: discord.Role
    ) -> None:
        await itx.response.defer(thinking=True)

        do_boilerplate_role_checks(role, itx.guild)
        yielded_users = (member for member in itx.guild.members if role in member.roles)

        value = await process_confirmation(itx, f"This will remove {role.name!r} from all members.")

        if not value:
            return
        await self.bulk_remove_roles(itx, yielded_users, role)

    @app_commands.command(name="allroles", description="List all roles in the server")
    async def all_roles(self, itx: Interaction) -> None:
        emb, length = membed(), 12

        paginator = PaginationItem(itx)
        paginator.total_pages = paginator.compute_total_pages(len(itx.guild.roles), length)

        async def get_page_part() -> discord.Embed:
            offset = length - (paginator.index * length) - 1

            emb.description = "\n".join(
                f"<@&{role.id}> \U00002014 {role.id}"
                for role in itx.guild.roles[offset:offset-length:-1]
            )

            return emb.set_footer(text=f"Page {paginator.index} of {paginator.total_pages}")

        paginator.get_page = get_page_part
        await paginator.navigate()

    @app_commands.command(name="info", description="Check info for a role")
    @app_commands.describe(role="The role to check info for.")
    async def role_info(self, itx: Interaction, role: discord.Role) -> None:
        await itx.response.defer(thinking=True)

        how_many_owns = len(role.members)
        proportion = (how_many_owns / len(itx.guild.members)) * 100
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
        await itx.followup.send(embed=about)

    @app_commands.command(name="removebots", description="Remove a role from all bots")
    @app_commands.describe(role="The role to remove from all bots.")
    async def remove_bot_roles(
        self,
        itx: Interaction,
        role: discord.Role
    ) -> None:
        await itx.response.defer(thinking=True)

        do_boilerplate_role_checks(role, itx.guild)
        yielded_users = (
            member
            for member in itx.guild.members
            if (member.bot) and (role in member.roles)
        )

        value = await process_confirmation(itx, f"This will remove {role.name!r} from all bots.")

        if not value:
            return
        await self.bulk_remove_roles(itx, yielded_users, role)

    @app_commands.command(name="humans", description="Add a role to all server humans")
    @app_commands.describe(role="The role to add to all humans.")
    async def add_human_roles(
        self,
        itx: Interaction,
        role: discord.Role
    ) -> None:
        await itx.response.defer(thinking=True)

        do_boilerplate_role_checks(role, itx.guild)
        yielded_users = (
            member
            for member in itx.guild.members
            if (not member.bot) and (role not in member.roles)
        )

        value = await process_confirmation(itx, f"This will add {role.name!r} to all humans in this server.")

        if not value:
            return
        await self.bulk_add_roles(itx, yielded_users, role)

    @app_commands.command(description="Remove a role from all server humans")
    @app_commands.describe(role="The role to remove from all humans.")
    async def removehumans(
        self,
        itx: Interaction,
        role: discord.Role
    ) -> None:
        await itx.response.defer(thinking=True)

        do_boilerplate_role_checks(role, itx.guild)
        yielded_users = (
            member
            for member in itx.guild.members
            if (not member.bot) and (role in member.roles)
        )

        value = await process_confirmation(itx, f"This will remove {role.name!r} from all humans in this server.")

        if not value:
            return
        await self.bulk_remove_roles(itx, yielded_users, role)

    @app_commands.command(name="in", description="Add a role to all members in a base role")
    @app_commands.describe(
        base_role="The role members need to get the new role.",
        new_role="The new role to add to all members in the base role."
    )
    async def add_role_in(
        self,
        itx: Interaction,
        base_role: discord.Role,
        new_role: discord.Role
    ) -> None:
        await itx.response.defer(thinking=True)

        do_boilerplate_role_checks(new_role, itx.guild)
        yielded_users = (member for member in new_role.members if base_role in member.roles)

        value = await process_confirmation(itx, f"This will add {new_role.name!r} to all members with {base_role.name!r}.")

        if not value:
            return
        await self.bulk_add_roles(itx, yielded_users, new_role)

    @app_commands.command(name="rin", description="Remove a role from all members in a base role")
    @app_commands.describe(
        base_role="The role members need to lose a role.",
        role="The role to remove from all members in the base role."
    )
    async def remove_role_in(
        self,
        itx: Interaction,
        base_role: discord.Role,
        role: discord.Role
    ) -> None:
        await itx.response.defer(thinking=True)

        do_boilerplate_role_checks(role, itx.guild)
        yielded_users = (member for member in role.members if base_role in member.roles)

        value = await process_confirmation(itx, f"This will remove {role.name!r} from all members with {base_role.name!r}.")

        if not value:
            return
        await self.bulk_remove_roles(itx, yielded_users, role)


roles = RoleManagement(
    name="role",
    description="Role management commands",
    default_permissions=discord.Permissions(manage_roles=True),
    allowed_contexts=GUILD_CONTEXT,
    allowed_installs=GUILD_INSTALL
)


@app_commands.command(description='Upload a new forum thread')
@app_commands.default_permissions(manage_guild=True)
@app_commands.allowed_installs(guilds=True, users=False)
@app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
@app_commands.describe(
    name="The name of the thread.",
    forum="What forum this thread should be in.",
    comment="The content of the message to send with the thread.",
    tags="The tags to apply to the thread, seperated by speech marks.",
    file=UPLOAD_FILE_DESCRIPTION,
    file2=UPLOAD_FILE_DESCRIPTION,
    file3=UPLOAD_FILE_DESCRIPTION
)
async def post(
    itx: Interaction,
    forum: discord.ForumChannel,
    name: str,
    tags: str,
    comment: Optional[str],
    file: Optional[discord.Attachment],
    file2: Optional[discord.Attachment],
    file3: Optional[discord.Attachment]
) -> None:
    await itx.response.defer(thinking=True, ephemeral=True)

    files = [
        await param_value.to_file()
        for param_name, param_value in iter(itx.namespace)
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
        content=comment,
        files=files,
        applied_tags=applicable_tags
    )

    await itx.followup.send(thread.jump_url, ephemeral=True)


@app_commands.context_menu(name="Purge Up To Here")
@app_commands.default_permissions(manage_messages=True)
@app_commands.allowed_installs(guilds=True, users=False)
@app_commands.allowed_contexts(guilds=True, dms=False, private_channels=False)
async def purge_from_here(itx: Interaction, message: discord.Message) -> None:
    await itx.response.defer(ephemeral=True)
    await itx.delete_original_response()

    try:
        await itx.channel.purge(after=discord.Object(id=message.id))
    except discord.HTTPException:
        await itx.followup.send(embed=membed("Could not purge this channel."))


exports = BotExports([roles, post, purge_from_here])