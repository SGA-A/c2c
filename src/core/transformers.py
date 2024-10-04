import discord
from discord import app_commands

from .errors import CustomTransformerError


class RawIntegerTransformer(app_commands.Transformer):
    """
    Transforms a string into an integer,
    only if it's a valid integer or shorthand for one.

    You can customize what happens when a shorthand
    is passed in in places that don't accept them.
    """

    INVALID_ARGUMENT = "You need to provide a real positive number."
    INVALID_SHORTHAND = (
        "Invalid shorthand for number passed in.\n"
        "-# The shorthand may be invalid in this context only, not elsewhere."
    )

    def __init__(self, reject_shorthands: bool = False) -> None:
        super().__init__()
        self.reject_shorthands = reject_shorthands

    def transform(self, _: discord.Interaction, value: str) -> int | str:
        value = value.translate(str.maketrans("", "", ","))

        try:
            converted = int(float(value))
            if converted < 1:
                raise CustomTransformerError(
                    value, self.type, self, self.INVALID_ARGUMENT
                )
        except ValueError as e:
            if self.reject_shorthands or value.lower() not in ("max", "all"):
                raise CustomTransformerError(
                    value, self.type, self, self.INVALID_SHORTHAND
                ) from e
            converted = value
        except OverflowError as e:
            raise CustomTransformerError(
                value, self.type, self, self.INVALID_ARGUMENT
            ) from e
        return converted