#!/usr/bin/env python3
"""Run a bobchallenge test case against an agent.

Usage:
    python tests/run_test.py dates
    python tests/run_test.py dates --keep    # don't delete the test project

Requires DATAIKU_URL and DATAIKU_API_KEY environment variables.
"""

import argparse
import os
import sys
import subprocess

import dataikuapi

from bobchallenge import setup, validate, teardown


def run(test_name, keep=False):
    url = os.environ["DATAIKU_URL"]
    key = os.environ["DATAIKU_API_KEY"]
    client = dataikuapi.DSSClient(url, key)
    client._session.verify = False

    print(f"--- Setting up test: {test_name}")
    case = setup(client, test_name)
    print(f"    Project: {case['project_key']}")
    print(f"    Sources: {case['sources']}")

    print(f"\n--- Running agent...")
    prompt = (
        f"You are working in Dataiku project '{case['project_key']}'. "
        f"The project already has these source datasets: {case['sources']}. "
        f"{case['prompt']}\n\n"
        f"Build and verify the output dataset before finishing."
    )

    result = subprocess.run(
        ["claude", "-p", prompt],
        capture_output=True,
        text=True,
    )
    print(result.stdout[-500:] if len(result.stdout) > 500 else result.stdout)
    if result.returncode != 0:
        print(f"    Agent failed (exit code {result.returncode})")
        print(result.stderr[-500:])

    print(f"\n--- Validating...")
    result = validate(client, test_name, case["project_key"])

    for check in result["checks"]:
        status = "PASS" if check["passed"] else "FAIL"
        detail = ""
        if not check["passed"]:
            detail = f" — {check.get('message', check.get('first_mismatches', ''))}"
        print(f"    {check['check']}: {status}{detail}")

    print(f"\n{'PASSED' if result['passed'] else 'FAILED'}")

    if keep:
        print(f"\n--- Keeping project: {case['project_key']}")
    else:
        print(f"\n--- Cleaning up...")
        teardown(client, case["project_key"])

    return result["passed"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a bobchallenge test case")
    parser.add_argument("test_name", nargs="?", default="dates")
    parser.add_argument("--keep", action="store_true", help="Keep the test project after validation")
    args = parser.parse_args()

    passed = run(args.test_name, keep=args.keep)
    sys.exit(0 if passed else 1)
