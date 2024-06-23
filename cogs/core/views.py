from typing import Optional
import discord

from .helpers import economy_check, respond, membed


class Confirm(discord.ui.View):
    def __init__(self, controlling_user: discord.abc.User):
        self.controlling_user = controlling_user
        super().__init__(timeout=10.0)
        self.value = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return await economy_check(interaction, self.controlling_user)

    @discord.ui.button(label='Cancel', style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = False
        self.stop()

        self.children[1].style = discord.ButtonStyle.secondary
        button.style = discord.ButtonStyle.success
        
        for item in self.children:
            item.disabled = True
        
        embed = interaction.message.embeds[0]
        embed.title = "Action Cancelled"
        embed.colour = discord.Colour.brand_red()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label='Confirm', style=discord.ButtonStyle.success)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = True
        self.stop()

        self.children[0].style = discord.ButtonStyle.secondary
        button.style = discord.ButtonStyle.success

        for item in self.children:
            item.disabled = True
        
        embed = interaction.message.embeds[0]
        embed.title = "Action Confirmed"
        embed.colour = discord.Colour.brand_green()
        await interaction.response.edit_message(embed=embed, view=self)


async def process_confirmation(
    interaction: discord.Interaction, 
    prompt: str, 
    view_owner: Optional[discord.Member] = None, 
    **kwargs
) -> bool:
    """
    Process a confirmation. This only updates the view.
    
    The actual action is done in the command itself.

    This returns a boolean indicating whether the user confirmed the action or not, or None if the user timed out.
    """

    view = Confirm(controlling_user=view_owner or interaction.user)
    confirm = membed(prompt)
    confirm.title = "Pending Confirmation"

    resp = await respond(interaction, embed=confirm, view=view, **kwargs)
    await view.wait()
    
    if view.value is None:
        msg = resp or await interaction.original_response()
        embed = msg.embeds[0]

        for item in view.children:
            item.disabled = True

        embed.title = "Timed Out"
        embed.description = f"~~{embed.description}~~"
        embed.colour = discord.Colour.brand_red()
        await msg.edit(embed=embed, view=view)
    return view.value


class MessageDevelopers(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60.0)

        self.add_item(
            discord.ui.Button(
                label="Contact a developer", 
                url="https://www.discordapp.com/users/546086191414509599"
            )
        )


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
