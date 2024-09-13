from re import compile
from typing import Callable, Any, Optional
from datetime import datetime, timedelta

import discord
from pytz import timezone
from asqlite import Connection
from discord.ext.commands import Context


async def declare_transaction(conn: Connection, /, *, user_id: int) -> bool:
    await conn.execute("INSERT INTO transactions (userID) VALUES ($0) ON CONFLICT DO NOTHING", user_id)

async def end_transaction(conn: Connection, /, *, user_id: int) -> bool:
    await conn.execute("DELETE FROM transactions WHERE userID = $0", user_id)


def membed(custom_description: Optional[str] = None, /) -> discord.Embed:
    """Quickly construct an embed with an optional description."""
    membedder = discord.Embed(colour=0x2B2D31, description=custom_description)
    return membedder


async def economy_check(interaction: discord.Interaction, original_id: int, /) -> bool:
    """Shared interaction check common amongst most interactions."""
    if original_id == interaction.user.id:
        return True
    await interaction.response.send_message(
        ephemeral=True,
        delete_after=5.0,
        embed=membed("This menu is not for you")
    )
    return False


class BaseInteractionView(discord.ui.View):
    """
    A view that ensures that only the interaction creator can make use of this view.

    It also destroys the view if an exception is raised.

    This view has no items, you'll need to add them in manually.
    """
    def __init__(
        self,
        interaction: discord.Interaction,
        controlling_user: Optional[discord.User] = None
    ) -> None:
        self.interaction = interaction
        self.controlling_user = controlling_user or interaction.user
        super().__init__(timeout=45.0)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return await economy_check(interaction, self.controlling_user.id)

    async def on_error(
        self,
        interaction: discord.Interaction,
        error: Exception,
        item: discord.ui.Item[Any],
        /
    ) -> None:
        try:
            await self.interaction.edit_original_response(view=None)
        except discord.HTTPException:
            pass
        if not self.is_finished():
            self.stop()
        await super().on_error(interaction, error, item)


class BaseContextView(discord.ui.View):
    """
    A view that ensures that only the command author can make use of this view.

    This view has no items, you'll need to add them in manually.
    """
    def __init__(self, ctx, /, controlling_user: Optional[discord.User] = None) -> None:
        self.ctx = ctx
        self.controlling_user = controlling_user or ctx.author
        super().__init__(timeout=45.0)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return await economy_check(interaction, self.controlling_user.id)

    async def on_error(
        self,
        interaction: discord.Interaction,
        error: Exception,
        item: discord.ui.Item[Any],
        /
    ) -> None:
        try:
            await self.interaction.edit_original_response(view=None)
        except discord.HTTPException:
            pass
        if not self.is_finished():
            self.stop()
        await super().on_error(interaction, error, item)


class MessageDevelopers(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=5.0)

        self.add_item(
            discord.ui.Button(
                label="Contact a developer",
                url="https://www.discordapp.com/users/546086191414509599"
            )
        )


class ConfirmButton(discord.ui.Button):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.success, label="Confirm")

    async def callback(self, interaction: discord.Interaction) -> None:
        self.view.value = True
        self.view.stop()

        embed = interaction.message.embeds[0]
        embed.title = "Action Confirmed"
        embed.colour = discord.Colour.brand_green()

        await interaction.response.edit_message(embed=embed, view=self.disable_items(self.view, self))


class CancelButton(discord.ui.Button):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.danger, label="Cancel")

    async def callback(self, interaction: discord.Interaction) -> None:
        self.view.value = False
        self.view.stop()

        embed = interaction.message.embeds[0]
        embed.title = "Action Cancelled"
        embed.colour = discord.Colour.brand_red()

        await interaction.response.edit_message(embed=embed, view=self.disable_items(self.view, self))


class GenericModal(discord.ui.Modal):
    def __init__(self, title: str, **kwargs) -> None:

        self.interaction = None

        for keyword, arguments in kwargs.items():
            setattr(self.data, keyword, arguments)

        super().__init__(title=title, timeout=180.0)

    data = discord.ui.TextInput(label="\u2800")

    async def on_submit(self, interaction: discord.Interaction) -> None:
        self.interaction = interaction
        self.stop()


async def format_timeout_view(embed: discord.Embed, view: discord.ui.View, edit_meth: Callable):
    """
    Edits to the view and embed are in-place.

    `edit_meth` is the method to use when editing a message, since it's so variable between different contexts.
    """

    embed.colour = discord.Colour.brand_red()
    embed.description = f"~~{embed.description}~~"
    embed.title = "Timed Out"
    view.value = False

    for item in view.children:
        item.disabled = True

    try:
        await edit_meth(embed=embed, view=view)
    except discord.HTTPException:
        pass
    return False



# ! Existing function that may be used sometime in the future
def parse_duration(input_duration: str) -> datetime:
    # Define regular expression pattern to extract days and hours
    pattern = compile(r'(?:(\d+)d)? ?(?:(\d+)h)?')

    # Extract days and hours from the input duration using the pattern
    match = pattern.match(input_duration)

    days = int(match.group(1)) if match.group(1) else 0
    hours = int(match.group(2)) if match.group(2) else 0

    if days == 0 and hours == 0:
        raise ValueError("Invalid duration, years-duration and/or seconds-duration is unsupported.")

    duration = timedelta(days=days, hours=hours)

    # Check if the duration exceeds 14 days
    if duration.days > 14:
        raise ValueError("Duration cannot exceed 14 days.")

    return discord.utils.utcnow() + duration


def datetime_to_string(datetime_obj: datetime) -> str:
    """Convert a datetime object to a string object.

    Datetime will be converted to this format: %Y-%m-%d %H:%M:%S
    """

    return f"{datetime_obj:%Y-%m-%d %H:%M:%S}"


def number_to_ordinal(n: int) -> str:
    """Convert 01 to 1st, 02 to 2nd etc."""
    if 10 <= n % 100 <= 20:
        return f"{n}th"

    suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
    return f"{n}{suffix}"


def string_to_datetime(string_obj: str, date_format = "%Y-%m-%d %H:%M:%S") -> datetime:
    """Convert a string into a datetime object, using format specifiers in `date_format`"""

    my_datetime = datetime.strptime(string_obj, date_format)
    return my_datetime.replace(tzinfo=timezone("UTC"))


async def respond(interaction: discord.Interaction, /, **kwargs) -> Optional[discord.WebhookMessage]:
    """
    Responds to the interaction by sending a message.

    Considers whether or not this interaction was already responded to before.
    """
    if interaction.response.is_done():
        return await interaction.followup.send(**kwargs)
    await interaction.response.send_message(**kwargs)


async def edit_response(interaction: discord.Interaction, /, **kwargs) -> Optional[discord.InteractionMessage]:
    """
    Edit an interaction's original response message, which may be a response.

    Considers whether or not this interaction was already responded to before.
    """
    if interaction.response.is_done():
        return await interaction.edit_original_response(**kwargs)
    await interaction.response.edit_message(**kwargs)


async def send_message(invocation: Context | discord.Interaction, /, **kwargs) -> Optional[discord.WebhookMessage]:
    """
    For use when using a `discord.Interaction` or a `commands.Context`

    Hybrid commands should not be invoked this way.
    """
    if isinstance(invocation, discord.Interaction):
        return await respond(invocation, **kwargs)
    await invocation.send(**kwargs)


async def process_confirmation(
    interaction: discord.Interaction,
    /,
    prompt: str,
    view_owner: discord.Member | None = None,
    **kwargs
) -> bool:
    """
    Process a confirmation. This only updates the view.

    The actual action is done in the command itself.

    This returns a boolean indicating whether the user confirmed the action or not, or None if the user timed out.
    """

    confirm_view = BaseInteractionView(interaction, view_owner).add_item(CancelButton()).add_item(ConfirmButton())
    confirm_view.value = None
    confirm_embed = membed(prompt)
    confirm_embed.title = "Pending Confirmation"
    
    await respond(interaction, embed=confirm_embed, view=confirm_view, **kwargs)

    await confirm_view.wait()
    if confirm_view.value is None:
        await format_timeout_view(confirm_embed, confirm_view, confirm_view.interaction.edit_original_response)
    return confirm_view.value


async def send_boilerplate_confirm(ctx, /, prompt: str) -> bool:
    confirm_view = BaseContextView(ctx).add_item(CancelButton()).add_item(ConfirmButton())
    confirm_view.value = None
    confirm_embed = membed(prompt)
    confirm_embed.title = "Pending Confirmation"

    msg: discord.Message = await ctx.send(embed=confirm_embed, view=confirm_view)
    await confirm_view.wait()
    if confirm_view.value is None:
        await format_timeout_view(confirm_embed, confirm_view, msg.edit)
    return confirm_view.value


async def is_setting_enabled(conn: Connection, user_id: int, setting: str) -> bool:
    """Check if a user has a setting enabled."""

    query = "SELECT value FROM settings WHERE userID = $0 AND setting = $1"
    result, = await conn.fetchone(query, user_id, setting) or (0,)
    return bool(result)


async def handle_confirm_outcome(
    interaction: discord.Interaction,
    prompt: str,
    view_owner: Optional[discord.User] = None,
    setting: Optional[str] = None,
    conn: Optional[Connection] = None,
    **kwargs
) -> Optional[bool]:
    """
    Handle a confirmation outcome correctly, accounting for whether or not a specific confirmation is enabled.

    Setting names should be lowercase.

    ## Returns
    ### `None`
    - When the user doesn't have the specified confirmation enabled.
    - When you specify a specific confirmation setting to check but that user doesn't have it enabled.
    - if a specific confirmation was passed in and the user has it disabled.

    ### `True`
    - When the user has confirmed, either by confirming on a specific confirmation you passed in to check
    - When enabled specific setting, or through a generic confirmation that the user confirmed on.

    ### `False`
    - When user has not confirmed (the confirmation timed out or they explicitly denied)
    - Applicable for both specific and generic confirmations

    ## Notes

    Transactions will now be created if a passed in confirmation is enabled or no confirmation is passed in.

    Thus, only use this function in the economy system on a user who is registered.

    Because foreign key constraints require you to pass in a valid row of the accounts table.

    All connections acquired by or in the function will also be released in this function. Do not handle it yourself.
    """

    can_proceed = None
    view_owner = view_owner or interaction.user

    conn = conn or await interaction.client.pool.acquire()  # always hold a connection
    try:
        disabled_confirms = setting and not(await is_setting_enabled(conn, view_owner.id, setting))
        if disabled_confirms:
            return

        await declare_transaction(conn, user_id=view_owner.id)
        await conn.commit()
        await interaction.client.pool.release(conn)
        conn = None

        can_proceed = await process_confirmation(interaction, prompt, view_owner, **kwargs)
    finally:
        if conn:
            await interaction.client.pool.release(conn)
    return can_proceed