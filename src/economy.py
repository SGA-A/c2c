from datetime import datetime, timedelta
from math import ceil, floor
from random import choices, randint
from re import search
from sqlite3 import IntegrityError, Row
from textwrap import dedent
from typing import Any, Literal, Optional

import discord
from asqlite import Connection
from discord import ButtonStyle, app_commands
from discord.app_commands import Choice

from ._types import BotExports, MaybeWebhook, UserEntry
from .core.bot import Interaction
from .core.constants import *
from .core.errors import CustomTransformerError, FailingConditionalError
from .core.helpers import (
    LRU,
    BaseView,
    add_multiplier,
    declare_transaction,
    end_transaction,
    get_multi_of,
    membed,
    respond,
    send_prompt,
    trans_prompt,
)
from .core.paginators import PaginationItem, RefreshPagination
from .core.transformers import RawIntegerTransformer

NO_FILTER = "0"
YT_SHORT = "https://www.youtube.com/shorts/vTrH4paRl90"
MIN_BET_KEYCARD = 500_000
MAX_BET_KEYCARD = 15_000_000
MIN_BET_WITHOUT = 100_000
MAX_BET_WITHOUT = 10_000_000
WARN_FOR_CONCURRENCY = (
    "You cannot interact with this right now.\n"
    "Finish any commands you are currently using before trying again."
)
ITEM_DESCRPTION = "Select an item."
ROBUX_DESCRIPTION = "Can be a number like 1234 or a shorthand (max, all, 1e6)."
INVOKER_NOT_REGISTERED = (
    "## <:notFound:1263922668823122075> You are not registered.\n"
    "You'll need to register first before you can use this command.\n"
    "### Already Registered?\n"
    "Find out what could've happened by calling "
    "[`/reasons`](https://www.google.com/)."
)
NOT_REGISTERED = "The user to act on must be registered."
SLOTS = (
    "\U0001f525", "\U0001f633", "\U0001f31f",
    "\U0001f494", "\U0001f595", "\U0001f921",
    "\U0001f355", "\U0001f346", "\U0001f351"
)
FIRE, FLUSHED, STAR, HEARTACHE, MF, CLOWN, PIZZA, AUBE, PEACH = SLOTS
BONUS_MULTIPLIERS = {
    f"{PIZZA*2}": 30,
    f"{CLOWN*2}": 60,
    f"{STAR*2}": 80,
    f"{HEARTACHE*2}": 90,
    f"{PEACH*2}": 100,
    f"{MF*2}": 120,
    f"{AUBE*2}": 130,
    f"{FLUSHED*2}": 110,
    f"{FIRE*2}": 140,
    f"{HEARTACHE*3}": 150,
    f"{MF*3}": 300,
    f"{CLOWN*3}": 350,
    f"{PIZZA*3}": 400,
    f"{AUBE*3}": 450,
    f"{PEACH*3}": 500,
    f"{FLUSHED*3}": 550,
    f"{STAR*3}": 600,
    f"{FIRE*3}": 900
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
RECURRING_MULTIPLIERS  = {
    "weekly": 10_000_000,
    "monthly": 100_000_000,
    "yearly": 1_000_000_000
}

item_handlers = {}

error_view = discord.ui.View()
error_view.stop()
error_view.add_item(
    discord.ui.Button(
        emoji="\U00002754",
        url="https://dankmemer.lol/tutorial/interaction-locks"
    )
)


def register_item(item):
    def decorator(func):
        item_handlers[item] = func
        return func
    return decorator


def add_multi_to_original(multi: int, original: int) -> int:
    return int(((multi / 100) * original) + original)

def selling_price_algo(base_price: int, multiplier: int) -> int:
    base_price //= 4
    base_price = (1 + (multiplier / 100)) * base_price
    return int(round(base_price, -2))


def generate_slot_combination() -> str:
    """A slot machine that generates and returns one row of slots."""

    weights = (800, 1000, 800, 100, 900, 800, 1000, 800, 800)

    slot_combination = "".join(choices(SLOTS, weights=weights, k=3))
    return slot_combination


def find_slot_matches(*args) -> Optional[int]:
    """
    Find any suitable matches in a slot outcome.

    The function takes in multiple arguments, each being the individual emoji.

    If there is a match, return the associated multiplier.

    Return `None` if no match found.

    This only checks the first two elements, but you must provide all three.
    """

    for emoji in args[:-1]:
        occurences = args.count(emoji)
        if occurences > 1:
            return BONUS_MULTIPLIERS[emoji*occurences]
    return None


class ItemInputTransformer(app_commands.Transformer):
    """
    Convert an item's name to a tuple
    containing the item ID, name, and emoji.
    """

    ITEM_NOT_FOUND = "No items exist with that name pattern."
    TIMED_OUT = "Timed out waiting for a response."
    QUERY = (
        """
        SELECT itemID, itemName, emoji
        FROM shop
        WHERE itemName LIKE '%' || ? || '%'
        COLLATE NOCASE
        ORDER BY INSTR(itemName, ?)
        LIMIT 5
        """
    )

    async def transform(
        self,
        itx: Interaction,
        value: str
    ) -> tuple[int, str, str]:
        async with itx.client.pool.acquire() as conn:
            rows = await conn.fetchall(self.QUERY, (value, value))

        if not rows:
            raise CustomTransformerError(
                value, self.type, self, self.ITEM_NOT_FOUND
            )

        length = len(rows)
        if length == 1:
            return rows[0]

        content = f"{length} results for {value!r} found, select one below."
        view = BaseView(itx, content)
        view.chosen_item = None

        for (item_id, item_name, item_emoji) in rows:
            view.add_item(MatchItem(item_id, item_name, item_emoji))

        await itx.response.send_message(content, view=view)
        await view.wait()

        if view.chosen_item:
            return view.chosen_item

        raise CustomTransformerError(value, self.type, self, self.TIMED_OUT)


class ConfirmResetData(BaseView):
    roo_fire = discord.PartialEmoji.from_str("<:rooFire:1263923362154156103>")
    WARNING = (
        f"## \U000026a0\U0000fe0f Advanced Warning\n"
        f"> See what resets by viewing the resetmydata tag.\n"
        f"This command resets **[__everything__](<{YT_SHORT}>)**.\n"
        f"Are you sure you want to do this? This is irreversible!\n\n"
        f"If so, press `Reset` **3** times.\n"
    )

    def __init__(self, itx: Interaction, target: UserEntry, /) -> None:
        super().__init__(itx, self.WARNING)

        self.target = target
        self.count = 0

    @discord.ui.button(label="Reset", style=ButtonStyle.danger, emoji=roo_fire)
    async def yes(self, itx: Interaction, button: discord.ui.Button) -> None:

        self.count += 1
        if self.count < 3:
            return await itx.response.edit_message(view=self)

        self.stop()

        button.disabled, self.children[-1].disabled = True, True
        button.style, self.children[-1].style = (
            ButtonStyle.success, ButtonStyle.secondary
        )

        await itx.response.edit_message(view=self)

        query = "DELETE FROM accounts WHERE userID = $0"
        async with itx.client.pool.acquire() as conn:
            tr = conn.transaction()
            await tr.start()

            try:
                await conn.execute(query, self.target.id)
            except Exception as e:
                itx.client.log_exception(e)
                await tr.rollback()

                return await itx.followup.send(
                    "The operation was unsuccessful. "
                    "Report this to the developers so they can get it fixed."
                )
            else:
                await tr.commit()

        end_note = (
            " Thanks for trying the experience out! "
            "You can start over from scratch whenever you like."
            if itx.user.id == self.target.id else ""
        )

        await itx.followup.send(f"Success.{end_note}")

    @discord.ui.button(label="Cancel", style=ButtonStyle.primary)
    async def no(self, itx: Interaction, button: discord.ui.Button) -> None:
        self.stop()

        button.disabled, self.children[0].disabled = True, True
        button.style, self.children[0].style = (
            ButtonStyle.success, ButtonStyle.secondary
        )

        await itx.response.edit_message(view=self)
        await self.end_transactions(itx)


class BalanceView(BaseView):
    """View for the balance command to mange and deposit/withdraw money."""

    def __init__(self, itx: Interaction, viewing: UserEntry) -> None:
        super().__init__(itx)

        self.viewing = viewing
        self.children[2].default_values = [discord.Object(id=self.viewing.id)]

    async def interaction_check(self, itx: Interaction) -> bool:
        #! Check it is the author of the original interaction running this

        # Parent method already responds if False
        value = await super().interaction_check(itx)
        if not value:
            return False

        #! Check if they're already in a transaction
        #! Check if they exist in the database

        return await transactional_check(itx)

    async def fetch_balance(self, itx: Interaction) -> discord.Embed:
        """Fetch the user's balance, format it into an embed."""

        balance = membed()
        balance.url = "https://dis.gd/support"
        balance.title = f"{self.viewing.display_name}'s Balances"
        balance.timestamp = discord.utils.utcnow()

        query = (
            """
            SELECT wallet, bank, bankspace
            FROM accounts
            WHERE userID = $0
            """
        )

        async with itx.client.pool.acquire() as conn:
            data = await conn.fetchone(query, self.viewing.id)

            if (not data) and (itx.user.id != self.viewing.id):
                balance.description = "This user is not registered."
                self.children[0].disabled = True
                self.children[1].disabled = True
                return balance

            inserted = await open_bank_new(self.viewing, conn)
            if inserted:
                await conn.commit()

            rank = await calc_net_ranking_for(self.viewing, conn)
            inv = await calc_inv_net(self.viewing, conn) if data else 0
            wallet, bank, bankspace = (
                data or await conn.fetchone(query, self.viewing.id)
            )

        space = (bank / bankspace) * 100
        money = wallet + bank

        balance.add_field(name="Wallet", value=f"{CURRENCY} {wallet:,}")
        balance.add_field(name="Bank", value=f"{CURRENCY} {bank:,}")
        balance.add_field(
            name="Bankspace",
            value=f"{CURRENCY} {bankspace:,} ({space:.2f}% full)"
        )

        balance.add_field(name="Money Net", value=f"{CURRENCY} {money:,}")
        balance.add_field(name="Inventory Net", value=f"{CURRENCY} {inv:,}")
        balance.add_field(name="Total Net", value=f"{CURRENCY} {inv+money:,}")

        balance.set_footer(text=f"Global Rank: #{rank}")
        self.checks(bank, wallet, bankspace-bank)
        return balance

    def checks(
        self,
        current_bank: int,
        current_wallet: int,
        current_bankspace_left: int
    ) -> None:
        """Check if balance buttons should be disabled or not."""
        if self.viewing.id != self.itx.user.id:
            self.children[0].disabled = True
            self.children[1].disabled = True
            return

        self.children[0].disabled = (current_bank == 0)
        self.children[1].disabled = (
            (current_wallet == 0) or (current_bankspace_left == 0)
        )

    @discord.ui.button(label="Withdraw", row=1)
    async def withdraw(self, itx: Interaction, _: discord.ui.Button) -> None:

        async with itx.client.pool.acquire() as conn:
            bank_amt = await fetch_account_data(
                itx.user.id, "bank", conn, default=0
            )

        if not bank_amt:
            return await itx.response.send_message(
                "You have nothing to withdraw."
            )

        modal = DepositOrWithdraw(
            title="Withdraw",
            default_val=bank_amt,
            view=self
        )

        await itx.response.send_modal(modal)

    @discord.ui.button(label="Deposit", row=1)
    async def deposit(self, itx: Interaction, _: discord.ui.Button) -> None:
        query = (
            """
            SELECT wallet, bank, bankspace
            FROM accounts
            WHERE userID = $0
            """
        )

        async with itx.client.pool.acquire() as conn:
            wallet, bank, bankspace = (
                await conn.fetchone(query, itx.user.id) or (0, 0, 0)
            )

        if not wallet:
            return await itx.response.send_message(
                "You have nothing to deposit."
            )

        available_bankspace = bankspace - bank
        if not available_bankspace:
            return await itx.response.send_message(
                f"Max bankspace of {CURRENCY} **{bankspace:,}** reached.\n"
                f"To hold more, use currency commands and level up more. "
                f"Bank Notes can aid with this."
            )

        available_bankspace = min(wallet, available_bankspace)
        modal = DepositOrWithdraw(
            title="Deposit",
            default_val=available_bankspace,
            view=self
        )

        await itx.response.send_modal(modal)

    @discord.ui.select(
        cls=discord.ui.UserSelect,
        placeholder="Select a registered user",
    )
    async def uslct(self, itx: Interaction, s: discord.ui.UserSelect) -> None:
        self.viewing = s.values[0]
        s.default_values = [discord.Object(id=self.viewing.id)]

        balance = await self.fetch_balance(itx)
        await itx.response.edit_message(embed=balance, view=self)

    @discord.ui.button(emoji="<:refreshPages:1263923160433168414>", row=1)
    async def refresh(self, itx: Interaction, _: discord.ui.Button) -> None:
        balance = await self.fetch_balance(itx)
        await itx.response.edit_message(embed=balance, view=self)

    @discord.ui.button(emoji="<:terminatePages:1263923664433319957>", row=1)
    async def close(self, itx: Interaction, _: discord.ui.Button) -> None:
        self.stop()
        for item in self.children:
            item.disabled = True

        await itx.response.edit_message(view=self)


class HighLow(BaseView):
    """View for the Highlow command and its associated functions."""

    def __init__(self, itx: Interaction, bet: int) -> None:
        super().__init__(itx, transactional=True)

        self.their_bet = bet
        self.true_value = randint(1, 100)
        self.hint_provided = randint(1, 100)

    async def start(self) -> None:
        query = membed(
            "I just chose a secret number between 0 and 100.\n"
            f"Is it *higher* or *lower* than **{self.hint_provided}**?"
        )

        query.set_author(
            name=f"{self.itx.user.name}'s high-low game",
            icon_url=self.itx.user.display_avatar.url
        )

        query.set_footer(
            text="The jackpot button is if you think it is the same!"
        )

        await self.itx.response.send_message(embed=query, view=self)

    async def blurplify(self, clicked: discord.ui.Button) -> None:
        self.stop()
        for item in self.children:
            item.disabled = True
            if item == clicked:
                continue
            item.style = ButtonStyle.secondary

    async def send_win(
        self,
        itx: Interaction,
        button: discord.ui.Button
    ) -> None:
        await self.blurplify(button)

        async with itx.client.pool.acquire() as conn, conn.transaction():
            await end_transaction(conn, self.itx.user.id)

            new_multi = await get_multi_of(itx.user.id, "robux", conn)
            total = add_multi_to_original(new_multi, self.their_bet)

            new_balance, = await update_account(itx.user.id, total, conn)
            hl_win, hl_loss = await update_games(
                itx.user.id,
                game_id=7,
                game_amt=total,
                returning_game_id=8,
                conn=conn
            )

        win_rate = (hl_win / (hl_win + hl_loss)) * 100

        win = itx.message.embeds[0]
        win.colour = discord.Colour.brand_green()
        win.description = (
            f"**You won {CURRENCY} {total:,}!**\n"
            f"Your hint was **{self.hint_provided}**. "
            f"The hidden number was **{self.true_value}**.\n"
            f"Your new balance is {CURRENCY} **{new_balance:,}**.\n"
            f"-# {win_rate:.1f}% of highlow games won."
        )

        win.set_footer(text=f"Multiplier: {new_multi:,}%")

        await itx.response.edit_message(embed=win, view=self)

    async def send_loss(
        self,
        itx: Interaction,
        button: discord.ui.Button
    ) -> None:
        await self.blurplify(button)

        async with itx.client.pool.acquire() as conn, conn.transaction():
            await end_transaction(conn, self.itx.user.id)

            new_amount, = await update_account(
                itx.user.id, -self.their_bet, conn
            )
            hl_loss, hl_win = await update_games(
                itx.user.id,
                game_id=8,
                game_amt=self.their_bet,
                returning_game_id=7,
                conn=conn
            )

        loss_rate = (hl_loss / (hl_loss + hl_win)) * 100

        lose = itx.message.embeds[0]
        lose.remove_footer()
        lose.colour = discord.Colour.brand_red()
        lose.description = (
            f"**You lost {CURRENCY} {self.their_bet:,}!**\n"
            f"Your hint was **{self.hint_provided}**. "
            f"The hidden number was **{self.true_value}**.\n"
            f"Your new balance is {CURRENCY} **{new_amount:,}**.\n"
            f"-# {loss_rate:.1f}% of highlow games lost."
        )

        await itx.response.edit_message(embed=lose, view=self)

    @discord.ui.button(label="Lower", style=ButtonStyle.primary)
    async def low(self, itx: Interaction, btn: discord.ui.Button) -> None:

        if self.true_value < self.hint_provided:
            return await self.send_win(itx, btn)
        await self.send_loss(itx, btn)

    @discord.ui.button(label="JACKPOT!", style=ButtonStyle.primary)
    async def jackpot(self, itx: Interaction, btn: discord.ui.Button) -> None:

        if self.hint_provided == self.true_value:
            return await self.send_win(itx, btn)
        await self.send_loss(itx, btn)

    @discord.ui.button(label="Higher", style=ButtonStyle.primary)
    async def high(self, itx: Interaction, btn: discord.ui.Button) -> None:

        if self.true_value > self.hint_provided:
            return await self.send_win(itx, btn)
        await self.send_loss(itx, btn)


class MultiplierView(RefreshPagination):
    robux_emoji = discord.PartialEmoji.from_str(
        "<:robuxMulti:1263923323088408688>"
    )
    xp_emoji = discord.PartialEmoji.from_str(
        "<:xpMulti:1263924221109731471>"
    )
    luck_emoji = discord.PartialEmoji.from_str(
        "<:luckMulti:1263922104231792710>"
    )

    prompt = "Select a multiplier"
    length = 6
    _multi = {
        "Robux": (0x59DDB3, robux_emoji.url),
        "XP": (0xCDC700, xp_emoji.url),
        "Luck": (0x65D654, luck_emoji.url)
    }

    options = [
        discord.SelectOption(label="Robux", emoji=robux_emoji),
        discord.SelectOption(label="XP", emoji=xp_emoji),
        discord.SelectOption(label="Luck", emoji=luck_emoji)
    ]

    def __init__(
        self,
        itx: Interaction,
        chosen_multiplier: str,
        viewing: UserEntry
    ) -> None:
        super().__init__(itx)

        self.viewing = viewing
        self.chosen_multiplier = chosen_multiplier

        self.embed = discord.Embed()
        self.embed.title = f"{self.viewing.display_name}'s Multipliers"
        self.embed.colour, thumb_url = self._multi[chosen_multiplier]
        self.embed.set_thumbnail(url=thumb_url)

        for option in self.children[-1].options:
            option.default = option.value == chosen_multiplier

    async def get_page(self, refresh: bool = False) -> list[discord.Embed]:
        if refresh:
            await self.format_pages()
            self.index = min(self.index, self.total_pages)

        if not self.total_multi:
            self.embed.description = self._repr()
            return [self.embed.set_footer(text="Empty")]

        offset = ((self.index - 1) * self.length)
        multis = "\n".join(
            f"` {multi} ` \U00002014 {cause}"
            for (multi, cause) in self.multiplier_list[
                offset:offset + self.length
            ]
        )

        self.embed.description = f"{self._repr()}{multis}"
        self.embed.set_footer(text=f"Page {self.index} of {self.total_pages}")
        return [self.embed]

    def _repr(self) -> str:
        """
        Represent a multiplier using proper formatting.
        Edits are in-place, returns None.

        To represent a user with no XP multiplier, shows 1x.

        The units are also converted as necessary based on the type.
        """

        unit, amount = (
            ("%", self.total_multi)
            if self.chosen_multiplier != "XP" else
            ("x", (1 + (self.total_multi / 100)))
        )

        return f"> {self.chosen_multiplier}: **{amount:.2f}{unit}**\n\n"

    async def format_pages(self) -> None:
        async with self.itx.client.pool.acquire() as conn:
            self.total_multi, = await conn.fetchone(
                """
                SELECT CAST(TOTAL(amount) AS INTEGER)
                FROM multipliers
                WHERE (userID IS NULL OR userID = $0)
                AND multi_type = $1
                COLLATE NOCASE
                """, self.viewing.id, self.chosen_multiplier
            )

            self.multiplier_list = []
            if self.total_multi:
                self.multiplier_list = await conn.fetchall(
                    """
                    SELECT amount, description
                    FROM multipliers
                    WHERE (userID IS NULL OR userID = $0)
                    AND multi_type = $1
                    COLLATE NOCASE
                    ORDER BY amount DESC
                    """, self.viewing.id, self.chosen_multiplier
                )

        self.total_pages = self.compute_total_pages(
            len(self.multiplier_list),
            self.length
        )

    @discord.ui.select(options=options, row=0, placeholder="Select multiplier")
    async def scall(self, itx: Interaction, select: discord.ui.Select) -> None:
        self.chosen_multiplier: str = select.values[0]
        self.index = 1

        for option in select.options:
            option.default = option.value == self.chosen_multiplier

        self.embed.colour, thumb_url = self._multi[self.chosen_multiplier]
        self.embed.set_thumbnail(url=thumb_url)

        await self.format_pages()
        await self.edit_page(itx)


class MatchItem(discord.ui.Button):
    """
    A menu to select an item from a list of items provided.

    For use when the user searches for an item with several matches.

    Helps by not having to retype the item name more specifically.
    """

    def __init__(
        self,
        item_id: int,
        item_name: str,
        ie: str
    ) -> None:
        super().__init__(label=item_name, emoji=ie)

        self.item_id = item_id

    async def callback(self, itx: Interaction) -> None:
        self.view.chosen_item = (self.item_id, self.label, self.emoji)
        self.view.stop()

        self.style = ButtonStyle.success
        for item in self.view.children:
            item.disabled = True

        await itx.response.edit_message(view=self.view)


class ItemQuantityModal(discord.ui.Modal):
    def __init__(
        self,
        item_name: str,
        item_cost: int,
        item_emoji: str
    ) -> None:
        super().__init__(title=f"Purchase {item_name}")

        self.item_cost = item_cost
        self.item_name = item_name
        self.ie = item_emoji
        self.activated_coupon = False

    quantity = discord.ui.TextInput(
        label="Quantity",
        placeholder=ROBUX_DESCRIPTION,
        default="1",
        min_length=1,
        max_length=5
    )

    async def begin_purchase(
        self,
        itx: Interaction,
        true_qty: int,
        conn: Connection,
        new_price: int
    ) -> None:

        await update_inv_new(itx.user.id, true_qty, self.item_name, conn)
        new_am, = await update_account(itx.user.id, -new_price, conn)

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
            await update_inv_new(itx.user.id, -1, "Shop Coupon", conn)
            success.add_field(
                name="Additional Info",
                value=(
                    "- <:shopCoupon:1263923497323855907> "
                    "5% Coupon Discount was applied"
                )
            )
        await respond(itx, embed=success)

    async def calculate_discount_price(self, /, itx: Interaction) -> int:
        """Check if the user is eligible for a discount on the item."""

        async with itx.client.pool.acquire() as conn:
            qty, always_use_coupon = await conn.fetchone(
                """
                SELECT inventory.qty, settings.value
                FROM shop
                LEFT JOIN inventory
                    ON shop.itemID = inventory.itemID
                LEFT JOIN settings
                    ON inventory.userID = settings.userID
                    AND settings.setting = 'always_use_coupon'
                WHERE shop.itemID = $0 AND inventory.userID = $1
                """, 8, itx.user.id
            )

        # Check the user has the item
        if not qty:
            return self.item_cost

        # Calculate discount price
        discounted_price = floor((95/100) * self.item_cost)

        # Check they have the setting enabled
        if always_use_coupon:
            self.activated_coupon = True
            return discounted_price

        async with itx.client.pool.acquire() as conn, conn.transaction():
            await declare_transaction(conn, itx.user.id)

        # Ask whether or not they wish to apply the coupon
        prompt = (
            f"Would you like to use your "
            f"<:shopCoupon:1263923497323855907> "
            f"**Shop Coupon** for an additional **5**% off?\n"
            f"(You have **{qty:,}** coupons in total)\n\n"

            f"This will bring the __actual price per unit__ "
            f"down to {CURRENCY} **{discounted_price:,}** if "
            f"you decide to use the coupon."
        )

        self.activated_coupon = await send_prompt(itx, prompt)

        await BaseView.end_transactions(itx)

        if self.activated_coupon is None:
            # Transaction ends, no further cleanup needed
            raise FailingConditionalError("Your purchase was cancelled.")

        if self.activated_coupon:
            return discounted_price
        return self.item_cost

    # ---------------------------------------------------------

    async def on_submit(self, itx: Interaction) -> MaybeWebhook:
        true_qty = RawIntegerTransformer().transform(itx, self.quantity.value)

        # base cost per unit (considering discounts)
        self.item_cost = await self.calculate_discount_price(itx)

        async with itx.client.pool.acquire() as conn:
            current_balance = await fetch_balance(itx.user.id, conn)

            if isinstance(true_qty, str):
                true_qty = current_balance // self.item_cost
                if not true_qty:
                    msg = f"You can't buy a single {self.ie} {self.item_name}"
                    return await respond(itx, msg)
            elif (self.item_cost * true_qty) > current_balance:
                msg = (
                    f"You don't have enough robux to "
                    f"buy **{true_qty:,}x {self.ie} {self.item_name}**."
                )
                return await respond(itx, msg)

            total_price = self.item_cost * true_qty
            can_proceed = await trans_prompt(
                itx,
                conn=conn,
                setting="buying_confirmations",
                prompt=(
                    f"Are you sure you want to buy **{true_qty:,}x {self.ie} "
                    f"{self.item_name}** for **{CURRENCY} {total_price:,}**?"
                    f"\n-# Costs **{CURRENCY} {self.item_cost:,}** per unit."
                )
            )

        async with itx.client.pool.acquire() as conn, conn.transaction():
            if can_proceed is not None:
                await end_transaction(conn, itx.user.id)
                if can_proceed is False:
                    return

            await self.begin_purchase(itx, true_qty, conn, total_price)

    async def on_error(self, itx: Interaction, error: Exception):
        # Catch both custom errors
        if hasattr(error, "cause"):
            return await respond(
                itx,
                error.cause,
                ephemeral=True
            )

        self.stop()
        await itx.response.edit_message(
            content="Something went wrong. Try again later.",
            view=None
        )
        await super().on_error(itx, error)


class ShopItem(discord.ui.Button):
    def __init__(self, item_name: str, cost: int, ie: str, **kwargs) -> None:
        super().__init__(
            style=ButtonStyle.primary,
            emoji=ie,
            label=item_name,
            **kwargs
        )

        self.item_name = item_name
        self.cost = cost
        self.ie = ie

    async def callback(self, itx: Interaction) -> None:

        await itx.response.send_modal(
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
            "1. You don't have that much money in your wallet.\n"
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
        super().__init__(title=title)

        self.their_default = default_val
        self.view = view
        self.amount.default = f"{self.their_default:,}"

    amount = discord.ui.TextInput(
        label="Amount",
        min_length=1,
        max_length=30,
        placeholder=ROBUX_DESCRIPTION
    )

    async def on_submit(self, itx: Interaction) -> None:
        val = RawIntegerTransformer().transform(itx, self.amount.value)

        if isinstance(val, str):
            val = self.their_default
        elif val > self.their_default:
            return await itx.response.send_message(
                self.bigarg_response[self.title],
                ephemeral=True
            )

        if self.title == "Withdraw":
            val = -val

        wallet, bank, bankspace = await self.update_account(itx, val)
        await self.update_embed(itx, wallet, bank, bankspace)

    async def update_account(self, itx: Interaction, val: int) -> tuple:
        async with itx.client.pool.acquire() as conn, conn.transaction():
            # ! flip the value of val if it is a withdrawal
            wallet, bank, bankspace = await conn.fetchone(
                """
                UPDATE accounts
                SET
                    bank = bank + $0,
                    wallet = wallet - $0
                WHERE userID = $1
                RETURNING wallet, bank, bankspace
                """, val, itx.user.id
            )
        return wallet, bank, bankspace

    async def update_embed(
        self,
        itx: Interaction,
        wallet: int,
        bank: int,
        bankspace: int
    ) -> None:
        prcnt_full = (bank / bankspace) * 100

        embed = itx.message.embeds[0]
        embed.set_field_at(0, name="Wallet", value=f"{CURRENCY} {wallet:,}")
        embed.set_field_at(1, name="Bank", value=f"{CURRENCY} {bank:,}")
        embed.set_field_at(
            index=2,
            name="Bankspace",
            value=f"{CURRENCY} {bankspace:,} ({prcnt_full:.2f}% full)"
        )
        embed.timestamp = discord.utils.utcnow()

        self.view.checks(bank, wallet, bankspace-bank)
        await itx.response.edit_message(embed=embed, view=self.view)

    async def on_error(self, itx: Interaction, error: Exception) -> None:
        await itx.client.tree.on_error(itx, error)


class InventoryPaginator(RefreshPagination):
    length = 8
    options = (
        "All",
        "Collectible",
        "Trinket",
        "Sellable",
        "Equipment",
        "Buff",
        "Debuff",
        "Lootbox",
        "Pack"
    )

    options = [
        discord.SelectOption(label=opt_name, value=str(i))
        for i, opt_name in enumerate(options)
    ]

    def __init__(
        self,
        itx: Interaction,
        embed: discord.Embed,
        viewing: UserEntry
    ) -> None:
        super().__init__(itx)

        self.embed = embed
        self.viewing = viewing
        self.data: list[Row] = []

        self.children[-2].default_values = [discord.Object(id=viewing.id)]
        self.applied_filters = [NO_FILTER]

        for option in self.children[-1].options:
            option.default = option.value == "0"

    async def get_page(self, refresh: bool = False) -> list[discord.Embed]:

        if refresh:
            await self.fetch_data()
            self.index = min(self.index, self.total_pages)

        if not self.data:
            self.embed.description = None
            return [self.embed.set_footer(text="Empty")]

        offset = (self.index - 1) * self.length
        self.embed.description = "\n".join(
            f"{ie} **{item_name}** \U00002500 {qty:,}"
            for (item_name, ie, qty) in self.data[
                offset:offset+self.length
            ]
        )

        self.embed.set_footer(text=f"Page {self.index} of {self.total_pages}")
        return [self.embed]

    async def fetch_data(self) -> None:
        if NO_FILTER not in self.applied_filters:
            placeholders = ",".join(("?",)*len(self.applied_filters))
            args = (self.viewing.id, *map(int, self.applied_filters))

            query = (
                f"""
                SELECT shop.itemName, shop.emoji, inventory.qty
                FROM shop
                INNER JOIN inventory
                    ON shop.itemID = inventory.itemID
                LEFT JOIN item_types
                    ON shop.itemType = item_types.id
                WHERE inventory.userID = ?
                AND shop.itemType IN ({placeholders})
                """
            )

        else:
            args = (self.viewing.id,)
            query = (
                """
                SELECT shop.itemName, shop.emoji, inventory.qty
                FROM shop
                INNER JOIN inventory
                    ON shop.itemID = inventory.itemID
                WHERE inventory.userID = ?
                """
            )

        async with self.itx.client.pool.acquire() as conn:
            self.data = await conn.fetchall(query, args)
        self.total_pages = self.compute_total_pages(
            len(self.data), self.length
        )

    def set_all(self, select: discord.ui.Select) -> None:
        self.applied_filters = [NO_FILTER]
        for option in select.options:
            option.default = option.value == "0"

    def set_values(self, select: discord.ui.Select) -> None:
        self.applied_filters = select.values
        for option in select.options:
            option.default = option.value in self.applied_filters

    @discord.ui.select(
        cls=discord.ui.UserSelect,
        placeholder="Select a registered user",
        row=0
    )
    async def inventory_user_select(
        self,
        itx: Interaction,
        select: discord.ui.UserSelect
    ) -> None:
        self.viewing = select.values[0]
        self.index = 1
        select.default_values = [discord.Object(id=self.viewing.id)]

        self.embed.set_author(
            name=f"{self.viewing.name}'s inventory",
            icon_url=self.viewing.display_avatar.url
        )

        await self.fetch_data()
        await self.edit_page(itx)

    @discord.ui.select(
        placeholder="Select a filter",
        max_values=len(options),
        options=options,
        row=1
    )
    async def item_filter_select(
        self,
        itx: Interaction,
        select: discord.ui.Select
    ) -> None:
        self.index = 1

        # this is in the order of item type IDs
        defaults = {opt.value for opt in select.options if opt.default}

        no_filter_default = NO_FILTER in defaults
        no_filter_selected = NO_FILTER in select.values

        len_defaults, len_selected = len(defaults), len(select.values)

        if no_filter_default:

            # ! All is in default and select
            if no_filter_selected:
                # ! Nothing changes when default is same as select

                if not (len_defaults == len_selected == 1):
                    self.applied_filters = select.values.copy()

                    try:
                        self.applied_filters.remove("0")
                    except ValueError:
                        pass

                    select.options[0].default = False
                    for option in select.options[1:]:
                        option.default = option.value in select.values

            # ! All is in default but not in select
            else:
                self.set_values(select)

        # ! All is in select but not default?
        elif no_filter_selected:
            self.set_all(select)

        # ! All is nowhere to be seen
        else:
            self.set_values(select)

        await self.fetch_data()
        await self.edit_page(itx)


user_mention = discord.AllowedMentions.none()
user_mention.users = True

ITEM_CONVERTER = app_commands.Transform[
    tuple[int, str, str], ItemInputTransformer
]
ROBUX_CONVERTER = app_commands.Transform[int | str, RawIntegerTransformer]
TR_QUERY = "SELECT userID FROM transactions WHERE userID = $0"


async def transactional_check(itx: Interaction) -> bool:
    async with itx.client.pool.acquire() as conn:
        data = await conn.fetchone(TR_QUERY, itx.user.id)

    if data is None:
        return True

    await itx.response.send_message(
        WARN_FOR_CONCURRENCY,
        view=error_view,
        ephemeral=True
    )
    return False


async def can_call_out(user_id: int, conn: Connection) -> bool:
    ret, = await conn.fetchone(
        """
        SELECT EXISTS (
            SELECT 1
            FROM accounts
            WHERE userID = $0
        )
        """, user_id
    )
    return not ret


def calculate_exp_for(*, level: int) -> int:
    """Calculate the experience points required for a given level."""
    return ceil((level/0.3)**1.3)


async def update_games(
    user_id: int,
    game_id: int,
    game_amt: int,
    returning_game_id: int,
    conn: Connection
) -> tuple:
    """
    Update the games table with the specified parameters.
    ## Parameters
    - user_id (int): The ID of the user.
    - game_id (int): The ID of the game type to increment.
    - game_amt (int): The monetary amount (not count) to increment by.
    - returning_game_id (int): The ID of the returning game.
    - conn (Connection): The database connection.
    ## Returns:
    - tuple: Contains the count of the current and returning game ID.
    """

    return await conn.fetchone(
        """
        INSERT INTO games (userID, state, value, amount)
        VALUES ($0, $1, 1, $2)
        ON CONFLICT(userID, state)
        DO UPDATE SET
            value = value + excluded.value,
            amount = amount + excluded.amount
        RETURNING
            games.value,
            COALESCE(
                (SELECT value FROM games WHERE state = $3 AND userID = $0), 0
            )
        """, user_id, game_id, game_amt, returning_game_id
    )


async def calc_inv_net(user: UserEntry, conn: Connection) -> int:
    """Calculate the net value of a user's inventory"""

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


async def calc_net_ranking_for(user: UserEntry, conn: Connection) -> int:
    """Calculate the ranking of a user based on their net worth."""

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
                        (
                            SUM(shop.cost * inventory.qty)
                            + COALESCE(money.total_balance, 0)
                        ) AS TotalNetWorth
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
                            (
                                SUM(shop.cost * inventory.qty)
                                + money.total_balance
                            ) AS TotalNetWorth
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


async def open_bank_new(user: UserEntry, conn: Connection) -> bool:
    """
    Register a new user.

    Return `True` on success, `False` otherwise.
    """

    query = (
        """
        INSERT INTO accounts (userID, wallet) VALUES ($0, $1)
        ON CONFLICT DO NOTHING RETURNING userID
        """
    )
    ret = await conn.fetchone(query, user.id, randint(10_000_000, 20_000_000))
    return ret is not None


async def fetch_account_data(
    user_id: int,
    field_name: str,
    conn: Connection,
    *,
    default: Optional[Any] = None
) -> Any:
    """Retrieves a specific field name only from the accounts table."""
    query = f"SELECT {field_name} FROM accounts WHERE userID = $0"
    data, = await conn.fetchone(query, user_id) or (default,)
    return data


async def fetch_balance(
    user_id: int,
    conn: Connection,
    mode: str = "wallet",
    /
) -> int:
    """Shorthand to get balance data of a user."""
    return await fetch_account_data(user_id, mode, conn, default=0)


async def update_account(
    user_id: int,
    amount: float | int,
    conn: Connection,
    mode: str = "wallet"
) -> Any:
    """Update a column in the account table."""

    query = (
        f"""
        UPDATE accounts
        SET {mode} = {mode} + $0
        WHERE userID = $1
        RETURNING {mode}
        """
    )

    return await conn.fetchone(query, amount, user_id)


async def update_wallet_many(conn: Connection, *params_users) -> list[Row]:
    """
    Update the bank of two users at once.
    Useful to transfer money between multiple users at once.

    The parameters are tuples.

    Each contains the amount to be added to the wallet and the user ID.

    Example:
    await update_wallet_many(conn, (100, USER2_ID), (200, USER_ID))
    """

    query = "UPDATE accounts SET wallet = wallet + ? WHERE userID = ?"

    await conn.executemany(query, params_users)

# ------------------ INVENTORY FUNCS ------------------ #

async def fetch_amt_by_id(
    user_id: int,
    item_id: int,
    conn: Connection
) -> int:
    """Fetch the quantity of an item owned by a user based via it's ID."""
    query = "SELECT qty FROM inventory WHERE userID = ? AND itemID = ?"
    val, = await conn.fetchone(query, (user_id, item_id)) or (0,)
    return val


async def fetch_amt_by_name(
    user_id: int,
    item_name: str,
    conn: Connection
) -> bool:
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


async def update_inv_new(
    user_id: int,
    amount: int,
    item_name: str,
    conn: Connection
) -> Optional[Any]:
    """
    Modify a user's inventory.

    If the item quantity is <= 0, delete the row.

    This method should always be called when updating the
    inventory to ensure rows are deleted when necessary.
    """

    item_row = await conn.fetchone(
        "SELECT itemID FROM shop WHERE itemName = $0", item_name
    )

    item_id = item_row[0] if item_row else None

    check_result = await conn.fetchone(
        """
        SELECT qty + ? <= 0
        FROM inventory
        WHERE userID = ? AND itemID = ?
        """, (amount, user_id, item_id)
    )

    if check_result and check_result[0]:
        # If the resulting quantity would be <= 0, delete the row
        await conn.execute(
            "DELETE FROM inventory WHERE userID = ? AND itemID = ?",
            (user_id, item_id)
        )
        return (0,)

    val = await conn.fetchone(
        """
        INSERT INTO inventory (userID, itemID, qty)
        VALUES (?, ?, ?)
        ON CONFLICT(userID, itemID) DO UPDATE SET qty = qty + ?
        RETURNING qty
        """, (user_id, item_id, amount, amount)
    )

    return val


async def update_inv_by_id(
    user_id: int,
    amount: int,
    item_id: int,
    conn: Connection
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
        """, amount, user_id, item_id
    )

    if check_result and check_result[0]:
        # If the resulting quantity would be <= 0, delete the row
        query = "DELETE FROM inventory WHERE userID = $0 AND itemID = $1"
        await conn.execute(query, user_id, item_id)
        return (0,)

    val = await conn.fetchone(
        """
        INSERT INTO inventory (userID, itemID, qty)
        VALUES ($0, $1, $2)
        ON CONFLICT(userID, itemID) DO UPDATE SET qty = qty + $2
        RETURNING qty
        """, user_id, item_id, amount
    )

    return val


# ------------ cooldowns ----------------

def has_cd(cd_timestamp: float) -> Optional[datetime]:
    """
    Check if a cooldown has expired. If not already, return when.

    Assumes the cooldown timestamp is epoch.
    """
    current_time = discord.utils.utcnow().timestamp()
    if current_time > cd_timestamp:
        return
    return datetime.fromtimestamp(cd_timestamp)


async def update_cooldown(
    user_id: int,
    cooldown_type: str,
    new_cd: str,
    conn: Connection
) -> None:
    """
    Update a user's cooldown.

    Raises `sqlite3.IntegrityError` when foreign userID constraint fails.
    """

    await conn.execute(
        """
        INSERT INTO cooldowns (userID, cooldown, until)
        VALUES ($0, $1, $2)
        ON CONFLICT(userID, cooldown) DO UPDATE SET until = $2
        """, user_id, cooldown_type, new_cd
    )

# ----------- END OF ECONOMY FUNCS, HERE ON IS JUST COMMANDS --------------


@app_commands.command(description="View all multipliers within the bot")
@app_commands.describe(
    user="The user whose multipliers you want to see. Defaults to your own.",
    multiplier="The type of multiplier you want to see. Defaults to robux."
)
async def multipliers(
    itx: Interaction,
    user: Optional[UserEntry],
    multiplier: Literal["Robux", "XP", "Luck"] = "Robux"
) -> None:
    user = user or itx.user
    paginator = MultiplierView(itx, multiplier, user)
    await paginator.format_pages()
    await paginator.navigate()


share = app_commands.Group(
    name="share",
    description="Share different assets with others"
)


@share.command(
    name="robux",
    description="Share robux with another user",
    extras={"exp_gained": 5}
)
@app_commands.rename(recipient="user")
@app_commands.describe(
    recipient="The user receiving the robux shared.",
    quantity=ROBUX_DESCRIPTION
)
async def share_robux(
    itx: Interaction,
    recipient: UserEntry,
    quantity: ROBUX_CONVERTER
) -> MaybeWebhook:

    sender = itx.user
    if sender.id == recipient.id:
        return await itx.response.send_message(
            "You can't share with yourself."
        )

    async with itx.client.pool.acquire() as conn:

        actual_wallet = await fetch_balance(sender.id, conn)
        if isinstance(quantity, str):
            quantity = actual_wallet
        elif quantity > actual_wallet:
            return await itx.response.send_message(
                "You don't have that much money to share."
            )

        share_prompt = (
            f"Are you sure you want to share {CURRENCY} "
            f"**{quantity:,}** with {recipient.mention}?"
        )
        can_proceed = await trans_prompt(
            itx,
            prompt=share_prompt,
            setting="share_robux_confirmations",
            conn=conn
        )

    async with itx.client.pool.acquire() as conn, conn.transaction():
        if can_proceed is not None:
            await end_transaction(conn, sender.id)
            if can_proceed is False:
                return

        if await can_call_out(recipient.id, conn):
            return await respond(itx, NOT_REGISTERED)

        await update_wallet_many(
            conn,
            (-int(quantity), sender.id),
            (int(quantity), recipient.id)
        )

    await respond(
        itx,
        f"Shared {CURRENCY} **{quantity:,}** with {recipient.mention}!"
    )


@share.command(
    name="items",
    description="Share items with another user",
    extras={"exp_gained": 5}
)
@app_commands.rename(recipient="user")
@app_commands.describe(
    item=ITEM_DESCRPTION,
    quantity="The amount of this item to share.",
    recipient="The user receiving the item."
)
async def share_items(
    itx: Interaction,
    recipient: UserEntry,
    quantity: app_commands.Range[int, 1],
    item: ITEM_CONVERTER
) -> MaybeWebhook:

    sender = itx.user
    if sender.id == recipient.id:
        return await respond(itx, "You can't share with yourself.")

    item_id, item_name, ie = item
    async with itx.client.pool.acquire() as conn:

        actual_inv_qty = await fetch_amt_by_id(itx.user.id, item_id, conn)

        if actual_inv_qty < quantity:
            return await respond(
                itx, f"You don't have **{quantity}x {ie} {item_name}**."
            )

        share_prompt = (
            f"Are you sure you want to share **{quantity:,} "
            f"{ie} {item_name}** with {recipient.mention}?"
        )
        can_proceed = await trans_prompt(
            itx,
            prompt=share_prompt,
            setting="share_item_confirmations",
            conn=conn
        )

    async with itx.client.pool.acquire() as conn, conn.transaction():
        if can_proceed is not None:
            await end_transaction(conn, sender.id)
            if can_proceed is False:
                return

        if await can_call_out(recipient.id, conn):
            return await respond(itx, NOT_REGISTERED)

        await update_inv_by_id(sender.id, -quantity, item_id, conn)
        await conn.execute(
            """
            INSERT INTO inventory (userID, itemID, qty)
            VALUES ($0, $1, $2)
            ON CONFLICT(userID, itemID) DO UPDATE SET qty = qty + $2
            """, recipient.id, item_id, quantity
        )

    await respond(
        itx,
        f"Shared **{quantity}x {ie} {item_name}** with {recipient.mention}!"
    )


shop = app_commands.Group(
    name="shop",
    description="View items available for purchase"
)


@shop.command(name="view", description="View all the shop items")
async def view_shop(itx: Interaction) -> None:

    async with itx.client.pool.acquire() as conn:
        shop_sorted = await conn.fetchall(
            """
            SELECT itemName, emoji, cost
            FROM shop
            WHERE available = 1
            GROUP BY itemName
            ORDER BY cost
            """
        )

    url = "https://youtu.be/dQw4w9WgXcQ"
    shop_metadata = [
        (
            f"{emote} {name} \U00002500 [{CURRENCY} **{cost:,}**]({url})",
            ShopItem(name, cost, emote, row=i % 2)
        )
        for i, (name, emote, cost) in enumerate(shop_sorted)
    ]

    emb = membed()
    emb.title = "Shop"
    length = 6

    total = PaginationItem.compute_total_pages(
        len(shop_metadata), length
    )
    paginator = PaginationItem(itx, total)

    async def get_page() -> discord.Embed:
        async with itx.client.pool.acquire() as conn:
            wallet = await fetch_balance(itx.user.id, conn)

        if len(paginator.children) > 2:
            backward_btn, forward_btn = paginator.children[:2]
            paginator.clear_items()
            paginator.add_item(backward_btn).add_item(forward_btn)

        offset = (paginator.index - 1) * length
        desc = "\n".join(
            item_metadata[0]
            for item_metadata in shop_metadata[offset:offset+length]
        )

        emb.description = (
            f"> You have {CURRENCY} **{wallet:,}**.\n\n{desc}"
        )

        for _, item_btn in shop_metadata[offset:offset + length]:
            item_btn.disabled = wallet < item_btn.cost
            paginator.add_item(item_btn)

        return emb.set_footer(
            text=f"Page {paginator.index} of {paginator.total_pages}"
        )

    paginator.get_page = get_page
    await paginator.navigate()


@shop.command(description="Sell an item from your inventory")
@app_commands.describe(
    item="The name of the item you want to sell.",
    sell_quantity="The amount of this item to sell. Defaults to 1."
)
async def sell(
    itx: Interaction,
    item: ITEM_CONVERTER,
    sell_quantity: app_commands.Range[int, 1] = 1
) -> None:
    seller = itx.user

    query = (
        """
        SELECT
            (
                SELECT COALESCE(SUM(amount), 0) AS total_amount
                FROM multipliers
                WHERE (userID IS NULL OR userID = $0)
                AND multi_type = 'robux'
            ) AS total_amount,
            COALESCE(inventory.qty, 0) AS qty,
            shop.cost,
            item_types.sellable
        FROM shop
        LEFT JOIN item_types ON shop.itemType = item_types.id
        LEFT JOIN inventory
            ON inventory.itemID = shop.itemID AND inventory.userID = $0
        WHERE shop.itemID = $1
        """
    )

    async with itx.client.pool.acquire() as conn:
        item_id, item_name, ie = item
        multi, qty, cost, sellable = (
            await conn.fetchone(query, seller.id, item_id)
        )

        if not sellable:
            msg = f"You can't sell **{ie} {item_name}**."
            raise FailingConditionalError(msg)
        elif qty < sell_quantity:
            msg = f"You don't have {ie} **{sell_quantity:,}x** {item_name}."
            raise FailingConditionalError(msg)

        # Selling price algorithm must be calculated before prompt is sent
        cost = selling_price_algo(cost*sell_quantity, multi)
        sell_prompt = (
            f"Are you sure you want to sell **{sell_quantity:,}x "
            f"{ie} {item_name}** for **{CURRENCY} {cost:,}**?"
        )

        can_proceed = await trans_prompt(
            itx,
            prompt=sell_prompt,
            setting="selling_confirmations",
            conn=conn
        )

    async with itx.client.pool.acquire() as conn, conn.transaction():
        if can_proceed is not None:
            await end_transaction(conn, seller.id)
            if can_proceed is False:
                return

        await update_inv_new(seller.id, -sell_quantity, item_name, conn)
        await update_account(seller.id, +cost, conn)

    embed = discord.Embed(colour=0xFFFFFF)
    embed.title = f"{seller.display_name}'s Sale Receipt"
    embed.set_footer(text="Thanks for your business.")
    embed.description = (
        f"{seller.mention} sold **{sell_quantity:,}x {ie} {item_name}** "
        f"and got paid {CURRENCY} **{cost:,}**."
    )

    await respond(itx, embed=embed)


@app_commands.command(description="Get more details on a specific item")
@app_commands.describe(item=ITEM_DESCRPTION)
async def item(itx: Interaction, item: ITEM_CONVERTER) -> None:

    query = (
        """
        WITH inventory_data AS (
            SELECT qty, itemID
            FROM inventory
            WHERE itemID = $1 AND userID = $2
        ),
        multiplier_data AS (
            SELECT COALESCE(SUM(amount), 0) AS total_amount
            FROM multipliers
            WHERE (userID IS NULL OR userID = $2)
            AND multi_type = 'robux'
        )
        SELECT
            COALESCE(inventory_data.qty, 0),
            item_types.type_name,
            shop.cost,
            shop.description,
            item_instructions.value,
            shop.emoji,
            item_rarities.colour,
            item_rarities.name,
            shop.available,
            item_types.sellable,
            multiplier_data.total_amount
        FROM shop
        LEFT JOIN inventory_data ON shop.itemID = inventory_data.itemID
        LEFT JOIN item_types ON shop.itemType = item_types.id
        LEFT JOIN item_rarities ON shop.rarity = item_rarities.rarityID
        LEFT JOIN item_instructions ON shop.itemID = item_instructions.itemID
        CROSS JOIN multiplier_data
        WHERE shop.itemID = $1
        """
    )

    async with itx.client.pool.acquire() as conn:
        item_id, item_name, _ = item
        (
            their_count,
            item_type,
            cost,
            description,
            instruction,
            emote,
            item_hex,
            item_rarity,
            available,
            sellable,
            multi
        ) = await conn.fetchone(query, item_id, itx.user.id)
        net = await calc_inv_net(itx.user, conn)

    dynamic_text = f"> *{description}*\n\nYou own **{their_count:,}**"

    if their_count:
        amt = ((their_count*cost)/net)*100
        if amt >= 0.1:
            dynamic_text += f" ({amt:.1f}% of your net worth)"

    instruction = (instruction or "").replace("\\n\\n", "\n\n", 1)
    dynamic_text = f"{dynamic_text}{instruction}"

    emote = discord.PartialEmoji.from_str(emote)

    em = discord.Embed(
        title=item_name,
        description=dynamic_text,
        url="https://www.youtube.com",
        colour=int(item_hex, 16)
    ).set_thumbnail(url=emote.url)

    em.set_footer(text=f"{item_rarity} {item_type}")
    em.add_field(name="Net Value", inline=False, value=f"{CURRENCY} {cost:,}")

    dynamic_text = f"- {"Can" if available else "Cannot"} purchase in shop"
    if sellable:
        new_sell = selling_price_algo(cost, multi)
        dynamic_text += (
            f"\n- Sellable for {CURRENCY} {new_sell:,} "
            f"(with your {multi}% multiplier)"
        )

    em.add_field(name="Additional Info", value=dynamic_text, inline=False)
    await respond(itx, embed=em)


@register_item("Bank Note")
async def increase_bank_space(itx: Interaction, quantity: int) -> None:

    expansion = randint(1_600_000, 6_000_000)
    expansion *= quantity

    async with itx.client.pool.acquire() as conn, conn.transaction():
        new_bankspace, = await conn.fetchone(
            """
            UPDATE accounts
            SET bankspace = bankspace + $0
            WHERE userID = $1
            RETURNING bankspace
            """, expansion, itx.user.id
        )

        args = (itx.user.id, quantity, "Bank Note", conn)
        new_amt, = await update_inv_new(*args)

    embed = membed().set_footer(text=f"{new_amt:,}x bank note left")

    embed.add_field(
        name="Used",
        value=f"{quantity}x <:BankNote:1263919952562487418> Bank Note"
    )

    embed.add_field(
        name="Added Bank Space",
        value=f"{CURRENCY} {expansion:,}"
    )

    embed.add_field(
        name="Total Bank Space",
        value=f"{CURRENCY} {new_bankspace:,}"
    )

    await respond(itx, embed=embed)


@app_commands.command(
    description="Use an item you own from your inventory",
    extras={"exp_gained": 3}
)
@app_commands.describe(
    item=ITEM_DESCRPTION,
    quantity="Amount of items to use, when possible."
)
async def use(
    itx: Interaction,
    item: ITEM_CONVERTER,
    quantity: app_commands.Range[int, 1] = 1
) -> MaybeWebhook:

    item_id, item_name, ie = item
    async with itx.client.pool.acquire() as conn:
        qty = await fetch_amt_by_id(itx.user.id, item_id, conn)

    if not qty:
        msg = (
            f"You don't have a single {ie} "
            f"**{item_name}**, therefore cannot use it."
        )
        return await respond(itx, msg)

    if qty < quantity:
        msg = (
            f"You don't have **{quantity}x {ie} "
            f"{item_name}**, therefore cannot use this many."
        )
        return await respond(itx, msg)

    handler = item_handlers.get(item_name)
    if handler is None:
        msg = (
            f"{ie} **{item_name}** does not have a use yet.\n"
            f"Wait until it does!"
        )
        return await respond(itx, msg)

    await handler(itx, quantity)


async def start_prestige(itx: Interaction, prestige: int) -> None:
    massive_prompt = dedent(
        "Prestiging means losing nearly everything you ever "
        "earnt in the currency system in exchange for increasing "
        "your 'Prestige Level' and upgrading your status.\n\n"
        "Check what you lose by reading the relevant tag.\n"
        "Are you sure you want to prestige?"
    )
    can_proceed = await trans_prompt(itx, massive_prompt)


    async with itx.client.pool.acquire() as conn, conn.transaction():
        await end_transaction(conn, itx.user.id)
        if can_proceed:
            await conn.execute(
                "DELETE FROM inventory WHERE userID = $0", itx.user.id
            )
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
                """, 0, 1, randint(100_000_000, 500_000_000), itx.user.id
            )

            await add_multiplier(
                conn,
                user_id=itx.user.id,
                multi_amount=10,
                multi_type="robux",
                cause="prestige",
                description=f"Prestige {prestige+1}"
            )


@app_commands.command(
    description="Sacrifice currency stats in exchange for incremental perks"
)
async def prestige(itx: Interaction) -> None:
    async with itx.client.pool.acquire() as conn:
        prestige, actual_level, actual_robux = await conn.fetchone(
            """
            SELECT
                prestige,
                level,
                (wallet + bank) AS total_robux
            FROM accounts
            WHERE userID = $0
            """, itx.user.id
        ) or (0, 0, 0)

    if prestige == 10:
        return await itx.response.send_message(
            "You reached the highest prestige!\n"
            "No more perks can be obtained from this command."
        )

    req_robux = (prestige + 1) * 24_000_000
    req_level = (prestige + 1) * 35
    met_check = (actual_robux >= req_robux) and (actual_level >= req_level)

    if met_check:
        return await start_prestige(itx, prestige)

    emote_id = search(r":(\d+)>", PRESTIGE_EMOTES[prestige+1]).group(1)

    actual_robux_progress = (actual_robux / req_robux) * 100
    actual_level_progress = (actual_level / req_level) * 100

    embed = membed(
        f"**Total Balance**\n"
        f"<:replyBranchExt:1263923237016834249> "
        f"{CURRENCY} {actual_robux:,} / {req_robux:,}\n"

        f"<:replyBranch:1263923209921757224> "
        f"` {int(actual_robux_progress):,}% `\n\n"

        f"**Level Required**\n"
        f"<:replyBranchExt:1263923237016834249> "
        f"{actual_level:,} / {req_level:,}\n"

        f"<:replyBranch:1263923209921757224> "
        f"` {int(actual_level_progress):,}% `"
    )

    embed.set_thumbnail(
        url=(
            f"https://cdn.discordapp.com/emojis/"
            f"{emote_id}.png?size=240&quality=lossless"
        )
    )

    embed.set_footer(text="Imagine thinking you can prestige already.")

    await itx.response.send_message(embed=embed)


@app_commands.command(
    description="Guess the number I am thinking of",
    extras={"exp_gained": 3}
)
@app_commands.describe(robux=ROBUX_DESCRIPTION)
async def highlow(itx: Interaction, robux: ROBUX_CONVERTER) -> None:

    async with itx.client.pool.acquire() as conn:
        wallet_amt = await fetch_balance(itx.user.id, conn)
        has_keycard = await fetch_amt_by_id(itx.user.id, item_id=1, conn=conn)

        robux = do_wallet_checks(wallet_amt, robux, has_keycard)

        await declare_transaction(conn, itx.user.id)

    await HighLow(itx, bet=robux).start()


@app_commands.command(
    description="Try your luck on a slot machine",
    extras={"exp_gained": 3}
)
@app_commands.describe(robux=ROBUX_DESCRIPTION)
async def slots(itx: Interaction, robux: ROBUX_CONVERTER) -> None:
    query = (
        """
        SELECT accounts.wallet, COALESCE(inventory.qty, 0)
        FROM accounts
        LEFT JOIN inventory
            ON (accounts.userID = inventory.userID) AND inventory.itemID = 1
        WHERE accounts.userID = $0
        """
    )
    async with itx.client.pool.acquire() as conn:
        wallet_amt, has_keycard = (
            await conn.fetchone(query, itx.user.id) or (0, 0)
        )
    robux = do_wallet_checks(wallet_amt, robux, has_keycard)

    emoji_1, emoji_2, emoji_3 = generate_slot_combination()
    multiplier = find_slot_matches(emoji_1, emoji_2, emoji_3)
    slot_machine = discord.Embed().set_author(
        name=f"{itx.user.name}'s slot machine",
        icon_url=itx.user.display_avatar.url
    )

    if multiplier:
        scaled_bet = add_multi_to_original(multiplier, robux)

        async with itx.client.pool.acquire() as conn, conn.transaction():
            new_wallet, = await update_account(itx.user.id, scaled_bet, conn)
            slot_win, slot_loss = await update_games(
                itx.user.id,
                game_id=3,
                game_amt=scaled_bet,
                returning_game_id=4,
                conn=conn
            )

        win_rate = (slot_win / (slot_win + slot_loss)) * 100

        slot_machine.colour = discord.Color.brand_green()
        slot_machine.description = (
            f"**\U0000003e** {emoji_1} {emoji_2} {emoji_3} **\U0000003c**\n\n"
            f"Multiplier: **{multiplier}%**\n"
            f"Payout: {CURRENCY} **{scaled_bet:,}**.\n"
            f"New Balance: {CURRENCY} **{new_wallet:,}**.\n"
            f"-# {win_rate:.1f}% of slots games won."
        )

    else:
        async with itx.client.pool.acquire() as conn, conn.transaction():
            new_wallet, = await update_account(itx.user.id, -robux, conn)
            slot_loss, slot_win = await update_games(
                itx.user.id,
                game_id=4,
                game_amt=robux,
                returning_game_id=3,
                conn=conn
            )

        prcntl = (slot_loss / (slot_loss + slot_win)) * 100

        slot_machine.colour = discord.Color.brand_red()
        slot_machine.description = (
            f"**\U0000003e** {emoji_1} {emoji_2} {emoji_3} **\U0000003c**\n\n"
            f"You lost: {CURRENCY} **{robux:,}**.\n"
            f"New Balance: {CURRENCY} **{new_wallet:,}**.\n"
            f"-# {prcntl:.1f}% of slots games lost."
        )

    await itx.response.send_message(embed=slot_machine)


@app_commands.command(description="View your currently owned items")
@app_commands.describe(user="The user whose inventory you want to see.")
async def inventory(itx: Interaction, user: Optional[UserEntry]) -> None:

    user = user or itx.user
    embed = membed().set_author(
        name=f"{user.name}'s inventory",
        icon_url=user.display_avatar.url
    )

    paginator = InventoryPaginator(itx, embed, user)
    await paginator.fetch_data()
    await paginator.navigate()


@app_commands.command(description="Get someone's balance")
@app_commands.describe(user="The user to find the balance of.")
async def balance(itx: Interaction, user: Optional[UserEntry]) -> None:
    user = user or itx.user

    balance_view = BalanceView(itx, user)
    balance = await balance_view.fetch_balance(itx)

    await itx.response.send_message(embed=balance, view=balance_view)


async def payout_recurring_income(
    itx: Interaction,
    income_type: str,
    weeks_away: int
) -> None:
    multiplier = RECURRING_MULTIPLIERS[income_type]

    # ! Do they have a cooldown?
    query = "SELECT until FROM cooldowns WHERE userID = $0 AND cooldown = $1"
    async with itx.client.pool.acquire() as conn:
        cd_timestamp = await conn.fetchone(query, itx.user.id, income_type)

    noun_period = income_type[:-2]
    if cd_timestamp is not None:
        cd_timestamp, = cd_timestamp

        user_cd = has_cd(cd_timestamp)
        if isinstance(user_cd, datetime):
            r = discord.utils.format_dt(user_cd, style="R")
            return await itx.response.send_message(
                f"**{itx.user.name}**, your {income_type} robux "
                f"was already redeemed this {noun_period}, try again {r}."
            )

    # ! Try updating the cooldown, giving robux

    async with itx.client.pool.acquire() as conn:
        ret = await update_account(itx.user.id, multiplier, conn)
        if ret is None:
            return await itx.response.send_message(INVOKER_NOT_REGISTERED)

        r = discord.utils.utcnow() + timedelta(weeks=weeks_away)
        await update_cooldown(itx.user.id, income_type, r.timestamp(), conn)
        await conn.commit()

    await itx.response.send_message(
        f"**{itx.user.name}**, you just got {CURRENCY} **{multiplier:,}** "
        f"for checking in this {noun_period}. See you next {noun_period}!"
    )


@app_commands.command(description="Get a weekly injection of robux")
async def weekly(itx: Interaction) -> None:
    await payout_recurring_income(itx, "weekly", weeks_away=1)


@app_commands.command(description="Get a monthly injection of robux")
async def monthly(itx: Interaction) -> None:
    await payout_recurring_income(itx, "monthly", weeks_away=4)


@app_commands.command(description="Get a yearly injection of robux")
async def yearly(itx: Interaction) -> None:
    await payout_recurring_income(itx, "yearly", weeks_away=52)


@app_commands.command(description="Request the deletion of all of your data")
@app_commands.describe(user="The user to erase data from.")
async def resetmydata(itx: Interaction, user: Optional[UserEntry]) -> None:
    user = user or itx.user

    if (user.id != itx.user.id) and (not itx.client.is_owner(itx.user)):
        return await itx.response.send_message(
            "You can only reset your own data."
        )

    who_is = "You are" if user.id == itx.user.id else f"{user.name} is"
    async with itx.client.pool.acquire() as conn:
        tr = conn.transaction()
        await tr.start()

        try:
            await declare_transaction(conn, user.id)
        except IntegrityError:
            await tr.rollback()
            return await itx.response.send_message(
                f"{who_is} not registered."
            )
        else:
            await tr.commit()

    view = ConfirmResetData(itx, user)
    await itx.response.send_message(view.content, view=view)


@app_commands.command(description="Withdraw robux from your bank account")
@app_commands.describe(robux=ROBUX_DESCRIPTION)
async def withdraw(itx: Interaction, robux: ROBUX_CONVERTER) -> None:

    async with itx.client.pool.acquire() as conn:
        bank_amt = await fetch_balance(itx.user.id, conn, "bank")

    if not bank_amt:
        return await itx.response.send_message(
            "You have nothing to withdraw."
        )

    if isinstance(robux, str):
        robux = bank_amt
    elif robux > bank_amt:
        return await itx.response.send_message(
            f"You only have {CURRENCY} **{bank_amt:,}** in your bank."
        )

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

    async with itx.client.pool.acquire() as conn, conn.transaction():
        wallet_new, bank_new = await conn.fetchone(query, robux, itx.user.id)

    embed = membed()
    embed.add_field(
        name="Withdrawn",
        value=f"{CURRENCY} {robux:,}",
        inline=False
    )
    embed.add_field(
        name="Current Wallet Balance",
        value=f"{CURRENCY} {wallet_new:,}"
    )
    embed.add_field(
        name="Current Bank Balance",
        value=f"{CURRENCY} {bank_new:,}"
    )

    await itx.response.send_message(embed=embed)


@app_commands.command(description="Deposit robux into your bank account")
@app_commands.describe(robux=ROBUX_DESCRIPTION)
async def deposit(itx: Interaction, robux: ROBUX_CONVERTER) -> None:

    query = "SELECT wallet, bank, bankspace FROM accounts WHERE userID = $0"
    async with itx.client.pool.acquire() as conn:
        wallet_amt, bank, bankspace = (
            await conn.fetchone(query, itx.user.id) or (0, 0, 0)
        )

    if not wallet_amt:
        return await itx.response.send_message(
            "You have nothing to deposit."
        )

    can_deposit = bankspace - bank
    if can_deposit <= 0:
        return await itx.response.send_message(
            f"Max bankspace of {CURRENCY} **{bankspace:,}** reached.\n"
            f"To hold more, use currency commands and level up more. "
            f"Bank Notes can aid with this."
        )

    if isinstance(robux, str):
        robux = min(wallet_amt, can_deposit)
    elif robux > wallet_amt:
        return await itx.response.send_message(
            f"You only have {CURRENCY} **{wallet_amt:,}** "
            f"in your wallet right now."
        )

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

    async with itx.client.pool.acquire() as conn, conn.transaction():
        wallet_new, bank_new = await conn.fetchone(query, robux, itx.user.id)

    embed = membed()
    embed.add_field(
        name="Deposited",
        value=f"{CURRENCY} {robux:,}",
        inline=False
    )
    embed.add_field(
        name="Current Wallet Balance",
        value=f"{CURRENCY} {wallet_new:,}"
    )
    embed.add_field(
        name="Current Bank Balance",
        value=f"{CURRENCY} {bank_new:,}"
    )

    await itx.response.send_message(embed=embed)


@app_commands.rename(host="user")
@app_commands.describe(host="The user you want to rob money from.")
@app_commands.command(
    description="Attempt to steal from someone's pocket",
    extras={"exp_gained": 4}
)
async def rob(itx: Interaction, host: UserEntry) -> None:
    robber = itx.user

    if robber.id == host.id:
        return await itx.response.send_message(
            "Seems pretty foolish to steal from yourself."
        )

    if host.bot:
        return await itx.response.send_message(
            "You are not allowed to steal from bots, back off my kind."
        )

    if not itx.is_guild_integration():
        return await itx.response.send_message("You cannot rob people here.")

    query = (
        """
        SELECT wallet, settings.value
        FROM accounts
        LEFT JOIN settings
            ON accounts.userID = settings.userID
            AND settings.setting = 'passive_mode'
        WHERE accounts.userID = $0
        """
    )

    query2 = (
        """
        SELECT wallet, settings.value
        FROM accounts
        LEFT JOIN settings
            ON accounts.userID = settings.userID
            AND settings.setting = 'passive_mode'
        WHERE accounts.userID = $0
        """
    )

    async with itx.client.pool.acquire() as conn:
        robber_wallet, robber_passive_mode = (
            await conn.fetchone(query, robber.id) or (0, 0)
        )
        host_wallet, host_passive_mode = (
            await conn.fetchone(query2, host.id) or (0, 0)
        )

    if robber_passive_mode:
        return await itx.response.send_message(
            "You are in passive mode! If you want to rob, turn that off!"
        )

    if host_passive_mode:
        return await itx.response.send_message(
            f"{host.name} is in passive mode, you cannot rob them!"
        )

    if host_wallet < 1_000_000:
        return await itx.response.send_message(
            f"{host.name} does not even have {CURRENCY} **1,000,000**."
        )

    if robber_wallet < 10_000_000:
        return await itx.response.send_message(
            f"You need at least {CURRENCY} **10,000,000** first."
        )

    fifty50, = choices((0, 1), weights=(49, 51))

    if fifty50:
        fine = randint(min(50_000, robber_wallet), robber_wallet)

        await itx.response.send_message(
            f"You got caught and paid {host.mention} {CURRENCY} **{fine:,}**."
        )

        async with itx.client.pool.acquire() as conn, conn.transaction():
            await update_wallet_many(
                conn, (fine, host.id), (-fine, robber.id)
            )
        return

    amt_stolen = randint(min(1_000_000, robber_wallet), robber_wallet)
    amt_dropped = floor((randint(1, 25) / 100) * amt_stolen)
    total = amt_stolen - amt_dropped
    percent_stolen = int((total/amt_stolen) * 100)

    async with itx.client.pool.acquire() as conn, conn.transaction():
        await update_wallet_many(
            conn, (-amt_stolen, host.id), (total, robber.id)
        )

    embed = membed()
    if percent_stolen <= 25:
        embed.title = "You stole a TINY portion!"
        embed.set_thumbnail(url="https://i.imgur.com/TA5j8d8.png")
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
        f"{CURRENCY} {amt_stolen:,} "
        f"(but dropped {CURRENCY} {amt_dropped:,} while escaping)"
    )

    embed.set_footer(text=f"You stole {CURRENCY} {total:,} in total")
    await itx.response.send_message(embed=embed)


def do_wallet_checks(
    wallet: int,
    bet : str | int,
    keycard: bool = False
) -> int:
    """
    Reusable wallet checks that are common amongst most gambling commands.

    Bet must be transformed an integer or shorthand via the `ROBUX_CONVERTER`
    """

    min_bet, max_bet = (
        (MIN_BET_KEYCARD, MAX_BET_KEYCARD) if keycard
        else (MIN_BET_WITHOUT, MIN_BET_KEYCARD)
    )

    if isinstance(bet, str):
        bet = min(max_bet, wallet)
    elif bet > wallet:
        raise FailingConditionalError(
            f"You don't have {CURRENCY} **{bet:,}** to spare."
        )

    # Cannot be an elif
    if (bet < min_bet) or (bet > max_bet):
        raise FailingConditionalError(
            f"You cannot bet less than "
            f"{CURRENCY} **{min_bet:,}**.\n"

            f"You also cannot bet anything more "
            f"than {CURRENCY} **{max_bet:,}**."
        )

    return bet


@app_commands.command(
    description="Bet your robux on a dice roll",
    extras={"exp_gained": 3}
)
@app_commands.describe(robux=ROBUX_DESCRIPTION)
async def bet(itx: Interaction, robux: ROBUX_CONVERTER) -> None:

    query = (
        """
        SELECT
            COALESCE(inventory.qty, 0),
            COALESCE(accounts.wallet, 0),
            CAST(TOTAL(multipliers.amount) AS INTEGER)
        FROM accounts
        INNER JOIN multipliers
            ON (accounts.userID = multipliers.userID)
            OR multipliers.userID IS NULL
        INNER JOIN inventory
            ON accounts.userID = inventory.userID
            AND inventory.itemID = 1
        WHERE accounts.userID = $0 AND multipliers.multi_type = 'robux'
        """
    )

    user = itx.user
    async with itx.client.pool.acquire() as conn:
        keycard_qty, wallet_amt, pmulti = await conn.fetchone(query, user.id)
    robux = do_wallet_checks(wallet_amt, robux, keycard_qty)

    their_roll, = choices(
        population=(1, 2, 3, 4, 5, 6),
        weights=(37 / 3, 37 / 3, 37 / 3, 63 / 3, 63 / 3, 63 / 3)
    )

    bot_roll, = choices(
        population=(1, 2, 3, 4, 5, 6),
        weights=(65 / 4, 65 / 4, 65 / 4, 65 / 4, 35 / 2, 35 / 2)
    )

    embed = discord.Embed().set_author(
        name=f"{user.name}'s gambling game",
        icon_url=user.display_avatar.url
    )

    if their_roll > bot_roll:
        scaled_bet = add_multi_to_original(pmulti, robux)
        async with itx.client.pool.acquire() as conn, conn.transaction():
            new_balance, = await update_account(user.id, scaled_bet, conn)
            bet_win, bet_loss = await update_games(
                user.id,
                game_id=1,
                game_amt=scaled_bet,
                returning_game_id=2,
                conn=conn
            )

        win_rate = (bet_win / (bet_win + bet_loss)) * 100

        embed.set_footer(text=f"Multiplier: {pmulti:,}%")
        embed.colour = discord.Color.brand_green()
        embed.description = (
            f"**You've rolled higher!**\n"
            f"You won {CURRENCY} **{scaled_bet:,}**.\n"
            f"You now have {CURRENCY} **{new_balance:,}**.\n"
            f"-# {win_rate:.1f}% of bet games won."
        )

    elif their_roll == bot_roll:
        embed.colour = discord.Color.yellow()
        embed.description = "**Tie.** You lost nothing nor gained anything!"

    else:
        async with itx.client.pool.acquire() as conn, conn.transaction():
            new_wallet, = await update_account(user.id, -robux, conn)
            bet_loss, bet_win = await update_games(
                user.id,
                game_id=2,
                game_amt=robux,
                returning_game_id=1,
                conn=conn
            )

        loss_rate = (bet_loss / (bet_loss + bet_win)) * 100

        embed.colour = discord.Color.brand_red()
        embed.description = (
            f"**You've rolled lower!**\n"
            f"You lost {CURRENCY} **{robux:,}**.\n"
            f"You now have {CURRENCY} **{new_wallet:,}**.\n"
            f"-# {loss_rate:.1f}% of bet games lost."
        )

    embed.add_field(name=user.name, value=f"Rolled `{their_roll}`")
    embed.add_field(name=itx.client.user.name, value=f"Rolled `{bot_roll}`")

    await itx.response.send_message(embed=embed)


@sell.autocomplete("item")
@share_items.autocomplete("item")
async def owned_item_ac(itx: Interaction, current: str) -> list[Choice[str]]:
    query = (
        """
        SELECT itemName
        FROM shop
        INNER JOIN inventory ON shop.itemID = inventory.itemID
        WHERE itemName LIKE '%' || ? || '%' AND userID = ?
        COLLATE NOCASE
        ORDER BY INSTR(itemName, ?)
        LIMIT 25
        """
    )

    async with itx.client.pool.acquire() as conn:
        options = await conn.fetchall(query, (current, itx.user.id, current))

    return [Choice(name=option, value=option) for (option,) in options]


_cache: LRU[str, list[Choice[str]]] = LRU(1024)


@use.autocomplete("item")
@item.autocomplete("item")
async def item_ac(itx: Interaction, current: str) -> list[Choice[str]]:
    if (val:=_cache.get(current, None)) is not None:
        return val

    query = (
        """
        SELECT itemName
        FROM shop
        WHERE itemName LIKE '%' || ? || '%'
        COLLATE NOCASE
        ORDER BY INSTR(itemName, ?)
        LIMIT 25
        """
    )

    async with itx.client.pool.acquire() as conn:
        options = await conn.fetchall(query, (current, current))

    _cache[current] = r = [
        Choice(name=option, value=option)
        for (option,) in options
    ]
    return r


cmds = [
    multipliers, share, shop, item, use, prestige,
    highlow, slots, inventory, balance, weekly,
    monthly, yearly, resetmydata, withdraw, deposit,
    rob, bet
]

for app_cmd in cmds:
    app_cmd: app_commands.Group | app_commands.Command

    if not isinstance(app_cmd, app_commands.Group):
        app_cmd.add_check(transactional_check)
        continue

    for subcmd in app_cmd.commands:
        subcmd.add_check(transactional_check)

exports = BotExports(cmds)