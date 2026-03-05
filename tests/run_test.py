#!/usr/bin/env python3
"""Run a test case against an agent.

Usage:
    python tests/run_test.py dates
    python tests/run_test.py dates --keep           # don't delete the test project
    python tests/run_test.py dates --agent claude    # explicit agent (default)

Requires DATAIKU_URL and DATAIKU_API_KEY environment variables.
"""

import argparse
import importlib
import os
import sys
import time

import dataikuapi

from evals import setup, validate, teardown


def _load_agent(name):
    """Load an agent adapter by name from the agents package."""
    return importlib.import_module(f"agents.{name}")


def run(test_name, keep=False, agent_name="claude"):
    url = os.environ["DATAIKU_URL"]
    key = os.environ["DATAIKU_API_KEY"]
    client = dataikuapi.DSSClient(url, key)
    client._session.verify = False

    print(f"--- Setting up test: {test_name}")
    case = setup(client, test_name)
    print(f"    Project: {case['project_key']}")
    print(f"    Sources: {case['sources']}")

    agent = _load_agent(agent_name)
    print(f"\n--- Running agent ({agent_name})...")
    prompt = (
        f"You are working in Dataiku project '{case['project_key']}'. "
        f"The project already has these source datasets: {case['sources']}. "
        f"{case['prompt']}\n\n"
        f"Build and verify the output dataset before finishing."
    )

    start = time.time()
    agent_result = agent.run(prompt, case["project_key"])
    duration_ms = int((time.time() - start) * 1000)

    stdout = agent_result.get("stdout", "")
    print(stdout[-500:] if len(stdout) > 500 else stdout)
    if agent_result.get("returncode", 0) != 0:
        print(f"    Agent failed (exit code {agent_result['returncode']})")
        stderr = agent_result.get("stderr", "")
        print(stderr[-500:])

    agent_stats = {"duration_ms": duration_ms, **agent_result.get("stats", {})}

    print(f"\n--- Validating...")
    result = validate(client, test_name, case["project_key"], agent_stats=agent_stats)

    for check in result["checks"]:
        status = "PASS" if check["passed"] else "FAIL"
        detail = ""
        if not check["passed"]:
            detail = f" — {check.get('message', check.get('first_mismatches', ''))}"
        print(f"    {check['check']}: {status}{detail}")

    print(f"\n{'PASSED' if result['passed'] else 'FAILED'}")

    if result.get("agent_stats"):
        stats = result["agent_stats"]
        duration_s = stats.get("duration_ms", 0) / 1000
        print(f"\n--- Agent stats:")
        print(f"    Duration: {duration_s:.1f}s")
        if "total_tokens" in stats:
            print(f"    Tokens: {stats['total_tokens']:,}")
        if "tool_uses" in stats:
            print(f"    Tool calls: {stats['tool_uses']}")

    if keep:
        print(f"\n--- Keeping project: {case['project_key']}")
    else:
        print(f"\n--- Cleaning up...")
        teardown(client, case["project_key"])

    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a Dataiku agent test case")
    parser.add_argument("test_name", nargs="?", default="dates")
    parser.add_argument("--keep", action="store_true", help="Keep the test project after validation")
    parser.add_argument("--agent", default="claude", help="Agent adapter to use (default: claude)")
    args = parser.parse_args()

    result = run(args.test_name, keep=args.keep, agent_name=args.agent)
    sys.exit(0 if result["passed"] else 1)
