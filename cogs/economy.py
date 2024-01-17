from other.utilities import *
from asyncio import sleep, TimeoutError as asyncTE
from string import ascii_letters, digits
from shelve import open as open_shelve
import datetime
import discord
from other.pagination import Pagination
from ImageCharts import ImageCharts
from discord.ext import commands
from math import floor
from random import randint, choices, choice, sample, shuffle
from pluralizer import Pluralizer
from discord import app_commands, SelectOption
import json
from asqlite import Connection as asqlite_Connection
from typing import Optional, Literal, Any, Union, List
from tatsu.wrapper import ApiWrapper


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
BANK_COLUMNS = ["bank", "pmulti", "bounty", "prestige"]
invoker_ch = int()
participants = set()
DOWN = True
UNIQUE_BADGES = {
            992152414566232139: "<:e1_stafff:1145039666916110356>",
            546086191414509599: "<:in_power:1153754243220647997>",
            1134123734421217412: "<:e1_bughunterGold:1145053225414832199>",
            1154092136115994687: "<:e1_bughunterGreen:1145052762351095998>",
            1047572530422108311: "<:cc:1146092310464049203>"}
SERVER_MULTIPLIERS = {
    829053898333225010: 120,
    780397076273954886: 160,
    1144923657064419398: 6969}
INV_TABLE_NAME = "inventory"
FEEDBACK_GLOBAL = 'Have complaints or suggestions? **Let us know:** </feedback:1172898645058785334>.'
ARROW = "<:arrowe:1180428600625877054>"
CURRENCY = '<:robux:1146394968882151434>'
PREMIUM_CURRENCY = '<:robuxpremium:1174417815327998012>'
ERR_UNREASON = membed('You are unqualified to use this command. Possible reasons include '
                      'insufficient balance and/or unreasonable input.')
DOWNM = membed('This command is currently outdated and will be made available at a later date.')
NOT_REGISTERED = membed('Could not find account associated with the user provided.')

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
     "info": "An item that changes use often. Its transformative functions change to match the seasonality of the year.",
     "url": "https://i.imgur.com/WX9mbie.png", "rarity": "**Rare** <:rare:1166316365892825138>", "qn": "dynamic_item",
     "emoji": "<:dynamic:1166082288069648394>"},

    {"name": "Resistor", "cost": 18102892402, "id": 4,
     "info": "No one knows how this works because no one has ever purchased "
             "this item. May cause distress to certain individuals upon purchase.",
     "url": "https://i.imgur.com/ggO9QbL.png", "rarity": "**Luxurious** <:luxurious:1166316420125163560>",
     "emoji": "<:resistor:1165934607447887973>"},

    {"name": "Clan_License", "cost": 20876994182, "id": 5,
     "info": "Create your own clan. It costs a fortune, but with it brings a lot of privileges exclusive to clan members.",
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


with open('C:\\Users\\georg\\PycharmProjects\\c2c\\cogs\\times.json') as file_name_thi:
    times = json.load(file_name_thi)

with open('C:\\Users\\georg\\PycharmProjects\\c2c\\cogs\\claimed.json') as file_name_four:
    claims = json.load(file_name_four)


def save_times():
    with open('C:\\Users\\georg\\PycharmProjects\\c2c\\cogs\\times.json', 'w') as file_name_seven:
        json.dump(times, file_name_seven, indent=4)

def acknowledge_claim():
    with open('C:\\Users\\georg\\PycharmProjects\\c2c\\cogs\\claimed.json', 'w') as file_name_nine:
        json.dump(claims, file_name_nine, indent=4)


def calculate_hand(hand):
    aces = hand.count(11)
    total = sum(hand)

    while total > 21 and aces > 0:
        total -= 10
        aces -= 1

    return total


def make_plural(word, count):
    mp = Pluralizer()
    return mp.pluralize(word=word, count=count)

def plural_for_own(count: int) -> str:
    """Only use this pluralizer if the term is 'own'. Nothing else."""
    if count != 1:
        return "own"
    else:
        return "owns"

def return_rand_str():
    all_char = ascii_letters + digits
    password = "".join(choice(all_char) for _ in range(randint(10, 11)))
    return password


def format_number_short(number):
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


def fmt_timestamp(year_inp: int, month_inp: int, day_inp: int, hour_inp: int, min_inp: Optional[int]
                  , fmt_style: Literal['f', 'F', 'd', 'D', 't', 'T', 'R']):
    """A helper function to format a :class:`datetime.datetime` for presentation within Discord.

        This allows for a locale-independent way of presenting data using Discord specific Markdown.

        +-------------+----------------------------+-----------------+
        |    Style    |       Example Output       |   Description   |
        +=============+============================+=================+
        | t           | 22:57                      | Short Time      |
        +-------------+----------------------------+-----------------+
        | T           | 22:57:58                   | Long Time       |
        +-------------+----------------------------+-----------------+
        | d           | 17/05/2016                 | Short Date      |
        +-------------+----------------------------+-----------------+
        | D           | 17 May 2016                | Long Date       |
        +-------------+----------------------------+-----------------+
        | f (default) | 17 May 2016 22:57          | Short Date Time |
        +-------------+----------------------------+-----------------+
        | F           | Tuesday, 17 May 2016 22:57 | Long Date Time  |
        +-------------+----------------------------+-----------------+
        | R           | 5 years ago                | Relative Time   |
        +-------------+----------------------------+-----------------+

        Note that the exact output depends on the user's locale setting in the client. The example output
        presented is using the ``en-GB`` locale.

        -----------

        Returns
        --------
        :class:`str`
            The formatted string.
        """

    if min_inp is None:
        min_inp = 0
    period = datetime.datetime(year=year_inp, month=month_inp, day=day_inp, hour=hour_inp, minute=min_inp)

    period_fmt = discord.utils.format_dt(period, fmt_style)
    return period_fmt


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
    """Modify custom profile attributes (or keys) of any given discord user. If "delete" is used on a key that does not exist, returns ``0``
    :param typemod: type of modification to the profile. could be ``update`` to update an already existing key, or ``create`` to create a new key or ``delete`` to delete a key
    :param key: The key to modify/delete.
    :param new_value: The new value to replace the old value with. For a typemod of ``delete``, this argument will not matter at all, since only the key name is required to delete a key."""
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
            await self.msg.edit(content="Timed out waiting for a response. The operation was cancelled.", view=None) 

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Make sure the original user that called the interaction is only in control, no one else."""
        if interaction.user == self.interaction.user:
            return True
        else:
            emb = membed(
                f"{self.interaction.user.mention} can only give consent to perform this action.")
            await interaction.response.send_message(embed=emb, ephemeral=True) 
            return False

    @discord.ui.button(label='Confirm', style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):

        self.timed_out = False
        for item in self.children:
            item.disabled = True

        tables_to_delete = [BANK_TABLE_NAME, INV_TABLE_NAME, COOLDOWN_TABLE_NAME, SLAY_TABLE_NAME]
        async with self.client.pool_connection.acquire() as conn: 
            conn: asqlite_Connection
            for table in tables_to_delete:
                await conn.execute(f"DELETE FROM `{table}` WHERE userID = ?", (self.member.id,))

            await conn.commit()
            await interaction.message.edit(
                content="You're now basically out of our database, we no longer have any EUD from you (end user data).",
                view=None)

    @discord.ui.button(label='Deny', style=discord.ButtonStyle.green)
    async def deny(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.timed_out = False
        for item in self.children:
            item.disabled = True
        await interaction.message.edit(content="The operation was cancelled, as per-request.", view=None)


class BlackjackUi(discord.ui.View):
    """View for the blackjack command and its associated functions."""

    def __init__(self, interaction: discord.Interaction, client: commands.Bot):
        self.interaction = interaction
        self.client: commands.Bot = client
        self.finished = False
        super().__init__(timeout=30)

    async def disable_all_items(self) -> None:
        for item in self.children:
            item.disabled = True

    async def on_timeout(self) -> None:
        await self.disable_all_items()
        if not self.finished:

            namount = self.client.games[self.interaction.user.id][-1]  
            namount = floor(((130 / 100) * namount))
            del self.client.games[self.interaction.user.id]  

            async with self.client.pool_connection.acquire() as conn:  
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

            return await self.message.edit( 
                content=None, embed=losse, view=self)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user == self.interaction.user:
            return True
        else:
            emb = discord.Embed(
                description=f"This game is being held under {self.interaction.user.name}'s name. Not yours.",
                color=0x2F3136
            )
            await interaction.response.send_message(embed=emb, ephemeral=True) 
            return False

    @discord.ui.button(label='Hit', style=discord.ButtonStyle.blurple)
    async def hit_bj(self, interaction: discord.Interaction, button: discord.ui.Button):

        namount = self.client.games[interaction.user.id][-1] 
        deck = self.client.games[interaction.user.id][0]  
        player_hand = self.client.games[interaction.user.id][1]  

        player_hand.append(deck.pop())
        self.client.games[interaction.user.id][-2].append(display_user_friendly_card_format(player_hand[-1])) 
        player_sum = sum(player_hand)

        if player_sum > 21:

            await self.disable_all_items()
            self.finished = True
            dealer_hand = self.client.games[interaction.user.id][2] 
            d_fver_p = [num for num in self.client.games[interaction.user.id][-2]] 
            d_fver_d = [num for num in self.client.games[interaction.user.id][-3]] 
            del self.client.games[interaction.user.id] 
            async with self.client.pool_connection.acquire() as conn:  
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
                embed.add_field(name=f"{interaction.guild.me.name} (Dealer)", value=f"**Cards** - {' '.join(d_fver_d)}\n"
                                                                            f"**Total** - `{sum(dealer_hand)}`")

                embed.set_author(name=f"{interaction.user.name}'s losing blackjack game",
                                 icon_url=interaction.user.display_avatar.url)
                await interaction.response.edit_message(content=None, embed=embed, view=None) 

        elif sum(player_hand) == 21:

            self.finished = True
            await self.disable_all_items()

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
                await interaction.response.edit_message(content=None, embed=win, view=None) 

        else:

            player_hand = self.client.games[interaction.user.id][1] 
            d_fver_p = [number for number in self.client.games[interaction.user.id][-2]] 
            necessary_show = self.client.games[interaction.user.id][-3][0] 
            ts = sum(player_hand)

            prg = discord.Embed(colour=0x2B2D31,
                                description=f"**Your move. Your hand is now {ts}**.")
            prg.add_field(name=f"{interaction.user.name} (Player)", value=f"**Cards** - {' '.join(d_fver_p)}\n"
                                                                    f"**Total** - `{ts}`")
            prg.add_field(name=f"{interaction.guild.me.name} (Dealer)", value=f"**Cards** - {necessary_show} `?`\n"
                                                                      f"**Total** - ` ? `")

            prg.set_footer(text="K, Q, J = 10  |  A = 1 or 11")
            prg.set_author(icon_url=interaction.user.display_avatar.url, name=f"{interaction.user.name}'s blackjack game")
            await interaction.response.edit_message( 
                content="Press **Hit** to hit, **Stand** to finalize your deck or "
                        "**Forfeit** to end your hand prematurely.", embed=prg, view=self)

    @discord.ui.button(label='Stand', style=discord.ButtonStyle.blurple)
    async def stand_bj(self, interaction: discord.Interaction, button: discord.ui.Button):

        await self.disable_all_items()

        deck = self.client.games[interaction.user.id][0] 
        player_hand = self.client.games[interaction.user.id][1] 
        dealer_hand = self.client.games[interaction.user.id][2] 
        namount = self.client.games[interaction.user.id][-1] 

        dealer_total = calculate_hand(dealer_hand)

        while dealer_total < 17:
            popped = deck.pop()

            dealer_hand.append(popped)

            self.client.games[interaction.user.id][-3].append(display_user_friendly_card_format(popped)) 

            dealer_total = calculate_hand(dealer_hand)

        player_sum = sum(player_hand)
        d_fver_p = self.client.games[interaction.user.id][-2] 
        d_fver_d = self.client.games[interaction.user.id][-3] 
        del self.client.games[interaction.user.id] 

        if dealer_total > 21:
            self.finished = True
            async with self.client.pool_connection.acquire() as conn:  
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

            win.set_author(icon_url=interaction.user.display_avatar.url, name=f"{interaction.user.name}'s winning blackjack game")
            await interaction.response.edit_message(content=None, embed=win, view=None) 

        elif dealer_total > sum(player_hand):
            self.finished = True
            async with self.client.pool_connection.acquire() as conn:  
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
            loser.set_author(icon_url=interaction.user.display_avatar.url, name=f"{interaction.user.name}'s losing blackjack game")
            await interaction.response.edit_message(content=None, embed=loser, view=None) 

        elif dealer_total < sum(player_hand):
            self.finished = True
            async with self.client.pool_connection.acquire() as conn:  
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
                                description=f"**You win! You stood with a higher score (`{player_sum}`) than the dealer (`{dealer_total}`).**\n"
                                            f"You won {CURRENCY}**{amount_after_multi:,}**. "
                                            f"You now have {CURRENCY}**{new_amount_balance[0]:,}**.\n"
                                            f"You won {prctnw}% of the games.")
            win.add_field(name=f"{interaction.user.name} (Player)", value=f"**Cards** - {' '.join(d_fver_p)}\n"
                                                                    f"**Total** - `{player_sum}`")
            win.add_field(name=f"{interaction.guild.me.name} (Dealer)", value=f"**Cards** - {' '.join(d_fver_d)}\n"
                                                                      f"**Total** - `{dealer_total}`")
            win.set_author(icon_url=interaction.user.display_avatar.url, name=f"{interaction.user.name}'s winning blackjack game")
            await interaction.response.edit_message(content=None, embed=win, view=None) 
        else:
            self.finished = True
            async with self.client.pool_connection.acquire() as conn:  
                conn: asqlite_Connection
                wallet_amt = await Economy.get_wallet_data_only(interaction.user, conn)
            tie = discord.Embed(colour=discord.Colour.yellow(),
                                description=f"**Tie! You tied with the dealer.**\n"
                                            f"Your wallet hasn't changed! You have {CURRENCY}**{wallet_amt:,}** still.")
            tie.add_field(name=f"{interaction.user.name} (Player)", value=f"**Cards** - {' '.join(d_fver_p)}\n"
                                                                    f"**Total** - `{player_sum}`")
            tie.add_field(name=f"{interaction.guild.me.name} (Dealer)", value=f"**Cards** - {' '.join(d_fver_d)}\n"
                                                                      f"**Total** - `{dealer_total}`")
            tie.set_author(icon_url=interaction.user.display_avatar.url, name=f"{interaction.user.name}'s blackjack game")
            await interaction.response.edit_message(content=None, embed=tie, view=None) 

    @discord.ui.button(label='Forfeit', style=discord.ButtonStyle.blurple)
    async def forfeit_bj(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.finished = True
        await self.disable_all_items()
        namount = self.client.games[interaction.user.id][-1] 
        namount = namount // 2
        dealer_total = sum(self.client.games[interaction.user.id][2]) 
        player_sum = sum(self.client.games[interaction.user.id][1]) 
        d_fver_p = self.client.games[interaction.user.id][-2] 
        d_fver_d = self.client.games[interaction.user.id][-3] 

        del self.client.games[interaction.user.id] 

        async with self.client.pool_connection.acquire() as conn:  
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

        await interaction.response.edit_message(content=None, embed=loser, view=None) 

class HighLow(discord.ui.View):
    """View for the Highlow command and its associated functions."""

    def __init__(self, interaction: discord.Interaction, client: commands.Bot, hint_provided: int, bet: int, value: int):
        self.interaction = interaction
        self.client = client
        self.true_value = value
        self.hint_provided = hint_provided
        self.their_bet = bet
        super().__init__(timeout=30)

    async def make_clicked_blurple_only(self, clicked_button: discord.ui.Button):
        for item in self.children:
            item.disabled = True
            if item == clicked_button:
                clicked_button.style = discord.ButtonStyle.blurple
                continue
            item.style = discord.ButtonStyle.gray

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user == self.interaction.user:
            return True

        await interaction.response.send_message( 
            content=f"This is not your highlow game {interaction.user.display_name}! Make one yourself.",
            ephemeral=True, delete_after=5.5)
        return False

    @discord.ui.button(label='Lower', style=discord.ButtonStyle.blurple)
    async def low(self, interaction: discord.Interaction, button: discord.ui.Button):
        async with self.client.pool_connection.acquire() as conn: 
            conn: asqlite_Connection

            if self.true_value < self.hint_provided:

                pmulti = await Economy.get_pmulti_data_only(interaction.user, conn)
                new_multi = SERVER_MULTIPLIERS.setdefault(interaction.guild.id, 0) + pmulti[0]
                total = floor((new_multi/100)*self.their_bet)
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
                await interaction.response.edit_message(embed=win, view=self)
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
                await interaction.response.edit_message(embed=lose, view=self)

    @discord.ui.button(label='JACKPOT!', style=discord.ButtonStyle.blurple)
    async def jackpot(self, interaction: discord.Interaction, button: discord.ui.Button):
        async with self.client.pool_connection.acquire() as conn: 
            conn: asqlite_Connection

            if self.hint_provided == self.true_value:

                pmulti = await Economy.get_pmulti_data_only(interaction.user, conn)
                new_multi = SERVER_MULTIPLIERS.setdefault(interaction.guild.id, 0) + pmulti[0]
                total = floor((new_multi+1000 / 100) * self.their_bet)
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
                await interaction.response.edit_message(embed=win, view=self)
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

                await interaction.response.edit_message(embed=lose, view=self)

    @discord.ui.button(label='Higher', style=discord.ButtonStyle.blurple)
    async def high(self, interaction: discord.Interaction, button: discord.ui.Button):
        async with self.client.pool_connection.acquire() as conn: 
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
                await interaction.response.edit_message(embed=win, view=self)
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
                await interaction.response.edit_message(embed=lose, view=self)


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
            if res == 0:
                return await interaction.response.send_message(  
                    embed=membed("<:warning_nr:1195732155544911882> You don't have a bio yet. Add one first."))

            else:
                return await interaction.response.send_message(  
                    embed=membed(f'## <:trim:1195732275283894292> Your bio has been removed.\n'
                                 f'The changes have taken effect immediately.'))


        phrases = "updated your" if get_profile_key_value(f"{interaction.user.id} bio") is not None else "created a new"
        modify_profile("update", f"{interaction.user.id} bio", self.bio.value)

        return await interaction.response.send_message( 
            embed=membed(
                f"## <:overwrite:1195729262729240666> Successfully {phrases} bio.\n"
                f"It is now:\n"
                f"> {self.bio.value or 'Empty: It should be removed, no input was given.'}\n"
                f"The changes have taken effect immediatley."))

    async def on_error(self, interaction: discord.Interaction, error):

        return await interaction.response.send_message( 
            embed=membed(f"Something went wrong.\n\n> {error.__cause__}"))


class DropdownLB(discord.ui.Select):
    def __init__(self, client: commands.Bot):
        optionss = [
            SelectOption(label='Bank + Wallet', description='Sort by the sum of bank and wallet.', default=True),
            SelectOption(label='Wallet', description='Sort by the wallet amount only.'),
            SelectOption(label='Bank', description='Sort by the bank amount only.'),
            SelectOption(label='Inventory Net', description='Sort by the net value of your inventory.')
        ]
        super().__init__(placeholder="Leaderboard Filter", options=optionss)
        self.client: commands.Bot = client

    async def callback(self, interaction: discord.Interaction):

        chosen_choice = self.values[0]

        for option in self.options:
            if option.value == chosen_choice:
                option.default = True
                continue
            option.default = False

        if chosen_choice == 'Bank + Wallet':

            async with self.client.pool_connection.acquire() as conn: 
                conn: asqlite_Connection = conn

                data = await conn.execute(
                    f"SELECT `userID`, SUM(`wallet` + `bank`) as total_balance FROM `{BANK_TABLE_NAME}` GROUP BY `userID` ORDER BY total_balance DESC",
                    ())
                data = await data.fetchall()

                not_database = []
                index = 1

                for member in data:
                    if index > 10:
                        break
                    member_name = await self.client.fetch_user(member[0])
                    their_badge = UNIQUE_BADGES.setdefault(member_name.id, f"")
                    msg1 = f"**{index}.** {member_name.name} {their_badge} \U00003022 {CURRENCY}{member[1]:,}"
                    not_database.append(msg1)
                    index += 1

                msg = "\n".join(not_database)

                lb = discord.Embed(
                    title=f"Leaderboard: {chosen_choice}",
                    description=f"Displaying the top `{index-1}` users.\n\n"
                                f"{msg}",
                    color=0x2F3136,
                    timestamp=discord.utils.utcnow()
                )
                lb.set_footer(
                    text=f"Ranked globally",
                    icon_url=self.client.user.avatar.url)

            await interaction.response.edit_message(content=None, embed=lb, view=self.view) 

        elif chosen_choice == 'Wallet':

            async with self.client.pool_connection.acquire() as conn: 
                conn: asqlite_Connection = conn

                data = await conn.execute(
                    f"SELECT `userID`, `wallet` as total_balance FROM `{BANK_TABLE_NAME}` GROUP BY `userID` ORDER BY total_balance DESC",
                    ())

                data = await data.fetchall()

                not_database = []
                index = 1

                for member in data:
                    member_name = await self.client.fetch_user(member[0])
                    their_badge = UNIQUE_BADGES.setdefault(member_name.id, f"")
                    msg1 = f"**{index}.** {member_name.name} {their_badge} \U00003022 {CURRENCY}{member[1]:,}"
                    not_database.append(msg1)
                    index += 1

                msg = "\n".join(not_database)

                lb = discord.Embed(
                    title=f"Leaderboard: {chosen_choice}",
                    description=f"Displaying the top `{index-1}` users.\n\n"
                                f"{msg}",
                    color=0x2F3136,
                    timestamp=discord.utils.utcnow()
                )
                lb.set_footer(
                    text=f"Ranked globally",
                    icon_url=self.client.user.avatar.url)

            await interaction.response.edit_message(content=None, embed=lb, view=self.view) 

        elif chosen_choice == 'Bank':
            async with self.client.pool_connection.acquire() as conn: 
                conn: asqlite_Connection = conn

                data = await conn.execute(
                    f"SELECT `userID`, `bank` as total_balance FROM `{BANK_TABLE_NAME}` GROUP BY `userID` ORDER BY total_balance DESC",
                    ())

                data = await data.fetchall()

                not_database = []
                index = 1

                for member in data:
                    member_name = await self.client.fetch_user(member[0])
                    their_badge = UNIQUE_BADGES.setdefault(member_name.id, f"")
                    msg1 = f"**{index}.** {member_name.name} {their_badge} \U00003022 {CURRENCY}{member[1]:,}"
                    not_database.append(msg1)
                    index += 1

                msg = "\n".join(not_database)

                lb = discord.Embed(
                    title=f"Leaderboard: {chosen_choice}",
                    description=f"Displaying the top `{index-1}` users.\n\n"
                                f"{msg}",
                    color=0x2F3136,
                    timestamp=discord.utils.utcnow()
                )
                lb.set_footer(
                    text=f"Ranked globally",
                    icon_url=self.client.user.avatar.url)

            await interaction.response.edit_message(content=None, embed=lb, view=self.view) 

        else:
            async with self.client.pool_connection.acquire() as conn: 
                conn: asqlite_Connection = conn

                data = await conn.execute(
                    f"SELECT `userID`, SUM(`Keycard` * ? + `Trophy` * ? + `Dynamic_Item` * ? + `Resistor` * ? + `Clan_License` * ? + `Hyperion` * ? + `Crisis` * ? + `Odd_Eye` * ? + `Amulet` * ?) as total_net FROM `{INV_TABLE_NAME}` GROUP BY `userID` ORDER BY total_net DESC",
                    (SHOP_ITEMS[0]["cost"], SHOP_ITEMS[1]["cost"], SHOP_ITEMS[2]["cost"], SHOP_ITEMS[3]["cost"], SHOP_ITEMS[4]["cost"], SHOP_ITEMS[5]["cost"], SHOP_ITEMS[6]["cost"], SHOP_ITEMS[7]["cost"], SHOP_ITEMS[8]["cost"]))


                data = await data.fetchall()

                not_database = []
                index = 1

                for member in data:
                    member_name = await self.client.fetch_user(member[0])
                    their_badge = UNIQUE_BADGES.setdefault(member_name.id, f"")
                    msg1 = f"**{index}.** {member_name.name} {their_badge} \U00003022 {CURRENCY}{member[1]:,}"
                    not_database.append(msg1)
                    index += 1

                msg = "\n".join(not_database)

                lb = discord.Embed(
                    title=f"Leaderboard: {chosen_choice}",
                    description=f"Displaying the top `{index-1}` users.\n\n"
                                f"{msg}",
                    color=0x2F3136,
                    timestamp=discord.utils.utcnow()
                )
                lb.set_footer(
                    text=f"Ranked globally",
                    icon_url=self.client.user.avatar.url)

            await interaction.response.edit_message(content=None, embed=lb, view=self.view) 

class Leaderboard(discord.ui.View):
    def __init__(self, client: commands.Bot):
        super().__init__(timeout=40.0)
        self.add_item(DropdownLB(client))

    async def on_timeout(self) -> None:
        for item in self.children:
            item.disabled = True
        await self.message.edit(view=self) 


class Economy(commands.Cog):

    def __init__(self, client: commands.Bot):
        self.client: commands.Bot = client


        self.not_registered = discord.Embed(description=f"## <:noacc:1183086855181324490> You are not registered.\n"
                                                        f"You'll need to register first before you can use this command"
                                                        f".\n"
                                                        f"### Already Registered?\n"
                                                        f"Find out what could've happened by calling the command "
                                                        f"[`>reasons`](https://www.google.com/).",
                                            colour=0x2F3136,
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


    async def fetch_tatsu_profile(self, user_id: int):
        """Get tatsu data associated with a given user."""
        repeat = ApiWrapper(key=self.client.TATSU_API_KEY)  
        repeat = await repeat.get_profile(user_id)
        return repeat

    async def raise_pmulti_warning(self, interaction: discord.Interaction, their_pmulti: int | str):
        if their_pmulti in {"0", 0}:
            hook_id = get_profile_key_value(f"{interaction.channel.id} webhook")
            if hook_id is None:
                async with self.client.session.get("https://i.imgur.com/3aMsyXI.jpg") as resp:  
                    avatar_data = await resp.read()
                hook = await interaction.channel.create_webhook(name='Notify', avatar=avatar_data)
                modify_profile("update", f"{interaction.channel.id} webhook", hook.id)
            else:
                hook = await self.client.fetch_webhook(hook_id)

            await hook.send(f"Hey {interaction.user.mention}! We noticed you have not set a personal "
                            f"multiplier. You should set one up now to increase your returns!")

    @staticmethod
    def calculate_hand(hand):
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
            f"INSERT INTO `{BANK_TABLE_NAME}`(userID, wallet, job, {', '.join(BANK_COLUMNS)}) VALUES(?, ?, ?, {', '.join(['0'] * len(BANK_COLUMNS))})",
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
    async def get_bank_data_new(user: discord.Member, conn_input: asqlite_Connection) -> Optional[Any]:
        """Retrieves robux data and other gambling stats from a registered user."""
        data = await conn_input.execute(f"SELECT * FROM `{BANK_TABLE_NAME}` WHERE userID = ?", (user.id,))
        data = await data.fetchone()
        return data

    @staticmethod
    async def get_wallet_data_only(user: discord.Member, conn_input: asqlite_Connection) -> Optional[Any]:
        """Retrieves the wallet amount only from a registered user's bank data."""
        data = await conn_input.execute(f"SELECT wallet FROM `{BANK_TABLE_NAME}` WHERE userID = ?", (user.id,))
        data = await data.fetchone()
        return data[0]

    @staticmethod
    async def get_spec_bank_data(user: discord.Member, field_name: str, conn_input: asqlite_Connection) -> Optional[
        Any]:
        """Retrieves a specific field name only from the bank table."""
        data = await conn_input.execute(f"SELECT {field_name} FROM `{BANK_TABLE_NAME}` WHERE userID = ?", (user.id,))
        data = await data.fetchone()
        return data[0]

    @staticmethod
    async def update_bank_new(user: discord.Member | discord.User, conn_input: asqlite_Connection, amount: Union[float, int] = 0,
                              mode: str = "wallet") -> Optional[Any]:
        """Modifies a user's balance in a given mode: either wallet (default) or bank.
        It also returns the new balance in the given mode, if any (defaults to wallet).
        Note that conn_input is not the last parameter, it is the second parameter to be included."""

        data = await conn_input.execute(
            f"UPDATE `{BANK_TABLE_NAME}` SET `{mode}` = `{mode}` + ? WHERE userID = ? RETURNING `{mode}`",
            (amount, user.id))
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
    async def get_inv_data_new(user: discord.Member, conn_input: asqlite_Connection) -> Optional[Any]:
        """Fetch all inventory data from a user."""
        users = await conn_input.execute(f"SELECT * FROM `{INV_TABLE_NAME}` WHERE userID = ?", (user.id,))
        users = await users.fetchone()
        return users

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
        data = await conn_input.execute(f"UPDATE `{INV_TABLE_NAME}` SET `{mode}` = `{mode}` + ? WHERE userID = ? RETURNING `{mode}`",
                                 (amount, user.id))
        await conn_input.commit()
        data = await data.fetchone()
        return data


    @staticmethod
    async def change_inv_new(user: discord.Member, amount: Union[float, int, None], mode: str,
                             conn_input: asqlite_Connection) -> Optional[Any]:

        data = await conn_input.execute(f"UPDATE `{INV_TABLE_NAME}` SET `{mode}` = ? WHERE userID = ? RETURNING `{mode}`", (amount, user.id))
        await conn_input.commit()
        data = await data.fetchone()
        return data

    # ------------ JOB FUNCS ----------------

    @staticmethod
    async def get_job_data_only(user: discord.Member, conn_input: asqlite_Connection) -> Optional[Any]:
        """Retrieves the users current job."""
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
        cd_columns = ["slaywork", "casino"]
        await conn_input.execute(
            f"INSERT INTO `{COOLDOWN_TABLE_NAME}`(userID, {', '.join(cd_columns)}) VALUES(?, {', '.join(['0'] * len(cd_columns))})",
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
    async def open_slay(conn_input: asqlite_Connection, user: discord.Member, sn: str, gd: str, pd: float, happy: int, stus: int):
        await conn_input.execute(
            "INSERT INTO slay (slay_name, userID, gender, productivity, happiness, status) VALUES (?, ?, ?, ?, ?, ?)",
            (sn, user.id, gd, pd, happy, stus))
        await conn_input.commit()

    @staticmethod
    async def get_slays(conn_input: asqlite_Connection, user: discord.Member):

        new_data = await conn_input.execute("SELECT * FROM slay WHERE userID = ?", (user.id,))
        new_data = await new_data.fetchall()

        return new_data

    @staticmethod
    async def change_slay_field(conn_input: asqlite_Connection, user: discord.Member, field: str, new_val: Any):
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
    async def on_app_command_completion(self, interaction: discord.Interaction, command):
        async with self.client.pool_connection.acquire() as conn: 
            conn: asqlite_Connection
            if await self.can_call_out(interaction.user, conn):
                return
            await self.update_bank_new(interaction.user, conn, 1, "cmds_ran")

    # ----------- END OF ECONOMY FUNCS, HERE ON IS JUST COMMANDS --------------


    pmulti = app_commands.Group(name='multi', description='No description.',
                                guild_only=True, guild_ids=[829053898333225010, 780397076273954886])

    @pmulti.command(name='view', description='check personal and global multipliers.')
    @app_commands.describe(user_name="whose multipliers to view")
    @app_commands.rename(user_name='user')
    @app_commands.checks.dynamic_cooldown(owners_nolimit)
    async def my_multi(self, interaction: discord.Interaction, user_name: Optional[discord.Member]):

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
                multi_own = discord.Embed(colour=0x2F3136, description=f'{user_name.name} doesn\'t have a personal '
                                                                       f'multiplier associated with their account.')
                multi_own.set_author(name=f'Viewing {user_name.name}\'s multipliers', icon_url=user_name.display_avatar.url)
            else:
                server_bs = SERVER_MULTIPLIERS.setdefault(interaction.guild.id, 0)
                multi_own = discord.Embed(colour=0x2F3136,
                                          description=f'Personal multiplier: **{their_multi[0]:,}**%\n'
                                                      f'*A multiplier that is unique to a user and is usually a fixed '
                                                      f'amount.*\n\n'
                                                      f'Global multiplier: **{server_bs:,}**%\n'
                                                      f'*A multiplier that changes based on the server you are calling'
                                                      f' commands in.*')
                multi_own.set_author(name=f'Viewing {user_name.name}\'s multipliers',
                                     icon_url=user_name.display_avatar.url)

            await interaction.response.send_message(embed=multi_own) 

    share = app_commands.Group(name='share', description='share different assets with others.',
                               guild_only=True, guild_ids=[829053898333225010, 780397076273954886])

    @share.command(name="robux", description="share robux with another user.")
    @app_commands.describe(other='the user to give robux to',
                           amount='the amount of robux to give them. Supports Shortcuts (max, all, exponents).')
    @app_commands.rename(other='user')
    @app_commands.checks.dynamic_cooldown(owners_nolimit)
    async def give_robux(self, interaction: discord.Interaction, other: discord.Member, amount: str):
        inter_user = interaction.user

        async with self.client.pool_connection.acquire() as conn: 
            conn: asqlite_Connection

            if not (await self.can_call_out_either(inter_user, other, conn)):
                return await interaction.response.send_message(embed=NOT_REGISTERED) 
            else:
                real_amount = determine_exponent(amount)
                wallet_amt_host = await Economy.get_wallet_data_only(inter_user, conn)

                if isinstance(real_amount, str):
                    if real_amount.lower() == 'all' or real_amount.lower() == 'max':
                        real_amount = wallet_amt_host
                    else:
                        return await interaction.response.send_message(embed=ERR_UNREASON) 
                    host_amt = await self.update_bank_new(inter_user, conn, -int(real_amount))
                    recp_amt = await self.update_bank_new(other, conn, int(real_amount))
                else:
                    if real_amount == 0:
                        return await interaction.response.send_message(embed=ERR_UNREASON) 
                    elif real_amount > wallet_amt_host:
                        return await interaction.response.send_message(embed=ERR_UNREASON) 
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
                return await interaction.response.send_message(embed=embed) 

    @share.command(name='items', description='share items with another user.')
    @app_commands.describe(item_name='the name of the item you want to share.',
                           amount='the amount of this item to share', username='the name of the user to share it with')
    @app_commands.checks.dynamic_cooldown(owners_nolimit)
    async def give_items(self, interaction: discord.Interaction,
                         item_name: Literal['Keycard', 'Trophy', 'Clan License', 'Resistor', 'Amulet', 'Dynamic Item', 'Hyperion', 'Crisis', 'Odd Eye'],
                         amount: Literal[1, 2, 3, 4, 5], username: discord.Member):
        primm = interaction.user

        async with self.client.pool_connection.acquire() as conn: 
            conn: asqlite_Connection
            item_name = item_name.replace(" ", "_")
            if not(await self.can_call_out_either(primm, username, conn)):
                embed = discord.Embed(description=f'Either you or {username.name} does not have an account.\n'
                                                  f'</balance:1179817617435926686> to register.',
                                      colour=0x2F3136)
                return await interaction.response.send_message(embed=embed) 
            else:
                quantity = await self.update_inv_new(primm, 0, item_name, conn)
                if amount > quantity[0]:
                    return await interaction.response.send_message(embed=ERR_UNREASON) 
                else:
                    receiver = await self.update_inv_new(username, +amount, item_name, conn)
                    new_after_transaction = quantity[0] - amount
                    sender = await self.change_inv_new(primm, new_after_transaction, item_name, conn)
                    item_name = " ".join(item_name.split("_"))
                    transaction_success = discord.Embed(
                        title="Transaction Complete",
                        description=f'- {primm.mention} has given **{amount}** {make_plural(item_name, amount)}\n'
                                    f'- {primm.mention} now has **{sender[0]}** {make_plural(item_name, sender[0])}\n'
                                    f'- {username.mention} now has **{receiver[0]}** {make_plural(item_name, receiver[0])}',
                        colour=0x2B2D31)
                    transaction_success.set_thumbnail(url="https://i.imgur.com/xRJ2hpF.png")
                    transaction_success.set_author(name=f'Transaction made by {primm.name}',
                                                   icon_url=primm.display_avatar.url)

                    await interaction.response.send_message(embed=transaction_success) 

    shop = app_commands.Group(name='shop', description='view items available for purchase.', guild_only=True,
                              guild_ids=[829053898333225010, 780397076273954886])

    @shop.command(name='view', description='view all shop items.')
    @app_commands.checks.dynamic_cooldown(owners_nolimit)
    async def view_the_shop(self, interaction: discord.Interaction):

        async with self.client.pool_connection.acquire() as conn:
            conn: asqlite_Connection

            if await self.can_call_out(interaction.user, conn):
                return await interaction.response.send_message(embed=self.not_registered)

            additional_notes = list()

            for item in SHOP_ITEMS:
                name = " ".join(item["name"].split("_"))

                additional_notes.append(
                    f"{item['emoji']} __{name}__ \U00002014 [\U000023e3 **{item['cost']:,}**](https://youtu.be/dQw4w9WgXcQ)\n"
                    f"{ARROW}{item["info"]}\n"
                    f"{ARROW}ID: `{item['id']}`\n"
                    f"{ARROW}Quantity Remaining: `{get_stock(name)}`")

            async def get_page_part(page: int):
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
                     item_name: Literal['Keycard', 'Trophy', 'Clan License', 'Resistor', 'Amulet', 'Dynamic Item', 'Hyperion', 'Crisis', 'Odd Eye']):

        item_stock = get_stock(item_name)
        match item_stock:
            case 0:
                stock_resp = f"The item is currently out of stock."
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
                async with self.client.pool_connection.acquire() as conn:  
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

                return await interaction.response.send_message(embed=em) 

        await interaction.response.send_message(f"There is no item named {item_name}.") 

    profile = app_commands.Group(name='editprofile', description='custom-profile-orientated commands for use.',
                                 guild_only=True, guild_ids=[829053898333225010, 780397076273954886])

    @profile.command(name='bio', description='add a bio to your profile.')
    @app_commands.checks.dynamic_cooldown(owners_nolimit)
    async def update_bio_profile(self, interaction: discord.Interaction):
        async with self.client.pool_connection.acquire() as conn: 
            conn: asqlite_Connection
            if await self.can_call_out(interaction.user, conn):
                return await interaction.response.send_message( 
                    embed=membed("<:warning_nr:1195732155544911882> You cannot use this command until you register."))
            await interaction.response.send_modal(UpdateInfo()) 

    @profile.command(name='avatar', description='change your profile avatar.')
    @app_commands.describe(url='the url of the new avatar. leave blank to remove.')
    @app_commands.checks.dynamic_cooldown(owners_nolimit)
    async def update_avatar_profile(self, interaction: discord.Interaction, url: Optional[str]):

        async with self.client.pool_connection.acquire() as conn: 
            conn: asqlite_Connection

            if await self.can_call_out(interaction.user, conn):
                return await interaction.response.send_message( 
                    embed=membed('<:warning_nr:1195732155544911882> You cannot use this command until you register.'))

        if url is None:
            res = modify_profile("delete", f"{interaction.user.id} avatar_url", url)
            match res:
                case 0:
                    res = "<:warning_nr:1195732155544911882> No custom avatar was found under your account."
                case _:
                    res = "<:overwrite:1195729262729240666> Your avatar was removed."
            return await interaction.response.send_message(embed=membed(res)) 

        successful = discord.Embed(colour=0x2B2D31,
                                   description=f"## <:overwrite:1195729262729240666> Your custom has been added.\n"
                                               f"- If valid, it will look like this ----->\n"
                                               f"- If you can't see it, change it!")
        successful.set_thumbnail(url=url)
        modify_profile("update", f"{interaction.user.id} avatar_url", url)
        await interaction.response.send_message(embed=successful) 

    @update_avatar_profile.error
    async def uap_error(self, interaction: discord.Interaction, err: discord.app_commands.AppCommandError):
        modify_profile("delete", f"{interaction.user.id} avatar_url", "who cares")
        return await interaction.response.send_message( 
            embed=membed(
                f"<:warning_nr:1195732155544911882> The avatar url requested for could not be added:\n"
                f"- The URL provided was not well formed.\n"
                f"- Discord embed thumbnails have specific image requirements to "
                f"ensure proper display.\n"
                f" - **The recommended size for a thumbnail is 80x80 pixels.**"
            ))

    @profile.command(name='visibility', description='hide your profile for privacy.')
    @app_commands.describe(mode='Toggle public or private profile')
    @app_commands.checks.dynamic_cooldown(owners_nolimit)
    async def update_vis_profile(self, interaction: discord.Interaction,
                                 mode: Literal['public', 'private']):
        async with self.client.pool_connection.acquire() as conn: 
            conn: asqlite_Connection
            if await self.can_call_out(interaction.user, conn):
                return await interaction.response.send_message( 
                    embed=membed("You cannot use this command until you register."))

        modify_profile("update", f"{interaction.user.id} vis", mode)
        cemoji = {"private": "<:privatee:1195728566919385088>",
                  "public": "<:publice:1195728479715590205>"}
        cemoji = cemoji.get(mode)
        await interaction.response.send_message(f"{cemoji} Your profile is now {mode}.", ephemeral=True, delete_after=7.5) 

    slay = app_commands.Group(name='slay', description='manage your slay.',
                              guild_only=True,
                              guild_ids=[829053898333225010, 780397076273954886])

    @slay.command(name='hire', description='hire your own slay.')
    @app_commands.describe(user='member to make a slay. if empty, specify new_slay_name.',
                           new_slay_name='The name of your slay, if you didn\'t pick a user.',
                           gender="the gender of your slay, doesn't have to be true..",
                           investment="how much robux your willing to spend on this slay (no shortcuts)")
    async def hire_slv(self, interaction: discord.Interaction, user: Optional[discord.Member],
                       new_slay_name: Optional[str], gender: Literal["male", "female"], investment: int):
        await interaction.response.defer(thinking=True) 
        async with self.client.pool_connection.acquire() as conn: 
            conn: asqlite_Connection

            if await self.can_call_out(interaction.user, conn):
                return await interaction.followup.send(embed=self.not_registered)

            if user and (interaction.user.id == user.id):
                return await interaction.followup.send("Why would you make yourself a slay?")
            elif (user is None) and (new_slay_name is None):
                return await interaction.followup.send("You did not input any slay.")
            elif (new_slay_name is not None) and (user is not None):
                return await interaction.followup.send("You cannot name your slay if the user has also "
                                                       "been inputted. Remove this argument if needed.")
            elif abs(investment) > await self.get_wallet_data_only(interaction.user, conn):
                return await interaction.followup.send(
                    embed=membed("Your slay will not obey your orders if you do not "
                                 "guarantee your investment.\n"
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
                    await interaction.followup.send(embed=slayy)

                else:
                    if len(slays) >= 6:
                        return await interaction.followup.send(
                            embed=membed("## You have reached the maximum slay quota for now.\n"
                                         "You must abandon a current slay before hiring a new one."))

                    for slay in slays:
                        if new_slay_name == slay[0]:
                            return await interaction.followup.send(
                                "You already own a slay with that name."
                            )

                    await self.open_slay(conn, interaction.user, new_slay_name, gender, prod, 100, 1)

                    slaye = discord.Embed(description=f"## Slay Summary\n"
                                                      f"- Paid **\U000023e3 {investment:,}** for the following:\n"
                                                      f" - Your brand new slay named {new_slay_name}\n"
                                                      f" - {new_slay_name} has a productivity level "
                                                      f"of `{prod}`.",
                                          color=discord.Color.from_rgb(0, 0, 0))
                    slaye.set_footer(text=f"{len(slays)+1}/6 slay slots consumed")

                    await interaction.followup.send(embed=slaye)

    @slay.command(name='abandon', description='abandon your slay.')
    @app_commands.rename(slay_purge='slay')
    @app_commands.describe(user='member to make a slay. if empty, specify new_slay_name.',
                           slay_purge='the name of your slay, if you didn\'t pick a user.')
    async def abandon_slv(self, interaction: discord.Interaction, user: Optional[discord.Member],
                          slay_purge: Optional[str]):
        async with self.client.pool_connection.acquire() as conn: 
            conn: asqlite_Connection

            if await self.can_call_out(interaction.user, conn):
                return await interaction.followup.send(embed=self.not_registered)

            if (user is None) and (slay_purge is None):
                return await interaction.response.send_message("You did not input any slay.") 
            elif (slay_purge is not None) and (user is not None):
                return await interaction.response.send_message("You cannot name your slay if the user has also " 
                                                               "been inputted. Remove this argument if needed.")
            else:
                slays = await self.get_slays(conn, interaction.user)

                if slay_purge is None:
                    slay_purge = user.display_name

                await self.delete_slay(conn, interaction.user, slay_purge)

                return await interaction.response.send_message( 
                embed=membed(f"Attempted to remove {slay_purge} from your owned slays.\n"
                             f" - {len(slays)}/6 total slay slots consumed."))


    @slay.command(name='viewall', description="see a user's owned slaves.")
    @app_commands.describe(user='the user to view the slays of')
    async def view_all_slays(self, interaction: discord.Interaction, user: Optional[discord.Member]):

        async with self.client.pool_connection.acquire() as conn: 
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
                return await interaction.response.send_message(embed=embed) 

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
            await interaction.response.send_message(embed=embed) 

    @slay.command(name='work', description="assign your slays to do tasks for you.")
    @app_commands.describe(duration="the time spent working (e.g, 18h or 1d 3h)")
    async def make_slay_work_pay(self, interaction: discord.Interaction, duration: str):
        await interaction.response.defer(thinking=True) 

        try:
            async with self.client.pool_connection.acquire() as conn: 
                conn: asqlite_Connection

                if await self.can_call_out(interaction.user, conn):
                    return await interaction.followup.send(embed=NOT_REGISTERED)

                if len(await self.get_slays(conn, interaction.user)) == 0:
                    return await interaction.followup.send(
                        embed=membed("You got no slays to send to work.")
                    )

                res_duration = parse_duration(duration)

                cooldown = await self.fetch_cooldown(conn, user=interaction.user, cooldown_type="slaywork")
                if cooldown is not None:
                    if cooldown[0] in {"0", 0}:
                        day = number_to_ordinal(int(res_duration.strftime("%d")))
                        shallow = res_duration.strftime(f"%A the {day} of %B at %I:%M%p")
                        await self.change_slay_field(conn, interaction.user, "status", 0)

                        res_duration = datetime_to_string(res_duration)
                        await self.update_cooldown(conn, user=interaction.user, cooldown_type="slaywork", new_cd=res_duration)
                        await interaction.followup.send(f"## Your slay(s) have been sent off.\n"
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
                                    disproportionate_share = randint(20000000, slay_fund-disproportionate_share)
                                    bonus = round((1.2 / 100) * disproportionate_share) + disproportionate_share
                                    total_fund += bonus

                                    content.add(f'- {slay[0]} was {doing_what} and got a total '
                                                f'of **\U000023e3 {disproportionate_share:,}**\n'
                                                f' - Bonus: **\U000023e3 {bonus:,}**')
                                else:
                                    doing_what = sad_actions.get(index_l)
                                    loss = (slay[-2]/100)*disproportionate_share
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
                            summ.set_footer(icon_url=interaction.user.display_avatar.url, text=f"For {interaction.user.name}")
                            summ.description = (f"## <a:2635serversubscriptionsanimated:1174417911344013523> Paycheck\n"
                                                f"> Your slays have made **\U000023e3 {slay_fund:,}**.\n"
                                                f"> Your new `wallet` balance now is **\U000023e3 {net_returns[0]:,}**."
                                                f"\n\nHere is a summary:\n"
                                                f"{'\n'.join(content)}\n")

                            return await interaction.followup.send(embed=summ)
                        else:
                            minutes, seconds = divmod(diff.total_seconds(), 60)
                            hours, minutes = divmod(minutes, 60)
                            days, hours = divmod(hours, 24)
                            await interaction.followup.send(f"Your slays are still working.\n"
                                                            f"They will finish working in **{int(days)}** days, "
                                                            f"**{int(hours)}** hours, **{int(minutes)}** minutes "
                                                            f"and **{int(seconds)}** seconds. ")
                else:
                    return await interaction.followup.send("## No data has been found under your name.\n"
                                                           "- This is because you've registered after the "
                                                           "cooldown system was implemented.\n"
                                                           "- A quick fix is to use the /discontinue command "
                                                           "and re-register (you can request a developer to "
                                                           "add your original items back).")
        except ValueError as veer:
            await interaction.followup.send(f"{veer}")

    @commands.command(name='reasons', description='identify causes of registration errors.')
    @commands.cooldown(1, 6)
    async def not_registered_why(self, ctx: commands.Context):
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

    @app_commands.command(name="use", description="use an item you own from your inventory.")
    @app_commands.guilds(discord.Object(id=829053898333225010), discord.Object(id=780397076273954886))
    @app_commands.describe(item='the name of the item to use')
    @app_commands.checks.dynamic_cooldown(owners_nolimit)
    async def use_item(self, interaction: discord.Interaction,
                       item: Literal['Keycard', 'Trophy', 'Clan License', 'Resistor', 'Amulet', 'Dynamic Item', 'Hyperion', 'Crisis', 'Odd Eye']):

        async with self.client.pool_connection.acquire() as conn: 
            conn: asqlite_Connection

            if await self.can_call_out(interaction.user,conn):
                return await interaction.response.send_message(embed=self.not_registered) 

            item = item.replace(" ", "_")
            quantity = await self.get_one_inv_data_new(interaction.user, item, conn)

            if not quantity:
                return await interaction.response.send_message( 
                    embed=membed(f"You don't have this item in your inventory."))

            match item:
                case 'Keycard' | 'Resistor' | 'Hyperion' | 'Crisis':
                    return await interaction.response.send_message(  
                        content="This item cannot be used. The effects are always passively active!")
                case 'Trophy':
                    if quantity > 1:
                        content = f'\nThey have **{quantity}** of them, WHAT A BADASS'
                    else:
                        content = ''
                    return await interaction.response.send_message( 
                        f"{interaction.user.name} is flexing on you all with their <:tr1:1165936712468418591> **~~PEPE~~ TROPHY**{content}")
                case _:
                    return await interaction.response.send_message( 
                        embed=membed("The functions for this item aren't available.\n"
                                     "If you wish to submit an idea for what these items do, "
                                     "comment on [this issue on our Github.](https://github.com/SGA-A/c2c/issues/12)")
                    )

    @app_commands.command(name="getjob", description="earn a salary becoming employed.")
    @app_commands.guilds(discord.Object(id=829053898333225010), discord.Object(id=780397076273954886))
    @app_commands.describe(job_name='the name of the job')
    @app_commands.checks.dynamic_cooldown(owners_nolimit)
    async def get_job(self, interaction: discord.Interaction,
                      job_name: Literal['Plumber', 'Cashier', 'Fisher', 'Janitor',
                                        'Youtuber', 'Police', 'I want to resign!']):

        async with self.client.pool_connection.acquire() as conn: 
            conn: asqlite_Connection
            if await self.can_call_out(interaction.user, conn):
                return await interaction.response.send_message(embed=self.not_registered) 

            cooldown = await self.fetch_cooldown(conn, user=interaction.user, cooldown_type="job_change")
            current_job = await self.get_job_data_only(interaction.user, conn) # default is 'None'

            if cooldown is not None:
                if cooldown[0] in {"0", 0}:

                    if current_job[0] != job_name:

                        ncd = datetime.datetime.now() + datetime.timedelta(days=2)  # the cd
                        ncd = datetime_to_string(ncd)
                        await self.update_cooldown(conn, user=interaction.user, cooldown_type="job_change", new_cd=ncd)

                        if job_name.startswith("I"):
                            if current_job != "None":
                                await self.change_job_new(interaction.user, conn, job_name='None')
                                return await interaction.response.send_message(
                                    embed=membed(f"Alright, I've removed you from your job.\n"
                                                 f"You cannot apply to another job for the next **48 hours**."))
                            return await interaction.response.send_message(
                                embed=membed("You're already unemployed!?"))

                        await self.change_job_new(interaction.user, conn, job_name=job_name)
                        return await interaction.response.send_message(
                            embed=membed(f"Congratulations, you've been hired.\n"
                                         f"Starting today, you are working as a {job_name.lower()}."))  
                    return await interaction.response.send_message(
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

                        await interaction.response.send_message(
                            embed=membed(f"{response}\n"
                                         f"Call this command again to begin your new career.")
                        )
                    else:
                        when = datetime.datetime.now() + datetime.timedelta(seconds=diff.total_seconds())
                        embed = discord.Embed(title="Cannot perform this action",
                                              description=f"You can change your job "
                                                          f"{discord.utils.format_dt(when, 'R')}.",
                                              colour=0x2B2D31)
                        await interaction.response.send_message(embed=embed) 

    @app_commands.command(name='profile', description='view user information and stats.')
    @app_commands.guilds(discord.Object(id=829053898333225010), discord.Object(id=780397076273954886))
    @app_commands.describe(user='the profile of the user to find', category='what type of data you want to view')
    @app_commands.checks.dynamic_cooldown(owners_nolimit)
    async def find_profile(self, interaction: discord.Interaction, user: Optional[discord.Member],
                           category: Optional[Literal["Main Profile", "Gambling Stats"]]):

        user = user or interaction.user
        category = category or "Main Profile"

        async with self.client.pool_connection.acquire() as conn: 

            if await self.can_call_out(user, conn):
                return await interaction.response.send_message(embed=NOT_REGISTERED) 

            data = await conn.execute(f"SELECT * FROM `bank` WHERE userID = ?", (user.id,))
            data = await data.fetchone()

            ephemerality = False

            if category == "Main Profile":
                if (get_profile_key_value(f"{user.id} vis") == "private") and (interaction.user.id != user.id):
                    return await interaction.response.send_message( 
                        embed=membed(f"# <:security:1153754206143000596> {user.name}'s profile is protected.\n"
                                     f"Only approved users can view {user.name}'s profile."))

                if (get_profile_key_value(f"{user.id} vis") == "private") and (interaction.user.id == user.id):
                    ephemerality = True

                procfile = discord.Embed(colour=user.colour, timestamp=discord.utils.utcnow())
                tatsu = await self.fetch_tatsu_profile(user.id)
                inv = 0
                unique = 0
                total = 0

                for item in SHOP_ITEMS:
                    item_quantity = await self.get_one_inv_data_new(user, item["name"], conn)
                    inv += item["cost"] * item_quantity
                    total += item_quantity
                    unique += 1 if item_quantity else 0

                if user.id == 992152414566232139:
                    procfile.set_image(
                        url="https://media.discordapp.net/attachments/1124672402413072446/1164912661004292136/20231010000451.png?ex=6544f075&is=65327b75&hm=dfef49bfcab2ca0f8f2d50db7733c5e3ba6cf691f5350ddf8fb8350fc2bb38d8&=&width=1246&height=701")

                match user.id:
                    case 546086191414509599 | 992152414566232139:
                        note = ("> <:cprofile:1174417914183561287> *This user's custom profile contains "
                                "additional perks that will not be publicized.*\n\n")
                    case _:
                        note = ""

                procfile.description = (f"### {user.name}'s Profile - [{tatsu.title or 'No title set'}](https://tatsu.gg/profile)\n"
                                        f"{note}"
                                        f"{PRESTIGE_EMOTES.setdefault(data[-1], "")} Prestige Level **{data[-1]}**\n"
                                        f"<:bountybag:1195653667135692800> Bounty: \U000023e3 **{data[-2]:,}**\n"
                                        f"{get_profile_key_value(f"{user.id} badges") or "No badges acquired yet"}")

                procfile.add_field(name='Robux',
                                   value=f"Wallet: `\U000023e3 {format_number_short(data[1])}`\n"
                                         f"Bank: `\U000023e3 {format_number_short(data[2])}`\n"
                                         f"Net: `\U000023e3 {format_number_short(data[1] + data[2])}`")

                procfile.add_field(name='Items',
                                   value=f"Unique: `{unique:,}`\n"
                                         f"Total: `{format_number_short(total)}`\n"
                                         f"Worth: `\U000023e3 {format_number_short(inv)}`")

                procfile.add_field(name='Tatsu',
                                   value=f"Credits: `{format_number_short(tatsu.credits)}`\n"
                                         f"Tokens: `{format_number_short(tatsu.tokens)}`\n"
                                         f"XP: `{format_number_short(tatsu.xp)}`")
                
                procfile.add_field(name='Commands',
                                   value=f"Total: `{format_number_short(data[15])}`")
                
                procfile.add_field(name="Drones",
                                   value="Limited")
                
                procfile.add_field(name="Showcase",
                                   value="No showcase") # soon!

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
                return await interaction.response.send_message( 
                    embed=procfile, silent=True, ephemeral=ephemerality)
            else:
                total_slots = data[3] + data[4]
                total_bets = data[5] + data[6]
                total_blackjacks = data[7] + data[8]

                try:
                    winbe = round((data[5] / total_bets) * 100)
                except ZeroDivisionError:
                    winbe = 0
                try:
                    winsl = round((data[3] / total_slots) * 100)
                except ZeroDivisionError:
                    winsl = 0
                try:
                    winbl = round((data[7] / total_blackjacks) * 100)
                except ZeroDivisionError:
                    winbl = 0

                stats = discord.Embed(title=f"{user.name}'s gambling stats",
                                      colour=0x2B2D31)

                stats.add_field(name=f"BET ({total_bets:,})",
                                value=f"Won: \U000023e3 {data[11]:,}\n"
                                      f"Lost: \U000023e3 {data[12]:,}\n"
                                      f"Net: \U000023e3 {data[11] - data[12]:,}\n"
                                      f"Win: {winbe}% ({data[5]})")
                stats.add_field(name=f"SLOTS ({total_slots:,})",
                                value=f"Won: \U000023e3 {data[9]:,}\n"
                                      f"Lost: \U000023e3 {data[10]:,}\n"
                                      f"Net: \U000023e3 {data[9] - data[10]:,}\n"
                                      f"Win: {winsl}% ({data[3]})")
                stats.add_field(name=f"BLACKJACK ({total_blackjacks:,})",
                                value=f"Won: \U000023e3 {data[13]:,}\n"
                                      f"Lost: \U000023e3 {data[14]:,}\n"
                                      f"Net: \U000023e3 {data[13] - data[14]:,}\n"
                                      f"Win: {winbl}% ({data[7]})")
                stats.set_footer(text="The number next to the name is how many matches are recorded")

                await interaction.response.send_message(embed=stats)  
                resp = await interaction.original_response()
                try:
                    its_sum = total_bets + total_slots + total_blackjacks
                    pie = (ImageCharts()
                           .chd(
                        f"t:{(total_bets / its_sum) * 100},{(total_slots / its_sum) * 100},{(total_blackjacks / its_sum) * 100}")
                           .chco("EA469E|03A9F4|FFC00C").chl(
                        f"BET ({total_bets})|SLOTS ({total_slots})|BJ ({total_blackjacks})")
                           .chdl("Total bet games|Total slot games|Total blackjack games").chli(f"{its_sum}").chs(
                        "600x480")
                           .cht("pd").chtt(f"{user.name}'s total games played"))
                    await resp.reply(content=pie.to_url())
                except ZeroDivisionError:
                    await resp.reply(content=f"Looks like {user.display_name} hasn't got enough data yet to form a pie chart.")

    @app_commands.command(name='highlow', description='guess the number. jackpot wins big!')
    @app_commands.guilds(discord.Object(id=829053898333225010), discord.Object(id=780397076273954886))
    @app_commands.checks.dynamic_cooldown(owners_nolimit)
    @app_commands.describe(robux='an integer to bet upon. Supports Shortcuts (max, all, exponents).')
    async def highlow(self, interaction: discord.Interaction, robux: str):

        def is_valid(value: int, user_balance: int) -> bool:
            """A check that defines that the amount a user inputs is valid for their account. Meets preconditions for highlow.
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

        async with self.client.pool_connection.acquire() as conn:  
            conn: asqlite_Connection
            if await self.can_call_out(interaction.user, conn):
                return await interaction.response.send_message(embed=self.not_registered) 

            real_amount = determine_exponent(robux)
            wallet_amt = await self.get_wallet_data_only(interaction.user, conn)
            if isinstance(real_amount, str):
                if real_amount.lower() == 'max' or real_amount.lower() == 'all':
                    if 50000000 > wallet_amt:
                        real_amount = wallet_amt
                    else:
                        real_amount = 50000000
            if not (is_valid(int(real_amount), wallet_amt)):
                return await interaction.response.send_message(embed=ERR_UNREASON) 

            number = randint(1, 100)
            hint = randint(1, 100)

            query = discord.Embed(colour=0x2B2D31,
                                  description=f"I just chose a secret number between 0 and 100.\n"
                                              f"Is the secret number *higher* or *lower* than {hint}?")
            query.set_author(name=f"{interaction.user.name}'s high-low game",
                             icon_url=interaction.user.display_avatar.url)
            query.set_footer(text="The jackpot button is if you think it is the same!")
            await interaction.response.send_message( 
                view=HighLow(interaction, self.client, hint_provided=hint, bet=real_amount, value=number),
                embed=query)

            pmulti = await self.get_pmulti_data_only(interaction.user, conn)
            await self.raise_pmulti_warning(interaction, pmulti[0])

    @app_commands.command(name='slots',
                          description='try your luck on a slot machine.')
    @app_commands.guilds(discord.Object(id=829053898333225010), discord.Object(id=780397076273954886))
    @app_commands.rename(keyword='robux')
    @app_commands.checks.dynamic_cooldown(owners_nolimit)
    @app_commands.describe(keyword='an integer to bet upon. Supports Shortcuts (max, all, exponents).')
    async def slots(self, interaction: discord.Interaction, keyword: str):

        async with self.client.pool_connection.acquire() as conn: 
            conn: asqlite_Connection
            if await self.can_call_out(interaction.user, conn):
                await interaction.response.send_message(embed=self.not_registered) 

        # --------------- Checks before betting i.e. has keycard, meets bet constraints. -------------
        data = await self.get_one_inv_data_new(interaction.user, "Keycard", conn)
        has_keycard = data and True
        expo = determine_exponent(keyword)
        try:
            assert isinstance(expo, int)
            amount = expo
        except AssertionError:
            if keyword.lower() in {'max', 'all'}:
                if has_keycard:
                    amount = 75000000
                else:
                    amount = 50000000
            else:
                return await interaction.response.send_message(embed=ERR_UNREASON) 

        # --------------- Contains checks before betting i.e. has keycard, meets bet constraints. -------------
        wallet_amt = await self.get_wallet_data_only(interaction.user, conn)
        if has_keycard:
            if (amount > 75000000) or (amount < 30000):
                err = discord.Embed(colour=0x2F3136, description=f'## You did not meet the slot machine criteria:\n'
                                                                 f'- You wanted to bet {CURRENCY}**{amount:,}**\n'
                                                                 f' - A minimum bet of {CURRENCY}**30,000** must '
                                                                 f'be made\n'
                                                                 f' - A maximum bet of {CURRENCY}**75,000,000** '
                                                                 f'can only be made.')
                return await interaction.response.send_message(embed=err) 
            elif amount > wallet_amt:
                err = discord.Embed(colour=0x2F3136, description=f'Cannot perform this action, '
                                                                 f'you only have {CURRENCY}**{wallet_amt:,}**.\n'
                                                                 f'You\'ll need {CURRENCY}**{amount - wallet_amt:,}**'
                                                                 f' more in your wallet first.')
                return await interaction.response.send_message(embed=err) 
        else:
            if (amount > 50000000) or (amount < 50000):
                err = discord.Embed(colour=0x2F3136, description=f'## You did not meet the slot machine criteria:\n'
                                                                 f'- You wanted to bet {CURRENCY}**{amount:,}**\n'
                                                                 f' - A minimum bet of {CURRENCY}**50,000** must '
                                                                 f'be made.\n'
                                                                 f' - A maximum bet of {CURRENCY}**50,000,000** '
                                                                 f'can only be made.')
                return await interaction.response.send_message(embed=err) 
            elif amount > wallet_amt:
                err = discord.Embed(colour=0x2F3136, description=f"## Cannot perform this action, "
                                                                 f"You only have {CURRENCY}**{wallet_amt:,}**.\n"
                                                                 f"You'll need {CURRENCY}**{amount - wallet_amt:,}**"
                                                                 f" more in your wallet first.")
                return await interaction.response.send_message(embed=err) 

        # ------------------ THE SLOT MACHINE ITESELF ------------------------

        emoji_outcome = generate_slot_combination()
        freq1, freq2, freq3 = emoji_outcome[0], emoji_outcome[1], emoji_outcome[2]
        slot_stuff = await self.get_bank_data_new(interaction.user, conn)
        id_won_amount, id_lose_amount = slot_stuff[3], slot_stuff[4]

        if emoji_outcome.count(freq1) > 1:


            emulti = BONUS_MULTIPLIERS[f'{freq1 * emoji_outcome.count(freq1)}']
            serv_multi = SERVER_MULTIPLIERS.setdefault(interaction.guild.id, 0)
            new_multi = serv_multi + emulti
            amount_after_multi = floor(((new_multi / 100) * amount) + amount)
            tma = amount_after_multi - amount
            await self.update_bank_new(interaction.user, conn, amount_after_multi, "slotwa")
            new_amount_balance = await self.update_bank_new(interaction.user, conn, amount_after_multi)
            new_id_won_amount = await self.update_bank_new(interaction.user, conn, 1, "slotw")
            new_total = id_lose_amount + new_id_won_amount[0]

            prcntw = round((new_id_won_amount[0] / new_total) * 100, 1)
            embed = discord.Embed(description=f"**\U0000003e** {emoji_outcome[0]} {emoji_outcome[1]} {emoji_outcome[2]} **\U0000003c**\n\n"
                                              f"**It's a match!** You've won {CURRENCY}**{amount_after_multi:,}** robux.\n"
                                              f"You got {PREMIUM_CURRENCY} **{tma:,}** as part of your `{new_multi}x` multiplier.\n"
                                              f"<:linkit:1176970030961930281> **{serv_multi}**% Server Multiplier, **{emulti}**% via slots.\n"
                                              f"Your new balance is {CURRENCY}**{new_amount_balance[0]:,}**.\n"
                                              f"You've won {prcntw}% of all slots games.",
                                  colour=discord.Color.brand_green())
            embed.set_author(name=f"{interaction.user.name}'s winning slot machine",
                             icon_url=interaction.user.display_avatar.url)
            await interaction.response.send_message(embed=embed) 

        elif emoji_outcome.count(freq2) > 1:

            emulti = BONUS_MULTIPLIERS[f'{freq2 * emoji_outcome.count(freq2)}']

            serv_multi = SERVER_MULTIPLIERS.setdefault(interaction.guild.id, 0)
            new_multi = serv_multi + emulti
            amount_after_multi = floor(((new_multi / 100) * amount) + amount)
            tma = amount_after_multi - amount
            await self.update_bank_new(interaction.user, conn, amount_after_multi, "slotwa")
            new_amount_balance = await self.update_bank_new(interaction.user, conn, amount_after_multi)
            new_id_won_amount = await self.update_bank_new(interaction.user, conn, 1, "slotw")
            new_total = id_lose_amount + new_id_won_amount[0]
            prcntw = round((new_id_won_amount[0] / new_total) * 100, 1)

            embed = discord.Embed(description=f"**\U0000003e** {emoji_outcome[0]} {emoji_outcome[1]} {emoji_outcome[2]} **\U0000003c**\n\n"
                                              f"**It's a match!** You've won {CURRENCY}**{amount_after_multi:,}** robux.\n"
                                              f"You got {PREMIUM_CURRENCY} **{tma:,}** as part of your `{new_multi}x` multiplier.\n"
                                              f"<:linkit:1176970030961930281> **{serv_multi}**% Server Multiplier, **{emulti}**% via slots.\n"
                                              f"Your new balance is {CURRENCY}**{new_amount_balance[0]:,}**.\n"
                                              f"You've won {prcntw}% of all slots games.",
                                  colour=discord.Color.brand_green())
            embed.set_author(name=f"{interaction.user.name}'s winning slot machine",
                             icon_url=interaction.user.display_avatar.url)
            await interaction.response.send_message(embed=embed) 

        else:

            await self.update_bank_new(interaction.user, conn, amount, "slotla")
            new_amount_balance = await self.update_bank_new(interaction.user, conn, -amount)
            new_id_lose_amount = await self.update_bank_new(interaction.user, conn, 1, "slotl")
            new_total = new_id_lose_amount[0] + id_won_amount

            prcntl = round((new_id_lose_amount[0] / new_total) * 100, 1)

            embed = discord.Embed(description=f"**\U0000003e** {emoji_outcome[0]} {emoji_outcome[1]} {emoji_outcome[2]} **\U0000003c**\n\n"
                                              f"**No match!** You've lost {CURRENCY}**{amount:,}** robux.\n"
                                              f"Your new balance is {CURRENCY}**{new_amount_balance[0]:,}**.\n"
                                              f"You've lost {prcntl}% of all slots games.",
                                  colour=discord.Color.brand_red())
            embed.set_author(name=f"{interaction.user.name}'s losing slot machine",
                             icon_url=interaction.user.display_avatar.url)
            await interaction.response.send_message(embed=embed) 

    @app_commands.command(name='inventory', description='view your currently owned items.')
    @app_commands.guilds(discord.Object(id=829053898333225010), discord.Object(id=780397076273954886))
    @app_commands.describe(member='the member to view the inventory of:')
    async def inventory(self, interaction: discord.Interaction, member: Optional[discord.Member]):
        member = member or interaction.user

        if member.bot and member.id != self.client.user.id:
            return await interaction.response.send_message(embed=membed("Bots do not have accounts."), delete_after=5.0) 

        async with self.client.pool_connection.acquire() as conn: 
            conn: asqlite_Connection

            if await self.can_call_out(member, conn):
                return await interaction.response.send_message(embed=NOT_REGISTERED) 

            em = discord.Embed(color=0x2F3136)
            length = 5
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
                        f"{item_emoji} **{qualified_name}** ({data[0]} owned)\nID: **`{item_id}`**\nItem Type: {item_type}")


            if len(owned_items) == 0:
                em.set_author(name=f"{member.name}'s Inventory", icon_url=member.display_avatar.url)
                em.description = (f"{member.name} currently has **no items** in their inventory.\n"
                                  f"**Net Value:** <:robux:1146394968882151434> 0\n"
                                  f"**Sell Value:** <:robux:1146394968882151434> 0")

                em.add_field(
                    name=f"Nothingness.", value=f"No items were found from this user.", inline=False)
                return await interaction.response.send_message(embed=em) 

            async def get_page_part(page: int):

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

    @app_commands.command(name='buy', description='make a purchase from the shop.')
    @app_commands.guilds(discord.Object(id=829053898333225010), discord.Object(id=780397076273954886))
    @app_commands.describe(item_name='the name of the item you want to buy.',
                           quantity='the quantity of the item(s) you wish to buy')
    async def buy(self, interaction: discord.Interaction,
                  item_name: Literal['Keycard', 'Trophy', 'Clan License', 'Resistor', 'Amulet', 'Dynamic Item', 'Hyperion', 'Crisis', 'Odd Eye'],
                  quantity: Optional[Literal[1, 2, 3, 4, 5]]):

        if quantity is None:
            quantity = 1

        async with self.client.pool_connection.acquire() as conn: 
            conn: asqlite_Connection

            if await self.can_call_out(interaction.user, conn):
                return await interaction.response.send_message(embed=self.not_registered) 

            wallet_amt = await self.get_wallet_data_only(interaction.user, conn)

            for item in SHOP_ITEMS:
                access_name = ' '.join(item["name"].split('_'))

                if item_name == access_name:
                    ie = item['emoji']
                    proper_name = item.setdefault('qn', None) or access_name
                    stock_item = get_stock(item_name)

                    if stock_item == 0:
                        return await interaction.response.send_message( 
                            embed=membed(f"## Unsuccessful Transaction\n"
                                         f"- The {ie} **{item_name}** is currently out of stock.\n"
                                         f" - Until a user who owns this item chooses to "
                                         f"sell it, stocks cannot be refilled."))

                    if quantity > stock_item:
                        proper_name = " ".join(proper_name.split("_"))
                        proper_name = make_plural(proper_name, stock_item)
                        their_name = make_plural(proper_name, quantity)
                        return await interaction.response.send_message( 
                            embed=membed(f"## Unsuccessful Transaction\n"
                                         f"There are only **{stock_item}** {ie} **{proper_name.title()}** available.\n"
                                         f"{ARROW}Meaning you cannot possibly buy **{quantity}** {their_name.title()}."))

                    total_cost = int((item["cost"] * int(quantity)))

                    if wallet_amt < int(total_cost):
                        proper_name = " ".join(proper_name.split("_"))
                        proper_name = make_plural(proper_name, quantity)
                        return await interaction.response.send_message( 
                            embed=membed(f"## Unsuccessful Transaction\n"
                                         f"You'll need {CURRENCY}**{total_cost - wallet_amt:,}** more to "
                                         f"purchase {quantity} {ie} **{proper_name.title()}**."))

                    await self.update_inv_new(interaction.user, +int(quantity), item["name"], conn)
                    await self.update_bank_new(interaction.user, conn, -total_cost)
                    modify_stock(item_name, "-", quantity)

                    match quantity:
                        case 1:
                            return await interaction.response.send_message( 
                                embed=membed(f"## Success\n"
                                             f"- Purchased **1** {ie} **{item_name}** by paying "
                                             f"{CURRENCY}**{total_cost:,}**.\n"
                                             f" - The items requested have been added to your inventory."))
                        case _:
                            their_name = ' '.join(proper_name.split("_"))
                            their_name = make_plural(their_name, quantity)
                            await interaction.response.send_message( 
                                embed=membed(f"## Success\n"
                                             f"- Purchased **{quantity}** {ie} **{their_name.title()}** by"
                                             f" paying {CURRENCY}**{total_cost:,}**.\n"
                                             f" - The items requested have been added to your inventory."))

    @app_commands.command(name='sell', description='sell an item from your inventory.')
    @app_commands.guilds(discord.Object(id=829053898333225010), discord.Object(id=780397076273954886))
    @app_commands.describe(item_name='the name of the item you want to sell.',
                           sell_quantity='the quantity you wish to sell. defaults to 1.')
    async def sell(self, interaction: discord.Interaction,
                   item_name: Literal['Keycard', 'Trophy', 'Clan License', 'Resistor', 'Amulet', 'Dynamic Item', 'Hyperion', 'Crisis', 'Odd Eye'],
                   sell_quantity: Optional[Literal[1, 2, 3, 4, 5]]):

        if sell_quantity is None:
            sell_quantity = 1

        name = item_name.replace(" ", "_")
        async with self.client.pool_connection.acquire() as conn: 
            conn: asqlite_Connection

            if await self.can_call_out(interaction.user, conn):
                return await interaction.response.send_message(embed=self.not_registered) 

            for item in SHOP_ITEMS:
                if name == item["name"]:
                    ie = item['emoji']
                    cost = int(round((item["cost"] / 4) * sell_quantity, ndigits=None))
                    quantity = await self.update_inv_new(interaction.user, 0, item["name"], conn)

                    if quantity[0] < 1:
                        return await interaction.response.send_message( 
                            embed=membed(f"You don't have a {ie} **{item_name}** in your inventory."))

                    new_quantity = quantity[0] - sell_quantity
                    if new_quantity < 0:
                        return await interaction.response.send_message( 
                            f"You are requesting to sell more than what you currently own. Not possible.")

                    await self.change_inv_new(interaction.user, new_quantity, item["name"], conn)
                    modify_stock(item_name, "+", sell_quantity)
                    await self.update_bank_new(interaction.user, conn, +cost)

                    match sell_quantity:
                        case 1:
                            proper_name = item.setdefault('qn', None) or name
                            proper_name = ' '.join(proper_name.split('_'))
                            return await interaction.response.send_message( 
                                embed=membed(f"You just sold 1 {ie} **{proper_name.title()}** and got "
                                             f"<:robux:1146394968882151434> **{cost:,}** in return."))
                        case _:
                            proper_name = item.setdefault('qn', None) or name
                            proper_name = ' '.join(proper_name.split('_'))
                            proper_name = make_plural(proper_name, sell_quantity)
                            return await interaction.response.send_message( 
                                embed=membed(f"You just sold {sell_quantity} {ie} **{proper_name.title()}** and got "
                                             f"<:robux:1146394968882151434> **{cost:,}** in return."))

    @app_commands.command(name="work", description="work and earn an income, if you have a job.")
    @app_commands.guilds(discord.Object(id=829053898333225010), discord.Object(id=780397076273954886))
    async def work(self, interaction: discord.Interaction):

        await interaction.response.defer(thinking=True, ephemeral=True) 

        words = {
            "Plumber": [("TOILET", "SINK", "SEWAGE", "SANITATION", "DRAINAGE", "PIPES"), 400000000],
            "Cashier": [("ROBUX", "TILL", "ITEMS", "WORKER", "REGISTER", "CHECKOUT", "TRANSACTIONS", "RECEIPTS"),
                        500000000],
            "Fisher": [("FISHING", "NETS", "TRAWLING", "FISHERMAN", "CATCH", "VESSEL", "AQUATIC", "HARVESTING", "MARINE"),
                       550000000],
            "Janitor": [("CLEANING", "SWEEPING", "MOPING", "CUSTODIAL", "MAINTENANCE", "SANITATION", "BROOM", "VACUUMING"),
                        650000000],
            "Youtuber": [("CONTENT CREATION", "VIDEO PRODUCTION", "CHANNEL", "SUBSCRIBERS", "EDITING", "UPLOAD",
                         "VLOGGING", "MONETIZATION", "THUMBNAILS", "ENGAGEMENT"), 1000000000],
            "Police": [("LAW ENFORCEMENT", "PATROL", "CRIME PREVENTION", "INVESTIGATION", "ARREST", "UNIFORM", "BADGE",
                       "INTERROGATION"), 1200000000]
        }

        async with self.client.pool_connection.acquire() as conn: 
            conn: asqlite_Connection

            if await self.can_call_out(interaction.user, conn):
                return await interaction.followup.send(embed=self.not_registered)
                
            job_val = await self.get_job_data_only(user=interaction.user, conn_input=conn)
            
            if job_val == "None":
                return await interaction.followup.send(embed=membed("You don't have a job, get one first."))

            possible_words: tuple = words.get(job_val)[0]
            selected_word = choice(possible_words)

            letters_to_hide = max(1, len(selected_word) // 3)

            indices_to_hide = [i for i, char in enumerate(selected_word) if char.isalpha()]
            indices_hidden = sample(indices_to_hide, min(letters_to_hide, len(indices_to_hide)))

            hidden_word_list = [char if i not in indices_hidden else '_' for i, char in enumerate(selected_word)]
            hidden_word = ''.join(hidden_word_list)

            def check(m):
                return m.content.lower() == selected_word.lower() and m.channel == interaction.channel and m.author == interaction.user

            await interaction.followup.send(
                embed=membed(
                    f"## <:worke:1195716983384191076> What is the word?\n"
                    f"Replace the blanks \U0000279c [`{hidden_word}`](https://www.sss.com)."))

            my_msg = await interaction.channel.send("Waiting for correct input..")

            try:
                await self.client.wait_for('message', check=check, timeout=15.0)
            except asyncTE:
                await interaction.followup.send(f"`BOSS`: Too slow, you get nothing for the attitude. I expect better "
                                                f"of you next time.")
            else:
                salary = words.get(job_val)[-1]
                rangeit = randint(10000000, salary)
                await self.update_bank_new(interaction.user, conn, rangeit, "bank")
                await my_msg.edit(content=f"`BOSS`: Good work from you {interaction.user.display_name}, got the "
                                          f"job done. You got **\U000023e3 {rangeit:,}** for your efforts. The "
                                          f"money has been sent to your bank account.")

    @app_commands.command(name="balance", description="returns a user's current balance.")
    @app_commands.describe(user='the user to return the balance of')
    @app_commands.guild_only()
    @app_commands.checks.dynamic_cooldown(owners_nolimit)
    async def find_balance(self, interaction: discord.Interaction, user: Optional[discord.Member]):
        """Returns a user's balance."""

        await interaction.response.defer(thinking=True) 

        user = user or interaction.user

        async with self.client.pool_connection.acquire() as conn: 
            conn: asqlite_Connection

            if await self.can_call_out(user, conn) and (user.id != interaction.user.id):
                return await interaction.followup.send(embed=membed(f"{user.name} isn't registered."))

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
                return await interaction.followup.send(embed=norer)
            else:
                new_data = await self.get_bank_data_new(user, conn)
                bank = new_data[1] + new_data[2]
                inv = 0

                for item in SHOP_ITEMS:
                    name = item["name"]
                    cost = item["cost"]
                    data = await self.get_one_inv_data_new(user, name, conn)
                    inv += int(cost) * data

                job_val = await self.get_job_data_only(user=user, conn_input=conn)

                balance = discord.Embed(color=0x2F3136, timestamp=discord.utils.utcnow())
                balance.set_author(name=f"{user.name}'s balance", icon_url=user.display_avatar.url)

                balance.add_field(name="<:walleten:1195719280898097192> Wallet", value=f"\U000023e3 {new_data[1]:,}", inline=True)
                balance.add_field(name="<:banken:1195708938734288967> Bank", value=f"\U000023e3 {new_data[2]:,}", inline=True)
                balance.add_field(name="<:joben:1195709539853553664> Job", value=f"{job_val}", inline=True)
                balance.add_field(name="<:netben:1195710007233228850> Money Net", value=f"\U000023e3 {bank:,}", inline=True)
                balance.add_field(name="<:netinven:1195711122343481364> Inventory Net", value=f"\U000023e3 {inv:,}", inline=True)
                balance.add_field(name="<:nettotalen:1195710560910725180> Total Net", value=f"\U000023e3 {inv+bank:,}", inline=True)

                if user.id in {992152414566232139, 546086191414509599}:
                    balance.set_footer(icon_url='https://cdn.discordapp.com/emojis/1174417902980583435.webp?size=128&'
                                                'quality=lossless',
                                       text='mallow is dazzled')

                await interaction.followup.send(embed=balance)

    @app_commands.command(name="discontinue", description="opt out of the virtual economy.")
    @app_commands.guilds(discord.Object(id=829053898333225010), discord.Object(id=780397076273954886))
    @app_commands.describe(member='the user to remove all of the data of')
    async def discontinue_bot(self, interaction: discord.Interaction, member: Optional[discord.Member]):

        member = member or interaction.user

        if interaction.user.id not in {992152414566232139, 546086191414509599}:
            if member is not None:
                return await interaction.response.send_message(embed=ERR_UNREASON) 
        else: 
            if member.bot:
                return await interaction.response.send_message(embed=ERR_UNREASON) 

        async with self.client.pool_connection.acquire() as conn: 
            conn: asqlite_Connection
            data = await self.get_bank_data_new(member, conn)

            if data is None:
                await interaction.response.send_message( 
                    embed=membed(f"Cannot perform this action, {member.name} is not on our database."))
            else:

                if member.id == interaction.user.id:
                    view = ConfirmDeny(interaction, self.client, member)
                    await interaction.response.send_message("## Are you sure you want to do this?\n" 
                                                            "You are about to erase all of your data "
                                                            "associated with your account.\n"
                                                            "**This process is irreversible, you cannot "
                                                            "recover this data afterwards.**",
                                                            view=view)  
                    view.msg = await interaction.original_response()
                    return
                tables_to_delete = [BANK_TABLE_NAME, INV_TABLE_NAME, COOLDOWN_TABLE_NAME, SLAY_TABLE_NAME]
                for table in tables_to_delete:
                    await conn.execute(f"DELETE FROM `{table}` WHERE userID = ?", (member.id,))

                await conn.commit()
                embed = discord.Embed(colour=0x2F3136,
                                      description=f"## <:successful:1183089889269530764> {member.name}'s records have been wiped.\n"
                                                  f"- {member.name} can register again at any time"
                                                  f" if {member.name} checks their balance.")

                await interaction.response.send_message(embed=embed) 

    @app_commands.command(name="withdraw", description="withdraw robux from your account.")
    @app_commands.guilds(discord.Object(id=829053898333225010), discord.Object(id=780397076273954886))
    @app_commands.describe(robux='the amount of robux to withdraw. Supports Shortcuts (max, all, exponents).')
    @app_commands.checks.dynamic_cooldown(owners_nolimit)
    async def withdraw(self, interaction: discord.Interaction, robux: str):

        user = interaction.user
        actual_amount = determine_exponent(robux)

        async with (self.client.pool_connection.acquire() as conn): 
            conn: asqlite_Connection
            if await self.can_call_out(interaction.user, conn):
                await interaction.response.send_message(embed=self.not_registered) 
            users = await self.get_bank_data_new(user, conn)

            bank_amt = users[2]
            if isinstance(actual_amount, str):
                if actual_amount.lower() == "all" or actual_amount.lower() == "max":
                    wallet_new = await self.update_bank_new(user, conn, +bank_amt)
                    bank_new = await self.update_bank_new(user, conn, -bank_amt, "bank")

                    embed = discord.Embed(colour=0x2F3136)


                    embed.add_field(name=f"<:withdraw:1195657655134470155> Withdrawn", value=f"\U000023e3 {bank_amt:,}", inline=False)
                    embed.add_field(name=f"Current Wallet Balance", value=f"\U000023e3 {wallet_new[0]:,}")
                    embed.add_field(name=f"Current Bank Balance", value=f"\U000023e3 {bank_new[0]:,}")

                    return await interaction.response.send_message(embed=embed) 
                return await interaction.response.send_message(embed=ERR_UNREASON) 

            amount_conv = abs(int(actual_amount))
            if amount_conv < 5000:
                embed = discord.Embed(colour=0x2F3136,
                                      description=f"- For performance reasons, a minimum of "
                                                  f"\U000023e3 **5,000** must be withdrawn.\n"
                                                  f" - You wanted to withdraw \U000023e3 **{amount_conv:,}**.\n")
                return await interaction.response.send_message(embed=embed) 

            elif amount_conv > bank_amt:
                embed = discord.Embed(colour=0x2F3136,
                                      description=f"- You do not have that much money in your bank.\n"
                                                  f" - You wanted to withdraw \U000023e3 **{amount_conv:,}**.\n"
                                                  f" - Currently, you only have \U000023e3 **{bank_amt:,}**.")
                return await interaction.response.send_message(embed=embed) 

            else:
                wallet_new = await self.update_bank_new(user, conn, +amount_conv)
                bank_new = await self.update_bank_new(user, conn, -amount_conv, "bank")

                embed = discord.Embed(colour=0x2F3136)
                embed.add_field(name=f"<:withdraw:1195657655134470155> Withdrawn", value=f"\U000023e3 {amount_conv:,}", inline=False)
                embed.add_field(name=f"Current Wallet Balance", value=f"\U000023e3 {wallet_new[0]:,}")
                embed.add_field(name=f"Current Bank Balance", value=f"\U000023e3 {bank_new[0]:,}")

                return await interaction.response.send_message(embed=embed) 

    @app_commands.command(name='deposit', description="deposit robux to your bank account.")
    @app_commands.guilds(discord.Object(id=829053898333225010), discord.Object(id=780397076273954886))
    @app_commands.describe(robux='the amount of robux to deposit. Supports Shortcuts (max, all, exponents).')
    @app_commands.checks.dynamic_cooldown(owners_nolimit)
    async def deposit(self, interaction: discord.Interaction, robux: str):
        user = interaction.user
        actual_amount = determine_exponent(robux)

        async with self.client.pool_connection.acquire() as conn: 
            conn: asqlite_Connection

            if await self.can_call_out(interaction.user, conn):
                return await interaction.response.send_message(embed=self.not_registered) 
            users = await self.get_bank_data_new(user, conn)
            wallet_amt = users[1]
            if isinstance(actual_amount, str):
                if actual_amount.lower() == "all" or actual_amount.lower() == "max":
                    wallet_new = await self.update_bank_new(user, conn, -wallet_amt)
                    bank_new = await self.update_bank_new(user, conn, +wallet_amt, "bank")

                    embed = discord.Embed(colour=0x2F3136)
                    embed.add_field(name="<:deposit:1195657772231036948> Deposited", value=f"\U000023e3 {wallet_amt:,}", inline=False)
                    embed.add_field(name="Current Wallet Balance", value=f"\U000023e3 {wallet_new[0]:,}")
                    embed.add_field(name="Current Bank Balance", value=f"\U000023e3 {bank_new[0]:,}")

                    return await interaction.response.send_message(embed=embed) 
                return await interaction.response.send_message(embed=ERR_UNREASON) 

            amount_conv = abs(int(actual_amount))
            if amount_conv < 5000:
                embed = discord.Embed(colour=0x2F3136,
                                      description=f"- For performance reasons, a minimum of "
                                                  f"\U000023e3 **5,000** must be deposited.\n"
                                                  f" - You wanted to deposit \U000023e3 **{amount_conv:,}**.\n")
                return await interaction.response.send_message(embed=embed) 

            elif amount_conv > wallet_amt:
                embed = discord.Embed(colour=0x2F3136,
                                      description=f"- You do not have that much money in your wallet.\n"
                                                  f" - You wanted to deposit \U000023e3 **{amount_conv:,}**.\n"
                                                  f" - Currently, you only have \U000023e3 **{wallet_amt:,}**.")
                return await interaction.response.send_message(embed=embed) 
            else:
                wallet_new = await self.update_bank_new(user, conn, -amount_conv)
                bank_new = await self.update_bank_new(user, conn, +amount_conv, "bank")

                embed = discord.Embed(colour=0x2F3136)
                embed.add_field(name="<:deposit:1195657772231036948> Deposited", value=f"\U000023e3 {amount_conv:,}", inline=False)
                embed.add_field(name="Current Wallet Balance", value=f"\U000023e3 {wallet_new[0]:,}")
                embed.add_field(name="Current Bank Balance", value=f"\U000023e3 {bank_new[0]:,}")

                return await interaction.response.send_message(embed=embed) 

    @app_commands.command(name='leaderboard', description='rank users based on various stats.')
    @app_commands.guilds(discord.Object(id=829053898333225010), discord.Object(id=780397076273954886))
    @app_commands.checks.dynamic_cooldown(owners_nolimit)
    async def get_leaderboard(self, interaction: discord.Interaction):

        async with self.client.pool_connection.acquire() as conn: 
            conn: asqlite_Connection = conn

            data = await conn.execute(
                f"SELECT `userID`, SUM(`wallet` + `bank`) as total_balance FROM `{BANK_TABLE_NAME}` GROUP BY `userID` ORDER BY total_balance DESC",
                ())
            data = await data.fetchall()

            not_database = []
            index = 1

            for member in data:
                member_name = await self.client.fetch_user(member[0])
                their_badge = UNIQUE_BADGES.setdefault(member_name.id, f"")
                member_amt = member[1]
                msg1 = f"**{index}.** {member_name.name} {their_badge} \U00003022 {CURRENCY}{member_amt:,}"
                not_database.append(msg1)
                index += 1

            msg = "\n".join(not_database)

            lb = discord.Embed(
                title=f"Leaderboard: Bank + Wallet",
                description=f"Displaying the top `{index-1}` users.\n\n"
                            f"{msg}",
                color=0x2F3136,
                timestamp=discord.utils.utcnow()
            )
            lb.set_footer(
                text=f"Ranked globally",
                icon_url=self.client.user.avatar.url)

        lb_view = Leaderboard(self.client)
        await interaction.response.send_message(embed=lb, view=lb_view) 
        lb_view.message = await interaction.original_response()

    @commands.guild_only()
    @commands.cooldown(1, 5)
    @commands.command(name='extend_profile', description='display misc info on a user.',
                      aliases=('e_p', 'ep', 'extend'))
    async def extend_profile(self, ctx: commands.Context, username: Optional[discord.Member]):
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

            procfile = discord.Embed(title='Profile Summary', description=f'This mostly displays {username.display_name}\'s '
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
                                     f"\U0000279c Voice State: {user_stats['voice_status']}", )
            procfile.set_thumbnail(url=username.display_avatar.url)
            procfile.set_footer(text=f"{discord.utils.utcnow().strftime('%A %d %b %Y, %I:%M%p')}")
            await ctx.send(embed=procfile)

    rob = app_commands.Group(name='rob', description='rob different places or people.',
                                guild_only=True, guild_ids=[829053898333225010, 780397076273954886])

    @rob.command(name="user", description="rob robux from another user.")
    @app_commands.describe(other='the user to rob from')
    @app_commands.checks.dynamic_cooldown(owners_nolimit)
    async def rob_the_user(self, interaction: discord.Interaction, other: discord.Member):
        """Rob someone else."""
        primary_id = str(interaction.user.id)
        other_id = str(other.id)

        async with self.client.pool_connection.acquire() as conn: 
            conn: asqlite_Connection

            if other_id == primary_id:
                embed = membed('You cannot rob yourself, everyone knows that.')
                return await interaction.response.send_message(embed=embed) 
            elif other.bot:
                embed = membed('You are not allowed to steal from bots, back off my kind')
                return await interaction.response.send_message(embed=embed) 
            elif other_id == "992152414566232139":
                embed = membed('You are not allowed to rob the developer of this bot.')
                return await interaction.response.send_message(embed=embed) 
            elif not (await self.can_call_out_either(interaction.user, other, conn)):
                embed = membed(f'- Either you or {other.name} does not have an account.\n'
                               f' - </balance:1179817617435926686> to register.')
                return await interaction.response.send_message(embed=embed) 
            else:
                prim_bal = await self.get_bank_data_new(interaction.user, conn)
                host_bal = await self.get_bank_data_new(other, conn)

                caught = [0, 1]
                result = choices(caught, weights=(49, 51), k=1)

                if not result[0]:
                    fine = randint(1, prim_bal[1])

                    prcf = round((fine/prim_bal[1])*100, ndigits=1)

                    await self.update_bank_new(interaction.user, conn, -fine)
                    await self.update_bank_new(other, conn, +fine)
                    conte = (f'- You were caught stealing now you paid {other.name} \U000023e3 **{fine:,}**.\n'
                             f'- **{prcf}**% of your money was handed over to the victim.')
                    return await interaction.response.send_message(embed=membed(conte)) 
                else:
                    steal_amount = randint(1, host_bal[1])
                    await self.update_bank_new(interaction.user, conn, +steal_amount)
                    await self.update_bank_new(other, conn, -steal_amount)

                    prcf = round((steal_amount / host_bal[1]) * 100, ndigits=1)

                    return await interaction.response.send_message( 
                        embed=membed(f"- You managed to steal \U000023e3 **{steal_amount:,}** from {other.name}.\n"
                                     f"- You took a dandy **{prcf}**% of {other.name}'s `wallet` balance."),
                        delete_after=10.0)

    @rob.command(name='casino', description='rob a casino vault.')
    async def rob_the_casino(self, interaction: discord.Interaction):

        await interaction.response.defer() 

        async with self.client.pool_connection.acquire() as conn: 
            conn: asqlite_Connection

            if await self.can_call_out(interaction.user, conn):
                return await interaction.followup.send(embed=self.not_registered)


            cooldown = await self.fetch_cooldown(conn, user=interaction.user, cooldown_type="casino")

            if cooldown is not None:
                if cooldown[0] in {"0", 0}:
                    channel = interaction.channel
                    ranint = randint(1000, 1999)
                    await channel.send(
                        embed=membed(f'A 4-digit PIN is required to enter the casino.\n'
                                     f'Here are the first 3 digits: {str(ranint)[:3]}'))

                    def check(m):
                        return m.content == f'{str(ranint)}' and m.channel == channel and m.author == interaction.user

                    try:
                        await self.client.wait_for('message', check=check, timeout=30.0)
                    except asyncTE:
                        await interaction.followup.send(
                            embed=membed(f"Too many seconds passed. Access denied. (The code was {ranint})"))
                    else:
                        msg = await interaction.followup.send(
                            embed=membed(f'You cracked the code and got access. Good luck escaping unscathed.'),
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

    @app_commands.command(name='coinflip', description='bet your robux on a coin flip.')
    @app_commands.guilds(discord.Object(id=829053898333225010), discord.Object(id=780397076273954886))
    @app_commands.describe(bet_on='what side of the coin you bet it will flip on',
                           amount='the amount of robux to bet. Supports Shortcuts (exponents only)')
    @app_commands.checks.dynamic_cooldown(owners_nolimit)
    @app_commands.rename(bet_on='side', amount='robux')
    async def coinflip(self, interaction: discord.Interaction, bet_on: str, amount: int):
        user = interaction.user

        async with self.client.pool_connection.acquire() as conn: 

            amount = determine_exponent(str(amount))

            bet_on = "heads" if "h" in bet_on.lower() else "tails"
            if not 5000 <= amount <= 100_000_000:
                return await interaction.response.send_message(  
                    embed=membed(f"*As per-policy*, the minimum bet is {CURRENCY}**5,000**, the maximum is "
                                 f"{CURRENCY}**200,000,000**."))

            conn: asqlite_Connection
            if await self.can_call_out(interaction.user, conn):
                return await interaction.response.send_message(embed=self.not_registered) 
            wallet_amt = await self.get_wallet_data_only(user, conn)
            if wallet_amt < amount:
                return await interaction.response.send_message(embed=ERR_UNREASON) 

            coin = ["heads", "tails"]
            result = choice(coin)

            if result != bet_on:
                await self.update_bank_new(user, conn, -amount)
                return await interaction.response.send_message( 
                    embed=membed(f"You got {result}, meaning you lost \U000023e3 **{amount:,}**."))

            await self.update_bank_new(user, conn, +amount)
            return await interaction.response.send_message(embed=membed(f"You got {result}, meaning you won \U000023e3 " 
                                                                        f"**{amount:,}**."))

    @app_commands.command(name="blackjack",
                          description="test your skills at blackjack.")
    @app_commands.guilds(discord.Object(id=829053898333225010), discord.Object(id=780397076273954886))
    @app_commands.checks.dynamic_cooldown(owners_nolimit)
    @app_commands.rename(bet_amount='robux')
    @app_commands.describe(bet_amount='the amount of robux to bet on. Supports Shortcuts (max, all, exponents).')
    async def play_blackjack(self, interaction: discord.Interaction, bet_amount: str):

        await interaction.response.defer(thinking=True) 

        # ------ Check the user is registered or already has an ongoing game ---------
        if len(self.client.games) >= 2: 
            return await interaction.followup.send(
                embed=membed(
                    "- The maximum consecutive blackjack games being held has been reached.\n"
                    "- To prevent server overload, you cannot start a game until the current games "
                    "being played has been finished.\n"
                    " - The maximum consecutive blackjack game quota has been set to `2`."
                )
            )

        if self.client.games.setdefault(interaction.user.id, None) is not None: 
            return await interaction.followup.send("You already have an ongoing game taking place.")

        async with self.client.pool_connection.acquire() as conn: 
            conn: asqlite_Connection
            if await self.can_call_out(interaction.user, conn):
                return await interaction.followup.send(embed=self.not_registered)

        # --------------------------------------------------------------

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
                if has_keycard and wallet_amt >= 100_000_000:
                    namount = 100_000_000
                else:
                    namount = wallet_amt
            else:
                return await interaction.followup.send(embed=ERR_UNREASON)  

        # -------------------- Check to see if user has sufficient balance --------------------------

        if has_keycard:
            if (namount > 100_000_000) or (namount < 500_000):
                err = discord.Embed(colour=0x2F3136, description=f'## You did not meet the blackjack criteria:\n'
                                                                 f'- You wanted to bet {CURRENCY}**{namount:,}**\n'
                                                                 f' - A minimum bet of {CURRENCY}**500,000** must '
                                                                 f'be made\n'
                                                                 f' - A maximum bet of {CURRENCY}**100,000,000** '
                                                                 f'can only be made.')
                return await interaction.followup.send(embed=err)  
            if namount > wallet_amt:
                err = discord.Embed(colour=0x2F3136, description=f'Cannot perform this action, '
                                                                 f'you only have {CURRENCY}**{wallet_amt:,}**.\n'
                                                                 f'You\'ll need {CURRENCY}**{namount - wallet_amt:,}**'
                                                                 f' more in your wallet first.')
                return await interaction.followup.send(embed=err)  
        else:
            if (namount > 50_000_000) or (namount < 1000000):
                err = discord.Embed(colour=0x2F3136, description=f'## You did not meet the blackjack criteria:\n'
                                                                 f'- You wanted to bet {CURRENCY}**{namount:,}**\n'
                                                                 f' - A minimum bet of {CURRENCY}**1,000,000** must '
                                                                 f'be made (this can decrease when you acquire a'
                                                                 f' <:lanyard:1165935243140796487> Keycard).\n'
                                                                 f' - A maximum bet of {CURRENCY}**50,000,000** '
                                                                 f'can only be made (this can increase when you '
                                                                 f'acquire a <:lanyard:1165935243140796487> '
                                                                 f'Keycard).')
                return await interaction.followup.send(embed=err)  
            if namount > wallet_amt:
                err = discord.Embed(colour=0x2F3136, description=f'Cannot perform this action, '
                                                                 f'you only have {CURRENCY}**{wallet_amt:,}**.\n'
                                                                 f'You\'ll need {CURRENCY}**{namount - wallet_amt:,}**'
                                                                 f' more in your wallet first.')
                return await interaction.followup.send(embed=err)  

        # ------------ In the case where the user already won --------------
        if self.calculate_hand(player_hand) == 21:

            bj_lose = await conn.execute('SELECT bjl FROM bank WHERE userID = ?', (interaction.user.id,))
            bj_lose = await bj_lose.fetchone()
            new_bj_win = await self.update_bank_new(interaction.user, conn, 1, "bjw")
            new_total = new_bj_win[0] + bj_lose[0]
            prctnw = round((new_bj_win[0]/new_total)*100)

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
            embed.add_field(name=f"{interaction.user.name} (Player)", value=f"**Cards** - {' '.join(d_fver_p)}\n"
                                                                      f"**Total** - `{sum(player_hand)}`")
            embed.add_field(name=f"{interaction.guild.me.name} (Dealer)", value=f"**Cards** - {' '.join(d_fver_d)}\n"
                                                                   f"**Total** - {sum(dealer_hand)}")
            return await interaction.followup.send(embed=embed) 

        shallow_pv = []
        shallow_dv = []

        for number in player_hand:
            remade = display_user_friendly_card_format(number)
            shallow_pv.append(remade)

        for number in dealer_hand:
            remade = display_user_friendly_card_format(number)
            shallow_dv.append(remade)

        self.client.games[interaction.user.id] = (deck, player_hand, dealer_hand, shallow_dv, shallow_pv, namount) 


        start = discord.Embed(colour=0x2B2D31,
                              description=f"The game has started. May the best win.\n"
                                          f"`\U000023e3 ~{format_number_short(namount)}` is up for grabs on the table.")

        start.add_field(name=f"{interaction.user.name} (Player)", value=f"**Cards** - {' '.join(shallow_pv)}\n"
                                                                  f"**Total** - `{sum(player_hand)}`")
        start.add_field(name=f"{interaction.guild.me.name} (Dealer)", value=f"**Cards** - {shallow_dv[0]} `?`\n"
                                                               f"**Total** - ` ? `")
        start.set_author(icon_url=interaction.user.display_avatar.url, name=f"{interaction.user.name}'s blackjack game")
        start.set_footer(text="K, Q, J = 10  |  A = 1 or 11")
        my_view = BlackjackUi(interaction, self.client)
        await interaction.followup.send(
            content="What do you want to do?\nPress **Hit** to to request an additional card, **Stand** to finalize "
                    "your deck or **Forfeit** to end your hand prematurely, sacrificing half of your original bet.",
            embed=start, view=my_view)
        my_view.message = await interaction.original_response()

        await self.raise_pmulti_warning(interaction, pmulti[0])

    @app_commands.command(name="bet",
                          description="bet your robux on a dice roll.")
    @app_commands.guilds(discord.Object(id=829053898333225010), discord.Object(id=780397076273954886))
    @app_commands.checks.dynamic_cooldown(owners_nolimit)
    @app_commands.rename(exponent_amount='robux')
    @app_commands.describe(exponent_amount='the amount of robux to bet. Supports Shortcuts (max, all, exponents).')
    async def bet(self, interaction: discord.Interaction, exponent_amount: str):
        """Bet your robux on a gamble to win or lose robux."""

        # --------------- Contains checks before betting i.e. has keycard, meets bet constraints. -------------
        async with self.client.pool_connection.acquire() as conn: 
            if await self.can_call_out(interaction.user, conn):
                return await interaction.response.send_message(embed=self.not_registered) 
            conn: asqlite_Connection
            wallet_amt = await self.get_wallet_data_only(interaction.user, conn)
            pmulti = await self.get_pmulti_data_only(interaction.user, conn)
            has_keycard = await self.get_one_inv_data_new(interaction.user, "Keycard", conn) >= 1
            hyperion_qty = await self.get_one_inv_data_new(interaction.user, "Hyperion", conn)
            expo = determine_exponent(exponent_amount)

            try:
                assert isinstance(expo, int)
                amount = expo
            except AssertionError:
                if exponent_amount.lower() in {'max', 'all'}:
                    amount = 100000000 if has_keycard else 50000000
                else:
                    return await interaction.response.send_message(embed=ERR_UNREASON) 

            if amount == 0:
                await interaction.response.send_message(embed=ERR_UNREASON) 
            if has_keycard:
                if (amount > 100000000) or (amount < 100000):
                    err = discord.Embed(colour=0x2F3136, description=f'## You did not meet the bet criteria:\n'
                                                                     f'- You wanted to bet {CURRENCY}**{amount:,}**\n'
                                                                     f' - A minimum bet of {CURRENCY}**100,000** must '
                                                                     f'be made\n'
                                                                     f' - A maximum bet of {CURRENCY}**100,000,000** '
                                                                     f'can only be made.')
                    return await interaction.response.send_message(embed=err) 
                elif amount > wallet_amt:
                    err = discord.Embed(colour=0x2F3136, description=f'Cannot perform this action, '
                                                                     f'you only have {CURRENCY}**{wallet_amt:,}**.\n'
                                                                     f'You\'ll need {CURRENCY}**{amount - wallet_amt:,}**'
                                                                     f' more in your wallet first.')
                    return await interaction.response.send_message(embed=err) 
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
                    return await interaction.response.send_message(embed=err) 
                elif amount > wallet_amt:
                    err = discord.Embed(colour=0x2F3136, description=f'Cannot perform this action, '
                                                                     f'you only have {CURRENCY}**{wallet_amt:,}**.\n'
                                                                     f'You\'ll need {CURRENCY}**{amount - wallet_amt:,}**'
                                                                     f' more in your wallet first.')
                    return await interaction.response.send_message(embed=err) 

            # --------------------------------------------------------
            smulti = SERVER_MULTIPLIERS.setdefault(interaction.guild.id, 0) + pmulti[0]
            badges = set()
            if hyperion_qty:
                badges.add("<:bot:1195463351338283199>")
            if pmulti[0] > 0:
                badges.add(PREMIUM_CURRENCY)
            if has_keycard:
                badges.add("<:lanyard:1165935243140796487>")
                your_choice = choices([1, 2, 3, 4, 5, 6], weights=[37 / 3, 37 / 3, 37 / 3, 63 / 3, 63 / 3, 63 / 3], k=1)
                bot_choice = choices([1, 2, 3, 4, 5, 6],
                                     weights=[65 / 4, 65 / 4, 65 / 4, 65 / 4, 35 / 2, 35 / 2], k=1)
            else:
                bot_choice = choices([1, 2, 3, 4, 5, 6],
                                     weights=[10, 10, 15, 27, 15, 23], k=1)
                your_choice = choices([1, 2, 3, 4, 5, 6], weights=[55/3, 55/3, 55/3, 45/3, 45/3, 45/3], k=1)


            if your_choice[0] > bot_choice[0]:

                bet_stuff = await self.get_bank_data_new(interaction.user, conn)
                id_won_amount, id_lose_amount = bet_stuff[5], bet_stuff[6]
                amount_after_multi = floor(((smulti / 100) * amount) + amount)
                await self.update_bank_new(interaction.user, conn, amount_after_multi, "betwa")
                new_amount_balance = await self.update_bank_new(interaction.user, conn, amount_after_multi)
                new_id_won_amount = await self.update_bank_new(interaction.user, conn, 1, "betw")
                prcntw = round((new_id_won_amount[0]/(id_lose_amount + new_id_won_amount[0]))*100, 1)


                embed = discord.Embed(description=f"**You've rolled higher!** You won {CURRENCY}**{amount_after_multi:,}** robux.\n"
                                                  f"Your new `wallet` balance is {CURRENCY}**{new_amount_balance[0]:,}**.\n"
                                                  f"You've won {prcntw}% of all games.",
                                      colour=discord.Color.brand_green())
                embed.set_author(name=f"{interaction.user.name}'s winning gambling game",
                                 icon_url=interaction.user.display_avatar.url)
            elif your_choice[0] == bot_choice[0]:
                embed = discord.Embed(description=f"**Tie.** You lost nothing nor gained anything!",
                                      colour=discord.Color.yellow())
                embed.set_author(name=f"{interaction.user.name}'s gambling game",
                                 icon_url=interaction.user.display_avatar.url)
            else:

                bet_stuff = await self.get_bank_data_new(interaction.user, conn)
                id_won_amount, id_lose_amount = bet_stuff[5], bet_stuff[6]

                await self.update_bank_new(interaction.user, conn, amount, "betla")
                new_amount_balance = await self.update_bank_new(interaction.user, conn, -amount)
                new_id_lose_amount = await self.update_bank_new(interaction.user, conn, 1, "betl")
                new_total = id_won_amount + new_id_lose_amount[0]

                prcntl = round((new_id_lose_amount[0]/new_total)*100, 1)

                embed = discord.Embed(description=f"**You've rolled lower!** You lost {CURRENCY}**{amount:,}**.\n"
                                                  f"Your new balance is {CURRENCY}**{new_amount_balance[0]:,}**.\n"
                                                  f"You've lost {prcntl}% of all games.",
                                       colour=discord.Color.brand_red())
                embed.set_author(name=f"{interaction.user.name}'s losing gambling game",
                                 icon_url=interaction.user.display_avatar.url)

            embed.add_field(name=interaction.user.name, value=f"Rolled `{your_choice[0]}` {''.join(badges)}")
            embed.add_field(name=self.client.user.name, value=f"Rolled `{bot_choice[0]}`")
            await interaction.response.send_message(embed=embed)  

            await self.raise_pmulti_warning(interaction, pmulti[0])

    @play_blackjack.autocomplete('bet_amount')
    @bet.autocomplete('exponent_amount')
    @deposit.autocomplete('robux')
    @withdraw.autocomplete('robux')
    async def callback_max_100(self, interaction: discord.Interaction, current: str) -> List[
        app_commands.Choice[str]]:

        chosen = {"all", "max", "50e6", "100e6"}
        return [
            app_commands.Choice(name=str(the_chose), value=str(the_chose))
            for the_chose in chosen if current.lower() in the_chose
        ]

    @slots.autocomplete('keyword')
    @highlow.autocomplete('robux')
    async def callback_max_75(self, interaction: discord.Interaction, current: str) -> List[
        app_commands.Choice[str]]:

        chosen = {"all", "max", "50e6", "75e6"}
        return [
            app_commands.Choice(name=str(the_chose), value=str(the_chose))
            for the_chose in chosen if current.lower() in the_chose
        ]


async def setup(client: commands.Bot):
    await client.add_cog(Economy(client))
