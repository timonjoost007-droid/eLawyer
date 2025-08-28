import discord
from discord import app_commands
import database
from datetime import datetime
import settings

# ---- Helper Function to Build Case Embed ----
async def build_case_embed(case_id):
    case = database.get_case_by_id(case_id)
    contacts = database.get_contacts_for_case(case_id)
    tasks = database.get_tasks_for_case(case_id)

    contact_list = "\n".join([f"- *{c[5]}* {c[1]} (ID {c[0]})" for c in contacts]) or "None linked"

    if tasks:
        task_lines = []
        for t in tasks:
            task_id, task_desc, deadline, done = t
            deadline_str = deadline or ""
            task_lines.append(f"- *#{task_id}* [{'✅' if done else '❌'}] {task_desc} {f'(Due: {deadline_str})' if deadline else ''}")
        task_list = "\n".join(task_lines)
    else:
        task_list = "No tasks."

    embed = discord.Embed(
        title=f"📂 Case {case[0]}: {case[1]}",
        description=case[2] or "No summary",
        color=discord.Color.blue(),
        timestamp=datetime.now()
    )
    embed.add_field(name="Notes", value=case[3] or "None", inline=False)
    embed.add_field(name="Contacts", value=contact_list, inline=False)
    embed.add_field(name="Tasks", value=task_list, inline=False)
    embed.set_footer(text=f"Created at {case[4]}")

    return embed

# ---- Helper Function to Build a case updated post ----
async def update_case_post(interaction: discord.Interaction, case_id: str, action_description: str):
    """
    Updates the starter embed of the case thread and logs an action message as a rich embed.
    Includes who performed the action and timestamp.
    """
    case = database.get_case_by_id(case_id)
    
    if not case or not case[4] or not case[5]:
        print(f"Error updating case post: no thread/message link")
        return  # missing thread/message link
    thread_id = int(case[4])
    starter_message_id = int(case[5])

    thread = interaction.client.get_channel(thread_id)
    if not thread:
        return

    # --- Update the starter embed ---
    try:
        starter_message = await thread.fetch_message(starter_message_id)
        embed = await build_case_embed(case_id)
        await starter_message.edit(embed=embed)
    except Exception as e:
        print(f"Error updating case post: {e}")

    # --- Log action as an embed ---
    log_embed = discord.Embed(
        title="📝 Case Log",
        description=action_description,
        color=discord.Color.orange(),
        timestamp=datetime.utcnow()
    )
    log_embed.set_author(name=str(interaction.user), icon_url=interaction.user.display_avatar.url)
    log_embed.set_footer(text=f"Case ID: {case_id}")

    await thread.send(embed=log_embed)

# ---- Modal for Editing a Case ----
class EditCaseModal(discord.ui.Modal, title="Edit Case"):
    def __init__(self, case_id, case):
        super().__init__()
        self.case_id = case_id
        # case = (id, name, summary, notes, created_at)

        self.name = discord.ui.TextInput(
            label="Name", default=case[1], required=True, max_length=100
        )
        self.summary = discord.ui.TextInput(
            label="Summary", default=case[2] or "", 
             style=discord.TextStyle.paragraph, max_length=4000
        )
        self.notes = discord.ui.TextInput(
            label="Notes", default=case[3] or "", required=False,
            style=discord.TextStyle.paragraph, max_length=4000
        )

        self.add_item(self.name)
        self.add_item(self.summary)
        self.add_item(self.notes)

    async def on_submit(self, interaction: discord.Interaction):
        # Update database
        database.update_case(
            self.case_id,
            self.name.value,
            self.summary.value,
            self.notes.value
        )

        # Build a detailed log message
        action_description = (
            f"Case updated:\n"
            f"• **Name:** {self.name.value}\n"
            f"• **Summary:** {self.summary.value or 'N/A'}\n"
            f"• **Notes:** {self.notes.value or 'N/A'}"
        )

        # Update the case thread post + log action
        await update_case_post(interaction, self.case_id, action_description)

        # Confirm to user
        await interaction.response.send_message(
            f"✅ Case `{self.case_id}` updated!",
            ephemeral=True
        )

# ---- Modal for Linking a Contact ----
class LinkContactModal(discord.ui.Modal, title="Link Contact to Case"):
    def __init__(self, case_id):
        super().__init__()
        self.case_id = case_id

        self.contact_id = discord.ui.TextInput(
            label="Contact ID",
            placeholder="Enter the contact ID you want to link",
            required=True,
            max_length=10
        )
        self.role = discord.ui.TextInput(
            label="Role in Case",
            placeholder="e.g. Plaintiff, Defendant, Attorney for Defendant",
            required=True,
            max_length=100
        )

        self.add_item(self.contact_id)
        self.add_item(self.role)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            contact_id = int(self.contact_id.value)
        except ValueError:
            await interaction.response.send_message(
                "Invalid contact ID. Please enter a number.",
                ephemeral=True
            )
            return

        contact = database.get_contact_by_id(contact_id)
        if not contact:
            await interaction.response.send_message(
                f"No contact found with ID `{contact_id}`.",
                ephemeral=True
            )
            return

        database.link_contact_to_case(self.case_id, contact_id, self.role.value)
        await update_case_post(interaction, self.case_id, f"Linked contact {contact_id} as {self.role.value}")
        await interaction.response.send_message(
            f"Linked contact `{contact_id}` to case `{self.case_id}` as **{self.role.value}**.",
            ephemeral=True
        )

# ---- Modal for adding a task ----
class AddTaskModal(discord.ui.Modal, title="Add Task to Case"):
    def __init__(self, case_id):
        super().__init__()
        self.case_id = case_id

        self.task_description = discord.ui.TextInput(
            label="Task Description",
            placeholder="Describe the task",
            required=True,
            style=discord.TextStyle.paragraph,
            max_length=300
        )

        self.deadline = discord.ui.TextInput(
            label="Deadline (optional)",
            placeholder="DD.MM.YYYY or DD.MM.YYYY HH:MM",
            required=False,
            max_length=25
        )

        self.add_item(self.task_description)
        self.add_item(self.deadline)

    async def on_submit(self, interaction: discord.Interaction):
        deadline_value = None
        if self.deadline.value.strip():
            # Try parsing input
            formats = ["%d.%m.%Y %H:%M", "%d.%m.%Y"]
            parsed_deadline = None
            for fmt in formats:
                try:
                    parsed_deadline = datetime.strptime(self.deadline.value.strip(), fmt)
                    break
                except ValueError:
                    continue

            if not parsed_deadline:
                await interaction.response.send_message(
                    "❌ Invalid deadline format. Please use **DD.MM.YYYY** or **DD.MM.YYYY HH:MM**.",
                    ephemeral=True
                )
                return

            # Save deadline in a standard format (e.g. ISO)
            deadline_value = parsed_deadline.strftime("%Y-%m-%d %H:%M")

        # Store in DB
        database.add_task(self.case_id, self.task_description.value, deadline_value)
        await update_case_post(interaction, self.case_id, f"New task added: {self.task_description.value}")
        await interaction.response.send_message(
            f"✅ Task added to case `{self.case_id}`.",
            ephemeral=True
        )

# ---- Modal for marking a task as done----
class MarkTaskDoneModal(discord.ui.Modal, title="Mark Task Done"):
    def __init__(self, case_id):
        super().__init__()
        self.case_id = case_id

        self.task_id = discord.ui.TextInput(
            label="Task ID",
            placeholder="Enter the Task ID to mark as done",
            required=True,
            max_length=10
        )

        self.add_item(self.task_id)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            task_id = int(self.task_id.value)
        except ValueError:
            await interaction.response.send_message(
                "Invalid Task ID. Must be a number.",
                ephemeral=True
            )
            return

        database.mark_task_done(task_id)
        await update_case_post(interaction, self.case_id, f"Task #{task_id} marked as done ✅")
        await interaction.response.send_message(
            f"Task `{task_id}` marked as done.",
            ephemeral=True
        )

# ---- Buttons View ----
class CaseView(discord.ui.View):
    def __init__(self, case_id, case):
        super().__init__(timeout=None)
        self.case_id = case_id
        self.case = case

    @discord.ui.button(label="Edit Case", style=discord.ButtonStyle.primary)
    async def edit_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(EditCaseModal(self.case_id, self.case))

    @discord.ui.button(label="Delete Case", style=discord.ButtonStyle.danger)
    async def delete_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        allowed_role = discord.utils.get(interaction.user.roles, id=settings.MANAGER_ROLE_ID)
        if not allowed_role:
            # Not allowed
            await interaction.response.send_message("❌ You do not have permission.", ephemeral=True)
            return
        case = database.get_case_by_id(self.case_id)
        if not case:
            await interaction.response.send_message(
                f"No case found with ID `{self.case_id}`.",
                ephemeral=True
            )
            return
        
        await update_case_post(interaction, self.case_id, "❌ Case deleted")

        database.delete_case(self.case_id)
        
        await interaction.response.send_message(
            f"Case `{self.case_id}` deleted.",
            ephemeral=True
        )

    @discord.ui.button(label="Link Contact", style=discord.ButtonStyle.secondary)
    async def link_contact_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(LinkContactModal(self.case_id))

    @discord.ui.button(label="Add Task", style=discord.ButtonStyle.success)
    async def add_task_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(AddTaskModal(self.case_id))

    @discord.ui.button(label="Mark Task Done", style=discord.ButtonStyle.secondary)
    async def mark_task_done_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(MarkTaskDoneModal(self.case_id))

# ---- Command Setup ----
async def setup(bot):
    @bot.tree.command(name="view_case", description="View details of a specific case by ID.")
    @app_commands.describe(case_id="The ID of the case to view")
    async def view_case(interaction: discord.Interaction, case_id: str):
        allowed_role = discord.utils.get(interaction.user.roles, id=settings.EMPLOYEE_ROLE_ID)
        if not allowed_role:
            # Not allowed
            await interaction.response.send_message("❌ You do not have permission.", ephemeral=True)
            return
        case = database.get_case_by_id(case_id)
        if not case:
            await interaction.response.send_message(
                f"No case found with ID `{case_id}`.",
                ephemeral=True
            )
            return

        contacts = database.get_contacts_for_case(case_id)
        contact_list = "\n".join([f"- *{c[5]}* {c[1]} (ID {c[0]})" for c in contacts]) or "None linked"

        # Fetch tasks for this case
        tasks = database.get_tasks_for_case(case_id)

        if tasks:
            task_list_lines = []
            for t in tasks:
                task_id, task_desc, deadline, done = t

                if deadline:
                    try:
                        dt = datetime.strptime(deadline, "%Y-%m-%d %H:%M")
                        deadline_str = dt.strftime("%d.%m.%Y %H:%M")
                    except ValueError:
                        deadline_str = deadline
                else:
                    deadline_str = None

                task_line = f"- *#{task_id}* [{'✅' if done else '❌'}] {task_desc}"
                if deadline_str:
                    task_line += f" (Due: {deadline_str})"

                task_list_lines.append(task_line)

            task_list = "\n".join(task_list_lines)
        else:
            task_list = "No tasks added."

        embed = discord.Embed(
            title=f"Case Details: {case[1]}",
            color=discord.Color.green()
        )
        embed.add_field(name="ID", value=case[0], inline=False)
        embed.add_field(name="Summary", value=case[2] or "None", inline=False)
        embed.add_field(name="Notes", value=case[3] or "None", inline=False)
        embed.add_field(name="Linked Contacts", value=contact_list, inline=False)
        embed.add_field(name="Tasks / TODOs", value=task_list, inline=False)
        embed.add_field(name="Created At", value=case[6], inline=False)

        view = CaseView(case_id, case)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
