import sqlite3
from datetime import datetime, timedelta, timezone
from re import search
from asyncio import sleep
from textwrap import dedent
from math import floor, ceil
from dataclasses import dataclass
from string import ascii_letters, digits

from random import (
    choice, 
    choices, 
    randint, 
    sample, 
    shuffle
)

from typing import (
    Any,
    Callable,
    Coroutine, 
    Literal, 
    List
)

import discord
import aiofiles
from discord.ext import commands, tasks
from discord import app_commands
from asqlite import ProxiedConnection as asqlite_Connection

from .core.helpers import (
    determine_exponent, 
    economy_check,
    membed,
    respond
)

from .core.paginator import (
    PaginationItem, 
    RefreshPagination
)

from .core.views import process_confirmation
from .core.constants import CURRENCY

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
        expiry_time = datetime.fromtimestamp(multiplier[2], tz=timezone.utc)
        expiry_time = discord.utils.format_dt(expiry_time, style="R")
        description += f" (expires {expiry_time})"
    return description


def selling_price_algo(base_price: int, multiplier: int) -> int:
    """Calculate the selling price of an item based on its rarity and base price."""
    return round(int(base_price * (1+multiplier/100)), -2)


"""ALL VARIABLES AND CONSTANTS FOR THE ECONOMY ENVIRONMENT"""
CONTEXT_AND_INSTALL = {"guilds": True}
USER_ENTRY = discord.Member | discord.User
MULTIPLIER_TYPES = Literal["xp", "luck", "robux"]
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
UNIQUE_BADGES = {
    992152414566232139: " <:staffMember:1263921583949480047>",
    546086191414509599: " <:devilAdvocate:1263921422166786179>",
    1134123734421217412: " <:goldBugHunter:1263921864963653662>",
    1154092136115994687: " <:bugHunter:1263920006392188968>",
    1047572530422108311: " <:c2cAvatar:1263920021063733451>",
    1148206353647669298: " <:staffMember:1263921583949480047>",
    10: " (MAX)"
}
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
NOT_REGISTERED = membed("This user is not registered, so you can't use this command on them.")
SLOTS = ('🔥', '😳', '🌟', '💔', '🖕', '🤡', '🍕', '🍆', '🍑')
BONUS_MULTIPLIERS = {
    "🍕🍕": 30,
    "🤡🤡": 60,
    "🌟🌟": 80,
    "💔💔": 90,
    "🍑🍑": 100,
    "🖕🖕": 120,
    "🍆🍆": 130,
    "😳😳": 110,
    "🔥🔥": 140,
    "💔💔💔": 150,
    "🖕🖕🖕": 300,
    "🤡🤡🤡": 350,
    "🍕🍕🍕": 400,
    "🍆🍆🍆": 450,
    "🍑🍑🍑": 500,
    "😳😳😳": 550,
    "🌟🌟🌟": 600,
    "🔥🔥🔥": 900
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
    1: "<:irn:1263922000049471650>",
    2: "<:iirn:1263921924082368665>",
    3: "<:iiirn:1263921904675323914>",
    4: "<:ivrn:1263922020232728667>",
    5: "<:vrn:1263924189178499126>",
    6: "<:virn:1263924087214837801>",
    7: "<:viirn:1263924064553013369>",
    8: "<:viiirn:1263924020395376682>",
    9: "<:ixrn:1263922037018202112>",
    10: "<:xrn:1263924236242780171>",
    11: "<:Xrne:1263924252470415476>"
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

    weights = (800, 1000, 800, 100, 900, 800, 1000, 800, 800)

    slot_combination = ''.join(choices(SLOTS, weights=weights, k=3))
    return slot_combination


def find_slot_matches(*args) -> None | int:
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


def generate_progress_bar(percentage: float | int) -> str:
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
        0: "<:pb1e:1263922730588311582><:pb2e:1263922807293612042>"
           "<:pb2e:1263922807293612042><:pb2e:1263922807293612042><:pb3e:1263922895969583105>",
        10: "<:pb1hf:1263922784124539053><:pb2e:1263922807293612042>"
            "<:pb2e:1263922807293612042><:pb2e:1263922807293612042><:pb3e:1263922895969583105>",
        20: "<:pb1f:1263922756727341171><:pb2e:1263922807293612042>"
            "<:pb2e:1263922807293612042><:pb2e:1263922807293612042><:pb3e:1263922895969583105>",
        30: "<:pb1f:1263922756727341171><:pb2hf:1263922865707946036>"
            "<:pb2e:1263922807293612042><:pb2e:1263922807293612042><:pb3e:1263922895969583105>",
        40: "<:pb1f:1263922756727341171><:pb2f:1263922838239182991>"
            "<:pb2e:1263922807293612042><:pb2e:1263922807293612042><:pb3e:1263922895969583105>",
        50: "<:pb1f:1263922756727341171><:pb2f:1263922838239182991>"
            "<:pb2hf:1263922865707946036><:pb2e:1263922807293612042><:pb3e:1263922895969583105>",
        60: "<:pb1f:1263922756727341171><:pb2f:1263922838239182991>"
            "<:pb2f:1263922838239182991><:pb2e:1263922807293612042><:pb3e:1263922895969583105>",
        70: "<:pb1f:1263922756727341171><:pb2f:1263922838239182991>"
            "<:pb2f:1263922838239182991><:pb2hf:1263922865707946036><:pb3e:1263922895969583105>",
        80: "<:pb1f:1263922756727341171><:pb2f:1263922838239182991>"
            "<:pb2f:1263922838239182991><:pb2f:1263922838239182991><:pb3e:1263922895969583105>",
        90: "<:pb1f:1263922756727341171><:pb2f:1263922838239182991>"
            "<:pb2f:1263922838239182991><:pb2f:1263922838239182991><:pb3hf:1263922944829292577>",
        100: "<:pb1f:1263922756727341171><:pb2f:1263922838239182991>"
            "<:pb2f:1263922838239182991><:pb2f:1263922838239182991><:pb3f:1263922923060727838>"

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
        SELECT CAST(TOTAL(cmd_count) AS INTEGER) 
        FROM command_uses
        WHERE userID = $0
        """, user_id
    )

    return total[0]


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

    fav = fav or "-"
    return fav[0]


class DepositOrWithdraw(discord.ui.Modal):
    bigarg_response = {
        "Withdraw": "You don't have that much money in your bank.",
        "Deposit": (
            "Either one (or both) of the following is true:\n" 
            "1. You only have don't have that much money in your wallet.\n"
            "2. You don't have enough bankspace to deposit that amount."
        )
    }

    def __init__(
        self, 
        *, 
        title: str, 
        default_val: int,
        view: "BalanceView"
    ) -> None:

        self.their_default = default_val
        self.view = view
        self.amount.default = f"{self.their_default:,}"
        super().__init__(title=title, timeout=120.0)

    amount = discord.ui.TextInput(
        label="Amount", 
        min_length=1, 
        max_length=30, 
        placeholder="A constant number or an exponent (e.g., 1e6, 1234)"
    )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        val = await determine_exponent(interaction, rinput=self.amount.value)
        if val is None:
            return
        val = int(val)

        if val > self.their_default:
            return await interaction.response.send_message(
                ephemeral=True,
                delete_after=5.0,
                embed=membed(self.bigarg_response[self.title])
            )

        if self.title == "Withdraw":
            val = -val

        wallet, bank, bankspace = await self.update_account(interaction, val)
        await self.update_embed(interaction, wallet, bank, bankspace)

    async def update_account(self, interaction: discord.Interaction, val: int) -> tuple:
        async with interaction.client.pool.acquire() as conn:

            # ! flip the value of val if it is a withdrawal 
            wallet, bank, bankspace = await conn.fetchone(
                """
                UPDATE accounts 
                SET 
                    bank = bank + $0, 
                    wallet = wallet - $0 
                WHERE userID = $1 
                RETURNING wallet, bank, bankspace
                """, val, interaction.user.id
            )
            await conn.commit()
        return wallet, bank, bankspace

    async def update_embed(
        self, 
        interaction: discord.Interaction, 
        wallet: int, 
        bank: int, 
        bankspace: int
    ) -> None:
        prcnt_full = (bank / bankspace) * 100

        embed = interaction.message.embeds[0]
        embed.set_field_at(0, name="Wallet", value=f"{CURRENCY} {wallet:,}")
        embed.set_field_at(1, name="Bank", value=f"{CURRENCY} {bank:,}")
        embed.set_field_at(2, name="Bankspace", value=f"{CURRENCY} {bankspace:,} ({prcnt_full:.2f}% full)")
        embed.timestamp = discord.utils.utcnow()

        self.view.checks(bank, wallet, bankspace-bank)
        await interaction.response.edit_message(embed=embed, view=self.view)

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        if isinstance(error, (ValueError, TypeError)):
            return await interaction.response.send_message(
                delete_after=5.0, 
                ephemeral=True,
                embed=membed(f"You need to provide a real amount to {self.title.lower()}.")
            )

        await interaction.response.send_message(embed=membed("Something went wrong. Try again later."))
        await super().on_error(interaction, error)


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
        except discord.HTTPException:
            pass
        finally:
            async with self.interaction.client.pool.acquire() as conn:
                await Economy.end_transaction(conn, user_id=self.interaction.user.id)

    @discord.ui.button(label='RESET MY DATA', style=discord.ButtonStyle.danger, emoji=discord.PartialEmoji.from_str("<:rooFire:1263923362154156103>"))
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
                await conn.execute("DELETE FROM accounts WHERE userID = $0", self.removing_user.id)
            except Exception as e:
                interaction.client.log_exception(e)

                await tr.rollback()

                return await interaction.response.send_message(
                    embed=membed(
                        "Failed to wipe user data.\n"
                        "Report this to the developers so they can get it fixed."
                    )
                )

            await tr.commit()

        whose = "your" if interaction.user.id == self.removing_user.id else f"{self.removing_user.mention}'s"
        end_note = " Thanks for using the bot." if whose == "your" else ""

        await interaction.response.send_message(
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
        except discord.HTTPException:
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
        except discord.HTTPException:
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

    def __init__(self, interaction: discord.Interaction, viewing: USER_ENTRY) -> None:

        self.interaction = interaction
        self.viewing = viewing
        super().__init__(timeout=120.0)
        self.children[2].default_values = [discord.Object(id=self.viewing.id)]

    async def fetch_balance(self, interaction: discord.Interaction) -> discord.Embed:
        """
        Fetch the user's balance, format it into an embed. 

        A connection needs to be supplied to the class instance in order for this to work.
        """

        balance = membed()
        balance.url = "https://dis.gd/support"
        balance.title = f"{self.viewing.display_name}'s Balances"
        balance.timestamp = discord.utils.utcnow()

        async with interaction.client.pool.acquire() as conn:
            query = (
                """
                SELECT wallet, bank, bankspace 
                FROM accounts 
                WHERE userID = $0
                """
            )

            nd = await conn.fetchone(query, self.viewing.id)
            if nd is None:
                if interaction.user.id != self.viewing.id:
                    balance.description = "This user is not registered."
                    self.children[0].disabled, self.children[1].disabled = True, True
                    return balance

                await Economy.open_bank_new(self.viewing, conn)
                nd = await conn.fetchone(query, self.viewing.id)

            inv = await Economy.calculate_inventory_value(self.viewing, conn)
            rank = await Economy.calculate_net_ranking_for(self.viewing, conn)

        wallet, bank, bankspace = nd
        del nd

        space = (bank / bankspace) * 100
        money = wallet + bank

        balance.add_field(name="Wallet", value=f"{CURRENCY} {wallet:,}")
        balance.add_field(name="Bank", value=f"{CURRENCY} {bank:,}")
        balance.add_field(name="Bankspace", value=f"{CURRENCY} {bankspace:,} ({space:.2f}% full)")
        balance.add_field(name="Money Net", value=f"{CURRENCY} {money:,}")
        balance.add_field(name="Inventory Net", value=f"{CURRENCY} {inv:,}")
        balance.add_field(name="Total Net", value=f"{CURRENCY} {inv+money:,}")

        balance.set_footer(text=f"Global Rank: #{rank}")
        self.checks(bank, wallet, bankspace-bank)
        return balance

    def checks(self, current_bank, current_wallet, current_bankspace_left) -> None:
        """Check if the buttons should be disabled or not."""
        if self.viewing.id != self.interaction.user.id:
            self.children[0].disabled, self.children[1].disabled = True, True
            return

        self.children[0].disabled = (current_bank == 0)
        self.children[1].disabled = (current_wallet == 0) or (current_bankspace_left == 0)

    @staticmethod
    async def send_failure(interaction: discord.Interaction) -> None:
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

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        #! Check it's the author of the original interaction running this

        value = await economy_check(interaction, self.interaction.user)
        if not value:
            return False
        del value

        #! Check if they're already in a transaction
        #! Check if they exist in the database
        #! Ensure connections are carried into item callbacks when prerequisites are met

        async with interaction.client.pool.acquire() as conn:
            query = "SELECT EXISTS (SELECT 1 FROM transactions WHERE userID = $0)"
            in_tr, = await conn.fetchone(query, interaction.user.id)
            if in_tr:
                await self.send_failure(interaction)
            return not in_tr

    async def on_timeout(self) -> Coroutine[Any, Any, None]:
        for item in self.children:
            item.disabled = True
        try:
            await self.interaction.edit_original_response(view=self)
        except discord.HTTPException:
            pass

    @discord.ui.button(label="Withdraw", disabled=True, row=1)
    async def withdraw_money_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Withdraw money from the bank."""

        async with interaction.client.pool.acquire() as conn:
            bank_amt = await Economy.get_spec_bank_data(interaction.user, "bank", conn)

        if not bank_amt:
            return await interaction.response.send_message(
                embed=membed("You have nothing to withdraw."), 
                ephemeral=True, 
                delete_after=3.0
            )

        await interaction.response.send_modal(
            DepositOrWithdraw(title=button.label, default_val=bank_amt, view=self)
        )

    @discord.ui.button(label="Deposit", disabled=True, row=1)
    async def deposit_money_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Deposit money into the bank."""

        async with interaction.client.pool.acquire() as conn:
            wallet, bank, bankspace = await conn.fetchone(
                """
                SELECT wallet, bank, bankspace 
                FROM accounts 
                WHERE userID = $0
                """, interaction.user.id
            )

        if not wallet:
            return await interaction.response.send_message(
                ephemeral=True, 
                delete_after=3.0,
                embed=membed("You have nothing to deposit.")
            )

        available_bankspace = bankspace - bank
        if not available_bankspace:
            return await interaction.response.send_message(
                ephemeral=True, 
                delete_after=5.0,
                embed=membed(
                    f"You can only hold {CURRENCY} **{bankspace:,}** in your bank right now.\n"
                    "To hold more, use currency commands and level up more."
                )
            )

        available_bankspace = min(wallet, available_bankspace)
        await interaction.response.send_modal(
            DepositOrWithdraw(title=button.label, default_val=available_bankspace, view=self)
        )

    @discord.ui.select(cls=discord.ui.UserSelect, placeholder="Select a registered user", row=0)
    async def select_user_balance(self, interaction: discord.Interaction, select: discord.ui.UserSelect):
        self.viewing = select.values[0]
        select.default_values = [discord.Object(id=self.viewing.id)]

        balance = await self.fetch_balance(interaction)
        await interaction.response.edit_message(embed=balance, view=self)

    @discord.ui.button(emoji="<:refreshPages:1263923160433168414>", row=1)
    async def refresh_balance(self, interaction: discord.Interaction, _: discord.ui.Button):
        """Refresh the current message to display the user's latest balance."""
        balance = await self.fetch_balance(interaction)
        await interaction.response.edit_message(embed=balance, view=self)

    @discord.ui.button(emoji="<:terminatePages:1263923664433319957>", row=1)
    async def close_view(self, interaction: discord.Interaction, _: discord.ui.Button):
        """Close the balance view."""
        self.stop()
        for item in self.children:
            item.disabled = True

        await interaction.response.edit_message(view=self)


class BlackjackUi(discord.ui.View):
    """View for the blackjack command and its associated functions."""

    def __init__(self, interaction: discord.Interaction):
        self.interaction = interaction
        self.finished = False
        super().__init__(timeout=30)

    async def on_error(
        self, 
        interaction: discord.Interaction, 
        error: Exception, 
        item: discord.ui.Item[Any], 
        /
    ) -> None:
        await super().on_error(interaction, error, item)
        try:
            await self.interaction.edit_original_response(view=None)
        except discord.HTTPException:
            pass

    async def on_timeout(self) -> None:
        if not self.finished:
            del self.interaction.client.games[self.interaction.user.id]

            async with self.interaction.client.pool.acquire() as conn:
                await Economy.end_transaction(conn, user_id=self.interaction.user.id)
                await conn.commit()

            try:
                await self.interaction.edit_original_response(
                    view=None, 
                    embed=membed("You backed off so the game ended.")
                )
            except discord.HTTPException:
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
            multiplied = add_multi_to_original(multi=their_multi, original=bet_amount)
            await Economy.end_transaction(conn, user_id=self.interaction.user.id)

            bj_lose, new_bj_win, new_amount_balance = await conn.fetchone(
                """
                UPDATE accounts
                SET 
                    wallet = wallet + $0,
                    bjw = bjw + 1,
                    bjwa = bjwa + $0
                WHERE userID = $1
                RETURNING bjl, bjw, wallet
                """, multiplied, self.interaction.user.id
            )

            await conn.commit()
            prctnw = (new_bj_win / (new_bj_win + bj_lose)) * 100
        return multiplied, new_amount_balance, prctnw, their_multi

    async def update_losing_data(self, *, bet_amount: int) -> tuple:
        """
        Return a tuple containing elements in this order:

        New amount balance, Percentage games lost
        """

        async with self.interaction.client.pool.acquire() as conn:
            await Economy.end_transaction(conn, user_id=self.interaction.user.id)
            bj_win, new_bj_lose, new_amount_balance = await conn.fetchone(
                """
                UPDATE accounts
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
        deck, player_hand, dealer_hand, d_fver_d, d_fver_p, namount = interaction.client.games[interaction.user.id]

        player_hand.append(deck.pop())
        d_fver_p.append(display_user_friendly_card_format(player_hand[-1]))
        player_sum = calculate_hand(player_hand)

        embed = interaction.message.embeds[0]

        if player_sum > 21:

            self.stop()
            self.finished = True
            del interaction.client.games[interaction.user.id]

            new_amount_balance, prnctl = await self.update_losing_data(bet_amount=namount)

            embed.colour = discord.Colour.brand_red()
            embed.description = (
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
            ).set_field_at(
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
            ).remove_footer()

            await interaction.response.edit_message(embed=embed, view=None)

        elif player_sum == 21:
            self.stop()
            self.finished = True
            del interaction.client.games[interaction.user.id]

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
            ).set_field_at(
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
            ).set_footer(text=f"Multiplier: {new_multi:,}%")

            await interaction.response.edit_message(embed=embed, view=None)
        else:
            necessary_show = d_fver_d[0]
            embed.description = f"**Your move. Your hand is now {player_sum}**."

            embed.set_field_at(
                index=0,
                name=f"{interaction.user.name} (Player)", 
                value=(
                    f"**Cards** - {' '.join(d_fver_p)}\n"
                    f"**Total** - `{player_sum}`"
                )
            ).set_field_at(
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

        deck, player_hand, dealer_hand, d_fver_d, d_fver_p, namount = interaction.client.games[interaction.user.id]
        dealer_total = calculate_hand(dealer_hand)
        player_sum = calculate_hand(player_hand)

        while dealer_total < 17:
            dealer_hand.append(deck.pop())

            d_fver_d.append(display_user_friendly_card_format(dealer_hand[-1]))

            dealer_total = calculate_hand(dealer_hand)

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

            embed.set_author(
                icon_url=interaction.user.display_avatar.url, 
                name=f"{interaction.user.name}'s winning blackjack game"
            ).set_footer(text=f"Multiplier: {new_multi:,}%")

        elif dealer_total > player_sum:
            new_amount_balance, prnctl = await self.update_losing_data(bet_amount=namount)

            embed.colour = discord.Colour.brand_red()
            embed.description = (
                f"**You lost. You stood with a lower score (`{player_sum}`) than the dealer (`{dealer_total}`).**\n"
                f"You lost {CURRENCY} **{namount:,}**. You now have {CURRENCY} **{new_amount_balance:,}**.\n"
                f"You lost {prnctl:.1f}% of the games."
            )

            embed.set_author(
                icon_url=interaction.user.display_avatar.url,
                name=f"{interaction.user.name}'s losing blackjack game"
            ).remove_footer()

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

            embed.set_author(
                icon_url=interaction.user.display_avatar.url,
                name=f"{interaction.user.name}'s winning blackjack game"
            ).set_footer(text=f"Multiplier: {new_multi:,}%")

        else:
            async with interaction.client.pool.acquire() as conn:
                conn: asqlite_Connection

                await Economy.end_transaction(conn, user_id=interaction.user.id)
                await conn.commit()

                wallet_amt = await Economy.get_wallet_data_only(interaction.user, conn)

            embed.colour = discord.Colour.yellow()
            embed.description = (
                f"**Tie! You tied with the dealer.**\n"
                f"Your wallet hasn't changed! You have {CURRENCY} **{wallet_amt:,}** still."
            )
            embed.remove_footer()

        embed.set_field_at(
            index=0,
            name=f"{interaction.user.name} (Player)", 
            value=(
                f"**Cards** - {' '.join(d_fver_p)}\n"
                f"**Total** - `{player_sum}`"
            )
        ).set_field_at(
            index=1,
            name=f"{interaction.client.user.name} (Dealer)", 
            value=(
                f"**Cards** - {' '.join(d_fver_d)}\n"
                f"**Total** - `{dealer_total}`"
            )
        )

        await interaction.response.edit_message(embed=embed, view=None)

    @discord.ui.button(label='Forfeit', style=discord.ButtonStyle.primary)
    async def forfeit_bj(self, interaction: discord.Interaction, _: discord.ui.Button):
        """Button for the blackjack interface to forfeit the current match."""
        self.stop()
        self.finished = True

        _, player_hand, dealer_hand, d_fver_d, d_fver_p, namount = interaction.client.games[interaction.user.id]
        namount //= 2

        dealer_total = calculate_hand(dealer_hand)
        player_sum = calculate_hand(player_hand)
        del interaction.client.games[interaction.user.id]

        new_amount_balance, prcntl = await self.update_losing_data(bet_amount=namount)

        embed = interaction.message.embeds[0]
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
        ).set_field_at(
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
        ).remove_footer()

        await interaction.response.edit_message(embed=embed, view=None)


class HighLow(discord.ui.View):
    """View for the Highlow command and its associated functions."""

    def __init__(self, interaction: discord.Interaction, bet: int) -> None:
        self.interaction = interaction
        self.their_bet = bet
        self.true_value = randint(1, 100)
        self.hint_provided = randint(1, 100)
        super().__init__(timeout=30)

    async def start(self):
        query = membed(
            "I just chose a secret number between 0 and 100.\n"
            f"Is the secret number *higher* or *lower* than **{self.hint_provided}**?"
        ).set_author(
            name=f"{self.interaction.user.name}'s high-low game", 
            icon_url=self.interaction.user.display_avatar.url
        ).set_footer(text="The jackpot button is if you think it is the same!")

        await self.interaction.response.send_message(embed=query, view=self)

    async def make_clicked_blurple_only(self, clicked_button: discord.ui.Button):
        """Disable all buttons in the interaction menu except the clicked one, setting its style to blurple."""
        self.stop()
        for item in self.children:
            item.disabled = True
            if item == clicked_button:
                item.style = discord.ButtonStyle.primary
                continue
            item.style = discord.ButtonStyle.secondary

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
        await self.make_clicked_blurple_only(button)
        async with interaction.client.pool.acquire() as conn:
            new_multi = await Economy.get_multi_of(user_id=interaction.user.id, multi_type="robux", conn=conn)
            total = add_multi_to_original(multi=new_multi, original=self.their_bet)
            new_balance = await Economy.update_bank_new(interaction.user, conn, total)
            await Economy.end_transaction(conn, user_id=self.interaction.user.id)
            await conn.commit()

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
        ).set_footer(text=f"Multiplier: {new_multi:,}%")

        await interaction.response.edit_message(embed=win, view=self)

    async def send_loss(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.make_clicked_blurple_only(button)
        async with interaction.client.pool.acquire() as conn:
            new_amount = await Economy.update_bank_new(interaction.user, conn, -self.their_bet)
            await Economy.end_transaction(conn, user_id=self.interaction.user.id)
            await conn.commit()

        lose = interaction.message.embeds[0]
        lose.colour = discord.Colour.brand_red()
        lose.description = (
            f'**You lost {CURRENCY} {self.their_bet:,}!**\n'
            f'Your hint was **{self.hint_provided}**. '
            f'The hidden number was **{self.true_value}**.\n'
            f'Your new balance is {CURRENCY} **{new_amount[0]:,}**.'
        )

        lose.set_author(
            name=f"{interaction.user.name}'s losing high-low game", 
            icon_url=interaction.user.display_avatar.url
        ).remove_footer()

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


class Leaderboard(RefreshPagination):
    podium_pos = {1: "### \U0001f947", 2: "\U0001f948", 3: "\U0001f949"}
    length = 6

    def __init__(
        self, 
        interaction: discord.Interaction, 
        chosen_option: str, 
        get_page: Callable | None = None
    ) -> None:
        self.chosen_option = chosen_option
        self.data = []
        super().__init__(interaction, get_page)

    @staticmethod
    def populate_data(bot: commands.Bot, ret: list[sqlite3.Row]) -> list[str]:
        data = []
        for i, (identifier, metric) in enumerate(ret, start=1):
            memobj = bot.get_user(identifier)
            data.append(f"{Leaderboard.podium_pos.get(i, "\U0001f539")} ` {metric:,} ` \U00002014 {memobj.name}{UNIQUE_BADGES.get(memobj.id, '')}")
        return data

    async def create_lb(self, conn: asqlite_Connection, item_id: int) -> None:
        data = await conn.fetchall(
            """
            SELECT 
                userID AS identifier,
                SUM(qty) AS metric
            FROM inventory
            WHERE itemID = $0
            GROUP BY userID
            ORDER BY SUM(qty) DESC
            """, item_id
        )

        self.data = self.populate_data(bot=self.interaction.client, ret=data)


class ExtendedLeaderboard(Leaderboard):
    """A paginated leaderboard, but with a dropdown that displays a list of other filters you can sort by."""
    options = [
        discord.SelectOption(label='Money Net', description='The sum of wallet and bank.'),
        discord.SelectOption(label='Wallet', description='The wallet amount only.'),
        discord.SelectOption(label='Bank', description='The bank amount only.'),
        discord.SelectOption(label='Inventory Net', description='The net value of your inventory.'),
        discord.SelectOption(label='Bounty', description="The sum paid for capturing a player."),
        discord.SelectOption(label='Commands', description="The total commands ran."),
        discord.SelectOption(label='Level', description="The player level."),
        discord.SelectOption(label='Net Worth', description="The sum of wallet, bank and inventory value.")
    ]

    query_dict = {
        'Money Net': (
            """
            SELECT 
                userID, 
                SUM(wallet + bank) AS total_balance 
            FROM accounts 
            GROUP BY userID 
            ORDER BY total_balance DESC
            """
        ),
        'Wallet': (
            """
            SELECT 
                userID, 
                wallet AS total_wallet 
            FROM accounts 
            GROUP BY userID 
            ORDER BY total_wallet DESC
            """
        ),
        'Bank': (
            """
            SELECT 
                userID, 
                bank AS total_bank 
            FROM accounts 
            GROUP BY userID 
            ORDER BY total_bank DESC
            """
        ),
        'Inventory Net': (
            """
            SELECT 
                inventory.userID, 
                SUM(shop.cost * inventory.qty) AS NetValue
            FROM inventory
            INNER JOIN shop 
                ON shop.itemID = inventory.itemID
            GROUP BY inventory.userID
            ORDER BY NetValue DESC
            """
        ),
        'Bounty': (
            """
            SELECT 
                userID, 
                bounty AS total_bounty 
            FROM accounts 
            GROUP BY userID 
            HAVING total_bounty > 0
            ORDER BY total_bounty DESC
            """
        ),
        'Commands': (
            """
            SELECT 
                userID, 
                SUM(cmd_count) AS total_commands
            FROM command_uses
            GROUP BY userID
            HAVING total_commands > 0
            ORDER BY total_commands DESC
            """
        ),
        'Level': (
            """
            SELECT userID, level 
            FROM accounts 
            GROUP BY userID 
            HAVING level > 0
            ORDER BY level DESC
            """
        ),
        'Net Worth': (
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
                        userID, 
                        SUM(wallet + bank) AS total_balance 
                    FROM 
                        accounts 
                    GROUP BY 
                        userID
                ) AS money ON inventory.userID = money.userID
            GROUP BY 
                COALESCE(inventory.userID, money.userID)
            ORDER BY 
                TotalNetWorth DESC
            """
        )
    }

    def __init__(self, interaction: discord.Interaction, chosen_option: str):
        super().__init__(interaction, chosen_option=chosen_option, get_page=self.get_page_part)

        self.lb = discord.Embed(
            title=f"Global Leaderboard: {chosen_option}",
            color=0x2B2D31,
            timestamp=discord.utils.utcnow()
        )

        for option in self.children[-1].options:
            option.default = option.value == chosen_option

    async def create_lb(self) -> None:
        self.lb.timestamp = discord.utils.utcnow()

        async with self.interaction.client.pool.acquire() as conn:
            data = await conn.fetchall(self.query_dict[self.chosen_option])

        self.data = self.populate_data(self.interaction.client, data)

    async def get_page_part(self, force_refresh: bool | None = None) -> discord.Embed:
        if force_refresh:
            await self.create_lb()

        self.reset_index(self.data)
        if not self.data:
            self.lb.set_footer(text="Empty")
            return self.lb

        offset = ((self.index - 1) * self.length)
        self.lb.description = "\n".join(self.data[offset:offset+self.length])
        self.lb.set_footer(text=f"Page {self.index} of {self.total_pages}")

        return self.lb

    @discord.ui.select(options=options, placeholder="Select a leaderboard filter", row=0)
    async def lb_stat_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.chosen_option = select.values[0]
        self.index = 1
        self.lb.title = f"Global Leaderboard: {self.chosen_option}"

        for option in select.options:
            option.default = option.value == self.chosen_option

        await self.create_lb()
        await self.edit_page(interaction)


@dataclass(slots=True, repr=False)
class ConnectionHolder:
    conn: asqlite_Connection


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

        success = discord.Embed(
            title="Successful Purchase",
            colour=0xFFFFFF,
            description=(
                f"> You have {CURRENCY} {new_am[0]:,} left.\n\n"
                "**You bought:**\n"
                f"- {true_qty:,}x {self.ie} {self.item_name}\n\n"
                "**You paid:**\n"
                f"- {CURRENCY} {new_price:,}"
            )
        ).set_footer(text="Thanks for your business.")

        if self.activated_coupon:
            await Economy.update_inv_new(interaction.user, -1, "Shop Coupon", conn)
            success.description += "\n\n**Additional info:**\n- <:shopCoupon:1263923497323855907> 5% Coupon Discount was applied"
        await respond(interaction, embed=success)
        await conn.commit()

    async def calculate_discounted_price_if_any(
        self, 
        user: USER_ENTRY, 
        holder: ConnectionHolder,
        interaction: discord.Interaction, 
        current_price: int
    ) -> int:
        """Check if the user is eligible for a discount on the item."""

        data = await holder.conn.fetchone(
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

        await Economy.declare_transaction(holder.conn, user_id=interaction.user.id)
        await interaction.client.pool.release(holder.conn)

        value = await process_confirmation(
            interaction=interaction, 
            prompt=(
                "Would you like to use your <:shopCoupon:1263923497323855907> "
                "**Shop Coupon** for an additional **5**% off?\n"
                f"(You have **{data[0]:,}** coupons in total)\n\n"
                f"This will bring your total for this purchase to {CURRENCY} "
                f"**{discounted_price:,}** if you decide to use the coupon."
            )
        )

        holder.conn = await interaction.client.pool.acquire()
        await Economy.end_transaction(holder.conn, user_id=interaction.user.id)
        await holder.conn.commit()

        if value is None:
            return value

        if value:
            self.activated_coupon = True
            return discounted_price
        return current_price  # if the view timed out or willingly pressed cancel

    # --------------------------------------------------------------------------------------------

    async def on_submit(self, interaction: discord.Interaction):
        true_quantity = await determine_exponent(
            interaction=interaction, 
            rinput=self.quantity.value
        )
        if true_quantity is None:
            return

        current_price = self.item_cost * true_quantity
        conn_holder = ConnectionHolder(await interaction.client.pool.acquire())

        new_price = await self.calculate_discounted_price_if_any(
            user=interaction.user, 
            holder=conn_holder, 
            interaction=interaction, 
            current_price=current_price
        )

        if new_price is None:
            await interaction.client.pool.release(conn_holder.conn)
            return await respond(
                interaction=interaction,
                embed=membed(
                    "You didn't respond in time so your purchase was cancelled."
                )
            )

        current_balance = await Economy.get_wallet_data_only(interaction.user, conn_holder.conn)
        if new_price > current_balance:
            await interaction.client.pool.release(conn_holder.conn)
            return await respond(
                interaction=interaction,
                embed=membed(f"You don't have enough robux to buy **{true_quantity:,}x {self.ie} {self.item_name}**.")
            )

        await interaction.client.pool.release(conn_holder.conn)
        del conn_holder

        can_proceed = await Economy.handle_confirm_outcome(
            interaction=interaction, 
            setting="buying_confirmations",
            confirmation_prompt=(
                f"Are you sure you want to buy **{true_quantity:,}x {self.ie} "
                f"{self.item_name}** for **{CURRENCY} {new_price:,}**?"
            )
        )

        async with interaction.client.pool.acquire() as conn:
            async with conn.transaction():
                if can_proceed is not None:
                    await Economy.end_transaction(conn, user_id=interaction.user.id)
                    if can_proceed is False:
                        return

                await self.begin_purchase(
                    interaction, 
                    true_quantity, 
                    conn, 
                    current_balance, 
                    new_price
                )


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
            em = await Economy.get_setting_embed(interaction, view=self.view, conn=conn)
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
            index=0, 
            name="Current", 
            value="<:Enabled:1263921710990622802> Enabled" if enabled else "<:Disabled:1263921453229801544> Disabled"
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
        except discord.HTTPException:
            pass

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return await economy_check(interaction, self.interaction.user)


class MultiplierView(RefreshPagination):

    length = 6
    colour_mapping = {
        "Robux": (0x59DDB3, "https://i.imgur.com/raX1Am0.png"),
        "XP": (0xCDC700, "https://i.imgur.com/7hJ0oiO.png"),
        "Luck": (0x65D654, "https://i.imgur.com/9xZIFOg.png")
    }

    multipliers = [
        discord.SelectOption(
            label='Robux',
            emoji="<:robuxMulti:1263923323088408688>"
        ),
        discord.SelectOption(
            label='XP',
            emoji='<:xpMulti:1263924221109731471>'
        ),
        discord.SelectOption(
            label='Luck', 
            emoji='<:luckMulti:1263922104231792710>'
        )
    ]

    def __init__(
        self, 
        interaction: discord.Interaction, 
        chosen_multiplier: str, 
        viewing: USER_ENTRY, 
        get_page: Callable | None = None
    ) -> None:

        self.viewing = viewing
        self.chosen_multiplier = chosen_multiplier

        self.embed = discord.Embed(title=f"{self.viewing.display_name}'s Multipliers")
        self.embed.colour, thumb_url = self.colour_mapping[chosen_multiplier]
        self.embed.set_thumbnail(url=thumb_url)

        super().__init__(interaction, get_page=get_page)

        for option in self.children[-1].options:
            option.default = option.value == chosen_multiplier

    def repr_multi(self):
        """
        Represent a multiplier using proper formatting.

        For instance, to represent a user with no XP multiplier, instead of showing 0, show 1x.

        The units are also converted as necessary based on the type we're looking at.
        """

        unit = "x" if self.chosen_multiplier == "XP" else "%"
        amount = self.total_multi if self.chosen_multiplier != "XP" else (1 + (self.total_multi / 100))

        self.embed.description = f"> {self.chosen_multiplier}: **{amount:.2f}{unit}**\n\n"

    async def format_pages(self) -> None:

        lowered = self.chosen_multiplier.lower()
        async with self.interaction.client.pool.acquire() as conn:
            conn: asqlite_Connection

            self.total_multi, = await conn.fetchone(
                """
                SELECT CAST(TOTAL(amount) AS INTEGER) 
                FROM multipliers
                WHERE (userID IS NULL OR userID = $0)
                AND multi_type = $1
                """, self.viewing.id, lowered
            )

            self.multiplier_list = await conn.fetchall(
                """
                SELECT amount, description, expiry_timestamp
                FROM multipliers
                WHERE (userID IS NULL OR userID = $0)
                AND multi_type = $1
                ORDER BY amount DESC
                """, self.viewing.id, lowered
            )

    async def navigate(self) -> None:
        """Get through the paginator properly."""
        emb = await self.get_page(self.index)
        self.update_buttons()

        await self.interaction.response.send_message(embed=emb, view=self)

    @discord.ui.select(options=multipliers, row=0, placeholder="Select a multiplier to view")
    async def callback(self, interaction: discord.Interaction, select: discord.ui.Select):

        self.chosen_multiplier: str = select.values[0]

        for option in select.options:
            option.default = option.value == self.chosen_multiplier

        await self.format_pages()

        self.embed.colour, thumb_url = self.colour_mapping[self.chosen_multiplier]
        self.embed.set_thumbnail(url=thumb_url)
        self.index = 1

        await self.edit_page(interaction)


class Economy(commands.Cog):
    """Advanced economy system to simulate a real world economy, available for everyone."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

        self.not_registered = membed(
            "## <:notFound:1263922668823122075> You are not registered.\n"
            "You'll need to register first before you can use this command.\n"
            "### Already Registered?\n"
            "Find out what could've happened by calling "
            "[`@me reasons`](https://www.google.com/)."
        )

    @staticmethod
    async def handle_confirm_outcome(
        interaction: discord.Interaction, 
        confirmation_prompt: str,
        view_owner: discord.Member | None = None,
        setting: str | None = None,
        conn: asqlite_Connection | None = None,
        **kwargs
    ) -> None | bool:
        """
        Handle a confirmation outcome correctly, accounting for whether or not a specific confirmation is enabled.

        The `setting` passed in should be lowercased, since all toggleable confirmation settings are lowercased.

        ## Returns
        `None` to indicate that the user doesn't have the specified confirmation enabled. 
        It's only returned when you specify a specific confirmation setting to check but that user doesn't have it enabled.

        `None` will only be returned if a specific confirmation was passed in and the user has it disabled.

        `True` to indicate the user has confirmed, either by confirming on a specific confirmation you passed in to check 
        if it is enabled, or through a generic confirmation that the user confirmed on.

        `False` to indicate that the user has not confirmed (the confirmation timed out or they explicitly denied), which 
        again can be called by the default confirmation or a specific confirmation you passed in to check for.

        ## Notes

        Transactions will now always be created, meaning you should only use this function in the economy system
        on a user who is registered, since foreign key constraints require you to pass in a valid row of the accounts table.

        All connections acquired, whether it be passed into the function or created in the function will also be released 
        in this exact function. Do not handle it yourself outside of the function.
        """

        can_proceed = None
        view_owner = view_owner or interaction.user

        conn = conn or await interaction.client.pool.acquire()  # always hold a connection
        try:
            enabled = Economy.is_setting_enabled
            can_confirm = setting and not(await enabled(conn, user_id=view_owner.id, setting=setting))
            if can_confirm:
                return

            await Economy.declare_transaction(conn, user_id=view_owner.id)
            await conn.commit()
            await interaction.client.pool.release(conn)
            conn = None

            can_proceed = await process_confirmation(
                interaction, 
                prompt=confirmation_prompt, 
                view_owner=view_owner,
                **kwargs
            )
        finally:
            if conn:
                await interaction.client.pool.release(conn)
        return can_proceed

    async def fetch_showdata(self, user: USER_ENTRY, conn: asqlite_Connection) -> tuple:

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

        ui_data, garbage = [], set()

        for (item_name, ie, inv_qty, itemID) in showdata:

            # ensures items in the showcase not in their inventory are removed
            if not inv_qty:
                garbage.add(itemID)
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
        ).set_thumbnail(url=user.display_avatar.url)
        return embed

    async def interaction_check(self, interaction: discord.Interaction):
        async with self.bot.pool.acquire() as conn:
            conn: asqlite_Connection
            data = await conn.fetchone("SELECT userID FROM transactions WHERE userID = $0", interaction.user.id)

            if data is None:
                return True

            error_view = discord.ui.View().add_item(
                discord.ui.Button(
                    label="Explain This!", 
                    url="https://dankmemer.lol/tutorial/interaction-locks"
                )
            )
            await interaction.response.send_message(
                view=error_view, 
                ephemeral=True,
                embed=membed(WARN_FOR_CONCURRENCY)
            )
            return False

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
        timestamp = datetime.fromtimestamp(expiry, tz=timezone.utc)
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
    async def partial_match_for(interaction: discord.Interaction, item_input: str, conn: asqlite_Connection):
        """
        If the user types part of an item name, get that item name indicated.

        This is known as partial matching for item names.

        Returns the item metadata in this order: itemID, itemName, itemEmoji
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
                                    userID, 
                                    SUM(wallet + bank) AS total_balance 
                                FROM 
                                    accounts 
                                GROUP BY 
                                    userID
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
                                        userID, 
                                        SUM(wallet + bank) AS total_balance 
                                    FROM 
                                        accounts 
                                    GROUP BY 
                                        userID
                                ) AS money ON inventory.userID = money.userID 
                            WHERE 
                                inventory.userID = $0
                        ), 0
                    )
            ) AS Rank
        """, user.id
        )
        val = val or ("Unlisted",)
        return val[0]

    @staticmethod
    async def open_bank_new(user: USER_ENTRY, conn_input: asqlite_Connection) -> None:
        ranumber = randint(10_000_000, 20_000_000)
        query = "INSERT INTO accounts (userID, wallet) VALUES ($0, $1)"
        await conn_input.execute(query, user.id, ranumber)

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
            "SELECT EXISTS (SELECT 1 FROM accounts WHERE userID = $0)", 
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
            """
            SELECT COUNT(*) 
            FROM accounts 
            WHERE userID IN (?, ?)
            """, (user1.id, user2.id)
        )

        return data[0] == 2

    @staticmethod
    async def get_wallet_data_only(user: USER_ENTRY, conn_input: asqlite_Connection) -> int:
        """Retrieves the wallet amount only from a registered user's bank data."""
        data = await conn_input.fetchone("SELECT wallet FROM accounts WHERE userID = $0", user.id)
        return data[0]

    @staticmethod
    async def get_spec_bank_data(user: USER_ENTRY, field_name: str, conn_input: asqlite_Connection) -> Any:
        """Retrieves a specific field name only from the accounts table."""
        data = await conn_input.fetchone(f"SELECT {field_name} FROM accounts WHERE userID = $0", user.id)
        return data[0]

    @staticmethod
    async def update_bank_new(
        user: USER_ENTRY, 
        conn_input: asqlite_Connection, 
        amount: float | int = 0, 
        mode: str = "wallet"
    ) -> Any | None:

        """
        Modifies a user's balance in a given mode: either wallet (default) or bank.

        It also returns the new balance in the given mode, if any (defaults to wallet).

        Note that conn_input is not the last parameter, it is the second parameter to be included.
        """

        data = await conn_input.fetchone(
            f"""
            UPDATE accounts 
            SET {mode} = {mode} + $0 
            WHERE userID = $1 RETURNING `{mode}`
            """, amount, user.id
        )
        return data

    @staticmethod
    async def change_bank_new(
        user: USER_ENTRY, 
        conn_input: asqlite_Connection, 
        amount: float | int | str = 0, 
        mode: str = "wallet"
    ) -> Any | None:
        """
        Modifies a user's field values in any given mode.

        Unlike the other updating the bank method, this function directly changes the value to the parameter ``amount``.

        It also returns the new balance in the given mode, if any (defaults to wallet).

        Note that conn_input is not the last parameter, it is the second parameter to be included.
        """

        data = await conn_input.fetchone(
            f"""
            UPDATE accounts 
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
        amount1: float | int, 
        mode2: str, 
        amount2: float | int, 
        table_name: str = "accounts"
        ) -> Any | None:
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
        amount1: float | int, 
        mode2: str, 
        amount2: float | int, 
        mode3: str, 
        amount3: float | int, 
        table_name: str = "accounts"
    ) -> Any | None:
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
    async def update_wallet_many(conn_input: asqlite_Connection, *params_users) -> list[sqlite3.Row]:
        """
        Update the bank of two users at once. Useful to transfer money between multiple users at once.
        
        The parameters are tuples, each tuple containing the amount to be added to the wallet and the user ID.

        Example:
        await Economy.update_wallet_many(conn, (100, 546086191414509599), (200, 270904126974590976))
        """

        query = (
            """
            UPDATE accounts 
            SET wallet = wallet + ? 
            WHERE userID = ?
            """
        )

        await conn_input.executemany(query, params_users)

    # ------------------ INVENTORY FUNCS ------------------ #

    @staticmethod
    async def get_one_inv_data_new(
        user: USER_ENTRY, 
        item_name: str, 
        conn_input: asqlite_Connection
    ) -> Any | None:
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
        amount: float | int, 
        item_name: str, 
        conn: asqlite_Connection
    ) -> Any | None:
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
        amount: float | int, 
        item_id: int, 
        conn: asqlite_Connection
    ) -> Any | None:
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
            """
            UPDATE accounts 
            SET 
                wallet = 0, 
                bank = 0, 
                job = $0, 
                bounty = 0 
            WHERE userID = $1
            """, "None", user.id
        )

        await conn_input.execute("DELETE FROM inventory WHERE userID = $0", user.id)

    # ------------ JOB FUNCS ----------------

    @staticmethod
    async def change_job_new(user: USER_ENTRY, conn_input: asqlite_Connection, job_name: str) -> None:
        """Modifies a user's job, returning the new job after changes were made."""

        await conn_input.execute(
            """
            UPDATE accounts 
            SET job = $0 
            WHERE userID = $1
            """, job_name, user.id
        )

    # ------------ cooldowns ----------------

    @staticmethod
    async def check_has_cd(
        conn: asqlite_Connection, 
        user_id: int, 
        cd_type: str | None = None, 
        mode="t", 
        until = "N/A"
    ) -> bool | str:
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
        time_left = datetime.fromtimestamp(until, tz=timezone.utc)
        time_left = (time_left - current_time).total_seconds()

        if time_left > 0:
            when = current_time + timedelta(seconds=time_left)
            return discord.utils.format_dt(when, style=mode), discord.utils.format_dt(when, style="R")
        return False

    @staticmethod
    async def update_cooldown(
        conn_input: asqlite_Connection, 
        *, 
        user_id: USER_ENTRY, 
        cooldown_type: str, 
        new_cd: str
    ) -> None:
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
        expiry: float | None = None,
        on_conflict: str = "UPDATE SET amount = amount + $1, description = $4"
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
    async def is_setting_enabled(conn: asqlite_Connection, user_id: int, setting: str) -> bool:
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
            view.clear_items().stop()
            return membed("This setting does not exist.")

        value, description = data
        view.setting_dropdown.current_setting_state = value

        embed = membed(f"> {description}")

        embed.title = " ".join(view.setting_dropdown.current_setting.split("_")).title()

        view.clear_items().add_item(view.setting_dropdown)

        if embed.title == "Profile Customization":
            view.add_item(ProfileCustomizeButton())
        else:
            enabled = value == 1
            current_text = "<:Enabled:1263921710990622802> Enabled" if enabled else "<:Disabled:1263921453229801544> Disabled"
            embed.add_field(name="Current", value=current_text)
            view.disable_button.disabled = not enabled
            view.enable_button.disabled = enabled
            view.add_item(view.disable_button).add_item(view.enable_button)
        return embed

    async def send_tip_if_enabled(self, interaction: discord.Interaction, conn: asqlite_Connection) -> None:
        """Send a tip if the user has enabled tips."""

        tips_enabled = await self.is_setting_enabled(conn, interaction.user.id, "tips")
        if not tips_enabled:
            return

        async with aiofiles.open("C:\\Users\\georg\\Documents\\c2c\\tips.txt") as f:
            contents = await f.readlines()
            atip = choice(contents)

        tip = membed(f"\U0001f4a1 `TIP`: {atip}")
        tip.set_footer(text="You can disable these tips in /settings.")

        await interaction.followup.send(embed=tip, ephemeral=True)
        del contents, atip, tip

    async def add_exp_or_levelup(
        self, 
        interaction: discord.Interaction, 
        connection: asqlite_Connection, 
        exp_gainable: int
    ) -> None:

        record = await connection.fetchone(
            """
            UPDATE accounts
            SET exp = exp + $0
            WHERE userID = $1 
            RETURNING exp, level
            """, exp_gainable, interaction.user.id
        )

        if record is None:
            return

        xp, level = record
        xp_needed = self.calculate_exp_for(level=level)

        if xp < xp_needed:
            return
        level += 1

        await self.add_multiplier(
            connection,
            user_id=interaction.user.id,
            multi_amount=((level // 3) or 1),
            multi_type="xp",
            cause="level",
            description=f"Level {level}"
        )

        await connection.execute(
            """
            UPDATE accounts 
            SET 
                level = level + 1, 
                exp = 0, 
                bankspace = bankspace + $0 
            WHERE userID = $1
            """, randint(50_000, 55_000*level), interaction.user.id
        )

        notifs_enabled = await self.is_setting_enabled(connection, interaction.user.id, "levelup_notifications")

        if notifs_enabled:
            rankup = discord.Embed(title="Level Up!", colour=0x55BEFF)
            rankup.description = (
                f"{choice(LEVEL_UP_PROMPTS)}, {interaction.user.name}!\n"
                f"You've leveled up from level **{level-1:,}** to level **{level:,}**."
            )

            await interaction.followup.send(embed=rankup)

    @commands.Cog.listener()
    async def on_app_command_completion(
        self, 
        interaction: discord.Interaction, 
        command: app_commands.Command | app_commands.ContextMenu
    ) -> None:
        """
        Track slash commands ran.

        Increase the interaction user's XP/Level if they are registered. 

        Provide a tip if the total commands counter for that command ran is a multiple of 15.
        """

        if isinstance(interaction.command, app_commands.ContextMenu):
            return
        cmd = interaction.command.parent or interaction.command

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

                exp_gainable *= (1+(multi/100))
                await self.add_exp_or_levelup(interaction, connection, int(exp_gainable))

    @commands.Cog.listener()
    async def on_command(self, ctx: commands.Context) -> None:
        """Track text commands ran."""
        cmd = ctx.command.parent or ctx.command

        async with self.bot.pool.acquire() as connection:
            try:
                row = await connection.fetchone("SELECT 1 FROM accounts WHERE userid = $0", ctx.author.id)
                assert row is not None
            except AssertionError:
                return
            else:
                await add_command_usage(ctx.author.id, f"@me {cmd.name}", connection)
                await connection.commit()

    # ----------- END OF ECONOMY FUNCS, HERE ON IS JUST COMMANDS --------------

    @app_commands.command(name="settings", description="Adjust user-specific settings")
    @app_commands.describe(setting="The specific setting you want to adjust. Defaults to view.")
    @app_commands.allowed_installs(**CONTEXT_AND_INSTALL)
    @app_commands.allowed_contexts(**CONTEXT_AND_INSTALL)
    async def view_user_settings(self, interaction: discord.Interaction, setting: str | None = None) -> None:
        """View or adjust user-specific settings."""
        async with self.bot.pool.acquire() as conn:
            conn: asqlite_Connection
            settings = await conn.fetchall("SELECT setting, brief FROM settings_descriptions")
            chosen_setting = setting or settings[0][0]

            view = UserSettings(data=settings, chosen_setting=chosen_setting, interaction=interaction)
            em = await Economy.get_setting_embed(interaction, view=view, conn=conn)
        await interaction.response.send_message(embed=em, view=view)

    @app_commands.command(name="multipliers", description="View all of your multipliers within the bot")
    @app_commands.describe(
        user="The user whose multipliers you want to see. Defaults to your own.",
        multiplier="The type of multiplier you want to see. Defaults to robux."
    )
    @app_commands.allowed_installs(**CONTEXT_AND_INSTALL)
    @app_commands.allowed_contexts(**CONTEXT_AND_INSTALL)
    async def my_multi(
        self, 
        interaction: discord.Interaction, 
        user: USER_ENTRY | None = None, 
        multiplier: Literal["Robux", "XP", "Luck"] = "Robux"
    ) -> None:

        user = user or interaction.user
        paginator = MultiplierView(interaction, chosen_multiplier=multiplier, viewing=user)
        await paginator.format_pages()

        async def get_page_part(force_refresh: bool = None) -> discord.Embed:
            if force_refresh:
                await paginator.format_pages()

            paginator.reset_index(paginator.multiplier_list).repr_multi()
            offset = ((paginator.index - 1) * paginator.length)

            if not paginator.total_multi:
                paginator.embed.set_footer(text="Empty")
                return paginator.embed

            paginator.embed.description += "\n".join(
                format_multiplier(multi)
                for multi in paginator.multiplier_list[offset:offset + paginator.length]
            )
            paginator.embed.set_footer(text=f"Page {paginator.index} of {paginator.total_pages}")
            return paginator.embed

        paginator.get_page = get_page_part
        await paginator.navigate()

    share = app_commands.Group(
        name='share', 
        description='Share different assets with others.', 
        allowed_contexts=app_commands.AppCommandContext(guild=True),
        allowed_installs=app_commands.AppInstallationType(guild=True)
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
        if sender.id == recipient.id:
            return await interaction.response.send_message(embed=membed("You can't share with yourself."))

        quantity = await determine_exponent(interaction, rinput=quantity)
        if quantity is None:
            return

        async with self.bot.pool.acquire() as conn:
            if await self.can_call_out(recipient, conn):
                return await respond(interaction=interaction, embed=NOT_REGISTERED)

            try:
                actual_wallet = await Economy.get_wallet_data_only(sender, conn)
            except TypeError:
                return await interaction.response.send_message(embed=self.not_registered)

            if isinstance(quantity, str):
                quantity = actual_wallet

            if quantity > actual_wallet:
                return await respond(
                    interaction,
                    embed=membed("You don't have that much money to share.")
                )

            can_proceed = await self.handle_confirm_outcome(
                interaction, 
                f"Are you sure you want to share {CURRENCY} **{quantity:,}** with {recipient.mention}?",
                setting="share_robux_confirmations",
                conn=conn
            )

        async with self.bot.pool.acquire() as conn:
            conn: asqlite_Connection
            async with conn.transaction():
                if can_proceed is not None:
                    await self.end_transaction(conn, user_id=sender.id)
                    if can_proceed is False:
                        return

                await self.update_wallet_many(
                    conn, 
                    (-int(quantity), sender.id), 
                    (int(quantity), recipient.id)
                )

        await respond(
            interaction, 
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
        quantity: app_commands.Range[int, 1], 
        item: str
    ) -> None:
        """Give an amount of items to another user."""

        sender = interaction.user
        if sender.id == recipient.id:
            return await interaction.response.send_message(embed=membed("You can't share with yourself."))

        async with self.bot.pool.acquire() as conn:
            if await self.can_call_out(recipient, conn):
                return await respond(interaction=interaction, embed=NOT_REGISTERED)

            item = await self.partial_match_for(interaction, item, conn)
            if item is None:
                return
            item_id, item_name, ie = item

            attrs = await conn.fetchone(
                """
                SELECT COALESCE(inventory.qty, 0), rarity
                FROM shop
                LEFT JOIN inventory 
                    ON inventory.itemID = shop.itemID AND inventory.userID = $0
                WHERE shop.itemID = $1
                """, sender.id, item_id
            )

            actual_inv_qty, item_rarity = attrs
            if actual_inv_qty < quantity:
                return await respond(interaction, embed=membed(f"You don't have **{quantity}x {ie} {item_name}**."))

            can_proceed = await self.handle_confirm_outcome(
                interaction, 
                f"Are you sure you want to share **{quantity:,} {ie} {item_name}** with {recipient.mention}?",
                setting="share_item_confirmations",
                conn=conn
            )

        async with self.bot.pool.acquire() as conn:
            async with conn.transaction():
                if can_proceed is not None:
                    await self.end_transaction(conn, user_id=sender.id)
                    if can_proceed is False:
                        return

                await self.update_inv_by_id(sender, -quantity, item_id, conn)
                await conn.execute(
                    """
                    INSERT INTO inventory (userID, itemID, qty) 
                    VALUES ($0, $1, $2) 
                    ON CONFLICT(userID, itemID) DO UPDATE SET qty = qty + $2
                    """, recipient.id, item_id, quantity
                )

        await respond(
            interaction,
            embed=discord.Embed(
                colour=RARITY_COLOUR.get(item_rarity, 0x2B2D31),
                description=f"Shared **{quantity}x {ie} {item_name}** with {recipient.mention}!"
            )
        )

    trade = app_commands.Group(
        name='trade', 
        description='Exchange different assets with others.', 
        allowed_contexts=app_commands.AppCommandContext(guild=True),
        allowed_installs=app_commands.AppInstallationType(guild=True)
    )

    async def coin_checks_passing(
        self,
        interaction: discord.Interaction,
        user_checked: discord.Member,
        coin_qty_offered: int,
        actual_wallet_amt
    ) -> bool | None:
        if actual_wallet_amt < coin_qty_offered:
            await respond(
                interaction, 
                embed=membed(
                    f"{user_checked.mention} only has {CURRENCY} **{actual_wallet_amt[0]:,}**.\n"
                    f"Not the requested {CURRENCY} **{coin_qty_offered:,}**."
                )
            )
            return
        return True

    async def item_checks_passing(
        self,
        interaction: discord.Interaction,
        conn: asqlite_Connection,
        user_to_check: discord.Member,
        item_data: tuple,
        item_qty_offered: int
    ) -> bool | None:

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
        can_continue: bool = True
    ) -> None | bool:
        """
        Send a confirmation prompt to `item_sender`, asking to confirm whether 
        they want to exchange their items (`item_sender_data`) with `coin_sender`, 
        in return for money (`coin_sender_qty`).

        The person that is confirming has to send items, in exchange they get coins.
        """

        if not can_continue:
            return

        can_continue = await self.handle_confirm_outcome(
            interaction,
            view_owner=item_sender,
            content=item_sender.mention,
            confirmation_prompt=dedent(
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
        can_continue: bool = True
    ) -> None | bool:

        """
        Send a confirmation prompt to `coin_sender`, asking to confirm whether 
        they want to exchange their coins for items.

        The person that is confirming has to send coins, and they get items in return.
        """

        if not can_continue:
            return

        can_continue = await self.handle_confirm_outcome(
            interaction,
            view_owner=coin_sender,
            content=coin_sender.mention,
            confirmation_prompt=dedent(
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
        can_continue: bool = True
    ) -> None | bool:

        """
        The person that is confirming has to send items, and they also get items in return.
        """

        if not can_continue:
            return

        can_continue = await self.handle_confirm_outcome(
            interaction,
            view_owner=item_sender,
            content=item_sender.mention,
            confirmation_prompt=dedent(
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

    async def default_checks_passing(
        self, 
        interaction: discord.Interaction, 
        with_who: discord.Member
    ) -> bool | None:
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

        for_robux = await determine_exponent(interaction, rinput=for_robux)
        if for_robux is None:
            return

        async with self.bot.pool.acquire() as conn:
            conn: asqlite_Connection
            item_details = await self.partial_match_for(interaction, item, conn)

            if item_details is None:
                return
            try:
                wallet_amt = await self.get_wallet_data_only(user=with_who, conn_input=conn)
            except TypeError:
                return await respond(interaction=interaction, embed=NOT_REGISTERED)

            if isinstance(for_robux, str):
                for_robux = wallet_amt

            # ! For the person sending items
            item_check_passing = await self.item_checks_passing(
                interaction, 
                conn,
                user_to_check=interaction.user,
                item_data=item_details,
                item_qty_offered=quantity
            )

            if not item_check_passing:
                return

        # Transaction created inside the function for interaction.user
        can_proceed = await self.prompt_for_coins(
            interaction,
            item_sender=interaction.user,
            item_sender_qty=quantity,
            item_sender_data=item_details,
            coin_sender=with_who,
            coin_sender_qty=for_robux
        )

        async with self.bot.pool.acquire() as conn:
            if not can_proceed:  
                await self.end_transaction(conn, user_id=interaction.user.id)
                await conn.commit()
                return

            # ! For the other person sending coins

            coin_check_passing = await self.coin_checks_passing(
                interaction,
                user_checked=with_who,
                coin_qty_offered=for_robux,
                actual_wallet_amt=wallet_amt
            )
            if not coin_check_passing:
                await self.end_transaction(conn, user_id=interaction.user.id)
                await conn.commit()
                return

        can_proceed = await self.prompt_coins_for_items(
            interaction,
            coin_sender=with_who,
            coin_sender_qty=for_robux,
            item_sender=interaction.user,
            item_sender_qty=quantity,
            item_sender_data=item_details,
            can_continue=can_proceed
        )

        query = "DELETE FROM transactions WHERE userID IN ($0, $1)"
        async with self.bot.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(query, interaction.user.id, with_who.id)
                if not can_proceed:
                    return

                await self.update_inv_by_id(interaction.user, -quantity, item_id=item_details[0], conn=conn)
                await self.update_inv_by_id(with_who, +quantity, item_id=item_details[0], conn=conn)
                await self.update_wallet_many(
                    conn, 
                    (-for_robux, with_who.id), 
                    (+for_robux, interaction.user.id)
                )

        embed = discord.Embed(colour=0xFFFFFF).set_footer(text="Thanks for your business.")
        embed.title = "Your Trade Receipt"
        embed.description = (
            f"- {interaction.user.mention} gave {with_who.mention} **{quantity}x {item_details[-1]} {item_details[1]}**.\n"
            f"- {interaction.user.mention} received {CURRENCY} **{for_robux:,}** in return."
        )

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

        robux_quantity = await determine_exponent(interaction, rinput=robux_quantity)
        if robux_quantity is None:
            return

        async with self.bot.pool.acquire() as conn:
            conn: asqlite_Connection
            item_details = await self.partial_match_for(interaction, for_item, conn)

            if item_details is None:
                return

            try:
                wallet_amt = await self.get_wallet_data_only(interaction.user, conn)
            except TypeError:
                return await respond(interaction=interaction, embed=NOT_REGISTERED)

            # ! For the person sending coins

            coin_check_passing = await self.coin_checks_passing(
                interaction,
                user_checked=interaction.user,
                coin_qty_offered=robux_quantity,
                actual_wallet_amt=wallet_amt
            )

            if not coin_check_passing:
                return

        can_proceed = await self.prompt_coins_for_items(
            interaction,
            coin_sender=interaction.user,
            coin_sender_qty=robux_quantity,
            item_sender=with_who,
            item_sender_qty=item_quantity,
            item_sender_data=item_details,
        )

        async with self.bot.pool.acquire() as conn:
            if not can_proceed:
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
                await self.end_transaction(conn, user_id=interaction.user.id)
                await conn.commit()
                return

        can_proceed = await self.prompt_for_coins(
            interaction,
            item_sender=with_who,
            item_sender_qty=item_quantity,
            item_sender_data=item_details,
            coin_sender=interaction.user,
            coin_sender_qty=robux_quantity
        )

        query = "DELETE FROM transactions WHERE userID IN ($0, $1)"
        async with self.bot.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(query, interaction.user.id, with_who.id)
                if not can_proceed:
                    return

                await self.update_inv_by_id(with_who, -item_quantity, item_id=item_details[0], conn=conn)
                await self.update_inv_by_id(interaction.user, item_quantity, item_id=item_details[0], conn=conn)
                await self.update_wallet_many(
                    conn, 
                    (-robux_quantity, interaction.user.id), 
                    (+robux_quantity, with_who.id)
                )

        embed = discord.Embed(colour=0xFFFFFF).set_footer(text="Thanks for your business.")
        embed.title = "Your Trade Receipt"
        embed.description = (
            f"- {interaction.user.mention} gave {with_who.mention} {CURRENCY} **{robux_quantity:,}**.\n"
            f"- {interaction.user.mention} received **{item_quantity}x** {item_details[-1]} {item_details[1]} in return."
        )

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
            item_details = await self.partial_match_for(interaction, item, conn)
            item2_details = await self.partial_match_for(interaction, for_item, conn)

            if (item_details is None) or (item2_details is None):
                return await respond(
                    interaction, 
                    embed=membed("You did not specify valid items to trade on.")
                )

            if item_details[0] == item2_details[0]:
                return await respond(
                    interaction, 
                    embed=membed(f"You can't trade {item_details[-1]} {item_details[1]}(s) on both sides.")
                )

            # ! For the person sending items
            can_proceed = await self.item_checks_passing(
                interaction, 
                conn,
                user_to_check=interaction.user,
                item_data=item_details,
                item_qty_offered=quantity
            )

            if not can_proceed:
                return

        can_proceed = await self.prompt_items_for_items(
            interaction,
            item_sender=interaction.user,
            item_sender_qty=quantity,
            item_sender_data=item_details,
            item_sender2=with_who,
            item_sender2_qty=for_quantity,
            item_sender2_data=item2_details
        )

        async with self.bot.pool.acquire() as conn:
            if not can_proceed:
                await self.end_transaction(conn, user_id=interaction.user.id)
                await conn.commit()
                return

            # ! For the other person sending items
            can_proceed = await self.item_checks_passing(
                interaction, 
                conn,
                user_to_check=with_who,
                item_data=item2_details,
                item_qty_offered=for_quantity
            )

            if not can_proceed:
                await self.end_transaction(conn, user_id=interaction.user.id)
                await conn.commit()
                return

        can_proceed = await self.prompt_items_for_items(
            interaction,
            item_sender=with_who,
            item_sender_qty=for_quantity,
            item_sender_data=item2_details,
            item_sender2=interaction.user,
            item_sender2_qty=quantity,
            item_sender2_data=item_details
        )

        query = "DELETE FROM transactions WHERE userID IN ($0, $1)"
        async with self.bot.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(query, interaction.user.id, with_who.id)
                if not can_proceed:
                    return

                await self.update_inv_by_id(interaction.user, -quantity, item_details[0], conn)
                await self.update_inv_by_id(with_who, -for_quantity, item2_details[0], conn)
                await conn.executemany(
                    sql="UPDATE inventory SET qty = qty + $0 WHERE userID = $1 AND itemID = $2",
                    seq_of_parameters=[
                        (for_quantity, interaction.user.id, item2_details[0]), 
                        (quantity, with_who.id, item_details[0])
                    ]
                )

        embed = discord.Embed(colour=0xFFFFFF).set_footer(text="Thanks for your business.")
        embed.title = "Your Trade Receipt"
        embed.description = (
            f"- {interaction.user.mention} gave {with_who.mention} **{quantity}x {item_details[-1]} {item_details[1]}**.\n"
            f"- {interaction.user.mention} received **{for_quantity}x {item2_details[-1]} {item2_details[1]}** in return."
        )
        await interaction.followup.send(embed=embed)

    @commands.command(name="freemium", description="Get a free random item.", aliases=('fr',))
    async def free_item(self, ctx: commands.Context) -> None:
        async with self.bot.pool.acquire() as conn:
            rQty = randint(1, 5)

            item, emoji = await self.update_user_inventory_with_random_item(ctx.author.id, conn, rQty)
            await conn.commit()

        await ctx.send(embed=membed(f"Success! You just got **{rQty}x** {emoji} {item}!"))

    showcase = app_commands.Group(
        name="showcase", 
        description="Manage your own item showcase.", 
        allowed_contexts=app_commands.AppCommandContext(guild=True),
        allowed_installs=app_commands.AppInstallationType(guild=True)
    )

    async def delete_missing_showcase_items(
        self, 
        conn: asqlite_Connection, 
        user_id: int, 
        items_to_delete: set | None = None
    ) -> int | None:
        """
        Delete showcase items that a user no longer has. 

        You can pass in pre-defined items as well.

        This does not commit any deletions.
        """
        items_to_delete = items_to_delete or set()
        if not items_to_delete:
            return

        placeholders = ', '.join(f'${i}' for i in range(1, len(items_to_delete)+1))
        query = f"""DELETE FROM showcase WHERE userID = $0 AND itemID IN ({placeholders})"""
        await conn.fetchall(query, user_id, *items_to_delete)
        return len(items_to_delete)

    @app_commands.describe(item=ITEM_DESCRPTION)
    @showcase.command(name="add", description="Add an item to your showcase")
    async def add_showcase_item(self, interaction: discord.Interaction, item: str) -> None:

        async with self.bot.pool.acquire() as conn:
            item_details = await self.partial_match_for(interaction, item, conn)

            if item_details is None:
                return
            item_id, item, ie = item_details
            all_embeds = []

            async with conn.transaction():

                val = await self.delete_missing_showcase_items(conn, interaction.user.id)

                if val:
                    all_embeds.append(membed(SHOWCASE_ITEMS_REMOVED))

                val = await Economy.user_has_item_from_id(interaction.user.id, item_id, conn)

                if not val:
                    all_embeds.append(f"You don't have a single {ie} **{item}**.")
                    return await respond(interaction, ephemeral=True, embeds=all_embeds)

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
            return await respond(interaction, ephemeral=True, embeds=all_embeds)

        all_embeds.append(membed(f"Added {ie} {item} to your showcase!"))
        await respond(interaction, embeds=all_embeds)

    @showcase.command(name="remove", description="Remove an item from your showcase")
    @app_commands.describe(item=ITEM_DESCRPTION)
    async def remove_showcase_item(self, interaction: discord.Interaction, item: str) -> None:

        async with self.bot.pool.acquire() as conn:
            conn: asqlite_Connection

            item_details = await self.partial_match_for(interaction, item, conn)

            if item_details is None:
                return
            item_id, item, ie = item_details

            val = await self.delete_missing_showcase_items(
                conn, 
                interaction.user.id, 
                items_to_delete={item_id,}
            )

            all_embeds = []

            if val and (val > 1):
                all_embeds.append(membed(SHOWCASE_ITEMS_REMOVED))
            await conn.commit()

            all_embeds.append(membed(f"If **{ie} {item}** was in your showcase, it's now been removed."))
            await respond(interaction=interaction, embeds=all_embeds)

    @commands.command(name="showcase", description="Test out your showcase before publishing", aliases=('sc',))
    async def show_showcase_data(self, ctx: commands.Context):
        async with self.bot.pool.acquire() as conn:
            emb = await self.fetch_showdata(ctx.author, conn)
        await ctx.send(embed=emb)

    shop = app_commands.Group(
        name='shop', 
        description='View items available for purchase.', 
        allowed_contexts=app_commands.AppCommandContext(guild=True),
        allowed_installs=app_commands.AppInstallationType(guild=True)
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

        shop_metadata = [
            (
                f"{item[1]} {item[0]} \U00002500 [{CURRENCY} **{item[2]:,}**](https://youtu.be/dQw4w9WgXcQ)", 
                ShopItem(item[0], item[2], item[1], row=i % 2)
            ) 
            for i, item in enumerate(shop_sorted)
        ]

        emb = membed()
        emb.title = "Shop"
        length = 6

        async def get_page_part(page: int) -> tuple[discord.Embed, int]:
            async with self.bot.pool.acquire() as conn:
                wallet = await self.get_wallet_data_only(interaction.user, conn) or 0
            emb.description = f"> You have {CURRENCY} **{wallet:,}**.\n\n"

            offset = (page - 1) * length

            if len(paginator.children) > 2:
                backward_btn, forward_btn = paginator.children[:2]
                paginator.clear_items().add_item(backward_btn).add_item(forward_btn)

            emb.description += "\n".join(
                item_metadata[0] 
                for item_metadata in shop_metadata[offset:offset + length]
            )

            for _, item_btn in shop_metadata[offset:offset + length]:
                item_btn.disabled = wallet < item_btn.cost
                paginator.add_item(item_btn)

            n = paginator.compute_total_pages(len(shop_metadata), length)
            emb.set_footer(text=f"Page {page} of {n}")
            return emb, n

        paginator.get_page = get_page_part
        await paginator.navigate()

    @shop.command(name='sell', description='Sell an item from your inventory', extras={})
    @app_commands.describe(
        item='The name of the item you want to sell.', 
        sell_quantity='The amount of this item to sell. Defaults to 1.'
    )
    async def sell(
        self, 
        interaction: discord.Interaction, 
        item: str, 
        sell_quantity: app_commands.Range[int, 1] = 1
    ) -> None:
        """Sell an item you already own."""
        seller = interaction.user

        async with self.bot.pool.acquire() as conn:
            conn: asqlite_Connection
            item_details = await self.partial_match_for(interaction, item, conn)
            if item_details is None:
                return
            item_id, item_name, ie = item_details

            item_attrs = await conn.fetchone(
                """
                SELECT COALESCE(inventory.qty, 0), cost, sellable
                FROM shop
                LEFT JOIN inventory 
                    ON inventory.itemID = shop.itemID AND inventory.userID = $0
                WHERE shop.itemID = $1
                """, seller.id, item_id
            )

            qty, cost, sellable = item_attrs
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

            multi = await Economy.get_multi_of(user_id=seller.id, multi_type="robux", conn=conn)
            cost = selling_price_algo((cost / 4) * sell_quantity, multi)
            can_proceed = await self.handle_confirm_outcome(
                interaction,
                f"Are you sure you want to sell **{sell_quantity:,}x {ie} {item_name}** for **{CURRENCY} {cost:,}**?",
                setting="selling_confirmations",
                conn=conn
            )

        async with self.bot.pool.acquire() as conn:
            async with conn.transaction():
                if can_proceed is not None:
                    await self.end_transaction(conn, user_id=seller.id)
                    if can_proceed is False:
                        return

                await self.update_inv_new(seller, -sell_quantity, item_name, conn)
                await self.update_bank_new(seller, conn, +cost)

        embed = membed(
            f"{seller.mention} sold **{sell_quantity:,}x {ie} {item_name}** "
            f"and got paid {CURRENCY} **{cost:,}**."
        ).set_footer(text="Thanks for your business.")

        embed.title = f"{seller.display_name}'s Sale Receipt"
        await respond(interaction, embed=embed)

    @app_commands.command(name='item', description='Get more details on a specific item')
    @app_commands.describe(item_name=ITEM_DESCRPTION)
    @app_commands.rename(item_name="name")
    @app_commands.allowed_installs(**CONTEXT_AND_INSTALL)
    @app_commands.allowed_contexts(**CONTEXT_AND_INSTALL)
    async def item(self, interaction: discord.Interaction, item_name: str) -> None:
        """This is a subcommand. Look up a particular item within the shop to get more information about it."""

        async with self.bot.pool.acquire() as conn:
            item_details = await self.partial_match_for(interaction, item_name, conn)
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
            net = await self.calculate_inventory_value(interaction.user, conn)

        their_count, item_type, cost, description, image, rarity, available, sellable, multi = data
        dynamic_text = f"> *{description}*\n\nYou own **{their_count:,}**"

        if their_count:
            amt = ((their_count*cost)/net)*100
            dynamic_text += f" ({amt:.1f}% of your net worth)" if amt >= 0.1 else ""

        em = discord.Embed(
            title=item_name,
            description=dynamic_text, 
            url="https://www.youtube.com",
            colour=RARITY_COLOUR.get(rarity, 0x2B2D31)
        ).set_thumbnail(url=image).set_footer(text=f"{rarity} {item_type}")

        sell_val_orig = int(cost / 4)
        sell_val_multi = selling_price_algo(sell_val_orig, multi)
        em.add_field(
            name="Value",
            inline=False,
            value=(
                f"- buy: {CURRENCY} {cost:,}\n"
                f"- sell: {CURRENCY} {sell_val_orig:,} ({CURRENCY} {sell_val_multi:,} with your {multi}% multi)"
            )
        ).add_field(
            name="Additional Info",
            value=(
                f"- {'can' if sellable else 'cannot'} be sold\n"
                f"- {'can' if available else 'cannot'} purchase in the shop"
            )
        )
        await respond(interaction=interaction, embed=em)

    @commands.command(name='reasons', description='Identify causes of registration errors', aliases=('rs',))
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
                        '- You opted out of the economy.\n'
                        '- The pool connection is outdated and hasn\'t been released yet.\n\n'
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
        new_bankspace, = await conn.fetchone(
            """
            UPDATE accounts 
            SET bankspace = bankspace + $0 
            WHERE userID = $1 
            RETURNING bankspace
            """, expansion, interaction.user.id
        )

        new_amt, = await Economy.update_inv_new(interaction.user, -quantity, "Bank Note", conn)

        embed = membed().set_footer(text=f"{new_amt:,}x bank note left")

        embed.add_field(
            name="Used", 
            value=f"{quantity}x <:BankNote:1263919952562487418> Bank Note"
        ).add_field(
            name="Added Bank Space", 
            value=f"{CURRENCY} {expansion:,}"
        ).add_field(
            name="Total Bank Space", 
            value=f"{CURRENCY} {new_bankspace:,}"
        )

        await conn.commit()
        await respond(interaction=interaction, embed=embed)

    @register_item('Trophy')
    async def flex_via_trophy(interaction: discord.Interaction, quantity: int, _: asqlite_Connection) -> None:
        content = f'\n\nThey have **{quantity}** of them, WHAT A BADASS' if quantity > 1 else ''

        await respond(
            interaction=interaction,
            embed=membed(
                f"{interaction.user.name} is flexing on you all "
                f"with their <:Trophy:1263923814874615930> **~~PEPE~~ TROPHY**{content}"
            )
        )

    @register_item('Bitcoin')
    async def gain_bitcoin_multiplier(interaction: discord.Interaction, _: int, conn: asqlite_Connection) -> None:
        future_expiry = (discord.utils.utcnow() + timedelta(minutes=30)).timestamp()

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
                interaction, 
                embed=membed("You already have a <:Bitcoin:1263919978717908992> Bitcoin multiplier active.")
            )

        await Economy.update_inv_by_id(interaction.user, amount=-1, item_id=21, conn=conn)
        await conn.commit()

        await respond(
            interaction=interaction,
            embed=membed(
                "You just activated a **30 minute** <:Bitcoin:1263919978717908992> Bitcoin multiplier!\n"
                "You'll get 500% more robux from transactions during this time."
            )
        )

        Economy.start_check_for_expiry(interaction)

    @app_commands.command(name="use", description="Use an item you own from your inventory", extras={"exp_gained": 3})
    @app_commands.describe(item=ITEM_DESCRPTION, quantity='Amount of items to use, when possible.')
    @app_commands.allowed_installs(**CONTEXT_AND_INSTALL)
    @app_commands.allowed_contexts(**CONTEXT_AND_INSTALL)
    async def use_item(
        self, 
        interaction: discord.Interaction, 
        item: str, 
        quantity: app_commands.Range[int, 1] = 1
    ) -> discord.WebhookMessage | None:
        """Use a currently owned item."""

        async with self.bot.pool.acquire() as conn:
            conn: asqlite_Connection

            item_details = await self.partial_match_for(interaction, item, conn)

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
                embed=membed(f"You don't have a single {ie} **{item_name}**, therefore cannot use it.")
            )

        qty, = data
        if qty < quantity:
            return await respond(
                interaction=interaction,
                ephemeral=True,
                embed=membed(f"You don't have **{quantity}x {ie} {item_name}**, therefore cannot use this many.")
            )

        handler = item_handlers.get(item_name)
        if handler is None:
            return await respond(
                interaction=interaction,
                ephemeral=True,
                embed=membed(f"{ie} **{item_name}** does not have a use yet.\nWait until it does!")
            )

        async with self.bot.pool.acquire() as conn:
            await handler(interaction, quantity, conn)

    async def start_prestige(self, interaction: discord.Interaction, prestige: int) -> None:
        massive_prompt = dedent(
            """
            Prestiging means losing nearly everything you've ever earned in the currency 
            system in exchange for increasing your 'Prestige Level' 
            and upgrading your status.
            **Things you will lose**:
            - All of your items/showcase
            - All of your robux
            - Your levels and XP
            Anything not mentioned in this list will not be lost.
            Are you sure you want to prestige?
            """
        )
        can_proceed = await self.handle_confirm_outcome(interaction, massive_prompt)

        async with self.bot.pool.acquire() as conn:
            await self.end_transaction(conn, user_id=interaction.user.id)
            if can_proceed:
                await conn.execute("DELETE FROM inventory WHERE userID = ?", interaction.user.id)
                await conn.execute(
                    """
                    UPDATE accounts 
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

    @app_commands.command(name="prestige", description="Sacrifice currency stats in exchange for incremental perks")
    @app_commands.allowed_installs(**CONTEXT_AND_INSTALL)
    @app_commands.allowed_contexts(**CONTEXT_AND_INSTALL)
    async def prestige(self, interaction: discord.Interaction) -> None:
        """Sacrifice a portion of your currency stats in exchange for incremental perks."""

        conn = await self.bot.pool.acquire()
        data = await conn.fetchone(
            """
            SELECT 
                prestige, 
                level, 
                (wallet + bank) AS total_robux 
            FROM accounts 
            WHERE userID = $0
            """, interaction.user.id
        )

        if data is None:
            await self.bot.pool.release(conn)
            return await interaction.response.send_message(embed=self.not_registered, ephemeral=True)

        prestige, actual_level, actual_robux = data

        if prestige == 10:
            await self.bot.pool.release(conn)
            return await interaction.response.send_message(
                ephemeral=True,
                embed=membed(
                    "You've reached the highest prestige!\n"
                    "No more perks can be obtained from this command."
                )
            )

        req_robux = (prestige + 1) * 24_000_000
        req_level = (prestige + 1) * 35
        met_check = (actual_robux >= req_robux) and (actual_level >= req_level)

        if met_check:
            await self.bot.pool.release(conn)
            return await self.start_prestige(interaction, prestige)
        await self.bot.pool.release(conn)

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
                f"<:replyBranchExt:1263923237016834249> {CURRENCY} {actual_robux:,}/{req_robux:,}\n"
                f"<:replyBranch:1263923209921757224> {generate_progress_bar(actual_robux_progress)} "
                f"` {int(actual_robux_progress):,}% `\n\n"
                f"**Level Required**\n"
                f"<:replyBranchExt:1263923237016834249> {actual_level:,}/{req_level:,}\n"
                f"<:replyBranch:1263923209921757224> {generate_progress_bar(actual_level_progress)} "
                f"` {int(actual_level_progress):,}% `"
            )
        ).set_thumbnail(url=emoji.url).set_footer(text="Imagine thinking you can prestige already.")

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name='profile', description='View user information and other stats')
    @app_commands.describe(user='The user whose profile you want to see.')
    @app_commands.allowed_installs(**CONTEXT_AND_INSTALL)
    @app_commands.allowed_contexts(**CONTEXT_AND_INSTALL)
    async def find_profile(
        self, 
        interaction: discord.Interaction, 
        user: USER_ENTRY | None = None
    ) -> None:
        """View your profile within the economy."""

        await interaction.response.send_message(
            embed=membed(
                "We're working on custom profiles so this command is disabled for now.\n"
                "-# Track our progress [here](https://github.com/SGA-A/c2c/issues/110)."
            )
        )

    @app_commands.command(name='highlow', description='Guess the number. Jackpot wins big!', extras={"exp_gained": 3})
    @app_commands.describe(robux=ROBUX_DESCRIPTION)
    @app_commands.allowed_installs(**CONTEXT_AND_INSTALL)
    @app_commands.allowed_contexts(**CONTEXT_AND_INSTALL)
    async def highlow(self, interaction: discord.Interaction, robux: str) -> None:
        """
        Guess the number. The user must guess if the clue the bot gives is higher,
        lower or equal to the actual number.
        """

        async with self.bot.pool.acquire() as conn:
            conn: asqlite_Connection

            wallet_amt = await conn.fetchone("SELECT wallet FROM accounts WHERE userID = $0", interaction.user.id)
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
            await self.declare_transaction(conn, user_id=interaction.user.id)

        await HighLow(interaction, bet=robux).start()

    @app_commands.command(name='slots', description='Try your luck on a slot machine', extras={"exp_gained": 3})
    @app_commands.describe(robux=ROBUX_DESCRIPTION)
    @app_commands.allowed_installs(**CONTEXT_AND_INSTALL)
    @app_commands.allowed_contexts(**CONTEXT_AND_INSTALL)
    async def slots(self, interaction: discord.Interaction, robux: str) -> None:
        """Play a round of slots. At least one matching combination is required to win."""


        # --------------- Checks before betting i.e. has keycard, meets bet constraints. -------------
        async with self.bot.pool.acquire() as conn:
            conn: asqlite_Connection
            has_keycard = await self.user_has_item_from_id(interaction.user.id, item_id=1, conn=conn)
            slot_stuff = await conn.fetchone("SELECT slotw, slotl, wallet FROM accounts WHERE userID = $0", interaction.user.id)
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

            async with self.bot.pool.acquire() as conn:
                updated = await self.update_bank_three_new(
                    interaction.user, 
                    conn, 
                    "slotwa", amount_after_multi, 
                    "wallet", amount_after_multi, 
                    "slotw", 1
                )
                await conn.commit()

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

            async with self.bot.pool.acquire() as conn:
                updated = await self.update_bank_three_new(
                    interaction.user, 
                    conn, 
                    "slotla", robux, 
                    "wallet", -robux, 
                    "slotl", 1
                )
                await conn.commit()

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
    @app_commands.describe(member='The user whose inventory you want to see.')
    @app_commands.allowed_installs(**CONTEXT_AND_INSTALL)
    @app_commands.allowed_contexts(**CONTEXT_AND_INSTALL)
    async def inventory(
        self, 
        interaction: discord.Interaction, 
        member: USER_ENTRY | None = None
    ) -> None:
        """View your inventory or another player's inventory."""
        member = member or interaction.user

        async with self.bot.pool.acquire() as conn:
            conn: asqlite_Connection

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

        em = membed().set_author(
            name=f"{member.display_name}'s Inventory", 
            icon_url=member.display_avatar.url
        )
        paginator = RefreshPagination(interaction)
        paginator.length = 8

        async def get_page_part(force_refresh: bool | None = None) -> discord.Embed:
            """Helper function to determine what page of the paginator we're on."""
            nonlocal owned_items
            if force_refresh:
                async with self.bot.pool.acquire() as conn:
                    owned_items = await conn.fetchall(query, member.id)

            paginator.reset_index(owned_items)
            if not owned_items:
                em.set_footer(text="Empty")
                return em

            offset = (paginator.index - 1) * paginator.length
            em.description = "\n".join(
                f"{item[1]} **{item[0]}** \U00002500 {item[2]:,}" 
                for item in owned_items[offset:offset + paginator.length]
            )

            em.set_footer(text=f"Page {paginator.index} of {paginator.total_pages}")
            return em

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

    async def do_tiles(self, interaction: discord.Interaction, job_name: str) -> None:

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
        allowed_contexts=app_commands.AppCommandContext(guild=True),
        allowed_installs=app_commands.AppInstallationType(guild=True)
    )

    @work.command(name="shift", description="Fulfill a shift at your current job", extras={"exp_gained": 3})
    async def shift_at_work(self, interaction: discord.Interaction) -> None:
        async with self.bot.pool.acquire() as conn:
            conn: asqlite_Connection

            data = await conn.fetchone(
                """
                SELECT accounts.job, COALESCE(cooldowns.until, 0.0)
                FROM accounts
                LEFT JOIN cooldowns
                ON accounts.userID = cooldowns.userID AND cooldowns.cooldown = $0
                WHERE accounts.userID = $1
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
                ncd = (discord.utils.utcnow() + timedelta(minutes=40)).timestamp()

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
                SELECT accounts.job, COALESCE(cooldowns.until, 0.0)
                FROM accounts
                LEFT JOIN cooldowns
                ON accounts.userID = cooldowns.userID AND cooldowns.cooldown = $1
                WHERE accounts.userID = $0
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

            ncd = (discord.utils.utcnow() + timedelta(days=2)).timestamp()
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
            data = await conn.fetchone(
                """
                SELECT accounts.job, COALESCE(cooldowns.until, 0.0)
                FROM accounts
                INNER JOIN cooldowns
                    ON accounts.userID = cooldowns.userID AND cooldowns.cooldown = $1
                WHERE accounts.userID = $0
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
            ncd = (discord.utils.utcnow() + timedelta(days=2)).timestamp()

            async with self.bot.pool.acquire() as conn:
                await self.change_job_new(interaction.user, conn, job_name='None')
                await self.update_cooldown(
                    conn, 
                    user_id=interaction.user.id, 
                    cooldown_type="job_change", 
                    new_cd=ncd
                )

    @app_commands.command(name="balance", description="Get someone's balance. Wallet, bank, and net worth.")
    @app_commands.describe(user='The user to find the balance of.')
    @app_commands.allowed_installs(**CONTEXT_AND_INSTALL)
    @app_commands.allowed_contexts(**CONTEXT_AND_INSTALL)
    async def find_balance(
        self, 
        interaction: discord.Interaction, 
        user: USER_ENTRY | None = None
    ) -> None:
        user = user or interaction.user

        balance_view = BalanceView(interaction, viewing=user)
        balance = await balance_view.fetch_balance(interaction)

        await interaction.response.send_message(embed=balance, view=balance_view)

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

            next_cd = discord.utils.utcnow() + timedelta(weeks=weeks_away)
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
    @app_commands.allowed_installs(**CONTEXT_AND_INSTALL)
    @app_commands.allowed_contexts(**CONTEXT_AND_INSTALL)
    async def weekly(self, interaction: discord.Interaction) -> None:
        await self.do_weekly_or_monthly(interaction, "weekly", weeks_away=1)

    @app_commands.command(description="Get a monthly injection of robux")
    @app_commands.allowed_installs(**CONTEXT_AND_INSTALL)
    @app_commands.allowed_contexts(**CONTEXT_AND_INSTALL)
    async def monthly(self, interaction: discord.Interaction) -> None:
        await self.do_weekly_or_monthly(interaction, "monthly", weeks_away=4)

    @app_commands.command(description="Get a yearly injection of robux")
    @app_commands.allowed_installs(**CONTEXT_AND_INSTALL)
    @app_commands.allowed_contexts(**CONTEXT_AND_INSTALL)
    async def yearly(self, interaction: discord.Interaction) -> None:
        await self.do_weekly_or_monthly(interaction, "yearly", weeks_away=52)

    @app_commands.command(name="resetmydata", description="Opt out of the virtual economy, deleting all of your data")
    @app_commands.describe(member='The player to remove all of the data of. Defaults to you.')
    @app_commands.allowed_installs(**CONTEXT_AND_INSTALL)
    @app_commands.allowed_contexts(**CONTEXT_AND_INSTALL)
    async def discontinue_bot(self, interaction: discord.Interaction, member: USER_ENTRY | None = None) -> None:
        """Opt out of the virtual economy and delete all of the user data associated."""

        member = member or interaction.user

        if (member.id != interaction.user.id) and (interaction.user.id not in self.bot.owner_ids):
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
            await conn.commit()

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
    @app_commands.describe(robux=ROBUX_DESCRIPTION)
    @app_commands.allowed_installs(**CONTEXT_AND_INSTALL)
    @app_commands.allowed_contexts(**CONTEXT_AND_INSTALL)
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

            bank_amt = await conn.fetchone("SELECT bank FROM accounts WHERE userID = $0", user.id)
            if bank_amt is None:
                return await interaction.response.send_message(embed=self.not_registered, ephemeral=True)
            bank_amt, = bank_amt

            query = (
                """
                UPDATE accounts
                SET 
                    wallet = wallet + $0,
                    bank = bank - $0
                WHERE userID = $1
                RETURNING wallet, bank
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
                    name="<:withdraw:1263924204986699938> Withdrawn", 
                    value=f"{CURRENCY} {bank_amt:,}", 
                    inline=False
                ).add_field(
                    name="Current Wallet Balance", value=f"{CURRENCY} {wallet_new:,}"
                ).add_field(name="Current Bank Balance", value=f"{CURRENCY} {bank_new:,}")

                return await interaction.response.send_message(embed=embed)

            if actual_amount > bank_amt:
                embed.description = f"You only have {CURRENCY} **{bank_amt:,}** in your bank right now."
                return await interaction.response.send_message(embed=embed, ephemeral=True)

            new_data = await conn.fetchone(query, actual_amount, user.id)
            await conn.commit()
            wallet_new, bank_new = new_data

            embed.add_field(
                name="<:withdraw:1263924204986699938> Withdrawn", 
                value=f"{CURRENCY} {actual_amount:,}", 
                inline=False
            ).add_field(
                name="Current Wallet Balance", value=f"{CURRENCY} {wallet_new:,}"
            ).add_field(
                name="Current Bank Balance", value=f"{CURRENCY} {bank_new:,}"
            )

            await interaction.response.send_message(embed=embed)

    @app_commands.command(name='deposit', description="Deposit robux into your bank account")
    @app_commands.describe(robux=ROBUX_DESCRIPTION)
    @app_commands.allowed_installs(**CONTEXT_AND_INSTALL)
    @app_commands.allowed_contexts(**CONTEXT_AND_INSTALL)
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
                SELECT 
                    wallet, 
                    bank, 
                    bankspace 
                FROM accounts 
                WHERE userID = $0
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
                """
                UPDATE accounts
                SET 
                    wallet = wallet - $0,
                    bank = bank + $0
                WHERE userID = $1
                RETURNING wallet, bank
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
                    name="<:deposit:1263920154648121375> Deposited", 
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
                name="<:deposit:1263920154648121375> Deposited", 
                value=f"{CURRENCY} {actual_amount:,}", 
                inline=False
            )

            embed.add_field(name="Current Wallet Balance", value=f"{CURRENCY} {wallet_new:,}")
            embed.add_field(name="Current Bank Balance", value=f"{CURRENCY} {bank_new:,}")
            await interaction.response.send_message(embed=embed)

    leaderboard = app_commands.Group(
        name="leaderboard",
        description="Rank users in various different ways.",
        allowed_contexts=app_commands.AppCommandContext(guild=True),
        allowed_installs=app_commands.AppInstallationType(guild=True)
    )

    @leaderboard.command(name='stats', description='Rank users based on various stats')
    @app_commands.describe(stat="The stat you want to see.")
    async def get_stat_lb(
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

        paginator = ExtendedLeaderboard(interaction, chosen_option=stat)
        await paginator.create_lb()

        await paginator.navigate()

    @leaderboard.command(name="item", description="Rank users based on an item count")
    @app_commands.describe(item=ITEM_DESCRPTION)
    async def get_item_lb(self, interaction: discord.Interaction, item: str):
        async with self.bot.pool.acquire() as conn:
            item_details = await self.partial_match_for(interaction, item, conn)
            if item_details is None:
                return
            item_id, item_name, _ = item_details
            paginator = Leaderboard(interaction, chosen_option=item_name)
            thumb_url, = await conn.fetchone("SELECT image FROM shop WHERE itemID = $0", item_id)
            await paginator.create_lb(conn, item_id)

        lb = membed().set_thumbnail(url=thumb_url)
        lb.timestamp = discord.utils.utcnow()
        lb.title = f"{item_name} Global Leaderboard"

        async def get_page_part(force_refresh: bool | None = None) -> discord.Embed:
            if force_refresh:
                async with self.bot.pool.acquire() as conn:
                    await paginator.create_lb(conn, item_id)

            paginator.reset_index(paginator.data)
            if not paginator.data:
                lb.set_footer(text="Empty")
                return lb

            offset = ((paginator.index- 1) * paginator.length)
            lb.description = "\n".join(paginator.data[offset:offset+paginator.length])
            lb.set_footer(text=f"Page {paginator.index} of {paginator.total_pages}")
            return lb

        paginator.get_page = get_page_part
        await paginator.navigate()

    @app_commands.command(description="Attempt to steal from someone's pocket", extras={"exp_gained": 4})
    @app_commands.describe(user='The user you want to rob money from.')
    @app_commands.allowed_installs(**CONTEXT_AND_INSTALL)
    @app_commands.allowed_contexts(**CONTEXT_AND_INSTALL)
    async def rob(self, interaction: discord.Interaction, user: discord.Member) -> None:
        """Rob someone else."""

        embed = membed()
        if interaction.user.id == user.id:
            embed.description = 'Seems pretty foolish to steal from yourself'
            return await interaction.response.send_message(embed=embed)
        elif user.bot:
            embed.description = 'You are not allowed to steal from bots, back off my kind'
            return await interaction.response.send_message(embed=embed)
        else:
            async with self.bot.pool.acquire() as conn:
                conn: asqlite_Connection

                if not (await self.can_call_out_either(interaction.user, user, conn)):
                    embed.description = f'Either you or {user.mention} are not registered.'
                    return await interaction.response.send_message(embed=embed, ephemeral=True)

                prim_d = await conn.fetchone(
                    """
                    SELECT wallet, job, bounty, settings.value
                    FROM accounts 
                    LEFT JOIN settings 
                        ON accounts.userID = settings.userID AND settings.setting = 'passive_mode'
                    WHERE accounts.userID = $0
                    """, interaction.user.id
                )

                if prim_d[-1]:
                    embed.description = "You are in passive mode! If you want to rob, turn that off!"
                    return await interaction.response.send_message(embed=embed)

                host_d = await conn.fetchone(
                    """
                    SELECT wallet, job, settings.value
                    FROM accounts
                    LEFT JOIN settings 
                        ON accounts.userID = settings.userID AND settings.setting = 'passive_mode' 
                    WHERE accounts.userID = $0
                    """, user.id
                )

                if host_d[-1]:
                    embed.description = f"{user.mention} is in passive mode, you can't rob them!"
                    return await interaction.response.send_message(embed=embed)

                if host_d[0] < 1_000_000:
                    embed.description = f"{user.mention} doesn't even have {CURRENCY} **1,000,000**, not worth it."
                    return await interaction.response.send_message(embed=embed)

                if prim_d[0] < 10_000_000:
                    embed.description = f"You need at least {CURRENCY} **10,000,000** in your wallet to rob someone."
                    return await interaction.response.send_message(embed=embed)

                result = choices((0, 1), weights=(49, 51), k=1)

                if not result[0]:
                    emote = choice(
                        (
                            "<a:kekRealize:970295657233539162>", 
                            "<:smhlol:1160157952410386513>", 
                        )
                    )

                    fine = randint(1, prim_d[0])
                    embed.description = (
                        f'You were caught lol {emote}\n'
                        f'You paid {user.mention} {CURRENCY} **{fine:,}**.'
                    )

                    b = prim_d[-1]
                    if b:
                        fine += b
                        embed.description += (
                            "\n\n**Bounty Status:**\n"
                            f"{user.mention} was also given your bounty of **{CURRENCY} {b:,}**."
                        )

                    await self.update_wallet_many(
                        conn, 
                        (fine, user.id), 
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
                    (-amt_stolen, user.id), 
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
    @app_commands.describe(user='The user to attempt to bankrob.')
    @app_commands.allowed_installs(**CONTEXT_AND_INSTALL)
    @app_commands.allowed_contexts(**CONTEXT_AND_INSTALL)
    async def bankrob_the_user(self, interaction: discord.Interaction, user: discord.Member) -> None:
        """Rob someone else's bank."""
        starter_id = interaction.user.id
        user_id = user.id

        if user_id == starter_id:
            return await interaction.response.send_message(embed=membed("You can't bankrob yourself."))
        if user.bot:
            return await interaction.response.send_message(embed=membed("You can't bankrob bots."))

        return await interaction.response.send_message(embed=membed("This feature is in development."))

    @app_commands.command(name='coinflip', description='Bet your robux on a coin flip', extras={"exp_gained": 3})
    @app_commands.describe(bet_on='The side of the coin you bet it will flip on.', robux=ROBUX_DESCRIPTION)
    @app_commands.rename(bet_on="side")
    @app_commands.allowed_installs(**CONTEXT_AND_INSTALL)
    @app_commands.allowed_contexts(**CONTEXT_AND_INSTALL)
    async def coinflip(self, interaction: discord.Interaction, bet_on: Literal["Heads", "Tails"], robux: str) -> None:
        """Flip a coin and make a bet on what side of the coin it flips to."""

        user = interaction.user
        bet_on = bet_on.lower()

        async with self.bot.pool.acquire() as conn:
            conn: asqlite_Connection

            wallet_amt = await conn.fetchone(
                """
                SELECT wallet
                FROM accounts
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

            embed.colour = discord.Colour.brand_green()
            embed.set_author(
                icon_url=user.display_avatar.url, 
                name=f"{user.name}'s winning coinflip game"
            ).set_footer(text=f"Multiplier: {their_multi}%")

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
    @app_commands.describe(robux=ROBUX_DESCRIPTION)
    @app_commands.allowed_installs(**CONTEXT_AND_INSTALL)
    @app_commands.allowed_contexts(**CONTEXT_AND_INSTALL)
    async def play_blackjack(self, interaction: discord.Interaction, robux: str) -> None:
        """Play a round of blackjack with the bot. Win by reaching 21 or a score higher than the bot without busting."""

        # ------ Check the user is registered or already has an ongoing game ---------

        async with self.bot.pool.acquire() as conn:
            wallet_amt = await conn.fetchone(
                """
                SELECT wallet
                FROM accounts
                WHERE userID = $0
                """, interaction.user.id
            )

            if wallet_amt is None:
                return await interaction.response.send_message(embed=self.not_registered, ephemeral=True)
            has_keycard = await self.user_has_item_from_id(interaction.user.id, item_id=1, conn=conn)

        # ----------- Check what the bet amount is, converting where necessary -----------

        wallet_amt, = wallet_amt
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

        await self.declare_transaction(conn, user_id=interaction.user.id)
        shallow_pv = [display_user_friendly_card_format(number) for number in player_hand]
        shallow_dv = [display_user_friendly_card_format(number) for number in dealer_hand]

        self.bot.games[interaction.user.id] = (deck, player_hand, dealer_hand, shallow_dv, shallow_pv, namount)

        initial = membed(
            f"The game has started. May the best win.\n"
            f"`{CURRENCY} ~{format_number_short(namount)}` is up for grabs on the table."
        ).add_field(
            name=f"{interaction.user.name} (Player)", 
            value=f"**Cards** - {' '.join(shallow_pv)}\n**Total** - `{player_sum}`"
        ).add_field(
            name=f"{self.bot.user.name} (Dealer)", 
            value=f"**Cards** - {shallow_dv[0]} `?`\n**Total** - ` ? `"
        ).set_author(
            name=f"{interaction.user.name}'s blackjack game",
            icon_url=interaction.user.display_avatar.url
        ).set_footer(text="K, Q, J = 10  |  A = 1 or 11")

        await interaction.response.send_message(
            embed=initial, 
            view=BlackjackUi(interaction)
        )

    async def do_wallet_checks(
        self, 
        interaction: discord.Interaction,  
        wallet_amount: int, 
        exponent_amount : str | int,
        has_keycard: bool = False
    ) -> int | None:
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
                        f"These values can increase when you acquire a <:Keycard:1263922058220408872> Keycard."
                    )
                )
        return amount

    @app_commands.command(name="bet", description="Bet your robux on a dice roll", extras={"exp_gained": 3})
    @app_commands.describe(robux=ROBUX_DESCRIPTION)
    @app_commands.allowed_installs(**CONTEXT_AND_INSTALL)
    @app_commands.allowed_contexts(**CONTEXT_AND_INSTALL)
    async def bet(self, interaction: discord.Interaction, robux: str) -> None:
        """Bet your robux on a gamble to win or lose robux."""

        # --------------- Contains checks before betting i.e. has keycard, meets bet constraints. -------------
        async with self.bot.pool.acquire() as conn:
            conn: asqlite_Connection

            data = await conn.fetchone(
                """
                SELECT wallet, betw, betl
                FROM accounts 
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
                badges.add("<:Keycard:1263922058220408872>")

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
                ).set_footer(text=f"Multiplier: {pmulti:,}%")

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
        query = (
            """
            SELECT itemName
            FROM shop
            INNER JOIN inventory ON shop.itemID = inventory.itemID
            WHERE LOWER(itemName) LIKE '%' || $0 || '%' AND userID = $1
            LIMIT 25
            """
        )

        async with self.bot.pool.acquire() as conn:
            options = await conn.fetchall(query, f'%{current.lower()}%', interaction.user.id)

        return [app_commands.Choice(name=option[0], value=option[0]) for option in options]

    @add_showcase_item.autocomplete('item')
    async def owned_not_in_showcase_lookup(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:

        query = (
            """
            SELECT itemName
            FROM shop
            INNER JOIN inventory ON shop.itemID = inventory.itemID
            LEFT JOIN showcase ON shop.itemID = showcase.itemID
            WHERE LOWER(itemName) LIKE '%' || ? || '%' 
                AND showcase.itemID IS NULL 
                AND inventory.userID = ?
            LIMIT 25
            """
        )

        async with self.bot.pool.acquire() as conn:
            conn: asqlite_Connection
            results = await conn.fetchall(query, (current.lower(), interaction.user.id))

        return [
            app_commands.Choice(name=result[0], value=result[0])
            for result in results
        ]

    @remove_showcase_item.autocomplete('item')
    async def showcase_items_lookup(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        query = (
            """
            SELECT itemName
            FROM shop
            INNER JOIN showcase ON shop.itemID = showcase.itemID AND showcase.userID = ?
            WHERE LOWER(itemName) LIKE '%' || ? || '%'
            """
        )

        async with self.bot.pool.acquire() as conn:
            options = await conn.fetchall(query, (interaction.user.id, current.lower()))

        return [app_commands.Choice(name=option[0], value=option[0]) for option in options]

    @item.autocomplete('item_name')
    @get_item_lb.autocomplete('item')
    @trade_coins_for_items.autocomplete('for_item')
    @trade_items_for_items.autocomplete('for_item')
    async def item_lookup(self, _: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        query = (
            """
            SELECT itemName 
            FROM shop
            WHERE LOWER(itemName) LIKE '%' || $0 || '%'
            LIMIT 25
            """
        )

        async with self.bot.pool.acquire() as conn:
            options = await conn.fetchall(query, f'%{current.lower()}%')

        return [app_commands.Choice(name=option[0], value=option[0]) for option in options]

    @view_user_settings.autocomplete('setting')
    async def setting_lookup(self, _: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        query = (
            """
            SELECT 
                setting, 
                REPLACE(setting, '_', ' ') AS formatted_setting 
            FROM settings_descriptions
            WHERE LOWER(setting) LIKE '%' || $0 || '%'
            """
        )

        async with self.bot.pool.acquire() as conn:
            results = await conn.fetchall(query, f'%{current.lower()}%')

        return [
            app_commands.Choice(name=result[1].title(), value=result[0])
            for result in results
        ]



async def setup(bot: commands.Bot) -> None:
    """Setup function to initiate the cog."""
    await bot.add_cog(Economy(bot))
