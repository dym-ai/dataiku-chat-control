#!/usr/bin/env python3
"""Run a test case against an executor.

Usage:
    python tests/run_test.py dates
    python tests/run_test.py dates --keep
    python tests/run_test.py dates --agent codex --workspace /path/to/workspace
    python tests/run_test.py dates --executor "python tests/executors/codex_cli.py"

Requires DATAIKU_URL and DATAIKU_API_KEY environment variables.
"""

import argparse
import os
import shlex
import sys
from pathlib import Path

import dataikuapi
import urllib3

from evals import setup, validate, teardown
from suite.protocol import build_request, run_executor
from suite.report import format_report


def _resolve_executor_command(agent_name, executor_command):
    if executor_command:
        return executor_command

    script = Path(__file__).parent / "executors" / f"{agent_name}_cli.py"
    return f"{shlex.quote(sys.executable)} {shlex.quote(str(script))}"


def _configure_ssl_verify(client):
    ssl_verify = os.environ.get("DATAIKU_SSL_VERIFY", "true")
    lowered = ssl_verify.lower()

    if lowered == "false":
        client._session.verify = False
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        return

    if lowered == "true":
        client._session.verify = True
        return

    client._session.verify = ssl_verify


def _build_project_url(base_url, project_key):
    return f"{base_url.rstrip('/')}/projects/{project_key}/"


def run(test_name, keep=False, agent_name="claude", executor_command=None, workspace=None):
    url = os.environ["DATAIKU_URL"]
    key = os.environ["DATAIKU_API_KEY"]
    client = dataikuapi.DSSClient(url, key)
    _configure_ssl_verify(client)

    print(f"--- Setting up test: {test_name}")
    try:
        case = setup(client, test_name)
    except Exception as exc:
        print(f"Setup failed: {exc}")
        return {"passed": False, "stage": "setup", "error": str(exc)}
    print(f"    Project: {case['project_key']}")
    print(f"    Sources: {case['sources']}")

    try:
        executor = _resolve_executor_command(agent_name, executor_command)
        print(f"\n--- Running executor...")
        request = build_request(test_name, case, workspace=workspace)
        executor_result = run_executor(executor, request)
        print(executor_result.get("summary", "Executor completed"))

        print(f"\n--- Validating...")
        result = validate(client, test_name, case["project_key"], agent_stats=executor_result.get("stats"))
        print()
        print(
            format_report(
                test_name,
                case["project_key"],
                executor_result,
                result,
                project_url=_build_project_url(url, case["project_key"]) if keep else None,
            )
        )
    finally:
        if keep:
            print(f"\n--- Keeping project: {case['project_key']}")
        else:
            print(f"\n--- Cleaning up...")
            teardown(client, case["project_key"])

    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a Dataiku agent evaluation case")
    parser.add_argument("test_name", nargs="?", default="dates")
    parser.add_argument("--keep", action="store_true", help="Keep the test project after validation")
    parser.add_argument(
        "--workspace",
        help="Workspace path to include in the executor request (defaults to current directory)",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--agent",
        choices=["claude", "codex"],
        default="claude",
        help="Bundled executor to use (default: claude)",
    )
    group.add_argument(
        "--executor",
        help="Custom executor command implementing the request/response protocol",
    )
    args = parser.parse_args()

    result = run(
        args.test_name,
        keep=args.keep,
        agent_name=args.agent,
        executor_command=args.executor,
        workspace=Path(args.workspace).resolve() if args.workspace else Path.cwd(),
    )
    sys.exit(0 if result["passed"] else 1)
