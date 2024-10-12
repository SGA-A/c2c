import asyncio
from contextlib import redirect_stdout, suppress
from io import StringIO
from textwrap import dedent, indent
from traceback import format_exc
from typing import Any, Optional

import discord
from discord import app_commands

from ._types import BotExports
from .core.bot import Interaction
from .core.helpers import BaseView


class DevTools(BaseView):
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

    def __init__(self, itx: Interaction) -> None:
        super().__init__(itx, self.on_boarding)

    @staticmethod
    def cleanup_code(content: str) -> str:
        # remove ```py\n```
        if content.startswith("```") and content.endswith("```"):
            return "\n".join(content.split("\n")[1:-1])

        # remove `foo`
        return content.strip("` \n")

    @staticmethod
    async def evaluate(
        itx: Interaction,
        msg: discord.Message
    ) -> Optional[discord.Message]:
        env = {
            "bot": itx.client,
            "itx": itx,
            "channel": itx.channel,
            "user": itx.user,
            "guild": itx.guild,
            "message": msg,
            "_": DevTools._last_result,
            "discord": discord,
            "asyncio": asyncio,
        }

        env.update(globals())

        script_body = DevTools.cleanup_code(msg.content)
        stdout = StringIO()

        to_compile = f"async def func():\n{indent(script_body, '  ')}"

        try:
            exec(to_compile, env)
        except Exception as e:
            return await msg.reply(
                f"```py\n{e.__class__.__name__}: {e}\n```"
            )

        func = env["func"]
        try:
            with redirect_stdout(stdout):
                ret = await func()
        except Exception:
            value = stdout.getvalue()
            await msg.reply(f"```py\n{value}{format_exc()}\n```")
        else:
            value = stdout.getvalue()

            with suppress(discord.HTTPException):
                await msg.add_reaction("\U00002705")

            if ret is None:
                if value:
                    try:
                        await msg.reply(f"```py\n{value}\n```")
                    except discord.HTTPException:
                        return await msg.reply(
                            "Output too long to display."
                        )
            else:
                DevTools._last_result = ret
                await msg.reply(f"```py\n{value}{ret}\n```")

    def eval_check(self, msg: discord.Message) -> bool:
        return (
            (msg.channel.id == self.itx.channel.id) and
            (msg.author.id == self.itx.user.id)
        )

    @discord.ui.button(label="Quit", style=discord.ButtonStyle.success)
    async def _quit(self, itx: Interaction, _: discord.ui.Button) -> None:
        await self.itx.delete_original_response()
        await itx.response.send_message("\U00002705", ephemeral=True)
        await itx.client.close()

    @discord.ui.button(label="Sync", style=discord.ButtonStyle.success)
    async def sync(self, itx: Interaction, _: discord.ui.Button) -> None:
        await itx.client.tree.sync(guild=None)
        await itx.response.send_message("\U00002705", ephemeral=True)

    @discord.ui.button(label="Evaluate", style=discord.ButtonStyle.success)
    async def _eval(self, itx: Interaction, _: discord.ui.Button) -> None:
        await itx.response.send_message("What would you like to evaluate?")

        try:
            msg = await itx.client.wait_for(
                "message", check=self.eval_check, timeout=90.0
            )
        except asyncio.TimeoutError:
            await itx.edit_original_response(
                content="Timed out waiting for a response."
            )
        else:
            await self.evaluate(itx, msg)

    @discord.ui.button(label="Blanket", style=discord.ButtonStyle.success)
    async def blanket(self, itx: Interaction, _: discord.ui.Button) -> None:
        await itx.channel.send(f".{'\n'*1900}\u200b")
        await itx.response.send_message(
            self.on_boarding, view=self, ephemeral=True
        )
        await self.itx.delete_original_response()

        self.itx = itx

    @discord.ui.button(emoji="<:terminatePages:1263923664433319957>")
    async def _stop(self, itx: Interaction, _: discord.ui.Button) -> None:
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


@app_commands.check(is_owner)
@app_commands.command(description="Manage the bot")
async def devtools(itx: Interaction) -> None:
    view = DevTools(itx)
    await itx.response.send_message(
        view.on_boarding,
        view=view,
        ephemeral=True
    )


exports = BotExports([devtools])