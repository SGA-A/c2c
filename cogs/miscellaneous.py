from io import BytesIO
from github import Github
from random import choice
from unicodedata import name
from time import perf_counter
from waifuim import WaifuAioClient
from psutil import Process, cpu_count
from waifuim.exceptions import APIException
from typing import Literal, Union, Optional, List
from re import compile as compile_it
from xml.etree.ElementTree import fromstring

from discord.ext import commands
from discord import app_commands

import discord
import datetime

from cogs.economy import (
    APP_GUILDS_IDS, 
    USER_ENTRY, 
    total_commands_used_by_user
)
from .core.paginator import Pagination, PaginationSimple
from .core.helpers import membed


ARROW = "<:arrowe:1180428600625877054>"
API_EXCEPTION = "The API fucked up, try again later."
RESPONSES = {
    403: "Forbidden - Access was denied",
    404: "Not Found",
    420: "Invalid Record - The record could not be saved",
    421: "User Throttled - User is throttled, try again later",
    422: "Locked - The resource is locked and cannot be modified",
    423: "Already Exists - The resource already exists",
    424: "Invalid Parameters - The given parameters were invalid",
    500: "Internal Server Error - Some unknown error occured on the konachan website's server",
    503: "Service Unavailable - The konachan website currently cannot handle the request"
}


def extract_attributes(post_element, mode: Literal["post", "tag"]) -> Union[dict, str]:
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


def extract_domain(website):
    dp = compile_it(r'https://(nekos\.pro|nekos\.best)')
    match = dp.match(website)
    return match.group(1)


def return_random_color():
    colors_crayon = (
        discord.Color.from_rgb(255, 204, 204),
        discord.Color.from_rgb(255, 232, 204),
        discord.Color.from_rgb(242, 255, 204),
        discord.Color.from_rgb(223, 255, 204),
        discord.Color.from_rgb(204, 255, 251),
        discord.Color.from_rgb(204, 204, 255),
        discord.Color.from_rgb(204, 255, 224),
        discord.Color.from_rgb(212, 190, 244),
        discord.Color.from_rgb(190, 244, 206),
        discord.Color.from_rgb(255, 203, 193),
        discord.Color.from_rgb(175, 250, 216),
        discord.Color.from_rgb(131, 227, 255),
        discord.Color.from_rgb(191, 252, 198),
        discord.Color.from_rgb(80, 85, 252)
    )
    return choice(colors_crayon)


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
        placeholder="Put anything you want to share about the bot here.."
    )

    async def on_submit(self, interaction: discord.Interaction):
        channel = interaction.guild.get_channel(1122902104802070572)
        embed = membed(self.message.value)
        embed.title = f'New Feedback: {self.fb_title.value or "Untitled"}'
        embed.set_author(name=interaction.user.name, icon_url=interaction.user.display_avatar.url)

        await channel.send(embed=embed)
        await interaction.response.send_message(ephemeral=True, embed=membed("Your response has been submitted!"))

    async def on_error(self, interaction: discord.Interaction, _):
        return await interaction.response.send_message(
            embed=membed("Your feedback could not be sent. Try again later.")
        )


class ImageSourceButton(discord.ui.Button):
    def __init__(self, url: Optional[str] = None):
        super().__init__(url=url or "https://www.google.com", label="Source", row=1)


class Utility(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.process = Process()
        self.wf = WaifuAioClient(session=bot.session, token=bot.WAIFU_API_KEY, app_name="c2c")
        self.g = Github('SGA-A', bot.GITHUB_TOKEN)

        self.image_src = app_commands.ContextMenu(
            name='Extract Image Source',
            callback=self.extract_source
        )
        
        self.get_embed_cmd = app_commands.ContextMenu(
            name='Extract Embed Colour',
            callback=self.embed_colour
        )

        self.bot.tree.add_command(self.image_src)
        self.bot.tree.add_command(self.get_embed_cmd)

    @staticmethod
    async def owners_nolimit(interaction: discord.Interaction) -> Optional[app_commands.Cooldown]:
        """Any of the owners of the bot bypass all cooldown restrictions."""
        if interaction.user.id in {546086191414509599, 992152414566232139}:
            return None
        return app_commands.Cooldown(1, 7)

    async def cog_unload(self) -> None:
        self.bot.tree.remove_command(self.get_embed_cmd.name, type=self.get_embed_cmd.type)
        self.bot.tree.remove_command(self.image_src.name, type=self.image_src.type)

    async def retrieve_via_kona(self, **params) -> Union[int, str]:
        """Returns a list of dictionaries for you to iterate through and fetch their attributes"""
        mode = params.pop("mode")
        base_url = f"https://konachan.net/{mode}.xml"

        async with self.bot.session.get(base_url, params=params) as response:
            if response.status != 200:
                return response.status
            
            posts_xml = await response.text()
            return parse_xml(posts_xml, mode=mode)

    @app_commands.guilds(*APP_GUILDS_IDS)
    @app_commands.command(name='serverinfo', description="Show information about the server and its members")
    async def display_server_info(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(thinking=True)

        guild = interaction.guild

        total_bots = 0

        for member in guild.members:
            if not member.bot:
                continue
            total_bots += 1

        embed = discord.Embed(
            title=guild.name,
            colour=guild.me.color,
            description=(
                f"Owner: {guild.owner.name}\n"
                f"Maximum File Size: {guild.filesize_limit / 1_000_000}MB\n"
                f"Role Count: {len(guild.roles)}\n"
            )
        )

        time = guild.created_at
        tn_full, tn_relative = discord.utils.format_dt(time), discord.utils.format_dt(time, style="R")
        embed.add_field(
            name="Created",
            value=f"{tn_full} ({tn_relative})",
        )
        embed.add_field(name="\U0000200b", value="\U0000200b")

        if guild.description:
            embed.add_field(
                name="Server Description",
                value=guild.description,
                inline=False
            )

        embed.add_field(
            name="Member Info",
            value=(
                f"Humans: {guild.member_count-total_bots:,}\n"
                f"Bots: {total_bots:,}\n"
                f"Total: {guild.member_count:,}\n"
            )
        )

        embed.add_field(
            name="Channel Info",
            value=(
                f"<:categoryCh:1226619447171875006> {len(guild.categories)}\n"
                f"<:textCh:1226619349037482154> {len(guild.text_channels)}\n"
                f"<:voiceCh:1226619160050663495> {len(guild.voice_channels)}"
            )
        )

        animated_emojis = sum(1 for emoji in guild.emojis if emoji.animated)

        embed.add_field(
            name="Emojis",
            value=(
                f"Static: {len(guild.emojis)-animated_emojis}/{guild.emoji_limit}\n"
                f"Animated: {animated_emojis}/{guild.emoji_limit}"
            )
        )

        embed.set_thumbnail(url=guild.icon.url)
       
        embed.set_author(
            name=f"Requested by {interaction.user.name}", 
            icon_url=interaction.user.display_avatar.url,
        )

        await interaction.followup.send(embed=embed)

    @app_commands.guilds(*APP_GUILDS_IDS)
    @app_commands.describe(user="Whose command usage to display. Defaults to you.")
    @app_commands.command(name="usage", description="See your total command usage")
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

    @app_commands.guilds(*APP_GUILDS_IDS)
    @app_commands.command(name='calc', description='Calculate an expression')
    @app_commands.describe(expression='The expression to evaluate.')
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

    @app_commands.guilds(*APP_GUILDS_IDS)
    @app_commands.command(name='ping', description='Checks latency of the bot')
    async def ping(self, interaction: discord.Interaction) -> None:
        start = perf_counter()
        content = membed(
            "Pong!\n"
            f"Initial response: {self.bot.latency * 1000:.0f}ms"
        )
        await interaction.response.send_message(embed=content)
        end = perf_counter()
        content.description += f"\nRound-trip: {(end - start) * 1000:.0f}ms"
        await interaction.edit_original_response(embed=content)

    @app_commands.guilds(*APP_GUILDS_IDS)
    async def extract_source(
        self, 
        interaction: discord.Interaction, 
        message: discord.Message
    ) -> None:

        images = set()
        counter = 0

        if message.embeds:
            for embed in message.embeds:
                if not embed.image:
                    continue
                counter += 1
                images.add(f"**{counter}**. [`{embed.image.height}x{embed.image.width}`]({embed.image.url})")
        
        for attr in message.attachments:
            counter += 1
            images.add(f"**{counter}**. [`{attr.height}x{attr.width}`]({attr.url})")

        embed = membed()
        if not counter:
            embed.description = "Could not find any attachments."
            return await interaction.response.send_message(embed=embed, ephemeral=True)
        
        embed.title = f"Found {counter} images from {message.author.name}"
        embed.description="\n".join(images)
        embed.set_thumbnail(url=message.author.display_avatar.url)
        
        await interaction.response.send_message(embed=embed)

    @app_commands.guilds(*APP_GUILDS_IDS)
    async def embed_colour(
        self, 
        interaction: discord.Interaction, 
        message: discord.Message
    ) -> None:

        all_embeds = list()
        counter = 0

        if message.embeds:
            for embed in message.embeds:
                counter += 1
                nembed = discord.Embed(
                    colour=embed.colour,
                    description=f"{embed.colour} - [`{embed.colour.value}`](https:/www.google.com)")
                all_embeds.append(nembed)

        if counter:
            return await interaction.response.send_message(embeds=all_embeds)

        await interaction.response.send_message(content="No embeds were found within this message.", ephemeral=True)

    @app_commands.command(name='bored', description="Find something to do if you're bored")
    @app_commands.guilds(*APP_GUILDS_IDS)
    @app_commands.describe(activity_type='The type of activities to filter by.')
    async def prompt_act(
        self, 
        interaction: discord.Interaction, 
        activity_type: Optional[
            Literal[
                "education", "recreational", "social", "diy", 
                "charity", "cooking", "relaxation", "music", "busywork"
            ]
        ] = ""
    ) -> None:
        
        if activity_type:
            activity_type = f"?type={activity_type}"
        
        async with self.bot.session.get(f"http://www.boredapi.com/api/activity{activity_type}") as response:
            if response.status != 200:
                return await interaction.response.send_message(embed=membed(API_EXCEPTION))
            
            resp = await response.json()
            await interaction.response.send_message(embed=membed(f"{resp['activity']}."))

    anime = app_commands.Group(
        name='anime', 
        description="Surf through anime images and posts.", 
        guild_only=True, 
        guild_ids=APP_GUILDS_IDS
    )

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

    @anime.command(name='kona', description='Retrieve NSFW posts from Konachan')
    @app_commands.rename(length="max_images")
    @app_commands.describe(
        tag1='A tag to base your search on.', 
        tag2='A tag to base your search on.',
        tag3='A tag to base your search on.' ,
        private='Hide the results from others. Defaults to True.',
        length='The maximum number of images to display at once. Defaults to 3.',
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
        page: Optional[app_commands.Range[int, 1]] = 1
    ) -> None:
        
        tags = [val for _, val in iter(interaction.namespace) if isinstance(val, str)]
        tagviewing = ' '.join(tags)

        posts_xml = await self.retrieve_via_kona(
            tags=tagviewing, 
            limit=9999, 
            page=page, 
            mode="post"
        )

        if isinstance(posts_xml, int):
            embed = membed("Failed to make this request.")
            embed.add_field(name="Cause", value=RESPONSES.get(posts_xml, "Not Known."))

            return await interaction.response.send_message(embed=embed)

        if not len(posts_xml):

            return await interaction.response.send_message(
                ephemeral=True,
                embed=membed(
                    "## No posts found.\n"
                    "- There are a few known causes:\n"
                    " - Entering an invalid tag name.\n"
                    " - Accessing some posts under the `copyright` tag.\n"
                    " - There are no posts found under this tag.\n"
                    " - The page requested exceeds the max length.\n"
                    "- You can find a tag by using /tagsearch "
                    "or [the website.](https://konachan.net/tag)"
                )
            )

        paginator = Pagination(interaction)

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
                embed = discord.Embed(
                    timestamp=datetime.datetime.fromtimestamp(item_attrs[-1]),
                    title=item_attrs[1],
                    url=item_attrs[0],
                    colour=0x2B2D31
                )

                embed.set_image(url=item_attrs[0])
                embeds.append(embed)

            n = paginator.compute_total_pages(len(additional_notes), length)
            return embeds, n
        
        paginator.get_page = get_page_part

        await paginator.navigate(ephemeral=private)

    @anime.command(name='char', description="Retrieve SFW or NSFW anime images")
    @app_commands.checks.dynamic_cooldown(owners_nolimit)
    @app_commands.describe(filter_by='The type of image to retrieve.')
    async def get_via_nekos(
        self, 
        interaction: discord.Interaction, 
        filter_by: Optional[
            Literal[
                "neko", "kitsune", "waifu", "husbando", "ai", "ass", "boobs", 
                "creampie", "paizuri", "pussy", "random", "ecchi", "fucking"
            ]
        ]
    ) -> None:

        api_urls = {
            "neko": ("https://nekos.best/api/v2/neko", 'https://nekos.pro/api/neko'),
            "kitsune": ("https://nekos.best/api/v2/kitsune",),
            "waifu": ("https://nekos.best/api/v2/waifu",),
            "husbando": ("https://nekos.best/api/v2/husbando",),
            "ai": "https://nekos.pro/api/ai",
            "ass": "https://nekos.pro/api/ass",
            "boobs": "https://nekos.pro/api/boobs",
            "creampie": "https://nekos.pro/api/creampie",
            "paizuri": "https://nekos.pro/api/paizuri",
            "pussy": "https://nekos.pro/api/pussy",
            "random": "https://nekos.pro/api/random",
            "ecchi": "https://nekos.pro/api/ecchi",
            "fucking": "https://nekos.pro/api/fucking"
        }

        if filter_by is None:
            filter_by = "neko"
        api_urls = api_urls.get(filter_by)

        if (isinstance(api_urls, str)) and (not interaction.channel.is_nsfw()):
            return await interaction.response.send_message(
                ephemeral=True,
                embed=membed("This API endpoint **must** be used within an NSFW channel.")
            )
        
        if isinstance(api_urls, tuple):
            api_urls = choice(api_urls)
        
        async with self.bot.session.get(api_urls) as resp:
            if resp.status != 200:
                return await interaction.response.send_message(embed=membed(API_EXCEPTION))

            embed = discord.Embed(colour=discord.Colour.from_rgb(243, 157, 30))
            data = await resp.json()

            if (extract_domain(api_urls) == "nekos.pro") and (not api_urls.endswith("ai")):
                embed.set_author(name=f"{data.setdefault('character_name', 'Unknown Source')}")
                embed.set_image(url=data["url"])
                embed.set_footer(text=f"ID: {data.get('id', 'Unknown ID')}")
            
            elif extract_domain(api_urls) == "nekos.best":
                data = data["results"][0]
                embed.set_author(name=f"{data['artist_name']}")
                embed.set_image(url=data["url"])
            
            else:
                embed.set_image(url=data["url"])
                embed.set_footer(text=f"ID: {data.get('id', 'Unknown ID')}")

            img_view = discord.ui.View()
            img_view.add_item(ImageSourceButton(url=data["url"]))

            await interaction.response.send_message(embed=embed, view=img_view)

    @anime.command(name='random', description="Get a completely random waifu image")
    @app_commands.checks.dynamic_cooldown(owners_nolimit)
    async def waifu_random_fetch(self, interaction: discord.Interaction) -> None:

        is_nsfw = interaction.channel.is_nsfw()

        try:
            image = await self.wf.search(is_nsfw=is_nsfw)
        except APIException as ae:
            return await interaction.response.send_message(ae.detail)

        embed = discord.Embed(
            colour=discord.Colour.from_rgb(243, 157, 30), 
            description=(
                f"Made <t:{int(image.uploaded_at.timestamp())}:R>\n"
                f"NSFW Toggle Enabled: {is_nsfw}\n"
                f"Tags: "
            )
        )

        embed.set_author(name=image.artist or 'Unknown Source')
        tags = set()
        for item in image.tags:
            tags.add(item.name)

        embed.description += ", ".join(tags)
        embed.set_image(url=image.url)

        img_view = discord.ui.View()
        img_view.add_item(ImageSourceButton(url=image.url))        

        await interaction.response.send_message(embed=embed, view=img_view)

    @anime.command(name='filter', description="Filter from SFW waifu images to send")
    @app_commands.describe(
        waifu="Include a female anime/manga character.",
        maid="Include women/girls employed to do work in their uniform.",
        marin_kitagawa="Include marin from My Dress-Up Darling.",
        mori_calliope="Include the english VTuber Mori.",
        raiden_shogun="Include the electro archon from Genshin Impact.",
        oppai="Include oppai within the sfw range.",
        selfies="Include photo-like image of a waifu.",
        uniform="Include girls wearing any kind of uniform.")
    @app_commands.checks.dynamic_cooldown(owners_nolimit)
    async def filter_waifu_search(
        self, 
        interaction: discord.Interaction, 
        waifu: Optional[bool], 
        maid: Optional[bool], 
        marin_kitagawa: Optional[bool], 
        mori_calliope: Optional[bool], 
        raiden_shogun: Optional[bool], 
        oppai: Optional[bool], 
        selfies: Optional[bool], 
        uniform: Optional[bool]
    ) -> None:

        tags = [param.replace('_', '-') for param, _ in iter(interaction.namespace)]

        if not tags:
            return await interaction.response.send_message(
                ephemeral=True,
                embed=membed("You need to include at least 1 tag.")
            )

        try:
            image = await self.wf.search(included_tags=tags, is_nsfw=False)
        except APIException as ae:
            return await interaction.response.send_message(embed=membed(ae.detail))

        embed = discord.Embed(
            colour=discord.Colour.from_rgb(243, 157, 30), 
            description=(
                f"Made <t:{int(image.uploaded_at.timestamp())}:R>\n"
                "Tags: "
            )
        )

        embed.set_author(name=image.artist or 'Unknown Source')
        tags = set()
        for item in image.tags:
            tags.add(item.name)
        embed.description += ", ".join(tags)
        embed.set_image(url=image.url)

        img_view = discord.ui.View()
        img_view.add_item(ImageSourceButton(url=image.url))

        await interaction.response.send_message(embed=embed, view=img_view)

    @app_commands.command(name='emojis', description='Fetch all the emojis c2c can access')
    @app_commands.guilds(*APP_GUILDS_IDS)
    async def emojis_paginator(self, interaction: discord.Interaction) -> None:
        length = 10
        emotes_all = []
        for i in self.bot.emojis:
            if i.animated:
                fmt = "<a:"
            else:
                fmt = "<:"
            needed = f"{i} (**{i.name}**) - `{fmt}{i.name}:{i.id}>`"
            emotes_all.append(needed)

        paginator = Pagination(interaction)

        async def get_page_part(page: int):
            emb = discord.Embed(
                colour=0x2B2D31,
                title="Emojis", 
                description=(
                    "> This is a command that fetches **all** of the emojis found"
                    " in the bot's internal cache and their associated atributes.\n\n"
                )
            )

            offset = (page - 1) * length
            for user in emotes_all[offset:offset + length]:
                emb.description += f"{user}\n"
            emb.set_author(
                name=interaction.guild.me.name, 
                icon_url=interaction.guild.me.display_avatar.url
            )
            n = paginator.compute_total_pages(len(emotes_all), length)
            return emb, n

        paginator.get_page = get_page_part

        await paginator.navigate()

    @app_commands.command(name='inviter', description='Creates a server invite link')
    @app_commands.guilds(*APP_GUILDS_IDS)
    @app_commands.default_permissions(create_instant_invite=True)
    @app_commands.describe(
        invite_lifespan='A non-zero duration in days for which the invite should last for.', 
        maximum_uses='The maximum number of uses for the created invite.'
    )
    async def gen_new_invite(
        self, 
        interaction: discord.Interaction, 
        invite_lifespan: app_commands.Range[int, 1], 
        maximum_uses: int
    ) -> None:

        maximum_uses = abs(maximum_uses)
        invite_lifespan *= 86400

        generated_invite = await interaction.channel.create_invite(
            reason=f'Invite creation requested by {interaction.user.name}',
            max_age=invite_lifespan, 
            max_uses=maximum_uses
        )

        match maximum_uses:
            case 0:
                maxim_usage = "No limit to maximum usage"
            case _:
                maxim_usage = f"Max usages set to {generated_invite.max_uses}"
        
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
    @app_commands.guilds(*APP_GUILDS_IDS)
    @app_commands.checks.dynamic_cooldown(owners_nolimit)
    async def random_fact(self, interaction: discord.Interaction) -> None:
        api_url = 'https://api.api-ninjas.com/v1/facts'
        parameters = {'X-Api-Key': self.bot.NINJAS_API_KEY}
        
        async with self.bot.session.get(api_url, params=parameters) as resp:
            if resp.status != 200:
                return await interaction.response.send_message(embed=membed(API_EXCEPTION))
            text = await resp.json()
            await interaction.response.send_message(embed=membed(f"{text[0]['fact']}."))

    async def format_api_response(
        self, 
        interaction: discord.Interaction, 
        start: float, 
        api_url: str, 
        **attrs
    ) -> Union[None, discord.WebhookMessage]:
        async with self.bot.session.get(api_url, **attrs) as response:  # params=params, headers=headers
            if response.status == 200:
                buffer = BytesIO(await response.read())
                end = perf_counter()
                return await interaction.followup.send(
                    content=f"Done. Took ` {end-start:.2f}s `.", 
                    file=discord.File(buffer, 'clip.gif')
                )

            await interaction.followup.send(embed=membed(API_EXCEPTION))

    @app_commands.command(name="image", description="Manipulate a user's avatar")
    @app_commands.describe(
        user="The user to apply the manipulation to.", 
        endpoint="What kind of manipulation sorcery to use."
    )
    @app_commands.guilds(*APP_GUILDS_IDS)
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

        await self.format_api_response(
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
    @app_commands.guilds(*APP_GUILDS_IDS)
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
    ) -> Union[discord.InteractionMessage, None]:

        start = perf_counter()
        await interaction.response.defer(thinking=True)

        user = user or interaction.user
        params = {'image_url': user.display_avatar.url}
        headers = {'Authorization': f'Bearer {self.bot.JEYY_API_KEY}'}
        api_url = f"https://api.jeyy.xyz/v2/image/{endpoint}"

        await self.format_api_response(
            interaction,
            start=start,
            api_url=api_url,
            params=params,
            headers=headers
        )

    @app_commands.command(name="locket", description="Insert people into a heart-shaped locket")
    @app_commands.describe(user="The user to add to the locket.", user2="The second user to add to the locket.")
    @app_commands.guilds(*APP_GUILDS_IDS)
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

        await self.format_api_response(
            interaction,
            start=start,
            api_url=api_url,
            params=params,
            headers=headers
        )

    @app_commands.command(name='charinfo', description='Show information about characters')
    @app_commands.guilds(*APP_GUILDS_IDS)
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
    @app_commands.guilds(*APP_GUILDS_IDS)
    async def feedback(self, interaction: discord.Interaction) -> None:
        feedback_modal = FeedbackModal()
        await interaction.response.send_modal(feedback_modal)

    @app_commands.command(name='about', description='Learn more about the bot')
    @app_commands.guilds(*APP_GUILDS_IDS)
    @app_commands.checks.cooldown(1, 10, key=lambda i: i.guild.id)
    async def about_the_bot(self, interaction: discord.Interaction) -> None:

        await interaction.response.defer(thinking=True)
        lentxt = len(self.bot.commands)
        self.bot.command_count = self.bot.command_count or (len(await self.bot.tree.fetch_commands(guild=discord.Object(id=interaction.guild.id))) + 1 + lentxt)
        lenslash = self.bot.command_count - lentxt

        repo = self.g.get_repo('SGA-A/c2c')

        commits = repo.get_commits()[:3]

        revision = [
            f"[`{commit.sha[:6]}`]({commit.html_url}) {commit.commit.message.splitlines()[0]} "
            f"({format_relative(commit.commit.author.date)})"
            for commit in commits
        ]

        embed = discord.Embed(
            description=(
                f'Latest Changes:\n'
                f'{"\n".join(revision)}'
            )
        )
        
        embed.title = 'Official Bot Server Invite'
        embed.url = 'https://discord.gg/W3DKAbpJ5E'
        embed.colour = discord.Colour.blurple()

        geo = self.bot.get_user(546086191414509599)
        embed.set_author(name=geo.name, icon_url=geo.display_avatar.url)

        total_members = 0
        total_unique = len(self.bot.users)

        text = 0
        voice = 0
        guilds = 0

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

        diff = datetime.datetime.now() - self.bot.time_launch
        minutes, seconds = divmod(diff.total_seconds(), 60)
        hours, minutes = divmod(minutes, 60)
        days, hours = divmod(hours, 24)

        embed.add_field(
            name='<:membersb:1195752573555183666> Members',
            value=f'{total_members} total\n{total_unique} unique'
        )

        embed.add_field(
            name='<:channelb:1195752572116541590> Channels', 
            value=f'{text + voice} total\n{text} text\n{voice} voice'
        )

        embed.add_field(
            name='<:processb:1195752570069713047> Process', 
            value=f'{memory_usage:.2f} MiB\n{cpu_usage:.2f}% CPU'
        )

        embed.add_field(
            name='<:serversb:1195752568303927377> Guilds', 
            value=(
                f'{guilds} total\n'
                f'{ARROW}{len(self.bot.emojis)} emojis\n'
                f'{ARROW}{len(self.bot.stickers)} stickers'
            )
        )

        embed.add_field(
            name='<:cmdsb:1195752574821879872> Commands', 
            value=(
                f'{self.bot.command_count} total\n'
                f'{ARROW}{lentxt} (prefix)\n'
                f'{ARROW}{lenslash} (slash)'
            )
        )

        embed.add_field(
            name='<:uptimeb:1195752565208522812> Uptime', 
            value=f"{int(days)}d {int(hours)}h {int(minutes)}m {int(seconds)}s"
        )

        embed.set_footer(text=f'Made with discord.py v{discord.__version__}', icon_url='http://i.imgur.com/5BFecvA.png')
        await interaction.followup.send(embed=embed)

    @commands.command(name="pickupline", description="Get pick up lines to use", aliases=('pul',))
    async def pick_up_lines(self, ctx: commands.Context) -> Union[None, discord.Message]:
        async with ctx.typing():
            async with self.bot.session.get("https://api.popcat.xyz/pickuplines") as resp:
                if resp.status != 200:
                    return await ctx.send(embed=membed(API_EXCEPTION))
                data = await resp.json()
                await ctx.reply(embed=membed(data["pickupline"]))

    @commands.command(name="wyr", description="Get 'would you rather' questions to use")
    async def would_yr(self, ctx: commands.Context) -> Union[None, discord.Message]:
        async with ctx.typing():
            async with self.bot.session.get("https://api.popcat.xyz/wyr") as resp:
                if resp.status != 200:
                    return await ctx.send(embed=membed(API_EXCEPTION))
                data = await resp.json()
                await ctx.reply(
                    embed=membed(
                        f'Would you rather:\n'
                        f'1. {data["ops1"].capitalize()} or..\n'
                        f'2. {data["ops2"].capitalize()}'
                    )
                )

    @commands.command(name="alert", description="Create real incoming iphone alerts")
    async def alert_iph(self, ctx: commands.Context, *, custom_text: str) -> Union[None, discord.Message]:
        async with ctx.typing():
            custom_text = '+'.join(custom_text.split(' '))
            async with self.bot.session.get(f"https://api.popcat.xyz/alert?text={custom_text}") as resp:
                if resp.status != 200:
                    return await ctx.send(embed=membed(API_EXCEPTION))
                embed: discord.Embed = membed()
                embed.set_image(url=resp.url)
                await ctx.send(embed=embed)

    @commands.command(name='avatar', description="Display a user's enlarged avatar")
    async def avatar(self, ctx, *, username: Union[discord.Member, discord.User] = None) -> None:
        """Shows a user's enlarged avatar (if possible)."""
        embed = discord.Embed(colour=0x2B2D31)
        username = username or ctx.author
        avatar = username.display_avatar.with_static_format('png')
        embed.set_author(name=username.name, url=username.display_avatar.url)
        embed.set_image(url=avatar)
        await ctx.send(embed=embed)

    @commands.command(name='banner', description="Display a user's enlarged banner")
    async def banner(
        self, 
        ctx: commands.Context, 
        *, 
        username: Union[discord.Member, discord.User] = commands.Author
    ) -> Union[None, discord.Message]:
        """Shows a user's enlarged avatar (if possible)."""
        embed = membed()
        
        if not username.banner:
            embed.description = f"{username.mention} does not have a banner."
            return await ctx.send(embed=embed)

        embed.set_author(name=username.name, url=username.display_avatar.url)
        embed.set_image(url=username.banner.with_static_format('png'))
        await ctx.send(embed=embed)

    @app_commands.checks.cooldown(1, 15, key=lambda i: i.guild.id)
    @app_commands.guilds(*APP_GUILDS_IDS)
    @app_commands.command(name="imagesearch", description="Browse images from the web")
    @app_commands.describe(
        query="The search query to use for the image search.",
        image_type="The type of image to search for. Defaults to photo.",
        limit="The maximum number of images to retrieve. Defaults to 5.",
        image_colour="The colour of the image to search for. Defaults to colour.",
        from_only="[Limited to Bot Owner] Search from this website only.",
        image_size="The size of the image. Defaults to medium."
    )
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
                    embed=membed("You are not allowed to use this feature.")
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

        em = membed(f"- Estimated Results: {results_count}\n- Search Time: {search_time}ms")

        em.set_author(name=user.name, icon_url=user.display_avatar.url)
        paginator = PaginationSimple(
            interaction, 
            invoker_id=user.id
        )
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


async def setup(bot: commands.Bot):
    await bot.add_cog(Utility(bot))
