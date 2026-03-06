# Dataiku Agent Test Suite

An executor-agnostic test harness for validating whether a coding agent, automation, or human workflow can build Dataiku pipelines correctly.

## How It Works

The test suite has four components:

- **Source projects** — Dataiku projects with hand-built pipelines that serve as the answer key (for example `BOBCHALLENGE`, or any project you choose)
- **Fixtures** (`evals/fixtures/*.json`) — snapshots of what "correct" looks like: the prompt to give the executor, expected recipe types, and expected output data
- **Evaluation core** (`evals/__init__.py`) — three functions: `setup()`, `validate()`, `teardown()`
- **Executors** (`executors/*.py`) — black-box protocol implementations that actually perform the work (Codex CLI, Claude Code CLI, or your own custom executor)

Each fixture references a `source_project` on your Dataiku instance. You can write fixtures against any project. Fixtures are not tied to a single source project.

### The Three Phases

**1. Setup** creates a fresh Dataiku project and copies source datasets from the fixture's source project:

```python
case = setup(client, "dates")
# Returns: {project_key: "BOBTEST_DATES_...", prompt: "I have a dataset...", sources: ["Dates"]}
```

At this point you have a clean project with only source data. No recipes, no outputs.

**2. Executor execution** is your responsibility. The suite writes a request JSON and invokes any executor command you provide. The executor can use Claude Code, Codex, MCP tools, browser automation, or even a human-in-the-loop flow. The suite does not care how the pipeline gets built.

**3. Validate** inspects the project and checks:

| Check | What It Verifies |
|-------|-----------------|
| `no_python_recipes` | Agent used visual recipes, not Python |
| `recipe_type_count` | Right kinds of recipes are present (for example at least 1 join, 3 prepare) |
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
- `DATAIKU_URL` and `DATAIKU_API_KEY` exported in your shell
- A Dataiku API key with permission to create and delete projects
- Optional: `DATAIKU_SSL_VERIFY=true|false|/path/to/ca-bundle.pem` for TLS verification control

### Option A: Interactive

If you want to drive the executor manually, use the evaluation core directly:

```python
from tests.evals import setup, validate, teardown

case = setup(client, "dates")
print(case["prompt"])
print(case["project_key"])

# Run your executor manually here

result = validate(client, "dates", case["project_key"])
for check in result["checks"]:
    status = "PASS" if check["passed"] else "FAIL"
    print(f"{check['check']}: {status}")

teardown(client, case["project_key"])
```

### Option B: CLI

Use the bundled Claude executor by default:

```bash
python tests/run_test.py dates
```

If your Dataiku instance uses an internal or custom certificate, you can control TLS verification explicitly:

```bash
DATAIKU_SSL_VERIFY=false python tests/run_test.py dates
DATAIKU_SSL_VERIFY=/path/to/root-ca.pem python tests/run_test.py dates
```

Use the bundled Codex executor against another workspace:

```bash
python tests/run_test.py dates --agent codex --workspace /path/to/workspace
```

Keep the project after validation for inspection:

```bash
python tests/run_test.py crane --keep
```

Use a custom executor command:

```bash
python tests/run_test.py dates --executor "python /path/to/my_executor.py" --workspace /path/to/workspace
```

### Executor Protocol

The suite invokes an executor command by appending two arguments:

```bash
--request /tmp/request.json --response /tmp/response.json
```

The request JSON contains:

```json
{
  "version": 1,
  "test_name": "dates",
  "project_key": "BOBTEST_DATES_...",
  "prompt": "The natural language task...",
  "sources": ["Dates"],
  "workspace": "/optional/workspace/path"
}
```

The response JSON should contain:

```json
{
  "version": 1,
  "status": "completed",
  "summary": "Short human-readable summary",
  "stdout": "Optional executor output",
  "stderr": "Optional executor stderr",
  "stats": {
    "duration_ms": 12345,
    "total_tokens": 1234,
    "tool_uses": 10
  }
}
```

The final CLI report includes:

- pass/fail status and per-check results
- executor stats when available, such as duration and token usage
- a direct project URL when `--keep` is used

Suggested `status` values:

- `completed`
- `failed`
- `aborted`
- `unsupported`

Bundled examples live in:

- `tests/executors/codex_cli.py`
- `tests/executors/claude_cli.py`

### Example: Codex Against Another Workspace

If your agent tooling lives in another repo, point the suite at that workspace:

```bash
python tests/run_test.py dates \
  --agent codex \
  --workspace /Users/dmitriryssev/Documents/GitHub/dataiku-agent-dev-kit
```

The suite still owns setup, validation, and reporting. The executor just receives the prompt, project key, source datasets, and workspace path.

## What Gets Graded

The framework validates **outcomes over process**:

- It **doesn't** care about intermediate dataset names
- It **doesn't** care about the exact number of recipe steps
- It **does** care that visual recipes were used, the right recipe types are present, and the final output data is correct

The one hard rule: **no Python recipes when visual recipes would suffice**. The point is to test whether the executor can use Dataiku's visual recipe system properly, not whether it can write pandas code.

## Adding a New Test Case

1. Build the pipeline in your source project, or verify it is already built.
2. Create a new JSON file in `evals/fixtures/`. The fixture schema:

```json
{
  "name": "my_test",
  "description": "What this test validates.",
  "prompt": "The natural language task to give the executor...",
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
- **`prompt`** — describe the task naturally; this is what the executor sees
- **`sources`** — datasets to copy from the source project into the test project
- **`source_renames`** — optional mapping to give datasets cleaner names in the test project
- **`expected_recipes`** — recipe types that should be used, validated by count rather than exact names
- **`expected_outputs`** — the final output to validate: schema, row count, and sample data for spot-checking

3. Test it:

```bash
python tests/run_test.py my_test --keep
```

## Included BOBCHALLENGE Pipelines

The `BOBCHALLENGE` project has additional pipelines that could be turned into fixtures:

| Use Case | Recipes | Recipe Types | Description |
|----------|---------|-------------|-------------|
| avocado | 5 | prepare, group, window, topn | Avocado sales YoY analysis by region |
| barbie | 6 | sampling, group, window, prepare | Barbie career analysis over decades |
| mk8 | 7 | prepare, join, sort | Mario Kart 8 optimal kart ranking |
| sox_compliance | 11 | prepare, join, group, stack | SOX audit - flag issues in control sign-off log |
| ev | 13 | sampling, group, window, topn | EV population trends and model gaps |
| stocks | 14 | stack, prepare, group, topn | Stock volatility, best/worst months, annual gains |
