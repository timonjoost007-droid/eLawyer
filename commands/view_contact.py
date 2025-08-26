import discord
from discord import app_commands
import database
from datetime import datetime
import settings

# ---- Helper Function to Build Contact Embed ----
async def build_contact_embed(contact_id):
    contact = database.get_contact_by_id(contact_id)
    cases = database.get_cases_for_contact(contact_id)

    case_list = "\n".join([f"- {c[1]} (ID {c[0]}) as **{c[2]}**" for c in cases]) or "None linked"

    embed = discord.Embed(
        title=f"📇 Contact {contact[0]}: {contact[1]}",
        color=discord.Color.purple(),
        timestamp=datetime.now()
    )
    embed.add_field(name="Contact", value=contact[2] or "None", inline=False)
    embed.add_field(name="Notes", value=contact[3] or "None", inline=False)
    embed.add_field(name="Status", value=contact[4] or "None", inline=False)
    embed.add_field(name="Discord User", value=f"<@{contact[5]}>" if contact[5] else "None", inline=False)
    embed.add_field(name="Cases Linked", value=case_list, inline=False)
    embed.set_footer(text=f"Created at {contact[6]}")

    return embed


# ---- Helper Function to Update Forum Post + Log ----
async def update_contact_post(interaction: discord.Interaction, contact_id: str, action_description: str):
    """
    Updates the starter embed of the contact thread and logs an action message.
    """
    contact = database.get_contact_by_id(contact_id)
    if not contact or not contact[6] or not contact[7]:
        print(f"Error updating contact post: no thread/message link")
        return  # missing forum thread link

    print(contact)
    print(contact[6], contact[7])
    thread_id = int(contact[6])
    starter_message_id = int(contact[7])

    thread = interaction.client.get_channel(thread_id)
    if not thread:
        return

    # --- Update starter embed ---
    try:
        starter_message = await thread.fetch_message(starter_message_id)
        embed = await build_contact_embed(contact_id)
        await starter_message.edit(embed=embed)
    except Exception as e:
        print(f"Error updating contact post: {e}")

    # --- Log action in the thread ---
    log_embed = discord.Embed(
        title="📝 Contact Log",
        description=action_description,
        color=discord.Color.orange(),
        timestamp=datetime.utcnow()
    )
    log_embed.set_author(name=str(interaction.user), icon_url=interaction.user.display_avatar.url)
    log_embed.set_footer(text=f"Contact ID: {contact_id}")

    await thread.send(embed=log_embed)


# ---- Modal for Editing Contact ----
class EditContactModal(discord.ui.Modal, title="Edit Contact"):
    def __init__(self, contact_id, contact):
        super().__init__()
        self.contact_id = contact_id

        self.name = discord.ui.TextInput(
            label="Name", default=contact[1], required=True, max_length=100
        )
        self.contact = discord.ui.TextInput(
            label="Contact", default=contact[2] or "", required=False,
            style=discord.TextStyle.paragraph, max_length=200
        )
        self.notes = discord.ui.TextInput(
            label="Notes", default=contact[3] or "", required=False,
            style=discord.TextStyle.paragraph, max_length=500
        )
        self.status = discord.ui.TextInput(
            label="Status", default=contact[4], required=True, max_length=50
        )
        self.discord_id = discord.ui.TextInput(
            label="Discord User ID (optional)",
            default=contact[5] if contact[5] else "",
            required=False,
            placeholder="Enter Discord user ID to link this contact"
        )

        self.add_item(self.name)
        self.add_item(self.contact)
        self.add_item(self.notes)
        self.add_item(self.status)
        self.add_item(self.discord_id)

    async def on_submit(self, interaction: discord.Interaction):
        discord_user_id = self.discord_id.value.strip() if self.discord_id.value else None

        database.update_contact(
            self.contact_id,
            self.name.value,
            self.contact.value,
            self.notes.value,
            self.status.value,
            discord_user_id
        )

        action_description = (
            f"Contact updated:\n"
            f"• **Name:** {self.name.value}\n"
            f"• **Contact:** {self.contact.value or 'N/A'}\n"
            f"• **Notes:** {self.notes.value or 'N/A'}\n"
            f"• **Status:** {self.status.value}\n"
            f"• **Discord:** {f'<@{discord_user_id}>' if discord_user_id else 'None'}"
        )

        await update_contact_post(interaction, self.contact_id, action_description)

        await interaction.response.send_message(
            f"✅ Contact `{self.contact_id}` updated!",
            ephemeral=True
        )


# ---- Buttons View ----
class ContactView(discord.ui.View):
    def __init__(self, contact_id, contact):
        super().__init__(timeout=None)
        self.contact_id = contact_id
        self.contact = contact

    @discord.ui.button(label="Edit Contact", style=discord.ButtonStyle.primary)
    async def edit_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(EditContactModal(self.contact_id, self.contact))

    @discord.ui.button(label="Delete Contact", style=discord.ButtonStyle.danger)
    async def delete_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        allowed_role = discord.utils.get(interaction.user.roles, id=settings.MANAGER_ROLE_ID)
        if not allowed_role:
            await interaction.response.send_message("❌ You do not have permission.", ephemeral=True)
            return

        contact = database.get_contact_by_id(self.contact_id)
        if not contact:
            await interaction.response.send_message(
                f"No contact found with ID `{self.contact_id}`.",
                ephemeral=True
            )
            return

        # Log deletion in the thread
        await update_contact_post(interaction, self.contact_id, f"❌ Contact `{contact[1]}` deleted by {interaction.user.mention}")

        # Delete contact in DB
        database.delete_contact(self.contact_id)

        await interaction.response.send_message(
            f"Contact `{self.contact_id}` deleted.",
            ephemeral=True
        )



# ---- Command Setup ----
async def setup(bot):
    @bot.tree.command(name="view_contact", description="View details of a contact/party by ID.")
    @app_commands.describe(contact_id="The ID of the contact to view")
    async def view_contact(interaction: discord.Interaction, contact_id: str):
        allowed_role = discord.utils.get(interaction.user.roles, id=settings.EMPLOYEE_ROLE_ID)
        if not allowed_role:
            # Not allowed
            await interaction.response.send_message("❌ You do not have permission.", ephemeral=True)
            return
        contact = database.get_contact_by_id(contact_id)
        if not contact:
            await interaction.response.send_message(
                f"No contact found with ID `{contact_id}`.",
                ephemeral=True
            )
            return

        cases = database.get_cases_for_contact(contact_id)
        case_list = "\n".join([f"- {c[1]} (ID {c[0]}) as **{c[2]}**" for c in cases]) or "None linked"

        embed = discord.Embed(
            title=f"Contact Details: {contact[1]}",
            color=discord.Color.purple()
        )
        embed.add_field(name="ID", value=contact[0], inline=False)
        embed.add_field(name="Contact", value=contact[2] or "None", inline=False)
        embed.add_field(name="Notes", value=contact[3] or "None", inline=False)
        embed.add_field(name="Status", value=contact[4] or "None", inline=False)
        embed.add_field(name="Discord User", value=f"<@{contact[5]}>" if contact[5] else "None", inline=False)
        embed.add_field(name="Created At", value=contact[6], inline=False)
        embed.add_field(name="Cases Linked", value=case_list, inline=False)

        view = ContactView(contact_id, contact)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
