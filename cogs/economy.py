"""The virtual economy system of the bot."""
from asyncio import sleep
from string import ascii_letters, digits
from shelve import open as open_shelve
from re import search
from ImageCharts import ImageCharts
from discord.ext import commands, tasks
from math import floor, ceil
from pytz import timezone
from pluralizer import Pluralizer
from discord import app_commands, SelectOption
from asqlite import Connection as asqlite_Connection
from traceback import print_exception


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


from other.utilities import (
    datetime_to_string, 
    string_to_datetime, 
    labour_productivity_via
)


import discord
import datetime
import aiofiles

from other.pagination import Pagination, PaginationItem, PaginationSimple


def membed(custom_description: str) -> discord.Embed:
    """Quickly construct an embed with a custom description using the preset."""
    membedder = discord.Embed(colour=0x2B2D31, description=custom_description)
    return membedder


def swap_elements(x, index1, index2) -> None:
    """Swap two elements in place given their indices, return None.
    
    lst: the list to swap elements in
    index1: the index of the element you want to swap
    index2: the index of the element you want to swap it with
    """

    x[index1], x[index2] = x[index2], x[index1]


async def economy_check(
        interaction: discord.Interaction, 
        original: discord.Member
    ) -> bool:
    """Shared interaction check common amongst most interactions."""
    if original != interaction.user:
        await interaction.response.send_message(
            embed=membed(f"This menu is controlled by {original.mention}."),
            ephemeral=True,
            delete_after=5.0
        )
        return False
    return True


def number_to_ordinal(n):
    """Convert 01 to 1st, 02 to 2nd etc."""
    if 10 <= n % 100 <= 20:
        return f"{n}th"
    
    suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
    return f"{n}{suffix}"


"""ALL VARIABLES AND CONSTANTS FOR THE ECONOMY ENVIRONMENT"""

BANK_TABLE_NAME = 'bank'
SLAY_TABLE_NAME = "slay"
INV_TABLE_NAME = "inventory"
COOLDOWN_TABLE_NAME = "cooldowns"
MIN_BET_KEYCARD = 500_000
MAX_BET_KEYCARD = 15_000_000
MIN_BET_WITHOUT = 100_000
MAX_BET_WITHOUT = 10_000_000
WARN_FOR_CONCURRENCY = "You are already in the middle of a transaction. Please finish that first."
ROBUX_DESCRIPTION = 'Can be a constant number like "1234" or a shorthand (max, all, 1e6).'
APP_GUILDS_ID = [829053898333225010, 780397076273954886]
DOWN = True
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
SERVER_MULTIPLIERS = {
    829053898333225010: 120,
    780397076273954886: 160
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
ARROW = "<:arrowe:1180428600625877054>"
CURRENCY = '\U000023e3'
PREMIUM_CURRENCY = '<:robuxpremium:1174417815327998012>'
STICKY_MESSAGE = "> \U0001f4cc This command is undergoing changes!\n\n"
DOWNM = membed('This command is currently outdated and will be made available at a later date.')
NOT_REGISTERED = membed('Could not find an account associated with the user provided.')
active_sessions = dict()
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


def make_plural(word, count):
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

    if abs(number) < 1e3:
        return str(number)
    elif abs(number) < 1e6:
        return '{:.1f}K'.format(number / 1e3)
    elif abs(number) < 1e9:
        return '{:.1f}M'.format(number / 1e6)
    elif abs(number) < 1e12:
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


def determine_exponent(rinput: str) -> str | int:
    """Finds out what the exponential value entered is equivalent to in numerical form. (e.g, 1e6)

    Can handle normal integers and "max"/"all" is always returned 'as-is', not converted to numerical form."""

    def is_exponential(val: str) -> bool:
        """Is the input an exponential input?"""
        return 'e' in val

    rinput = rinput.lower()

    if rinput in {"max", "all"}:
        return rinput

    if is_exponential(rinput):
        before_e_str, after_e_str = map(str, rinput.split('e'))
        before_e = float(before_e_str)
        ten_exponent = min(int(after_e_str), 30)
        actual_value = before_e * (10 ** ten_exponent)
    else:
        try:
            rinput = rinput.translate(str.maketrans('', '', ','))
            actual_value = int(rinput)
        except ValueError:
            return rinput

    return floor(abs(actual_value))


def generate_slot_combination():
    """A slot machine that generates and returns one row of slots."""

    weights = [
        (800, 1000, 800, 100, 900, 800, 1000, 800, 800),
        (800, 1000, 800, 100, 900, 800, 1000, 800, 800),
        (800, 1000, 800, 100, 900, 800, 1000, 800, 800)]

    slot_combination = ''.join(choices(SLOTS, weights=w, k=1)[0] for w in weights)
    return slot_combination


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


def get_profile_key_value(key: str) -> Any:
    """Fetch a profile key (attribute) from the database. Returns None if no key is found."""
    with open_shelve("C:\\Users\\georg\\Documents\\c2c\\db-shit\\profile_mods") as dbmr:
        return dbmr.get(key)


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


def display_user_friendly_card_format(number: int, /):
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


def modify_profile(typemod: Literal["update", "create", "delete"], key: str, new_value: Any):
    """Modify custom profile attributes (or keys) of any given discord user.
    If "delete" is used on a key that does not exist, returns ``0``
    :param typemod: type of modification to the profile.
    Could be ``update`` to update an already existing key, or ``create`` to create a new key or ``delete``
    to delete a key.
    :param key: The key to modify/delete.
    :param new_value: The new value to replace the old value with. For a typemod of ``delete``,
    this argument will not matter at all, since only the key name is required to delete a key."""
    with open_shelve("C:\\Users\\georg\\Documents\\c2c\\db-shit\\profile_mods") as dbm:
        match typemod:
            case "update" | "create":
                dbm.update({f'{key}': new_value})
                return dict(dbm)
            case "delete":
                try:
                    del dbm[f"{key}"]
                except KeyError:
                    return 0
            case _:
                return "invalid type of modification value entered"


async def add_command_usage(user_id: int, command_name: str, conn: asqlite_Connection) -> int:
    """Add command usage to db. Only include the parent name if it is a subcommand."""
    
    value = await conn.fetchone(
        """
        INSERT INTO command_uses (userID, cmd_name, cmd_count)
        VALUES (?, ?, 1)
        ON CONFLICT(userID, cmd_name) DO UPDATE SET cmd_count = cmd_count + 1 
        RETURNING cmd_count
        """, (user_id, command_name)
    )

    return value[0]


async def total_commands_used_by_user(user_id: int, conn: asqlite_Connection) -> int:
    """
    Select all records for the given user_id and sum up the command_count.
    
    This will always return a value.
    """

    total = await conn.fetchone(
        """
        SELECT COALESCE(SUM(cmd_count), 0) FROM command_uses
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
    
    if fav is None:
        return "-"
    
    return fav[0]



class DepositOrWithdraw(discord.ui.Modal):
    def __init__(self, *, title: str = ..., default_val: int, conn: asqlite_Connection, 
                 message: discord.InteractionMessage, view_children) -> None:
        self.their_default = default_val
        self.conn = conn
        self.message = message
        self.view_children = view_children  #  note this is the view itself
        self.amount.default = f"{self.their_default:,}"  # access its children via 
        super().__init__(title=title, timeout=120.0)  # self.view_children.children

    amount = discord.ui.TextInput(label="Amount", min_length=1, max_length=30)

    def checks(self, bank, wallet, any_bankspace_left):
        self.view_children.children[0].disabled = (bank == 0)
        self.view_children.children[1].disabled = (wallet == 0) or (any_bankspace_left == 0)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        val = determine_exponent(self.amount.value.replace(",", ""))
        val = int(val)

        if not val:
            return await interaction.response.send_message(
                embed=membed("You need to provide a positive number as your amount."),
                ephemeral=True,
                delete_after=3.0
        )
        
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

            data = await self.conn.execute(
                """
                UPDATE bank 
                SET bank = bank + ?, wallet = wallet + ? 
                WHERE userID = ? 
                RETURNING wallet, bank, bankspace
                """, 
                (-val, val, interaction.user.id)
            )

            await self.conn.commit()
            data = await data.fetchone()

            prcnt_full = (data[1] / data[2]) * 100

            embed.set_field_at(0, name="Wallet", value=f"{CURRENCY} {data[0]:,}")
            embed.set_field_at(1, name="Bank", value=f"{CURRENCY} {data[1]:,}")
            embed.set_field_at(2, name="Bankspace", value=f"{CURRENCY} {data[2]:,} ({prcnt_full:.2f}% full)")
            embed.timestamp = discord.utils.utcnow()

            self.checks(data[1], data[0], data[2]-data[1])
            return await interaction.response.edit_message(embed=embed, view=self.view_children)
        
        # ! Deposit Branch
        
        if val > self.their_default:
            return await interaction.response.send_message(
                embed=membed(
                    "Either one (or both) of the following is true:\n" 
                    "1. You only have don't have that much money in your wallet.\n"
                    "2. You don't have enough bankspace to deposit that amount."),
                ephemeral=True, delete_after=10.0)

        updated = await self.conn.execute(
            "UPDATE bank SET bank = bank + ?, wallet = wallet + ? WHERE userID = ? "
            "RETURNING wallet, bank, bankspace", 
            (val, -val, interaction.user.id))
              
        await self.conn.commit()
        updated = await updated.fetchone()
        prcnt_full = (updated[1] / updated[2]) * 100

        embed.set_field_at(0, name="Wallet", value=f"{CURRENCY} {updated[0]:,}")
        embed.set_field_at(1, name="Bank", value=f"{CURRENCY} {updated[1]:,}")
        embed.set_field_at(2, name="Bankspace", value=f"{CURRENCY} {updated[2]:,} ({prcnt_full:.2f}% full)")
        embed.timestamp = discord.utils.utcnow()

        self.checks(updated[1], updated[0], updated[2]-updated[1])
        await interaction.response.edit_message(embed=embed, view=self.view_children)

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:

        if isinstance(error, ValueError):
            return await interaction.response.send_message(
                embed=membed(f"You need to provide a real amount to {self.title.lower()}."),
                delete_after=3.0, ephemeral=True)
        
        await interaction.response.send_message(embed=membed("Something went wrong."), ephemeral=True)


class ConfirmResetData(discord.ui.View):
    def __init__(self, interaction: discord.Interaction, client: commands.Bot, user_to_remove: discord.Member):
        self.interaction: discord.Interaction = interaction
        self.removing_user: discord.Member = user_to_remove
        self.client: commands.Bot = client
        self.count = 0
        super().__init__(timeout=30.0)
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return await economy_check(interaction, self.interaction.user)
    
    async def on_timeout(self) -> Coroutine[Any, Any, None]:
        del active_sessions[self.interaction.user.id]
        for item in self.children:
            item.disabled = True
        try:
            embed = self.message.embeds[0]
            embed.title = "Timed Out"
            embed.colour = discord.Colour.brand_red()
            return await self.message.edit(embed=embed, view=self)
        except discord.NotFound:
            pass

    @discord.ui.button(label='RESET MY DATA', style=discord.ButtonStyle.danger, emoji=discord.PartialEmoji.from_str("<a:rooFireAhh:1208545466132860990>"))
    async def confirm_button_reset(self, interaction: discord.Interaction, _: discord.ui.Button):
        
        embed: discord.Embed = self.message.embeds[0]
        self.count += 1
        if self.count < 3:
            return await interaction.response.edit_message(view=self)
        
        for item in self.children:
            item.disabled = True
        self.stop()
        
        del active_sessions[interaction.user.id]
        
        tables_to_delete = {BANK_TABLE_NAME, INV_TABLE_NAME, COOLDOWN_TABLE_NAME, SLAY_TABLE_NAME}
        async with self.client.pool_connection.acquire() as conn:
            for table in tables_to_delete:
                await conn.execute(f"DELETE FROM `{table}` WHERE userID = ?", (self.removing_user.id,))
            await conn.commit()

        embed.title = "Confirmed"
        embed.colour = discord.Colour.brand_red()

        await interaction.response.edit_message(embed=embed, view=self)
        whose = "your" if interaction.user.id == self.removing_user.id else f"{self.removing_user.mention}'s"
        end_note = " Thanks for using the bot." if whose == "your" else ""

        await interaction.followup.send(embed=membed(f"All of {whose} data has been reset.{end_note}"))

    @discord.ui.button(label='CANCEL', style=discord.ButtonStyle.primary)
    async def cancel_button_reset(self, interaction: discord.Interaction, _: discord.ui.Button):
        del active_sessions[interaction.user.id]

        for item in self.children:
            item.disabled = True
        self.stop()

        embed: discord.Embed = self.message.embeds[0]
        embed.title = "Cancelled"
        embed.colour = discord.Colour.blurple()
        await interaction.response.edit_message(embed=embed, view=self)


class Confirm(discord.ui.View):
    def __init__(self, interaction: discord.Interaction):
        self.interaction = interaction
        super().__init__(timeout=40.0)
        self.value = None

    async def interaction_check(self, interaction: discord.Interaction[discord.Client]) -> bool:
        return await economy_check(interaction, self.interaction.user)

    @discord.ui.button(label='Cancel', style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        del active_sessions[interaction.user.id]
        self.children[1].style = discord.ButtonStyle.secondary
        button.style = discord.ButtonStyle.success
        
        for item in self.children:
            item.disabled = True

        await interaction.response.edit_message(view=self)
        
        self.value = False
        self.stop()

    @discord.ui.button(label='Confirm', style=discord.ButtonStyle.success)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        del active_sessions[interaction.user.id]
        self.children[0].style = discord.ButtonStyle.secondary
        button.style = discord.ButtonStyle.success

        for item in self.children:
            item.disabled = True
        
        await interaction.response.edit_message(view=self)
        
        self.value = True
        self.stop()


async def respond(interaction: discord.Interaction, **kwargs) -> discord.WebhookMessage | None:
    """Determine if we should respond to the interaction or send followups"""
    if interaction.response.is_done():
        return await interaction.followup.send(**kwargs)
    await interaction.response.send_message(**kwargs)


async def process_confirmation(interaction: discord.Interaction, prompt: str) -> bool:
    """
    Process a confirmation. This only updates the view.
    
    The actual action is done in the command itself.

    You do not need to check if another confirmation is active, as this function does that for you.

    This returns a boolean indicating whether the user confirmed the action or not, or None if the user timed out.
    """

    if active_sessions.get(interaction.user.id):
        return await respond(interaction, embed=membed(WARN_FOR_CONCURRENCY))
    active_sessions.update({interaction.user.id: 1})
    
    view = Confirm(interaction)
    confirm = discord.Embed(
        title="Pending Confirmation",
        colour=0x2B2D31,
        description=prompt
    )

    resp = await respond(interaction, embed=confirm, view=view)
    msg = resp or await interaction.original_response()
    await view.wait()
    
    embed = msg.embeds[0]
    if view.value is None:
        for item in view.children:
            item.disabled = True

        del active_sessions[interaction.user.id]
        embed.title = "Timed Out"
        embed.description = f"~~{embed.description}~~"
        embed.colour = discord.Colour.brand_red()
        await msg.edit(embed=embed, view=view)
        return view.value
    
    if view.value:

        embed.title = "Action Confirmed"
        embed.colour = discord.Colour.brand_green()
        await msg.edit(embed=embed, view=view)
        return view.value
    
    embed.title = "Action Cancelled"
    embed.colour = discord.Colour.brand_red()
    await msg.edit(embed=embed, view=view)
    return view.value


class RememberPositionView(discord.ui.View):
    def __init__(
            self, 
            interaction: discord.Interaction, 
            conn: asqlite_Connection, 
            all_emojis: list[str], 
            actual_emoji: str, 
            their_job: str):

        self.interaction = interaction
        self.conn: asqlite_Connection = conn
        self.actual_emoji = actual_emoji
        self.their_job = their_job
        self.base = randint(5_500_000, 9_500_000)
        super().__init__(timeout=15.0)

        for emoji in all_emojis:
            self.add_item(RememberPosition(emoji, self.determine_outcome))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return await economy_check(interaction, self.interaction.user)
    
    async def on_timeout(self) -> Coroutine[Any, Any, None]:

        self.base_reward = floor((25 / 100) * self.base_reward)
        await Economy.update_bank_new(self.interaction.user, self.conn, self.base_reward)
        await self.conn.commit()

        embed = self.message.embeds[0]
        embed.title = "Terrible effort!"
        embed.description = f"**You were given:**\n- {CURRENCY} {self.base_reward:,} for a sub-par shift"
        embed.colour = discord.Colour.brand_red()
        embed.set_footer(text=f"Working as a {self.their_job}")

        try:
            await self.message.edit(embed=embed, view=None)
        except discord.NotFound:
            pass

    async def determine_outcome(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Determine the position of the real emoji."""
        self.stop()
        embed = self.message.embeds[0]

        if button.emoji.name == self.actual_emoji:
            embed.title = "Great work!"
            embed.description = f"**You were given:**\n- {CURRENCY} {self.base:,} for your shift"
            embed.colour = discord.Colour.brand_green()
        else:
            self.base = floor((25 / 100) * self.base)
            embed.title = "Terrible work!"
            embed.description = f"**You were given:**\n- {CURRENCY} {self.base:,} for a sub-par shift"
            embed.colour = discord.Colour.brand_red()
        
        embed.set_footer(text=f"Working as a {self.their_job}")
        
        await Economy.update_bank_new(interaction.user, self.conn, self.base)
        await self.conn.commit()

        await interaction.response.edit_message(content=None, embed=embed, view=None)


class RememberPosition(discord.ui.Button):
    """A minigame to remember the position the tiles shown were on once hidden."""

    def __init__(self, random_emoji: str, button_cb: Callable):
        self.button_cb = button_cb
        super().__init__(emoji=random_emoji)
    
    async def callback(self, interaction: discord.Interaction):
        await self.button_cb(interaction, button=self)


class RememberOrder(discord.ui.View):
    """A minigame to remember the position the tiles shown were on once hidden."""

    def __init__(self, interaction: discord.Interaction, client: commands.Bot, 
                 list_of_five_order: list, their_job: str, base_reward: int):

        self.interaction = interaction
        self.client: commands.Bot = client
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

        async with self.client.pool_connection.acquire() as conn:
            conn: asqlite_Connection
            self.base_reward = floor((25 / 100) * self.base_reward)

            await Economy.update_bank_new(self.interaction.user, conn, self.base_reward)
            await conn.commit()

        embed = self.message.embeds[0]
        embed.title = "Terrible effort!"
        embed.description = f"**You were given:**\n- {CURRENCY} {self.base_reward:,} for a sub-par shift"
        embed.colour = discord.Colour.brand_red()
        embed.set_footer(text=f"Working as a {self.their_job}")

        try:
            await self.message.edit(embed=embed, view=None)
        except discord.NotFound:
            pass
    
    """If the position of a given item was correct, disable the button."""

    async def disable_if_correct(self, interaction: discord.Interaction, button: discord.ui.Button):
        if button.label == self.list_of_five_order[self.pos]:
            button.disabled = True
            self.pos += 1
            if self.pos == 5:
                async with self.client.pool_connection.acquire() as conn:
                    conn: asqlite_Connection
                    await Economy.update_bank_new(interaction.user, conn, self.base_reward)
                    await conn.commit()

                self.stop()
                embed = self.message.embeds[0]
                embed.title = "Great work!"
                embed.description = f"**You were given:**\n- {CURRENCY} {self.base_reward:,} for your shift"
                embed.colour = discord.Colour.brand_green()
                embed.set_footer(text=f"Working as a {self.their_job}")
                return await interaction.response.edit_message(embed=embed, view=None)
            return await interaction.response.edit_message(view=self)
        
        self.stop()
        self.pos = self.pos or 1
        self.base_reward -= int((self.pos / 4) * self.base_reward)
        
        async with self.client.pool_connection.acquire() as conn:
            conn: asqlite_Connection
            await Economy.update_bank_new(interaction.user, conn, self.base_reward)
            await conn.commit()

        embed = self.message.embeds[0]
        embed.title = "Terrible work!"
        embed.description = f"**You were given:**\n- {CURRENCY} {self.base_reward:,} for a sub-par shift"
        embed.colour = discord.Colour.brand_red()
        embed.set_footer(text=f"Working as a {self.their_job}")

        await interaction.response.edit_message(embed=embed, view=None)

    @discord.ui.button(label="A")
    async def choice_one(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.disable_if_correct(interaction, button=button)
    
    @discord.ui.button(label="B")
    async def choice_two(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.disable_if_correct(interaction, button=button)

    @discord.ui.button(label="C")
    async def choice_three(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.disable_if_correct(interaction, button=button)

    @discord.ui.button(label="D")
    async def choice_four(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Callback for the green buttons."""
        await self.disable_if_correct(interaction, button=button)

    @discord.ui.button(label="E")
    async def choice_five(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Callback for the blue buttons."""
        await self.disable_if_correct(interaction, button=button)


class BalanceView(discord.ui.View):
    """View for the balance command to mange and deposit/withdraw money."""

    def __init__(self, interaction: discord.Interaction, client: commands.Bot,
                 wallet: int, bank: int, bankspace: int, viewing: discord.Member):
        self.interaction = interaction
        self.client: commands.Bot = client
        self.their_wallet = wallet
        self.their_bank = bank
        self.their_bankspace = bankspace
        self.viewing = viewing
        super().__init__(timeout=120.0)
        
        self.checks(self.their_bank, self.their_wallet, self.their_bankspace-self.their_bank)

    def checks(self, new_bank, new_wallet, any_new_bankspace_left):
        """Check if the buttons should be disabled or not."""
        if self.viewing.id != self.interaction.user.id:
            self.children[0].disabled = True
            self.children[1].disabled = True
            return
        
        self.children[0].disabled = (new_bank == 0)
        self.children[1].disabled = (new_wallet == 0) or (any_new_bankspace_left == 0)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return await economy_check(interaction, self.interaction.user)
    
    async def on_timeout(self) -> Coroutine[Any, Any, None]:
        for item in self.children:
            item.disabled = True
        try:
            await self.message.edit(view=self)    
        except discord.NotFound:
            pass

    @discord.ui.button(label="Withdraw", disabled=True)
    async def withdraw_money_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Withdraw money from the bank."""

        async with self.client.pool_connection.acquire() as conn:
            conn: asqlite_Connection
            bank_amt = await Economy.get_spec_bank_data(
                interaction.user, 
                field_name="bank", 
                conn_input=conn
            )

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
                conn=conn, 
                message=self.message, 
                view_children=self
            )
        )

    @discord.ui.button(label="Deposit", disabled=True)
    async def deposit_money_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Deposit money into the bank."""

        async with self.client.pool_connection.acquire() as conn:
            conn: asqlite_Connection
            data = await conn.fetchone(
                "SELECT wallet, bank, bankspace FROM `bank` WHERE userID = ?", 
                (interaction.user.id,)
            )

        if not data[0]:
            return await interaction.response.send_message(
                embed=membed("You have nothing to deposit."), 
                ephemeral=True, 
                delete_after=3.0
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
                conn=conn, 
                message=self.message, 
                view_children=self
            )
        )
    
    @discord.ui.button(emoji="<:refreshicon:1205432056369389590>")
    async def refresh_balance(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Refresh the current message to display the user's latest balance."""

        async with self.client.pool_connection.acquire() as conn:
            conn: asqlite_Connection
            nd = await conn.execute(
                """
                SELECT wallet, bank, bankspace FROM `bank` WHERE userID = $0
                """, self.viewing.id
            )

            nd = await nd.fetchone()
            bank = nd[0] + nd[1]
            inv = await Economy.calculate_inventory_value(self.viewing, conn)

            space = (nd[1] / nd[2]) * 100
            
            balance: discord.Embed = self.message.embeds[0]
            balance.timestamp = discord.utils.utcnow()
            balance.clear_fields()

            balance.add_field(name="Wallet", value=f"{CURRENCY} {nd[0]:,}")
            balance.add_field(name="Bank", value=f"{CURRENCY} {nd[1]:,}")
            balance.add_field(name="Bankspace", value=f"{CURRENCY} {nd[2]:,} ({space:.2f}% full)")
            balance.add_field(name="Money Net", value=f"{CURRENCY} {bank:,}")
            balance.add_field(name="Inventory Net", value=f"{CURRENCY} {inv:,}")
            balance.add_field(name="Total Net", value=f"{CURRENCY} {inv + bank:,}")
            
        self.checks(nd[1], nd[0], nd[2]-nd[1])
        await interaction.response.edit_message(content=None, embed=balance, view=self)

    @discord.ui.button(emoji=discord.PartialEmoji.from_str("<:terminate:1205810058357907487>"))
    async def close_view(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Close the balance view."""
        self.stop()
        await interaction.response.edit_message(view=None)


class BlackjackUi(discord.ui.View):
    """View for the blackjack command and its associated functions."""

    def __init__(self, interaction: discord.Interaction, client: commands.Bot):
        self.interaction = interaction
        self.client: commands.Bot = client
        self.finished = False
        super().__init__(timeout=30)

    async def on_error(self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item[Any], /) -> None:
        print_exception(type(error), error, error.__traceback__)
        await interaction.response.send_message(
            embed=membed("Something went wrong. Try again later."))

    async def on_timeout(self) -> None:
        if not self.finished:
            del self.client.games[self.interaction.user.id]
            try:
                await self.message.edit(
                    content=None, embed=membed("You backed off so the game ended."), view=None)
            except discord.NotFound:
                pass

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return await economy_check(interaction, self.interaction.user)

    @discord.ui.button(label='Hit', style=discord.ButtonStyle.primary)
    async def hit_bj(self, interaction: discord.Interaction, _: discord.ui.Button):
        """Button in the interface to hit within blackjack."""
        namount = self.client.games[interaction.user.id][-1]
        deck = self.client.games[interaction.user.id][0]
        player_hand = self.client.games[interaction.user.id][1]

        player_hand.append(deck.pop())
        self.client.games[interaction.user.id][-2].append(
            display_user_friendly_card_format(player_hand[-1]))
        player_sum = calculate_hand(player_hand)

        if player_sum > 21:

            self.stop()
            self.finished = True
            dealer_hand = self.client.games[interaction.user.id][2]
            d_fver_p = [num for num in self.client.games[interaction.user.id][-2]]
            d_fver_d = [num for num in self.client.games[interaction.user.id][-3]]
            del self.client.games[interaction.user.id]

            async with self.client.pool_connection.acquire() as conn:
                conn: asqlite_Connection

                await Economy.update_bank_new(interaction.user, conn, namount, "bjla")
                bj_win = await conn.fetchone('SELECT bjw FROM bank WHERE userID = ?', (interaction.user.id,))
                new_bj_lose = await Economy.update_bank_new(interaction.user, conn, 1, "bjl")
                new_amount_balance = await Economy.update_bank_new(interaction.user, conn, -namount)
                new_total = new_bj_lose[0] + bj_win[0]
                prnctl = (new_bj_lose[0] / new_total) * 100
                await conn.commit()

                embed = discord.Embed(colour=discord.Colour.brand_red(),
                                      description=f"**You lost. You went over 21 and busted.**\n"
                                                  f"You lost {CURRENCY} **{namount:,}**. You now "
                                                  f"have {CURRENCY} **{new_amount_balance[0]:,}**\n"
                                                  f"You lost {prnctl:.1f}% of the games.")

                embed.add_field(name=f"{interaction.user.name} (Player)", 
                                value=f"**Cards** - {' '.join(d_fver_p)}\n"
                                      f"**Total** - `{player_sum}`")
                
                embed.add_field(name=f"{interaction.client.user.name} (Dealer)",
                                value=f"**Cards** - {' '.join(d_fver_d)}\n"
                                      f"**Total** - `{calculate_hand(dealer_hand)}`")

                embed.set_author(name=f"{interaction.user.name}'s losing blackjack game",
                                 icon_url=interaction.user.display_avatar.url)
                await interaction.response.edit_message(content=None, embed=embed, view=None)

        elif player_sum == 21:
            self.stop()
            self.finished = True

            dealer_hand = self.client.games[interaction.user.id][2]
            d_fver_p = [num for num in self.client.games[interaction.user.id][-2]]
            d_fver_d = [num for num in self.client.games[interaction.user.id][-3]]

            del self.client.games[interaction.user.id]

            async with self.client.pool_connection.acquire() as conn:
                conn: asqlite_Connection

                bj_lose = await conn.execute('SELECT bjl FROM bank WHERE userID = ?', (interaction.user.id,))
                bj_lose = await bj_lose.fetchone()
                new_bj_win = await Economy.update_bank_new(interaction.user, conn, 1, "bjw")
                new_total = new_bj_win[0] + bj_lose[0]
                prctnw = (new_bj_win[0] / new_total) * 100
                pmulti = await Economy.get_pmulti_data_only(interaction.user, conn)
                new_multi = SERVER_MULTIPLIERS.get(interaction.guild.id, 0) + pmulti[0]
                
                amount_after_multi = floor(((new_multi / 100) * namount) + namount) + randint(1, 999)
                await Economy.update_bank_new(interaction.user, conn, amount_after_multi, "bjwa")
                new_amount_balance = await Economy.update_bank_new(interaction.user, conn, amount_after_multi)
                await conn.commit()

                win = discord.Embed(
                    colour=discord.Colour.brand_green(),
                    description=(
                        f"**You win! You got to {player_sum}**.\n"
                        f"You won {CURRENCY} **{amount_after_multi:,}**. "
                        f"You now have {CURRENCY} **{new_amount_balance[0]:,}**.\n"
                        f"You won {prctnw:.1f}% of the games."
                    )
                )

                win.add_field(
                    name=f"{interaction.user.name} (Player)", 
                    value=(
                        f"**Cards** - {' '.join(d_fver_p)}\n"
                        f"**Total** - `{player_sum}`"
                    )
                )

                win.add_field(
                    name=f"{interaction.client.user.name} (Dealer)", 
                    value=(
                        f"**Cards** - {' '.join(d_fver_d)}\n"
                        f"**Total** - `{calculate_hand(dealer_hand)}`"
                    )
                )

                win.set_author(
                    name=f"{interaction.user.name}'s winning blackjack game", 
                    icon_url=interaction.user.display_avatar.url
                )

                await interaction.response.edit_message(content=None, embed=win, view=None)

        else:

            d_fver_p = [number for number in self.client.games[interaction.user.id][-2]]
            necessary_show = self.client.games[interaction.user.id][-3][0]

            prg = discord.Embed(colour=0x2B2D31,
                                description=f"**Your move. Your hand is now {player_sum}**.")
            prg.add_field(
                name=f"{interaction.user.name} (Player)", 
                value=(
                    f"**Cards** - {' '.join(d_fver_p)}\n"
                    f"**Total** - `{player_sum}`"
                )
            )
            
            prg.add_field(
                name=f"{interaction.client.user.name} (Dealer)",
                value=(
                    f"**Cards** - {necessary_show} `?`\n"
                    f"**Total** - ` ? `"
                )
            )

            prg.set_footer(text="K, Q, J = 10  |  A = 1 or 11")
            prg.set_author(
                icon_url=interaction.user.display_avatar.url,
                name=f"{interaction.user.name}'s blackjack game"
            )

            await interaction.response.edit_message( 
                embed=prg, 
                view=self,
                content=(
                    "Press **Hit** to hit, **Stand** to finalize your deck or "
                    "**Forfeit** to end your hand prematurely."
                )
            )

    @discord.ui.button(label='Stand', style=discord.ButtonStyle.primary)
    async def stand_bj(self, interaction: discord.Interaction, _: discord.ui.Button):
        """Button interface in blackjack to stand."""
        self.stop()
        self.finished = True

        deck = self.client.games[interaction.user.id][0]
        player_hand = self.client.games[interaction.user.id][1]
        dealer_hand = self.client.games[interaction.user.id][2]
        namount = self.client.games[interaction.user.id][-1]

        dealer_total = calculate_hand(dealer_hand)
        player_sum = calculate_hand(player_hand)

        while dealer_total < 17:
            popped = deck.pop()

            dealer_hand.append(popped)

            self.client.games[interaction.user.id][-3].append(display_user_friendly_card_format(popped))

            dealer_total = calculate_hand(dealer_hand)

        d_fver_p = self.client.games[interaction.user.id][-2]
        d_fver_d = self.client.games[interaction.user.id][-3]
        del self.client.games[interaction.user.id]

        if dealer_total > 21:
            async with self.client.pool_connection.acquire() as conn:
                conn: asqlite_Connection

                bj_lose = await conn.fetchone('SELECT bjl FROM bank WHERE userID = ?', (interaction.user.id,))
                new_bj_win = await Economy.update_bank_new(interaction.user, conn, 1, "bjw")
                new_total = new_bj_win[0] + bj_lose[0]
                prctnw = (new_bj_win[0] / new_total) * 100

                pmulti = await Economy.get_pmulti_data_only(interaction.user, conn)
                new_multi = SERVER_MULTIPLIERS.get(interaction.guild.id, 0) + pmulti[0]
                amount_after_multi = floor(((new_multi / 100) * namount) + namount) + randint(1, 999)
                await Economy.update_bank_new(interaction.user, conn, amount_after_multi, "bjwa")
                new_amount_balance = await Economy.update_bank_new(interaction.user, conn, amount_after_multi)
                await conn.commit()

            win = discord.Embed(
                colour=discord.Colour.brand_green(),
                description=(
                    f"**You win! The dealer went over 21 and busted.**\n"
                    f"You won {CURRENCY} **{amount_after_multi:,}**. "
                    f"You now have {CURRENCY} **{new_amount_balance[0]:,}**.\n"
                    f"You won {prctnw:.1f}% of the games."
                )
            )

            win.add_field(
                name=f"{interaction.user.name} (Player)", 
                value=(
                    f"**Cards** - {' '.join(d_fver_p)}\n"
                    f"**Total** - `{player_sum}`"
                )
            )

            win.add_field(
                name=f"{interaction.client.user.name} (Dealer)", 
                value=(
                    f"**Cards** - {' '.join(d_fver_d)}\n"
                    f"**Total** - `{dealer_total}`"
                )
            )

            win.set_author(
                icon_url=interaction.user.display_avatar.url, 
                name=f"{interaction.user.name}'s winning blackjack game"
            )

            await interaction.response.edit_message(content=None, embed=win, view=None)

        elif dealer_total > player_sum:
            async with self.client.pool_connection.acquire() as conn:
                conn: asqlite_Connection

                bj_win = await conn.fetchone('SELECT bjw FROM bank WHERE userID = ?', (interaction.user.id,))
                new_bj_lose = await Economy.update_bank_new(interaction.user, conn, 1, "bjl")
                new_total = new_bj_lose[0] + bj_win[0]
                prnctl = (new_bj_lose[0] / new_total) * 100
                await Economy.update_bank_new(interaction.user, conn, namount, "bjla")
                new_amount_balance = await Economy.update_bank_new(interaction.user, conn, -namount)
                await conn.commit()

            loser = discord.Embed(
                colour=discord.Colour.brand_red(),
                description=(
                    f"**You lost. You stood with a lower score (`{player_sum}`) than "
                    f"the dealer (`{dealer_total}`).**\n"
                    f"You lost {CURRENCY} **{namount:,}**. You now "
                    f"have {CURRENCY} **{new_amount_balance[0]:,}**.\n"
                    f"You lost {prnctl:.1f}% of the games."
                )
            )
            
            loser.add_field(
                name=f"{interaction.user.name} (Player)", 
                value=(
                    f"**Cards** - {' '.join(d_fver_p)}\n"
                    f"**Total** - `{player_sum}`"
                )
            )

            loser.add_field(
                name=f"{interaction.client.user.name} (Dealer)", 
                value=(
                    f"**Cards** - {' '.join(d_fver_d)}\n"
                    f"**Total** - `{dealer_total}`"
                )
            )

            loser.set_author(
                icon_url=interaction.user.display_avatar.url,
                name=f"{interaction.user.name}'s losing blackjack game"
            )
            
            await interaction.response.edit_message(content=None, embed=loser, view=None)

        elif dealer_total < player_sum:
            async with self.client.pool_connection.acquire() as conn:
                conn: asqlite_Connection

                bj_lose = await conn.fetchone('SELECT bjl FROM bank WHERE userID = ?', (interaction.user.id,))
                new_bj_win = await Economy.update_bank_new(interaction.user, conn, 1, "bjw")
                new_total = new_bj_win[0] + bj_lose[0]
                prctnw = (new_bj_win[0] / new_total) * 100

                pmulti = await Economy.get_pmulti_data_only(interaction.user, conn)
                new_multi = SERVER_MULTIPLIERS.get(interaction.guild.id, 0) + pmulti[0]
                amount_after_multi = floor(((new_multi / 100) * namount) + namount) + randint(1, 999)
                new_amount_balance = await Economy.update_bank_new(interaction.user, conn, amount_after_multi)
                await Economy.update_bank_new(interaction.user, conn, amount_after_multi, "bjwa")
                await conn.commit()

            win = discord.Embed(
                colour=discord.Colour.brand_green(),
                description=(
                    f"**You win! You stood with a higher score (`{player_sum}`) than the "
                    f"dealer (`{dealer_total}`).**\n"
                    f"You won {CURRENCY} **{amount_after_multi:,}**. "
                    f"You now have {CURRENCY} **{new_amount_balance[0]:,}**.\n"
                    f"You won {prctnw:.1f}% of the games."
                )
            )

            win.add_field(
                name=f"{interaction.user.name} (Player)", 
                value=(
                    f"**Cards** - {' '.join(d_fver_p)}\n"
                    f"**Total** - `{player_sum}`"
                )
            )

            win.add_field(
                name=f"{interaction.client.user.name} (Dealer)", 
                value=(
                    f"**Cards** - {' '.join(d_fver_d)}\n"
                    f"**Total** - `{dealer_total}`"
                )
            )

            win.set_author(
                icon_url=interaction.user.display_avatar.url,
                name=f"{interaction.user.name}'s winning blackjack game"
            )

            await interaction.response.edit_message(content=None, embed=win, view=None)
        else:
            async with self.client.pool_connection.acquire() as conn:
                conn: asqlite_Connection
                wallet_amt = await Economy.get_wallet_data_only(interaction.user, conn)
            
            tie = discord.Embed(
                colour=discord.Colour.yellow(),
                description=(
                    f"**Tie! You tied with the dealer.**\n"
                    f"Your wallet hasn't changed! You have {CURRENCY} **{wallet_amt:,}** still."
                )
            )

            tie.add_field(
                name=f"{interaction.user.name} (Player)", 
                value=(
                    f"**Cards** - {' '.join(d_fver_p)}\n"
                    f"**Total** - `{player_sum}`"
                )
            )

            tie.add_field(
                name=f"{interaction.client.user.name} (Dealer)", 
                value=(
                    f"**Cards** - {' '.join(d_fver_d)}\n"
                    f"**Total** - `{dealer_total}`"
                )
            )

            tie.set_author(
                icon_url=interaction.user.display_avatar.url, 
                name=f"{interaction.user.name}'s blackjack game"
            )

            await interaction.response.edit_message(content=None, embed=tie, view=None)

    @discord.ui.button(label='Forfeit', style=discord.ButtonStyle.primary)
    async def forfeit_bj(self, interaction: discord.Interaction, _: discord.ui.Button):
        """Button for the blackjack interface to forfeit the current match."""

        self.stop()
        self.finished = True

        namount = self.client.games[interaction.user.id][-1]
        namount //= 2

        dealer_total = calculate_hand(self.client.games[interaction.user.id][2])
        player_sum = calculate_hand(self.client.games[interaction.user.id][1])
        d_fver_p = self.client.games[interaction.user.id][-2]
        d_fver_d = self.client.games[interaction.user.id][-3]

        del self.client.games[interaction.user.id]

        async with self.client.pool_connection.acquire() as conn:
            conn: asqlite_Connection

            bj_win = await conn.fetchone('SELECT bjw FROM bank WHERE userID = ?', (interaction.user.id,))
            new_bj_lose = await Economy.update_bank_new(interaction.user, conn, 1, "bjl")
            new_total = new_bj_lose[0] + bj_win[0]
            prcntl = (new_bj_lose[0] / new_total) * 100
            await Economy.update_bank_new(interaction.user, conn, namount, "bjla")
            await Economy.update_bank_new(self.interaction.guild.me, conn, namount)
            new_amount_balance = await Economy.update_bank_new(interaction.user, conn, -namount)
            await conn.commit()

        loser = discord.Embed(
            colour=discord.Colour.brand_red(),
            description=(
                f"**You forfeit. The dealer took half of your bet for surrendering.**\n"
                f"You lost {CURRENCY} **{namount:,}**. You now "
                f"have {CURRENCY} **{new_amount_balance[0]:,}**.\n"
                f"You lost {prcntl:.1f}% of the games."
            )
        )

        loser.add_field(
            name=f"{interaction.user.name} (Player)", 
            value=(
                f"**Cards** - {' '.join(d_fver_p)}\n"
                f"**Total** - `{player_sum}`"
            )
        )

        loser.add_field(
            name=f"{interaction.client.user.name} (Dealer)", 
            value=(
                f"**Cards** - {' '.join(d_fver_d)}\n"
                f"**Total** - `{dealer_total}`"
            )
        )

        loser.set_author(
            icon_url=interaction.user.display_avatar.url, 
            name=f"{interaction.user.name}'s losing blackjack game"
        )

        await interaction.response.edit_message(content=None, embed=loser, view=None)


class HighLow(discord.ui.View):
    """View for the Highlow command and its associated functions."""

    def __init__(
            self, interaction: discord.Interaction, 
            hint_provided: int, bet: int, value: int):
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
        for item in self.children:
            item.disabled = True
        await self.message.edit(embed=membed("The game ended because you didn't answer in time."), view=None)

    async def send_win(self, interaction: discord.Interaction, button: discord.ui.Button, conn: asqlite_Connection):
        pmulti = await Economy.get_pmulti_data_only(interaction.user, conn)
        new_multi = SERVER_MULTIPLIERS.get(interaction.guild.id, 0) + pmulti[0]
        total = self.their_bet * (new_multi // 100 + 1)
        new_balance = await Economy.update_bank_new(interaction.user, conn, total)
        await self.make_clicked_blurple_only(button)

        win = discord.Embed(
            colour=discord.Colour.brand_green(),
            description=(
                f'**You won {CURRENCY} {total:,}!**\n'
                f'Your hint was **{self.hint_provided}**. '
                f'The hidden number was **{self.true_value}**.\n'
                f'Your new balance is {CURRENCY} **{new_balance[0]:,}**.'
            )
        )

        win.set_author(
            name=f"{interaction.user.name}'s winning high-low game", 
            icon_url=interaction.user.display_avatar.url
        )

        await interaction.response.edit_message(embed=win, view=self)

    async def send_loss(self, interaction: discord.Interaction, button: discord.ui.Button, conn: asqlite_Connection):
        new_amount = await Economy.update_bank_new(interaction.user, conn, -self.their_bet)
        await self.make_clicked_blurple_only(button)

        lose = discord.Embed()
        lose.description = (
            f'**You lost {CURRENCY} {self.their_bet:,}!**\n'
            f'Your hint was **{self.hint_provided}**. '
            f'The hidden number was **{self.true_value}**.\n'
            f'Your new balance is {CURRENCY} **{new_amount[0]:,}**.')
        
        lose.colour = discord.Colour.brand_red()
        lose.set_author(
            name=f"{interaction.user.name}'s losing high-low game", 
            icon_url=interaction.user.display_avatar.url)
        await interaction.response.edit_message(embed=lose, view=self)

    @discord.ui.button(label='Lower', style=discord.ButtonStyle.primary)
    async def low(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Button for highlow interface to allow users to guess lower."""
        async with interaction.client.pool_connection.acquire() as conn:
            conn: asqlite_Connection

            async with conn.transaction():

                if self.true_value < self.hint_provided:
                    return await self.send_win(interaction, button, conn)
                await self.send_loss(interaction, button, conn)

    @discord.ui.button(label='JACKPOT!', style=discord.ButtonStyle.primary)
    async def jackpot(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Button for highlow interface to guess jackpot, meaning the guessed number is the actual number."""

        async with interaction.client.pool_connection.acquire() as conn:
            conn: asqlite_Connection

            async with conn.transaction():
                if self.hint_provided == self.true_value:
                    await self.send_win(interaction, button, conn)
                    return await self.message.add_reaction("\U0001f911")
                await self.send_loss(interaction, button, conn)

    @discord.ui.button(label='Higher', style=discord.ButtonStyle.primary)
    async def high(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Button for highlow interface to allow users to guess higher."""
        
        async with interaction.client.pool_connection.acquire() as conn:
            conn: asqlite_Connection

            async with conn.transaction():
                if self.true_value > self.hint_provided:
                    return await self.send_win(interaction, button, conn)
                await self.send_loss(interaction, button, conn)


class ImageModal(discord.ui.Modal):

    def __init__(self, conn, their_choice, the_view):
        self.conn = conn
        self.choice: str = their_choice
        self.the_view = the_view
        super().__init__(title=f"Change Photo of {self.choice.title()}", timeout=60.0)

    image = discord.ui.TextInput(
        style=discord.TextStyle.paragraph,
        label='Image URL',
        required=True,
        placeholder="Drop a photo url of what you want your servant to look like.",
        min_length=5,
        max_length=500
    )

    async def on_submit(self, interaction: discord.Interaction):

        await self.conn.execute(
            f"UPDATE `{SLAY_TABLE_NAME}` SET url = ? WHERE userID = ? AND slay_name = ?",
            (self.image.value, interaction.user.id, self.choice)
        )
        await self.conn.commit()

        embed = interaction.message.embeds[0]
        embed.set_image(url=self.image.value)

        await interaction.response.edit_message(view=self.the_view)

    async def on_error(self, interaction: discord.Interaction, error):
        return await interaction.response.send_message(
            embed=membed("The photo you provided was invalid, try a different one."))


class HexModal(discord.ui.Modal):
    def __init__(self, conn, their_choice, the_view):
        self.conn = conn
        self.choice: str = their_choice
        self.the_view = the_view
        super().__init__(title=f"Change Embed Hex Colour for {self.choice.title()}", timeout=60.0)

    hexinput = discord.ui.TextInput(
        style=discord.TextStyle.short,
        label='Hex Colour',
        required=True,
        placeholder="A hexadecimal value like #1A2B3C or FFFFFF.",
        min_length=6,
        max_length=7
    )

    async def on_submit(self, interaction: discord.Interaction):

        stripped_color_string = self.hexinput.value.replace("#", "")
        embed = interaction.message.embeds[0]
        stored_hex_repr = int(stripped_color_string, 16)
        embed.colour = stored_hex_repr

        await self.conn.execute(
            f"UPDATE `{SLAY_TABLE_NAME}` SET hex = ? WHERE userID = ? AND slay_name = ?",
            (stored_hex_repr, interaction.user.id, self.choice)
        )
        await self.conn.commit()
        await interaction.response.edit_message(view=self.the_view)

    async def on_error(self, interaction: discord.Interaction, error):
        warning = membed(
            ("The hex colour provided was not valid.\n"
             "It needs to be in this format: `#FFFFFF`.\n" 
             "Note that you do not need to include the hashtag."
            )
        )
        if not interaction.response.is_done():
            return await interaction.response.send_message(embed=warning)
        return await interaction.followup.send(embed=warning)


class InvestmentModal(discord.ui.Modal, title="Increase Investment"):

    def __init__(self, conn, client: commands.Bot, their_choice, the_view):
        super().__init__()
        self.conn = conn
        self.choice = their_choice
        self.the_view = the_view
        self.economy = client.get_cog("Economy")

    investa = discord.ui.TextInput(
        style=discord.TextStyle.short,
        label='Increment Value',
        required=True,
        placeholder="A shorthand (max, all, 5e6) or a constant.",
        min_length=1,
        max_length=100
    )

    async def on_submit(self, interaction: discord.Interaction):

        expo = determine_exponent(self.investa.value)
        wallet_amt = await Economy.get_wallet_data_only(interaction.user, self.conn)

        try:
            assert isinstance(expo, int)
            amount = expo
        except AssertionError:
            if expo.lower() in {'max', 'all'}:
                amount = wallet_amt
            else:
                return await interaction.response.send_message(
                    embed=membed("You need to provide a valid input to bet with."))

        if amount > wallet_amt:
            return await interaction.response.send_message(
                embed=membed("You don't have that much money in your wallet."), delete_after=3.0, ephemeral=True)

        productivity = labour_productivity_via(investment=amount)

        dtls = await self.conn.execute(
            "UPDATE `slay` SET investment = investment + ?, productivity = productivity + ? WHERE slay_name = ? AND "
            "userID = ? RETURNING *",
            (amount, productivity, self.choice, interaction.user.id))
        await self.conn.execute(f"UPDATE `{BANK_TABLE_NAME}` SET `wallet` = ? WHERE userID = ?",
                                (wallet_amt - amount, interaction.user.id))

        await self.conn.commit()
        dtls = await dtls.fetchone()

        sembed = await self.economy.servant_preset(interaction.user.id, dtls)
        await interaction.response.edit_message(content=None, embed=sembed, view=self.the_view)

    async def on_error(self, interaction: discord.Interaction, error):
        print_exception(type(error), error, error.__traceback__)
        return await interaction.response.send_message(
            embed=membed("We couldn't update your investment properly."))


class DropdownLB(discord.ui.Select):
    def __init__(self, client: commands.Bot, their_choice: str):
        self.economy = client.get_cog("Economy")

        options = [
            SelectOption(label='Bank + Wallet', description='Sort by the sum of bank and wallet.'),
            SelectOption(label='Wallet', description='Sort by the wallet amount only.'),
            SelectOption(label='Bank', description='Sort by the bank amount only.'),
            SelectOption(label='Inventory Net', description='Sort by the net value of your inventory.'),
            SelectOption(label='Bounty', description="Sort by the sum paid for capturing a player."),
            SelectOption(label='Commands', description="Sort by total commands ran."),
            SelectOption(label='Level', description="Sort by player level.")
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
    def __init__(self, client: commands.Bot, their_choice, channel_id):
        super().__init__(timeout=40.0)
        self.channel_id = channel_id
        self.add_item(DropdownLB(client, their_choice))

    async def on_timeout(self) -> None:
        del active_sessions[self.channel_id]
        for item in self.children:
            item.disabled = True
        try:
            await self.message.edit(view=self)
        except discord.NotFound:
            pass

class DispatchServantView(discord.ui.View):
    def __init__(self, client: commands.Bot, conn, chosen_slay: str, skill_lvl, interaction: discord.Interaction):
        super().__init__(timeout=40.0)
        self.interaction = interaction
        self.add_item(SelectTaskMenu(conn, chosen_slay, skill_lvl))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return await economy_check(interaction, self.interaction.user)

    async def on_timeout(self) -> None:
        for item in self.children:
            item.disabled = True
        try:
            await self.message.edit(view=self)
        except discord.NotFound:
            pass 


class Servants(discord.ui.Select):
    def __init__(self, client: commands.Bot, their_slays: list, their_choice: str, owner_id: int, conn):

        options = [SelectOption(
            emoji=GENDOR_EMOJIS.get(slay[1]), label=slay[0], description=f"Level {slay[2]} | Skill Level {slay[-1]}") for slay in their_slays]

        self.client: commands.Bot = client
        self.owner_id = owner_id
        self.conn = conn
        self.choice = their_choice
        self.economy = client.get_cog("Economy")

        super().__init__(options=options, placeholder="Select Servant Name", row=0)

        for option in options:
            option.default = option.value == self.choice

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        resp = await interaction.original_response()

        self.choice = self.values[0]
        
        for option in self.options:
            option.default = option.value == self.choice

        dtls = await self.conn.fetchone(
            "SELECT * FROM `slay` WHERE userID = ? AND slay_name = ?", (self.owner_id, self.choice))

        sembed = await self.economy.servant_preset(self.owner_id, dtls)  # servant embed

        await interaction.followup.edit_message(resp.id, content=None, embed=sembed, view=self.view)


class SelectTaskMenu(discord.ui.Select):
    def __init__(self, conn, servant_name: str, skill_lvl: int):

        self.conn = conn
        self.worker = servant_name
        self.skill_lvl = skill_lvl

        self.attrs = {
            1203056234731671683: (0, 25, 0.5, 0x73f27b),
            1203056272396648558: (1, 50, 1.5, 0xf4c500),
            1203056297310822411: (2, 75, 3.0, 0xde4147)
        }

        options = [
            SelectOption(
                emoji="<:battery_green:1203056234731671683>", 
                label="Assisting the elderly", 
                description=f"Skill L1 | {CURRENCY} ~400M"
            ),
            SelectOption(
                emoji="<:battery_green:1203056234731671683>", 
                label="Ask for financial support", 
                description=f"Skill L1 | {CURRENCY} ~800M"
            ),
            SelectOption(
                emoji="<:battery_green:1203056234731671683>", 
                label="Do your job", 
                description=f"Skill L1 | {CURRENCY} ~1B"
            ),
            SelectOption(
                emoji="<:battery_yellow:1203056272396648558>", 
                label="Hunt for loot", 
                description=f"Skill L2 | {CURRENCY} ~2.5B"
            ),
            SelectOption(
                emoji="<:battery_yellow:1203056272396648558>", 
                label="Delude Robbers", 
                description=f"Skill L2 | {CURRENCY} ~5B"
            ),
            SelectOption(
                emoji="<:battery_yellow:1203056272396648558>", 
                label="Plan heists on idle", 
                description=f"Skill L2 | {CURRENCY} ~10B"
            ),
            SelectOption(
                emoji="<:battery_red:1203056297310822411>", 
                label="Perform large-scale crimes", 
                description=f"Skill L3 | {CURRENCY} ~50B"
            ),
            SelectOption(
                emoji="<:battery_red:1203056297310822411>", 
                label="Prostitution", 
                description=f"Skill L3 | {CURRENCY} ~1T")
        ]

        super().__init__(options=options, placeholder="Pick a task")

    def calculate_time(self, skill_level, emoji_id: int):
        """Task difficulty is expected to be expressed in terms of the option's label.
        
        This always returns the time needed to complete the task in hours"""

        base_time_hours = 1.5
        base_time_minutes = base_time_hours * 60

        skill_multiplier = {0: 2, 1: 1.5, 2: 1, 3: 0.75}  # Adjust as needed

        adjusted_time_minutes = base_time_minutes * skill_multiplier[skill_level] * self.attrs[emoji_id][2]
        adjusted_time_hours = round(adjusted_time_minutes / 60)

        return adjusted_time_hours

    async def callback(self, interaction: discord.Interaction):
        
        energy = await self.conn.fetchone(
            "SELECT energy, hunger FROM `slay` WHERE userID = ? AND slay_name = ?", 
            (interaction.user.id, self.worker)
        )

        energy, hunger = energy

        chosen = self.values[0]

        for option in self.options:
            option.default = option.label == chosen
            if option.default:
                uri = option.emoji.url
                emoji = option.emoji.id
                description = option.description

        if energy < self.attrs[emoji][1]:
            return await interaction.response.send_message(
                embed=membed(f"{self.worker.title()} is too tired to do this task."), delete_after=3.0)

        if hunger <= 50:
            return await interaction.response.send_message(
                embed=membed(f"{self.worker.title()} is malnourished and cannot be dispatched.\n"
                             "Give them something to eat first."), delete_after=3.0)        

        required_skill_level = self.attrs[emoji][0]
        if self.skill_lvl < required_skill_level:
            return await interaction.response.send_message(
                embed=membed(
                    f"{self.worker.title()} needs to acquire Skill Level **{required_skill_level}** first."), 
                delete_after=3.0)

        # ! This is where you clear the view and must not listen any longer to it
        self.view.clear_items()
        self.view.stop()

        payout = description.split("~")[-1]
        payout = reverse_format_number_short(payout)

        res_duration = self.calculate_time(skill_level=self.skill_lvl, emoji_id=emoji)
        res_duration = discord.utils.utcnow() + datetime.timedelta(hours=res_duration)
    
        embed = discord.Embed(
            title="Task Started",
            description=f"{self.worker.title()} has started the task titled {repr(chosen)}.\n"
                        f"- They should finish {discord.utils.format_dt(res_duration, style="R")}.\n"
                        f"- There is a small chance that your servant may not return, depending on risk associated.\n"
                        f"- You'll need to call this command again to check back on their progress.",
            colour=0x313338)
        embed.set_thumbnail(url=uri)

        await interaction.response.edit_message(embed=embed, view=self.view)
        
        res_duration = datetime_to_string(res_duration)
        payout = randint(payout, payout + (payout // 2))
        await self.conn.execute(
            """
            UPDATE `slay` SET status = 0, work_until = ?, tasktype = ?, toreduce = ?, toadd = ? 
            WHERE userID = ? AND LOWER(slay_name) = LOWER(?)
            """, (res_duration, emoji, self.attrs[emoji][1], payout, interaction.user.id, self.worker))
        await self.conn.commit()

class ServantsManager(discord.ui.View):
    pronouns = {"Female": ("her", "she"), "Male": ("his", "he")}

    def __init__(self, client: commands.Bot, their_choice, owner_id: int, owner_slays, conn):
        """invoker is who is calling the command, owner_id is what the owner of these servants we're looking at are.

        their_choice is the default value thats been picked (i.e. the default servant chosen specified from the
        command."""

        super().__init__(timeout=60.0)
        self.removed_items = []
        self.manage_button = None
        self.child = Servants(client, owner_slays, their_choice, owner_id, conn)
        self.add_item(self.child)
        self.economy = client.get_cog("Economy")

        for item in self.children:
            if isinstance(item, Servants):
                continue

            if item.label == "Manage":
                self.manage_button = item
                continue

            self.removed_items.append(item)
            self.remove_item(item)

    async def on_timeout(self) -> None:
        for item in self.children:
            item.disabled = True
        try:
            await self.message.edit(view=self)
        except discord.NotFound:
            pass

    async def check_user(self, interaction: discord.Interaction):
        if interaction.user.id != self.child.owner_id:
            await interaction.response.send_message(
                embed=membed("This is not your servant"), 
                ephemeral=True, 
                delete_after=3.0
            )
    
    async def add_exp_handle_interactions(self, interaction: discord.Interaction, mode: str, by=1):
        """Add experience points to the servant increment their level if max XP is hit."""
        async with self.child.conn.transaction():
            val = await self.child.conn.execute(
                f'UPDATE `{SLAY_TABLE_NAME}` SET exp = exp + ? WHERE userID = ? AND slay_name = ? '
                f'AND EXISTS (SELECT 1 FROM `{SLAY_TABLE_NAME}` WHERE userID = ?) RETURNING exp, level',
                (by, interaction.user.id, self.child.choice, interaction.user.id))
            val = await val.fetchone()

            if val:
                xp, level = val
                exp_needed = Economy.calculate_serv_exp_for(level=level)

                if xp >= exp_needed:
                    
                    up = discord.Embed(
                        title=f"Your {self.child.choice.title()} just leveled up!", 
                        description=f"` {level} ` \U0000279c ` {level + 1} `",
                        colour=discord.Colour.random())

                    await self.child.conn.execute(
                        "UPDATE `slay` SET level = level + 1, exp = 0 WHERE userID = ? AND slay_name = ?",
                        (interaction.user.id, self.child.choice))
                    
                    distance = 3 - (level+1) % 3 if (level+1) % 3 != 0 else 0
                    if distance:
                        up.set_footer(text=f"{distance} level(s) left to unlocking a new skill level!")
                    else:
                        await self.child.conn.execute(
                            "UPDATE `slay` SET skillL = skillL + 1 WHERE userID = ? AND slay_name = ?",)
                        up.set_footer(text=f"Your servant just unlocked: Skill L{level//3}!")
                        
                    await respond(interaction, embed=up)

            dtls = await self.child.conn.execute(
                    f"UPDATE `slay` SET {mode} = 100 WHERE slay_name = ? AND userID = ? RETURNING *",
                    (self.child.choice, self.child.owner_id))

            dtls = await dtls.fetchone()

            sembed = await self.economy.servant_preset(self.child.owner_id, dtls) 
            await interaction.response.edit_message(content=None, embed=sembed, view=self)

    @discord.ui.button(label="Manage", style=discord.ButtonStyle.primary, row=1)
    async def manage_servant(self, interaction: discord.Interaction, button: discord.ui.Button):
        
        await self.check_user(interaction)
        if interaction.response.is_done():
            return

        self.remove_item(button)
        for item in self.removed_items:
            self.add_item(item)
        
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label='Feed', style=discord.ButtonStyle.primary, row=1)
    async def feed_servant(self, interaction: discord.Interaction, _: discord.ui.Button):

        await self.check_user(interaction)
        if interaction.response.is_done():
            return

        current_hunger = await self.child.conn.fetchone(
            "SELECT hunger from `slay` WHERE userID = ? AND slay_name = ?", 
            (self.child.owner_id, self.child.choice))
        
        if current_hunger[0] >= 90:
            return await interaction.response.send_message(
                embed=membed("Your servant is not hungry!"), 
                ephemeral=True, 
                delete_after=5.0)

        await self.add_exp_handle_interactions(interaction, mode="hunger")

    @discord.ui.button(label='Wash', style=discord.ButtonStyle.primary, row=1)
    async def wash_servant(self, interaction: discord.Interaction, _: discord.ui.Button):

        await self.check_user(interaction)
        if interaction.response.is_done():
            return

        current_hygiene = await self.child.conn.fetchone(
            "SELECT hygiene from `slay` WHERE userID = ? AND slay_name = ?", (self.child.owner_id, self.child.choice))

        if current_hygiene[0] >= 90:
            return await interaction.response.send_message(
                embed=membed("You can't wash them just yet, they are looking pretty clean already!"), 
                ephemeral=True, delete_after=3.0)

        possible = choice(
            ("You wet your servant's hair with warm water before applying a gentle tear-free shampoo.\n"
             "They enjoyed every second of it.",
             "You lathered the soap and massaged it onto their back to ensure a thorough cleaning.",
             "Your servant is comforted being around you..",
             "You rubbed a damp cloth around their entire body, inconsiderate of where you were touching.\n"
             "Maybe this needed an extra cleanse?"
             )
        )

        await respond(embed=membed(possible), delete_after=5.0)
        await self.add_exp_handle_interactions(interaction, mode="hygiene")

    @discord.ui.button(label='Invest', style=discord.ButtonStyle.primary, row=1)
    async def invest_in_servant(self, interaction: discord.Interaction, _: discord.ui.Button):

        await self.check_user(interaction)
        if interaction.response.is_done():
            return

        await interaction.response.send_modal(
            InvestmentModal(self.child.conn, self.child.client, self.child.choice, self))

    @discord.ui.button(label="\u200b", emoji="\U0001fac2", style=discord.ButtonStyle.secondary, row=2)
    async def hug(self, interaction: discord.Interaction, _: discord.ui.Button):

        await self.check_user(interaction)
        if interaction.response.is_done():
            return

        data = await self.child.conn.fetchone(
            "SELECT gender from `slay` WHERE userID = ? AND slay_name = ?", (self.child.owner_id, self.child.choice))
        her_his, she_he = self.pronouns.get(data[0])[0], self.pronouns.get(data[0])[1]

        selection = choice(
            ("Your servant is greatful for your affection and embraces you tightly.",
             f"You are enveloped in a warm, tight hug, savoring the moment with {her_his} body.",
             f"Wrapped in each other's arms, you shared a tender hug with {her_his}, finding solace in the silent "
             "connection.",
             f"{she_he.title()} held your body close, feeling a sense of security in the embrace of "
             f"someone truly special to {her_his} heart.",
             "As you hugged them, you whispered words of comfort, "
             f"letting {her_his} mind know {she_he} was cherished and valued.",
             f"The embrace was more than physical; it was celebrating the mutual connection {she_he} shared with you.",
             f"With a smile, you embraced {her_his} lascivious body, feeling a sense of completeness as if both of "
             "your hearts were synchronized in that moment.",
             "The hug was a blend of familiarity and excitement, as if rediscovering the "
             "joy of being close to someone dear.")
        )

        dtls = await self.child.conn.execute(
            "UPDATE `slay` SET love = love + 35 WHERE slay_name = ? AND userID = ? AND love <= 100 RETURNING *",
            (self.child.choice, self.child.owner_id))

        dtls = await dtls.fetchone()

        if dtls is not None:
            await self.child.conn.commit()

            sembed = await self.economy.servant_preset(self.child.owner_id, dtls)
            await interaction.message.edit(content=None, embed=sembed, view=self)
        await interaction.response.send_message(embed=membed(selection), delete_after=5.0)

    @discord.ui.button(label="\u200b", emoji="\U0001f48b", style=discord.ButtonStyle.secondary, row=2)
    async def kiss(self, interaction: discord.Interaction, _: discord.ui.Button):

        await self.check_user(interaction)
        if interaction.response.is_done():
            return

        pronouns = {"Female": ("her", "she"), "Male": ("his", "he")}

        data = await self.child.conn.fetchone(
            "SELECT gender from `slay` WHERE userID = ? AND slay_name = ?", (self.child.owner_id, self.child.choice))
        her_his, she_he = pronouns.get(data[0])[0], pronouns.get(data[0])[1]

        selection = choice(
            (f"Your came into contact with {her_his} lips, planting a lingering kiss that conveyed both passion and "
             f"tenderness. {she_he.title()} was forever grateful.",
             f"With a playful grin, you sealed {her_his} lips with a light, affectionate kiss.",
             f"You closed {her_his} eyes slowly and gently kissed {her_his} on the cheek.",
             f"In a tender moment, you leaned in and placed a soft kiss on {her_his} lips, expressing your affection.",
             "You placed a passionate kiss speaking of desire and an unspoken connection that went beyond just words. "
             f"{she_he.title()} embraced it albeit awkwardly and held her captive in the state she was enthralled in.",
             "A gentle peck on the nose became a cherished routine, a simple act that spoke volumes.")
        )

        dtls = await self.child.conn.execute(
            "UPDATE `slay` SET love = love + 35 WHERE slay_name = ? AND userID = ? AND love <= 100 RETURNING *",
            (self.child.choice, self.child.owner_id))
        dtls = await dtls.fetchone()
        
        if dtls is not None:
            await self.child.conn.commit()
            sembed = await self.economy.servant_preset(self.child.owner_id, dtls)
            await interaction.message.edit(content=None, embed=sembed, view=self)
        await interaction.response.send_message(embed=membed(selection), delete_after=5.0)

    @discord.ui.button(emoji="\U00002728", label="Add Photo", style=discord.ButtonStyle.success, row=3)
    async def photo_modal(self, interaction: discord.Interaction, _: discord.ui.Button):

        await self.check_user(interaction)
        if interaction.response.is_done():
            return

        await interaction.response.send_modal(
            ImageModal(self.child.conn, self.child.choice, self))

    @discord.ui.button(emoji="\U00002728", label="Add Colour", style=discord.ButtonStyle.success, row=3)
    async def hex_modal(self, interaction: discord.Interaction, _: discord.ui.Button):

        await self.check_user(interaction)
        if interaction.response.is_done():
            return

        await interaction.response.send_modal(
            HexModal(self.child.conn, self.child.choice, self))

    @discord.ui.button(label="Go back", style=discord.ButtonStyle.primary, row=4)
    async def go_back(self, interaction: discord.Interaction, _: discord.ui.Button):

        await self.check_user(interaction)
        if interaction.response.is_done():
            return

        for item in self.removed_items:
            self.remove_item(item)
        self.add_item(self.manage_button)
        await interaction.response.edit_message(view=self)

class ShowcaseDropdown(discord.ui.Select):
    def __init__(self, showcase_list: list, showcase_details):
        self.showcase_list = showcase_list
        self.current_item = "0" if self.showcase_list[0][0] == "0" else self.showcase_list[0]
        self.showcase_dtls = showcase_details

        options = []
        for i in range(1, 7):
            
            item_id = self.showcase_list[i-1]

            if item_id[0] == "0":
                options.append(discord.SelectOption(label=f"Slot {i}", default=i==1, value=f"{item_id}{generateID()}"))
                continue
            
            details: tuple = self.showcase_dtls.get(item_id)
            options.append(discord.SelectOption(label=details[0], emoji=details[1], default=i==1, value=item_id))

        super().__init__(options=options, row=0)
    
    async def callback(self, interaction: discord.Interaction):
        self.current_item = self.values[0]  # the current item being clicked on (its ID)
        for option in self.options:
            option.default = option.value == self.current_item
        
        current_item_index = self.showcase_list.index(self.current_item)

        if self.current_item[0] == "0":
            for item in self.view.children:
                if not hasattr(item, "label"):
                    continue
                item.disabled = True
        else:
            self.view.children[0].disabled = (current_item_index - 1) < 0
            try:
                self.view.children[1].disabled = (self.showcase_list[current_item_index+1] == "0")
            except IndexError:
                self.view.children[1].disabled = True

        await interaction.response.edit_message(view=self.view)


class ShowcaseView(discord.ui.View):
    def __init__(self, interaction: discord.Interaction, showcase_list_backend: list, showcase_details: dict):
        self.interaction: discord.Interaction = interaction
        self.showcase_list: list = showcase_list_backend  # the actual backend contents of the showcase ["1", "10", "5"] etc
        self.showcase_details = showcase_details  # the details of each individual showcase item, excluding free slots

        super().__init__(timeout=45.0)

        self.select_item = ShowcaseDropdown(showcase_list=self.showcase_list, showcase_details=self.showcase_details)
        
        self.add_item(self.select_item)
        self.children[0].disabled = True
        self.children[1].disabled = self.showcase_list[self.showcase_list.index(self.select_item.current_item)+1] == "0"
    
    async def on_error(self, interaction: discord.Interaction, error: Exception, _) -> None:
        print_exception(type(error), error, error.__traceback__)
        await interaction.response.send_message(
            embed=membed("Your showcase did not update correctly."))

    async def on_timeout(self) -> None:
        for item in self.children:
            item.disabled = True
        try:
            await self.message.edit(view=self)
        except discord.NotFound:
            pass
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return await economy_check(interaction, self.interaction.user)
    
    def do_button_checks(self, current_item_index: int):
        previous_item_index = current_item_index - 1
        self.children[0].disabled = previous_item_index < 0
        
        next_item_index = current_item_index + 1
        try:
            self.children[1].disabled = self.showcase_list[next_item_index] == "0"
        except IndexError:
            self.children[1].disabled = True

    async def start_updating_order(self, user: discord.Member, interaction: discord.Interaction) -> None:
        async with interaction.client.pool_connection.acquire() as conn:
            conn: asqlite_Connection
            
            changedShowcase = " ".join(self.showcase_list)
            await Economy.change_bank_new(user, conn, changedShowcase, "showcase")    
            await conn.commit()
            showcase_ui_new = []

            showbed = self.message.embeds[0]
            showbed.description = "You can reorder your showcase here.\n\n"

            for i, showcase_item in enumerate(self.showcase_list, start=1):
                
                if showcase_item == "0":
                    showcase_ui_new.append(f"[**`{i}.`**](https://www.google.com) Empty slot")
                    continue

                item_data = self.showcase_details[showcase_item]
                name, emoji, _ = item_data
                
                showcase_ui_new.append(f"[**`{i}.`**](https://www.google.com) {emoji} {name}")

            showbed.description += "\n".join(showcase_ui_new)
            await interaction.response.edit_message(embed=showbed, view=self)

    @discord.ui.button(emoji="<:move_up:1213223442241818705>", row=1)
    async def move_up(self, interaction: discord.Interaction, _: discord.ui.Button):

        current_item_index = self.showcase_list.index(self.select_item.current_item)
        swap_elements(self.showcase_list, current_item_index, current_item_index-1)
        self.do_button_checks(current_item_index-1)

        await self.start_updating_order(interaction.user, interaction)

    @discord.ui.button(emoji="<:move_down:1213223440669085756>", row=1)
    async def move_down(self, interaction: discord.Interaction, _: discord.ui.Button):
        
        current_item_index = self.showcase_list.index(self.select_item.current_item)
        swap_elements(self.showcase_list, current_item_index, current_item_index+1)
        self.do_button_checks(current_item_index+1)

        await self.start_updating_order(interaction.user, interaction)


class ItemQuantityModal(discord.ui.Modal):
    def __init__(self, client: commands.Bot, item_name: str, item_cost: int, item_emoji: str):
        self.client = client
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

    async def calculate_discounted_price_if_any(
            self, user: discord.Member, 
            conn: asqlite_Connection, interaction: discord.Interaction, current_price: int) -> int:
        """Check if the user is eligible for a discount on the item."""

        data = await conn.fetchone(
            """
            SELECT inventory.qty
            FROM shop
            INNER JOIN inventory ON shop.itemID = inventory.itemID
            WHERE shop.itemID = ? AND inventory.userID = ?
            """, (12, user.id))

        if not data:
            return current_price

        discounted_price = floor((95/100) * current_price)

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

        if value is None:
            return value
        
        if value:
            self.activated_coupon = True
            return discounted_price
        return current_price
    
    # --------------------------------------------------------------------------------------------
    
    async def confirm_purchase(
            self, interaction: discord.Interaction, 
            new_price: int, true_qty: int, conn: asqlite_Connection, current_balance: int) -> None:

        value = await process_confirmation(
            interaction=interaction, 
            prompt=(
                f"Are you sure you want to buy **{true_qty:,}x {self.ie} "
                f"{self.item_name}** for **{CURRENCY} {new_price:,}**?"
            )
        )
        
        if value:
            await Economy.update_inv_new(interaction.user, true_qty, self.item_name, conn)
            new_am = await Economy.change_bank_new(interaction.user, conn, current_balance-new_price)
            await conn.commit()

            confirm = discord.Embed(
                title="Successful Purchase",
                description=(
                    f"> You have {CURRENCY} {new_am[0]:,} left.\n\n"
                    "**You bought:**\n"
                    f"- {true_qty:,}x {self.ie} {self.item_name}\n\n"
                    "**You paid:**\n"
                    f"- {CURRENCY} {new_price:,}"),
                colour=0xFFFFFF)
            confirm.set_footer(text="Thanks for your business.")

            if self.activated_coupon:
                await Economy.update_inv_new(interaction.user, -1, "Shop Coupon", conn)
                confirm.description += "\n\n**Additional info:**\n- <:coupon:1210894601829879818> 5% Coupon Discount was applied"
            await respond(interaction, embed=confirm)
    
    # --------------------------------------------------------------------------------------------

    async def on_submit(self, interaction: discord.Interaction):
        true_quantity = determine_exponent(self.quantity.value)
    
        async with self.client.pool_connection.acquire() as conn:
            conn: asqlite_Connection

            if isinstance(true_quantity, str):
                return await interaction.response.send_message(
                    embed=membed("You need to provide a real amount."), 
                    ephemeral=True
                )
            
            true_quantity = abs(true_quantity)

            if not true_quantity:
                return await interaction.response.send_message(
                    embed=membed("You need to provide a positive amount"), 
                    ephemeral=True
                )

            current_price = self.item_cost * true_quantity
            current_balance = await Economy.get_wallet_data_only(interaction.user, conn)

            new_price = await self.calculate_discounted_price_if_any(
                interaction.user, conn, interaction, current_price)
            
            if new_price is None:
                return await respond(
                    interaction=interaction,
                    embed=membed(
                        "You didn't respond in time so your purchase was cancelled."
                    )
                )
            
            if not interaction.response.is_done():
                await interaction.response.defer(thinking=True)

            if new_price > current_balance:
                return await interaction.followup.send(
                    embed=membed(
                        f"You don't have enough money to buy **{true_quantity:,}x {self.ie} {self.item_name}**."))

            await self.confirm_purchase(
                interaction, 
                new_price, 
                true_quantity, 
                conn, 
                current_balance
            )

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        print_exception(type(error), error, error.__traceback__)
        if interaction.response.is_done():
            await interaction.response.defer(thinking=True)
        await interaction.followup.send(content="Something went wrong")


class ShopItem(discord.ui.Button):
    def __init__(self, item_name: str, cost: int, ie: str,**kwargs):
        self.item_name = item_name
        self.cost = cost
        self.ie = ie
        super().__init__(style=discord.ButtonStyle.primary, emoji=self.ie, label=item_name, **kwargs)

    async def callback(self, interaction: discord.Interaction):
        if active_sessions.get(interaction.user.id):
            return await interaction.response.send_message(embed=membed(WARN_FOR_CONCURRENCY))
        
        await interaction.response.send_modal(
            ItemQuantityModal(
                interaction.client, 
                item_name=self.item_name, 
                item_cost=self.cost, 
                item_emoji=self.ie
            )
        )


class Economy(commands.Cog):

    def __init__(self, client: commands.Bot):
        self.client: commands.Bot = client

        self.not_registered = membed(
            "## <:noacc:1183086855181324490> You are not registered.\n"
            "You'll need to register first before you can use this command.\n"
            "### Already Registered?\n"
            "Find out what could've happened by calling "
            "[`>reasons`](https://www.google.com/)."
        )
        self.batch_update.start()

    @tasks.loop(hours=1)
    async def batch_update(self):
        async with self.client.pool_connection.acquire() as conn:
            conn: asqlite_Connection

            await conn.execute(
                f"""
                UPDATE `{SLAY_TABLE_NAME}` 
                SET love = CASE WHEN love - $0 < 0 THEN 0 ELSE love - $0 END, 
                hunger = CASE WHEN hunger - $1 < 0 THEN 0 ELSE hunger - $1 END,
                energy = CASE WHEN energy + $2 > 100 THEN 0 ELSE energy + $2 END,
                hygiene = CASE WHEN hygiene - $3 < 0 THEN 0 ELSE hygiene - $3 END
                """,
                5, 10, 15, 20
            )
            await conn.commit()

    @batch_update.before_loop
    async def before_update(self):
        self.batch_update.stop()

    @staticmethod
    async def partial_match_for(item_input: str, conn: asqlite_Connection):
        """If the user types part of an item name, get that item name indicated.

        This is known as partial matching for item names."""
        res = await conn.fetchall("SELECT itemName FROM shop WHERE LOWER(itemName) LIKE LOWER(?)", f"%{item_input}%")

        if res:
            if len(res) == 1:
                return res[0]
            return res
        return None

    @staticmethod
    def calculate_exp_for(*, level: int):
        """Calculate the experience points required for a given level."""
        return 12 + ceil((0.25 * level / 90.8) ** 2)

    @staticmethod
    def calculate_serv_exp_for(*, level: int):
        """Calculate the experience points required for a given level."""
        return 10 + ceil((0.75 * level / 817.9) ** 2)

    @staticmethod
    async def calculate_inventory_value(user: discord.abc.User, conn: asqlite_Connection):
        """A reusable funtion to calculate the net value of a user's inventory"""

        res = await conn.execute(
            """
            SELECT COALESCE(SUM(shop.cost * inventory.qty), 0) AS NetValue
            FROM shop
            LEFT JOIN inventory ON shop.itemID = inventory.itemID AND inventory.userID = ?
            """, (user.id,)
        )

        res = await res.fetchone()
        return res[0]

    async def create_leaderboard_preset(self, chosen_choice: str):
        """A single reused function used to map the chosen leaderboard made by the user to the associated query."""
        async with self.client.pool_connection.acquire() as conn:
            conn: asqlite_Connection = conn
            
            lb = discord.Embed(
                title=f"Leaderboard: {chosen_choice}",
                color=0x2B2D31,
                timestamp=discord.utils.utcnow()
            )

            lb.set_footer(text="Ranked globally")
            not_database = []

            if chosen_choice == 'Bank + Wallet':

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
                    f"""
                    SELECT `userID`, `cmds_ran` AS total_commands 
                    FROM `{BANK_TABLE_NAME}` 
                    GROUP BY `userID` 
                    HAVING cmds_ran > 0
                    ORDER BY total_commands DESC
                    """
                )

            else:
                data = await conn.fetchall(
                    f"""
                    SELECT `userID`, `level` AS lvl 
                    FROM `{BANK_TABLE_NAME}` 
                    GROUP BY `userID` 
                    HAVING lvl > 0
                    ORDER BY lvl DESC
                    """
                )

            for i, member in enumerate(data):
                member_name = self.client.get_user(member[0])
                their_badge = UNIQUE_BADGES.get(member_name.id, "")
                msg1 = f"**{i+1}.** {member_name.name} {their_badge} \U00003022 `{member[1]:,}`"
                not_database.append(msg1)
            
            lb.description = (
                f"Displaying the top [`{len(data)}`](https://www.quora.com/) users.\n\n"
                f"{'\n'.join(not_database) or 'No data.'}")
            return lb

    async def servant_preset(self, owner_id: int, dtls):
        """Get servant details from the given owner ID, return it in a unique servant card."""

        owner_name = self.client.get_user(owner_id)
        (
            slay_name, 
            gender, 
            productivity, 
            love, 
            energy, 
            hexx, 
            lvl, 
            xp, 
            hygiene, 
            status, 
            investment, 
            hunger,
            claimed, 
            img
            ) = (
            dtls[0], dtls[2], dtls[3], dtls[4], 
            dtls[5], dtls[7], dtls[8], dtls[9], 
            dtls[10], dtls[11], dtls[12], dtls[13], 
            dtls[-2], dtls[-1]
            )

        boundary = self.calculate_exp_for(level=lvl)
        claimed = string_to_datetime(claimed)

        sdetails = discord.Embed(
            color=hexx or GENDER_COLOURS.get(gender, 0x2B2D31), 
            title=f"{slay_name} {GENDOR_EMOJIS.get(gender)}",
            description=(
                f"Currently: {"*Awaiting orders*" if status else "*Working*"}\n"
                f"**Investment:** {CURRENCY} {investment:,}\n"
                f"**Productivity:** `{productivity}x`"
            )
        )

        sdetails.add_field(name="Hunger", value=f"{generate_progress_bar(hunger)} ({hunger}%)")
        sdetails.add_field(name="Energy", value=f"{generate_progress_bar(energy)} ({energy}%)")
        sdetails.add_field(name="Love", value=f"{generate_progress_bar(love)} ({love}%)")
        sdetails.add_field(name="Claimed", value=discord.utils.format_dt(claimed, style="D"))
        sdetails.add_field(name="Hygiene", value=f"{generate_progress_bar(hygiene)} ({hygiene}%)")
        sdetails.add_field(name='Experience', value=f"{generate_progress_bar((xp / boundary) * 100)}\n`Level {lvl}`")

        sdetails.set_footer(text=f"Belongs to {owner_name.name}", icon_url=owner_name.display_avatar.url)
        sdetails.set_image(url=img)
        return sdetails

    # ------------------ BANK FUNCS ------------------ #

    @staticmethod
    async def open_bank_new(user: discord.Member, conn_input: asqlite_Connection) -> None:
        """Register the user, if they don't exist. Only use in balance commands (reccommended.)"""
        ranumber = randint(10_000_000, 20_000_000)

        await conn_input.execute(
            f"INSERT INTO `{BANK_TABLE_NAME}` (userID, wallet, job) VALUES (?, ?, ?)",
            (user.id, ranumber, "None")
        )

    @staticmethod
    async def can_call_out(user: discord.Member | discord.User, conn_input: asqlite_Connection):
        """Check if the user is NOT in the database and therefore not registered (evaluates True if not in db).
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
    async def can_call_out_either(user1: discord.Member, user2: discord.Member, conn_input: asqlite_Connection):
        """Check if both users are in the database. (evaluates True if both users are in db.)
        Example usage:

        if not(await self.can_call_out_either(interaction.user, username, conn)):
            do something

        This is what should be done all the time to check if a user IS NOT REGISTERED."""
        data = await conn_input.fetchone(
            f"SELECT COUNT(*) FROM `{BANK_TABLE_NAME}` WHERE userID IN (?, ?)", 
            (user1.id, user2.id)
        )

        return data[0] == 2

    @staticmethod
    async def get_wallet_data_only(user: discord.Member, conn_input: asqlite_Connection) -> Optional[Any]:
        """Retrieves the wallet amount only from a registered user's bank data."""
        data = await conn_input.fetchone(f"SELECT wallet FROM `{BANK_TABLE_NAME}` WHERE userID = ?", (user.id,))
        return data[0]

    @staticmethod
    async def get_spec_bank_data(user: discord.Member, field_name: str, conn_input: asqlite_Connection) -> Any:
        """Retrieves a specific field name only from the bank table."""
        data = await conn_input.fetchone(f"SELECT {field_name} FROM `{BANK_TABLE_NAME}` WHERE userID = ?", (user.id,))
        return data[0]

    @staticmethod
    async def update_bank_new(user: discord.Member | discord.User, conn_input: asqlite_Connection,
                              amount: Union[float, int, str] = 0,
                              mode: str = "wallet") -> Optional[Any]:
        """Modifies a user's balance in a given mode: either wallet (default) or bank.
        It also returns the new balance in the given mode, if any (defaults to wallet).
        Note that conn_input is not the last parameter, it is the second parameter to be included."""

        data = await conn_input.fetchone(
            f"UPDATE `{BANK_TABLE_NAME}` SET `{mode}` = `{mode}` + ? WHERE userID = ? RETURNING `{mode}`",
            (amount, user.id))
        return data

    @staticmethod
    async def change_bank_new(
        user: discord.Member | discord.User, 
        conn_input: asqlite_Connection, 
        amount: Union[float, int, str] = 0, 
        mode: str = "wallet") -> Optional[Any]:
        """Modifies a user's field values in any given mode.

        Unlike the other updating the bank method, this function directly changes the value to the parameter ``amount``.

        It also returns the new balance in the given mode, if any (defaults to wallet).

        Note that conn_input is not the last parameter, it is the second parameter to be included."""

        data = await conn_input.execute(
            f"UPDATE `{BANK_TABLE_NAME}` SET `{mode}` = ? WHERE userID = ? RETURNING `{mode}`",
            (amount, user.id)
        )

        data = await data.fetchone()
        return data

    @staticmethod
    async def update_bank_multiple_new(
        user: discord.Member | discord.User, 
        conn_input: asqlite_Connection, 
        mode1: str, 
        amount1: Union[float, int], 
        mode2: str, 
        amount2: Union[float, int], 
        table_name: Optional[str] = "bank") -> Optional[Any]:
        """
        Modifies any two fields at once by their respective amounts. Returning the values of both fields.
        
        You are able to choose what table you wish to modify the contents of.
        """
        
        data = await conn_input.execute(
            f"UPDATE `{table_name}` SET `{mode1}` = `{mode1}` + ?, `{mode2}` = `{mode2}` + ? WHERE userID = ? "
            f"RETURNING `{mode1}`, `{mode2}`",
            (amount1, amount2, user.id))
        data = await data.fetchone()
        return data

    @staticmethod
    async def update_bank_three_new(
        user: discord.Member | discord.User, conn_input: asqlite_Connection, 
        mode1: str, 
        amount1: Union[float, int], 
        mode2: str, 
        amount2: Union[float, int], 
        mode3: str, 
        amount3: Union[float, int], 
        table_name: Optional[str] = "bank") -> Optional[Any]:
        """
        Modifies any three fields at once by their respective amounts. Returning the values of both fields.
        
        You are able to choose what table you wish to modify the contents of.
        """

        data = await conn_input.execute(
            f"""UPDATE `{table_name}` 
            SET `{mode1}` = `{mode1}` + ?, `{mode2}` = `{mode2}` + ?, `{mode3}` = `{mode3}` + ? WHERE userID = ? 
            RETURNING `{mode1}`, `{mode2}`, `{mode3}`
            """,
            (amount1, amount2, amount3, user.id))
        data = await data.fetchone()
        return data

    # ------------------ INVENTORY FUNCS ------------------ #

    @staticmethod
    async def open_inv_new(user: discord.Member, conn_input: asqlite_Connection) -> None:
        """Register a new user's inventory records into the db."""

        await conn_input.execute(f"INSERT INTO `{INV_TABLE_NAME}` (userID) VALUES(?)", (user.id,))

    @staticmethod
    async def get_one_inv_data_new(user: discord.Member, item_name: str, conn_input: asqlite_Connection) -> Optional[Any]:
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
        """Check if a user has a specific item based on its id."""
        query = (
            """
            SELECT EXISTS (
                SELECT 1
                FROM inventory
                WHERE inventory.userID = ? AND inventory.itemID = ?
            )
            """
        )

        result = await conn.fetchone(query, (user_id, item_id))
        return bool(result[0]) if result else False

    @staticmethod
    async def user_has_item_from_name(user_id: int, item_name: str, conn: asqlite_Connection) -> bool:
        """Check if a user has a specific item based on its name."""
        query = (
            """
            SELECT EXISTS (
                SELECT 1
                FROM inventory
                INNER JOIN shop ON inventory.itemID = shop.itemID
                WHERE inventory.userID = ? AND shop.itemName = ?
            )
            """
        )

        result = await conn.fetchone(query, (user_id, item_name))
        return bool(result[0]) if result else False

    @staticmethod
    async def update_inv_new(
        user: discord.Member, amount: Union[float, int], 
        item_name: str, conn: asqlite_Connection) -> Optional[Any]:
        """Modify a user's inventory."""

        item_row = await conn.fetchone(
            "SELECT itemID FROM shop WHERE itemName = ?", (item_name,))
        
        item_id = item_row[0] if item_row else None

        check_result = await conn.fetchone(
            """
            SELECT qty + ? <= 0
            FROM inventory
            WHERE userID = ? AND itemID = ?
            """, 
            (amount, user.id, item_id)
        )
        
        if check_result and check_result[0]:
            # If the resulting quantity would be <= 0, delete the row
            await conn.execute("DELETE FROM inventory WHERE userID = ? AND itemID = ?", (user.id, item_id))
            return (0,)
        
        val = await conn.execute(
            """
            INSERT INTO inventory (userID, itemID, qty)
            VALUES (?, ?, ?)
            ON CONFLICT(userID, itemID) DO UPDATE SET qty = qty + ? 
            RETURNING qty
            """, 
            (user.id, item_id, amount, amount)
        )

        val = await val.fetchone()
        return val

    @staticmethod
    async def update_user_inventory_with_random_item(user_id: int, conn: asqlite_Connection, qty: int) -> None:
        """Update user's inventory with a random item."""
        
        random_item_query = """
            SELECT itemID, itemName, emoji
            FROM shop
            ORDER BY RANDOM()
            LIMIT 1
        """

        random_item = await conn.fetchone(random_item_query)
        
        update_query = """
            INSERT INTO inventory (userID, itemID, qty)
            VALUES (?, ?, ?)
            ON CONFLICT(userID, itemID) DO UPDATE SET qty = qty + 1
        """
        await conn.execute(update_query, (user_id, random_item[0], qty))
        return random_item[1:]
    
    @staticmethod
    async def kill_the_user(user: discord.Member, conn_input: asqlite_Connection) -> None:
        """Define what it means to kill a user."""

        await conn_input.execute(
            f"UPDATE `{BANK_TABLE_NAME}` SET wallet = 0, bank = 0, showcase = ?, job = ?, bounty = 0 WHERE userID = ?", 
            ("0 0 0", "None", user.id))
        
        await conn_input.execute(f"DELETE FROM `{INV_TABLE_NAME}` WHERE userID = ?", (user.id,))
        await conn_input.execute(f"INSERT INTO `{INV_TABLE_NAME}` (userID) VALUES(?)", (user.id,))        
        await conn_input.execute(f"DELETE FROM `{SLAY_TABLE_NAME}` WHERE userID = ?", (user.id,))


    @staticmethod
    async def change_inv_new(
        user: discord.Member, 
        amount: Union[float, int, None], 
        item_name: str, 
        conn: asqlite_Connection
        ) -> Optional[Any]:
        """Change a specific attribute in the user's inventory data and return the updated value."""
        # Retrieve the item ID based on the item name
        item_row = await conn.fetchone("SELECT itemID FROM shop WHERE itemName = $0", item_name)
        
        item_id = item_row[0] if item_row else None  # Extract the item ID from the result if found

        # Update or insert the item into the user's inventory
        await conn.execute(
            """
            INSERT INTO inventory (userID, itemID, qty)
            VALUES (?, ?, ?)
            ON CONFLICT(userID, itemID) DO UPDATE SET qty = ?
            """, 
            (user.id, item_id, amount, amount)
        )


    # ------------ JOB FUNCS ----------------

    @staticmethod
    async def change_job_new(user: discord.Member, conn_input: asqlite_Connection, job_name: str) -> None:
        """Modifies a user's job, returning the new job after changes were made."""

        await conn_input.execute(
            f"UPDATE `{BANK_TABLE_NAME}` SET `job` = ? WHERE userID = ?",
            (job_name, user.id)
        )

    # ------------ cooldowns ----------------

    @staticmethod
    async def open_cooldowns(user: discord.Member, conn_input: asqlite_Connection):
        """Create a new row in the CD table, adding specified actions for a user in the cooldowns table."""
        await conn_input.execute(f"INSERT INTO `{COOLDOWN_TABLE_NAME}` (userID) VALUES(?)", (user.id,))

    @staticmethod
    def is_no_cooldown(cooldown_value: float, mode="t"):
        """Check if a user has no cooldowns."""
        if not cooldown_value:
            return True
        current_time = discord.utils.utcnow()
        timestamp_to_dt = datetime.datetime.fromtimestamp(cooldown_value, tz=timezone('UTC'))
        time_left = (timestamp_to_dt - current_time).total_seconds()
        
        if time_left > 0:
            when = current_time + datetime.timedelta(seconds=time_left)
            return discord.utils.format_dt(when, style=mode), discord.utils.format_dt(when, style="R")
        return True

    @staticmethod
    async def update_cooldown(conn_input: asqlite_Connection, *, user: discord.Member, cooldown_type: str, new_cd: str):
        """Update a user's cooldown. Requires accessing the return value via the index, so [0].

        Use this func to reset and create a cooldown."""

        data = await conn_input.execute(
            f"UPDATE `cooldowns` SET `{cooldown_type}` = ? WHERE userID = ? RETURNING `{cooldown_type}`",
            (new_cd, user.id)
        )

        data = await data.fetchone()
        return data

    # ------------ PMULTI FUNCS -------------

    @staticmethod
    async def get_pmulti_data_only(user: discord.Member, conn_input: asqlite_Connection) -> Optional[Any]:
        """Retrieves the pmulti amount only from a registered user's bank data."""
        data = await conn_input.fetchone(f"SELECT pmulti FROM `{BANK_TABLE_NAME}` WHERE userID = ?", (user.id,))
        return data

    @staticmethod
    async def change_pmulti_new(
        user: discord.Member, 
        conn_input: asqlite_Connection, 
        amount: Union[float, int] = 0, 
        mode: str = "pmulti"
        ) -> Optional[Any]:
        """Modifies a user's personal multiplier, returning the new multiplier after changes were made."""

        data = await conn_input.execute(
            f"UPDATE `{BANK_TABLE_NAME}` SET `{mode}` = ? WHERE userID = ? RETURNING `{mode}`",
            (amount, user.id))
        data = await data.fetchone()
        return data

    # ------------------- slay ----------------

    @staticmethod
    async def open_slay(conn_input: asqlite_Connection, user: discord.Member, sn: str, gd: str, dateclaim: str):
        """
        Open a new slay entry for a user in the slay database table.

        Parameters:
        - conn_input (asqlite_Connection): The SQLite database connection.
        - user (discord.Member): The Discord member for whom a new slay entry is being created.
        - sn (str): The name of the slay.
        - gd (str): The gender of the slay.
        - pd (float): The productivity value associated with the slay.
        """

        await conn_input.execute(
            "INSERT INTO slay (slay_name, userID, gender, claimed) VALUES (?, ?, ?, ?)",
            (sn, user.id, gd, dateclaim))

    @staticmethod
    async def delete_slay(conn_input: asqlite_Connection, user: discord.Member, slay_name):
        """Remove a single slay row from the db and return 1 if the row existed, 0 otherwise."""

        await conn_input.execute("DELETE FROM slay WHERE userID = ? AND slay_name = ?", (user.id, slay_name))
    

    # -----------------------------------------

    @commands.Cog.listener()
    async def on_app_command_completion(
        self, 
        interaction: discord.Interaction, 
        command: Union[app_commands.Command, app_commands.ContextMenu]
        ) -> None | discord.WebhookMessage:
        
        """
        Increment the total command ran by a user by 1 for each call. Increase the interaction user's invoker if
        they are registered. Also provide a tip if the total commands ran counter is a multiple of 15.
        """

        cmd = interaction.command
        if isinstance(cmd, app_commands.ContextMenu):
            return

        async with self.client.pool_connection.acquire() as connection:
            connection: asqlite_Connection

            if await self.can_call_out(interaction.user, connection):
                return

            async with connection.transaction():
                cmd = cmd.parent or cmd
                total = await add_command_usage(interaction.user.id, command_name=cmd.name, conn=connection)

                if not total % 15:

                    async with aiofiles.open("C:\\Users\\georg\\Documents\\c2c\\tips.txt") as f:
                        contents = await f.readlines()
                        shuffle(contents)
                        atip = choice(contents)

                    tip = discord.Embed()
                    tip.description = f"\U0001f4a1 `TIP`: {atip}"
                    tip.set_footer(text="You will be able to disable these tips.")
                    
                    return await interaction.followup.send(embed=tip, ephemeral=True)

                exp_gainable = command.extras.get("exp_gained")
                
                if not exp_gainable:
                    return

                record = await connection.fetchone(
                    'INSERT INTO `bank` (userID, exp, level) VALUES (?, 1, 1) '
                    'ON CONFLICT (userID) DO UPDATE SET exp = exp + ? RETURNING exp, level',
                    (interaction.user.id, exp_gainable)
                )

                if not record:
                    return
                
                xp, level = record
                exp_needed = self.calculate_exp_for(level=level)
                
                if xp < exp_needed:
                    return
                
                await connection.execute(
                    """
                    UPDATE `bank` 
                    SET level = level + 1, exp = 0, bankspace = bankspace + ? 
                    WHERE userID = ?
                    """,
                    (randint(300_000, 20_000_000), interaction.user.id)
                )
                
                rankup = discord.Embed()
                rankup.title = "Level Up!"
                rankup.colour = 0x55BEFF
                rankup.description = (
                    f"{choice(LEVEL_UP_PROMPTS)}, {interaction.user.name}!\n"
                    f"You've leveled up from level **{level:,}** to level **{level+1:,}**."
                )
                
                await interaction.followup.send(embed=rankup)

    # ----------- END OF ECONOMY FUNCS, HERE ON IS JUST COMMANDS --------------

    pmulti = app_commands.Group(
        name='multi', 
        description='Manage multipliers and their sources.', 
        guild_only=True, 
        guild_ids=APP_GUILDS_ID
    )

    @pmulti.command(name='view', description='Check personal and global multipliers')
    @app_commands.describe(user_name="The user whose multipliers you want to see. Defaults to your own.")
    @app_commands.rename(user_name='user')
    @app_commands.checks.cooldown(1, 6)
    async def my_multi(self, interaction: discord.Interaction, user_name: Optional[discord.Member]):
        """View a user's personal multiplier and global multipliers linked with the server invocation."""
        async with self.client.pool_connection.acquire() as conn:
            conn: asqlite_Connection

            if user_name is None:
                user_name = interaction.user

            if await Economy.can_call_out(user_name, conn):
                return await interaction.response.send_message(embed=NOT_REGISTERED)
            their_multi = await Economy.get_pmulti_data_only(user_name, conn)

            if their_multi[0] == 0 and (user_name.id == interaction.user.id):
                rand = randint(30, 90)
                await Economy.change_pmulti_new(user_name, conn, rand)
                await conn.commit()
                multi_own = discord.Embed(
                    colour=0x2B2D31, 
                    description=f'# Your new personal multiplier has been created.\n'
                                f'- Starting now, your new personal multiplier is **{rand}**%\n'
                                f' - You cannot change this multiplier, it is fixed and unique '
                                f'to your account.\n'
                                f' - Your personal multiplier will be used to determine the incre'
                                f'ase bonus rewards you receive when claiming rewards, gambling, '
                                f'and receiving robux (indicated by a <:robuxpremium:11744178153'
                                f'27998012>).\n'
                                f' - That means under these given conditions, you will receive '
                                f'**{rand}**% more of an asset/robux depending on the case.\n\n'
                                f'If you\'ve received a low roll, there is a very *small chance* '
                                f'you can request for a buff (in very unfortunate cases).')
            elif (their_multi[0] == 0) and (user_name.id != interaction.user.id):
                multi_own = discord.Embed(colour=0x2B2D31, description="No multipliers found for this user.")
                multi_own.set_author(
                    name=f'Viewing {user_name.name}\'s multipliers', 
                    icon_url=user_name.display_avatar.url)
            else:
                server_bs = SERVER_MULTIPLIERS.get(interaction.guild.id, 0)
                multi_own = discord.Embed(
                    colour=0x2B2D31, 
                    description=f'{STICKY_MESSAGE}'
                                f'Personal multiplier: **{their_multi[0]:,}**%\n'
                                f'*A multiplier that is unique to a user and is usually a fixed '
                                f'amount.*\n\n'
                                f'Global multiplier: **{server_bs:,}**%\n'
                                f'*A multiplier that changes based on the server you are calling'
                                f' commands in.*')
                multi_own.set_author(
                    name=f'Viewing {user_name.name}\'s multipliers', 
                    icon_url=user_name.display_avatar.url)

            await interaction.response.send_message(embed=multi_own)

    share = app_commands.Group(
        name='share', 
        description='share different assets with others.', 
        guild_only=True, 
        guild_ids=APP_GUILDS_ID
    )

    @share.command(name="robux", description="Share robux with another user", extras={"exp_gained": 5})
    @app_commands.rename(share_amount="amount")
    @app_commands.describe(
        recipient='The user receiving the robux shared.', 
        share_amount=ROBUX_DESCRIPTION
    )
    @app_commands.checks.cooldown(1, 6)
    async def share_robux(
        self, 
        interaction: discord.Interaction, 
        recipient: discord.Member, 
        share_amount: str
    ) -> None:
        """"Give an amount of robux to another user."""

        user = interaction.user

        async with interaction.client.pool_connection.acquire() as conn:
            conn: asqlite_Connection

            if not (await self.can_call_out_either(user, recipient, conn)):
                return await interaction.response.send_message(embed=NOT_REGISTERED)
            else:
                share_amount = determine_exponent(share_amount)
                wallet_amt_host = await Economy.get_wallet_data_only(user, conn)

                if isinstance(share_amount, str):
                    if share_amount.lower() not in {"all", "max"}:
                        return await interaction.response.send_message(
                            embed=membed("You need to provide a valid amount to share.")
                        )
                    share_amount = wallet_amt_host
                
                if not share_amount:
                    return await interaction.response.send_message(
                        embed=membed("The share amount needs to be greater than zero."))
                
                if share_amount > wallet_amt_host:
                    return await interaction.response.send_message(
                        embed=membed("You don't have that much money to share."))

                sql_query = """
                    UPDATE bank 
                    SET wallet = wallet + ? 
                    WHERE userID = ?
                """

                params_sender = (-int(share_amount), user.id)
                params_recipient = (int(share_amount), recipient.id)
                await conn.executemany(sql_query, [params_sender, params_recipient])
                await conn.commit()

                return await interaction.response.send_message(
                    embed=membed(f"Shared {CURRENCY} **{share_amount:,}** with {recipient.mention}!")
                )

    @share.command(name='items', description='Share items with another user', extras={"exp_gained": 5})
    @app_commands.describe(
        item_name='Select an item.', 
        quantity='The amount of this item to share.', 
        recipient='The user receiving the item.'
    )
    @app_commands.checks.cooldown(1, 5)
    async def share_items(
        self, 
        interaction: discord.Interaction, 
        item_name: str, 
        quantity: int, 
        recipient: discord.Member) -> None:
        """Give an amount of items to another user."""

        primm = interaction.user
        async with self.client.pool_connection.acquire() as conn:
            conn: asqlite_Connection
            
            name_res = await self.partial_match_for(item_name, conn)

            if name_res is None:
                return await interaction.response.send_message(
                    embed=membed(
                        "This item does not exist. Are you trying"
                        " to [SUGGEST](https://ptb.discord.com/channels/829053898333225010/"
                        "1121094935802822768/1202647997641523241) an item?"
                    )
                )

            elif isinstance(name_res, list):

                suggestions = [item[0] for item in name_res]
                return await interaction.response.send_message(
                    content="There is more than one item with that name pattern.\nSelect one of the following options:",
                    embed=membed(
                        '\n'.join(suggestions)
                    )
                )
            else:
                name_res = name_res[0]

                if not (await self.can_call_out_either(primm, recipient, conn)):
                    return await interaction.response.send_message(
                        embed=membed("Either you or the recipient are not registered.")
                    )
                else:

                    attrs = await conn.fetchone(
                        """
                        SELECT inventory.qty, shop.emoji, shop.rarity
                        FROM inventory
                        INNER JOIN shop ON inventory.itemID = shop.itemID
                        WHERE inventory.userID = $0 AND shop.itemName = $1
                        """, primm.id, name_res
                    )
                    
                    if attrs is None:
                        return await interaction.response.send_message(
                            embed=membed(f"You don't own a single **{name_res}**.")
                        )
                    else:
                        if attrs[0] < quantity:
                            return await interaction.response.send_message(
                                embed=membed(f"You don't have **{quantity}x {attrs[1]} {name_res}**.")
                            )
                        
                        await self.update_inv_new(recipient, +quantity, name_res, conn)
                        await self.update_inv_new(primm, -quantity, name_res, conn)
                        await conn.commit()

                        await interaction.response.send_message(
                            embed=discord.Embed(
                                colour=RARITY_COLOUR.get(attrs[-1], 0x2B2D31),
                                description=f"Shared **{quantity}x {attrs[1]} {name_res}** with {recipient.mention}!"
                            )
                        )

    showcase = app_commands.Group(
        name="showcase", 
        description="Manage your showcased items.", 
        guild_only=True, 
        guild_ids=APP_GUILDS_ID
    )

    @showcase.command(name="view", description="View your item showcase")
    @app_commands.checks.cooldown(1, 5)
    async def view_showcase(self, interaction: discord.Interaction):
        """View your current showcase. This is not what it look like on the profile."""

        async with self.client.pool_connection.acquire() as conn:
            conn: asqlite_Connection

            if await self.can_call_out(interaction.user, conn):
                return await interaction.response.send_message(embed=self.not_registered)

            showbed = discord.Embed(
                colour=0x2B2D31,
                title=f"{interaction.user.global_name}'s Showcase",
                description="You can reorder your showcase here.\n\n"
            )
            
            showbed.set_thumbnail(url=interaction.user.display_avatar.url)

            showcase: str = await self.get_spec_bank_data(interaction.user, "showcase", conn)
            showcase: list = showcase.split(" ")

            id_details = dict()
            for item_id in showcase:
                if item_id == "0":
                    continue
                showdata = await conn.fetchone(
                    """
                    SELECT shop.itemName, shop.emoji, inventory.qty
                    FROM shop
                    INNER JOIN inventory ON shop.itemID = inventory.itemID
                    WHERE shop.itemID = ? AND inventory.userID = ?
                    """, (item_id, interaction.user.id)
                )
                id_details.update({item_id: (showdata[0], showdata[1], showdata[2])})

            showcase_ui_new = []
            changes_were_made = False

            for i, showcase_item in enumerate(showcase, start=1):
                if showcase_item == "0":
                    showcase_ui_new.append(f"[**`{i}.`**](https://www.google.com) Empty slot")
                    continue
                item_data = id_details[showcase_item]
                name, emoji, qty = item_data
                
                if qty:
                    showcase_ui_new.append(
                        f"[**`{i}.`**](https://www.google.com) {emoji} {name}")
                    continue
                
                showcase[i] = "0"
                changes_were_made = True
                showcase_ui_new.append(f"[**`{i}.`**](https://www.google.com) Empty slot")

            showbed.description += "\n".join(showcase_ui_new)
            
            if changes_were_made:
                changed_showcase = " ".join(showcase)
                await self.change_bank_new(interaction.user, conn, changed_showcase, "showcase")
                await conn.commit()

            showcase_view = ShowcaseView(interaction, showcase, id_details)
            await interaction.response.send_message(embed=showbed, view=showcase_view)
            showcase_view.message = await interaction.original_response()

    @showcase.command(name="add", description="Add an item to your showcase", extras={"exp_gained": 1})
    @app_commands.checks.cooldown(1, 10)
    @app_commands.describe(item_name="Select an item.")
    async def add_showcase_item(self, interaction: discord.Interaction, item_name: str):
        """This is a subcommand. Adds an item to your showcase."""

        async with self.client.pool_connection.acquire() as conn:
            conn: asqlite_Connection

            name_res = await self.partial_match_for(item_name, conn)

            if name_res is None:
                return await interaction.response.send_message(
                    embed=membed("This item does not exist. Check the spelling and try again."))

            elif isinstance(name_res, list):

                suggestions = [item[0] for item in name_res]
                return await interaction.response.send_message(
                    content="There is more than one item with that name pattern.\nSelect one of the following options:",
                    embed=membed(
                        '\n'.join(suggestions)
                    )
                )
            else:
                name_res = name_res[0]

                data = await conn.fetchone(
                    """
                    SELECT shop.emoji, shop.itemID, inventory.qty, bank.showcase
                    FROM shop
                    INNER JOIN inventory ON shop.itemID = inventory.itemID
                    INNER JOIN bank ON bank.userID = inventory.userID
                    WHERE shop.itemName = $0 AND inventory.userID = $1
                    """, name_res, interaction.user.id
                )
                
                if data is None:
                    return await interaction.response.send_message(
                        embed=membed(f"You don't have a single **{name_res}**.")
                    )

                showcase: str = data[-1]
                showcase: list = showcase.split(" ")

                if showcase.count("0") == 0:
                    return await interaction.response.send_message(
                        embed=membed("You can only have 6 items to showcase.")
                    )

                item_id = str(data[1])
                if item_id in showcase:
                    return await interaction.response.send_message(
                        embed=membed(f"You already have a {data[0]} **{name_res}** in your showcase.")
                    )
                
                placeholder = showcase.index("0")
                showcase[placeholder] = item_id

                showcase = " ".join(showcase)
                await self.change_bank_new(interaction.user, conn, showcase, "showcase")
                await conn.commit()

                return await interaction.response.send_message(
                    embed=membed(f"Added {data[0]} **{name_res}** to your showcase!")
                )

    @showcase.command(name="remove", description="Remove an item from your showcase", extras={"exp_gained": 1})
    @app_commands.checks.cooldown(1, 10)
    @app_commands.describe(item_name="Select an item.")
    async def remove_showcase_item(
        self, 
        interaction: discord.Interaction, 
        item_name: str) -> None:
        """This is a subcommand. Removes an existing item from your showcase."""

        async with self.client.pool_connection.acquire() as conn:
            conn: asqlite_Connection

            if await self.can_call_out(interaction.user, conn):
                return await interaction.response.send_message(embed=self.not_registered)

            name_res = await self.partial_match_for(item_name, conn)

            if name_res is None:
                return await interaction.response.send_message(
                    embed=membed("This item does not exist. Check the spelling and try again."))

            elif isinstance(name_res, list):

                suggestions = [item[0] for item in name_res]
                return await interaction.response.send_message(
                    content="There is more than one item with that name pattern.\nSelect one of the following options:",
                    embed=membed('\n'.join(suggestions)))
            else:
                name_res = name_res[0]

                data = await conn.fetchone(
                    """
                    SELECT shop.emoji, shop.itemID, inventory.qty, bank.showcase
                    FROM shop
                    INNER JOIN inventory ON shop.itemID = inventory.itemID
                    INNER JOIN bank ON bank.userID = inventory.userID
                    WHERE shop.itemName = $0 AND inventory.userID = $1
                    """, name_res, interaction.user.id
                )
                
                if data is None:
                    return await interaction.response.send_message(
                        embed=membed(f"You don't have a single **{name_res}**.")
                    )

                showcase: str = data[-1]
                showcase: list = showcase.split(" ")

                item_id = str(data[1])
                if item_id not in showcase:
                    return await interaction.response.send_message(
                        embed=membed(f"You don't have a {data[0]} **{name_res}** in your showcase.")
                    )
                
                initial = showcase.index(item_id)
                showcase[initial] = "0"

                showcase = " ".join(showcase)
                await self.change_bank_new(interaction.user, conn, showcase, "showcase")
                await conn.commit()

                await interaction.response.send_message(
                    embed=membed(f"Removed {data[0]} **{name_res}** from your showcase!")
                )

    shop = app_commands.Group(
        name='shop', 
        description='view items available for purchase.', 
        guild_only=True, 
        guild_ids=APP_GUILDS_ID
    )

    @shop.command(name='view', description='View all the shop items')
    @app_commands.checks.cooldown(1, 12)
    async def view_the_shop(self, interaction: discord.Interaction):
        """This is a subcommand. View the currently available items within the shop."""

        paginator = PaginationItem(interaction)
        async with self.client.pool_connection.acquire() as conn:
            conn: asqlite_Connection

            if await self.can_call_out(interaction.user, conn):
                return await interaction.response.send_message(embed=self.not_registered)
            
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

            async def get_page_part(page: int):
                wallet = await self.get_wallet_data_only(interaction.user, conn)

                emb = discord.Embed(
                    title="Shop",
                    color=0x2B2D31,
                    description=f"> You have {CURRENCY} **{wallet:,}**.\n\n"
                )

                length = 6
                offset = (page - 1) * length

                for item in paginator.children:
                    if item.style == discord.ButtonStyle.blurple:
                        paginator.remove_item(item)

                for item_mod in additional_notes[offset:offset + length]:
                    emb.description += f"{item_mod[0]}\n"
                    item_mod[1].disabled = wallet < item_mod[1].cost
                    paginator.add_item(item_mod[1])

                n = Pagination.compute_total_pages(len(additional_notes), length)
                emb.set_footer(text=f"Page {page} of {n}")
                return emb, n
        paginator.get_page = get_page_part
        await paginator.navigate()

    @shop.command(name='sell', description='Sell an item from your inventory', extras={"exp_gained": 4})
    @app_commands.describe(
        item_name='The name of the item you want to sell.', 
        sell_quantity='The amount of this item to sell. Defaults to 1.'
    )
    async def sell(
        self, 
        interaction: discord.Interaction, 
        item_name: str, 
        sell_quantity: Optional[int] = 1) -> None:
        """Sell an item you already own."""

        sell_quantity = abs(sell_quantity)
        async with self.client.pool_connection.acquire() as conn:
            conn: asqlite_Connection

            if await self.can_call_out(interaction.user, conn):
                return await interaction.response.send_message(embed=self.not_registered)

            name_res = await self.partial_match_for(item_name, conn)

            if name_res is None:
                return await interaction.response.send_message(
                    "This item does not exist. Are you trying"
                    " to [SUGGEST](https://ptb.discord.com/channels/829053898333225010/"
                    "1121094935802822768/1202647997641523241) an item?")

            elif isinstance(name_res, list):

                suggestions = [item[0] for item in name_res]
                return await interaction.response.send_message(
                    content="There is more than one item with that name pattern.\nSelect one of the following options:",
                    embed=membed('\n'.join(suggestions)))
            else:
                name_res = name_res[0]
                wallet_amt = await conn.fetchone(
                    """
                    SELECT wallet 
                    FROM bank 
                    WHERE userID = $0
                    """, interaction.user.id)
                
                if wallet_amt is None:
                    return await interaction.response.send_message(
                        embed=membed("You don't have this item.")
                    )
                wallet_amt = wallet_amt[0]

                item_attrs = await conn.fetchone(
                    """
                    SELECT shop.emoji, shop.cost, inventory.qty
                    FROM shop
                    INNER JOIN inventory ON shop.itemID = inventory.itemID
                    WHERE shop.itemName = $0 AND inventory.userID = $1
                    """, name_res, interaction.user.id
                )

                emoji, cost, qty = item_attrs
                new_qty = qty - sell_quantity
                
                if new_qty < 0:
                    return await interaction.response.send_message(
                        embed=membed(f"You're **{abs(new_qty)}** short on selling {emoji} **{sell_quantity:,}x** {name_res}, so uh no."))

                cost = floor((cost * sell_quantity) / 4)
                value = await process_confirmation(
                    interaction=interaction, 
                    prompt=(
                        f"Are you sure you want to sell **{sell_quantity:,}x "
                        f"{emoji} {name_res}** for **{CURRENCY} {cost:,}**?"
                    )
                )

                if value:
                    await self.change_inv_new(interaction.user, new_qty, name_res, conn)
                    await self.update_bank_new(interaction.user, conn, +cost)
                    await conn.commit()

                    embed = discord.Embed()
                    embed.title = f"{interaction.user.global_name}'s Sale Receipt"
                    embed.description=(
                        f"{interaction.user.mention} sold **{sell_quantity:,}x {emoji} {name_res}** "
                        f"and got paid {CURRENCY} **{cost:,}**.")
                    embed.colour = 0x2B2D31
                    
                    embed.set_footer(text="Thanks for your business.")

                    await interaction.followup.send(embed=embed)

    @app_commands.command(name='item', description='Get more details on a specific item')
    @app_commands.describe(item_name='Select an item.')
    @app_commands.rename(item_name="name")
    @app_commands.guilds(*APP_GUILDS_ID)
    async def item(self, interaction: discord.Interaction, item_name: str):
        """This is a subcommand. Look up a particular item within the shop to get more information about it."""

        async with self.client.pool_connection.acquire() as conn:
            conn: asqlite_Connection
            name_res = await self.partial_match_for(item_name, conn)

            if name_res is None:
                return await interaction.response.send_message(
                    embed=membed("This item does not exist. Check the spelling and try again."))

            elif isinstance(name_res, list):

                suggestions = [item[0] for item in name_res]
                return await interaction.response.send_message(
                    content="There is more than one item with that name pattern.\nSelect one of the following options:",
                    embed=membed('\n'.join(suggestions)))
            else:
                name_res = name_res[0]
                data = await conn.fetchone("SELECT cost, description, image, rarity, emoji, available FROM shop WHERE itemName = ?", name_res)
                
                dynamic_text = f"> {data[1]}\n\n"
                dynamic_text += f"This item {"can" if data[5] else "cannot"} be purchased.\n"

                total_count = await conn.fetchone(
                    """
                    SELECT COALESCE(COUNT(DISTINCT userID), 0)
                    FROM inventory
                    INNER JOIN shop ON inventory.itemID = shop.itemID
                    WHERE shop.itemName = $0
                    """, name_res
                )

                total_count = total_count[0]
                dynamic_text += f"**{total_count}** {make_plural("person", total_count)} {plural_for_own(total_count)} this item.\n"
                
                their_count = await self.get_one_inv_data_new(interaction.user, name_res, conn)
                dynamic_text += f"You own **{their_count}**."

                net = await self.calculate_inventory_value(interaction.user, conn)

                if their_count:
                    amt = ((their_count*data[0])/net)*100
                    dynamic_text += f" ({amt:.1f}% of your net worth)"

                em = discord.Embed(
                    title=name_res,
                    description=dynamic_text, 
                    colour=RARITY_COLOUR.get(data[3], 0x2B2D31), 
                    url="https://www.youtube.com")
                
                em.set_thumbnail(url=data[2])
                em.add_field(name="Buying price", value=f"<:robux:1146394968882151434> {data[0]:,}")
                em.add_field(name="Selling price", value=f"<:robux:1146394968882151434> {floor(int(data[0]) / 4):,}")
                em.set_footer(text=f"This is {data[3].lower()}!")
                return await interaction.response.send_message(embed=em)

    servant = app_commands.Group(
        name='servant', 
        description='Manage your servant.', 
        guild_only=True, 
        guild_ids=APP_GUILDS_ID
    )

    @servant.command(name='hire', description='Hire your own servant')
    @app_commands.describe(name='The name of your new servant.', gender="The gender of your new servant.")
    async def hire_slv(self, interaction: discord.Interaction, name: str, gender: Literal["Male", "Female"]):
        """This is a subcommand. Hire a new slay based on the parameters, which affect the economic indicators."""

        async with self.client.pool_connection.acquire() as conn:
            conn: asqlite_Connection

            if await self.can_call_out(interaction.user, conn):
                return await interaction.response.send_message(embed=self.not_registered)

            servants = await conn.fetchall("SELECT slay_name FROM slay WHERE userID = ?", (interaction.user.id,))
            size = len(servants)

            if size >= 6:
                return await interaction.response.send_message(
                    embed=membed("You cannot have more than 6 servants."))

            dupe_check_result = await conn.fetchone("SELECT slay_name FROM slay WHERE LOWER(slay_name) = LOWER(?)", name)
            
            if dupe_check_result is not None:
                return await interaction.response.send_message(
                    embed=membed("Somebody already owns a servant with that name."))
        
            intro = choice(
                (
                    "Your servant has come fourth.", "And here they come.", 
                    "Your servant is feeling nervous upfront.", "Here come's the charm."
                )
            )

            slaye = discord.Embed(
                title=intro,
                description=(
                    "You are a stranger to your them right now.\n\n"
                    "Give them something to do or comfort them with whatever your choosing.\n"
                    "Remember, your servant can only give you what you give back:\n"
                    "- Keep them happy so that they are obedient\n"
                    "- Give them time to relax when they are zapped out\n"
                    "- They are human, they want to feel loved just like you do\n"
                    "- Give them the necessities needed to survive, food, water and the likes.\n\n"
                    "Lack of care may also lead to your servant fleeing away."),
                color=0x00FF7F)

            slaye.set_footer(text=f"{size + 1}/6 slay slots consumed")
            await self.open_slay(conn, interaction.user, name, gender, datetime_to_string(discord.utils.utcnow()))
            await conn.commit()
            await interaction.response.send_message(embed=slaye)

    @servant.command(name='abandon', description='Abandon a servant you own')
    @app_commands.describe(servant_name='The name of your servant. Must be exact, case-insensitive.')
    async def abandon_slv(self, interaction: discord.Interaction, servant_name: str):
        """This is a subcommand. Abandon an existing slay."""

        async with self.client.pool_connection.acquire() as conn:
            conn: asqlite_Connection

            if await self.can_call_out(interaction.user, conn):
                return await interaction.response.send_message(embed=self.not_registered)

            servants = await conn.fetchall(
                "SELECT slay_name, claimed FROM slay WHERE userID = $0",interaction.user.id
            )

            for servant in servants:
                if servant[0].lower() != servant_name.lower():
                    continue
                since_arrival = string_to_datetime(servant[-1])

                if (discord.utils.utcnow() - since_arrival).total_seconds() < 172_800:
                    time_required = since_arrival + datetime.timedelta(days=2)
                    return await interaction.response.send_message(
                        embed=membed(
                            "You cannot get rid of them just yet!\n"
                            f"Come back {discord.utils.format_dt(time_required, style='R')} if you're convinced"
                            f" {servant_name.title()} is not for you.")
                        )
                
                await self.delete_slay(conn, interaction.user, servant_name)
                await conn.commit()
                return await interaction.response.send_message(
                    embed=membed(f"{servant_name.title()} was told to leave.")
                )

            return await interaction.response.send_message(
                embed=membed("You don't have own a servant with this name.")
            )

    @servant.command(name='lookup', description="Look for a servant by their name")
    @app_commands.describe(servant_name="The name of the servant to look up. Must be exact, case-insensitive.")
    async def view_servents(self, interaction: discord.Interaction, servant_name: str):
        """This is a subcommand. View all current slays owned by the author or optionally another user."""

        async with self.client.pool_connection.acquire() as conn:
            conn: asqlite_Connection

            dtls = await conn.fetchone("SELECT * FROM `slay` WHERE LOWER(slay_name) = LOWER($0)", servant_name)
            if dtls is None:
                return await interaction.response.send_message(
                    embed=membed("Nobody owns a servant with the name provided.")
                )

            user_id = dtls[1]
            sep = await conn.fetchall("SELECT slay_name, gender, level, skillL FROM `slay` WHERE userID = $0", user_id)

            view = ServantsManager(
                client=self.client, 
                their_choice=servant_name, 
                owner_id=user_id, 
                owner_slays=[(slay[0], slay[1], slay[2], slay[-1]) for slay in sep], 
                conn=conn
            )
            sembed: discord.Embed = await self.servant_preset(user_id, dtls)

            await interaction.response.send_message(embed=sembed, view=view)
            view.message = await interaction.original_response()

    @servant.command(name='work', description="Assign your slays to do tasks for you")
    @app_commands.describe( servant_name="The name of the servant you want to assign a task to. Must be exact, case-insensitive.")
    async def make_servant_work(self, interaction: discord.Interaction, servant_name: str):
        """
        This is a subcommand. Dispatch your slays to work.
        The command has to be called again to receive the money gained from this action.
        """

        async with self.client.pool_connection.acquire() as conn:
            conn: asqlite_Connection

            if await self.can_call_out(interaction.user, conn):
                return await interaction.response.send_message(embed=self.not_registered)

            data = await conn.fetchone(
                """
                SELECT slay_name, work_until, skillL FROM slay
                WHERE userID = $0 AND LOWER(slay_name) = LOWER($1)
                """, interaction.user.id, servant_name
            )
            
            if data is None:
                return await interaction.response.send_message(
                    ephemeral=True,
                    embed=membed("You do not have any servants with this name.")
                )
            
            slay_name, work_until, skill_level = data

            async with conn.transaction():
                
                if not work_until:
                    prompt = DispatchServantView(
                        self.client, 
                        conn, 
                        slay_name, 
                        skill_level, 
                        interaction
                    )

                    embed = discord.Embed()
                    embed.title = "Task Menu"
                    embed.description = (
                        f"What would you like {slay_name.title()} to do?\n"
                        "Some tasks require your servant to attain a certain skill level.\n"
                        "- 25 energy points are required for <:battery_green:1203056234731671683>\n"
                        "- 50 energy points are required for <:battery_yellow:1203056272396648558>\n"
                        "- 75 energy points are required for <:battery_red:1203056297310822411>\n"
                        f"You can only pick 1 task for {slay_name.title()} to complete."
                    )
                    embed.colour = 0x2B2D31
                    
                    await interaction.response.send_message(embed=embed, view=prompt)
                    prompt.message = await interaction.original_response()
                    return

                current_time = discord.utils.utcnow()
                timestamp_to_dt = datetime.datetime.fromtimestamp(work_until, tz=timezone('UTC'))
                time_left = (timestamp_to_dt - current_time).total_seconds()
                
                if time_left:
                    when = timestamp_to_dt + datetime.timedelta(seconds=time_left)
                    relative = discord.utils.format_dt(when, style="R")
                    when = discord.utils.format_dt(when)
                    return await interaction.response.send_message(
                        embed=membed(
                            f"{slay_name} is still working.\n"
                            f"They'll be back at {when} ({relative}).")
                    )

                data = await conn.execute(
                    """
                    UPDATE `slay` set tasks_completed = tasks_completed + 1,
                    status = 1, energy = CASE WHEN energy - toreduce < 0 THEN 0 ELSE energy - toreduce END, 
                    work_until = 0 WHERE userID = ? AND slay_name = ? RETURNING toadd, hex, gender
                    """,
                    (interaction.user.id, slay_name)
                )

                data = await data.fetchone()

                hexclr = data[1] or GENDER_COLOURS.get(data[2], 0x2B2D31)
                embed = discord.Embed()
                embed.title = "Task Complete"
                embed.description = (
                    f"**{slay_name} has given you:**\n"
                    f"- {CURRENCY} {data[0]:,}"
                )
                embed.colour = hexclr
                embed.set_footer(text="No taxes!")

                res = choices([0, 1], weights=(0.85, 0.15), k=1)
                await self.update_bank_new(interaction.user, conn, data[0])
                
                if res[0]:
                    qty = randint(1, 3)
                    ranitem = await self.update_user_inventory_with_random_item(interaction.user.id, conn, qty)
                    embed.description += f"\n- {qty}x {ranitem[0]} {ranitem[1]} (bonus)\n"
                
                await interaction.response.send_message(embed=embed)
                msg = await interaction.original_response()
                await msg.add_reaction("<a:owoKonataDance:1205288135861473330>")

    @commands.command(name='reasons', description='Identify causes of registration errors')
    async def not_registered_why(self, ctx: commands.Context):
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
    async def increase_bank_space(interaction, quantity: int, conn: asqlite_Connection):
        expansion = randint(1_600_000, 6_000_000)
        expansion *= quantity
        new_bankspace = await conn.execute(
            "UPDATE bank SET bankspace = bankspace + ? WHERE userID = ? RETURNING bankspace", 
            (expansion, interaction.user.id)
        )
        new_bankspace = await new_bankspace.fetchone()
        new_amt = await Economy.update_inv_new(interaction.user, -quantity, "Bank Note", conn)
        
        embed = discord.Embed(colour=0x2B2D31)
        
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
        await interaction.response.send_message(embed=embed)

    @register_item('Trophy')
    async def handle_trophy(interaction, quantity):
        content = f'\nThey have **{quantity}** of them, WHAT A BADASS' if quantity > 1 else ''
        
        await interaction.response.send_message(
            embed=membed(
                f"{interaction.user.name} is flexing on you all "
                f"with their <:tr1:1165936712468418591> **~~PEPE~~ TROPHY**{content}"
            )
        )

    @app_commands.command(name="use", description="Use an item you own from your inventory", extras={"exp_gained": 3})
    @app_commands.guilds(*APP_GUILDS_ID)
    @app_commands.describe(item='Select an item.', quantity='Amount of items to use, when possible.')
    @app_commands.checks.cooldown(1, 6)
    async def use_item(self, interaction: discord.Interaction, item: str, quantity: Optional[int] = 1):
        """Use a currently owned item."""
        quantity = abs(quantity)

        async with self.client.pool_connection.acquire() as conn:
            conn: asqlite_Connection
            
            name_res = await self.partial_match_for(item, conn)

            if name_res is None:
                return await interaction.response.send_message(
                    embed=membed("This item does not exist. Check the spelling and try again.")
                )

            elif isinstance(name_res, list):

                suggestions = [item[0] for item in name_res]
                return await interaction.response.send_message(
                    content="There is more than one item with that name pattern.\nSelect one of the following options:",
                    embed=membed(
                        '\n'.join(suggestions)
                    )
                )
            
            else:
                name_res = name_res[0]

                data = await conn.fetchone(
                    """
                    SELECT shop.emoji, inventory.qty
                    FROM shop
                    INNER JOIN inventory ON shop.itemID = inventory.itemID
                    WHERE shop.itemName = $0 AND inventory.userID = $1
                    """, name_res, interaction.user.id
                )

                if not data:
                    return await interaction.response.send_message(
                        embed=membed(f"You don't own a single {name_res}, therefore cannot use it.")
                    )
                
                ie, qty = data
                if qty < quantity:
                    return await interaction.response.send_message(
                        embed=membed(f"You don't own **{quantity}x {ie} {name_res}**, therefore cannot use this many.")
                    )
                
                handler = item_handlers.get(name_res)
                if handler is None:
                    return await interaction.response.send_message(
                        embed=membed(f"{ie} **{name_res}** does not have a use yet.")
                    )
                
                if name_res == "Bank Note":
                    return await handler(interaction, quantity, conn)
                await handler(interaction, qty)

    @app_commands.command(name="prestige", description="Sacrifice currency stats in exchange for incremental perks")
    @app_commands.guilds(*APP_GUILDS_ID)
    @app_commands.checks.cooldown(1, 6)
    async def prestige(self, interaction: discord.Interaction):
        """Sacrifice a portion of your currency stats in exchange for incremental perks."""

        async with self.client.pool_connection.acquire() as conn:
            conn: asqlite_Connection
            
            if await self.can_call_out(interaction.user, conn):
                return await interaction.response.send_message(embed=self.not_registered)

            data = await conn.fetchone(
                """
                SELECT prestige, level, wallet, bank FROM `bank` WHERE userID = $0
                """, interaction.user.id
            )

            prestige = data[0]
            actual_level = data[1]
            actual_robux = data[2] + data[3]

            if prestige == 10:
                return await interaction.response.send_message(
                    embed=membed(
                        "You've reached the highest prestige!\n"
                        "No more perks can be obtained from this command.")
                )

            req_robux = (prestige + 1) * 24_000_000
            req_level = (prestige + 1) * 35

            if (actual_robux >= req_robux) and (actual_level >= req_level):
                massive_prompt = (
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
                
                value = await process_confirmation(
                    interaction=interaction, 
                    prompt=massive_prompt
                )

                if value:

                    await conn.execute("DELETE FROM inventory WHERE userID = ?", interaction.user.id)
                    await conn.execute(
                        f"""
                        UPDATE `{BANK_TABLE_NAME}` SET wallet = $0, bank = $0, showcase = $1, level = $2, exp = $0, 
                        prestige = prestige + 1, bankspace = bankspace + $3 
                        WHERE userID = $4
                        """, 0, '0 0 0', 1, randint(100_000_000, 500_000_000), interaction.user.id
                    )

                    await conn.commit()
            else:
                emoji = PRESTIGE_EMOTES.get(prestige + 1)
                emoji = search(r':(\d+)>', emoji)
                emoji = self.client.get_emoji(int(emoji.group(1)))

                actual_robux_progress = (actual_robux / req_robux) * 100
                actual_level_progress = (actual_level / req_level) * 100

                embed = discord.Embed(
                    title=f"Prestige {prestige + 1} Requirements",
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
                    ),
                    colour=0x2B2D31
                )
                embed.set_thumbnail(url=emoji.url)
                embed.set_footer(text="Imagine thinking you can prestige already.")
                return await interaction.response.send_message(embed=embed)

    async def do_showcase_lookup(self, raw_showcase: str, conn: asqlite_Connection, user_id):
        id_details = {}

        for item_id in raw_showcase.split():
            
            if item_id == "0":
                continue
            
            showdata = await conn.fetchone(
                """
                SELECT shop.itemName, shop.emoji, inventory.qty
                FROM shop
                INNER JOIN inventory ON shop.itemID = inventory.itemID
                WHERE shop.itemID = $0 AND inventory.userID = $1
                """, item_id, user_id
            )

            if showdata:
                id_details[item_id] = showdata

        return [
            f"`{item_data[2]}x` {item_data[1]} {item_data[0]}"
            for item_data in id_details.values()
        ]

    @app_commands.command(name='profile', description='View user information and other stats')
    @app_commands.guilds(*APP_GUILDS_ID)
    @app_commands.describe(
        user='The user whose profile you want to see.', 
        category='What type of data you want to view.'
    )
    @app_commands.checks.cooldown(1, 6)
    async def find_profile(
        self, 
        interaction: discord.Interaction, 
        user: Optional[discord.Member], 
        category: Optional[Literal["Main Profile", "Gambling Stats"]] = "Main Profile"):
        """View your profile within the economy."""

        user = user or interaction.user

        if (get_profile_key_value(f"{user.id} vis") == "private") and (interaction.user.id != user.id):
            return await interaction.response.send_message(
                embed=membed(
                    f"# <:security:1153754206143000596> {user.name}'s profile is protected.\n"
                    f"Only approved users can view {user.name}'s profile info."
                )
            )

        ephemerality = (get_profile_key_value(f"{user.id} vis") == "private") and (interaction.user.id == user.id)

        async with self.client.pool_connection.acquire() as conn:
            conn: asqlite_Connection

            if await self.can_call_out(user, conn):
                return await interaction.response.send_message(embed=NOT_REGISTERED)

            if category == "Main Profile":
                procfile = discord.Embed(colour=user.colour)

                data = await conn.fetchone(
                    f"""
                    SELECT wallet, bank, showcase, title, bounty, prestige, level, exp 
                    FROM `{BANK_TABLE_NAME}` 
                    WHERE userID = $0
                    """, user.id
                )
                wallet, bank, showcase, title, bounty, prestige, level, exp = data

                net_attrs = await conn.fetchone(
                    """
                    SELECT COALESCE(COUNT(DISTINCT inventory.itemID), 0), COALESCE(SUM(qty), 0), COALESCE(SUM(qty * cost), 0)
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

                # ------------ SERVANT STUFF ------------

                their_slays = await conn.fetchall(
                    "SELECT slay_name, level FROM slay WHERE userID = $0 ORDER BY level DESC", user.id
                )
                sized = len(their_slays)
                
                if sized:
                    first_name, first_level = their_slays[0]
                    total_slays = (f"**{first_name}** (L{first_level})")
                    if (sized-1):
                        total_slays += f"\n+ {sized-1} other(s)"
                else:
                    total_slays = "No servants"
                
                # -------------- COMMANDS --------------
                
                cmd_count = await total_commands_used_by_user(user.id, conn=conn)
                fav = await find_fav_cmd_for(user.id, conn=conn)

                # ---------------------------------------

                procfile.title = f"{user.name} - {title}"
                procfile.url = "https://www.dis.gd/support"
                procfile.description = (
                    f"""
                    {PRESTIGE_EMOTES.get(prestige, "")} Prestige Level **{prestige}** {UNIQUE_BADGES.get(prestige, "")}
                    <:bountybag:1195653667135692800> Bounty: {CURRENCY} **{bounty:,}**
                    {get_profile_key_value(f"{user.id} badges") or "No badges acquired yet"}
                    """
                )
                
                boundary = self.calculate_exp_for(level=level)
                procfile.add_field(
                    name='Level',
                    value=(
                        f"Level: `{level:,}`\n"
                        f"Experience: `{exp}/{boundary}`\n"
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
                        f"Favourite: `{fav}`"
                    )
                )

                procfile.add_field(name="Servants", value=total_slays)
                
                procfile.add_field(
                    name="Showcase", 
                    value="\n".join(showcase_ui_new) or "No showcase"
                )

                if get_profile_key_value(f"{user.id} bio"):
                    procfile.description += f"**Bio:** {get_profile_key_value(f'{user.id} bio')}"
                if get_profile_key_value(f"{user.id} avatar_url"):
                    try:
                        procfile.set_thumbnail(url=get_profile_key_value(f"{user.id} avatar_url"))
                    except discord.HTTPException:
                        modify_profile("delete", f"{user.id} avatar_url", "placeholder")
                        procfile.set_thumbnail(url=user.display_avatar.url)
                else:
                    procfile.set_thumbnail(url=user.display_avatar.url)
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

                await interaction.response.send_message(embed=stats, ephemeral=ephemerality)
                msg = await interaction.original_response()
                
                try:
                    piee = discord.Embed(title="Games played")
                    piee.colour = 0x2B2D31

                    its_sum = total_bets + total_slots + total_blackjacks
                    pie = (ImageCharts()
                           .chd(
                        f"t:{(total_bets / its_sum) * 100},"
                        f"{(total_slots / its_sum)* 100},{(total_blackjacks / its_sum) * 100}")
                           .chco("EA469E|03A9F4|FFC00C").chl(
                        f"BET ({total_bets})|SLOTS ({total_slots})|BJ ({total_blackjacks})")
                           .chdl("Total bet games|Total slot games|Total blackjack games").chli(f"{its_sum}").chs(
                        "600x480")
                           .cht("pd").chtt(f"{user.name}'s total games played"))
                    piee.set_image(url=pie.to_url())
                    
                    await msg.reply(embed=piee)
                except ZeroDivisionError:
                    await msg.reply(
                        embed=membed(
                            f"{user.mention} has not got enough data yet to form a pie chart."
                        )
                    )

    @app_commands.command(name='highlow', description='Guess the number. Jackpot wins big!', extras={"exp_gained": 3})
    @app_commands.guilds(*APP_GUILDS_ID)
    @app_commands.checks.cooldown(1, 6)
    @app_commands.describe(robux=ROBUX_DESCRIPTION)
    async def highlow(self, interaction: discord.Interaction, robux: str):
        """
        Guess the number. The user must guess if the clue the client gives is higher,
        lower or equal to the actual number.
        """

        async with self.client.pool_connection.acquire() as conn:
            conn: asqlite_Connection
            
            if await self.can_call_out(interaction.user, conn):
                return await interaction.response.send_message(embed=self.not_registered)

            wallet_amt = await self.get_wallet_data_only(interaction.user, conn)
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

            query = discord.Embed()
            query.colour = 0x2B2D31
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

            await interaction.response.send_message(view=hl_view, embed=query)
            hl_view.message = await interaction.original_response()

    @app_commands.command(name='slots', description='Try your luck on a slot machine', extras={"exp_gained": 3})
    @app_commands.guilds(*APP_GUILDS_ID)
    @app_commands.checks.cooldown(1, 2)
    @app_commands.rename(amount='robux')
    @app_commands.describe(amount=ROBUX_DESCRIPTION)
    async def slots(self, interaction: discord.Interaction, amount: str):
        """Play a round of slots. At least one matching combination is required to win."""

        async with self.client.pool_connection.acquire() as conn:
            conn: asqlite_Connection

            if await self.can_call_out(interaction.user, conn):
                await interaction.response.send_message(embed=self.not_registered)

        # --------------- Checks before betting i.e. has keycard, meets bet constraints. -------------
        has_keycard = await self.user_has_item_from_id(interaction.user.id, item_id=1, conn=conn)
        slot_stuff = await conn.fetchone("SELECT slotw, slotl, wallet FROM `bank` WHERE userID = $0", interaction.user.id)
        id_won_amount, id_lose_amount, wallet_amt = slot_stuff[0], slot_stuff[1], slot_stuff[-1]

        amount = await self.do_wallet_checks(
            interaction=interaction,
            wallet_amount=wallet_amt,
            exponent_amount=amount,
            has_keycard=has_keycard
        )
        
        if amount is None:
            return

        # ------------------ THE SLOT MACHINE ITESELF ------------------------

        emoji_outcome = generate_slot_combination()
        freq1, freq2, freq3 = emoji_outcome[0], emoji_outcome[1], emoji_outcome[2]

        async with conn.transaction():
            if emoji_outcome.count(freq1) > 1:

                new_multi = (SERVER_MULTIPLIERS.get(interaction.guild.id, 0) +
                            BONUS_MULTIPLIERS[f'{freq1 * emoji_outcome.count(freq1)}'])
                amount_after_multi = floor(((new_multi / 100) * amount) + amount)
                updated = await self.update_bank_three_new(
                    interaction.user, 
                    conn, 
                    "slotwa", amount_after_multi, 
                    "wallet", amount_after_multi, 
                    "slotw", 1
                )

                prcntw = (updated[2] / (id_lose_amount + updated[2])) * 100

                embed = discord.Embed(
                    colour=discord.Color.brand_green(),
                    description=(
                        f"""
                        **\U0000003e** {freq1} {freq2} {freq3} **\U0000003c**\n
                        **It's a match!** You've won {CURRENCY} **{amount_after_multi:,}** robux.
                        Your new balance is {CURRENCY} **{updated[1]:,}**.\n
                        You've won {prcntw:.1f}% of all slots games.
                        """)
                    )

                embed.set_author(
                    name=f"{interaction.user.name}'s winning slot machine", 
                    icon_url=interaction.user.display_avatar.url
                )
                embed.set_footer(text=f"Multiplier: {new_multi}%")

            elif emoji_outcome.count(freq2) > 1:

                new_multi = (
                    SERVER_MULTIPLIERS.get(interaction.guild.id, 0) +
                    BONUS_MULTIPLIERS[f'{freq2 * emoji_outcome.count(freq2)}']
                )
                amount_after_multi = floor(((new_multi / 100) * amount) + amount)

                updated = await self.update_bank_three_new(
                    interaction.user, 
                    conn, 
                    "slotwa", amount_after_multi, 
                    "wallet", amount_after_multi, 
                    "slotw", 1
                )

                prcntw = (updated[2] / (id_lose_amount + updated[2])) * 100

                embed = discord.Embed(
                    colour=discord.Color.brand_green(),
                    description=(
                        f"**\U0000003e** {freq1} {freq2} {freq3} **\U0000003c**\n\n"
                        f"**It's a match!** You've won {CURRENCY} **{amount_after_multi:,}** robux.\n"
                        f"Your new balance is {CURRENCY} **{updated[1]:,}**.\n"
                        f"You've won {prcntw:.1f}% of all slots games."
                    )
                )

                embed.set_footer(text=f"Multiplier: {new_multi}%")
                embed.set_author(
                    name=f"{interaction.user.name}'s winning slot machine",
                    icon_url=interaction.user.display_avatar.url
                )

            else:
                updated = await self.update_bank_three_new(
                    interaction.user, 
                    conn, 
                    "slotla", amount, 
                    "wallet", -amount, 
                    "slotl", 1
                )

                prcntl = (updated[-1] / (updated[-1] + id_won_amount)) * 100

                embed = discord.Embed(
                    colour=discord.Color.brand_red(),
                    description=(
                        f"**\U0000003e** {freq1} {freq2} {freq3} **\U0000003c**\n\n"
                        f"**No match!** You've lost {CURRENCY} **{amount:,}** robux.\n"
                        f"Your new balance is {CURRENCY} **{updated[1]:,}**.\n"
                        f"You've lost {prcntl:.1f}% of all slots games."
                    )
                )

                embed.set_author(
                    name=f"{interaction.user.name}'s losing slot machine", 
                    icon_url=interaction.user.display_avatar.url
                )

            await interaction.response.send_message(embed=embed)

    
    @app_commands.command(name='inventory', description='View your currently owned items')
    @app_commands.guilds(*APP_GUILDS_ID)
    @app_commands.describe(member='The user whose inventory you want to see.')
    async def inventory(self, interaction: discord.Interaction, member: Optional[discord.Member]):
        """View your inventory or another player's inventory."""

        member = member or interaction.user

        if (member.bot) and (member.id != self.client.user.id):
            return await interaction.response.send_message(
                embed=membed("Bots do not have accounts."))

        async with self.client.pool_connection.acquire() as conn:
            conn: asqlite_Connection

            if await self.can_call_out(member, conn):
                return await interaction.response.send_message(embed=NOT_REGISTERED)

            em = discord.Embed(color=0x2F3136)
            length = 8

            owned_items = await conn.fetchall(
                """
                SELECT shop.itemName, shop.emoji, inventory.qty
                FROM shop
                INNER JOIN inventory ON shop.itemID = inventory.itemID
                WHERE inventory.userID = $0
                """, member.id
            )

            if not owned_items:
                if member.id == interaction.user.id:
                    em.description = "You don't own any items yet."
                else:
                    em.description = f"{member.name} has nothing for you to see."
                return await interaction.response.send_message(embed=em)

            em.set_author(name=f"{member.display_name}'s Inventory", icon_url=member.display_avatar.url)
            paginator = PaginationSimple(interaction)

            async def get_page_part(page: int):
                """Helper function to determine what page of the paginator we're on."""

                offset = (page - 1) * length
                em.description = ""
                
                for item in owned_items[offset:offset + length]:
                    em.description += f"{item[1]} **{item[0]}** \U00002500 {item[2]}\n"

                n = paginator.compute_total_pages(len(owned_items), length)
                em.set_footer(text=f"Page {page} of {n}")
                return em, n
            
            paginator.get_page = get_page_part

            await paginator.navigate()

    async def do_order(self, interaction: discord.Interaction, job_name: str):
        possible_words: tuple = JOB_KEYWORDS.get(job_name)[0] 
        list_possible_words = list(possible_words)
        shuffle(list_possible_words)
        
        reduced = randint(10000000, JOB_KEYWORDS.get(job_name)[-1])
        
        selected_words = sample(list_possible_words, k=5)
        selected_words = [word.lower() for word in selected_words]

        embed = discord.Embed(
            title="Remember the order of words!",
            description="\n".join(selected_words),
            colour=0x2B2D31)

        await interaction.response.send_message(embed=embed)
        
        view = RememberOrder(
            interaction, client=self.client, 
            list_of_five_order=selected_words, their_job=job_name,
            base_reward=reduced)
        view.message = await interaction.original_response()
        
        await sleep(3)
        
        await view.message.edit(
            embed=membed("What was the order?"),
            view=view
        )

    async def do_tiles(self, interaction: discord.Interaction, job_name: str, conn: asqlite_Connection):
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
            conn, 
            all_emojis=emojis, 
            actual_emoji=emoji, 
            their_job=job_name
        )
        
        prompter.description = "What was the emoji?"
        
        view.message = await interaction.original_response()
        return await view.message.edit(embed=prompter, view=view)

    work = app_commands.Group(
        name="work", description="Work management commands", 
        guild_only=True, guild_ids=APP_GUILDS_ID)

    @work.command(name="shift", description="Fulfill a shift at your current job", extras={"exp_gained": 3})
    async def shift_at_work(self, interaction: discord.Interaction):
        async with self.client.pool_connection.acquire() as conn:
            conn: asqlite_Connection

            if await self.can_call_out(interaction.user, conn):
                return await interaction.response.send_message(embed=self.not_registered)
            
            data = await conn.fetchall(
                """
                SELECT work FROM cooldowns WHERE userID = $0 UNION ALL SELECT job FROM bank WHERE userID = $0
                """, interaction.user.id
            )

            job_name = data[1][0]
            if job_name == "None":
                    return await interaction.response.send_message(
                        embed=membed("You don't have a job, get one first.")
                    )

            has_cd = self.is_no_cooldown(data[0][0])
            if isinstance(has_cd, tuple):
                return await interaction.response.send_message(
                    embed=membed(f"You can work again at {has_cd[0]} ({has_cd[1]}).")
                )

            async with conn.transaction():
                ncd = (discord.utils.utcnow() + datetime.timedelta(minutes=40)).timestamp()
                await self.update_cooldown(conn, user=interaction.user, cooldown_type="work", new_cd=ncd)

            possible_minigames = choices((1, 2), k=1, weights=(35, 65))[0]
            num_to_func_link = {
                2: "do_order",
                1: "do_tiles"
            }

            method_name = num_to_func_link[possible_minigames]
            method = getattr(self, method_name)
            if method_name == "do_order": 
                return await method(interaction, job_name)
            await method(interaction, job_name, conn)

    @work.command(name="apply", description="Apply for a job", extras={"exp_gained": 1})
    @app_commands.rename(chosen_job="job")
    @app_commands.describe(chosen_job='The job you want to apply for.')
    @app_commands.checks.cooldown(1, 6)
    async def get_job(
        self, 
        interaction: discord.Interaction, 
        chosen_job: Literal['Plumber', 'Cashier', 'Fisher', 'Janitor', 'Youtuber', 'Police']):

        async with self.client.pool_connection.acquire() as conn:
            conn: asqlite_Connection

            if await self.can_call_out(interaction.user, conn):
                return await interaction.response.send_message(embed=self.not_registered)
            
            data = await conn.fetchall(
                """
                SELECT job_change FROM cooldowns WHERE userID = $0 UNION ALL SELECT job FROM bank WHERE userID = $0
                """, interaction.user.id
            )

            has_cd = self.is_no_cooldown(cooldown_value=data[0][0])
            
            if isinstance(has_cd, tuple):
                embed = discord.Embed(
                    title="Cannot perform this action", 
                    description=f"You can change your job {has_cd[1]}.", 
                    colour=0x2B2D31)
                    
                return await interaction.response.send_message(embed=embed)

            async with conn.transaction():
                
                if data[1][0] != "None":
                    return await interaction.response.send_message(
                    embed=membed(
                        f"You are already working as a **{data[1][0]}**.\n"
                        "You'll have to resign first using /work resign."))

                ncd = (discord.utils.utcnow() + datetime.timedelta(days=2)).timestamp()
                await self.update_cooldown(
                    conn, user=interaction.user, cooldown_type="job_change", new_cd=ncd)
                
                await self.change_job_new(interaction.user, conn, job_name=chosen_job)
                embed = discord.Embed()
                embed.title = f"Congratulations, you are now working as a {chosen_job}"
                embed.description = "You can start working now for every 40 minutes."
                embed.colour = 0x2B2D31
                await interaction.response.send_message(embed=embed)
    
    @work.command(name="resign", description="Resign from your current job")
    @app_commands.checks.cooldown(1, 6)
    async def job_resign(self, interaction: discord.Interaction):
        async with self.client.pool_connection.acquire() as conn:
            conn: asqlite_Connection

            if await self.can_call_out(interaction.user, conn):
                return await interaction.response.send_message(embed=self.not_registered)

            data = await conn.fetchall(
                """
                SELECT job_change FROM cooldowns WHERE userID = $0 UNION ALL SELECT job FROM bank WHERE userID = $0
                """, interaction.user.id
            )

            if data[1][0] == "None":
                return await interaction.response.send_message(embed=membed("You're already unemployed."))

            has_cd = self.is_no_cooldown(cooldown_value=data[0][0])

            if isinstance(has_cd, tuple):
                embed = discord.Embed(
                    title="Cannot perform this action", 
                    description=f"You can change your job {has_cd[1]}.", 
                    colour=0x2B2D31)

                return await interaction.response.send_message(embed=embed)

            value = await process_confirmation(
                interaction=interaction, 
                prompt=(
                    f"Are you sure you want to resign from your current job as a **{data[1][0]}**?\n"
                    "You won't be able to apply to another job for the next 48 hours."
                )
            )

            if value:
                ncd = (discord.utils.utcnow() + datetime.timedelta(days=2)).timestamp()
                await self.update_cooldown(conn, user=interaction.user, cooldown_type="job_change", new_cd=ncd)
                await self.change_job_new(interaction.user, conn, job_name='None')
    
    @app_commands.command(name="balance", description="Get someone's balance. Wallet, bank, and net worth.")
    @app_commands.describe(user='The user to find the balance of.', with_force='Register this user if not already. Only for bot owners.')
    @app_commands.guilds(*APP_GUILDS_ID)
    async def find_balance(self, interaction: discord.Interaction, user: Optional[discord.Member], with_force: Optional[bool]):
        
        user = user or interaction.user

        async with self.client.pool_connection.acquire() as conn:
            conn: asqlite_Connection

            if await self.can_call_out(user, conn) and (user.id != interaction.user.id):
                if with_force and (interaction.user.id in self.client.owner_ids):
                    await self.open_bank_new(user, conn)
                    await self.open_inv_new(user, conn)
                    await self.open_cooldowns(user, conn)
                    await conn.commit()

                    return await interaction.response.send_message(embed=membed(f"Force registered {user.mention}."))
                
                await interaction.response.send_message(embed=membed(f"{user.mention} isn't registered."))

            elif await self.can_call_out(user, conn) and (user.id == interaction.user.id):

                await self.open_bank_new(user, conn)
                await self.open_inv_new(user, conn)
                await self.open_cooldowns(user, conn)
                await conn.commit()

                norer = membed(
                    f"# <:successful:1183089889269530764> You are now registered.\n"
                    f"Your records have been added in our database, {user.mention}.\n"
                    f"From now on, you may use any of the economy commands.\n"
                    f"Here are some of our top used commands:\n"
                    f"### 1. Start earning quick robux:\n"
                    f" - </bet:1172898644622585883>, "
                    f"</coinflip:1172898644622585882> </slots:1172898644287029332>, "
                    f"</step:1172898643884380166>, </highlow:1172898644287029331>\n"
                    f"### 2. Seek out employment:\n "
                    f" - </getjob:1172898643884380168>, </work:1172898644287029336>\n"
                    f"### 3. Customize your look:\n"
                    f" - </editprofile bio:1172898645532749948>, "
                    f"</editprofile avatar:1172898645532749948>\n"
                    f"### 4. Manage your Account:\n"
                    f" - </balance:1172898644287029337>, "
                    f"</withdraw:1172898644622585876>, </deposit:1172898644622585877>, "
                    f"</inventory:1172898644287029333>, </shop view:1172898645532749946>, "
                    f"</buy:1172898644287029334>"
                )
                
                return await interaction.response.send_message(embed=norer)
            else:
                nd = await conn.execute("SELECT wallet, bank, bankspace FROM `bank` WHERE userID = ?", (user.id,))
                nd = await nd.fetchone()
                bank = nd[0] + nd[1]
                inv = await self.calculate_inventory_value(user, conn)

                space = (nd[1] / nd[2]) * 100

                balance = discord.Embed(
                    title=f"{user.name}'s balances", 
                    colour=0x2B2D31, 
                    timestamp=discord.utils.utcnow(), 
                    url="https://dis.gd/support"
                )

                balance.add_field(name="Wallet", value=f"{CURRENCY} {nd[0]:,}")
                balance.add_field(name="Bank", value=f"{CURRENCY} {nd[1]:,}")
                balance.add_field(name="Bankspace", value=f"{CURRENCY} {nd[2]:,} ({space:.2f}% full)")
                balance.add_field(name="Money Net", value=f"{CURRENCY} {bank:,}")
                balance.add_field(name="Inventory Net", value=f"{CURRENCY} {inv:,}")
                balance.add_field(name="Total Net", value=f"{CURRENCY} {inv + bank:,}")
                
                view = BalanceView(interaction, self.client, nd[0], nd[1], nd[2], user)
                await interaction.response.send_message(embed=balance, view=view)
                view.message = await interaction.original_response()

    @app_commands.command(name="weekly", description="Get a weekly injection of robux to your bank")
    @app_commands.guilds(*APP_GUILDS_ID)
    async def weekly(self, interaction: discord.Interaction):
        """Get a weekly injection of robux once per week."""

        async with self.client.pool_connection.acquire() as conn:
            conn: asqlite_Connection

            if await self.can_call_out(interaction.user, conn):
                return await interaction.response.send_message(embed=self.not_registered)

            ncd = await conn.fetchone("SELECT weekly FROM cooldowns WHERE userID = ?", (interaction.user.id,))
            has_cd = self.is_no_cooldown(ncd[0])

            if isinstance(has_cd, tuple):
                return await interaction.response.send_message(
                    embed=membed(f"You already got your weekly robux this week, try again {has_cd[1]}."))
            
            success = discord.Embed()
            success.colour = 0x2B2D31
            success.title = f"{interaction.user.display_name}'s Weekly Robux"
            success.url = "https://www.youtube.com/watch?v=ue_X8DskUN4"
            
            async with conn.transaction():
                next_week = discord.utils.utcnow() + datetime.timedelta(weeks=1)
                ncd = discord.utils.format_dt(next_week, style="R")
                
                success.description=(
                    f"You just got {CURRENCY} **10,000,000** for checking in this week.\n"
                    f"See you next week ({ncd})!"
                )
                
                await self.update_cooldown(conn, user=interaction.user, cooldown_type="weekly", new_cd=next_week.timestamp())
                await self.update_bank_new(interaction.user, conn, 10_000_000)

            await interaction.response.send_message(embed=success)

    @app_commands.command(name="resetmydata", description="Opt out of the virtual economy, deleting all of your data")
    @app_commands.guilds(*APP_GUILDS_ID)
    @app_commands.describe(member='The player to remove all of the data of. Defaults to the user calling the command.')
    async def discontinue_bot(self, interaction: discord.Interaction, member: Optional[discord.Member]):
        """Opt out of the virtual economy and delete all of the user data associated."""

        if active_sessions.get(interaction.user.id):
            return await interaction.response.send_message(embed=membed(WARN_FOR_CONCURRENCY))

        member = member or interaction.user
        if interaction.user.id not in self.client.owner_ids:
            if (member is not None) and (member != interaction.user):
                return await interaction.response.send_message(
                    embed=membed("You are not allowed to do this."))

        async with self.client.pool_connection.acquire() as conn:
            conn: asqlite_Connection

            if await self.can_call_out(member, conn):
                await interaction.response.send_message(
                    embed=membed(f"Could not find {member.mention} in the database."))
            else:

                active_sessions.update({interaction.user.id: 1})

                view = ConfirmResetData(interaction=interaction, client=self.client, user_to_remove=member)
                link = "https://www.youtube.com/shorts/vTrH4paRl90"            
                await interaction.response.send_message(
                    embed=membed(
                        f"This command will reset **[EVERYTHING]({link})**.\n"
                        "Are you **SURE** you want to do this?\n\n"
                        "If you do, click `RESET MY DATA` **3** times."), view=view)
                view.message = await interaction.original_response()

    @app_commands.command(name="withdraw", description="Withdraw robux from your bank account")
    @app_commands.guilds(*APP_GUILDS_ID)
    @app_commands.describe(robux=ROBUX_DESCRIPTION)
    async def withdraw(self, interaction: discord.Interaction, robux: str):
        """Withdraw a given amount of robux from your bank."""

        user = interaction.user
        actual_amount = determine_exponent(robux)

        async with (self.client.pool_connection.acquire() as conn):
            conn: asqlite_Connection
            if await self.can_call_out(interaction.user, conn):
                await interaction.response.send_message(embed=self.not_registered)

            bank_amt = await self.get_spec_bank_data(interaction.user, "bank", conn)

            if isinstance(actual_amount, str):
                if actual_amount.lower() == "all" or actual_amount.lower() == "max":

                    if not bank_amt:
                        return await interaction.response.send_message(
                            embed=membed("You have nothing to withdraw."))

                    wallet_new = await self.update_bank_new(user, conn, +bank_amt)
                    bank_new = await self.update_bank_new(user, conn, -bank_amt, "bank")
                    await conn.commit()

                    embed = discord.Embed(colour=0x2B2D31)

                    embed.add_field(
                        name="<:withdraw:1195657655134470155> Withdrawn", 
                        value=f"{CURRENCY} {bank_amt:,}", 
                        inline=False
                    )
                    embed.add_field(name="Current Wallet Balance", value=f"{CURRENCY} {wallet_new[0]:,}")
                    embed.add_field(name="Current Bank Balance", value=f"{CURRENCY} {bank_new[0]:,}")

                    return await interaction.response.send_message(embed=embed)
                return await interaction.response.send_message(
                    embed=membed("You need to provide a real amount to withdraw."))

            amount_conv = abs(int(actual_amount))

            if not amount_conv:
                return await interaction.response.send_message(
                    embed=membed("The amount to withdraw needs to be greater than 0."))

            elif amount_conv > bank_amt:
                return await interaction.response.send_message(
                    embed=membed(f"You only have {CURRENCY} **{bank_amt:,}** in your bank right now.")
                )

            else:
                wallet_new = await self.update_bank_new(user, conn, +amount_conv)
                bank_new = await self.update_bank_new(user, conn, -amount_conv, "bank")
                await conn.commit()

                embed = discord.Embed(colour=0x2B2D31)
                
                embed.add_field(
                    name="<:withdraw:1195657655134470155> Withdrawn", 
                    value=f"{CURRENCY} {amount_conv:,}", 
                    inline=False
                )
                
                embed.add_field(name="Current Wallet Balance", value=f"{CURRENCY} {wallet_new[0]:,}")
                embed.add_field(name="Current Bank Balance", value=f"{CURRENCY} {bank_new[0]:,}")

                return await interaction.response.send_message(embed=embed)

    @app_commands.command(name='deposit', description="Deposit robux into your bank account")
    @app_commands.guilds(*APP_GUILDS_ID)
    @app_commands.describe(robux=ROBUX_DESCRIPTION)
    async def deposit(self, interaction: discord.Interaction, robux: str):
        """Deposit an amount of robux into your bank."""

        user = interaction.user
        actual_amount = determine_exponent(robux)

        async with self.client.pool_connection.acquire() as conn:
            conn: asqlite_Connection

            if await self.can_call_out(interaction.user, conn):
                return await interaction.response.send_message(embed=self.not_registered)

            details = await conn.execute("SELECT wallet, bank, bankspace FROM `bank` WHERE userID = ?",
                                         (interaction.user.id,))
            details = await details.fetchone()
            wallet_amt = details[0]

            if isinstance(actual_amount, str):
                if actual_amount.lower() == "all" or actual_amount.lower() == "max":
                    available_bankspace = details[2] - details[1]

                    if not available_bankspace:
                        return await interaction.response.send_message(
                            embed=membed(
                                f"You can only hold **{CURRENCY} {details[2]:,}** in your bank right now.\n"
                                f"To hold more, use currency commands and level up more."
                            )
                        )

                    available_bankspace = min(wallet_amt, available_bankspace)
                    
                    if not available_bankspace:
                        return await interaction.response.send_message(embed=membed("You have nothing to deposit."))

                    wallet_new = await self.update_bank_new(user, conn, -available_bankspace)
                    bank_new = await self.update_bank_new(user, conn, +available_bankspace, "bank")
                    await conn.commit()

                    embed = discord.Embed(colour=0x2B2D31)
                    
                    embed.add_field(
                        name="<:deposit:1195657772231036948> Deposited", 
                        value=f"{CURRENCY} {available_bankspace:,}", 
                        inline=False
                    )

                    embed.add_field(name="Current Wallet Balance", value=f"{CURRENCY} {wallet_new[0]:,}")
                    embed.add_field(name="Current Bank Balance", value=f"{CURRENCY} {bank_new[0]:,}")

                    return await interaction.response.send_message(embed=embed)
                return await interaction.response.send_message(
                    embed=membed("You need to provide a real amount to deposit."))

            amount_conv = abs(int(actual_amount))
            available_bankspace = details[2] - details[1]
            available_bankspace -= amount_conv

            if amount_conv > wallet_amt:
                return await interaction.response.send_message(
                    embed=membed(f"You only have {CURRENCY} **{wallet_amt:,}** in your wallet right now.")
                )

            elif not amount_conv:
                return await interaction.response.send_message(
                    embed=membed("The amount to deposit needs to be greater than 0.")
                )
            elif available_bankspace < 0:
                return await interaction.response.send_message(
                    embed=membed(
                        f"You can only hold **{CURRENCY} {details[2]:,}** in your bank right now.\n"
                        f"To hold more, use currency commands and level up more."))
            else:
                wallet_new = await self.update_bank_new(user, conn, -amount_conv)
                bank_new = await self.update_bank_new(user, conn, +amount_conv, "bank")
                await conn.commit()

                embed = discord.Embed(colour=0x2B2D31)
                
                embed.add_field(
                    name="<:deposit:1195657772231036948> Deposited", 
                    value=f"{CURRENCY} {amount_conv:,}", 
                    inline=False
                )

                embed.add_field(name="Current Wallet Balance", value=f"{CURRENCY} {wallet_new[0]:,}")
                embed.add_field(name="Current Bank Balance", value=f"{CURRENCY} {bank_new[0]:,}")

                return await interaction.response.send_message(embed=embed)

    @app_commands.command(name='leaderboard', description='Rank users based on various stats')
    @app_commands.guilds(*APP_GUILDS_ID)
    @app_commands.checks.cooldown(1, 6)
    @app_commands.describe(stat="The stat you want to see.")
    async def get_leaderboard(self, interaction: discord.Interaction,
                              stat: Literal[
                                  "Bank + Wallet", "Wallet", "Bank", "Inventory Net", "Bounty", "Commands", "Level"]):
        """View the leaderboard and filter the results based on different stats inputted."""

        if active_sessions.get(interaction.channel.id):
            return await interaction.response.send_message(
                embed=membed("The command is still active in this channel."))
        active_sessions.update({interaction.channel.id: 1})

        lb_view = Leaderboard(self.client, stat, channel_id=interaction.channel.id)
        lb = await self.create_leaderboard_preset(chosen_choice=stat)

        await interaction.response.send_message(embed=lb, view=lb_view)
        lb_view.message = await interaction.original_response()

    @app_commands.command(name='rob', description='Rob robux from another user', extras={"exp_gained": 4})
    @app_commands.rename(other="user")
    @app_commands.guilds(*APP_GUILDS_ID)
    @app_commands.describe(other='The user you want to rob money from.')
    @app_commands.checks.cooldown(1, 6)
    async def rob_the_user(self, interaction: discord.Interaction, other: discord.Member):
        """Rob someone else."""
        primary_id = str(interaction.user.id)
        other_id = str(other.id)

        if other_id == primary_id:
            embed = membed('Seems pretty foolish to steal from yourself')
            return await interaction.response.send_message(embed=embed)
        elif other.bot:
            embed = membed('You are not allowed to steal from bots, back off my kind')
            return await interaction.response.send_message(embed=embed)
        else:
            async with self.client.pool_connection.acquire() as conn:
                if not (await self.can_call_out_either(interaction.user, other, conn)):
                    return await interaction.response.send_message(
                        embed=membed(f'Either you or {other.mention} are not registered.')
                    )

                prim_d = await conn.execute("SELECT wallet, job, bounty from `bank` WHERE userID = ?",
                                            (interaction.user.id,))
                prim_d = await prim_d.fetchone()
                host_d = await conn.execute("SELECT wallet, job from `bank` WHERE userID = ?", (other.id,))
                host_d = await host_d.fetchone()

                if host_d[0] < 1_000_000:
                    return await interaction.response.send_message(
                        embed=membed(f"{other.mention} doesn't even have {CURRENCY} **1,000,000**, not worth it.")
                    )
                if prim_d[0] < 10_000_000:
                    return await interaction.response.send_message(
                        embed=membed(f"You need at least {CURRENCY} **10,000,000** in your wallet to rob someone.")
                    )

                result = choices([0, 1], weights=(49, 51), k=1)
                
                embed = discord.Embed(colour=0x2B2D31)
                async with conn.transaction():
                    if not result[0]:
                        emote = choice(
                            [
                                "<a:kekRealize:970295657233539162>", "<:smhlol:1160157952410386513>", 
                                "<:z_HaH:783399959068016661>", "<:lmao:784308818418728972>", 
                                "<:lamaww:789865027007414293>", "<a:StoleThisEmote5:791327136296075327>", 
                                "<:jerryLOL:792239708364341258>", "<:dogkekw:797946573144850432>"])
                        
                        fine = randint(1, prim_d[0])
                        embed.description = (
                            f'You were caught lol {emote}\n'
                            f'You paid {other.mention} {CURRENCY} **{fine:,}**.'
                        )

                        b = prim_d[-1]
                        if b:
                            fine += b
                            embed.description += (
                                "\n\n**Bounty Status:**\n"
                                f"{other.mention} was also given your bounty of **{CURRENCY} {b:,}**."
                            )

                            await self.update_bank_new(other, conn, +fine)
                            await self.update_bank_new(interaction.user, conn, -fine)
                            await conn.execute("UPDATE `bank` SET bounty = 0 WHERE userID = ?", (interaction.user.id,))
                            
                            return await interaction.response.send_message(embed=embed)
                        
                        await self.update_bank_new(interaction.user, conn, -fine)
                        await self.update_bank_new(other, conn, +fine)
                        return await interaction.response.send_message(embed=embed)

                    amt_stolen = randint(1_000_000, host_d[0])
                    lost = floor((25 / 100) * amt_stolen)
                    total = amt_stolen - lost
                    percent_stolen = floor((total/amt_stolen) * 100)

                    await self.update_bank_new(interaction.user, conn, +total)
                    await self.update_bank_new(other, conn, -total)
                    
                    if percent_stolen >= 75:
                        embed.title = "You stole BASICALLY EVERYTHING YOU POSSIBLY COULD!"
                        embed.set_thumbnail(url="https://i.imgur.com/jY3PzTv.png")
                    if percent_stolen >= 50:
                        embed.title = "You stole a fairly decent chunk!"
                        embed.set_thumbnail(url="https://i.imgur.com/eNIT8qw.png")
                    if percent_stolen >= 25:
                        embed.title = "You stole a small portion!"
                        embed.set_thumbnail(url="https://i.imgur.com/148ClcS.png")
                    else:
                        embed.title = "You stole a TINY portion!"
                        embed.set_thumbnail(url="https://i.imgur.com/nZmHhJX.png")
                    
                    embed.description = (
                        f"""
                        **You managed to get:**
                        {CURRENCY} {amt_stolen:,} (but dropped {CURRENCY} {lost:,} while escaping)
                        """
                    )

                    embed.set_footer(text=f"You stole {CURRENCY} {total:,} in total")
                    return await interaction.response.send_message(embed=embed)

    @app_commands.command(name='bankrob', description="Gather people to rob someone's bank")
    @app_commands.guilds(*APP_GUILDS_ID)
    @app_commands.describe(user='The user to attempt to bankrob.')
    @app_commands.checks.cooldown(1, 60)
    async def bankrob_the_user(self, interaction: discord.Interaction, user: discord.Member):
        """Rob someone else's bank."""
        starter_id = interaction.user.id
        user_id = user.id

        if user_id == starter_id:
            return await interaction.response.send_message(
                embed=membed("You can't bankrob yourself."))
        elif user.bot:
            return await interaction.response.send_message(
                embed=membed("You can't bankrob bots."))
        else:
            return await interaction.response.send_message(
                embed=membed("This command is under construction."))
        
            async with self.client.pool_connection.acquire() as conn:
                if not (await self.can_call_out_either(interaction.user, user, conn)):
                    return await interaction.response.send_message(
                        embed=membed(f"Either you or {user.mention} aren't registered.")
                    )
                wallet = await self.get_wallet_data_only(interaction.user, conn)
                
                if wallet < 1e6:
                    return await interaction.response.send_message(
                        embed=membed(
                            f"You need at least {CURRENCY} **1,000,000** in your wallet to start a bankrobbery."
                        )
                    )

    @app_commands.command(name='coinflip', description='Bet your robux on a coin flip', extras={"exp_gained": 3})
    @app_commands.guilds(*APP_GUILDS_ID)
    @app_commands.describe(
        bet_on='The side of the coin you bet it will flip on.', 
        amount=ROBUX_DESCRIPTION
    )
    @app_commands.checks.cooldown(1, 6)
    @app_commands.rename(bet_on='side', amount='robux')
    async def coinflip(self, interaction: discord.Interaction, bet_on: str, amount: str):
        """Flip a coin and make a bet on what side of the coin it flips to."""

        user = interaction.user
        bet_on = "heads" if "h" in bet_on.lower() else "tails"
        
        async with interaction.client.pool_connection.acquire() as conn:
            conn: asqlite_Connection
            
            wallet_amt = await self.get_wallet_data_only(interaction.user, conn)
            has_keycard = await self.user_has_item_from_id(
                user_id=interaction.user.id,
                item_id=1,
                conn=conn
            )
            
            amount = await self.do_wallet_checks(
                interaction=interaction,
                wallet_amount=wallet_amt,
                exponent_amount=amount,
                has_keycard=has_keycard
            )

            if amount is None:
                return

            if await self.can_call_out(interaction.user, conn):
                return await interaction.response.send_message(embed=self.not_registered)

            result = choice(("heads", "tails"))

            async with conn.transaction():
                if result != bet_on:
                    await self.update_bank_new(user, conn, -amount)
                    return await interaction.response.send_message(
                        embed=membed(
                            f"You got {result}, meaning you lost {CURRENCY} **{amount:,}**."
                        )
                    )

                await self.update_bank_new(user, conn, +amount)
                return await interaction.response.send_message(
                    embed=membed(
                        f"You got {result}, meaning you won {CURRENCY} **{amount:,}**."
                    )
                )

    @app_commands.command(
            name="blackjack", 
            description="Test your skills at blackjack", 
            extras={"exp_gained": 3}
    )
    @app_commands.guilds(*APP_GUILDS_ID)
    @app_commands.checks.cooldown(1, 4)
    @app_commands.rename(bet_amount='robux')
    @app_commands.describe(bet_amount=ROBUX_DESCRIPTION)
    async def play_blackjack(self, interaction: discord.Interaction, bet_amount: str):
        """Play a round of blackjack with the bot. Win by reaching 21 or a score higher than the bot without busting."""

        # ------ Check the user is registered or already has an ongoing game ---------
        
        if len(self.client.games) >= 2:
            return await interaction.response.send_message(
                embed=membed("The maximum number of concurrent games has been reached.")
            )

        if self.client.games.get(interaction.user.id) is not None:
            return await interaction.response.send_message(
                embed=membed("You already have an ongoing game taking place.")
            )

        async with self.client.pool_connection.acquire() as conn:
            conn: asqlite_Connection
            
            if await self.can_call_out(interaction.user, conn):
                return await interaction.response.send_message(embed=self.not_registered)

        has_keycard = await self.user_has_item_from_id(interaction.user.id, item_id=1, conn=conn)
        
        wallet_amt, pmulti = await conn.fetchone(
            """
            SELECT wallet, pmulti
            FROM bank
            WHERE userID = $0
            """, interaction.user.id
        )

        # ----------- Check what the bet amount is, converting where necessary -----------

        namount = await self.do_wallet_checks(
            interaction=interaction, 
            has_keycard=has_keycard,
            wallet_amount=wallet_amt,
            exponent_amount=bet_amount
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
            bj_lose = await conn.fetchone('SELECT bjl FROM bank WHERE userID = $0', interaction.user.id)
            new_bj_win = await self.update_bank_new(interaction.user, conn, 1, "bjw")
            new_total = new_bj_win[0] + bj_lose[0]

            prctnw = (new_bj_win[0] / new_total) * 100
            new_multi = SERVER_MULTIPLIERS.get(interaction.guild.id, 0) + pmulti
            amount_after_multi = floor(((new_multi / 100) * namount) + namount) + randint(1, 999)
            new_amount_balance = await self.update_bank_new(interaction.user, conn, amount_after_multi)
            await conn.commit()

            d_fver_p = display_user_friendly_deck_format(player_hand)
            d_fver_d = display_user_friendly_deck_format(dealer_hand)

            winner = discord.Embed(colour=discord.Colour.brand_green())
            winner.description = (
                f"**Blackjack! You've already won with a total of {player_sum}!**\n"
                f"You won {CURRENCY} **{amount_after_multi:,}**. "
                f"You now have {CURRENCY} **{new_amount_balance[0]:,}**.\n"
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
                name=f"{interaction.client.user.name} (Dealer)", 
                value=(
                    f"**Cards** - {d_fver_d}\n"
                    f"**Total** - `{dealer_sum}`"
                )
            )
            
            winner.set_author(
                name=f"{interaction.user.name}'s winning blackjack game", 
                icon_url=interaction.user.display_avatar.url
            )
            
            return await interaction.response.send_message(embed=winner)

        shallow_pv = [display_user_friendly_card_format(number) for number in player_hand]
        shallow_dv = [display_user_friendly_card_format(number) for number in dealer_hand]

        self.client.games[interaction.user.id] = (deck, player_hand, dealer_hand, shallow_dv, shallow_pv, namount)

        initial = discord.Embed()
        initial.colour = 0x2B2D31
        initial.description = (
            f"The game has started. May the best win.\n"
            f"`{CURRENCY} ~{format_number_short(namount)}` is up for grabs on the table."
        )
        
        initial.add_field(
            name=f"{interaction.user.name} (Player)", 
            value=f"**Cards** - {' '.join(shallow_pv)}\n**Total** - `{player_sum}`")
        initial.add_field(
            name=f"{interaction.client.user.name} (Dealer)", 
            value=f"**Cards** - {shallow_dv[0]} `?`\n**Total** - ` ? `")
        
        initial.set_author(icon_url=interaction.user.display_avatar.url, name=f"{interaction.user.name}'s blackjack game")
        initial.set_footer(text="K, Q, J = 10  |  A = 1 or 11")
        bj_view = BlackjackUi(interaction, self.client)
        
        await interaction.response.send_message(
            content="What do you want to do?\nPress **Hit** to to request an additional card, **Stand** to finalize "
                    "your deck or **Forfeit** to end your hand prematurely, sacrificing half of your original bet.",
            embed=initial, view=bj_view)
        bj_view.message = await interaction.original_response()

    async def do_wallet_checks(
            self, 
            interaction: discord.Interaction,  
            wallet_amount: int, 
            exponent_amount : str | int,
            has_keycard: Optional[bool] = False
        ) -> int | None:
        """Reusable wallet checks that are common amongst most gambling commands."""

        expo = determine_exponent(exponent_amount)
        try:
            assert isinstance(expo, int)
            amount = expo
        except AssertionError:
            if exponent_amount.lower() in {'max', 'all'}:
                if has_keycard:
                    amount = min(MAX_BET_KEYCARD, wallet_amount)
                else:
                    amount = min(MAX_BET_WITHOUT, wallet_amount)
            else:
                return await interaction.response.send_message(
                    embed=membed("You need to provide a real amount to bet upon.")
                )

        if amount > wallet_amount:
            return await interaction.response.send_message(
                embed=membed("You are too poor for this bet.")
            )

        if has_keycard:

            if (amount < MIN_BET_KEYCARD) or (amount > MAX_BET_KEYCARD):
                return await interaction.response.send_message(
                    embed=membed(
                        f"You can't bet less than {CURRENCY} **{MIN_BET_KEYCARD:,}**.\n"
                        f"You also can't bet anything more than {CURRENCY} **{MAX_BET_KEYCARD:,}**."
                    )
                )
        else:
            if (amount < MIN_BET_WITHOUT) or (amount > MAX_BET_WITHOUT):
                return await interaction.response.send_message(
                    embed=membed(
                        f"You can't bet less than {CURRENCY} **{MIN_BET_WITHOUT:,}**.\n"
                        f"You also can't bet anything more than {CURRENCY} **{MAX_BET_WITHOUT:,}**.\n"
                        f"These values can increase when you acquire a <:lanyard:1165935243140796487> Keycard."
                    )
                )
            
        return amount

    @app_commands.command(name="bet", description="Bet your robux on a dice roll", extras={"exp_gained": 3})
    @app_commands.guilds(*APP_GUILDS_ID)
    @app_commands.checks.cooldown(1, 6)
    @app_commands.rename(exponent_amount='robux')
    @app_commands.describe(exponent_amount=ROBUX_DESCRIPTION)
    async def bet(self, interaction: discord.Interaction, exponent_amount: str):
        """Bet your robux on a gamble to win or lose robux."""

        # --------------- Contains checks before betting i.e. has keycard, meets bet constraints. -------------
        async with self.client.pool_connection.acquire() as conn:
            if await self.can_call_out(interaction.user, conn):
                return await interaction.response.send_message(embed=self.not_registered)
            conn: asqlite_Connection

            data = await conn.fetchone(
                f"SELECT pmulti, wallet, betw, betl FROM `{BANK_TABLE_NAME}` WHERE userID = $0", 
                interaction.user.id
            )

            pmulti, wallet_amt = data[0], data[1]
            has_keycard = await self.user_has_item_from_id(interaction.user.id, item_id=1, conn=conn)

            amount = await self.do_wallet_checks(
                interaction=interaction, 
                has_keycard=has_keycard,
                wallet_amount=wallet_amt,
                exponent_amount=exponent_amount
            )
            
            if amount is None:
                return
            
            # --------------------------------------------------------
            smulti = SERVER_MULTIPLIERS.get(interaction.guild.id, 0) + pmulti
            badges = set()
            id_won_amount, id_lose_amount = data[2], data[3]
            if pmulti:
                badges.add(PREMIUM_CURRENCY)

            if has_keycard:
                badges.add("<:lanyard:1165935243140796487>")
                
                your_choice = choices(
                    [1, 2, 3, 4, 5, 6], 
                    weights=[37 / 3, 37 / 3, 37 / 3, 63 / 3, 63 / 3, 63 / 3]
                )

                bot_choice = choices(
                    [1, 2, 3, 4, 5, 6], 
                    weights=[65 / 4, 65 / 4, 65 / 4, 65 / 4, 35 / 2, 35 / 2]
                )

            else:
                bot_choice = choices(
                    [1, 2, 3, 4, 5, 6], 
                    weights=[10, 10, 15, 27, 15, 23])
                
                your_choice = choices(
                    [1, 2, 3, 4, 5, 6], 
                    weights=[55 / 3, 55 / 3, 55 / 3, 45 / 3, 45 / 3, 45 / 3]
                )
            
            async with conn.transaction():
                if your_choice[0] > bot_choice[0]:

                    amount_after_multi = floor(((smulti / 100) * amount) + amount)
                    updated = await self.update_bank_three_new(
                        interaction.user, conn, "betwa", amount_after_multi,
                        "betw", 1, "wallet", amount_after_multi)

                    prcntw = (updated[1] / (id_lose_amount + updated[1])) * 100

                    embed = discord.Embed(
                        colour=discord.Color.brand_green(),
                        description=(
                            f"**You've rolled higher!** You won {CURRENCY} **{amount_after_multi:,}** robux.\n"
                            f"Your new `wallet` balance is {CURRENCY} **{updated[2]:,}**.\n"
                            f"You've won {prcntw:.1f}% of all games."
                        )
                    )
                    embed.set_author(name=f"{interaction.user.name}'s winning gambling game",
                                    icon_url=interaction.user.display_avatar.url)
                elif your_choice[0] == bot_choice[0]:
                    embed = discord.Embed(description="**Tie.** You lost nothing nor gained anything!",
                                        colour=discord.Color.yellow())
                    embed.set_author(name=f"{interaction.user.name}'s gambling game",
                                    icon_url=interaction.user.display_avatar.url)
                else:
                    updated = await self.update_bank_three_new(
                        interaction.user, conn, "betla", amount,
                        "betl", 1, "wallet", -amount)

                    new_total = id_won_amount + updated[1]
                    prcntl = (updated[1] / new_total) * 100

                    embed = discord.Embed(
                        colour=discord.Color.brand_red(),
                        description=(
                            f"**You've rolled lower!** You lost {CURRENCY} **{amount:,}**.\n"
                            f"Your new balance is {CURRENCY} **{updated[2]:,}**.\n"
                            f"You've lost {prcntl:.1f}% of all games."
                        )
                    )

                    embed.set_author(
                        name=f"{interaction.user.name}'s losing gambling game", 
                        icon_url=interaction.user.display_avatar.url
                    )

                embed.add_field(name=interaction.user.name, value=f"Rolled `{your_choice[0]}` {''.join(badges)}")
                embed.add_field(name=self.client.user.name, value=f"Rolled `{bot_choice[0]}`")
                await interaction.response.send_message(embed=embed)

    @play_blackjack.autocomplete('bet_amount')
    @bet.autocomplete('exponent_amount')
    @slots.autocomplete('amount')
    @highlow.autocomplete('robux')
    async def calback_max_50(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        """Autocomplete callback for when the maximum accepted bet value is 50 million."""

        chosen = {"all", "max", "15e6"}
        return [
            app_commands.Choice(name=str(the_chose), value=str(the_chose))
            for the_chose in chosen if current.lower() in the_chose
        ]

    @add_showcase_item.autocomplete('item_name')
    @remove_showcase_item.autocomplete('item_name')
    @sell.autocomplete('item_name')
    @use_item.autocomplete('item')
    @share_items.autocomplete('item_name')
    async def owned_items_lookup(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        
        async with self.client.pool_connection.acquire() as conn:
            options = await conn.fetchall(
                """
                SELECT shop.itemName, shop.emoji, inventory.qty
                FROM shop
                INNER JOIN inventory ON shop.itemID = inventory.itemID
                WHERE inventory.userID = $0
            """, interaction.user.id)

            return [app_commands.Choice(name=option[0], value=option[0]) for option in options if current.lower() in option[0].lower()]

    @view_servents.autocomplete('servant_name')
    async def servant_lookup(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        """Autocomplete callback for the servant menu."""

        async with interaction.client.pool_connection.acquire() as conn:
            options = await conn.fetchall("SELECT slay_name FROM slay")

            return [
                app_commands.Choice(name=option[0], value=option[0])
                for option in options if current.lower() in option[0].lower()]

    @item.autocomplete('item_name')
    async def item_lookup(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        async with interaction.client.pool_connection.acquire() as conn:
            res = await conn.fetchall("SELECT itemName FROM shop")
            return [app_commands.Choice(name=iterable[0], value=iterable[0]) for iterable in res if current.lower() in iterable[0].lower()]


async def setup(client: commands.Bot):
    """Setup function to initiate the cog."""
    await client.add_cog(Economy(client))
