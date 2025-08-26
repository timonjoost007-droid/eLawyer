import sqlite3
import os
import settings

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def get_connection():
    return sqlite3.connect(f"{BASE_DIR}\\database.db")

def create_table(table_name, schema):
    connection = get_connection()
    cursor = connection.cursor()

    # Build CREATE TABLE statement
    columns_sql = ",\n    ".join([f"{col} {definition}" for col, definition in schema.items()])
    cursor.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            {columns_sql}
        )
        """
    )

    connection.commit()
    connection.close()

def create_all_tables():
    for table, schema in settings.DATABASE_SCHEMA.items():
        create_table(table, schema)

def insert_case(case_id, name, summary, notes, channel_id=None, message_id=None):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        "INSERT INTO cases (id, name, summary, notes, channel_id, message_id) VALUES (?, ?, ?, ?, ?, ?)",
        (case_id, name, summary, notes, channel_id, message_id)
    )
    connection.commit()
    connection.close()


def update_case(case_id, name=None, summary=None, notes=None, channel_id=None, message_id=None):
    connection = get_connection()
    cursor = connection.cursor()

    fields = []
    params = []

    if name is not None:
        fields.append("name = ?")
        params.append(name)
    if summary is not None:
        fields.append("summary = ?")
        params.append(summary)
    if notes is not None:
        fields.append("notes = ?")
        params.append(notes)
    if channel_id is not None:
        fields.append("channel_id = ?")
        params.append(channel_id)
    if message_id is not None:
        fields.append("message_id = ?")
        params.append(message_id)

    if not fields:
        connection.close()
        return

    query = f"UPDATE cases SET {', '.join(fields)} WHERE id = ?"

    params.append(case_id)

    cursor.execute(query, params)
    connection.commit()
    connection.close()


def count_cases_today(today):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM cases WHERE strftime('%d%m%Y', created_at) = ?", (today,)
    )
    count = cursor.fetchone()[0]
    connection.close()
    return count

def get_all_cases():
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT id, name, summary, notes, channel_id, message_id, created_at FROM cases")
    cases = cursor.fetchall()
    connection.close()
    return cases


def get_case_by_id(case_id):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        "SELECT id, name, summary, notes, channel_id, message_id, created_at FROM cases WHERE id = ?",
        (case_id,)
    )
    case = cursor.fetchone()
    connection.close()
    return case

def delete_case(case_id):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("DELETE FROM cases  WHERE id=?", (case_id,))
    connection.commit()
    connection.close()

def insert_contact(name, contact, notes, status, discord_id=None, channel_id=None, message_id=None):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        "INSERT INTO contacts (name, contact, notes, status, discord_id, channel_id, message_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (name, contact, notes, status, discord_id, channel_id, message_id)
    )
    connection.commit()
    contact_id = cursor.lastrowid
    connection.close()
    return contact_id

def get_all_contacts():
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        "SELECT id, name, contact, notes, status, discord_id, channel_id, message_id, created_at FROM contacts"
    )
    contacts = cursor.fetchall()
    connection.close()
    return contacts


def get_contact_by_id(contact_id):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        "SELECT id, name, contact, notes, status, discord_id, channel_id, message_id, created_at FROM contacts WHERE id = ?",
        (contact_id,)
    )
    contact = cursor.fetchone()
    connection.close()
    return contact

def update_contact(contact_id, name=None, contact=None, notes=None, status=None, discord_id=None, channel_id=None, message_id=None):
    connection = get_connection()
    cursor = connection.cursor()

    updates = []
    values = []

    if name is not None:
        updates.append("name=?")
        values.append(name)
    if contact is not None:
        updates.append("contact=?")
        values.append(contact)
    if notes is not None:
        updates.append("notes=?")
        values.append(notes)
    if status is not None:
        updates.append("status=?")
        values.append(status)
    if discord_id is not None:
        updates.append("discord_id=?")
        values.append(discord_id)
    if channel_id is not None:
        updates.append("channel_id=?")
        values.append(channel_id)
    if message_id is not None:
        updates.append("message_id=?")
        values.append(message_id)

    if updates:  # only run if there are fields to update
        sql = f"UPDATE contacts SET {', '.join(updates)} WHERE id=?"
        values.append(contact_id)
        cursor.execute(sql, tuple(values))
        connection.commit()

    connection.close()

def delete_contact(contact_id):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("DELETE FROM contacts WHERE id=?", (contact_id,))
    connection.commit()
    connection.close()

def link_contact_to_case(case_id, contact_id, role):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO case_contacts (case_id, contact_id, role) VALUES (?, ?, ?)",
        (case_id, contact_id, role)
    )
    connection.commit()
    connection.close()

def get_contacts_for_case(case_id):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT c.id, c.name, c.contact, c.notes, c.status,  cc.role, c.created_at, c.discord_id
        FROM contacts c
        INNER JOIN case_contacts cc ON c.id = cc.contact_id
        WHERE cc.case_id = ?
        """,
        (case_id,)
    )
    contacts = cursor.fetchall()
    connection.close()
    return contacts

def get_cases_for_contact(contact_id):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT ca.id, ca.name, cc.role
        FROM cases ca
        INNER JOIN case_contacts cc ON ca.id = cc.case_id
        WHERE cc.contact_id = ?
        """,
        (contact_id,)
    )
    cases = cursor.fetchall()
    connection.close()
    return cases

def unlink_contact_from_case(case_id, contact_id):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        "DELETE FROM case_contacts WHERE case_id=? AND contact_id=?",
        (case_id, contact_id)
    )
    connection.commit()
    connection.close()

def add_task(case_id, task, deadline=None):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        "INSERT INTO case_tasks (case_id, task, deadline) VALUES (?, ?, ?)",
        (case_id, task, deadline)
    )
    connection.commit()
    connection.close()

def get_tasks_for_case(case_id):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        "SELECT id, task, deadline, done FROM case_tasks WHERE case_id = ?",
        (case_id,)
    )
    tasks = cursor.fetchall()
    connection.close()
    return tasks

def mark_task_done(task_id):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        "UPDATE case_tasks SET done = 1 WHERE id = ?",
        (task_id,)
    )
    connection.commit()
    connection.close()

def delete_task(task_id):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        "DELETE FROM case_tasks WHERE id = ?",
        (task_id,)
    )
    connection.commit()
    connection.close()

def get_all_tasks():
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(
        "SELECT id, case_id, task, deadline, done FROM case_tasks"
    )
    tasks = cursor.fetchall()
    connection.close()
    return tasks

def get_tasks_due_between(start: str = None, end: str = None): # maybe I need to switch to timestamps here
    """
    Returns all tasks with deadlines between start and end.
    - start and end are strings in "YYYY-MM-DD HH:MM" format.
    - If start is None, defaults to now.
    - If end is None, fetches all future tasks.
    """
    connection = get_connection()
    cursor = connection.cursor()

    query = "SELECT id, case_id, task, deadline, done FROM case_tasks WHERE deadline IS NOT NULL"
    params = []

    if start:
        query += " AND deadline >= ?"
        params.append(start)
    if end:
        query += " AND deadline <= ?"
        params.append(end)

    cursor.execute(query, params)
    tasks = cursor.fetchall()
    connection.close()
    return tasks

#------

def migrate_database():
    connection = get_connection()
    cursor = connection.cursor()

    # Define expected schema
    expected_schema = settings.DATABASE_SCHEMA

    for table, columns in expected_schema.items():
        # Get existing columns in DB
        cursor.execute(f"PRAGMA table_info({table})")
        existing_cols = {col[1] for col in cursor.fetchall()}

        # Add missing columns
        for col_name, col_def in columns.items():
            if col_name not in existing_cols:
                print(f"[MIGRATION] Adding missing column '{col_name}' to '{table}'")
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_def}")

        # Warn about deprecated columns
        for col_name in existing_cols:
            if col_name not in columns:
                print(f"[WARNING] Column '{col_name}' exists in '{table}' but is not in expected schema (deprecated?). Deleting.")

    connection.commit()
    connection.close()