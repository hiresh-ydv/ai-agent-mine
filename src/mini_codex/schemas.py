"""Tool input models plus the JSON schemas handed to the LLM.

The argument models are used by the dispatcher to validate every tool call in
Python before it runs. The JSON schemas are derived from the same source of
truth so the model and the runtime never drift apart.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from .errors import ToolError


class SearchCodebaseArgs(BaseModel):
    query: str = Field(..., description="Term, symbol, or phrase to search for.")
    extensions: list[str] | None = Field(
        default=None, description="Optional list of allowed file extensions, e.g. ['.py']."
    )
    max_results: int | None = Field(
        default=None, ge=1, le=500, description="Maximum number of matching files to return."
    )


class SearchInFileArgs(BaseModel):
    path: str = Field(..., description="Project-relative path of the file to search within.")
    query: str = Field(..., description="Literal term or regular expression to find.")
    context_lines: int | None = Field(
        default=0, ge=0, le=20, description="Number of surrounding lines to include per match."
    )
    regex: bool = Field(default=False, description="Treat the query as a regular expression.")


class ReadFileArgs(BaseModel):
    path: str = Field(..., description="Project-relative path of the file to read.")
    start_line: int = Field(..., ge=1, description="First line to return (1-indexed).")
    end_line: int = Field(..., ge=1, description="Last line to return (inclusive).")


class ProposeEditArgs(BaseModel):
    path: str = Field(..., description="Project-relative path of the file to edit.")
    old_text: str = Field(..., description="Exact existing source text to replace.")
    new_text: str = Field(..., description="Replacement source text.")
    reason: str = Field(..., description="Concise explanation of why this edit fixes the issue.")


class RequestApprovalArgs(BaseModel):
    patch_id: str = Field(..., description="Identifier of the pending patch to review and apply.")


class RunTestsArgs(BaseModel):
    test_target: str | None = Field(
        default=None, description="Optional project-relative test file or target to run."
    )
    test_profile: str | None = Field(
        default="default", description="Named, predefined and trusted test profile."
    )


def _parameters(model: type[BaseModel], required: list[str]) -> dict[str, Any]:
    schema = model.model_json_schema()
    properties = schema.get("properties", {})
    # Drop pydantic bookkeeping that models do not need to see.
    for prop in properties.values():
        prop.pop("title", None)
    return {
        "type": "object",
        "properties": properties,
        "required": required,
        "additionalProperties": False,
    }


# Ordered list of every tool the model is allowed to call.
TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "search_codebase",
        "description": (
            "Search the project for files and lines matching a term or symbol. "
            "Use this first to locate relevant files without being told their paths."
        ),
        "model": SearchCodebaseArgs,
        "required": ["query"],
    },
    {
        "name": "search_in_file",
        "description": (
            "Search inside one project file for a literal term or regular expression, "
            "returning matching line numbers and optional context."
        ),
        "model": SearchInFileArgs,
        "required": ["path", "query"],
    },
    {
        "name": "read_file",
        "description": (
            "Read an exact line range from a project file. Returns each line with its "
            "1-indexed line number so you can reference precise locations."
        ),
        "model": ReadFileArgs,
        "required": ["path", "start_line", "end_line"],
    },
    {
        "name": "propose_edit",
        "description": (
            "Prepare a minimal patch for a file WITHOUT modifying it. The old_text must "
            "be an exact, unique snippet of the current file contents. Returns a patch_id "
            "and a unified diff; it does not change any file."
        ),
        "model": ProposeEditArgs,
        "required": ["path", "old_text", "new_text", "reason"],
    },
    {
        "name": "request_approval_and_apply",
        "description": (
            "Show the pending patch to the human and apply it ONLY if they approve. "
            "Use the patch_id returned by propose_edit. If the human rejects, stop and "
            "report that no changes were made."
        ),
        "model": RequestApprovalArgs,
        "required": ["patch_id"],
    },
    {
        "name": "run_tests",
        "description": (
            "Run the project's approved test command (pytest) after a patch is applied. "
            "Returns the real exit code and bounded output. Never assume tests passed "
            "without calling this tool."
        ),
        "model": RunTestsArgs,
        "required": [],
    },
]

_BY_NAME = {definition["name"]: definition for definition in TOOL_DEFINITIONS}


def tool_schemas() -> list[dict[str, Any]]:
    """Return tool definitions in the OpenAI/Groq function-calling format."""

    schemas = []
    for definition in TOOL_DEFINITIONS:
        schemas.append(
            {
                "type": "function",
                "function": {
                    "name": definition["name"],
                    "description": definition["description"],
                    "parameters": _parameters(definition["model"], definition["required"]),
                },
            }
        )
    return schemas


def model_for(tool_name: str) -> type[BaseModel]:
    definition = _BY_NAME.get(tool_name)
    if definition is None:
        raise ToolError(f"Unknown tool: {tool_name}")
    return definition["model"]
