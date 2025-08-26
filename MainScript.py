import os
import discord
from discord.ext import commands, tasks
from discord import app_commands
from dotenv import load_dotenv
import importlib
import pkgutil
from datetime import datetime, timedelta
import database  # <-- Import  database module
import settings # <-- Import settings module

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Create tables
database.create_all_tables()
database.migrate_database()

load_dotenv()
TOKEN = settings.DISCORD_TOKEN

intents = discord.Intents.all()
bot = commands.Bot(command_prefix=settings.COMMAND_PREFIX, intents=intents)

# ------------------ CONFIG ------------------
NOTIFICATION_CHANNEL_ID = settings.NOTIFICATION_CHANNEL_ID  # Set your Discord channel ID in .env
DUE_SOON_WINDOW = settings.DUE_SOON_WINDOW  # Notify tasks due within N hour
NOTIFIED_TASKS = set()  # Tracks tasks already notified
# -------------------------------------------

def parse_deadline(deadline_str):
    """Parse deadline in either DD.MM.YYYY or DD.MM.YYYY HH:MM format."""
    if not deadline_str:
        return None
    for fmt in ("%d.%m.%Y %H:%M", "%d.%m.%Y"):
        try:
            return datetime.strptime(deadline_str, fmt)
        except ValueError:
            continue
    return None

# ------------------ BACKGROUND LOOP ------------------
@tasks.loop(minutes=5)
async def check_due_tasks():
    now = datetime.now()
    upcoming_window = now + DUE_SOON_WINDOW
    
    all_tasks = database.get_all_tasks()
    channel = bot.get_channel(NOTIFICATION_CHANNEL_ID)
    if not channel:
        return  # skip if channel not found
    
    for task in all_tasks:
        task_id, case_id, description, deadline_str, done = task
        
        if done or task_id in NOTIFIED_TASKS:
            continue  # Skip completed or already notified tasks
        
        task_dt = parse_deadline(deadline_str)
        if not task_dt:
            continue

        case = database.get_case_by_id(case_id)
        contacts = database.get_contacts_for_case(case_id)

        # Collect mentions for Discord users who have discord_id set
        print(contacts)
        mentions = [f"<@{c[7]}>" for c in contacts if c[7]]  # c[7] is discord_id
        mention_text = " ".join(mentions) if mentions else "No users linked"

        if task_dt < now:
            # OVERDUE TASK
            embed = discord.Embed(
                title="❌ Task Overdue!",
                color=discord.Color.red(),
                timestamp=task_dt
            )
            embed.add_field(name="Task", value=description, inline=False)
            embed.add_field(name="Case", value=f"{case[1]} (ID: {case_id})", inline=False)
            embed.add_field(name="Deadline", value=task_dt.strftime('%d.%m.%Y %H:%M'), inline=False)
            embed.add_field(name="Linked Contacts", value=mention_text, inline=False)
            embed.set_footer(text="Reminder from TaskBot")

            await channel.send(embed=embed)

            # Send actual ping message
            if mentions:
                await channel.send("🔔 " + " ".join(mentions))

            NOTIFIED_TASKS.add(task_id)

        elif now <= task_dt <= upcoming_window:
            # DUE SOON TASK
            embed = discord.Embed(
                title="⚠️ Task Due Soon!",
                color=discord.Color.orange(),
                timestamp=task_dt
            )
            embed.add_field(name="Task", value=description, inline=False)
            embed.add_field(name="Case", value=f"{case[1]} (ID: {case_id})", inline=False)
            embed.add_field(name="Deadline", value=task_dt.strftime('%d.%m.%Y %H:%M'), inline=False)
            embed.add_field(name="Linked Contacts", value=mention_text, inline=False)
            embed.set_footer(text="Reminder from TaskBot")

            await channel.send(embed=embed)

            # Send actual ping message
            if mentions:
                await channel.send("🔔 " + " ".join(mentions))

            NOTIFIED_TASKS.add(task_id)


# ------------------ BOT EVENTS ------------------
@bot.event
async def on_ready():
    # Dynamically import and setup all command modules
    commands_path = os.path.join(BASE_DIR, "commands")
    for _, module_name, _ in pkgutil.iter_modules([commands_path]):
        module = importlib.import_module(f"commands.{module_name}")
        if hasattr(module, "setup"):
            await module.setup(bot)
    
    await bot.tree.sync()
    print(f"{bot.user} is online!")
    
    # Start the background task
    check_due_tasks.start()
    check_due_tasks()

# ------------------ RUN BOT ------------------
bot.run(TOKEN)
