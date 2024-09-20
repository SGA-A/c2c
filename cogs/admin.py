from io import StringIO
from traceback import format_exc
from textwrap import indent, dedent
from contextlib import redirect_stdout
from typing import Any, Optional

import asyncio
import discord

from discord import app_commands
from discord.ext import commands

from .core.bot import C2C
from .core.helpers import membed, edit_response


class DevTools(discord.ui.View):
    _last_result: Optional[Any] = None
    on_boarding = dedent(
        """
        ## Developer Panel
        Select the below options to get started:
        **Quit**
        -# Shut down the bot process gracefully.
        **Sync**
        -# Send a new copy of your command tree to Discord.
        **Evaluate**
        -# Execute arbitrary Python code within Discord.
        **Blanket**
        -# Heavily nest the invocation channel with new lines.
        """
    )

    def __init__(self, interaction: discord.Interaction):
        self.interaction = interaction
        super().__init__(timeout=90.0)
    
    async def respond_timeout(self, interaction: discord.Interaction) -> None:
        self.stop()
        for item in self.children:
            item.disabled = True
        await edit_response(interaction, view=self)

    @staticmethod
    def cleanup_code(content: str) -> str:
        # remove ```py\n```
        if content.startswith("```") and content.endswith("```"):
            return "\n".join(content.split("\n")[1:-1])

        # remove `foo`
        return content.strip("` \n")

    @staticmethod
    async def evaluate(interaction: discord.Interaction, message: discord.Message) -> Optional[discord.Message]:
        env = {
            "bot": interaction.client,
            "itx": interaction,
            "channel": interaction.channel,
            "user": interaction.user,
            "guild": interaction.guild,
            "message": message,
            "_": DevTools._last_result,
            "discord": discord,
            "asyncio": asyncio,
        }

        env.update(globals())

        script_body = DevTools.cleanup_code(message.content)
        stdout = StringIO()

        to_compile = f'async def func():\n{indent(script_body, "  ")}'

        try:
            exec(to_compile, env)
        except Exception as e:
            return await message.reply(f"```py\n{e.__class__.__name__}: {e}\n```")

        func = env["func"]
        try:
            with redirect_stdout(stdout):
                ret = await func()  # return value
        except Exception:
            value = stdout.getvalue()
            await message.reply(f"```py\n{value}{format_exc()}\n```")
        else:
            value = stdout.getvalue()
            try:
                await message.add_reaction("\U00002705")
            except discord.HTTPException:
                pass

            if ret is None:
                if value:
                    try:
                        await message.reply(f"```py\n{value}\n```")
                    except discord.HTTPException:
                        return await message.reply("Output too long to display.")
            else:
                DevTools._last_result = ret
                await message.reply(f"```py\n{value}{ret}\n```")

    def eval_check(self, msg: discord.Message):
        return (
            (msg.channel.id == self.interaction.channel.id) and
            (msg.author.id == self.interaction.user.id)
        )

    @discord.ui.button(label="Quit", style=discord.ButtonStyle.success)
    async def quit_button(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self.interaction.delete_original_response()
        await interaction.response.send_message("\U00002705", ephemeral=True)
        await interaction.client.close()
    
    @discord.ui.button(label="Sync", style=discord.ButtonStyle.success)
    async def sync_button(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.client.tree.sync(guild=None)
        await interaction.response.send_message("\U00002705", ephemeral=True)
    
    @discord.ui.button(label="Evaluate", style=discord.ButtonStyle.success)
    async def eval_button(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.send_message("What would you like to evaluate?")

        try:
            msg = await interaction.client.wait_for('message', check=self.eval_check, timeout=90.0)
        except asyncio.TimeoutError:
            await interaction.edit_original_response(content="Timed out waiting for a response.")
        else:
            await self.evaluate(interaction, msg)

    @discord.ui.button(label="Blanket", style=discord.ButtonStyle.success)
    async def blanket_button(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.channel.send(f".{'\n'*1900}-# Blanked out the channel.")
        await interaction.response.send_message(self.on_boarding, view=self, ephemeral=True)
        await self.interaction.delete_original_response()

        # Disable view items from the new message
        self.interaction = interaction

    @discord.ui.button(emoji="<:terminatePages:1263923664433319957>")
    async def terminate_button(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self.respond_timeout(interaction)


class Admin(commands.Cog):
    """Developer tools relevant to maintainence of the bot. Only available for use by the bot developers."""

    def __init__(self, bot: C2C):
        self.bot = bot

    async def interaction_check(self, interaction: discord.Interaction[C2C]):
        if interaction.user.id in self.bot.owner_ids:
            return True
        await interaction.response.send_message(
            embed=membed("You do not own this bot.")
        )
        return False
    
    @app_commands.command(description="Manage the bot")
    async def devtools(self, interaction: discord.Interaction):
        view = DevTools(interaction)
        await interaction.response.send_message(view.on_boarding, view=view, ephemeral=True)

    async def send_role_guide(self):
        channel = self.bot.get_partial_messageable(1254883155882672249)
        original = channel.get_partial_message(1254901254530924644)

        role_content_pt1 = (
            """
            # Role Guide
            Roles are similar to ranks or accessories that you can add to your profile.
            There are a few self-assignable roles that you can pick up in <id:customize> by clicking on the buttons.

            There are also roles that are given out based on how active you are within the server on a weekly basis:
            - <@&1190772029830471781>: Given to users that sent at least 50 messages in the last week.
            - <@&1190772182591209492>: Given to users that sent at least 150 messages in the last week.

            Other miscellaneous roles for your knowledge:
            - <@&893550756953735278>: The people who manage the server.
            - <@&1148209142465581098>: The role for a backup account, granted administrator permissions.
            - <@&1273655614085664828>: The role verified server members can obtain.
            - <@&1140197893261758505>: Given to people who had their message on the legacy starboard.
            - <@&1121426143598354452>: Given on a per-user basis, granting certain privileges.
            - <@&1150848144440053780>: Bots that only need read access to bot command channels.
            - <@&1150848206008238151>: Bots that require full read access throughout the server.
            """
        )

        await original.edit(content=dedent(role_content_pt1))


async def setup(bot: C2C):
    """Setup for cog."""
    await bot.add_cog(Admin(bot))
