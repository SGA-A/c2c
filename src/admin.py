import asyncio
from io import StringIO
from traceback import format_exc
from textwrap import indent, dedent
from contextlib import redirect_stdout, suppress
from typing import Any, Optional

import discord
from discord import app_commands

from .core.bot import Interaction
from ._types import BotExports


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

    def __init__(self, itx: Interaction):
        self.itx = itx
        super().__init__(timeout=90.0)

    @staticmethod
    def cleanup_code(content: str) -> str:
        # remove ```py\n```
        if content.startswith("```") and content.endswith("```"):
            return "\n".join(content.split("\n")[1:-1])

        # remove `foo`
        return content.strip("` \n")

    @staticmethod
    async def evaluate(itx: Interaction, message: discord.Message) -> Optional[discord.Message]:
        env = {
            "bot": itx.client,
            "itx": itx,
            "channel": itx.channel,
            "user": itx.user,
            "guild": itx.guild,
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
            return await itx.followup.send(f"```py\n{e.__class__.__name__}: {e}\n```")

        func = env["func"]
        try:
            with redirect_stdout(stdout):
                ret = await func()
        except Exception:
            value = stdout.getvalue()
            await itx.followup.send(f"```py\n{value}{format_exc()}\n```")
        else:
            value = stdout.getvalue()

            with suppress(discord.HTTPException):
                await message.add_reaction("\U00002705")

            if ret is None:
                if value:
                    try:
                        await itx.followup.send(f"```py\n{value}\n```")
                    except discord.NotFound:
                        return await itx.followup.send("Output too long to display.")
            else:
                DevTools._last_result = ret
                await itx.followup.send(f"```py\n{value}{ret}\n```")

    def eval_check(self, msg: discord.Message):
        return (
            (msg.channel.id == self.itx.channel.id) and
            (msg.author.id == self.itx.user.id)
        )

    @discord.ui.button(label="Quit", style=discord.ButtonStyle.success)
    async def quit_button(self, itx: Interaction, _: discord.ui.Button) -> None:
        await self.itx.delete_original_response()
        await itx.response.send_message("\U00002705", ephemeral=True)
        await itx.client.close()

    @discord.ui.button(label="Sync", style=discord.ButtonStyle.success)
    async def sync_button(self, itx: Interaction, _: discord.ui.Button) -> None:
        await itx.client.tree.sync(guild=None)
        await itx.response.send_message("\U00002705", ephemeral=True)

    @discord.ui.button(label="Evaluate", style=discord.ButtonStyle.success)
    async def eval_button(self, itx: Interaction, _: discord.ui.Button) -> None:
        await itx.response.send_message("What would you like to evaluate?")

        try:
            msg = await itx.client.wait_for('message', check=self.eval_check, timeout=90.0)
        except asyncio.TimeoutError:
            await itx.edit_original_response(content="Timed out waiting for a response.")
        else:
            await self.evaluate(itx, msg)

    @discord.ui.button(label="Blanket", style=discord.ButtonStyle.success)
    async def blanket_button(self, itx: Interaction, _: discord.ui.Button) -> None:
        await itx.channel.send(f".{'\n'*1900}\u200b")
        await itx.response.send_message(self.on_boarding, view=self, ephemeral=True)
        await self.itx.delete_original_response()

        self.itx = itx

    @discord.ui.button(emoji="<:terminatePages:1263923664433319957>")
    async def terminate_button(self, itx: Interaction, _: discord.ui.Button) -> None:
        self.stop()
        for item in self.children:
            item.disabled = True
        await itx.response.edit_message(view=self)


async def is_owner(itx: Interaction) -> bool:
    if itx.client.is_owner(itx.user):
        return True
    await itx.response.send_message(
        "You do not own this bot.",
        ephemeral=True
    )
    return False


async def send_role_guide(itx: Interaction) -> None:
    channel = itx.client.get_partial_messageable(1254883155882672249)
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


@app_commands.check(is_owner)
@app_commands.command(description="Manage the bot")
async def devtools(itx: Interaction):
    view = DevTools(itx)
    await itx.response.send_message(view.on_boarding, view=view, ephemeral=True)


exports = BotExports([devtools])