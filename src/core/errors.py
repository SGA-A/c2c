from typing import Any

import discord
from discord import app_commands


class CustomTransformerError(app_commands.TransformerError):
    """
    Exception that's raised when an error occurs
    during the transformation of an argument.

    Contains an additional attribute `cause` that
    describes the cause of the error.
    """
    def __init__(
        self,
        value: Any,
        opt_type: discord.AppCommandOptionType,
        transformer: app_commands.Transformer,
        cause: str
    ) -> None:
        super().__init__(value, opt_type, transformer)
        self.cause = cause


class FailingConditionalError(app_commands.CheckFailure):
    """
    Exception raised when a condition required for
    the command to continue is not met.
    """
    def __init__(self, cause: str) -> None:
        self.cause = cause
        super().__init__()