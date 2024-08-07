from typing import Any

import discord
from discord import app_commands


class ItemTransformerError(app_commands.TransformerError):
    def __init__(
        self, 
        value: Any, 
        opt_type: discord.AppCommandOptionType, 
        transformer: app_commands.Transformer,
        cause: str
    ) -> None:
        super().__init__(value, opt_type, transformer)
        self.cause = cause