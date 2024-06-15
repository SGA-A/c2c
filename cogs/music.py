from typing import Literal
from os.path import basename
from asyncio import get_event_loop

import discord
import yt_dlp as youtube_dl
from discord.ext import commands
from discord import app_commands

from .core.helpers import membed
from .core.constants import APP_GUILDS_IDS


# Suppress noise about console usage from errors
youtube_dl.utils.bug_reports_message = lambda: ''


YTDL_FORMAT_OPTIONS = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'
}

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 
    'options': '-vn -filter:a "volume=0.25"'
}

ytdl = youtube_dl.YoutubeDL(YTDL_FORMAT_OPTIONS)


class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5) -> None:
        super().__init__(source, volume)

        self.data = data

        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None) -> "YTDLSource":
        loop = loop or get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False))

        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]

        filename = data['url']
        return cls(discord.FFmpegPCMAudio(filename, **FFMPEG_OPTIONS), data=data)


class Music(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot: commands.Bot = bot

    async def play_source(self, voice_client):
        source = discord.FFmpegPCMAudio("C:\\Users\\georg\\Documents\\c2c\\battlet.mp3")
        voice_client.play(source, after=lambda e: print('Player error: %s' % e) if e else self.bot.loop.create_task(self.play_source(voice_client)))
    
    async def do_join_checks(self, interaction: discord.Interaction):
        if (interaction.user.voice is None):
            await interaction.followup.send(embed=membed("Connect to a voice channel first."))
            return
        
        if interaction.guild.voice_client is not None:
            if (interaction.user not in interaction.guild.me.voice.channel.members):
                await interaction.followup.send(
                    embed=membed(f"Connect to {interaction.guild.me.voice.channel.mention} first.")
                )
                return
            return interaction.guild.voice_client
        
        voice = await interaction.user.voice.channel.connect()
        await interaction.guild.me.edit(deafen=True)
        return voice

    @app_commands.guilds(*APP_GUILDS_IDS)
    @app_commands.command(description='Quickly join and play some music')
    async def preset(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        voice = await self.do_join_checks(interaction)
        if not voice:
            return
        
        if voice.is_playing():
            voice.stop()

        await self.bot.loop.create_task(self.play_source(voice))
        await interaction.followup.send(embed=membed("Now playing: `Scaramouche Battle Theme.mp3`."))

    @app_commands.guilds(*APP_GUILDS_IDS)
    @app_commands.command(description='Plays a file from the local filesystem')
    @app_commands.describe(song="The name of the song to play.")
    async def play(
        self, 
        interaction: discord.Interaction, 
        song: Literal["Say You Won't Let Go"]
    ) -> None:
        await interaction.response.defer(ephemeral=True)

        voice = await self.do_join_checks(interaction)
        if not voice:
            return

        if voice.is_playing():
            voice.stop()

        pathn = f"C:\\Users\\georg\\Music\\{song}.mp3"
        source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(pathn))
        file_name = basename(pathn)
        
        voice.play(source, after=lambda e: print(f'Player error: {e}') if e else None)
        await interaction.followup.send(embed=membed(f'Now playing: ` {file_name} `.'))

    @app_commands.guilds(*APP_GUILDS_IDS)
    @app_commands.describe(query="Could be a search term or a YouTube track link.")
    @app_commands.command(description="Streams music via url from YouTube")
    async def stream(self, interaction: discord.Interaction, query: str):
        await interaction.response.defer(ephemeral=True)

        voice = await self.do_join_checks(interaction)
        if not voice:
            return

        if voice.is_playing():
            voice.stop()

        player = await YTDLSource.from_url(query, loop=self.bot.loop)
        voice.play(player, after=lambda e: print(f'Player error: {e}') if e else None)
        await interaction.followup.send(embed=membed(f'Now playing: [{player.title}]({player.url}).'))

    @app_commands.guilds(*APP_GUILDS_IDS)
    @app_commands.command(description='Pause the player')
    async def pause(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        voice = await self.do_join_checks(interaction)
        if not voice:
            return
        
        if not voice.is_playing():
            return await interaction.followup.send(embed=membed("The player is already paused."))
        
        voice.pause()
        return await interaction.followup.send(embed=membed("Paused the player."))

    @app_commands.guilds(*APP_GUILDS_IDS)
    @app_commands.command(description='Resume the player')
    async def resume(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        voice = await self.do_join_checks(interaction)
        if not voice:
            return
        
        if not voice.is_paused():
            return await interaction.followup.send(embed=membed("The player is not paused."))
        
        voice.resume()
        await interaction.followup.send(embed=membed("Resumed the player."))

    @app_commands.guilds(*APP_GUILDS_IDS)
    @app_commands.describe(volume="The volume to set the player to")
    @app_commands.command(description="Changes the player's volume")
    async def volume(self, interaction: discord.Interaction, volume: app_commands.Range[int, 1, 250]):
        await interaction.response.defer(ephemeral=True)

        voice = await self.do_join_checks(interaction)
        if not voice:
            return

        voice.source.volume = volume / 100
        await interaction.followup.send(embed=membed(f"Changed volume of the player to {volume}%."))

    @app_commands.guilds(*APP_GUILDS_IDS)
    @app_commands.command(description='Stop the player')
    async def stop(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        voice = await self.do_join_checks(interaction)
        if not voice:
            return
        
        if not voice.is_playing():
            return await interaction.followup.send(embed=membed("The player is not playing."))
        
        voice.stop()
        await interaction.followup.send(embed=membed("Stopped the player."))

    @app_commands.guilds(*APP_GUILDS_IDS)
    @app_commands.command(description='Disconnect the bot from voice')
    async def leave(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        if interaction.guild.voice_client is None:
            return await interaction.followup.send(embed=membed("I'm not in a voice channel."))
        
        if interaction.user not in interaction.guild.me.voice.channel.members:
            return await interaction.followup.send(
                embed=membed(f"Connect to {interaction.guild.me.voice.channel.mention} first.")
            )
        
        if interaction.guild.voice_client.is_playing():
            interaction.guild.voice_client.stop()

        await interaction.guild.voice_client.disconnect()
        await interaction.followup.send(embed=membed("Disconnected the player."))


async def setup(bot: commands.Bot):
    await bot.add_cog(Music(bot))
