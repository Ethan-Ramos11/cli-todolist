import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union, Any

from rich.console import Console
from tqdm import tqdm

from task_manager import config
from task_manager.models import Task

console = Console()


def get_db_connection() -> sqlite3.Connection:
    """Creates and returns a database connection with proper configuration.

    Returns:
        sqlite3.Connection: A configured SQLite database connection with:
            - Foreign key constraints enabled
            - Row factory set to sqlite3.Row
    """
    conn = sqlite3.connect(config.DB_FULL_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Initializes the database with required tables and default categories.

    Creates the following tables if they don't exist:
        - categories: Stores task categories with colors
        - tasks: Main tasks table with foreign key to categories
        - tags: Stores available tags
        - task_tags: Junction table for many-to-many relationship between tasks and tags

    Also populates default categories with predefined colors.
    """
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


def add_task(task: Task) -> int:
    """Adds a new task to the database.

    Args:
        task (Task): Task object containing task details including:
            - title
            - description
            - due_date
            - status
            - priority
            - category
            - tags

    Returns:
        int: The ID of the newly created task
    """
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
) -> List[Dict[str, Any]]:
    """Retrieves tasks with optional filtering.

    Args:
        status (Optional[str]): Filter tasks by status (e.g., 'pending', 'completed')
        priority (Optional[str]): Filter tasks by priority (e.g., 'high', 'medium', 'low')
        category (Optional[str]): Filter tasks by category name
        tag (Optional[str]): Filter tasks by tag name
        search (Optional[str]): Search term to match in title or description
        limit (int, optional): Maximum number of tasks to return. Defaults to 100.

    Returns:
        List[Dict[str, Any]]: List of task dictionaries containing:
            - id: Task ID
            - title: Task title
            - description: Task description
            - due_date: Task due date
            - created_at: Creation timestamp
            - updated_at: Last update timestamp
            - status: Task status
            - priority: Task priority
            - category: Category name
            - category_color: Category color
            - tags: List of associated tags
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    query = ("""
    SELECT 
             t.id, t.title, t.description, t.due_date, t.created_at, 
             t.updated_at, t.status, t.priority, 
             c.name as category, c.color as category_color
    FROM tasks t
    LEFT JOIN categories c on t.category_id = c.id
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


def get_task(task_id: int) -> Optional[Dict[str, Any]]:
    """Retrieves a single task by its ID.

    Args:
        task_id (int): The ID of the task to retrieve

    Returns:
        Optional[Dict[str, Any]]: Task dictionary if found, None otherwise. Contains:
            - id: Task ID
            - title: Task title
            - description: Task description
            - due_date: Task due date
            - status: Task status
            - priority: Task priority
            - category: Category name
            - category_color: Category color
            - tags: List of associated tags
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
                SELECT 
                    t.id, t.title, t.description, t.due_date, t.status, t.priority,
                    c.name as category, c.color as category_color
                    FROM tasks t
                    LEFT JOIN categories c ON t.category_id = c.id
                    WHERE t.id = ?
    """, (task_id, ))
    task = cursor.fetchone()
    if not task:
        conn.close()
        return None

    task_dict = dict(task)
    cursor.execute("""
    SELECT tg.name
    FROM tags tg 
    JOIN task_tags tt ON tg.id = tt.tag_id
    WHERE tt.task_id = ?
    """, (task_id,))
    task_dict['tags'] = [row['name'] for row in cursor.fetchall()]

    conn.close()
    return task_dict


def delete_task(task_id: int) -> bool:
    """Deletes a task from the database.

    Args:
        task_id (int): The ID of the task to delete

    Returns:
        bool: True if task was deleted, False if task not found
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM tasks WHERE id = ?", (task_id,))
    if not cursor.fetchone():
        conn.close()
        return False

    cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))

    conn.commit()
    conn.close()
    return True


def update_tasks(task_id: int, task_data: Dict[str, Any]) -> bool:
    """Updates an existing task with new data.

    Args:
        task_id (int): The ID of the task to update
        task_data (Dict[str, Any]): Dictionary containing fields to update:
            - title: New task title
            - description: New task description
            - due_date: New due date
            - status: New status
            - priority: New priority
            - category: New category name
            - tags: New list of tags

    Returns:
        bool: True if task was updated, False if task not found

    Note:
        - If category doesn't exist, it will be created
        - Existing tags will be removed and replaced with new tags
        - updated_at timestamp is automatically set to current time
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT if FROM TASKS WHERE id = ?", (task_id,))
    if not cursor.fetchone():
        conn.close()
        return False

    if "category" in task_data:
        category_name = task_data.pop("category", None)
        if category_name:
            cursor.execute(
                "SELECT if FROM categories WHERE name = ?", (category_name,))
            result = cursor.fetchone()
            if result:
                task_data["category_id"] = result["id"]
            else:
                cursor.execute(
                    "INSERT INTO categories (name) VALUES (?)", (category_name,))
                task_data["category_id"] = cursor.lastrowid
    else:
        task_data['category_id'] = None

    tags = task_data.pop('tags', None)
    if "due_date" in task_data and isinstance(task_data['due_date'], datetime):
        task_data['due_date'] = task_data['due_date'].isoformat()

    if task_data:
        task_data["updated_at"] = datetime.now().isoformat()

        placeholders = ", ".join([f"field = ?" for field in task_data.keys()])
        values = list(task_data.values())
        values.append(task_id)
        cursor.execute(
            f"UPDATE tasks SET {placeholders} WHERE id = ?", values)

    if tags is not None:
        cursor.execute("DELETE FROM task_tags WHERE task_id = ?", (task_id,))

        for tag_name in tags:
            cursor.execute(
                "INSERT INTO tags (name) VALUES (?) ON CONFLICT(name) DO NOTHING", (tag_name,)
            )
            cursor.execute("SELECT id FROM tags WHERE name = ?", (tag_name,))
            tag_id = cursor.fetchone()["id"]
            cursor.execute(
                "INSERT INTO task_tags (task_id, tag_id) VALUES (?, ?)",
                (task_id, tag_id))
    conn.commit()
    conn.close()
    return True
