from datetime import timedelta
from typing import Literal, Optional

import discord
from discord import app_commands
from discord.ext import commands
from asqlite import Connection as asqlite_Connection

from .core.helpers import membed


def return_default_user_voice_settings(name: str) -> tuple:
    return (f"{name}'s Channel", 0, 64000, set(), set(), "1 1 1", None)


class MemberSelect(discord.ui.UserSelect):
    def __init__(
        self, 
        tempvoice_instance: "TempVoice", 
        mode: Literal["Block", "Trust"], 
        user: discord.Member
    ) -> None:
        self.mode = mode
        self.tempvoice_instance = tempvoice_instance
        self.verb = f"{self.mode.lower()}ed"
        self.user_data: set[str] = tempvoice_instance.active_voice_channels[user.id][self.verb]

        super().__init__(
            placeholder=f"Select members to {mode.lower()}", 
            min_values=1, 
            max_values=3,
            default_values=[
                discord.SelectDefaultValue.from_user(discord.Object(id=int(user_id))) for user_id in self.user_data
            ]
        )

    def can_allow(self, interaction: discord.Interaction, selected: discord.Member) -> bool:
        return not(selected.guild_permissions.administrator or (selected in {interaction.user, interaction.guild.me}))

    async def callback(self, interaction: discord.Interaction):
        self.view.stop()
        
        selected_without_admin = {str(selected.id) for selected in self.values if self.can_allow(interaction, selected)}
        oppo_verb = "blocked" if self.verb == "trusted" else "trusted"
        
        owner_data = self.tempvoice.active_voice_channels[interaction.user.id]
        trusted_and_blocked = owner_data[oppo_verb].intersection(selected_without_admin)
        if trusted_and_blocked:
            return await interaction.response.edit_message(
                view=None, 
                embed=membed(f"Some of the members selected are {oppo_verb}!")
            )

        selected_without_admin = self.user_data.union(selected_without_admin)
        if selected_without_admin == self.user_data:
            return await interaction.response.edit_message(
                view=None,
                embed=membed(
                    f"No changes were made to {self.verb} users. Ensure that:\n"
                    f"- You did not select admins.\n"
                    f"- You did not select {interaction.client.user.mention}.\n"
                    f"- You did not select yourself."
                )
            )

        overwrites_to_add = selected_without_admin - self.user_data
        overwrites = {**interaction.user.voice.channel.overwrites}        
        
        trust_or_block = discord.PermissionOverwrite()
        is_granted = self.mode == "Trust"
        trust_or_block.update(connect=is_granted, read_messages=is_granted)

        for overwrite_entry in overwrites_to_add:
            overwrites.update({interaction.guild.get_member(int(overwrite_entry)): trust_or_block})

        await interaction.user.voice.channel.edit(overwrites=overwrites)
        self.tempvoice_instance.active_voice_channels[interaction.user.id].update({self.verb: selected_without_admin})

        await interaction.response.edit_message(
            embed=membed(f"{self.mode}ed **{len(selected_without_admin)}** users."), 
            view=None
        )


class PrivacyOptions(discord.ui.Select):
    def __init__(
        self, 
        tempvoice_instance: "TempVoice", 
        voice_channel: discord.VoiceChannel, 
        privacy_setting: list
    ) -> None:
        self.privacy_setting = privacy_setting  #  [Can_connect, Can_view, Can_send_messages] either 0 or 1
        self.voice_channel = voice_channel
        self.tempvoice_instance = tempvoice_instance
        
        options = [
            discord.SelectOption(label="Lock", description="Only trusted users will be able to join"),
            discord.SelectOption(label="Unlock", description="Everyone will be able to join"),
            discord.SelectOption(label="Invisible", description="Only trusted users will be able to view your channel"),
            discord.SelectOption(label="Visible", description="Everyone will be able to view your channel"),
            discord.SelectOption(label="Close Chat", description="Only trusted users will be able to send messages"),
            discord.SelectOption(label="Open Chat", description="Everyone will be able to send messages")
        ]

        super().__init__(placeholder="Select a Privacy Option", options=options)

    async def callback(self, interaction: discord.Interaction):
        self.view.stop()
        chosen = self.values[0]
        overwrites = self.voice_channel.overwrites_for(interaction.guild.default_role)

        if chosen in {"Invisible", "Visible"}:
            colIndex = 1
            check = chosen == "Visible"
            content = f"{self.voice_channel.mention} is **{"no longer hidden" if check else "hidden"}**."
            overwrites.read_messages = check
        elif chosen in {"Close Chat", "Open Chat"}:
            check = chosen == "Open Chat"
            colIndex = 2
            content = f"{self.voice_channel.mention}'s chat is **now {"open" if check else "closed"}**."
            overwrites.send_messages = check
        else:
            colIndex = 0
            check = chosen == "Unlock"
            content = f"{self.voice_channel.mention} has been **{"unlocked" if check else "locked"}**."
            overwrites.connect = check

        self.privacy_setting[colIndex] = str(int(check))
        combination = " ".join(self.privacy_setting)
        self.tempvoice_instance.active_voice_channels[interaction.user.id].update({"privacy": combination})

        await self.voice_channel.set_permissions(interaction.guild.default_role, overwrite=overwrites)
        await interaction.response.edit_message(embed=membed(content), view=None)


class TrustOrBlock(discord.ui.View):
    def __init__(
        self, 
        interaction: discord.Interaction, 
        tempvoice: "TempVoice", 
        mode: Literal["Block", "Trust"]
    ) -> None:
        self.interaction = interaction
        super().__init__(timeout=60.0)

        self.add_item(
            MemberSelect(
                tempvoice_instance=tempvoice, 
                mode=mode, 
                user=interaction.user
            )
        )

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.voice is not None:
            return True
        await interaction.response.edit_message(view=None, embed=membed("You disconnected."))
        return False

    async def on_timeout(self):
        self.children[0].disabled = True
        try:
            await self.interaction.edit_original_response(view=self)
        except discord.NotFound:
            pass


class PrivacyView(discord.ui.View):
    def __init__(
        self, 
        voice_channel: discord.VoiceChannel, 
        tempvoice: "TempVoice", 
        privacy_setting: list, 
        interaction: discord.Interaction
    ) -> None:

        self.interaction = interaction
        super().__init__(timeout=60.0)
        
        self.add_item(
            PrivacyOptions(
                tempvoice_instance=tempvoice,
                voice_channel=voice_channel, 
                privacy_setting=privacy_setting
            )
        )

    async def on_timeout(self):
        self.children[0].disabled = True
        try:
            await self.interaction.edit_original_response(view=self)
        except discord.NotFound:
            pass

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.voice:
            return True
        await interaction.response.edit_message(view=None, embed=membed("You disconnected."))
        return False


class TempVoice(commands.Cog):
    """Interface with temporary voice channels in your server, available for server managers to setup and anyone to use."""
    def __init__(self, bot: commands.Bot) -> None:
        self.bot: commands.Bot = bot
        self.active_voice_channels = {}

    async def store_data_locally(self, *, member: discord.Member, conn: asqlite_Connection) -> None:
        vdata = await conn.fetchone(
            "SELECT name, `limit`, bitrate, blocked, trusted, privacy, status FROM userVoiceSettings WHERE ownerID = ?", member.id)
        if vdata:
            vdata = list(vdata)
            vdata[3] ={uid for uid in vdata[3].split()}
            vdata[4] = {uid for uid in vdata[4].split()}
        vdata = vdata or return_default_user_voice_settings(member.name)
        
        self.active_voice_channels.update(
            {
                member.id: {
                    "name": vdata[0],
                    "limit": vdata[1],
                    "bitrate": vdata[2],
                    "blocked": vdata[3],  # stored as set of strings
                    "trusted": vdata[4],  # stored as set of strings
                    "privacy": vdata[5],
                    "status": vdata[6]
                }
            }
        )

    async def upon_joining_creator(
        self, 
        owner: discord.Member, 
        creator_channel_id: int
    ) -> None:
        user_data = self.active_voice_channels[owner.id]

        category: discord.CategoryChannel = owner.guild.get_channel(creator_channel_id).category
        
        if category is None:
            category = await owner.guild.create_category("TempVoice")
        
        # ! [Can_connect, Can_view, Can_send_messages] either 0 (False) or 1 (True)
        privacy: list = user_data["privacy"].split(" ")

        me_overwrites = discord.PermissionOverwrite()
        me_overwrites.update(
            connect=True, 
            read_messages=True,
            send_messages=True,
            manage_channels=True,
            move_members=True
        )

        everyone_overwrites = discord.PermissionOverwrite()
        everyone_overwrites.update(
            connect=privacy[0] == "1",
            read_messages=privacy[1] == "1",
            send_messages=privacy[-1] == "1"
        )
        
        blocked_overwrites = discord.PermissionOverwrite()
        blocked_overwrites.update(connect=False, read_messages=False)

        owner_overwrites = discord.PermissionOverwrite()
        owner_overwrites.update(
            connect=True, 
            read_messages=True
        )

        overwrites = {
            owner.guild.default_role: everyone_overwrites,
            owner: owner_overwrites,
            owner.guild.me: me_overwrites
        }
        
        # Update permissions for trusted users
        overwrites.update({owner.guild.get_member(int(anyone)): owner_overwrites for anyone in user_data["trusted"]})

        # Update permissions for blocked users
        overwrites.update({owner.guild.get_member(int(anyone)): blocked_overwrites for anyone in user_data["blocked"]})

        try:
            channel = await category.create_voice_channel(
                name=user_data["name"], 
                bitrate=user_data["bitrate"], 
                user_limit=user_data["limit"], 
                overwrites=overwrites
            )
            await owner.move_to(channel)

            current_status = user_data["status"]
            if current_status:
                await channel.edit(status=current_status)

        except discord.RateLimited as rl:
            time_until = discord.utils.format_dt(
                discord.utils.utcnow() + timedelta(seconds=rl.retry_after),
                style="R"
            )

            await owner.send(
                delete_after=25.0,
                embed=discord.Embed(
                    colour=0x2B2D31,
                    title="Slow down!",
                    description=(
                        "You've hit the discord ratelimit for creating voice channels.\n"
                        f"You'll have to try again {time_until}."
                    )
                )
            )
            del self.active_voice_channels[owner.id]
    
    async def handle_mutual_removals(
        self, 
        interaction: discord.Interaction, 
        member: discord.Member, 
        verb: Literal["trusted", "blocked"]
    ) -> None:

        data_searched = self.active_voice_channels[interaction.user.id][verb]
        if str(member.id) not in data_searched:
            return await interaction.response.send_message(
                embed=membed(f"{member.mention} is not a {verb} user."), 
                ephemeral=True
            )
        
        await interaction.user.voice.channel.set_permissions(member, overwrite=None)
        data_searched.remove(str(member.id))
        self.active_voice_channels[interaction.user.id].update({verb: data_searched})
        
        await interaction.response.send_message(
            embed=membed(f"{member.mention} is **no longer {verb}**."), 
            ephemeral=True
        )

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):

        if member.bot:
            return
        if before.channel == after.channel:
            return
        
        async with self.bot.pool.acquire() as conn:
            conn: asqlite_Connection

            query = "SELECT voiceID FROM guildVoiceSettings WHERE guildID = $0"
            creatorChannelID = await conn.fetchone(query, member.guild.id)
            
            if creatorChannelID is None:
                return
            creatorChannelId = creatorChannelID[0]

            if after.channel is None:
                old_channel_data = self.active_voice_channels.get(member.id)

                if old_channel_data is None:  # owner hasnt left yet
                    return
                
                if len(before.channel.members):
                    return
                
                if before.channel.id != creatorChannelId:
                    await before.channel.delete(reason="All users disconnected.")

                old_channel_data.update(
                    {
                        "blocked": " ".join(old_channel_data["blocked"]), 
                        "trusted":" ".join(old_channel_data["trusted"])
                    }
                )
                
                async with conn.transaction():
                    await conn.execute(
                        """
                        INSERT OR REPLACE INTO userVoiceSettings 
                            (ownerID, name, `limit`, bitrate, blocked, trusted, privacy, status) 
                        VALUES 
                            (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (member.id, *old_channel_data.values())
                    )

                    del self.active_voice_channels[member.id]
                return
            
            if after.channel.id == creatorChannelId:  # if user joined creator channel
                await self.store_data_locally(member=member, conn=conn)
                await self.upon_joining_creator(member, creatorChannelId)


    voice = app_commands.Group(
        name="voice", 
        description="Manage your own temporary voice channel.", 
        allowed_contexts=app_commands.AppCommandContext(guild=True),
        allowed_installs=app_commands.AppInstallationType(guild=True)
    )
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        using_setup_cmd = (
            (interaction.command.parent is None) 
            or (self.active_voice_channels.get(interaction.user.id) is not None)
        )
        if using_setup_cmd:
            return True
        await interaction.response.send_message(
            ephemeral=True, 
            embed=membed("You haven't created your own channel yet.")
        )
        return False
    
    @app_commands.command(name="setup", description="Setup a creator channel for temporary voice channels")
    @app_commands.describe(creator_channel="The channel for making temporary voice channels. Leave empty to remove setup.")
    @app_commands.guild_install()
    @app_commands.allowed_contexts(guilds=True)
    async def setup_voice(self, interaction: discord.Interaction, creator_channel: Optional[discord.VoiceChannel] = None):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message(
                ephemeral=True,
                embed=membed("You are not an admin.")
        )
        
        resp = interaction.response.send_message
        embed = discord.Embed(title="Changes to Setup", colour=discord.Colour.blurple())
        async with self.bot.pool.acquire() as conn:
            if creator_channel is None:
                query = "DELETE FROM guildVoiceSettings WHERE guildID = $0 RETURNING voiceID"
                ret = await conn.fetchone(query, interaction.guild.id)
                if ret:
                    ret, = ret
                    await conn.commit()
                    embed.description = f"Removed setup for temporary voice channels in <#{ret}>."
                    return await resp(embed=embed)
                embed.title = "No Setup Found"
                embed.description = "You have not set up temporary voice channels in this server."
                return await resp(embed=embed)

            query = (
                """
                INSERT INTO guildVoiceSettings (guildID, voiceID) 
                VALUES ($0, $1) 
                ON CONFLICT(guildID) 
                DO UPDATE SET voiceID = $1
                """
            )

            await conn.execute(query, interaction.guild.id, creator_channel.id)
            await conn.commit()

        embed.description = f"Set the creator channel to {creator_channel.mention} in this server."
        embed.set_footer(text="Permissions are required, double check they are set.")
        await resp(embed=embed)

    @voice.command(name="rename", description="Change the name of your temporary voice channel")
    @app_commands.checks.cooldown(2, 600.0)
    @app_commands.describe(channel_name="The new name of the temporary voice channel. Leave blank to reset.")
    async def rename_voice(self, interaction: discord.Interaction, channel_name: Optional[str]):

        channel_name = channel_name or f"{interaction.user.name}'s Channel"
        self.active_voice_channels[interaction.user.id].update({"name": channel_name})

        await interaction.user.voice.channel.edit(name=channel_name)
        await interaction.response.send_message(embed=membed(f"Renamed the channel to **{channel_name}**"))

    @voice.command(name="status", description="Set the status of your temporary voice channel")
    @app_commands.checks.cooldown(3, 60.0)
    @app_commands.describe(text="The text shown on the voice channel status. Leave empty to reset it.")
    async def set_status(self, interaction: discord.Interaction, text: Optional[app_commands.Range[str, None, 500]]):
        channel = interaction.user.voice.channel

        self.active_voice_channels[interaction.user.id].update({"status": text})

        await channel.edit(status=text)
        await interaction.response.send_message(embed=membed(f"Set the status of {channel.mention} successfully."))

    @voice.command(name="bitrate", description="Change the bitrate of your temporary voice channel")
    @app_commands.checks.cooldown(1, 15)
    @app_commands.describe(bitrate="The bitrate to set the channel to.")
    async def bitrate_voice(self, interaction: discord.Interaction, bitrate: app_commands.Range[int, 8, 96]):

        bitrate_limit = interaction.guild.bitrate_limit
        if (bitrate * 1000) > bitrate_limit:
            return await interaction.response.send_message(
                embed=membed(f"Bitrate must be less than {bitrate_limit / 1000} kbps."))

        self.active_voice_channels[interaction.user.id].update({"bitrate": bitrate*1000})
        await interaction.user.voice.channel.edit(bitrate=(bitrate*1000))

        await interaction.response.send_message(
            embed=membed(f"Bitrate of {interaction.user.voice.channel.mention} set to **{bitrate}** kbps.")
        )

    @voice.command(name="limit", description="Change the user limit of your temporary voice channel")
    @app_commands.checks.cooldown(1, 15)
    @app_commands.describe(limit="The user limit to set the channel to. 0 for no limit.")
    async def limit_voice(self, interaction: discord.Interaction, limit: app_commands.Range[int, 0, 99]):

        self.active_voice_channels[interaction.user.id].update({"limit": limit})

        await interaction.user.voice.channel.edit(user_limit=limit)
        await interaction.response.send_message(
            embed=membed(f"User limit of {interaction.user.voice.channel.mention} set to **{limit}**."))

    @voice.command(name="privacy", description="Lock or hide your temporary voice channel")
    async def modify_voice_privacy(self, interaction: discord.Interaction):
        
        privacy_view = PrivacyView(
            voice_channel=interaction.user.voice.channel,
            tempvoice=self, 
            privacy_setting=self.active_voice_channels[interaction.user.id]["privacy"].split(), 
            interaction=interaction
        )

        await interaction.response.send_message(view=privacy_view, ephemeral=True)
    
    @voice.command(name="kick", description="Kick a user from your temporary voice channel")
    @app_commands.describe(member="The user to kick from the channel.")
    async def kick_user_voice(self, interaction: discord.Interaction, member: discord.Member):
        user = interaction.user
        user_voice = user.voice
        await interaction.response.defer(thinking=True, ephemeral=True)

        not_found = membed(f"{member.mention} is not in your voice channel.")
        if member.voice is None:
            return await interaction.followup.send(embed=not_found)
        
        if member.voice.channel is not user_voice.channel:
            return await interaction.followup.send(embed=not_found)

        await member.move_to(None, reason=f"Requested by {user.name} (ID: {user.id})")
        await interaction.followup.send(
            ephemeral=True,
            embed=membed(f"Kicked {member.mention} from {user_voice.channel.mention}.")
        )

    @voice.command(name="trust", description="Trust users with permanent access to your temporary voice channel")
    async def change_trusted_users(self, interaction: discord.Interaction):
        trust_view = TrustOrBlock(interaction, tempvoice=self, mode="Trust")
        await interaction.response.send_message(view=trust_view, ephemeral=True)
    
    @voice.command(name="block", description="Block users from accessing your temporary voice channel")
    async def block_users(self, interaction: discord.Interaction):
        block_view = TrustOrBlock(interaction, tempvoice=self, mode="Block")
        await interaction.response.send_message(view=block_view, ephemeral=True)    
    
    @voice.command(name="untrust", description="Remove trusted users access to your temporary channel")
    @app_commands.describe(member="The user to untrust from the channel.")
    async def untrust_users(self, interaction: discord.Interaction, member: discord.Member):
        await self.handle_mutual_removals(interaction, member, "trusted")
    
    @voice.command(name="unblock", description="Remove blocked users from your temporary voice channel")
    @app_commands.describe(member="The user to unblock from the channel.")
    async def unblock_users(self, interaction: discord.Interaction, member: discord.Member):
        await self.handle_mutual_removals(interaction, member, "blocked")

    @voice.command(name="info", description="Get information about a temporary voice channel")
    async def voice_info(self, interaction: discord.Interaction):
        user = interaction.user
        data = self.active_voice_channels[user.id]

        privacy_broken = data["privacy"].split()
        privacy = ["Locked", "Hidden", "Closed Chat"]
        privacy = {privacy[i] for i, check in enumerate(privacy_broken) if check == "0"}

        embed = membed(
            f"- **Bitrate:** {data['bitrate'] // 1000} kbps\n"
            f"- **User Limit:** {data['limit'] or 'No limit'}\n"
            f"- **Privacy:** {', '.join(privacy) or 'Public Configuration'}\n"
        )

        embed.url = user.voice.channel.jump_url
        embed.title = data["name"]

        embed.add_field(
            name="Trusted Members\U000000b9", 
            value=", ".join({self.bot.get_user(int(trusted)).mention for trusted in data["trusted"]}) or "*None.*", 
            inline=False
        )
        
        embed.add_field(
            name="Blocked Members\U000000b2", 
            value=", ".join({self.bot.get_user(int(blocked)).mention for blocked in data["blocked"]}) or "*None.*", 
            inline=False
        )
        
        embed.set_footer(
            text=(
            "\U000000b9 Trusted Members can join your locked or hidden temporary voice channel\n"
            "\U000000b2 Blocked Members cannot see your temporary channel"
            )
        )
        await interaction.response.send_message(embed=embed)

    @voice.command(name="reset", description="Reset and disconnect from your temporary voice channel")
    async def reset_voice(self, interaction: discord.Interaction):

        self.active_voice_channels[interaction.user.id] = return_default_user_voice_settings(interaction.user.name)
        for member in interaction.user.voice.channel.members:
            await member.move_to(None)

        await interaction.response.send_message(
            embed=membed(
                f"Reset {interaction.user.voice.channel.mention}."
            )
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(TempVoice(bot))