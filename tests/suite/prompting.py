"""Shared prompt construction for bundled executors."""


def build_executor_prompt(request):
    return "\n\n".join(
        [
            "Use the repository scaffolding available in this workspace when helpful, "
            "including local docs, scripts, MCP helpers, and skills, as optional aids for carrying "
            "out this benchmark task.",
            f"You are working in Dataiku project '{request['project_key']}'. "
            f"The project already has these source datasets: {request.get('sources', [])}.",
            request["prompt"],
            "Build and verify the required output dataset before finishing. "
            "Use the benchmark prompt and the runtime behavior as the source of truth for task "
            "requirements. "
            "Prefer Dataiku visual recipes when possible and avoid Python recipes unless a visual "
            "recipe is impossible for the task. "
            "If you use repository Dataiku tools that require authentication, read the API key "
            "from the DATAIKU_API_KEY environment variable.",
        ]
    )
