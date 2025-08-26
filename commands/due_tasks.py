import discord
from discord import app_commands
from datetime import datetime, timedelta
import database
import settings

from datetime import datetime

def parse_deadline(deadline_str):
    """Parse deadline from user input or DB format.
    
    Accepts:
    - DD.MM.YYYY
    - DD.MM.YYYY HH:MM
    - YYYY-MM-DD HH:MM (DB stored format)
    """
    if not deadline_str:
        return None

    for fmt in ("%d.%m.%Y %H:%M", "%d.%m.%Y", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(deadline_str.strip(), fmt)
        except ValueError:
            continue

    return None  # malformed date



async def setup(bot):
    @bot.tree.command(
        name="due_tasks",
        description="Get all tasks due in a specific time period."
    )
    @app_commands.describe(
        start_date="Start date (DD.MM.YYYY) – optional, defaults to today",
        end_date="End date (DD.MM.YYYY) – optional, defaults to all future tasks"
    )
    async def due_tasks(interaction: discord.Interaction, start_date: str = None, end_date: str = None):
        allowed_role = discord.utils.get(interaction.user.roles, id=settings.EMPLOYEE_ROLE_ID)
        if not allowed_role:
            # Not allowed
            await interaction.response.send_message("❌ You do not have permission.", ephemeral=True)
            return

        # Parse input dates or set defaults
        try:
            start_dt = datetime.strptime(start_date, "%d.%m.%Y") if start_date else datetime.now() - timedelta(days=1)
            end_dt = datetime.strptime(end_date, "%d.%m.%Y") if end_date else None
        except ValueError:
            await interaction.response.send_message(
                "Invalid date format. Please use DD.MM.YYYY",
                ephemeral=True
            )
            return

        # Convert to SQLite-compatible strings
        start_str = start_dt.strftime("%Y-%m-%d %H:%M")
        end_str = end_dt.strftime("%Y-%m-%d %H:%M") if end_dt else None

        # Fetch tasks using new DB function
        all_tasks = database.get_tasks_due_between(start=start_str, end=end_str)

        due_tasks_list = []
        for task in all_tasks:
            task_id, case_id, description, deadline, done = task
            if done:  # Skip completed tasks
                continue
            if not deadline:
                continue

            task_dt = parse_deadline(deadline)
            
            if not task_dt:
                continue  # skip malformed dates

            # Only include tasks whose deadline falls within the period
            if start_dt <= task_dt <= (end_dt if end_dt else task_dt):
                case = database.get_case_by_id(case_id)
                due_tasks_list.append(
                    f"- ❌ {description} (Case: {case[1]} ID: {case_id}, Due: {task_dt.strftime('%d.%m.%Y %H:%M')})"
                )

        if not due_tasks_list:
            due_tasks_list = ["No tasks due in this period."]

        # Split into multiple embeds if too long
        chunks = [due_tasks_list[i:i+20] for i in range(0, len(due_tasks_list), 20)]
        for i, chunk in enumerate(chunks):
            embed = discord.Embed(
                title=f"Due Tasks {start_date or 'Today'} - {end_date or 'Future'}" + (f" (Part {i+1})" if len(chunks) > 1 else ""),
                description="\n".join(chunk),
                color=discord.Color.orange()
            )

            if i == 0:
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                await interaction.followup.send(embed=embed, ephemeral=True)
