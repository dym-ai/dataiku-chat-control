# Dataiku Chat Control

Control Dataiku DSS through Claude Code using the Python API.

## Overview

This project enables Claude Code to perform administrative and user actions on Dataiku DSS via chat, including:

- Adjusting admin settings
- Building and deploying projects
- Managing datasets, recipes, and scenarios
- User and group management
- Importing SQL tables from connections (Snowflake, etc.)

## Architecture

```
User Request → Claude Code → Python Script → dataikuapi → Dataiku DSS Instance
```

## Setup

```bash
# Create virtual environment
python -m venv venv

# Activate and install dependencies
source venv/bin/activate
pip install -r requirements.txt

# Configure credentials
cp .env.example .env
# Edit .env with your DATAIKU_URL and DATAIKU_API_KEY
```

## Usage

Test connection:
```bash
./venv/bin/python client.py
```

### Create a Dataset

```bash
# From CSV file
./venv/bin/python create_dataset.py PROJECT_KEY dataset_name data.csv

# From JSON
./venv/bin/python create_dataset.py PROJECT_KEY dataset_name '{"columns": ["id", "name"], "rows": [[1, "Alice"]]}'
```

### Import SQL Table

```bash
./venv/bin/python import_sql_table.py PROJECT_KEY connection_name SCHEMA TABLE_NAME [dataset_name]
```

## Documentation

- [Dataiku Developer Guide](https://developer.dataiku.com/latest/index.html)
- [Python API Reference](https://developer.dataiku.com/latest/api-reference/python/client.html)
