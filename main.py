import datetime
import os
import typing
import sys
from discord.ext import commands
from discord.ext.commands import Context, Greedy
import discord
from typing import Optional, Literal
import asyncio
from discord import FFmpegPCMAudio, app_commands
import random
from datetime import datetime
import time

intents = discord.Intents.all()
intents.message_content = True
snipe_message_author = None
snipe_message_content = None
snipe_message_id = None

client = commands.Bot(command_prefix='>', intents=intents, case_insensitive=True,
                      owner_ids={992152414566232139, 546086191414509599},
                      activity=discord.Activity(type=discord.ActivityType.competing, name='EK2023'),
                      status=discord.Status.dnd)

pRange = random.randint(1, 255)
possible_color = discord.Color.from_rgb(pRange, pRange, pRange)
number = random.randint(1, 1000)
client.remove_command('help')
print(sys.version)


# Search for a specific term in this project using Ctrl + Shift + F


async def load():
    for filename in os.listdir('./cogs'):
        if filename.endswith(".py"):
            await client.load_extension(f"cogs.{filename[:-3]}")


async def play_source(voice_client):
    source = FFmpegPCMAudio("battlet.mp3", executable='ffmpeg')
    voice_client.play(source, after=lambda e: print('Player error: %s' % e) if e else client.loop.create_task(
        play_source(voice_client)))


@client.event
async def on_ready():
    global new1
    print(f'connected.')
    s1 = datetime.now()
    client.tree.copy_global_to(guild=discord.Object(id=829053898333225010))
    await client.tree.sync(guild=discord.Object(id=829053898333225010))
    new1 = str(s1.strftime("%j:%H:%M:%S"))

"""
HOW TO RUN ON PYTHON 3.11:
Type the following:
py -3.11 main.py
thats it!
"""


@client.event
async def on_message(message):
    emoji = discord.utils.get(client.emojis, name='KarenLaugh')
    if message.author.id == client.user:
        return
    if client.user.mentioned_in(message):
        await message.channel.send("<a:e1_waves:1125055723999592551> try using "
                                   "</help:1124814156659437650> to see a list of my commands.")
    await client.process_commands(message)


def is_owner(interaction: discord.Interaction):
    if interaction.user.id == interaction.guild.owner_id:
        return True
    return False


client.sniped_messages = {}


@client.event
async def on_message_delete(message):
    if message.attachments:
        bob = message.attachments[0]
        client.sniped_messages[message.guild.id] = (bob.proxy_url, message.content,
                                                    message.author, message.channel.name, message.created_at)
    else:
        client.sniped_messages[message.guild.id] = (message.content, message.author,
                                                    message.channel.name, message.created_at)


@commands.is_owner()
@client.command(name='snipei')
async def snipe(ctx):
    global bob_proxy_url
    try:
        bob_proxy_url, contents, author, channel_name, timerr = client.sniped_messages[ctx.guild.id]
    except:
        contents, author, channel_name, timerr = client.sniped_messages[ctx.guild.id]
    try:
        embed = discord.Embed(description=contents, color=discord.Color.purple(), timestamp=timerr)
        embed.set_image(url=bob_proxy_url)
        embed.set_author(name=f"{author.name}#{author.discriminator}", icon_url=author.avatar.url)
        embed.set_footer(text=f"Deleted in : #{channel_name}")
        await ctx.channel.send(embed=embed)
    except:
        embed = discord.Embed(description=contents, color=discord.Color.purple(), timestamp=timerr)
        embed.set_author(name=f"{author.name}#{author.discriminator}", icon_url=author.avatar.url)
        embed.set_footer(text=f"Deleted in : #{channel_name}")
        await ctx.channel.send(embed=embed)


@client.tree.command(name='pin', description='pin a specified message in any channel.',
                     guild=discord.Object(id=829053898333225010))
@app_commands.check(is_owner)
@app_commands.describe(message_id='the ID of the message to be pinned')
async def pin_it(interaction: discord.Interaction, message_id: str):
    a = await client.fetch_guild(interaction.guild.id)
    b = await a.fetch_channel(interaction.channel.id)
    c = await b.fetch_message(int(message_id))
    await c.pin(reason=f'Requested by {interaction.user.name}.')
    await interaction.response.send_message(content="The requested message has been pinned successfully.", ephemeral=True, delete_after=3.0)


@client.tree.command(name='react', description='Forces the client to react to a message with any reaction requested.',
                     guild=discord.Object(id=829053898333225010))
@app_commands.check(is_owner)
@app_commands.describe(message_id='the ID of the message to be pinned (must be in the invocation channel)', emoji='The custom or unicode emoji to choose from (NOT THE NAME)')
async def react(interaction: discord.Interaction, message_id: str, emoji: str):
    a = await client.fetch_guild(interaction.guild.id)
    b = await a.fetch_channel(interaction.channel.id)
    c = await b.fetch_message(int(message_id))
    await c.add_reaction(emoji)
    await interaction.response.send_message(content='the emoji has been added to the message', ephemeral=True, delete_after=3.0)


class FeedbackModal(discord.ui.Modal, title='Submit feedback'):
    fb_title = discord.ui.TextInput(
        style=discord.TextStyle.short,
        label="Title",
        required=False,
        placeholder="Give your feedback a title.."
    )

    message = discord.ui.TextInput(
        style=discord.TextStyle.long,
        label='Description',
        required=True,
        placeholder="Provide the feedback here."
    )

    async def on_submit(self, interaction: discord.Interaction):
        channel = interaction.guild.get_channel(1122902104802070572)
        embed = discord.Embed(title='New Feedback',
                              description=self.message.value, colour=discord.Color.magenta())

        embed.set_author(name=interaction.user)
        await channel.send(embed=embed)
        await interaction.response.send_message(f"your response has been submitted, {interaction.user}", ephemeral=True)

    async def on_error(self, interaction: discord.Interaction, error):
        await interaction.response.send_message(f"an error occured.")
        await interaction.delete_original_response()


class Reason(typing.NamedTuple):
    reason: str


class Transformer(app_commands.Transformer):
    async def transform(self, interaction: discord.Interaction, value: str) -> Reason:
        return Reason(reason=f"**{value}**")


class SimpleView(discord.ui.View):

    foo: bool = None

    async def disable_all_items(self):
        for item in self.children:
            item.disabled = True
        await self.message.edit(view=self)

    async def on_timeout(self) -> None:
        await self.disable_all_items()
        await self.message.channel.send("timed out.")

    @discord.ui.button(label='1', style=discord.ButtonStyle.blurple)
    async def hello(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("world")
        self.foo = True
        self.stop()

    @discord.ui.button(label='2', style=discord.ButtonStyle.grey)
    async def hello2(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("world")
        self.foo = False
        self.stop()


class SelectMenu(discord.ui.Select):
    def __init__(self):
        optionss = [
            discord.SelectOption(label='Owner', description='Commands only accessible by the Bot Owner.',
                                 emoji='<a:e1_butterflyB:1124677894275338301>'),
            discord.SelectOption(label='Moderation',
                                 description='Commands accessible by those with further permissions.',
                                 emoji='<a:e1_starR:1124677520038567946>'),
            discord.SelectOption(label='Utility', description='Generic useful commands for ease of access.',
                                 emoji='<a:e1_starG:1124677658500927488>'),
            discord.SelectOption(label='Economy', description='Commands related to the Economy system.',
                                 emoji='<a:e1_starY:1124677741980176495>')
        ]
        super().__init__(placeholder="Name of category", options=optionss)

    async def callback(self, interaction: discord.Interaction):
        choice = self.values[0]
        if choice == 'Owner':
            embed = discord.Embed(title='Help: Owner',
                                  description='These are commands only accessible by <@992152414566232139> and <@546086191414509599>. Any other user attempting to use'
                                              ' the command will raise [Forbidden](https://discordpy.readthedocs.io/en/v2.3.1/api.html#discord.Forbidden) and checks will fail.\n\n'
                                              '`>sync` - synchronizes all slash commands to the current guild. Parameters are optional.\n'
                                              '`>snipei` - fetches any image that has been deleted recently in a channel.\n'
                                              '</uptime:1125126993923547288> - returns the amount of time the client has been online for (in HH:MM:SS)\n'
                                              '</pin:1125098970914488411> - pins a message to the invocation channel. Requires the message ID.\n'
                                              '</react:1125111517512208595> - the client reacts to a given message. Requires the message ID.\n'
                                              '</edit:1125126993923547289> - edits a given message sent by the client. Requires the message ID.\n'
                                              '</button:1125331114274345006> - displays a button menu.\n'
                                              '</unload:1125441064917020683> - unloads a cog from the bot, removing its functionality.\n'
                                              '</load:1125441064917020684> - loads a cog into the bot, adding its functionality.\n'
                                              '</reload:1125441064917020686> - reloads a cog into the bot, reloading its functionality.\n'
                                              '`>eval` - evaluates arbitary code.\n'
                                              '`>say` - repeats what you typed\n'
                                              '</repeat:1122922256276934746> - (same as `>say`) repeats what you typed.\n'
                                              '</generate:1125410667898351666> - generates a given amount of money to the author.',
                                  colour=discord.Colour.from_rgb(91, 170, 239))
            embed.set_image(url='https://media.discordapp.net/attachments/1124994990246985820/1125005648422256692/762082-3602628412.jpg?width=1377&height=701')
            embed.set_footer(text='got any suggestions for the bot? use the /feedback command to let us know about it.', icon_url=client.user.avatar.url)
            await interaction.response.edit_message(embed=embed)
        if choice == 'Moderation':
            embed = discord.Embed(title='Help: Moderation',
                                  description="These commands are accessible by any user with moderator permissions, such as `manage_messages` and `kick_users`\n\n"
                                              "`>cc` - creates a named channel.\n"
                                              "`>rc` - removes a named channel\n"
                                              "</kick:1125441064917020687> - kicks a mentioned user.\n"
                                              "</ban:1125441064917020688> - bans a mentioned user.\n"
                                              "`>setdelay` - sets a delay (slowmode) to which users can send messages.\n"
                                              "</purge:1125441064917020689> - bulk delete a given amount of messages, excluding pinned messages.",
                                  colour=discord.Colour.from_rgb(247, 14, 115))
            embed.set_image(url='https://media.discordapp.net/attachments/1124994990246985820/1125041765200703528/pink.jpg?width=1247&height=701')
            embed.set_footer(text='got any suggestions for the bot? use the /feedback command to let us know about it.', icon_url=client.user.avatar.url)
            await interaction.response.edit_message(embed=embed)
        if choice == 'Utility':
            embed = discord.Embed(title='Help: Utility',
                                  description="These are commands that can be used by anybody, and can be fun or useful in general.\n\n"
                                              "</ping:1054011107695677450> - returns the delay before a transfer of data begins.\n"
                                              "</com:1125433087715717192> - returns the most common letters in a word.\n"
                                              "</charinfo:1125433087715717193> - shows unicode information about any given character.\n"
                                              "</tn:1125126993923547290> - returns the time now in a given format of choice.\n"
                                              "</feedback:1122906134269927595> - used to send feedback to the client developers about the bot.",
                                  colour=discord.Colour.from_rgb(15, 255, 135))
            embed.add_field(name="But wait, there's more!",
                            value="**Context menu** commands can be used. This can be done by right clicking any message and then clicking/tapping `Apps` and then clicking"
                                  " any command with my avatar on it!\n\n"
                                  "`Report User` - this reports the given user's message directly to the developers of the client only for them to look into. "
                                  "There will be punishments for misuse of this command!")
            embed.set_image(url='https://media.discordapp.net/attachments/1124994990246985820/1125009796429520936/wp6063334-2886616470.jpg?width=1168&height=701')
            embed.set_footer(text='got any suggestions for the bot? use the /feedback command to let us know about it.', icon_url=client.user.avatar.url)
            await interaction.response.edit_message(embed=embed)
        if choice == 'Economy':
            embed = discord.Embed(title='Help: Economy',
                                  description="These are commands that can be used by anybody, and relate to the Economy system of the client.\n\n"
                                              "</balance:1125331114274345001> - returns your current balance, along with your current job.\n"
                                              "</find_balance:1125331114274345002> - returns a specific user's balance. Requires the user's ID.\n"
                                              "</register:1125331114274345003> - register into the monetary system\n"
                                              "</give:1125331114274345004> - gives an amount of money to someone else, who must be registered. Requires the receiver to be mentioned.\n"
                                              "</rob:1125331114274345005> - robs someone else, who must be registered. Requires mentioning the person to be robbed.\n"
                                              "</bet:1125410667898351667> - bet your money on a gamble to win or lose coins.",
                                  colour=discord.Colour.from_rgb(255, 215, 0))
            embed.set_image(url='https://media.discordapp.net/attachments/1124994990246985820/1125010187812605972/wp6402672.jpg?width=1247&height=701')
            embed.set_footer(text='got any suggestions for the bot? use the /feedback command to let us know about it.', icon_url=client.user.avatar.url)
            await interaction.response.edit_message(embed=embed)


class Select(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(SelectMenu())


@client.tree.command(name='feedback', description='Send feedback to the client developers regarding the bot.')
async def feedback(interaction: discord.Interaction):
    feedback_modal = FeedbackModal()
    feedback_modal_user = interaction.user
    await interaction.response.send_modal(feedback_modal)


@client.tree.command(name='uptime', description='Returns the time the bot has been active for (in HH:MM:SS)',
                     guild=discord.Object(id=829053898333225010))
@app_commands.check(is_owner)
async def uptime(interaction: discord.Interaction):
    """Returns the time the bot has been online for (in HH:MM:SS)"""
    s2 = datetime.now()
    new2 = str(s2.strftime("%j:%H:%M:%S"))
    FMT = '%j:%H:%M:%S'
    tdelta = datetime.strptime(new2, FMT) - datetime.strptime(new1, FMT)
    await interaction.response.send_message(content=f"**Uptime** (in format HH:MM:SS): {tdelta}"
                                            , ephemeral=True, delete_after=3.0)


@client.tree.command(name='edit', description='edit a message sent by the client.',
                     guild=discord.Object(id=829053898333225010))
@app_commands.check(is_owner)
@app_commands.describe(msg='The ID of the message to edit', new_content='The new content to replace it with')
async def edit(interaction: discord.Interaction, msg: str, new_content: str):
    a = await client.fetch_guild(interaction.guild.id)
    b = await a.fetch_channel(interaction.channel.id)
    c = await b.fetch_message(int(msg))
    await c.edit(content=str(new_content))
    await interaction.response.send_message(content="edits have been made", ephemeral=True, delete_after=3.0)


@client.tree.command(name='button', description='A test button to see how they work')
async def butttonerr(interaction: discord.Interaction):
    view = SimpleView(timeout=60)
    msg = await interaction.response.send_message(view=view)
    view.message = msg
    await view.wait()
    if view.foo is None:
        await interaction.response.edit_message(content="timed out.")


@client.tree.command(name='tn', description="using discord's unix timestamp model, returns the time now "
                                            "in a given format, which is optional",
                     guild=discord.Object(id=829053898333225010))
@app_commands.describe(spec='the mode of displaying the current time now')
@app_commands.guild_only()
async def tn(interaction: discord.Interaction, spec: Optional[Literal["t - returns short time (format HH:MM)",
"T - return long time (format HH:MM:SS)", "d - returns short date (format DD/MM/YYYY)",
"D - returns long date (format DD Month Year)", "F - returns long date and time (format Day, DD Month Year MM:SS)",
"R - returns the relative time since now"]] = None) -> None:

    """Using Discord's unix timestamp model, returns the time now in a given format, which is optional.
    Following parameters are accepted: Greedy(discord.Object)
    ?tn t -> returns short time (format HH:MM)
    ?tn T -> return long time (format HH:MM:SS)
    ?tn d -> returns short date (format DD/MM/YYYY)
    ?tn D -> returns long date (format DD Month Year)
    ?tn F -> returns long date and time (format Day, DD Month Year MM:SS)
    ?tn R -> returns the relative time since now, but in this scenario, it is inefficient to use.

    If no parameter is added, uses the default timestamp (in format DD Month Year MM:SS)
    """
    date_time = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    pattern = '%d.%m.%Y %H:%M:%S'
    epoch = int(time.mktime(time.strptime(date_time, pattern)))
    if spec:
        embed = discord.Embed(title='Epoch Timestamp conversion',
                              description=f'your conversion is: <t:{epoch}:{spec[0]}>\n'
                                          f'the epoch time in this format is: {epoch}', colour=possible_color)
        embed.set_thumbnail(url=interaction.user.avatar.url)
        await interaction.response.send_message(embed=embed, ephemeral=True)
    else:
        embed2 = discord.Embed(title='Epoch Timestamp conversion',
                                description=f'your conversion is: <t:{epoch}>\n'
                                            f'the epoch time in this format is: {epoch}', colour=possible_color)
        embed2.set_thumbnail(url=interaction.user.avatar.url)
        await interaction.response.send_message(embed=embed2, ephemeral=True)


@client.command(name='continue')
@commands.guild_only()
@commands.is_owner()
async def provide_appendix(ctx):
    third_embed = discord.Embed(title='\U0001f916 How-to-bot',
                                description='There are *a lot* of bots inside this server. It is probable that other '
                                            'than from the name of the bot itself, you have no idea what each of the '
                                            'bots do. This guide will briefly explain what some of bots here do.\n\n'
                                            '__Labels__\n'
                                            '**Miscellaneous** - The bot can perform various tasks that are not '
                                            'restricted to members of higher authority. Examples include fun commands, '
                                            'an economy system and other useful commands to play around with\n'
                                            '**Music** - The bot is designed to play music within voice channels.\n'
                                            '**Games** - The bot has a variety of minigames and real-life games to play'
                                            ' around with.\n'
                                            '**Core** - These are bots that are designed for core functionality of the '
                                            'server. These generally require members of higher permissions to use as it'
                                            ' is based upon server management.\n\n__Bot Directory__'
                                            '<@&1054018165362925611> - Core, Miscellaneous `Supports Slash Commands`\n'
                                            '<@&1122560847940698124> - Music `Supports Slash Commands`\n'
                                            '<@&980756619107373069> - Games, Miscellaneous (chess) `Supports Slash Commands`\n'
                                            '<@&924046889001844767> - Core, Miscellaneous (leveling) `Supports Slash Commands`\n'
                                            '<@&897413473649184769> - Core, Miscellaneous (utility), Games '
                                            '`Supports Slash Commands`\n'
                                            '<@&993248388101455963> - Music `Supports Slash Commands`\n'
                                            '<@&1121087635444736104> - Core, Miscellaneous (fun) `Supports Slash Commands`\n'
                                            '<@&1119993490810621984> - Core `Supports Slash Commands`\n'
                                            '<@&1122488655806730263> - Games `Does not Support Slash Commands, type g.help '
                                            'instead`\n'
                                            '<@&1121395714988187681> - Miscellaneous (quoting messages) `Supports Slash Commands`\n'
                                            '<@&923905586830114817> - Games, Miscellaneous (anime) `Supports Slash Commands`\n'
                                            '<@&1140192690626117674> - Core `Does not Support Slash Commands, use star help instead`\n'
                                            '<@&1121398247806734388> - Miscellaneous (self-explanatory) `Supports Slash Commands`\n'
                                            '<@&1125787076684681238> - Core `Supports Slash Commands`\n'
                                            '<@&924625138434080791> - Games, Miscellaneous (userphone, SFX) `Supports Slash '
                                            'Commands`\n'
                                            '<@&1139810946773159980> - Core `Supports Slash Commands`',
                                colour=discord.Colour.from_rgb(18, 177, 255))

    await ctx.send(embed=third_embed)

@client.command(name='sync')
@commands.guild_only()
@commands.is_owner()
async def sync(
        ctx: Context, guilds: Greedy[discord.Object], spec: Optional[Literal["~", "*", "^"]] = None) -> None:
    """Following parameters are accepted:
?sync -> global sync
?sync ~ -> sync current guild
?sync * -> copies all global app commands to current guild and syncs
?sync ^ -> clears all commands from the current guild target and syncs (removes guild commands)
?sync id_1 id_2 -> syncs guilds with id 1 and 2"""
    if not guilds:
        if spec == "~":
            synced = await ctx.bot.tree.sync(guild=ctx.guild)
        elif spec == "*":
            ctx.bot.tree.copy_global_to(guild=ctx.guild)
            synced = await ctx.bot.tree.sync(guild=ctx.guild)
        elif spec == "^":
            ctx.bot.tree.clear_commands(guild=ctx.guild)
            await ctx.bot.tree.sync(guild=ctx.guild)
            synced = []
        else:
            synced = await ctx.bot.tree.sync()

        await ctx.send(
            f"Synced {len(synced)} commands {'globally' if spec is None else 'to the current guild.'}"
        )
        return

    ret = 0
    for guild in guilds:
        try:
            await ctx.bot.tree.sync(guild=guild)
        except discord.HTTPException:
            pass
        else:
            ret += 1

    await ctx.send(f"Synced the tree to {ret}/{len(guilds)}.")


@client.tree.command(name='repeat', description='make the bot say what you tell me to say.',
                     guild=discord.Object(id=829053898333225010))
@app_commands.check(is_owner)
@app_commands.describe(kwargs='what should i say?')
async def repeat(interaction: discord.Interaction, kwargs: str):
    await interaction.response.send_message(f"{kwargs}")


@repeat.error
async def repeat_error(interaction: discord.Interaction, error):
    await interaction.response.send_message("checks have failed. you do not meet the requirements to execute this command.", ephemeral=True)


@client.tree.context_menu(name='Report User')
async def report_message(interaction: discord.Interaction, message: discord.Message):
    # We're sending this response message with ephemeral=True, so only the command executor can see it
    await interaction.response.send_message(
        f'Thanks for reporting this message by {message.author.mention} to our moderators. It will be dealt with as soon as possible.', ephemeral=True
    )

    # Handle report by sending it into a log channel
    log_channel = interaction.guild.get_channel(1124090797613142087)  # replace with your channel id

    embed = discord.Embed(title='Reported Message')
    if message.content:
        embed.description = message.content

    embed.set_author(name=message.author.display_name, icon_url=message.author.display_avatar.url)
    embed.timestamp = message.created_at

    url_view = discord.ui.View()
    url_view.add_item(discord.ui.Button(label='Go to Message', style=discord.ButtonStyle.url, url=message.jump_url))

    await log_channel.send(embed=embed, view=url_view)


def check_if_it_is_me(interaction: discord.Interaction) -> bool:
    return interaction.user.id == 546086191414509599


@client.tree.context_menu(name='Override Rules')
@app_commands.check(check_if_it_is_me)
async def override_rules(interaction: discord.Interaction, message: discord.Message):

    await message.delete()
    embed = discord.Embed(title='Rules & Guidelines', description="<a:e1_alert:1124674618179977276> Unlike most servers"
                                                                  ", we are not imposing any strict "
                                                                  "enforcements on how to behave in the server. In a "
                                                                  "small friend server such as this, these limitations"
                                                                  " should not hinder the user's ability to express"
                                                                  " their thoughts and opinions freely. However, we do "
                                                                  "expect that you come into this server with a few "
                                                                  "behavioural guidelines in mind, and these apply to"
                                                                  " almost any other server too. Failure to follow"
                                                                  " these guidelines will result in heavy sanctions and"
                                                                  " punishments. <a:e1_alert:1124674618179977276>\n\n"
                                                                  "These guidelines explain what isn’t allowed on "
                                                                  "Discord."
                                                                  " Everyone on Discord must follow these rules, and "
                                                                  "they apply to all parts of the platform, including "
                                                                  "your content and behaviors.",
                          colour=discord.Colour.from_rgb(243, 13, 72))
    embed.add_field(name='1. Use common sense.',
                    value='If your behavior is deemed inappropriate by staff, they have the right to apply '
                          'punishments depending on the situation.', inline=False)
    embed.add_field(name='2. Do not use hate speech or engage in other hateful conduct.',
                    value='We consider __**hate speech**__ to be any form of expression that either attacks'
                          ' other people or promotes hatred or violence against them based on their protected '
                          'characteristics.\n We consider the following to be protected characteristics: age; caste; '
                          'color; disability; ethnicity; family responsibilities; gender; gender identity; housing '
                          'status; national origin; race; refugee or immigration status; religious affiliation; '
                          'serious illness; sex; sexual orientation; socioeconomic class and status; source of income; '
                          'status as a victim of domestic violence, sexual violence, or stalking; and weight and size.',
                    inline=False)
    embed.add_field(name='3. Do not threaten to harm another individual or a group of people.',
                    value='This includes direct, indirect, and suggestive threats.', inline=False)
    embed.add_field(name='4. Do not share real media depicting gore, excessive violence, or animal harm.',
                    value='This especially applies with the intention to harass or shock others.', inline=False)
    embed.add_field(name='5. Do not organize, promote, or engage in any illegal behavior.',
                    value='Examples include buying, selling, or trading of dangerous and regulated goods. '
                          'Dangerous goods '
                          'have reasonable potential to cause real-world, physical harm to individuals. Regulated goods'
                          ' have laws in place that restrict the purchase, sale, trade, or ownership of the goods.',
                    inline=False)
    embed.add_field(name='\U0001f54a Lasting Remarks',
                    value='These guidelines will continue to evolve over time. This means we may take action against '
                          'a user, or content that violates the spirit of these guidelines when we encounter a new '
                          'threat or harm that is not explicitly covered in the current version. It is your '
                          'responsibility to keep these guidelines and any implicit ones in mind when engaging in '
                          'activity around and within this server.', inline=False)

    embed.set_footer(text="thanks for reading. now go have fun!", icon_url='https://cdn.discordapp.com/attachments/'
                                                                           '1124672402413072446/1140254405912969287/o'
                                                                           'utput-onlinegiftools.gif')
    await interaction.response.send_message(embed=embed, silent=True)


@client.tree.context_menu(name='Override Information')
@app_commands.check(check_if_it_is_me)
async def override_info(interaction: discord.Interaction, message: discord.Message):

    await message.delete()
    embed = discord.Embed(title='This is cc.',
                          description="Receiving regular improvements, more features are being added monthly to"
                                      " make your experience in this server slightly more better than it has been"
                                      " before. If there is anything you would like to see improved, ping "
                                      "<@546086191414509599> and it will be considered accordingly.\n\n"
                                      "<a:e1_butterflyP:1124677835299233834> remember to read <#902138223571116052> "
                                      "before you begin sending messages here, as these rules"
                                      " differ from the conventional rules throughout most Discord servers.\n"
                                      "<a:e1_butterflyP:1124677835299233834> we have a diverse range of colour roles to"
                                      " choose from, find them at <#1121095327806672997>. we will also consider "
                                      "requests to receive your own custom colour at your disposal.\n"
                                      "<a:e1_butterflyP:1124677835299233834> - experiment with a range of bots within"
                                      " the server that provide lots of games and fun commands to play around with. try"
                                      " it out in <#1121094935802822768>.",
                          colour=discord.Colour.from_rgb(244, 127, 255))
    embed.add_field(name='Leveling System',
                    value='of course what is a server without its own leveling system. designed to promote activity, '
                          'you will be rewarded for reaching each of the following respective level roles:\n'
                          '<@&923930948909797396> - you get this role with no additional perks.\n'
                          '<@&923931088613699584> - *hidden*\n'
                          '<@&923931156125204490> - *hidden*\n'
                          '<@&923931553791348756> - ability to request for a specific permission (requires approval)\n'
                          '<@&923931585953280050> - *hidden*\n'
                          '<@&923931615208546313> - *hidden*\n'
                          '<@&923931646783287337> - ability to request for a specific permission (requires approval)\n'
                          '<@&923931683311456267> - *hidden*\n'
                          '<@&923931729016795266> - *hidden*\n'
                          '<@&923931772020985866> - ability to request for a custom channel type of your choice.\n'
                          '<@&923931819571810305> - you can request <@546086191414509599> to implement any feature '
                          'into this bot.\n'
                          '<@&923931862001414284> - any 1 of the following events will happen in Appendix 1.',
                    inline=False)
    third_embed = discord.Embed(title='\U0001f916 How-to-bot',
                                description='There are *a lot* of bots inside this server. It is probable that other '
                                            'than from the name of the bot itself, you have no idea what each of the '
                                            'bots do. This guide will briefly explain what some of bots here do.\n\n'
                                            '__Labels__\n'
                                            '**Miscellaneous** - The bot can perform various tasks that are not '
                                            'restricted to members of higher authority. Examples include fun commands, '
                                            'an economy system and other useful commands to play around with\n'
                                            '**Music** - The bot is designed to play music within voice channels.\n'
                                            '**Games** - The bot has a variety of minigames and real-life games to play'
                                            ' around with.\n'
                                            '**Core** - These are bots that are designed for core functionality of the '
                                            'server. These generally require members of higher permissions to use as it'
                                            ' is based upon server management.\n\n__Bot Directory__\n'
                                            '<@&1054018165362925611> - Core, Miscellaneous `Supports Slash Commands`\n'
                                            '<@&1122560847940698124> - Music `Supports Slash Commands`\n'
                                            '<@&980756619107373069> - Games, Miscellaneous (chess) `Supports Slash Commands`\n'
                                            '<@&924046889001844767> - Core, Miscellaneous (leveling) `Supports Slash Commands`\n'
                                            '<@&897413473649184769> - Core, Miscellaneous (utility), Games '
                                            '`Supports Slash Commands`\n'
                                            '<@&993248388101455963> - Music `Supports Slash Commands`\n'
                                            '<@&1121087635444736104> - Core, Miscellaneous (fun) `Supports Slash Commands`\n'
                                            '<@&1119993490810621984> - Core `Supports Slash Commands`\n'
                                            '<@&1122488655806730263> - Games `Does not Support Slash Commands, type g.help '
                                            'instead`\n'
                                            '<@&1121395714988187681> - Miscellaneous (quoting messages) `Supports Slash Commands`\n'
                                            '<@&923905586830114817> - Games, Miscellaneous (anime) `Supports Slash Commands`\n'
                                            '<@&1140192690626117674> - Core `Does not Support Slash Commands, use star help instead`\n'
                                            '<@&1121398247806734388> - Miscellaneous (self-explanatory) `Supports Slash Commands`\n'
                                            '<@&1125787076684681238> - Core `Supports Slash Commands`\n'
                                            '<@&924625138434080791> - Games, Miscellaneous (userphone, SFX) `Supports Slash '
                                            'Commands`\n'
                                            '<@&1139810946773159980> - Core `Supports Slash Commands`',
                                colour=discord.Colour.from_rgb(18, 177, 255))
    second_embed = discord.Embed(title='Appendix 1',
                                 description='if you somehow manage to reach <@&923931862001414284>, '
                                             'out of 6 events, 1 will '
                                             'take place. A dice will be rolled and the outcome will ultimately depend '
                                             'on a dice roll.\n\n'
                                             '**Event 1:** your level of experience and wisdom will prove you worthy of'
                                             ' receiving <@&912057500914843680>, a role only members of high authority '
                                             'can attain. `Roll 1 on the dice to unlock this.`\n'
                                             '**Event 2:** your familiarity with this server will allow you to get '
                                             '1 Month of Discord Nitro immediately when available. `Roll 2 on the '
                                             'dice to unlock this.`\n'
                                             '**Event 3:** this is a karma roll. you will receive **nothing.**'
                                             ' `Roll 3 on the dice to unlock this.`\n'
                                             '**Event 4:** for the sake of nonplus, **this event will not be disclosed'
                                             ' until it is received.** `Roll 4 on the dice'
                                             ' to unlock this.`\n'
                                             '**Event 5:** this is a karma roll. you will receive **nothing.** `Roll'
                                             ' 5 on the dice to unlock this.`\n'
                                             '**Event 6:** this is a special one \U00002728. only one '
                                             'could occur: a face reveal'
                                             ' or a voice reveal by the owner. the choice will be made by '
                                             'another dice roll (yes, another one).',
                                 colour=discord.Colour.from_rgb(255, 75, 126))
    second_embed.add_field(name='Blacklisted Channels',
                           value='to remove the possibility of advantage, the following channels have been blacklisted.'
                                 ' you will not be able to earn EXP in these channels:\n'
                                 '<#1121094935802822768>, <#1122623337764487218>, <#1121397509605044274>, '
                                 '<#1122948514368979066>')
    second_embed.add_field(name='Additional Note',
                           value='any attempts to exploit this system in an attempt to gain further EXP **will not '
                                 'work.** the bot that manages leveling (<@437808476106784770>) is trained to '
                                 'recognize EXP exploits such as spamming and excessive text blocking.\n'
                                 'so it will take time to reach the maximum level!',
                           inline=False)
    second_embed.set_footer(text='reminder: the perks from all roles are one-time use only and cannot be reused or '
                                 'recycled.')
    await interaction.response.send_message(embeds=[embed, third_embed, second_embed], silent=True)


@client.tree.command(name='help', description='Help command for cxc, outlines all categories of commands',
                     guild=discord.Object(id=829053898333225010))
async def repeat(interaction: discord.Interaction):

    embed = discord.Embed(title='Help', description='```diff\n[Patch #7]\n- Dropdowns have been created.\n- Dropdowns are now fully functional```\n\n'
                                                    'hi! <a:e1_wave:1124974582009434173> Use this dropdown to find a command based on its category. Note that:\n\n'
                                                    '<:e1_dotR:1124995153862598706> This help command may not display all available commands.\n'
                                                    '<:e1_dotR:1124995153862598706> The prefix for this bot is `>` (for text commands)\n'
                                                    '<:e1_dotR:1124995153862598706> This help command is liable to errors, see `Feedback` below to let us know about it.\n'
                                                    '<:e1_dotR:1124995153862598706> Most of the commands available are now Slash Commands.', colour=discord.Colour.from_rgb(226, 67, 67))
    embed.add_field(name='Feedback', value='Do you have feedback you wish to share to the Bot Developers? Try using </feedback:1122906134269927595> to help improve this experience!')
    await interaction.response.send_message(embed=embed, view=Select(), ephemeral=True)


async def main():
    await load()
    await client.start("MTA0NzU3MjUzMDQyMjEwODMxMQ.GLNHdE.8nfwDhxgayHXEDUS-wClaQVEUDcw9_VA7BS9dM")

asyncio.run(main())
