"""The virtual economy system of the bot."""
import sqlite3
import datetime
from re import search
from asyncio import sleep
from textwrap import dedent
from math import floor, ceil
from traceback import print_exception
from string import ascii_letters, digits

from random import (
    randint, 
    choices, 
    choice, 
    sample, 
    shuffle
)

from typing import (
    Coroutine, 
    Optional, 
    Literal, 
    Any, 
    Union, 
    List, 
    Callable
)

import discord
import aiofiles
from pytz import timezone
from pluralizer import Pluralizer
from ImageCharts import ImageCharts
from discord.ext import commands, tasks
from discord import app_commands, SelectOption
from asqlite import ProxiedConnection as asqlite_Connection

from .core.helpers import (
    determine_exponent, 
    membed,
    respond,
    economy_check
)

from .core.views import process_confirmation
from .core.constants import CURRENCY, APP_GUILDS_IDS
from .core.paginator import PaginationItem, RefreshPagination, RefreshSelectPaginationExtended


def swap_elements(x, index1, index2) -> None:
    """Swap two elements in place given their indices, return None.
    
    lst: the list to swap elements in
    index1: the index of the element you want to swap
    index2: the index of the element you want to swap it with
    """

    x[index1], x[index2] = x[index2], x[index1]


def add_multi_to_original(*, multi: int, original: int) -> int:
    return int(((multi / 100) * original) + original)


def format_multiplier(multiplier):
    """Formats a multiplier for a more readable display."""
    description = f"` {multiplier[0]} ` \U00002014 {multiplier[1]}"
    if multiplier[2]:
        expiry_time = datetime.datetime.fromtimestamp(multiplier[2], tz=timezone("UTC"))
        expiry_time = discord.utils.format_dt(expiry_time, style="R")
        description += f" (expires {expiry_time})"
    return description


def selling_price_algo(base_price: int, multiplier: int) -> int:
    """Calculate the selling price of an item based on its rarity and base price."""
    return int(round(base_price * (1+multiplier/100), ndigits=-5))


def number_to_ordinal(n) -> str:
    """Convert 01 to 1st, 02 to 2nd etc."""
    if 10 <= n % 100 <= 20:
        return f"{n}th"
    
    suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
    return f"{n}{suffix}"


"""ALL VARIABLES AND CONSTANTS FOR THE ECONOMY ENVIRONMENT"""

USER_ENTRY = Union[discord.Member, discord.User]
MULTIPLIER_TYPES = Literal["xp", "luck", "robux"]
BANK_TABLE_NAME = 'bank'
SLAY_TABLE_NAME = "slay"
INV_TABLE_NAME = "inventory"
COOLDOWN_TABLE_NAME = "cooldowns"
MIN_BET_KEYCARD = 500_000
MAX_BET_KEYCARD = 15_000_000
MIN_BET_WITHOUT = 100_000
MAX_BET_WITHOUT = 10_000_000
SHOWCASE_ITEMS_REMOVED = (
    "Other items were removed from your showcase.\n"
    "You need to own at least one of every item you showcase."
)
WARN_FOR_CONCURRENCY = (
    "You cannot interact with this command because you are in an ongoing command.\n"
    "Finish any commands you are currently using before trying again.\n"
)
ITEM_DESCRPTION = 'Select an item.'
ROBUX_DESCRIPTION = 'Can be a constant number like "1234" or a shorthand (max, all, 1e6).'
GENDER_COLOURS = {"Female": 0xF3AAE0, "Male": 0x737ECF}
GENDOR_EMOJIS = {"Male": "<:male:1201993062885380097>", "Female": "<:female:1201992742574755891>"}
UNIQUE_BADGES = {
    992152414566232139: "<:e1_stafff:1145039666916110356>",
    546086191414509599: "<:in_power:1153754243220647997>",
    1134123734421217412: "<:e1_bughunterGold:1145053225414832199>",
    1154092136115994687: "<:e1_bughunterGreen:1145052762351095998>",
    1047572530422108311: "<:cc:1146092310464049203>",
    1148206353647669298: "<:e1_stafff:1145039666916110356>",
    10: " (MAX)"}
RARITY_COLOUR = {
    "Godly": 0xE2104B,
    "Legendary": 0xDA4B3D,
    "Epic": 0xDE63FF,
    "Rare": 0x5250A6,
    "Uncommon": 0x9EFF8E,
    "Common": 0x367B70
}
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
PREMIUM_CURRENCY = '<:robuxpremium:1174417815327998012>'
DOWNM = membed("This is a work in progress!")
NOT_REGISTERED = membed("This user is not registered, so you can't use this command on them.")
SLOTS = ('🔥', '😳', '🌟', '💔', '🖕', '🤡', '🍕', '🍆', '🍑')
BONUS_MULTIPLIERS = {
    "🍕🍕": 55,
    "🤡🤡": 56.5,
    "💔💔": 66.6,
    "🍑🍑": 66.69,
    "🖕🖕": 196.6699,
    "🍆🍆": 129.979,
    "😳😳": 329.999,
    "🌟🌟": 300.53,
    "🔥🔥": 350.5,
    "💔💔💔": 451.11,
    "🖕🖕🖕": 533.761,
    "🤡🤡🤡": 622.227,
    "🍕🍕🍕": 654.555,
    "🍆🍆🍆": 655.521,
    "🍑🍑🍑": 766.667,
    "😳😳😳": 669,
    "🌟🌟🌟": 600,
    "🔥🔥🔥": 850
}

JOB_KEYWORDS = {
    "Plumber": (
        (
            "TOILET", "SINK", "SEWAGE", "SANITATION", "DRAINAGE", "PIPES", "FAUCET", 
            "LEAKAGE", "FIXTURES", "CLOG", "VALVE", "CORROSION", "WRENCH", "SEPTIC", 
            "FIXTURE", "TAP", "BLOCKAGE", "OVERFLOW", "PRESSURE", "REPAIRS","BACKFLOW"
        ), 14_000_000
    ),

    "Cashier": (
        (
            "ROBUX", "TILL", "ITEMS", "WORKER", 
            "REGISTER", "CHECKOUT", "TRANSACTIONS", 
            "RECEIPTS", "SCANNER", "PRICING", "BARCODES", 
            "CURRENCY", "CHANGE", "CHECKOUT", "BAGGIN", 
            "DISCOUNTS", "REFUNDS", "EXCHANGE", "GIFTCARDS"
        ), 15_000_000
    ),

    "Fisher": (
        (
            "FISHING", "NETS", "TRAWLING", "FISHERMAN", "CATCH", 
            "VESSEL", "AQUATIC", "HARVESTING", "MARINE"
        ), 18_000_000
    ),

    "Janitor": (
        (
            "CLEANING", "SWEEPING", "MOPING", "CUSTODIAL", 
            "MAINTENANCE", "SANITATION", "BROOM", "VACUUMING", "RECYCLING",
            "DUSTING", "RESTROOM", "LITTER", "POLISHING"
        ), 16_000_000
    ),

    "Youtuber": (
        (
            "CONTENT CREATION", "VIDEO PRODUCTION", "CHANNEL", "SUBSCRIBERS", 
            "EDITING", "UPLOAD", "VLOGGING", "MONETIZATION", "THUMBNAIL", 
            "ENGAGEMENT", "COMMENTS", "EQUIPMENT", "LIGHTING", "MICROPHONE", 
            "CAMERA", "COPYRIGHT", "COMMUNITY", "FANBASE", "DEMOGRAPHIC", 
            "INFLUENCER", "SPONSORSHIP", "ALGORITHM", "COLLABORATE"
        ), 20_000_000
    ),

    "Police": (
        (
            "LAW ENFORCEMENT", "PATROL", "CRIME PREVENTION", 
            "INVESTIGATION", "ARREST", "UNIFORM", "BADGE", 
            "INTERROGATION", "FORENSICS", "SUSPECT", "PURSUIT", 
            "INCIDENT", "EMERGENCY", "SUSPECT", "EVIDENCE", 
            "RADIO", "DISPATCHER", "WITNESS"
        ), 10_000_000
    )
}

PRESTIGE_EMOTES = {
    1: "<:irn:1195469430054985749>",
    2: "<:iirn:1195469426783432714>",
    3: "<:iiirn:1195469423969054901>",
    4: "<:ivrn:1195469421628633119>",
    5: "<:vrn:1195469418235445328>",
    6: "<:virn:1195469416712900658>",
    7: "<:viirn:1195469413995003944>",
    8: "<:viiirn:1195469412438904973>",
    9: "<:ixrn:1195469410916388874>",
    10: "<:xrn:1195469408806637578>",
    11: "<:Xrne:1164937391514062848>"
}

item_handlers = {}


def register_item(item):
    def decorator(func):
        item_handlers[item] = func
        return func
    return decorator


def calculate_hand(hand: list) -> int:
    """Calculate the value of a hand in a blackjack game, accounting for possible aces."""

    aces = hand.count(11)
    total = sum(hand)

    while total > 21 and aces:
        total -= 10
        aces -= 1

    return total


def make_plural(word, count) -> str:
    """Generate the plural form of a word based on the given count."""
    mp = Pluralizer()
    return mp.pluralize(word=word, count=count)


def plural_for_own(count: int) -> str:
    """Only use this pluralizer if the term is 'own'. Nothing else."""
    if count == 1:
        return "owns"
    return "own"


def generateID() -> str:
    """
    Generate a random string of alphanumeric characters.

    Returns:
    str: A randomly generated string consisting of letters (both cases) and digits.

    Description:
    This function generates a random string by combining uppercase letters, lowercase letters,
    and digits. The length of the generated string is determined randomly within the range
    of 10 to 11 characters. This can be used, for example, for generating random passwords
    or unique identifiers.

    Example:
    >>> generateID()
    'kR3Gx9pYsZ'
    >>> generateID()
    '2hL7NQv6IzE'
    """

    all_char = ascii_letters + digits
    id_u = "".join(choice(all_char) for _ in range(randint(10, 11)))
    return id_u


def format_number_short(number: int) -> str:
    """
    Format a numerical value in a concise, abbreviated form.

    Parameters:
    - number (float): The numerical value to be formatted.

    Returns:
    str: The formatted string representing the number in a short, human-readable form.

    Description:
    This function formats a numerical value in a concise and abbreviated manner,
    suitable for displaying large or small numbers in a more readable format.
    The function uses 'K' for thousands, 'M' for millions, 'B' for billions, and 'T' for trillions.

    Example:
    >>> format_number_short(500)
    '500'
    >>> format_number_short(1500)
    '1.5K'
    >>> format_number_short(1200000)
    '1.2M'
    >>> format_number_short(2500000000)
    '2.5B'
    >>> format_number_short(9000000000000)
    '9.0T'
    """

    if number < 1e3:
        return str(number)
    elif number < 1e6:
        return '{:.1f}K'.format(number / 1e3)
    elif number < 1e9:
        return '{:.1f}M'.format(number / 1e6)
    elif number < 1e12:
        return '{:.1f}B'.format(number / 1e9)
    else:
        return '{:.1f}T'.format(number / 1e12)


def reverse_format_number_short(formatted_number: str) -> int:
    """
    Reverse the process of formatting a numerical value in a concise, abbreviated form.

    Parameters:
    - formatted_number (str): The formatted string representing the number in a short, human-readable form.

    Returns:
    int: The numerical value represented by the formatted string.

    Description:
    This function reverses the process of formatting a numerical value in a concise and abbreviated manner.
    It takes a formatted string, such as '1.2M' or '2.5B', and converts it back to the corresponding numerical value.
    The function supports values formatted with 'K' for thousands, 'M' for millions, 'B' for billions, and 'T' for trillions.

    Example:
    >>> reverse_format_number_short('500')
    500
    >>> reverse_format_number_short('1.5K')
    1500
    >>> reverse_format_number_short('1.2M')
    1200000
    >>> reverse_format_number_short('2.5B')
    2500000000
    >>> reverse_format_number_short('9.0T')
    9000000000000
    """

    suffixes = {'K': 1e3, 'M': 1e6, 'B': 1e9, 'T': 1e12}

    for suffix, value in suffixes.items():
        if formatted_number.endswith(suffix):
            number_part = formatted_number[:-1]
            return int(float(number_part) * value)

    return int(formatted_number)


def generate_slot_combination() -> str:
    """A slot machine that generates and returns one row of slots."""

    weights = [
        (800, 1000, 800, 100, 900, 800, 1000, 800, 800),
        (800, 1000, 800, 100, 900, 800, 1000, 800, 800),
        (800, 1000, 800, 100, 900, 800, 1000, 800, 800)
    ]

    slot_combination = ''.join(choices(SLOTS, weights=w, k=1)[0] for w in weights)
    return slot_combination


def find_slot_matches(*args) -> Union[None, int]:
    """
    Find any suitable matches in a slot outcome.

    The function takes in multiple arguments, each being the individual emoji.
    
    If there is a match, return the outcome's associated multiplier.
    
    Return `None` if no match found.

    This only checks the first two elements, but you must provide all three.
    """

    for emoji in args[:-1]:
        occurences = args.count(emoji)
        if occurences > 1:
            return BONUS_MULTIPLIERS[emoji*occurences]
    return None


def generate_progress_bar(percentage: Union[float, int]) -> str:
    """
    Generate a visual representation of a progress bar based on the given percentage.

    Parameters:
    percentage (float): The completion percentage of a task.

    Returns:
    str: A string representing a progress bar with visual indicators.

    Description:
    This function generates a visual representation of a progress bar using custom emojis
    for different completion levels. The progress bar is determined based on the provided
    percentage value, rounding it to the nearest multiple of 10. The function returns a string
    with visual indicators corresponding to the completion level.
    """

    percentage = round(percentage, -1)
    percentage = min(percentage, 100)
    
    progress_bar = {
        0: "<:pb1e:1199056980195676201><:pb2e:1199056978908037180>"
           "<:pb2e:1199056978908037180><:pb2e:1199056978908037180><:pb3e:1199056983966367785>",
        10: "<:pb1hf:1199058030768181368><:pb2e:1199056978908037180>"
            "<:pb2e:1199056978908037180><:pb2e:1199056978908037180><:pb3e:1199056983966367785>",
        20: "<:pb1f:1199056982670315621><:pb2e:1199056978908037180>"
            "<:pb2e:1199056978908037180><:pb2e:1199056978908037180><:pb3e:1199056983966367785>",
        30: "<:pb1f:1199056982670315621><:pb2hf:1199056986571022428>"
            "<:pb2e:1199056978908037180><:pb2e:1199056978908037180><:pb3e:1199056983966367785>",
        40: "<:pb1f:1199056982670315621><:pb2f:1199062626408337549>"
            "<:pb2e:1199056978908037180><:pb2e:1199056978908037180><:pb3e:1199056983966367785>",
        50: "<:pb1f:1199056982670315621><:pb2f:1199062626408337549>"
            "<:pb2hf:1199056986571022428><:pb2e:1199056978908037180><:pb3e:1199056983966367785>",
        60: "<:pb1f:1199056982670315621><:pb2f:1199062626408337549>"
            "<:pb2f:1199062626408337549><:pb2e:1199056978908037180><:pb3e:1199056983966367785>",
        70: "<:pb1f:1199056982670315621><:pb2f:1199062626408337549>"
            "<:pb2f:1199062626408337549><:pb2hf:1199056986571022428><:pb3e:1199056983966367785>",
        80: "<:pb1f:1199056982670315621><:pb2f:1199062626408337549>"
            "<:pb2f:1199062626408337549><:pb2f:1199062626408337549><:pb3e:1199056983966367785>",
        90: "<:pb1f:1199056982670315621><:pb2f:1199062626408337549>"
            "<:pb2f:1199062626408337549><:pb2f:1199062626408337549><:pb3hf:1199063922779623565>",
        100: "<:pb1f:1199056982670315621><:pb2f:1199062626408337549>"
             "<:pb2f:1199062626408337549><:pb2f:1199062626408337549><:pb3f:1199059438456291510>"

    }.get(percentage)

    return progress_bar


def display_user_friendly_deck_format(deck: list, /) -> str:
    """Convert a deck view into a more user-friendly view of the deck."""
    remade = list()
    suits = ["\U00002665", "\U00002666", "\U00002663", "\U00002660"]
    ranks = {10: ["K", "Q", "J"], 11: "A"}

    chosen_suit = choice(suits)
    for number in deck:
        conversion_letter = ranks.get(number)
        if conversion_letter:
            unfmt = choice(conversion_letter)
            fmt = f"[`{chosen_suit} {unfmt}`](https://www.youtube.com)"
            remade.append(fmt)
            continue
        unfmt = number
        fmt = f"[`{chosen_suit} {unfmt}`](https://www.youtube.com)"
        remade.append(fmt)
        continue
    remade = ' '.join(remade)
    return remade


def display_user_friendly_card_format(number: int, /) -> str:
    """Convert a single card into the user-friendly card version linked and ranked."""
    suits = ["\U00002665", "\U00002666", "\U00002663", "\U00002660"]
    ranks = {10: ["K", "Q", "J"], 11: "A"}

    chosen_suit = choice(suits)
    conversion_letter = ranks.get(number)
    if conversion_letter:
        unfmt = choice(conversion_letter)
        fmt = f"[`{chosen_suit} {unfmt}`](https://www.youtube.com)"
        return fmt
    unfmt = number
    fmt = f"[`{chosen_suit} {unfmt}`](https://www.youtube.com)"
    return fmt


async def add_command_usage(user_id: int, command_name: str, conn: asqlite_Connection) -> int:
    """Add command usage to db. Only include the parent name if it is a subcommand."""
    
    value = await conn.fetchone(
        """
        INSERT INTO command_uses (userID, cmd_name, cmd_count)
        VALUES ($0, $1, 1)
        ON CONFLICT(userID, cmd_name) DO UPDATE SET cmd_count = cmd_count + 1 
        RETURNING cmd_count
        """, user_id, command_name
    )

    return value[0]


async def total_commands_used_by_user(user_id: int, conn: asqlite_Connection) -> int:
    """
    Select all records for the given user_id and sum up the command_count.
    
    This will always return a value.
    """

    total = await conn.fetchone(
        """
        SELECT TOTAL(cmd_count) 
        FROM command_uses
        WHERE userID = $0
        """, user_id
    )

    return int(total[0])


async def find_fav_cmd_for(user_id, conn: asqlite_Connection) -> str:
    """Select the command with the highest command_count for the given user id."""
    
    fav = await conn.fetchone(
        """
        SELECT cmd_name FROM command_uses
        WHERE userID = $0
        ORDER BY cmd_count DESC
        LIMIT 1
        """, user_id
    )
    
    if fav is None:
        return "-"
    
    return fav[0]



class DepositOrWithdraw(discord.ui.Modal):
    def __init__(
        self, *, 
        title: str, 
        default_val: int, 
        message: discord.InteractionMessage, 
        view: discord.ui.View
    ) -> None:
        
        self.their_default = default_val
        self.message = message
        self.view = view
        self.amount.default = f"{self.their_default:,}"
        super().__init__(title=title, timeout=120.0)

    amount = discord.ui.TextInput(
        label="Amount", 
        min_length=1, 
        max_length=30, 
        placeholder="A constant number or an exponent (e.g., 1e6, 1234)"
    )

    def checks(self, bank, wallet, any_bankspace_left) -> None:
        self.view.children[0].disabled = (bank == 0)
        self.view.children[1].disabled = (wallet == 0) or (any_bankspace_left == 0)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        val = await determine_exponent(
            interaction=interaction, 
            rinput=self.amount.value
        )
        if val is None:
            return
        val = int(val)

        embed = self.message.embeds[0]
        if self.title.startswith("W"):
            if val > self.their_default:
                return await interaction.response.send_message(
                    ephemeral=True,
                    delete_after=5.0,
                    embed=membed(
                        f"You only have {CURRENCY} **{self.their_default:,}**, "
                        f"therefore cannot withdraw {CURRENCY} **{val:,}**."
                    )
                )

            async with interaction.client.pool.acquire() as conn:
                data = await conn.fetchone(
                    """
                    UPDATE bank 
                    SET 
                        bank = bank - $0, 
                        wallet = wallet + $0 
                    WHERE userID = $1 
                    RETURNING wallet, bank, bankspace
                    """, val, interaction.user.id
                )
                await conn.commit()

            prcnt_full = (data[1] / data[2]) * 100

            embed.set_field_at(0, name="Wallet", value=f"{CURRENCY} {data[0]:,}")
            embed.set_field_at(1, name="Bank", value=f"{CURRENCY} {data[1]:,}")
            embed.set_field_at(2, name="Bankspace", value=f"{CURRENCY} {data[2]:,} ({prcnt_full:.2f}% full)")
            embed.timestamp = discord.utils.utcnow()

            self.checks(data[1], data[0], data[2]-data[1])
            return await interaction.response.edit_message(embed=embed, view=self.view)
        
        # ! Deposit Branch
        
        if val > self.their_default:
            return await interaction.response.send_message(
                ephemeral=True, 
                delete_after=10.0,
                embed=membed(
                    "Either one (or both) of the following is true:\n" 
                    "1. You only have don't have that much money in your wallet.\n"
                    "2. You don't have enough bankspace to deposit that amount."
                )
            )

        async with interaction.client.pool.acquire() as conn:
            updated = await conn.fetchone(
                """
                UPDATE bank 
                SET 
                    bank = bank + $0, 
                    wallet = wallet - $0 
                WHERE userID = $1 
                RETURNING wallet, bank, bankspace
                """, val, interaction.user.id
            )
            await conn.commit()

        prcnt_full = (updated[1] / updated[2]) * 100

        embed.set_field_at(0, name="Wallet", value=f"{CURRENCY} {updated[0]:,}")
        embed.set_field_at(1, name="Bank", value=f"{CURRENCY} {updated[1]:,}")
        embed.set_field_at(2, name="Bankspace", value=f"{CURRENCY} {updated[2]:,} ({prcnt_full:.2f}% full)")
        embed.timestamp = discord.utils.utcnow()

        self.checks(updated[1], updated[0], updated[2]-updated[1])
        await interaction.response.edit_message(embed=embed, view=self.view)

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        if isinstance(error, (ValueError, TypeError)):
            return await interaction.response.send_message(
                delete_after=5.0, 
                ephemeral=True,
                embed=membed(f"You need to provide a real amount to {self.title.lower()}.")
            )
    
        print_exception(type(error), error, error.__traceback__)
        await interaction.response.send_message(embed=membed("Something went wrong. Try again later."))


class ConfirmResetData(discord.ui.View):
    def __init__(self, interaction: discord.Interaction, user_to_remove: USER_ENTRY) -> None:
        self.interaction: discord.Interaction = interaction
        self.removing_user: USER_ENTRY = user_to_remove
        self.count = 0
        super().__init__(timeout=30.0)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return await economy_check(interaction, self.interaction.user)

    async def on_timeout(self) -> Coroutine[Any, Any, None]:
        try:
            await self.interaction.delete_original_response()
        except discord.NotFound:
            pass

    @discord.ui.button(label='RESET MY DATA', style=discord.ButtonStyle.danger, emoji=discord.PartialEmoji.from_str("<a:rooFireAhh:1208545466132860990>"))
    async def confirm_button_reset(self, interaction: discord.Interaction, _: discord.ui.Button):

        self.count += 1
        if self.count < 3:
            return await interaction.response.edit_message(view=self)

        self.stop()
        await self.interaction.delete_original_response()

        async with interaction.client.pool.acquire() as conn:
            conn: asqlite_Connection

            tr = conn.transaction()
            await tr.start()

            try:
                await conn.execute("DELETE FROM bank WHERE userID = $0", self.removing_user.id)
            except Exception as e:
                print_exception(type(e), e, e.__traceback__)

                await tr.rollback()

                return await interaction.response.send_message(
                    content=interaction.user.mention,
                    embed=membed(
                        f"Failed to wipe {self.removing_user.mention}'s data.\n"
                        "Report this to the developers so they can get it fixed."
                    )
                )

            await tr.commit()

        whose = "your" if interaction.user.id == self.removing_user.id else f"{self.removing_user.mention}'s"
        end_note = " Thanks for using the bot." if whose == "your" else ""

        await interaction.response.send_message(
            content=interaction.user.mention, 
            embed=membed(f"All of {whose} data has been wiped.{end_note}")
        )

    @discord.ui.button(label='CANCEL', style=discord.ButtonStyle.primary)
    async def cancel_button_reset(self, interaction: discord.Interaction, _: discord.ui.Button):
        self.stop()
        await self.interaction.delete_original_response()

        async with interaction.client.pool.acquire() as conn:
            await Economy.end_transaction(conn, user_id=interaction.user.id)


class RememberPositionView(discord.ui.View):
    def __init__(
        self, 
        interaction: discord.Interaction,  
        all_emojis: list[str], 
        actual_emoji: str, 
        their_job: str
    ) -> None:

        self.interaction = interaction
        self.actual_emoji = actual_emoji
        self.their_job = their_job
        self.base = randint(5_500_000, 9_500_000)
        super().__init__(timeout=15.0)

        for emoji in all_emojis:
            self.add_item(RememberPosition(emoji, self.determine_outcome))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return await economy_check(interaction, self.interaction.user)
    
    async def on_timeout(self) -> Coroutine[Any, Any, None]:
        
        self.base = int((25 / 100) * self.base)
        async with self.interaction.client.pool.acquire() as conn:
            await Economy.update_bank_new(self.interaction.user, conn, self.base)

        embed = discord.Embed(title="Terrible effort!", colour=discord.Colour.brand_red())
        embed.description = f"**You were given:**\n- {CURRENCY} {self.base:,} for a sub-par shift"
        embed.set_footer(text=f"Working as a {self.their_job}")

        try:
            await self.interaction.edit_original_response(embed=embed, view=None)
        except discord.NotFound:
            pass

    async def determine_outcome(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        """Determine the position of the real emoji."""
        self.stop()
        embed = discord.Embed()

        if button.emoji.name == self.actual_emoji:
            embed.title = "Great work!"
            embed.description = f"**You were given:**\n- {CURRENCY} {self.base:,} for your shift"
            embed.colour = discord.Colour.brand_green()
        else:
            self.base = int((25 / 100) * self.base)
            embed.title = "Terrible work!"
            embed.description = f"**You were given:**\n- {CURRENCY} {self.base:,} for a sub-par shift"
            embed.colour = discord.Colour.brand_red()
        
        embed.set_footer(text=f"Working as a {self.their_job}")
        
        async with interaction.client.pool.acquire() as conn:
            await Economy.update_bank_new(interaction.user, conn, self.base)
            await conn.commit()

        await interaction.response.edit_message(embed=embed, view=None)


class RememberPosition(discord.ui.Button):
    """A minigame to remember the position the tiles shown were on once hidden."""

    def __init__(self, random_emoji: str, button_cb: Callable) -> None:
        self.button_cb = button_cb
        super().__init__(emoji=random_emoji)
    
    async def callback(self, interaction: discord.Interaction) -> None:
        await self.button_cb(interaction, button=self)


class RememberOrder(discord.ui.View):
    """A minigame to remember the position the tiles shown were on once hidden."""

    def __init__(
        self, 
        interaction: discord.Interaction, 
        list_of_five_order: list, 
        their_job: str, 
        base_reward: int
    ) -> None:

        self.interaction = interaction
        self.list_of_five_order = list_of_five_order  # the exact order of the words shown to the user
        self.their_job = their_job  # the job the user is working as
        self.base_reward = base_reward  # the base reward the user will get
        self.pos = 0  # the position we are currently at, checking the user's input

        super().__init__(timeout=20.0)
        removed = [item for item in self.children]
        self.clear_items()
        
        x = [0, 1, 2, 3, 4]
        shuffle(x)
        
        for index in x:
            removed[index].label = self.list_of_five_order[index]
            self.add_item(removed[index])

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return await economy_check(interaction, self.interaction.user)
    
    async def on_timeout(self) -> Coroutine[Any, Any, None]:

        async with self.interaction.client.pool.acquire() as conn:
            conn: asqlite_Connection
            self.base_reward = floor((25 / 100) * self.base_reward)

            await Economy.update_bank_new(self.interaction.user, conn, self.base_reward)
            await conn.commit()

        embed = discord.Embed(title="Terrible effort!", colour=discord.Colour.brand_red())
        embed.description = f"**You were given:**\n- {CURRENCY} {self.base_reward:,} for a sub-par shift"
        embed.set_footer(text=f"Working as a {self.their_job}")

        try:
            await self.interaction.edit_original_response(embed=embed, view=None)
        except discord.NotFound:
            pass

    async def disable_if_correct(self, interaction: discord.Interaction, button: discord.ui.Button):
        """If the position of a given item was correct, disable the button."""
        if button.label == self.list_of_five_order[self.pos]:
            button.disabled = True
            self.pos += 1
            if self.pos == 5:
                async with self.interaction.client.pool.acquire() as conn:
                    conn: asqlite_Connection
                    await Economy.update_bank_new(interaction.user, conn, self.base_reward)
                    await conn.commit()

                self.stop()
                embed = discord.Embed(title="Great work!", colour=discord.Colour.brand_green())
                embed.description = f"**You were given:**\n- {CURRENCY} {self.base_reward:,} for your shift"
                embed.set_footer(text=f"Working as a {self.their_job}")
                return await interaction.response.edit_message(embed=embed, view=None)
            return await interaction.response.edit_message(view=self)
        
        self.stop()
        self.pos = self.pos or 1
        self.base_reward -= int((self.pos / 4) * self.base_reward)
        
        async with self.interaction.client.pool.acquire() as conn:
            conn: asqlite_Connection
            await Economy.update_bank_new(interaction.user, conn, self.base_reward)
            await conn.commit()

        embed = discord.Embed(title="Terrible work!", colour=discord.Colour.brand_red())
        embed.description = f"**You were given:**\n- {CURRENCY} {self.base_reward:,} for a sub-par shift"
        embed.set_footer(text=f"Working as a {self.their_job}")

        await interaction.response.edit_message(embed=embed, view=None)

    @discord.ui.button()
    async def choice_one(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.disable_if_correct(interaction, button=button)
    
    @discord.ui.button()
    async def choice_two(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.disable_if_correct(interaction, button=button)

    @discord.ui.button()
    async def choice_three(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.disable_if_correct(interaction, button=button)

    @discord.ui.button()
    async def choice_four(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.disable_if_correct(interaction, button=button)

    @discord.ui.button()
    async def choice_five(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.disable_if_correct(interaction, button=button)


class BalanceView(discord.ui.View):
    """View for the balance command to mange and deposit/withdraw money."""

    def __init__(
        self, 
        interaction: discord.Interaction, 
        wallet: int, 
        bank: int, 
        bankspace: int, 
        viewing: USER_ENTRY
    ) -> None:

        self.interaction = interaction
        self.their_wallet = wallet
        self.their_bank = bank
        self.their_bankspace = bankspace
        self.viewing = viewing
        self.conn = None
        super().__init__(timeout=120.0)

        self.checks(self.their_bank, self.their_wallet, self.their_bankspace-self.their_bank)

    def checks(self, new_bank, new_wallet, any_new_bankspace_left) -> None:
        """Check if the buttons should be disabled or not."""
        if self.viewing.id != self.interaction.user.id:
            return  # ! already initialized disabled logic

        self.children[0].disabled = (new_bank == 0)
        self.children[1].disabled = (new_wallet == 0) or (any_new_bankspace_left == 0)

    async def send_failure(self, interaction: discord.Interaction) -> None:
        warning = discord.ui.View().add_item(
            discord.ui.Button(
                label="Explain This!", 
                url="https://dankmemer.lol/tutorial/interaction-locks"
            )
        )
        await interaction.response.send_message(
            view=warning, 
            ephemeral=True,
            embed=membed(
                "Either one of the following is true:\n"
                "- You aren't registered anymore.\n"
                "- You have not yet finished an ongoing command.\n"
                "For the latter, you should first finish any previous "
                "commands before using this one."
            )
        )
    
    async def release_conn(self):
        await self.interaction.client.pool.release(self.conn)
        self.conn = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        #! Check it's the author of the original interaction running this
        
        value = await economy_check(interaction, self.interaction.user)
        if not value:
            return False

        del value
        self.conn = await self.interaction.client.pool.acquire()

        #! Check if they're already in a transaction
        #! Check if they exist in the database
        #! Ensure connections are carried into item callbacks when meeting prerequisite

        try:
            await Economy.declare_transaction(self.conn, user_id=interaction.user.id)
        except sqlite3.IntegrityError:
            await self.send_failure(interaction)
            await self.release_conn()
            return False
        else:
            await Economy.end_transaction(self.conn, user_id=interaction.user.id)
            return True

    async def on_timeout(self) -> Coroutine[Any, Any, None]:
        for item in self.children:
            item.disabled = True
        try:
            await self.interaction.edit_original_response(view=self)  
        except discord.NotFound:
            pass

    @discord.ui.button(label="Withdraw", disabled=True)
    async def withdraw_money_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Withdraw money from the bank."""

        bank_amt = await Economy.get_spec_bank_data(
            interaction.user, 
            field_name="bank", 
            conn_input=self.conn
        )
        await self.release_conn()

        if not bank_amt:
            return await interaction.response.send_message(
                embed=membed("You have nothing to withdraw."), 
                ephemeral=True, 
                delete_after=3.0
            )

        await interaction.response.send_modal(
            DepositOrWithdraw(
                title=button.label, 
                default_val=bank_amt, 
                message=interaction.message, 
                view=self
            )
        )

    @discord.ui.button(label="Deposit", disabled=True)
    async def deposit_money_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Deposit money into the bank."""

        data = await self.conn.fetchone(
            """
            SELECT wallet, bank, bankspace 
            FROM `bank` 
            WHERE userID = $0
            """, interaction.user.id
        )
        await self.release_conn()

        if not data[0]:
            return await interaction.response.send_message(
                ephemeral=True, 
                delete_after=3.0,
                embed=membed("You have nothing to deposit.")
            )
        
        available_bankspace = data[2] - data[1]
        if not available_bankspace:
            return await interaction.response.send_message(
                ephemeral=True, 
                delete_after=5.0,
                embed=membed(
                    f"You can only hold {CURRENCY} **{data[2]:,}** in your bank right now.\n"
                    "To hold more, use currency commands and level up more."
                )
            )

        available_bankspace = min(data[0], available_bankspace)
        
        await interaction.response.send_modal(
            DepositOrWithdraw(
                title=button.label, 
                default_val=available_bankspace,
                message=interaction.message, 
                view=self
            )
        )
    
    @discord.ui.button(emoji="<:refreshicon:1205432056369389590>")
    async def refresh_balance(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Refresh the current message to display the user's latest balance."""

        nd = await self.conn.fetchone(
            """
            SELECT wallet, bank, bankspace 
            FROM `bank` 
            WHERE userID = $0
            """, self.viewing.id
        )

        bank = nd[0] + nd[1]
        inv = await Economy.calculate_inventory_value(self.viewing, self.conn)
        rank = await Economy.calculate_net_ranking_for(self.viewing, self.conn)
        await self.release_conn()

        space = (nd[1] / nd[2]) * 100

        balance = interaction.message.embeds[0]
        balance.timestamp = discord.utils.utcnow()
        balance.clear_fields()

        balance.add_field(name="Wallet", value=f"{CURRENCY} {nd[0]:,}")
        balance.add_field(name="Bank", value=f"{CURRENCY} {nd[1]:,}")
        balance.add_field(name="Bankspace", value=f"{CURRENCY} {nd[2]:,} ({space:.2f}% full)")
        balance.add_field(name="Money Net", value=f"{CURRENCY} {bank:,}")
        balance.add_field(name="Inventory Net", value=f"{CURRENCY} {inv:,}")
        balance.add_field(name="Total Net", value=f"{CURRENCY} {inv + bank:,}")

        balance.set_footer(text=f"Global Rank: #{rank}")

        self.checks(nd[1], nd[0], nd[2]-nd[1])
        await interaction.response.edit_message(embed=balance, view=self)

    @discord.ui.button(emoji=discord.PartialEmoji.from_str("<:terminate:1205810058357907487>"))
    async def close_view(self, interaction: discord.Interaction, _: discord.ui.Button):
        """Close the balance view."""
        await self.release_conn()
        self.stop()
        for item in self.children:
            item.disabled = True

        await interaction.response.edit_message(view=self)


class BlackjackUi(discord.ui.View):
    """View for the blackjack command and its associated functions."""

    def __init__(self, interaction: discord.Interaction):
        self.interaction = interaction
        self.bot: commands.Bot = interaction.client
        self.finished = False
        super().__init__(timeout=30)

    async def on_error(
        self, 
        interaction: discord.Interaction, 
        error: Exception, 
        _: discord.ui.Item[Any], 
        /
    ) -> None:
        print_exception(type(error), error, error.__traceback__)
        await interaction.response.send_message(embed=membed("Something went wrong."))

    async def on_timeout(self) -> None:
        if not self.finished:
            del self.bot.games[self.interaction.user.id]
            
            async with self.bot.pool.acquire() as conn:
                await Economy.end_transaction(conn, user_id=self.interaction.user.id)
                await conn.commit()

            try:
                await self.interaction.edit_original_response(
                    view=None, 
                    embed=membed("You backed off so the game ended.")
                )
            except discord.NotFound:
                pass

    async def update_winning_data(self, *, bet_amount: int) -> tuple:
        """
        Return a tuple containing elements in this order:
        
        Amount after multiplier effect, New amount balance, Percentage games won, multiplier
        """
        
        async with self.interaction.client.pool.acquire() as conn:

            their_multi = await Economy.get_multi_of(
                user_id=self.interaction.user.id, 
                multi_type="robux", 
                conn=conn
            )

            amount_after_multi = add_multi_to_original(multi=their_multi, original=bet_amount)

            await Economy.end_transaction(conn, user_id=self.interaction.user.id)
            bj_lose, new_bj_win, new_amount_balance = await conn.fetchone(
                f"""
                UPDATE `{BANK_TABLE_NAME}`
                SET 
                    wallet = wallet + $0,
                    bjw = bjw + 1,
                    bjwa = bjwa + $0
                WHERE userID = $1
                RETURNING bjl, bjw, wallet
                """, amount_after_multi, self.interaction.user.id
            )

            await conn.commit()
            prctnw = (new_bj_win / (new_bj_win + bj_lose)) * 100
        return amount_after_multi, new_amount_balance, prctnw, their_multi

    async def update_losing_data(self, *, bet_amount: int) -> tuple:
        """
        Return a tuple containing elements in this order:
        
        New amount balance, Percentage games lost
        """

        async with self.interaction.client.pool.acquire() as conn:
            await Economy.end_transaction(conn, user_id=self.interaction.user.id)
            bj_win, new_bj_lose, new_amount_balance = await conn.fetchone(
                f"""
                UPDATE `{BANK_TABLE_NAME}`
                SET
                    wallet = wallet - $0,
                    bjla = bjla + $0,
                    bjl = bjl + 1
                WHERE userID = $1
                RETURNING bjw, bjl, wallet
                """, bet_amount, self.interaction.user.id
            )

            await conn.commit()
            prnctl = (new_bj_lose / (new_bj_lose + bj_win)) * 100
        return new_amount_balance, prnctl

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return await economy_check(interaction, self.interaction.user)

    @discord.ui.button(label='Hit', style=discord.ButtonStyle.primary)
    async def hit_bj(self, interaction: discord.Interaction, _: discord.ui.Button):
        """Button in the interface to hit within blackjack."""
        namount = self.bot.games[interaction.user.id][-1]
        deck = self.bot.games[interaction.user.id][0]
        player_hand = self.bot.games[interaction.user.id][1]

        player_hand.append(deck.pop())
        self.bot.games[interaction.user.id][-2].append(display_user_friendly_card_format(player_hand[-1]))
        player_sum = calculate_hand(player_hand)

        embed = interaction.message.embeds[0]

        if player_sum > 21:

            self.stop()
            self.finished = True
            dealer_hand = self.bot.games[interaction.user.id][2]
            d_fver_p = [num for num in self.bot.games[interaction.user.id][-2]]
            d_fver_d = [num for num in self.bot.games[interaction.user.id][-3]]
            del self.bot.games[interaction.user.id]

            new_amount_balance, prnctl = await self.update_losing_data(bet_amount=namount)

            embed.colour = discord.Colour.brand_red()
            embed.description=(
                f"**You lost. You went over 21 and busted.**\n"
                f"You lost {CURRENCY} **{namount:,}**. "
                f"You now have {CURRENCY} **{new_amount_balance:,}**.\n"
                f"You lost {prnctl:.1f}% of the games."
            )

            embed.set_field_at(
                index=0,
                name=f"{interaction.user.name} (Player)",  
                value=(
                    f"**Cards** - {' '.join(d_fver_p)}\n"
                    f"**Total** - `{player_sum}`"
                )
            )
            
            embed.set_field_at(
                index=1,
                name=f"{interaction.client.user.name} (Dealer)", 
                value=(
                    f"**Cards** - {' '.join(d_fver_d)}\n"
                    f"**Total** - `{calculate_hand(dealer_hand)}`"
                )
            )

            embed.set_author(
                name=f"{interaction.user.name}'s losing blackjack game", 
                icon_url=interaction.user.display_avatar.url
            )
            embed.remove_footer()

            await interaction.response.edit_message(embed=embed, view=None)

        elif player_sum == 21:
            self.stop()
            self.finished = True

            dealer_hand = self.bot.games[interaction.user.id][2]
            d_fver_p = [num for num in self.bot.games[interaction.user.id][-2]]
            d_fver_d = [num for num in self.bot.games[interaction.user.id][-3]]

            del self.bot.games[interaction.user.id]

            (   amount_after_multi, 
                new_amount_balance, 
                prctnw, 
                new_multi 
            ) = await self.update_winning_data(bet_amount=namount)

            embed.colour = discord.Colour.brand_green()
            embed.description = (
                f"**You win! You got to 21**.\n"
                f"You won {CURRENCY} **{amount_after_multi:,}**. "
                f"You now have {CURRENCY} **{new_amount_balance:,}**.\n"
                f"You won {prctnw:.1f}% of the games."
            )

            embed.set_field_at(
                index=0,
                name=f"{interaction.user.name} (Player)", 
                value=(
                    f"**Cards** - {' '.join(d_fver_p)}\n"
                    f"**Total** - `{player_sum}`"
                )
            )

            embed.set_field_at(
                index=1,
                name=f"{interaction.client.user.name} (Dealer)", 
                value=(
                    f"**Cards** - {' '.join(d_fver_d)}\n"
                    f"**Total** - `{calculate_hand(dealer_hand)}`"
                )
            )

            embed.set_author(
                name=f"{interaction.user.name}'s winning blackjack game", 
                icon_url=interaction.user.display_avatar.url
            )
            embed.set_footer(text=f"Multiplier: {new_multi:,}%")
            await interaction.response.edit_message(embed=embed, view=None)
        else:

            d_fver_p = [number for number in self.bot.games[interaction.user.id][-2]]
            necessary_show = self.bot.games[interaction.user.id][-3][0]

            embed.description = f"**Your move. Your hand is now {player_sum}**."

            embed.set_field_at(
                index=0,
                name=f"{interaction.user.name} (Player)", 
                value=(
                    f"**Cards** - {' '.join(d_fver_p)}\n"
                    f"**Total** - `{player_sum}`"
                )
            )
            
            embed.set_field_at(
                index=1,
                name=f"{interaction.client.user.name} (Dealer)",
                value=(
                    f"**Cards** - {necessary_show} `?`\n"
                    f"**Total** - ` ? `"
                )
            )

            await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label='Stand', style=discord.ButtonStyle.primary)
    async def stand_bj(self, interaction: discord.Interaction, _: discord.ui.Button):
        """Button interface in blackjack to stand."""
        self.stop()
        self.finished = True

        deck = self.bot.games[interaction.user.id][0]
        player_hand = self.bot.games[interaction.user.id][1]
        dealer_hand = self.bot.games[interaction.user.id][2]
        namount = self.bot.games[interaction.user.id][-1]

        dealer_total = calculate_hand(dealer_hand)
        player_sum = calculate_hand(player_hand)

        while dealer_total < 17:
            popped = deck.pop()

            dealer_hand.append(popped)

            self.bot.games[interaction.user.id][-3].append(display_user_friendly_card_format(popped))

            dealer_total = calculate_hand(dealer_hand)

        d_fver_p = self.bot.games[interaction.user.id][-2]
        d_fver_d = self.bot.games[interaction.user.id][-3]

        del self.bot.games[interaction.user.id]

        embed = interaction.message.embeds[0]
        if dealer_total > 21:

            (   amount_after_multi, 
                new_amount_balance, 
                prctnw, 
                new_multi 
            ) = await self.update_winning_data(bet_amount=namount)

            embed.colour = discord.Colour.brand_green()
            embed.description = (
                f"**You win! The dealer went over 21 and busted.**\n"
                f"You won {CURRENCY} **{amount_after_multi:,}**. "
                f"You now have {CURRENCY} **{new_amount_balance:,}**.\n"
                f"You won {prctnw:.1f}% of the games."
            )

            embed.set_field_at(
                index=0,
                name=f"{interaction.user.name} (Player)", 
                value=(
                    f"**Cards** - {' '.join(d_fver_p)}\n"
                    f"**Total** - `{player_sum}`"
                )
            )

            embed.set_field_at(
                index=1,
                name=f"{interaction.client.user.name} (Dealer)", 
                value=(
                    f"**Cards** - {' '.join(d_fver_d)}\n"
                    f"**Total** - `{dealer_total}`"
                )
            )

            embed.set_author(
                icon_url=interaction.user.display_avatar.url, 
                name=f"{interaction.user.name}'s winning blackjack game"
            )
            embed.set_footer(text=f"Multiplier: {new_multi:,}%")

            await interaction.response.edit_message(embed=embed, view=None)

        elif dealer_total > player_sum:
            new_amount_balance, prnctl = await self.update_losing_data(bet_amount=namount)

            embed.colour = discord.Colour.brand_red()
            embed.description = (
                f"**You lost. You stood with a lower score (`{player_sum}`) than the dealer (`{dealer_total}`).**\n"
                f"You lost {CURRENCY} **{namount:,}**. You now have {CURRENCY} **{new_amount_balance:,}**.\n"
                f"You lost {prnctl:.1f}% of the games."
            )
            
            embed.set_field_at(
                index=0,
                name=f"{interaction.user.name} (Player)", 
                value=(
                    f"**Cards** - {' '.join(d_fver_p)}\n"
                    f"**Total** - `{player_sum}`"
                )
            )

            embed.set_field_at(
                index=1,
                name=f"{interaction.client.user.name} (Dealer)", 
                value=(
                    f"**Cards** - {' '.join(d_fver_d)}\n"
                    f"**Total** - `{dealer_total}`"
                )
            )

            embed.set_author(
                icon_url=interaction.user.display_avatar.url,
                name=f"{interaction.user.name}'s losing blackjack game"
            )
            embed.remove_footer()
            
            await interaction.response.edit_message(embed=embed, view=None)

        elif dealer_total < player_sum:
            
            (   amount_after_multi, 
                new_amount_balance, 
                prctnw, 
                new_multi 
            ) = await self.update_winning_data(bet_amount=namount)

            embed.colour = discord.Colour.brand_green()
            embed.description = (
                f"**You win! You stood with a higher score (`{player_sum}`) than the dealer (`{dealer_total}`).**\n"
                f"You won {CURRENCY} **{amount_after_multi:,}**. You now have {CURRENCY} **{new_amount_balance:,}**.\n"
                f"You won {prctnw:.1f}% of the games."
            )

            embed.set_field_at(
                index=0,
                name=f"{interaction.user.name} (Player)", 
                value=(
                    f"**Cards** - {' '.join(d_fver_p)}\n"
                    f"**Total** - `{player_sum}`"
                )
            )

            embed.set_field_at(
                index=1,
                name=f"{interaction.client.user.name} (Dealer)", 
                value=(
                    f"**Cards** - {' '.join(d_fver_d)}\n"
                    f"**Total** - `{dealer_total}`"
                )
            )

            embed.set_author(
                icon_url=interaction.user.display_avatar.url,
                name=f"{interaction.user.name}'s winning blackjack game"
            )

            embed.set_footer(text=f"Multiplier: {new_multi:,}%")

            await interaction.response.edit_message(embed=embed, view=None)
        else:
            async with self.bot.pool.acquire() as conn:
                conn: asqlite_Connection

                await Economy.end_transaction(conn, user_id=interaction.user.id)
                await conn.commit()

                wallet_amt = await Economy.get_wallet_data_only(interaction.user, conn)

            embed.colour = discord.Colour.yellow()
            embed.description = (
                f"**Tie! You tied with the dealer.**\n"
                f"Your wallet hasn't changed! You have {CURRENCY} **{wallet_amt:,}** still."
            )

            embed.set_field_at(
                index=0,
                name=f"{interaction.user.name} (Player)", 
                value=(
                    f"**Cards** - {' '.join(d_fver_p)}\n"
                    f"**Total** - `{player_sum}`"
                )
            )

            embed.set_field_at(
                index=1,
                name=f"{interaction.client.user.name} (Dealer)", 
                value=(
                    f"**Cards** - {' '.join(d_fver_d)}\n"
                    f"**Total** - `{dealer_total}`"
                )
            )

            embed.remove_footer()

            await interaction.response.edit_message(embed=embed, view=None)

    @discord.ui.button(label='Forfeit', style=discord.ButtonStyle.primary)
    async def forfeit_bj(self, interaction: discord.Interaction, _: discord.ui.Button):
        """Button for the blackjack interface to forfeit the current match."""

        self.stop()
        self.finished = True

        namount = self.bot.games[interaction.user.id][-1]
        namount //= 2

        dealer_total = calculate_hand(self.bot.games[interaction.user.id][2])
        player_sum = calculate_hand(self.bot.games[interaction.user.id][1])
        d_fver_p = self.bot.games[interaction.user.id][-2]
        d_fver_d = self.bot.games[interaction.user.id][-3]

        del self.bot.games[interaction.user.id]
        embed = interaction.message.embeds[0]

        new_amount_balance, prcntl = await self.update_losing_data(bet_amount=namount)

        embed.colour = discord.Colour.brand_red()
        embed.description = (
            f"**You forfeit. The dealer took half of your bet for surrendering.**\n"
            f"You lost {CURRENCY} **{namount:,}**. You now have {CURRENCY} **{new_amount_balance:,}**.\n"
            f"You lost {prcntl:.1f}% of the games."
        )

        embed.set_field_at(
            index=0,
            name=f"{interaction.user.name} (Player)", 
            value=(
                f"**Cards** - {' '.join(d_fver_p)}\n"
                f"**Total** - `{player_sum}`"
            )
        )

        embed.set_field_at(
            index=1,
            name=f"{interaction.client.user.name} (Dealer)", 
            value=(
                f"**Cards** - {' '.join(d_fver_d)}\n"
                f"**Total** - `{dealer_total}`"
            )
        )

        embed.set_author(
            icon_url=interaction.user.display_avatar.url, 
            name=f"{interaction.user.name}'s losing blackjack game"
        )

        embed.remove_footer()

        await interaction.response.edit_message(embed=embed, view=None)


class HighLow(discord.ui.View):
    """View for the Highlow command and its associated functions."""

    def __init__(
        self, 
        interaction: discord.Interaction, 
        hint_provided: int, 
        bet: int, 
        value: int
    ) -> None:

        self.interaction = interaction
        self.true_value = value
        self.hint_provided = hint_provided
        self.their_bet = bet
        super().__init__(timeout=30)

    async def make_clicked_blurple_only(self, clicked_button: discord.ui.Button):
        """Disable all buttons in the interaction menu except the clicked one, setting its style to blurple."""
        for item in self.children:
            item.disabled = True
            if item == clicked_button:
                item.style = discord.ButtonStyle.primary
                continue
            item.style = discord.ButtonStyle.secondary
        self.stop()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return await economy_check(interaction, self.interaction.user)

    async def on_timeout(self) -> None:
        async with self.interaction.client.pool.acquire() as conn:
            await Economy.end_transaction(conn, user_id=self.interaction.user.id)
            await conn.commit()

        for item in self.children:
            item.disabled = True

        await self.interaction.edit_original_response(
            view=None, 
            embed=membed("The game ended because you didn't answer in time.")
        )

    async def send_win(self, interaction: discord.Interaction, button: discord.ui.Button):
        async with interaction.client.pool.acquire() as conn:
            new_multi = await Economy.get_multi_of(user_id=interaction.user.id, multi_type="robux", conn=conn)
            total = add_multi_to_original(multi=new_multi, original=self.their_bet)
            new_balance = await Economy.update_bank_new(interaction.user, conn, total)
            await Economy.end_transaction(conn, user_id=self.interaction.user.id)
            await conn.commit()

        await self.make_clicked_blurple_only(button)

        win = interaction.message.embeds[0]

        win.colour = discord.Colour.brand_green()
        win.description = (
            f'**You won {CURRENCY} {total:,}!**\n'
            f'Your hint was **{self.hint_provided}**. '
            f'The hidden number was **{self.true_value}**.\n'
            f'Your new balance is {CURRENCY} **{new_balance[0]:,}**.'
        )

        win.set_author(
            name=f"{interaction.user.name}'s winning high-low game", 
            icon_url=interaction.user.display_avatar.url
        )

        win.set_footer(text=f"Multiplier: {new_multi:,}%")

        await interaction.response.edit_message(embed=win, view=self)

    async def send_loss(self, interaction: discord.Interaction, button: discord.ui.Button):
        async with interaction.client.pool.acquire() as conn:
            new_amount = await Economy.update_bank_new(interaction.user, conn, -self.their_bet)
            await Economy.end_transaction(conn, user_id=self.interaction.user.id)
            await conn.commit()

        await self.make_clicked_blurple_only(button)

        lose = interaction.message.embeds[0]

        lose.colour = discord.Colour.brand_red()
        lose.description = (
            f'**You lost {CURRENCY} {self.their_bet:,}!**\n'
            f'Your hint was **{self.hint_provided}**. '
            f'The hidden number was **{self.true_value}**.\n'
            f'Your new balance is {CURRENCY} **{new_amount[0]:,}**.'
        )
        lose.remove_footer()
        
        lose.set_author(
            name=f"{interaction.user.name}'s losing high-low game", 
            icon_url=interaction.user.display_avatar.url
        )
        await interaction.response.edit_message(embed=lose, view=self)

    @discord.ui.button(label='Lower', style=discord.ButtonStyle.primary)
    async def low(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Button for highlow interface to allow users to guess lower."""

        if self.true_value < self.hint_provided:
            return await self.send_win(interaction, button)
        await self.send_loss(interaction, button)

    @discord.ui.button(label='JACKPOT!', style=discord.ButtonStyle.primary)
    async def jackpot(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Button for highlow interface to guess jackpot, meaning the guessed number is the actual number."""

        if self.hint_provided == self.true_value:
            await self.send_win(interaction, button)
            return await interaction.message.add_reaction("\U0001f389")
        await self.send_loss(interaction, button)

    @discord.ui.button(label='Higher', style=discord.ButtonStyle.primary)
    async def high(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Button for highlow interface to allow users to guess higher."""
        
        if self.true_value > self.hint_provided:
            return await self.send_win(interaction, button)
        await self.send_loss(interaction, button)


class DropdownLB(discord.ui.Select):
    def __init__(self, bot: commands.Bot, their_choice: str):
        self.economy = bot.get_cog("Economy")

        options = [
            SelectOption(label='Money Net', description='Sort by the sum of bank and wallet.'),
            SelectOption(label='Wallet', description='Sort by the wallet amount only.'),
            SelectOption(label='Bank', description='Sort by the bank amount only.'),
            SelectOption(label='Inventory Net', description='Sort by the net value of your inventory.'),
            SelectOption(label='Bounty', description="Sort by the sum paid for capturing a player."),
            SelectOption(label='Commands', description="Sort by total commands ran."),
            SelectOption(label='Level', description="Sort by player level."),
            SelectOption(label='Net Worth', description="Sort by the sum of bank, wallet, and inventory value.")
        ]

        super().__init__(options=options)

        for option in self.options:
            option.default = option.value == their_choice

    async def callback(self, interaction: discord.Interaction):

        chosen_choice = self.values[0]

        for option in self.options:
            option.default = option.value == chosen_choice

        lb = await self.economy.create_leaderboard_preset(chosen_choice=chosen_choice)

        await interaction.response.edit_message(embed=lb, view=self.view)


class Leaderboard(discord.ui.View):
    def __init__(self, interaction: discord.Interaction, their_choice: str):
        self.interaction = interaction
        super().__init__(timeout=45.0)
        self.add_item(DropdownLB(interaction.client, their_choice))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return await economy_check(interaction, self.interaction.user)

    async def on_timeout(self) -> None:
        for item in self.children:
            item.disabled = True
        try:
            await self.interaction.edit_original_response(view=self)
        except discord.NotFound:
            pass


class ItemQuantityModal(discord.ui.Modal):
    def __init__(
        self, 
        item_name: str, 
        item_cost: int, 
        item_emoji: str
    ) -> None:

        self.item_cost = item_cost
        self.item_name = item_name
        self.ie = item_emoji
        self.activated_coupon = False

        super().__init__(timeout=60.0, title=f"Purchase {item_name}")
    
    quantity = discord.ui.TextInput(
        label="Quantity",
        placeholder="A positive integer.",
        default="1",
        min_length=1,
        max_length=5
    )

    async def begin_purchase(
        self, 
        interaction: discord.Interaction, 
        true_qty: int, 
        conn: asqlite_Connection, 
        current_balance, 
        new_price
    ) -> None:
        
        await Economy.update_inv_new(interaction.user, true_qty, self.item_name, conn)
        new_am = await Economy.change_bank_new(interaction.user, conn, current_balance-new_price)
        await conn.commit()

        success = discord.Embed(
            title="Successful Purchase",
            colour=0xFFFFFF,
            description=(
                f"> You have {CURRENCY} {new_am[0]:,} left.\n\n"
                "**You bought:**\n"
                f"- {true_qty:,}x {self.ie} {self.item_name}\n\n"
                "**You paid:**\n"
                f"- {CURRENCY} {new_price:,}")
        )
        success.set_footer(text="Thanks for your business.")

        if self.activated_coupon:
            await Economy.update_inv_new(interaction.user, -1, "Shop Coupon", conn)
            success.description += "\n\n**Additional info:**\n- <:coupon:1210894601829879818> 5% Coupon Discount was applied"
        await respond(interaction, embed=success)

    async def calculate_discounted_price_if_any(
        self, user: USER_ENTRY, 
        conn: asqlite_Connection, 
        interaction: discord.Interaction, 
        current_price: int
    ) -> int:
        """Check if the user is eligible for a discount on the item."""

        data = await conn.fetchone(
            """
            SELECT inventory.qty, settings.value
            FROM shop
            LEFT JOIN inventory 
                ON shop.itemID = inventory.itemID
            LEFT JOIN settings 
                ON inventory.userID = settings.userID AND settings.setting = 'always_use_coupon'
            WHERE shop.itemID = $0 AND inventory.userID = $1
            """, 12, user.id
        )

        if not data:
            return current_price

        discounted_price = floor((95/100) * current_price)

        if data[-1]:
            self.activated_coupon = True
            return discounted_price

        await Economy.declare_transaction(conn, user_id=interaction.user.id)

        value = await process_confirmation(
            interaction=interaction, 
            prompt=(
                "Would you like to use your <:coupon:1210894601829879818> "
                "**Shop Coupon** for an additional **5**% off?\n"
                f"(You have **{data[0]:,}** coupons in total)\n\n"
                f"This will bring your total for this purchase to {CURRENCY} "
                f"**{discounted_price:,}** if you decide to use the coupon."
            )
        )

        await Economy.end_transaction(conn, user_id=interaction.user.id)
        await conn.commit()

        if value is None:
            return value
        
        if value:
            self.activated_coupon = True
            return discounted_price
        return current_price
    
    # --------------------------------------------------------------------------------------------
    
    async def confirm_purchase(
            self, 
            interaction: discord.Interaction, 
            new_price: int, 
            true_qty: int, 
            conn: asqlite_Connection, 
            current_balance: int
        ) -> None:

        await Economy.declare_transaction(conn, user_id=interaction.user.id)
        value = await process_confirmation(
            interaction=interaction, 
            prompt=(
                f"Are you sure you want to buy **{true_qty:,}x {self.ie} "
                f"{self.item_name}** for **{CURRENCY} {new_price:,}**?"
            )
        )
        await Economy.end_transaction(conn, user_id=interaction.user.id)
        await conn.commit()

        if value:
            await self.begin_purchase(interaction, true_qty, conn, current_balance, new_price)
    
    # --------------------------------------------------------------------------------------------

    async def on_submit(self, interaction: discord.Interaction):
        true_quantity = await determine_exponent(
            interaction=interaction, 
            rinput=self.quantity.value
        )

        if true_quantity is None:
            return
    
        async with interaction.client.pool.acquire() as conn:
            conn: asqlite_Connection

            current_price = self.item_cost * true_quantity
            current_balance = await Economy.get_wallet_data_only(interaction.user, conn)

            new_price = await self.calculate_discounted_price_if_any(
                user=interaction.user, 
                conn=conn, 
                interaction=interaction, 
                current_price=current_price
            )
            
            if new_price is None:
                return await respond(
                    interaction=interaction,
                    embed=membed(
                        "You didn't respond in time so your purchase was cancelled."
                    )
                )

            if new_price > current_balance:
                return await respond(
                    interaction=interaction,
                    embed=membed(f"You don't have enough money to buy **{true_quantity:,}x {self.ie} {self.item_name}**.")
                )

            setting_enabled = await Economy.is_setting_enabled(conn, user_id=interaction.user.id, setting="buying_confirmations")
            if setting_enabled:
                await self.confirm_purchase(
                    interaction, 
                    new_price, 
                    true_quantity, 
                    conn, 
                    current_balance
                )
                return
            
            await self.begin_purchase(interaction, true_quantity, conn, current_balance, new_price)

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        print_exception(type(error), error, error.__traceback__)
        await respond(interaction=interaction, embed=membed("Something went wrong. Try again later."))


class ShopItem(discord.ui.Button):
    def __init__(self, item_name: str, cost: int, ie: str,**kwargs):
        self.item_name = item_name
        self.cost = cost
        self.ie = ie

        super().__init__(
            style=discord.ButtonStyle.primary, 
            emoji=self.ie, 
            label=item_name, 
            **kwargs
        )

    async def callback(self, interaction: discord.Interaction):
        
        await interaction.response.send_modal(
            ItemQuantityModal( 
                item_name=self.item_name, 
                item_cost=self.cost, 
                item_emoji=self.ie
            )
        )


class MatchView(discord.ui.View):
    def __init__(self, interaction: discord.Interaction) -> None:
        self.interaction = interaction
        self.chosen_item = 0
        super().__init__(timeout=15.0)
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return await economy_check(interaction, self.interaction.user)
    
    async def on_timeout(self) -> None:
        await self.interaction.delete_original_response()


class MatchItem(discord.ui.Button):
    """
    A menu to select an item from a list of items provided. 
    
    Should be used when the user searches for an item that matches multiple items.
    Helps users by not having to retype the item name more specifically.
    """
    
    def __init__(
        self, 
        item_id: int, 
        item_name: str, 
        ie: str, 
        **kwargs
    ) -> None:
        self.item_id = item_id

        super().__init__(
            label=item_name, 
            emoji=ie, 
            custom_id=f"{item_id}", 
            **kwargs
        )

    async def callback(self, interaction: discord.Interaction):
        self.view.chosen_item = (int(self.custom_id), self.label, self.emoji)
        self.view.stop()

        await interaction.response.edit_message(view=self.view)
        await interaction.message.delete()


class ProfileCustomizeButton(discord.ui.Button):
    def __init__(self, **kwargs) -> None:

        super().__init__(
            label="Edit Profile (in development)", 
            row=2, 
            disabled=True, 
            **kwargs
        )

    async def callback(self, _: discord.Interaction):
        pass


class SettingsDropdown(discord.ui.Select):

    def __init__(self, data: tuple, default_setting: str) -> None:
        """data is a list of tuples containing the settings and their brief descriptions."""
        options = [
            discord.SelectOption(label=" ".join(setting.split("_")).title(), description=brief, default=setting == default_setting, value=setting)
            for setting, brief in data
        ]
        self.current_setting = default_setting
        self.current_setting_state = None

        super().__init__(options=options, placeholder="Select a setting", row=0)
    
    async def callback(self, interaction: discord.Interaction):
        self.current_setting = self.values[0]
        self.view.first_pass_complete = True

        for option in self.options:
            option.default = option.value == self.current_setting

        async with interaction.client.pool.acquire() as conn:
            conn: asqlite_Connection
            em = await Economy.get_setting_embed(interaction=interaction, view=self.view, conn=conn)
            await interaction.response.edit_message(embed=em, view=self.view)


class ToggleButton(discord.ui.Button):
    def __init__(self, setting_dropdown: SettingsDropdown, **kwargs) -> None:
        self.setting_dropdown = setting_dropdown
        super().__init__(**kwargs)
    
    async def edit_tips_multi(self, conn: asqlite_Connection, user_id: int, enabled: bool) -> None:
        if self.setting_dropdown.current_setting != "tips":
            return
        
        if enabled:
            await Economy.add_multiplier(
                conn, 
                user_id=user_id,
                multi_amount=10,
                multi_type="robux",
                cause="tips",
                description="Tips Enabled",
                on_conflict="NOTHING"
            )
            return

        await Economy.remove_multiplier_from_cause(
            conn,
            user_id=user_id,
            cause="tips"
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        self.setting_dropdown.current_setting_state = int(not self.setting_dropdown.current_setting_state)

        enabled = self.setting_dropdown.current_setting_state == 1
        em = interaction.message.embeds[0]
        em.set_field_at(
            0, 
            name="Current", 
            value="<:Enabled:1231347743356616734> Enabled" if enabled else "<:Disabled:1231347741402071060> Disabled"
        )

        self.view.disable_button.disabled = not enabled
        self.view.enable_button.disabled = enabled

        await interaction.response.edit_message(embed=em, view=self.view)

        async with interaction.client.pool.acquire() as conn:
            conn: asqlite_Connection

            await conn.execute(
                """
                INSERT INTO settings (userID, setting, value) 
                VALUES ($0, $1, $2)
                ON CONFLICT (userID, setting) DO UPDATE SET value = $2
                """, 
                interaction.user.id, 
                self.setting_dropdown.current_setting, 
                self.setting_dropdown.current_setting_state
            )

            await self.edit_tips_multi(conn, interaction.user.id, enabled)
            await conn.commit()


class UserSettings(discord.ui.View):
    def __init__(
        self, 
        data: list, 
        chosen_setting: str, 
        interaction: discord.Interaction
    ) -> None:
        
        super().__init__(timeout=60.0)
        self.interaction = interaction
        
        self.setting_dropdown = SettingsDropdown(data=data, default_setting=chosen_setting)
        self.disable_button = ToggleButton(self.setting_dropdown, label="Disable", style=discord.ButtonStyle.danger, row=1)
        self.enable_button = ToggleButton(self.setting_dropdown, label="Enable", style=discord.ButtonStyle.success, row=1)
    
    async def on_timeout(self) -> None:
        for item in self.children:
            item.disabled = True
        try:
            await self.interaction.edit_original_response(view=self)
        except discord.NotFound:
            pass
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return await economy_check(interaction, self.interaction.user)


class MultiplierSelect(discord.ui.Select):

    colour_mapping = {
        "robux": (0x59DDB3, "https://i.imgur.com/raX1Am0.png"),
        "xp": (0xCDC700, "https://i.imgur.com/7hJ0oiO.png"),
        "luck": (0x65D654, "https://i.imgur.com/9xZIFOg.png")
    }

    def __init__(self, selected_option: str, viewing: discord.Member) -> None:

        defined_options = [
            SelectOption(
                label='Robux',
                emoji="<:robuxMulti:1247992187006750803>"
            ),
            SelectOption(
                label='XP',
                emoji='<:xpMulti:1247992334910623764>'
            ),
            SelectOption(
                label='Luck', 
                emoji='<:luckMulti:1247992217272844290>'
            )
        ]

        for option in defined_options:
            if option.value.lower() == selected_option.lower():
                option.default = True
                break
        
        self.viewing = viewing
        super().__init__(options=defined_options, row=0)

    @staticmethod
    def repr_multi(*, amount, multi: MULTIPLIER_TYPES):
        """
        Represent a multiplier using proper formatting.
        
        For instance, to represent a user with no XP multiplier, instead of showing 0, show 1x.
        
        The units are also converted as necessary based on the type we're looking at.
        """

        unit = "x" if multi == "xp" else "%"
        amount = amount if multi != "xp" else (1 + (amount / 100))

        return f"{amount}{unit}"

    @staticmethod
    async def format_pages(
        interaction: discord.Interaction,
        chosen_multiplier: MULTIPLIER_TYPES, 
        viewing: discord.Member
    ) -> tuple[int, list]:

        lowered = chosen_multiplier.lower()
        async with interaction.client.pool.acquire() as conn:
            conn: asqlite_Connection

            count = await conn.fetchone(
                """
                SELECT CAST(TOTAL(amount) AS INTEGER) 
                FROM multipliers
                WHERE (userID IS NULL OR userID = $0)
                AND multi_type = $1
                """, viewing.id, lowered
            )

            pages = await conn.fetchall(
                """
                SELECT amount, description, expiry_timestamp
                FROM multipliers
                WHERE (userID IS NULL OR userID = $0)
                AND multi_type = $1
                ORDER BY amount DESC
                """, viewing.id, lowered
            )

        return count, pages

    async def callback(self, interaction: discord.Interaction):

        chosen_multiplier: str = self.values[0]

        for option in self.options:
            option.default = option.value == chosen_multiplier
        
        lowered = chosen_multiplier.lower()

        self.view: RefreshSelectPaginationExtended
        viewing = self.viewing
        
        total_multi, pages = await MultiplierSelect.format_pages(
            interaction, 
            chosen_multiplier=lowered, 
            viewing=viewing
        )

        embed = discord.Embed(title=f"{viewing.display_name}'s Multipliers")
        embed.colour, thumb_url = MultiplierSelect.colour_mapping[lowered]
        embed.set_thumbnail(url=thumb_url)

        representation = MultiplierSelect.repr_multi(amount=total_multi[0], multi=lowered)
        self.view.index = 1

        async def get_page_part(page: int, force_refresh: Optional[bool] = False):

            if force_refresh:
                nonlocal pages, total_multi, representation

                total_multi, pages = await MultiplierSelect.format_pages(
                    interaction, 
                    chosen_multiplier=lowered, 
                    viewing=viewing
                )
                representation = MultiplierSelect.repr_multi(amount=total_multi[0], multi=lowered)

            length = 6
            offset = (page - 1) * length

            embed.description = f"> {chosen_multiplier}: **{representation}**\n\n"
            n = self.view.compute_total_pages(len(pages), length)

            if not total_multi[0]:
                embed.set_footer(text="Empty")
                return embed, n
            
            embed.description += "\n".join(
                format_multiplier(multiplier)
                for multiplier in pages[offset:offset + length]
            )

            embed.set_footer(text=f"Page {page} of {n}")
            return embed, n
        
        self.view.get_page = get_page_part
        await self.view.edit_page(interaction)


class Economy(commands.Cog):

    def __init__(self, bot: commands.Bot) -> None:
        self.bot: commands.Bot = bot

        self.not_registered = membed(
            "## <:noacc:1183086855181324490> You are not registered.\n"
            "You'll need to register first before you can use this command.\n"
            "### Already Registered?\n"
            "Find out what could've happened by calling "
            "[`>reasons`](https://www.google.com/)."
        )

    @staticmethod
    async def fetch_showdata(user: USER_ENTRY, conn: asqlite_Connection) -> tuple:

        showdata = await conn.fetchall(
            """
            SELECT 
                shop.itemName, 
                shop.emoji, 
                COALESCE(inventory.qty, 0), 
                showcase.itemID
            FROM showcase
            INNER JOIN shop
                ON showcase.itemID = shop.itemID
            LEFT JOIN inventory
                ON showcase.itemID = inventory.itemID AND inventory.userID = $0
            WHERE showcase.userID = $0
            ORDER BY showcase.itemPos
            """, user.id
        )

        ui_data = []
        garbage = set()

        offset = 0
        for (item_name, ie, inv_qty, itemID) in showdata:
            
            # ensures items in the showcase not in their inventory are removed
            if not inv_qty:
                garbage.add(itemID)
                offset += 1
                continue
        
            ui_data.append(f"` {inv_qty:,}x ` {ie} {item_name}")
        
        # wipe out the garbage items from the showcase, since they don't exist in the inventory
        if garbage:
            placeholders = ', '.join(f'${i}' for i in range(1, len(garbage)+1))
            await conn.execute(f"DELETE FROM showcase WHERE userID = $0 AND itemID IN ({placeholders})", user.id, *garbage)
            await conn.commit()

        embed = discord.Embed(
            title=f"{user.display_name}'s Showcase", 
            description="\n".join(ui_data) or "Nothing to see here!"
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        return embed

    async def interaction_check(self, interaction: discord.Interaction):
        async with self.bot.pool.acquire() as conn:
            conn: asqlite_Connection
            data = await conn.fetchone("SELECT userID FROM transactions WHERE userID = $0", interaction.user.id)

            if data is None:
                return True
            
            a = discord.ui.View().add_item(
                discord.ui.Button(
                    label="Explain This!", 
                    url="https://dankmemer.lol/tutorial/interaction-locks"
                )
            )
            await interaction.response.send_message(
                view=a, 
                ephemeral=True,
                embed=membed(WARN_FOR_CONCURRENCY)
            )
            return False

    @tasks.loop(hours=1)
    async def batch_update(self):
        async with self.bot.pool.acquire() as conn:
            conn: asqlite_Connection

            await conn.execute(
                f"""
                UPDATE `{SLAY_TABLE_NAME}` 
                SET love = CASE WHEN love - $0 < 0 THEN 0 ELSE love - $0 END, 
                hunger = CASE WHEN hunger - $1 < 0 THEN 0 ELSE hunger - $1 END,
                energy = CASE WHEN energy + $2 > 100 THEN 0 ELSE energy + $2 END,
                hygiene = CASE WHEN hygiene - $3 < 0 THEN 0 ELSE hygiene - $3 END
                """, 5, 10, 15, 20
            )
            await conn.commit()

    @batch_update.before_loop
    async def before_update(self) -> None:
        self.batch_update.stop()

    @staticmethod
    @tasks.loop()
    async def check_for_expiry(interaction: discord.Interaction) -> None:
        """Check for expired multipliers and remove them from the database."""

        async with interaction.client.pool.acquire() as conn:
            next_task = await conn.fetchone(
                """
                SELECT rowid, expiry_timestamp 
                FROM multipliers 
                WHERE expiry_timestamp IS NOT NULL 
                ORDER BY expiry_timestamp
                LIMIT 1
                """
            )

        if next_task is None:
            Economy.check_for_expiry.cancel()
            return

        row_id, expiry = next_task
        timestamp = datetime.datetime.fromtimestamp(expiry, tz=timezone("UTC"))
        await discord.utils.sleep_until(timestamp)

        async with interaction.client.pool.acquire() as conn:
            await conn.execute("DELETE FROM multipliers WHERE rowid = $0", row_id)
            await conn.commit()

    @staticmethod
    def start_check_for_expiry(interaction) -> None:
        check = Economy.check_for_expiry
        if check.is_running():
            check.restart(interaction)
        else:
            check.start(interaction)

    @staticmethod
    async def partial_match_for(interaction: discord.Interaction, item_input: str, conn: asqlite_Connection) -> None | tuple:
        """
        If the user types part of an item name, get that item name indicated.

        This is known as partial matching for item names.
        """
        res = await conn.fetchall(
            """
            SELECT itemID, itemName, emoji 
            FROM shop 
            WHERE LOWER(itemName) LIKE LOWER($0)
            LIMIT 5
            """, f"%{item_input}%"
        )

        if not res:
            return await interaction.response.send_message(
                ephemeral=True,
                embed=membed(
                    "This item does not exist. Are you trying"
                    " to [SUGGEST](https://ptb.discord.com/channels/829053898333225010/"
                    "1121094935802822768/1202647997641523241) an item?"
                )
            )
        
        if len(res) == 1:
            return res[0]

        match_view = MatchView(interaction)
        
        for item in res:
            match_view.add_item(MatchItem(ie=item[-1], item_id=item[0], item_name=item[1]))
        
        await respond(
            interaction=interaction,
            view=match_view,
            embed=membed(
                "There is more than one item with that name pattern.\n"
                "Select one of the following items:"
            ).set_author(name=f"Search: {item_input}", icon_url=interaction.user.display_avatar.url)
        )

        not_pressed = await match_view.wait()
        if not_pressed:
            await interaction.followup.send(embed=membed("No item selected, cancelled this request."))
            return
        return match_view.chosen_item

    @staticmethod
    def calculate_exp_for(*, level: int) -> int:
        """Calculate the experience points required for a given level."""
        return ceil((level/0.3)**1.3)

    @staticmethod
    async def calculate_inventory_value(user: USER_ENTRY, conn: asqlite_Connection) -> int:
        """A reusable funtion to calculate the net value of a user's inventory"""

        res = await conn.fetchone(
            """
            SELECT COALESCE(SUM(shop.cost * inventory.qty), 0) AS NetValue
            FROM shop
            LEFT JOIN inventory 
                ON shop.itemID = inventory.itemID AND inventory.userID = $0
            """, user.id
        )

        return res[0]

    async def create_leaderboard_preset(self, chosen_choice: str) -> discord.Embed:
        """A single reused function used to map the chosen leaderboard made by the user to the associated query."""
        async with self.bot.pool.acquire() as conn:
            conn: asqlite_Connection = conn
            
            player_badges = {2: "\U0001f948", 3: "\U0001f949"}

            lb = discord.Embed(
                title=f"Leaderboard: {chosen_choice}",
                color=0x2B2D31,
                timestamp=discord.utils.utcnow()
            )

            lb.set_footer(text="Ranked globally")

            if chosen_choice == 'Money Net':

                data = await conn.fetchall(
                    f"""
                    SELECT `userID`, SUM(`wallet` + `bank`) AS total_balance 
                    FROM `{BANK_TABLE_NAME}` 
                    GROUP BY `userID` 
                    ORDER BY total_balance DESC
                    """
                )

            elif chosen_choice == 'Wallet':

                data = await conn.fetchall(
                    f"""
                    SELECT `userID`, `wallet` AS total_wallet 
                    FROM `{BANK_TABLE_NAME}` 
                    GROUP BY `userID` 
                    ORDER BY total_wallet DESC
                    """
                )

            elif chosen_choice == 'Bank':
                data = await conn.fetchall(
                    f"""
                    SELECT `userID`, `bank` AS total_bank 
                    FROM `{BANK_TABLE_NAME}` 
                    GROUP BY `userID` 
                    ORDER BY total_bank DESC
                    """
                )

            elif chosen_choice == 'Inventory Net':

                data = await conn.fetchall(
                    """
                    SELECT inventory.userID, SUM(shop.cost * inventory.qty) AS NetValue
                    FROM inventory
                    INNER JOIN shop ON shop.itemID = inventory.itemID
                    GROUP BY inventory.userID
                    ORDER BY NetValue DESC
                    """
                )

            elif chosen_choice == 'Bounty':

                data = await conn.fetchall(
                    f"""
                    SELECT `userID`, `bounty` AS total_bounty 
                    FROM `{BANK_TABLE_NAME}` 
                    GROUP BY `userID` 
                    HAVING total_bounty > 0
                    ORDER BY total_bounty DESC
                    """
                )

            elif chosen_choice == 'Commands':

                data = await conn.fetchall(
                    """
                    SELECT userID, SUM(cmd_count) AS total_commands
                    FROM command_uses
                    GROUP BY userID
                    HAVING total_commands > 0
                    ORDER BY total_commands DESC
                    """
                )

            elif chosen_choice == 'Level':

                data = await conn.fetchall(
                    f"""
                    SELECT `userID`, `level` AS lvl 
                    FROM `{BANK_TABLE_NAME}` 
                    GROUP BY `userID` 
                    HAVING lvl > 0
                    ORDER BY lvl DESC
                    """
                )

            else:

                data = await conn.fetchall(
                    """
                    SELECT 
                        COALESCE(inventory.userID, money.userID) AS userID, 
                        (COALESCE(SUM(shop.cost * inventory.qty), 0) + COALESCE(money.total_balance, 0)) AS TotalNetWorth
                    FROM 
                        inventory
                    LEFT JOIN 
                        shop ON shop.itemID = inventory.itemID
                    RIGHT JOIN 
                        (
                            SELECT 
                                `userID`, 
                                SUM(`wallet` + `bank`) AS total_balance 
                            FROM 
                                `bank` 
                            GROUP BY 
                                `userID`
                        ) AS money ON inventory.userID = money.userID
                    GROUP BY 
                        COALESCE(inventory.userID, money.userID)
                    ORDER BY 
                        TotalNetWorth DESC
                    """
                )
            top_rankings = []

            if data:
                first_member = data[0]
                member_name = self.bot.get_user(first_member[0])

                top_rankings.append(
                    f"### \U0001f947 ` {first_member[1]:,} ` \U00002014 {member_name.name} {UNIQUE_BADGES.get(member_name.id, '')}\n"
                )

            top_rankings += [
                f"{player_badges.get(i, "\U0001f539")} ` {member[1]:,} ` \U00002014 {member_name.name} {UNIQUE_BADGES.get(member_name.id, '')}" 
                for i, member in enumerate(data[1:], start=2) if (member_name := self.bot.get_user(member[0]))
            ]

            lb.description = '\n'.join(top_rankings) or 'No data.'
            return lb

    # ------------------ BANK FUNCS ------------------ #

    @staticmethod
    async def calculate_net_ranking_for(user: USER_ENTRY, conn: asqlite_Connection) -> int:
        """Calculate the alternative net ranking of a user based on their net worth."""
        val = await conn.fetchone(
            """
            SELECT 
            (
                SELECT 
                    COUNT(*) + 1 
                FROM 
                    (
                        SELECT 
                            inventory.userID, 
                            (SUM(shop.cost * inventory.qty) + COALESCE(money.total_balance, 0)) AS TotalNetWorth
                        FROM 
                            inventory
                        LEFT JOIN 
                            shop ON shop.itemID = inventory.itemID
                        LEFT JOIN 
                            (
                                SELECT 
                                    `userID`, 
                                    SUM(`wallet` + `bank`) AS total_balance 
                                FROM 
                                    `bank` 
                                GROUP BY 
                                    `userID`
                            ) AS money ON inventory.userID = money.userID
                        GROUP BY 
                            inventory.userID
                    ) AS rankings
                WHERE 
                    TotalNetWorth > COALESCE(
                        (
                            SELECT 
                                (SUM(shop.cost * inventory.qty) + money.total_balance) AS TotalNetWorth 
                            FROM 
                                inventory 
                            INNER JOIN 
                                shop ON shop.itemID = inventory.itemID 
                            INNER JOIN 
                                (
                                    SELECT 
                                        `userID`, 
                                        SUM(`wallet` + `bank`) AS total_balance 
                                    FROM 
                                        `bank` 
                                    GROUP BY 
                                        `userID`
                                ) AS money ON inventory.userID = money.userID 
                            WHERE 
                                inventory.userID = $0
                        ), 
                        0
                    )
            ) AS Rank
        """, user.id
        )
        val = val or ("Not listed",)
        return val[0]

    @staticmethod
    async def open_bank_new(user: USER_ENTRY, conn_input: asqlite_Connection) -> None:
        """Register the user, if they don't exist. Only use in balance commands (reccommended.)"""
        ranumber = randint(10_000_000, 20_000_000)

        await conn_input.execute(
            f"""
            INSERT INTO `{BANK_TABLE_NAME}` (userID, wallet) 
            VALUES (?, ?)
            """, (user.id, ranumber)
        )

    @staticmethod
    async def can_call_out(user: USER_ENTRY, conn_input: asqlite_Connection) -> bool:
        """
        Check if the user is NOT in the database and therefore not registered (evaluates True if not in db).
        
        Example usage:
        if await self.can_call_out(interaction.user, conn):
            await interaction.response.send_message(embed=self.not_registered)

        This is what should be done all the time to check if a user IS NOT REGISTERED.
        """
        data = await conn_input.fetchone(
            f"SELECT EXISTS (SELECT 1 FROM `{BANK_TABLE_NAME}` WHERE userID = $0)", 
            user.id
        )

        return not data[0]

    @staticmethod
    async def can_call_out_either(user1: USER_ENTRY, user2: USER_ENTRY, conn_input: asqlite_Connection) -> bool:
        """
        Check if both users are in the database. (evaluates True if both users are in db.)
        Example usage:

        if not(await self.can_call_out_either(interaction.user, username, conn)):
            do something

        This is what should be done all the time to check if both users are not registereed.
        """

        data = await conn_input.fetchone(
            f"""
            SELECT COUNT(*) 
            FROM {BANK_TABLE_NAME} 
            WHERE userID IN (?, ?)
            """, (user1.id, user2.id)
        )

        return data[0] == 2

    @staticmethod
    async def get_wallet_data_only(user: USER_ENTRY, conn_input: asqlite_Connection) -> int:
        """Retrieves the wallet amount only from a registered user's bank data."""
        data = await conn_input.fetchone(f"SELECT wallet FROM `{BANK_TABLE_NAME}` WHERE userID = $0", user.id)
        return data[0]

    @staticmethod
    async def get_spec_bank_data(user: USER_ENTRY, field_name: str, conn_input: asqlite_Connection) -> Any:
        """Retrieves a specific field name only from the bank table."""
        data = await conn_input.fetchone(f"SELECT {field_name} FROM `{BANK_TABLE_NAME}` WHERE userID = $0", user.id)
        return data[0]

    @staticmethod
    async def update_bank_new(
        user: USER_ENTRY, 
        conn_input: asqlite_Connection, 
        amount: Union[float, int] = 0, 
        mode: str = "wallet"
    ) -> Optional[Any]:
        
        """
        Modifies a user's balance in a given mode: either wallet (default) or bank.
        
        It also returns the new balance in the given mode, if any (defaults to wallet).
        
        Note that conn_input is not the last parameter, it is the second parameter to be included.
        """

        data = await conn_input.fetchone(
            f"""
            UPDATE {BANK_TABLE_NAME} 
            SET {mode} = {mode} + $0 
            WHERE userID = $1 RETURNING `{mode}`
            """, amount, user.id
        )
        return data

    @staticmethod
    async def change_bank_new(
        user: USER_ENTRY, 
        conn_input: asqlite_Connection, 
        amount: Union[float, int, str] = 0, 
        mode: str = "wallet"
    ) -> Optional[Any]:
        """
        Modifies a user's field values in any given mode.

        Unlike the other updating the bank method, this function directly changes the value to the parameter ``amount``.

        It also returns the new balance in the given mode, if any (defaults to wallet).

        Note that conn_input is not the last parameter, it is the second parameter to be included.
        """

        data = await conn_input.fetchone(
            f"""
            UPDATE {BANK_TABLE_NAME} 
            SET `{mode}` = ? 
            WHERE userID = ? 
            RETURNING `{mode}`
            """, (amount, user.id)
        )

        return data

    @staticmethod
    async def update_bank_multiple_new(
        user: USER_ENTRY, 
        conn_input: asqlite_Connection, 
        mode1: str, 
        amount1: Union[float, int], 
        mode2: str, 
        amount2: Union[float, int], 
        table_name: Optional[str] = "bank"
        ) -> Optional[Any]:
        """
        Modifies any two fields at once by their respective amounts. Returning the values of both fields.
        
        You are able to choose what table you wish to modify the contents of.
        """
        
        data = await conn_input.fetchone(
            f"""
            UPDATE `{table_name}` 
            SET 
                {mode1} = {mode1} + ?, 
                {mode2} = {mode2} + ? 
            WHERE userID = ? 
            RETURNING {mode1}, {mode2}
            """, (amount1, amount2, user.id)
        )
        return data

    @staticmethod
    async def update_bank_three_new(
        user: USER_ENTRY, conn_input: asqlite_Connection, 
        mode1: str, 
        amount1: Union[float, int], 
        mode2: str, 
        amount2: Union[float, int], 
        mode3: str, 
        amount3: Union[float, int], 
        table_name: Optional[str] = "bank"
        ) -> Optional[Any]:
        """
        Modifies any three fields at once by their respective amounts. Returning the values of both fields.
        
        You are able to choose what table you wish to modify the contents of.
        """

        data = await conn_input.fetchone(
            f"""
            UPDATE `{table_name}` 
            SET 
                {mode1} = {mode1} + ?, 
                {mode2} = {mode2} + ?, 
                {mode3} = {mode3} + ? 
            WHERE userID = ? 
            RETURNING {mode1}, {mode2}, {mode3}
            """, (amount1, amount2, amount3, user.id)
        )

        return data

    @staticmethod
    async def update_wallet_many(conn_input: asqlite_Connection, *params_users) -> None:
        """
        Update the bank of two users at once. Useful to transfer money between multiple users at once.
        
        The parameters are tuples, each tuple containing the amount to be added to the wallet and the user ID.

        Example:
        await Economy.update_wallet_many(conn, (100, 546086191414509599), (200, 270904126974590976))
        """

        query = (
            """
            UPDATE bank 
            SET wallet = wallet + ? 
            WHERE userID = ?
            """
        )

        await conn_input.executemany(query, params_users)

    # ------------------ INVENTORY FUNCS ------------------ #

    @staticmethod
    async def get_one_inv_data_new(user: USER_ENTRY, item_name: str, conn_input: asqlite_Connection) -> Optional[Any]:
        """Fetch inventory data from one specific item inputted. Use this method before making any updates."""
        query = (
            """
            SELECT inventory.qty
            FROM inventory
            INNER JOIN shop ON inventory.itemID = shop.itemID
            WHERE inventory.userID = ? AND shop.itemName = ?
            """
        )
        
        inv_data = await conn_input.fetchone(query, (user.id, item_name))
        if inv_data:
            return inv_data[0]
        return 0

    @staticmethod
    async def user_has_item_from_id(user_id: int, item_id: int, conn: asqlite_Connection) -> bool:
        """Check if a user has a specific item based on its id. Return a numerical value."""
        query = (
            """
            SELECT qty
            FROM inventory
            WHERE inventory.userID = ? AND inventory.itemID = ?
            """
        )

        val = await conn.fetchone(query, (user_id, item_id))
        return val[0] if val else 0

    @staticmethod
    async def user_has_item_from_name(user_id: int, item_name: str, conn: asqlite_Connection) -> bool:
        """Check if a user has a specific item based on its name. Return a numerical value."""
        query = (
            """
            SELECT qty
            FROM inventory
            INNER JOIN shop 
                ON inventory.itemID = shop.itemID
            WHERE inventory.userID = ? AND shop.itemName = ?
            """
        )

        result = await conn.fetchone(query, (user_id, item_name))
        return result[0] if result else 0

    @staticmethod
    async def update_inv_new(
        user: USER_ENTRY, 
        amount: Union[float, int], 
        item_name: str, 
        conn: asqlite_Connection
    ) -> Optional[Any]:
        """
        Modify a user's inventory. 
        
        If the item quantity is <= 0, delete the row.
        
        This method should always be called when updating the inventory to ensure rows are deleted when necessary.
        """

        item_row = await conn.fetchone("SELECT itemID FROM shop WHERE itemName = $0", item_name)
        
        item_id = item_row[0] if item_row else None

        check_result = await conn.fetchone(
            """
            SELECT qty + ? <= 0
            FROM inventory
            WHERE userID = ? AND itemID = ?
            """, (amount, user.id, item_id)
        )
        
        if check_result and check_result[0]:
            # If the resulting quantity would be <= 0, delete the row
            await conn.execute("DELETE FROM inventory WHERE userID = ? AND itemID = ?", (user.id, item_id))
            return (0,)
        
        val = await conn.fetchone(
            """
            INSERT INTO inventory (userID, itemID, qty)
            VALUES (?, ?, ?)
            ON CONFLICT(userID, itemID) DO UPDATE SET qty = qty + ? 
            RETURNING qty
            """, (user.id, item_id, amount, amount)
        )

        return val

    @staticmethod
    async def update_inv_by_id(
        user: USER_ENTRY, 
        amount: Union[float, int], 
        item_id: int, 
        conn: asqlite_Connection
    ) -> Optional[Any]:
        """
        Modify a user's inventory by the item ID. 
        
        Shares the same logic as the `update_inv_new` method.
        """

        check_result = await conn.fetchone(
            """
            SELECT qty + $0 <= 0
            FROM inventory
            WHERE userID = $1 AND itemID = $2
            """, amount, user.id, item_id
        )
        
        if check_result and check_result[0]:
            # If the resulting quantity would be <= 0, delete the row
            await conn.execute("DELETE FROM inventory WHERE userID = $0 AND itemID = $1", user.id, item_id)
            return (0,)
        
        val = await conn.fetchone(
            """
            INSERT INTO inventory (userID, itemID, qty)
            VALUES ($0, $1, $2)
            ON CONFLICT(userID, itemID) DO UPDATE SET qty = qty + $2
            RETURNING qty
            """, user.id, item_id, amount
        )

        return val

    @staticmethod
    async def update_user_inventory_with_random_item(user_id: int, conn: asqlite_Connection, qty: int) -> tuple:
        """
        Update user's inventory with a random item by a random amount requested. 
        
        Return the item name and emoji.
        """
        random_item_query = await conn.fetchone(
            """
            SELECT itemID, itemName, emoji
            FROM shop
            ORDER BY RANDOM()
            LIMIT 1
            """
        )
        
        update_query = (
            """
            INSERT INTO inventory (userID, itemID, qty)
            VALUES ($0, $1, $2)
            ON CONFLICT(userID, itemID) DO UPDATE SET qty = qty + 1
            """
        )

        await conn.execute(update_query, user_id, random_item_query[0], qty)
        return random_item_query[1:]
    
    @staticmethod
    async def kill_the_user(user: USER_ENTRY, conn_input: asqlite_Connection) -> None:
        """Define what it means to kill a user."""

        await conn_input.execute(
            f"UPDATE `{BANK_TABLE_NAME}` SET wallet = 0, bank = 0, showcase = ?, job = ?, bounty = 0 WHERE userID = ?", 
            ("0 0 0", "None", user.id))
        
        await conn_input.execute(f"DELETE FROM `{INV_TABLE_NAME}` WHERE userID = ?", (user.id,))
        await conn_input.execute(f"INSERT INTO `{INV_TABLE_NAME}` (userID) VALUES(?)", (user.id,))        
        await conn_input.execute(f"DELETE FROM `{SLAY_TABLE_NAME}` WHERE userID = ?", (user.id,))

    # ------------ JOB FUNCS ----------------

    @staticmethod
    async def change_job_new(user: USER_ENTRY, conn_input: asqlite_Connection, job_name: str) -> None:
        """Modifies a user's job, returning the new job after changes were made."""

        await conn_input.execute(
            f"""
            UPDATE `{BANK_TABLE_NAME}` 
            SET job = $0 
            WHERE userID = $1
            """, job_name, user.id
        )

    # ------------ cooldowns ----------------

    @staticmethod
    async def check_has_cd(
        conn: asqlite_Connection, 
        user_id: int, 
        cd_type: Optional[str] = None, 
        mode="t", 
        until = "N/A"
    ) -> Union[bool, str]:
        """
        Check if a user has no cooldowns.
        
        To save queries, if you can, make the query yourself in
        advance and pass it in to the `until` kwarg.
        """
        
        if isinstance(until, str):
            until = (
                """
                SELECT until 
                FROM cooldowns 
                WHERE userID = $0 AND cooldown = $1
                """
            )
            
            until = await conn.fetchone(until, user_id, cd_type)
            if until:
                until, = until

        if not until:
            return None
        
        current_time = discord.utils.utcnow()
        time_left = datetime.datetime.fromtimestamp(until, tz=timezone('UTC'))
        time_left = (time_left - current_time).total_seconds()
        
        if time_left > 0:
            when = current_time + datetime.timedelta(seconds=time_left)
            return discord.utils.format_dt(when, style=mode), discord.utils.format_dt(when, style="R")
        return False

    @staticmethod
    async def update_cooldown(
        conn_input: asqlite_Connection, *, 
        user_id: USER_ENTRY, 
        cooldown_type: str, 
        new_cd: str
    ) -> Any:
        """Update a user's cooldown.
        
        Raises `sqlite3.IntegrityError` when foreign userID constraint fails.
        """

        await conn_input.execute(
            """
            INSERT INTO cooldowns (userID, cooldown, until)
            VALUES ($0, $1, $2)
            ON CONFLICT(userID, cooldown) DO UPDATE SET until = $2
            """, user_id, cooldown_type, new_cd
        )

    @staticmethod
    async def declare_transaction(conn: asqlite_Connection, *, user_id: int) -> bool:
        await conn.execute("INSERT INTO transactions (userID) VALUES ($0)", user_id)
    
    @staticmethod
    async def end_transaction(conn: asqlite_Connection, *, user_id: int) -> bool:
        await conn.execute("DELETE FROM transactions WHERE userID = $0", user_id)

    # -----------------------------------------

    @staticmethod
    async def add_multiplier(
        conn: asqlite_Connection, *, 
        user_id: int, 
        multi_amount: int,
        multi_type: MULTIPLIER_TYPES,
        cause: str,
        description: str,
        expiry: Optional[float] = None,
        on_conflict: Optional[str] = "UPDATE SET amount = amount + $1, description = $4"
    ) -> None:
        """
        Add a multiplier to the database.
        
        Parameters
        ------------
        conn
            The connection to the database.
        user_id
            The user's ID to add the multiplier to.
        multi_amount
            The amount of the multiplier.
        multi_type 
            The type of the multiplier. 
            Can be either 'xp', 'luck', or 'robux'.
        cause
            Why the multiplier was added. 
            Must be consistent in order to find it later.
        description
            A description of the multiplier. 
            This will show up on the user multiplier list.
        expiry
            The expiry timestamp of the multiplier.
            Can be None if the multiplier is permanent.
        on_conflict
            The action to take when a conflict occurs.
            Defaults to updating the amount and description.

        Returns
        ------------
        A boolean, either True to indicate that the multiplier was updated/inserted, or False if it was not.

        If you supplied a DO NOTHING clause to the `on_conflict` parameter, 
        this will return `False` if the `on_conflict` clause was triggered. 
        Otherwise, row insertion occurs, returning `True`. 
        This is useful for apply temporary multipliers.

        If you supplied a DO UPDATE clause (which is provided by default to the `on_conflict` parameter),
        this will always return `True` because in either case an operation took place.
        This is useful for applying permanent multipliers that can be updated incrementally.
        """

        result = await conn.fetchone(
            f"""
            INSERT INTO multipliers (userID, amount, multi_type, cause, description, expiry_timestamp)
            VALUES ($0, $1, $2, $3, $4, $5)
            ON CONFLICT(userID, cause) DO {on_conflict} 
            RETURNING rowid
            """, user_id, multi_amount, multi_type, cause, description, expiry
        )
        return result is not None

    @staticmethod
    async def remove_multiplier_from_cause(conn: asqlite_Connection, *, user_id: int, cause: str) -> None:
        """Remove a multiplier from a user based on the cause."""

        await conn.execute('DELETE FROM multipliers WHERE userID = $0 AND cause = $1', user_id, cause)
    
    @staticmethod
    async def get_multi_of(*, user_id: int, multi_type: MULTIPLIER_TYPES, conn: asqlite_Connection) -> int:
        """Get the amount of a multiplier of a specific type for a user."""

        multiplier, = await conn.fetchone(
            """
            SELECT TOTAL(amount) 
            FROM multipliers
            WHERE (userID IS NULL OR userID = $0) 
            AND multi_type = $1
            """, user_id, multi_type
        )
        return int(multiplier)
    
    @staticmethod
    async def is_setting_enabled(conn: asqlite_Connection, *, user_id: int, setting: str) -> bool:
        """Check if a user has a setting enabled."""

        result = await conn.fetchone(
            """
            SELECT value 
            FROM settings 
            WHERE userID = $0 AND setting = $1
            """, user_id, setting
        )
        if result is None:
            return False
        return bool(result[0])

    @staticmethod
    async def get_setting_embed(
        interaction: discord.Interaction, 
        view: UserSettings, 
        conn: asqlite_Connection
    ) -> discord.Embed:

        data = await conn.fetchone(
            """
            SELECT 
                COALESCE((SELECT settings.value FROM settings WHERE settings.userID = $0 AND setting = $1), 0) AS settingUser, 
                settings_descriptions.description 
            FROM settings_descriptions 
            WHERE setting = $1
            """, interaction.user.id, view.setting_dropdown.current_setting
        )

        if data is None:
            view.clear_items()
            view.stop()
            return membed("This setting does not exist.")

        value, description = data
        view.setting_dropdown.current_setting_state = value
        
        embed = membed(
            f"> {description}"
        )

        embed.title = " ".join(view.setting_dropdown.current_setting.split("_")).title()

        view.clear_items()
        view.add_item(view.setting_dropdown)

        if embed.title == "Profile Customization":
            view.add_item(ProfileCustomizeButton())
        else:
            enabled = value == 1
            current_text = "<:Enabled:1231347743356616734> Enabled" if enabled else "<:Disabled:1231347741402071060> Disabled"
            embed.add_field(name="Current", value=current_text)
            view.disable_button.disabled = not enabled
            view.enable_button.disabled = enabled
            view.add_item(view.disable_button)
            view.add_item(view.enable_button)
        return embed

    async def send_tip_if_enabled(self, interaction: discord.Interaction, conn: asqlite_Connection) -> None:
        """Send a tip if the user has enabled tips."""

        tips_enabled = await self.is_setting_enabled(
            conn, 
            user_id=interaction.user.id, 
            setting="tips"
        )

        if tips_enabled:
            async with aiofiles.open("C:\\Users\\georg\\Documents\\c2c\\tips.txt") as f:
                contents = await f.readlines()
                shuffle(contents)
                atip = choice(contents)

            tip = membed()
            tip.description = f"\U0001f4a1 `TIP`: {atip}"
            tip.set_footer(text="You can disable these tips in /settings.")
            
            await interaction.followup.send(embed=tip, ephemeral=True)

    async def add_exp_or_levelup(
        self, 
        interaction: discord.Interaction, 
        connection: asqlite_Connection, 
        exp_gainable: int
    ) -> None:

        record = await connection.fetchone(
            """
            UPDATE bank
            SET exp = exp + $0
            WHERE userID = $1 
            RETURNING exp, level
            """, exp_gainable, interaction.user.id
        )

        if record is None:
            return
        
        xp, level = record
        exp_needed = self.calculate_exp_for(level=level)
        
        if xp < exp_needed:
            return
        
        await self.add_multiplier(
            connection,
            user_id=interaction.user.id,
            multi_amount=2,
            multi_type="xp",
            cause="level",
            description=f"Level {level+1}"
        )

        await connection.execute(
            """
            UPDATE `bank` 
            SET 
                level = level + 1, 
                exp = 0, 
                bankspace = bankspace + $0 
            WHERE userID = $1
            """, randint(300_000, 20_000_000), interaction.user.id
        )
        
        notifs_enabled = await self.is_setting_enabled(
            connection, 
            user_id=interaction.user.id, 
            setting="levelup_notifications"
        )

        if notifs_enabled:
            rankup = discord.Embed(title="Level Up!", colour=0x55BEFF)
            rankup.description = (
                f"{choice(LEVEL_UP_PROMPTS)}, {interaction.user.name}!\n"
                f"You've leveled up from level **{level:,}** to level **{level+1:,}**."
            )

            await interaction.followup.send(embed=rankup)

    @commands.Cog.listener()
    async def on_app_command_completion(
        self, 
        interaction: discord.Interaction, 
        command: Union[app_commands.Command, app_commands.ContextMenu]
    ) -> None:
        
        """
        Increment the total command ran by a user by 1 for each call. 
        
        Increase the interaction user's XP/Level if they are registered. 
        
        Provide a tip if the total commands ran counter is a multiple of 15.
        """

        cmd = interaction.command.parent or interaction.command
        if isinstance(cmd, app_commands.ContextMenu):
            return

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
            ON CONFLICT(userID, cmd_name) DO UPDATE SET cmd_count = cmd_count + 1 
            RETURNING cmd_count, (SELECT total FROM multi)
            """
        )

        async with self.bot.pool.acquire() as connection:
            connection: asqlite_Connection

            async with connection.transaction():
                try:
                    data = await connection.fetchone(query, interaction.user.id, "xp", f"/{cmd.name}")
                except sqlite3.IntegrityError:
                    return

                total, multi = data

                if not total % 15:
                    await self.send_tip_if_enabled(interaction, connection)

                exp_gainable = command.extras.get("exp_gained")
                if not exp_gainable:
                    return
                
                exp_gainable *= ((multi/100)+1)
                await self.add_exp_or_levelup(interaction, connection, int(exp_gainable))

    @commands.Cog.listener()
    async def on_command(self, ctx: commands.Context) -> None:
        """Track text commands ran."""

        cmd = ctx.command.parent or ctx.command

        async with self.bot.pool.acquire() as connection:
            connection: asqlite_Connection

            await add_command_usage(
                user_id=ctx.author.id, 
                command_name=f">{cmd.name}", 
                conn=connection
            )
            await connection.commit()

    # ----------- END OF ECONOMY FUNCS, HERE ON IS JUST COMMANDS --------------

    @app_commands.guilds(*APP_GUILDS_IDS)
    @app_commands.command(name="settings", description="Adjust user-specific settings")
    @app_commands.describe(setting="The specific setting you want to adjust. Defaults to view.")
    async def view_user_settings(self, interaction: discord.Interaction, setting: Optional[str]) -> None:
        """View or adjust user-specific settings."""
        async with self.bot.pool.acquire() as conn:
            conn: asqlite_Connection
            query = "SELECT setting, brief FROM settings_descriptions"
            settings = await conn.fetchall(query)
            chosen_setting = setting or settings[0][0]

            view = UserSettings(data=settings, chosen_setting=chosen_setting, interaction=interaction)
            em = await Economy.get_setting_embed(interaction, view=view, conn=conn)
            await interaction.response.send_message(embed=em, view=view)

    @app_commands.guilds(*APP_GUILDS_IDS)
    @app_commands.command(name="multipliers", description="View all of your multipliers within the bot")
    @app_commands.describe(
        user="The user whose multipliers you want to see. Defaults to your own.",
        multiplier="The type of multiplier you want to see. Defaults to robux."
    )
    async def my_multi(
        self, 
        interaction: discord.Interaction, 
        user: Optional[USER_ENTRY], 
        multiplier: Optional[Literal["Robux", "XP", "Luck"]] = "Robux"
    ) -> None:

        user = user or interaction.user
        lowered = multiplier.lower()

        total_multi, pages = await MultiplierSelect.format_pages(
            interaction, 
            chosen_multiplier=lowered, 
            viewing=user
        )

        embed = discord.Embed(title=f"{user.display_name}'s Multipliers")
        embed.colour, thumb_url = MultiplierSelect.colour_mapping[lowered]
        embed.set_thumbnail(url=thumb_url)

        select_menu = MultiplierSelect(selected_option=lowered, viewing=user)
        paginator = RefreshSelectPaginationExtended(interaction, select=select_menu)

        async def get_page_part(page: int, force_refresh: Optional[bool] = False):

            if force_refresh:
                nonlocal pages, total_multi

                total_multi, pages = await MultiplierSelect.format_pages(
                    interaction, 
                    chosen_multiplier=lowered, 
                    viewing=user
                )

            length = 6
            offset = ((page - 1) * length)

            representation = MultiplierSelect.repr_multi(amount=total_multi[0], multi=lowered)
            embed.description = f"> {multiplier}: **{representation}**\n\n"

            n = paginator.compute_total_pages(len(pages), length)

            if not total_multi[0]:
                embed.set_footer(text="Empty")
                return embed, n

            embed.description += "\n".join(
                format_multiplier(multi)
                for multi in pages[offset:offset + length]
            )

            embed.set_footer(text=f"Page {page} of {n}")
            return embed, n
        
        paginator.get_page = get_page_part
        await paginator.navigate()

    share = app_commands.Group(
        name='share', 
        description='Share different assets with others.', 
        guild_only=True, 
        guild_ids=APP_GUILDS_IDS
    )

    @share.command(name="robux", description="Share robux with another user", extras={"exp_gained": 5})
    @app_commands.rename(recipient="user")
    @app_commands.describe(
        recipient='The user receiving the robux shared.', 
        quantity=ROBUX_DESCRIPTION
    )
    async def share_robux(
        self, 
        interaction: discord.Interaction, 
        recipient: USER_ENTRY,
        quantity: str
    ) -> None:
        """"Give an amount of robux to another user."""

        sender = interaction.user

        async with interaction.client.pool.acquire() as conn:
            conn: asqlite_Connection

            if not (await self.can_call_out_either(sender, recipient, conn)):
                return await interaction.response.send_message(ephemeral=True, embed=NOT_REGISTERED)
            else:
                quantity = await determine_exponent(
                    interaction=interaction, 
                    rinput=quantity
                )
                if quantity is None:
                    return

                wallet_amt_host = await Economy.get_wallet_data_only(sender, conn)

                if isinstance(quantity, str):
                    quantity = wallet_amt_host
                
                if quantity > wallet_amt_host:
                    return await interaction.response.send_message(
                        ephemeral=True,
                        embed=membed("You don't have that much money to share.")
                    )
                
                setting_enabled = await Economy.is_setting_enabled(conn, user_id=interaction.user.id, setting="share_robux_confirmations")
                if setting_enabled:
                    await self.declare_transaction(conn, user_id=interaction.user.id)
                    value = await process_confirmation(
                        interaction=interaction, 
                        prompt=f"Are you sure you want to share {CURRENCY} **{quantity:,}** with {recipient.mention}?"
                    )
                    await self.end_transaction(conn, user_id=interaction.user.id)
                    await conn.commit()
                    if not value:
                        return

                await self.update_wallet_many(
                    conn, 
                    (-int(quantity), sender.id), 
                    (int(quantity), recipient.id)
                )
                await conn.commit()

                return await respond(
                    interaction=interaction,
                    embed=membed(f"Shared {CURRENCY} **{quantity:,}** with {recipient.mention}!")
                )

    @share.command(name='items', description='Share items with another user', extras={"exp_gained": 5})
    @app_commands.rename(recipient='user')
    @app_commands.describe(
        item=ITEM_DESCRPTION, 
        quantity='The amount of this item to share.', 
        recipient='The user receiving the item.'
    )
    async def share_items(
        self, 
        interaction: discord.Interaction, 
        recipient: USER_ENTRY,
        quantity: int, 
        item: str
    ) -> None:
        """Give an amount of items to another user."""

        sender = interaction.user
        async with self.bot.pool.acquire() as conn:
            conn: asqlite_Connection
            
            if not (await self.can_call_out_either(sender, recipient, conn)):
                return await interaction.response.send_message(ephemeral=True, embed=NOT_REGISTERED)

            item = await Economy.partial_match_for(interaction, item, conn)
            if item is None:
                return
            item_id, item_name, ie = item

            attrs = await conn.fetchone(
                """
                SELECT inventory.qty, shop.rarity, settings.value
                FROM inventory
                INNER JOIN shop ON inventory.itemID = shop.itemID
                LEFT JOIN settings ON inventory.userID = settings.userID AND settings.setting = 'share_item_confirmations'
                WHERE inventory.userID = $0 AND inventory.itemID = $1
                """, sender.id, item_id
            )

            if attrs is None:
                return await respond(
                    interaction, 
                    ephemeral=True,
                    embed=membed(f"You don't own a single {ie} **{item_name}**.")
                )
            
            else:
                if attrs[0] < quantity:
                    return await respond(
                        interaction, 
                        ephemeral=True,
                        embed=membed(f"You don't have **{quantity}x {ie} {item_name}**.")
                    )
                
                if attrs[-1]:
                    await Economy.declare_transaction(conn, user_id=interaction.user.id)
                    value = await process_confirmation(
                        interaction=interaction, 
                        prompt=f"Are you sure you want to share **{quantity}x {ie} {item_name}** with {recipient.mention}?"
                    )
                    await Economy.end_transaction(conn, user_id=interaction.user.id)
                    await conn.commit()

                    if not value:
                        return

                await self.update_inv_by_id(sender, -quantity, item_id, conn)
                
                await conn.execute(
                    """
                    INSERT INTO inventory (userID, itemID, qty) 
                    VALUES ($0, $1, $2) 
                    ON CONFLICT(userID, itemID) DO 
                        UPDATE SET qty = qty + $2
                    """, recipient.id, item_id, quantity
                )

                await conn.commit()

                await respond(
                    interaction,
                    embed=discord.Embed(
                        colour=RARITY_COLOUR.get(attrs[-1], 0x2B2D31),
                        description=f"Shared **{quantity}x {ie} {item_name}** with {recipient.mention}!"
                    )
                )

    trade = app_commands.Group(
        name='trade', 
        description='Exchange different assets with others.', 
        guild_only=True, 
        guild_ids=APP_GUILDS_IDS
    )
    
    async def coin_checks_passing(
        self,
        interaction: discord.Interaction,
        user_checked: discord.Member,
        coin_qty_offered: int,
        actual_wallet_amt
    ) -> Union[bool, None]:
        if actual_wallet_amt is None:
            await respond(interaction, embed=membed(f"{user_checked.mention} is not registered."))
        elif actual_wallet_amt[0] < coin_qty_offered:
            await respond(
                interaction, 
                embed=membed(
                    f"{user_checked.mention} only has {CURRENCY} **{actual_wallet_amt[0]:,}**.\n"
                    f"Not the requested {CURRENCY} **{coin_qty_offered:,}**."
                )
            )
        else:
            return True
    
    async def item_checks_passing(
        self,
        interaction: discord.Interaction,
        conn: asqlite_Connection,
        user_to_check: discord.Member,
        item_data: tuple,
        item_qty_offered: int
    ) -> Union[bool, None]:
        
        item_amt = await self.user_has_item_from_id(
            user_id=user_to_check.id,
            item_id=item_data[0],
            conn=conn
        )
        if not item_amt:
            await respond(
                interaction, 
                embed=membed(f"{user_to_check.mention} does not have a single {item_data[-1]} {item_data[1]}.")
            )
        elif item_amt < item_qty_offered:
            await respond(
                interaction, 
                embed=membed(
                    f"{user_to_check.mention} only has **{item_amt}x {item_data[-1]} {item_data[1]}**.\n"
                    f"Not the requested **{item_qty_offered}**."
                )
            )
        else:
            return True
            

    async def prompt_for_coins(
        self,
        interaction: discord.Interaction,
        item_sender: discord.Member,
        item_sender_qty: int,
        item_sender_data: tuple,
        coin_sender: discord.Member,
        coin_sender_qty: int,
        can_continue: Optional[bool] = True
    ) -> Union[None, bool]:
        
        """
        Send a confirmation prompt to `item_sender`, asking to confirm whether 
        they want to exchange their items (`item_sender_data`) with `coin_sender`, 
        in return for money (`coin_sender_qty`).

        The person that is confirming has to send items, in exchange they get coins.
        """

        if not can_continue:
            return
        
        can_continue = await process_confirmation(
            interaction,
            view_owner=item_sender,
            content=item_sender.mention,
            prompt=dedent(
                f"""
                > Are you sure you want to trade with {coin_sender.mention}?

                **Their:**
                - {CURRENCY} {coin_sender_qty:,}

                **For Your:**
                - {item_sender_qty}x {item_sender_data[-1]} {item_sender_data[1]}
                """
            )
        )
        return can_continue

    async def prompt_coins_for_items(
        self,
        interaction: discord.Interaction,
        coin_sender: discord.Member,
        item_sender: discord.Member,
        coin_sender_qty: int,
        item_sender_qty: int,
        item_sender_data: tuple,
        can_continue: Optional[bool] = True
    ) -> Union[None, bool]:
        
        """
        Send a confirmation prompt to `coin_sender`, asking to confirm whether 
        they want to exchange their coins for items.

        The person that is confirming has to send coins, and they get items in return.
        """
        # TODO Build checks for ensuring they actually have the specified amount of coins.

        if not can_continue:
            return
        
        can_continue = await process_confirmation(
            interaction,
            view_owner=coin_sender,
            content=coin_sender.mention,
            prompt=dedent(
                f"""
                > Are you sure you want to trade with {item_sender.mention}?

                **Their:**
                - {item_sender_qty}x {item_sender_data[-1]} {item_sender_data[1]}

                **For Your:**
                - {CURRENCY} {coin_sender_qty:,}
                """
            )
        )
        return can_continue
    
    async def prompt_items_for_items(
        self,
        interaction: discord.Interaction,
        item_sender: discord.Member,
        item_sender_qty: int,
        item_sender_data: tuple,
        item_sender2: discord.Member,
        item_sender2_qty: int,
        item_sender2_data: tuple,
        can_continue: Optional[bool] = True
    ) -> Union[None, bool]:
        
        """
        The person that is confirming has to send items, and they also get items in return.
        """

        # TODO Build checks for ensuring they actually have the specified quantity of items
        
        if not can_continue:
            return
        
        can_continue = await process_confirmation(
            interaction,
            view_owner=item_sender,
            content=item_sender.mention,
            prompt=dedent(
                f"""
                > Are you sure you want to trade with {item_sender2.mention}?

                **Their:**
                - {item_sender2_qty}x {item_sender2_data[-1]} {item_sender2_data[1]}

                **For Your:**
                - {item_sender_qty}x {item_sender_data[-1]} {item_sender_data[1]}
                """
            )
        )
        return can_continue

    async def default_checks_passing(self, interaction: discord.Interaction, with_who: discord.Member) -> Union[bool, None]:
        if with_who.id == interaction.user.id:
            return await interaction.response.send_message(
                ephemeral=True, 
                embed=membed("You can't trade with yourself.")
            )
        elif with_who.bot:
            return await interaction.response.send_message(
                ephemeral=True, 
                embed=membed("You can't trade with bots.")
            )
        return True

    @trade.command(name="items_for_coins", description="Exchange your items for coins in return")
    @app_commands.rename(with_who="with")
    @app_commands.describe(
        item="What item will you give?",
        quantity="How much of the item will you give?",
        with_who="Who are you giving this to?",
        for_robux="How much robux do you expect in return?"
    )
    async def trade_items_for_coins(
        self, 
        interaction: discord.Interaction, 
        quantity: int, 
        item: str,
        with_who: discord.Member,
        for_robux: str
    ) -> None:
        
        default_check_passing = await self.default_checks_passing(interaction, with_who)
        if not default_check_passing:
            return
        
        for_robux = await determine_exponent(
            interaction=interaction, 
            rinput=for_robux
        )

        if for_robux is None:
            return

        async with self.bot.pool.acquire() as conn:
            conn: asqlite_Connection
            item_details = await Economy.partial_match_for(interaction, item, conn)

            if item_details is None:
                return

            wallet_amt = await conn.fetchone("SELECT wallet FROM bank WHERE userID = $0", with_who.id)
            if isinstance(for_robux, str):
                for_robux = wallet_amt[0] if wallet_amt else 0

            await self.declare_transaction(conn, user_id=interaction.user.id)
            await conn.commit()
            
            # ! For the person sending items
            item_check_passing = await self.item_checks_passing(
                interaction, 
                conn,
                user_to_check=interaction.user,
                item_data=item_details,
                item_qty_offered=quantity
            )

            if not item_check_passing:
                await self.end_transaction(conn, user_id=interaction.user.id)
                await conn.commit()
                return

            can_continue = await self.prompt_for_coins(
                interaction,
                item_sender=interaction.user,
                item_sender_qty=quantity,
                item_sender_data=item_details,
                coin_sender=with_who,
                coin_sender_qty=for_robux
            )
            if not can_continue:
                await self.end_transaction(conn, user_id=interaction.user.id)
                await conn.commit()
                return

            # ! For the other person sending coins

            await self.declare_transaction(conn, user_id=with_who.id)
            await conn.commit()

            coin_check_passing = await self.coin_checks_passing(
                interaction,
                user_checked=with_who,
                coin_qty_offered=for_robux,
                actual_wallet_amt=wallet_amt
            )
            if not coin_check_passing:
                await conn.execute(
                    """
                    DELETE FROM transactions 
                    WHERE userID IN ($0, $1)
                    """, interaction.user.id, with_who.id
                )
                await conn.commit()
                return

            can_continue = await self.prompt_coins_for_items(
                interaction,
                coin_sender=with_who,
                coin_sender_qty=for_robux,
                item_sender=interaction.user,
                item_sender_qty=quantity,
                item_sender_data=item_details,
                can_continue=can_continue
            )
            
            async with conn.transaction():
                await conn.execute(
                    """
                    DELETE FROM transactions 
                    WHERE userID IN ($0, $1)
                    """, interaction.user.id, with_who.id
                )
                if not can_continue:
                    return
                
                await self.update_inv_by_id(interaction.user, -quantity, item_details[0], conn)
                await conn.execute("UPDATE inventory SET qty = qty + $0 WHERE userID = $1 AND itemID = $2", quantity, with_who.id, item_details[0])
                await self.update_wallet_many(
                    conn, 
                    (-for_robux, with_who.id), 
                    (+for_robux, interaction.user.id)
                )

            embed = discord.Embed(colour=0xFFFFFF)
            embed.title = "Your Trade Receipt"
            embed.description = (
                f"- {interaction.user.mention} gave {with_who.mention} **{quantity}x {item_details[-1]} {item_details[1]}**.\n"
                f"- {interaction.user.mention} received {CURRENCY} **{for_robux:,}** in return."
            )
            embed.set_footer(text="Thanks for your business.")

            await interaction.followup.send(embed=embed)
    
    @trade.command(name="coins_for_items", description="Exchange your coins for items in return")
    @app_commands.rename(with_who="with")
    @app_commands.describe(
        robux_quantity="How much coins do you want to give?",
        for_item="What item do you want to receive?",
        item_quantity="How much of this item do you expect in return?",
        with_who="Who are you trading with?"
    )
    async def trade_coins_for_items(
        self, 
        interaction: discord.Interaction, 
        robux_quantity: str,
        for_item: str,
        item_quantity: int, 
        with_who: discord.Member,
    ) -> None:
        
        default_check_passing = await self.default_checks_passing(interaction, with_who)
        if not default_check_passing:
            return
        
        robux_quantity = await determine_exponent(
            interaction=interaction, 
            rinput=robux_quantity
        )

        if robux_quantity is None:
            return

        async with self.bot.pool.acquire() as conn:
            conn: asqlite_Connection
            item_details = await Economy.partial_match_for(interaction, for_item, conn)

            if item_details is None:
                return

            wallet_amt = await conn.fetchone("SELECT wallet FROM bank WHERE userID = $0", interaction.user.id)
            if isinstance(robux_quantity, str):
                robux_quantity = wallet_amt[0] if wallet_amt else 0

            # ! For the person sending coins

            await self.declare_transaction(conn, user_id=interaction.user.id)
            await conn.commit()

            coin_check_passing = await self.coin_checks_passing(
                interaction,
                user_checked=interaction.user,
                coin_qty_offered=robux_quantity,
                actual_wallet_amt=wallet_amt
            )

            if not coin_check_passing:
                await self.end_transaction(conn, user_id=interaction.user.id)
                await conn.commit()
                return

            can_continue = await self.prompt_coins_for_items(
                interaction,
                coin_sender=interaction.user,
                coin_sender_qty=robux_quantity,
                item_sender=with_who,
                item_sender_qty=item_quantity,
                item_sender_data=item_details,
            )

            if not can_continue:
                await self.end_transaction(conn, user_id=interaction.user.id)
                await conn.commit()
                return
            
            # ! For the other person sending items
            item_check_passing = await self.item_checks_passing(
                interaction, 
                conn,
                user_to_check=with_who,
                item_data=item_details,
                item_qty_offered=item_quantity
            )

            if not item_check_passing:
                await conn.execute(
                    """
                    DELETE FROM transactions 
                    WHERE userID IN ($0, $1)
                    """, interaction.user.id, with_who.id
                )
                await conn.commit()
                return

            can_continue = await self.prompt_for_coins(
                interaction,
                item_sender=with_who,
                item_sender_qty=item_quantity,
                item_sender_data=item_details,
                coin_sender=interaction.user,
                coin_sender_qty=robux_quantity
            )

            async with conn.transaction():
                await conn.execute(
                    """
                    DELETE FROM transactions 
                    WHERE userID IN ($0, $1)
                    """, interaction.user.id, with_who.id
                )

                if not can_continue:
                    return
                
                await self.update_inv_by_id(with_who, -item_quantity, item_details[0], conn)
                await conn.execute(
                    """
                    UPDATE inventory 
                        SET qty = qty + $0 
                    WHERE userID = $1 AND itemID = $2
                    """, item_quantity, interaction.user.id, item_details[0]
                )
                await self.update_wallet_many(
                    conn, 
                    (-robux_quantity, interaction.user.id), 
                    (+robux_quantity, with_who.id)
                )

            embed = discord.Embed(colour=0xFFFFFF)
            embed.title = "Your Trade Receipt"
            embed.description = (
                f"- {interaction.user.mention} gave {with_who.mention} {CURRENCY} **{robux_quantity:,}**.\n"
                f"- {interaction.user.mention} received **{item_quantity}x** {item_details[-1]} {item_details[1]} in return."
            )
            embed.set_footer(text="Thanks for your business.")
            await interaction.followup.send(embed=embed)
    
    @trade.command(name="items_for_items", description="Exchange your items for other items")
    @app_commands.rename(with_who="with")
    @app_commands.describe(
        item="What item will you give?",
        quantity="How much of the item will you give?",
        with_who="Who are you giving this to?",
        for_item="What item do you want in return?",
        for_quantity="How much of this item do you expect in return?"
    )
    async def trade_items_for_items(
        self, 
        interaction: discord.Interaction, 
        quantity: int, 
        item: str,
        with_who: discord.Member,
        for_item: str,
        for_quantity: int
    ) -> None:
        
        default_check_passing = await self.default_checks_passing(interaction, with_who)
        if not default_check_passing:
            return

        async with self.bot.pool.acquire() as conn:
            conn: asqlite_Connection
            item_details = await Economy.partial_match_for(interaction, item, conn)
            item2_details = await Economy.partial_match_for(interaction, for_item, conn)

            if item_details is None or item2_details is None:
                await interaction.followup.send(embed=membed("You did not specify valid items to trade on."))
                return

            if item_details[0] == item2_details[0]:
                return await interaction.response.send_message(
                    ephemeral=True, 
                    embed=membed(f"You can't trade {item_details[-1]} {item_details[1]}(s) on both sides.")
                )

            # ! For the person sending items
            await self.declare_transaction(conn, user_id=interaction.user.id)
            await conn.commit()

            can_continue = await self.item_checks_passing(
                interaction, 
                conn,
                user_to_check=interaction.user,
                item_data=item_details,
                item_qty_offered=quantity
            )

            if not can_continue:
                await self.end_transaction(conn, user_id=interaction.user.id)
                await conn.commit()
                return

            can_continue = await self.prompt_items_for_items(
                interaction,
                item_sender=interaction.user,
                item_sender_qty=quantity,
                item_sender_data=item_details,
                item_sender2=with_who,
                item_sender2_qty=for_quantity,
                item_sender2_data=item2_details
            )

            if not can_continue:
                await self.end_transaction(conn, user_id=interaction.user.id)
                await conn.commit()
                return

            # ! For the other person sending items
            can_continue = await self.item_checks_passing(
                interaction, 
                conn,
                user_to_check=with_who,
                item_data=item2_details,
                item_qty_offered=for_quantity
            )

            if not can_continue:
                await conn.execute(
                    """
                    DELETE FROM transactions 
                    WHERE userID IN ($0, $1)
                    """, interaction.user.id, with_who.id
                )
                await conn.commit()
                return

            can_continue = await self.prompt_items_for_items(
                interaction,
                item_sender=with_who,
                item_sender_qty=for_quantity,
                item_sender_data=item2_details,
                item_sender2=interaction.user,
                item_sender2_qty=quantity,
                item_sender2_data=item_details
            )

            async with conn.transaction():
                await conn.execute(
                    """
                    DELETE FROM transactions 
                    WHERE userID IN ($0, $1)
                    """, interaction.user.id, with_who.id
                )

                if not can_continue:
                    return
                
                await self.update_inv_by_id(interaction.user, -quantity, item_details[0], conn)
                await self.update_inv_by_id(with_who, -for_quantity, item2_details[0], conn)

                await conn.executemany(
                    "UPDATE inventory SET qty = qty + $0 WHERE userID = $1 AND itemID = $2",
                    [
                        (for_quantity, interaction.user.id, item2_details[0]), 
                        (quantity, with_who.id, item_details[0])
                    ]
                )

            embed = discord.Embed(colour=0xFFFFFF)
            embed.title = "Your Trade Receipt"
            embed.description = (
                f"- {interaction.user.mention} gave {with_who.mention} **{quantity}x {item_details[-1]} {item_details[1]}**.\n"
                f"- {interaction.user.mention} received **{for_quantity}x {item2_details[-1]} {item2_details[1]}** in return."
            )
            embed.set_footer(text="Thanks for your business.")
            await interaction.followup.send(embed=embed)

    @commands.command(name="freemium", description="Get a free random item.")
    async def free_item(self, ctx: commands.Context) -> None:
        async with self.bot.pool.acquire() as conn:
            conn: asqlite_Connection
            rQty = randint(1, 5)

            item, emoji = await self.update_user_inventory_with_random_item(ctx.author.id, conn, rQty)
            await conn.commit()

            await ctx.send(embed=membed(f"Success! You just got **{rQty}x** {emoji} {item}!"))

    showcase = app_commands.Group(
        name="showcase", 
        description="Manage your own item showcase.", 
        guild_ids=APP_GUILDS_IDS,
        guild_only=True
    )

    async def delete_missing_showcase_items(
        self, 
        conn: asqlite_Connection, 
        user_id: int, 
        items_to_delete: Optional[set] = None 
    ) -> Union[None, int]:
        """
        Delete showcase items that a user no longer has. 
        
        You can pass in pre-defined items as well.

        This does not commit any deletions.
        """

        items_non_existant = await conn.fetchall(
            """
            SELECT
                showcase.itemID
            FROM showcase
            LEFT JOIN inventory
                ON showcase.itemID = inventory.itemID AND inventory.userID = $0
            WHERE showcase.userID = $0 AND inventory.qty IS NULL
            """, user_id
        )

        # meaning no pending deletion tasks
        if (not items_non_existant) and (items_to_delete is None):
            return
        
        items_to_delete = items_to_delete or set()
        for item in items_non_existant:
            items_to_delete.add(item[0])

        placeholders = ', '.join(f'${i}' for i in range(1, len(items_to_delete)+1))
        await conn.fetchall(
            f"""
            DELETE FROM showcase 
            WHERE userID = $0 AND itemID IN ({placeholders})
            """, user_id, *items_to_delete
        )
        return len(items_to_delete)

    @app_commands.describe(item=ITEM_DESCRPTION)
    @showcase.command(name="add", description="Add an item to your showcase")
    async def add_showcase_item(self, interaction: discord.Interaction, item: str) -> None:

        async with self.bot.pool.acquire() as conn:
            item_details = await Economy.partial_match_for(interaction, item, conn)

            if item_details is None:
                return
            item_id, item, ie = item_details
            all_embeds = []

            async with conn.transaction():

                val = await self.delete_missing_showcase_items(
                    conn,
                    user_id=interaction.user.id
                )

                if val:
                    all_embeds.append(membed(SHOWCASE_ITEMS_REMOVED))

                val = await Economy.user_has_item_from_id(interaction.user.id, item_id, conn)

                if not val:
                    all_embeds.append(f"You don't have a single {ie} **{item}**.")
                    return await respond(
                        interaction=interaction, 
                        ephemeral=True,
                        embeds=all_embeds
                    )

                # ! Insert branch
                val = await conn.fetchone(
                    """
                    INSERT INTO showcase (userID, itemID, itemPos)
                    SELECT $1, $2, COALESCE((SELECT MAX(itemPos) FROM showcase WHERE userID = $1), 0) + 1
                    WHERE NOT EXISTS (
                        SELECT 1 FROM showcase WHERE userID = $1 AND itemID = $2
                    )
                    RETURNING itemID
                    """, interaction.user.id, item_id
                )

            if val is None:
                all_embeds.append(membed(f"You already have **{ie} {item}** in your showcase."))
                return await respond(
                    interaction=interaction,
                    ephemeral=True,
                    embeds=all_embeds
                )
            
            all_embeds.append(membed(f"Added {ie} {item} to your showcase!"))
            await respond(interaction=interaction, embeds=all_embeds)

    @showcase.command(name="remove", description="Remove an item from your showcase")
    @app_commands.describe(item=ITEM_DESCRPTION)
    async def remove_showcase_item(self, interaction: discord.Interaction, item: str) -> None:
        
        async with self.bot.pool.acquire() as conn:
            conn: asqlite_Connection

            item_details = await Economy.partial_match_for(interaction, item, conn)

            if item_details is None:
                return
            item_id, item, ie = item_details

            val = await self.delete_missing_showcase_items(
                conn,
                user_id=interaction.user.id,
                items_to_delete={item_id,}
            )
            all_embeds = []

            if val and (val > 1):
                all_embeds.append(membed(SHOWCASE_ITEMS_REMOVED))
            await conn.commit()
            
            all_embeds.append(membed(f"If **{ie} {item}** was in your showcase, it's now been removed."))
            await respond(interaction=interaction, embeds=all_embeds)

    @commands.command(name="st", description="Test out your showcase before publishing")
    async def show_showcase_data(self, ctx: commands.Context):
        async with self.bot.pool.acquire() as conn:
            emb = await Economy.fetch_showdata(ctx.author, conn)
            await ctx.send(embed=emb)

    shop = app_commands.Group(
        name='shop', 
        description='View items available for purchase.', 
        guild_only=True, 
        guild_ids=APP_GUILDS_IDS
    )

    @shop.command(name='view', description='View all the shop items')
    async def view_the_shop(self, interaction: discord.Interaction) -> None:
        """This is a subcommand. View the currently available items within the shop."""

        paginator = PaginationItem(interaction)
        async with self.bot.pool.acquire() as conn:
        
            shop_sorted = await conn.fetchall(
                """
                SELECT itemName, emoji, cost
                FROM shop 
                WHERE available = 1 
                GROUP BY itemName
                ORDER BY cost
                """
            )

            additional_notes = [
                (
                    f"{item[1]} {item[0]} \U00002500 [{CURRENCY} **{item[2]:,}**](https://youtu.be/dQw4w9WgXcQ)", 
                    ShopItem(item[0], item[2], item[1], row=i % 2)
                ) 
                for i, item in enumerate(shop_sorted)
            ]

            emb = membed()
            emb.title = "Shop"

            async def get_page_part(page: int):
                wallet = await self.get_wallet_data_only(interaction.user, conn)
                wallet = wallet or 0

                emb.description = f"> You have {CURRENCY} **{wallet:,}**.\n\n"

                length = 6
                offset = (page - 1) * length

                for item in paginator.children:
                    if item.style == discord.ButtonStyle.blurple:
                        paginator.remove_item(item)

                for item_attrs in additional_notes[offset:offset + length]:
                    emb.description += f"{item_attrs[0]}\n"
                    item_attrs[1].disabled = wallet < item_attrs[1].cost
                    paginator.add_item(item_attrs[1])

                n = paginator.compute_total_pages(len(additional_notes), length)
                emb.set_footer(text=f"Page {page} of {n}")
                return emb, n

            paginator.get_page = get_page_part
            await paginator.navigate()

    @shop.command(name='sell', description='Sell an item from your inventory', extras={"exp_gained": 4})
    @app_commands.describe(
        item='The name of the item you want to sell.', 
        sell_quantity='The amount of this item to sell. Defaults to 1.'
    )
    async def sell(
        self, 
        interaction: discord.Interaction, 
        item: str, 
        sell_quantity: Optional[app_commands.Range[int, 1]] = 1
    ) -> None:
        """Sell an item you already own."""
        
        sell_quantity = abs(sell_quantity)
        
        async with self.bot.pool.acquire() as conn:
            conn: asqlite_Connection

            item_details = await Economy.partial_match_for(interaction, item, conn)

            if item_details is None:
                return
            item_id, item_name, ie = item_details

            item_attrs = await conn.fetchone(
                """
                SELECT shop.cost, inventory.qty, shop.sellable
                FROM shop
                INNER JOIN inventory ON shop.itemID = inventory.itemID
                WHERE shop.itemID = $0 AND inventory.userID = $1
                """, item_id, interaction.user.id
            )

            if item_attrs is None:
                return await respond(
                    interaction=interaction, 
                    ephemeral=True,
                    embed=membed(f"You don't own a single {ie} **{item_name}**.")
                )

            cost, qty, sellable = item_attrs

            if not sellable:
                return await respond(
                    interaction=interaction, 
                    ephemeral=True,
                    embed=membed(f"You can't sell **{ie} {item_name}**.")
                )

            if qty < sell_quantity:
                return await respond(
                    interaction=interaction,
                    ephemeral=True, 
                    embed=membed(f"You don't have {ie} **{sell_quantity:,}x** {item_name}, so uh no.")
                )

            multi = await Economy.get_multi_of(user_id=interaction.user.id, multi_type="robux", conn=conn)
            cost = selling_price_algo((cost / 4) * sell_quantity, multi)

            if await self.is_setting_enabled(conn, user_id=interaction.user.id, setting="selling_confirmations"):
                await Economy.declare_transaction(conn, user_id=interaction.user.id)

                value = await process_confirmation(
                    interaction=interaction, 
                    prompt=(
                        f"Are you sure you want to sell **{sell_quantity:,}x "
                        f"{ie} {item_name}** for **{CURRENCY} {cost:,}**?"
                    )
                )
                await Economy.end_transaction(conn, user_id=interaction.user.id)
                await conn.commit()

                if not value:
                    return

            embed = membed(
                f"{interaction.user.mention} sold **{sell_quantity:,}x {ie} {item_name}** "
                f"and got paid {CURRENCY} **{cost:,}**."
            )

            embed.title = f"{interaction.user.display_name}'s Sale Receipt"
            embed.set_footer(text="Thanks for your business.")
            await respond(interaction, embed=embed)
            
            await self.update_inv_new(interaction.user, -qty, item_name, conn)
            await self.update_bank_new(interaction.user, conn, +cost)
            await conn.commit()

    @app_commands.command(name='item', description='Get more details on a specific item')
    @app_commands.describe(item_name=ITEM_DESCRPTION)
    @app_commands.rename(item_name="name")
    @app_commands.guilds(*APP_GUILDS_IDS)
    async def item(self, interaction: discord.Interaction, item_name: str) -> None:
        """This is a subcommand. Look up a particular item within the shop to get more information about it."""

        async with self.bot.pool.acquire() as conn:
            conn: asqlite_Connection
            item_details = await Economy.partial_match_for(interaction, item_name, conn)

            if item_details is None:
                return
            item_id, item_name, _ = item_details

            data = await conn.fetchone(
                """
                WITH inventory_data AS (
                    SELECT 
                        qty, 
                        itemID 
                    FROM inventory 
                    WHERE itemID = $1 AND userID = $2
                ),
                multiplier_data AS (
                    SELECT 
                        COALESCE(SUM(amount), 0) AS total_amount
                    FROM multipliers
                    WHERE (userID IS NULL OR userID = $2)
                    AND multi_type = $3
                )
                SELECT 
                    COALESCE(inventory_data.qty, 0) AS qty,
                    shop.itemType,
                    shop.cost,
                    shop.description,
                    shop.image,
                    shop.rarity,
                    shop.available,
                    shop.sellable,
                    multiplier_data.total_amount AS multiplier
                FROM shop
                LEFT JOIN inventory_data ON shop.itemID = inventory_data.itemID
                CROSS JOIN multiplier_data
                WHERE shop.itemID = $1
                """, item_id, interaction.user.id, "robux"
            )

            their_count, item_type, cost, description, image, rarity, available, sellable, multi = data
            dynamic_text = (
                f"> *{description}*\n\n"
                f"You own **{their_count:,}**"
            )

            net = await self.calculate_inventory_value(interaction.user, conn)
            if their_count:
                amt = ((their_count*cost)/net)*100
                dynamic_text += f" ({amt:.1f}% of your net worth)" if amt >= 0.1 else ""

            em = discord.Embed(
                title=item_name,
                description=dynamic_text, 
                colour=RARITY_COLOUR.get(rarity, 0x2B2D31), 
                url="https://www.youtube.com"
            )

            sell_val_orig = int(cost / 4)
            sell_val_multi = selling_price_algo(sell_val_orig, multi)
            em.add_field(
                name="Value",
                inline=False,
                value=(
                    f"- buy: {CURRENCY} {cost:,}\n"
                    f"- sell: {CURRENCY} {sell_val_orig:,} ({CURRENCY} {sell_val_multi:,} with your {multi}% multi)"
                )
            )

            em.add_field(
                name="Additional Info",
                value=(
                    f"- {'can' if sellable else 'cannot'} be sold\n"
                    f"- {'can' if available else 'cannot'} purchase in the shop"
                )
            )

            em.set_thumbnail(url=image)
            em.set_footer(text=f"{rarity} {item_type}")
            await respond(interaction=interaction, embed=em)

    @commands.command(name='reasons', description='Identify causes of registration errors')
    async def not_registered_why(self, ctx: commands.Context) -> None:
        """Display all the possible causes of a not registered check failure."""

        async with ctx.typing():
            await ctx.send(
                embed=discord.Embed(
                    colour=0x2B2D31,
                    title="Not registered? But why?",
                    description=(
                        'This list is not exhaustive, all known causes will be displayed:\n'
                        '- You were removed by the c2c developers.\n'
                        '- You opted out of the system yourself.\n'
                        '- The database is currently under construction.\n'
                        '- The database malfunctioned due to a undelivered transaction.\n'
                        '- You called a command that is using an outdated database.\n'
                        '- The database unexpectedly closed (likely due to maintenance).\n'
                        '- The developers are modifying the database contents.\n'
                        '- The database is closed and a connection has not been yet.\n'
                        '- The command hasn\'t acquired a pool connection (devs know why).\n\n'
                        'Found an unusual bug on a command? **Report it now to prevent further issues.**'
                    )
                )
            )

    @register_item('Bank Note')
    async def increase_bank_space(
        interaction: discord.Interaction, 
        quantity: int, 
        conn: asqlite_Connection
    ) -> None:
        
        expansion = randint(1_600_000, 6_000_000)
        expansion *= quantity
        new_bankspace = await conn.fetchone(
            """
            UPDATE bank 
            SET bankspace = bankspace + $0 
            WHERE userID = $1 
            RETURNING bankspace
            """, expansion, interaction.user.id
        )

        new_amt = await Economy.update_inv_new(interaction.user, -quantity, "Bank Note", conn)
        
        embed = membed()
        
        embed.add_field(
            name="Used", 
            value=f"{quantity}x <:BankNote:1216429670908694639> Bank Note"
        )
        
        embed.add_field(
            name="Added Bank Space", 
            value=f"{CURRENCY} {expansion:,}"
        )

        embed.add_field(
            name="Total Bank Space", 
            value=f"{CURRENCY} {new_bankspace[0]:,}"
        )

        embed.set_footer(text=f"{new_amt[0]:,}x bank note left")
        await conn.commit()
        await respond(interaction=interaction, embed=embed)

    @register_item('Trophy')
    async def flex_via_trophy(interaction: discord.Interaction, quantity: int, _: asqlite_Connection) -> None:
        content = f'\n\nThey have **{quantity}** of them, WHAT A BADASS' if quantity > 1 else ''
        
        await respond(
            interaction=interaction,
            embed=membed(
                f"{interaction.user.name} is flexing on you all "
                f"with their <:tr1:1165936712468418591> **~~PEPE~~ TROPHY**{content}"
            )
        )
    
    @register_item('Bitcoin')
    async def gain_bitcoin_multiplier(interaction: discord.Interaction, _: int, conn: asqlite_Connection) -> None:
        future_expiry = (discord.utils.utcnow() + datetime.timedelta(minutes=30)).timestamp()

        applied_successfully = await Economy.add_multiplier(
            conn, 
            user_id=interaction.user.id, 
            multi_amount=500,
            multi_type="robux",
            cause="bitcoin",
            description="Bitcoin Multiplier",
            expiry=future_expiry,
            on_conflict="NOTHING"
        )

        if not applied_successfully:
            return await respond(
                interaction=interaction,
                embed=membed("You already have a <:btc:1244948562471551047> Bitcoin multiplier active.")
            )

        await Economy.update_inv_by_id(interaction.user, amount=-1, item_id=21, conn=conn)
        await conn.commit()
        
        await respond(
            interaction=interaction,
            embed=membed(
                "You just activated a **30 minute** <:btc:1244948562471551047> Bitcoin multiplier!\n"
                "You'll get 500% more robux from transactions during this time."
            )
        )

        Economy.start_check_for_expiry(interaction)

    @app_commands.command(name="use", description="Use an item you own from your inventory", extras={"exp_gained": 3})
    @app_commands.guilds(*APP_GUILDS_IDS)
    @app_commands.describe(item=ITEM_DESCRPTION, quantity='Amount of items to use, when possible.')
    async def use_item(
        self, 
        interaction: discord.Interaction, 
        item: str, 
        quantity: Optional[int] = 1
    ) -> Union[discord.WebhookMessage, None]:
        """Use a currently owned item."""
        quantity = abs(quantity)

        async with self.bot.pool.acquire() as conn:
            conn: asqlite_Connection
            
            item_details = await Economy.partial_match_for(interaction, item, conn)

            if item_details is None:
                return
            item_id, item_name, ie = item_details

            data = await conn.fetchone(
                """
                SELECT qty
                FROM inventory
                WHERE itemID = $0 AND userID = $1
                """, item_id, interaction.user.id
            )

            if not data:
                return await respond(
                    interaction=interaction,
                    ephemeral=True,
                    embed=membed(f"You don't own a single {ie} **{item_name}**, therefore cannot use it.")
                )
            
            qty, = data
            if qty < quantity:
                return await respond(
                    interaction=interaction,
                    ephemeral=True,
                    embed=membed(f"You don't own **{quantity}x {ie} {item_name}**, therefore cannot use this many.")
                )
            
            handler = item_handlers.get(item_name)
            if handler is None:
                return await respond(
                    interaction=interaction,
                    ephemeral=True,
                    embed=membed(f"{ie} **{item_name}** does not have a use yet.\nWait until it does!")
                )
            
            await handler(interaction, quantity, conn)

    @app_commands.command(name="prestige", description="Sacrifice currency stats in exchange for incremental perks")
    @app_commands.guilds(*APP_GUILDS_IDS)
    async def prestige(self, interaction: discord.Interaction) -> None:
        """Sacrifice a portion of your currency stats in exchange for incremental perks."""

        async with self.bot.pool.acquire() as conn:
            conn: asqlite_Connection
            
            data = await conn.fetchone(
                """
                SELECT prestige, level, wallet + bank AS total_robux 
                FROM `bank` 
                WHERE userID = $0
                """, interaction.user.id
            )

            if data is None:
                return await interaction.response.send_message(embed=self.not_registered, ephemeral=True)

            prestige, actual_level, actual_robux = data

            if prestige == 10:
                return await interaction.response.send_message(
                    ephemeral=True,
                    embed=membed(
                        "You've reached the highest prestige!\n"
                        "No more perks can be obtained from this command."
                    )
                )

            req_robux = (prestige + 1) * 24_000_000
            req_level = (prestige + 1) * 35

            if (actual_robux >= req_robux) and (actual_level >= req_level):
                massive_prompt = dedent(
                    """
                    Prestiging means losing nearly everything you've ever earned in the currency 
                    system in exchange for increasing your 'Prestige Level' 
                    and upgrading your status.
                    **Things you will lose**:
                    - All of your items/showcase
                    - All of your robux
                    - Your drone(s)
                    - Your levels and XP
                    Anything not mentioned in this list will not be lost.
                    Are you sure you want to prestige?
                    """
                )
                
                await Economy.declare_transaction(conn, user_id=interaction.user.id)
                await conn.commit()
                value = await process_confirmation(
                    interaction=interaction, 
                    prompt=massive_prompt
                )

                await Economy.end_transaction(conn, user_id=interaction.user.id)
                if value:

                    await conn.execute("DELETE FROM inventory WHERE userID = ?", interaction.user.id)
                    await conn.execute(
                        f"""
                        UPDATE `{BANK_TABLE_NAME}` 
                        SET 
                            wallet = $0, 
                            bank = $0, 
                            level = $1, 
                            exp = $0, 
                            prestige = prestige + 1, 
                            bankspace = bankspace + $2 
                        WHERE userID = $3
                        """, 0, 1, randint(100_000_000, 500_000_000), interaction.user.id
                    )
                    
                    await self.add_multiplier(
                        conn,
                        user_id=interaction.user.id,
                        multi_amount=10,
                        multi_type="robux",
                        cause="prestige",
                        description=f"Prestige {prestige+1}"
                    )

                await conn.commit()
            else:
                emoji = PRESTIGE_EMOTES.get(prestige + 1)
                emoji = search(r':(\d+)>', emoji)
                emoji = self.bot.get_emoji(int(emoji.group(1)))

                actual_robux_progress = (actual_robux / req_robux) * 100
                actual_level_progress = (actual_level / req_level) * 100

                embed = discord.Embed(
                    title=f"Prestige {prestige + 1} Requirements",
                    colour=0x2B2D31,
                    description=(
                        f"**Total Balance**\n"
                        f"<:replyconti:1199688910649954335> {CURRENCY} {actual_robux:,}/{req_robux:,}\n"
                        f"<:replyi:1199688912646455416> {generate_progress_bar(actual_robux_progress)} "
                        f"` {int(actual_robux_progress):,}% `\n"
                        f"\n"
                        f"**Level Required**\n"
                        f"<:replyconti:1199688910649954335> {actual_level:,}/{req_level:,}\n"
                        f"<:replyi:1199688912646455416> {generate_progress_bar(actual_level_progress)} "
                        f"` {int(actual_level_progress):,}% `"
                    )
                )
                embed.set_thumbnail(url=emoji.url)
                embed.set_footer(text="Imagine thinking you can prestige already.")
                await interaction.response.send_message(embed=embed)

    @app_commands.command(name='profile', description='View user information and other stats')
    @app_commands.guilds(*APP_GUILDS_IDS)
    @app_commands.describe(
        user='The user whose profile you want to see.', 
        category='What type of data you want to view.'
    )
    async def find_profile(
        self, 
        interaction: discord.Interaction, 
        user: Optional[USER_ENTRY], 
        category: Optional[Literal["Main Profile", "Gambling Stats"]] = "Main Profile"
    ) -> None:
        """View your profile within the economy."""

        return await interaction.response.send_message(
            embed=membed(
                "We're working on custom profiles so this command is disabled for now.\n"
                "Track our progress [here](https://github.com/SGA-A/c2c/issues/110)."
            )
        )

        user = user or interaction.user

        vis = True
        if vis:
            return await interaction.response.send_message(
                embed=membed(
                    f"# <:security:1153754206143000596> {user.name}'s profile is protected.\n"
                    f"Only approved users can view {user.name}'s profile info."
                )
            )

        ephemerality = (vis == "private") and (interaction.user.id == user.id)

        async with self.bot.pool.acquire() as conn:
            conn: asqlite_Connection

            if category == "Main Profile":
                procfile = discord.Embed(colour=user.colour)

                data = await conn.fetchone(
                    f"""
                    SELECT wallet, bank, showcase, title, bounty, prestige, level, exp 
                    FROM `{BANK_TABLE_NAME}` 
                    WHERE userID = $0
                    """, user.id
                )

                if data is None:
                    return await interaction.response.send_message(ephemeral=True, embed=NOT_REGISTERED)

                wallet, bank, showcase, title, bounty, prestige, level, exp = data

                net_attrs = await conn.fetchone(
                    """
                    SELECT 
                        COUNT(DISTINCT inventory.itemID), 
                        COALESCE(SUM(qty), 0), 
                        COALESCE(SUM(qty * cost), 0)
                    FROM inventory
                    JOIN shop ON inventory.itemID = shop.itemID
                    WHERE userID = $0
                    """, user.id
                )

                # ----------- SHOWCASE STUFF ------------
                
                showcase_ui_new = await self.do_showcase_lookup(
                    raw_showcase=showcase,
                    conn=conn,
                    user_id=user.id
                )

                # -------------- COMMANDS --------------
                
                cmd_count = await total_commands_used_by_user(user.id, conn=conn)
                fav = await find_fav_cmd_for(user.id, conn=conn)

                # ---------------------------------------

                procfile.title = f"{user.name} - {title}"
                procfile.url = "https://www.dis.gd/support"
                procfile.description = dedent(
                    f"""
                    {PRESTIGE_EMOTES.get(prestige, "")} Prestige Level **{prestige}** {UNIQUE_BADGES.get(prestige, "")}
                    <:bountybag:1195653667135692800> Bounty: {CURRENCY} **{bounty:,}**
                    {vis or "No badges acquired yet"}
                    """
                )
                
                boundary = self.calculate_exp_for(level=level)
                procfile.add_field(
                    name='Level',
                    value=(
                        f"Level: `{level:,}`\n"
                        f"Experience: `{format_number_short(exp)}/{format_number_short(boundary)}`\n"
                        f"{generate_progress_bar((exp / boundary) * 100)}"
                    )
                )

                procfile.add_field(
                    name='Robux',
                    value=(
                        f"Wallet: `{CURRENCY} {format_number_short(wallet)}`\n"
                        f"Bank: `{CURRENCY} {format_number_short(bank)}`\n"
                        f"Net: `{CURRENCY} {format_number_short(wallet+bank)}`"
                    )
                )

                procfile.add_field(
                    name='Items',
                    value=(
                        f"Unique: `{net_attrs[0]:,}`\n"
                        f"Total: `{format_number_short(net_attrs[1])}`\n"
                        f"Worth: `{CURRENCY} {format_number_short(net_attrs[2])}`"
                    )
                )

                procfile.add_field(
                    name='Commands', 
                    value=(
                        f"Total: `{format_number_short(cmd_count)}`\n"
                        f"Favourite: `{fav[1:]}`"
                    )
                )
                
                procfile.add_field(
                    name="Showcase", 
                    value="\n".join(showcase_ui_new) or "No showcase"
                )

                return await interaction.response.send_message(embed=procfile, ephemeral=ephemerality)
            else:
                data = await conn.fetchone(
                    f"""
                    SELECT 
                        slotw, slotl, betw, betl, bjw, bjl, 
                        slotwa, slotla, betwa, betla, bjwa, bjla 
                    FROM 
                        `{BANK_TABLE_NAME}` 
                    WHERE 
                        userID = $0
                    """, user.id
                )

                if data is None:
                    return await interaction.response.send_message(embed=NOT_REGISTERED, ephemeral=True)

                total_slots = data[0] + data[1]
                total_bets = data[2] + data[3]
                total_blackjacks = data[4] + data[5]

                try:
                    winbe = (data[2] / total_bets) * 100
                except ZeroDivisionError:
                    winbe = 0
                try:
                    winsl = (data[0] / total_slots) * 100
                except ZeroDivisionError:
                    winsl = 0
                try:
                    winbl = (data[4] / total_blackjacks) * 100
                except ZeroDivisionError:
                    winbl = 0

                stats = discord.Embed(
                    title=f"{user.name}'s gambling stats", 
                    description="**Reminder:** Games that have resulted in a tie are not tracked.",
                    colour=0x2B2D31
                )
                
                stats.add_field(
                    name=f"BET ({total_bets:,})",
                    value=(
                        f"Won: {CURRENCY} {data[8]:,}\n"
                        f"Lost: {CURRENCY} {data[9]:,}\n"
                        f"Net: {CURRENCY} {data[8] - data[9]:,}\n"
                        f"Win: {winbe:.0f}% ({data[2]})"
                    )
                )

                stats.add_field(
                    name=f"SLOTS ({total_slots:,})",
                    value=(
                        f"Won: {CURRENCY} {data[6]:,}\n"
                        f"Lost: {CURRENCY} {data[7]:,}\n"
                        f"Net: {CURRENCY} {data[6] - data[7]:,}\n"
                        f"Win: {winsl:.0f}% ({data[0]})"
                    )
                )

                stats.add_field(
                    name=f"BLACKJACK ({total_blackjacks:,})",
                    value=(
                        f"Won: {CURRENCY} {data[10]:,}\n"
                        f"Lost: {CURRENCY} {data[11]:,}\n"
                        f"Net: {CURRENCY} {data[10] - data[11]:,}\n"
                        f"Win: {winbl:.0f}% ({data[4]})"
                    )
                )

                stats.set_footer(text="The number next to the name is how many matches are recorded")

                piee = discord.Embed(title="Games played")  # piee - pie embed
                piee.colour = 0x2B2D31

                try:

                    its_sum = total_bets + total_slots + total_blackjacks
                    pie = (
                        ImageCharts().chd(
                            f"t:{(total_bets / its_sum) * 100},"
                            f"{(total_slots / its_sum) * 100},{(total_blackjacks / its_sum) * 100}"
                        )
                        .chco("EA469E|03A9F4|FFC00C")
                        .chl(f"BET ({total_bets})|SLOTS ({total_slots})|BJ ({total_blackjacks})")
                        .chdl("Total bet games|Total slot games|Total blackjack games")
                        .chli(f"{its_sum}")
                        .chs("600x480")
                        .cht("pd")
                        .chtt(f"{user.name}'s total games played")
                    )

                    piee.set_image(url=pie.to_url())
                except ZeroDivisionError:
                    piee.description = f"{user.mention} has not got enough data yet to form a pie chart."
                
                await interaction.response.send_message(embeds=[stats, piee], ephemeral=ephemerality)

    @app_commands.command(name='highlow', description='Guess the number. Jackpot wins big!', extras={"exp_gained": 3})
    @app_commands.guilds(*APP_GUILDS_IDS)
    @app_commands.describe(robux=ROBUX_DESCRIPTION)
    async def highlow(self, interaction: discord.Interaction, robux: str) -> None:
        """
        Guess the number. The user must guess if the clue the bot gives is higher,
        lower or equal to the actual number.
        """

        async with self.bot.pool.acquire() as conn:
            conn: asqlite_Connection

            wallet_amt = await conn.fetchone(f"SELECT wallet FROM `{BANK_TABLE_NAME}` WHERE userID = $0", interaction.user.id)
            if wallet_amt is None:
                return await interaction.response.send_message(embed=self.not_registered, ephemeral=True)
            wallet_amt, = wallet_amt

            has_keycard = await self.user_has_item_from_id(interaction.user.id, item_id=1, conn=conn)
            robux = await self.do_wallet_checks(
                interaction=interaction,
                wallet_amount=wallet_amt,
                exponent_amount=robux,
                has_keycard=has_keycard
            )

            if robux is None:
                return

            number = randint(1, 100)
            hint = randint(1, 100)

            query = membed()
            query.description = (
                "I just chose a secret number between 0 and 100.\n"
                f"Is the secret number *higher* or *lower* than **{hint}**?"
            )

            query.set_author(
                name=f"{interaction.user.name}'s high-low game", 
                icon_url=interaction.user.display_avatar.url
            )

            query.set_footer(text="The jackpot button is if you think it is the same!")
            
            hl_view = HighLow(
                interaction, 
                hint_provided=hint, 
                bet=robux, 
                value=number
            )

            await Economy.declare_transaction(conn, user_id=interaction.user.id)
            await interaction.response.send_message(view=hl_view, embed=query)

    @app_commands.command(name='slots', description='Try your luck on a slot machine', extras={"exp_gained": 3})
    @app_commands.guilds(*APP_GUILDS_IDS)
    @app_commands.describe(robux=ROBUX_DESCRIPTION)
    async def slots(self, interaction: discord.Interaction, robux: str) -> None:
        """Play a round of slots. At least one matching combination is required to win."""

        async with self.bot.pool.acquire() as conn:
            conn: asqlite_Connection

        # --------------- Checks before betting i.e. has keycard, meets bet constraints. -------------
        has_keycard = await self.user_has_item_from_id(interaction.user.id, item_id=1, conn=conn)
        slot_stuff = await conn.fetchone("SELECT slotw, slotl, wallet FROM `bank` WHERE userID = $0", interaction.user.id)
        id_won_amount, id_lose_amount, wallet_amt = slot_stuff[0], slot_stuff[1], slot_stuff[-1]

        robux = await self.do_wallet_checks(
            interaction=interaction,
            wallet_amount=wallet_amt,
            exponent_amount=robux,
            has_keycard=has_keycard
        )
        
        if robux is None:
            return

        # ------------------ THE SLOT MACHINE ITESELF ------------------------

        emoji_outcome = generate_slot_combination()
        emoji_1, emoji_2, emoji_3 = emoji_outcome
        multiplier = find_slot_matches(emoji_1, emoji_2, emoji_3)
        slot_machine = discord.Embed()

        if multiplier:

            amount_after_multi = add_multi_to_original(multi=multiplier, original=robux)

            async with conn.transaction():
                conn: asqlite_Connection
                updated = await self.update_bank_three_new(
                    interaction.user, 
                    conn, 
                    "slotwa", amount_after_multi, 
                    "wallet", amount_after_multi, 
                    "slotw", 1
                )

            prcntw = (updated[2] / (id_lose_amount + updated[2])) * 100

            slot_machine.colour = discord.Color.brand_green()
            slot_machine.description = (
                f"**\U0000003e** {emoji_1} {emoji_2} {emoji_3} **\U0000003c**\n\n"
                f"**It's a match!** You've won {CURRENCY} **{amount_after_multi:,}**.\n"
                f"Your new balance is {CURRENCY} **{updated[1]:,}**.\n"
                f"You've won {prcntw:.1f}% of all slots games."
            )

            slot_machine.set_author(
                name=f"{interaction.user.name}'s winning slot machine", 
                icon_url=interaction.user.display_avatar.url
            )
            slot_machine.set_footer(text=f"Multiplier: {multiplier}%")

        else:

            async with conn.transaction():
                conn: asqlite_Connection
                updated = await self.update_bank_three_new(
                    interaction.user, 
                    conn, 
                    "slotla", robux, 
                    "wallet", -robux, 
                    "slotl", 1
                )

            prcntl = (updated[-1] / (updated[-1] + id_won_amount)) * 100

            slot_machine.colour = discord.Color.brand_red()
            slot_machine.description = (
                f"**\U0000003e** {emoji_1} {emoji_2} {emoji_3} **\U0000003c**\n\n"
                f"**No match!** You've lost {CURRENCY} **{robux:,}**.\n"
                f"Your new balance is {CURRENCY} **{updated[1]:,}**.\n"
                f"You've lost {prcntl:.1f}% of all slots games."
            )

            slot_machine.set_author(
                name=f"{interaction.user.name}'s losing slot machine", 
                icon_url=interaction.user.display_avatar.url
            )

        await interaction.response.send_message(embed=slot_machine)
    
    @app_commands.command(name='inventory', description='View your currently owned items')
    @app_commands.guilds(*APP_GUILDS_IDS)
    @app_commands.describe(member='The user whose inventory you want to see.')
    async def inventory(
        self, 
        interaction: discord.Interaction, 
        member: Optional[USER_ENTRY]
    ) -> None:
        """View your inventory or another player's inventory."""
        member = member or interaction.user

        if (member.bot) and (member.id != self.bot.user.id):
            return await interaction.response.send_message(
                ephemeral=True,
                embed=membed("Bots do not have accounts.")
            )

        async with self.bot.pool.acquire() as conn:
            conn: asqlite_Connection

            em = membed()
            length = 8

            query = (
                """
                SELECT shop.itemName, shop.emoji, inventory.qty
                FROM shop
                INNER JOIN inventory 
                    ON shop.itemID = inventory.itemID
                WHERE inventory.userID = $0
                """
            )

            owned_items = await conn.fetchall(query, member.id)

            if not owned_items:
                if member.id == interaction.user.id:
                    em.description = "You don't have any items yet."
                else:
                    em.description = f"{member.mention} has nothing for you to see."
                return await interaction.response.send_message(embed=em, ephemeral=True)

            em.set_author(
                name=f"{member.display_name}'s Inventory", 
                icon_url=member.display_avatar.url
            )
            paginator = RefreshPagination(interaction)

            async def get_page_part(page: int, force_refresh: Optional[bool] = False):
                """Helper function to determine what page of the paginator we're on."""

                if force_refresh:
                    nonlocal owned_items
                    owned_items = await conn.fetchall(query, member.id)

                n = paginator.compute_total_pages(len(owned_items), length)
                page = min(page, n)
                paginator.index = page

                offset = (page - 1) * length
                em.description = "\n".join(
                    f"{item[1]} **{item[0]}** \U00002500 {item[2]:,}" 
                    for item in owned_items[offset:offset + length]
                )

                em.set_footer(text=f"Page {page} of {n}")
                return em, n

            paginator.get_page = get_page_part

            await paginator.navigate()

    async def do_order(self, interaction: discord.Interaction, job_name: str) -> None:
        possible_words: tuple = JOB_KEYWORDS.get(job_name)[0] 
        list_possible_words = list(possible_words)
        shuffle(list_possible_words)
        
        reduced = randint(5000000, JOB_KEYWORDS.get(job_name)[-1])
        
        selected_words = sample(list_possible_words, k=5)
        selected_words = [word.lower() for word in selected_words]

        embed = discord.Embed(
            title="Remember the order of words!",
            description="\n".join(selected_words),
            colour=0x2B2D31
        )

        await interaction.response.send_message(embed=embed)
        
        view = RememberOrder(
            interaction, 
            list_of_five_order=selected_words, 
            their_job=job_name,
            base_reward=reduced
        )

        await sleep(3)
        await interaction.edit_original_response(
            embed=membed("What was the order?"),
            view=view
        )

    async def do_tiles(
            self, 
            interaction: discord.Interaction, 
            job_name: str
        ) -> None:

        emojis = [
            "\U0001f600", "\U0001f606", "\U0001f643", "\U0001f642", "\U0001f609", 
            "\U0001f60c", "\U0001f917", "\U0001f914", "\U0001f601", "\U0001f604"
        ]

        shuffle(emojis)
        emoji = choice(emojis)

        prompter = membed(f"Look at the emoji closely!\n{emoji}")

        await interaction.response.send_message(embed=prompter)
        await sleep(3)

        view = RememberPositionView(
            interaction, 
            all_emojis=emojis, 
            actual_emoji=emoji, 
            their_job=job_name
        )
        
        prompter.description = "What was the emoji?"
        return await interaction.edit_original_response(embed=prompter, view=view)

    work = app_commands.Group(
        name="work", 
        description="Work management commands.", 
        guild_only=True, 
        guild_ids=APP_GUILDS_IDS
    )

    @work.command(name="shift", description="Fulfill a shift at your current job", extras={"exp_gained": 3})
    async def shift_at_work(self, interaction: discord.Interaction) -> None:
        async with self.bot.pool.acquire() as conn:
            conn: asqlite_Connection
            
            data = await conn.fetchone(
                """
                SELECT bank.job, COALESCE(cooldowns.until, 0.0)
                FROM bank
                LEFT JOIN cooldowns
                ON bank.userID = cooldowns.userID AND cooldowns.cooldown = $0
                WHERE bank.userID = $1
                """, "working", interaction.user.id
            )
            
            if data is None:
                return await interaction.response.send_message(embed=self.not_registered, ephemeral=True)

            job_name, current_cd = data
            if job_name == "None":
                return await interaction.response.send_message(
                    ephemeral=True,
                    embed=membed("You don't have a job, get one first.")
                )

            has_cd = await self.check_has_cd(
                conn, 
                user_id=interaction.user.id,
                until=current_cd
            )

            if isinstance(has_cd, tuple):
                return await interaction.response.send_message(
                    embed=membed(f"You can work again at {has_cd[0]} ({has_cd[1]}).")
                )

            async with conn.transaction():
                ncd = (discord.utils.utcnow() + datetime.timedelta(minutes=40)).timestamp()
                
                await self.update_cooldown(
                    conn, 
                    user_id=interaction.user.id, 
                    cooldown_type="working", 
                    new_cd=ncd
                )

        possible_minigames = choices((1, 2), k=1, weights=(80, 20))[0]
        method_name = {
            2: "do_order",
            1: "do_tiles"
        }.get(possible_minigames)

        method_name = getattr(self, method_name)
        await method_name(interaction, job_name)

    @work.command(name="apply", description="Apply for a job", extras={"exp_gained": 1})
    @app_commands.rename(chosen_job="job")
    @app_commands.describe(chosen_job='The job you want to apply for.')
    async def get_job(
        self, 
        interaction: discord.Interaction, 
        chosen_job: Literal['Plumber', 'Cashier', 'Fisher', 'Janitor', 'Youtuber', 'Police']
    ) -> None:

        async with self.bot.pool.acquire() as conn:
            conn: asqlite_Connection

            data = await conn.fetchone(
                """
                SELECT bank.job, COALESCE(cooldowns.until, 0.0)
                FROM bank
                LEFT JOIN cooldowns
                ON bank.userID = cooldowns.userID AND cooldowns.cooldown = $1
                WHERE bank.userID = $0
                """, "job_change", interaction.user.id
            )

            if data is None:
                return await interaction.response.send_message(
                    ephemeral=True,
                    embed=self.not_registered
                )

            has_cd = await self.check_has_cd(
                conn, 
                user_id=interaction.user.id,
                until=data[-1]
            )
            
            if isinstance(has_cd, tuple):
                embed = discord.Embed(
                    title="Cannot perform this action", 
                    description=f"You can change your job {has_cd[1]}.", 
                    colour=0x2B2D31
                )
                return await interaction.response.send_message(embed=embed, ephemeral=True)

            if data[0] != "None":
                return await interaction.response.send_message(
                    ephemeral=True,
                    embed=membed(
                        f"You are already working as a **{data[0]}**.\n"
                        "You'll have to resign first using /work resign."
                    )
                )

            ncd = (discord.utils.utcnow() + datetime.timedelta(days=2)).timestamp()
            async with conn.transaction():

                await self.update_cooldown(
                    conn, 
                    user_id=interaction.user.id, 
                    cooldown_type="job_change", 
                    new_cd=ncd
                )
                await self.change_job_new(interaction.user, conn, job_name=chosen_job)

            embed = membed("You can start working now for every 40 minutes.")
            embed.title = f"Congratulations, you are now working as a {chosen_job}"

            await interaction.response.send_message(embed=embed)
    
    @work.command(name="resign", description="Resign from your current job")
    async def job_resign(self, interaction: discord.Interaction) -> None:
        async with self.bot.pool.acquire() as conn:
            conn: asqlite_Connection

            data = await conn.fetchone(
                """
                SELECT bank.job, COALESCE(cooldowns.until, 0.0)
                FROM bank
                LEFT JOIN cooldowns
                ON bank.userID = cooldowns.userID AND cooldowns.cooldown = $1
                WHERE bank.userID = $0
                """, "job_change", interaction.user.id
            )

            if not data:
                return await interaction.response.send_message(
                    ephemeral=True, 
                    embed=self.not_registered
                )

            if data[0] == "None":
                return await interaction.response.send_message(
                    ephemeral=True,
                    embed=membed("You're already unemployed.")
                )

            has_cd = await self.check_has_cd(
                conn, 
                user_id=interaction.user.id, 
                until=data[-1]
            )
            
            if isinstance(has_cd, tuple):
                embed = discord.Embed(
                    title="Cannot perform this action", 
                    description=f"You can change your job {has_cd[1]}.", 
                    colour=0x2B2D31
                )

                return await interaction.response.send_message(embed=embed, ephemeral=True)

            value = await process_confirmation(
                interaction=interaction, 
                prompt=(
                    f"Are you sure you want to resign from your current job as a **{data[0]}**?\n"
                    "You won't be able to apply to another job for the next 48 hours."
                )
            )

            if value:
                ncd = (discord.utils.utcnow() + datetime.timedelta(days=2)).timestamp()
                
                await self.update_cooldown(
                    conn, 
                    user_id=interaction.user.id, 
                    cooldown_type="job_change", 
                    new_cd=ncd
                )

                await self.change_job_new(interaction.user, conn, job_name='None')
    
    @app_commands.command(name="balance", description="Get someone's balance. Wallet, bank, and net worth.")
    @app_commands.describe(user='The user to find the balance of.')
    @app_commands.guilds(*APP_GUILDS_IDS)
    async def find_balance(
        self, 
        interaction: discord.Interaction, 
        user: Optional[USER_ENTRY]
    ) -> None:

        user = user or interaction.user

        async with self.bot.pool.acquire() as conn:
            conn: asqlite_Connection
            not_registered = await self.can_call_out(user, conn)

            balance = membed()
            if not_registered:
                if interaction.user.id != user.id:
                    balance.description = f"{user.mention} is not registered."
                    return await interaction.response.send_message(ephemeral=True, embed=balance)

                await self.open_bank_new(user, conn)
                balance.colour = discord.Colour.green()

            nd = await conn.fetchone(
                """
                SELECT wallet, bank, bankspace 
                FROM `bank` 
                WHERE userID = $0
                """, user.id
            )

            bank = nd[0] + nd[1]
            inv = await self.calculate_inventory_value(user, conn)
            rank = await self.calculate_net_ranking_for(user, conn)
            space = (nd[1] / nd[2]) * 100

            balance.title = f"{user.display_name}'s Balances"
            balance.url = "https://dis.gd/support"
            balance.timestamp = discord.utils.utcnow()

            balance.add_field(name="Wallet", value=f"{CURRENCY} {nd[0]:,}")
            balance.add_field(name="Bank", value=f"{CURRENCY} {nd[1]:,}")
            balance.add_field(name="Bankspace", value=f"{CURRENCY} {nd[2]:,} ({space:.2f}% full)")
            balance.add_field(name="Money Net", value=f"{CURRENCY} {bank:,}")
            balance.add_field(name="Inventory Net", value=f"{CURRENCY} {inv:,}")
            balance.add_field(name="Total Net", value=f"{CURRENCY} {inv + bank:,}")

            balance.set_footer(text=f"Global Rank: #{rank}")

            view = BalanceView(
                interaction, 
                wallet=nd[0], 
                bank=nd[1], 
                bankspace=nd[2], 
                viewing=user
            )

            await interaction.response.send_message(embed=balance, view=view)

    async def do_weekly_or_monthly(
        self, 
        interaction: discord.Interaction, 
        recurring_income_type: str,
        weeks_away: int
    ) -> None:
        
        async with self.bot.pool.acquire() as conn:
            conn: asqlite_Connection

            multiplier = {
                "weekly": 10_000_000,
                "monthly": 100_000_000,
                "yearly": 1_000_000_000
            }.get(recurring_income_type)

            has_cd = await self.check_has_cd(
                conn, 
                user_id=interaction.user.id, 
                cd_type=recurring_income_type
            )
            noun_period = recurring_income_type[:-2]

            if isinstance(has_cd, tuple):
                return await interaction.response.send_message(
                    embed=membed(f"You already got your {recurring_income_type} robux this {noun_period}, try again {has_cd[1]}.")
                )
            
            next_cd = discord.utils.utcnow() + datetime.timedelta(weeks=weeks_away)
            async with conn.transaction():

                try:
                    await self.update_cooldown(
                        conn, 
                        user_id=interaction.user.id, 
                        cooldown_type=recurring_income_type, 
                        new_cd=next_cd.timestamp()
                    )

                except sqlite3.IntegrityError:
                    return await interaction.response.send_message(embed=self.not_registered)

                await self.update_bank_new(interaction.user, conn, multiplier)

            next_cd = discord.utils.format_dt(next_cd, style="R")    
            success = membed(
                f"You just got {CURRENCY} **{multiplier:,}** for checking in this {noun_period}.\n"
                f"See you next {noun_period} ({next_cd})!"
            )

            success.title = f"{interaction.user.display_name}'s {recurring_income_type.title()} Robux"
            success.url = "https://www.youtube.com/watch?v=ue_X8DskUN4"

            await interaction.response.send_message(embed=success)

    @app_commands.command(name="weekly", description="Get a weekly injection of robux")
    @app_commands.guilds(*APP_GUILDS_IDS)
    async def weekly(self, interaction: discord.Interaction) -> None:
        await self.do_weekly_or_monthly(interaction, "weekly", weeks_away=1)
    
    @app_commands.command(description="Get a monthly injection of robux")
    @app_commands.guilds(*APP_GUILDS_IDS)
    async def monthly(self, interaction: discord.Interaction) -> None:
        await self.do_weekly_or_monthly(interaction, "monthly", weeks_away=4)
    
    @app_commands.command(description="Get a yearly injection of robux")
    @app_commands.guilds(*APP_GUILDS_IDS)
    async def yearly(self, interaction: discord.Interaction) -> None:
        await self.do_weekly_or_monthly(interaction, "yearly", weeks_away=52)

    @app_commands.command(name="resetmydata", description="Opt out of the virtual economy, deleting all of your data")
    @app_commands.guilds(*APP_GUILDS_IDS)
    @app_commands.describe(member='The player to remove all of the data of. Defaults to the user calling the command.')
    async def discontinue_bot(self, interaction: discord.Interaction, member: Optional[USER_ENTRY]) -> None:
        """Opt out of the virtual economy and delete all of the user data associated."""
        
        member = member or interaction.user

        if member.id != interaction.user.id:
            if interaction.user.id not in self.bot.owner_ids:
                return await interaction.response.send_message(
                    ephemeral=True,
                    embed=membed("You are not allowed to do this.")
                )

        async with self.bot.pool.acquire() as conn:
            conn: asqlite_Connection

            if await self.can_call_out(member, conn):
                return await interaction.response.send_message(
                    ephemeral=True,
                    embed=membed(f"{member.mention} isn't registered.")
                )
            await self.declare_transaction(conn, user_id=member.id)

            view = ConfirmResetData(
                interaction=interaction, 
                user_to_remove=member
            )

            link = "https://www.youtube.com/shorts/vTrH4paRl90"            
            await interaction.response.send_message(
                view=view,
                embed=membed(
                    f"This command will reset **[EVERYTHING]({link})**.\n"
                    "Are you **SURE** you want to do this?\n\n"
                    "If you do, click `RESET MY DATA` **3** times."
                )
            )

    @app_commands.command(name="withdraw", description="Withdraw robux from your bank account")
    @app_commands.guilds(*APP_GUILDS_IDS)
    @app_commands.describe(robux=ROBUX_DESCRIPTION)
    async def withdraw(self, interaction: discord.Interaction, robux: str) -> None:
        """Withdraw a given amount of robux from your bank."""

        user = interaction.user
        actual_amount = await determine_exponent(
            interaction=interaction, 
            rinput=robux
        )

        if actual_amount is None:
            return

        async with self.bot.pool.acquire() as conn:
            conn: asqlite_Connection

            bank_amt = await conn.fetchone(
                """
                SELECT bank
                FROM bank
                WHERE userID = $0
                """, user.id
            )

            if bank_amt is None:
                return await interaction.response.send_message(embed=self.not_registered, ephemeral=True)
            bank_amt, = bank_amt

            query = (
                f"""
                UPDATE `{BANK_TABLE_NAME}`
                SET 
                    wallet = wallet + $0,
                    `bank` = `bank` - $0
                WHERE userID = $1
                RETURNING wallet, `bank`
                """
            )

            embed = membed()
            if isinstance(actual_amount, str):

                if not bank_amt:
                    embed.description = "You have nothing to withdraw."
                    return await interaction.response.send_message(embed=embed, ephemeral=True)

                new_data = await conn.fetchone(query, bank_amt, user.id)
                await conn.commit()
                wallet_new, bank_new = new_data

                embed.add_field(
                    name="<:withdraw:1195657655134470155> Withdrawn", 
                    value=f"{CURRENCY} {bank_amt:,}", 
                    inline=False
                )
                embed.add_field(name="Current Wallet Balance", value=f"{CURRENCY} {wallet_new:,}")
                embed.add_field(name="Current Bank Balance", value=f"{CURRENCY} {bank_new:,}")

                return await interaction.response.send_message(embed=embed)

            if actual_amount > bank_amt:
                embed.description = f"You only have {CURRENCY} **{bank_amt:,}** in your bank right now."
                return await interaction.response.send_message(embed=embed, ephemeral=True)

            new_data = await conn.fetchone(query, actual_amount, user.id)
            await conn.commit()
            wallet_new, bank_new = new_data

            embed.add_field(
                name="<:withdraw:1195657655134470155> Withdrawn", 
                value=f"{CURRENCY} {actual_amount:,}", 
                inline=False
            )
            
            embed.add_field(name="Current Wallet Balance", value=f"{CURRENCY} {wallet_new:,}")
            embed.add_field(name="Current Bank Balance", value=f"{CURRENCY} {bank_new:,}")

            await interaction.response.send_message(embed=embed)

    @app_commands.command(name='deposit', description="Deposit robux into your bank account")
    @app_commands.guilds(*APP_GUILDS_IDS)
    @app_commands.describe(robux=ROBUX_DESCRIPTION)
    async def deposit(self, interaction: discord.Interaction, robux: str) -> None:
        """Deposit an amount of robux into your bank."""

        user = interaction.user
        actual_amount = await determine_exponent(
            interaction=interaction, 
            rinput=robux
        )
        if actual_amount is None:
            return

        async with self.bot.pool.acquire() as conn:
            conn: asqlite_Connection

            details = await conn.fetchone(
                """
                SELECT wallet, bank, bankspace FROM `bank` WHERE userID = $0
                """, interaction.user.id
            )
            if details is None:
                return await interaction.response.send_message(embed=self.not_registered, ephemeral=True)
            
            wallet_amt, bank, bankspace = details

            available_bankspace = bankspace - bank
            embed = membed()
            
            if available_bankspace <= 0:
                embed.description = (
                    f"You can only hold **{CURRENCY} {details[2]:,}** in your bank right now.\n"
                    f"To hold more, use currency commands and level up more. Bank notes can aid with this."
                )
                return await interaction.response.send_message(embed=embed, ephemeral=True)
            
            query = (
                f"""
                UPDATE `{BANK_TABLE_NAME}`
                SET 
                    wallet = wallet - $0,
                    `bank` = `bank` + $0
                WHERE userID = $1
                RETURNING wallet, `bank`
                """
            )

            if isinstance(actual_amount, str):

                available_bankspace = min(wallet_amt, available_bankspace)
                
                if not available_bankspace:
                    embed.description = "You have nothing to deposit."
                    return await interaction.response.send_message(embed=embed, ephemeral=True)

                wallet_new, bank_new = await conn.fetchone(query, available_bankspace, user.id)
                await conn.commit()
                
                embed.add_field(
                    name="<:deposit:1195657772231036948> Deposited", 
                    value=f"{CURRENCY} {available_bankspace:,}", 
                    inline=False
                )

                embed.add_field(name="Current Wallet Balance", value=f"{CURRENCY} {wallet_new:,}")
                embed.add_field(name="Current Bank Balance", value=f"{CURRENCY} {bank_new:,}")

                return await interaction.response.send_message(embed=embed)

            available_bankspace -= actual_amount

            if actual_amount > wallet_amt:
                embed.description = f"You only have {CURRENCY} **{wallet_amt:,}** in your wallet right now."
                return await interaction.response.send_message(embed=embed, ephemeral=True)

            wallet_new, bank_new = await conn.fetchone(query, actual_amount, user.id)
            await conn.commit()

            embed.add_field(
                name="<:deposit:1195657772231036948> Deposited", 
                value=f"{CURRENCY} {actual_amount:,}", 
                inline=False
            )

            embed.add_field(name="Current Wallet Balance", value=f"{CURRENCY} {wallet_new:,}")
            embed.add_field(name="Current Bank Balance", value=f"{CURRENCY} {bank_new:,}")
            await interaction.response.send_message(embed=embed)

    @app_commands.command(name='leaderboard', description='Rank users based on various stats')
    @app_commands.guilds(*APP_GUILDS_IDS)
    @app_commands.describe(stat="The stat you want to see.")
    async def get_leaderboard(
        self, 
        interaction: discord.Interaction, 
        stat: Literal[
            "Money Net", 
            "Wallet", 
            "Bank", 
            "Inventory Net", 
            "Bounty", 
            "Commands", 
            "Level",
            "Net Worth"
        ]
    ) -> None:
        """View the leaderboard and filter the results based on different stats inputted."""

        lb_view = Leaderboard(interaction, their_choice=stat)
        lb = await self.create_leaderboard_preset(chosen_choice=stat)

        await interaction.response.send_message(embed=lb, view=lb_view)

    @app_commands.command(name='rob', description="Attempt to steal from someone's pocket", extras={"exp_gained": 4})
    @app_commands.guilds(*APP_GUILDS_IDS)
    @app_commands.rename(robbing="user")
    @app_commands.describe(robbing='The user you want to rob money from.')
    async def rob_the_user(self, interaction: discord.Interaction, robbing: discord.Member) -> None:
        """Rob someone else."""

        embed = membed()
        if interaction.user.id == robbing.id:
            embed.description = 'Seems pretty foolish to steal from yourself'
            return await interaction.response.send_message(embed=embed)
        elif robbing.bot:
            embed.description = 'You are not allowed to steal from bots, back off my kind'
            return await interaction.response.send_message(embed=embed)
        else:
            async with self.bot.pool.acquire() as conn:
                conn: asqlite_Connection

                if not (await self.can_call_out_either(interaction.user, robbing, conn)):
                    embed.description = f'Either you or {robbing.mention} are not registered.'
                    return await interaction.response.send_message(embed=embed, ephemeral=True)

                prim_d = await conn.fetchone(
                    """
                    SELECT wallet, job, bounty, settings.value
                    FROM `bank` 
                    LEFT JOIN settings 
                        ON bank.userID = settings.userID AND settings.setting = 'passive_mode'
                    WHERE bank.userID = $0
                    """, interaction.user.id
                )

                host_d = await conn.fetchone(
                    """
                    SELECT wallet, job, settings.value
                    FROM `bank`
                    LEFT JOIN settings 
                        ON bank.userID = settings.userID AND settings.setting = 'passive_mode' 
                    WHERE bank.userID = $0
                    """, robbing.id
                )

                if prim_d[-1]:
                    embed.description = "You are in passive mode! If you want to rob, turn that off!"
                    return await interaction.response.send_message(embed=embed)
                
                if host_d[-1]:
                    embed.description = f"{robbing.mention} is in passive mode, you can't rob them!"
                    return await interaction.response.send_message(embed=embed)

                if host_d[0] < 1_000_000:
                    embed.description = f"{robbing.mention} doesn't even have {CURRENCY} **1,000,000**, not worth it."
                    return await interaction.response.send_message(embed=embed)
                
                if prim_d[0] < 10_000_000:
                    embed.description = f"You need at least {CURRENCY} **10,000,000** in your wallet to rob someone."
                    return await interaction.response.send_message(embed=embed)

                result = choices((0, 1), weights=(49, 51), k=1)

                if not result[0]:
                    emote = choice(
                        (
                            "<a:kekRealize:970295657233539162>", "<:smhlol:1160157952410386513>", 
                            "<:z_HaH:783399959068016661>", "<:lmao:784308818418728972>", 
                            "<:lamaww:789865027007414293>", "<a:StoleThisEmote5:791327136296075327>", 
                            "<:jerryLOL:792239708364341258>", "<:dogkekw:797946573144850432>"
                        )
                    )
                    
                    fine = randint(1, prim_d[0])
                    embed.description = (
                        f'You were caught lol {emote}\n'
                        f'You paid {robbing.mention} {CURRENCY} **{fine:,}**.'
                    )

                    b = prim_d[-1]
                    if b:
                        fine += b
                        embed.description += (
                            "\n\n**Bounty Status:**\n"
                            f"{robbing.mention} was also given your bounty of **{CURRENCY} {b:,}**."
                        )

                    await self.update_wallet_many(
                        conn, 
                        (fine, robbing.id), 
                        (-fine, interaction.user.id)
                    )
                    await conn.commit()

                    return await interaction.response.send_message(embed=embed)

                amt_stolen = randint(1_000_000, host_d[0])
                amt_dropped = floor((25 / 100) * amt_stolen)
                total = amt_stolen - amt_dropped
                percent_stolen = int((total/amt_stolen) * 100)
                
                await self.update_wallet_many(
                    conn, 
                    (-amt_stolen, robbing.id), 
                    (total, interaction.user.id)
                )
                await conn.commit()
                
                if percent_stolen <= 25:
                    embed.title = "You stole a TINY portion!"
                    embed.set_thumbnail(url="https://i.imgur.com/nZmHhJX.png")
                elif percent_stolen <= 50:
                    embed.title = "You stole a small portion!"
                    embed.set_thumbnail(url="https://i.imgur.com/148ClcS.png")
                elif percent_stolen <= 75:
                    embed.title = "You stole a fairly decent chunk!"
                    embed.set_thumbnail(url="https://i.imgur.com/eNIT8qw.png")
                else:
                    embed.title = "You stole BASICALLY EVERYTHING YOU POSSIBLY COULD!"
                    embed.set_thumbnail(url="https://i.imgur.com/jY3PzTv.png")
                
                embed.description = (
                    f"**You managed to get:**\n"
                    f"{CURRENCY} {amt_stolen:,} (but dropped {CURRENCY} {amt_dropped:,} while escaping)"
                )

                embed.set_footer(text=f"You stole {CURRENCY} {total:,} in total")
                await interaction.response.send_message(embed=embed)

    @app_commands.command(name='bankrob', description="Gather people to rob someone's bank")
    @app_commands.guilds(*APP_GUILDS_IDS)
    @app_commands.describe(user='The user to attempt to bankrob.')
    async def bankrob_the_user(self, interaction: discord.Interaction, user: discord.Member) -> None:
        """Rob someone else's bank."""
        starter_id = interaction.user.id
        user_id = user.id

        if user_id == starter_id:
            return await interaction.response.send_message(embed=membed("You can't bankrob yourself."))
        if user.bot:
            return await interaction.response.send_message(embed=membed("You can't bankrob bots."))
        
        return await interaction.response.send_message(embed=membed("This command is under construction."))

    @app_commands.command(name='coinflip', description='Bet your robux on a coin flip', extras={"exp_gained": 3})
    @app_commands.guilds(*APP_GUILDS_IDS)
    @app_commands.describe(
        side='The side of the coin you bet it will flip on.', 
        robux=ROBUX_DESCRIPTION
    )
    async def coinflip(self, interaction: discord.Interaction, side: str, robux: str) -> None:
        """Flip a coin and make a bet on what side of the coin it flips to."""

        user = interaction.user
        bet_on = "heads" if "h" in side.lower() else "tails"
        
        async with interaction.client.pool.acquire() as conn:
            conn: asqlite_Connection
            
            wallet_amt = await conn.fetchone(
                """
                SELECT wallet
                FROM bank
                WHERE userID = $0
                """, user.id
            )

            if wallet_amt is None:
                return await interaction.response.send_message(embed=self.not_registered, ephemeral=True)
            wallet_amt, = wallet_amt

            has_keycard = await self.user_has_item_from_id(
                user_id=user.id,
                item_id=1,
                conn=conn
            )
            
            amount = await self.do_wallet_checks(
                interaction=interaction,
                wallet_amount=wallet_amt,
                exponent_amount=robux,
                has_keycard=has_keycard
            )

            if amount is None:
                return
            
            result = choice(("heads", "tails"))
            embed = discord.Embed()

            if result != bet_on:
                embed.set_author(
                    icon_url=user.display_avatar.url, 
                    name=f"{user.name}'s losing coinflip game"
                )
                embed.colour = discord.Colour.brand_red()

                namount, = await self.update_bank_new(user, conn, -amount)
                await conn.commit()

                embed.description = (
                    f"**You lost.** The coin landed on {result}.\n"
                    f"You lost {CURRENCY} **{amount:,}**.\n"
                    f"You now have {CURRENCY} **{namount:,}**."
                )

                return await interaction.response.send_message(embed=embed)
            
            their_multi = await self.get_multi_of(
                user_id=user.id,
                multi_type="robux",
                conn=conn
            )

            embed.set_author(
                icon_url=user.display_avatar.url, 
                name=f"{user.name}'s winning coinflip game"
            )
            embed.colour = discord.Colour.brand_green()

            embed.set_footer(text=f"Multiplier: {their_multi}%")
            
            amount = add_multi_to_original(multi=their_multi, original=amount)
            namount, = await self.update_bank_new(user, conn, +amount)
            await conn.commit()

            embed.description = (
                f"**You won!** The coin landed on the side you bet on.\n"
                f"You won {CURRENCY} **{amount:,}**.\n"
                f"You now have {CURRENCY} **{namount:,}**."
            )

            await interaction.response.send_message(embed=embed)

    @app_commands.command(name="blackjack", description="Test your skills at blackjack", extras={"exp_gained": 3})
    @app_commands.guilds(*APP_GUILDS_IDS)
    @app_commands.describe(robux=ROBUX_DESCRIPTION)
    async def play_blackjack(self, interaction: discord.Interaction, robux: str) -> None:
        """Play a round of blackjack with the bot. Win by reaching 21 or a score higher than the bot without busting."""

        # ------ Check the user is registered or already has an ongoing game ---------

        async with self.bot.pool.acquire() as conn:
            conn: asqlite_Connection
        
        wallet_amt = await conn.fetchone(
            """
            SELECT wallet
            FROM bank
            WHERE userID = $0
            """, interaction.user.id
        )

        if wallet_amt is None:
            return await interaction.response.send_message(embed=self.not_registered, ephemeral=True)
        
        wallet_amt, = wallet_amt
        has_keycard = await self.user_has_item_from_id(interaction.user.id, item_id=1, conn=conn)

        # ----------- Check what the bet amount is, converting where necessary -----------

        namount = await self.do_wallet_checks(
            interaction=interaction, 
            has_keycard=has_keycard,
            wallet_amount=wallet_amt,
            exponent_amount=robux
        )
        
        if namount is None:
            return

        # ----------------- Game setup ---------------------------------

        deck = [2, 3, 4, 5, 6, 7, 8, 9, 10, 10, 10, 10, 11] * 4
        shuffle(deck)

        player_hand = [deck.pop(), deck.pop()]
        dealer_hand = [deck.pop(), deck.pop()]

        # ------------ In the case where the user already won --------------
        player_sum = calculate_hand(player_hand)
        dealer_sum = calculate_hand(dealer_hand)

        if player_sum == 21:
            new_multi = await Economy.get_multi_of(user_id=interaction.user.id, multi_type="robux", conn=conn)
            amount_after_multi = add_multi_to_original(multi=new_multi, original=namount)

            new_bj_win, bj_lose, new_amount_balance = await conn.fetchone(
                f"""
                UPDATE `{BANK_TABLE_NAME}` 
                SET 
                    bjw = bjw + 1,
                    wallet = wallet + $0 
                WHERE userID = $1 
                RETURNING bjw, bjl, wallet
                """, amount_after_multi, interaction.user.id,
            )

            prctnw = (new_bj_win / (new_bj_win + bj_lose)) * 100
            await conn.commit()

            d_fver_p = display_user_friendly_deck_format(player_hand)
            d_fver_d = display_user_friendly_deck_format(dealer_hand)

            winner = discord.Embed(colour=discord.Colour.brand_green())
            winner.description = (
                f"**Blackjack! You've already won with a total of {player_sum}!**\n"
                f"You won {CURRENCY} **{amount_after_multi:,}**. "
                f"You now have {CURRENCY} **{new_amount_balance:,}**.\n"
                f"You won {prctnw:.2f}% of the games."
            )
            
            winner.add_field(
                name=f"{interaction.user.name} (Player)", 
                value=(
                    f"**Cards** - {d_fver_p}\n"
                    f"**Total** - `{player_sum}`"
                )
            )
            
            winner.add_field(
                name=f"{self.bot.user.name} (Dealer)", 
                value=(
                    f"**Cards** - {d_fver_d}\n"
                    f"**Total** - `{dealer_sum}`"
                )
            )
            
            winner.set_author(
                name=f"{interaction.user.name}'s winning blackjack game", 
                icon_url=interaction.user.display_avatar.url
            )

            winner.set_footer(text=f"Multiplier: {new_multi:,}%")
            
            return await interaction.response.send_message(embed=winner)


        await self.declare_transaction(conn, user_id=interaction.user.id)
        shallow_pv = [display_user_friendly_card_format(number) for number in player_hand]
        shallow_dv = [display_user_friendly_card_format(number) for number in dealer_hand]

        self.bot.games[interaction.user.id] = (deck, player_hand, dealer_hand, shallow_dv, shallow_pv, namount)

        initial = membed(
            f"The game has started. May the best win.\n"
            f"`{CURRENCY} ~{format_number_short(namount)}` is up for grabs on the table."
        )
        
        initial.add_field(
            name=f"{interaction.user.name} (Player)", 
            value=f"**Cards** - {' '.join(shallow_pv)}\n**Total** - `{player_sum}`"
        )
        
        initial.add_field(
            name=f"{self.bot.user.name} (Dealer)", 
            value=f"**Cards** - {shallow_dv[0]} `?`\n**Total** - ` ? `"
        )
        
        initial.set_author(icon_url=interaction.user.display_avatar.url, name=f"{interaction.user.name}'s blackjack game")
        initial.set_footer(text="K, Q, J = 10  |  A = 1 or 11")
        
        await interaction.response.send_message(
            embed=initial, 
            view=BlackjackUi(interaction=interaction)
        )

    async def do_wallet_checks(
        self, 
        interaction: discord.Interaction,  
        wallet_amount: int, 
        exponent_amount : Union[str, int],
        has_keycard: Optional[bool] = False
    ) -> Union[int, None]:
        """Reusable wallet checks that are common amongst most gambling commands."""

        expo = await determine_exponent(
            interaction=interaction, 
            rinput=exponent_amount
        )
        
        if expo is None:
            return

        try:
            assert isinstance(expo, (int, float))
            amount = expo
        except AssertionError:
            if has_keycard:
                amount = min(MAX_BET_KEYCARD, wallet_amount)
            else:
                amount = min(MAX_BET_WITHOUT, wallet_amount)

        if amount > wallet_amount:
            return await interaction.response.send_message(
                ephemeral=True,
                embed=membed("You are too poor for this bet.")
            )

        if has_keycard:
            if (amount < MIN_BET_KEYCARD) or (amount > MAX_BET_KEYCARD):
                return await interaction.response.send_message(
                    ephemeral=True,
                    embed=membed(
                        f"You can't bet less than {CURRENCY} **{MIN_BET_KEYCARD:,}**.\n"
                        f"You also can't bet anything more than {CURRENCY} **{MAX_BET_KEYCARD:,}**."
                    )
                )
        else:
            if (amount < MIN_BET_WITHOUT) or (amount > MAX_BET_WITHOUT):
                return await interaction.response.send_message(
                    ephemeral=True,
                    embed=membed(
                        f"You can't bet less than {CURRENCY} **{MIN_BET_WITHOUT:,}**.\n"
                        f"You also can't bet anything more than {CURRENCY} **{MAX_BET_WITHOUT:,}**.\n"
                        f"These values can increase when you acquire a <:lanyard:1165935243140796487> Keycard."
                    )
                )
        return amount

    @app_commands.command(name="bet", description="Bet your robux on a dice roll", extras={"exp_gained": 3})
    @app_commands.guilds(*APP_GUILDS_IDS)
    @app_commands.describe(robux=ROBUX_DESCRIPTION)
    async def bet(self, interaction: discord.Interaction, robux: str) -> None:
        """Bet your robux on a gamble to win or lose robux."""

        # --------------- Contains checks before betting i.e. has keycard, meets bet constraints. -------------
        async with self.bot.pool.acquire() as conn:
            conn: asqlite_Connection

            data = await conn.fetchone(
                f"""
                SELECT wallet, betw, betl
                FROM `{BANK_TABLE_NAME}` 
                WHERE userID = $0
                """, interaction.user.id
            )

            if data is None:
                return await interaction.response.send_message(embed=self.not_registered, ephemeral=True)
            wallet_amt, id_won_amount, id_lose_amount = data

            pmulti = await Economy.get_multi_of(user_id=interaction.user.id, multi_type="robux", conn=conn)
            has_keycard = await self.user_has_item_from_id(interaction.user.id, item_id=1, conn=conn)

            robux = await self.do_wallet_checks(
                interaction=interaction, 
                has_keycard=has_keycard,
                wallet_amount=wallet_amt,
                exponent_amount=robux
            )
            
            if robux is None:
                return
            
            # --------------------------------------------------------
            badges = set()

            if has_keycard:
                badges.add("<:lanyard:1165935243140796487>")
                
                their_roll, = choices(
                    population=(1, 2, 3, 4, 5, 6), 
                    weights=[37 / 3, 37 / 3, 37 / 3, 63 / 3, 63 / 3, 63 / 3]
                )

                bot_roll, = choices(
                    population=(1, 2, 3, 4, 5, 6), 
                    weights=(65 / 4, 65 / 4, 65 / 4, 65 / 4, 35 / 2, 35 / 2)
                )

            else:
                their_roll, = choices(
                    population=(1, 2, 3, 4, 5, 6), 
                    weights=(10, 10, 15, 27, 15, 23)
                )
                
                bot_roll, = choices(
                    population=(1, 2, 3, 4, 5, 6), 
                    weights=(55 / 3, 55 / 3, 55 / 3, 45 / 3, 45 / 3, 45 / 3)
                )
            
            embed = discord.Embed()

            if their_roll > bot_roll:
                amount_after_multi = add_multi_to_original(multi=pmulti, original=robux)
                updated = await self.update_bank_three_new(
                    interaction.user, 
                    conn, 
                    "betwa", amount_after_multi,
                    "betw", 1, 
                    "wallet", amount_after_multi
                )
                await conn.commit()

                prcntw = (updated[1] / (id_lose_amount + updated[1])) * 100

                embed.colour = discord.Color.brand_green()
                embed.description=(
                    f"**You've rolled higher!**\n"
                    f"You won {CURRENCY} **{amount_after_multi:,}**.\n"
                    f"You now have {CURRENCY} **{updated[2]:,}**.\n"
                    f"You've won {prcntw:.1f}% of all games."
                )

                embed.set_author(
                    name=f"{interaction.user.name}'s winning gambling game", 
                    icon_url=interaction.user.display_avatar.url
                )
                embed.set_footer(text=f"Multiplier: {pmulti:,}%")

            elif their_roll == bot_roll:
                embed.colour = discord.Color.yellow()
                embed.description = "**Tie.** You lost nothing nor gained anything!"

                embed.set_author(
                    name=f"{interaction.user.name}'s gambling game", 
                    icon_url=interaction.user.display_avatar.url
                )

            else:
                updated = await self.update_bank_three_new(
                    interaction.user, 
                    conn, 
                    "betla", robux,
                    "betl", 1, 
                    "wallet", -robux
                )
                await conn.commit()

                new_total = id_won_amount + updated[1]
                prcntl = (updated[1] / new_total) * 100

                embed.colour = discord.Color.brand_red()
                embed.description=(
                    f"**You've rolled lower!**\n"
                    f"You lost {CURRENCY} **{robux:,}**.\n"
                    f"You now have {CURRENCY} **{updated[2]:,}**.\n"
                    f"You've lost {prcntl:.1f}% of all games."
                )

                embed.set_author(
                    name=f"{interaction.user.name}'s losing gambling game", 
                    icon_url=interaction.user.display_avatar.url
                )

            embed.add_field(name=interaction.user.name, value=f"Rolled `{their_roll}` {''.join(badges)}")
            embed.add_field(name=self.bot.user.name, value=f"Rolled `{bot_roll}`")

            await interaction.response.send_message(embed=embed)

    @sell.autocomplete('item')
    @use_item.autocomplete('item')
    @share_items.autocomplete('item')
    @trade_items_for_coins.autocomplete('item')
    @trade_items_for_items.autocomplete('item')
    async def owned_items_lookup(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        
        async with self.bot.pool.acquire() as conn:
            options = await conn.fetchall(
                """
                SELECT shop.itemName, inventory.qty
                FROM shop
                INNER JOIN inventory ON shop.itemID = inventory.itemID
                WHERE inventory.userID = $0
                """, interaction.user.id
            )

            return [app_commands.Choice(name=option[0], value=option[0]) for option in options if current.lower() in option[0].lower()]

    @add_showcase_item.autocomplete('item')
    async def owned_not_in_showcase_lookup(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        
        async with self.bot.pool.acquire() as conn:
            options = await conn.fetchall(
                """
                SELECT shop.itemName
                FROM shop
                INNER JOIN inventory ON shop.itemID = inventory.itemID
                LEFT JOIN showcase ON shop.itemID = showcase.itemID AND showcase.userID = $0
                WHERE inventory.userID = $0 AND showcase.itemID IS NULL
                """, interaction.user.id
            )

            return [app_commands.Choice(name=option[0], value=option[0]) for option in options if current.lower() in option[0].lower()]

    @remove_showcase_item.autocomplete('item')
    async def showcase_items_lookup(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        async with self.bot.pool.acquire() as conn:
            conn: asqlite_Connection

            options = await conn.fetchall(
                """
                SELECT itemName
                FROM shop
                INNER JOIN showcase ON shop.itemID = showcase.itemID
                WHERE showcase.userID = $0
                ORDER BY showcase.itemPos DESC
                """, interaction.user.id
            )

            return [app_commands.Choice(name=option[0], value=option[0]) for option in options if current.lower() in option[0].lower()]

    @item.autocomplete('item_name')
    @trade_coins_for_items.autocomplete('for_item')
    @trade_items_for_items.autocomplete('for_item')
    async def item_lookup(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        async with interaction.client.pool.acquire() as conn:
            res = await conn.fetchall("SELECT itemName FROM shop")
            return [
                app_commands.Choice(name=iterable[0], value=iterable[0]) 
                for iterable in res if current.lower() in iterable[0].lower()
            ]
    
    @view_user_settings.autocomplete('setting')
    async def setting_lookup(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        
        async with interaction.client.pool.acquire() as conn:
            query = "SELECT setting FROM settings_descriptions"
            res = await conn.fetchall(query)
        
        return [
            app_commands.Choice(name=" ".join(iterable[0].split("_")).title(), value=iterable[0])
            for iterable in res if current.lower() in iterable[0].lower()
        ]


async def setup(bot: commands.Bot) -> None:
    """Setup function to initiate the cog."""
    await bot.add_cog(Economy(bot))
