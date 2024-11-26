from typing import Any, NamedTuple, Protocol

from discord import Member, User, WebhookMessage
from discord.app_commands import Command, ContextMenu, Group

type UserEntry = Member | User
type ACommand = Command[Any, Any, Any]
type AppCommandTypes = Group | ACommand | ContextMenu
type MaybeWebhook = WebhookMessage | None

class BotExports(NamedTuple):
    commands: list[AppCommandTypes] | None = None


class HasExports(Protocol):
    exports: BotExports
