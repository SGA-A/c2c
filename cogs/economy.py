import datetime

import discord
from discord.ext import commands
import random
from discord import app_commands
import json

CREATIVE_COLOR = discord.Color.random()

# C:\\Users\\Computer\\PycharmProjects\\pythonProject1\\cogs\\economy.json


with open('C:\\Users\\Computer\\PycharmProjects\\pythonProject3\\cogs\\economy.json') as file:
    amounts = json.load(file)

with open('C:\\Users\\Computer\\PycharmProjects\\pythonProject3\\cogs\\jobs.json') as file:
    job = json.load(file)

with open('C:\\Users\\Computer\\PycharmProjects\\pythonProject3\\cogs\\times.json') as file:
    times = json.load(file)


def saveData():
    with open('C:\\Users\\Computer\\PycharmProjects\\pythonProject3\\cogs\\economy.json', 'w') as file:
        json.dump(amounts, file, indent=4)

    with open('C:\\Users\\Computer\\PycharmProjects\\pythonProject3\\cogs\\jobs.json', 'w') as file:
        json.dump(job, file, indent=4)

    with open('C:\\Users\\Computer\\PycharmProjects\\pythonProject3\\cogs\\times.json', 'w') as file:
        json.dump(times, file, indent=4)


def is_owner(interaction: discord.Interaction):
    if interaction.user.id == interaction.guild.owner_id:
        return True
    return False


def backup():
    with open('C:\\Users\\Computer\\PycharmProjects\\pythonProject1\\cogs\\backup.json', 'w') as file:
        json.dump(amounts, file, indent=4)


class Economy(commands.Cog):
    def __init__(self, client):
        self.client = client

    @app_commands.command(name="balance", description='returns your current balance along with your current job.')
    @app_commands.guilds(discord.Object(id=829053898333225010), discord.Object(id=780397076273954886))
    async def balance(self, interaction: discord.Interaction):
        main_id = str(interaction.user.id)

        if main_id in amounts:
            if main_id in job:
                balance = discord.Embed(title=f"{interaction.user.name}'s balance",
                                        description=f"**Wallet : `{amounts[main_id]:,}`**\n**Job : `{job[main_id]}`**",
                                        color=CREATIVE_COLOR)
                balance.set_thumbnail(url=interaction.user.avatar.url)
                balance.set_footer(text=f"{datetime.datetime.today().strftime('%A %d %b %Y, %I:%M%p')}")
                await interaction.response.send_message(embed=balance)
            elif main_id not in job:
                job[main_id] = "None"
                balance = discord.Embed(title=f"{interaction.user.name}'s balance",
                                        description=f"**Wallet : `{amounts[main_id]:,}`**\n**Job : `{job[main_id]}`**",
                                        color=CREATIVE_COLOR)
                balance.set_thumbnail(url=interaction.user.avatar.url)
                balance.set_footer(text=f"{datetime.datetime.today().strftime('%A %d %b %Y, %I:%M%p')}")
                await interaction.response.send_message(embed=balance)

            saveData()
            backup()
        else:
            await interaction.response.send_message(content=f"you don't have an account.", ephemeral=True, delete_after=4.0)

    @app_commands.command(name="find_balance", description="returns a specific user's balance")
    @app_commands.guilds(discord.Object(id=829053898333225010), discord.Object(id=780397076273954886))
    @app_commands.describe(user='a mentioned username to find the balance of')
    async def fb(self, interaction: discord.Interaction, user: discord.Member):
        """Returns a specific user's balance."""
        if str(user.id) in amounts:
            if str(user.id) in job:
                balance = discord.Embed(title=f"{user.name}'s balance",
                                        description=f"**Wallet : `{amounts[str(user.id)]:,}`**\n**Job : `{job[str(user.id)]}`**",
                                        color=CREATIVE_COLOR)
                balance.set_thumbnail(url=user.avatar.url)
                balance.set_footer(text=f"{datetime.datetime.today().strftime('%A %d %b %Y, %I:%M%p')}")
                await interaction.response.send_message(embed=balance)
            elif str(user.id) not in job:
                job[str(user.id)] = "None"
                balance = discord.Embed(title=f"{user.name}'s balance",
                                        description=f"**Wallet : `{amounts[str(user.id)]:,}`**\n**Job : `{job[str(user.id)]}`**",
                                        color=CREATIVE_COLOR)
                balance.set_thumbnail(url=user.avatar.url)
                balance.set_footer(text=f"{datetime.datetime.today().strftime('%A %d %b %Y, %I:%M%p')}")
                await interaction.response.send_message(embed=balance)

            saveData()
            backup()
        else:
            await interaction.response.send_message(content=f"the user inputted does not have an account", ephemeral=True, delete_after=4.0)

    @app_commands.command(name="register", description="register into the monetary system of the client.")
    @app_commands.guilds(discord.Object(id=829053898333225010), discord.Object(id=780397076273954886))
    async def register(self, interaction: discord.Interaction):
        """Register into the monetary system"""
        id = str(interaction.user.id)
        id_won_amount = str(id) + " " + str(1)
        id_lose_amount = str(id) + " " + str(0)
        total = str(id) + " " + str(10)
        if id not in amounts:
            amounts[id] = 10000000
            times[id_won_amount] = 0
            times[id_lose_amount] = 0
            times[total] = 0
            embed = discord.Embed(title='Complete',
                                  description=f'hihi {interaction.user.name} <a:e1_wave:1124974582009434173> '
                                              f'your username has been added to our records and you may begin using monetary'
                                              f' commands now. See </help:1124814156659437650> to find out about it.\n'
                                              f'<a:e1_exc:1124675683856175174> As of now, your current balance is {amounts[id]:,}.\n'
                                              f'<a:e1_exc:1124675683856175174> you can request for more money by messaging <@546086191414509599>\n',
                                  colour=CREATIVE_COLOR)
            embed.set_footer(text='more money earnt will count towards purchasing new special items!', icon_url=interaction.user.avatar)
            await interaction.response.send_message(embed=embed)
            saveData()
            backup()
            print(f"[+] Registered {interaction.user.name} - {interaction.user.id}")
        else:
            print("[+] The register command was executed but the user was already registered.")
            await interaction.response.send_message(content="You already have an account.", ephemeral=True,
                                                    delete_after=4.0)

    @app_commands.command(name="give", description="give an amount of money to someone else, who must be registered"
                                                   " and mentioned.")
    @app_commands.guilds(discord.Object(id=829053898333225010), discord.Object(id=780397076273954886))
    @app_commands.describe(other='the user to give money to', amount='the amount of money to give them')
    async def give(self, interaction: discord.Interaction, other: discord.Member, amount: str):
        primary_id = str(interaction.user.id)
        other_id = str(other.id)
        if primary_id not in amounts:
            await interaction.response.send_message(content="you do not have an account.", ephemeral=True, delete_after=4.0)
        elif other_id not in amounts:
            await interaction.response.send_message(content="the other party does not have an account.", ephemeral=True, delete_after=4.0)
        elif amounts[primary_id] < int(amount):
            await interaction.response.send_message(content="you cannot afford this transaction.", ephemeral=True, delete_after=4.0)
        else:
            amounts[primary_id] -= int(amount)
            amounts[other_id] += int(amount)
            embed = discord.Embed(title='Transaction complete',
                                  description=f'<a:e1_arrow:1124677438396452914> <@{primary_id}> now has {amounts[primary_id]:,}\n'
                                              f'<a:e1_arrow:1124677438396452914> {other.mention} now has {amounts[other_id]:,}')
            embed.set_thumbnail(url=interaction.user.avatar.url)
            await interaction.response.send_message(embed=embed)
        saveData()
        backup()

    @app_commands.command(name="rob", description="rob money from someone else. amount robbed varies based on the host's balance")
    @app_commands.guilds(discord.Object(id=829053898333225010), discord.Object(id=780397076273954886))
    @app_commands.describe(other='the user to rob from')
    async def rob(self, interaction: discord.Interaction, other: discord.Member):
        """Rob someone else."""
        primary_id = str(interaction.user.id)
        other_id = str(other.id)
        if primary_id not in amounts:
            await interaction.response.send_message(content="you do not have an account.", ephemeral=True, delete_after=4.0)
        elif other_id not in amounts:
            await interaction.response.send_message(content="the other party does not have an account.", ephemeral=True, delete_after=4.0)
        else:
            stealAmount = random.randint(1, amounts[other_id])
            Caught = random.randint(1, 2)
            fine = random.randint(1, amounts[primary_id])
            if Caught == 1:
                print("[+] User was caught stealing.")
                amounts[primary_id] -= fine
                amounts[other_id] += fine
                await interaction.response.send_message(content=f"you were caught stealing now you paid {other.name} {fine:,} coins.")
            elif Caught == 2:
                amounts[primary_id] += stealAmount
                amounts[other_id] -= stealAmount
                await interaction.response.send_message(content=f"you stole {stealAmount:,} coins from {other.name}.")
        saveData()
        backup()

    @app_commands.command(name="generate",
                          description="generates money directly onto the author's balance")
    @app_commands.guilds(discord.Object(id=829053898333225010), discord.Object(id=780397076273954886))
    @app_commands.check(is_owner)
    @app_commands.describe(amount='the amount of money to generate')
    async def generate(self, interaction: discord.Interaction, amount: str):
        """Generates a given amount of money to the author."""
        user = str(interaction.user.id)
        new_amount = amounts[user] + int(amount)
        try:
            amounts[user] += int(amount)
            embed2 = discord.Embed(title='Success',
                                   description=f"-> added {int(amount):,} coins to {interaction.user.name}.\n"
                                               f"-> {interaction.user.name}'s balance is {new_amount:,}.", colour=CREATIVE_COLOR)
            embed2.set_footer(text=f"{datetime.datetime.today().strftime('%A %d %b %Y, %I:%M%p')}", icon_url=interaction.user.avatar.url)
            await interaction.response.send_message(embed=embed2)
        except json.JSONDecodeError as e:
            await interaction.response.send_message(content=f'something went wrong.')

    @app_commands.command(name="bet",
                          description="bet your money on a gamble to win or lose coins.")
    @app_commands.guilds(discord.Object(id=829053898333225010), discord.Object(id=780397076273954886))
    @app_commands.checks.cooldown(1, 7.0, key=lambda i: (i.guild_id, i.user.id))
    @app_commands.describe(amount='the amount of money to bet upon')
    async def bet(self, interaction: discord.Interaction, amount: str):
        """Bet your money on a gamble to win or lose coins."""
        id = str(interaction.user.id)
        id_won_amount = str(id) + " " + str(1)
        id_lose_amount = str(id) + " " + str(0)
        total = str(id) + " " + str(10)
        if id in amounts:
            result = random.randint(1, 2)
            possible_multi = [1.01, 1.02, 1.03, 1.1, 1.3, 1.5, 1.6, 1.8]
            times[total] += 1
            if result == 1:  # this roll is considered a win, so give them the amount betted PLUS the multi effect.
                outcome_multi = random.choice(possible_multi)
                amount_after_multi = round(outcome_multi * int(amount), ndigits=None)
                new_amount = amounts[id] + amount_after_multi
                amounts[id] = new_amount
                times[id_won_amount] += 1
                saveData()
                backup()
                embed = discord.Embed(title=f"{interaction.user.name}'s gambling game (winning)",
                                      description=f"-> You won {amount_after_multi:,} coins.\n"
                                                  f"-> Your multiplier in this game was {outcome_multi}x (you receive {outcome_multi} times more than what you originally bet upon).\n"
                                                  f"-> Your new balance is {new_amount:,}.",
                                      colour=discord.Color.from_rgb(3, 255, 36))
                embed.set_footer(
                    text=f'out of {times[total]} game(s) played, you won {times[id_won_amount]} of them!',
                    icon_url=interaction.user.avatar.url)
                await interaction.response.send_message(embed=embed)

            if result == 2:
                outcome_multi = random.choice(possible_multi)
                amount_after_multi = round(outcome_multi * amount, ndigits=None)
                new_amountr = amounts[id] - amount_after_multi
                amounts[id] = new_amountr
                times[id_lose_amount] += 1
                saveData()
                backup()
                embed2 = discord.Embed(title=f"{interaction.user.name}'s gambling game (loss)",
                                       description=f"-> You lost {amount_after_multi:,} coins.\n"
                                                   f"-> Your multiplier in this game was {outcome_multi}x (you lose {outcome_multi} times more than what you originally betted upon).\n"
                                                   f"-> Your new balance is {new_amountr:,}.",
                                       colour=discord.Color.from_rgb(255, 25, 25))
                embed2.set_footer(
                    text=f'out of {times[total]} game(s) played, you lost {times[id_lose_amount]} of them!',
                    icon_url=interaction.user.avatar.url)
                await interaction.response.send_message(embed=embed2)
        elif id not in amounts:
            await interaction.response.send_message(content="you do not have an account.", ephemeral=True, delete_after=4.0)

    @bet.error
    async def on_test_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(str(error), ephemeral=True)

    @bet.error
    async def on_test_error2(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CommandInvokeError):
            await interaction.response.send_message(str(error), ephemeral=True)

    @bet.error
    async def on_test_error3(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CheckFailure):
            await interaction.response.send_message(str(error), ephemeral=True)

    @bet.error
    async def on_test_error4(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CommandLimitReached):
            await interaction.response.send_message(str(error), ephemeral=True)

    @bet.error
    async def on_test_error5(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CommandSyncFailure):
            await interaction.response.send_message(str(error), ephemeral=True)

async def setup(client):
    await client.add_cog(Economy(client))
