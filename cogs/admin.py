import random
from discord.ext import commands
import io
import textwrap
from contextlib import redirect_stdout
import traceback
from typing import Optional, Any
import discord
import asyncio
from discord import app_commands
import nacl


def is_owner(interaction: discord.Interaction):
    if interaction.user.id == interaction.guild.owner_id:
        return True
    return False


class Administrate(commands.Cog):
    def __init__(self, client):
        self.client = client
        self._last_result: Optional[Any] = None

    def cleanup_code(self, content: str) -> str:
        """Automatically removes code blocks from the code."""
        # remove ```py\n```
        if content.startswith('```') and content.endswith('```'):
            return '\n'.join(content.split('\n')[1:-1])

        # remove `foo`
        return content.strip('` \n')

    @app_commands.command(name="unload", description="unload a cog (file) from the client")
    @app_commands.guilds(discord.Object(id=829053898333225010), discord.Object(id=780397076273954886))
    @app_commands.check(is_owner)
    @app_commands.describe(cog='the name of the cog (file) to unload, with the extension.')
    async def unload(self, interaction: discord.Interaction, cog: str):
        await self.client.unload_extension(cog)
        await interaction.response.send_message(content='this cog has been unloaded.', ephemeral=True, delete_after=4.0)

    @app_commands.command(name="load", description="load a cog (file) from the client")
    @app_commands.guilds(discord.Object(id=829053898333225010), discord.Object(id=780397076273954886))
    @app_commands.check(is_owner)
    @app_commands.describe(cog='the name of the cog (file) to load, with the extension.')
    async def load(self, interaction: discord.Interaction, cog: str):
        await self.client.load_extension(cog)
        await interaction.response.send_message(content='this cog has been loaded.', ephemeral=True, delete_after=4.0)

    @app_commands.command(name="reload", description="reload a cog (file) from the client")
    @app_commands.guilds(discord.Object(id=829053898333225010), discord.Object(id=780397076273954886))
    @app_commands.check(is_owner)
    @app_commands.describe(cog='the name of the cog (file) to reload, with the extension.')
    async def reload(self, interaction: discord.Interaction, cog: str):
        await self.client.reload_extension(cog)
        await interaction.response.send_message(content='this cog has been reloaded.', ephemeral=True, delete_after=4.0)

    @commands.is_owner()
    @commands.guild_only()
    @commands.command()
    async def eval(self, ctx, *, body: str):
        """Evaluates arbitary code."""

        env = {
            'client': self.client,
            'ctx': ctx,
            'channel': ctx.channel,
            'author': ctx.author,
            'guild': ctx.guild,
            'message': ctx.message,
            '_': self._last_result,
            'discord': discord,
            'io': io,
            'asyncio': asyncio,
            'random': random,
            'nacl': nacl,
            'pynacl': nacl

        }

        env.update(globals())

        body = self.cleanup_code(body)
        stdout = io.StringIO()

        to_compile = f'async def func():\n{textwrap.indent(body, "  ")}'

        try:
            exec(to_compile, env)
        except Exception as e:
            return await ctx.send(f'```py\n{e.__class__.__name__}: {e}\n```')

        func = env['func']
        try:
            with redirect_stdout(stdout):
                ret = await func()
        except Exception as e:
            value = stdout.getvalue()
            await ctx.send(f'```py\n{value}{traceback.format_exc()}\n```')
        else:
            value = stdout.getvalue()
            try:
                await ctx.message.add_reaction('\u2705')
            except:
                pass

            if ret is None:
                if value:
                    await ctx.send(f'```py\n{value}\n```')
            else:
                self._last_result = ret
                await ctx.send(f'```py\n{value}{ret}\n```')


async def setup(client):
    await client.add_cog(Administrate(client))
