import datetime
from io import BytesIO
from random import choice
from unicodedata import name
from time import perf_counter
from typing import Literal, Optional, List
from xml.etree.ElementTree import fromstring

import discord
from pytz import timezone
from discord.ext import commands
from discord import app_commands
from psutil import Process, cpu_count

from cogs.economy import total_commands_used_by_user, USER_ENTRY
from .core.helpers import membed, number_to_ordinal
from .core.paginator import Pagination, PaginationSimple
from .core.constants import LIMITED_CONTEXTS, LIMITED_INSTALLS

ARROW = "<:arrowe:1180428600625877054>"
API_EXCEPTION = "The API fucked up, try again later."
UPLOAD_FILE_DESCRIPTION = "A file to upload alongside the thread."
ANIME_ENDPOINTS = (
    "https://purrbot.site/api/img/nsfw/neko/img",
)
EMBED_TIMEZONES = {
    'Pacific': 'US/Pacific',
    'Mountain': 'US/Mountain',
    'Central': 'US/Central',
    'Eastern': 'US/Eastern',
    'Britain': 'Europe/London',
    'Sydney': 'Australia/Sydney',
    'Japan': 'Asia/Tokyo',
    'Germany': 'Europe/Berlin',
    'India': 'Asia/Kolkata'
}

def extract_attributes(post_element, mode: Literal["post", "tag"]) -> dict | str:
    if mode == "post":
        keys_to_extract = {"created_at", "jpeg_url", "author"}
        data = {key: post_element.get(key) for key in keys_to_extract}
    else:
        data = post_element.get("name")

    del post_element
    return data


def format_dt(dt: datetime.datetime, style: Optional[str] = None) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)

    if style is None:
        return f'<t:{int(dt.timestamp())}>'
    return f'<t:{int(dt.timestamp())}:{style}>'


def format_relative(dt: datetime.datetime) -> str:
    return format_dt(dt, 'R')


def parse_xml(xml_content, mode: Literal["post", "tag"]):
    result = fromstring(xml_content).findall(f".//{mode}")

    extracted_data = [extract_attributes(res, mode=mode) for res in result]
    return extracted_data


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
        placeholder="Any concerns, feature requests or bug reports for the bot."
    )

    async def on_submit(self, interaction: discord.Interaction):
        channel = interaction.client.get_partial_messageable(1124090797613142087)
        embed = membed(self.message.value)
        embed.title = f'New Feedback: {self.fb_title.value or "Untitled"}'
        embed.set_author(
            name=interaction.user.name, 
            icon_url=interaction.user.display_avatar.url
        )

        await channel.send(embed=embed)
        await interaction.response.send_message(
            ephemeral=True, 
            embed=membed("Your response has been submitted!")
        )


class ImageSourceButton(discord.ui.Button):
    def __init__(self, url: Optional[str] = "https://www.google.com") -> None:
        super().__init__(url=url, label="Source", row=1)


class Utility(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.process = Process()

        self.cog_context_menus = {
            app_commands.ContextMenu(
                name='Extract Image Source',
                callback=self.extract_source,
                allowed_contexts=app_commands.AppCommandContext(guild=True, private_channel=True),
                allowed_installs=app_commands.AppInstallationType(guild=True, user=True)
            ),
            app_commands.ContextMenu(
                name='Extract Embed Colour',
                callback=self.embed_colour,
                allowed_contexts=app_commands.AppCommandContext(guild=True, private_channel=True),
                allowed_installs=app_commands.AppInstallationType(guild=True, user=True)
            ),
            app_commands.ContextMenu(
                name="View User Avatar",
                callback=self.view_avatar,
                allowed_contexts=app_commands.AppCommandContext(guild=True, private_channel=True),
                allowed_installs=app_commands.AppInstallationType(guild=True, user=True)
            ),
            app_commands.ContextMenu(
                name="View User Banner",
                callback=self.view_banner,
                allowed_contexts=app_commands.AppCommandContext(guild=True, private_channel=True),
                allowed_installs=app_commands.AppInstallationType(guild=True, user=True)
            )
        }
        
        for context_menu in self.cog_context_menus:
            self.bot.tree.add_command(context_menu)

    async def cog_unload(self) -> None:
        for context_menu in self.cog_context_menus:
            self.bot.tree.remove_command(context_menu)
    
    async def get_commits(self):
        async with self.bot.session.get(
            url="https://api.github.com/repos/SGA-A/c2c/commits",
            headers={"Authorization": f"token {self.bot.GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
        ) as response:
            if response.status == 200:
                commits = await response.json()
                return commits[:3]
            return []

    async def tag_search_autocomplete(
        self,
        _: discord.Interaction,
        current: str,
    ) -> List[app_commands.Choice[str]]:
        
        tags_xml = await self.retrieve_via_kona(
            name=current.lower(), 
            mode="tag",
            page=1,
            order="count",
            limit=25
        )

        if isinstance(tags_xml, int):  # http exception
            return

        return [
            app_commands.Choice(name=tag_name, value=tag_name)
            for tag_name in tags_xml if current.lower() in tag_name.lower()
        ]


    async def retrieve_via_kona(self, **params) -> int | str:
        """Returns a list of dictionaries for you to iterate through and fetch their attributes"""
        mode = params.pop("mode")
        base_url = f"https://konachan.net/{mode}.xml"

        async with self.bot.session.get(base_url, params=params) as response:
            if response.status != 200:
                return response.status
            
            posts_xml = await response.text()
            return parse_xml(posts_xml, mode=mode)

    async def format_gif_api_response(
        self, 
        interaction: discord.Interaction, 
        start: float, 
        api_url: str, 
        **attrs
    ) -> None | discord.WebhookMessage:
        
        async with self.bot.session.get(api_url, **attrs) as response:
            if response.status != 200:
                await interaction.followup.send(embed=membed(API_EXCEPTION))
            
            buffer = BytesIO(await response.read())
            end = perf_counter()
            
            await interaction.followup.send(content=f"Took `{end-start:.2f}s`.", file=discord.File(buffer, 'clip.gif'))

    @app_commands.command(name='serverinfo', description="Show information about the server and its members")
    @app_commands.guild_install()
    @app_commands.allowed_contexts(**LIMITED_CONTEXTS)
    async def display_server_info(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(thinking=True)

        guild = interaction.guild

        total_bots = 0

        for member in guild.members:
            if not member.bot:
                continue
            total_bots += 1

        serverinfo = discord.Embed(title=guild.name, colour=guild.me.color)
        serverinfo.set_thumbnail(url=guild.icon.url)
        serverinfo.description = (
            f"\U00002726 Owner: {guild.owner.name}\n"
            f"\U00002726 Maximum File Size: {guild.filesize_limit / 1_000_000}MB\n"
            f"\U00002726 Role Count: {len(guild.roles)-1}\n"
        )

        tn_full, tn_relative = (
            discord.utils.format_dt(guild.created_at), 
            discord.utils.format_dt(guild.created_at, style="R")
        )
        
        serverinfo.add_field(
            name="Created",
            value=f"{tn_full} ({tn_relative})",
        )

        if guild.description:
            serverinfo.add_field(
                name="Server Description",
                value=guild.description,
                inline=False
            )

        serverinfo.add_field(
            name="Member Info",
            value=(
                f"\U00002023 Humans: {guild.member_count-total_bots:,}\n"
                f"\U00002023 Bots: {total_bots:,}\n"
                f"\U00002023 Total: {guild.member_count:,}\n"
            )
        )

        serverinfo.add_field(
            name="Channel Info",
            value=(
                f"\U00002023 <:categoryCh:1226619447171875006> {len(guild.categories)}\n"
                f"\U00002023 <:textCh:1226619349037482154> {len(guild.text_channels)}\n"
                f"\U00002023 <:voiceCh:1226619160050663495> {len(guild.voice_channels)}"
            )
        )

        animated_emojis = sum(1 for emoji in guild.emojis if emoji.animated)

        serverinfo.add_field(
            name="Emojis",
            value=(
                f"\U00002023 Static: {len(guild.emojis)-animated_emojis}/{guild.emoji_limit}\n"
                f"\U00002023 Animated: {animated_emojis}/{guild.emoji_limit}"
            )
        )

        await interaction.followup.send(embed=serverinfo)

    @app_commands.describe(user="Whose command usage to display. Defaults to you.")
    @app_commands.command(name="usage", description="See your total command usage")
    @app_commands.allowed_installs(**LIMITED_INSTALLS)
    @app_commands.allowed_contexts(guilds=True, private_channels=True)
    async def view_user_usage(self, interaction: discord.Interaction, user: Optional[USER_ENTRY]):
        user = user or interaction.user

        async with self.bot.pool.acquire() as conn:

            total_cmd_count = await total_commands_used_by_user(user.id, conn)

            command_usage = await conn.fetchall(
                """
                SELECT cmd_name, cmd_count
                FROM command_uses
                WHERE userID = $0
                ORDER BY cmd_count DESC
                """, user.id
            )

            if not command_usage:
                return await interaction.response.send_message(
                    embed=membed(
                        f"{user.mention} has never used any bot commands before.\n"
                        "Or, they have not used the bot since the rewrite (<t:1712935339:R>)."
                    )
                )

            em = membed()
            em.title = f"{user.display_name}'s Command Usage"
            paginator = PaginationSimple(
                interaction, 
                invoker_id=interaction.user.id
            )

            async def get_page_part(page: int, length: Optional[int] = 12):

                offset = (page - 1) * length
                em.description = f"> Total: {total_cmd_count:,}\n\n"
                
                for item in command_usage[offset:offset + length]:
                    em.description += f"` {item[1]:,} ` \U00002014 {item[0]}\n"

                n = paginator.compute_total_pages(len(command_usage), length)
                em.set_footer(text=f"Page {page} of {n}")
                return em, n
            paginator.get_page = get_page_part

        await paginator.navigate()

    @app_commands.command(name='calc', description='Calculate an expression')
    @app_commands.describe(expression='The expression to evaluate.')
    @app_commands.allowed_installs(**LIMITED_INSTALLS)
    @app_commands.allowed_contexts(guilds=True, private_channels=True)
    async def calculator(self, interaction: discord.Interaction, expression: str) -> None:
        try:
            interpretable = expression.replace('^', '**').replace(',', '_')
            
            # Evaluate the expression
            result = eval(interpretable)

            # Format the result with commas for thousands separator
            result = f"{result:,}" if isinstance(result, (int, float)) else "Invalid Equation"
        except Exception:
            result = "Invalid Equation"

        output = membed(
            f"""
            \U0001f4e5 **Input:**
            ```{expression}```
            \U0001f4e4 **Output:**
            ```{result}```
            """
        )

        await interaction.response.send_message(embed=output)

    @commands.command(name='ping', description='Checks latency of the bot')
    async def ping(self, ctx: commands.Context) -> None:
        msg_content = "Pong!"
        msg = await ctx.send(msg_content)
        msg_content += f" `{self.bot.latency * 1000:.0f}ms`"
        await msg.edit(content=msg_content)

    async def extract_source(
        self, 
        interaction: discord.Interaction, 
        message: discord.Message
    ) -> None:

        images = set()
        counter = 0

        if message.embeds:
            for embed in message.embeds:
                for asset in (embed.image, embed.thumbnail):
                    if not asset:
                        continue
                    images.add(f"**{counter}**. [`{embed.image.height}x{embed.image.width}`]({embed.image.url})")
        
        for attr in message.attachments:
            images.add(f"**{counter}**. [`{attr.height}x{attr.width}`]({attr.url})")

        embed = membed()
        if not counter:
            embed.description = "Could not find any attachments."
            return await interaction.response.send_message(embed=embed, ephemeral=True)
        
        embed.title = f"Found {counter} images from {message.author.name}"
        embed.description="\n".join(images)
        embed.set_thumbnail(url=message.author.display_avatar.url)
        
        await interaction.response.send_message(ephemeral=True, embed=embed)

    async def embed_colour(
        self, 
        interaction: discord.Interaction, 
        message: discord.Message
    ) -> None:

        all_embeds = [
            discord.Embed(
                colour=embed.colour, 
                description=f"{embed.colour} - [`{embed.colour.value}`](https:/www.google.com)"
            ) for embed in message.embeds
        ]

        if all_embeds:
            return await interaction.response.send_message(ephemeral=True, embeds=all_embeds)

        await interaction.response.send_message(
            ephemeral=True, 
            embed=membed("No embeds were found within this message.")
        )

    anime = app_commands.Group(
        name='anime', 
        description="Surf through anime images and posts.", 
        nsfw=False,
        allowed_contexts=app_commands.AppCommandContext(guild=True, private_channel=True),
        allowed_installs=app_commands.AppInstallationType(guild=True, user=True)
    )

    @anime.command(name='kona', description='Retrieve NSFW posts from Konachan')
    @app_commands.rename(length="max_images")
    @app_commands.describe(
        tag1='A tag to base your search on.', 
        tag2='A tag to base your search on.',
        tag3='A tag to base your search on.' ,
        private='Hide the results from others. Defaults to True.',
        length='The maximum number of images to display at once. Defaults to 3.',
        maximum='The maximum number of images to retrieve. Defaults to 30.',
        page='The page number to look through.'
    )
    @app_commands.autocomplete(
        tag1=tag_search_autocomplete, 
        tag2=tag_search_autocomplete, 
        tag3=tag_search_autocomplete
    )
    async def kona_fetch(
        self, 
        interaction: discord.Interaction, 
        tag1: str, 
        tag2: Optional[str],
        tag3: Optional[str],
        private: Optional[bool] = True,
        length: Optional[app_commands.Range[int, 1, 10]] = 3,
        maximum: Optional[app_commands.Range[int, 1, 9999]] = 30,
        page: Optional[app_commands.Range[int, 1]] = 1
    ) -> None:
        
        tags = filter(lambda x: isinstance(x[1], str), iter(interaction.namespace))
        tagviewing = ' '.join(val for _, val in tags)

        posts_xml = await self.retrieve_via_kona(
            tags=tagviewing, 
            limit=maximum, 
            page=page, 
            mode="post"
        )

        if isinstance(posts_xml, int):
            embed = membed("Failed to make this request.")
            embed.title = f"{posts_xml}. That's an error."
            return await interaction.response.send_message(embed=embed)

        if not len(posts_xml):
            
            embed = membed(
                "- There are a few known causes:\n"
                " - Entering an invalid tag name.\n"
                " - Accessing some posts under the `copyright` tag.\n"
                " - There are no posts found under this tag.\n"
                " - The page requested exceeds the max length.\n"
                "- You can find a tag by using /tagsearch "
                "or [the website.](https://konachan.net/tag)"
            )
            embed.title = "No posts found."
            return await interaction.response.send_message(ephemeral=True, embed=embed)

        additional_notes = [
            (
                f"{result['jpeg_url']}",
                f"{result['author']}",
                result['created_at']
            )
            for result in posts_xml
        ]

        async def get_page_part(page: int):
            embeds = []

            offset = (page - 1) * length

            for item_attrs in additional_notes[offset:offset + length]:
                embed = membed()
                embed.timestamp = datetime.datetime.fromtimestamp(int(item_attrs[-1]), tz=datetime.timezone.utc)
                embed.title = item_attrs[1]
                embed.url = item_attrs[0]

                embed.set_image(url=item_attrs[0])
                embeds.append(embed)

            n = Pagination.compute_total_pages(len(additional_notes), length)
            return embeds, n

        await Pagination(interaction, get_page=get_page_part).navigate(ephemeral=private)

    @anime.command(name='char', description="Retrieve SFW or NSFW anime images")
    @app_commands.describe(filter_by='The type of image to retrieve.')
    async def get_via_nekos(
        self, 
        interaction: discord.Interaction, 
        filter_by: Optional[Literal["neko", "kitsune", "waifu", "husbando"]] = "neko"
    ) -> None:

        async with self.bot.session.get(f"https://nekos.best/api/v2/{filter_by}") as resp:
            if resp.status != 200:
                return await interaction.response.send_message(embed=membed(API_EXCEPTION))

            data = await resp.json()
            data = data['results'][0]

        embed = discord.Embed(colour=0xFF9D2C)
        embed.set_author(name=f"{data['artist_name']}")
        embed.set_image(url=data['url'])

        img_view = discord.ui.View()
        img_view.add_item(ImageSourceButton(url=data["url"]))

        await interaction.response.send_message(embed=embed, view=img_view)

    @anime.command(name='random', description="Get a completely random waifu image")
    async def waifu_random_fetch(self, interaction: discord.Interaction) -> None:

        embed = discord.Embed(colour=0xFF9D2C)
        async with self.bot.session.get(choice(ANIME_ENDPOINTS)) as resp:
            if resp.status != 200:
                return await interaction.response.send_message(embed=membed(API_EXCEPTION))
            data = await resp.json()
            data = data["link"]

        embed.set_image(url=data)
        img_view = discord.ui.View()
        img_view.add_item(ImageSourceButton(url=data))
        return await interaction.response.send_message(embed=embed, view=img_view, ephemeral=True)

    @app_commands.command(name='emojis', description='Fetch all the emojis c2c can access')
    @app_commands.allowed_contexts(guilds=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def emojis_paginator(self, interaction: discord.Interaction) -> None:
        length = 8
        all_emojis = [f"{i} (**{i.name}**) \U00002014 `{i}`" for i in self.bot.emojis]

        emb = membed()
        emb.title = "Emojis"

        async def get_page_part(page: int):
            offset = (page - 1) * length
            emb.description = "\n".join(all_emojis[offset:offset + length])
            n = Pagination.compute_total_pages(len(all_emojis), length)
            return emb, n

        await Pagination(interaction, get_page=get_page_part).navigate()

    @app_commands.command(name='inviter', description='Creates a server invite link')
    @app_commands.default_permissions(create_instant_invite=True)
    @app_commands.describe(
        invite_lifespan='A non-zero duration in days for which the invite should last for.', 
        maximum_uses='The maximum number of uses for the created invite.'
    )
    @app_commands.guild_install()
    @app_commands.allowed_contexts(**LIMITED_CONTEXTS)
    async def gen_new_invite(
        self, 
        interaction: discord.Interaction, 
        invite_lifespan: app_commands.Range[int, 1], 
        maximum_uses: app_commands.Range[int, 1]
    ) -> None:
        invite_lifespan *= 86400

        generated_invite = await interaction.channel.create_invite(
            reason=f'Invite creation requested by {interaction.user.name}',
            max_age=invite_lifespan, 
            max_uses=maximum_uses
        )

        maxim_usage = f"Max usages set to {generated_invite.max_uses}" if maximum_uses else "No limit to maximum usage"
        formatted_expiry = discord.utils.format_dt(generated_invite.expires_at, 'R')
        success = discord.Embed(
            title='Successfully generated new invite link', 
            colour=0x2B2D31,
            description=(
                f'**A new invite link was created.**\n'
                f'- Invite channel set to {generated_invite.channel}\n'
                f'- {maxim_usage}\n'
                f'- Expires {formatted_expiry}\n'
                f'- Invite Link is: {generated_invite.url}'
            )
        )
        success.set_author(
            name=interaction.user.name, 
            icon_url=interaction.user.display_avatar.url
        )

        await interaction.response.send_message(embed=success)

    @app_commands.command(name='randomfact', description='Queries a random fact')
    @app_commands.allowed_contexts(guilds=True, private_channels=True)
    @app_commands.allowed_installs(**LIMITED_INSTALLS)
    async def random_fact(self, interaction: discord.Interaction) -> None:
        
        async with self.bot.session.get(
            url='https://api.api-ninjas.com/v1/facts', 
            params={'X-Api-Key': self.bot.NINJAS_API_KEY}
        ) as resp:
            if resp.status != 200:
                return await interaction.response.send_message(embed=membed(API_EXCEPTION))
            
            text = await resp.json()
            await interaction.response.send_message(embed=membed(f"{text[0]['fact']}."))

    @app_commands.command(name="image", description="Manipulate a user's avatar")
    @app_commands.describe(
        user="The user to apply the manipulation to.", 
        endpoint="What kind of manipulation sorcery to use."
    )
    @app_commands.allowed_contexts(guilds=True, private_channels=True)
    @app_commands.allowed_installs(**LIMITED_INSTALLS)
    async def image_manip(
        self, 
        interaction: discord.Interaction, 
        user: Optional[discord.User], 
        endpoint: Optional[
            Literal[
                "abstract", "balls", "billboard", "bonks", "bubble", "canny", "clock",
                "cloth", "contour", "cow", "cube", "dilate", "fall", "fan", "flush", "gallery",
                "globe", "half-invert", "hearts", "infinity", "laundry", "lsd", "optics", "parapazzi"
            ]
        ] = "abstract"
    ) -> None:

        start = perf_counter()
        await interaction.response.defer(thinking=True)
        
        user = user or interaction.user
        params = {'image_url': user.display_avatar.url}
        headers = {'Authorization': f'Bearer {self.bot.JEYY_API_KEY}'}
        api_url = f"https://api.jeyy.xyz/v2/image/{endpoint}"

        await self.format_gif_api_response(
            interaction,
            start=start,
            api_url=api_url,
            params=params,
            headers=headers
        )

    @app_commands.command(name="image2", description="Manipulate a user's avatar further")
    @app_commands.describe(
        user="The user to apply the manipulation to.",
        endpoint="What kind of manipulation sorcery to use."
    )
    @app_commands.allowed_contexts(guilds=True, private_channels=True)
    @app_commands.allowed_installs(**LIMITED_INSTALLS)
    async def image2_manip(
        self, 
        interaction: discord.Interaction,
        user: Optional[discord.User],
        endpoint: Optional[
            Literal[
                "minecraft", "patpat", "plates", "pyramid", "radiate", "rain", "ripped", "ripple",
                "shred", "wiggle", "warp", "wave"
            ]
        ] = "wave"
    ) -> None | discord.InteractionMessage:

        start = perf_counter()
        await interaction.response.defer(thinking=True)

        user = user or interaction.user
        params = {'image_url': user.display_avatar.url}
        headers = {'Authorization': f'Bearer {self.bot.JEYY_API_KEY}'}
        api_url = f"https://api.jeyy.xyz/v2/image/{endpoint}"

        await self.format_gif_api_response(
            interaction,
            start=start,
            api_url=api_url,
            params=params,
            headers=headers
        )

    @app_commands.command(name="locket", description="Insert people into a heart-shaped locket")
    @app_commands.describe(user="The user to add to the locket.", user2="The second user to add to the locket.")
    @app_commands.allowed_contexts(guilds=True, private_channels=True)
    @app_commands.allowed_installs(**LIMITED_INSTALLS)
    async def locket_manip(
        self, 
        interaction: discord.Interaction, 
        user: Optional[discord.User], 
        user2: discord.User
    ) -> None:

        start = perf_counter()
        await interaction.response.defer(thinking=True)

        user = user or interaction.user
        params = {'image_url': user.display_avatar.url, 'image_url_2': user2.display_avatar.url}
        headers = {'Authorization': f'Bearer {self.bot.JEYY_API_KEY}'}
        api_url = "https://api.jeyy.xyz/v2/image/heart_locket"

        await self.format_gif_api_response(
            interaction,
            start=start,
            api_url=api_url,
            params=params,
            headers=headers
        )

    @app_commands.command(name='charinfo', description='Show information about characters')
    @app_commands.allowed_contexts(guilds=True, private_channels=True)
    @app_commands.allowed_installs(**LIMITED_INSTALLS)
    @app_commands.describe(characters='Any written letters or symbols.')
    async def charinfo(self, interaction: discord.Interaction, *, characters: str) -> None:
        """
        Shows you information about a number of characters.
        Only up to 25 characters at a time.
        """

        def to_string(c):
            digit = f'{ord(c):x}'
            the_name = name(c, 'Name not found.')
            c = '\\`' if c == '`' else c
            return (
                f'[`\\U{digit:>08}`](http://www.fileformat.info/info/unicode/char/{digit}): {the_name} '
                f'**\N{EM DASH}** {c}'
            )

        msg = '\n'.join(map(to_string, characters))
        if len(msg) > 2000:
            return await interaction.response.send_message(
                ephemeral=True, 
                embed=membed('Output too long to display.')
            )
        await interaction.response.send_message(msg, suppress_embeds=True)

    @app_commands.command(name='feedback', description='Send feedback to the c2c developers')
    @app_commands.allowed_contexts(guilds=True, private_channels=True)
    @app_commands.allowed_installs(**LIMITED_INSTALLS)
    async def feedback(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_modal(FeedbackModal())

    @app_commands.command(name='about', description='Learn more about the bot')
    @app_commands.allowed_contexts(guilds=True, private_channels=True)
    @app_commands.allowed_installs(**LIMITED_INSTALLS)
    async def about_the_bot(self, interaction: discord.Interaction) -> None:

        commits = await self.get_commits()
        to_iso = datetime.datetime.fromisoformat
        revision = [
            f"[`{commit['sha'][:6]}`]({commit['html_url']}) {commit['commit']['message'].splitlines()[0]} "
            f"({format_relative(to_iso(commit['commit']['author']['date']))})"
            for commit in commits
        ]

        embed = discord.Embed(colour=discord.Colour.blurple())
        embed.description = (
            f'Latest Changes:\n'
            f'{"\n".join(revision)}'
        )
        
        embed.title = 'Official Bot Server Invite'
        embed.url = 'https://discord.gg/W3DKAbpJ5E'

        geo = self.bot.get_user(546086191414509599)
        embed.set_author(name=geo.name, icon_url=geo.display_avatar.url)

        total_members, total_unique = 0, len(self.bot.users)
        text, voice, guilds = 0, 0, 0

        for guild in self.bot.guilds:
            guilds += 1
            if guild.unavailable:
                continue

            total_members += guild.member_count or 0
            for channel in guild.channels:
                if isinstance(channel, discord.TextChannel):
                    text += 1
                elif isinstance(channel, discord.VoiceChannel):
                    voice += 1

        memory_usage = self.process.memory_full_info().uss / 1024 ** 2
        cpu_usage = self.process.cpu_percent() / cpu_count()
        embed.timestamp = discord.utils.utcnow()

        diff = embed.timestamp - self.bot.time_launch
        minutes, seconds = divmod(diff.total_seconds(), 60)
        hours, minutes = divmod(minutes, 60)
        days, hours = divmod(hours, 24)

        async with interaction.client.pool.acquire() as conn:
            slash_ran, total_ran, text_ran = await conn.fetchone(
                """
                WITH slash_commands AS (
                    SELECT SUM(cmd_count) AS total_sum 
                    FROM command_uses
                    WHERE cmd_name LIKE '/%'
                ),
                total_commands AS (
                    SELECT SUM(cmd_count) AS total_sum
                    FROM command_uses
                )
                SELECT 
                    slash_commands.total_sum AS slash_commands_sum,
                    total_commands.total_sum AS total_commands_sum,
                    (total_commands.total_sum - slash_commands.total_sum) AS text_commands_sum
                FROM 
                    slash_commands, 
                    total_commands
                """
            )

        embed.add_field(
            name='<:membersb:1247991723284758610> Members',
            value=f'{total_members} total\n{total_unique} unique'
        )

        embed.add_field(
            name='<:channelb:1247991694398460007> Channels', 
            value=f'{text + voice} total\n{text} text\n{voice} voice'
        )

        embed.add_field(
            name='<:processb:1247991668804947968> Process', 
            value=f'{memory_usage:.2f} MiB\n{cpu_usage:.2f}% CPU'
        )

        embed.add_field(
            name='<:serversb:1247991639427780661> Guilds', 
            value=(
                f'{guilds} total\n'
                f'{ARROW}{len(self.bot.emojis)} emojis\n'
                f'{ARROW}{len(self.bot.stickers)} stickers'
            )
        )

        embed.add_field(
            name='<:cmdsb:1247991799801315369> Commands Run', 
            value=(
                f"{total_ran:,} total\n"
                f"{ARROW} {slash_ran:,} slash\n"
                f"{ARROW} {text_ran:,} text"
            )
        )

        embed.add_field(
            name='<:uptimeb:1247991586743255042> Uptime', 
            value=f"{int(days)}d {int(hours)}h {int(minutes)}m {int(seconds)}s"
        )

        embed.set_footer(
            text=f'Made with discord.py v{discord.__version__}', 
            icon_url='http://i.imgur.com/5BFecvA.png'
        )
        
        await interaction.response.send_message(embed=embed)

    async def view_avatar(
        self, 
        interaction: discord.Interaction,
        username: discord.User
    ) -> None:
        embed = membed()

        avatar = username.display_avatar.with_static_format('png')
        embed.set_author(name=username.display_name, url=avatar.url)
        embed.set_image(url=avatar.url)
        await interaction.response.send_message(embed=embed)

    async def view_banner(
        self, 
        interaction: discord.Interaction, 
        username: discord.User
    ) -> None:
        embed = membed()

        username = await self.bot.fetch_user(username.id)
        
        embed.set_author(
            name=username.display_name, 
            icon_url=username.display_avatar.url,
            url=username.display_avatar.url
        )

        if not username.banner:
            embed.description = "This user does not have a banner."
            return await interaction.response.send_message(embed=embed)

        embed.set_image(url=username.banner.with_static_format('png'))
        await interaction.response.send_message(embed=embed)

    @app_commands.checks.cooldown(1, 7, key=lambda i: i.guild.id)
    @app_commands.command(name="imagesearch", description="Browse images from the web")
    @app_commands.describe(
        query="The search query to use for the image search.",
        image_type="The type of image to search for. Defaults to photo.",
        limit="The maximum number of images to retrieve. Defaults to 5.",
        image_colour="The colour of the image to search for. Defaults to colour.",
        from_only="[Limited to Bot Owner] Search from this website only.",
        image_size="The size of the image. Defaults to medium."
    )
    @app_commands.allowed_contexts(guilds=True, private_channels=True)
    @app_commands.allowed_contexts(**LIMITED_CONTEXTS)
    async def image_search(
        self, 
        interaction: discord.Interaction, 
        query: str, 
        image_type: Optional[Literal["clipart", "face", "lineart", "news", "photo", "animated"]] = "photo", 
        limit: Optional[app_commands.Range[int, 1, 10]] = 5,
        image_colour: Optional[Literal["color", "gray", "mono", "trans"]] = "color", 
        from_only: Optional[str] = None, 
        image_size: Optional[Literal["huge", "icon", "large", "medium", "small", "xlarge", "xxlarge"]] = "medium"
    ) -> None:
        
        user = interaction.user

        params = {
            'key': self.bot.GOOGLE_CUSTOM_SEARCH_API_KEY,
            'cx': self.bot.GOOGLE_CUSTOM_SEARCH_ENGINE,
            'q': query.replace(' ', '+'),
            'searchType': 'image',
            'imgType': image_type,
            'num': limit,
            'imgSize': image_size,
            'imgColorType': image_colour
        }

        if from_only:
            if user.id not in self.bot.owner_ids:
                return await interaction.response.send_message(
                    ephemeral=True, 
                    embed=membed("You can't use this feature.")
                )
            params.update({'siteSearch': from_only, 'siteSearchFilter': "i"})

        async with self.bot.session.get('https://www.googleapis.com/customsearch/v1', params=params) as response:
            if response.status != 200:
                return await interaction.response.send_message(embed=membed(API_EXCEPTION))
            response_json = await response.json()
            search_details = response_json.get('searchInformation', {})
            results_count = search_details.get('formattedTotalResults', 'Not available')
            search_time = search_details.get('searchTime', 'Not calculated')

            images = response_json.get('items', [])
            image_info = [
                (
                    image.get('title'), 
                    image.get('link')
                ) 
                for image in images
            ]

        em = membed()
        em.set_author(name=f"{results_count} results ({search_time}ms)", icon_url=user.display_avatar.url)
        paginator = PaginationSimple(interaction, invoker_id=user.id)
        length = 1

        async def get_page_part(page: int):
            """Helper function to determine what page of the paginator we're on."""

            offset = (page - 1) * length

            for item in image_info[offset:offset + length]:
                em.title = item[0]
                em.set_image(url=item[1])
                em.url = item[1]

            n = paginator.compute_total_pages(len(image_info), length)
            em.set_footer(text=f"Page {page} of {n}")
            return em, n
        
        paginator.get_page = get_page_part
        await paginator.navigate()

    @app_commands.command(name='post', description='Upload a new forum thread')
    @app_commands.guild_install()
    @app_commands.allowed_contexts(guilds=True)
    @app_commands.describe(
        name="The name of the thread.",
        forum="What forum this thread should be in.",
        description="The content of the message to send with the thread.",
        tags="The tags to apply to the thread, seperated by speech marks.",
        file=UPLOAD_FILE_DESCRIPTION,
        file2=UPLOAD_FILE_DESCRIPTION,
        file3=UPLOAD_FILE_DESCRIPTION
    )
    @app_commands.default_permissions(manage_guild=True)
    async def create_new_thread(
        self, 
        interaction: discord.Interaction, 
        forum: discord.ForumChannel,
        name: str, 
        description: Optional[str], 
        tags: str, 
        file: Optional[discord.Attachment], 
        file2: Optional[discord.Attachment],
        file3: Optional[discord.Attachment]
    ) -> None:

        await interaction.response.defer(thinking=True)
        tags = tags.lower().split('""')

        files = [
            await param_value.to_file() 
            for param_name, param_value in iter(interaction.namespace) 
            if param_name.startswith("f") and param_value
        ]

        applicable_tags = []
        for tag in tags:
            tag = forum.get_tag(tag)
            if not tag:
                continue
            applicable_tags.append(tag)

        thread, _ = await forum.create_thread(
            name=name,
            content=description,
            files=files,
            applied_tags=applicable_tags
        )

        await interaction.followup.send(
            ephemeral=True, 
            embed=membed(f"Your thread was created here: {thread.jump_url}.")
        )

    @commands.command(name="worldclock", description="See the world clock and the visual sunmap", aliases=('wc',))
    async def worldclock(self, ctx: commands.Context):
        async with ctx.typing():
            now = discord.utils.utcnow()
            clock = discord.Embed(colour=0x2AA198, timestamp=now)

            clock.title = "UTC"
            clock.description = f"```prolog\n{now:%I:%M %p, %A} {number_to_ordinal(int(f"{now:%d}"))} {now:%Y}```"
            clock.set_author(
                icon_url="https://i.imgur.com/CIl9Dyp.png",
                name="All formats given in 12h notation"
            )

            for location, tz in EMBED_TIMEZONES.items():
                time_there = datetime.datetime.now(tz=timezone(tz))
                clock.add_field(name=location, value=f"```prolog\n{time_there:%I:%M %p}```")

            clock.add_field(
                name="Legend",
                inline=False,
                value=(
                    "☀️ = The Sun's position directly overhead in relation to an observer.\n"
                    "🌕 = The Moon's position at its zenith in relation to an observer."
                )
            )

            clock.set_image(url=f"https://www.timeanddate.com/scripts/sunmap.php?iso={now:'%Y%m%dT%H%M'}")
            clock.set_footer(text="Sunmap image courtesy of timeanddate.com")
            await ctx.send(embed=clock)


async def setup(bot: commands.Bot):
    await bot.add_cog(Utility(bot))
