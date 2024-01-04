from __future__ import annotations
from dotenv import load_dotenv
from datetime import datetime
from os import listdir, environ
from sys import version
from discord.ext import commands
from typing import Literal
from collections import deque
from discord.utils import setup_logging
from discord import app_commands, Object, ui, Intents, Status, Embed, Interaction, CustomActivity
from discord import RawReactionActionEvent, AppCommandType, SelectOption, Colour, File, Webhook
from asyncio import run, TimeoutError as asyncio_TimeoutError
from typing import Dict, Optional, TYPE_CHECKING, Union, List
from aiohttp import ClientSession
from asqlite import create_pool
from logging import INFO as LOGGING_INFO


if TYPE_CHECKING:
    from discord.abc import Snowflake

    AppCommandStore = Dict[str, app_commands.AppCommand]  # name: AppCommand


class CustomContext(commands.Context):
    async def prompt(
            self,
            message: str,
            *,
            timeout=30.0,
            delete_after=False
    ) -> Optional[bool]:
        """Prompt the author with an interactive confirmation message.

        This method will send the `message` content, and wait for max `timeout` seconds
        (default is `30`) for the author to react to the message.

        If `delete_after` is `True`, the message will be deleted before returning a
        True, False, or None indicating whether the author confirmed, denied,
        or didn't interact with the message.
        """
        msg = await self.send(message)

        for reaction in ('\U00002705', '\U0000274c'):
            await msg.add_reaction(reaction)

        confirmation = None

        # This function is a closure because it is defined inside of another
        # function. This allows the function to access the self and msg
        # variables defined above.

        def check(payload: RawReactionActionEvent):
            # 'nonlocal' works almost like 'global' except for functions inside of
            # functions. This means that when 'confirmation' is changed, that will
            # apply to the variable above
            nonlocal confirmation

            if payload.message_id != msg.id or payload.user_id != self.author.id:
                return False

            emoji = str(payload.emoji)

            if emoji == '✅':
                confirmation = True
                return True

            elif emoji == '❌':
                confirmation = False
                return True

            # This means that it was neither of the two emojis added, so the author
            # added some other unrelated reaction.
            return False

        try:
            await self.bot.wait_for('raw_reaction_add', check=check, timeout=timeout)
        except asyncio_TimeoutError:
            # The 'confirmation' variable is still None in this case
            pass

        if delete_after:
            await msg.delete()
        return confirmation


class MyCommandTree(app_commands.CommandTree):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._global_app_commands: AppCommandStore = {}
        # guild_id: AppCommandStore
        self._guild_app_commands: Dict[int, AppCommandStore] = {}

    def find_app_command_by_names(
            self,
            *qualified_name: str,
            guild: Optional[Union[Snowflake, int]] = None,
    ) -> Optional[app_commands.AppCommand]:
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
            guild: Optional[Union[Snowflake, int]] = None,
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
                    ret[option.qualified_name] = option  # type: ignore
                    unpack_options(option.options)  # type: ignore

        for command in commandsr:
            ret[command.name] = command
            unpack_options(command.options)  # type: ignore

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

    async def fetch_commands(self, *, guild: Optional[Snowflake] = None) -> List[app_commands.AppCommand]:
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
        # Forward all arguments, and keyword-only arguments to commands.Bot
        super().__init__(*args, **kwargs)

        # Custom bot attributes can be set here.
        self.remove_command('help')

        # Database and HTTP Connections
        self.pool_connection = None
        self.session = None
        self.games = dict()

        # Misc
        self.time_launch = None

    async def get_context(self, message, *, cls=CustomContext):  # From the above codeblock
        return await super().get_context(message, cls=cls)

    async def setup_hook(self):

        # Confirmation that the bot has logged in
        print(f"\nwe're in.\n")

        # Create a pool connection for database queries
        self.pool_connection = await create_pool('C:\\Users\\georg\\PycharmProjects\\c2c\\db-shit\\economy.db')

        # Modify the client variable
        self.time_launch = str(datetime.now().strftime("%j:%H:%M:%S"))

        # Create a aiohttp session once and reuse this throughout the bot.
        self.session = ClientSession()

client = C2C(command_prefix='>', intents=Intents.all(), case_insensitive=True,
             owner_ids={992152414566232139, 546086191414509599},
             activity=CustomActivity(name='Serving cc • /help'),
             status=Status.idle, tree_cls=MyCommandTree)
print(version)


async def load_cogs():
    for filename in listdir('./cogs'):
        if filename.endswith(".py"):
            await client.load_extension(f"cogs.{filename[:-3]}")

def return_txt_cmds_first(command_holder: dict,
                          category: Literal["Economy", "Moderation", "Miscellaneous", "Administrate", "Music"]) -> dict:
    """Displays all the text-based commands that are defined within a cog as a dict. This should always be called first for consistency."""
    the_cog = client.get_cog(category)
    cog_cmds = the_cog.get_commands()
    for cmd in cog_cmds:
        command_holder.update({cmd.name: deque([f'{category}', f'{cmd.description}', 'txt'])})
    return command_holder


def return_interaction_cmds_last(command_holder: dict,
                                 category: Literal["Economy", "Moderation", "Miscellaneous", "Administrate", "Music"]) -> dict:
    """Displays all the app commands and grouped app commands that are defined within a cog as a dict. This should always be called last for consistency."""
    the_cog = client.get_cog(category)
    cog_cmds = the_cog.get_app_commands()

    for cmd in cog_cmds:
        command_holder.update({cmd.name: deque([f'{category}', f'{cmd.description}', 'sla'])})
    return command_holder

async def total_command_count(interaction: Interaction) -> int:
    """Return the total amount of commands detected within the client, including text and slash commands."""
    amount = 0
    lenslash = len(await client.tree.fetch_commands(guild=Object(id=interaction.guild.id)))
    lentxt = len(client.commands)
    amount += (lenslash+lentxt)
    return amount


class SelectMenu(ui.Select):
    def __init__(self):
        optionss = [
            SelectOption(label='Owner', description='commands accessible by the bot owners.',
                                 emoji='<a:e1_butterflyB:1124677894275338301>'),
            SelectOption(label='Moderation',
                                 description='commands accessible by those with further permissions.',
                                 emoji='<a:e1_starR:1124677520038567946>'),
            SelectOption(label='Utility', description='generic commands that may serve useful.',
                                 emoji='<a:e1_starG:1124677658500927488>'),
            SelectOption(label='Economy', description='commands related to the virtual economy.',
                                 emoji='<a:e1_starY:1124677741980176495>'),
            SelectOption(label='Music', description='commands for listening to music on discord.',
                                 emoji='<a:e1_starPur:1125040539943837738>')
        ]
        super().__init__(placeholder="Name of category", options=optionss)

    async def callback(self, interaction: Interaction):

        choice = self.values[0]
        cmd_formatter: set = set()

        total_cmds_rough = await total_command_count(interaction)

        total_cmds_cata = 0

        if choice == 'Owner':

            for option in self.options:
                if option.value == "Owner":
                    option.default = True
                else:
                    option.default = False

            the_dict = {}
            new_dict = return_txt_cmds_first(the_dict, "Administrate")
            all_cmds: dict = return_interaction_cmds_last(new_dict, "Administrate")

            embed = Embed(title='Help: Owner', colour=Colour.from_rgb(91, 170, 239))
            embed.set_image(url='https://media.discordapp.net/attachments/1124994990246985820/1125005648422256692/762082-3602628412.jpg?width=1377&height=701')
            embed.set_footer(text='Got any suggestions for the bot? use the /feedback command '
                                  'to let us know about it.', icon_url=client.user.avatar.url)
            for cmd, cmd_details in all_cmds.items():
                total_cmds_cata += 1
                if cmd_details[-1] == 'txt':
                    cmd_formatter.add(f"\U0000279c [`>{cmd}`](https://youtu.be/dQw4w9WgXcQ) - {cmd_details[1]}")
                else:
                    command_manage = client.tree.get_app_command(cmd, guild=Object(id=829053898333225010)) # type: ignore
                    cmd_formatter.add(f"\U0000279c **{command_manage.mention}** - {cmd_details[1]}")

            embed.add_field(name='About: Owner',
                            value=f'Contains commands that are only able to be utilized by the bot developers, and mostly '
                                  f'contain commands related to debugging and testing new features into the client for later release.\n'
                                  f'__Interesting Stats__\n'
                                  f'- There are **{total_cmds_cata}** commands in this category\n'
                                  f'- Accounts for **{round((total_cmds_cata / total_cmds_rough)*100,ndigits=2)}%** of all commands.\n'
                                  f'- Last modified: <t:1702722548:D> (**<t:1702722548:R>**)\n'
                                  f'- Status: **READY**')

            embed.description = "\n".join(cmd_formatter)

            await interaction.response.edit_message(attachments=[], embed=embed, view=self.view) # type: ignore

        elif choice == 'Moderation':

            for option in self.options:
                if option.value == "Moderation":
                    option.default = True
                else:
                    option.default = False

            the_dict = {}
            new_dict = return_txt_cmds_first(the_dict, choice) # type: ignore
            all_cmdss: dict = return_interaction_cmds_last(new_dict, choice) # type: ignore

            embed = Embed(title='Help: Moderation', colour=Colour.from_rgb(247, 14, 115))
            embed.set_image(url='https://media.discordapp.net/attachments/1124994990246985820/1125041765200703528/pink.jpg?width=1247&height=701')
            embed.set_footer(text='Got any suggestions for the bot? use the /feedback command to let us know about it.', icon_url=client.user.avatar.url)

            for cmd, cmd_details in all_cmdss.items():
                if cmd_details[-1] == 'txt':
                    cmd_formatter.add(f"\U0000279c [`>{cmd}`](https://youtu.be/dQw4w9WgXcQ) - {cmd_details[1]}")
                    total_cmds_cata += 1
                else:
                    command_manage = client.tree.get_app_command(cmd, guild=Object(id=829053898333225010)) # type: ignore
                    cmd_formatter.add(f"\U0000279c **{command_manage.mention}** - {cmd_details[1]}")
                    total_cmds_cata += 1

            embed.add_field(name='About: Mod',
                            value=f'Contains commands that are related to server management and moderation, hence these '
                                  f'commands require invokers to have higher levels of permissions to utilize these.\n'
                                  f'__Interesting Stats__\n'
                                  f'- There are **{total_cmds_cata}** commands in this category\n'
                                  f'- Accounts for **{round((total_cmds_cata / total_cmds_rough) * 100, ndigits=2)}%** of all commands.\n'
                                  f'- Last modified: <t:1698856225:D> (**<t:1698856225:R>**)\n'
                                  f'- Status: **READY**')
            embed.description = "\n".join(cmd_formatter)

            await interaction.response.edit_message(attachments=[], embed=embed, view=self.view) # type: ignore

        elif choice == 'Utility':

            for option in self.options:
                if option.value == "Utility":
                    option.default = True
                else:
                    option.default = False

            the_dict = {}
            new_dict = return_txt_cmds_first(the_dict, "Miscellaneous")
            all_cmdsss: dict = return_interaction_cmds_last(new_dict, "Miscellaneous")

            embed = Embed(title='Help: Utility', colour=Colour.from_rgb(15, 255, 135))
            embed.set_image(url='https://media.discordapp.net/attachments/1124994990246985820/1125009796429520936/wp6063334-2886616470.jpg?width=1168&height=701')
            embed.set_footer(text='Got any suggestions for the bot? use the /feedback command to let us know about it.', icon_url=client.user.avatar.url)

            for cmd, cmd_details in all_cmdsss.items():
                if cmd_details[-1] == 'txt':
                    cmd_formatter.add(f"\U0000279c [`>{cmd}`](https://youtu.be/dQw4w9WgXcQ) - {cmd_details[1]}")
                    total_cmds_cata += 1
                else:
                    command_manage = client.tree.get_app_command(cmd, guild=Object(id=829053898333225010)) # type: ignore
                    cmd_formatter.add(f"\U0000279c **{command_manage.mention}** - {cmd_details[1]}")
                    total_cmds_cata += 1

            embed.add_field(name='About: Utility',
                            value=f'Contains commands that may serve useful to some users, especially to some of the geeks out there.\n'
                                  f'__Interesting Stats__\n'
                                  f'- There are **{total_cmds_cata}** commands in this category\n'
                                  f'- Accounts for **{round((total_cmds_cata / total_cmds_rough) * 100, ndigits=2)}%** of all commands.\n'
                                  f'- Last modified: <t:1702722548:D> (**<t:1702722548:R>**)\n'
                                  f'- Status: **READY**')
            embed.description = "\n".join(cmd_formatter)

            await interaction.response.edit_message(attachments=[], embed=embed, view=self.view) # type: ignore

        elif choice == 'Economy':

            for option in self.options:
                if option.value == "Economy":
                    option.default = True
                else:
                    option.default = False

            embed = Embed(title='Help: Economy', colour=Colour.from_rgb(255, 215, 0))
            embed.set_image(url='https://media.discordapp.net/attachments/1124994990246985820/1125010187812605972/wp6402672.jpg?width=1247&height=701')
            embed.set_footer(text='Got any suggestions for the bot? use the /feedback command to let us know about it.', icon_url=client.user.avatar.url)

            the_dict = {}
            new_dict = return_txt_cmds_first(the_dict, "Economy")
            all_cmdssss: dict = return_interaction_cmds_last(new_dict, "Economy")

            for cmd, cmd_details in all_cmdssss.items():
                if cmd_details[-1] == 'txt':
                    cmd_formatter.add(f"\U0000279c [`>{cmd}`](https://youtu.be/dQw4w9WgXcQ) - {cmd_details[1]}")
                    total_cmds_cata += 1
                else:
                    command_manage = client.tree.get_app_command(cmd, guild=Object(id=829053898333225010)) # type: ignore
                    cmd_formatter.add(
                        f"\U0000279c **{command_manage.mention}** - {cmd_details[1]}")
                    total_cmds_cata += 1

            embed.description = "\n".join(cmd_formatter)
            embed.add_field(name='About: Economy',
                            value=f'Contains commands that can be used by anybody, and relate to the virtual economy system of the client.\n'
                                  f'__Interesting Stats__\n'
                                  f'- There are **{total_cmds_cata}** commands in this category\n'
                                  f'- Accounts for **{round((total_cmds_cata / total_cmds_rough) * 100, ndigits=2)}%** of all commands.\n'
                                  f'- Last modified: <t:1702722548:D> (**<t:1702722548:R>**)\n'
                                  f'- Status: **LOCKED**')

            await interaction.response.edit_message(attachments=[], embed=embed, view=self.view) # type: ignore
        else:
            for option in self.options:
                if option.value == "Music":
                    option.default = True
                else:
                    option.default = False

            embed = Embed(title='Help: Music', colour=Colour.from_rgb(105, 83, 224))
            that_file = File("C:\\Users\\georg\\Downloads\\Media\\wallpaper\\purple-wp.jpg",
                                     filename="image.png")
            embed.set_image(url="attachment://image.png")
            embed.set_footer(text='Got any suggestions for the bot? use the /feedback command to let us know about it.',
                             icon_url=client.user.avatar.url)

            the_dict: dict = {}
            all_cmdssss = return_txt_cmds_first(the_dict, "Music")

            for cmd, cmd_details in all_cmdssss.items():
                cmd_formatter.add(f"\U0000279c [`>{cmd}`](https://youtu.be/dQw4w9WgXcQ) - {cmd_details[1]}")
                total_cmds_cata += 1

            embed.description = "\n".join(cmd_formatter)
            embed.add_field(name='About: Music',
                            value=f'Contains commands that can be used by anybody, related to the music client '
                                  f'and its functions. Use these commands to play music on Discord.\n'
                                  f'__Interesting Stats__\n'
                                  f'- There are **{total_cmds_cata}** commands in this category\n'
                                  f'- Accounts for **{round((total_cmds_cata / total_cmds_rough) * 100, ndigits=2)}%** of all commands.\n'
                                  f'- Last modified: <t:1703857689:D> (**<t:1703857689:R>**)\n'
                                  f'- Status: **READY**')
            await interaction.response.edit_message(attachments=[that_file], embed=embed, view=self.view) # type: ignore


class Select(ui.View):
    def __init__(self):
        super().__init__(timeout=40.0)
        self.add_item(SelectMenu())

    async def on_timeout(self) -> None:
        # Step 2
        for item in self.children:
            item.disabled = True
        # Step 3
        await self.message.edit(view=self) # type: ignore

@client.command(name='confirm')
async def confirm_panel(ctx: CustomContext):
    prompt = await ctx.prompt(f"Are you sure you want to do this?")
    if prompt:
        await ctx.send("You accepted.")
    else:
        await ctx.send("Cancelled operation.")


@client.command(name='dispatch-webhook', aliases=("dww",))
async def dispatch_the_webhook_when(ctx: commands.Context):
    await ctx.message.delete()
    embed = Embed(
        colour=Colour.from_rgb(3, 102, 214),
        title='Changes for 2024 Q1',
    description="Changes that have taken place in the period between January 1 - March 31 are noted here.\n\n"
                "- **Linked Roles**: Integrate your Github account to Discord and claim your linked role "
                "in the 'Linked Roles' tab.\n"
                " - Once claimed, you receive <@&1190772742409158667> and a badge next to your name in most channels.\n"
                "- **Activity Roles**: earn roles by participating regularly in channels.\n"
                " - <@&1190772029830471781> - earnt by sending 50 messages per week.\n"
                " - <@&1190772182591209492> - earnt by sending 150 messages per week.\n"
                "- **New Bots added**: <@491769129318088714> and <@770100332998295572>\n"
                "- **Event Highlights**: A recurring event for New Years Day was added.\n"
                " - Every year this event is created on the 1st Jan.\n"
                "- **Slash Command Changes:** You now only see slash commands that are relevant to you.\n"
                " - Server management related slash commands were removed completley for server members.\n"
                " - More are regularly being detected and removed from the list.\n"
                "- **XP Changes**: It recently became possible to earn XP in bot command channels\n"
                " - Link to announcement: https://discord.com/channels/829053898333225010/1121094935802822768/1166397053329477642.\n"
                "- **Channel Overhaul**: For a more simplistic look, <#1121445944576188517> and <#902138223571116052> were modified.")

    embed.set_footer(icon_url=ctx.guild.icon.url, text="That's all for Q1 2024. Next review due: 30 June 2024.")

    urll = "https://discord.com/api/webhooks/1163132850699247746/dSp0XRiADRL31YLS20W9i66Nq-ePYb-fFqID9UjdgFTuNQIFTtpHvBwmdvt1PcE2j9UM"
    webhook = Webhook.from_url(url=urll, session=client.session)
    thread = await ctx.guild.fetch_channel(1190736866308276394)  # thread id
    rtype = "feature" or "bugfix"
    await webhook.send(f'Patch notes for Q1 2024 / This is mostly a `{rtype}` release', embed=embed,
                       thread=Object(id=thread.id), silent=True)
    await ctx.send(f"Done. The webhook was sent to '{thread.name}' with ID {thread.id}.")


@client.command(name="reqs")
async def requirements_for_cogs(ctx: commands.Context):
    embed = Embed(title="Prerequisites to execute commands",
                  description="There is a set baseline of conditions that must be met for **all** commands in "
                              "order to execute the command. If you do not meet this, you will get this error:\n"
                              "> You have not met a prerequisite before executing this command.\n"
                              "Any other error that is displayed is irrelevant here, and will not resolve the issue.\n\n"
                              "This embed will briefly outline what the prequisites for executing commands are. These "
                              "ultimately depend on what category the command is in, as well as what server you are"
                              " calling it in. Note there are situations where this is not the case (see below).\n"
                              "The prerequisites for the following categories are outlined:\n"
                              "### <a:e1_butterflyB:1124677894275338301> Owner\n"
                              "- You are the bot owner.\n"
                              "- You are calling the command in a server, not a DM.\n"
                              "### <a:e1_starR:1124677520038567946> Moderation\n"
                              "- You have the specific server management permissions.\n"
                              " - The permission required for each command varies, use common sense to figure out.\n"
                              " - **Only applies to** `>close`**:** you could also own the thread to execute it.\n"
                              "- You are calling the command in a server, not a DM.\n"
                              "### <a:e1_starG:1124677658500927488> Utility\n"
                              "- You are calling the command in a server, not a DM.\n"
                              "- **Only applies to** `/kona`: You must call the command in an NSFW channel.\n"
                              "- **Only applies to** `>inviter` You have the `Create Invite` permission.\n"
                              "### <a:e1_starY:1124677741980176495> Economy\n"
                              "- **Only applies to [cc](https://discord.gg/W3DKAbpJ5E):** "
                              "You have the <@&1168204249096785980> role.\n"
                              "### <a:e1_starPur:1125040539943837738> Music\n"
                              "- **Only applies to [cc](https://discord.gg/W3DKAbpJ5E):** "
                              "You have the <@&990900517301522432> role.",
                  colour=Colour.dark_embed())
    embed.set_footer(text="These conditions only outline what should be met. Not the other way around.",
                     icon_url=client.user.avatar.url)

    await ctx.send(embed=embed)


@client.tree.command(name='help', description='help command for c2c, outlines all categories of commands.',
                     guilds=[Object(id=829053898333225010), Object(id=780397076273954886)])
async def help_command(interaction: Interaction):
    embed = Embed(title='Help Menu for c2c',
                  description=f'```fix\n[Patch #26]\n'
                              f'- More commands interacting with API Interfaces\n'
                              f'- Major performance improvements\n'
                              f'- Databases have fully replaced json```\n'
                              f'Use this dropdown to find a command based on its category. '
                              f'A few things to note:\n'
                              f'- This help command does not display uncategorized commands.\n'
                              f'- The prefix for this bot is `>` (for text commands)\n'
                              f'- Not all categories are accessible to everyone, check the details prior.',
                  colour=Colour.from_rgb(138, 175, 255))
    embed.add_field(name='Feedback System',
                    value=f'We have a feedback system! Use the </feedback:1179817617767268353> command to help '
                          f'improve this experience.')
    my_view = Select()
    await interaction.response.send_message(embed=embed, view=my_view, ephemeral=True) # type: ignore
    my_view.message = await interaction.original_response()


async def main():
    await load_cogs()
    try:
        setup_logging(level=LOGGING_INFO)

        load_dotenv()
        token = environ.get("BOT_TOKEN")
        client.NINJAS_API_KEY = environ.get("API_KEY")
        client.TATSU_API_KEY = environ.get("TATSU_API_KEY")

        await client.start(token)
    finally:
        await client.close()
run(main())
