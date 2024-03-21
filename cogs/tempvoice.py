from discord.ext import commands
from discord import app_commands

from cogs.economy import APP_GUILDS_ID, membed
from typing import Optional
from asqlite import Connection as asqlite_Connection

import discord


class PrivacyOptions(discord.ui.Select):
    def __init__(self, client: commands.Bot, 
                 voice_channel: discord.VoiceChannel, privacy_setting: list):
        self.privacy_setting = privacy_setting  #  [Can_connect, Can_view, Can_send_messages] either 0 or 1
        self.voice_channel = voice_channel
        self.tempvoice = client.get_cog("TempVoice")
        self.client = client
        
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
        await interaction.response.defer()
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
        self.tempvoice.active_voice_channels[interaction.user.id].update({"privacy": " ".join(self.privacy_setting)})

        await self.voice_channel.set_permissions(interaction.guild.default_role, overwrite=overwrites)
        await interaction.edit_original_response(embed=membed(content), view=None)


class PrivacyView(discord.ui.View):
    def __init__(
            self, voice_channel: discord.VoiceChannel, 
            client: commands.Bot, privacy_setting: list, 
            interaction: discord.Interaction):
        self.interaction = interaction
        super().__init__(timeout=60.0)
        self.add_item(PrivacyOptions(client, voice_channel, privacy_setting))

    async def on_timeout(self):
        self.children[0].disabled = True
        try:
            await self.interaction.edit_original_response(view=self)
        except discord.NotFound:
            pass
    
    async def on_error(self, interaction: discord.Interaction[discord.Client], error: Exception, item: discord.ui.Item) -> None:
        await interaction.edit_original_response(
            embed=membed("Something went wrong. You should try again later when the developers resolve the issue."), view=None
        )        


class TempVoice(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client: commands.Bot = client
        self.active_voice_channels = {}

    async def store_data_locally(self, *, member: discord.Member, conn: asqlite_Connection):
        vdata = await conn.fetchone(
            "SELECT name, `limit`, bitrate, blocked, trusted, privacy FROM userVoiceSettings WHERE ownerID = ?", member.id)

        vdata = vdata or (f"{member.name}'s Channel", 0, 64000, set(), set(), "1 1 1")
        
        self.active_voice_channels.update(
            {
                member.id: {
                    "name": vdata[0],
                    "limit": vdata[1],
                    "bitrate": vdata[2],
                    "blocked": vdata[3],  # stored as set of strings
                    "trusted": vdata[4],  # stored as set of strings
                    "privacy": vdata[5]
                }
            })
        # TODO tranform set of strings into a single string using join meth

    async def upon_joining_creator(
            self, owner: discord.Member, creator_channel_id: int):
        user_data = self.active_voice_channels[owner.id]

        category: discord.CategoryChannel = owner.guild.get_channel(creator_channel_id).category
        
        if category is None:
            category = await owner.guild.create_category("TempVoice")
        
        # ! [Can_connect, Can_view, Can_send_messages] either 0 (False) or 1 (True)
        privacy: list = user_data["privacy"].split()

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
        
        owner_overwrites = discord.PermissionOverwrite()
        owner_overwrites.update(
            connect=True, 
            read_messages=True, 
            send_messages=True
        )

        overwrites = {
            owner.guild.default_role: everyone_overwrites,
            owner: owner_overwrites,
            owner.guild.me: me_overwrites
        }
        try:
            channel = await category.create_voice_channel(
                name=user_data["name"], 
                bitrate=user_data["bitrate"], 
                user_limit=user_data["limit"], overwrites=overwrites)
        except discord.RateLimited as rl:
            print(f"we are being ratelimited, try again in {rl.retry_after}s")
            del self.active_voice_channels[owner.id]
        await owner.move_to(channel)
    
    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):

        if member.bot:
            return
        if before.channel == after.channel:
            return
        
        async with self.client.pool_connection.acquire() as conn:
            conn: asqlite_Connection

            creatorChannelId = await conn.fetchone(
                "SELECT voiceID FROM guildVoiceSettings WHERE guildID = $0", member.guild.id)
            
            if creatorChannelId is None:
                return
            creatorChannelId = creatorChannelId[0]

            if after.channel is None:
                if (len(before.channel.members)-1) > 0:
                    return
                
                if before.channel.id != creatorChannelId:
                    await before.channel.delete(reason="All users disconnected.")

                try:
                    old_channel_data: dict = self.active_voice_channels[member.id]
                except KeyError:  # if the bot reset/reloaded
                    return

                old_channel_data.update(
                    {
                        "blocked": " ".join(old_channel_data["blocked"]), 
                        "trusted":" ".join(old_channel_data["trusted"])})
                
                async with conn.transaction():
                    await conn.execute(
                        """
                        UPDATE userVoiceSettings 
                        SET name = ?, `limit` = ?, bitrate = ?, blocked = ?, trusted = ?, privacy = ?""", 
                        *old_channel_data)
                    del self.active_voice_channels[member.id]
                return
            
            if after.channel.id == creatorChannelId:  # if user joined creator channel
                await self.store_data_locally(member=member, conn=conn)
                await self.upon_joining_creator(member, creatorChannelId)
                return
            
            if after.channel is not None:  # if it is a temp vc
                if before.channel.id == creatorChannelId:
                    return
                
                if str(member.id) in self.active_voice_channels[member.id]["blocked"]:
                    return await member.move_to(None, reason="This user is blocked.")


    voice = app_commands.Group(
        name="voice", 
        description="Temporary voice channel management commands", 
        guild_ids=APP_GUILDS_ID, 
        guild_only=True
        )
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return self.active_voice_channels.get(interaction.user.id) is not None

    @voice.command(name="setup", description="Setup a temporary voice channel")
    @app_commands.describe(creator_channel="The channel to use for making temporary voice channels.")
    @app_commands.checks.cooldown(1, 60, key=lambda interaction: interaction.guild_id)
    async def setup_voice(self, interaction: discord.Interaction, creator_channel: discord.VoiceChannel):
        
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                embed=membed("You are not an admin."))
            return
        
        embed = discord.Embed(title="Setup Complete")
        async with self.client.pool_connection.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO guildVoiceSettings (guildID, voiceID) VALUES ($0, $1) 
                ON CONFLICT (guildID) DO UPDATE SET voiceID = $1""", 
                interaction.guild.id, creator_channel.id)
            await conn.commit()

        embed.description = f"Set the creator channel to {creator_channel.mention}."
        embed.colour = discord.Colour.blurple()

        await interaction.response.send_message(embed=embed)

    @voice.command(name="rename", description="Change the name of your temporary voice channel")
    @app_commands.checks.cooldown(2, 600.0)
    @app_commands.describe(channel_name="The new name of the temporary voice channel. Leave blank to reset.")
    async def rename_voice(self, interaction: discord.Interaction, channel_name: Optional[str]):
        user = interaction.user

        channel_name = channel_name or f"{user.name}'s Channel"
        self.active_voice_channels[user.id].update({"name": channel_name})

        await user.voice.channel.edit(name=channel_name)
        await interaction.response.send_message(
            embed=membed(f"Renamed the channel to **{channel_name}**"))

    @voice.command(name="bitrate", description="Change the bitrate of your temporary voice channel")
    @app_commands.checks.cooldown(1, 15)
    @app_commands.describe(bitrate="The bitrate to set the channel to.")
    async def bitrate_voice(self, interaction: discord.Interaction, bitrate: app_commands.Range[int, 8, 96]):
        user = interaction.user
        voice = user.voice
        
        bitrate_limit = interaction.guild.bitrate_limit
        if (bitrate * 1000) > bitrate_limit:
            return await interaction.response.send_message(
                embed=membed(f"Bitrate must be less than {bitrate_limit / 1000} kbps."))

        self.active_voice_channels[user.id].update({"bitrate": bitrate*1000})
        await voice.channel.edit(bitrate=(bitrate*1000))

        await interaction.response.send_message(
            embed=membed(f"Changed the bitrate of {voice.channel.mention} to **{bitrate / 1000}** kbps."))                

    @voice.command(name="limit", description="Change the user limit of your temporary voice channel")
    @app_commands.checks.cooldown(1, 15)
    @app_commands.describe(limit="The user limit to set the channel to. 0 for no limit.")
    async def limit_voice(self, interaction: discord.Interaction, limit: app_commands.Range[int, 0, 99]):
        user = interaction.user
        voice = user.voice

        self.active_voice_channels[user.id].update({"limit": limit})

        await voice.channel.edit(user_limit=limit)
        await interaction.response.send_message(
            embed=membed(f"Changed the limit of {voice.channel.mention} to **{limit}** users"))

    @voice.command(name="privacy", description="Lock or hide your temporary voice channel")
    async def modify_voice_privacy(self, interaction: discord.Interaction):
        user = interaction.user
        
        setting = self.active_voice_channels[user.id]["privacy"].split()
        privacy_view = PrivacyView(user.voice.channel, self.client, setting, interaction)
        await interaction.response.send_message(view=privacy_view, ephemeral=True)
    
    @voice.command(name="kick", description="Kick a user from your temporary voice channel")
    @app_commands.describe(member="The user to kick from the channel.")
    async def kick_user_voice(self, interaction: discord.Interaction, member: discord.Member):
        user = interaction.user
        user_voice = user.voice

        not_found = membed(f"{member.mention} is not in your voice channel.")
        if member.voice is None:
            return await interaction.response.send_message(embed=not_found)
        
        if member.voice.channel is not user_voice.channel:
            return await interaction.response.send_message(embed=not_found)

        await member.move_to(None, reason=f"Requested by {user.name} (ID: {user.id})")
        await interaction.response.send_message(
            embed=membed(f"Kicked {member.mention} from {user_voice.channel.mention}."), 
            ephemeral=True)


async def setup(client: commands.Bot):
    await client.add_cog(TempVoice(client))
