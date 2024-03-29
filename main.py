from __future__ import annotations

from dotenv import load_dotenv
from datetime import datetime
from os import listdir, environ
from sys import version

from re import compile
from random import choice
from collections import deque
from typing import Literal, Any, Dict, Optional, TYPE_CHECKING, Union, List, Tuple
from logging import INFO as LOGGING_INFO

from asyncio import run
from aiohttp import ClientSession
from asqlite import create_pool

from discord.utils import setup_logging, format_dt
from discord import app_commands, Object, ui, Intents, Status, Embed, Interaction, CustomActivity
from discord import AppCommandType, SelectOption, Colour, Webhook, NotFound, ButtonStyle
from discord.ext import commands

from cogs.economy import membed

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
intents.guilds = True
intents.voice_states = True


client = C2C(
    command_prefix='>', intents=intents, case_insensitive=True, help_command=None, 
    owner_ids={992152414566232139, 546086191414509599},  # 1148206353647669298
    activity=CustomActivity(name='Serving cc • /help'), status=Status.idle, 
    tree_cls=MyCommandTree, max_messages=100, max_ratelimit_timeout=30.0)
print(version)


cogs = Literal[
    "admin", "ctx_events", "economy", 
    "miscellaneous", "moderation", "music", 
    "slash_events", "tempvoice"]
classnames = Literal["Economy", "Moderation", "Utility", "Owner", "Music", "TempVoice"]


@client.check
async def globally_block_dms(ctx) -> bool:
    return ctx.guild is not None


async def load_cogs() -> None:
    for filename in listdir('C:\\Users\\georg\\Documents\\c2c\\cogs'):
        if filename.endswith(".py"):
            await client.load_extension(f"cogs.{filename[:-3]}")


def return_txt_cmds_first(
        command_holder: dict, category: classnames) -> dict:
    """Displays all the text-based commands that are defined within a cog as a dict. This should always be called
    first for consistency."""
    for cmd in client.get_cog(category).get_commands():
        command_holder.update({cmd.name: deque([f'{category}', f'{cmd.description}', 'txt'])})
    return command_holder


def return_interaction_cmds_last(
        command_holder: dict, category: classnames) -> dict:
    """Displays all the app commands and grouped app commands that are defined within a cog as a dict. This should
    always be called last for consistency."""
    for cmd in client.get_cog(category).get_app_commands():
        command_holder.update({cmd.name: deque([f'{category}', f'{cmd.description}', 'sla'])})
    return command_holder


def fill_up_commands(category: classnames) -> dict:
    """Assumes a category has both slash and text commands."""
    the_dict = {}
    new_dict = return_txt_cmds_first(the_dict, category)
    all_cmds: dict = return_interaction_cmds_last(new_dict, category)
    return all_cmds


def generic_loop_with_subcommand(all_cmds: dict, cmd_formatter: set, guild_id) -> Tuple[set, int]:
    total_command_count = 0

    for cmd, cmd_details in all_cmds.items():
        total_command_count += 1

        if cmd_details[-1] == 'txt':
            cmd_formatter.add(f"\U00002022 [`>{cmd}`](https://youtu.be/dQw4w9WgXcQ) - {cmd_details[1]}")
            continue
        
        command_manage = client.tree.get_app_command(cmd, guild=Object(id=guild_id))
        
        try:
            got_something = False
            if command_manage.options:
                for option in command_manage.options:
                    if isinstance(option, app_commands.AppCommandGroup):
                        got_something = True
                        total_command_count += 1
                        cmd_formatter.add(f"\U00002022 {option.mention} - {option.description}")
            
            if not got_something:
                cmd_formatter.add(f"\U00002022 {command_manage.mention} - {cmd_details[1]}")
        except AttributeError:
            continue
    return cmd_formatter, total_command_count


async def total_command_count(interaction: Interaction) -> int:
    """Return the total amount of commands detected within the client, including text and slash commands."""
    amount = (len(await client.tree.fetch_commands(guild=Object(id=interaction.guild.id))) + 1) + len(client.commands)
    return amount


class SelectMenu(ui.Select):
    def __init__(self):
        optionss = [
            SelectOption(
                label='Owner', 
                description='Debugging facilities for developers.', 
                emoji='<:ownerSTAR:1221502316478464050>'),
            SelectOption(
                label='Moderation', 
                description='Manage your own server, easily.', 
                emoji='<:modSTAR:1221502315241013259>'),
            SelectOption(
                label='Utility', 
                description='Entertainment beginning.', 
                emoji='<:utilitySTAR:1221502313798172753>'),
            SelectOption(
                label='Economy', 
                description='Earn a living in a simulated virtual economy.', 
                emoji='\U00002b50'),
            SelectOption(
                label="TempVoice", 
                description="Configure your own temporary voice channel.",
                emoji="<:tempSTAR:1221502312472903851>"),
            SelectOption(
                label='Music', 
                description='Stream your favourite tunes from any platform.', 
                emoji='<:musicSTAR:1221502310967017652>')
        ]
        super().__init__(placeholder="Select a command category", options=optionss)

    async def callback(self, interaction: Interaction):

        their_choice = self.values[0]
        cmd_formatter = set()

        total_cmds_rough = await total_command_count(interaction)
        total_cmds_cata = 0

        for option in self.options:
            option.default = option.value == their_choice

        embed = Embed()
        embed.title = f"Help: {their_choice}"
        if their_choice == 'Owner':

            all_cmds = fill_up_commands(their_choice)

            embed.colour = 0x5BAAEF
            embed.set_thumbnail(
                url='https://cdn.discordapp.com/icons/592654230112698378/1a4fed4eca3d81da620a662a8b383c5b.png?size=512')

            for cmd, cmd_details in all_cmds.items():
                total_cmds_cata += 1

                if cmd_details[-1] == 'txt':
                    cmd_formatter.add(f"\U00002022 [`>{cmd}`](https://youtu.be/dQw4w9WgXcQ) - {cmd_details[1]}")
                    continue

                command_manage = client.tree.get_app_command(cmd, guild=Object(id=interaction.guild.id))
                cmd_formatter.add(f"\U00002022 **{command_manage.mention}** - {cmd_details[1]}")

        elif their_choice == 'Moderation':

            all_cmds = fill_up_commands(their_choice)

            embed.colour = 0xF70E73
            embed.set_thumbnail(url='https://emoji.discadia.com/emojis/74e65408-2adb-46dc-86a7-363f3096b6b2.PNG')

            cmd_formatter, total_cmds_cata = generic_loop_with_subcommand(all_cmds, cmd_formatter, interaction.guild_id)

            roles = client.tree.get_app_command("role", guild=Object(id=interaction.guild.id))
            for option in roles.options:
                total_cmds_cata += 1
                cmd_formatter.add(f"\U00002022 {option.mention} - {option.description}")

        elif (their_choice == 'Utility') or (their_choice == "TempVoice"):

            all_cmds = fill_up_commands(their_choice)
            match their_choice:
                case "Utility":
                    embed.colour = 0x0FFF87
                    embed.set_thumbnail(url='https://i.imgur.com/YHBLgVx.png')
                case _:
                    embed.colour = 0x8A1941
                    embed.set_thumbnail(url='https://i.imgur.com/b8u1MQj.png')
            cmd_formatter, total_cmds_cata = generic_loop_with_subcommand(all_cmds, cmd_formatter, interaction.guild_id)
        elif their_choice == 'Economy':
            
            embed.colour = 0xFFD700
            embed.set_thumbnail(url='https://upload.wikimedia.org/wikipedia/commons/thumb/c/c7/Robux_2019_Logo_gold.svg/200px-Robux_2019_Logo_gold.svg.png')

            all_cmds = fill_up_commands(their_choice)
            
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
        else:
            embed.colour = 0x6953E0
            embed.set_thumbnail(url="https://i.imgur.com/nFZTMFl.png")

            all_cmds = return_txt_cmds_first(dict(), their_choice)

            for cmd, cmd_details in all_cmds.items():
                cmd_formatter.add(f"\U00002022 [`>{cmd}`](https://youtu.be/dQw4w9WgXcQ) - {cmd_details[1]}")
                total_cmds_cata += 1

        proportion = (total_cmds_cata / total_cmds_rough) * 100
        embed.description = "\n".join(cmd_formatter)
        embed.add_field(
            name='Info', 
            value=(
                f'- {total_cmds_cata} commands listed\n'
                f'- {proportion:.2f}% of all commands are here'
            )
        )

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


class Confirm(ui.View):
    """Chopped down version of the original interactive menu."""

    def __init__(self, ctx: commands.Context):
        self.ctx = ctx
        super().__init__(timeout=45.0)
        self.value = None

    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.user.id in interaction.client.owner_ids:
            return True
        await interaction.response.send_message(
            embed=membed("This confirmation menu is for developer use only."), ephemeral=True)
        return False

    @ui.button(label='Cancel', style=ButtonStyle.red)
    async def cancel(self, interaction: Interaction, button: ui.Button):
        self.children[1].style = ButtonStyle.grey
        button.style = ButtonStyle.success
        
        for item in self.children:
            item.disabled = True

        await interaction.response.edit_message(view=self)
        
        self.value = False
        self.stop()

    @ui.button(label='Confirm', style=ButtonStyle.green)
    async def confirm(self, interaction: Interaction, button: ui.Button):
        self.children[0].style = ButtonStyle.grey
        button.style = ButtonStyle.success

        for item in self.children:
            item.disabled = True
        
        await interaction.response.edit_message(view=self)

        self.value = True
        self.stop()


async def confirm_before_hot_reloading(ctx: commands.Context) -> bool:
    confirm = Confirm(ctx)

    confirmation = Embed(title="Pending Confirmation", colour=0x2B2D31)
    confirmation.description = (
        "Data previously loaded into a data structure will be lost.\n"
        "Are you **sure** you want to proceed?")
    msg = await ctx.send(embed=confirmation, view=confirm)
    
    await confirm.wait()

    if confirm.value is None:
        for item in confirm.children:
            item.disabled = True

        confirmation.title = "Timed out"
        confirmation.description = f"~~{confirmation.description}~~"
        confirmation.colour = Colour.brand_red()
    elif confirm.value:
        confirmation.title = "Action Confirmed"
        confirmation.colour = Colour.green()
    else:
        confirmation.title = "Action Cancelled"
        confirmation.colour = Colour.brand_red()
    
    await msg.edit(embed=confirmation, view=confirm)
    return confirm.value


@commands.is_owner()
@client.command(name='reload', aliases=("rl",))
async def reload_cog(ctx: commands.Context, cog_name: cogs):
    val = await confirm_before_hot_reloading(ctx)
    try:
        if not val:
            return
        await client.reload_extension(f"cogs.{cog_name}")
    except commands.ExtensionNotLoaded:
        return await ctx.reply(embed=membed("That extension has not been loaded in yet."))
    except commands.ExtensionNotFound:
        return await ctx.reply(embed=membed("Could not find an extension with that name."))
    except commands.NoEntryPointError:
        return await ctx.reply(embed=membed("The extension does not have a setup function."))
    
    except commands.ExtensionFailed as e:
        print(e)
        return await ctx.reply(embed=membed("The extension failed to load. See the console for traceback."))
    
    await ctx.reply(embed=membed("Done."))

@commands.is_owner()
@client.command(name='unload', aliases=("ul",))
async def unload_cog(ctx: commands.Context, cog_name: cogs):

    try:
        val = await confirm_before_hot_reloading(ctx)
        if not val:
            return
        await client.unload_extension(f"cogs.{cog_name}")
    except commands.ExtensionNotLoaded:
        return await ctx.reply("That extension has not been loaded in yet.")
    except commands.ExtensionNotFound:
        return await ctx.reply("Could not find an extension with that name.")
    
    await ctx.reply(embed=membed("Done."))


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
