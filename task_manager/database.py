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



