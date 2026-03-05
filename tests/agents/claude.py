"""Claude Code agent adapter.

Invokes ``claude -p <prompt>`` via subprocess and parses usage stats from
the CLI output.
"""

import re
import subprocess


def _parse_stats(stdout):
    """Extract usage stats from claude CLI output."""
    stats = {}

    for line in stdout.splitlines():
        line = line.strip()
        if "total_tokens" in line:
            m = re.search(r"total_tokens[:\s]+(\d+)", line)
            if m:
                stats["total_tokens"] = int(m.group(1))
        if "tool_uses" in line or "tool_calls" in line:
            m = re.search(r"(?:tool_uses|tool_calls)[:\s]+(\d+)", line)
            if m:
                stats["tool_uses"] = int(m.group(1))

    return stats


def run(prompt, project_key):
    """Run Claude Code with the given prompt.

    Returns:
        {"stdout": str, "returncode": int, "stats": dict}
    """
    result = subprocess.run(
        ["claude", "-p", prompt],
        capture_output=True,
        text=True,
    )

    return {
        "stdout": result.stdout,
        "stderr": result.stderr,
        "returncode": result.returncode,
        "stats": _parse_stats(result.stdout),
    }
