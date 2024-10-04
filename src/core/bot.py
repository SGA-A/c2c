from typing import Self
from random import choice
from psutil import Process
from sqlite3 import IntegrityError
from json import load as json_load
from traceback import format_exception
from logging import error as logging_error
from aiohttp import ClientSession, DummyCookieJar

import discord
from discord import app_commands
from asqlite import Pool, Connection

from .._types import HasExports, AppCommandTypes
from .helpers import membed, add_multiplier
from .errors import CustomTransformerError, FailingConditionalError


type Interaction = discord.Interaction[C2C]


LEVEL_UP_PROMPTS = (
    "Great work",
    "Hard work paid off",
    "Inspiring",
    "Top notch",
    "You're on fire",
    "You're on a roll",
    "Keep it up",
    "Amazing",
    "I'm proud of you",
    "Fantastic work",
    "Superb effort",
    "Brilliant job",
    "Outstanding",
    "You're doing great"
)


def calculate_exp_for(level: int, /) -> int:
    """Calculate the experience points required for a given level."""
    return int((level/0.3)**1.3)


async def add_exp_or_levelup(
    itx: Interaction,
    conn: Connection,
    exp_gainable: int
) -> None:

    record = await conn.fetchone(
        """
        UPDATE accounts
        SET exp = exp + $0
        WHERE userID = $1
        RETURNING exp, level
        """, exp_gainable, itx.user.id
    )

    if record is None:
        return

    xp, level = record
    xp_needed = calculate_exp_for(level)

    if xp < xp_needed:
        return
    level += 1

    await add_multiplier(
        conn,
        user_id=itx.user.id,
        multi_amount=((level // 3) or 1),
        multi_type="xp",
        cause="level",
        description=f"Level {level}"
    )

    await conn.execute(
        """
        UPDATE accounts
        SET
            level = level + 1,
            exp = 0,
            bankspace = bankspace + $0
        WHERE userID = $1
        """, 55_000*level, itx.user.id
    )

    rankup = membed(
        f"{choice(LEVEL_UP_PROMPTS)}, {itx.user.name}!\n"
        f"You've leveled up from level **{level-1:,}** to **{level:,}**."
    )

    await itx.followup.send(embed=rankup)


class BasicTree(app_commands.CommandTree["C2C"]):

    @classmethod
    def from_c2c(cls: type[Self], client: "C2C") -> Self:
        all_installs = app_commands.AppInstallationType(guild=True, user=True)
        all_contexts = app_commands.AppCommandContext(
            guild=True,
            dm_channel=True,
            private_channel=True
        )

        return cls(
            client,
            fallback_to_global=False,
            allowed_contexts=all_contexts,
            allowed_installs=all_installs
        )

    @staticmethod
    def handle_transformer_error(error: app_commands.AppCommandError) -> None:
        if isinstance(error, CustomTransformerError):
            msg = error.cause
        elif error.type.value == discord.AppCommandOptionType.user.value:
            msg = f"{error.value} is not a member of this server."
        elif error.type.value == discord.AppCommandOptionType.string.value:
            msg = "You need to provide a valid number."
        else:
            msg = "An error occurred while processing your input."
        return msg

    async def on_error(
        self,
        itx: Interaction,
        error: app_commands.AppCommandError
    ) -> None:
        try:
            if not itx.response.is_done():
                await itx.response.defer(thinking=True)
            meth = itx.followup.send
        except discord.HTTPException:
            meth = itx.channel.send

        error = getattr(error, "original", error)

        if isinstance(error, app_commands.TransformerError):
            msg = self.handle_transformer_error(error)
        elif isinstance(error, app_commands.CheckFailure):
            if not isinstance(error, FailingConditionalError):
                return
            msg = error.cause
        elif isinstance(error, app_commands.CommandNotFound):
            msg = "This command no longer exists!"
        else:
            self.client.log_exception(error)
            msg = (
                "Seems like the bot has stumbled upon an unexpected error.\n"
                "Not to worry. If the issue persists, please let us know."
            )
        await meth(msg, view=self.client.contact_devs)


class C2C(discord.Client):
    owner_ids = {992152414566232139, 546086191414509599}
    def __init__(self, pool: Pool, initial_exts: list[HasExports]) -> None:
        flags = discord.MemberCacheFlags.none()
        flags.joined = True

        intents = discord.Intents.none()
        intents.message_content = True
        intents.emojis_and_stickers = True
        intents.messages = True
        intents.guilds = True
        intents.members = True

        no_mentions = discord.AllowedMentions.none()

        with open(".\\config.json", "r") as f:
            config: dict[str, str] = json_load(f)
            for k, v in config.items():
                setattr(self, k, v)

        super().__init__(
            allowed_mentions=no_mentions,
            intents=intents,
            max_messages=None,
            member_cache_flags=flags,
            status=discord.Status.idle
        )

        # Setup
        self.pool = pool
        self.initial_exts = initial_exts
        self.tree = BasicTree.from_c2c(self)
        self.session = ClientSession(cookie_jar=DummyCookieJar())

        # Misc
        self.process = Process()
        self.time_launch = discord.utils.utcnow()
        self.contact_devs = discord.ui.View(timeout=5.0).add_item(
            discord.ui.Button(
                label="Contact a developer",
                url="https://www.discordapp.com/users/546086191414509599"
            )
        )

    @staticmethod
    def is_owner(user: discord.abc.User) -> bool:
        return user.id in C2C.owner_ids

    async def on_app_command_completion(
        self,
        itx: Interaction,
        command: AppCommandTypes
    ) -> None:
        """
        Track slash commands ran.

        Increase the interaction user's XP/Level if they are registered.
        """

        if isinstance(itx.command, app_commands.ContextMenu):
            return
        cmd = itx.command.parent or itx.command

        query = (
            """
            WITH multi AS (
                SELECT COALESCE(SUM(amount), 0) AS total
                FROM multipliers
                WHERE (userID IS NULL OR userID = $0)
                AND multi_type = $1
            )

            INSERT INTO command_uses (userID, cmd_name, cmd_count)
            VALUES ($0, $2, 1)
            ON CONFLICT(userID, cmd_name)
                DO UPDATE SET cmd_count = cmd_count + 1
            RETURNING (SELECT total FROM multi)
            """
        )

        async with self.pool.acquire() as conn, conn.transaction():
            try:
                multi, = await conn.fetchone(
                    query, itx.user.id, "xp", f"/{cmd.name}"
                )
            except IntegrityError:
                return

            exp_gainable = command.extras.get("exp_gained")
            if not exp_gainable:
                return

            exp_gainable *= (1+(multi/100))
            await add_exp_or_levelup(itx, conn, int(exp_gainable))

    def log_exception(self, error: Exception) -> None:
        formatted_traceback = "".join(
            format_exception(type(error), error, error.__traceback__)
        )
        logging_error(formatted_traceback)

    async def close(self) -> None:
        await self.pool.close()
        await self.session.close()
        await super().close()

    async def setup_hook(self) -> None:
        # ! If in the future some modules don't have commands
        # ! if mod.exports.commands followed by this branch

        for mod in self.initial_exts:
            for command_obj in mod.exports.commands:
                self.tree.add_command(command_obj)