import discord
from discord import app_commands
from datetime import datetime
import database  # import your database module
import settings   # import config with CASE_FORUM_CHANNEL_ID

class CaseModal(discord.ui.Modal, title="Create Case"):
    case_name = discord.ui.TextInput(
        label="Case Name",
        placeholder="Enter case name",
        required=True,
        max_length=100
    )
    summary = discord.ui.TextInput(
        label="Summary",
        placeholder="Optional summary",
        required=False,
        style=discord.TextStyle.paragraph,
        max_length=4000
    )
    notes = discord.ui.TextInput(
        label="Notes",
        placeholder="Optional notes",
        required=False,
        style=discord.TextStyle.paragraph,
        max_length=4000
    )

    async def on_submit(self, interaction: discord.Interaction):
        # Generate unique case ID based on today's count
        today = datetime.now().strftime("%d%m%Y")
        count = database.count_cases_today(today)
        case_id = f"{count+1}-{today}"
        
        name = self.case_name.value
        summary = self.summary.value or ""
        notes = self.notes.value or ""

        # --- Create forum post for this case ---
        forum_channel = interaction.client.get_channel(settings.CASE_FORUM_CHANNEL_ID)
        if forum_channel is None:
            await interaction.response.send_message(
                "⚠️ Forum channel not found. Please check settings.CASE_FORUM_CHANNEL_ID.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title=f"📂 Case {case_id}: {name}",
            description=summary or "No summary provided",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )

        embed.add_field(name="Case ID", value=case_id, inline=False)
        embed.add_field(name="Notes", value=notes or "N/A", inline=False)
        embed.set_footer(text="Case created")

        # Create a forum thread/post with embed instead of plain content
        created = await forum_channel.create_thread(
            name=f"[{case_id}] {name}",
            embed=embed
        )

        case_thread = created.thread
        starter_message_id = created.message.id

        # Store both thread and starter message ID
        database.insert_case(case_id, name, summary, notes, str(case_thread.id), str(starter_message_id))

        # Confirm to user
        await interaction.response.send_message(
            f"✅ Case created!\nID: `{case_id}`\nName: `{name}`\n🔗 Linked forum post: {case_thread.mention}",
            ephemeral=True
        )

async def setup(bot):
    @bot.tree.command(name="create_case", description="Creates a new case with a form.")
    async def create_case(interaction: discord.Interaction):
        allowed_role = discord.utils.get(interaction.user.roles, id=settings.EMPLOYEE_ROLE_ID)
        if not allowed_role:
            # Not allowed
            await interaction.response.send_message("❌ You do not have permission.", ephemeral=True)
            return
        await interaction.response.send_modal(CaseModal())
