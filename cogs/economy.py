import asyncio
import datetime
from modules.inventory_funcs import *
from modules.bank_funcs import *
from discord.app_commands import AppCommandError
import discord
from discord.ext import commands
from random import randint, choices, choice
from discord import app_commands
import json
from typing import Optional, Literal
from tatsu.wrapper import ApiWrapper
CREATIVE_COLOR = discord.Color.random()

# C:\\Users\\Computer\\PycharmProjects\\pythonProject1\\cogs\\economy.json


with open('C:\\Users\\Computer\\PycharmProjects\\pythonProject3\\cogs\\economy.json') as file:
    amounts = json.load(file)

with open('C:\\Users\\Computer\\PycharmProjects\\pythonProject3\\cogs\\jobs.json') as file:
    job = json.load(file)

with open('C:\\Users\\Computer\\PycharmProjects\\pythonProject3\\cogs\\times.json') as file:
    times = json.load(file)


def saveAmountJobTimes():
    with open('C:\\Users\\Computer\\PycharmProjects\\pythonProject3\\cogs\\economy.json', 'w') as file:
        json.dump(amounts, file, indent=4)

    with open('C:\\Users\\Computer\\PycharmProjects\\pythonProject3\\cogs\\jobs.json', 'w') as file:
        json.dump(job, file, indent=4)

    with open('C:\\Users\\Computer\\PycharmProjects\\pythonProject3\\cogs\\times.json', 'w') as file:
        json.dump(times, file, indent=4)


def saveAmount():
    with open('C:\\Users\\Computer\\PycharmProjects\\pythonProject3\\cogs\\economy.json', 'w') as file:
        json.dump(amounts, file, indent=4)


def is_owner(interaction: discord.Interaction):
    if interaction.user.id == interaction.guild.owner_id:
        return True
    return False


def backup():
    with open('C:\\Users\\Computer\\PycharmProjects\\pythonProject1\\cogs\\backup.json', 'w') as file:
        json.dump(amounts, file, indent=4)


def is_exponential(array: list):
    if "e" in array:
        return True
    return False


def item_exists(what_to_find: str, where_to_find_it: str) -> bool:
    if what_to_find in where_to_find_it:
        return True
    return False


API_KEY = 'oOEQJTNUwb-7vZ5btX4z096G3WlFnpQEH'
CURRENCY = '<:robux:1146394968882151434>'
bonus_multiplier = {
    "🍕🍕": 1,
    "🤡🤡": 1,
    "💔💔": 1,
    "🍑🍑": 1,
    "🖕🖕": 1,
    "🍆🍆": 1,
    "😳😳": 2,
    "🌟🌟": 2,
    "🔥🔥": 3,
    "💔💔💔": 3,
    "🖕🖕🖕": 5,
    "🤡🤡🤡": 10,
    "🍕🍕🍕": 15,
    "🍆🍆🍆": 20,
    "🍑🍑🍑": 25,
    "😳😳😳": 30,
    "🌟🌟🌟": 35,
    "🔥🔥🔥": 50

}

async def get_tatsu_member_ranking(server_id: int, user_id: int):
    wrapper = ApiWrapper(key=API_KEY)
    result = await wrapper.get_member_ranking(server_id, user_id)
    return result


async def get_tatsu_profile(user_id: int):
    wrapper = ApiWrapper(key=API_KEY)
    result = await wrapper.get_profile(user_id)
    return result

def generate_slot_combination():
    situation = [1, 2]
    chosen = choices(situation, weights=(5000, 1000), k=1)
    slot = ['🔥', '😳', '🌟', '💔', '🖕', '🤡', '🍕', '🍆', '🍑']
    if chosen[0] == 1:
        slot1 = choices(slot, weights=(40, 100, 40, 100, 80, 40, 100, 40, 40), k=1)
        slot2 = choices(slot, weights=(40, 100, 40, 100, 80, 40, 100, 90, 40), k=1)
        slot3 = choices(slot, weights=(40, 100, 40, 100, 80, 40, 100, 90, 90), k=1)
        appendable_outcome = f'{slot1[0]}{slot2[0]}{slot3[0]}'
        return appendable_outcome
    if chosen[0] == 2:
        outcome = ['😳😳', '🌟🌟', '🔥🔥', '💔💔💔', '🖕🖕🖕', '🤡🤡🤡', '🍕🍕🍕', '🍆🍆🍆', '🍑🍑🍑', '😳😳😳', '🌟🌟🌟',
                   '🔥🔥🔥']
        chosen_outcome = choices(outcome, cum_weights=[2000, 5000, 5000, 3000, 4000, 7000, 3000, 3000, 3000, 3000, 0, 9000], k=1)
        appendable_outcome = chosen_outcome[0]
        if len(appendable_outcome) == 2:
            slot3 = choices(slot, weights=(40, 100, 40, 100, 80, 40, 100, 90, 90), k=1)
            appendable_outcome = appendable_outcome + slot3[0]

        return appendable_outcome


class Shop(app_commands.Group):
    @app_commands.command(name='view', description='view a list of items that are available for purchase.')
    async def shop(self, interaction: discord.Interaction):
        user = interaction.user
        await open_inv(user)

        em = discord.Embed(
            title="Shop",
            color=discord.Color(0x00ff00)
        )
        x = 1
        for item in shop_items:
            name = item["name"]
            cost = item["cost"]
            item_id = item["id"]
            item_info = item["info"]

            x += 1
            if x > 1:
                em.add_field(name=f"{name} -- {cost}",
                             value=f"{item_info}\nID: `{item_id}`", inline=False)

        await interaction.response.send_message(embed=em)

    @app_commands.command(description='get info about a particular item.')
    @app_commands.describe(item_name='the name of the item you want to sell.')
    async def lookup(self, interaction: discord.Interaction, item_name: Literal['Keycard']):
        for item in shop_items:
            name = item["name"]
            cost = item["cost"]
            item_info = item["info"]

            if name == item_name:
                em = discord.Embed(
                    description=item_info,
                    title=f"{name}"
                )

                sell_amt = int(cost / 4)

                em.add_field(name="Buying price", value=cost, inline=False)
                em.add_field(name="Selling price",
                             value=str(sell_amt), inline=False)

                return await interaction.response.send_message(embed=em)

        await interaction.response.send_message(f"There's no item named {item_name}")

#     @app_commands.guilds(discord.Object(id=829053898333225010), discord.Object(id=780397076273954886))

class Economy(commands.Cog):
    def __init__(self, client):
        self.client = client

    def cog_load(self):
        tree = self.client.tree
        self._old_tree_error = tree.on_error
        tree.on_error = self.on_app_command_error

    async def on_app_command_error(
            self,
            interaction: discord.Interaction,
            error: AppCommandError
    ):
        print(error)
        await interaction.response.send_message(f"an error was found.\n\n"
                                                f"{error}")

    @app_commands.command(name="getjob", description="become employed in a new job and earn a regular daily salary.")
    @app_commands.guilds(discord.Object(id=829053898333225010), discord.Object(id=780397076273954886))
    @app_commands.describe(job_name='the name of the job')
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: (i.guild.id, i.user.id))
    async def get_job(self, interaction: discord.Interaction,
                      job_name: Literal['plumber', 'cashier', 'fisher', 'janitor', 'youtuber']):
        try:
            user_id = str(interaction.user.id)
            if user_id in amounts:
                if job_name == "plumber":
                    job[user_id] = "Plumber"
                    await interaction.response.send_message("You are a plumber now.")
                elif job_name == "cashier":
                    job[user_id] = "Cashier"
                    await interaction.response.send_message("You are a cashier now.")
                elif job_name == "fisher":
                    job[user_id] = "Fisher"
                    await interaction.response.send_message("You are a fisher now.")
                elif job_name == "janitor":
                    job[user_id] = "Janitor"
                    await interaction.response.send_message("You are a janitor now.")
                elif job_name == "youtuber":
                    job[user_id] = "Youtuber"
                    await interaction.response.send_message("You are a youtuber now.")
            else:
                await interaction.response.send_message("You do not have an account")
            saveAmountJobTimes()
        except Exception as e:
            print(e)

    @app_commands.command(name='slots', description='take your chances and gamble on a slot machine.')
    @app_commands.guilds(discord.Object(id=829053898333225010), discord.Object(id=780397076273954886))
    @app_commands.describe(keyword='an integer/shortcut to bet on slots. typing max will bet 10million or less.')
    async def slots(self, interaction: discord.Interaction, keyword: str):

        if interaction.user.id != 546086191414509599:
            await interaction.response.send_message(f"This command will be implemented soon. ETA: <t:1703505600:R> (Christmas Day). Along with this `2` other commands will later be implemented:\n"
                                                    f"\U0000279c `/highlow`\n"
                                                    f"\U0000279c `/lottery`\n"
                                                    f"Stay tuned for more info.")
            return

        amount_list_exp = []
        user_id = str(interaction.user.id)
        # splitting the exponential value into its component parts
        for item in keyword:
            amount_list_exp.append(item.lower())

        # using the above function, iterates through each item
        if is_exponential(amount_list_exp):
            before_e = []
            after_e = []
            for item in amount_list_exp:
                if item != "e":
                    before_e.append(item)  # appends the numbers before exponent value in a separate before_e list
                else:
                    exponent_pos = amount_list_exp.index("e")  # finds the index position of the exponent itself
                    after_e.append(amount_list_exp[
                                   exponent_pos + 1:])  # appends everything after the exponent to another separate after_e list
                    break

            before_e_str, ten_exponent = "".join(before_e), "".join(
                after_e[0])  # concatenate the iterables to their respective strings

            exponent_value = 10 ** int(ten_exponent)
            actual_value = eval(f'{before_e_str}*{exponent_value}')
        else:
            if keyword == "max":
                if amounts[user_id] > 10000000:
                    actual_value = 10000000
                else:
                    actual_value = amounts[user_id]
            else:
                actual_value = keyword

        amount = int(actual_value)


        # -------------------- CHECKS GO HERE ----------------------------

        # ----------------------------------------------------------------


        sid_won_amount = str(user_id) + " " + str(4)
        sid_lose_amount = str(user_id) + " " + str(2)
        stotal = str(user_id) + " " + str(42)
        emoji_outcome = generate_slot_combination()  # this is a string
        freq1, freq2, freq3 = emoji_outcome[0], emoji_outcome[1], emoji_outcome[2]
        times[stotal] += 1
        if emoji_outcome.count(freq1) > 1:  # WINNING SLOT MACHINE
            # most_frequent_emoji_outcome = freq1
            times[sid_won_amount] += 1
            corresponding_multiplier = bonus_multiplier[f'{freq1*emoji_outcome.count(freq1)}']
            if corresponding_multiplier != 1:
                new_reward = round(corresponding_multiplier*amount, ndigits=None)
            else:
                new_reward = amount
            amounts[user_id] += new_reward
            saveAmountJobTimes()
            embed = discord.Embed(title=f"{interaction.user.name}'s slot machine",
                                  description=f"**\U0000003e** {emoji_outcome[0]} {emoji_outcome[1]} {emoji_outcome[2]} **\U0000003c**\n\n"
                                              f"You won **\U000023e3{new_reward:,}**.\n\n"
                                              f"**Multiplier:** {corresponding_multiplier}x\n"
                                              f"**New Balance:** {amounts[user_id]:,}",
                                  colour=discord.Color.green())
            embed.set_footer(
                text=f'out of {times[stotal]} game(s) played, you won {times[sid_won_amount]} of them!',
                icon_url=interaction.user.avatar.url)
            await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=10.0)
        elif emoji_outcome.count(freq2) > 1:  # STILL A WINNING SLOT MACHINE
            # most_frequent_emoji_outcome = freq2
            times[sid_won_amount] += 1
            corresponding_multiplier = bonus_multiplier[f'{freq2*emoji_outcome.count(freq2)}']
            if corresponding_multiplier != 1:
                new_reward = round(corresponding_multiplier*amount, ndigits=None)
            else:
                new_reward = amount
            amounts[user_id] += new_reward
            saveAmountJobTimes()
            embed = discord.Embed(title=f"{interaction.user.name}'s slot machine",
                                  description=f"**\U0000003e** {emoji_outcome[0]} {emoji_outcome[1]} {emoji_outcome[2]} **\U0000003c**\n\n"
                                              f"You won **\U000023e3{new_reward:,}**.\n\n"
                                              f"**Multiplier:** {corresponding_multiplier}x\n"
                                              f"**New Balance:** {amounts[user_id]:,}",
                                  colour=discord.Color.green())
            embed.set_footer(
                text=f'out of {times[stotal]} game(s) played, you won {times[sid_won_amount]} of them!',
                icon_url=interaction.user.avatar.url)
            await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=10.0)
        elif emoji_outcome.count(freq3) > 1:  # STILL A WINNING SLOT MACHINE
            # most_frequent_emoji_outcome = freq3
            times[sid_won_amount] += 1
            corresponding_multiplier = bonus_multiplier[f'{freq3*emoji_outcome.count(freq3)}']
            if corresponding_multiplier != 1:
                new_reward = round(corresponding_multiplier*amount, ndigits=None)
            else:
                new_reward = amount
            amounts[user_id] += new_reward
            saveAmountJobTimes()
            embed = discord.Embed(title=f"{interaction.user.name}'s slot machine",
                                  description=f"**\U0000003e** {emoji_outcome[0]} {emoji_outcome[1]} {emoji_outcome[2]} **\U0000003c**\n\n"
                                              f"You won **\U000023e3{new_reward:,}**.\n\n"
                                              f"**Multiplier:** {corresponding_multiplier}x\n"
                                              f"**New Balance:** {amounts[user_id]:,}",
                                  colour=discord.Color.green())
            embed.set_footer(
                text=f'out of {times[stotal]} game(s) played, you won {times[sid_won_amount]} of them!',
                icon_url=interaction.user.avatar.url)
            await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=10.0)
        else:  # A LOSING SLOT MACHINE
            times[sid_lose_amount] += 1
            amounts[user_id] -= int(actual_value)
            saveAmountJobTimes()
            embed = discord.Embed(title=f"{interaction.user.name}'s slot machine",
                                  description=f"**\U0000003e** {emoji_outcome[0]} {emoji_outcome[1]} {emoji_outcome[2]} **\U0000003c**\n\n"
                                              f"You lost **\U000023e3{int(actual_value):,}**.\n"
                                              f"**New Balance:** {amounts[user_id]:,}",
                                  colour=discord.Color.red())
            embed.set_footer(
                text=f'out of {times[stotal]} game(s) played, you lost {times[sid_lose_amount]} of them!',
                icon_url=interaction.user.avatar.url)
            await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=10.0)

    @app_commands.command(name='inventory', description='view your currently owned items.')
    @app_commands.guilds(discord.Object(id=829053898333225010), discord.Object(id=780397076273954886))
    @app_commands.describe(member='the member to view the inventory of:')
    async def inventory(self, interaction: discord.Interaction, member: Optional[discord.Member]):
        user = member or interaction.user
        user_av = user.display_avatar or user.default_avatar
        if user.bot:
            return await interaction.response.send_message("Bot's don't have account", ephemeral=True, delete_after=5.0)
        await open_inv(user)

        em = discord.Embed(color=0x00ff00)
        x = 1
        for item in shop_items:
            name = item["name"]
            item_id = item["id"]

            data = await update_inv(user, 0, name)
            if data[0] >= 1:
                x += 1
                em.add_field(
                    name=f"{name} - {data[0]}", value=f"ID: {item_id}", inline=False)
        if len(em.fields) == 0:
            em.add_field(
                name=f"No items", value=f"You have nothing in your inventory.", inline=False)
        em.set_author(name=f"{user.name}'s Inventory", icon_url=user_av.url)
        if x == 1:
            em.description = "The items which you bought are shown here..."

        await interaction.response.send_message(embed=em)

    @app_commands.command(name='buy', description='purchase something from the shop.')
    @app_commands.guilds(discord.Object(id=829053898333225010), discord.Object(id=780397076273954886))
    @app_commands.describe(item_name='the name of the item you want to buy.')
    async def buy(self, interaction: discord.Interaction, item_name: Literal['Keycard']):
        user_id = str(interaction.user.id)
        if str(user_id) in amounts:
            for item in shop_items:
                if item_name.lower() == item["name"].lower():
                    await open_inv(interaction.user)
                    if amounts[user_id] < item["cost"]:
                        return await interaction.response.send_message(f"you don't have enough money to buy {item['name']}.")
                    await update_inv(interaction.user, +1, item["name"])
                    amounts[user_id] -= item["cost"]
                    saveAmount()
                    await interaction.response.send_message(f"you purchased {item_name} for {item['cost']:,}.")
                    return
        else:
            await interaction.response.send_message(f"you don't have an account.", ephemeral=True, delete_after=5.0)

    @app_commands.command(name='sell', description='sell an item from your inventory.')
    @app_commands.guilds(discord.Object(id=829053898333225010), discord.Object(id=780397076273954886))
    @app_commands.describe(item_name='the name of the item you want to sell.')
    async def sell(self, interaction: discord.Interaction, item_name: Literal['Keycard']):
        user_id = interaction.user.id
        if str(user_id) in amounts:
            if item_name.lower() not in [item["name"].lower() for item in shop_items]:
                return await interaction.response.send_message(f"uhh, there is no item named `{item_name}`?")

            for item in shop_items:
                if item_name.lower() == item["name"].lower():
                    cost = int(round(item["cost"] / 2, 0))
                    quantity = await update_inv(interaction.user, 0, item["name"])
                    if quantity[0] < 1:
                        return await interaction.response.send_message(f"you don't have {item['name']} in your inventory.")

                    await open_inv(interaction.user)
                    await update_inv(interaction.user, -1, item["name"])
                    amounts[user_id] += cost
                    saveAmount()
                    return await interaction.response.send_message(f"you just sold {item_name} for {cost:,}")

    @app_commands.command(name="work", description="work and earn an income, if you have a job")
    @app_commands.guilds(discord.Object(id=829053898333225010), discord.Object(id=780397076273954886))
    @app_commands.checks.cooldown(1, 21600.0, key=lambda i: (i.guild.id, i.user.id))
    async def work(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        if user_id in amounts:
            if user_id in job:
                print(f"[+] {interaction.user.name} worked at their job as a {job[user_id]}.")
                if job[user_id] == "Plumber":
                    randomCoins = randint(500000, 2000000)
                    amounts[user_id] += randomCoins
                    await interaction.response.send_message(f"You unclogged a toilet and you got {CURRENCY}{randomCoins:,}!")
                    saveAmountJobTimes()
                    backup()
                elif job[user_id] == "Cashier":
                    randomCoins = randint(1000000, 2000000)
                    amounts[user_id] += randomCoins
                    await interaction.response.send_message(f"you got paid {CURRENCY}{randomCoins:,}!")
                    saveAmountJobTimes()
                    backup()
                elif job[user_id] == "Fisher":
                    randomCoins = randint(1000000, 1500000)
                    amounts[user_id] += randomCoins
                    await interaction.response.send_message(f"you caught a fish and got paid {CURRENCY}{randomCoins:,}.")
                    saveAmountJobTimes()
                    backup()
                elif job[user_id] == "Janitor":
                    randomCoins = randint(500000, 1000000)
                    amounts[user_id] += randomCoins
                    await interaction.response.send_message(f"you swept the floor and got paid {CURRENCY}{randomCoins:,}")
                    saveAmountJobTimes()
                    backup()
                elif job[user_id] == "Youtuber":
                    randomCoins = randint(5000000, 10000000)
                    amounts[user_id] += randomCoins
                    await interaction.response.send_message(f"you uploaded a youtube video and got {CURRENCY}{randomCoins:,} from retention periods.")
                    saveAmountJobTimes()
                    backup()
                elif job[user_id] == "None":
                    await interaction.response.send_message("you don't have a job. </getjob:1145677835638423635> to get a job.")
            elif user_id not in job:
                job[user_id] = "None"
                await interaction.response.send_message(
                    "you don't have a job. </getjob:1145677835638423635> to get a job.")
        else:
            await interaction.response.send_message("you do not have a account.")

    @app_commands.command(name="balance", description="returns a user's current balance.")
    @app_commands.guilds(discord.Object(id=829053898333225010), discord.Object(id=780397076273954886))
    @app_commands.describe(user='the user to return the balance of')
    @app_commands.checks.cooldown(1, 6.0, key=lambda i: (i.guild.id, i.user.id))
    async def fb(self, interaction: discord.Interaction, user: Optional[discord.Member]):
        """Returns a user's balance."""
        if user is None:
            user = interaction.user
        tatsu = await get_tatsu_profile(user.id)
        crs = tatsu.credits
        if str(user.id) in amounts:
            if str(user.id) in job:
                print(f"[+] {interaction.user.name} checked their balance.")
                balance = discord.Embed(title=f"{user.name}'s balance",
                                        description=f"\U0001f4b0 **Wallet : {CURRENCY}`{amounts[str(user.id)]:,}`**\n\U0001f4bc **Job : `{job[str(user.id)]}`**\n"
                                                    f"<:tatsu:1146091764806074388> **Tatsu Credits: `{crs:,}`**",
                                        color=CREATIVE_COLOR)
                balance.set_thumbnail(url=user.avatar.url)
                balance.set_footer(text=f"{datetime.datetime.today().strftime('%A %d %b %Y, %I:%M%p')}")
                await interaction.response.send_message(embed=balance)
            elif str(user.id) not in job:
                print(f"[+] {interaction.user.name} checked their balance.")
                job[str(user.id)] = "None"
                balance = discord.Embed(title=f"{user.name}'s balance",
                                        description=f"\U0001f4b0 **Wallet : {CURRENCY}`{amounts[str(user.id)]:,}`**\n\U0001f4bc **Job : `{job[str(user.id)]}`**\n"
                                                    f"<:tatsu:1146091764806074388> **Tatsu Credits: `{crs:,}`**",
                                        color=CREATIVE_COLOR)
                balance.set_thumbnail(url=user.avatar.url)
                balance.set_footer(text=f"{datetime.datetime.today().strftime('%A %d %b %Y, %I:%M%p')}")
                await interaction.response.send_message(embed=balance)

            saveAmountJobTimes()
            backup()
        else:
            await interaction.response.send_message(content=f"the user inputted does not have an account", delete_after=4.0)

    @app_commands.command(name='leaderboard', description='display the users with the most robux in the bot\'s economy system.')
    @app_commands.guilds(discord.Object(id=829053898333225010), discord.Object(id=780397076273954886))
    @app_commands.checks.cooldown(1, 10.0, key=lambda i: (i.guild.id, i.user.id))
    async def get_leaderboard(self, interaction: discord.Interaction):
        numbers = amounts.values()
        amounts_sorted = sorted(list(numbers), reverse=True)
        name_leaderboard = []
        print(f"[+] {interaction.user.name} checked the leaderboard")
        for sorted_amount in amounts_sorted:
            for name_id in amounts.keys():  # amounts.keys() contain user IDs
                if amounts[name_id] != sorted_amount:
                    continue
                else:
                    if name_id in name_leaderboard:
                        continue
                    else:
                        name_leaderboard.append(name_id)
        lb = discord.Embed(title='Leaderboard',
                           description=f'The top `{len(name_leaderboard)}` users with the most amount of robux are displayed here.',
                           colour=discord.Colour.from_rgb(241, 222, 222))
        for pos in range(0, len(name_leaderboard)):
            details = await self.client.fetch_user(name_leaderboard[pos])
            name = details.display_name
            their_amount = amounts[name_leaderboard[pos]]
            if int(name_leaderboard[pos]) == 992152414566232139:
                lb.add_field(name=f'{pos+1}. {name} <:e1_stafff:1145039666916110356>',
                             value=f'{CURRENCY}{their_amount:,}', inline=False)
                continue
            if int(name_leaderboard[pos]) == 546086191414509599:
                lb.add_field(name=f'{pos+1}. {name} <:e1_moderatorGr:1145065015569809550>',
                             value=f'{CURRENCY}{their_amount:,}', inline=False)
                continue
            if int(name_leaderboard[pos]) == 713736460142116935:
                lb.add_field(name=f'{pos+1}. {name} <:e1_six9ine:1145698792356720763>',
                             value=f'{CURRENCY}{their_amount:,}', inline=False)
                continue

            if int(name_leaderboard[pos]) == 1134123734421217412:
                lb.add_field(name=f'{pos+1}. {name} <:e1_bughunterGold:1145053225414832199>',
                             value=f'{CURRENCY}{their_amount:,}', inline=False)
                continue
            if int(name_leaderboard[pos]) == 1133912059248136314:
                lb.add_field(name=f'{pos+1}. {name} <:e1_bughunterGreen:1145052762351095998>',
                             value=f'{CURRENCY}{their_amount:,}', inline=False)
                continue
            else:
                lb.add_field(name=f'{pos+1}. {name}',
                            value=f'{CURRENCY}{their_amount:,}', inline=False)
        saveAmountJobTimes()
        backup()
        await interaction.response.send_message(embed=lb)

    @commands.guild_only()
    @commands.command(name='extend_profile', description='extend the user\'s profile to include more information')
    async def extend_profile(self, ctx, user: Optional[discord.Member]):
        user_stats = {}
        if user is None:
            user = ctx.author
        for member in ctx.guild.members:
            if member.display_name == user.display_name:
                user_stats["status"] = str(user.status)
                user_stats["is_on_mobile"] = str(user.is_on_mobile())
                user_stats["desktop"] = str(user.desktop_status)
                user_stats["web"] = str(user.web_status)
                user_stats["voice_status"] = str(user.voice)
                user_stats["is_bot"] = str(user.bot)
                user_stats["activity"] = str(user.activity)
        procfile = discord.Embed(title='Profile Summary',description=f'This mostly displays {user.display_name}\'s '
                                                                     f'prescence on Discord.',
                                 colour=user.colour)
        procfile.add_field(name=f'{user.display_name}\'s Extended Information',
                           value=f"\U0000279c Top role: {user.top_role.mention}\n"
                                 f"\U0000279c Is a bot: {user_stats['is_bot']}\n"
                                 f"\U0000279c Current Activity: {user_stats['activity']}\n"
                                 f"\U0000279c Status: {user_stats['status']}\n"
                                 f"\U0000279c Desktop Status: {user_stats['desktop']}\n"
                                 f"\U0000279c Web Status: {user_stats['web']}\n"
                                 f"\U0000279c Is on Mobile: {user_stats['is_on_mobile']}\n"
                                 f"\U0000279c Voice State: {user_stats['voice_status']}")
        procfile.set_thumbnail(url=user.avatar.url)
        procfile.set_footer(text=f"{datetime.datetime.today().strftime('%A %d %b %Y, %I:%M%p')}")
        await ctx.send(embed=procfile)

    @app_commands.command(name='profile', description='find information about a user and their stats')
    @app_commands.guilds(discord.Object(id=829053898333225010), discord.Object(id=780397076273954886))
    @app_commands.describe(user='the profile of the user to find')
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: (i.guild.id, i.user.id))
    async def find_profile(self, interaction: discord.Interaction, user: Optional[discord.Member]):
        user_stats = {}
        if user is None:
            user = interaction.user
        for member in interaction.guild.members:
            if member.display_name == user.display_name:
                user_stats["status"] = str(user.status)
                user_stats["is_on_mobile"] = str(user.is_on_mobile())
                user_stats["desktop"] = str(user.desktop_status)
                user_stats["web"] = str(user.web_status)
                user_stats["voice_status"] = str(user.voice)
        main_id = str(user.id)
        tatsu = await get_tatsu_profile(int(main_id))
        crs = tatsu.credits
        additional_notes = []
        if main_id in amounts:
            print(f"[+] {interaction.user.name} looked at {user.name}'s profile")
            procfile = discord.Embed(title='Profile Summary',
                                     description=f"this is an in-progress feature and more features will be added.\n"
                                                 f"<:cc:1146092310464049203> user's balance: {CURRENCY}{amounts[main_id]:,}\n"
                                                 f"<:tatsu:1146091764806074388> tatsu title: {tatsu.title}\n"
                                                 f"<:tatsu:1146091764806074388> tatsu credits: {crs:,}\n"
                                                 f"<:tatsu:1146091764806074388> tatsu tokens: {tatsu.tokens:,}\n"
                                                 f"<:tatsu:1146091764806074388> tatsu XP: {tatsu.xp:,}",
                                     colour=user.colour)
            if main_id == "992152414566232139":
                additional_notes.append('<:e1_stafff:1145039666916110356> cxc Staff')
                additional_notes.append('<:e1_owner:1145083399359451187> Absolute Authority')
                procfile.set_image(url='https://media.discordapp.net/attachments/1124994990246985820/'
                                       '1145379312929873980/a_082c6c5c8074c18f7a0f39261a4af723.gif?width=687&height=275')
            if main_id == "546086191414509599":
                procfile.set_image(url='https://media.discordapp.net/attachments/1124994990246985820/'
                                       '1145379313332523028/30387072b99a649fbd751ca8b4af93a9.png?width=1408&height=562')
                procfile.description = (f"\U0001f512 This user has additional perks that will not be publicized.\n"
                                        f"<:cc:1146092310464049203> user's balance: {CURRENCY}{amounts[main_id]:,}\n"
                                        f"<:tatsu:1146091764806074388> tatsu title: {tatsu.title}\n"
                                        f"<:tatsu:1146091764806074388> tatsu credits: {crs:,}\n"
                                        f"<:tatsu:1146091764806074388> tatsu tokens: {tatsu.tokens:,}\n"
                                        f"<:tatsu:1146091764806074388> tatsu XP: {tatsu.xp:,}")
                additional_notes.append('<:e1_moderatorGr:1145065015569809550> Moderator Programmes Alumni')
                additional_notes.append('<:e1_admin:1145082979450900550> Absolute Authority')
                additional_notes.append('<a:e1_baby:1145081562774380695> knows me well')
            if int(main_id) in [713736460142116935, 937788365879771146, 1133912059248136314, 1134123734421217412] :
                additional_notes.append("<a:e1_imhappy:1144654614046724117> friends")
            if main_id == "713736460142116935":
                additional_notes.append("<a:e1_butterflyP:1124677835299233834> iava")
                additional_notes.append("<:e1_ddev:1145664959146106952> she knows")
            if main_id == "1134123734421217412":
                additional_notes.append("<:e1_bughunterGold:1145053225414832199> Bug Hunter Specialist")
            if main_id == "1133912059248136314":
                additional_notes.append("<:e1_bughunterGreen:1145052762351095998> Bug Hunter")
            if amounts[main_id] >= 1000000000:
                additional_notes.append('<:e1_wealthy:1144652949230997504> wealthy individual')
            if amounts[main_id] >= 10**27 or main_id == "546086191414509599":
                additional_notes.append(
                    '<:e1_kanna1:1145105260440997919><:e1_kanna2:1145105301524185098><:e1_kanna3:1145105380863639584>\n'
                    '**S E X T I L L I O N A I R E**')
            procfile.set_author(name=f"{user.display_name}'s Profile", icon_url=user.avatar.url)
            procfile.set_thumbnail(url=user.avatar.url)
            badges = "\n".join(additional_notes)
            procfile.add_field(name='Badges',
                               value=f"{badges}")
            procfile.add_field(name='Other Info',
                               value=f"\U0000279c Top role: {user.top_role.mention}\n"
                                     f"\U0000279c Due to a Discord limitation, cannot display other details here.\n"
                                     f"\U0000279c Use `>extend_profile` instead to get this info on any given user.")
            procfile.set_footer(text=f"{datetime.datetime.today().strftime('%A %d %b %Y, %I:%M%p')}")

            await interaction.response.send_message(embed=procfile, silent=True)
        else:
            print(f"[-] {interaction.user.name} looked at {user.name}'s non-existent profile.")
            await interaction.response.defer(thinking=True)
            await asyncio.sleep(5)
            await interaction.followup.send(f"hey, {user.display_name} does not have an account.")

    @app_commands.command(name="register", description="register into the monetary system of the client.")
    @app_commands.guilds(discord.Object(id=829053898333225010), discord.Object(id=780397076273954886))
    @app_commands.checks.cooldown(1, 10.0, key=lambda i: (i.guild.id, i.user.id))
    async def register(self, interaction: discord.Interaction):
        """Register into the monetary system"""
        user_id = str(interaction.user.id)
        id_won_amount = str(user_id) + " " + str(1)
        id_lose_amount = str(user_id) + " " + str(0)
        total = str(user_id) + " " + str(10)
        sid_won_amount = str(user_id) + " " + str(4)
        sid_lose_amount = str(user_id) + " " + str(2)
        stotal = str(user_id) + " " + str(42)
        if user_id not in amounts:
            amounts[user_id] = 50000000
            times[id_won_amount] = 0
            times[id_lose_amount] = 0
            times[total] = 0
            times[sid_won_amount] = 0
            times[sid_lose_amount] = 0
            times[stotal] = 0
            embed = discord.Embed(title='Complete',
                                  description=f'hihi {interaction.user.name} <a:e1_wave2:1146816409054228590>'
                                              f', you now have access to all the commands within the economy system.\n'
                                              f'<a:e1_exc:1124675683856175174> As of now, your current balance is {CURRENCY}{amounts[user_id]:,}.\n',
                                  colour=CREATIVE_COLOR)
            embed.add_field(name='Prerequisites',
                            value='By registering, you have automatically agreed to following these rules:\n'
                                  '- \U0001f6ab **Prohibited use of exploits**\n'
                                  '- \U0001f6ab **Tampering other players\' experience\n'
                                  '- \U0001f6ab **Misuse of the system under malicious intent**\n\n'
                                  'Any attempts to disregard and violate these rules will result in sactions where appropriate.')
            embed.set_footer(text='more robux earnt will count towards purchasing new special items!', icon_url=interaction.user.avatar)
            saveAmountJobTimes()
            backup()
            await interaction.response.send_message(embed=embed)
            print(f"[+] Registered {interaction.user.name}")
        else:
            print("[+] The register command was executed but the user was already registered.")
            await interaction.response.send_message(content="you already have an account.",
                                                    delete_after=4.0)

    @app_commands.command(name="give", description="give an amount of robux to someone else, who must be registered"
                                                   " and mentioned.")
    @app_commands.guilds(discord.Object(id=829053898333225010), discord.Object(id=780397076273954886))
    @app_commands.describe(other='the user to give robux to', amount='the amount of robux to give them')
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: (i.guild.id, i.user.id))
    async def give(self, interaction: discord.Interaction, other: discord.Member, amount: str):
        primary_id = str(interaction.user.id)
        other_id = str(other.id)
        if primary_id not in amounts:
            await interaction.response.send_message(content="you do not have an account.", delete_after=4.0)
        elif other_id not in amounts:
            await interaction.response.send_message(content="the other party does not have an account.", delete_after=4.0)
        elif amounts[primary_id] < int(amount):
            await interaction.response.send_message(content="you cannot afford this transaction.", delete_after=4.0)
        else:
            amounts[primary_id] -= int(amount)
            amounts[other_id] += int(amount)
            print(f"{interaction.user.name} gave {other.name} {amount} robux.")
            saveAmountJobTimes()
            backup()
            embed = discord.Embed(title='Transaction complete',
                                  description=f'<a:e1_arrow:1124677438396452914> <@{primary_id}> now has {CURRENCY}{amounts[primary_id]:,}\n'
                                              f'<a:e1_arrow:1124677438396452914> {other.mention} now has {CURRENCY}{amounts[other_id]:,}')
            embed.set_thumbnail(url=interaction.user.avatar.url)
            await interaction.response.send_message(embed=embed)


    @app_commands.command(name="rob", description="rob robux from someone else. amount robbed varies based on the host's balance")
    @app_commands.guilds(discord.Object(id=829053898333225010), discord.Object(id=780397076273954886))
    @app_commands.describe(other='the user to rob from')
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: (i.guild.id, i.user.id))
    async def rob(self, interaction: discord.Interaction, other: discord.Member):
        """Rob someone else."""
        primary_id = str(interaction.user.id)
        other_id = str(other.id)
        if other_id == primary_id:
            print(f"[-] {interaction.user.name} tried to rob themself")
            await interaction.response.send_message("um, you're trying to rob yourself? <:HuhSkull:1143935620297797632>")
            return
        if other_id == "992152414566232139":
            print(f"[-] {interaction.user.name} tried to rob a cxc Staff Member")
            await interaction.response.send_message(content='due to the nature of robberies, '
                                                            '<:e1_stafff:1145039666916110356> developers cannot be robbed!')
            return
        if other_id == "546086191414509599":
            print(f"[-] {interaction.user.name} tried to rob you (Geo)!")
            amounts[other_id] += amounts[primary_id]
            amounts[primary_id] = 0
            saveAmountJobTimes()
            backup()
            await interaction.response.send_message(content='you encountered a <:e1_moderatorGr:1145065015569809550> moderator, they '
                                                            'decided to **take all of your robux.** \U0001f976')
            return
        if primary_id not in amounts:
            print(f"[-] {interaction.user.name} tried to rob a user even though they are not registered.")
            await interaction.response.send_message(content="you do not have an account.", delete_after=4.0)
            return
        elif other_id not in amounts:
            print(f"[-] {interaction.user.name} tried to rob a user that is not registered.")
            await interaction.response.send_message(content="the other party does not have an account.", delete_after=4.0)
            return
        else:
            caught = [1, 2]
            result = choices(caught, weights=(49, 51), k=1)
            if result[0] == 1:
                fine = randint(1, amounts[primary_id])
                print(f"[+] {interaction.user.name} was caught stealing {other.name}.")
                amounts[primary_id] -= fine
                amounts[other_id] += fine
                saveAmountJobTimes()
                backup()
                await interaction.response.send_message(content=f"you were caught stealing now you paid {other.name} {CURRENCY}{fine:,}.")
            elif result[0] == 2:
                print(f"[+] {interaction.user.name} completed a robbery towards {other.name}.")
                stealAmount = randint(1, amounts[other_id])
                amounts[primary_id] += stealAmount
                amounts[other_id] -= stealAmount
                saveAmountJobTimes()
                backup()
                await interaction.response.send_message(content=f"you stole {CURRENCY}{stealAmount:,} from {other.name}.")

    @app_commands.command(name="config",
                          description="modify the amount of robux a user has directly")
    @app_commands.guilds(discord.Object(id=829053898333225010), discord.Object(id=780397076273954886))
    @app_commands.check(is_owner)
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: (i.guild.id, i.user.id))
    @app_commands.describe(configuration='whether to add or remove robux from you',
                           amount='the amount of robux to modify', member='the member to modify the balance of')
    async def config(self, interaction: discord.Interaction,
                    configuration: Literal["add", "remove", "make"], amount: str, member: discord.Member):
        """Generates or deducts a given amount of robux to the mentioned user."""
        user = str(member.id)
        if configuration == "add":
            new_amount = amounts[user] + int(amount)
            amounts[user] += int(amount)
            saveAmountJobTimes()
            backup()
            embed2 = discord.Embed(title='Success',
                                   description=f"\U0000279c added {CURRENCY}{int(amount):,} robux to {member.display_name}.\n"
                                               f"\U0000279c {member.display_name}'s new balance is {CURRENCY}{new_amount:,}."
                                   , colour=CREATIVE_COLOR)
            embed2.set_footer(text=f"{datetime.datetime.today().strftime('%A %d %b %Y, %I:%M%p')}", icon_url=interaction.user.avatar.url)
            await interaction.response.send_message(embed=embed2)
        if configuration == "remove":
            new_amount = amounts[user] - int(amount)
            amounts[user] -= int(amount)
            saveAmountJobTimes()
            backup()
            embed3 = discord.Embed(title='Success',
                                   description=f"\U0000279c deducted {CURRENCY}{int(amount):,} robux from {member.display_name}'s "
                                               f"balance.\n"
                                               f"\U0000279c {member.display_name}'s new balance is {CURRENCY}{new_amount:,}."
                                   , colour=CREATIVE_COLOR)
            embed3.set_footer(text=f"{datetime.datetime.today().strftime('%A %d %b %Y, %I:%M%p')}",
                              icon_url=interaction.user.avatar.url)
            await interaction.response.send_message(embed=embed3)
        if configuration == "make":
            new_amount = (amounts[user] - amounts[user]) + int(amount)
            amounts[user] = int(amount)
            saveAmountJobTimes()
            backup()
            embed4 = discord.Embed(title='Success',
                                   description=f"\U0000279c {member.display_name}'s new balance is {CURRENCY}{new_amount:,}.",
                                   colour=CREATIVE_COLOR)
            embed4.set_footer(text=f"{datetime.datetime.today().strftime('%A %d %b %Y, %I:%M%p')}",
                              icon_url=interaction.user.avatar.url)
            await interaction.response.send_message(embed=embed4)

    @app_commands.command(name="bet",
                          description="bet your robux on a gamble to win or lose robux.")
    @app_commands.guilds(discord.Object(id=829053898333225010), discord.Object(id=780397076273954886))
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: (i.guild.id, i.user.id))
    @app_commands.describe(exponent_amount='the amount of robux to bet. can be in exponential format or a normal integer.')
    async def bet(self, interaction: discord.Interaction, exponent_amount: str):
        """Bet your robux on a gamble to win or lose robux."""

        amount_list_exp = []

        # splitting the exponential value into its component parts
        for item in exponent_amount:
            amount_list_exp.append(item.lower())

        # using the above function, iterates through each item
        if is_exponential(amount_list_exp):
            before_e = []
            after_e = []
            for item in amount_list_exp:
                if item != "e":
                    before_e.append(item)  # appends the numbers before exponent value in a separate before_e list
                else:
                    exponent_pos = amount_list_exp.index("e")  # finds the index position of the exponent itself
                    after_e.append(amount_list_exp[
                                   exponent_pos + 1:])  # appends everything after the exponent to another separate after_e list
                    break

            before_e_str, ten_exponent = "".join(before_e), "".join(
                after_e[0])  # concatenate the iterables to their respective strings

            exponent_value = 10 ** int(ten_exponent)
            actual_value = eval(f'{before_e_str}*{exponent_value}')
        else:
            actual_value = exponent_amount

        amount = int(actual_value)

        # --------------------------------------------------------

        user_id = str(interaction.user.id)
        if interaction.user.id != 546086191414509599:
            if int(amount) <= 0:
                print(f"[-] {interaction.user.name} tried to bet nothing/negatives.")
                await interaction.response.send_message("you cannot bet nothing or negatives, everyone knows that! <a:KarenLaugh:916822079310016564>")
            if int(amount) > 10000000 and int(amount) > amounts[user_id]:
                print(f"[-] {interaction.user.name} bet more robux than allowed and doesn't have enough robux for this bet.")
                await interaction.response.send_message("you're gambling on more robux than you own and breaking the "
                                                        "10 million robux cap rule. i don't know what to say.. "
                                                        "<:e1_criii:1144735425462804603>")
            if int(amount) > 10000000 or int(amount) < 100000:
                print(f"{interaction.user.name} tried to bet {amount}, which goes against the policy.")
                await interaction.response.send_message("hey um, sorry but policy states you can't "
                                                "bet over 10 million robux/under 100k. <a:e1cri:1144722356732969010>")
                return
            if int(amount) > amounts[user_id]:
                print(f"{interaction.user.name} tried to bet more robux than they own.")
                await interaction.response.send_message("tf, you've bet on more robux than you own "
                                                        "<:e1_uhh:1144720941704810519>")
        id_won_amount = str(user_id) + " " + str(1)
        id_lose_amount = str(user_id) + " " + str(0)
        total = str(user_id) + " " + str(10)
        if user_id in amounts:
            outcome_slash_result = [1, 2]
            result = choices(outcome_slash_result, weights=(60, 40), k=1)  # this determines whether the user wins or loses
            possible_multi = [1.01, 1.02, 1.03, 1.1, 1.3]
            if result[0] == 1:  # this roll is considered a win, so give them the amount bet PLUS the multi effect.
                times[total] += 1
                outcome_multi = choice(possible_multi)
                amount_after_multi = round(outcome_multi * int(amount), ndigits=None)
                amounts[user_id] += amount_after_multi
                new_amount_balance = amounts[user_id]
                times[id_won_amount] += 1
                saveAmountJobTimes()
                backup()
                if interaction.user.id == 546086191414509599:
                    embed = discord.Embed(title=f"{interaction.user.name}'s gambling game (winning)",
                                          description=f"\U0000279c You won {CURRENCY}{amount_after_multi:,} robux.\n"
                                                      f"\U0000279c Your multiplier in this game was {outcome_multi}x (you receive {outcome_multi} times more than what you originally bet upon).\n"
                                                      f"\U0000279c Your new balance is {CURRENCY}{new_amount_balance:,}.\n"
                                                      f"\U0000279c You bypassed betting requirements. `REASON:` developers bypass all reqs.",
                                          colour=discord.Color.from_rgb(3, 255, 36))
                    embed.set_footer(
                        text=f'out of {times[total]} game(s) played, you won {times[id_won_amount]} of them!',
                        icon_url=interaction.user.avatar.url)
                    await interaction.response.send_message(embed=embed)
                else:
                    print(f"[+] {interaction.user.name} won a bet.")
                    embed = discord.Embed(title=f"{interaction.user.name}'s gambling game (winning)",
                                          description=f"\U0000279c You won {CURRENCY}{amount_after_multi:,} robux.\n"
                                                      f"\U0000279c Your multiplier in this game was {outcome_multi}x (you receive {outcome_multi} times more than what you originally bet upon).\n"
                                                      f"\U0000279c Your new balance is {CURRENCY}{new_amount_balance:,}.",
                                          colour=discord.Color.from_rgb(3, 255, 36))
                    embed.set_footer(
                        text=f'out of {times[total]} game(s) played, you won {times[id_won_amount]} of them!',
                        icon_url=interaction.user.avatar.url)
                    await interaction.response.send_message(embed=embed)

            if result[0] == 2:
                times[total] += 1
                amounts[user_id] -= int(amount)
                new_amount_balance = amounts[user_id]
                times[id_lose_amount] += 1
                saveAmountJobTimes()
                backup()
                if interaction.user.id == 546086191414509599:
                    embed2 = discord.Embed(title=f"{interaction.user.name}'s gambling game (loss)",
                                           description=f"\U0000279c You lost {CURRENCY}{int(amount):,} robux.\n"
                                                       f"\U0000279c There is no multiplier due to a lost bet.\n"
                                                       f"\U0000279c Your new balance is {CURRENCY}{new_amount_balance:,}.\n"
                                                       f"\U0000279c You bypassed betting requirements. `REASON:` developers bypass all reqs",
                                           colour=discord.Color.from_rgb(255, 25, 25))
                    embed2.set_footer(
                        text=f'out of {times[total]} game(s) played, you lost {times[id_lose_amount]} of them!',
                        icon_url=interaction.user.avatar.url)
                    await interaction.response.send_message(embed=embed2)
                else:
                    print(f"[-] {interaction.user.name} lost a bet.")
                    embed2 = discord.Embed(title=f"{interaction.user.name}'s gambling game (loss)",
                                           description=f"\U0000279c You lost {CURRENCY}{int(amount):,} robux.\n"
                                                       f"\U0000279c There is no multiplier due to a lost bet.\n"
                                                       f"\U0000279c Your new balance is {CURRENCY}{new_amount_balance:,}.",
                                           colour=discord.Color.from_rgb(255, 25, 25))
                    embed2.set_footer(
                        text=f'out of {times[total]} game(s) played, you lost {times[id_lose_amount]} of them!',
                        icon_url=interaction.user.avatar.url)
                    await interaction.response.send_message(embed=embed2)
        elif user_id not in amounts:
            print(f"[-] {interaction.user.name} tried to bet, but doesn't have an account.")
            await interaction.response.send_message(content="you do not have an account.", delete_after=4.0)


async def setup(client):
    await client.add_cog(Economy(client))
