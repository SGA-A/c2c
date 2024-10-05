from typing import Any, NamedTuple, Protocol

from discord.app_commands import Command, ContextMenu, Group

type ACommand = Command[Any, Any, Any]
type AppCommandTypes = Group | ACommand | ContextMenu


class BotExports(NamedTuple):
    commands: list[AppCommandTypes] | None = None


class HasExports(Protocol):
    exports: BotExports