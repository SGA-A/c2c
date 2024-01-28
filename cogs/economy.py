"""The virtual economy system of the bot."""
from other.utilities import parse_duration, datetime_to_string, string_to_datetime, labour_productivity_via
from asyncio import sleep, TimeoutError as asyncTE
from string import ascii_letters, digits
from shelve import open as open_shelve
from re import sub, search
from other.pagination import Pagination
from ImageCharts import ImageCharts
from discord.ext import commands
from math import floor, ceil
from random import randint, choices, choice, sample, shuffle
from pluralizer import Pluralizer
from discord import app_commands, SelectOption
from asqlite import Connection as asqlite_Connection
from typing import Optional, Literal, Any, Union, List

import discord
import datetime
import json


def membed(custom_description: str) -> discord.Embed:
    """Quickly create an embed with a custom description using the preset."""
    membedder = discord.Embed(colour=0x2B2D31,
                              description=custom_description)
    return membedder


def number_to_ordinal(n):
    """Convert 01 to 1st, 02 to 2nd etc."""
    if 10 <= n % 100 <= 20:
        suffix = 'th'
    else:
        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')

    return str(n) + suffix


"""ALL VARIABLES AND CONSTANTS FOR THE ECONOMY ENVIRONMENT"""

BANK_TABLE_NAME = 'bank'
SLAY_TABLE_NAME = "slay"
COOLDOWN_TABLE_NAME = "cooldowns"
APP_GUILDS_ID = [829053898333225010, 780397076273954886]
DOWN = True
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
    780397076273954886: 160,
    1144923657064419398: 6969}
INV_TABLE_NAME = "inventory"
ARROW = "<:arrowe:1180428600625877054>"
CURRENCY = '<:robux:1146394968882151434>'
PREMIUM_CURRENCY = '<:robuxpremium:1174417815327998012>'
ERR_UNREASON = membed('You are unqualified to use this command. Possible reasons include '
                      'insufficient balance and/or unreasonable input.')
DOWNM = membed('This command is currently outdated and will be made available at a later date.')
NOT_REGISTERED = membed('Could not find account associated with the user provided.')
active_sessions = dict()
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

SHOP_ITEMS = [
    {"name": "Keycard", "cost": 8269069420, "id": 1, "info": "Allows you to bypass certain restrictions, and you get "
                                                             "more returns from certain activities!",
     "url": "https://i.imgur.com/WZOWysT.png", "rarity": "**Common** <:common:1166316338571132928>",
     "emoji": "<:lanyard:1165935243140796487>"},

    {"name": "Trophy", "cost": 5085779847, "id": 2, "info": "Flex on your friends with this trophy! There are also "
                                                            "some hidden side effects..",
     "url": "https://i.imgur.com/32iEaMb.png", "rarity": "**Luxurious** <:luxurious:1166316420125163560>",
     "emoji": "<:tr1:1165936712468418591>"},

    {"name": "Dynamic_Item", "cost": 55556587196, "id": 3,
     "info": "An item that changes use often. Its transformative "
             "functions change to match the seasonality of the year.",
     "url": "https://i.imgur.com/WX9mbie.png", "rarity": "**Rare** <:rare:1166316365892825138>", "qn": "dynamic_item",
     "emoji": "<:dynamic:1197949814898446478>"},

    {"name": "Resistor", "cost": 18102892402, "id": 4,
     "info": "No one knows how this works because no one has ever purchased "
             "this item. May cause distress to certain individuals upon purchase.",
     "url": "https://i.imgur.com/ggO9QbL.png", "rarity": "**Luxurious** <:luxurious:1166316420125163560>",
     "emoji": "<:resistor:1165934607447887973>"},

    {"name": "Clan_License", "cost": 20876994182, "id": 5,
     "info": "Create your own clan. It costs a fortune, but with it brings a lot of "
             "privileges exclusive to clan members.",
     "url": "https://i.imgur.com/nPcMNk8.png", "rarity": "**Rare** <:rare:1166316365892825138>", "qn": "clan_license",
     "emoji": "<:clan_license:1165936231922806804>"},

    {"name": "Hyperion", "cost": 49510771984, "id": 6,
     "info": "The `passive` drone that actively helps in increasing the returns in almost everything.",
     "url": "https://i.imgur.com/bmNyob0.png", "rarity": "**Rare** <:rare:1166316365892825138>", "qn": "hyperion_drone",
     "emoji": "<:DroneHyperion:1171491601726574613>"},

    {"name": "Crisis", "cost": 765191412472, "id": 7,
     "info": "The `support` drone that can bring status effects into the game, wreaking havoc onto other users!",
     "url": "https://i.imgur.com/obOJwJm.png", "rarity": "**Rare** <:rare:1166316365892825138>", "qn": "crisis_drone",
     "emoji": "<:DroneCrisis:1171491564258852894>"},

    {"name": "Odd_Eye", "cost": 33206481258, "id": 8,
     "info": "An eye that may prove advantageous during certain events. It may even become a pet with time..",
     "url": "https://i.imgur.com/rErrYrH.gif", "rarity": "**Luxurious** <:luxurious:1166316420125163560>",
     "qn": "odd_eye", "emoji": "<a:eyeOdd:1166465357142298676>"},

    {"name": "Amulet", "cost": 159961918315, "id": 9,
     "info": "Found from a black market, it is said that it contains an extract found only from the ancient relics "
             "lost millions of years ago.",
     "url": "https://i.imgur.com/m8jRWk5.png", "rarity": "**Luxurious** <:luxurious:1166316420125163560>",
     "emoji": "<:amuletrccc:1196529299847643198>"},
]

NAME_TO_INDEX = {
    "Keycard": 0,
    "Trophy": 1,
    "Dynamic_Item": 2,
    "Resistor": 3,
    "Clan_License": 4,
    "Hyperion": 5,
    "Crisis": 6,
    "Odd_Eye": 7,
    "Amulet": 8}

with open('C:\\Users\\georg\\PycharmProjects\\c2c\\cogs\\times.json') as file_name_thi:
    times = json.load(file_name_thi)

with open('C:\\Users\\georg\\PycharmProjects\\c2c\\cogs\\claimed.json') as file_name_four:
    claims = json.load(file_name_four)


def save_times():
    """Save other extraneous data related to the bot in a JSON file."""
    with open('C:\\Users\\georg\\PycharmProjects\\c2c\\cogs\\times.json', 'w') as file_name_seven:
        json.dump(times, file_name_seven, indent=4)


def acknowledge_claim():
    """Acknowledge certain user interactions in a JSON file."""
    with open('C:\\Users\\georg\\PycharmProjects\\c2c\\cogs\\claimed.json', 'w') as file_name_nine:
        json.dump(claims, file_name_nine, indent=4)


def calculate_hand(hand):
    """Calculate the value of a hand in a blackjack game, accounting for possible aces."""

    aces = hand.count(11)
    total = sum(hand)

    while total > 21 and aces > 0:
        total -= 10
        aces -= 1

    return total


def make_plural(word, count):
    """Generate the plural form of a word based on the given count."""
    mp = Pluralizer()
    return mp.pluralize(word=word, count=count)


def plural_for_own(count: int) -> str:
    """Only use this pluralizer if the term is 'own'. Nothing else."""
    if count != 1:
        return "own"
    else:
        return "owns"


def return_rand_str():
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
    >>> return_rand_str()
    'kR3Gx9pYsZ'
    >>> return_rand_str()
    '2hL7NQv6IzE'
    """

    all_char = ascii_letters + digits
    password = "".join(choice(all_char) for _ in range(randint(10, 11)))
    return password


def format_number_short(number):
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


def owners_nolimit(interaction: discord.Interaction) -> Optional[app_commands.Cooldown]:
    """Any of the owners of the client bypass all cooldown restrictions (i.e. Splint + inter_geo)."""
    if interaction.user.id in {546086191414509599, 992152414566232139}:
        return None
    return app_commands.Cooldown(1, randint(6, 8))


def determine_exponent(rinput: str) -> str | int:
    """Finds out what the exponential value entered is equivalent to in numerical form.

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
        ten_exponent = int(after_e_str)
        actual_value = before_e * (10 ** ten_exponent)
    else:
        try:
            actual_value = int(rinput)
        except ValueError:
            return rinput

    return floor(abs(actual_value))


def generate_slot_combination():
    """A slot machine that generates and returns one row of slots."""
    slot = ['🔥', '😳', '🌟', '💔', '🖕', '🤡', '🍕', '🍆', '🍑']

    weights = [
        (800, 1000, 800, 100, 900, 800, 1000, 800, 800),
        (800, 1000, 800, 100, 900, 800, 1000, 800, 800),
        (800, 1000, 800, 100, 900, 800, 1000, 800, 800)]

    slot_combination = ''.join(choices(slot, weights=w, k=1)[0] for w in weights)
    return slot_combination


def generate_progress_bar(percentage):
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
    if percentage > 100:
        percentage = 100

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
    with open_shelve("C:\\Users\\georg\\PycharmProjects\\c2c\\db-shit\\profile_mods") as dbmr:
        return dbmr.setdefault(key, None)


def display_user_friendly_deck_format(deck: list, /):
    """Convert a deck view into a more user-friendly view of the deck."""
    remade = list()
    suits = ["\U00002665", "\U00002666", "\U00002663", "\U00002660"]
    ranks = {10: ["K", "Q", "J"], 1: "A"}
    chosen_suit = choice(suits)
    for number in deck:
        conversion_letter = ranks.setdefault(number, None)
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
    ranks = {10: ["K", "Q", "J"]}
    chosen_suit = choice(suits)
    conversion_letter = ranks.setdefault(number, None)
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
    with open_shelve("C:\\Users\\georg\\PycharmProjects\\c2c\\db-shit\\profile_mods") as dbm:
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


def get_stock(item: str) -> int:
    """Find out how much of an item is available."""
    with open_shelve("C:\\Users\\georg\\PycharmProjects\\c2c\\db-shit\\stock") as dbm:
        a = dbm.get(f"{item}")
        if a is None:
            a = 0
        return int(a)


def modify_stock(item: str, modify_type: Literal["+", "-"], amount: int) -> int:
    """Directly modify the amount of stocks available for an item, returns the new amount that is available."""
    with open_shelve("C:\\Users\\georg\\PycharmProjects\\c2c\\db-shit\\stock") as dbm:
        match modify_type:
            case "+":
                a = dbm.get(f"{item}")
                if a is None:
                    a = 0
                new_count = int(a) + amount
                dbm.update({f'{item}': new_count})
                dbm.close()
                return new_count
            case "-":
                a = dbm.get(f"{item}")
                if a is None:
                    a = 0
                new_count = int(a) - amount
                dbm.update({f'{item}': new_count})
                return new_count


class ConfirmDeny(discord.ui.View):
    def __init__(self, interaction: discord.Interaction, client: commands.Bot, member: discord.Member):
        self.interaction = interaction
        self.client: commands.Bot = client
        self.member = member
        self.timed_out: bool = True
        super().__init__(timeout=30)

    async def on_timeout(self) -> None:
        for item in self.children:
            item.disabled = True
        if self.timed_out:
            await self.msg.edit(embed=membed("Timed out waiting for a response.\n"  # type: ignore
                                             "The operation was cancelled."), view=None)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Make sure the original user that called the interaction is only in control, no one else."""
        if interaction.user == self.interaction.user:
            return True
        else:
            emb = membed(
                f"{self.interaction.user.mention} can only give consent to perform this action.")
            await interaction.response.send_message(embed=emb, ephemeral=True)  # type: ignore
            return False

    @discord.ui.button(label='Confirm', style=discord.ButtonStyle.gray)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Confirmation button."""

        self.timed_out = False
        for item in self.children:
            item.disabled = True

        tables_to_delete = [BANK_TABLE_NAME, INV_TABLE_NAME, COOLDOWN_TABLE_NAME, SLAY_TABLE_NAME]
        async with self.client.pool_connection.acquire() as conn:  # type: ignore
            conn: asqlite_Connection
            for table in tables_to_delete:
                await conn.execute(f"DELETE FROM `{table}` WHERE userID = ?", (self.member.id,))

            success = discord.Embed(title="Action Confirmed",
                                    description="You're now basically out of our database, "
                                                "we no longer have any EUD from you (end user data).",
                                    colour=discord.Colour.brand_green())

            await conn.commit()
            await interaction.message.edit(embed=success, view=None)

    @discord.ui.button(label='Deny', style=discord.ButtonStyle.gray)
    async def deny(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Deny button."""
        self.timed_out = False
        for item in self.children:
            item.disabled = True

        success = discord.Embed(title="Action Cancelled",
                                description="The operation has been cancelled.",
                                colour=discord.Colour.brand_red())

        await interaction.message.edit(embed=success, view=None)


class BlackjackUi(discord.ui.View):
    """View for the blackjack command and its associated functions."""

    def __init__(self, interaction: discord.Interaction, client: commands.Bot):
        self.interaction = interaction
        self.client: commands.Bot = client
        self.finished = False
        super().__init__(timeout=30)

    async def disable_all_items(self) -> None:
        """Disable all items within the blackjack interface."""
        for item in self.children:
            item.disabled = True

    async def on_timeout(self) -> None:
        await self.disable_all_items()
        if not self.finished:
            namount = self.client.games[self.interaction.user.id][-1]  # type: ignore
            namount = floor(((130 / 100) * namount))
            del self.client.games[self.interaction.user.id]  # type: ignore

            async with self.client.pool_connection.acquire() as conn:  # type: ignore
                conn: asqlite_Connection

                await Economy.update_bank_new(self.interaction.guild.me, conn, namount)
                new_amount_balance = await Economy.update_bank_new(self.interaction.user, conn, -namount)

            losse = discord.Embed(
                colour=0x2B2D31,
                description=f"## No response detected.\n"
                            f"- {self.interaction.user.mention} was fined \U000023e3 {namount:,} for unpunctuality.\n"
                            f" - The dealer received {self.interaction.user.display_name}'s bet in full.\n"
                            f" - An additional 30% tax was as included as part of a gambling duty.\n"
                            f"- {self.interaction.user.mention} now has \U000023e3 {new_amount_balance[0]:,}."
            )
            losse.set_author(name=f"{self.interaction.user.name}'s timed-out blackjack game",
                             icon_url=self.interaction.user.display_avatar.url)

            return await self.message.edit(  # type: ignore
                content=None, embed=losse, view=self)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user == self.interaction.user:
            return True
        else:
            emb = discord.Embed(
                description=f"This game is being held under {self.interaction.user.name}'s name. Not yours.",
                color=0x2F3136
            )
            await interaction.response.send_message(embed=emb, ephemeral=True)  # type: ignore
            return False

    @discord.ui.button(label='Hit', style=discord.ButtonStyle.blurple)
    async def hit_bj(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Button in the interface to hit within blackjack."""

        namount = self.client.games[interaction.user.id][-1]  # type: ignore
        deck = self.client.games[interaction.user.id][0]  # type: ignore
        player_hand = self.client.games[interaction.user.id][1]  # type: ignore

        player_hand.append(deck.pop())
        self.client.games[interaction.user.id][-2].append(  # type: ignore
            display_user_friendly_card_format(player_hand[-1]))
        player_sum = sum(player_hand)

        if player_sum > 21:

            await self.disable_all_items()
            self.finished = True
            dealer_hand = self.client.games[interaction.user.id][2]  # type: ignore
            d_fver_p = [num for num in self.client.games[interaction.user.id][-2]]  # type: ignore
            d_fver_d = [num for num in self.client.games[interaction.user.id][-3]]  # type: ignore
            del self.client.games[interaction.user.id]  # type: ignore
            async with self.client.pool_connection.acquire() as conn:  # type: ignore
                conn: asqlite_Connection

                await Economy.update_bank_new(interaction.user, conn, namount, "bjla")
                bj_win = await conn.execute('SELECT bjw FROM bank WHERE userID = ?', (interaction.user.id,))
                bj_win = await bj_win.fetchone()
                new_bj_lose = await Economy.update_bank_new(interaction.user, conn, 1, "bjl")
                new_total = new_bj_lose[0] + bj_win[0]
                prnctl = round((new_bj_lose[0] / new_total) * 100)

                new_amount_balance = await Economy.update_bank_new(interaction.user, conn, -namount)
                embed = discord.Embed(colour=discord.Colour.brand_red(),
                                      description=f"**You lost. You went over 21 and busted.**\n"
                                                  f"You lost {CURRENCY}**{namount:,}**. You now "
                                                  f"have {CURRENCY}**{new_amount_balance[0]:,}**\n"
                                                  f"You lost {prnctl}% of the games.")

                embed.add_field(name=f"{interaction.user.name} (Player)", value=f"**Cards** - {' '.join(d_fver_p)}\n"
                                                                                f"**Total** - `{player_sum}`")
                embed.add_field(name=f"{interaction.guild.me.name} (Dealer)",
                                value=f"**Cards** - {' '.join(d_fver_d)}\n"
                                      f"**Total** - `{sum(dealer_hand)}`")

                embed.set_author(name=f"{interaction.user.name}'s losing blackjack game",
                                 icon_url=interaction.user.display_avatar.url)
                await interaction.response.edit_message(content=None, embed=embed, view=None)  # type: ignore

        elif sum(player_hand) == 21:

            self.finished = True
            await self.disable_all_items()

            dealer_hand = self.client.games[interaction.user.id][2]  # type: ignore
            d_fver_p = [num for num in self.client.games[interaction.user.id][-2]]  # type: ignore
            d_fver_d = [num for num in self.client.games[interaction.user.id][-3]]  # type: ignore

            del self.client.games[interaction.user.id]  # type: ignore

            async with self.client.pool_connection.acquire() as conn:  # type: ignore
                conn: asqlite_Connection

                bj_lose = await conn.execute('SELECT bjl FROM bank WHERE userID = ?', (interaction.user.id,))
                bj_lose = await bj_lose.fetchone()
                new_bj_win = await Economy.update_bank_new(interaction.user, conn, 1, "bjw")
                new_total = new_bj_win[0] + bj_lose[0]
                prctnw = round((new_bj_win[0] / new_total) * 100)

                pmulti = await Economy.get_pmulti_data_only(interaction.user, conn)
                new_multi = SERVER_MULTIPLIERS.setdefault(interaction.guild.id, 0) + pmulti[0]
                amount_after_multi = floor(((new_multi / 100) * namount) + namount) + randint(1, 999)
                await Economy.update_bank_new(interaction.user, conn, amount_after_multi, "bjwa")
                new_amount_balance = await Economy.update_bank_new(interaction.user, conn, amount_after_multi)

                win = discord.Embed(colour=discord.Colour.brand_green(),
                                    description=f"**You win! You got to {player_sum}**.\n"
                                                f"You won {CURRENCY}**{amount_after_multi:,}**. "
                                                f"You now have {CURRENCY}**{new_amount_balance[0]:,}**.\n"
                                                f"You won {prctnw}% of the games.")

                win.add_field(name=f"{interaction.user.name} (Player)", value=f"**Cards** - {' '.join(d_fver_p)}\n"
                                                                              f"**Total** - `{player_sum}`")
                win.add_field(name=f"{interaction.guild.me.name} (Dealer)", value=f"**Cards** - {' '.join(d_fver_d)}\n"
                                                                                  f"**Total** - `{sum(dealer_hand)}`")
                win.set_author(name=f"{interaction.user.name}'s winning blackjack game",
                               icon_url=interaction.user.display_avatar.url)
                await interaction.response.edit_message(content=None, embed=win, view=None)  # type: ignore

        else:

            player_hand = self.client.games[interaction.user.id][1]  # type: ignore
            d_fver_p = [number for number in self.client.games[interaction.user.id][-2]]  # type: ignore
            necessary_show = self.client.games[interaction.user.id][-3][0]  # type: ignore
            ts = sum(player_hand)

            prg = discord.Embed(colour=0x2B2D31,
                                description=f"**Your move. Your hand is now {ts}**.")
            prg.add_field(name=f"{interaction.user.name} (Player)", value=f"**Cards** - {' '.join(d_fver_p)}\n"
                                                                          f"**Total** - `{ts}`")
            prg.add_field(name=f"{interaction.guild.me.name} (Dealer)", value=f"**Cards** - {necessary_show} `?`\n"
                                                                              f"**Total** - ` ? `")

            prg.set_footer(text="K, Q, J = 10  |  A = 1 or 11")
            prg.set_author(icon_url=interaction.user.display_avatar.url,
                           name=f"{interaction.user.name}'s blackjack game")
            await interaction.response.edit_message(  # type: ignore
                content="Press **Hit** to hit, **Stand** to finalize your deck or "
                        "**Forfeit** to end your hand prematurely.", embed=prg, view=self)

    @discord.ui.button(label='Stand', style=discord.ButtonStyle.blurple)
    async def stand_bj(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Button interface in blackjack to stand."""

        await self.disable_all_items()

        deck = self.client.games[interaction.user.id][0]  # type: ignore
        player_hand = self.client.games[interaction.user.id][1]  # type: ignore
        dealer_hand = self.client.games[interaction.user.id][2]  # type: ignore
        namount = self.client.games[interaction.user.id][-1]  # type: ignore

        dealer_total = calculate_hand(dealer_hand)

        while dealer_total < 17:
            popped = deck.pop()

            dealer_hand.append(popped)

            self.client.games[interaction.user.id][-3].append(display_user_friendly_card_format(popped))  # type: ignore

            dealer_total = calculate_hand(dealer_hand)

        player_sum = sum(player_hand)
        d_fver_p = self.client.games[interaction.user.id][-2]  # type: ignore
        d_fver_d = self.client.games[interaction.user.id][-3]  # type: ignore
        del self.client.games[interaction.user.id]  # type: ignore

        if dealer_total > 21:
            self.finished = True
            async with self.client.pool_connection.acquire() as conn:  # type: ignore
                conn: asqlite_Connection

                bj_lose = await conn.execute('SELECT bjl FROM bank WHERE userID = ?', (interaction.user.id,))
                bj_lose = await bj_lose.fetchone()
                new_bj_win = await Economy.update_bank_new(interaction.user, conn, 1, "bjw")
                new_total = new_bj_win[0] + bj_lose[0]
                prctnw = round((new_bj_win[0] / new_total) * 100)

                pmulti = await Economy.get_pmulti_data_only(interaction.user, conn)
                new_multi = SERVER_MULTIPLIERS.setdefault(interaction.guild.id, 0) + pmulti[0]
                amount_after_multi = floor(((new_multi / 100) * namount) + namount) + randint(1, 999)
                await Economy.update_bank_new(interaction.user, conn, amount_after_multi, "bjwa")
                new_amount_balance = await Economy.update_bank_new(interaction.user, conn, amount_after_multi)

            win = discord.Embed(colour=discord.Colour.brand_green(),
                                description=f"**You win! The dealer went over 21 and busted.**\n"
                                            f"You won {CURRENCY}**{amount_after_multi:,}**. "
                                            f"You now have {CURRENCY}**{new_amount_balance[0]:,}**.\n"
                                            f"You won {prctnw}% of the games.")

            win.add_field(name=f"{interaction.user.name} (Player)", value=f"**Cards** - {' '.join(d_fver_p)}\n"
                                                                          f"**Total** - `{player_sum}`")
            win.add_field(name=f"{interaction.guild.me.name} (Dealer)", value=f"**Cards** - {' '.join(d_fver_d)}\n"
                                                                              f"**Total** - `{dealer_total}`")

            win.set_author(icon_url=interaction.user.display_avatar.url,
                           name=f"{interaction.user.name}'s winning blackjack game")
            await interaction.response.edit_message(content=None, embed=win, view=None)  # type: ignore

        elif dealer_total > sum(player_hand):
            self.finished = True
            async with self.client.pool_connection.acquire() as conn:  # type: ignore
                conn: asqlite_Connection

                bj_win = await conn.execute('SELECT bjw FROM bank WHERE userID = ?', (interaction.user.id,))
                bj_win = await bj_win.fetchone()
                new_bj_lose = await Economy.update_bank_new(interaction.user, conn, 1, "bjl")
                new_total = new_bj_lose[0] + bj_win[0]
                prnctl = round((new_bj_lose[0] / new_total) * 100)
                await Economy.update_bank_new(interaction.user, conn, namount, "bjla")
                new_amount_balance = await Economy.update_bank_new(interaction.user, conn, -namount)

            loser = discord.Embed(colour=discord.Colour.brand_red(),
                                  description=f"**You lost. You stood with a lower score (`{player_sum}`) than "
                                              f"the dealer (`{dealer_total}`).**\n"
                                              f"You lost {CURRENCY}**{namount:,}**. You now "
                                              f"have {CURRENCY}**{new_amount_balance[0]:,}**.\n"
                                              f"You lost {prnctl}% of the games.")

            loser.add_field(name=f"{interaction.user.name} (Player)", value=f"**Cards** - {' '.join(d_fver_p)}\n"
                                                                            f"**Total** - `{player_sum}`")
            loser.add_field(name=f"{interaction.guild.me.name} (Dealer)", value=f"**Cards** - {' '.join(d_fver_d)}\n"
                                                                                f"**Total** - `{dealer_total}`")
            loser.set_author(icon_url=interaction.user.display_avatar.url,
                             name=f"{interaction.user.name}'s losing blackjack game")
            await interaction.response.edit_message(content=None, embed=loser, view=None)  # type: ignore

        elif dealer_total < sum(player_hand):
            self.finished = True
            async with self.client.pool_connection.acquire() as conn:  # type: ignore
                conn: asqlite_Connection

                bj_lose = await conn.execute('SELECT bjl FROM bank WHERE userID = ?', (interaction.user.id,))
                bj_lose = await bj_lose.fetchone()
                new_bj_win = await Economy.update_bank_new(interaction.user, conn, 1, "bjw")
                new_total = new_bj_win[0] + bj_lose[0]
                prctnw = round((new_bj_win[0] / new_total) * 100)

                pmulti = await Economy.get_pmulti_data_only(interaction.user, conn)
                new_multi = SERVER_MULTIPLIERS.setdefault(interaction.guild.id, 0) + pmulti[0]
                amount_after_multi = floor(((new_multi / 100) * namount) + namount) + randint(1, 999)
                new_amount_balance = await Economy.update_bank_new(interaction.user, conn, amount_after_multi)
                await Economy.update_bank_new(interaction.user, conn, amount_after_multi, "bjwa")

            win = discord.Embed(colour=discord.Colour.brand_green(),
                                description=f"**You win! You stood with a higher score (`{player_sum}`) than the "
                                            f"dealer (`{dealer_total}`).**\n"
                                            f"You won {CURRENCY}**{amount_after_multi:,}**. "
                                            f"You now have {CURRENCY}**{new_amount_balance[0]:,}**.\n"
                                            f"You won {prctnw}% of the games.")
            win.add_field(name=f"{interaction.user.name} (Player)", value=f"**Cards** - {' '.join(d_fver_p)}\n"
                                                                          f"**Total** - `{player_sum}`")
            win.add_field(name=f"{interaction.guild.me.name} (Dealer)", value=f"**Cards** - {' '.join(d_fver_d)}\n"
                                                                              f"**Total** - `{dealer_total}`")
            win.set_author(icon_url=interaction.user.display_avatar.url,
                           name=f"{interaction.user.name}'s winning blackjack game")
            await interaction.response.edit_message(content=None, embed=win, view=None)  # type: ignore
        else:
            self.finished = True
            async with self.client.pool_connection.acquire() as conn:  # type: ignore
                conn: asqlite_Connection
                wallet_amt = await Economy.get_wallet_data_only(interaction.user, conn)
            tie = discord.Embed(colour=discord.Colour.yellow(),
                                description=f"**Tie! You tied with the dealer.**\n"
                                            f"Your wallet hasn't changed! You have {CURRENCY}**{wallet_amt:,}** still.")
            tie.add_field(name=f"{interaction.user.name} (Player)", value=f"**Cards** - {' '.join(d_fver_p)}\n"
                                                                          f"**Total** - `{player_sum}`")
            tie.add_field(name=f"{interaction.guild.me.name} (Dealer)", value=f"**Cards** - {' '.join(d_fver_d)}\n"
                                                                              f"**Total** - `{dealer_total}`")
            tie.set_author(icon_url=interaction.user.display_avatar.url,
                           name=f"{interaction.user.name}'s blackjack game")
            await interaction.response.edit_message(content=None, embed=tie, view=None)  # type: ignore

    @discord.ui.button(label='Forfeit', style=discord.ButtonStyle.blurple)
    async def forfeit_bj(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Button for the blackjack interface to forfeit the current match."""

        self.finished = True
        await self.disable_all_items()
        namount = self.client.games[interaction.user.id][-1]  # type: ignore
        namount //= 2
        dealer_total = sum(self.client.games[interaction.user.id][2])  # type: ignore
        player_sum = sum(self.client.games[interaction.user.id][1])  # type: ignore
        d_fver_p = self.client.games[interaction.user.id][-2]  # type: ignore
        d_fver_d = self.client.games[interaction.user.id][-3]  # type: ignore

        del self.client.games[interaction.user.id]  # type: ignore

        async with self.client.pool_connection.acquire() as conn:  # type: ignore
            conn: asqlite_Connection

            bj_win = await conn.execute('SELECT bjw FROM bank WHERE userID = ?', (interaction.user.id,))
            bj_win = await bj_win.fetchone()
            new_bj_lose = await Economy.update_bank_new(interaction.user, conn, 1, "bjl")
            new_total = new_bj_lose[0] + bj_win[0]
            await Economy.update_bank_new(interaction.user, conn, namount, "bjla")
            await Economy.update_bank_new(self.interaction.guild.me, conn, namount)
            new_amount_balance = await Economy.update_bank_new(interaction.user, conn, -namount)

        loser = discord.Embed(colour=discord.Colour.brand_red(),
                              description=f"**You forfeit. The dealer took half of your bet for surrendering.**\n"
                                          f"You lost {CURRENCY}**{namount:,}**. You now "
                                          f"have {CURRENCY}**{new_amount_balance[0]:,}**.\n"
                                          f"You lost {round((new_bj_lose[0] / new_total) * 100)}% of the games.")

        loser.add_field(name=f"{interaction.user.name} (Player)", value=f"**Cards** - {' '.join(d_fver_p)}\n"
                                                                        f"**Total** - `{player_sum}`")
        loser.add_field(name=f"{interaction.guild.me.name} (Dealer)", value=f"**Cards** - {' '.join(d_fver_d)}\n"
                                                                            f"**Total** - `{dealer_total}`")
        loser.set_author(icon_url=interaction.user.display_avatar.url,
                         name=f"{interaction.user.name}'s losing blackjack game")

        await interaction.response.edit_message(content=None, embed=loser, view=None)  # type: ignore


class HighLow(discord.ui.View):
    """View for the Highlow command and its associated functions."""

    def __init__(self, interaction: discord.Interaction, client: commands.Bot, hint_provided: int, bet: int,
                 value: int):
        self.interaction = interaction
        self.client = client
        self.true_value = value
        self.hint_provided = hint_provided
        self.their_bet = bet
        super().__init__(timeout=30)

    async def make_clicked_blurple_only(self, clicked_button: discord.ui.Button):
        """Disable all buttons in the interaction menu except the clicked one, setting its style to blurple."""
        for item in self.children:
            item.disabled = True
            if item == clicked_button:
                clicked_button.style = discord.ButtonStyle.blurple
                continue
            item.style = discord.ButtonStyle.gray

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user == self.interaction.user:
            return True

        await interaction.response.send_message(  # type: ignore
            content=f"This is not your highlow game {interaction.user.display_name}! Make one yourself.",
            ephemeral=True, delete_after=5.5)
        return False

    @discord.ui.button(label='Lower', style=discord.ButtonStyle.blurple)
    async def low(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Button for highlow interface to allow users to guess lower."""
        async with self.client.pool_connection.acquire() as conn:  # type: ignore
            conn: asqlite_Connection

            if self.true_value < self.hint_provided:

                pmulti = await Economy.get_pmulti_data_only(interaction.user, conn)
                new_multi = SERVER_MULTIPLIERS.setdefault(interaction.guild.id, 0) + pmulti[0]
                total = floor((new_multi / 100) * self.their_bet)
                total += self.their_bet
                new_amount = await Economy.update_bank_new(interaction.user, conn, total)
                await self.make_clicked_blurple_only(button)

                win = discord.Embed(description=f'**You won \U000023e3 {total:,}!**\n'
                                                f'Your hint was **{self.hint_provided}**. '
                                                f'The hidden number was **{self.true_value}**.\n'
                                                f'Your new balance is \U000023e3 **{new_amount[0]:,}**.',
                                    colour=discord.Color.brand_green())
                win.set_author(name=f"{interaction.user.name}'s winning high-low game",
                               icon_url=interaction.user.display_avatar.url)
                await interaction.response.edit_message(embed=win, view=self)  # type: ignore
            else:
                new_amount = await Economy.update_bank_new(interaction.user, conn, -self.their_bet)
                await self.make_clicked_blurple_only(button)

                lose = discord.Embed(description=f'**You lost \U000023e3 {self.their_bet:,}!**\n'
                                                 f'Your hint was **{self.hint_provided}**. '
                                                 f'The hidden number was **{self.true_value}**.\n'
                                                 f'Your new balance is \U000023e3 **{new_amount[0]:,}**.',
                                     colour=discord.Color.brand_red())
                lose.set_author(name=f"{interaction.user.name}'s losing high-low game",
                                icon_url=interaction.user.display_avatar.url)
                await interaction.response.edit_message(embed=lose, view=self)  # type: ignore

    @discord.ui.button(label='JACKPOT!', style=discord.ButtonStyle.blurple)
    async def jackpot(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Button for highlow interface to guess jackpot, meaning the guessed number is the actual number."""

        async with self.client.pool_connection.acquire() as conn:  # type: ignore
            conn: asqlite_Connection

            if self.hint_provided == self.true_value:

                pmulti = await Economy.get_pmulti_data_only(interaction.user, conn)
                new_multi = SERVER_MULTIPLIERS.setdefault(interaction.guild.id, 0) + pmulti[0]
                total = floor((new_multi + 1000 / 100) * self.their_bet)
                total += self.their_bet
                new_balance = await Economy.update_bank_new(interaction.user, conn, total)
                await self.make_clicked_blurple_only(button)

                win = discord.Embed(description=f'**\U0001f929 You won \U000023e3 {total:,}! Jackpot! \U0001f929**\n'
                                                f'Your hint was **{self.hint_provided}**. '
                                                f'The hidden number was **{self.true_value}**\n'
                                                f'Your new balance is \U000023e3 **{new_balance[0]:,}**.',
                                    colour=discord.Color.brand_green())
                win.set_author(name=f"{interaction.user.name}'s winning high-low game",
                               icon_url=interaction.user.display_avatar.url)
                await interaction.response.edit_message(embed=win, view=self)  # type: ignore
            else:
                new_bal = await Economy.update_bank_new(interaction.user, conn, -self.their_bet)
                await self.make_clicked_blurple_only(button)

                lose = discord.Embed(description=f'**You lost \U000023e3 {self.their_bet:,}!**\n'
                                                 f'Your hint was **{self.hint_provided}**. '
                                                 f'The hidden number was **{self.true_value}**.\n'
                                                 f'Your new balance is \U000023e3 **{new_bal[0]:,}**.',
                                     colour=discord.Color.brand_red())
                lose.set_author(name=f"{interaction.user.name}'s losing high-low game",
                                icon_url=interaction.user.display_avatar.url)

                await interaction.response.edit_message(embed=lose, view=self)  # type: ignore

    @discord.ui.button(label='Higher', style=discord.ButtonStyle.blurple)
    async def high(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Button for highlow interface to allow users to guess higher."""

        async with self.client.pool_connection.acquire() as conn:  # type: ignore
            conn: asqlite_Connection

            if self.true_value > self.hint_provided:

                pmulti = await Economy.get_pmulti_data_only(interaction.user, conn)
                new_multi = SERVER_MULTIPLIERS.setdefault(interaction.guild.id, 0) + pmulti[0]
                total = floor((new_multi / 100) * self.their_bet)
                total += self.their_bet
                new_bal = await Economy.update_bank_new(interaction.user, conn, total)
                await self.make_clicked_blurple_only(button)

                win = discord.Embed(description=f'**You won \U000023e3 {total:,}!**\n'
                                                f'Your hint was **{self.hint_provided}**. '
                                                f'The hidden number was **{self.true_value}**.\n'
                                                f'Your new balance is \U000023e3 **{new_bal[0]:,}**.',
                                    colour=discord.Color.brand_green())
                win.set_author(name=f"{interaction.user.name}'s winning high-low game",
                               icon_url=interaction.user.display_avatar.url)
                await interaction.response.edit_message(embed=win, view=self)  # type: ignore
            else:
                new_bal = await Economy.update_bank_new(interaction.user, conn, -self.their_bet)
                await self.make_clicked_blurple_only(button)

                lose = discord.Embed(description=f'**You lost \U000023e3 {self.their_bet:,}!**\n'
                                                 f'Your hint was **{self.hint_provided}**. '
                                                 f'The hidden number was **{self.true_value}**.\n'
                                                 f'Your new balance is \U000023e3 **{new_bal[0]:,}**.',
                                     colour=discord.Color.brand_red())
                lose.set_author(name=f"{interaction.user.name}'s losing high-low game",
                                icon_url=interaction.user.display_avatar.url)
                await interaction.response.edit_message(embed=lose, view=self)  # type: ignore


class UpdateInfo(discord.ui.Modal, title='Update your Profile'):
    bio = discord.ui.TextInput(
        style=discord.TextStyle.paragraph,
        label='Bio',
        required=False,
        placeholder="Insert your bio here.. (type 'delete' to remove your existent bio)."
    )

    async def on_submit(self, interaction: discord.Interaction):

        if self.bio.value == "delete":
            res = modify_profile("delete", f"{interaction.user.id} bio", "placeholder")
            if not res:
                return await interaction.response.send_message(  # type: ignore
                    embed=membed("<:warning_nr:1195732155544911882> You don't have a bio yet. Add one first."))
            return await interaction.response.send_message(  # type: ignore
                embed=membed('## <:trim:1195732275283894292> Your bio has been removed.\n'
                             'The changes have taken effect immediately.'))

        phrases = "updated your" if get_profile_key_value(f"{interaction.user.id} bio") is not None else "created a new"
        modify_profile("update", f"{interaction.user.id} bio", self.bio.value)

        return await interaction.response.send_message(  # type: ignore
            embed=membed(
                f"## <:overwrite:1195729262729240666> Successfully {phrases} bio.\n"
                "It is now:\n"
                f"> {self.bio.value or 'Empty: It should be removed, no input was given.'}\n"
                "The changes have taken effect immediatley."))

    async def on_error(self, interaction: discord.Interaction, error):

        return await interaction.response.send_message(  # type: ignore
            embed=membed(f"Something went wrong.\n\n> {error.__cause__}"))


class DropdownLB(discord.ui.Select):
    def __init__(self, client: commands.Bot, their_choice: str):
        optionss = [
            SelectOption(label='Bank + Wallet', description='Sort by the sum of bank and wallet.'),
            SelectOption(label='Wallet', description='Sort by the wallet amount only.'),
            SelectOption(label='Bank', description='Sort by the bank amount only.'),
            SelectOption(label='Inventory Net', description='Sort by the net value of your inventory.'),
            SelectOption(label='Bounty', description="Sort by the sum paid for capturing a player."),
            SelectOption(label='Commands', description="Sort by total commands ran."),
            SelectOption(label='Level', description="Sort by player level.")
        ]

        for option in optionss:
            if option.value == their_choice:
                option.default = True

        super().__init__(options=optionss)
        self.client: commands.Bot = client

    async def callback(self, interaction: discord.Interaction):

        chosen_choice = self.values[0]

        for option in self.options:
            if option.value == chosen_choice:
                option.default = True
                continue
            option.default = False

        lb = await Economy.create_leaderboard_preset(Economy(self.client), chosen_choice=chosen_choice)

        await interaction.response.edit_message(content=None, embed=lb, view=self.view)  # type: ignore


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
            await self.message.edit(view=self)  # type: ignore
        except discord.NotFound:
            pass


class Economy(commands.Cog):

    def __init__(self, client: commands.Bot):
        self.client: commands.Bot = client

        self.not_registered = discord.Embed(description="## <:noacc:1183086855181324490> You are not registered.\n"
                                                        "You'll need to register first before you "
                                                        "can use this command.\n"
                                                        "### Already Registered?\n"
                                                        "Find out what could've happened by calling the command "
                                                        "[`>reasons`](https://www.google.com/).", colour=0x2F3136,
                                            timestamp=datetime.datetime.now(datetime.UTC))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        role = interaction.guild.get_role(1168204249096785980)
        if (role in interaction.user.roles) or (role is None):
            return True
        return False

    async def cog_check(self, ctx: commands.Context) -> bool:
        role = ctx.guild.get_role(1168204249096785980)
        if (role in ctx.author.roles) or (role is None):
            return True
        return False

    @staticmethod
    async def send_return_interaction_orginal_response(interaction: discord.Interaction):
        """Pass the interaction to the function, sends a response and returns it, allowing you to make edits.

        This is good for commands that have a lot of background processing or overhead, for commands that
        cannot neccesarily meet the 3 second limit threshold to respond.
        """

        await interaction.response.send_message(  # type: ignore
            content="Crunching the latest data just for you, give us a mo'..")
        return await interaction.original_response()

    @staticmethod
    def calculate_exp_for(*, level: int):
        """Calculate the experience points required for a given level."""
        return ceil((level / 0.9)**0.8)

    async def create_leaderboard_preset(self, chosen_choice: str):
        """A single reused function used to map the chosen leaderboard made by the user to the associated query."""
        async with self.client.pool_connection.acquire() as conn:  # type: ignore
            conn: asqlite_Connection = conn
            if chosen_choice == 'Bank + Wallet':

                data = await conn.execute(
                    f"""
                    SELECT `userID`, SUM(`wallet` + `bank`) as 
                    total_balance FROM `{BANK_TABLE_NAME}` GROUP BY `userID` ORDER BY total_balance DESC
                    """,
                    ())
                data = await data.fetchall()

                not_database = []
                index = 0

                for member in data:
                    member_name = await self.client.fetch_user(member[0])
                    their_badge = UNIQUE_BADGES.setdefault(member_name.id, "")
                    msg1 = f"**{index+1}.** {member_name.name} {their_badge} \U00003022 {CURRENCY}{member[1]:,}"
                    not_database.append(msg1)
                    index += 1

                msg = "\n".join(not_database)

                lb = discord.Embed(
                    title=f"Leaderboard: {chosen_choice}",
                    description=f"Displaying the top `{index}` users.\n\n"
                                f"{msg}",
                    color=0x2F3136,
                    timestamp=discord.utils.utcnow()
                )
                lb.set_footer(
                    text="Ranked globally",
                    icon_url=self.client.user.avatar.url)

                return lb
            elif chosen_choice == 'Wallet':

                data = await conn.execute(
                    f"""
                    SELECT `userID`, `wallet` as total_balance FROM `{BANK_TABLE_NAME}` 
                    GROUP BY `userID` ORDER BY total_balance DESC
                    """,
                    ())

                data = await data.fetchall()

                not_database = []
                index = 0

                for member in data:
                    member_name = await self.client.fetch_user(member[0])
                    their_badge = UNIQUE_BADGES.setdefault(member_name.id, "")
                    msg1 = f"**{index+1}.** {member_name.name} {their_badge} \U00003022 {CURRENCY}{member[1]:,}"
                    not_database.append(msg1)
                    index += 1

                msg = "\n".join(not_database)

                lb = discord.Embed(
                    title=f"Leaderboard: {chosen_choice}",
                    description=f"Displaying the top `{index}` users.\n\n"
                                f"{msg}",
                    color=0x2F3136,
                    timestamp=discord.utils.utcnow()
                )
                lb.set_footer(
                    text="Ranked globally",
                    icon_url=self.client.user.avatar.url)

                return lb
            elif chosen_choice == 'Bank':
                data = await conn.execute(
                    f"""
                    SELECT `userID`, `bank` as total_balance 
                    FROM `{BANK_TABLE_NAME}` GROUP BY `userID` ORDER BY total_balance DESC
                    """,
                    ())

                data = await data.fetchall()

                not_database = []
                index = 0

                for member in data:
                    member_name = await self.client.fetch_user(member[0])
                    their_badge = UNIQUE_BADGES.setdefault(member_name.id, "")
                    msg1 = f"**{index+1}.** {member_name.name} {their_badge} \U00003022 {CURRENCY}{member[1]:,}"
                    not_database.append(msg1)
                    index += 1

                msg = "\n".join(not_database)

                lb = discord.Embed(
                    title=f"Leaderboard: {chosen_choice}",
                    description=f"Displaying the top `{index}` users.\n\n"
                                f"{msg}",
                    color=0x2F3136,
                    timestamp=discord.utils.utcnow()
                )
                lb.set_footer(
                    text="Ranked globally",
                    icon_url=self.client.user.avatar.url)

                return lb
            elif chosen_choice == 'Inventory Net':

                item_costs = [item["cost"] for item in SHOP_ITEMS]
                total_net_sql = " + ".join([f"`{item['name']}` * ?" for item in SHOP_ITEMS])

                data = await conn.execute(
                    f"""
                    SELECT `userID`, 
                    SUM({total_net_sql}) as total_net 
                    FROM `{INV_TABLE_NAME}` GROUP BY `userID` ORDER BY total_net DESC
                    """,
                    tuple(item_costs)
                )

                data = await data.fetchall()

                not_database = []
                index = 0

                for member in data:
                    member_name = await self.client.fetch_user(member[0])
                    their_badge = UNIQUE_BADGES.setdefault(member_name.id, "")
                    msg1 = f"**{index+1}.** {member_name.name} {their_badge} \U00003022 {CURRENCY}{member[1]:,}"
                    not_database.append(msg1)
                    index += 1

                msg = "\n".join(not_database)

                lb = discord.Embed(
                    title=f"Leaderboard: {chosen_choice}",
                    description=f"Displaying the top `{index}` users.\n\n"
                                f"{msg}",
                    color=0x2F3136,
                    timestamp=discord.utils.utcnow()
                )
                lb.set_footer(
                    text="Ranked globally",
                    icon_url=self.client.user.avatar.url)
                return lb

            elif chosen_choice == 'Bounty':

                data = await conn.execute(
                    f"""
                    SELECT `userID`, `bounty` as total_bounty 
                    FROM `{BANK_TABLE_NAME}` 
                    GROUP BY `userID` 
                    HAVING total_bounty > 0
                    ORDER BY total_bounty DESC
                    """,
                    ())

                data = await data.fetchall()

                not_database = []
                index = 0

                for member in data:
                    member_name = await self.client.fetch_user(member[0])
                    their_badge = UNIQUE_BADGES.setdefault(member_name.id, "")
                    msg1 = f"**{index + 1}.** {member_name.name} {their_badge} \U00003022 {CURRENCY}{member[1]:,}"
                    not_database.append(msg1)
                    index += 1

                lb = discord.Embed(
                    title=f"Leaderboard: {chosen_choice}",
                    description=f"Displaying the top `{index}` users.\n"
                                f"Users without a bounty aren't displayed.\n\n"
                                f"{'\n'.join(not_database) or 'No data.'}",
                    color=0x2F3136,
                    timestamp=discord.utils.utcnow()
                )
                lb.set_footer(
                    text="Ranked globally",
                    icon_url=self.client.user.avatar.url)

                return lb

            elif chosen_choice == 'Commands':

                data = await conn.execute(
                    f"""
                    SELECT `userID`, `cmds_ran` as total_commands 
                    FROM `{BANK_TABLE_NAME}` 
                    GROUP BY `userID` 
                    HAVING cmds_ran > 0
                    ORDER BY total_commands DESC
                    """,
                    ())

                data = await data.fetchall()

                not_database = []
                index = 0

                for member in data:
                    member_name = await self.client.fetch_user(member[0])
                    their_badge = UNIQUE_BADGES.setdefault(member_name.id, "")
                    msg1 = f"**{index + 1}.** {member_name.name} {their_badge} \U00003022 `{member[1]:,}`"
                    not_database.append(msg1)
                    index += 1

                lb = discord.Embed(
                    title=f"Leaderboard: {chosen_choice}",
                    description=f"Displaying the top `{index}` users.\n\n"
                                f"{'\n'.join(not_database) or 'No data.'}",
                    color=0x2F3136,
                    timestamp=discord.utils.utcnow()
                )
                lb.set_footer(
                    text="Ranked globally",
                    icon_url=self.client.user.avatar.url)

                return lb

            data = await conn.execute(
                f"""
                SELECT `userID`, `level` as lvl 
                FROM `{BANK_TABLE_NAME}` 
                GROUP BY `userID` 
                HAVING lvl > 0
                ORDER BY lvl DESC
                """,
                ())

            data = await data.fetchall()

            not_database = []
            index = 0

            for member in data:
                member_name = await self.client.fetch_user(member[0])
                their_badge = UNIQUE_BADGES.setdefault(member_name.id, "")
                msg1 = f"**{index + 1}.** {member_name.name} {their_badge} \U00003022 `{member[1]:,}`"
                not_database.append(msg1)
                index += 1

            lb = discord.Embed(
                title=f"Leaderboard: {chosen_choice}",
                description=f"Displaying the top `{index}` users.\n\n"
                            f"{'\n'.join(not_database) or 'No data.'}",
                color=0x2F3136,
                timestamp=discord.utils.utcnow())

            lb.set_footer(
                text="Ranked globally",
                icon_url=self.client.user.avatar.url)

            return lb

    async def raise_pmulti_warning(self, interaction: discord.Interaction, their_pmulti: int | str):
        """Warn users if they have not set up a personal multiplier yet using a webhook."""
        if their_pmulti in {"0", 0}:
            hook_id = get_profile_key_value(f"{interaction.channel.id} webhook")
            if hook_id is None:
                async with self.client.session.get("https://i.imgur.com/3aMsyXI.jpg") as resp:  # type: ignore
                    avatar_data = await resp.read()
                hook = await interaction.channel.create_webhook(name='Notify', avatar=avatar_data)
                modify_profile("update", f"{interaction.channel.id} webhook", hook.id)
            else:
                hook = await self.client.fetch_webhook(hook_id)

            await hook.send(f"Hey {interaction.user.mention}! We noticed you have not set a personal "
                            f"multiplier. You should set one up now to increase your returns!")

    async def send_custom_text(self, interaction: discord.Interaction,
                               custom_text: str):
        """Send a custom text using the webhook provided."""
        hook_id = get_profile_key_value(f"{interaction.channel.id} webhook")
        if hook_id is None:
            async with self.client.session.get("https://i.imgur.com/3aMsyXI.jpg") as resp:  # type: ignore
                avatar_data = await resp.read()
            hook = await interaction.channel.create_webhook(name='Notify', avatar=avatar_data)
            modify_profile("update", f"{interaction.channel.id} webhook", hook.id)
        else:
            hook = await self.client.fetch_webhook(hook_id)

        await hook.send(embed=membed(custom_text))

    @staticmethod
    def calculate_hand(hand):
        """Calculate the value of a hand in a blackjack game, accounting for possible aces."""
        aces = hand.count(11)
        total = sum(hand)

        while total > 21 and aces > 0:
            total -= 10
            aces -= 1

        return total

    # ------------------ BANK FUNCS ------------------ #

    @staticmethod
    async def open_bank_new(user: discord.Member, conn_input: asqlite_Connection) -> None:
        """Register the user, if they don't exist. Only use in balance commands (reccommended.)"""
        ranumber = randint(500_000_000, 3_000_000_000)

        await conn_input.execute(
            f"INSERT INTO `{BANK_TABLE_NAME}`(userID, wallet, job) VALUES (?, ?, ?)",
            (user.id, ranumber, "None"))

        await conn_input.commit()

    @staticmethod
    async def can_call_out(user: discord.Member, conn_input: asqlite_Connection):
        """Check if the user is NOT in the database and therefore not registered (evaluates True if not in db).
        Example usage:
        if await self.can_call_out(interaction.user, conn):
            await interaction.response.send_message(embed=self.not_registered)

        This is what should be done all the time to check if a user IS NOT REGISTERED.
        """
        data = await conn_input.execute(f"SELECT EXISTS (SELECT 1 FROM `{BANK_TABLE_NAME}` WHERE userID = ?)",
                                        (user.id,))
        data = await data.fetchone()

        return not data[0]

    @staticmethod
    async def can_call_out_either(user1: discord.Member, user2: discord.Member, conn_input: asqlite_Connection):
        """Check if both users are in the database. (evaluates True if both users are in db.)
        Example usage:

        if not(await self.can_call_out_either(interaction.user, username, conn)):
            do something

        This is what should be done all the time to check if a user IS NOT REGISTERED."""
        data = await conn_input.execute(f"SELECT COUNT(*) FROM `{BANK_TABLE_NAME}` WHERE userID IN (?, ?)",
                                        (user1.id, user2.id))
        data = await data.fetchone()

        return data[0] == 2

    @staticmethod
    async def get_wallet_data_only(user: discord.Member, conn_input: asqlite_Connection) -> Optional[Any]:
        """Retrieves the wallet amount only from a registered user's bank data."""
        data = await conn_input.execute(f"SELECT wallet FROM `{BANK_TABLE_NAME}` WHERE userID = ?", (user.id,))
        data = await data.fetchone()
        return data[0]

    @staticmethod
    async def get_spec_bank_data(user: discord.Member, field_name: str, conn_input: asqlite_Connection) -> Any:
        """Retrieves a specific field name only from the bank table."""
        data = await conn_input.execute(f"SELECT {field_name} FROM `{BANK_TABLE_NAME}` WHERE userID = ?", (user.id,))
        data = await data.fetchone()
        return data[0]

    @staticmethod
    async def update_bank_new(user: discord.Member | discord.User, conn_input: asqlite_Connection,
                              amount: Union[float, int, str] = 0,
                              mode: str = "wallet") -> Optional[Any]:
        """Modifies a user's balance in a given mode: either wallet (default) or bank.
        It also returns the new balance in the given mode, if any (defaults to wallet).
        Note that conn_input is not the last parameter, it is the second parameter to be included."""

        data = await conn_input.execute(
            f"UPDATE `{BANK_TABLE_NAME}` SET `{mode}` = `{mode}` + ? WHERE userID = ? RETURNING `{mode}`",
            (amount, user.id))
        data = await data.fetchone()
        return data

    @staticmethod
    async def change_bank_new(user: discord.Member | discord.User, conn_input: asqlite_Connection,
                              amount: Union[float, int, str] = 0,
                              mode: str = "wallet") -> Optional[Any]:
        """Modifies a user's field values in any given mode.

        Unlike the other updating the bank method, this function directly changes the value to the parameter ``amount``.

        It also returns the new balance in the given mode, if any (defaults to wallet).

        Note that conn_input is not the last parameter, it is the second parameter to be included."""

        data = await conn_input.execute(
            f"UPDATE `{BANK_TABLE_NAME}` SET `{mode}` = ? WHERE userID = ? RETURNING `{mode}`",
            (amount, user.id))
        data = await data.fetchone()
        return data

    @staticmethod
    async def update_bank_multiple_new(user: discord.Member | discord.User, conn_input: asqlite_Connection,
                                       mode1: str, amount1: Union[float, int], mode2: str, amount2: Union[float, int],
                                       table_name: Optional[str] = "bank") -> Optional[Any]:
        """Modifies any two fields at once by their respective amounts. Returning the values of both fields.
        You are able to choose what table you wish to modify the contents of."""
        data = await conn_input.execute(
            f"UPDATE `{table_name}` SET `{mode1}` = `{mode1}` + ?, `{mode2}` = `{mode2}` + ? WHERE userID = ? "
            f"RETURNING `{mode1}`, `{mode2}`",
            (amount1, amount2, user.id))
        data = await data.fetchone()
        return data

    @staticmethod
    async def update_bank_three_new(user: discord.Member | discord.User, conn_input: asqlite_Connection,
                                    mode1: str, amount1: Union[float, int], mode2: str, amount2: Union[float, int],
                                    mode3: str, amount3: Union[float, int],
                                    table_name: Optional[str] = "bank") -> Optional[Any]:
        """Modifies any three fields at once by their respective amounts. Returning the values of both fields.
        You are able to choose what table you wish to modify the contents of."""
        data = await conn_input.execute(
            f"""UPDATE `{table_name}` 
            SET `{mode1}` = `{mode1}` + ?, `{mode2}` = `{mode2}` + ?, `{mode3}` = `{mode3}` + ? WHERE userID = ? 
            RETURNING `{mode1}`, `{mode2}`, `{mode3}`
            """,
            (amount1, amount2, amount3, user.id))
        await conn_input.commit()
        data = await data.fetchone()
        return data

    # ------------------ INVENTORY FUNCS ------------------ #

    @staticmethod
    async def open_inv_new(user: discord.Member, conn_input: asqlite_Connection) -> None:
        """Register a new user's inventory records into the db."""

        await conn_input.execute(f"INSERT INTO `{INV_TABLE_NAME}`(userID) VALUES(?)", (user.id,))

        for item in SHOP_ITEMS:
            await conn_input.execute(f"UPDATE `{INV_TABLE_NAME}` SET `{item["name"]}` = ? WHERE userID = ?",
                                     (0, user.id,))
        await conn_input.commit()

    @staticmethod
    async def get_one_inv_data_new(user: discord.Member, item: str, conn_input: asqlite_Connection) -> Optional[Any]:
        """Fetch inventory data from one specific item inputted."""
        users = await conn_input.execute(f"SELECT {item} FROM `{INV_TABLE_NAME}` WHERE userID = ?", (user.id,))
        users = await users.fetchone()
        return users[0]

    @staticmethod
    async def update_inv_new(user: discord.Member, amount: Union[float, int], mode: str,
                             conn_input: asqlite_Connection) -> Optional[Any]:
        """Modify a user's inventory."""
        data = await conn_input.execute(
            f"UPDATE `{INV_TABLE_NAME}` SET `{mode}` = `{mode}` + ? WHERE userID = ? RETURNING `{mode}`",
            (amount, user.id))
        await conn_input.commit()
        data = await data.fetchone()
        return data

    @staticmethod
    async def change_inv_new(user: discord.Member, amount: Union[float, int, None], mode: str,
                             conn_input: asqlite_Connection) -> Optional[Any]:
        """Change a specific attribute in the user's inventory data and return the updated value."""

        data = await conn_input.execute(
            f"UPDATE `{INV_TABLE_NAME}` SET `{mode}` = ? WHERE userID = ? RETURNING `{mode}`", (amount, user.id))
        await conn_input.commit()
        data = await data.fetchone()
        return data

    # ------------ JOB FUNCS ----------------

    @staticmethod
    async def get_job_data_only(user: discord.Member, conn_input: asqlite_Connection) -> str:
        """Retrieves the users current job. This is now always a string."""
        data = await conn_input.execute(f"SELECT job FROM `{BANK_TABLE_NAME}` WHERE userID = ?", (user.id,))
        data = await data.fetchone()
        return data[0]

    @staticmethod
    async def change_job_new(user: discord.Member, conn_input: asqlite_Connection, job_name: str) -> None:
        """Modifies a user's job, returning the new job after changes were made."""

        await conn_input.execute(
            f"UPDATE `{BANK_TABLE_NAME}` SET `job` = ? WHERE userID = ?",
            (job_name, user.id))
        await conn_input.commit()

    # ------------ cooldowns ----------------

    @staticmethod
    async def open_cooldowns(user: discord.Member, conn_input: asqlite_Connection):
        """Create a new row in the CD table, adding specified actions for a user in the cooldowns table."""
        cd_columns = ["slaywork", "casino"]
        await conn_input.execute(
            f"""INSERT INTO `{COOLDOWN_TABLE_NAME}`
            (userID, {', '.join(cd_columns)}) VALUES(?, {', '.join(['0'] * len(cd_columns))})
            """,
            (user.id,))
        await conn_input.commit()

    @staticmethod
    async def fetch_cooldown(conn_input: asqlite_Connection, *, user: discord.Member, cooldown_type: str):
        """Fetch a cooldown from the cooldowns table. Requires indexing."""
        data = await conn_input.execute(f"SELECT `{cooldown_type}` FROM `{'cooldowns'}` WHERE userID = ?", (user.id,))
        data = await data.fetchone()
        return data

    @staticmethod
    async def update_cooldown(conn_input: asqlite_Connection, *, user: discord.Member, cooldown_type: str, new_cd: str):
        """Update a user's cooldown. Requires accessing the return value via the index, so [0].

        Use this func to reset and create a cooldown."""

        data = await conn_input.execute(
            f"UPDATE `{'cooldowns'}` SET `{cooldown_type}` = ? WHERE userID = ? RETURNING `{cooldown_type}`",
            (new_cd, user.id))
        await conn_input.commit()
        data = await data.fetchone()
        return data

    # ------------ PMULTI FUNCS -------------

    @staticmethod
    async def get_pmulti_data_only(user: discord.Member, conn_input: asqlite_Connection) -> Optional[Any]:
        """Retrieves the pmulti amount only from a registered user's bank data."""
        data = await conn_input.execute(f"SELECT pmulti FROM `{BANK_TABLE_NAME}` WHERE userID = ?", (user.id,))
        data = await data.fetchone()
        return data

    @staticmethod
    async def change_pmulti_new(user: discord.Member, conn_input: asqlite_Connection, amount: Union[float, int] = 0,
                                mode: str = "pmulti") -> Optional[Any]:
        """Modifies a user's personal multiplier, returning the new multiplier after changes were made."""

        data = await conn_input.execute(
            f"UPDATE `{BANK_TABLE_NAME}` SET `{mode}` = ? WHERE userID = ? RETURNING `{mode}`",
            (amount, user.id))
        await conn_input.commit()
        data = await data.fetchone()
        return data

    # ------------------- slay ----------------

    @staticmethod
    async def open_slay(conn_input: asqlite_Connection, user: discord.Member, sn: str, gd: str, pd: float, happy: int,
                        stus: int):
        """
        Open a new slay entry for a user in the slay database table.

        Parameters:
        - conn_input (asqlite_Connection): The SQLite database connection.
        - user (discord.Member): The Discord member for whom a new slay entry is being created.
        - sn (str): The name of the slay.
        - gd (str): The gender of the slay.
        - pd (float): The productivity value associated with the slay.
        - happy (int): The happiness value associated with the slay.
        - stus (int): The status value associated with the slay.
        """

        await conn_input.execute(
            "INSERT INTO slay (slay_name, userID, gender, productivity, happiness, status) VALUES (?, ?, ?, ?, ?, ?)",
            (sn, user.id, gd, pd, happy, stus))
        await conn_input.commit()

    @staticmethod
    async def get_slays(conn_input: asqlite_Connection, user: discord.Member):
        """
        Retrieve all slay entries for a specific user from the slay database table.

        Parameters:
        - conn_input (asqlite_Connection): The SQLite database connection.
        - user (discord.Member): The Discord member for whom slay entries are being retrieved.

        Returns:
        List[Dict[str, Union[int, str, float]]]: A list of dictionaries containing slay information,
        or an empty list if no entries are found.

        Description:
        This static method retrieves all slay entries for a specific user from the slay database table.
        The result is a list of dictionaries, each representing a slay entry with associated information such as
        slay_name, userID, gender, productivity, happiness, and status.
        If no entries are found, an empty list is returned.

        Example:
        slay_entries = await get_slays(conn, user)
        print(slay_entries)
        [{'slay_name': 'Slay1', 'userID': 123456789, 'gender': 'Male',
        'productivity': 0.8, 'happiness': 70, 'status': 1},
         {'slay_name': 'Slay2', 'userID': 123456789, 'gender': 'Female',
          'productivity': 0.9, 'happiness': 80, 'status': 2}]
        """

        new_data = await conn_input.execute("SELECT * FROM slay WHERE userID = ?", (user.id,))
        new_data = await new_data.fetchall()

        return new_data

    @staticmethod
    async def change_slay_field(conn_input: asqlite_Connection, user: discord.Member, field: str, new_val: Any):
        """
        Change a specific field in a user's slay entry and commit the changes to the slay database.

        Parameters:
        - conn_input (asqlite_Connection): The SQLite database connection.
        - user (discord.Member): The Discord member whose slay entry is being modified.
        - field (str): The field to be modified (e.g., 'slay_name', 'gender', 'productivity').
        - new_val (Any): The new value to be set for the specified field.

        Returns:
        None

        Description:
        This static method is used to change a specific field in a user's slay entry and commit the changes
        to the slay database. The 'field' parameter specifies the field to be modified, and 'new_val' is the new value
        to be set for that field.

        Example:
        await change_slay_field(conn, user, 'happiness', 90)
        """

        await conn_input.execute(f"UPDATE `{SLAY_TABLE_NAME}` SET `{field}` = ? WHERE userID = ?", (new_val, user.id,))
        await conn_input.commit()

    @staticmethod
    async def delete_slay(conn_input: asqlite_Connection, user: discord.Member, slay_name):
        """Remove a single slay row from the db and return 1 if the row existed, 0 otherwise."""

        await conn_input.execute("DELETE FROM slay WHERE userID = ? AND slay_name = ?", (user.id, slay_name))
        await conn_input.commit()

    @staticmethod
    async def count_happiness_above_threshold(conn_input: asqlite_Connection, user: discord.Member):
        """Count the number of rows for a given user ID where happiness is greater than 30."""

        rows = await conn_input.fetchall("SELECT happiness FROM slay WHERE userID = ?", user.id)

        count = 0

        for row in rows:
            if row["happiness"] > 30:
                count += 1

        return count

    @staticmethod
    async def modify_happiness(conn_input: asqlite_Connection, slaves_for_user: discord.Member):
        """Modify every row's happiness field for a given user ID with a different random number."""

        rows = await conn_input.fetchall("SELECT * FROM slay WHERE userID = ?", slaves_for_user.id)

        for _ in rows:
            await conn_input.execute("UPDATE slay SET happiness = ? WHERE userID = ?",
                                     (randint(20, 40), slaves_for_user.id))

        await conn_input.commit()

    # -----------------------------------------

    @commands.Cog.listener()
    async def on_app_command_completion(self, interaction: discord.Interaction,
                                        command: Union[app_commands.Command, app_commands.ContextMenu]):
        """
        Increment the total command ran by a user by 1 for each call. Increase the interaction user's invoker if
        they are registered.
        """
        async with self.client.pool_connection.acquire() as connection:  # type: ignore
            connection: asqlite_Connection

            if await self.can_call_out(interaction.user, connection):
                return

            async with connection.transaction():
                await connection.execute(
                    f"UPDATE `{BANK_TABLE_NAME}` SET `cmds_ran` = `cmds_ran` + ? WHERE userID = ?",
                    (1, interaction.user.id))

                exp_gainable = command.extras.setdefault("exp_gained", None)

                if not exp_gainable:
                    return

                record = await connection.fetchone(
                    'INSERT INTO `bank` (userID, exp, level) VALUES (?, 1, 1) '
                    'ON CONFLICT (userID) DO UPDATE SET exp = exp + ? RETURNING exp, level',
                    (interaction.user.id, exp_gainable))

                if record:
                    xp, level = record
                    exp_needed = self.calculate_exp_for(level=level)

                    if xp >= exp_needed:
                        await connection.execute(
                            """UPDATE `bank` SET level = level + 1, exp = 0, 
                            bankspace = bankspace + ? WHERE userID = ?""",
                            (randint(300_000, 20_000_000), interaction.user.id))

                        await self.send_custom_text(interaction,
                                                    custom_text=f'{interaction.user.mention} has just leveled '
                                                                f'up to Level **{level+1}**.')

    # ----------- END OF ECONOMY FUNCS, HERE ON IS JUST COMMANDS --------------

    pmulti = app_commands.Group(name='multi', description='No description.',
                                guild_only=True, guild_ids=APP_GUILDS_ID)

    @pmulti.command(name='view', description='check personal and global multipliers.')
    @app_commands.describe(user_name="whose multipliers to view")
    @app_commands.rename(user_name='user')
    @app_commands.checks.cooldown(1, 6)
    async def my_multi(self, interaction: discord.Interaction, user_name: Optional[discord.Member]):
        """View a user's personal multiplier and global multipliers linked with the server invocation."""

        async with self.client.pool_connection.acquire() as conn:  # type: ignore
            conn: asqlite_Connection

            if user_name is None:
                user_name = interaction.user

            if await Economy.can_call_out(user_name, conn):
                return await interaction.response.send_message(embed=NOT_REGISTERED)  # type: ignore
            their_multi = await Economy.get_pmulti_data_only(user_name, conn)

            if their_multi[0] == 0 and (user_name.id == interaction.user.id):
                rand = randint(30, 90)
                await Economy.change_pmulti_new(user_name, conn, rand)
                multi_own = discord.Embed(colour=0x2F3136,
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
                multi_own = discord.Embed(colour=0x2F3136, description="No multipliers found for this user.")
                multi_own.set_author(name=f'Viewing {user_name.name}\'s multipliers',
                                     icon_url=user_name.display_avatar.url)
            else:
                server_bs = SERVER_MULTIPLIERS.setdefault(interaction.guild.id, 0)
                multi_own = discord.Embed(colour=0x2F3136,
                                          description=f'> **The way multipliers work is being changed soon.** It will '
                                                      f'no longer be fixed and will offer more flexibility. See [#35]('
                                                      f'https://github.com/SGA-A/c2c/issues/35) for the details.\n\n'
                                                      f'Personal multiplier: **{their_multi[0]:,}**%\n'
                                                      f'*A multiplier that is unique to a user and is usually a fixed '
                                                      f'amount.*\n\n'
                                                      f'Global multiplier: **{server_bs:,}**%\n'
                                                      f'*A multiplier that changes based on the server you are calling'
                                                      f' commands in.*')
                multi_own.set_author(name=f'Viewing {user_name.name}\'s multipliers',
                                     icon_url=user_name.display_avatar.url)

            await interaction.response.send_message(embed=multi_own)  # type: ignore

    share = app_commands.Group(name='share', description='share different assets with others.',
                               guild_only=True, guild_ids=APP_GUILDS_ID)

    @share.command(name="robux", description="share robux with another user.", extras={"exp_gained": 5})
    @app_commands.describe(other='the user to give robux to',
                           amount='the amount of robux to give them. Supports Shortcuts (max, all, exponents).')
    @app_commands.rename(other='user')
    @app_commands.checks.cooldown(1, 6)
    async def give_robux(self, interaction: discord.Interaction, other: discord.Member, amount: str):
        """"Give an amount of robux to another user."""

        inter_user = interaction.user

        async with self.client.pool_connection.acquire() as conn:  # type: ignore
            conn: asqlite_Connection

            if not (await self.can_call_out_either(inter_user, other, conn)):
                return await interaction.response.send_message(embed=NOT_REGISTERED)  # type: ignore
            else:
                real_amount = determine_exponent(amount)
                wallet_amt_host = await Economy.get_wallet_data_only(inter_user, conn)

                if isinstance(real_amount, str):
                    if real_amount.lower() == 'all' or real_amount.lower() == 'max':
                        real_amount = wallet_amt_host
                    else:
                        return await interaction.response.send_message(embed=ERR_UNREASON)  # type: ignore
                    host_amt = await self.update_bank_new(inter_user, conn, -int(real_amount))
                    recp_amt = await self.update_bank_new(other, conn, int(real_amount))
                else:
                    if real_amount == 0:
                        return await interaction.response.send_message(embed=ERR_UNREASON)  # type: ignore
                    elif real_amount > wallet_amt_host:
                        return await interaction.response.send_message(embed=ERR_UNREASON)  # type: ignore
                    else:
                        host_amt = await self.update_bank_new(inter_user, conn, -int(real_amount))
                        recp_amt = await self.update_bank_new(other, conn, int(real_amount))

                embed = discord.Embed(
                    title='Transaction Complete',
                    description=f'- {inter_user.mention} has given {other.mention} \U000023e3 {real_amount:,}\n'
                                f'- {inter_user.mention} now has \U000023e3 {host_amt[0]:,} in their wallet.\n'
                                f'- {other.mention} now has \U000023e3 {recp_amt[0]:,} in their wallet.',
                    colour=0x2F3136)
                embed.set_thumbnail(url="https://i.imgur.com/RxQuE8T.png")
                embed.set_author(name=f'Transaction made by {inter_user.name}',
                                 icon_url=inter_user.display_avatar.url)
                return await interaction.response.send_message(embed=embed)  # type: ignore

    @share.command(name='items', description='share items with another user.', extras={"exp_gained": 5})
    @app_commands.describe(item_name='the name of the item you want to share.',
                           amount='the amount of this item to share', username='the name of the user to share it with')
    @app_commands.checks.cooldown(1, 5)
    async def give_items(self, interaction: discord.Interaction,
                         item_name: Literal[
                             'Keycard', 'Trophy', 'Clan License', 'Resistor', 'Amulet',
                             'Dynamic Item', 'Hyperion', 'Crisis', 'Odd Eye'],
                         amount: Literal[1, 2, 3, 4, 5], username: discord.Member):
        """Give an amount of items to another user."""

        primm = interaction.user

        async with self.client.pool_connection.acquire() as conn:  # type: ignore
            conn: asqlite_Connection
            item_name = item_name.replace(" ", "_")
            if not (await self.can_call_out_either(primm, username, conn)):
                embed = discord.Embed(description=f'Either you or {username.name} does not have an account.\n'
                                                  f'</balance:1179817617435926686> to register.',
                                      colour=0x2F3136)
                return await interaction.response.send_message(embed=embed)  # type: ignore
            else:
                quantity = await self.update_inv_new(primm, 0, item_name, conn)
                if amount > quantity[0]:
                    return await interaction.response.send_message(embed=ERR_UNREASON)  # type: ignore
                else:
                    receiver = await self.update_inv_new(username, +amount, item_name, conn)
                    new_after_transaction = quantity[0] - amount
                    sender = await self.change_inv_new(primm, new_after_transaction, item_name, conn)
                    item_name = " ".join(item_name.split("_"))
                    transaction_success = discord.Embed(
                        title="Transaction Complete",
                        description=f'- {primm.mention} has given **{amount}** {make_plural(item_name, amount)}\n'
                                    f'- {primm.mention} now has **{sender[0]}** {make_plural(item_name, sender[0])}\n'
                                    f'- {username.mention} now '
                                    f'has **{receiver[0]}** {make_plural(item_name, receiver[0])}',
                        colour=0x2B2D31)
                    transaction_success.set_thumbnail(url="https://i.imgur.com/xRJ2hpF.png")
                    transaction_success.set_author(name=f'Transaction made by {primm.name}',
                                                   icon_url=primm.display_avatar.url)

                    await interaction.response.send_message(embed=transaction_success)  # type: ignore

    showcase = app_commands.Group(name="showcase", description="manage your showcased items.", guild_only=True,
                                  guild_ids=APP_GUILDS_ID)

    @showcase.command(name="view", description="view your item showcase.")
    @app_commands.checks.cooldown(1, 5)
    async def view_showcase(self, interaction: discord.Interaction):
        """View your current showcase. This is not representative of what it look like on the profile."""

        async with self.client.pool_connection.acquire() as conn:  # type: ignore
            conn: asqlite_Connection

            if await self.can_call_out(interaction.user, conn):
                return await interaction.response.send_message(embed=self.not_registered)  # type: ignore

            showbed = discord.Embed(
                colour=0x2B2D31,
                description="These items will show on your profile.\n\n"
            )
            showbed.set_author(
                name=f"{interaction.user.name}'s Showcase",
                icon_url=interaction.user.display_avatar.url
            )

            showcase: str = await self.get_spec_bank_data(interaction.user, "showcase", conn)
            showcase: list = showcase.split(" ")

            nshowcase = []

            should_warn_user = False
            for i in range(1, 4):
                try:
                    item = showcase[i - 1]

                    if item == "0":
                        should_warn_user = True
                        nshowcase.append(f"`{i}`. Empty slot")
                        continue

                    qty = await self.get_one_inv_data_new(interaction.user, item, conn)
                    if qty >= 1:
                        nshowcase.append(f"`{i}`. {' '.join(item.split("_"))}")
                        continue
                    nshowcase.append(f"[**`{i}`**](https://www.google.com). **Requires replacement.**")
                except IndexError:
                    nshowcase.append(f"`{i}`. Empty slot")

            showbed.description += "\n".join(nshowcase)
            if should_warn_user:
                showbed.set_footer(text="You can add more items to your showcase.")

            await interaction.response.send_message(embed=showbed)  # type: ignore

    @showcase.command(name="add", description="add an item to your showcase.", extras={"exp_gained": 1})
    @app_commands.checks.cooldown(1, 10)
    @app_commands.describe(item_name="the item you want to add to your showcase",
                           position="the position within your showcase you want it to be in")
    async def add_showcase_item(self, interaction: discord.Interaction,
                                position: int,
                                item_name: Literal[
                                    'Keycard', 'Trophy', 'Clan License', 'Resistor', 'Amulet',
                                    'Dynamic Item', 'Hyperion', 'Crisis', 'Odd Eye']):
        """This is a subcommand. Adds an item to your showcase."""

        async with self.client.pool_connection.acquire() as conn:  # type: ignore
            conn: asqlite_Connection

            if await self.can_call_out(interaction.user, conn):
                return await interaction.response.send_message(embed=self.not_registered)  # type: ignore

            item_name = "_".join(item_name.split(' '))
            item_qty = await self.get_one_inv_data_new(interaction.user, item_name, conn)

            showcase: str = await self.get_spec_bank_data(interaction.user, "showcase", conn)
            showcase: list = showcase.split(" ")

            if 1 <= position <= 3:

                if len(showcase) > 3 and (showcase.count("0") == 0):
                    return await interaction.response.send_message(  # type: ignore
                        embed=membed("You already have the maximum of 3 showcase slots."))

                if item_qty == 0:
                    return await interaction.response.send_message(  # type: ignore
                        embed=membed("You cannot flex on someone with something you don't even have."))

                if item_name in showcase:
                    item_index = showcase.index(item_name)
                    if item_index == position - 1:
                        return await interaction.response.send_message(  # type: ignore
                            embed=membed("You already have this item in this slot."))

                    showcase[item_index] = "0"
                    await interaction.channel.send(
                        embed=membed("**Warning:** You already had this item in your showcase.\n"
                                     "I have removed it from it's previous location.\n"
                                     "Your preview may not be accurate as a result."))

                if showcase[position - 1] != "0":
                    await interaction.channel.send(
                        embed=membed("**Warning:** Another item was already in the specified position.\n"
                                     "Under your request, it has been replaced with a new item."))

                showcase[position - 1] = item_name
                showcase_shadow = " ".join(showcase)
                showcase_view = await self.change_bank_new(interaction.user, conn, showcase_shadow, "showcase")

                success = discord.Embed(title="Changes to showcase",
                                        description="Okay, that item was **added** into your showcase.\n"
                                                    "Here is a quick preview:```py\n"
                                                    f"{showcase_view[0].split(' ')}```\n"
                                                    f"`0` is used here to indicate that slot position is empty.\n"
                                                    f"This is not what it will look like on your profile!",
                                        colour=discord.Colour.brand_green())
                success.set_footer(text="What a flex.")

                return await interaction.response.send_message(embed=success)  # type: ignore

            await interaction.response.send_message(  # type: ignore
                embed=membed("Invalid position.\n"
                             "There are only 3 slots available.\n"
                             "It must be one of the following: `1`, `2` or `3`.")
            )

    @showcase.command(name="remove", description="remove an item from your showcase.", extras={"exp_gained": 1})
    @app_commands.checks.cooldown(1, 10)
    @app_commands.describe(item_name="the item you want to remove from your showcase")
    async def remove_showcase_item(self, interaction: discord.Interaction,
                                   item_name: Literal[
                                       'Keycard', 'Trophy', 'Clan License', 'Resistor', 'Amulet',
                                       'Dynamic Item', 'Hyperion', 'Crisis', 'Odd Eye']):
        """This is a subcommand. Removes an existing item from your showcase."""

        async with self.client.pool_connection.acquire() as conn:  # type: ignore
            conn: asqlite_Connection

            if await self.can_call_out(interaction.user, conn):
                return await interaction.response.send_message(embed=self.not_registered)  # type: ignore

            item_name = "_".join(item_name.split(' '))

            showcase: str = await self.get_spec_bank_data(interaction.user, "showcase", conn)
            showcase: list = showcase.split(" ")

            for item in showcase:
                if item == "0":
                    continue
                if item == item_name:
                    item_index = showcase.index(item)
                    showcase[item_index] = "0"
                    showcase_shadow = " ".join(showcase)
                    showcase_view = await self.change_bank_new(interaction.user, conn, showcase_shadow, "showcase")

                    success = discord.Embed(title="Changes to showcase",
                                            description="Okay, that item was **deleted** from your showcase.\n"
                                                        "Here is a quick preview:```py\n"
                                                        f"- {showcase_view[0].split(' ')}```\n"
                                                        f"`0` is used here to indicate that slot position is empty.\n"
                                                        f"This is not what it will look like on your profile!",
                                            colour=discord.Colour.brand_red())

                    success.set_footer(text="How humble of you.")
                    return await interaction.response.send_message(embed=success)  # type: ignore

            await interaction.response.send_message(  # type: ignore
                embed=membed("Could not find that item in your showcase. Sorry."))

    shop = app_commands.Group(name='shop', description='view items available for purchase.', guild_only=True,
                              guild_ids=APP_GUILDS_ID)

    @shop.command(name='view', description='view all shop items.')
    @app_commands.checks.cooldown(1, 6)
    async def view_the_shop(self, interaction: discord.Interaction):
        """This is a subcommand. View the currently available items within the shop."""

        async with self.client.pool_connection.acquire() as conn:  # type: ignore
            conn: asqlite_Connection

            if await self.can_call_out(interaction.user, conn):
                return await interaction.response.send_message(embed=self.not_registered)  # type: ignore

            additional_notes = list()

            for item in SHOP_ITEMS:
                name = " ".join(item["name"].split("_"))

                additional_notes.append(
                    f"{item['emoji']} __{name}__ \U00002014 "
                    f"[\U000023e3 **{item['cost']:,}**](https://youtu.be/dQw4w9WgXcQ)\n"
                    f"{ARROW}{item["info"]}\n"
                    f"{ARROW}ID: `{item['id']}`\n"
                    f"{ARROW}Quantity Remaining: `{get_stock(name)}`")

            async def get_page_part(page: int):
                """Helper function to determine what page of the paginator we're on."""
                emb = discord.Embed(
                    title="Shop",
                    color=0x2B2D31,
                    description=""
                )
                offset = (page - 1) * 5
                length = 3

                for item_mod in additional_notes[offset:offset + length]:
                    emb.description += f"{item_mod}\n\n"
                n = Pagination.compute_total_pages(len(additional_notes), length)
                emb.set_footer(text=f"This is page {page} of {n}")
                return emb, n

            await Pagination(interaction, get_page_part).navigate()


    @shop.command(name='lookup', description='get info about a particular item.')
    @app_commands.describe(item_name='the name of the item you want to sell.')
    async def lookup_item(self, interaction: discord.Interaction,
                          item_name: Literal[
                              'Keycard', 'Trophy', 'Clan License', 'Resistor', 'Amulet',
                              'Dynamic Item', 'Hyperion', 'Crisis', 'Odd Eye']):
        """This is a subcommand. Look up a particular item within the shop to get more information about it."""

        item_stock = get_stock(item_name)
        match item_stock:
            case 0:
                stock_resp = "The item is currently out of stock."
            case 1 | 2 | 3:
                stock_resp = f"There are shortage in stocks, only **{item_stock}** remain."
            case _:
                stock_resp = f"The item is in stock (**{item_stock}** available)."

        match item_name:
            case 'Keycard':
                clr = discord.Colour.from_rgb(80, 85, 252)
            case 'Trophy':
                clr = discord.Colour.from_rgb(254, 204, 78)
            case 'Clan License':
                clr = discord.Colour.from_rgb(209, 30, 54)
            case 'Resistor':
                clr = discord.Colour.from_rgb(78, 0, 237)
            case 'Dynamic Item':
                clr = discord.Colour.from_rgb(233, 0, 15)
            case _:
                clr = discord.Colour.from_rgb(54, 123, 112)

        for item in SHOP_ITEMS:
            stored = item["name"]
            name_beta = stored.split("_")
            name = " ".join(name_beta)
            cost = item["cost"]

            if name == item_name:
                async with self.client.pool_connection.acquire() as conn:  # type: ignore
                    conn: asqlite_Connection
                    data = await conn.execute(f"SELECT COUNT(*) FROM inventory WHERE {stored} > 0")
                    data = await data.fetchone()
                    owned_by_how_many = data[0]
                    their_count = await self.get_one_inv_data_new(interaction.user, stored, conn)

                em = discord.Embed(title=name,
                                   description=f"> {item["info"]}\n\n"
                                               f"{stock_resp}\n"
                                               f"**{owned_by_how_many}** {make_plural("person", owned_by_how_many)} "
                                               f"{plural_for_own(owned_by_how_many)} this item.\n"
                                               f"You own **{their_count}**.",
                                   colour=clr, url="https://www.youtube.com"
                                   )
                em.set_thumbnail(url=item["url"])
                em.add_field(name="Buying price", value=f"<:robux:1146394968882151434> {cost:,}")
                em.add_field(name="Selling price",
                             value=f"<:robux:1146394968882151434> {floor(int(cost) / 4):,}")

                return await interaction.response.send_message(embed=em)  # type: ignore

        await interaction.response.send_message(f"There is no item named {item_name}.")  # type: ignore

    profile = app_commands.Group(name='editprofile', description='custom-profile-orientated commands for use.',
                                 guild_only=True, guild_ids=APP_GUILDS_ID)

    @profile.command(name='title', description='add a title to your profile.')
    @app_commands.checks.cooldown(1, 30)
    @app_commands.describe(text="maximum of 32 characters allowed")
    async def update_title_profile(self, interaction: discord.Interaction, text: str):
        """This is a subcommand. Change your current title, which is displayed on your profile."""

        async with self.client.pool_connection.acquire() as conn:  # type: ignore
            conn: asqlite_Connection

            if await self.can_call_out(interaction.user, conn):
                return await interaction.response.send_message(  # type: ignore
                    embed=self.not_registered)

            if len(text) > 32:
                return await interaction.response.send_message(  # type: ignore
                    embed=membed("Title cannot exceed 32 characters."))

            text = sub(r'[\n\t]', '', text)
            await self.change_bank_new(interaction.user, conn, text, "title")

            await interaction.response.send_message(  # type: ignore
                embed=membed(f"### {interaction.user.name}'s Profile - [{text}](https://www.dis.gd/support)\n"
                             f"Your title has been changed. A preview is shown above."))

    @profile.command(name='bio', description='add a bio to your profile.')
    @app_commands.checks.cooldown(1, 30)
    async def update_bio_profile(self, interaction: discord.Interaction):
        """This is a subcommand. Add a bio to your profile, or update an existing one."""

        async with self.client.pool_connection.acquire() as conn:  # type: ignore
            conn: asqlite_Connection
            if await self.can_call_out(interaction.user, conn):
                return await interaction.response.send_message(embed=self.not_registered)  # type: ignore
            await interaction.response.send_modal(UpdateInfo())  # type: ignore

    @profile.command(name='avatar', description='change your profile avatar.')
    @app_commands.describe(url='the url of the new avatar. leave blank to remove.')
    @app_commands.checks.cooldown(1, 30)
    async def update_avatar_profile(self, interaction: discord.Interaction, url: Optional[str]):
        """This is a subcommand. Change the avatar that is displayed on the profile embed."""

        async with self.client.pool_connection.acquire() as conn:  # type: ignore
            conn: asqlite_Connection

            if await self.can_call_out(interaction.user, conn):
                return await interaction.response.send_message(embed=self.not_registered)  # type: ignore

        if url is None:
            res = modify_profile("delete", f"{interaction.user.id} avatar_url", url)
            match res:
                case 0:
                    res = "<:warning_nr:1195732155544911882> No custom avatar was found under your account."
                case _:
                    res = "<:overwrite:1195729262729240666> Your avatar was removed."
            return await interaction.response.send_message(embed=membed(res))  # type: ignore

        successful = discord.Embed(colour=0x2B2D31,
                                   description="## <:overwrite:1195729262729240666> Your custom has been added.\n"
                                               "- If valid, it will look like this ----->\n"
                                               "- If you can't see it, change it!")
        successful.set_thumbnail(url=url)
        modify_profile("update", f"{interaction.user.id} avatar_url", url)
        await interaction.response.send_message(embed=successful)  # type: ignore

    @update_avatar_profile.error
    async def uap_error(self, interaction: discord.Interaction, err: discord.app_commands.AppCommandError):
        """Error handler that is fallback when the new avatar could not be updated."""

        modify_profile("delete", f"{interaction.user.id} avatar_url", "who cares")
        return await interaction.response.send_message(  # type: ignore
            embed=membed(
                "<:warning_nr:1195732155544911882> The avatar url requested for could not be added:\n"
                "- The URL provided was not well formed.\n"
                "- Discord embed thumbnails have specific image requirements to ensure proper display.\n"
                " - **The recommended size for a thumbnail is 80x80 pixels.**"
            ))

    @profile.command(name='visibility', description='hide your profile for privacy.')
    @app_commands.describe(mode='Toggle public or private profile')
    @app_commands.checks.cooldown(1, 30)
    async def update_vis_profile(self, interaction: discord.Interaction,
                                 mode: Literal['public', 'private']):
        """This is a subcommand. Make your profile public or private."""

        async with self.client.pool_connection.acquire() as conn:  # type: ignore
            conn: asqlite_Connection
            if await self.can_call_out(interaction.user, conn):
                return await interaction.response.send_message(embed=self.not_registered)  # type: ignore

        modify_profile("update", f"{interaction.user.id} vis", mode)
        cemoji = {"private": "<:privatee:1195728566919385088>",
                  "public": "<:publice:1195728479715590205>"}
        cemoji = cemoji.get(mode)
        await interaction.response.send_message(f"{cemoji} Your profile is now {mode}.",  # type: ignore
                                                ephemeral=True, delete_after=7.5)

    slay = app_commands.Group(name='slay', description='manage your slay.',
                              guild_only=True,
                              guild_ids=APP_GUILDS_ID)

    @slay.command(name='hire', description='hire your own slay.')
    @app_commands.describe(user='member to make a slay. if empty, specify new_slay_name.',
                           new_slay_name='The name of your slay, if you didn\'t pick a user.',
                           gender="the gender of your slay, doesn't have to be true..",
                           investment="how much robux your willing to spend on this slay (no shortcuts)")
    async def hire_slv(self, interaction: discord.Interaction, user: Optional[discord.Member],
                       new_slay_name: Optional[str], gender: Literal["male", "female"], investment: int):
        """This is a subcommand. Hire a new slay based on the parameters, which affect the economic indicators."""

        msg = await self.send_return_interaction_orginal_response(interaction)

        async with self.client.pool_connection.acquire() as conn:  # type: ignore
            conn: asqlite_Connection

            if await self.can_call_out(interaction.user, conn):
                return await msg.edit(content=None, embed=self.not_registered)

            if user and (interaction.user.id == user.id):
                return await msg.edit(content="Why would you make yourself a slay?")
            elif (user is None) and (new_slay_name is None):
                return await msg.edit(content="You did not input any slay.")
            elif (new_slay_name is not None) and (user is not None):
                return await msg.edit(content="You cannot name your slay if the user has also "
                                              "been inputted. Remove this argument if needed.")
            elif abs(investment) > await self.get_wallet_data_only(interaction.user, conn):
                return await msg.edit(
                    content=None,
                    embed=membed("Your slay will not obey your orders if you do not guarantee your investment.\n"
                                 "Hook up some more robux in your investment to increase your slay's productivity."))
            else:

                investment = abs(investment)
                await self.update_bank_new(interaction.user, conn, -investment)
                prod = labour_productivity_via(investment=investment)
                slays = await self.get_slays(conn, interaction.user)
                if new_slay_name is None:
                    new_slay_name = user.display_name

                if not slays:

                    await self.open_slay(conn, interaction.user, new_slay_name, gender, prod, 100, 1)
                    slayy = discord.Embed(description=f"## Slay Summary\n"
                                                      f"- Paid **\U000023e3 {investment:,}** for the following:\n"
                                                      f" - Your brand new slay named {new_slay_name}\n"
                                                      f" - {new_slay_name} has a productivity level "
                                                      f"of `{prod}`.",
                                          colour=discord.Colour.from_rgb(0, 0, 0))
                    slayy.set_footer(text="1/6 slots consumed")
                    await msg.edit(content=None, embed=slayy)

                else:
                    if len(slays) >= 6:
                        return await msg.edit(
                            content=None,
                            embed=membed("## You have reached the maximum slay quota for now.\n"
                                         "You must abandon a current slay before hiring a new one."))

                    for slay in slays:
                        if new_slay_name == slay[0]:
                            return await msg.edit(
                                content="You already own a slay with that name.")

                    await self.open_slay(conn, interaction.user, new_slay_name, gender, prod, 100, 1)

                    slaye = discord.Embed(description=f"## Slay Summary\n"
                                                      f"- Paid **\U000023e3 {investment:,}** for the following:\n"
                                                      f" - Your brand new slay named {new_slay_name}\n"
                                                      f" - {new_slay_name} has a productivity level "
                                                      f"of `{prod}`.",
                                          color=discord.Color.from_rgb(0, 0, 0))
                    slaye.set_footer(text=f"{len(slays) + 1}/6 slay slots consumed")

                    await msg.edit(content=None, embed=slaye)

    @slay.command(name='abandon', description='abandon your slay.')
    @app_commands.rename(slay_purge='slay')
    @app_commands.describe(user='member to make a slay. if empty, specify new_slay_name.',
                           slay_purge='the name of your slay, if you didn\'t pick a user.')
    async def abandon_slv(self, interaction: discord.Interaction, user: Optional[discord.Member],
                          slay_purge: Optional[str]):
        """This is a subcommand. Abandon an existing slay."""

        async with self.client.pool_connection.acquire() as conn:  # type: ignore
            conn: asqlite_Connection

            if await self.can_call_out(interaction.user, conn):
                return await interaction.followup.send(embed=self.not_registered)

            if (user is None) and (slay_purge is None):
                return await interaction.response.send_message("You did not input any slay.")  # type: ignore
            elif (slay_purge is not None) and (user is not None):
                return await interaction.response.send_message(  # type: ignore
                    "You cannot name your slay if the user has also " 
                    "been inputted. Remove this argument if needed.")
            else:
                slays = await self.get_slays(conn, interaction.user)

                if slay_purge is None:
                    slay_purge = user.display_name

                await self.delete_slay(conn, interaction.user, slay_purge)

                return await interaction.response.send_message(  # type: ignore
                    embed=membed(f"Attempted to remove {slay_purge} from your owned slays.\n"
                                 f" - {len(slays)}/6 total slay slots consumed."))

    @slay.command(name='viewall', description="see a user's owned slaves.")
    @app_commands.describe(user='the user to view the slays of')
    async def view_all_slays(self, interaction: discord.Interaction, user: Optional[discord.Member]):
        """This is a subcommand. View all current slays owned by the author or optionally another user."""

        async with self.client.pool_connection.acquire() as conn:  # type: ignore
            conn: asqlite_Connection

            if user is None:
                user = interaction.user

            if await self.can_call_out(user, conn):
                return await interaction.followup.send(embed=NOT_REGISTERED)

            stats = {1: "Free", 0: "Working"}
            slays = await self.get_slays(conn, user)
            embed = discord.Embed(colour=0x2F3136)
            embed.set_author(name=f'{user.name}\'s Slays', icon_url=user.display_avatar.url)

            if len(slays) == 0:
                embed.add_field(name="Nothingness.", value="This user has no slays yet.", inline=False)
                return await interaction.response.send_message(embed=embed)  # type: ignore

            for slay in slays:
                if 66 <= slay[4] <= 100:
                    state = "\U0001f603 "
                elif 33 <= slay[4] < 66:
                    state = "\U0001f610 "
                else:
                    state = "\U0001f641 "
                embed.add_field(name=f'{state}{slay[0]}', value=f'{ARROW}{slay[2]}\n{ARROW}{slay[3]}'
                                                                f'\n{ARROW}{stats.get(slay[5])}')

            embed.set_footer(text=f"{len(slays)}/6 slay slots consumed")
            await interaction.response.send_message(embed=embed)  # type: ignore

    @slay.command(name='work', description="assign your slays to do tasks for you.", extras={"exp_gained": 5})
    @app_commands.describe(duration="the time spent working (e.g, 18h or 1d 3h)")
    async def make_slay_work_pay(self, interaction: discord.Interaction, duration: str):
        """
        This is a subcommand. Dispatch your slays to work.
        The command has to be called again to receive the money gained from this action.
        """

        msg = await self.send_return_interaction_orginal_response(interaction)

        try:
            async with self.client.pool_connection.acquire() as conn:  # type: ignore
                conn: asqlite_Connection

                if await self.can_call_out(interaction.user, conn):
                    return await msg.edit(content=None, embed=NOT_REGISTERED)

                if len(await self.get_slays(conn, interaction.user)) == 0:
                    return await msg.edit(
                        content=None, embed=membed("You got no slays to send to work.")
                    )

                res_duration = parse_duration(duration)

                cooldown = await self.fetch_cooldown(conn, user=interaction.user, cooldown_type="slaywork")
                if cooldown is not None:
                    if cooldown[0] in {"0", 0}:
                        day = number_to_ordinal(int(res_duration.strftime("%d")))
                        shallow = res_duration.strftime(f"%A the {day} of %B at %I:%M%p")
                        await self.change_slay_field(conn, interaction.user, "status", 0)

                        res_duration = datetime_to_string(res_duration)
                        await self.update_cooldown(conn, user=interaction.user, cooldown_type="slaywork",
                                                   new_cd=res_duration)
                        await msg.edit(
                            content=f"## Your slay(s) have been sent off.\n"
                                    f"{ARROW}As commanded, they will work until {shallow} (UTC).")
                    else:
                        cooldown = string_to_datetime(cooldown[0])
                        diff = cooldown - datetime.datetime.now()

                        if diff.total_seconds() <= 0:
                            content = set()
                            await self.update_cooldown(conn, user=interaction.user, cooldown_type="slaywork",
                                                       new_cd="0")

                            labour_actions: dict = {
                                0: "making numerous bets at the casino",
                                1: "working at factory made for slays",
                                2: "playing with the slot machine",
                                3: "doing multiple high-low games",
                                4: "bidding at an auction",
                                5: "robbing vulnerable victims",
                                6: "robbing the central bank"
                            }

                            sad_actions: dict = {
                                0: "isolating oneself from friends and family",
                                1: "struggling with a mundane job at a soul-crushing factory",
                                2: "mindlessly hoping for a change and working for better treatment",
                                3: "seeking fleeting excitement for others to give money",
                                4: "trying to fill the emptiness in his heart",
                                5: "trying to succumb to a life of crime",
                                6: "desperately attempting to rob the central bank, a futile and dangerous endeavor"
                            }

                            happy_slays = await self.count_happiness_above_threshold(conn, interaction.user)

                            index_l = 0
                            slay_fund = randint(50000000, 325000000 * happy_slays)
                            total_fund = 0 + slay_fund
                            disproportionate_share = 0
                            await self.change_slay_field(conn, interaction.user, "status", 1)
                            await self.change_slay_field(conn, interaction.user, "happiness", 100 - randint(20, 67))
                            summ = discord.Embed(colour=discord.Colour.from_rgb(66, 164, 155))
                            slays = await self.get_slays(conn, interaction.user)
                            for slay in slays:
                                if slay[-2] > 30:
                                    doing_what = labour_actions.get(index_l)
                                    disproportionate_share = randint(20000000, slay_fund - disproportionate_share)
                                    bonus = round((1.2 / 100) * disproportionate_share) + disproportionate_share
                                    total_fund += bonus

                                    content.add(f'- {slay[0]} was {doing_what} and got a total '
                                                f'of **\U000023e3 {disproportionate_share:,}**\n'
                                                f' - Bonus: **\U000023e3 {bonus:,}**')
                                else:
                                    doing_what = sad_actions.get(index_l)
                                    loss = (slay[-2] / 100) * disproportionate_share
                                    disproportionate_share = randint(2000, abs(slay_fund - disproportionate_share))
                                    content.add(f'- {slay[0]} was {doing_what} and got a total '
                                                f'of **\U000023e3 {loss:,}**\n'
                                                f' - Bonus: **\U000023e3 {bonus:,}**')

                                    if not summ.fields:
                                        summ.add_field(name='You have an unhappy slay.',
                                                       value='Paying too little attention to your '
                                                             'slay\'s needs will result in your slay running away.',
                                                       inline=False)
                                index_l += 1

                            await self.modify_happiness(conn, interaction.user)
                            net_returns = await self.update_bank_new(interaction.user, conn, total_fund)
                            summ.set_footer(icon_url=interaction.user.display_avatar.url,
                                            text=f"For {interaction.user.name}")
                            summ.description = (f"## <a:2635serversubscriptionsanimated:1174417911344013523> Paycheck\n"
                                                f"> Your slays have made **\U000023e3 {slay_fund:,}**.\n"
                                                f"> Your new `wallet` balance now is **\U000023e3 {net_returns[0]:,}**."
                                                f"\n\nHere is a summary:\n"
                                                f"{'\n'.join(content)}\n")

                            return await msg.edit(content=None, embed=summ)
                        else:
                            minutes, seconds = divmod(diff.total_seconds(), 60)
                            hours, minutes = divmod(minutes, 60)
                            days, hours = divmod(hours, 24)
                            await msg.edit(content=f"Your slays are still working.\n"
                                                   f"They will finish working in **{int(days)}** days, "
                                                   f"**{int(hours)}** hours, **{int(minutes)}** minutes "
                                                   f"and **{int(seconds)}** seconds. ")
                else:
                    return await msg.edit(content="## No data has been found under your name.\n"
                                                  "- This is because you've registered after the "
                                                  "cooldown system was implemented.\n"
                                                  "- A quick fix is to use the /discontinue command "
                                                  "and re-register (you can request a developer to "
                                                  "add your original items back).")
        except ValueError as veer:
            await msg.edit(content=f"{veer}")

    @commands.command(name='reasons', description='identify causes of registration errors.')
    @commands.cooldown(1, 6)
    async def not_registered_why(self, ctx: commands.Context):
        """Display all the possible causes of a not registered check failure."""

        async with ctx.typing():
            await ctx.send(
                embed=discord.Embed(
                    title="Not registered? But why?",
                    description='This list is not exhaustive, all known causes will be displayed:\n'
                                '- You were removed by the c2c developers.\n'
                                '- You opted out of the system yourself.\n'
                                '- The database is currently under construction.\n'
                                '- The database malfunctioned due to a undelivered transaction.\n'
                                '- You called a command that is using an outdated database.\n'
                                '- The database unexpectedly closed (likely due to maintenance).\n'
                                '- The developers are modifying the database contents.\n'
                                '- The database is closed and a connection has not been yet.\n'
                                '- The command hasn\'t acquired a pool connection (devs know why).\n\n'
                                'Found an unusual bug on a command? **Report it now to prevent further '
                                'issues.**', colour=0x2B2D31))

    @app_commands.command(name="use", description="use an item you own from your inventory.", extras={"exp_gained": 3})
    @app_commands.guilds(discord.Object(id=829053898333225010), discord.Object(id=780397076273954886))
    @app_commands.describe(item='the name of the item to use')
    @app_commands.checks.cooldown(1, 6)
    async def use_item(self, interaction: discord.Interaction,
                       item: Literal[
                           'Keycard', 'Trophy', 'Clan License', 'Resistor', 'Amulet',
                           'Dynamic Item', 'Hyperion', 'Crisis', 'Odd Eye']):
        """Use a currently owned item."""

        async with self.client.pool_connection.acquire() as conn:  # type: ignore
            conn: asqlite_Connection

            if await self.can_call_out(interaction.user, conn):
                return await interaction.response.send_message(embed=self.not_registered)  # type: ignore

            item = item.replace(" ", "_")
            quantity = await self.get_one_inv_data_new(interaction.user, item, conn)

            if not quantity:
                return await interaction.response.send_message(  # type: ignore
                    embed=membed("You don't have this item in your inventory."))

            match item:
                case 'Keycard' | 'Resistor' | 'Hyperion' | 'Crisis':
                    return await interaction.response.send_message(  # type: ignore
                        content="This item cannot be used. The effects are always passively active!")
                case 'Trophy':
                    if quantity > 1:
                        content = f'\nThey have **{quantity}** of them, WHAT A BADASS'
                    else:
                        content = ''
                    return await interaction.response.send_message(  # type: ignore
                        f"{interaction.user.name} is flexing on you all "
                        f"with their <:tr1:1165936712468418591> **~~PEPE~~ TROPHY**{content}")
                case _:
                    return await interaction.response.send_message(  # type: ignore
                        embed=membed("The functions for this item aren't available.\n"
                                     "If you wish to submit an idea for what these items do, "
                                     "comment on [this issue on our Github.](https://github.com/SGA-A/c2c/issues/12)")
                    )

    @app_commands.command(name="prestige", description="sacrifice currency stats in exchange for incremental perks.")
    @app_commands.guilds(discord.Object(id=829053898333225010), discord.Object(id=780397076273954886))
    @app_commands.checks.cooldown(1, 6)
    async def prestige(self, interaction: discord.Interaction):
        """Sacrifice a portion of your currency stats in exchange for incremental perks."""

        async with self.client.pool_connection.acquire() as conn:  # type: ignore
            conn: asqlite_Connection
            if await self.can_call_out(interaction.user, conn):
                return await interaction.response.send_message(embed=self.not_registered)  # type: ignore

            data = await conn.fetchone(
                """
                SELECT prestige, level, wallet, bank FROM `bank` WHERE userID = ?
                """, (interaction.user.id,)
            )

            prestige = data[0]
            actual_level = data[1]
            actual_robux = data[2] + data[3]

            if prestige == 10:
                return await interaction.response.send_message(  # type: ignore
                    embed=membed("You've reached the highest prestige!\n"
                                 "No more perks can be obtained from this command.")
                )

            req_robux = (prestige + 1) * 24_000_000
            req_level = (prestige + 1) * 35

            if (actual_robux >= req_robux) and (actual_level >= req_level):
                if active_sessions.setdefault(interaction.user.id, None):
                    return await interaction.response.send_message(  # type: ignore
                        embed=membed("I am already waiting for your input."))
                active_sessions.update({interaction.user.id: 1})

                embed = discord.Embed(
                    title="Are you sure?",
                    description=(
                        "Prestiging means losing nearly everything you've ever earned in the currency "
                        "system in exchange for increasing your 'Prestige Level' "
                        "and upgrading your status.\n\n"
                        "**Things you will lose**:\n"
                        "- All of your items/showcase\n"
                        "- All of your robux\n"
                        "- Your drone(s)\n"
                        "- Your levels and XP\n"
                        "Anything not mentioned in this list will not be lost.\n"
                        "Are you sure you want to prestige?\n"
                        "Type `yes` to confirm or `no` to cancel."
                    ),
                    colour=0x2B2D31
                )
                embed.set_footer(text="This is final and cannot be undone.")

                await interaction.response.send_message(embed=embed)  # type: ignore
                msg = await interaction.original_response()

                def check(m):
                    """Requirements that the client has to wait for."""
                    return ((("n" in m.content.lower()) or ("y" in m.content.lower()))
                            and m.channel == interaction.channel and m.author == interaction.user)

                try:
                    their_message = await self.client.wait_for('message', check=check, timeout=15.0)
                except asyncTE:
                    del active_sessions[interaction.user.id]
                    embed.colour = discord.Colour.brand_red()
                    embed.title = "Action Cancelled"
                    await msg.edit(embed=embed)
                else:
                    del active_sessions[interaction.user.id]
                    if "y" in their_message.content.lower():

                        for item in SHOP_ITEMS:
                            await conn.execute(
                                f"UPDATE `{INV_TABLE_NAME}` SET `{item["name"]}` = ? WHERE userID = ?",
                                (0, interaction.user.id,))
                        await conn.execute(
                            f"""
                            UPDATE `{BANK_TABLE_NAME}` SET wallet = ?, bank = ?, showcase = ?, level = ?, exp = ?, 
                            prestige = prestige + 1, bankspace = bankspace + ? 
                            WHERE userID = ?
                            """, (0, 0, '0 0 0', 1, 0, randint(100_000_000, 500_000_000), interaction.user.id))
                        await conn.commit()
                        embed.colour = discord.Colour.brand_green()
                        embed.title = "Action Confirmed"
                        return await msg.edit(embed=embed)

                    embed.colour = discord.Colour.brand_red()
                    embed.title = "Action Cancelled"
                    await msg.edit(embed=embed)
            else:
                emoji = PRESTIGE_EMOTES.get(prestige+1)
                emoji = search(r':(\d+)>', emoji)
                emoji = self.client.get_emoji(int(emoji.group(1)))

                actual_robux_progress = (actual_robux/req_robux)*100
                actual_level_progress = (actual_level/req_level)*100

                embed = discord.Embed(
                    title=f"Prestige {prestige+1} Requirements",
                    description=(
                        f"**Total Balance**\n"
                        f"<:replyconti:1199688910649954335> \U000023e3 {actual_robux:,}/{req_robux:,}\n"
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
                return await interaction.response.send_message(embed=embed)  # type: ignore

    @app_commands.command(name="getjob", description="earn a salary becoming employed.", extras={"exp_gained": 5})
    @app_commands.guilds(discord.Object(id=829053898333225010), discord.Object(id=780397076273954886))
    @app_commands.describe(job_name='the name of the job')
    @app_commands.checks.cooldown(1, 6)
    async def get_job(self, interaction: discord.Interaction,
                      job_name: Literal[
                          'Plumber', 'Cashier', 'Fisher', 'Janitor', 'Youtuber', 'Police', 'I want to resign!']):
        """Either get a job or resign from your current job."""

        async with self.client.pool_connection.acquire() as conn:  # type: ignore
            conn: asqlite_Connection
            if await self.can_call_out(interaction.user, conn):
                return await interaction.response.send_message(embed=self.not_registered)  # type: ignore

            cooldown = await self.fetch_cooldown(conn, user=interaction.user, cooldown_type="job_change")
            current_job = await self.get_job_data_only(interaction.user, conn)

            if cooldown is not None:
                if cooldown[0] in {"0", 0}:

                    if current_job[0] != job_name:

                        if job_name.startswith("I"):
                            if current_job != "None":
                                ncd = datetime.datetime.now() + datetime.timedelta(days=2)
                                ncd = datetime_to_string(ncd)
                                await self.update_cooldown(conn, user=interaction.user, cooldown_type="job_change",
                                                           new_cd=ncd)

                                await self.change_job_new(interaction.user, conn, job_name='None')
                                return await interaction.response.send_message(  # type: ignore
                                    embed=membed("Alright, I've removed you from your job.\n"
                                                 "You cannot apply to another job for the next **48 hours**."))
                            return await interaction.response.send_message(  # type: ignore
                                embed=membed("You're already unemployed!?"))

                        ncd = datetime.datetime.now() + datetime.timedelta(days=2)
                        ncd = datetime_to_string(ncd)
                        await self.update_cooldown(conn, user=interaction.user, cooldown_type="job_change", new_cd=ncd)

                        await self.change_job_new(interaction.user, conn, job_name=job_name)
                        return await interaction.response.send_message(  # type: ignore
                            embed=membed(f"Congratulations, you've been hired.\n"
                                         f"Starting today, you are working as a {job_name.lower()}."))  # type: ignore
                    return await interaction.response.send_message(  # type: ignore
                        embed=membed(f"You're already a {job_name.lower()}!"))

                else:

                    cooldown = string_to_datetime(cooldown[0])
                    now = datetime.datetime.now()
                    diff = cooldown - now

                    if diff.total_seconds() <= 0:
                        await self.update_cooldown(conn, user=interaction.user, cooldown_type="job_change",
                                                   new_cd="0")
                        if current_job is None:
                            response = "You've just applied for a new job, and got a response already!"
                        else:
                            response = "You've done the paperwork and have now resigned from your previous job."

                        await interaction.response.send_message(  # type: ignore
                            embed=membed(f"{response}\n"
                                         f"Call this command again to begin your new career.")
                        )
                    else:
                        when = datetime.datetime.now() + datetime.timedelta(seconds=diff.total_seconds())
                        embed = discord.Embed(title="Cannot perform this action",
                                              description=f"You can change your job "
                                                          f"{discord.utils.format_dt(when, 'R')}.",
                                              colour=0x2B2D31)
                        await interaction.response.send_message(embed=embed)  # type: ignore

    @app_commands.command(name='profile', description='view user information and stats.')
    @app_commands.guilds(discord.Object(id=829053898333225010), discord.Object(id=780397076273954886))
    @app_commands.describe(user='the profile of the user to find', category='what type of data you want to view')
    @app_commands.checks.cooldown(1, 6)
    async def find_profile(self, interaction: discord.Interaction, user: Optional[discord.Member],
                           category: Optional[Literal["Main Profile", "Gambling Stats"]]):
        """View your profile within the economy."""

        user = user or interaction.user
        category = category or "Main Profile"

        if (get_profile_key_value(f"{user.id} vis") == "private") and (interaction.user.id != user.id):
            return await interaction.response.send_message(  # type: ignore
                embed=membed(f"# <:security:1153754206143000596> {user.name}'s profile is protected.\n"
                             f"Only approved users can view {user.name}'s profile info."))

        ephemerality = False
        if (get_profile_key_value(f"{user.id} vis") == "private") and (interaction.user.id == user.id):
            ephemerality = True

        await interaction.response.send_message(  # type: ignore
            "Crunching the latest data just for you, give us a mo'..", ephemeral=ephemerality, silent=True)
        msg = await interaction.original_response()

        async with self.client.pool_connection.acquire() as conn:  # type: ignore
            conn: asqlite_Connection

            if await self.can_call_out(user, conn):
                return await msg.edit(content=None, embed=NOT_REGISTERED)

            if category == "Main Profile":

                data = await conn.fetchone(
                    f"""SELECT wallet, bank, cmds_ran, showcase, title, 
                    bounty, prestige, level, exp FROM `{BANK_TABLE_NAME}` WHERE userID = ?
                    """,
                    (user.id,))

                procfile = discord.Embed(colour=user.colour, timestamp=discord.utils.utcnow())
                inv = 0
                unique = 0
                total = 0

                for item in SHOP_ITEMS:
                    item_quantity = await self.get_one_inv_data_new(user, item["name"], conn)
                    inv += item["cost"] * item_quantity
                    total += item_quantity
                    unique += 1 if item_quantity else 0

                match user.id:
                    case 546086191414509599 | 992152414566232139 | 1148206353647669298:
                        note = "> <:e1_stafff:1145039666916110356> *This user is a developer of this bot.*\n\n"
                    case _:
                        note = ""

                showcase: str = data[3]
                showcase: list = showcase.split(" ")

                nshowcase = []

                for i in range(1, 4):
                    try:
                        that_item = showcase[i - 1]
                        if item == "0":
                            continue
                        qty = await self.get_one_inv_data_new(user, that_item, conn)
                        if qty >= 1:
                            nshowcase.append(f"`{qty}x` {SHOP_ITEMS[NAME_TO_INDEX.get(that_item)]['emoji']}")
                    except IndexError:
                        continue

                procfile.description = (f"### {user.name}'s Profile - [{data[4]}](https://www.dis.gd/support)\n"
                                        f"{note}"
                                        f"{PRESTIGE_EMOTES.setdefault(data[6], "")} Prestige Level **{data[6]}**"
                                        f"{UNIQUE_BADGES.setdefault(data[-1], "")}\n"
                                        f"<:bountybag:1195653667135692800> Bounty: \U000023e3 **{data[5]:,}**\n"
                                        f"{get_profile_key_value(f"{user.id} badges") or "No badges acquired yet"}")

                boundary = self.calculate_exp_for(level=data[7])
                procfile.add_field(name='Level',
                                   value=f"Level: `{data[7]:,}`\n" 
                                         f"Experience: `{data[8]}/{boundary}`\n" 
                                         f"{generate_progress_bar((data[8]/boundary)*100)}")

                procfile.add_field(name='Robux',
                                   value=f"Wallet: `\U000023e3 {format_number_short(int(data[0]))}`\n"
                                         f"Bank: `\U000023e3 {format_number_short(data[1])}`\n"
                                         f"Net: `\U000023e3 {format_number_short(data[0] + data[1])}`")

                procfile.add_field(name='Items',
                                   value=f"Unique: `{unique:,}`\n"
                                         f"Total: `{format_number_short(total)}`\n"
                                         f"Worth: `\U000023e3 {format_number_short(inv)}`")

                procfile.add_field(name='Commands',
                                   value=f"Total: `{format_number_short(data[2])}`")

                procfile.add_field(name="Drones",
                                   value="See [#32](https://github.com/SGA-A/c2c/issues/32)")

                procfile.add_field(name="Showcase",
                                   value="\n".join(nshowcase) or "No showcase")

                if get_profile_key_value(f"{user.id} bio"):
                    procfile.description += f"\n**Bio:** {get_profile_key_value(f'{user.id} bio')}"
                if get_profile_key_value(f"{user.id} avatar_url"):
                    try:
                        procfile.set_thumbnail(url=get_profile_key_value(f"{user.id} avatar_url"))
                    except discord.HTTPException:
                        modify_profile("delete", f"{user.id} avatar_url", "placeholder")
                        procfile.set_thumbnail(url=user.display_avatar.url)
                else:
                    procfile.set_thumbnail(url=user.display_avatar.url)
                return await msg.edit(content=None, embed=procfile)
            else:

                data = await conn.fetchone(
                    f"""
                    SELECT slotw, slotl, betw, betl, bjw, bjl, slotwa, slotla,
                    betwa, betla, bjwa, bjla FROM `{BANK_TABLE_NAME}` WHERE userID = ?
                    """,
                    (user.id,))

                total_slots = data[0] + data[1]
                total_bets = data[2] + data[3]
                total_blackjacks = data[4] + data[5]

                try:
                    winbe = round((data[2] / total_bets) * 100)
                except ZeroDivisionError:
                    winbe = 0
                try:
                    winsl = round((data[0] / total_slots) * 100)
                except ZeroDivisionError:
                    winsl = 0
                try:
                    winbl = round((data[4] / total_blackjacks) * 100)
                except ZeroDivisionError:
                    winbl = 0

                stats = discord.Embed(title=f"{user.name}'s gambling stats",
                                      colour=0x2B2D31)
                stats.description = "**Reminder:** Games that have resulted in a tie are not tracked."
                stats.add_field(name=f"BET ({total_bets:,})",
                                value=f"Won: \U000023e3 {data[8]:,}\n"
                                      f"Lost: \U000023e3 {data[9]:,}\n"
                                      f"Net: \U000023e3 {data[8] - data[9]:,}\n"
                                      f"Win: {winbe}% ({data[2]})")
                stats.add_field(name=f"SLOTS ({total_slots:,})",
                                value=f"Won: \U000023e3 {data[6]:,}\n"
                                      f"Lost: \U000023e3 {data[7]:,}\n"
                                      f"Net: \U000023e3 {data[6] - data[7]:,}\n"
                                      f"Win: {winsl}% ({data[0]})")
                stats.add_field(name=f"BLACKJACK ({total_blackjacks:,})",
                                value=f"Won: \U000023e3 {data[10]:,}\n"
                                      f"Lost: \U000023e3 {data[11]:,}\n"
                                      f"Net: \U000023e3 {data[10] - data[11]:,}\n"
                                      f"Win: {winbl}% ({data[4]})")
                stats.set_footer(text="The number next to the name is how many matches are recorded")

                await msg.edit(content=None, embed=stats)  # type: ignore
                try:
                    its_sum = total_bets + total_slots + total_blackjacks
                    pie = (ImageCharts()
                           .chd(
                        f"t:{(total_bets / its_sum) * 100},"
                        f"{(total_slots / its_sum) * 100},{(total_blackjacks / its_sum) * 100}")
                           .chco("EA469E|03A9F4|FFC00C").chl(
                        f"BET ({total_bets})|SLOTS ({total_slots})|BJ ({total_blackjacks})")
                           .chdl("Total bet games|Total slot games|Total blackjack games").chli(f"{its_sum}").chs(
                        "600x480")
                           .cht("pd").chtt(f"{user.name}'s total games played"))
                    await msg.reply(content=pie.to_url())
                except ZeroDivisionError:
                    await msg.reply(
                        content=f"Looks like {user.display_name} hasn't got enough data yet to form a pie chart.")

    @app_commands.command(name='highlow', description='guess the number. jackpot wins big!', extras={"exp_gained": 3})
    @app_commands.guilds(discord.Object(id=829053898333225010), discord.Object(id=780397076273954886))
    @app_commands.checks.cooldown(1, 6)
    @app_commands.describe(robux='an integer to bet upon. Supports Shortcuts (max, all, exponents).')
    async def highlow(self, interaction: discord.Interaction, robux: str):
        """
        Guess the number. The user must guess if the clue the client gives is higher,
        lower or equal to the actual number.
        """

        def is_valid(value: int, user_balance: int) -> bool:
            """A check that defines that the amount a user inputs is valid for their account.
            Meets preconditions for highlow.
            :param value: amount to check,
            :param user_balance: the user's balance currenctly, which should be an integer.
            :return: A boolean indicating whether the amount is valid for the function to proceed."""
            if value <= 0:
                return False
            elif value > 75_000_000:
                return False
            elif value < 100000:
                return False
            elif value > user_balance:
                return False
            else:
                return True

        async with self.client.pool_connection.acquire() as conn:  # type: ignore
            conn: asqlite_Connection
            if await self.can_call_out(interaction.user, conn):
                return await interaction.response.send_message(embed=self.not_registered)  # type: ignore

            real_amount = determine_exponent(robux)
            wallet_amt = await self.get_wallet_data_only(interaction.user, conn)

            if isinstance(real_amount, str):
                if real_amount in {'all', 'max'}:
                    if 75000000 > wallet_amt:
                        real_amount = wallet_amt
                    else:
                        real_amount = 75000000
                else:
                    return await interaction.response.send_message(embed=ERR_UNREASON)  # type: ignore

            if not (is_valid(int(real_amount), wallet_amt)):
                return await interaction.response.send_message(embed=ERR_UNREASON)  # type: ignore

            number = randint(1, 100)
            hint = randint(1, 100)

            query = discord.Embed(colour=0x2B2D31,
                                  description=f"I just chose a secret number between 0 and 100.\n"
                                              f"Is the secret number *higher* or *lower* than {hint}?")
            query.set_author(name=f"{interaction.user.name}'s high-low game",
                             icon_url=interaction.user.display_avatar.url)
            query.set_footer(text="The jackpot button is if you think it is the same!")
            await interaction.response.send_message(  # type: ignore
                view=HighLow(interaction, self.client, hint_provided=hint, bet=real_amount, value=number),
                embed=query)

            pmulti = await self.get_pmulti_data_only(interaction.user, conn)
            await self.raise_pmulti_warning(interaction, pmulti[0])

    @app_commands.command(name='slots',
                          description='try your luck on a slot machine.', extras={"exp_gained": 3})
    @app_commands.guilds(discord.Object(id=829053898333225010), discord.Object(id=780397076273954886))
    @app_commands.checks.cooldown(1, 2)
    @app_commands.rename(amount='robux')
    @app_commands.describe(amount='an integer to bet upon. Supports Shortcuts (max, all, exponents).')
    async def slots(self, interaction: discord.Interaction, amount: str):
        """Play a round of slots. At least one matching combination is required to win."""

        async with self.client.pool_connection.acquire() as conn:  # type: ignore
            conn: asqlite_Connection

            if await self.can_call_out(interaction.user, conn):
                await interaction.response.send_message(embed=self.not_registered)  # type: ignore

        # --------------- Checks before betting i.e. has keycard, meets bet constraints. -------------
        data = await self.get_one_inv_data_new(interaction.user, "Keycard", conn)
        amount = determine_exponent(amount)

        slot_stuff = await conn.execute(f"SELECT slotw, slotl, wallet FROM `{BANK_TABLE_NAME}` WHERE userID = ?",
                                        (interaction.user.id,))
        slot_stuff = await slot_stuff.fetchone()

        id_won_amount, id_lose_amount, wallet_amt = slot_stuff[0], slot_stuff[1], slot_stuff[-1]

        try:
            assert isinstance(amount, int)
            amount = amount
        except AssertionError:
            if amount in {'max', 'all'}:
                if data >= 1:
                    amount = min(75_000_000, wallet_amt)
                else:
                    amount = min(50_000_000, wallet_amt)
            else:
                return await interaction.response.send_message(embed=ERR_UNREASON)  # type: ignore

        # --------------- Contains checks before betting i.e. has keycard, meets bet constraints. -------------
        if data >= 1:
            if not (30000 <= amount <= 75000000):
                return await interaction.response.send_message(  # type: ignore
                    embed=discord.Embed(colour=0x2F3136, description=(
                        f'## You did not meet the slot machine criteria.\n'
                        f'- You wanted to bet {CURRENCY}**{amount:,}**\n'
                        f' - A minimum bet of {CURRENCY}**30,000** must be made\n'
                        f' - A maximum bet of {CURRENCY}**75,000,000** can only be made.'
                    )))
            elif amount > wallet_amt:
                return await interaction.response.send_message(  # type: ignore
                    embed=discord.Embed(colour=0x2F3136, description=(
                        f'Cannot perform this action.\n'
                        f'You only have {CURRENCY}**{wallet_amt:,}**.\n'
                        f'You\'ll need {CURRENCY}**{amount - wallet_amt:,}** more in your wallet first.'
                    )))
        else:
            if not (50000 <= amount <= 50000000):
                return await interaction.response.send_message(  # type: ignore
                    embed=discord.Embed(colour=0x2F3136, description=(
                        f'## You did not meet the slot machine criteria.\n'
                        f'- You wanted to bet {CURRENCY}**{amount:,}**\n'
                        f' - A minimum bet of {CURRENCY}**50,000** must be made.\n'
                        f' - A maximum bet of {CURRENCY}**50,000,000** can only be made.'
                    )))

            elif amount > wallet_amt:
                return await interaction.response.send_message(  # type: ignore
                    embed=discord.Embed(colour=0x2F3136, description=(
                        f"## Cannot perform this action.\n"
                        f"You only have {CURRENCY}**{wallet_amt:,}**.\n"
                        f"You'll need {CURRENCY}**{amount - wallet_amt:,}** more in your wallet first."
                    )))

        # ------------------ THE SLOT MACHINE ITESELF ------------------------

        emoji_outcome = generate_slot_combination()
        freq1, freq2, freq3 = emoji_outcome[0], emoji_outcome[1], emoji_outcome[2]

        if emoji_outcome.count(freq1) > 1:

            new_multi = (SERVER_MULTIPLIERS.setdefault(interaction.guild.id, 0) +
                         BONUS_MULTIPLIERS[f'{freq1 * emoji_outcome.count(freq1)}'])
            amount_after_multi = floor(((new_multi / 100) * amount) + amount)
            updated = await self.update_bank_three_new(interaction.user, conn, "slotwa", amount_after_multi,
                                                       "wallet", amount_after_multi, "slotw", 1)

            prcntw = round((updated[2] / (id_lose_amount + updated[2])) * 100, 1)

            embed = discord.Embed(description=f"**\U0000003e** {freq1} {freq2} {freq3} **\U0000003c**\n\n"
                                              f"**It's a match!** You've won "
                                              f"\U000023e3 **{amount_after_multi:,}** robux.\n"
                                              f"Your new balance is \U000023e3 **{updated[1]:,}**.\n"
                                              f"You've won {prcntw}% of all slots games.",
                                  colour=discord.Color.brand_green())

            embed.set_author(name=f"{interaction.user.name}'s winning slot machine",
                             icon_url=interaction.user.display_avatar.url)
            embed.set_footer(text=f"Multiplier: {new_multi}%")

        elif emoji_outcome.count(freq2) > 1:

            new_multi = (SERVER_MULTIPLIERS.setdefault(interaction.guild.id, 0) +
                         BONUS_MULTIPLIERS[f'{freq2 * emoji_outcome.count(freq2)}'])
            amount_after_multi = floor(((new_multi / 100) * amount) + amount)

            updated = await self.update_bank_three_new(interaction.user, conn, "slotwa", amount_after_multi,
                                                       "wallet", amount_after_multi, "slotw", 1)

            prcntw = round((updated[2] / (id_lose_amount + updated[2])) * 100, 1)

            embed = discord.Embed(
                description=f"**\U0000003e** {freq1} {freq2} {freq3} **\U0000003c**\n\n"
                            f"**It's a match!** You've won \U000023e3 **{amount_after_multi:,}** robux.\n"
                            f"Your new balance is \U000023e3 **{updated[1]:,}**.\n"
                            f"You've won {prcntw}% of all slots games.",
                colour=discord.Color.brand_green())

            embed.set_footer(text=f"Multiplier: {new_multi}%")
            embed.set_author(name=f"{interaction.user.name}'s winning slot machine",
                             icon_url=interaction.user.display_avatar.url)

        else:
            updated = await self.update_bank_three_new(interaction.user, conn, "slotla", amount,
                                                       "wallet", -amount, "slotl", 1)

            prcntl = round((updated[-1] / (updated[-1] + id_won_amount)) * 100, 1)

            embed = discord.Embed(description=f"**\U0000003e** {freq1} {freq2} {freq3} **\U0000003c**\n\n"
                                              f"**No match!** You've lost {CURRENCY}**{amount:,}** robux.\n"
                                              f"Your new balance is {CURRENCY}**{updated[1]:,}**.\n"
                                              f"You've lost {prcntl}% of all slots games.",
                                  colour=discord.Color.brand_red())

            embed.set_author(name=f"{interaction.user.name}'s losing slot machine",
                             icon_url=interaction.user.display_avatar.url)

        await interaction.response.send_message(embed=embed)  # type: ignore

    @app_commands.command(name='inventory', description='view your currently owned items.')
    @app_commands.guilds(discord.Object(id=829053898333225010), discord.Object(id=780397076273954886))
    @app_commands.describe(member='the member to view the inventory of:')
    async def inventory(self, interaction: discord.Interaction, member: Optional[discord.Member]):
        """View your inventory or another player's inventory."""

        member = member or interaction.user

        if member.bot and member.id != self.client.user.id:
            return await interaction.response.send_message(  # type: ignore
                embed=membed("Bots do not have accounts."), delete_after=5.0)

        async with self.client.pool_connection.acquire() as conn:  # type: ignore
            conn: asqlite_Connection

            if await self.can_call_out(member, conn):
                return await interaction.response.send_message(embed=NOT_REGISTERED)  # type: ignore

            em = discord.Embed(color=0x2F3136)
            length = 3
            value, svalue = 0, 0
            total_items = 0
            owned_items = []

            for item in SHOP_ITEMS:
                name = item["name"]
                qualified_name = " ".join(name.split("_"))
                cost = item["cost"]
                item_id = item["id"]
                item_emoji = item["emoji"]
                item_type = item["rarity"]
                data = await self.update_inv_new(member, 0, name, conn)
                if data[0] >= 1:
                    value += int(cost) * data[0]
                    svalue += int(cost / 4) * data[0]
                    total_items += data[0]
                    owned_items.append(
                        f"{item_emoji} **{qualified_name}** ({data[0]} owned)\n"
                        f"ID: **`{item_id}`**\nItem Type: {item_type}")

            if len(owned_items) == 0:
                em.set_author(name=f"{member.name}'s Inventory", icon_url=member.display_avatar.url)
                em.description = (f"{member.name} currently has **no items** in their inventory.\n"
                                  f"**Net Value:** <:robux:1146394968882151434> 0\n"
                                  f"**Sell Value:** <:robux:1146394968882151434> 0")

                em.add_field(
                    name="Nothingness.", value="No items were found from this user.", inline=False)
                return await interaction.response.send_message(embed=em)  # type: ignore

            async def get_page_part(page: int):
                """Helper function to determine what page of the paginator we're on."""

                em.set_author(name=f"{member.name}'s Inventory", icon_url=member.display_avatar.url)

                offset = (page - 1) * length

                em.description = (f"{member.name} currently has **`{total_items}`** item(s) in their inventory.\n"
                                  f"**Net Value:** <:robux:1146394968882151434> {value:,}\n"
                                  f"**Sell Value:** <:robux:1146394968882151434> {svalue:,}\n\n")

                for itemm in owned_items[offset:offset + length]:
                    em.description += f"{itemm}\n\n"

                n = Pagination.compute_total_pages(len(owned_items), length)

                em.set_footer(text=f"Owned Items \U00002500 Page {page} of {n}")
                return em, n

            await Pagination(interaction, get_page_part).navigate()

    @app_commands.command(name='buy', description='make a purchase from the shop.', extras={"exp_gained": 4})
    @app_commands.guilds(discord.Object(id=829053898333225010), discord.Object(id=780397076273954886))
    @app_commands.describe(item_name='the name of the item you want to buy.',
                           quantity='the quantity of the item(s) you wish to buy')
    async def buy(self, interaction: discord.Interaction,
                  item_name: Literal[
                      'Keycard', 'Trophy', 'Clan License', 'Resistor', 'Amulet',
                      'Dynamic Item', 'Hyperion', 'Crisis', 'Odd Eye'],
                  quantity: Optional[Literal[1, 2, 3, 4, 5]]):
        """Buy an item directly from the shop."""

        if quantity is None:
            quantity = 1

        async with self.client.pool_connection.acquire() as conn:  # type: ignore
            conn: asqlite_Connection

            if await self.can_call_out(interaction.user, conn):
                return await interaction.response.send_message(embed=self.not_registered)  # type: ignore

            wallet_amt = await self.get_wallet_data_only(interaction.user, conn)

            for item in SHOP_ITEMS:
                access_name = ' '.join(item["name"].split('_'))

                if item_name == access_name:
                    ie = item['emoji']
                    proper_name = item.setdefault('qn', None) or access_name
                    stock_item = get_stock(item_name)

                    if stock_item == 0:
                        return await interaction.response.send_message(  # type: ignore
                            embed=membed(f"## Unsuccessful Transaction\n"
                                         f"- The {ie} **{item_name}** is currently out of stock.\n"
                                         f" - Until a user who owns this item chooses to "
                                         f"sell it, stocks cannot be refilled."))

                    if quantity > stock_item:
                        proper_name = " ".join(proper_name.split("_"))
                        proper_name = make_plural(proper_name, stock_item)
                        their_name = make_plural(proper_name, quantity)
                        return await interaction.response.send_message(  # type: ignore
                            embed=membed(f"## Unsuccessful Transaction\n"
                                         f"There are only **{stock_item}** {ie} **{proper_name.title()}** available.\n"
                                         f"{ARROW}Meaning you cannot "
                                         f"possibly buy **{quantity}** {their_name.title()}."))

                    total_cost = int((item["cost"] * int(quantity)))

                    if wallet_amt < int(total_cost):
                        proper_name = " ".join(proper_name.split("_"))
                        proper_name = make_plural(proper_name, quantity)
                        return await interaction.response.send_message(  # type: ignore
                            embed=membed(f"## Unsuccessful Transaction\n"
                                         f"You'll need {CURRENCY}**{total_cost - wallet_amt:,}** more to "
                                         f"purchase {quantity} {ie} **{proper_name.title()}**."))

                    await self.update_inv_new(interaction.user, +int(quantity), item["name"], conn)
                    await self.update_bank_new(interaction.user, conn, -total_cost)
                    modify_stock(item_name, "-", quantity)

                    match quantity:
                        case 1:
                            return await interaction.response.send_message(  # type: ignore
                                embed=membed(f"## Success\n"
                                             f"- Purchased **1** {ie} **{item_name}** by paying "
                                             f"{CURRENCY}**{total_cost:,}**.\n"
                                             f" - The items requested have been added to your inventory."))
                        case _:
                            their_name = ' '.join(proper_name.split("_"))
                            their_name = make_plural(their_name, quantity)
                            await interaction.response.send_message(  # type: ignore
                                embed=membed(f"## Success\n"
                                             f"- Purchased **{quantity}** {ie} **{their_name.title()}** by"
                                             f" paying {CURRENCY}**{total_cost:,}**.\n"
                                             f" - The items requested have been added to your inventory."))

    @app_commands.command(name='sell', description='sell an item from your inventory.', extras={"exp_gained": 4})
    @app_commands.guilds(discord.Object(id=829053898333225010), discord.Object(id=780397076273954886))
    @app_commands.describe(item_name='the name of the item you want to sell.',
                           sell_quantity='the quantity you wish to sell. defaults to 1.')
    async def sell(self, interaction: discord.Interaction,
                   item_name: Literal[
                       'Keycard', 'Trophy', 'Clan License', 'Resistor',
                       'Amulet', 'Dynamic Item', 'Hyperion', 'Crisis', 'Odd Eye'],
                   sell_quantity: Optional[Literal[1, 2, 3, 4, 5]]):
        """Sell an item you already own."""

        if sell_quantity is None:
            sell_quantity = 1

        name = item_name.replace(" ", "_")
        async with self.client.pool_connection.acquire() as conn:  # type: ignore
            conn: asqlite_Connection

            if await self.can_call_out(interaction.user, conn):
                return await interaction.response.send_message(embed=self.not_registered)  # type: ignore

            for item in SHOP_ITEMS:
                if name == item["name"]:
                    ie = item['emoji']
                    cost = int(round((item["cost"] / 4) * sell_quantity, ndigits=None))
                    quantity = await self.update_inv_new(interaction.user, 0, item["name"], conn)

                    if quantity[0] < 1:
                        return await interaction.response.send_message(  # type: ignore
                            embed=membed(f"You don't have a {ie} **{item_name}** in your inventory."))

                    new_quantity = quantity[0] - sell_quantity
                    if new_quantity < 0:
                        return await interaction.response.send_message(  # type: ignore
                            "You are requesting to sell more than what you currently own. Not possible.")

                    await self.change_inv_new(interaction.user, new_quantity, item["name"], conn)
                    modify_stock(item_name, "+", sell_quantity)
                    await self.update_bank_new(interaction.user, conn, +cost)

                    match sell_quantity:
                        case 1:
                            proper_name = item.setdefault('qn', None) or name
                            proper_name = ' '.join(proper_name.split('_'))
                            return await interaction.response.send_message(  # type: ignore
                                embed=membed(f"You just sold 1 {ie} **{proper_name.title()}** and got "
                                             f"<:robux:1146394968882151434> **{cost:,}** in return."))
                        case _:
                            proper_name = item.setdefault('qn', None) or name
                            proper_name = ' '.join(proper_name.split('_'))
                            proper_name = make_plural(proper_name, sell_quantity)
                            return await interaction.response.send_message(  # type: ignore
                                embed=membed(f"You just sold {sell_quantity} {ie} **{proper_name.title()}** and got "
                                             f"<:robux:1146394968882151434> **{cost:,}** in return."))

    @app_commands.command(name="work", description="work and earn an income, if you have a job.",
                          extras={"exp_gained": 3})
    @app_commands.guilds(discord.Object(id=829053898333225010), discord.Object(id=780397076273954886))
    async def work(self, interaction: discord.Interaction):
        """Work at your current job. You must have one for this to work."""

        await interaction.response.defer(thinking=True, ephemeral=True)  # type: ignore

        words = {
            "Plumber": [("TOILET", "SINK", "SEWAGE", "SANITATION", "DRAINAGE", "PIPES"), 400000000],
            "Cashier": [("ROBUX", "TILL", "ITEMS", "WORKER", "REGISTER", "CHECKOUT", "TRANSACTIONS", "RECEIPTS"),
                        500000000],
            "Fisher": [
                ("FISHING", "NETS", "TRAWLING", "FISHERMAN", "CATCH", "VESSEL", "AQUATIC", "HARVESTING", "MARINE"),
                550000000],
            "Janitor": [
                ("CLEANING", "SWEEPING", "MOPING", "CUSTODIAL", "MAINTENANCE", "SANITATION", "BROOM", "VACUUMING"),
                650000000],
            "Youtuber": [("CONTENT CREATION", "VIDEO PRODUCTION", "CHANNEL", "SUBSCRIBERS", "EDITING", "UPLOAD",
                          "VLOGGING", "MONETIZATION", "THUMBNAILS", "ENGAGEMENT"), 1000000000],
            "Police": [("LAW ENFORCEMENT", "PATROL", "CRIME PREVENTION", "INVESTIGATION", "ARREST", "UNIFORM", "BADGE",
                        "INTERROGATION"), 1200000000]
        }

        async with self.client.pool_connection.acquire() as conn:  # type: ignore
            conn: asqlite_Connection

            if await self.can_call_out(interaction.user, conn):
                return await interaction.followup.send(embed=self.not_registered)

            job_val = await self.get_job_data_only(user=interaction.user, conn_input=conn)

            if job_val == "None":
                msg = await interaction.followup.send(embed=membed("You don't have a job, get one first."))
                return await msg.delete(delay=15.0)

            possible_words: tuple = words.get(job_val)[0]
            selected_word = choice(possible_words)

            letters_to_hide = max(1, len(selected_word) // 3)  # You can adjust this ratio

            indices_to_hide = [i for i, char in enumerate(selected_word) if char.isalpha()]
            indices_hidden = sample(indices_to_hide, min(letters_to_hide, len(indices_to_hide)))

            hidden_word_list = [char if i not in indices_hidden else '_' for i, char in enumerate(selected_word)]
            hidden_word = ''.join(hidden_word_list)

            def check(m):
                """Requirements that the client has to wait for."""
                return (m.content.lower() == selected_word.lower()
                        and m.channel == interaction.channel and m.author == interaction.user)

            msg: discord.WebhookMessage = await interaction.followup.send(
                embed=membed(
                    f"## <:worke:1195716983384191076> What is the word?\n"
                    f"Replace the blanks \U0000279c [`{hidden_word}`](https://www.sss.com)."))
            await msg.delete(delay=15.0)

            my_msg = await interaction.channel.send("Waiting for correct input..")

            try:
                await self.client.wait_for('message', check=check, timeout=15.0)
            except asyncTE:
                await my_msg.edit(content="Your boss is considering cutting your salary!")
                await interaction.followup.send("`BOSS`: Too slow, you get nothing for the attitude. I expect better "
                                                "of you next time.")
            else:
                salary = words.get(job_val)[-1]
                rangeit = randint(10000000, salary)
                await self.update_bank_new(interaction.user, conn, rangeit)
                await my_msg.edit(content=f"`BOSS`: Good work from you {interaction.user.display_name}, got the "
                                          f"job done. You got **\U000023e3 {rangeit:,}** for your efforts.")

    @app_commands.command(name="balance", description="returns a user's current balance.")
    @app_commands.describe(user='the user to return the balance of',
                           with_force='whether to register this user if not already')
    @app_commands.guild_only()
    @app_commands.checks.cooldown(1, 6)
    async def find_balance(self, interaction: discord.Interaction, user: Optional[discord.Member],
                           with_force: Optional[bool]):
        """Returns a user's balance."""
        msg = await self.send_return_interaction_orginal_response(interaction)

        user = user or interaction.user

        async with self.client.pool_connection.acquire() as conn:  # type: ignore
            conn: asqlite_Connection

            if await self.can_call_out(user, conn) and (user.id != interaction.user.id):
                if with_force and (interaction.user.id in self.client.owner_ids):
                    await self.open_bank_new(user, conn)
                    await self.open_inv_new(user, conn)
                    await self.open_cooldowns(user, conn)
                    return await msg.edit(content=None, embed=membed(f"Force registered {user.name}."))
                await msg.edit(content=None, embed=membed(f"{user.name} isn't registered."))

            elif await self.can_call_out(user, conn) and (user.id == interaction.user.id):

                await self.open_bank_new(user, conn)
                await self.open_inv_new(user, conn)
                await self.open_cooldowns(user, conn)
                norer = membed(f"# <:successful:1183089889269530764> You are now registered.\n"
                               f"Your records have been added in our database, **{user.name}**.\n"
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
                               f"</buy:1172898644287029334>")
                return await msg.edit(content=None, embed=norer)
            else:
                nd = await conn.execute("SELECT wallet, bank, bankspace FROM `bank` WHERE userID = ?", (user.id,))
                nd = await nd.fetchone()
                bank = nd[0] + nd[1]
                inv = 0

                for item in SHOP_ITEMS:
                    name = item["name"]
                    cost = item["cost"]
                    data = await self.get_one_inv_data_new(user, name, conn)
                    inv += int(cost) * data

                space = round((nd[1]/nd[2])*100, 2)

                balance = discord.Embed(color=0x2F3136, timestamp=discord.utils.utcnow())
                balance.set_author(name=f"{user.name}'s balance", icon_url=user.display_avatar.url)

                balance.add_field(name="<:walleten:1195719280898097192> Wallet", value=f"\U000023e3 {nd[0]:,}",
                                  inline=True)
                balance.add_field(name="<:banken:1195708938734288967> Bank", value=f"\U000023e3 {nd[1]:,}",
                                  inline=True)
                balance.add_field(name="<:bankspacen:1198635497107501147> Bankspace",
                                  value=f"\U000023e3 {nd[2]:,} ({space}% full)", inline=True)
                balance.add_field(name="<:netben:1195710007233228850> Money Net", value=f"\U000023e3 {bank:,}",
                                  inline=True)
                balance.add_field(name="<:netinven:1195711122343481364> Inventory Net", value=f"\U000023e3 {inv:,}",
                                  inline=True)
                balance.add_field(name="<:nettotalen:1195710560910725180> Total Net",
                                  value=f"\U000023e3 {inv + bank:,}", inline=True)

                if user.id in self.client.owner_ids:
                    balance.set_footer(icon_url='https://cdn.discordapp.com/emojis/1174417902980583435.webp?size=128&'
                                                'quality=lossless',
                                       text='mallow is dazzled')

                await msg.edit(content=None, embed=balance)

    @app_commands.command(name="resetmydata", description="opt out of the virtual economy.")
    @app_commands.guilds(discord.Object(id=829053898333225010), discord.Object(id=780397076273954886))
    @app_commands.describe(member='the user to remove all of the data of')
    async def discontinue_bot(self, interaction: discord.Interaction, member: Optional[discord.Member]):
        """Opt out of the virtual economy and delete all of the user data associated."""

        member = member or interaction.user
        if interaction.user.id not in self.client.owner_ids:
            if (member is not None) and (member != interaction.user):
                return await interaction.response.send_message(  # type: ignore
                    embed=membed(f"You are not allowed to delete other user's data.\n"
                                 f"{member.mention} should call this command themselves"
                                 f" to reset their data."))

        async with self.client.pool_connection.acquire() as conn:  # type: ignore
            conn: asqlite_Connection

            if await self.can_call_out(member, conn):
                await interaction.response.send_message(  # type: ignore
                    embed=membed(f"Could not find {member.name} in the database."))
            else:

                if member.id == interaction.user.id:
                    view = ConfirmDeny(interaction, self.client, member)

                    embed = discord.Embed(title="Are you sure you want to do this?",
                                          description="Remember, you are about to erase **all** your data.\n"
                                                      "This process is irreversible, you "
                                                      "cannot recover this data again.",
                                          colour=0x2B2D31)

                    await interaction.response.send_message(embed=embed, view=view)  # type: ignore
                    view.msg = await interaction.original_response()
                    return

                tables_to_delete = {BANK_TABLE_NAME, INV_TABLE_NAME, COOLDOWN_TABLE_NAME, SLAY_TABLE_NAME}

                for table in tables_to_delete:
                    await conn.execute(f"DELETE FROM `{table}` WHERE userID = ?", (member.id,))

                await conn.commit()
                success = discord.Embed(title="Action Confirmed",
                                        description=f"{member.name} is now basically out of our database, "
                                                    f"we no longer have any EUD from {member.name} (end user data).",
                                        colour=discord.Colour.brand_green())
                success.set_footer(text="Some requirements were bypassed.", icon_url=self.client.user.avatar.url)

                await interaction.response.send_message(embed=success)  # type: ignore

    @app_commands.command(name="withdraw", description="withdraw robux from your account.")
    @app_commands.guilds(discord.Object(id=829053898333225010), discord.Object(id=780397076273954886))
    @app_commands.describe(robux='the amount of robux to withdraw. Supports Shortcuts (max, all, exponents).')
    @app_commands.checks.cooldown(1, 6)
    async def withdraw(self, interaction: discord.Interaction, robux: str):
        """Withdraw a given amount of robux from your bank."""

        user = interaction.user
        actual_amount = determine_exponent(robux)

        async with (self.client.pool_connection.acquire() as conn):  # type: ignore
            conn: asqlite_Connection
            if await self.can_call_out(interaction.user, conn):
                await interaction.response.send_message(embed=self.not_registered)  # type: ignore

            bank_amt = await self.get_spec_bank_data(interaction.user, "bank", conn)
            if isinstance(actual_amount, str):
                if actual_amount.lower() == "all" or actual_amount.lower() == "max":
                    wallet_new = await self.update_bank_new(user, conn, +bank_amt)
                    bank_new = await self.update_bank_new(user, conn, -bank_amt, "bank")

                    embed = discord.Embed(colour=0x2F3136)

                    embed.add_field(name="<:withdraw:1195657655134470155> Withdrawn", value=f"\U000023e3 {bank_amt:,}",
                                    inline=False)
                    embed.add_field(name="Current Wallet Balance", value=f"\U000023e3 {wallet_new[0]:,}")
                    embed.add_field(name="Current Bank Balance", value=f"\U000023e3 {bank_new[0]:,}")

                    return await interaction.response.send_message(embed=embed)  # type: ignore
                return await interaction.response.send_message(embed=ERR_UNREASON)  # type: ignore

            amount_conv = abs(int(actual_amount))

            if not amount_conv:
                return await interaction.response.send_message(  # type: ignore
                    embed=membed("The amount to withdraw needs to be more than 0."))

            elif amount_conv > bank_amt:
                embed = discord.Embed(colour=0x2F3136,
                                      description="- You do not have that much money in your bank.\n"
                                                  f" - You wanted to withdraw \U000023e3 **{amount_conv:,}**.\n"
                                                  f" - Currently, you only have \U000023e3 **{bank_amt:,}**.")
                return await interaction.response.send_message(embed=embed)  # type: ignore

            else:
                wallet_new = await self.update_bank_new(user, conn, +amount_conv)
                bank_new = await self.update_bank_new(user, conn, -amount_conv, "bank")

                embed = discord.Embed(colour=0x2F3136)
                embed.add_field(name="<:withdraw:1195657655134470155> Withdrawn", value=f"\U000023e3 {amount_conv:,}",
                                inline=False)
                embed.add_field(name="Current Wallet Balance", value=f"\U000023e3 {wallet_new[0]:,}")
                embed.add_field(name="Current Bank Balance", value=f"\U000023e3 {bank_new[0]:,}")

                return await interaction.response.send_message(embed=embed)  # type: ignore

    @app_commands.command(name='deposit', description="deposit robux to your bank account.")
    @app_commands.guilds(discord.Object(id=829053898333225010), discord.Object(id=780397076273954886))
    @app_commands.describe(robux='the amount of robux to deposit. Supports Shortcuts (max, all, exponents).')
    @app_commands.checks.cooldown(1, 6)
    async def deposit(self, interaction: discord.Interaction, robux: str):
        """Deposit an amount of robux into your bank."""

        user = interaction.user
        actual_amount = determine_exponent(robux)

        async with self.client.pool_connection.acquire() as conn:  # type: ignore
            conn: asqlite_Connection

            if await self.can_call_out(interaction.user, conn):
                return await interaction.response.send_message(embed=self.not_registered)  # type: ignore

            details = await conn.execute("SELECT wallet, bank, bankspace FROM `bank` WHERE userID = ?",
                                         (interaction.user.id,))
            details = await details.fetchone()
            wallet_amt = details[0]
            if isinstance(actual_amount, str):
                if actual_amount.lower() == "all" or actual_amount.lower() == "max":
                    available_bankspace = details[2] - details[1]

                    if not available_bankspace:
                        return await interaction.response.send_message(  # type: ignore
                            embed=membed(f"You can only hold **\U000023e3 {details[2]:,}** in your bank right now.\n"
                                         f"To hold more, use currency commands and level up more."))

                    wallet_new = await self.update_bank_new(user, conn, -available_bankspace)
                    bank_new = await self.update_bank_new(user, conn, +available_bankspace, "bank")

                    embed = discord.Embed(colour=0x2F3136)
                    embed.add_field(name="<:deposit:1195657772231036948> Deposited",
                                    value=f"\U000023e3 {available_bankspace:,}", inline=False)
                    embed.add_field(name="Current Wallet Balance", value=f"\U000023e3 {wallet_new[0]:,}")
                    embed.add_field(name="Current Bank Balance", value=f"\U000023e3 {bank_new[0]:,}")

                    return await interaction.response.send_message(embed=embed)  # type: ignore
                return await interaction.response.send_message(embed=ERR_UNREASON)  # type: ignore

            amount_conv = abs(int(actual_amount))
            available_bankspace = details[2] - details[1]
            available_bankspace -= amount_conv

            if available_bankspace < 0:
                return await interaction.response.send_message(  # type: ignore
                    embed=membed(f"You can only hold **\U000023e3 {details[2]:,}** in your bank right now.\n"
                                 f"To hold more, use currency commands and level up more."))

            elif not amount_conv:
                return await interaction.response.send_message(  # type: ignore
                    embed=membed("The amount to deposit needs to be more than 0.")
                )

            elif amount_conv > wallet_amt:
                embed = discord.Embed(colour=0x2F3136,
                                      description=f"- You do not have that much money in your wallet.\n"
                                                  f" - You wanted to deposit \U000023e3 **{amount_conv:,}**.\n"
                                                  f" - Currently, you only have \U000023e3 **{wallet_amt:,}**.")
                return await interaction.response.send_message(embed=embed)  # type: ignore
            else:
                wallet_new = await self.update_bank_new(user, conn, -amount_conv)
                bank_new = await self.update_bank_new(user, conn, +amount_conv, "bank")  # \U000023e3

                embed = discord.Embed(colour=0x2F3136)
                embed.add_field(name="<:deposit:1195657772231036948> Deposited", value=f"\U000023e3 {amount_conv:,}",
                                inline=False)
                embed.add_field(name="Current Wallet Balance", value=f"\U000023e3 {wallet_new[0]:,}")
                embed.add_field(name="Current Bank Balance", value=f"\U000023e3 {bank_new[0]:,}")

                return await interaction.response.send_message(embed=embed)  # type: ignore

    @app_commands.command(name='leaderboard', description='rank users based on various stats.')
    @app_commands.guilds(discord.Object(id=829053898333225010), discord.Object(id=780397076273954886))
    @app_commands.checks.cooldown(1, 6)
    @app_commands.describe(stat="the stat you want to see")
    async def get_leaderboard(self, interaction: discord.Interaction,
                              stat: Literal[
                                  "Bank + Wallet", "Wallet", "Bank", "Inventory Net", "Bounty", "Commands", "Level"]):
        """View the leaderboard and filter the results based on different stats inputted."""

        await interaction.response.send_message(  # type: ignore
            content="Crunching the latest data just for you, give us a mo'..")
        lb_view = Leaderboard(self.client, stat, channel_id=interaction.channel.id)
        lb_view.message = await interaction.original_response()

        if not active_sessions.setdefault(interaction.channel.id, None):
            active_sessions.update({interaction.channel.id: 1})
        else:
            return await lb_view.message.edit(  # type: ignore
                content=None, embed=membed("This command is still active in this channel."))

        lb = await self.create_leaderboard_preset(chosen_choice=stat)
        await lb_view.message.edit(content=None, embed=lb, view=lb_view)  # type: ignore

    @commands.guild_only()
    @commands.cooldown(1, 5)
    @commands.command(name='extend_profile', description='display misc info on a user.',
                      aliases=('e_p', 'ep', 'extend'))
    async def extend_profile(self, ctx: commands.Context, username: Optional[discord.Member]):
        """Display prescence information on a given user."""

        async with ctx.typing():
            user_stats = {}
            username = username or ctx.author

            username = ctx.guild.get_member(username.id)

            user_stats["status"] = str(username.status)
            user_stats["is_on_mobile"] = str(username.is_on_mobile())
            user_stats["desktop"] = str(username.desktop_status)
            user_stats["web"] = str(username.web_status)
            user_stats["voice_status"] = str(username.voice)
            user_stats["is_bot"] = str(username.bot)
            user_stats["activity"] = str(username.activity)

            procfile = discord.Embed(title='Profile Summary',
                                     description=f'This mostly displays {username.display_name}\'s '
                                                 f'prescence on Discord.',
                                     colour=0x2F3136)
            procfile.add_field(name=f'{username.display_name}\'s Extended Information',
                               value=f"\U0000279c Top role: {username.top_role.mention}\n"
                                     f"\U0000279c Is a bot: {user_stats['is_bot']}\n"
                                     f"\U0000279c Current Activity: {user_stats['activity']}\n"
                                     f"\U0000279c Status: {user_stats['status']}\n"
                                     f"\U0000279c Desktop Status: {user_stats['desktop']}\n"
                                     f"\U0000279c Web Status: {user_stats['web']}\n"
                                     f"\U0000279c Is on Mobile: {user_stats['is_on_mobile']}\n"
                                     f"\U0000279c Voice State: {user_stats['voice_status'] or 'No voice'}", )
            procfile.set_thumbnail(url=username.display_avatar.url)
            procfile.set_footer(text=f"{discord.utils.utcnow().strftime('%A %d %b %Y, %I:%M%p')}")
            await ctx.send(embed=procfile)

    rob = app_commands.Group(name='rob', description='rob different places or people.',
                             guild_only=True, guild_ids=APP_GUILDS_ID)

    @rob.command(name="user", description="rob robux from another user.", extras={"exp_gained": 1})
    @app_commands.describe(other='the user to rob from')
    @app_commands.checks.cooldown(1, 6)
    async def rob_the_user(self, interaction: discord.Interaction, other: discord.Member):
        """Rob someone else."""
        primary_id = str(interaction.user.id)
        other_id = str(other.id)

        async with self.client.pool_connection.acquire() as conn:  # type: ignore
            conn: asqlite_Connection

            if other_id == primary_id:
                embed = membed('You cannot rob yourself, everyone knows that.')
                return await interaction.response.send_message(embed=embed)  # type: ignore
            elif other.bot:
                embed = membed('You are not allowed to steal from bots, back off my kind')
                return await interaction.response.send_message(embed=embed)  # type: ignore
            elif other_id == "992152414566232139":
                embed = membed('You are not allowed to rob the developer of this bot.')
                return await interaction.response.send_message(embed=embed)  # type: ignore
            elif not (await self.can_call_out_either(interaction.user, other, conn)):
                embed = membed(f'- Either you or {other.name} does not have an account.\n'
                               f' - </balance:1179817617435926686> to register.')
                return await interaction.response.send_message(embed=embed)  # type: ignore
            else:
                prim_d = await conn.execute("SELECT wallet, job, bounty from `bank` WHERE userID = ?",
                                            (interaction.user.id,))
                prim_d = await prim_d.fetchone()
                host_d = await conn.execute("SELECT wallet, job from `bank` WHERE userID = ?", (other.id,))
                host_d = await host_d.fetchone()

                result = choices([0, 1], weights=(29, 71), k=1)

                if (prim_d[1] == "Police") or (host_d[1] == "Police"):
                    return await interaction.response.send_message(  # type: ignore
                        embed=membed("Either the host is a police officer and/or you are working as one.\n"
                                     "In any case, you would risk losing your bounty and your job."))

                if not result[0]:
                    fine = randint(1, prim_d[0])
                    prcf = round((fine / prim_d[0]) * 100, ndigits=1)
                    conte = (f'- You were caught stealing now you paid {other.name} \U000023e3 **{fine:,}**.\n'
                             f'- **{prcf}**% of your money was handed over to the victim.')

                    b = prim_d[-1]
                    if b:
                        fine += b
                        conte += (f"\n- **You're on the bounty board!** {other.mention} handed you over to the police "
                                  f"and your bounty of **\U000023e3 {b:,}** was given to them.")

                    await self.update_bank_new(interaction.user, conn, -fine)
                    await self.update_bank_new(other, conn, +fine)
                    return await interaction.response.send_message(embed=membed(conte))  # type: ignore
                else:
                    steal_amount = randint(1, host_d[0])
                    await self.update_bank_new(interaction.user, conn, +steal_amount)
                    await self.update_bank_new(other, conn, -steal_amount)

                    prcf = round((steal_amount / host_d[0]) * 100, ndigits=1)

                    return await interaction.response.send_message(  # type: ignore
                        embed=membed(f"You managed to steal \U000023e3 **{steal_amount:,}** from {other.name}.\n"
                                     f"You took a dandy **{prcf}**% of {other.name}."),
                        delete_after=10.0)

    @rob.command(name='casino', description='rob a casino vault.', extras={"exp_gained": 10})
    async def rob_the_casino(self, interaction: discord.Interaction):
        """This a subcommand. Rob the buil"""

        await interaction.response.defer()  # type: ignore

        async with self.client.pool_connection.acquire() as conn:  # type: ignore
            conn: asqlite_Connection

            if await self.can_call_out(interaction.user, conn):
                return await interaction.followup.send(embed=self.not_registered)

            cooldown = await self.fetch_cooldown(conn, user=interaction.user, cooldown_type="casino")

            if await self.get_job_data_only(interaction.user, conn) == "Police":
                return await interaction.followup.send(  # type: ignore
                    embed=membed("You cannot rob the casino as a police officer.")
                )

            if cooldown is not None:
                if cooldown[0] in {"0", 0}:
                    channel = interaction.channel
                    ranint = randint(1000, 1999)
                    await channel.send(
                        embed=membed(f'A 4-digit PIN is required to enter the casino.\n'
                                     f'Here are the first 3 digits: {str(ranint)[:3]}'))

                    def check(m):
                        """Requirements that the client has to wait for."""
                        return m.content == f'{str(ranint)}' and m.channel == channel and m.author == interaction.user

                    try:
                        await self.client.wait_for('message', check=check, timeout=30.0)
                    except asyncTE:
                        await interaction.followup.send(
                            embed=membed(f"Too many seconds passed. Access denied. (The code was {ranint})"))
                    else:
                        msg = await interaction.followup.send(
                            embed=membed('You cracked the code and got access. Good luck escaping unscathed.'),
                            wait=True)
                        hp = 100
                        messages = await channel.send(
                            embed=membed("Passing through security forces.. (HP: 100/100)"),
                            reference=msg.to_reference(fail_if_not_exists=False))
                        hp -= randint(16, 40)
                        await sleep(0.9)
                        await messages.edit(embed=membed(f"Disabling security on security floor.. (HP {hp}/100)"))
                        hp -= randint(15, 59)
                        await sleep(0.9)
                        await messages.edit(embed=membed(f"Entering the vault.. (HP {hp}/100)"))
                        hp -= randint(1, 25)
                        await sleep(1.5)
                        if hp <= 5:
                            await self.update_bank_new(interaction.user, conn, )
                            timeout = randint(5, 12)
                            await messages.edit(
                                embed=membed(f"## <:rwarning:1165960059260518451> Critical HP Reached.\n"
                                             f"- Your items and robux will not be lost.\n"
                                             f"- Police forces were alerted and escorted you out of the building.\n"
                                             f"- You may not enter the casino for another **{timeout}** hours."))
                            ncd = datetime.datetime.now() + datetime.timedelta(hours=timeout)
                            ncd = datetime_to_string(ncd)
                            await self.update_cooldown(conn, user=interaction.user, cooldown_type="casino", new_cd=ncd)
                        else:
                            recuperate_amt = randint(6, 21)
                            total, extra = 0, 0
                            pmulti = await self.get_pmulti_data_only(interaction.user, conn)
                            new_multi = SERVER_MULTIPLIERS.setdefault(interaction.guild.id, 0) + pmulti[0]

                            for _ in range(recuperate_amt):
                                fill_by = randint(212999999, 286999999)
                                total += fill_by
                                extra += floor(((new_multi / 100) * fill_by))
                                await messages.edit(
                                    embed=membed(f"> \U0001f4b0 **{interaction.user.name}'s "
                                                 f"Duffel Bag**: {total:,} / 3,000,000,000\n"
                                                 f"> {PREMIUM_CURRENCY} **Bonus**: {extra:,} / 5,000,000,0000"))
                                await sleep(0.9)

                            overall = total + extra
                            wllt = await self.update_bank_new(interaction.user, conn, +overall)

                            timeout = randint(18, 24)
                            ncd = datetime.datetime.now() + datetime.timedelta(hours=timeout)
                            ncd = datetime_to_string(ncd)
                            await self.update_cooldown(conn, user=interaction.user, cooldown_type="casino", new_cd=ncd)
                            bounty = randint(12500000, 105_000_000)
                            nb = await self.update_bank_new(interaction.user, conn, +bounty, "bounty")
                            await messages.edit(
                                content=f"Your bounty has increased by \U000023e3 "
                                        f"**{bounty:,}**, to \U000023e3 **{nb[0]:,}**!",
                                embed=membed(f"> \U0001f4b0 **{interaction.user.name}'s "
                                             f"Duffel Bag**: \U000023e3 {total:,} / \U000023e3 10,000,000,000\n"
                                             f"> {PREMIUM_CURRENCY} **Bonus**: \U000023e3 {extra:,} "
                                             f"/ \U000023e3 50,000,000,0000\n"
                                             f"> [\U0001f4b0 + {PREMIUM_CURRENCY}] **Total**: \U000023e3 **{overall:,}"
                                             f"**\n\nYou escaped without a scratch.\n"
                                             f"Your new `wallet` balance is \U000023e3 {wllt[0]:,}"))
                else:
                    cooldown = string_to_datetime(cooldown[0])
                    now = datetime.datetime.now()
                    diff = cooldown - now

                    if diff.total_seconds() <= 0:
                        await self.update_cooldown(conn, user=interaction.user, cooldown_type="casino",
                                                   new_cd="0")
                        await interaction.followup.send(
                            embed=membed("The casino is now ready for use.\n"
                                         "Call this command again to start a robbery."))
                    else:
                        minutes, seconds = divmod(diff.total_seconds(), 60)
                        hours, minutes = divmod(minutes, 60)
                        days, hours = divmod(hours, 24)
                        await interaction.followup.send(f"# Not yet.\n"
                                                        f"The casino is not ready. It will be available for "
                                                        f"you in **{int(hours)}** hours, **{int(minutes)}** minutes "
                                                        f"and **{int(seconds)}** seconds.")

    @app_commands.command(name='coinflip', description='bet your robux on a coin flip.', extras={"exp_gained": 3})
    @app_commands.guilds(discord.Object(id=829053898333225010), discord.Object(id=780397076273954886))
    @app_commands.describe(bet_on='what side of the coin you bet it will flip on',
                           amount='the amount of robux to bet. Supports Shortcuts (exponents only)')
    @app_commands.checks.cooldown(1, 6)
    @app_commands.rename(bet_on='side', amount='robux')
    async def coinflip(self, interaction: discord.Interaction, bet_on: str, amount: int):
        """Flip a coin and make a bet on what side of the coin it flips to."""

        user = interaction.user

        async with self.client.pool_connection.acquire() as conn:  # type: ignore

            amount = determine_exponent(str(amount))

            bet_on = "heads" if "h" in bet_on.lower() else "tails"
            if not 5000 <= amount <= 100_000_000:
                return await interaction.response.send_message(  # type: ignore
                    embed=membed(f"*As per-policy*, the minimum bet is {CURRENCY}**5,000**, the maximum is "
                                 f"{CURRENCY}**200,000,000**."))

            conn: asqlite_Connection
            if await self.can_call_out(interaction.user, conn):
                return await interaction.response.send_message(embed=self.not_registered)  # type: ignore
            wallet_amt = await self.get_wallet_data_only(user, conn)
            if wallet_amt < amount:
                return await interaction.response.send_message(embed=ERR_UNREASON)  # type: ignore

            coin = ["heads", "tails"]
            result = choice(coin)

            if result != bet_on:
                await self.update_bank_new(user, conn, -amount)
                return await interaction.response.send_message(  # type: ignore
                    embed=membed(f"You got {result}, meaning you lost \U000023e3 **{amount:,}**."))

            await self.update_bank_new(user, conn, +amount)
            return await interaction.response.send_message(  # type: ignore
                embed=membed(f"You got {result}, meaning you won \U000023e3 " 
                             f"**{amount:,}**."))

    @app_commands.command(name="blackjack",
                          description="test your skills at blackjack.", extras={"exp_gained": 3})
    @app_commands.guilds(discord.Object(id=829053898333225010), discord.Object(id=780397076273954886))
    @app_commands.checks.cooldown(1, 6)
    @app_commands.rename(bet_amount='robux')
    @app_commands.describe(bet_amount='the amount of robux to bet on. Supports Shortcuts (max, all, exponents).')
    async def play_blackjack(self, interaction: discord.Interaction, bet_amount: str):
        """Play a round of blackjack with the bot. Win by reaching 21 or a score higher than the bot without busting."""

        # ------ Check the user is registered or already has an ongoing game ---------
        if len(self.client.games) >= 2:  # type: ignore
            return await interaction.response.send_message(  # type: ignore
                embed=membed(
                    "- The maximum consecutive blackjack games being held has been reached.\n"
                    "- To prevent server overload, you cannot start a game until the current games "
                    "being played has been finished.\n"
                    " - The maximum consecutive blackjack game quota has been set to `2`."
                )
            )

        if self.client.games.setdefault(interaction.user.id, None) is not None:  # type: ignore
            return await interaction.response.send_message(  # type: ignore
                "You already have an ongoing game taking place.")

        async with self.client.pool_connection.acquire() as conn:  # type: ignore
            conn: asqlite_Connection
            if await self.can_call_out(interaction.user, conn):
                return await interaction.response.send_message(embed=self.not_registered)  # type: ignore

        # ----------------- Game setup ---------------------------------

        deck = [2, 3, 4, 5, 6, 7, 8, 9, 10, 10, 10, 10] * 4
        shuffle(deck)

        player_hand = [deck.pop(), deck.pop()]
        dealer_hand = [deck.pop(), deck.pop()]

        keycard_amt = await self.get_one_inv_data_new(interaction.user, "Keycard", conn)
        wallet_amt = await self.get_wallet_data_only(interaction.user, conn)
        pmulti = await self.get_pmulti_data_only(interaction.user, conn)
        has_keycard = keycard_amt >= 1
        # ----------- Check what the bet amount is, converting where necessary -----------

        expo = determine_exponent(bet_amount)

        try:
            assert isinstance(expo, int)
            namount = expo
        except AssertionError:
            if bet_amount.lower() in {'max', 'all'}:
                if has_keycard:
                    namount = min(100_000_000, wallet_amt)
                else:
                    namount = min(50_000_000, wallet_amt)
            else:
                return await interaction.response.send_message(embed=ERR_UNREASON)  # type: ignore

        # -------------------- Check to see if user has sufficient balance --------------------------

        if has_keycard:
            if not (500_000 <= namount <= 100_000_000):
                return await interaction.response.send_message(  # type: ignore
                    embed=discord.Embed(colour=0x2F3136, description=(
                        f'## You did not meet the blackjack criteria.\n'
                        f'- You wanted to bet {CURRENCY}**{namount:,}**\n'
                        f' - A minimum bet of {CURRENCY}**500,000** must be made\n'
                        f' - A maximum bet of {CURRENCY}**100,000,000** can only be made.'
                    )))  # type: ignore
            elif namount > wallet_amt:
                return await interaction.response.send_message(  # type: ignore
                    embed=discord.Embed(colour=0x2F3136, description=(
                        f'Cannot perform this action.\n'
                        f'You only have {CURRENCY}**{wallet_amt:,}**.\n'
                        f'You\'ll need {CURRENCY}**{namount - wallet_amt:,}** more in your wallet first.'
                    )))  # type: ignore
        else:
            if not (1000000 <= namount <= 50_000_000):
                return await interaction.response.send_message(  # type: ignore
                    embed=discord.Embed(colour=0x2F3136, description=(
                        f'## You did not meet the blackjack criteria.\n'
                        f'- You wanted to bet {CURRENCY}**{namount:,}**\n'
                        f' - A minimum bet of {CURRENCY}**1,000,000** must be made.\n'
                        f' - A maximum bet of {CURRENCY}**50,000,000** can only be made.'
                    )))  # type: ignore
            elif namount > wallet_amt:
                return await interaction.response.send_message(  # type: ignore
                    embed=discord.Embed(colour=0x2F3136, description=(
                        f"## Cannot perform this action.\n"
                        f"You only have {CURRENCY}**{wallet_amt:,}**.\n"
                        f"You'll need {CURRENCY}**{namount - wallet_amt:,}** more in your wallet first."
                    )))  # type: ignore

        # ------------ In the case where the user already won --------------
        if self.calculate_hand(player_hand) == 21:
            bj_lose = await conn.execute('SELECT bjl FROM bank WHERE userID = ?', (interaction.user.id,))
            bj_lose = await bj_lose.fetchone()
            new_bj_win = await self.update_bank_new(interaction.user, conn, 1, "bjw")
            new_total = new_bj_win[0] + bj_lose[0]
            prctnw = round((new_bj_win[0] / new_total) * 100)

            new_multi = SERVER_MULTIPLIERS.setdefault(interaction.guild.id, 0) + pmulti[0]
            amount_after_multi = floor(((new_multi / 100) * namount) + namount) + randint(1, 999)
            await self.update_bank_new(interaction.user, conn, amount_after_multi, "bjwa")
            new_amount_balance = await self.update_bank_new(interaction.user, conn, amount_after_multi)
            d_fver_p = display_user_friendly_deck_format(player_hand)
            d_fver_d = display_user_friendly_deck_format(dealer_hand)

            embed = discord.Embed(colour=discord.Colour.brand_green(),
                                  description=(
                                      f"**Blackjack! You've already won with a total of {sum(player_hand)}!**\n\n"
                                      f"You won {CURRENCY}**{amount_after_multi:,}**. "
                                      f"You now have {CURRENCY}**{new_amount_balance[0]:,}**.\n"
                                      f"You won {prctnw}% of the games."))
            embed.add_field(name=f"{interaction.user.name} (Player)",
                            value=f"**Cards** - {' '.join(d_fver_p)}\n"
                                  f"**Total** - `{sum(player_hand)}`")
            embed.add_field(name=f"{interaction.guild.me.name} (Dealer)",
                            value=f"**Cards** - {' '.join(d_fver_d)}\n"
                                  f"**Total** - {sum(dealer_hand)}")
            return await interaction.response.send_message(embed=embed)  # type: ignore

        shallow_pv = []
        shallow_dv = []

        for number in player_hand:
            remade = display_user_friendly_card_format(number)
            shallow_pv.append(remade)

        for number in dealer_hand:
            remade = display_user_friendly_card_format(number)
            shallow_dv.append(remade)

        self.client.games[interaction.user.id] = (deck, player_hand, dealer_hand,  # type: ignore
                                                  shallow_dv, shallow_pv, namount)

        start = discord.Embed(colour=0x2B2D31,
                              description=f"The game has started. May the best win.\n"
                                          f"`\U000023e3 ~{format_number_short(namount)}` is up for grabs on the table.")

        start.add_field(name=f"{interaction.user.name} (Player)",
                        value=f"**Cards** - {' '.join(shallow_pv)}\n"
                              f"**Total** - `{sum(player_hand)}`")
        start.add_field(name=f"{interaction.guild.me.name} (Dealer)",
                        value=f"**Cards** - {shallow_dv[0]} `?`\n"
                              f"**Total** - ` ? `")
        start.set_author(icon_url=interaction.user.display_avatar.url, name=f"{interaction.user.name}'s blackjack game")
        start.set_footer(text="K, Q, J = 10  |  A = 1 or 11")
        my_view = BlackjackUi(interaction, self.client)
        await interaction.response.send_message(  # type: ignore
            content="What do you want to do?\nPress **Hit** to to request an additional card, **Stand** to finalize "
                    "your deck or **Forfeit** to end your hand prematurely, sacrificing half of your original bet.",
            embed=start, view=my_view)
        my_view.message = await interaction.original_response()

        await self.raise_pmulti_warning(interaction, pmulti[0])

    @app_commands.command(name="bet",
                          description="bet your robux on a dice roll.", extras={"exp_gained": 3})
    @app_commands.guilds(discord.Object(id=829053898333225010), discord.Object(id=780397076273954886))
    @app_commands.checks.cooldown(1, 6)
    @app_commands.rename(exponent_amount='robux')
    @app_commands.describe(exponent_amount='the amount of robux to bet. Supports Shortcuts (max, all, exponents).')
    async def bet(self, interaction: discord.Interaction, exponent_amount: str):
        """Bet your robux on a gamble to win or lose robux."""

        # --------------- Contains checks before betting i.e. has keycard, meets bet constraints. -------------
        async with self.client.pool_connection.acquire() as conn:  # type: ignore
            if await self.can_call_out(interaction.user, conn):
                return await interaction.response.send_message(embed=self.not_registered)  # type: ignore
            conn: asqlite_Connection

            data = await conn.execute(f"SELECT pmulti, wallet, betw, betl FROM `{BANK_TABLE_NAME}` WHERE userID = ?",
                                      (interaction.user.id,))
            data = await data.fetchone()
            pmulti, wallet_amt = data[0], data[1]
            has_keycard = await self.get_one_inv_data_new(interaction.user, "Keycard", conn) >= 1
            expo = determine_exponent(exponent_amount)

            try:
                assert isinstance(expo, int)
                amount = expo
            except AssertionError:
                if exponent_amount.lower() in {'max', 'all'}:
                    if has_keycard:
                        amount = min(100_000_000, wallet_amt)
                    else:
                        amount = min(50_000_000, wallet_amt)
                else:
                    return await interaction.response.send_message(embed=ERR_UNREASON)  # type: ignore

            if has_keycard:
                if (amount > 100000000) or (amount < 100000):
                    err = discord.Embed(colour=0x2F3136, description=f'## You did not meet the bet criteria:\n'
                                                                     f'- You wanted to bet {CURRENCY}**{amount:,}**\n'
                                                                     f' - A minimum bet of {CURRENCY}**100,000** must '
                                                                     f'be made\n'
                                                                     f' - A maximum bet of {CURRENCY}**100,000,000** '
                                                                     f'can only be made.')
                    return await interaction.response.send_message(embed=err)  # type: ignore
                elif amount > wallet_amt:
                    err = discord.Embed(colour=0x2F3136, description=f'Cannot perform this action, '
                                                                     f'you only have {CURRENCY}**{wallet_amt:,}**.\n'
                                                                     f'You\'ll need '
                                                                     f'{CURRENCY}**{amount - wallet_amt:,}**'
                                                                     f' more in your wallet first.')
                    return await interaction.response.send_message(embed=err)  # type: ignore
            else:
                if (amount > 50000000) or (amount < 500000):
                    err = discord.Embed(colour=0x2F3136, description=f'## You did not meet the bet criteria:\n'
                                                                     f'- You wanted to bet {CURRENCY}**{amount:,}**.\n'
                                                                     f' - A minimum bet of {CURRENCY}**500,000** must '
                                                                     f'be made (this can decrease when you acquire a'
                                                                     f' <:lanyard:1165935243140796487> Keycard).\n'
                                                                     f' - A maximum bet of {CURRENCY}**50,000,000** '
                                                                     f'can only be made (this can increase when you '
                                                                     f'acquire a <:lanyard:1165935243140796487> '
                                                                     f'Keycard).')
                    return await interaction.response.send_message(embed=err)  # type: ignore
                elif amount > wallet_amt:
                    err = discord.Embed(colour=0x2F3136, description=f'Cannot perform this action, '
                                                                     f'you only have {CURRENCY}**{wallet_amt:,}**.\n'
                                                                     f'You\'ll need '
                                                                     f'{CURRENCY}**{amount - wallet_amt:,}**'
                                                                     f' more in your wallet first.')
                    return await interaction.response.send_message(embed=err)  # type: ignore

            # --------------------------------------------------------
            smulti = SERVER_MULTIPLIERS.setdefault(interaction.guild.id, 0) + pmulti
            badges = set()
            id_won_amount, id_lose_amount = data[2], data[3]
            if pmulti > 0:
                badges.add(PREMIUM_CURRENCY)
            if has_keycard:
                badges.add("<:lanyard:1165935243140796487>")
                your_choice = choices([1, 2, 3, 4, 5, 6], weights=[37 / 3, 37 / 3, 37 / 3, 63 / 3, 63 / 3, 63 / 3], k=1)
                bot_choice = choices([1, 2, 3, 4, 5, 6],
                                     weights=[65 / 4, 65 / 4, 65 / 4, 65 / 4, 35 / 2, 35 / 2], k=1)
            else:
                bot_choice = choices([1, 2, 3, 4, 5, 6],
                                     weights=[10, 10, 15, 27, 15, 23], k=1)
                your_choice = choices([1, 2, 3, 4, 5, 6], weights=[55 / 3, 55 / 3, 55 / 3, 45 / 3, 45 / 3, 45 / 3], k=1)

            if your_choice[0] > bot_choice[0]:

                amount_after_multi = floor(((smulti / 100) * amount) + amount)
                updated = await self.update_bank_three_new(
                    interaction.user, conn, "betwa", amount_after_multi,
                    "betw", 1, "wallet", amount_after_multi)

                prcntw = round((updated[1] / (id_lose_amount + updated[1])) * 100, 1)

                embed = discord.Embed(
                    description=f"**You've rolled higher!** You won {CURRENCY}**{amount_after_multi:,}** robux.\n"
                                f"Your new `wallet` balance is {CURRENCY}**{updated[2]:,}**.\n"
                                f"You've won {prcntw}% of all games.",
                    colour=discord.Color.brand_green())
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
                prcntl = round((updated[1] / new_total) * 100, 1)

                embed = discord.Embed(description=f"**You've rolled lower!** You lost {CURRENCY}**{amount:,}**.\n"
                                                  f"Your new balance is {CURRENCY}**{updated[2]:,}**.\n"
                                                  f"You've lost {prcntl}% of all games.",
                                      colour=discord.Color.brand_red())
                embed.set_author(name=f"{interaction.user.name}'s losing gambling game",
                                 icon_url=interaction.user.display_avatar.url)

            embed.add_field(name=interaction.user.name, value=f"Rolled `{your_choice[0]}` {''.join(badges)}")
            embed.add_field(name=self.client.user.name, value=f"Rolled `{bot_choice[0]}`")
            await interaction.response.send_message(embed=embed)  # type: ignore

            await self.raise_pmulti_warning(interaction, pmulti)

    @play_blackjack.autocomplete('bet_amount')
    @bet.autocomplete('exponent_amount')
    @deposit.autocomplete('robux')
    @withdraw.autocomplete('robux')
    async def callback_max_100(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        """Autocomplete callback for when the maximum accepted bet value is 100 million."""

        chosen = {"all", "max", "50e6", "100e6"}
        return [
            app_commands.Choice(name=str(the_chose), value=str(the_chose))
            for the_chose in chosen if current.lower() in the_chose
        ]

    @slots.autocomplete('amount')
    @highlow.autocomplete('robux')
    async def callback_max_75(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        """Autocomplete callback for when the maximum accepted bet value is 75 million."""
        chosen = {"all", "max", "50e6", "75e6"}
        return [
            app_commands.Choice(name=str(the_chose), value=str(the_chose))
            for the_chose in chosen if current.lower() in the_chose
        ]


async def setup(client: commands.Bot):
    """Setup function to initiate the cog."""
    await client.add_cog(Economy(client))
