# TodoList CLI

A simple command-line task manager built in Python. This project serves as a learning exercise to understand CLI application development and basic task management concepts.

## Features

- Add new tasks
- List all tasks
- Mark tasks as complete
- Delete tasks
- Simple and intuitive command-line interface

## Installation

1. Clone this repository:

```bash
git clone https://github.com/yourusername/todolist-cli.git
cd todolist-cli
```

2. Create a virtual environment (recommended):

```bash
python -m venv venv
source venv/bin/activate  # On Windows, use: venv\Scripts\activate
```

3. Install the package in development mode:

```bash
pip install -e .
```

For development dependencies (testing, formatting, etc.):

```bash
pip install -e ".[dev]"
```

## Dependencies

The project uses modern Python packaging with `pyproject.toml`. Main dependencies include:

- typer: For building the CLI interface
- rich: For beautiful terminal formatting
- pydantic: For data validation
- tabulate: For table formatting
- tqdm: For progress bars

## Usage

Run the application using:

```bash
taskman
```

### Available Commands

- `add <task>` - Add a new task
- `list` - Show all tasks
- `complete <task_id>` - Mark a task as complete
- `delete <task_id>` - Delete a task
- `help` - Show available commands
- `exit` - Exit the application

## Project Structure

```
todolist-cli/
├── task_manager/    # Main package directory
├── pyproject.toml   # Project configuration and dependencies
└── README.md       # This file
```

## Learning Goals

This project is designed to help learn:

- Command-line interface development
- Basic Python programming
- Task management concepts
- File I/O operations
- User input handling
- Modern Python packaging with pyproject.toml

## Contributing

Feel free to fork this project and experiment with adding new features or improvements!

## License

This project is open source and available under the MIT License.
