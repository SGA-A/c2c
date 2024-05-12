from re import compile
from pytz import timezone
from time import perf_counter
from datetime import timedelta, datetime

from discord import app_commands
from discord.ext import commands, tasks

from .core.paginator import Pagination
from .core.views import process_confirmation
from .core.helpers import membed, respond
from .core.constants import APP_GUILDS_IDS

import discord


def do_boilerplate_role_checks(role: discord.Role, guild: discord.Guild, my_top: discord.Role) -> str | None:

    if role.managed:
        return f"The role {role.mention} is managed and cannot be assigned or removed."

    if role >= my_top:
        roles_beneath = [iter_role for iter_role in guild.roles if (iter_role < role) and (iter_role > my_top)]
        roles_beneath = [role.name for role in roles_beneath]

        return (
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
            except KeyError:
                continue
            except ValueError:
                continue
        return time


class RoleManagement(app_commands.Group):

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.guild.me.guild_permissions.manage_roles:
            return True
        
        embed = membed("I'm missing permissions required to use this command.")
        embed.add_field(name="Missing Permissions (1)", value="Manage Roles")
        await interaction.response.send_message(embed=embed)

    async def bulk_add_roles(
        self, 
        interaction: discord.Interaction, 
        users_without_it: set, 
        role: discord.Role, 
        how_many: int
    ) -> str | None:

        start_time = perf_counter()
        try:
            
            for member in users_without_it:
                await member.add_roles(
                    discord.Object(id=role.id), 
                    reason=f"Bulk role-add requested by {interaction.user} (ID: {interaction.user.id})", 
                    atomic=True
                )

        except discord.HTTPException:
            return "We are being rate-limited. Try again later"
        finally:
            end_time = perf_counter()
            success = discord.Embed()
            success.colour = 0x54CD68
            success.title = "Success"
            success.description = f"Added {role.mention} to **{how_many}** members."
            await respond(
                interaction=interaction,
                content=f"Took {end_time - start_time:.2f}s", 
                embed=success
            )

    async def bulk_remove_roles(
            self, 
            interaction: discord.Interaction, 
            targets: set, 
            new_role: discord.Role, 
            how_many: int
        ) -> str | None:
        
        start_time = perf_counter()
        try:
            for member in targets:
                await member.remove_roles(
                    discord.Object(id=new_role.id), 
                    reason=f"Bulk role-remove requested by {interaction.user} (ID: {interaction.user.id})", 
                    atomic=True
                )

        except discord.HTTPException:
            return "We are being rate-limited. Try again later."
        finally:
            end_time = perf_counter()
            success = discord.Embed()
            success.colour = 0x54CD68
            success.title = "Success"
            success.description = f"Removed {new_role.mention} from **{how_many}** members."
            await respond(
                interaction=interaction,
                content=f"Took {end_time - start_time:.2f}s", 
                embed=success
            )

    @app_commands.command(name="add", description="Adds a role to the specified member")
    @app_commands.describe(user="The user to add the role to.", role="The role to add to this user.")
    async def add_role(self, interaction: discord.Interaction, user: discord.Member, role: discord.Role):

        if role in user.roles:
            return await interaction.response.send_message(
                embed=membed(f"{user.mention} already has {role.mention}.")
            )

        resp = do_boilerplate_role_checks(role, interaction.guild, interaction.guild.me.top_role)
        if resp:
            return await interaction.response.send_message(embed=membed(resp))
        
        await user.add_roles(
            discord.Object(id=role.id), 
            reason=f"Requested by {interaction.user} (ID: {interaction.user.id})"
        )

        await interaction.response.send_message(embed=membed(f"Added {role.mention} to {user.mention}."))

    @app_commands.command(name="remove", description="Removes a role from the specified member")
    @app_commands.describe(user="The user to remove the role from.", role="The role to remove from this user.")
    async def remove_role(self, interaction: discord.Interaction, user: discord.Member, role: discord.Role):
        
        if role not in user.roles:
            return await interaction.response.send_message(
                embed=membed(f"{user.mention} does not have {role.mention}.")
            )

        resp = do_boilerplate_role_checks(role, interaction.guild, interaction.guild.me.top_role)
        
        if resp:
            return await interaction.response.send_message(embed=membed(resp))
    
        await user.remove_roles(
            discord.Object(id=role.id), 
            reason=f"Requested by {interaction.user} (ID: {interaction.user.id})"
        )

        await interaction.response.send_message(embed=membed(f"Removed {role.mention} from {user.mention}."))

    @app_commands.command(name="custom", description="Add or remove multiple roles in a single command")
    @app_commands.describe(
        user="The user to add/remove roles to.", 
        roles="Precede role name with +/- to add or remove. Separate each with spaces."
    )
    async def custom_roles(
        self, 
        interaction: discord.Interaction, 
        user: discord.Member, 
        roles: str
        ) -> discord.WebhookMessage:
        await interaction.response.defer()

        roles = roles.split()
        added_roles = set()
        removed_roles = set()

        for role in roles:
            switch = role[0]
            if switch not in ("+", "-"):
                continue
            
            rolemention = discord.utils.get(interaction.guild.roles, name=role[1:])

            if rolemention is None:
                continue
            if rolemention.managed:
                continue

            if switch == "+":
                added_roles.add(rolemention)
                continue
            removed_roles.add(rolemention)

        their_roles = set(user.roles)
        added_roles = added_roles.difference(their_roles)
        removed_roles = removed_roles.intersection(their_roles)

        if (not added_roles) and (not removed_roles):
            return await interaction.followup.send(embed=membed("No changes were made."))
        
        embed = discord.Embed(colour=0x2B2D31, title="Role Changes")

        await user.add_roles(
            *added_roles, 
            reason=f"Custom request by {interaction.user} (ID: {interaction.user.id})"
        )

        embed.add_field(
            name="Added", 
            value="\n".join(role.mention for role in added_roles) or "\U0000200b"
        )

        embed.add_field(
            name="Removed", 
            value="\n".join(role.mention for role in removed_roles) or "\U0000200b"
        )
        await user.remove_roles(
            *removed_roles, 
            reason=f"Custom request by {interaction.user} (ID: {interaction.user.id})"
        )
        
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="all", description="Adds a role to all members")
    @app_commands.describe(role="The role to add to all members.")
    async def add_role_all(self, interaction: discord.Interaction, role: discord.Role):
        await interaction.response.defer(thinking=True)
        
        guild = interaction.guild
        users_without_it = {member for member in guild.members if (role not in member.roles)}
        
        how_many = len(users_without_it)
        if not how_many:
            return await interaction.followup.send(embed=membed("Everybody has this role already."))

        resp = do_boilerplate_role_checks(role, guild, guild.me.top_role)
        if resp:
            return await interaction.followup.send(embed=membed(resp))
        
        value = await process_confirmation(
            interaction=interaction, 
            prompt=(
                f"This will add {role.mention} to **{how_many}** members."
            )
        )
        
        if value:
            resp = await self.bulk_add_roles(
                interaction, 
                users_without_it, 
                role, 
                how_many
            )
            if resp:
                await interaction.followup.send(embed=membed(resp))
    
    @app_commands.command(name="rall", description="Removes a role from all members")
    @app_commands.describe(role="The role to remove to all members.")
    async def remove_roles_all(self, interaction: discord.Interaction, role: discord.Role):
        await interaction.response.defer(thinking=True)

        guild = interaction.guild
        users_without_it = {member for member in guild.members if (role in member.roles)}

        how_many = len(users_without_it)
        if not how_many:
            return await interaction.followup.send(embed=membed("Nobody has this role already."))

        resp = do_boilerplate_role_checks(role, guild, guild.me.top_role)
        if resp: 
            return await interaction.followup.send(embed=membed(resp))
        
        value = await process_confirmation(
            interaction=interaction, 
            prompt=(
                f"This will remove {role.mention} from **{how_many}** members."
            )
        )

        if value:
            resp = await self.bulk_remove_roles(
                interaction, 
                users_without_it, 
                role, 
                how_many
            )
            if resp:
                await interaction.followup.send(embed=membed(resp))

    @app_commands.command(name="allroles", description="Lists all roles in the server")
    async def all_roles(self, interaction: discord.Interaction):

        guild_roles = sorted(interaction.guild.roles, reverse=True)
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
    
    @app_commands.command(name="info", description="Check info for a role")
    @app_commands.describe(role="The role to check info for.")
    async def role_info(self, interaction: discord.Interaction, role: discord.Role):
        await interaction.response.defer(thinking=True)

        how_many_owns = len(role.members)
        proportion = (how_many_owns / len(interaction.guild.members)) * 100
        fmt_d, fmt_r = discord.utils.format_dt(role.created_at, "D"), discord.utils.format_dt(role.created_at, "R")

        about = discord.Embed()
        about.colour = role.colour
        about.title = "Role Info"
        about.description = (
            f"- **Name**: {role.name}\n"
            f"- **Members**: {len(role.members)} ({proportion:.1f}% of members)\n"
            f"- **Colour**: {role.colour}\n"
            f"- **Created**: {fmt_d} ({fmt_r})"
        )
        about.set_footer(text=f"ID: {role.id}")
        await interaction.followup.send(embed=about)

    @app_commands.command(name="removebots", description="Removes a role from all bots")
    @app_commands.describe(role="The role to remove from all bots.")
    async def remove_bots(self, interaction: discord.Interaction, role: discord.Role):
        await interaction.response.defer(thinking=True)

        guild = interaction.guild
        users_without_it = {member for member in guild.members if (role in member.roles) and member.bot}
        count = len(users_without_it)
        
        if not count:
            return await interaction.followup.send(embed=membed("No bots have this role."))

        resp = do_boilerplate_role_checks(role, guild, guild.me.top_role)
        if resp:
            return await interaction.followup.send(embed=membed(resp))

        value = await process_confirmation(
            interaction=interaction, 
            prompt=f"This will remove {role.mention} from **{count}** bot(s)."
        )

        if value:
            resp = await self.bulk_remove_roles(
                interaction, 
                targets=users_without_it, 
                new_role=role, 
                how_many=count
            )
            if resp:
                return await interaction.followup.send(embed=membed(resp))
        
    @app_commands.command(name="humans", description="Adds a role to all humans")
    @app_commands.describe(role="The role to add to all humans.")
    async def add_humans(self, interaction: discord.Interaction, role: discord.Role):
        await interaction.response.defer(thinking=True)

        guild = interaction.guild
        users_without_it = {member for member in guild.members if (not member.bot) and (role not in member.roles)}
        count = len(users_without_it)
        
        if not count:
            return await interaction.followup.send(embed=membed("All humans have this role already."))

        resp = do_boilerplate_role_checks(role, guild, guild.me.top_role)
        if resp:
            return await interaction.followup.send(embed=membed(resp))

        value = await process_confirmation(
            interaction=interaction, 
            prompt=f"This will add {role.mention} to **{count}** user(s)."
        )

        if value:
            resp = await self.bulk_add_roles(
                interaction, 
                users_without_it, 
                role, 
                count
            )
            if resp:
                await interaction.followup.send(embed=membed(resp))

    @app_commands.command(name="removehumans", description="Removes a role from all humans")
    @app_commands.describe(role="The role to remove from all humans.")
    async def remove_humans(self, interaction: discord.Interaction, role: discord.Role):
        await interaction.response.defer(thinking=True)
        
        guild = interaction.guild
        users_without_it = {member for member in guild.members if (not member.bot) and (role in member.roles)}

        how_many = len(users_without_it)
        if not how_many:
            return await interaction.followup.send(embed=membed("No humans have this role."))

        resp = do_boilerplate_role_checks(role, guild, guild.me.top_role)
        if resp:
            return await interaction.followup.send(embed=membed(resp))

        value = await process_confirmation(
            interaction=interaction, 
            prompt=f"This will remove {role.mention} from **{how_many}** user(s)."
        )

        if value:
            resp = await self.bulk_remove_roles(
                interaction, 
                targets=users_without_it, 
                new_role=role, 
                how_many=how_many
            )
            if resp:
                return await interaction.followup.send(embed=membed(resp))
        
    @app_commands.command(name="in", description="Adds a role to all members currently in a base role")
    @app_commands.describe(base_role="The role members need to get a new role.", new_role="The new role to add to all members in the base role.")
    async def add_role_in(self, interaction: discord.Interaction, base_role: discord.Role, new_role: discord.Role):
        await interaction.response.defer(thinking=True)

        has_role = set(base_role.members)
        has_new_role = set(new_role.members)
        users_without_it = has_role.difference(has_new_role)
        
        count = len(users_without_it)
        if not count:
            return await interaction.followup.send(
                embed=membed("Nobody in the base role doesn't have the new role already.")
        )
        
        resp = do_boilerplate_role_checks(new_role, interaction.guild, interaction.guild.me.top_role)
        if resp:
            return await interaction.followup.send(embed=membed(resp))
        
        value = await process_confirmation(
            interaction=interaction, 
            prompt=f"This will add {new_role.mention} to **{count}** user(s)."
        )

        if value:
            resp = await self.bulk_add_roles(
                interaction, 
                users_without_it, 
                new_role, 
                count
            )
            if resp:
                await interaction.followup.send(embed=membed(resp))
        
    @app_commands.command(name="rin", description="Removes a role from all members currently in a base role")
    @app_commands.describe(base_role="The role members need to lose a role.", new_role="The role to remove from all members in the base role.")
    async def remove_role_in(self, interaction: discord.Interaction, base_role: discord.Role, new_role: discord.Role):
        await interaction.response.defer(thinking=True)

        has_role = set(base_role.members)
        has_got_new = set(new_role.members)
        users_with_both = has_role.intersection(has_got_new)
        how_many = len(users_with_both)

        if not how_many:
            return await interaction.followup.send(
                embed=membed("Nobody in the base role has the new role.")
            )
        
        resp = do_boilerplate_role_checks(new_role, interaction.guild, interaction.guild.me.top_role)
        if resp:
            return await interaction.followup.send(embed=membed(resp))

        value = await process_confirmation(
            interaction=interaction, 
            prompt=f"This will remove {new_role.mention} from **{how_many}** user(s)."
        )

        if value:
            resp = await self.bulk_remove_roles(interaction, users_with_both, new_role, how_many)
            if resp:
                return await interaction.followup.send(embed=membed(resp))


class Moderation(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

        self.purge_from_here_cmd = app_commands.ContextMenu(
            name='Purge Up To Here',
            callback=self.purge_from_here
        )
        
        roles = RoleManagement(
            name="role", 
            description="Role management commands",
            guild_ids=APP_GUILDS_IDS,  
            guild_only=True, 
            default_permissions=discord.Permissions(manage_roles=True)
        )
        
        self.bot.tree.add_command(self.purge_from_here_cmd)
        self.bot.tree.add_command(roles)

    @app_commands.default_permissions(manage_messages=True)
    @app_commands.guilds(*APP_GUILDS_IDS)
    async def purge_from_here(self, interaction: discord.Interaction, message: discord.Message):

        await interaction.response.defer(ephemeral=True)
        
        count = await interaction.channel.purge(after=discord.Object(id=message.id))
        msg: discord.WebhookMessage = await interaction.followup.send(embed=membed(f"Deleted **{len(count)}** messages."))
        await msg.delete(delay=3.0)

    @tasks.loop()
    async def check_for_role(self):
        # fetch the task with the lowest/earliest `end_time`
        async with self.bot.pool.acquire() as conn:
            next_task = await conn.fetchone('SELECT * FROM tasks ORDER BY end_time ASC LIMIT 1')

            # if no remaining tasks, stop the loop
            if next_task is None:
                self.check_for_role.cancel()
                return
            
            # sleep until the task should be done
            # if the time is before now, this should return immediately
            
            mod_to, role_id, end_time, in_guild = next_task
            timestamp = datetime.fromtimestamp(end_time, tz=timezone("UTC"))
            await discord.utils.sleep_until(timestamp)

            # do your actual task stuff here
            guild = self.bot.get_guild(in_guild)
            
            try:
                mem: discord.Member = guild.get_member(mod_to)
                guild = await mem.remove_roles(
                    discord.Object(id=role_id),
                    reason="Temporary role has expired"
                )
            except discord.HTTPException:
                pass
            finally:
                # delete the task we just completed
                await conn.execute('DELETE FROM tasks WHERE mod_to = $0', mod_to)
                await conn.commit()

    @commands.has_permissions(manage_threads=True)
    @commands.command(name="close", description="Close the invocation thread")
    async def close_thread(self, ctx: commands.Context):
        if not isinstance(ctx.channel, discord.Thread):
            return await ctx.reply(embed=membed("This is not a thread."))
        
        await ctx.message.delete()
        await ctx.send(
            embed=membed(
                "This thread is now locked due to lack of use.\n"
                "It may be re-opened if needed by contacting an admin."
            )
        )

        return await ctx.channel.edit(
            locked=True,
            archived=True,
            reason=f'Marked as closed by {ctx.author} (ID: {ctx.author.id})'
        )

    @commands.has_permissions(manage_channels=True)
    @commands.command(name='delay', description='Sets a slowmode for the invoker channel', aliases=('d',))
    async def set_delay(self, ctx: commands.Context, slowmode_in_seconds: int):
        """Sets a delay to which users can send messages."""
        slowmode_in_seconds = abs(slowmode_in_seconds)
        await ctx.channel.edit(slowmode_delay=slowmode_in_seconds)
        if slowmode_in_seconds:
            return await ctx.send(embed=membed(f'Slowmode set to **{slowmode_in_seconds}** seconds.'))
        await ctx.send(embed=membed("Disabled slowmode."))

    temprole = app_commands.Group(
        name="temprole", 
        description="Set roles that expire after a certain time.", 
        guild_only=True, 
        guild_ids=APP_GUILDS_IDS, 
        default_permissions=discord.Permissions(manage_roles=True)
    )

    @temprole.command(name="add", description="Adds a temporary role")
    @app_commands.describe(user="The user to add the role to.", role="The role to add to this user.", duration="When this role should be removed e.g. 1d 7h 19m 4s.")
    async def add_temp_role(self, interaction: discord.Interaction, user: discord.Member, duration: app_commands.Transform[int, TimeConverter], role: discord.Role):

        if not duration:
            return await interaction.response.send_message(embed=membed("Use a valid duration format e.g. 1d 7h 19m 4s."))

        if role in user.roles:
            return await interaction.response.send_message(embed=membed("That member already has this role."))

        guild = interaction.guild
        resp = do_boilerplate_role_checks(role, guild, guild.me.top_role)
        if resp:
            return await interaction.response.send_message(embed=membed(resp))
        
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
        success = discord.Embed()
        success.colour = role.colour
        success.title = "Temporary role added"
        success.description = f"Granted {user.mention} the {role.mention} role for "
        success.description += ' and '.join(f"{quantity} {unit}" for quantity, unit in time_components if quantity)

        await user.add_roles(
            discord.Object(id=role.id), 
            reason=f"Temporary role requested by {interaction.user} (ID: {interaction.user.id})"
        )
        await interaction.response.send_message(embed=success)

        # Scheduling task
        timestamp = (discord.utils.utcnow() + timedelta(seconds=duration)).timestamp()

        conn = await self.bot.pool.acquire()
        
        await conn.execute(
            """
            INSERT INTO tasks (mod_to, role_id, end_time, in_guild) 
            VALUES ($0, $1, $2, $3)
            """, user.id, role.id, timestamp, guild.id
        )

        await conn.commit()
        await self.bot.pool.release(conn)

        if self.check_for_role.is_running():
            self.check_for_role.restart()
            return
        self.check_for_role.start()


async def setup(bot: commands.Bot):
    await bot.add_cog(Moderation(bot))
