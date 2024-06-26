from __future__ import annotations

from os import environ
from asyncio import run
from pathlib import Path
from sys import version
from traceback import format_exception
from aiohttp import ClientSession, DummyCookieJar, TCPConnector

from logging import (
    INFO, 
    FileHandler, 
    error as log_error, 
    info as log_info
)

from typing import (
    Any,
    Dict,
    List,
    Literal,
    Optional,
    TYPE_CHECKING
)

from discord import (
    AllowedMentions,
    app_commands,
    AppCommandType,
    Embed,
    Interaction,
    Intents,
    Object,
    SelectOption,
    Status,
    ui,
    utils
)

from dotenv import load_dotenv
from asqlite import create_pool
from discord.ext import commands
from discord.utils import setup_logging

from cogs.core.helpers import membed
from cogs.core.paginator import RefreshSelectPagination


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
        guild: Optional[Snowflake | int] = None,
    ) -> Optional[app_commands.AppCommand] | Any:
        
        bot_app_commands = self._global_app_commands
        if guild:
            guild_id = guild.id if not isinstance(guild, int) else guild
            guild_commands = self._guild_app_commands.get(guild_id, {})
            if not guild_commands and self.fallback_to_global:
                bot_app_commands = self._global_app_commands
            else:
                bot_app_commands = guild_commands

        for cmd_name, cmd in bot_app_commands.items():
            if any(name in qualified_name for name in cmd_name.split()):
                return cmd

        return None

    def get_app_command(
        self, 
        value: str | int,
        guild: Optional[Snowflake | int] = None
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
    def _unpack_app_commands(bot_app_cmds: List[app_commands.AppCommand]) -> AppCommandStore:
        ret: AppCommandStore = {}

        def unpack_options(options: List[app_commands.AppCommand | app_commands.AppCommandGroup | app_commands.Argument]) -> None:
            for option in options:
                if isinstance(option, app_commands.AppCommandGroup):
                    ret[option.qualified_name] = option
                    unpack_options(option.options)

        for command in bot_app_cmds:
            ret[command.name] = command
            unpack_options(command.options)

        return ret

    async def _update_cache(
        self, 
        bot_app_cmds: List[app_commands.AppCommand], 
        guild: Optional[Snowflake | int] = None
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
            self._guild_app_commands[_guild.id] = self._unpack_app_commands(bot_app_cmds)
        else:
            self._global_app_commands = self._unpack_app_commands(bot_app_cmds)

    async def fetch_command(self, command_id: int, /, *, guild: Optional[Snowflake] = None) -> app_commands.AppCommand:
        res = await super().fetch_command(command_id, guild=guild)
        await self._update_cache([res], guild=guild)
        return res

    async def fetch_commands(
        self, 
        *, 
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
        
        super().clear_commands(guild=guild, type=command_type)
        if clear_app_commands_cache:
            self.clear_app_commands_cache(guild=guild)

    async def sync(self, *, guild: Optional[Snowflake] = None) -> List[app_commands.AppCommand]:
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
        self.fetched_tree = False
        self.time_launch = None

    def log_exception(self, error):
        formatted_traceback = ''.join(format_exception(type(error), error, error.__traceback__))
        log_error(formatted_traceback)

    async def yield_app_commands(self) -> None:
        """Fetch app commands via HTTP when they're not already in the tree."""

        if self.fetched_tree:
            return

        await self.tree.fetch_commands(guild=None)
        self.fetched_tree = True

    async def close(self):
        await self.pool.close()
        await self.session.close()
        await super().close()

    async def setup_hook(self):

        for file in Path("cogs").glob("**/*.py"):
            if "core" in file.parts:
                continue

            *tree, _ = file.parts
            try:
                await self.load_extension(f"{".".join(tree)}.{file.stem}")
            except Exception as e:
                self.log_exception(e)
                await super().close()

        self.pool = await create_pool("C:\\Users\\georg\\Documents\\c2c\\database\\economy.db")

        self.time_launch = utils.utcnow()
        self.session = ClientSession(
            connector=TCPConnector(limit=30, loop=self.loop, limit_per_host=5), 
            cookie_jar=DummyCookieJar(loop=self.loop)
        )


intents = Intents(
    emojis_and_stickers=True,
    guild_messages=True,
    guilds=True,
    members=True,
    voice_states=True
)


bot = C2C(
    allowed_mentions=AllowedMentions.none(),
    case_insensitive=True,
    command_prefix=commands.when_mentioned,
    help_command=None,
    intents=intents,
    max_messages=None,
    max_ratelimit_timeout=30.0,
    owner_ids={992152414566232139, 546086191414509599},
    status=Status.idle,
    strip_after_prefix=True,
    tree_cls=MyCommandTree,
)


cogs = {
    "admin", 
    "ctx_events", 
    "economy", 
    "miscellaneous", 
    "moderation", 
    "music", 
    "slash_events", 
    "tags",
    "tempvoice"
}

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


def generic_loop_with_subcommand(all_cmds: dict, cmd_formatter: list, guild_id) -> set:

    for (cmd, cmd_details) in all_cmds.items():

        if cmd_details[-1] == 'txt':
            cmd_formatter.append(f"- [`{HelpDropdown.prefix}{cmd}`](https://youtu.be/dQw4w9WgXcQ) \U00002014 {cmd_details[0]}")
            continue
        
        command_manage = bot.tree.get_app_command(cmd, guild=Object(id=guild_id))
        if not isinstance(command_manage, app_commands.AppCommand):
            continue

        contains_subcommands = False
        for option in command_manage.options:
            if isinstance(option, app_commands.AppCommandGroup):
                contains_subcommands = True
                cmd_formatter.append(f"- {option.mention} \U00002014 {option.description}")

        if contains_subcommands:
            continue
        cmd_formatter.append(f"- {command_manage.mention} \U00002014 {command_manage.description}")

    return cmd_formatter


def get_cog_name(*, shorthand: str) -> str:
    # Match the shortened name with the full cog name
    matches = [cog for cog in cogs if shorthand.lower() in cog]
    if len(matches) >= 1:
        return matches[0]
    return None


class HelpDropdown(ui.Select):
    prefix = "@me "
    colour_mapping = {
        "Owner": (0x5BAAEF, "https://cdn.discordapp.com/icons/592654230112698378/1a4fed4eca3d81da620a662a8b383c5b.png?size=512"),
        "Moderation": (0xF70E73, "https://emoji.discadia.com/emojis/74e65408-2adb-46dc-86a7-363f3096b6b2.PNG"),
        "Tags": (0x9EE1FF, "https://i.imgur.com/uHb7xhc.png"),
        "Utility": (0x0FFF87, "https://i.imgur.com/YHBLgVx.png"),
        "Economy": (0xD0C383, "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c7/Robux_2019_Logo_gold.svg/200px-Robux_2019_Logo_gold.svg.png"),
        "Music": (0x6953E0, "https://i.imgur.com/nFZTMFl.png"),
        "TempVoice": (0x821743, "https://i.imgur.com/b8u1MQj.png")
    }

    def __init__(self, selected_option: str) -> None:
        
        defined_options = [
            SelectOption(
                label='Owner', 
                description='Debugging facilities for developers.', 
                emoji='<:ownerSTAR:1221502316478464050>',
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

        for option in defined_options:
            if option.value == selected_option:
                option.default = True
                break
        
        super().__init__(options=defined_options, row=0)

    @staticmethod
    def format_pages(chosen_help_category: str, guild_id: int) -> list:
        pages = []

        embed = Embed(title=f"Help: {chosen_help_category}")
        embed.colour, thumb_url = HelpDropdown.colour_mapping[chosen_help_category]
        embed.set_thumbnail(url=thumb_url)

        if chosen_help_category == 'Owner':

            all_cmds = fill_up_commands(chosen_help_category)
            for (cmd, cmd_details) in all_cmds.items():

                if cmd_details[-1] == 'txt':
                    pages.append(f"- [`{HelpDropdown.prefix}{cmd}`](https://youtu.be/dQw4w9WgXcQ) \U00002014 {cmd_details[0]}")
                    continue

                command_manage = bot.tree.get_app_command(cmd, guild=Object(id=guild_id))
                pages.append(f"- **{command_manage.mention}** \U00002014 {command_manage.description}")

        elif chosen_help_category == 'Moderation':

            all_cmds = fill_up_commands(chosen_help_category)
            all_cmds.update({"role": "sla"})

            pages = generic_loop_with_subcommand(all_cmds, pages, guild_id)

        elif chosen_help_category == 'Tags':

            all_cmds = bot.get_cog(chosen_help_category).get_commands()[0]
            for i, cmd in enumerate(all_cmds.commands, start=1):
                pages.append(f"- [`{HelpDropdown.prefix}{cmd}`](https://youtu.be/dQw4w9WgXcQ) \U00002014 {cmd.description}")

        elif chosen_help_category in {"Utility", "TempVoice"}:

            all_cmds = fill_up_commands(chosen_help_category)      
            pages = generic_loop_with_subcommand(all_cmds, pages, guild_id)

        elif chosen_help_category == 'Economy':

            all_cmds = fill_up_commands(chosen_help_category)
            pages = generic_loop_with_subcommand(all_cmds, pages, guild_id)

        else:
            all_cmds = return_txt_cmds_first({}, chosen_help_category)

            for (cmd, cmd_details) in all_cmds.items():
                pages.append(f"- [`{HelpDropdown.prefix}{cmd}`](https://youtu.be/dQw4w9WgXcQ) \U00002014 {cmd_details[0]}")        
        
        return pages

    async def callback(self, interaction: Interaction) -> None:

        chosen_category: str = self.values[0]

        for option in self.options:
            option.default = option.value == chosen_category

        self.view: RefreshSelectPagination

        pages = HelpDropdown.format_pages(
            chosen_help_category=chosen_category, 
            guild_id=interaction.guild.id
        )

        embed = Embed(title=f"Help: {chosen_category}")
        embed.colour, thumb_url = HelpDropdown.colour_mapping[chosen_category]
        embed.set_thumbnail(url=thumb_url)

        self.view.index = 1
        async def get_page_part(page: int):

            length = 6
            offset = (page - 1) * length
            embed.description = "\n".join(pages[offset:offset + length])

            n = self.view.compute_total_pages(len(pages), length)
            embed.set_footer(text=f"Page {page} of {n}")
            return embed, n
        
        self.view.get_page = get_page_part
        await self.view.edit_page(interaction)


@app_commands.describe(category="The category you want help on.")
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.allowed_installs(guilds=True, users=True)
@bot.tree.command(name="help", description="Shows help for different categories")
async def help_command_category(interaction: Interaction, category: classnames) -> None:
    value = await do_guild_checks(interaction)
    if not value:
        return

    await bot.yield_app_commands()

    pages = HelpDropdown.format_pages(
        chosen_help_category=category, 
        guild_id=interaction.guild.id
    )

    embed = Embed(title=f"Help: {category}")
    embed.colour, thumb_url = HelpDropdown.colour_mapping[category]
    embed.set_thumbnail(url=thumb_url)

    async def get_page_part(page: int):

        length = 6
        offset = (page - 1) * length
        embed.description = "\n".join(pages[offset:offset + length])

        n = paginator.compute_total_pages(len(pages), length)
        embed.set_footer(text=f"Page {page} of {n}")
        return embed, n

    select_menu = HelpDropdown(selected_option=category)
    paginator = RefreshSelectPagination(
        interaction, 
        select=select_menu, 
        get_page=get_page_part
    )

    await paginator.navigate(ephemeral=True)


@bot.command(name="test")
async def testit(ctx: commands.Context) -> None:
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


@commands.is_owner()
@bot.command(name='reload', aliases=("rl",)) 
async def reload_cog(ctx: commands.Context, cog_input: str) -> None:

    cog_name = get_cog_name(shorthand=cog_input)
    if cog_name is None:
        return await ctx.reply(embed=membed("This extension does not exist."))

    embed = membed()
    try:
        await bot.reload_extension(f"cogs.{cog_name}")
        embed.add_field(name="Reloaded", value=f"cogs/{cog_name}.py")
    except commands.ExtensionNotLoaded:
        embed.description = "That extension has not been loaded in yet."
    except commands.NoEntryPointError:
        embed.description = "The extension does not have a setup function."
    except commands.ExtensionFailed as e:
        bot.log_exception(e)
        embed.description = "The extension failed to load. See the logs for traceback."
    finally:
        await ctx.reply(embed=embed)


@commands.is_owner()
@bot.command(name='unload', aliases=("ul",))
async def unload_cog(ctx: commands.Context, cog_input: str) -> None:

    cog_name = get_cog_name(shorthand=cog_input)
    if cog_name is None:
        return await ctx.reply(embed=membed("This extension does not exist."))
    
    embed = membed()
    try:
        await bot.unload_extension(f"cogs.{cog_name}")
        embed.add_field(name="Unloaded", value=f"cogs/{cog_name}.py")
    except commands.ExtensionNotLoaded:
        embed.description = "That extension has not been loaded in yet."
    
    await ctx.reply(embed=embed)


@commands.is_owner()
@bot.command(name='load', aliases=("l",))
async def load_cog(ctx: commands.Context, cog_input: str) -> None:
    
    cog_name = get_cog_name(shorthand=cog_input)
    if cog_name is None:
        return await ctx.reply(embed=membed("This extension does not exist."))
    
    embed = membed()
    try:
        await bot.load_extension(f"cogs.{cog_name}")
        embed.add_field(name="Loaded", value=f"cogs/{cog_name}.py")
    except commands.ExtensionAlreadyLoaded:
        embed.description = "That extension is already loaded."
    except commands.NoEntryPointError:
        embed.description = "The extension does not have a setup function."
    except commands.ExtensionFailed as e:
        bot.log_exception(e)
        embed.description = "The extension failed to load. See the logs for traceback."

    await ctx.reply(embed=embed)


async def do_guild_checks(interaction: Interaction) -> bool | None:
    if interaction.guild is None:
        second = membed(
            "Some commands aren't available here.\n"
            "Since you're not using this in a guild, you won't be able to use core functionality of the bot.\n"
            "This includes the economy system, (temporary) role and voice management.\n"
            "It is recommended to use this bot in a guild.\n"
            "Some slash commands are available here, but no text (aka prefix) commands."
        )
        return await interaction.response.send_message(embed=second, ephemeral=True)
    return True


async def main():

    setup_logging(
        level=INFO,
        handler=FileHandler(filename='discord.log', encoding='utf-8', mode='w')
    )
    log_info(version)
    load_dotenv()
    
    TOKEN = environ.get("BOT_TOKEN")
    bot.WEBHOOK_URL = environ.get("WEBHOOK_URL")
    bot.GITHUB_TOKEN = environ.get("GITHUB_TOKEN")
    bot.JEYY_API_KEY = environ.get("JEYY_API_KEY")
    bot.NINJAS_API_KEY = environ.get("NINJAS_API_KEY")
    bot.GOOGLE_CUSTOM_SEARCH_API_KEY = environ.get("GOOGLE_CUSTOM_SEARCH_API_KEY")
    bot.GOOGLE_CUSTOM_SEARCH_ENGINE = environ.get("GOOGLE_CUSTOM_SEARCH_ENGINE")

    await bot.start(TOKEN)


run(main())
