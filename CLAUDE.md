# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

## Project Purpose

This project enables Claude Code to control Dataiku DSS through an MCP server. The MCP server provides a `client` object and helper functions for interacting with Dataiku.

## Using Dataiku

Use the `mcp__dataiku__execute_python` tool to run Python code. The execution environment includes:

- `client` - Authenticated DSSClient for the current instance
- `helpers.jobs` - Build and run operations
- `helpers.inspection` - Dataset and project info
- `helpers.search` - Find datasets, recipes, etc.
- `helpers.export` - Export data as records

### Examples

```python
# List projects
print(client.list_project_keys())

# Get project summary
from helpers.inspection import project_summary
print(project_summary(client, "PROJECT_KEY"))

# Build a dataset
from helpers.jobs import build_and_wait
build_and_wait(client, "PROJECT_KEY", "dataset_name")
```

### Multi-Instance Support

Use `mcp__dataiku__use_instance` to switch between configured instances.
Use `mcp__dataiku__list_instances` to see available instances.

## Important: Schema Updates

After creating or modifying a recipe, you **must** compute and apply schema before building:

```python
from helpers.jobs import compute_and_apply_schema
compute_and_apply_schema(client, "PROJECT", "recipe_name")
```

## Skills

This project includes skills in `.claude/skills/` that are automatically discovered by Claude Code. Each skill contains a `SKILL.md` with usage guidance and a `references/` folder with detailed code examples.

### How to Use Skills Effectively

1. **Always read the relevant reference files** before writing Dataiku API code — do not rely on general knowledge. Dataiku's API has subtle differences from similar tools.
2. **Read the Pitfalls section** at the top of each reference file before writing code. Each file documents its own gotchas inline. See `references/pitfalls.md` for a quick index.
3. **Use tested patterns** from `references/patterns/` when available — copy and adapt rather than writing from scratch.
4. **Always verify output data** after running a recipe. Sample the output and check values before reporting success. Recipes can succeed but produce wrong data.

## Tests

The `tests/harness/` folder contains an agent-agnostic test harness that validates whether a coding agent can build Dataiku pipelines correctly. Each fixture references a source project on the Dataiku instance (e.g. `BOBCHALLENGE`) but the harness works with any project.

### How It Works

Each test case has three phases:

1. **Setup** — creates a clean Dataiku project and copies source datasets
2. **Agent execution** — the agent receives a natural language prompt and builds the pipeline (this step is the caller's responsibility)
3. **Validate** — checks the agent's work against expected results

### Validation Checks

- **no_python_recipes** — did the agent use visual recipes instead of defaulting to Python?
- **recipe_type_count** — are the right kinds of recipes present (e.g. at least 1 join, 3 prepare)?
- **exists** — does the expected output dataset exist?
- **schema_columns** — does the output have the right columns?
- **row_count** — does the output have the expected number of rows?
- **data_values** — do spot-checked rows match expected values?

### Interactive Usage (via MCP)

```python
from tests.harness import setup, validate, teardown

case = setup(client, "dates")       # creates project, copies source data
print(case["prompt"])               # give this prompt to the agent under test

# ... agent builds the pipeline in case["project_key"] ...

result = validate(client, "dates", case["project_key"])
print(result)                       # {"passed": True/False, "checks": [...]}

teardown(client, case["project_key"])  # optional cleanup
```

### CLI Usage

```bash
# Run with auto-cleanup
python tests/run_test.py dates

# Run and keep the project for inspection
python tests/run_test.py dates --keep
```

Requires `DATAIKU_URL` and `DATAIKU_API_KEY` environment variables. The CLI runner invokes `claude -p` as the agent, but the framework is agent-agnostic — swap in any agent that can talk to Dataiku.

### Adding Test Cases

Drop a new JSON file in `tests/harness/fixtures/`. Each fixture specifies:

- `prompt` — the natural language task
- `sources` — datasets to copy from `BOBCHALLENGE`
- `expected_recipes` — recipe types and wiring to validate
- `expected_outputs` — schema, row count, and sample data to check

### Important: Visual Recipes Preferred

The test harness validates that agents use Dataiku's visual recipes (prepare, join, group, window, etc.) when appropriate, rather than writing Python recipes. Python recipes should only be used when visual recipes are insufficient.

## API Documentation

- [Developer Guide](https://developer.dataiku.com/latest/index.html)
- [Python API Reference](https://developer.dataiku.com/latest/api-reference/python/client.html)
