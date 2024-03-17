from discord.ext import commands
from discord import app_commands

from cogs.economy import APP_GUILDS_ID, membed
from typing import Optional
import discord


class PrivacyOptions(discord.ui.Select):
    def __init__(self, client: commands.Bot, 
                 voice_channel: discord.VoiceChannel, privacy_setting: list):
        self.privacy_setting = privacy_setting  #  [Can_connect, Can_view, Can_send_messages] either 0 or 1
        self.voice_channel = voice_channel
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
        
        async with self.client.pool_connection.acquire() as conn:
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
            
            self.privacy_setting[colIndex] = int(check)
            rejoined = " ".join(self.privacy_setting)
            await conn.execute(
                "UPDATE guildVoiceSettings SET privacy = ? WHERE privacy = ?", 
                (rejoined, self.voice_channel.name))
            await conn.commit()

        await self.voice_channel.set_permissions(
            interaction.guild.default_role, overwrite=overwrites)
        await interaction.edit_original_response(embed=membed(content), ephemeral=True, view=None)


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


class TempVoice(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client: commands.Bot = client

    def add_user_to_db(self, member: discord.Member):
        pass  # not sure how to do this yet
    
    voice = app_commands.Group(
        name="voice", 
        description="Temporary voice channel management commands", 
        guild_ids=APP_GUILDS_ID, 
        guild_only=True
        )
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.voice is None:
            await interaction.response.send_message(
                embed=membed(
                    "You need to be in a voice "
                    "channel to use the `/voice` subcommands."))
            return False
        return True

    @voice.command(name="setup", description="Setup a temporary voice channel")
    @app_commands.describe(creator_channel="The channel to use for making temporary voice channels.")
    @app_commands.checks.cooldown(1, 60, key=lambda interaction: interaction.guild_id)
    async def setup_voice(self, interaction: discord.Interaction, creator_channel: discord.VoiceChannel):
        
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                embed=membed("You must be an administrator to use this command."))
            return
        
        embed = discord.Embed()
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
    @app_commands.checks.cooldown(1, 15)
    @app_commands.describe(channel_name="The new name of the temporary voice channel. Leave blank to reset.")
    async def rename_voice(self, interaction: discord.Interaction, channel_name: Optional[str]):
        user = interaction.user
        voice = user.voice
        
        async with self.client.pool_connection.acquire() as conn:
            voice_data = await conn.fetchone(
                "SELECT ownerID FROM guildVoiceSettings WHERE name = $0", user.voice.channel.name)
            if voice_data[0] != user.id:
                return await interaction.response.send_message(
                    embed=membed("You do not own this channel."))
            
            channel_name = channel_name or f"{user.name}'s Channel"
            
            await conn.execute("UPDATE userVoiceSettings SET name = ? WHERE ownerID = ?", (channel_name, user.id))
            await conn.commit()

            await voice.channel.edit(name=channel_name)
            await interaction.response.send_message(
                embed=membed(f"Renamed the channel to **{channel_name}**"))

    @voice.command(name="bitrate", description="Change the bitrate of your temporary voice channel")
    @app_commands.checks.cooldown(1, 15)
    @app_commands.describe(bitrate="The bitrate to set the channel to.")
    async def bitrate_voice(self, interaction: discord.Interaction, bitrate: app_commands.Range[int, 8, 128]):
        user = interaction.user
        voice = user.voice
        
        async with self.client.pool_connection.acquire() as conn:
            
            voice_data = await conn.fetchone(
                "SELECT ownerID FROM guildVoiceSettings WHERE name = $0", user.voice.channel.name)
            if voice_data[0] != user.id:
                return await interaction.response.send_message(
                    embed=membed("You do not own this channel."))

            bitrate_limit = interaction.guild.bitrate_limit
            if (bitrate * 1000) > bitrate_limit:
                return await interaction.response.send_message(embed=membed(f"Bitrate must be less than {bitrate_limit / 1000} kbps."))
            
            await conn.execute("UPDATE userVoiceSettings SET bitrate = ? WHERE ownerID = ?", (bitrate, user.id))
            await conn.commit()

            await voice.channel.edit(bitrate=bitrate)
            await interaction.response.send_message(
                embed=membed(f"Changed the bitrate of {voice.channel.mention} to **{bitrate / 1000}** kbps."))                

    @voice.command(name="limit", description="Change the user limit of your temporary voice channel")
    @app_commands.checks.cooldown(1, 15)
    @app_commands.describe(limit="The user limit to set the channel to. 0 for no limit.")
    async def limit_voice(self, interaction: discord.Interaction, limit: app_commands.Range[int, 0, 99]):
        user = interaction.user
        voice = user.voice
        
        async with self.client.pool_connection.acquire() as conn:
            
            voice_data = await conn.fetchone(
                "SELECT ownerID FROM guildVoiceSettings WHERE name = $0", user.voice.channel.name)
            if voice_data[0] != user.id:
                return await interaction.response.send_message(
                    embed=membed("You do not own this channel."))

            await conn.execute("UPDATE userVoiceSettings SET limit = ? WHERE ownerID = ?", (limit, user.id))
            await conn.commit()

            await voice.channel.edit(user_limit=limit)
            await interaction.response.send_message(
                embed=membed(f"Changed the limit of {voice.channel.mention} to **{limit}** users"))

    @voice.command(name="privacy", description="Lock or hide your temporary voice channel")
    async def modify_voice_privacy(self, interaction: discord.Interaction):
        user = interaction.user
        
        async with self.client.pool_connection.acquire() as conn:
            voice_data = await conn.fetchone(
                "SELECT ownerID, privacy FROM guildVoiceSettings WHERE name = $0", user.voice.channel.name)
            if voice_data[0] != user.id:
                return await interaction.response.send_message(
                    embed=membed("You do not own this channel."))
            
        setting = voice_data[1].split()
        privacy_view = PrivacyView(user.voice.channel, self.client, setting, interaction)
        await interaction.response.send_message(privacy_view, ephemeral=True)
    
    @voice.command(name="kick", description="Kick a user from your temporary voice channel")
    @app_commands.describe(member="The user to kick from the channel.")
    async def kick_user_voice(self, interaction: discord.Interaction, member: discord.Member):
        user = interaction.user

        if member.voice is None:
            return await interaction.response.send_message(
                embed=membed(f"{member.mention} is not in a voice channel."))
        if member.voice.channel.id != user.voice.channel.id:
            return await interaction.response.send_message(
                embed=membed(f"{member.mention} is not in your voice channel."))
        
        async with self.client.pool_connection.acquire() as conn:
            voice_data = await conn.fetchone(
                "SELECT ownerID FROM guildVoiceSettings WHERE name = $0", user.voice.channel.name)
            if voice_data[0] != user.id:
                return await interaction.response.send_message(
                    embed=membed("You do not own this channel."))

        await member.move_to(None, reason=f"Requested by {user.name} (ID: {user.id})")
        await interaction.response.send_message(
            embed=membed(f"Kicked {member.mention} from {user.voice.channel.mention}."), 
            ephemeral=True)


async def setup(client: commands.Bot):
    await client.add_cog(TempVoice(client))
