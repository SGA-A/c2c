import datetime
import os
from modules import inventory_funcs
import typing
import sys
from discord.ext import commands
from discord.ext.commands import Context, Greedy
import discord
from typing import Optional, Literal
import asyncio
from discord import FFmpegPCMAudio, app_commands
import random
import time
from PyDictionary import PyDictionary
from discord.app_commands import AppCommandError
import psutil
from cogs.economy import Shop

intents = discord.Intents.all()
intents.message_content = True

client = commands.Bot(command_prefix='>', intents=intents, case_insensitive=True,
                      owner_ids={992152414566232139, 546086191414509599},
                      activity=discord.Activity(type=discord.ActivityType.listening, name='hip tunes'),
                      status=discord.Status.idle)

pRange = random.randint(1, 255)
possible_color = discord.Color.from_rgb(pRange, pRange, pRange)
number = random.randint(1, 1000)
client.remove_command('help')
print(sys.version)


def return_random_color():
    colors_crayon = {
        "warm pink": discord.Color.from_rgb(255, 204, 204),
        "warm orange": discord.Color.from_rgb(255, 232, 204),
        "warm yellow": discord.Color.from_rgb(242, 255, 204),
        "warm green": discord.Color.from_rgb(223, 255, 204),
        "warm blue": discord.Color.from_rgb(204, 255, 251),
        "warm purple": discord.Color.from_rgb(204, 204, 255),
        "polar ice": discord.Color.from_rgb(204, 255, 224),
        "polar pink": discord.Color.from_rgb(212, 190, 244),
        "unusual green": discord.Color.from_rgb(190, 244, 206)
    }
    return random.choice(list(colors_crayon.values()))


def len_channels():
    total_channels = 0
    for guild in client.guilds:
        total_channels += len(guild.channels)
    return total_channels


# Search for a specific term in this project using Ctrl + Shift + F
# Shift Tab to Unindent a block of code

async def load():
    for filename in os.listdir('./cogs'):
        if filename.endswith(".py"):
            await client.load_extension(f"cogs.{filename[:-3]}")


def return_custom_emoji(emoji_name):
    emoji = discord.utils.get(client.emojis, name=emoji_name)
    return emoji


async def play_source(voice_client):
    source = FFmpegPCMAudio("battlet.mp3", executable='ffmpeg')
    voice_client.play(source, after=lambda e: print('Player error: %s' % e) if e else client.loop.create_task(
        play_source(voice_client)))


@client.event
async def on_ready():
    global new1
    global geo
    await inventory_funcs.DB.connect()
    if not inventory_funcs.DB.is_connected:
        raise RuntimeError("Database access denied")
    await inventory_funcs.create_table()
    print(f'connected.')
    geo = await client.fetch_user(546086191414509599)
    s1 = datetime.datetime.now()
    myshop = Shop(name='shop', description='view items that are available for purchase.', guild_only=True,
                  guild_ids=[829053898333225010, 780397076273954886])
    client.tree.add_command(myshop)
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
    if message.author.id == 1047572530422108311:
        return
    if message.guild is None:
        print(f"{message.content} - {message.author.name}")
        msg = await message.channel.send("# Reminder\n"
                                      "hi <a:e1_imhappy:1144654614046724117>. **do not send me DMs.** i will not read them nor respond to commands here either "
                                      "and will **never message you.** use a server to interact with me instead!")
        await msg.delete(delay=7.0)
    #  useful for preventing comments by a user at a particular channel e.g. during certain topics
    """if message.channel.id == 1119991877010202744:
        if message.author.id == 1134123734421217412:
            await message.delete()
            await message.channel.send("you're messages will be continuously deleted until this topic is closed.")"""
    if message.content.startswith('psst'):
        await message.delete()
        await message.channel.send(file=discord.File("C:\\Users\\Computer\\Downloads\\secret.png",
                                                     description='A girl whispering something to another girl\'s ear'))
        return
    if geo.mentioned_in(message):
        await message.add_reaction('<:e1_comfy:1150361201352659066>')
    if "goggy" in message.content:
        possible_response = ["you meant geo right", "that's not his name", "*geo", "who is goggy?", "stop calling him goggy >:(",
                             "\U0001f620", "\U0001f928", "@goggy does not exist", "goggy more like geo"]
        await message.channel.send(f"{random.choice(possible_response)}")
    await client.process_commands(message)


@client.event
async def on_presence_update(before, after):
    if before.display_name == 'carl':
        if after.status == discord.Status.online:
            update_message = await client.fetch_channel(1121095327806672997)
            the_message = await update_message.fetch_message(1151232300990873721)
            await the_message.edit(content=f"<@235148962103951360> is now fully operational, self-roles now function as intended.")
        if after.status == discord.Status.offline:
            update_message = await client.fetch_channel(1121095327806672997)
            the_message = await update_message.fetch_message(1151232300990873721)
            await the_message.edit(content=f"at the moment, <@235148962103951360> is offline. as a result, these self roles will not function as intended.")
    else:
        return


def is_owner(interaction: discord.Interaction):
    if interaction.user.id == 546086191414509599:
        return True
    return False


@client.tree.error
async def on_app_command_error(
    interaction: discord.Interaction,
    error: AppCommandError
):
    await interaction.response.send_message(f"{error}", ephemeral=True)


@client.command(name='sayit')
@commands.is_owner()
async def sayit(ctx):
    await ctx.message.delete()
    await ctx.send(f"<@235148962103951360> is now fully operational, self-roles now function as intended.", silent=True)


@commands.is_owner()
@commands.guild_only()
@client.command(name='regex')
async def automod_regex(ctx):
    await ctx.guild.create_automod_rule(name='new rule by cxc', event_type=discord.AutoModRuleEventType.message_send,
                                        trigger=discord.AutoModTrigger(regex_patterns=["a", "b", "c", "d", "e"]),
                                        actions=[discord.AutoModRuleAction(duration=datetime.timedelta(minutes=5.0))])
    await ctx.send("done")


@commands.is_owner()
@commands.guild_only()
@client.command(name='mentions')
async def automod_mentions(ctx):
    await ctx.guild.create_automod_rule(name='new rule by cxc', event_type=discord.AutoModRuleEventType.message_send,
                                        trigger=discord.AutoModTrigger(mention_limit=5),
                                        actions=[discord.AutoModRuleAction(duration=datetime.timedelta(minutes=5.0))])
    await ctx.send("done")

@commands.is_owner()
@commands.guild_only()
@client.command(name='keyword')
async def automod_keyword(ctx, word):
    await ctx.guild.create_automod_rule(name='new rule by cxc', event_type=discord.AutoModRuleEventType.message_send,
                                        trigger=discord.AutoModTrigger(keyword_filter=[f'{word}']),
                                        actions=[discord.AutoModRuleAction(duration=datetime.timedelta(minutes=5.0))])
    await ctx.send("done")


class InviteButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60.0)
        self.add_item(discord.ui.Button(
            label="Invite Link",
            url="https://discord.com/api/oauth2/authorize?client_id=1047572530422108311&permissions=8&scope=applications.commands%20bot",
            style=discord.ButtonStyle.danger))



@client.command(name='invite')
@commands.guild_only()
async def invite_bot(ctx):
    await ctx.send("add me to your server below!", view=InviteButton())


@commands.is_owner()
@client.command(name='update')
@commands.guild_only()
async def push_update(ctx):
    await ctx.message.delete()
    # continuer = await ctx.fetch_message(1140952278862401657)
    original = await ctx.fetch_message(1142392804446830684)
    embed = discord.Embed(title='Update Schedule',
                          description='This embed will post any changes to the server in the near future. This includes'
                                      ' any feature updates within the server and any other optimization changes.',
                          colour=discord.Colour.from_rgb(101, 242, 171))
    embed.add_field(name='Known Future Changes',
                    value='There are currently no scheduled updates.')
    embed.set_footer(text='check back later for any known scheduled updates..',
                     icon_url='https://pa1.narvii.com/6025/9497042b3aad0518f08dd2bfefb0e2262f4a7149_hq.gif')
    # await ctx.send(reference=continuer, embed=embed, silent=True, mention_author=False)
    await original.edit(embed=embed)


@commands.is_owner()
@client.command(name='update2')
@commands.guild_only()
async def push_update2(ctx):
    await ctx.message.delete()
    original = await ctx.fetch_message(1140952278862401657)
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
                                            '<@&980756619107373069> - Games, Miscellaneous (chess) `Supports Slash Commands`\n'
                                            '<@&924046889001844767> - Core, Miscellaneous (leveling) `Supports Slash Commands`\n'
                                            '<@&897413473649184769> - Core, Miscellaneous (utility), Games '
                                            '`Supports Slash Commands`\n'
                                            '<@&990629304322904077> - Music `Supports Slash Commands`\n'
                                            '<@&1054018165362925611> - Core, Miscellaneous `Supports Slash Commands`\n'
                                            '<@&1121087635444736104> - Core, Miscellaneous (fun) `Supports Slash Commands`\n'
                                            '<@&1119993490810621984> - Core `Supports Slash Commands`\n'
                                            '<@&1144278276798423114> - Games, Miscellaneous (genshin-orientated)\n'
                                            '<@&1121395714988187681> - Miscellaneous (quoting messages) `Supports Slash Commands`\n'
                                            '<@&923905586830114817> - Games, Miscellaneous (anime) `Supports Slash Commands`\n'
                                            '<@&1146684108978798624> - Miscellaneous (snipe deleted messages)\n'
                                            '<@&1140192690626117674> - Core `Does not Support Slash Commands, use star help instead`\n'
                                            '<@&1121398247806734388> - Miscellaneous (self-explanatory) `Supports Slash Commands`\n'
                                            '<@&1125787076684681238> - Core `Supports Slash Commands`\n'
                                            '<@&924625138434080791> - Games, Miscellaneous (userphone, SFX) `Supports Slash '
                                            'Commands`',
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
    await original.edit(embeds=[embed, third_embed, second_embed])



@commands.is_owner()
@client.command(name='invite_link')
@commands.guild_only()
async def get_server_invite_link(ctx):
    await ctx.message.delete()
    await ctx.send("**Permanent Invite Link** - discord.gg/W3DKAbpJ5E\n"
                   "This link ***will never*** expire, but note that it can "
                   "be disabled by an Administrator without notice.", silent=True)


@client.command(name='calc', aliases=['calculate', 'c'])
@commands.guild_only()
async def calculator(ctx, *the_args):
    async with ctx.typing():
        result = eval(f'{the_args[0]}')
        await ctx.reply(f'**{ctx.author.name}**, the answer is `{result}`', allowed_mentions=False)
        await asyncio.sleep(1)


@commands.is_owner()
@client.command(name='cthr', aliases=['ct', 'create_thread'])
@commands.guild_only()
async def create_thread(ctx):
    forum_channel = await client.fetch_channel(1147176894903627888)
    message = await ctx.fetch_message(1147203137195745431)
    thread_embed = discord.Embed(title='This is a forum channel.',
                                 description='The bigger the community grows, the harder it '
                                             'becomes to keep track of all the ongoing discussions. '
                                             'Through this channel we give everyone a chance to make their voices heard.',
                                 colour=discord.Colour.from_rgb(87,242,135))
    thread_embed.add_field(name='What are Forum Channels?',
                           value='Forum Channels are designed to allow conversations to coexist without people talking over each other.\n\n'
                                 'When you enter a Forum Channel, you don’t see every message that’s being shared across every conversation. '
                                 'Instead, you see an easy-to-navigate list of conversations where you have full control of which you’d like to jump into.\n\n'
                                 '**Post Guidelines** define what kinds of topics are allowed and use **Tags** help people find discussions '
                                 'they’re interested in—all designed to help members create new posts seamlessly, reduce clutter, and foster meaningful conversations.',
                           inline=False)
    thread_embed.add_field(name='Before you start posting..',
                           value='Read the **Post Guidelines** to grasp what is and isn\'t allowed on this channel.', inline=False)
    thread_embed.set_footer(text='Note that you are restricted to creating 1 post every 5 minutes to avoid excessive posts.')
    await message.edit(content='Forum channels help create value with conversation.', embed=thread_embed)


@client.event
async def on_error(interaction: discord.Interaction, error):
    if isinstance(error, discord.ext.commands.errors.MissingPermissions):
        await interaction.response.send_message('you do not have permission to execute this command.', ephemeral=True)

    else:
        await interaction.response.send_message(f'that did not work. Please contact the bot developer',
                                                ephemeral=True)
        raise error  # this will show some debug print in the console, when debugging


@client.tree.command(name='defer', description='beta preview of a deferred slash command response',
                     guilds=[discord.Object(id=829053898333225010), discord.Object(id=780397076273954886)])
async def deferred(interaction: discord.Interaction):
    await interaction.response.defer()
    await asyncio.sleep(5)
    await interaction.followup.send("this message was deferred.")


@client.tree.command(name='define', description='find the definition of any word of your choice.',
                     guilds=[discord.Object(id=829053898333225010), discord.Object(id=780397076273954886)])
@app_commands.checks.cooldown(1, 3, key=lambda i: i.user.id)
@app_commands.describe(word='the term that is to be defined for you')
async def define_word(interaction: discord.Interaction, word: str):
    try:
        the_dictionary = PyDictionary()
        choice = word
        meaning = the_dictionary.meaning(f'{choice.lower()}')
        for item in meaning.items():
            for thing in item:
                if isinstance(thing, list):
                    unique_colour = return_random_color()
                    the_result = discord.Embed(title=f'Define: {choice.lower()}',
                                               description=f'This shows all the available definitions for the word {choice}.',
                                               colour=unique_colour)
                    for x in range(0, len(thing)):
                        the_result.add_field(name=f'Definition {x+1}', value=f'{thing[x]}')
                    if len(the_result.fields) == 0:
                        the_result.add_field(name=f'Looks like no results were found.', value=f'We couldn\'t find a definition for this word.')
                    await interaction.response.send_message(embed=the_result)
                else:
                    continue
    except AttributeError:
        await interaction.response.send_message(content=f'try again, but this time input an actual word.')

@client.tree.command(name='about', description='shows some stats related to the client',
                     guilds=[discord.Object(id=829053898333225010), discord.Object(id=780397076273954886)])
@app_commands.checks.cooldown(1, 3, key=lambda i: i.user.id)
async def about_the_bot(interaction: discord.Interaction):
    geoxor = await client.fetch_user(546086191414509599)
    amount = 0
    commands_total = client.all_commands
    context = commands_total.keys()
    context_amount = len(context)
    amount += context_amount
    for slash_command in client.tree.walk_commands(guild=interaction.guild, type=discord.AppCommandType.user):  # A slash command.
        amount += 1
    for slash_command in client.tree.walk_commands(guild=interaction.guild, type=discord.AppCommandType.message):  # A user context menu command.
        amount += 1
    for slash_command in client.tree.walk_commands(guild=interaction.guild, type=discord.AppCommandType.chat_input):  # A message context menu command.
        amount += 1
    embed = discord.Embed(title='About c2c',
                          description='c2c was made with creativity in mind. knowing that there are almost limitless possibilites of creation '
                                      'through the api, <@546086191414509599> and <@992152414566232139> wanted to create a bot seamlessly integrating'
                                      ' fun and utility with maximum efficiency. accomplishing a wide range of tasks, it has reached the pinnacle of success in'
                                      ' creating a client that serves you well. **command 2 control**.',
                          colour=discord.Colour.from_rgb(145,149,213),
                          url=client.user.avatar.url)
    embed.add_field(name='Run on',
                    value=f'discord.py v{discord.__version__}')
    embed.add_field(name='Activity',
                    value=f'{client.activity.name}')
    embed.add_field(name='Internal Cache Ready',
                    value=f'{str(client.is_ready())}')
    embed.add_field(name=f'Process',
                    value=f'CPU Usage: {psutil.cpu_percent()}%\n'
                          f'RAM Usage: {psutil.virtual_memory().percent}%')
    embed.add_field(name='Servers',
                    value=f'{len(client.guilds)}\n'
                          f'-> {len_channels()} channels\n'
                          f'-> {len(client.emojis)} emojis\n'
                          f'-> {len(client.stickers)} stickers')
    embed.add_field(name='Users',
                    value=f'{len(client.users)} users\n'
                          f'{len(client.voice_clients)} voice connections.')
    embed.add_field(name='Total Commands Available',
                    value=f'{amount}')
    embed.set_thumbnail(url=client.user.avatar.url)
    embed.set_author(name='made possible with discord.py:',
                     icon_url='https://media.discordapp.net/attachments/1124994990246985820/1146442046723330138/'
                              '3aa641b21acded468308a37eef43d7b3.png?width=411&height=411',
                     url='https://discordpy.readthedocs.io/en/latest/index.html')
    await interaction.response.defer()
    await asyncio.sleep(5)
    await interaction.followup.send(embed=embed, silent=True)


@client.tree.command(name='pin', description='pin a specified message in any channel.',
                     guilds=[discord.Object(id=829053898333225010), discord.Object(id=780397076273954886)])
@app_commands.check(is_owner)
@app_commands.describe(message_id='the ID of the message to be pinned')
async def pin_it(interaction: discord.Interaction, message_id: str):
    a = await client.fetch_guild(interaction.guild.id)
    b = await a.fetch_channel(interaction.channel.id)
    c = await b.fetch_message(int(message_id))
    await c.pin(reason=f'Requested by {interaction.user.name}.')
    await interaction.response.send_message(content="The requested message has been pinned successfully.",
                                            ephemeral=True, delete_after=3.0)


@client.tree.command(name='react', description='Forces the client to react to a message with any reaction requested.',
                     guilds=[discord.Object(id=829053898333225010), discord.Object(id=780397076273954886)])
@app_commands.check(is_owner)
@app_commands.describe(message_id='the ID of the message to react to:',
                       emote='the name of the emoji to react with, e.g., KarenLaugh')
async def react(interaction: discord.Interaction, message_id: str, emote: str):
    b = await interaction.guild.fetch_channel(interaction.channel.id)
    c = await b.fetch_message(int(message_id))
    emoji = return_custom_emoji(emote)  # a function to return a custom emoji
    await c.add_reaction(emoji)
    await interaction.response.send_message(content='the emoji has been added to the message', ephemeral=True,
                                            delete_after=3.0)


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
                                              '`>sync_tree` - synchronizes all slash commands to the current guild. Parameters are optional.\n'
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
                                              '</config:1125410667898351666> - generates a given amount of money to the author.\n'
                                              '`>blank` - clear the current channel without removing messages.\n'
                                              '</react:1125111517512208595> - i will react to a message using a given emoji.\n'
                                              '`>invite` - invite the client to a given server.\n'
                                              '`>update` - updates the information in <#1121445944576188517>\n'
                                              '`>update2` - updates the upper information in <#1121445944576188517>',
                                  colour=discord.Colour.from_rgb(91, 170, 239))
            embed.set_image(
                url='https://media.discordapp.net/attachments/1124994990246985820/1125005648422256692/762082-3602628412.jpg?width=1377&height=701')
            embed.set_footer(text='got any suggestions for the bot? use the /feedback command to let us know about it.',
                             icon_url=client.user.avatar.url)
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
            embed.set_image(
                url='https://media.discordapp.net/attachments/1124994990246985820/1125041765200703528/pink.jpg?width=1247&height=701')
            embed.set_footer(text='got any suggestions for the bot? use the /feedback command to let us know about it.',
                             icon_url=client.user.avatar.url)
            await interaction.response.edit_message(embed=embed)
        if choice == 'Utility':
            embed = discord.Embed(title='Help: Utility',
                                  description="These are commands that can be used by anybody, and can be fun or useful in general.\n\n"
                                              "</ping:1054011107695677450> - returns the delay before a transfer of data begins.\n"
                                              "</com:1125433087715717192> - returns the most common letters in a word.\n"
                                              "</define:1142428536834097252> - find definitions of any word of choice\n"
                                              "`>calculate` - find out the answers to any calculation of choice.\n"
                                              "`>spotify` - gets the spotify activity of any member, if any.\n"
                                              "</charinfo:1125433087715717193> - shows unicode information about any given character.\n"
                                              "</tn:1125126993923547290> - returns the time now in a given format of choice.\n"
                                              "</feedback:1122906134269927595> - used to send feedback to the client developers about the bot.\n"
                                              "</defer:1142531961492086866> - defers the interaction response.",
                                  colour=discord.Colour.from_rgb(15, 255, 135))
            embed.add_field(name="But wait, there's more!",
                            value="**Message Context Menus** can be used. This can be done by right clicking any message, clicking/tapping `Apps` and then clicking"
                                  " any command with my avatar on it!\n\n"
                                  "`Override Information` (owner use only)\n"
                                  "`Override Rules` (owner use only)\n"
                                  "`Report User` - this reports the given user's message directly to the developers of the client only for them to look into."
                                  "\nThere will be punishments for misuse of these commands!")
            embed.set_image(
                url='https://media.discordapp.net/attachments/1124994990246985820/1125009796429520936/wp6063334-2886616470.jpg?width=1168&height=701')
            embed.set_footer(text='got any suggestions for the bot? use the /feedback command to let us know about it.',
                             icon_url=client.user.avatar.url)
            await interaction.response.edit_message(embed=embed)
        if choice == 'Economy':
            embed = discord.Embed(title='Help: Economy',
                                  description="These are commands that can be used by anybody, and relate to the Economy system of the client.\n\n"
                                              "</balance:1125331114274345001> - returns a user's balance, along with their current job.\n"
                                              "</register:1125331114274345003> - register into the monetary system\n"
                                              "</profile:1144661482878017657> - view information about users and display their badges.\n"
                                              "</give:1125331114274345004> - gives an amount of money to someone else, who must be registered.\n"
                                              "</rob:1125331114274345005> - robs someone else, who must be registered.\n"
                                              "</bet:1125410667898351667> - bet your money on a gamble to win or lose coins.\n"
                                              "</leaderboard:1145035956739649556> - displays the users with the most coins the virtual economy.",
                                  colour=discord.Colour.from_rgb(255, 215, 0))
            embed.set_image(
                url='https://media.discordapp.net/attachments/1124994990246985820/1125010187812605972/wp6402672.jpg?width=1247&height=701')
            embed.set_footer(text='got any suggestions for the bot? use the /feedback command to let us know about it.',
                             icon_url=client.user.avatar.url)
            await interaction.response.edit_message(embed=embed)


class Select(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(SelectMenu())


@client.tree.command(name='feedback', description='Send feedback to the client developers regarding the bot.',
                     guilds=[discord.Object(id=829053898333225010), discord.Object(id=780397076273954886)])
async def feedback(interaction: discord.Interaction):
    feedback_modal = FeedbackModal()
    feedback_modal_user = interaction.user
    await interaction.response.send_modal(feedback_modal)


@client.tree.command(name='uptime', description='Returns the time the bot has been active for (in HH:MM:SS)',
                     guilds=[discord.Object(id=829053898333225010), discord.Object(id=780397076273954886)])
@app_commands.check(is_owner)
async def uptime(interaction: discord.Interaction):
    """Returns the time the bot has been online for (in HH:MM:SS)"""
    s2 = datetime.datetime.now()
    new2 = str(s2.strftime("%j:%H:%M:%S"))
    FMT = '%j:%H:%M:%S'
    tdelta = datetime.datetime.strptime(new2, FMT) - datetime.datetime.strptime(new1, FMT)
    await interaction.response.send_message(content=f"**Uptime** (in format HH:MM:SS): {tdelta}"
                                            , ephemeral=True, delete_after=3.0)


@client.tree.command(name='edit', description='edit a message sent by the client.',
                     guilds=[discord.Object(id=829053898333225010), discord.Object(id=780397076273954886)])
@app_commands.check(is_owner)
@app_commands.describe(msg='The ID of the message to edit', new_content='The new content to replace it with')
async def edit(interaction: discord.Interaction, msg: str, new_content: str):
    a = await client.fetch_guild(interaction.guild.id)
    b = await a.fetch_channel(interaction.channel.id)
    c = await b.fetch_message(int(msg))
    await c.edit(content=str(new_content))
    await interaction.response.send_message(content="edits have been made", ephemeral=True, delete_after=3.0)


@client.tree.command(name='button', description='A test button to see how they work',
                     guilds=[discord.Object(id=829053898333225010), discord.Object(id=780397076273954886)])
async def the_button(interaction: discord.Interaction):
    view = SimpleView(timeout=60)
    msg = await interaction.response.send_message(view=view)
    view.message = msg
    await view.wait()
    if view.foo is None:
        await interaction.response.edit_message(content="timed out.")


@client.tree.command(name='tn', description="using discord's unix timestamp model, returns the time now "
                                            "in a given format",
                     guilds=[discord.Object(id=829053898333225010), discord.Object(id=780397076273954886)])
@app_commands.describe(spec='the mode of displaying the current time now')
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
    date_time = datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S")
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


@client.command(name='blank')
@commands.guild_only()
@commands.is_owner()
async def blank(ctx):
    await ctx.send(".\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\nCleared.")


@client.command(name='sync_tree')
@commands.guild_only()
@commands.is_owner()
async def sync_tree(
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
                     guilds=[discord.Object(id=829053898333225010), discord.Object(id=780397076273954886)])
@app_commands.check(is_owner)
@app_commands.describe(message='what should i say?', channel='the channel to send the message to.')
async def repeat(interaction: discord.Interaction, message: str, channel: Optional[discord.TextChannel]):
    begin_emoji = message.find("{")
    begin_content = message[:begin_emoji]
    end_emoji = message.find("}")
    end_content = message[end_emoji+1:]
    if begin_emoji != -1:
        if end_emoji != -1:
            emoji_name = message[begin_emoji+1:end_emoji]
            actual_emoji = return_custom_emoji(emoji_name)
            if channel is None:
                channel = interaction.channel
            await channel.send(f"{begin_content}{actual_emoji}{end_content}")
            await interaction.response.send_message(f"your emojified response has been sent to <#{channel.id}>!", ephemeral=True)
        else:
            await interaction.response.send_message("invalid format", ephemeral=True)
    else:
        await interaction.response.send_message(message)


@repeat.error
async def repeat_error(interaction: discord.Interaction, error):
    await interaction.response.send_message(
        "checks have failed. you do not meet the requirements to execute this command.")


@client.command(name='spotify', pass_context=True, aliases=['sp', 'spot'])
@commands.guild_only()
async def find_spotify_activity(ctx, user: int = None):
    user = ctx.guild.get_member(user)
    if user is None:
        user = ctx.author
        pass
    if user.activities:
        for activity in user.activities:
            if str(activity).lower() == "spotify":
                embed = discord.Embed(
                    title=f"{user.name}'s Spotify",
                    description=f"Listening to {activity.title}",
                    color=activity.colour)
                duration = str(activity.duration)
                final_duration = duration[3:7]
                embed.set_thumbnail(url=activity.album_cover_url)
                embed.set_author(name=f"{user.display_name}", icon_url=user.avatar.url)
                embed.add_field(name="Artist", value=activity.artist)
                embed.add_field(name="Album", value=activity.album)
                embed.add_field(name="Song Duration", value=final_duration)
                embed.set_footer(text="Song started at {}".format(activity.created_at.strftime("%H:%M %p")))
                embed.url = f"https://open.spotify.com/embed/track/{activity.track_id}"
                await ctx.send(embed=embed)
                return
    await ctx.send(f"{user.display_name}'s spotify activity was not found.")
    return

@client.tree.context_menu(name='Report User',
                          guilds=[discord.Object(id=829053898333225010), discord.Object(id=780397076273954886)])
async def report_message(interaction: discord.Interaction, message: discord.Message):
    # We're sending this response message with ephemeral=True, so only the command executor can see it
    await interaction.response.send_message(
        f'Thanks for reporting this message by {message.author.mention} to our moderators. It will be dealt with as soon as possible.',
        ephemeral=True
    )

    # Handle report by sending it into a log channel
    log_channel = interaction.guild.get_channel(1124090797613142087)  # replace with your channel id

    embed = discord.Embed(title='Reported Message')
    if message.content:
        embed.description = message.content
        embed.add_field(name='Reported by',
                        value=f'{interaction.user.display_name}', inline=False)

    embed.set_author(name=message.author.display_name, icon_url=message.author.display_avatar.url)
    embed.timestamp = message.created_at

    url_view = discord.ui.View()
    url_view.add_item(discord.ui.Button(label='Go to Message', style=discord.ButtonStyle.url, url=message.jump_url))

    await log_channel.send(embed=embed, view=url_view)


def check_if_it_is_me(interaction: discord.Interaction) -> bool:
    return interaction.user.id == 546086191414509599


@client.tree.context_menu(name='Override Rules',
                          guilds=[discord.Object(id=829053898333225010), discord.Object(id=780397076273954886)])
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


@client.tree.context_menu(name='Override Information',
                          guilds=[discord.Object(id=829053898333225010), discord.Object(id=780397076273954886)])
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
                                            '<@1144278276798423114> - Games, Miscellaneous (genshin-orientated)'
                                            '<@&1121395714988187681> - Miscellaneous (quoting messages) `Supports Slash Commands`\n'
                                            '<@&923905586830114817> - Games, Miscellaneous (anime) `Supports Slash Commands`\n'
                                            '<@&1140192690626117674> - Core `Does not Support Slash Commands, use star help instead`\n'
                                            '<@&1121398247806734388> - Miscellaneous (self-explanatory) `Supports Slash Commands`\n'
                                            '<@&1125787076684681238> - Core `Supports Slash Commands`\n'
                                            '<@&924625138434080791> - Games, Miscellaneous (userphone, SFX) `Supports Slash '
                                            'Commands`',
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
                     guilds=[discord.Object(id=829053898333225010), discord.Object(id=780397076273954886)])
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(title='Help',
                          description='```diff\n[Patch #9]\n- Added 4 new commands to the list\n- Dropdowns are now fully functional```\n\n'
                                      'hi! <a:e1_wave:1124974582009434173> Use this dropdown to find a command based on its category. Note that:\n\n'
                                      '<:e1_dotR:1124995153862598706> This help command may not display all available commands.\n'
                                      '<:e1_dotR:1124995153862598706> The prefix for this bot is `>` (for text commands)\n'
                                      '<:e1_dotR:1124995153862598706> This help command is liable to errors, see `Feedback` below to let us know about it.\n'
                                      '<:e1_dotR:1124995153862598706> Most of the commands available are now Slash Commands.',
                          colour=discord.Colour.from_rgb(226, 67, 67))
    embed.add_field(name='Feedback',
                    value='Do you have feedback you wish to share to the Bot Developers? Try using </feedback:1122906134269927595> to help improve this experience!')
    await interaction.response.send_message(embed=embed, view=Select(), ephemeral=True)


async def main():
    await load()
    await client.start("MTA0NzU3MjUzMDQyMjEwODMxMQ.GLNHdE.8nfwDhxgayHXEDUS-wClaQVEUDcw9_VA7BS9dM")


asyncio.run(main())
