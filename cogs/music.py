import yt_dlp as youtube_dl

from re import findall
from os.path import basename
from discord.ext import commands
from asyncio import TimeoutError as asyncTE, get_event_loop

from discord import (
    FFmpegPCMAudio, 
    PCMVolumeTransformer
)

from cogs.economy import membed


# Suppress noise about console usage from errors
youtube_dl.utils.bug_reports_message = lambda: ''


ytdl_format_options = {
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
    'source_address': '0.0.0.0',  # bind to ipv4 since ipv6 addresses cause issues sometimes
}

ffmpeg_options = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5','options': '-vn -filter:a "volume=0.25"'}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)


class YTDLSource(PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)

        self.data = data

        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(FFmpegPCMAudio(filename, **ffmpeg_options), data=data)


class Music(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot: commands.Bot = bot

    async def cog_check(self, ctx: commands.Context) -> bool:
        role = ctx.guild.get_role(990900517301522432)
        return (role is None) or (role in ctx.author.roles)

    async def play_source(self, voice_client):
        source = FFmpegPCMAudio("C:\\Users\\georg\\PycharmProjects\\c2c\\other\\battlet.mp3")
        voice_client.play(source, after=lambda e: print('Player error: %s' % e) if e else self.bot.loop.create_task(self.play_source(voice_client)))

    @commands.command(description="Join a voice channel")
    async def join(self, ctx: commands.Context):
        await ctx.message.add_reaction('<:successful:1183089889269530764>')
        await ctx.author.voice.channel.connect(self_deaf=True)

    @commands.command(description='Quickly join and play some music')
    async def preset(self, ctx: commands.Context):
        async with ctx.typing():
            channel = ctx.message.author.voice.channel
            voice = await channel.connect(self_deaf=True)
            await self.bot.loop.create_task(self.play_source(voice))
        
        await ctx.send(embed=membed("Now playing: ` Scaramouche Battle Theme.mp3 `"))

    @commands.command(description='Plays a file from the local filesystem')
    async def play(self, ctx: commands.Context):
        channel = ctx.channel

        choice = membed(
            "Send the number that corresponds to the song you wish to play.\n"
            "` 1 ` - Best Music of Genshin Impact\n"
            "` 2 ` - Discord Stage Music 1 Hour\n"
            "` 3 ` - Fortnite Loading Screen EXTENDED\n"
            "` 4 ` - Mellow Vibe lo-fi beats\n"
            "` 5 ` - Sumeru lo-fi beats\n"
            "` 6 ` - Tokyo lo-fi HipHop Mix\n"
            "` 7 ` - Study lo-fi HipHop Mix (You Inspire Me)"
        )

        my_msg = await ctx.send(
            content=ctx.author.mention,
            embed=choice
        )

        def check(message):
            return (
                message.channel == channel and 
                message.content in {"1", "2", "3", "4", "5", "6", "7"} and 
                message.author == ctx.author
            )

        try:
            msg = await self.bot.wait_for('message', check=check, timeout=15.0)
        except asyncTE:
            await my_msg.edit(embed=membed("Timed out waiting for a response."))
        else:
            quantity = int(findall(r'\d+', msg.content)[0])

            pathn = {
                1: "C:\\Users\\georg\\Music\\Best Music of Genshin Impact.mp3",
                2: "C:\\Users\\georg\\Music\\Discord Stage Music 1 Hour.mp3",
                3: "C:\\Users\\georg\\Music\\Fortnite Loading Screen Music.mp3",
                4: "C:\\Users\\georg\\Music\\Mellow Vibe.mp3",
                5: "C:\\Users\\georg\\Music\\sumeru lo-fi beats.mp3",
                6: "C:\\Users\\georg\\Music\\Tokyo Lofi HipHop Mix.mp3",
                7: "C:\\Users\\georg\\Music\\You inspire me.mp3"
            }.get(quantity)

            source = PCMVolumeTransformer(FFmpegPCMAudio(pathn))
            file_name = basename(pathn)
            ctx.voice_client.play(source, after=lambda e: print(f'Player error: {e}') if e else None)

            await my_msg.edit(embed=membed(f'Now playing: `{file_name}`'))

    @commands.command(description="Streams music via url from YouTube")
    async def stream(self, ctx: commands.Context, *, url):

        async with ctx.typing():
            player = await YTDLSource.from_url(url, loop=self.bot.loop, stream=True)
            ctx.voice_client.play(player, after=lambda e: print(f'Player error: {e}') if e else None)

        await ctx.send(embed=membed(f'Now playing: [{player.title}]({player.url})'))

    @commands.command(name='pause', description='Pause the player, if playing music')
    async def pause(self, ctx: commands.Context):

        if not ctx.voice_client.is_playing():
            return await ctx.send(embed=membed("The player is already paused."))
        
        ctx.voice_client.pause()
        return await ctx.message.add_reaction('<:successful:1183089889269530764>')

    @commands.command(description='Resume the player')
    async def resume(self, ctx: commands.Context):
        if not ctx.voice_client.is_paused():
            return await ctx.send(embed=membed("The player is not paused."))
        
        ctx.voice_client.resume()
        await ctx.message.add_reaction('<:successful:1183089889269530764>')

    @commands.command(description="Changes the player's volume", aliases=('vol',))
    async def volume(self, ctx: commands.Context, volume: int):
        ctx.voice_client.source.volume = volume / 100
        await ctx.send(embed=membed(f"Changed volume to {volume}%"))

    @commands.command(description='Disconnect the bot from voice', aliases=('leave', 'disconnect'))
    async def stop(self, ctx: commands.Context):
        await ctx.voice_client.disconnect()
        await ctx.message.add_reaction('<:successful:1183089889269530764>')

    @play.before_invoke
    @stream.before_invoke
    @pause.before_invoke
    @resume.before_invoke
    @volume.before_invoke
    @stop.before_invoke
    async def ensure_voice(self, ctx: commands.Context):
        if (ctx.voice_client is None) and (ctx.voice_client.channel != ctx.author.voice.channel):
            await ctx.send(embed=membed("I'm not in your voice channel."))


async def setup(bot: commands.Bot):
    await bot.add_cog(Music(bot))
