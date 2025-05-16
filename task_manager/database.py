import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

from rich.console import Console
from tqdm import tqdm

from task_manager import config
from task_manager.models import Task

console = Console()


def get_db_connection():
    conn = sqlite3.connect(config.DB_FULL_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    conn.execute("""
    Create TABLE IF NOT EXISTS categories (
                 id INTEGER PRIMARY KEY, 
                 name TEXT NOT NULL UNIQUE, 
                 color TEXT DEFAULT 'white',
                 created_at TEXT DEFAULT CURRENT_TIMESTAMP)
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
                 id INTEGER PRIMARY KEY,
                 title TEXT NOT NULL,
                 description TEXT, 
                 created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                 updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                 status TEXT DEFAULT 'pending',
                 priority TEXT DEFAULT 'medium',
                 category_id INTEGER, 
                 FOREIGN KEY (category_id) REFERENCES categories (id) ON DELETE SET NULL)
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tags(
                   id INTEGER PRIMARY KEY, 
                   name TEXT NOT NULL UNIQUE, 
                   created_at TEXT DEFAULT CURRENT_TIMESTAMP)
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS task_tags (
                   task_id INTEGER,
                   tag_id INTEGER, 
                   PRIMARY KEY (task_id, tag_id),
                   FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE,
                   FOREIGN KEY (tag_id) REFERENCES tags (id) ON DELETE CASCADE) 
    """)

    default_categories = [
        ("Work", "blue"),
        ("Personal", "green"),
        ("Health", "red"),
        ("Finance", "yellow"),
        ("Education", "cyan"),
    ]
    for category, color in default_categories:
        cursor.execute("""
            INSERT INTO categories (name, color) VALUES (?,?) ON CONFLICT(name) DO NOTHING""", (category, color))

    conn.commit()
    conn.close()
    console.print(
        "[bold green]Database initialized successfully![/bold green]")


def add_task(task):
    conn = get_db_connection()
    cursor = conn.cursor()

    category_id = None
    if task.category:
        cursor.execute(
            "SELECT id FROM categories WHERE name = ?" (task.category,))
        result = cursor.fetchone()
        if result:
            category_id = result['id']
        else:
            cursor.execute(
                "INSERT INTO categories (name) VALUES (?)", (task.category))
            category_id = cursor.lastrowid
    cursor.execute("""
    INSERT INTO tasks (
                   title, description, due_date, status, priority, category_id
                   ) VALUES (?,?,?,?,?,?)
    """, (
        task.title,
        task.description,
        task.due_date.isoformat() if task.due_date else None,
        task.status,
        task.priority,
        category_id
    ))
    task_id = cursor.lastrowid

    if task.tags:
        for tag in task.tags:
            cursor.execute(
                "INSERT INTO tags (name) VALUES (?) ON CONFLICT(name) DO NOTHING", (tag,))

            cursor.execute("SELECT id FROM tags WHERE name = ?", (tag,))
            tag_id = cursor.fetchone()['id']

            cursor.execute(
                "INSERT INTO task_tags (task_id, tag_id) VALUES (?,?)", (task_id, tag_id))
    conn.commit()
    conn.close()

    return task_id


def get_tasks(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    category: Optional[str] = None,
    tag: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 100,
) -> List[Dict]:
    conn = get_db_connection()
    cursor = conn.cursor()

    query = ("""
    SELECT 
             t.id, t.title, t.description, t.due_date, t.created_at, 
             t.updated_at, t.status, t.priority, 
             c.name as category, c.color as category_color
    FROM tasks t
    LEFT JOIN categories c on t.catogory_id = c.id
    """)

    params = []
    where_clauses = []

    if tag:
        query += """
    JOIN task_tags tt on t.id = tt.task_id
    JOIN tags tg ON tt.tag_id = tg.id
    """

    if status:
        where_clauses.append("t.status = ?")
        params.append(status)

    if priority:
        where_clauses.append("t.priority = ?")
        params.append(priority)

    if category:
        where_clauses.append("c.name = ?")
        params.append(category)

    if search:
        where_clauses.append("(t.title LIKE ? OR t.description LIKE ?)")
        search_term = f"%{search}%"
        params.extend([search_term, search_term])

    if where_clauses:
        query += " WHERE " + " AND ".join(where_clauses)

    query += " ORDER BY t.due_date ASC, t.priority DESC, t.id DESC LIMIT ?"
    params.append(limit)
    cursor.execute(query, params)
    tasks = [dict(row) for row in cursor.fetchall()]

    for task in tasks:
        cursor.execute("""
                       SELECT tg.name 
                       FROM tags tg 
                       JOIN task_tags tt ON tg.id = tt.tag_id
                       WHERE tt.task_id = ?
    """, ([task['id']],))
        task['tags'] = [row['name'] for row in cursor.fetchall()]
    conn.close()
    return tasks


