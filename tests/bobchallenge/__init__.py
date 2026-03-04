"""
Bobchallenge test harness.

Usage:
    from tests.bobchallenge import setup, validate

    case = setup(client, "dates")
    # ... give case["prompt"] to your agent, pointed at case["project_key"] ...
    result = validate(client, "dates", case["project_key"])
    print(result)

    teardown(client, case["project_key"])
"""

import json
import time
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _load_fixture(name):
    path = FIXTURES_DIR / f"{name}.json"
    with open(path) as f:
        return json.load(f)


def setup(client, test_name):
    """Create a clean project and copy source datasets from BOBCHALLENGE.

    Returns dict with:
        - project_key: the new project key
        - prompt: the natural language task to give the agent
        - sources: list of source dataset names copied
    """
    fixture = _load_fixture(test_name)
    source_project = client.get_project(fixture["source_project"])

    # Create test project
    ts = int(time.time())
    project_key = f"BOBTEST_{test_name.upper()}_{ts}"
    client.create_project(project_key, project_key, owner="admin")
    test_project = client.get_project(project_key)

    # Copy source datasets
    for ds_name in fixture["sources"]:
        source_ds = source_project.get_dataset(ds_name)

        # Create dataset in test project
        builder = test_project.new_managed_dataset(ds_name)
        builder.with_store_into("filesystem_managed")
        builder.create()

        # Copy data from source to target (also syncs schema)
        target_ds = test_project.get_dataset(ds_name)
        future = source_ds.copy_to(target_ds, sync_schema=True)
        future.wait_for_result()

    return {
        "project_key": project_key,
        "prompt": fixture["prompt"],
        "sources": fixture["sources"],
    }


def validate(client, test_name, project_key):
    """Validate that the project outputs match expected fixture data.

    Returns dict with:
        - passed: bool
        - checks: list of individual check results
    """
    fixture = _load_fixture(test_name)
    project = client.get_project(project_key)
    checks = []

    # Check recipes: correct types and wiring
    expected_recipes = fixture.get("expected_recipes", [])
    if expected_recipes:
        actual_recipes = project.list_recipes()
        actual_by_output = {}
        for r in actual_recipes:
            recipe = project.get_recipe(r["name"])
            settings = recipe.get_settings()
            for out in settings.get_flat_output_refs():
                actual_by_output[out] = {
                    "name": r["name"],
                    "type": settings.type,
                    "inputs": sorted(settings.get_flat_input_refs()),
                }

        for exp_recipe in expected_recipes:
            output = exp_recipe["output"]
            actual = actual_by_output.get(output)

            if actual is None:
                checks.append({
                    "check": "recipe_exists",
                    "output": output,
                    "passed": False,
                    "message": f"No recipe produces '{output}'",
                })
                continue

            # Check recipe type
            type_ok = actual["type"] == exp_recipe["type"]
            checks.append({
                "check": "recipe_type",
                "output": output,
                "passed": type_ok,
                "expected": exp_recipe["type"],
                "actual": actual["type"],
            })

            # Check recipe inputs
            inputs_ok = sorted(actual["inputs"]) == sorted(exp_recipe["inputs"])
            checks.append({
                "check": "recipe_inputs",
                "output": output,
                "passed": inputs_ok,
                "expected": sorted(exp_recipe["inputs"]),
                "actual": sorted(actual["inputs"]),
            })

    for ds_name, expected in fixture["expected_outputs"].items():
        # Check dataset exists
        try:
            ds = project.get_dataset(ds_name)
            ds_def = ds.get_definition()
        except Exception:
            checks.append({
                "dataset": ds_name,
                "check": "exists",
                "passed": False,
                "message": f"Dataset '{ds_name}' not found",
            })
            continue

        checks.append({
            "dataset": ds_name,
            "check": "exists",
            "passed": True,
        })

        # Check schema (column names)
        actual_cols = [c["name"] for c in ds_def["schema"]["columns"]]
        expected_cols = [c["name"] for c in expected["schema"]]
        cols_match = set(actual_cols) == set(expected_cols)
        checks.append({
            "dataset": ds_name,
            "check": "schema_columns",
            "passed": cols_match,
            "expected": expected_cols,
            "actual": actual_cols,
        })

        if not cols_match:
            continue

        # Check data
        try:
            actual_rows = _read_rows(ds, project)
        except Exception as e:
            checks.append({
                "dataset": ds_name,
                "check": "data_readable",
                "passed": False,
                "message": str(e),
            })
            continue

        # Check row count
        count_match = len(actual_rows) == expected["row_count"]
        checks.append({
            "dataset": ds_name,
            "check": "row_count",
            "passed": count_match,
            "expected": expected["row_count"],
            "actual": len(actual_rows),
        })

        # Spot-check sample rows from fixture against actual data.
        # Match by row position (fixture data = first N rows in order).
        mismatches = []
        sample_data = expected.get("data", [])
        for i, exp in enumerate(sample_data):
            if i >= len(actual_rows):
                mismatches.append({
                    "row": i, "column": "*",
                    "expected": exp, "actual": "(missing row)",
                })
                continue
            actual = actual_rows[i]
            for col in expected_cols:
                actual_val = _normalize(actual.get(col))
                expected_val = _normalize(exp.get(col))
                if actual_val != expected_val:
                    mismatches.append({
                        "row": i, "column": col,
                        "expected": expected_val, "actual": actual_val,
                    })

        data_match = len(mismatches) == 0
        check = {
            "dataset": ds_name,
            "check": "data_values",
            "passed": data_match,
            "sample_size": len(sample_data),
            "mismatches": len(mismatches),
        }
        if not data_match:
            check["first_mismatches"] = mismatches[:5]
        checks.append(check)

    passed = all(c["passed"] for c in checks)
    return {"passed": passed, "checks": checks}


def teardown(client, project_key):
    """Delete the test project."""
    client.get_project(project_key).delete()


def _read_rows(ds, project):
    """Read all rows from a dataset as list of dicts. No MCP dependency."""
    schema = ds.get_definition().get("schema", {}).get("columns", [])
    col_names = [c["name"] for c in schema]
    rows = []
    for row in ds.iter_rows():
        if isinstance(row, dict):
            rows.append(row)
        else:
            rows.append(dict(zip(col_names, row)))
    return rows


def _normalize(val):
    """Normalize a value for comparison (handles datetime objects, timezone suffixes, etc.)."""
    if val is None:
        return None
    if hasattr(val, "isoformat"):
        return val.strftime("%Y-%m-%d")
    s = str(val)
    # Strip timezone suffix for date comparison
    for suffix in ["T00:00:00+00:00", "T00:00:00Z", "T00:00:00"]:
        if s.endswith(suffix):
            s = s[: -len(suffix)]
    return s
