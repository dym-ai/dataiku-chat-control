# Dataiku Agent Test Suite

An agent-agnostic test harness for validating whether a coding agent can build Dataiku pipelines correctly.

## How It Works

The test suite has three components:

- **Source projects** — Dataiku projects with hand-built pipelines that serve as the answer key (e.g. `BOBCHALLENGE`, or any project you choose)
- **Fixtures** (`evals/fixtures/*.json`) — snapshots of what "correct" looks like: the prompt to give the agent, expected recipe types, and expected output data
- **Harness** (`evals/__init__.py`) — three functions: `setup()`, `validate()`, `teardown()`

Each fixture references a `source_project` on your Dataiku instance. You can write fixtures against any project — they're not tied to a specific one.

### The Three Phases

**1. Setup** creates a fresh Dataiku project and copies source datasets from the fixture's source project:

```python
case = setup(client, "dates")
# Returns: {project_key: "BOBTEST_DATES_...", prompt: "I have a dataset...", sources: ["Dates"]}
```

At this point you have a clean project with only source data. No recipes, no outputs.

**2. Agent execution** is your responsibility. Give the prompt to whatever agent you're testing — Claude Code, OpenAI, LangChain, a custom agent, or even a human. The framework doesn't care how the pipeline gets built.

**3. Validate** inspects the project and checks:

| Check | What It Verifies |
|-------|-----------------|
| `no_python_recipes` | Agent used visual recipes, not Python |
| `recipe_type_count` | Right kinds of recipes are present (e.g. at least 1 join, 3 prepare) |
| `exists` | Expected output dataset exists |
| `schema_columns` | Output has the right columns |
| `row_count` | Output has the expected number of rows |
| `data_values` | Spot-checked sample rows match expected values |

```python
result = validate(client, "dates", case["project_key"])
# Returns: {passed: True/False, checks: [...], agent_stats: {...}}
```

## Available Test Cases

These fixtures ship with the repo (source project: `BOBCHALLENGE`):

| Fixture | Recipes | Recipe Types | What It Tests |
|---------|---------|-------------|---------------|
| `dates` | 1 | prepare | Date parsing + GREL formula to compute end-of-month |
| `crane` | 5 | 2× prepare, join, prepare, group | Multi-step pipeline: filter, cross join, overlap calculation, aggregation |

## Usage

### Prerequisites

- A running Dataiku DSS instance with the source project referenced by your fixtures
- Source datasets in that project must have data (uploaded files)
- Python with `dataikuapi` installed

### Option A: Interactive (via MCP session)

If you're in a Claude Code session (or any agent session) with the Dataiku MCP server connected:

```python
from tests.evals import setup, validate, teardown

# 1. Create the test project
case = setup(client, "dates")
print(case["prompt"])       # The task to give the agent
print(case["project_key"])  # The project to work in

# 2. Give the prompt to your agent, tell it to work in the test project
#    ... agent builds the pipeline ...

# 3. Validate the result
result = validate(client, "dates", case["project_key"])
for check in result["checks"]:
    status = "PASS" if check["passed"] else "FAIL"
    print(f"  {check['check']}: {status}")

# 4. Clean up (optional — skip to inspect the project in the Dataiku UI)
teardown(client, case["project_key"])
```

You can pass agent performance stats to `validate()` for tracking:

```python
result = validate(client, "dates", case["project_key"], agent_stats={
    "total_tokens": 29873,
    "tool_uses": 26,
    "duration_ms": 106627,
})
print(result["agent_stats"])  # Included in the result
```

### Option B: CLI (automated)

Uses Claude Code by default, but any agent adapter can be selected with `--agent`:

```bash
export DATAIKU_URL=https://your-instance.dataiku.com
export DATAIKU_API_KEY=your-api-key

# Run a test case (creates project, runs agent, validates, cleans up)
python tests/run_test.py dates

# Keep the project after validation for inspection
python tests/run_test.py crane --keep

# Use a different agent adapter
python tests/run_test.py dates --agent my_agent
```

### Writing an Agent Adapter

Create a Python module in `tests/agents/` that exports a `run` function:

```python
# tests/agents/my_agent.py

def run(prompt, project_key):
    """Execute the agent and return results.

    Returns:
        {"stdout": str, "returncode": int, "stats": dict}
    """
    # ... invoke your agent here ...
    return {
        "stdout": output_text,
        "returncode": 0,
        "stats": {"total_tokens": 1234, "tool_uses": 10},
    }
```

The runner handles timing (`duration_ms`) automatically and merges it with any stats your adapter returns.

### Option C: As a Benchmark

Run the same fixture against different agents and compare results:

```bash
python tests/run_test.py dates --agent claude
python tests/run_test.py dates --agent my_agent
```

```
claude:   dates PASS   107s   29k tokens   26 tool calls
my_agent: dates PASS   180s   45k tokens   52 tool calls
other:    dates FAIL   — used python recipe instead of visual
```

## What Gets Graded

The framework validates **outcomes over process**:

- It **doesn't** care about intermediate dataset names (agents pick their own)
- It **doesn't** care about the exact number of recipe steps
- It **does** care that visual recipes were used, the right recipe types are present, and the final output data is correct

The one hard rule: **no Python recipes when visual recipes would suffice**. The point is to test whether the agent can use Dataiku's visual recipe system properly, not whether it can write pandas code.

## Adding a New Test Case

1. Build the pipeline in your source project (or verify it's already built)
2. Create a new JSON file in `evals/fixtures/`. The fixture schema:

```json
{
  "name": "my_test",
  "description": "What this test validates.",
  "prompt": "The natural language task to give the agent...",
  "source_project": "MY_PROJECT",
  "sources": ["Source_Dataset_Name"],
  "source_renames": {
    "Ugly_Long_Dataset_Name": "Clean_Name"
  },
  "expected_recipes": [
    {"type": "shaker", "inputs": ["Clean_Name"], "output": "intermediate"},
    {"type": "grouping", "inputs": ["intermediate"], "output": "final_output"}
  ],
  "expected_outputs": {
    "final_output": {
      "schema": [
        {"name": "column_name", "type": "bigint"}
      ],
      "row_count": 42,
      "data": [
        {"column_name": "expected_value"}
      ]
    }
  }
}
```

Key fields:
- **`source_project`** — any Dataiku project on your instance that has the source data
- **`prompt`** — describe the task naturally; this is what the agent sees
- **`sources`** — datasets to copy from the source project into the test project
- **`source_renames`** — optional mapping to give datasets cleaner names in the test project
- **`expected_recipes`** — recipe types that should be used (validated by count, not exact names)
- **`expected_outputs`** — the final output to validate (schema + row count + sample data for spot-checking)

3. Test it: `python tests/run_test.py my_test --keep`

## Included BOBCHALLENGE Pipelines

The `BOBCHALLENGE` project has additional pipelines that could be turned into fixtures:

| Use Case | Recipes | Recipe Types | Description |
|----------|---------|-------------|-------------|
| avocado | 5 | prepare, group, window, topn | Avocado sales YoY analysis by region |
| barbie | 6 | sampling, group, window, prepare | Barbie career analysis over decades |
| mk8 | 7 | prepare, join, sort | Mario Kart 8 optimal kart ranking |
| sox_compliance | 11 | prepare, join, group, stack | SOX audit — flag issues in control sign-off log |
| ev | 13 | sampling, group, window, topn | EV population trends and model gaps |
| stocks | 14 | stack, prepare, group, topn | Stock volatility, best/worst months, annual gains |
