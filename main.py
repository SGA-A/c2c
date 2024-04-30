from __future__ import annotations

from asyncio import run
from aiohttp import ClientSession
from asqlite import create_pool

from dotenv import load_dotenv
from datetime import datetime
from pathlib import Path
from traceback import print_exception
from os import environ
from sys import version, stderr

from re import compile
from logging import INFO

from typing import (
    Literal, 
    Any, 
    Dict, 
    Optional, 
    TYPE_CHECKING, 
    Union, 
    List
)

from discord import (
    app_commands, 
    Object, 
    ui, 
    Intents,
    Status, 
    Embed, 
    Interaction, 
    CustomActivity,
    AppCommandType, 
    SelectOption, 
    Colour,
    Webhook, 
    NotFound
)

from discord.utils import setup_logging
from discord.ext import commands
from cogs.economy import membed, APP_GUILDS_ID

if TYPE_CHECKING:
    from discord.abc import Snowflake

    AppCommandStore = Dict[str, app_commands.AppCommand]  # name: AppCommand


slash_cmds = None


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
            self, 
            value: Union[str, int],
            guild: Optional[Union[Snowflake, int]] = None
        ) -> Optional[app_commands.AppCommand]:
        
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
            self, 
            cmads: List[app_commands.AppCommand], 
            guild: Optional[Union[Snowflake, int]] = None
        ) -> None:

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

    async def fetch_command(self, command_id: int, /, *, guild: Optional[Snowflake] = None) -> app_commands.AppCommand:
        res = await super().fetch_command(command_id, guild=guild)
        await self._update_cache([res], guild=guild)
        return res

    async def fetch_commands(
            self, *, 
            guild: Optional[Snowflake] = None
        ) -> List[app_commands.AppCommand]:

        res = await super().fetch_commands(guild=guild)
        await self._update_cache(res, guild=guild)
        return res

    def clear_app_commands_cache(self, *, guild: Optional[Snowflake]) -> None:
        if guild:
            self._guild_app_commands.pop(guild.id, None)
        else:
            self._global_app_commands = {}

    def clear_commands(
            self, 
            *, 
            guild: Optional[Snowflake], 
            command_type: Optional[AppCommandType] = None, 
            clear_app_commands_cache: bool = True
        ) -> None:
        
        super().clear_commands(guild=guild)
        if clear_app_commands_cache:
            self.clear_app_commands_cache(guild=guild)

    async def sync(
            self, 
            *, 
            guild: Optional[Snowflake] = None
        ) -> List[app_commands.AppCommand]:

        res = await super().sync(guild=guild)
        await self._update_cache(res, guild=guild)
        return res


class C2C(commands.Bot):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

        # Database and HTTP Connections
        self.pool = None
        self.session = None

        # Misc
        self.games = dict()
        self.time_launch = None

    async def setup_hook(self):
        print("we're in.")

        for file in Path('cogs').glob('**/*.py'):
            *tree, _ = file.parts
            try:
                await self.load_extension(f"{'.'.join(tree)}.{file.stem}")
            except Exception as e:
                print_exception(type(e), e, e.__traceback__, file=stderr)

        self.pool = await create_pool(
            'C:\\Users\\georg\\Documents\\c2c\\db-shit\\economy.db'
        )

        self.time_launch = datetime.now()
        self.session = ClientSession()


intents = Intents.none()
intents.members = True
intents.guild_messages = True
intents.message_content = True
intents.emojis_and_stickers = True
intents.guilds = True
intents.voice_states = True


bot = C2C(
    command_prefix='>', 
    intents=intents, 
    case_insensitive=True, 
    help_command=None, 
    owner_ids={992152414566232139, 546086191414509599},
    activity=CustomActivity(name='Serving cc • /help'), 
    status=Status.idle, 
    tree_cls=MyCommandTree, 
    max_messages=100, 
    max_ratelimit_timeout=30.0
)
print(version)


cogs = Literal[
    "admin", 
    "ctx_events", 
    "economy", 
    "miscellaneous", 
    "moderation", 
    "music", 
    "slash_events", 
    "tags",
    "tempvoice"
]

classnames = Literal[
    "Economy", 
    "Moderation", 
    "Utility", 
    "Owner", 
    "Music", 
    "Tags", 
    "TempVoice"
]


def return_txt_cmds_first(command_holder: dict, category: classnames) -> dict:
    """Displays all text-based commands defined within a cog as a dict."""
    for cmd in bot.get_cog(category).get_commands():
        command_holder.update(
            {
                cmd.name: (f'{cmd.description}', 'txt')
            }
        )
    return command_holder


def return_interaction_cmds_last(command_holder: dict, category: classnames) -> dict:
    """Displays all slash commands defined within a cog as a dict."""
    for cmd in bot.get_cog(category).get_app_commands():
        command_holder.update(
            {
                cmd.name: (f'{cmd.description}', 'sla')
            }
        )
    return command_holder


def fill_up_commands(category: classnames) -> dict:
    """Assumes a category has both slash and text commands."""
    new_dict = return_txt_cmds_first({}, category)
    all_cmds: dict = return_interaction_cmds_last(new_dict, category)
    return all_cmds


def generic_loop_slash_only_subcommands(all_cmds: dict, cmd_formatter: list, guild_id) -> set:
    """Returns tuple with first element as set of commands, second being the total command count."""
    for i, cmd in enumerate(all_cmds, start=1):

        command_manage = bot.tree.get_app_command(cmd, guild=Object(id=guild_id))

        for option in command_manage.options:
            if not isinstance(option, app_commands.AppCommandGroup):
                continue

            contains_subcommands = False
            for option in command_manage.options:
                if isinstance(option, app_commands.AppCommandGroup):
                    contains_subcommands = True
                    cmd_formatter.append(f"{i}. {option.mention} - {option.description}")

            if not contains_subcommands:
                cmd_formatter.append(f"{i}. {command_manage.mention} - {command_manage.description}")
    return cmd_formatter


def generic_loop_with_subcommand(all_cmds: dict, cmd_formatter: list, guild_id) -> set:

    for i, (cmd, cmd_details) in enumerate(all_cmds.items(), start=1):

        if cmd_details[-1] == 'txt':
            cmd_formatter.append(f"{i}. [`>{cmd}`](https://youtu.be/dQw4w9WgXcQ) - {cmd_details[0]}")
            continue
        
        command_manage = bot.tree.get_app_command(cmd, guild=Object(id=guild_id))

        if not isinstance(command_manage, app_commands.AppCommand):
            continue

        contains_subcommands = False
        for option in command_manage.options:
            if isinstance(option, app_commands.AppCommandGroup):
                contains_subcommands = True
                cmd_formatter.append(f"{i}. {option.mention} - {option.description}")

        if not contains_subcommands:
            cmd_formatter.append(f"{i}. {command_manage.mention} - {command_manage.description}")

    return cmd_formatter


async def total_command_count(interaction: Interaction) -> int:
    """Return the total amount of commands detected within the bot, including text and slash commands."""
    global slash_cmds
    if slash_cmds:
        return slash_cmds
    return (len(await bot.tree.fetch_commands(guild=Object(id=interaction.guild.id))) + 1) + len(bot.commands)


class HelpDropdown(ui.Select):
    def __init__(self):
        optionss = [
            SelectOption(
                label='Owner', 
                description='Debugging facilities for developers.', 
                emoji='<:ownerSTAR:1221502316478464050>'
            ),
            SelectOption(
                label='Moderation', 
                description='Manage your own server, easily.', 
                emoji='<:modSTAR:1221502315241013259>'
            ),
            SelectOption(
                label='Utility', 
                description='Entertainment beginning.', 
                emoji='<:utilitySTAR:1221502313798172753>'
            ),
            SelectOption(
                label='Economy', 
                description='Earn a living in a simulated virtual economy.', 
                emoji='\U00002b50'
            ),
            SelectOption(
                label='Tags',
                description='Create and manage your own tags.',
                emoji='<:tagsSTAR:1227681495255355535>'
            ),
            SelectOption(
                label="TempVoice", 
                description="Configure your own temporary voice channel.",
                emoji="<:tempSTAR:1221502312472903851>"
            ),
            SelectOption(
                label='Music', 
                description='Stream your favourite tunes from any platform.', 
                emoji='<:musicSTAR:1221502310967017652>'
            )
        ]
        super().__init__(placeholder="Select a command category", options=optionss)

    async def callback(self, interaction: Interaction):

        chosen_help_category: str = self.values[0]
        cmd_formatter = []

        total_cmds_rough = await total_command_count(interaction)

        for option in self.options:
            option.default = option.value == chosen_help_category

        embed = Embed(title=f"Help: {chosen_help_category}")
        if chosen_help_category == 'Owner':
            
            all_cmds = fill_up_commands(chosen_help_category)

            embed.colour = 0x5BAAEF
            embed.set_thumbnail(url='https://cdn.discordapp.com/icons/592654230112698378/1a4fed4eca3d81da620a662a8b383c5b.png?size=512')

            for i, (cmd, cmd_details) in enumerate(all_cmds.items(), start=1):

                if cmd_details[-1] == 'txt':
                    cmd_formatter.append(f"{i}. [`>{cmd}`](https://youtu.be/dQw4w9WgXcQ) - {cmd_details[0]}")
                    continue

                command_manage = bot.tree.get_app_command(cmd, guild=Object(id=interaction.guild.id))
                cmd_formatter.append(f"{i}. **{command_manage.mention}** - {command_manage.description}")

        elif chosen_help_category == 'Moderation':

            all_cmds = fill_up_commands(chosen_help_category)
            all_cmds.update({"role": "sla"})

            embed.colour = 0xF70E73
            embed.set_thumbnail(url='https://emoji.discadia.com/emojis/74e65408-2adb-46dc-86a7-363f3096b6b2.PNG')

            cmd_formatter = generic_loop_with_subcommand(all_cmds, cmd_formatter, interaction.guild_id)

        elif chosen_help_category == 'Tags':

            all_cmds = bot.get_cog(chosen_help_category).get_commands()[0]
            for i, cmd in enumerate(all_cmds.commands, start=1):
                cmd_formatter.append(f"{i}. [`>{cmd.qualified_name}`](https://youtu.be/dQw4w9WgXcQ) - {cmd.description}")
        
            embed.colour = 0x9EE1FF
            embed.set_thumbnail(url='https://i.imgur.com/uHb7xhc.png')
            embed.set_footer(text="These are also available as slash commands!")

        elif chosen_help_category in {"Utility", "TempVoice"}:

            all_cmds = fill_up_commands(chosen_help_category)
            match chosen_help_category:
                case "Utility":
                    embed.colour = 0x0FFF87
                    embed.set_thumbnail(url='https://i.imgur.com/YHBLgVx.png')
                case _:
                    embed.colour = 0x8A1941
                    embed.set_thumbnail(url='https://i.imgur.com/b8u1MQj.png')
            
            cmd_formatter = generic_loop_with_subcommand(all_cmds, cmd_formatter, interaction.guild_id)
        elif chosen_help_category == 'Economy':
            
            embed.colour = 0xFFD700
            embed.set_thumbnail(url='https://upload.wikimedia.org/wikipedia/commons/thumb/c/c7/Robux_2019_Logo_gold.svg/200px-Robux_2019_Logo_gold.svg.png')

            all_cmds = fill_up_commands(chosen_help_category)
            
            cmd_formatter = generic_loop_with_subcommand(all_cmds, cmd_formatter, interaction.guild_id)
        else:
            embed.colour = 0x6953E0
            embed.set_thumbnail(url="https://i.imgur.com/nFZTMFl.png")

            all_cmds = return_txt_cmds_first({}, chosen_help_category)

            for i, (cmd, cmd_details) in enumerate(all_cmds.items(), start=1):
                cmd_formatter.append(f"{i}. [`>{cmd}`](https://youtu.be/dQw4w9WgXcQ) - {cmd_details[0]}")

        prcntage = (len(cmd_formatter) / total_cmds_rough) * 100

        embed.description = "\n".join(cmd_formatter)
        embed.add_field(
            name="Info", 
            value=(
                f"- {total_cmds_rough} commands total\n"
                f"- {prcntage:.0f}% of all commands are here"
            )
        )

        await interaction.response.edit_message(embed=embed, view=self.view)


class Select(ui.View):
    def __init__(self):
        super().__init__(timeout=30.0)
        self.add_item(HelpDropdown())

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

    async def convert(self, _, argument):
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


@bot.command(name='convert')
async def convert_time(ctx, time: TimeConverter):
    await ctx.send(f"Converted time: {time} seconds")


@bot.command(name="test")
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


@bot.command(name='dispatch-webhook', aliases=("dw",))
async def dispatch_the_webhook_when(ctx: commands.Context):
    await ctx.message.delete()
    embed = Embed(
        colour=Colour.from_rgb(3, 102, 214),
        title='Changelog',
        description=(
            "Changes taken place between <t:1711929600:d> - <t:1719705600:d> are noted here.\n\n"
            "- Added new colour roles\n"
            "- Changed the colour of some colour roles\n"
            "- Added new self roles obtainable via <id:customize>\n"
            "- Changed the default colour for <@&914565377961369632>\n"
            "- Emojified the topic of all non-archived channels\n"
            "- Added new tasks to complete in Server Onboarding\n"
            "- Removed more redundant permissions from bots\n"
            "- Cleaned the pinned messages of most channels\n"
            "- Added a requirement to include tags upon creating a post\n"
            "- Simplified the guidelines thread for the forum (https://discord.com/channels/829053898333225010/1147203137195745431)\n"
            "- Added a policy to never close threads that are inactive, only lock them\n"
            "- Kicked more bots off the server\n"
            "- Renamed some channels for consistency\n"
            "- Disabled some custom AutoMod rules\n"
        )
    )
    
    embed.set_footer(
        icon_url=ctx.guild.icon.url, 
        text="That's all for Q2 2024. Next review due: 30 September 2024."
    )
    
    webhook = Webhook.from_url(url=bot.WEBHOOK_URL, session=bot.session)
    rtype = "feature"  # or "bugfix"
    
    # For editing the original message

    # msg = await webhook.fetch_message(
    #     1225532637217554503, 
    #     thread=Object(id=1190736866308276394)
    # )

    # await msg.edit(
    #     content=f'This is mostly a `{rtype}` release.', 
    #     embed=embed
    # )

    await webhook.send(
        content=f'This is mostly a `{rtype}` release.',
        embed=embed, 
        thread=Object(id=1190736866308276394),
        silent=True
    )
    
    await ctx.send("Done.")


@commands.is_owner()
@bot.command(name='reload', aliases=("rl",))
async def reload_cog(ctx: commands.Context, cog_name: cogs):
    try:
        await bot.reload_extension(f"cogs.{cog_name}")
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
@bot.command(name='unload', aliases=("ul",))
async def unload_cog(ctx: commands.Context, cog_name: cogs):

    try:
        await bot.unload_extension(f"cogs.{cog_name}")
    except commands.ExtensionNotLoaded:
        return await ctx.reply("That extension has not been loaded in yet.")
    except commands.ExtensionNotFound:
        return await ctx.reply("Could not find an extension with that name.")
    
    await ctx.reply(embed=membed("Done."))


@commands.is_owner()
@bot.command(name='load', aliases=("ld",))
async def load_cog(ctx: commands.Context, cog_name: cogs):
    try:
        await bot.load_extension(f"cogs.{cog_name}")
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


async def do_guild_checks(interaction: Interaction):
    app_commands_not_supported = True
    if interaction.guild:
        gid = interaction.guild.id
        app_commands_not_supported = gid not in APP_GUILDS_ID

    if app_commands_not_supported:
        supported_guilds = "\n".join(f" - {bot.get_guild(sgid).name}" for sgid in APP_GUILDS_ID)

        second = membed(
            "Commands are **not** available here:\n"
            "- Slash commands are only supported in these servers:\n"
            f"{supported_guilds}\n"
            "- Text commands are supported everywhere except DMs.\n\n"
            "This was done to prevent hidden abuse.\n"
            "You may contact the developers to request another guild to be added."
        )
        return await interaction.response.send_message(embed=second, ephemeral=True)
    return app_commands_not_supported


@bot.tree.command(name='help', description='The help command for c2c. Shows help for different categories.')
async def help_command_category(interaction: Interaction):
    
    value = await do_guild_checks(interaction)
    if value is None:
        return

    embed = Embed(
        title="Help for c2c", 
        colour=0xB8B9C9,
        description=(
            "**For your reference:**\n"
            "- This does not display uncategorized commands.\n"
            "- The prefix for this bot is `>` (for text commands)\n"
            "- Not all categories are accessible to everyone, check the details prior\n\n"
        )
    )

    help_view = Select()
    await interaction.response.send_message(embed=embed, view=help_view, ephemeral=True)
    help_view.message = await interaction.original_response()


async def main():
    try:
        setup_logging(level=INFO)

        load_dotenv()
        TOKEN = environ.get("BOT_TOKEN")
        bot.WEBHOOK_URL = environ.get("WEBHOOK_URL")
        bot.GITHUB_TOKEN = environ.get("GITHUB_TOKEN")
        bot.JEYY_API_KEY = environ.get("JEYY_API_KEY")
        bot.NINJAS_API_KEY = environ.get("API_KEY")
        bot.WAIFU_API_KEY = environ.get("WAIFU_API_KEY")
        bot.GOOGLE_CUSTOM_SEARCH_API_KEY = environ.get("GOOGLE_CUSTOM_SEARCH_API_KEY")
        bot.GOOGLE_CUSTOM_SEARCH_ENGINE = environ.get("GOOGLE_CUSTOM_SEARCH_ENGINE")

        await bot.start(TOKEN)
    finally:
        await bot.close()


run(main())
