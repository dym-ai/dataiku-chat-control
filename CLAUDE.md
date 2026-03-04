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

## API Documentation

- [Developer Guide](https://developer.dataiku.com/latest/index.html)
- [Python API Reference](https://developer.dataiku.com/latest/api-reference/python/client.html)
