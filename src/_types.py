from typing import Any, NamedTuple, Protocol

from discord import app_commands


type ACommand = app_commands.Command[Any, Any, Any]
type AppCommandTypes = app_commands.Group | ACommand | app_commands.ContextMenu


class BotExports(NamedTuple):
    commands: list[AppCommandTypes] | None = None


class HasExports(Protocol):
    exports: BotExports