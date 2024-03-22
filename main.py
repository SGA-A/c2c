from __future__ import annotations

from dotenv import load_dotenv
from datetime import datetime
from os import listdir, environ
from sys import version

from re import compile
from random import choice
from collections import deque
from typing import Literal, Any, Dict, Optional, TYPE_CHECKING, Union, List
from logging import INFO as LOGGING_INFO

from asyncio import run
from aiohttp import ClientSession
from asqlite import create_pool

from discord.utils import setup_logging, format_dt
from discord import app_commands, Object, ui, Intents, Status, Embed, Interaction, CustomActivity
from discord import AppCommandType, SelectOption, Colour, Webhook, NotFound
from discord.ext import commands


if TYPE_CHECKING:
    from discord.abc import Snowflake

    AppCommandStore = Dict[str, app_commands.AppCommand]  # name: AppCommand


# Search for a specific term in this project using Ctrl + Shift + F


class MyCommandTree(app_commands.CommandTree):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._global_app_commands: AppCommandStore = {}
        self._guild_app_commands: Dict[int, AppCommandStore] = {}

    def find_app_command_by_names(
            self,
            *qualified_name: str,
            guild: Optional[Union[Snowflake, int]] = None,
    ) -> Optional[app_commands.AppCommand] | Any:
        commandsr = self._global_app_commands
        if guild:
            guild_id = guild.id if not isinstance(guild, int) else guild
            guild_commands = self._guild_app_commands.get(guild_id, {})
            if not guild_commands and self.fallback_to_global:
                commandsr = self._global_app_commands
            else:
                commandsr = guild_commands

        for cmd_name, cmd in commandsr.items():
            if any(name in qualified_name for name in cmd_name.split()):
                return cmd

        return None

    def get_app_command(
            self, value: Union[str, int],
            guild: Optional[Union[Snowflake, int]] = None) -> Optional[app_commands.AppCommand]:
        def search_dict(d: AppCommandStore) -> Optional[app_commands.AppCommand]:
            for cmd_name, cmd in d.items():
                if value == cmd_name or (str(value).isdigit() and int(value) == cmd.id):
                    return cmd
            return None

        if guild:
            guild_id = guild.id if not isinstance(guild, int) else guild
            guild_commands = self._guild_app_commands.get(guild_id, {})
            if not self.fallback_to_global:
                return search_dict(guild_commands)
            else:
                return search_dict(guild_commands) or search_dict(self._global_app_commands)
        else:
            return search_dict(self._global_app_commands)

    @staticmethod
    def _unpack_app_commands(commandsr: List[app_commands.AppCommand]) -> AppCommandStore:
        ret: AppCommandStore = {}

        def unpack_options(
                options: List[Union[app_commands.AppCommand, app_commands.AppCommandGroup, app_commands.Argument]]):
            for option in options:
                if isinstance(option, app_commands.AppCommandGroup):
                    ret[option.qualified_name] = option
                    unpack_options(option.options)

        for command in commandsr:
            ret[command.name] = command
            unpack_options(command.options)

        return ret

    async def _update_cache(
            self, cmads: List[app_commands.AppCommand], 
            guild: Optional[Union[Snowflake, int]] = None) -> None:
        # because we support both int and Snowflake
        # we need to convert it to a Snowflake like object if it's an int
        _guild: Optional[Snowflake] = None
        if guild is not None:
            if isinstance(guild, int):
                _guild = Object(guild)
            else:
                _guild = guild

        if _guild:
            self._guild_app_commands[_guild.id] = self._unpack_app_commands(cmads)
        else:
            self._global_app_commands = self._unpack_app_commands(cmads)

    async def fetch_command(
            self, command_id: int, /, *, 
            guild: Optional[Snowflake] = None) -> app_commands.AppCommand:
        res = await super().fetch_command(command_id, guild=guild)
        await self._update_cache([res], guild=guild)
        return res

    async def fetch_commands(
            self, *, 
            guild: Optional[Snowflake] = None) -> List[app_commands.AppCommand]:
        res = await super().fetch_commands(guild=guild)
        await self._update_cache(res, guild=guild)
        return res

    def clear_app_commands_cache(self, *, guild: Optional[Snowflake]) -> None:
        if guild:
            self._guild_app_commands.pop(guild.id, None)
        else:
            self._global_app_commands = {}

    def clear_commands(self, *, guild: Optional[Snowflake], typer: Optional[AppCommandType] = None,
                       clear_app_commands_cache: bool = True) -> None:
        super().clear_commands(guild=guild)
        if clear_app_commands_cache:
            self.clear_app_commands_cache(guild=guild)

    async def sync(self, *, guild: Optional[Snowflake] = None) -> List[app_commands.AppCommand]:
        res = await super().sync(guild=guild)
        await self._update_cache(res, guild=guild)
        return res


class C2C(commands.Bot):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        # Database and HTTP Connections
        self.pool_connection = None
        self.session = None

        # Misc
        self.games = dict()
        self.time_launch = None

    async def setup_hook(self):
        print("we're in.")

        self.pool_connection = await create_pool(
            'C:\\Users\\georg\\Documents\\c2c\\db-shit\\economy.db')
        self.time_launch = datetime.now()
        self.session = ClientSession()


intents = Intents.none()
intents.members = True
intents.guild_messages = True
intents.message_content = True
intents.emojis_and_stickers = True
intents.guild_reactions = True
intents.guilds = True
intents.voice_states = True


client = C2C(
    command_prefix='>', intents=intents, case_insensitive=True, help_command=None, 
    owner_ids={992152414566232139, 546086191414509599, 1148206353647669298},
    activity=CustomActivity(name='Serving cc • /help'), status=Status.idle, 
    tree_cls=MyCommandTree, max_messages=100, max_ratelimit_timeout=30.0)
print(version)


cogs = Literal[
    "admin", "ctx_events", "economy", 
    "miscellaneous", "moderation", "music", 
    "slash_events", "tempvoice"]


@client.check
async def globally_block_dms(ctx) -> bool:
    return ctx.guild is not None


async def load_cogs() -> None:
    for filename in listdir('C:\\Users\\georg\\Documents\\c2c\\cogs'):
        if filename.endswith(".py"):
            await client.load_extension(f"cogs.{filename[:-3]}")


def return_txt_cmds_first(command_holder: dict,
                          category: Literal["Economy", "Moderation", "Miscellaneous", "Administrate", "Music"]) -> dict:
    """Displays all the text-based commands that are defined within a cog as a dict. This should always be called
    first for consistency."""
    for cmd in client.get_cog(category).get_commands():
        command_holder.update({cmd.name: deque([f'{category}', f'{cmd.description}', 'txt'])})
    return command_holder


def return_interaction_cmds_last(command_holder: dict,
                                 category: Literal[
                                     "Economy", "Moderation", "Miscellaneous", "Administrate", "Music"]) -> dict:
    """Displays all the app commands and grouped app commands that are defined within a cog as a dict. This should
    always be called last for consistency."""
    for cmd in client.get_cog(category).get_app_commands():
        command_holder.update({cmd.name: deque([f'{category}', f'{cmd.description}', 'sla'])})
    return command_holder


async def total_command_count(interaction: Interaction) -> int:
    """Return the total amount of commands detected within the client, including text and slash commands."""
    amount = (len(await client.tree.fetch_commands(guild=Object(id=interaction.guild.id))) + 1) + len(client.commands)
    return amount


class SelectMenu(ui.Select):
    def __init__(self):
        optionss = [
            SelectOption(
                label='Owner', 
                description='Commands available to bot owners.', 
                emoji='<a:e1_butterflyB:1124677894275338301>'),
            SelectOption(
                label='Moderation', 
                description='Commands available to moderators.', 
                emoji='<a:e1_starR:1124677520038567946>'),
            SelectOption(
                label='Utility', 
                description='Other helpful commands and resources.', 
                emoji='<a:e1_starG:1124677658500927488>'),
            SelectOption(
                label='Economy', 
                description='Commands for our virtual economy.', 
                emoji='<a:e1_starY:1124677741980176495>'),
            SelectOption(
                label='Music', 
                description='Commands for a music experience.', 
                emoji='<a:e1_starPur:1125040539943837738>')
        ]
        super().__init__(placeholder="Select a command category", options=optionss)

    async def callback(self, interaction: Interaction):

        their_choice = self.values[0]
        cmd_formatter: set = set()

        total_cmds_rough = await total_command_count(interaction)
        total_cmds_cata = 0

        for option in self.options:
            option.default = option.value == their_choice

        if their_choice == 'Owner':

            the_dict = {}
            new_dict = return_txt_cmds_first(the_dict, "Administrate")
            all_cmds: dict = return_interaction_cmds_last(new_dict, "Administrate")

            embed = Embed(title='Help: Owner', colour=Colour.from_rgb(91, 170, 239))
            embed.set_thumbnail(
                url='https://cdn.discordapp.com/icons/592654230112698378/1a4fed4eca3d81da620a662a8b383c5b.png?size=512')

            for cmd, cmd_details in all_cmds.items():
                total_cmds_cata += 1

                if cmd_details[-1] == 'txt':
                    cmd_formatter.add(f"\U00002022 [`>{cmd}`](https://youtu.be/dQw4w9WgXcQ) - {cmd_details[1]}")
                    continue

                command_manage = client.tree.get_app_command(cmd, guild=Object(id=interaction.guild.id))
                cmd_formatter.add(f"\U00002022 **{command_manage.mention}** - {cmd_details[1]}")

            proportion = (total_cmds_cata / total_cmds_rough) * 100
            
            embed.description = "\n".join(cmd_formatter)
            embed.add_field(
                name='About: Owner', 
                value=(
                    f'Contains commands that are only able to be utilized by the bot developers, '
                    f'and mostly'
                    f'contain commands related to debugging and testing new features into the client '
                    f'for later release.\n'
                    f'__Interesting Stats__\n'
                    f'- There are **{total_cmds_cata}** commands in this category\n'
                    f'- Accounts for **{proportion:.2f}%** of all commands\n'
                    f'- Last modified: <t:1702722548:D> (**<t:1702722548:R>**)\n'
                    f'- Status: **READY**'))

            await interaction.response.edit_message(embed=embed, view=self.view)

        elif their_choice == 'Moderation':

            the_dict = {}
            new_dict = return_txt_cmds_first(the_dict, "Moderation")
            all_cmds: dict = return_interaction_cmds_last(new_dict, "Moderation")

            embed = Embed(title='Help: Moderation', colour=Colour.from_rgb(247, 14, 115))
            embed.set_thumbnail(url='https://emoji.discadia.com/emojis/74e65408-2adb-46dc-86a7-363f3096b6b2.PNG')

            for cmd, cmd_details in all_cmds.items():
                total_cmds_cata += 1

                if cmd_details[-1] == 'txt':
                    cmd_formatter.add(f"\U00002022 [`>{cmd}`](https://youtu.be/dQw4w9WgXcQ) - {cmd_details[1]}")
                    continue
                
                command_manage = client.tree.get_app_command(cmd, guild=Object(id=interaction.guild.id))
                
                try:
                    got_something = False
                    if command_manage.options:
                        for option in command_manage.options:
                            if isinstance(option, app_commands.AppCommandGroup):
                                got_something = True
                                total_cmds_cata += 1
                                cmd_formatter.add(f"\U00002022 {option.mention} - {option.description}")
                    
                    if not got_something:
                        cmd_formatter.add(f"\U00002022 {command_manage.mention} - {cmd_details[1]}")
                except AttributeError:
                    continue

            roles = client.tree.get_app_command("role", guild=Object(id=interaction.guild.id))
            for option in roles.options:
                total_cmds_cata += 1
                cmd_formatter.add(f"\U00002022 {option.mention} - {option.description}")
            
            proportion = (total_cmds_cata / total_cmds_rough) * 100
            
            embed.description = "\n".join(cmd_formatter)
            embed.add_field(
                name='About: Mod', 
                value=(
                    f'Contains commands that are related to server management and moderation, hence these'
                    f' commands require invokers to have higher levels of permissions to utilize these.\n'
                    f'__Interesting Stats__\n'
                    f'- There are **{total_cmds_cata}** commands in this category\n'
                    f'- Accounts for **{proportion:.2f}%** of all commands\n'
                    f'- Last modified: <t:1698856225:D> (**<t:1698856225:R>**)\n'
                    f'- Status: **READY**'))

            await interaction.response.edit_message(embed=embed, view=self.view)

        elif their_choice == 'Utility':

            the_dict = {}
            new_dict = return_txt_cmds_first(the_dict, "Miscellaneous")
            all_cmds: dict = return_interaction_cmds_last(new_dict, "Miscellaneous")

            embed = Embed(title='Help: Utility', colour=Colour.from_rgb(15, 255, 135))
            embed.set_thumbnail(url='https://i.imgur.com/YHBLgVx.png')

            for cmd, cmd_details in all_cmds.items():
                total_cmds_cata += 1
                if cmd_details[-1] == 'txt':
                    cmd_formatter.add(f"\U00002022 [`>{cmd}`](https://youtu.be/dQw4w9WgXcQ) - {cmd_details[1]}")
                    continue

                command_manage = client.tree.get_app_command(cmd, guild=Object(id=interaction.guild.id))

                try:
                    got_something = False
                    if command_manage.options:
                        for option in command_manage.options:
                            if isinstance(option, app_commands.AppCommandGroup):
                                got_something = True
                                total_cmds_cata += 1
                                cmd_formatter.add(
                                    f"\U00002022 {option.mention} - {option.description}")
                    if not got_something:
                        cmd_formatter.add(f"\U00002022 {command_manage.mention} - {cmd_details[1]}")
                except AttributeError:
                    continue
            
            proportion = (total_cmds_cata / total_cmds_rough) * 100
            
            embed.description = "\n".join(cmd_formatter)
            embed.add_field(
                name='About: Utility', 
                value=(
                    f'Contains commands that may serve useful to some users, '
                    f'especially to some of the geeks out there.\n'
                    f'__Interesting Stats__\n'
                    f'- There are **{total_cmds_cata}** commands in this category\n'
                    f'- Accounts for **{proportion:.2f}%**'
                    f' of all commands\n'
                    f'- Last modified: <t:1702722548:D> (**<t:1702722548:R>**)\n'
                    f'- Status: **READY**'))

            await interaction.response.edit_message(embed=embed, view=self.view)

        elif their_choice == 'Economy':
            
            embed = Embed(title='Help: Economy', colour=Colour.from_rgb(255, 215, 0))
            embed.set_thumbnail(url='https://upload.wikimedia.org/wikipedia/commons/thumb/c/c7/Robux_2019_Logo_gold.svg/200px-Robux_2019_Logo_gold.svg.png')

            the_dict = {}
            new_dict = return_txt_cmds_first(the_dict, "Economy")
            all_cmds: dict = return_interaction_cmds_last(new_dict, "Economy")
            for cmd, cmd_details in all_cmds.items():
                total_cmds_cata += 1
                if cmd_details[-1] == 'txt':
                    cmd_formatter.add(f"\U00002022 [`>{cmd}`](https://youtu.be/dQw4w9WgXcQ) - {cmd_details[1]}")
                    continue

                command_manage = client.tree.get_app_command(cmd, guild=Object(id=interaction.guild.id))

                try:
                    got_something = False
                    if command_manage.options:
                        for option in command_manage.options:
                            if isinstance(option, app_commands.AppCommandGroup):
                                got_something = True
                                total_cmds_cata += 1
                                cmd_formatter.add(
                                    f"\U00002022 {option.mention} - {option.description}")
                    if not got_something:
                        cmd_formatter.add(f"\U00002022 {command_manage.mention} - {cmd_details[1]}")
                except AttributeError:
                    cmd_formatter.add(f"\U00002022 </balance:1192188834134376500> - {cmd_details[1]}")

            proportion = (total_cmds_cata / total_cmds_rough) * 100

            embed.description = "\n".join(cmd_formatter)
            embed.add_field(
                name='About: Economy', 
                value=(
                    f'Contains commands that can be used by anybody, and relate to the virtual economy '
                    f'system of the client.\n'
                    f'__Interesting Stats__\n'
                    f'- There are **{total_cmds_cata}** commands in this category\n'
                    f'- Accounts for **{proportion:.2f}%** of all commands\n'
                    f'- Last modified: <t:1702722548:D> (**<t:1702722548:R>**)\n'
                    f'- Status: **LOCKED**'))

            await interaction.response.edit_message(embed=embed, view=self.view)

        else:

            embed = Embed(title='Help: Music', colour=Colour.from_rgb(105, 83, 224))
            embed.set_thumbnail(url="https://i.imgur.com/nFZTMFl.png")

            the_dict: dict = {}
            all_cmds = return_txt_cmds_first(the_dict, "Music")

            for cmd, cmd_details in all_cmds.items():
                cmd_formatter.add(f"\U00002022 [`>{cmd}`](https://youtu.be/dQw4w9WgXcQ) - {cmd_details[1]}")
                total_cmds_cata += 1

            proportion = (total_cmds_cata / total_cmds_rough) * 100

            embed.description = "\n".join(cmd_formatter)
            embed.add_field(
                name='About: Music', 
                value=(
                    f'Contains commands that can be used by anybody, related to the music client '
                    f'and its functions. Use these commands to play music on Discord.\n'
                    f'__Interesting Stats__\n'
                    f'- There are **{total_cmds_cata}** commands in this category\n'
                    f'- Accounts for **{proportion:.2f}%** of all commands\n'
                    f'- Last modified: <t:1703857689:D> (**<t:1703857689:R>**)\n'
                    f'- Status: **READY**'))
            await interaction.response.edit_message(embed=embed, view=self.view)


class Select(ui.View):
    def __init__(self):
        super().__init__(timeout=60.0)
        self.add_item(SelectMenu())

    async def on_timeout(self) -> None:
        for item in self.children:
            item.disabled = True
        try:
            await self.message.edit(view=self)
        except NotFound:
            pass


class TimeConverter(commands.Converter):
    time_regex = compile(r"(\d{1,5}(?:[.,]?\d{1,5})?)([smhd])")
    time_dict = {"h": 3600, "s": 1, "m": 60, "d": 86400}

    async def convert(self, ctx, argument):
        matches = self.time_regex.findall(argument.lower())
        time = 0
        for v, k in matches:
            try:
                time += self.time_dict[k]*float(v)
            except KeyError:
                raise commands.BadArgument(f"{k} is an invalid time-key! h/m/s/d are valid!")
            except ValueError:
                raise commands.BadArgument(f"{v} is not a number!")
        return time


@client.command(name='convert')
async def convert_time(ctx, time: TimeConverter):
    await ctx.send(f"Converted time: {time} seconds")


@client.command(name="test")
async def testit(ctx):
    embed = Embed()
    embed.title = "Your balance"
    embed.add_field(name="Field 1", value="240,254,794")
    embed.add_field(name="Field 2", value="693,201,329")
    embed.add_field(name="\U0000200b", value="\U0000200b")
    embed.add_field(name="Field 3", value="1,000,000,000")
    embed.add_field(name="Field 4", value="1,000,000,000")
    embed.add_field(name="\U0000200b", value="\U0000200b")
    embed.set_footer(text="This embed is used within DMO!")
    await ctx.send(embed=embed)


@client.command(name='dispatch-webhook', aliases=("dw",))
async def dispatch_the_webhook_when(ctx: commands.Context):
    await ctx.message.delete()
    embed = Embed(
        colour=Colour.from_rgb(3, 102, 214),
        title='Changes for 2024 Q1',
        description="Changes that have taken place in the period between January 1 - March 31 are noted here.\n\n"
                    "- Some bots were remove")
    embed.set_footer(icon_url=ctx.guild.icon.url, text="That's all for Q1 2024. Next review due: 30 June 2024.")
    
    webhook = Webhook.from_url(url=client.WEBHOOK_URL, session=client.session)
    thread = await ctx.guild.fetch_channel(1190736866308276394)
    rtype = "feature" # or "bugfix"
    
    await webhook.send(
        f'Patch notes for Q1 2024 / This is mostly a `{rtype}` release', 
        embed=embed, thread=Object(id=thread.id), silent=True)
    
    await ctx.send(f"Sent to '{thread.mention}' with ID {thread.id}.")


@commands.is_owner()
@client.command(name='reload', aliases=("rl",))
async def reload_cog(ctx: commands.Context, cog_name: cogs):

    try:
        await client.reload_extension(f"cogs.{cog_name}")
    except commands.ExtensionNotLoaded:
        return await ctx.send("That extension has not been loaded in yet.")
    except commands.ExtensionNotFound:
        return await ctx.send("Could not find an extension with that name.")
    except commands.NoEntryPointError:
        return await ctx.send("The extension does not have a setup function.")
    
    except commands.ExtensionFailed as e:
        print(e)
        return await ctx.send("The extension failed to load. See the console for traceback.")
    
    await ctx.message.add_reaction("\U00002705")


@commands.is_owner()
@client.command(name='unload', aliases=("ul",))
async def unload_cog(ctx: commands.Context, cog_name: cogs):

    try:
        await client.unload_extension(f"cogs.{cog_name}")
    except commands.ExtensionNotLoaded:
        return await ctx.send("That extension has not been loaded in yet.")
    except commands.ExtensionNotFound:
        return await ctx.send("Could not find an extension with that name.")
    
    await ctx.message.add_reaction("\U00002705")


@commands.is_owner()
@client.command(name='load', aliases=("ld",))
async def load_cog(ctx: commands.Context, cog_name: cogs):
        
    try:
        await client.load_extension(f"cogs.{cog_name}")
    except commands.ExtensionAlreadyLoaded:
        return await ctx.send("That extension is already loaded.")
    except commands.ExtensionNotFound:
        return await ctx.send("Could not find an extension with that name.")
    except commands.NoEntryPointError:
        return await ctx.send("The extension does not have a setup function.")
    
    except commands.ExtensionFailed as e:
        print(e)
        return await ctx.send("The extension failed to load. See the console for traceback.")

    await ctx.message.add_reaction("\U00002705")


@client.tree.command(
    name='help', 
    description='The help command for c2c. Shows help for different categories.', 
    guilds=[Object(id=829053898333225010), Object(id=780397076273954886)])
async def help_command_category(interaction: Interaction):
    
    epicker = choice(
        ["<:githubB:1195500626382164119>", "<:githubBF:1195498685296021535>", 
         "<:githubW:1195499565508460634>", "<:githubBlue:1195664427836506212>"])

    embed = Embed(
        title='Help Menu for c2c', 
        description=(
            '```fix\n[Patch #31]\n'
            '- ON_MESSAGE events (triggers) added\n'
            '- Buttons are generally available\n'
            '- Shop command redesign and grouped```\n'
            'A few things to note:\n'
            '- This help command does not display uncategorized commands.\n'
            '- The prefix for this bot is `>` (for text commands)\n'
            '- Not all categories are accessible to everyone, check the details prior.'), 
            colour=Colour.from_rgb(138, 175, 255))
    embed.add_field(
        name="Who are you?", 
        value=(
            "I'm a bot made by Splint#6019 and Geo#2181. "
            f"I've been on Discord since <t:1669831154:f> and joined {interaction.guild.name} on "
            f"{format_dt(interaction.guild.me.joined_at, style="f")}.\n\n"
            "I have a variety of features such as an advanced economy system, moderation, debugging "
            "tools and some other random features that may aid you in this journey. "
            "You can get more information on my commands by using the dropdown below.\n\n"
            f"I'm also open source. You can see my code on {epicker} "
            "[GitHub](https://github.com/SGA-A/c2c)."), inline=False)

    help_view = Select()
    await interaction.response.send_message(embed=embed, view=help_view, ephemeral=True)
    help_view.message = await interaction.original_response()


async def main():
    try:
        setup_logging(level=LOGGING_INFO)

        load_dotenv()
        TOKEN = environ.get("BOT_TOKEN")
        client.WEBHOOK_URL = environ.get("WEBHOOK_URL")
        client.GITHUB_TOKEN = environ.get("GITHUB_TOKEN")
        client.JEYY_API_KEY = environ.get("JEYY_API_KEY")
        client.NINJAS_API_KEY = environ.get("API_KEY")
        client.WAIFU_API_KEY = environ.get("WAIFU_API_KEY")

        await load_cogs()
        await client.start(TOKEN)
    finally:
        await client.close()


run(main())
