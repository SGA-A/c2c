
from sqlite3 import Row, IntegrityError
from math import floor, ceil
from re import search
from textwrap import dedent
from string import ascii_letters, digits
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from random import (
    choice, 
    choices, 
    randint, 
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
from asqlite import Connection


from .core.bot import C2C
from .core.paginators import PaginationItem, RefreshPagination
from .core.errors import CustomTransformerError, FailingConditionalError
from .core.transformers import RawIntegerTransformer
from .core.constants import CURRENCY
from .core.helpers import (
    BaseInteractionView,
    economy_check,
    membed,
    respond,
    process_confirmation,
    declare_transaction,
    end_transaction,
    is_setting_enabled,
    handle_confirm_outcome
)


USER_ENTRY = discord.Member | discord.User
POSSIBLE_INTEGER_SHORTHAND = int | str
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


def swap_elements(x, index1, index2) -> None:
    """Swap two elements in place given their indices, return None.
    
    lst: the list to swap elements in
    index1: the index of the element you want to swap
    index2: the index of the element you want to swap it with
    """

    x[index1], x[index2] = x[index2], x[index1]


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


def add_multi_to_original(multi: int, original: int) -> int:
    return int(((multi / 100) * original) + original)


def format_multiplier(multiplier):
    """Formats a multiplier for a more readable display."""
    description = f"` {multiplier[0]} ` \U00002014 {multiplier[1]}"
    if multiplier[2]:
        expiry_time = datetime.fromtimestamp(multiplier[2], tz=timezone.utc)
        expiry_time = discord.utils.format_dt(expiry_time, style="R")
        description = f"{description} (expires {expiry_time})"
    return description


def selling_price_algo(base_price: int, multiplier: int) -> int:
    """Calculate the selling price of an item based on its rarity and base price."""
    return round(int(base_price * (1+multiplier/100)), -2)


def calculate_hand(hand: list) -> int:
    """Calculate the value of a hand in a blackjack game, accounting for possible aces."""

    aces = hand.count(11)
    total = sum(hand)

    while total > 21 and aces:
        total -= 10
        aces -= 1

    return total


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


async def add_command_usage(user_id: int, command_name: str, conn) -> int:
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


async def total_commands_used_by_user(user_id: int, conn: Connection) -> int:
    """
    Select all records for the given user_id and sum up the command_count.

    This will always return a value.
    """

    total, = await conn.fetchone(
        """
        SELECT CAST(TOTAL(cmd_count) AS INTEGER) 
        FROM command_uses
        WHERE userID = $0
        """, user_id
    )

    return total


async def find_fav_cmd_for(user_id, conn: Connection) -> str:
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


@tasks.loop()
async def drop_expired(interaction: discord.Interaction) -> None:
    """Drop expired multipliers from the database."""
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
        drop_expired.cancel()
        return

    row_id, expiry = next_task
    timestamp = datetime.fromtimestamp(expiry, tz=timezone.utc)
    await discord.utils.sleep_until(timestamp)

    async with interaction.client.pool.acquire() as conn, conn.transaction():
        await conn.execute("DELETE FROM multipliers WHERE rowid = $0", row_id)


def start_drop_expired(interaction: discord.Interaction) -> None:
    if drop_expired.is_running():
        drop_expired.restart(interaction)
    else:
        drop_expired.start(interaction)


class MatchView(BaseInteractionView):
    def __init__(self, interaction: discord.Interaction, /) -> None:
        self.chosen_item = 0
        super().__init__(interaction)


class ItemInputTransformer(app_commands.Transformer):
    """Transforms an item name into a row containing the item's ID, name, and emoji."""
    ITEM_NOT_FOUND = "No items found with that name pattern."
    TIMED_OUT = "Timed out waiting for a response."

    async def transform(self, interaction: discord.Interaction, value: str) -> Row:
        async with interaction.client.pool.acquire() as conn:
            res = await conn.fetchall(
                """
                SELECT itemID, itemName, emoji 
                FROM shop 
                WHERE LOWER(itemName) LIKE LOWER($0)
                LIMIT 5
                """, f"%{value}%"
            )

        if not res:
            raise CustomTransformerError(value, self.type, self, self.ITEM_NOT_FOUND)

        if len(res) == 1:
            return res[0]

        match_view = MatchView(interaction)

        for (item_id, item_name, item_emoji) in res:
            match_view.add_item(MatchItem(item_id, item_name, item_emoji))

        prompt_embed = membed(
            "There is more than one item with that name pattern.\n"
            "Select one of the following items:"
        ).set_author(name=f"Search: {value}", icon_url=interaction.user.display_avatar.url)

        await respond(interaction, view=match_view, embed=prompt_embed)

        not_pressed = await match_view.wait()
        if not_pressed:
            raise CustomTransformerError(value, self.type, self, self.TIMED_OUT)
        return match_view.chosen_item


class UserSettings(BaseInteractionView):
    def __init__(
        self, 
        interaction: discord.Interaction,
        /,
        data: list, 
        chosen_setting: str
    ) -> None:
        super().__init__(interaction)

        self.setting_dropdown = SettingsDropdown(data=data, default_setting=chosen_setting)
        self.disable_button = ToggleButton(self.setting_dropdown, label="Disable", style=discord.ButtonStyle.danger, row=1)
        self.enable_button = ToggleButton(self.setting_dropdown, label="Enable", style=discord.ButtonStyle.success, row=1)


class ConfirmResetData(BaseInteractionView):
    def __init__(self, interaction: discord.Interaction, /, to_remove: USER_ENTRY) -> None:
        self.to_remove: USER_ENTRY = to_remove
        self.count = 0
        super().__init__(interaction)

    async def on_timeout(self) -> Coroutine[Any, Any, None]:
        try:
            await self.interaction.delete_original_response()
        except discord.HTTPException:
            pass
        finally:
            async with self.interaction.client.pool.acquire() as conn, conn.transaction():
                await end_transaction(conn, user_id=self.interaction.user.id)

    @discord.ui.button(label='RESET MY DATA', style=discord.ButtonStyle.danger, emoji=discord.PartialEmoji.from_str("<:rooFire:1263923362154156103>"))
    async def confirm_button_reset(self, interaction: discord.Interaction, _: discord.ui.Button):

        self.count += 1
        if self.count < 3:
            return await interaction.response.edit_message(view=self)

        self.stop()
        await self.interaction.delete_original_response()

        async with interaction.client.pool.acquire() as conn, conn.transaction() as tr:
            try:
                await conn.execute("DELETE FROM accounts WHERE userID = $0", self.to_remove.id)
            except Exception as e:
                interaction.client.log_exception(e)
                await tr.rollback()

                return await interaction.response.send_message(
                    embed=membed(
                        "Failed to wipe user data.\n"
                        "Report this to the developers so they can get it fixed."
                    )
                )

        whose = "your" if interaction.user.id == self.to_remove.id else f"{self.to_remove.mention}'s"
        end_note = " Thanks for using the bot." if whose == "your" else ""

        await interaction.response.send_message(
            embed=membed(f"All of {whose} data has been wiped.{end_note}")
        )

    @discord.ui.button(label='CANCEL', style=discord.ButtonStyle.primary)
    async def cancel_button_reset(self, interaction: discord.Interaction, _: discord.ui.Button):
        self.stop()
        await self.interaction.delete_original_response()

        async with interaction.client.pool.acquire() as conn, conn.transaction():
            await end_transaction(conn, user_id=self.to_remove.id)


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

        value = await economy_check(interaction, self.interaction.user.id)
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

    @discord.ui.button(label="Withdraw", row=1)
    async def withdraw_money_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Withdraw money from the bank."""

        async with interaction.client.pool.acquire() as conn:
            bank_amt = await Economy.fetch_account_data(interaction.user.id, "bank", conn)

        if not bank_amt:
            return await interaction.response.send_message(
                embed=membed("You have nothing to withdraw."), 
                ephemeral=True, 
                delete_after=3.0
            )

        await interaction.response.send_modal(
            DepositOrWithdraw(title=button.label, default_val=bank_amt, view=self)
        )

    @discord.ui.button(label="Deposit", row=1)
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


class BlackjackUi(BaseInteractionView):
    """View for the blackjack command and its associated functions."""

    def __init__(self, interaction: discord.Interaction):
        super().__init__(interaction)

    async def on_timeout(self) -> None:
        del self.interaction.client.games[self.interaction.user.id]

        async with self.interaction.client.pool.acquire() as conn, conn.transaction():
            await end_transaction(conn, user_id=self.interaction.user.id)

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

        async with self.interaction.client.pool.acquire() as conn, conn.transaction():
            their_multi = await Economy.get_multi_of(self.interaction.user.id, "robux", conn)
            multiplied = add_multi_to_original(their_multi, bet_amount)
            await end_transaction(conn, user_id=self.interaction.user.id)

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

        prctnw = (new_bj_win / (new_bj_win + bj_lose)) * 100
        return multiplied, new_amount_balance, prctnw, their_multi

    async def update_losing_data(self, *, bet_amount: int) -> tuple:
        """
        Return a tuple containing elements in this order:

        New amount balance, Percentage games lost
        """

        async with self.interaction.client.pool.acquire() as conn, conn.transaction():
            await end_transaction(conn, user_id=self.interaction.user.id)
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

        prnctl = (new_bj_lose / (new_bj_lose + bj_win)) * 100
        return new_amount_balance, prnctl

    @discord.ui.button(label='Hit', style=discord.ButtonStyle.primary)
    async def hit_bj(self, interaction: discord.Interaction, _: discord.ui.Button):
        (
            deck, 
            player_hand, 
            dealer_hand, 
            d_fver_d, 
            d_fver_p, 
            namount
        ) = interaction.client.games[interaction.user.id]

        player_hand.append(deck.pop())
        d_fver_p.append(display_user_friendly_card_format(player_hand[-1]))
        player_sum = calculate_hand(player_hand)

        embed = interaction.message.embeds[0]
        if player_sum > 21:
            self.stop()
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
            ).remove_footer()

            return await interaction.response.edit_message(embed=embed, view=None)

        elif player_sum == 21:
            self.stop()
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

            return await interaction.response.edit_message(embed=embed, view=None)

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
        self.stop()

        (
            deck, 
            player_hand, 
            dealer_hand, 
            d_fver_d, 
            d_fver_p, 
            namount
        ) = interaction.client.games[interaction.user.id]

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
            async with interaction.client.pool.acquire() as conn, conn.transaction():
                await end_transaction(conn, user_id=interaction.user.id)
                wallet_amt = await Economy.fetch_balance(interaction.user.id, conn)
            
            embed.remove_footer()
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
        (
            _, 
            player_hand, 
            dealer_hand, 
            d_fver_d, 
            d_fver_p, 
            namount
        ) = interaction.client.games[interaction.user.id]

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


class HighLow(BaseInteractionView):
    """View for the Highlow command and its associated functions."""

    def __init__(self, interaction: discord.Interaction, bet: int) -> None:
        self.their_bet = bet
        self.true_value = randint(1, 100)
        self.hint_provided = randint(1, 100)
        super().__init__(interaction)

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

    async def on_timeout(self) -> None:
        async with self.interaction.client.pool.acquire() as conn, conn.transaction():
            await end_transaction(conn, user_id=self.interaction.user.id)

        for item in self.children:
            item.disabled = True

        await self.interaction.edit_original_response(
            view=None, 
            embed=membed("The game ended because you didn't answer in time.")
        )

    async def send_win(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.make_clicked_blurple_only(button)
        async with interaction.client.pool.acquire() as conn, conn.transaction():
            new_multi = await Economy.get_multi_of(interaction.user.id, "robux", conn)
            total = add_multi_to_original(new_multi, self.their_bet)
            new_balance = await Economy.update_account(interaction.user.id, total, conn)
            await end_transaction(conn, user_id=self.interaction.user.id)

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
        async with interaction.client.pool.acquire() as conn, conn.transaction():
            new_amount = await Economy.update_account(interaction.user.id, -self.their_bet, conn)
            await end_transaction(conn, user_id=self.interaction.user.id)

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
    def populate_data(bot: C2C, ret: list[Row]) -> list[str]:
        data = []
        offset = 0
        for i, (identifier, metric) in enumerate(ret, start=1):
            memobj = bot.get_user(identifier)
            if memobj is None:
                offset += 1
                continue

            fmt = (
                f"{Leaderboard.podium_pos.get(i-offset, "\U0001f539")} ` {metric:,} ` "
                f"\U00002014 {memobj.name}{UNIQUE_BADGES.get(memobj.id, '')}"
            )
            data.append(fmt)
        return data

    async def create_lb(self, conn: Connection, item_id: int) -> None:
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


@dataclass(slots=True, repr=False)
class ConnectionHolder:
    conn: Connection


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
            em = await Economy.get_setting_embed(interaction, view=self.view, conn=conn)
        await interaction.response.edit_message(embed=em, view=self.view)


class ToggleButton(discord.ui.Button):
    def __init__(self, setting_dropdown: SettingsDropdown, **kwargs) -> None:
        self.setting_dropdown = setting_dropdown
        super().__init__(**kwargs)

    async def callback(self, interaction: discord.Interaction) -> None:
        self.setting_dropdown.current_setting_state = int(not self.setting_dropdown.current_setting_state)

        enabled = self.setting_dropdown.current_setting_state == 1
        em = interaction.message.embeds[0].set_field_at(
            index=0, 
            name="Current", 
            value="<:Enabled:1263921710990622802> Enabled" if enabled else "<:Disabled:1263921453229801544> Disabled"
        )

        self.view.disable_button.disabled = not enabled
        self.view.enable_button.disabled = enabled

        await interaction.response.edit_message(embed=em, view=self.view)

        async with interaction.client.pool.acquire() as conn, conn.transaction():
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
        conn: Connection, 
        new_price: int
    ) -> None:

        await Economy.update_inv_new(interaction.user, true_qty, self.item_name, conn)
        new_am, = await Economy.update_account(interaction.user.id, -new_price, conn)

        success = discord.Embed(
            title="Successful Purchase",
            colour=0xFFFFFF,
            description=(
                f"> You have {CURRENCY} {new_am:,} left.\n\n"
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

    async def calculate_discount_price(
        self, 
        interaction: discord.Interaction, 
        /,
        holder: ConnectionHolder,
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
            """, 12, interaction.user.id
        )

        if not data:
            return current_price

        discounted_price = floor((95/100) * current_price)

        if data[-1]:
            self.activated_coupon = True
            return discounted_price

        await declare_transaction(holder.conn, user_id=interaction.user.id)
        await interaction.client.pool.release(holder.conn)

        value = await process_confirmation(
            interaction, 
            prompt=(
                "Would you like to use your <:shopCoupon:1263923497323855907> "
                "**Shop Coupon** for an additional **5**% off?\n"
                f"(You have **{data[0]:,}** coupons in total)\n\n"
                f"This will bring your total for this purchase to {CURRENCY} "
                f"**{discounted_price:,}** if you decide to use the coupon."
            )
        )

        holder.conn = await interaction.client.pool.acquire()
        await end_transaction(holder.conn, user_id=interaction.user.id)
        await holder.conn.commit()

        if value is None:
            return value

        if value:
            self.activated_coupon = True
            return discounted_price
        return current_price  # if the view timed out or willingly pressed cancel

    # --------------------------------------------------------------------------------------------

    async def on_submit(self, interaction: discord.Interaction):
        true_quantity = RawIntegerTransformer(reject_shorthands=True).transform(interaction, self.quantity.value)

        current_price = self.item_cost * true_quantity
        conn_holder = ConnectionHolder(await interaction.client.pool.acquire())

        new_price = await self.calculate_discount_price(interaction, conn_holder, current_price)

        if new_price is None:
            await interaction.client.pool.release(conn_holder.conn)
            return await respond(
                interaction,
                embed=membed(
                    "You didn't respond in time so your purchase was cancelled."
                )
            )

        current_balance = await Economy.fetch_balance(interaction.user.id, conn_holder.conn)
        if new_price > current_balance:
            await interaction.client.pool.release(conn_holder.conn)
            return await respond(
                interaction,
                embed=membed(f"You don't have enough robux to buy **{true_quantity:,}x {self.ie} {self.item_name}**.")
            )

        await interaction.client.pool.release(conn_holder.conn)
        del conn_holder

        can_proceed = await handle_confirm_outcome(
            interaction, 
            setting="buying_confirmations",
            prompt=(
                f"Are you sure you want to buy **{true_quantity:,}x {self.ie} "
                f"{self.item_name}** for **{CURRENCY} {new_price:,}**?"
            )
        )

        async with interaction.client.pool.acquire() as conn, conn.transaction():
            if can_proceed is not None:
                await end_transaction(conn, user_id=interaction.user.id)
                if can_proceed is False:
                    return

            await self.begin_purchase(interaction, true_quantity, conn, new_price)


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
        val = RawIntegerTransformer().transform(interaction, self.amount.value)
        
        if isinstance(val, str):
            val = self.their_default
        elif val > self.their_default:
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
        async with interaction.client.pool.acquire() as conn, conn.transaction():
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


class Economy(commands.Cog):
    """Advanced economy system to simulate a real world economy, available for everyone."""
    ITEM_CONVERTER = app_commands.Transform[Row, ItemInputTransformer]
    ROBUX_CONVERTER = app_commands.Transform[int | str, RawIntegerTransformer]

    def __init__(self, bot: C2C) -> None:
        self.bot = bot

        self.not_registered = membed(
            "## <:notFound:1263922668823122075> You are not registered.\n"
            "You'll need to register first before you can use this command.\n"
            "### Already Registered?\n"
            "Find out what could've happened by calling "
            "[`@me reasons`](https://www.google.com/)."
        )

    async def interaction_check(self, interaction: discord.Interaction):
        async with self.bot.pool.acquire() as conn:
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
    def calculate_exp_for(*, level: int) -> int:
        """Calculate the experience points required for a given level."""
        return ceil((level/0.3)**1.3)

    @staticmethod
    async def get_setting_embed(
        interaction: discord.Interaction, 
        /,
        view: UserSettings, 
        conn: Connection
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

    @staticmethod
    async def calculate_inventory_value(user: USER_ENTRY, conn: Connection) -> int:
        """A reusable funtion to calculate the net value of a user's inventory"""

        res, = await conn.fetchone(
            """
            SELECT COALESCE(SUM(shop.cost * inventory.qty), 0) AS NetValue
            FROM shop
            LEFT JOIN inventory 
                ON shop.itemID = inventory.itemID AND inventory.userID = $0
            """, user.id
        )

        return res

    # ------------------ BANK FUNCS ------------------ #

    @staticmethod
    async def calculate_net_ranking_for(user: USER_ENTRY, conn: Connection) -> int:
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
        val, = val or ("Unlisted",)
        return val

    @staticmethod
    async def open_bank_new(user: USER_ENTRY, conn_input: Connection) -> None:
        ranumber = randint(10_000_000, 20_000_000)
        query = "INSERT INTO accounts (userID, wallet) VALUES ($0, $1)"
        await conn_input.execute(query, user.id, ranumber)

    @staticmethod
    async def can_call_out(user: USER_ENTRY, conn_input: Connection) -> bool:
        """
        Check if the user is NOT in the database and therefore not registered (evaluates True if not in db).

        Example usage:
        if await self.can_call_out(interaction.user, conn):
            await interaction.response.send_message(embed=self.not_registered)

        This is what should be done all the time to check if a user IS NOT REGISTERED.
        """

        has_account_column, = await conn_input.fetchone(
            "SELECT EXISTS (SELECT 1 FROM accounts WHERE userID = $0)", 
            user.id
        )
        return not has_account_column

    @staticmethod
    async def can_call_out_either(user1: USER_ENTRY, user2: USER_ENTRY, conn_input: Connection) -> bool:
        """
        Check if both users are in the database. (evaluates True if both users are in db.)
        Example usage:

        if not(await self.can_call_out_either(interaction.user, username, conn)):
            do something

        This is what should be done all the time to check if both users are not registereed.
        """

        rows_present, = await conn_input.fetchone(
            """
            SELECT COUNT(*) 
            FROM accounts 
            WHERE userID IN (?, ?)
            """, (user1.id, user2.id)
        )

        return rows_present == 2

    @staticmethod
    async def fetch_balance(user_id: int, /, conn: Connection, mode: str = "wallet") -> int:
        """Shorthand to get balance data of a user."""
        return await Economy.fetch_account_data(user_id, mode, 0, conn)

    @staticmethod
    async def fetch_account_data(user_id: int, field_name: str, default: Any, conn: Connection) -> Any:
        """Retrieves a specific field name only from the accounts table."""
        query = f"SELECT {field_name} FROM accounts WHERE userID = $0"
        data, = await conn.fetchone(query, user_id) or (default,)
        return data

    @staticmethod
    async def update_account(
        user_id: int, 
        amount: float | int, 
        conn: Connection,
        mode: str = "wallet"
    ) -> Any:
        """Update miscellaneous account data."""
        query = f"UPDATE accounts SET {mode} = {mode} + $0 WHERE userID = $1 RETURNING {mode}"

        return await conn.fetchone(query, amount, user_id)

    @staticmethod
    async def update_fields(
        user_id: int, 
        conn: Connection, 
        table_name: str = "accounts",
        **kwargs: float | int
    ) -> Any | None:
        """
        Modifies any number of fields at once by their respective amounts. 
        
        Returns the values of the updated fields.

        All fields passed in must be of type `int` or `float`.
        """

        if not kwargs:
            raise ValueError("At least one field must be provided to update.")

        set_clause = ", ".join(f"{field} = {field} + ?" for field in kwargs.keys())
        values = tuple(kwargs.values()) + (user_id,)

        query = (
            f"""
            UPDATE `{table_name}` 
            SET {set_clause} 
            WHERE userID = ? 
            RETURNING {', '.join(kwargs.keys())}
            """
        )

        return await conn.fetchone(query, values)

    @staticmethod
    async def update_wallet_many(conn: Connection, *params_users) -> list[Row]:
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

        await conn.executemany(query, params_users)

    # ------------------ INVENTORY FUNCS ------------------ #

    @staticmethod
    async def fetch_item_qty_from_id(user_id: int, item_id: int, conn: Connection) -> bool:
        """Fetch the quantity of an item owned by a user based via it's ID."""
        query = "SELECT qty FROM inventory WHERE userID = ? AND itemID = ?"
        val, = await conn.fetchone(query, (user_id, item_id)) or (0,)
        return val

    @staticmethod
    async def user_has_item_from_name(user_id: int, item_name: str, conn: Connection) -> bool:
        """Fetch the quantity of an item owned by a user based via it's name."""
        query = (
            """
            SELECT qty
            FROM inventory
            INNER JOIN shop 
                ON inventory.itemID = shop.itemID
            WHERE inventory.userID = ? AND shop.itemName = ?
            """
        )

        result, = await conn.fetchone(query, (user_id, item_name)) or (0,)
        return result

    @staticmethod
    async def update_inv_new(
        user: USER_ENTRY, 
        amount: float | int, 
        item_name: str, 
        conn: Connection
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
        conn: Connection
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
    async def update_user_inventory_with_random_item(user_id: int, conn: Connection, qty: int) -> tuple:
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

    # ------------ cooldowns ----------------

    @staticmethod
    def has_cd(cd_timestamp: float) -> None | datetime:
        """Check if a cooldown has expired. Returns when it will expire if not already."""
        current_time = discord.utils.utcnow().timestamp()
        if current_time > cd_timestamp:
            return
        return datetime.fromtimestamp(cd_timestamp)

    @staticmethod
    async def update_cooldown(conn: Connection, user_id: int, cooldown_type: str, new_cd: str) -> None:
        """Update a user's cooldown.

        Raises `sqlite3.IntegrityError` when foreign userID constraint fails.
        """

        await conn.execute(
            """
            INSERT INTO cooldowns (userID, cooldown, until)
            VALUES ($0, $1, $2)
            ON CONFLICT(userID, cooldown) DO UPDATE SET until = $2
            """, user_id, cooldown_type, new_cd
        )

    # -----------------------------------------

    @staticmethod
    async def add_multiplier(
        conn: Connection, *, 
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
    async def remove_multiplier_from_cause(conn: Connection, *, user_id: int, cause: str) -> None:
        """Remove a multiplier from a user based on the cause."""

        await conn.execute('DELETE FROM multipliers WHERE userID = $0 AND cause = $1', user_id, cause)

    @staticmethod
    async def get_multi_of(user_id: int, multi_type: MULTIPLIER_TYPES, conn: Connection) -> int:
        """Get the amount of a multiplier of a specific type for a user."""

        multiplier, = await conn.fetchone(
            """
            SELECT CAST(TOTAL(amount) AS INTEGER) 
            FROM multipliers
            WHERE (userID IS NULL OR userID = $0) 
            AND multi_type = $1
            """, user_id, multi_type
        )
        return multiplier

    async def send_tip_if_enabled(self, interaction: discord.Interaction, conn: Connection) -> None:
        """Send a tip if the user has enabled tips."""

        tips_enabled = await is_setting_enabled(conn, interaction.user.id, "tips")
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
        /, 
        conn: Connection, 
        exp_gainable: int
    ) -> None:

        record = await conn.fetchone(
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
            conn,
            user_id=interaction.user.id,
            multi_amount=((level // 3) or 1),
            multi_type="xp",
            cause="level",
            description=f"Level {level}"
        )

        await conn.execute(
            """
            UPDATE accounts 
            SET 
                level = level + 1, 
                exp = 0, 
                bankspace = bankspace + $0 
            WHERE userID = $1
            """, randint(50_000, 55_000*level), interaction.user.id
        )

        notifs_enabled = await is_setting_enabled(conn, interaction.user.id, "levelup_notifications")

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

        async with self.bot.pool.acquire() as conn, conn.transaction():
            try:
                data = await conn.fetchone(query, interaction.user.id, "xp", f"/{cmd.name}")
            except IntegrityError:
                return

            total, multi = data
            if not total % 15:
                await self.send_tip_if_enabled(interaction, conn)

            exp_gainable = command.extras.get("exp_gained")
            if not exp_gainable:
                return

            exp_gainable *= (1+(multi/100))
            await self.add_exp_or_levelup(interaction, conn, int(exp_gainable))

    @commands.Cog.listener()
    async def on_command_completion(self, ctx: commands.Context) -> None:
        """Track text commands ran."""
        if ctx.interaction:
            return

        cmd = ctx.command.parent or ctx.command
        async with self.bot.pool.acquire() as conn:
            try:
                await add_command_usage(ctx.author.id, f"@me {cmd.name}", conn)
            except IntegrityError:
                pass
            else:
                await conn.commit()

    # ----------- END OF ECONOMY FUNCS, HERE ON IS JUST COMMANDS --------------

    @app_commands.command(description="Adjust user-specific settings")
    @app_commands.describe(setting="The specific setting you want to adjust. Defaults to view.")
    async def settings(self, interaction: discord.Interaction, setting: str | None = None) -> None:
        """View or adjust user-specific settings."""
        async with self.bot.pool.acquire() as conn:
            settings = await conn.fetchall("SELECT setting, brief FROM settings_descriptions")
            chosen_setting = setting or settings[0][0]

            view = UserSettings(interaction, data=settings, chosen_setting=chosen_setting)
            em = await self.get_setting_embed(interaction, view=view, conn=conn)
        await interaction.response.send_message(embed=em, view=view)

    @app_commands.command(description="View all of your multipliers within the bot")
    @app_commands.describe(
        user="The user whose multipliers you want to see. Defaults to your own.",
        multiplier="The type of multiplier you want to see. Defaults to robux."
    )
    async def multipliers(
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

    share = app_commands.Group(name='share', description='Share different assets with others.')

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
        quantity: ROBUX_CONVERTER
    ) -> None:
        """"Give an amount of robux to another user."""

        sender = interaction.user
        if sender.id == recipient.id:
            return await interaction.response.send_message(embed=membed("You can't share with yourself."))

        async with self.bot.pool.acquire() as conn:
            if await self.can_call_out(recipient, conn):
                return await respond(interaction, embed=NOT_REGISTERED)

            actual_wallet = await self.fetch_balance(sender.id, conn)
            if isinstance(quantity, str):
                quantity = actual_wallet
            elif quantity > actual_wallet:
                return await respond(
                    interaction,
                    embed=membed("You don't have that much money to share.")
                )

            can_proceed = await handle_confirm_outcome(
                interaction, 
                prompt=f"Are you sure you want to share {CURRENCY} **{quantity:,}** with {recipient.mention}?",
                setting="share_robux_confirmations",
                conn=conn
            )

        async with self.bot.pool.acquire() as conn, conn.transaction():
            if can_proceed is not None:
                await end_transaction(conn, user_id=sender.id)
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
        item: ITEM_CONVERTER
    ) -> None:

        sender = interaction.user
        if sender.id == recipient.id:
            return await interaction.response.send_message(embed=membed("You can't share with yourself."))

        async with self.bot.pool.acquire() as conn:
            if await self.can_call_out(recipient, conn):
                return await respond(interaction, embed=NOT_REGISTERED)

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

            can_proceed = await handle_confirm_outcome(
                interaction, 
                prompt=f"Are you sure you want to share **{quantity:,} {ie} {item_name}** with {recipient.mention}?",
                setting="share_item_confirmations",
                conn=conn
            )

        async with self.bot.pool.acquire() as conn, conn.transaction():
            if can_proceed is not None:
                await end_transaction(conn, user_id=sender.id)
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

    trade = app_commands.Group(name='trade', description='Exchange different assets with others.')

    def default_checks_passing(self, trader: discord.Member, with_who: discord.Member) -> None:
        if with_who.id == trader.id:
            raise FailingConditionalError("You can't trade with yourself.")
        elif with_who.bot:
            raise FailingConditionalError("You can't trade with bots.")

    def robux_checks_passing(
        self,
        user_checked: discord.Member,
        robux_qty_offered: int,
        actual_wallet_amt: int
    ) -> None:
        if actual_wallet_amt < robux_qty_offered:
            resp = (
                f"{user_checked.mention} only has {CURRENCY} **{actual_wallet_amt:,}**.\n"
                f"Not the requested {CURRENCY} **{robux_qty_offered:,}**."
            )
            raise FailingConditionalError(resp)

    async def item_checks_passing(
        self,
        conn: Connection,
        user_to_check: discord.Member,
        item_data: tuple,
        item_qty_offered: int
    ) -> None:
        """
        Basic trading item checks. 
        
        If checks fail, it is your responsibility to respond and close transactions.
        """
        item_id, item_name, ie = item_data

        item_amt = await self.fetch_item_qty_from_id(user_to_check.id, item_id, conn)
        if item_amt < item_qty_offered:
            resp = (
                f"{user_to_check.mention} has **{item_amt}x {ie} {item_name}**.\n"
                f"Not the requested **{item_qty_offered}**."
            )
            raise FailingConditionalError(resp)

    async def prompt_for_robux(
        self,
        interaction: discord.Interaction,
        item_sender: discord.Member,
        item_sender_qty: int,
        item_sender_data: tuple,
        robux_sender: discord.Member,
        robux_sender_qty: int
    ) -> None | bool:
        """
        Send a confirmation prompt to `item_sender`, asking to confirm whether 
        they want to exchange their items (`item_sender_data`) with `robux_sender`, 
        in return for money (`robux_sender_qty`).

        The person that is confirming has to send items, in exchange they get robux.
        """
        can_continue = await handle_confirm_outcome(
            interaction,
            view_owner=item_sender,
            content=item_sender.mention,
            prompt=dedent(
                f"""
                > Are you sure you want to trade with {robux_sender.mention}?

                **Their:**
                - {CURRENCY} {robux_sender_qty:,}

                **For Your:**
                - {item_sender_qty}x {item_sender_data[-1]} {item_sender_data[1]}
                """
            )
        )
        return can_continue

    async def prompt_robux_for_items(
        self,
        interaction: discord.Interaction,
        robux_sender: discord.Member,
        item_sender: discord.Member,
        robux_sender_qty: int,
        item_sender_qty: int,
        item_sender_data: tuple
    ) -> None | bool:

        """
        Send a confirmation prompt to `robux_sender`, asking to confirm whether 
        they want to exchange their robux for items.

        The person that is confirming has to send robux, and they get items in return.
        """
        can_continue = await handle_confirm_outcome(
            interaction,
            view_owner=robux_sender,
            content=robux_sender.mention,
            prompt=dedent(
                f"""
                > Are you sure you want to trade with {item_sender.mention}?

                **Their:**
                - {item_sender_qty}x {item_sender_data[-1]} {item_sender_data[1]}

                **For Your:**
                - {CURRENCY} {robux_sender_qty:,}
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
        item_sender2_data: tuple
    ) -> None | bool:

        """
        The person that is confirming has to send items, and they also get items in return.
        """
        can_continue = await handle_confirm_outcome(
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

    @trade.command(name="items_for_robux", description="Exchange your items for robux in return")
    @app_commands.rename(with_who="with")
    @app_commands.describe(
        item="What item will you give?",
        quantity="How much of the item will you give?",
        with_who="Who are you giving this to?",
        for_robux="How much robux do you expect in return?"
    )
    async def trade_items_for_robux(
        self, 
        interaction: discord.Interaction, 
        quantity: int, 
        item: ITEM_CONVERTER,
        with_who: discord.Member,
        for_robux: ROBUX_CONVERTER
    ) -> None:

        self.default_checks_passing(interaction.user, with_who)

        async with self.bot.pool.acquire() as conn:
            wallet_amt = await self.fetch_balance(with_who.id, conn)

            # ! For the person sending items
            await self.item_checks_passing(conn, interaction.user, item, quantity)

        if isinstance(for_robux, str):
            for_robux = wallet_amt
        else:
            self.robux_checks_passing(with_who, for_robux, wallet_amt)

        # Transaction created inside the function for interaction.user
        can_proceed = await self.prompt_for_robux(
            interaction,
            item_sender=interaction.user,
            item_sender_qty=quantity,
            item_sender_data=item,
            robux_sender=with_who,
            robux_sender_qty=for_robux
        )

        async with self.bot.pool.acquire() as conn:
            if not can_proceed:  
                await end_transaction(conn, user_id=interaction.user.id)
                await conn.commit()
                return

        # ! For the other person sending robux

        can_proceed = await self.prompt_robux_for_items(
            interaction,
            robux_sender=with_who,
            robux_sender_qty=for_robux,
            item_sender=interaction.user,
            item_sender_qty=quantity,
            item_sender_data=item
        )

        query = "DELETE FROM transactions WHERE userID IN ($0, $1)"
        async with self.bot.pool.acquire() as conn, conn.transaction():
            await conn.execute(query, interaction.user.id, with_who.id)
            if not can_proceed:
                return

            await self.update_inv_by_id(interaction.user, -quantity, item_id=item[0], conn=conn)
            await self.update_inv_by_id(with_who, +quantity, item_id=item[0], conn=conn)
            await self.update_wallet_many(
                conn, 
                (-for_robux, with_who.id), 
                (+for_robux, interaction.user.id)
            )

        embed = discord.Embed(colour=0xFFFFFF).set_footer(text="Thanks for your business.")
        embed.title = "Your Trade Receipt"
        embed.description = (
            f"- {interaction.user.mention} gave {with_who.mention} **{quantity}x {item[-1]} {item[1]}**.\n"
            f"- {interaction.user.mention} received {CURRENCY} **{for_robux:,}** in return."
        )

        await interaction.followup.send(embed=embed)

    @trade.command(name="robux_for_items", description="Exchange your robux for items in return")
    @app_commands.rename(with_who="with")
    @app_commands.describe(
        robux="How much robux do you want to give?",
        for_item="What item do you want to receive?",
        item_quantity="How much of this item do you expect in return?",
        with_who="Who are you trading with?"
    )
    async def trade_robux_for_items(
        self, 
        interaction: discord.Interaction, 
        robux: ROBUX_CONVERTER,
        for_item: ITEM_CONVERTER,
        item_quantity: int, 
        with_who: discord.Member,
    ) -> None:

        self.default_checks_passing(interaction.user, with_who)

        async with self.bot.pool.acquire() as conn:
            wallet_amt = await self.fetch_balance(interaction.user.id, conn)

            if isinstance(robux, str):
                robux = wallet_amt
            else:
                self.robux_checks_passing(interaction.user, robux, wallet_amt)
            await self.item_checks_passing(conn, with_who, for_item, item_quantity)

        can_proceed = await self.prompt_robux_for_items(
            interaction,
            robux_sender=interaction.user,
            robux_sender_qty=robux,
            item_sender=with_who,
            item_sender_qty=item_quantity,
            item_sender_data=for_item,
        )

        async with self.bot.pool.acquire() as conn:
            if not can_proceed:
                await end_transaction(conn, user_id=interaction.user.id)
                await conn.commit()
                return

        can_proceed = await self.prompt_for_robux(
            interaction,
            item_sender=with_who,
            item_sender_qty=item_quantity,
            item_sender_data=for_item,
            robux_sender=interaction.user,
            robux_sender_qty=robux
        )

        query = "DELETE FROM transactions WHERE userID IN ($0, $1)"
        async with self.bot.pool.acquire() as conn, conn.transaction():
            await conn.execute(query, interaction.user.id, with_who.id)
            if not can_proceed:
                return

            await self.update_inv_by_id(with_who, -item_quantity, item_id=for_item[0], conn=conn)
            await self.update_inv_by_id(interaction.user, item_quantity, item_id=for_item[0], conn=conn)
            await self.update_wallet_many(
                conn, 
                (-robux, interaction.user.id), 
                (+robux, with_who.id)
            )

        embed = discord.Embed(colour=0xFFFFFF).set_footer(text="Thanks for your business.")
        embed.title = "Your Trade Receipt"
        embed.description = (
            f"- {interaction.user.mention} gave {with_who.mention} {CURRENCY} **{robux:,}**.\n"
            f"- {interaction.user.mention} received **{item_quantity}x** {for_item[-1]} {for_item[1]} in return."
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
        item: ITEM_CONVERTER,
        with_who: discord.Member,
        for_item: ITEM_CONVERTER,
        for_quantity: int
    ) -> None:
        
        self.default_checks_passing(interaction.user, with_who)

        if item[0] == for_item[0]:
            return await respond(
                interaction, 
                embed=membed(f"You can't trade {item[-1]} {item[1]}(s) on both sides.")
            )

        async with self.bot.pool.acquire() as conn:
            await self.item_checks_passing(conn, interaction.user, item, quantity)
            await self.item_checks_passing(conn, with_who, for_item, for_quantity)

        can_proceed = await self.prompt_items_for_items(
            interaction,
            item_sender=interaction.user,
            item_sender_qty=quantity,
            item_sender_data=item,
            item_sender2=with_who,
            item_sender2_qty=for_quantity,
            item_sender2_data=for_item
        )

        async with self.bot.pool.acquire() as conn:
            if not can_proceed:
                await end_transaction(conn, user_id=interaction.user.id)
                await conn.commit()
                return

        can_proceed = await self.prompt_items_for_items(
            interaction,
            item_sender=with_who,
            item_sender_qty=for_quantity,
            item_sender_data=for_item,
            item_sender2=interaction.user,
            item_sender2_qty=quantity,
            item_sender2_data=item
        )

        query = "DELETE FROM transactions WHERE userID IN ($0, $1)"
        async with self.bot.pool.acquire() as conn, conn.transaction():
            await conn.execute(query, interaction.user.id, with_who.id)
            if not can_proceed:
                return

            await self.update_inv_by_id(interaction.user, -quantity, item[0], conn)
            await self.update_inv_by_id(with_who, -for_quantity, for_item[0], conn)
            await conn.executemany(
                sql="UPDATE inventory SET qty = qty + $0 WHERE userID = $1 AND itemID = $2",
                seq_of_parameters=[
                    (for_quantity, interaction.user.id, for_item[0]), 
                    (quantity, with_who.id, item[0])
                ]
            )

        embed = discord.Embed(colour=0xFFFFFF).set_footer(text="Thanks for your business.")
        embed.title = "Your Trade Receipt"
        embed.description = (
            f"- {interaction.user.mention} gave {with_who.mention} **{quantity}x {item[-1]} {item[1]}**.\n"
            f"- {interaction.user.mention} received **{for_quantity}x {for_item[-1]} {for_item[1]}** in return."
        )
        await interaction.followup.send(embed=embed)

    @commands.command(description="Get a free random item.", aliases=('fr',))
    async def freemium(self, ctx: commands.Context) -> None:
        rQty = randint(1, 5)
        async with self.bot.pool.acquire() as conn, conn.transaction():
            item, emoji = await self.update_user_inventory_with_random_item(ctx.author.id, conn, rQty)

        await ctx.send(embed=membed(f"Success! You just got **{rQty}x** {emoji} {item}!"))

    shop = app_commands.Group(name='shop', description='View items available for purchase.')

    @shop.command(name='view', description='View all the shop items')
    async def view_shop(self, interaction: discord.Interaction) -> None:
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
                wallet = await self.fetch_balance(interaction.user.id, conn)
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

    @shop.command(description='Sell an item from your inventory', extras={})
    @app_commands.describe(
        item='The name of the item you want to sell.', 
        sell_quantity='The amount of this item to sell. Defaults to 1.'
    )
    async def sell(
        self, 
        interaction: discord.Interaction, 
        item: ITEM_CONVERTER, 
        sell_quantity: app_commands.Range[int, 1] = 1
    ) -> None:
        """Sell an item you already own."""
        seller = interaction.user

        async with self.bot.pool.acquire() as conn:
            item_id, item_name, ie = item

            qty, cost, sellable = await conn.fetchone(
                """
                SELECT COALESCE(inventory.qty, 0), cost, sellable
                FROM shop
                LEFT JOIN inventory 
                    ON inventory.itemID = shop.itemID AND inventory.userID = $0
                WHERE shop.itemID = $1
                """, seller.id, item_id
            )

            if not sellable:
                return await respond(
                    interaction, 
                    embed=membed(f"You can't sell **{ie} {item_name}**.")
                )

            if qty < sell_quantity:
                return await respond(
                    interaction,
                    embed=membed(f"You don't have {ie} **{sell_quantity:,}x** {item_name}, so no.")
                )

            multi = await Economy.get_multi_of(user_id=seller.id, multi_type="robux", conn=conn)
            cost = selling_price_algo((cost / 4) * sell_quantity, multi)
            can_proceed = await handle_confirm_outcome(
                interaction,
                prompt=f"Are you sure you want to sell **{sell_quantity:,}x {ie} {item_name}** for **{CURRENCY} {cost:,}**?",
                setting="selling_confirmations",
                conn=conn
            )

        async with self.bot.pool.acquire() as conn, conn.transaction():
            if can_proceed is not None:
                await end_transaction(conn, user_id=seller.id)
                if can_proceed is False:
                    return

            await self.update_inv_new(seller, -sell_quantity, item_name, conn)
            await self.update_account(seller.id, +cost, conn)

        embed = membed(
            f"{seller.mention} sold **{sell_quantity:,}x {ie} {item_name}** "
            f"and got paid {CURRENCY} **{cost:,}**."
        ).set_footer(text="Thanks for your business.")

        embed.title = f"{seller.display_name}'s Sale Receipt"
        await respond(interaction, embed=embed)

    @app_commands.command(description='Get more details on a specific item')
    @app_commands.describe(item=ITEM_DESCRPTION)
    async def item(self, interaction: discord.Interaction, item: ITEM_CONVERTER) -> None:
        """This is a subcommand. Look up a particular item within the shop to get more information about it."""

        async with self.bot.pool.acquire() as conn:
            item_id, item_name, _ = item

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
        await respond(interaction, embed=em)

    @commands.command(description='Identify causes of registration errors', aliases=('rs',))
    async def reasons(self, ctx: commands.Context) -> None:
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
    async def increase_bank_space(interaction: discord.Interaction, quantity: int) -> None:

        expansion = randint(1_600_000, 6_000_000)
        expansion *= quantity

        async with interaction.client.pool.acquire() as conn, conn.transaction():
            new_bankspace, = await conn.fetchone(
                """
                UPDATE accounts 
                SET bankspace = bankspace + $0 
                WHERE userID = $1 
                RETURNING bankspace
                """, expansion, interaction.user.id
            )

            new_amt, = await Economy.update_inv_new(
                interaction.user, 
                -quantity, 
                "Bank Note", 
                conn
            )

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

        await respond(interaction, embed=embed)

    @register_item('Bitcoin')
    async def gain_bitcoin_multiplier(interaction: discord.Interaction, _: int) -> None:
        future_expiry = (discord.utils.utcnow() + timedelta(minutes=30)).timestamp()

        async with interaction.client.pool.acquire() as conn, conn.transaction():
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
            await Economy.update_inv_by_id(
                interaction.user, 
                amount=-1, 
                item_id=21, 
                conn=conn
            )

        if not applied_successfully:
            return await respond(
                interaction, 
                embed=membed("You already have a <:Bitcoin:1263919978717908992> Bitcoin multiplier active.")
            )

        await respond(
            interaction,
            embed=membed(
                "You just activated a **30 minute** <:Bitcoin:1263919978717908992> Bitcoin multiplier!\n"
                "You'll get 500% more robux from transactions during this time."
            )
        )

        start_drop_expired(interaction)

    @app_commands.command(description="Use an item you own from your inventory", extras={"exp_gained": 3})
    @app_commands.describe(item=ITEM_DESCRPTION, quantity='Amount of items to use, when possible.')
    async def use(
        self, 
        interaction: discord.Interaction, 
        item: ITEM_CONVERTER, 
        quantity: app_commands.Range[int, 1] = 1
    ) -> discord.WebhookMessage | None:
        """Use a currently owned item."""

        item_id, item_name, ie = item
        async with self.bot.pool.acquire() as conn:
            data = await conn.fetchone(
                """
                SELECT qty
                FROM inventory
                WHERE itemID = $0 AND userID = $1
                """, item_id, interaction.user.id
            )

        if not data:
            return await respond(
                interaction,
                ephemeral=True,
                embed=membed(f"You don't have a single {ie} **{item_name}**, therefore cannot use it.")
            )

        qty, = data
        if qty < quantity:
            return await respond(
                interaction,
                ephemeral=True,
                embed=membed(f"You don't have **{quantity}x {ie} {item_name}**, therefore cannot use this many.")
            )

        handler = item_handlers.get(item_name)
        if handler is None:
            return await respond(
                interaction,
                ephemeral=True,
                embed=membed(f"{ie} **{item_name}** does not have a use yet.\nWait until it does!")
            )

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
        can_proceed = await handle_confirm_outcome(interaction, massive_prompt)

        async with self.bot.pool.acquire() as conn, conn.transaction():
            await end_transaction(conn, user_id=interaction.user.id)
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

    @app_commands.command(description="Sacrifice currency stats in exchange for incremental perks")
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

    @app_commands.command(description='View user information and other stats')
    @app_commands.describe(user='The user whose profile you want to see.')
    async def profile(
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

    @app_commands.command(description='Guess the number. Jackpot wins big!', extras={"exp_gained": 3})
    @app_commands.describe(robux=ROBUX_DESCRIPTION)
    async def highlow(self, interaction: discord.Interaction, robux: ROBUX_CONVERTER) -> None:
        """
        Guess the number. The user must guess if the clue the bot gives is higher,
        lower or equal to the actual number.
        """

        async with self.bot.pool.acquire() as conn:
            wallet_amt = await self.fetch_balance(interaction.user.id, conn)
            has_keycard = await self.fetch_item_qty_from_id(interaction.user.id, item_id=1, conn=conn)

            robux = self.do_wallet_checks(wallet_amt, robux, has_keycard)

            await declare_transaction(conn, user_id=interaction.user.id)

        await HighLow(interaction, bet=robux).start()

    @app_commands.command(description='Try your luck on a slot machine', extras={"exp_gained": 3})
    @app_commands.describe(robux=ROBUX_DESCRIPTION)
    async def slots(self, interaction: discord.Interaction, robux: ROBUX_CONVERTER) -> None:
        """Play a round of slots. At least one matching combination is required to win."""

        query = "SELECT slotw, slotl, wallet FROM accounts WHERE userID = $0"

        # Game checks
        async with self.bot.pool.acquire() as conn:
            has_keycard = await self.fetch_item_qty_from_id(interaction.user.id, item_id=1, conn=conn)
            slot_wins, slot_losses, wallet_amt = await conn.fetchone(query, interaction.user.id) or (0, 0, 0)
        robux = self.do_wallet_checks(wallet_amt, robux, has_keycard)

        # The actual slot machine

        emoji_1, emoji_2, emoji_3 = generate_slot_combination()
        multiplier = find_slot_matches(emoji_1, emoji_2, emoji_3)
        slot_machine = discord.Embed()

        if multiplier:
            amount_after_multi = add_multi_to_original(multiplier, robux)

            async with self.bot.pool.acquire() as conn, conn.transaction():
                data = await self.update_fields(
                    interaction.user.id, 
                    conn, 
                    slotwa=amount_after_multi, 
                    slotw=1, 
                    wallet=amount_after_multi
                )

            prcntw = ((slot_wins+1) / (slot_losses + (slot_wins+1))) * 100

            slot_machine.colour = discord.Color.brand_green()
            slot_machine.description = (
                f"**\U0000003e** {emoji_1} {emoji_2} {emoji_3} **\U0000003c**\n\n"
                f"Multiplier: **{multiplier}%**\n"
                f"Payout: {CURRENCY} **{amount_after_multi:,}**.\n"
                f"New Balance: {CURRENCY} **{data[-1]:,}**.\n"
                f"-# **{prcntw:.1f}%** of all slots games won."
            )

        else:
            async with self.bot.pool.acquire() as conn, conn.transaction():
                data = await self.update_fields(
                    interaction.user.id, 
                    conn, 
                    slotla=robux,
                    slotl=1,
                    wallet=-robux
                )

            prcntl = ((slot_losses+1) / (slot_wins + (slot_losses+1))) * 100

            slot_machine.colour = discord.Color.brand_red()
            slot_machine.description = (
                f"**\U0000003e** {emoji_1} {emoji_2} {emoji_3} **\U0000003c**\n\n"
                f"You lost: {CURRENCY} **{robux:,}**.\n"
                f"New Balance: {CURRENCY} **{data[-1]:,}**.\n"
                f"-# {prcntl:.1f}% of all slots games lost."
            )

        await interaction.response.send_message(embed=slot_machine)

    @app_commands.command(description='View your currently owned items')
    @app_commands.describe(member='The user whose inventory you want to see.')
    async def inventory(
        self, 
        interaction: discord.Interaction, 
        member: USER_ENTRY | None = None
    ) -> None:
        """View your inventory or another player's inventory."""
        member = member or interaction.user

        async with self.bot.pool.acquire() as conn:
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

        length = 8
        paginator = RefreshPagination(interaction)
        paginator.total_pages = paginator.compute_total_pages(len(owned_items), length) or 1
        em = membed().set_author(
            name=f"{member.name}'s inventory", 
            icon_url=member.display_avatar.url
        )

        async def get_page_part(force_refresh: bool | None = None) -> discord.Embed:
            """Helper function to determine what page of the paginator we're on."""
            nonlocal owned_items
            if force_refresh:
                async with self.bot.pool.acquire() as conn:
                    owned_items = await conn.fetchall(query, member.id)
                paginator.reset_index(owned_items, length)

            if not owned_items:
                em.set_footer(text="Empty")
                return em

            offset = (paginator.index - 1) * length
            em.description = "\n".join(
                f"{ie} **{item_name}** \U00002500 {qty:,}" 
                for (item_name, ie, qty) in owned_items[offset:offset+length]
            )
            return em.set_footer(text=f"Page {paginator.index} of {paginator.total_pages}")

        paginator.get_page = get_page_part
        await paginator.navigate()

    @app_commands.command(description="Get someone's balance")
    @app_commands.describe(user='The user to find the balance of.')
    async def balance(
        self, 
        interaction: discord.Interaction, 
        user: USER_ENTRY | None = None
    ) -> None:
        user = user or interaction.user

        balance_view = BalanceView(interaction, viewing=user)
        balance = await balance_view.fetch_balance(interaction)

        await interaction.response.send_message(embed=balance, view=balance_view)

    async def payout_recurring_income(
        self, 
        interaction: discord.Interaction, 
        income_type: str,
        weeks_away: int
    ) -> None:
        multiplier = {
            "weekly": 10_000_000,
            "monthly": 100_000_000,
            "yearly": 1_000_000_000
        }.get(income_type)
        em = membed()

        # ! Do they have a cooldown?
        async with self.bot.pool.acquire() as conn:
            query = "SELECT until FROM cooldowns WHERE userID = $0 AND cooldown = $1"
            cd_timestamp = await conn.fetchone(query, interaction.user.id, income_type)

        noun_period = income_type[:-2]
        if cd_timestamp is not None:
            cd_timestamp, = cd_timestamp

            has_cd = self.has_cd(cd_timestamp)
            if isinstance(has_cd, datetime):
                r = discord.utils.format_dt(has_cd, style="R")
                em.description = (
                    f"You already got your {income_type} robux "
                    f"this {noun_period}, try again {r}."
                )
                return await interaction.response.send_message(embed=em)

        # ! Try updating the cooldown, giving robux
        r = discord.utils.utcnow() + timedelta(weeks=weeks_away)
        rformatted = discord.utils.format_dt(r, style="R")

        async with self.bot.pool.acquire() as conn, conn.transaction() as tr:
            try:
                ret = await self.update_account(interaction.user.id, multiplier, conn)
                assert ret is not None
            except AssertionError:
                await tr.rollback()
                return await interaction.response.send_message(embed=self.not_registered)
            await self.update_cooldown(conn, interaction.user.id, income_type, r.timestamp())

        em.description = (
            f"You just got {CURRENCY} **{multiplier:,}** for checking in this {noun_period}.\n"
            f"See you next {noun_period} ({rformatted})!"
        )

        em.title = f"{interaction.user.display_name}'s {income_type.title()} Robux"
        em.url = "https://www.youtube.com/watch?v=ue_X8DskUN4"

        await interaction.response.send_message(embed=em)

    @app_commands.command(description="Get a weekly injection of robux")
    async def weekly(self, interaction: discord.Interaction) -> None:
        await self.payout_recurring_income(interaction, "weekly", weeks_away=1)

    @app_commands.command(description="Get a monthly injection of robux")
    async def monthly(self, interaction: discord.Interaction) -> None:
        await self.payout_recurring_income(interaction, "monthly", weeks_away=4)

    @app_commands.command(description="Get a yearly injection of robux")
    async def yearly(self, interaction: discord.Interaction) -> None:
        await self.payout_recurring_income(interaction, "yearly", weeks_away=52)

    @app_commands.command(description="Opt out of the virtual economy, deleting all of your data")
    @app_commands.describe(member='The player to remove all of the data of. Defaults to you.')
    async def resetmydata(self, interaction: discord.Interaction, member: USER_ENTRY | None = None) -> None:
        """Opt out of the virtual economy and delete all of the user data associated."""

        member = member or interaction.user

        if (member.id != interaction.user.id) and (interaction.user.id not in self.bot.owner_ids):
            return await interaction.response.send_message(
                ephemeral=True,
                embed=membed("You are not allowed to do this.")
            )

        async with self.bot.pool.acquire() as conn:
            if await self.can_call_out(member, conn):
                return await interaction.response.send_message(
                    ephemeral=True,
                    embed=membed(f"{member.mention} isn't registered.")
                )
            await declare_transaction(conn, user_id=member.id)
            await conn.commit()

        view = ConfirmResetData(interaction, member)

        link = "https://www.youtube.com/shorts/vTrH4paRl90"            
        await interaction.response.send_message(
            view=view,
            embed=membed(
                f"This command will reset **[EVERYTHING]({link})**.\n"
                "Are you **SURE** you want to do this?\n\n"
                "If you do, click `RESET MY DATA` **3** times."
            )
        )

    @app_commands.command(description="Withdraw robux from your bank account")
    @app_commands.describe(robux=ROBUX_DESCRIPTION)
    async def withdraw(self, interaction: discord.Interaction, robux: ROBUX_CONVERTER) -> None:
        """Withdraw a given amount of robux from your bank."""

        async with self.bot.pool.acquire() as conn:
            bank_amt = await self.fetch_balance(interaction.user.id, conn, "bank")

        embed = membed()
        if not bank_amt:
            embed.description = "You have nothing to withdraw."
            return await interaction.response.send_message(embed=embed)

        if isinstance(robux, str):
            robux = bank_amt
        elif robux > bank_amt:
            embed.description = f"You only have {CURRENCY} **{bank_amt:,}** in your bank right now."
            return await interaction.response.send_message(embed=embed, ephemeral=True)

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

        async with self.bot.pool.acquire() as conn, conn.transaction():
            wallet_new, bank_new = await conn.fetchone(query, robux, interaction.user.id)

        embed.add_field(name="Withdrawn", value=f"{CURRENCY} {robux:,}", inline=False)
        embed.add_field(name="Current Wallet Balance", value=f"{CURRENCY} {wallet_new:,}")
        embed.add_field(name="Current Bank Balance", value=f"{CURRENCY} {bank_new:,}")

        await interaction.response.send_message(embed=embed)

    @app_commands.command(description="Deposit robux into your bank account")
    @app_commands.describe(robux=ROBUX_DESCRIPTION)
    async def deposit(self, interaction: discord.Interaction, robux: ROBUX_CONVERTER) -> None:
        """Deposit an amount of robux into your bank."""

        query = "SELECT wallet, bank, bankspace FROM accounts WHERE userID = $0"
        async with self.bot.pool.acquire() as conn:
            wallet_amt, bank, bankspace = await conn.fetchone(query, interaction.user.id) or (0, 0, 0)

        embed = membed()
        if not wallet_amt:
            embed.description = "You have nothing to deposit."
            return await interaction.response.send_message(embed=embed)

        can_deposit = bankspace - bank
        if can_deposit <= 0:
            embed.description = (
                f"You can only hold {CURRENCY} **{bankspace:,}** in your bank right now.\n"
                f"To hold more, use currency commands and level up more. Bank Notes can aid with this."
            )
            return await interaction.response.send_message(embed=embed)

        if isinstance(robux, str):
            robux = min(wallet_amt, can_deposit)
        elif robux > wallet_amt:
            embed.description = f"You only have {CURRENCY} **{wallet_amt:,}** in your wallet right now."
            return await interaction.response.send_message(embed=embed)

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

        async with self.bot.pool.acquire() as conn, conn.transaction():
            wallet_new, bank_new = await conn.fetchone(query, robux, interaction.user.id)

        embed.add_field(name="Deposited", value=f"{CURRENCY} {robux:,}", inline=False)
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
    async def get_item_lb(
        self, 
        interaction: discord.Interaction, 
        item: ITEM_CONVERTER
    ):
        async with self.bot.pool.acquire() as conn:
            item_id, item_name, _ = item
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
    @app_commands.rename(host='user')
    @app_commands.describe(host='The user you want to rob money from.')
    async def rob(self, interaction: discord.Interaction, host: discord.Member) -> None:
        """Rob someone else."""
        robber = interaction.user
        embed = membed()
        
        if robber.id == host.id:
            embed.description = 'Seems pretty foolish to steal from yourself'
            return await interaction.response.send_message(embed=embed)
        elif host.bot:
            embed.description = 'You are not allowed to steal from bots, back off my kind'
            return await interaction.response.send_message(embed=embed)

        query = (
            """
            SELECT wallet, bounty, settings.value
            FROM accounts 
            LEFT JOIN settings 
                ON accounts.userID = settings.userID AND settings.setting = 'passive_mode'
            WHERE accounts.userID = $0
            """
        )

        query2 = (
            """
            SELECT wallet, settings.value
            FROM accounts
            LEFT JOIN settings 
                ON accounts.userID = settings.userID AND settings.setting = 'passive_mode' 
            WHERE accounts.userID = $0
            """
        )

        async with self.bot.pool.acquire() as conn:
            if not (await self.can_call_out_either(robber, host, conn)):
                return await interaction.response.send_message(embed=NOT_REGISTERED)

            robber_wallet, robber_bounty, robber_passive_mode = await conn.fetchone(query, robber.id)
            host_wallet, host_passive_mode = await conn.fetchone(query2, host.id)

        if robber_passive_mode:
            embed.description = "You are in passive mode! If you want to rob, turn that off!"
            return await interaction.response.send_message(embed=embed)

        if host_passive_mode:
            embed.description = f"{host.mention} is in passive mode, you can't rob them!"
            return await interaction.response.send_message(embed=embed)

        if host_wallet < 1_000_000:
            embed.description = f"{host.mention} doesn't even have {CURRENCY} **1,000,000**, not worth it."
            return await interaction.response.send_message(embed=embed)

        if robber_wallet < 10_000_000:
            embed.description = f"You need at least {CURRENCY} **10,000,000** in your wallet to rob someone."
            return await interaction.response.send_message(embed=embed)

        fifty50, = choices((0, 1), weights=(49, 51))

        if fifty50:
            emote = choice(
                (
                    "<a:kekRealize:970295657233539162>", 
                    "<:smhlol:1160157952410386513>", 
                )
            )

            fine = randint(min(50_000, robber_wallet), robber_wallet)
            embed.description = (
                f'You were caught lol {emote}\n'
                f'You paid {host.mention} {CURRENCY} **{fine:,}**.'
            )

            if robber_bounty:
                fine += robber_bounty
                embed.description += (
                    "\n\n**Bounty Status:**\n"
                    f"{host.mention} was also given your bounty of **{CURRENCY} {robber_bounty:,}**."
                )

            async with self.bot.pool.acquire() as conn, conn.transaction():
                await self.update_wallet_many(conn, (fine, host.id), (-fine, robber.id))

            return await interaction.response.send_message(embed=embed)

        amt_stolen = randint(min(1_000_000, robber_wallet), robber_wallet)
        amt_dropped = floor((randint(1, 25) / 100) * amt_stolen)
        total = amt_stolen - amt_dropped
        percent_stolen = int((total/amt_stolen) * 100)

        async with self.bot.pool.acquire() as conn, conn.transaction():
            await self.update_wallet_many(conn, (-amt_stolen, host.id), (total, robber.id))

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

    @app_commands.command(description="Gather people to rob someone's bank")
    @app_commands.describe(user='The user to attempt to bankrob.')
    async def bankrob(self, interaction: discord.Interaction, user: discord.Member) -> None:
        """Rob someone else's bank."""
        starter_id = interaction.user.id
        user_id = user.id

        if user_id == starter_id:
            return await interaction.response.send_message(embed=membed("You can't bankrob yourself."))
        if user.bot:
            return await interaction.response.send_message(embed=membed("You can't bankrob bots."))

        await interaction.response.send_message(embed=membed("This feature is in development."))

    @app_commands.command(description="Test your skills at blackjack", extras={"exp_gained": 3})
    @app_commands.describe(robux=ROBUX_DESCRIPTION)
    async def blackjack(self, interaction: discord.Interaction, robux: ROBUX_CONVERTER) -> None:
        """
        Play a round of blackjack with the bot. 

        Win by reaching 21 and a higher score than the bot without bust.
        """

        # Game checks

        async with self.bot.pool.acquire() as conn, conn.transaction():
            wallet_amt = await self.fetch_balance(interaction.user.id, conn)
            has_keycard = await self.fetch_item_qty_from_id(interaction.user.id, item_id=1, conn=conn)
            robux = self.do_wallet_checks(wallet_amt, robux, has_keycard)
            await declare_transaction(conn, user_id=interaction.user.id)

        # Game setup

        deck = [2, 3, 4, 5, 6, 7, 8, 9, 10, 10, 10, 10, 11] * 4
        shuffle(deck)

        player_hand = [deck.pop(), deck.pop()]
        dealer_hand = [deck.pop(), deck.pop()]

        player_sum = calculate_hand(player_hand)

        shallow_pv = [display_user_friendly_card_format(number) for number in player_hand]
        shallow_dv = [display_user_friendly_card_format(number) for number in dealer_hand]

        self.bot.games[interaction.user.id] = (deck, player_hand, dealer_hand, shallow_dv, shallow_pv, robux)

        initial = membed(
            f"The game has started. May the best win.\n"
            f"`{CURRENCY} ~{format_number_short(robux)}` is up for grabs on the table."
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

        await interaction.response.send_message(embed=initial, view=BlackjackUi(interaction))

    def do_wallet_checks(self, wallet: int, bet : str | int, keycard: bool = False) -> int:
        """
        Reusable wallet checks that are common amongst most gambling commands.

        The parameter `bet_amount` must first be transformed into an integer/valid shorthand 
        via the `ROBUX_CONVERTER` converter.
        """

        if isinstance(bet, str):
            bet = min(MAX_BET_KEYCARD, wallet) if keycard else min(MAX_BET_WITHOUT, wallet)
        
        if keycard:
            if (bet < MIN_BET_KEYCARD) or (bet > MAX_BET_KEYCARD):
                raise FailingConditionalError(
                    f"You can't bet less than {CURRENCY} **{MIN_BET_KEYCARD:,}**.\n"
                    f"You also can't bet anything more than {CURRENCY} **{MAX_BET_KEYCARD:,}**."
                )
        elif (bet < MIN_BET_WITHOUT) or (bet > MAX_BET_WITHOUT):
            raise FailingConditionalError(
                f"You can't bet less than {CURRENCY} **{MIN_BET_WITHOUT:,}**.\n"
                f"You also can't bet anything more than {CURRENCY} **{MAX_BET_WITHOUT:,}**.\n"
                f"-# These values can increase when you acquire a <:Keycard:1263922058220408872> Keycard."
            )
        return bet

    @app_commands.command(description="Bet your robux on a dice roll", extras={"exp_gained": 3})
    @app_commands.describe(robux=ROBUX_DESCRIPTION)
    async def bet(self, interaction: discord.Interaction, robux: ROBUX_CONVERTER) -> None:
        """Bet your robux on a gamble to win or lose robux."""

        # Game checks
        user = interaction.user
        query = "SELECT wallet, betw, betl FROM accounts WHERE userID = $0"

        async with self.bot.pool.acquire() as conn:
            wallet_amt, id_won_amount, id_lose_amount = await conn.fetchone(query, user.id) or (0, 0, 0)

            has_keycard = await self.fetch_item_qty_from_id(user.id, item_id=1, conn=conn)
            robux = self.do_wallet_checks(wallet_amt, robux, has_keycard)
            
            pmulti = await self.get_multi_of(user.id, "robux", conn)

        badges = ""

        if has_keycard:
            badges = "<:Keycard:1263922058220408872>"

            their_roll, = choices(
                population=(1, 2, 3, 4, 5, 6), 
                weights=(37 / 3, 37 / 3, 37 / 3, 63 / 3, 63 / 3, 63 / 3)
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
            amount_after_multi = add_multi_to_original(pmulti, robux)
            async with self.bot.pool.acquire() as conn, conn.transaction():
                updated = await self.update_fields(
                    user.id, 
                    conn, 
                    betwa=amount_after_multi, 
                    betw=1, 
                    wallet=amount_after_multi
                )

            prcntw = (updated[1] / (id_lose_amount + updated[1])) * 100

            embed.colour = discord.Color.brand_green()
            embed.description=(
                f"**You've rolled higher!**\n"
                f"You won {CURRENCY} **{amount_after_multi:,}**.\n"
                f"You now have {CURRENCY} **{updated[2]:,}**.\n"
                f"You've won {prcntw:.1f}% of all games."
            )

            embed.set_author(
                name=f"{user.name}'s winning gambling game", 
                icon_url=user.display_avatar.url
            ).set_footer(text=f"Multiplier: {pmulti:,}%")

        elif their_roll == bot_roll:
            embed.colour = discord.Color.yellow()
            embed.description = "**Tie.** You lost nothing nor gained anything!"

            embed.set_author(
                name=f"{user.name}'s gambling game", 
                icon_url=user.display_avatar.url
            )

        else:
            async with self.bot.pool.acquire() as conn, conn.transaction():
                updated = await self.update_fields(
                    user.id, 
                    conn, 
                    betla=robux, 
                    betl=1, 
                    wallet=-robux
                )

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
                name=f"{user.name}'s losing gambling game", 
                icon_url=user.display_avatar.url
            )

        embed.add_field(name=user.name, value=f"Rolled `{their_roll}` {''.join(badges)}")
        embed.add_field(name=self.bot.user.name, value=f"Rolled `{bot_roll}`")

        await interaction.response.send_message(embed=embed)

    @sell.autocomplete('item')
    @item.autocomplete('item')
    @share_items.autocomplete('item')
    @trade_items_for_robux.autocomplete('item')
    @trade_items_for_items.autocomplete('item')
    async def owned_items_lookup(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        query = (
            """
            SELECT itemName
            FROM shop
            INNER JOIN inventory ON shop.itemID = inventory.itemID
            WHERE LOWER(itemName) LIKE '%' || ? || '%' AND userID = ?
            LIMIT 25
            """
        )

        async with self.bot.pool.acquire() as conn:
            options = await conn.fetchall(query, (f'%{current.lower()}%', interaction.user.id))

        return [app_commands.Choice(name=option, value=option) for (option,) in options]

    @item.autocomplete('item')
    @get_item_lb.autocomplete('item')
    @trade_robux_for_items.autocomplete('for_item')
    @trade_items_for_items.autocomplete('for_item')
    async def item_lookup(self, _: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        query = (
            """
            SELECT itemName 
            FROM shop
            WHERE LOWER(itemName) LIKE '%' || ? || '%'
            LIMIT 25
            """
        )

        async with self.bot.pool.acquire() as conn:
            options = await conn.fetchall(query, (f'%{current.lower()}%',))

        return [app_commands.Choice(name=option, value=option) for (option,) in options]

    @settings.autocomplete('setting')
    async def setting_lookup(self, _: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        query = (
            """
            SELECT 
                setting, 
                REPLACE(setting, '_', ' ') AS formatted_setting 
            FROM settings_descriptions
            WHERE LOWER(setting) LIKE '%' || ? || '%'
            """
        )

        async with self.bot.pool.acquire() as conn:
            results = await conn.fetchall(query, (f'%{current.lower()}%',))

        return [
            app_commands.Choice(name=formatted_setting.title(), value=setting)
            for (setting, formatted_setting) in results
        ]



async def setup(bot: C2C) -> None:
    """Setup function to initiate the cog."""
    await bot.add_cog(Economy(bot))
