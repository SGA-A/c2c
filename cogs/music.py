from discord import FFmpegPCMAudio, VoiceChannel, PCMVolumeTransformer, Embed
from discord.ext import commands
from asyncio import TimeoutError as asyncTE
from re import findall
from os.path import basename


class Music(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client: commands.Bot = client

    async def cog_check(self, ctx: commands.Context) -> bool:
        role = ctx.guild.get_role(990900517301522432)
        if (role in ctx.author.roles) or (role is None):
            return True
        return False

    async def play_source(self, voice_client):
        source = FFmpegPCMAudio("C:\\Users\\georg\\PycharmProjects\\c2c\\other\\battlet.mp3")
        voice_client.play(source, after=lambda e: print('Player error: %s' % e) if e else self.client.loop.create_task(
            self.play_source(voice_client)))

    @commands.command(name='join', description="Join a voice channel")
    async def join(self, ctx, *, channel: VoiceChannel):
        """Joins a voice channel"""
        await ctx.message.add_reaction('<:successful:1183089889269530764>')

        if ctx.voice_client is not None:
            return await ctx.voice_client.move_to(channel)

        await channel.connect(self_deaf=True)

    @commands.command(name='preset', description='Quickly join and play some music')
    async def use_preset(self, ctx):
        async with ctx.typing():
            if ctx.author.voice:
                channel = ctx.message.author.voice.channel
                voice = await channel.connect(self_deaf=True)
                await self.client.loop.create_task(self.play_source(voice))
                await ctx.send("Done. Now playing `Scaramouche Battle Theme.mp3`")
            else:
                await ctx.send('You aren\'t in a voice channel.')

    @commands.command(name='play', description='Plays a file from the local filesystem')
    async def play_music(self, ctx,):
        """Plays a file from the local filesystem"""
        channel = ctx.channel

        choice = Embed(title='Choose a song to play',
                       description='Send the number that corresponds to the song you wish to play.\n'
                                   '`1` - Best Music of Genshin Impact\n'
                                   '`2` - Discord Stage Music 1 Hour\n'
                                   '`3` - Fortnite Loading Screen EXTENDED\n'
                                   '`4` - Mellow Vibe lo-fi beats\n'
                                   '`5` - Sumeru lo-fi beats\n'
                                   '`6` - Tokyo lo-fi HipHop Mix\n'
                                   '`7` - Study lo-fi HipHop Mix (You Inspire Me)',
                       colour=0x313338)

        my_msg = await ctx.send(
            content=f"*Waiting for input from {ctx.author}..*",
            embed=choice)

        def check(message):
            return message.channel == channel and message.content in {"1", "2", "3", "4", "5", "6", "7"}

        try:
            msg = await self.client.wait_for('message', check=check, timeout=15.0)

        except asyncTE:
            await my_msg.edit(content="Timed out waiting for a response.", embed=None)

        else:

            # Use regular expression to find the numeric value
            matches = findall(r'\d+', msg.content)

            # If there are matches, get the first one and convert it to an integer
            quantity = matches[0]  # if matches else 0

            files = {
                "1": "C:\\Users\\georg\\Music\\Best Music of Genshin Impact.mp3",
                "2": "C:\\Users\\georg\\Music\\Discord Stage Music 1 Hour.mp3",
                "3": "C:\\Users\\georg\\Music\\Fortnite Loading Screen Music.mp3",
                "4": "C:\\Users\\georg\\Music\\Mellow Vibe.mp3",
                "5": "C:\\Users\\georg\\Music\\sumeru lo-fi beats.mp3",
                "6": "C:\\Users\\georg\\Music\\Tokyo Lofi HipHop Mix.mp3",
                "7": "C:\\Users\\georg\\Music\\You inspire me.mp3"
            }
            pathn = files.get(str(quantity))
            source = PCMVolumeTransformer(FFmpegPCMAudio(pathn))
            file_name = basename(pathn)
            ctx.voice_client.play(source, after=lambda e: print(f'Player error: {e}') if e else None)

            await my_msg.edit(content=f'Now playing: `{file_name}`', embed=None)

    @commands.command(name='pause', description='Pause the player, if playing music')
    async def pause_cl(self, ctx):
        if ctx.voice_client:
            if ctx.voice_client.is_playing():
                ctx.voice_client.pause()
                return await ctx.message.add_reaction('<:successful:1183089889269530764>')
            else:
                return await ctx.send("The player is already paused.")
        else:
            await ctx.send("Not connected to voice.")

    @commands.command(name='resume', description='Resume the player, if music is paused')
    async def resume_cl(self, ctx):
        if ctx.voice_client:
            if ctx.voice_client.is_paused():
                ctx.voice_client.resume()
                return await ctx.message.add_reaction('<:successful:1183089889269530764>')
            else:
                return await ctx.send("The player is not paused.")
        await ctx.send("Not connected to voice.")

    @commands.command(name='volume', description="Changes the player's volume")
    async def volume(self, ctx, volume: int):
        """Changes the player's volume"""

        if ctx.voice_client is None:
            return await ctx.send("You aren't connected to a voice channel.")

        ctx.voice_client.source.volume = volume / 100
        await ctx.send(f"Changed volume to {volume}%")

    @commands.command(name='stop', description='Stops the player, disconnecting the bot from voice',
                      aliases=('leave', 'disconnect'))
    async def stop(self, ctx):
        """Stops and disconnects the bot from voice"""
        await ctx.voice_client.disconnect()
        await ctx.message.add_reaction('<:successful:1183089889269530764>')

    @play_music.before_invoke
    async def ensure_voice(self, ctx):
        if ctx.voice_client is None:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect(self_deaf=True)
            else:
                await ctx.send("You are not connected to a voice channel.")
                raise commands.CommandError("Not connected to a voice channel.")
        elif ctx.voice_client.is_playing():
            ctx.voice_client.stop()


async def setup(client: commands.Bot):
    await client.add_cog(Music(client))
