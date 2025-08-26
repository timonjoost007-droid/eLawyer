import discord
from discord import app_commands
import database
import settings
from datetime import datetime

class ContactModal(discord.ui.Modal, title="Add Contact"):
    name = discord.ui.TextInput(label="Name", required=True, max_length=100)
    contact = discord.ui.TextInput(label="Contact", required=False, style=discord.TextStyle.paragraph, max_length=200)
    notes = discord.ui.TextInput(label="Notes", required=False, style=discord.TextStyle.paragraph, max_length=500)
    status = discord.ui.TextInput(label="Status", required=True, placeholder="Client / VIP / Of Interest", max_length=50)
    discord_id = discord.ui.TextInput(
        label="Discord User ID (optional)",
        required=False,
        placeholder="Enter Discord user ID to link this contact"
    )

    async def on_submit(self, interaction: discord.Interaction):
        # Convert empty string to None
        discord_user_id = self.discord_id.value.strip() if self.discord_id.value else None

        # Get contacts forum
        forum_channel = interaction.client.get_channel(settings.CONTACTS_FORUM_CHANNEL_ID)
        if forum_channel is None:
            await interaction.response.send_message(
                "⚠️ Contacts forum channel not found. Please check settings.CONTACTS_FORUM_CHANNEL_ID.",
                ephemeral=True
            )
            return

        # Step 1: Create placeholder thread
        created = await forum_channel.create_thread(
            name=f"{self.name.value}",
            content="📌 Contact created via bot."
        )

        contact_thread = created.thread
        starter_message = created.message

        # Step 2: Save in DB (with channel + message IDs)
        contact_id = database.insert_contact(
            self.name.value,
            self.contact.value,
            self.notes.value,
            self.status.value,
            discord_user_id,
            str(contact_thread.id),
            str(starter_message.id)
        )

        # Step 3: Build embed (now including contact_id)
        embed = discord.Embed(
            title=f"👤 {self.name.value}",
            description=f"🆔 **Contact ID:** `{contact_id}`\n📌 **Status:** {self.status.value}",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        if self.contact.value:
            embed.add_field(name="Contact Info", value=self.contact.value, inline=False)
        if self.notes.value:
            embed.add_field(name="Notes", value=self.notes.value, inline=False)
        if discord_user_id:
            embed.add_field(name="Linked Discord", value=f"<@{discord_user_id}>", inline=False)

        # Update the starter message with the final embed
        await starter_message.edit(content="📌 Contact created via bot:", embed=embed)

        # Confirm to user
        await interaction.response.send_message(
            f"✅ Contact added!\nID: `{contact_id}`\nName: `{self.name.value}`"
            f"\n🔗 Linked forum post: {contact_thread.mention}"
            + (f"\nDiscord: <@{discord_user_id}>" if discord_user_id else ""),
            ephemeral=True
        )


async def setup(bot):
    @bot.tree.command(name="add_contact", description="Add a new contact/party.")
    async def add_contact(interaction: discord.Interaction):
        allowed_role = discord.utils.get(interaction.user.roles, id=settings.EMPLOYEE_ROLE_ID)
        if not allowed_role:
            # Not allowed
            await interaction.response.send_message("❌ You do not have permission.", ephemeral=True)
            return
       # Allowed
        await interaction.response.send_modal(ContactModal())
