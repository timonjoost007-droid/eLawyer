import os
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ------------------ DISCORD ------------------
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
COMMAND_PREFIX = "e!"

# ------------------ PERMS ------------------

EMPLOYEE_ROLE_ID = 1404762559613243442
MANAGER_ROLE_ID = 1409979344478015591

# ------------------ CHANNELS ------------------
# Preferably, put these IDs in your .env instead of hardcoding
NOTIFICATION_CHANNEL_ID = 1409979145970253854
CASE_FORUM_CHANNEL_ID = 1409978960384757853
CONTACTS_FORUM_CHANNEL_ID = 1409979025819963476

# ------------------ TASK SETTINGS ------------------
DUE_SOON_WINDOW = timedelta(hours=int(os.getenv("DUE_SOON_HOURS", "24")))

# ------------------ DATABASE ------------------
DATABASE_SCHEMA = {
        "cases": {
            "id": "TEXT",
            "name": "TEXT",
            "summary": "TEXT",
            "notes": "TEXT",
            "channel_id": "TEXT",  # linked forum post / channel
            "message_id": "TEXT",  # linked forum post / channel message
            "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
        },
        "contacts": {
            "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
            "name": "TEXT NOT NULL",
            "contact": "TEXT",
            "notes": "TEXT",
            "status": "TEXT",
            "discord_id": "TEXT",
            "channel_id": "TEXT",   # forum channel where contact post lives
            "message_id": "TEXT",   # message/post ID inside that channel
            "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
        },
        "case_contacts": {
            "case_id": "TEXT",
            "contact_id": "INTEGER",
            "role": "TEXT"
        },
        "case_tasks": {
            "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
            "case_id": "TEXT",
            "task": "TEXT NOT NULL",
            "deadline": "TIMESTAMP",
            "done": "INTEGER DEFAULT 0"
        }
    }