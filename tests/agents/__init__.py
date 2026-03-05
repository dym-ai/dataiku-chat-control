"""Agent adapters for the test runner.

Each adapter module must export a ``run`` function with this signature::

    def run(prompt: str, project_key: str) -> dict:
        \"\"\"Execute the agent and return results.

        Returns:
            {
                "stdout": str,       # agent's stdout output
                "returncode": int,   # 0 = success
                "stats": dict,       # optional: {"total_tokens": int, "tool_uses": int, ...}
            }
        \"\"\"

The runner owns timing (``duration_ms``) and merges it with the adapter's
returned stats before passing them to ``validate()``.

Built-in adapters:
- ``claude`` — invokes ``claude -p`` via subprocess (default)
"""
