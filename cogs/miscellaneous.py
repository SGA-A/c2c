from discord.ext import commands
from discord import app_commands
import unicodedata
import discord


def is_owner(interaction: discord.Interaction):
    if interaction.user.id == interaction.guild.owner_id:
        return True
    return False


class Miscellaneous(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.is_owner()
    @commands.command(name='say')
    async def say(self, ctx, *, text):
        """Makes the bot say what you want it to say."""
        await ctx.message.delete()
        await ctx.send(f"{text}")

    @app_commands.command(name='ping', description='checks the latency of the bot')
    async def ping(self, interaction: discord.Interaction):

        await interaction.response.send_message(content=f"latency: **{round(self.client.latency * 1000)}** ms")

    @app_commands.command(name='com', description='finds out what the most common letters in a word are')
    @app_commands.guilds(discord.Object(id=829053898333225010), discord.Object(id=780397076273954886))
    @app_commands.describe(word='the single word used by the client')
    async def common(self, interaction: discord.Interaction, word: str):

        letters = []
        frequency = []

        for letter in word:
            if letter not in letters:
                letters.append(letter)
                frequency.append(1)
            else:
                i = letters.index(letter)
                frequency[i] += 1

        n = max(frequency)

        # Look for most common letter(s) and add to commons list
        commons = []
        counter = 0
        for m in frequency:
            if n == m:
                commons.append(letters[counter])
            counter += 1

        # Format most common letters
        commons.sort()
        answer = ''
        for letter in commons:
            answer = answer + letter + ' '

        # Remove extra space at the end of the string
        answer = answer[:-1]

        await interaction.response.send_message(content=f'{answer}')

    @app_commands.command(name='charinfo', description='displays unicode/other information of characters (max 25)')
    @app_commands.guilds(discord.Object(id=829053898333225010), discord.Object(id=780397076273954886))
    @app_commands.describe(characters='any written letters or symbols')
    async def charinfo(self, interaction: discord.Interaction, *, characters: str):
        """Shows you information about a number of characters.
        Only up to 25 characters at a time.
        """

        def to_string(c):
            digit = f'{ord(c):x}'
            name = unicodedata.name(c, 'Name not found.')
            return f'`\\U{digit:>08}`: {name} - {c} \N{EM DASH} <http://www.fileformat.info/info/unicode/char/{digit}>'

        msg = '\n'.join(map(to_string, characters))
        if len(msg) > 2000:
            await interaction.response.send_message(content='the output is too long to display', ephemeral=True, delete_after=4.0)
            return
        await interaction.response.send_message(content=f'{msg}')


async def setup(client):
    await client.add_cog(Miscellaneous(client))
