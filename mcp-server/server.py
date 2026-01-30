#!/usr/bin/env python3
"""Dataiku MCP Server - Code Execution Paradigm.

This MCP server exposes a single tool that executes Python code with a
pre-configured Dataiku client and helper modules. This follows the
"code execution with MCP" pattern for maximum flexibility and minimal
token overhead.

Supports multiple Dataiku instances - use `use_instance` to switch between them.
Configure instances in .dataiku-instances.json (see .dataiku-instances.example.json).

Usage:
    python server.py
"""

import sys
import os
import json
from io import StringIO
from pathlib import Path
from textwrap import dedent

# Add paths for imports
server_dir = Path(__file__).parent
parent_dir = server_dir.parent
sys.path.insert(0, str(parent_dir))  # For client.py
sys.path.insert(0, str(server_dir))  # For helpers package

from mcp.server.fastmcp import FastMCP
from dataikuapi import DSSClient

import helpers
from helpers import jobs, inspection, search, export

# =============================================================================
# Instance Configuration - Load from config file
# =============================================================================

CONFIG_FILE = parent_dir / ".dataiku-instances.json"
EXAMPLE_CONFIG_FILE = parent_dir / ".dataiku-instances.example.json"

def load_instances():
    """Load instance configurations from the config file."""
    if not CONFIG_FILE.exists():
        return None, None

    with open(CONFIG_FILE) as f:
        config = json.load(f)

    return config.get("instances", {}), config.get("default", None)

INSTANCES, DEFAULT_INSTANCE = load_instances()

# Check if config is missing
_config_missing = INSTANCES is None or len(INSTANCES) == 0

if _config_missing:
    _instructions = dedent(f"""
    ⚠️  DATAIKU INSTANCES NOT CONFIGURED

    Please create a config file at:
      {CONFIG_FILE}

    Copy from the example file:
      cp {EXAMPLE_CONFIG_FILE} {CONFIG_FILE}

    Then edit with your instance details:
    {{
      "default": "MyInstance",
      "instances": {{
        "MyInstance": {{
          "url": "https://your-instance.dataiku.com",
          "api_key": "dkuaps-your-api-key",
          "description": "My Dataiku instance"
        }}
      }}
    }}

    After creating the config, restart Claude Code.
    """).strip()
    INSTANCES = {}
    DEFAULT_INSTANCE = None
else:
    # Build instructions with available instances
    instance_list = "\n".join(
        f'  - {name}: {cfg["description"]} ({cfg["url"]})'
        for name, cfg in INSTANCES.items()
    )
    _instructions = dedent(f"""
    Dataiku DSS control server with multi-instance support.

    **Current instance: {DEFAULT_INSTANCE}** (default)

    Available instances:
    {instance_list}

    Use `use_instance("InstanceName")` to switch instances at the start of a session.

    Available in the execution namespace:
    - client: Authenticated DSSClient instance
    - helpers.jobs: build_and_wait, run_scenario_and_wait, compute_and_apply_schema
    - helpers.inspection: dataset_info, project_summary
    - helpers.search: find_datasets, find_by_connection
    - helpers.export: to_records, sample, head

    Example:
        # List all projects
        print(client.list_project_keys())

    IMPORTANT: After creating or modifying a recipe, you MUST compute and apply schema
    before building, or the build will fail with missing column errors.
    """).strip()

# =============================================================================
# Server State
# =============================================================================

_current_instance = DEFAULT_INSTANCE
_client = None

def get_dataiku_client():
    """Get or create the Dataiku client for current instance."""
    global _client
    if _current_instance and _current_instance in INSTANCES:
        instance_config = INSTANCES[_current_instance]
        _client = DSSClient(instance_config["url"], instance_config["api_key"])
    return _client

def switch_instance(instance_name: str) -> bool:
    """Switch to a different Dataiku instance."""
    global _current_instance, _client
    if instance_name in INSTANCES:
        _current_instance = instance_name
        _client = None  # Reset client so it reconnects
        return True
    return False

# =============================================================================
# MCP Server Setup
# =============================================================================

# Initialize MCP server
mcp = FastMCP("dataiku", instructions=_instructions)

# Persistent execution namespace
execution_globals = {
    "__builtins__": __builtins__,
    "helpers": helpers,
    "jobs": jobs,
    "inspection": inspection,
    "search": search,
    "export": export,
}


@mcp.tool()
def use_instance(instance_name: str) -> str:
    """Switch to a different Dataiku instance.

    Call this at the start of a session to connect to a specific instance.

    Args:
        instance_name: Name of the instance to use (e.g., "Jed", "Analytics")

    Returns:
        Confirmation message with instance details
    """
    if _config_missing:
        return f"No instances configured. Please create {CONFIG_FILE}"

    if instance_name not in INSTANCES:
        available = ", ".join(INSTANCES.keys())
        return f"Unknown instance '{instance_name}'. Available instances: {available}"

    if switch_instance(instance_name):
        config = INSTANCES[instance_name]
        # Reset the client in execution globals
        execution_globals["client"] = get_dataiku_client()
        return f"Switched to instance '{instance_name}'\nURL: {config['url']}\nDescription: {config['description']}"

    return f"Failed to switch to instance '{instance_name}'"


@mcp.tool()
def list_instances() -> str:
    """List all available Dataiku instances.

    Returns:
        List of configured instances with their details
    """
    if _config_missing:
        return f"No instances configured. Please create {CONFIG_FILE}"

    lines = [f"Current instance: {_current_instance}", "", "Available instances:"]
    for name, config in INSTANCES.items():
        marker = " (active)" if name == _current_instance else ""
        lines.append(f"  - {name}{marker}")
        lines.append(f"      URL: {config['url']}")
        lines.append(f"      Description: {config['description']}")
    return "\n".join(lines)


@mcp.tool()
def execute_python(code: str) -> str:
    """Execute Python code with pre-configured Dataiku client.

    The execution environment includes:
    - client: Authenticated DSSClient connected to your Dataiku instance
    - helpers.jobs: build_and_wait, run_scenario_and_wait, run_recipe_and_wait
    - helpers.inspection: dataset_info, project_summary, connection_info
    - helpers.search: find_datasets, find_recipes, find_by_connection
    - helpers.export: to_records, sample, head, get_schema

    Variables persist across calls within the same session.

    Args:
        code: Python code to execute

    Returns:
        stdout output from the code, or error message if execution fails
    """
    if _config_missing:
        return f"No instances configured. Please create {CONFIG_FILE}"

    # Ensure client is in namespace
    execution_globals["client"] = get_dataiku_client()

    # Capture stdout
    stdout_capture = StringIO()
    old_stdout = sys.stdout
    sys.stdout = stdout_capture

    try:
        # Execute the code
        exec(code, execution_globals)
        output = stdout_capture.getvalue()
        return output if output else "(executed successfully, no output)"
    except Exception as e:
        import traceback
        error_output = stdout_capture.getvalue()
        tb = traceback.format_exc()
        return f"{error_output}\nError: {type(e).__name__}: {e}\n\n{tb}"
    finally:
        sys.stdout = old_stdout


@mcp.tool()
def list_helpers() -> str:
    """List all available helper functions and their signatures.

    Returns:
        Formatted list of all helper modules and functions
    """
    output = []

    output.append("=== helpers.jobs ===")
    output.append("  build_and_wait(client, project_key, dataset_name, build_mode='RECURSIVE_BUILD', timeout=600)")
    output.append("  run_scenario_and_wait(client, project_key, scenario_id, timeout=600)")
    output.append("  run_recipe_and_wait(client, project_key, recipe_name, timeout=600)")
    output.append("  wait_for_job(job, timeout=600, poll_interval=2)")
    output.append("  get_job_log(client, project_key, job_id)")
    output.append("  compute_and_apply_schema(client, project_key, recipe_name)  # REQUIRED after creating/modifying recipes")
    output.append("")

    output.append("=== helpers.inspection ===")
    output.append("  dataset_info(client, project_key, dataset_name, sample_size=5)")
    output.append("  project_summary(client, project_key)")
    output.append("  list_projects_summary(client)")
    output.append("  connection_info(client, connection_name)")
    output.append("  list_connections_summary(client)")
    output.append("  user_info(client, login=None)")
    output.append("")

    output.append("=== helpers.search ===")
    output.append("  find_datasets(client, pattern, project_key=None)")
    output.append("  find_recipes(client, pattern, project_key=None)")
    output.append("  find_scenarios(client, pattern, project_key=None)")
    output.append("  find_by_connection(client, connection_name)")
    output.append("  find_by_type(client, dataset_type, project_key=None)")
    output.append("  find_users(client, pattern)")
    output.append("")

    output.append("=== helpers.export ===")
    output.append("  to_records(client, project_key, dataset_name, limit=100)")
    output.append("  sample(client, project_key, dataset_name, n=10)")
    output.append("  get_schema(client, project_key, dataset_name)")
    output.append("  get_column_names(client, project_key, dataset_name)")
    output.append("  count_rows(client, project_key, dataset_name)")
    output.append("  head(client, project_key, dataset_name, n=5)")
    output.append("  describe(client, project_key, dataset_name)")
    output.append("  to_csv_string(client, project_key, dataset_name, limit=100)")

    return "\n".join(output)


if __name__ == "__main__":
    # Run the MCP server
    mcp.run()
