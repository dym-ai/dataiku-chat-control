"""OpenAI Codex CLI agent adapter.

Invokes ``codex exec`` non-interactively with full-auto mode and
network access enabled (needed for Dataiku API calls).
"""

import subprocess


def run(prompt, project_key):
    """Run Codex CLI with the given prompt.

    Returns:
        {"stdout": str, "stderr": str, "returncode": int, "stats": dict}
    """
    result = subprocess.run(
        [
            "codex", "exec",
            "--full-auto",
            "--sandbox", "danger-full-access",
            prompt,
        ],
        capture_output=True,
        text=True,
    )

    return {
        "stdout": result.stdout,
        "stderr": result.stderr,
        "returncode": result.returncode,
        "stats": {},
    }
