"""Executor request/response protocol helpers."""

import json
import shlex
import subprocess
import tempfile
from pathlib import Path

PROTOCOL_VERSION = 1


def build_request(test_name, case, workspace=None):
    """Build the executor request payload for a test case."""
    return {
        "version": PROTOCOL_VERSION,
        "test_name": test_name,
        "project_key": case["project_key"],
        "prompt": case["prompt"],
        "sources": case["sources"],
        "workspace": str(workspace) if workspace else None,
    }


def run_executor(executor_command, request):
    """Run an executor command with request/response JSON files."""
    if not executor_command:
        raise ValueError("Executor command is required")

    args = shlex.split(executor_command)
    with tempfile.TemporaryDirectory(prefix="dataiku-eval-") as temp_dir:
        temp_path = Path(temp_dir)
        request_path = temp_path / "request.json"
        response_path = temp_path / "response.json"
        request_path.write_text(json.dumps(request, indent=2))

        completed = subprocess.run(
            [*args, "--request", str(request_path), "--response", str(response_path)],
            capture_output=True,
            text=True,
        )

        response = _load_response(response_path)
        return _merge_result(completed, response)


def _load_response(response_path):
    if not response_path.exists():
        return {}

    try:
        return json.loads(response_path.read_text())
    except json.JSONDecodeError as exc:
        return {
            "version": PROTOCOL_VERSION,
            "status": "failed",
            "summary": f"Executor wrote invalid JSON to {response_path}: {exc}",
        }


def _merge_result(completed, response):
    result = dict(response)
    result.setdefault("version", PROTOCOL_VERSION)
    result.setdefault("status", "completed" if completed.returncode == 0 else "failed")
    result.setdefault(
        "summary",
        "Executor completed without a summary"
        if completed.returncode == 0
        else f"Executor exited with code {completed.returncode}",
    )
    result.setdefault("stdout", result.get("stdout") or completed.stdout)
    result.setdefault("stderr", result.get("stderr") or completed.stderr)
    result.setdefault("stats", {})
    result["executor_returncode"] = completed.returncode
    return result
