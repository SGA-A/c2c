from re import compile
from typing import Optional, Union
from datetime import datetime, timedelta

import discord
from pytz import timezone


# ! Existing function that may be used sometime in the future
def parse_duration(input_duration: str) -> datetime:
    
    # Define regular expression pattern to extract days and hours
    pattern = compile(r'(?:(\d+)d)? ?(?:(\d+)h)?')

    # Extract days and hours from the input duration using the pattern
    match = pattern.match(input_duration)

    days = int(match.group(1)) if match.group(1) else 0
    hours = int(match.group(2)) if match.group(2) else 0

    if days == 0 and hours == 0:
        raise ValueError("Invalid duration, years-duration and/or seconds-duration is unsupported.")

    duration = timedelta(days=days, hours=hours)

    # Check if the duration exceeds 14 days
    if duration.days > 14:
        raise ValueError("Duration cannot exceed 14 days.")
    
    return discord.utils.utcnow() + duration


def datetime_to_string(datetime_obj: datetime) -> str:
    """Convert a datetime object to a string object.

    Datetime will be converted to this format: %Y-%m-%d %H:%M:%S
    """

    return f"{datetime_obj:%Y-%m-%d %H:%M:%S}"


def number_to_ordinal(n: int) -> str:
    """Convert 01 to 1st, 02 to 2nd etc."""
    if 10 <= n % 100 <= 20:
        return f"{n}th"
    
    suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
    return f"{n}{suffix}"


def string_to_datetime(string_obj: str) -> datetime:
    """
    Convert a string object to a datetime object.

    String must be in this format: %Y-%m-%d %H:%M:%S

    ## Parameters
    string_obj 
        the input string representing a date and time.
    timezone 
        the timezone to attach to the datetime object.
    ## Returns 
        A datetime object.
    """

    date_format = "%Y-%m-%d %H:%M:%S"
    my_datetime = datetime.strptime(string_obj, date_format)
    my_datetime = my_datetime.replace(tzinfo=timezone("UTC"))
    return my_datetime


async def respond(interaction: discord.Interaction, **kwargs) -> Union[None, discord.WebhookMessage]:
    """Determine if we should respond to the interaction or send followups."""
    if interaction.response.is_done():
        return await interaction.followup.send(**kwargs)
    await interaction.response.send_message(**kwargs)


def membed(custom_description: Optional[str] = None) -> discord.Embed:
    """Quickly construct an embed with an optional description."""
    membedder = discord.Embed(colour=0x2B2D31, description=custom_description)
    return membedder


async def determine_exponent(interaction: discord.Interaction, rinput: str) -> str | int:
    """
    Finds out what the exponential value entered is equivalent to in numerical form. (e.g, 1e6)

    Can handle normal integers.
    
    The shorthands "max" and "all" always return 'as-is', and must be handled yourself.
    """

    rinput = rinput.lower()

    if rinput in {"max", "all"}:
        return rinput
    try:
        if 'e' in rinput:
            before_e_str, after_e_str = map(str, rinput.split('e'))
            before_e = float(before_e_str)
            ten_exponent = min(int(after_e_str), 50)
            actual_value = abs(int(before_e * (10 ** ten_exponent)))
        else:
            rinput = rinput.translate(str.maketrans('', '', ','))
            actual_value = abs(int(rinput))
        
        if not actual_value:
            raise ValueError
        return actual_value

    except (ValueError, TypeError):
        await respond(
            interaction=interaction,
            ephemeral=True,
            embed=membed("You need to provide a real positive number.")
        )
        return


async def economy_check(interaction: discord.Interaction, original: Union[discord.Member, discord.User]) -> bool:
    """Shared interaction check common amongst most interactions."""
    if original.id == interaction.user.id:
        return True
    await interaction.response.send_message(
        ephemeral=True,
        delete_after=5.0,
        embed=membed(f"This menu is controlled by {original.mention}.")
    )
    return False
