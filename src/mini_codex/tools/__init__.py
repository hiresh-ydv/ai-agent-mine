"""Tool registry: maps every model-callable tool to its schema and handler."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from ..schemas import TOOL_DEFINITIONS, model_for, tool_schemas
from . import approval, propose_edit, read_file, run_tests, search_codebase, search_in_file

Handler = Callable[[dict[str, Any], Any], dict[str, Any]]

_HANDLERS: dict[str, Handler] = {
    "search_codebase": search_codebase.run,
    "search_in_file": search_in_file.run,
    "read_file": read_file.run,
    "propose_edit": propose_edit.run,
    "request_approval_and_apply": approval.run,
    "run_tests": run_tests.run,
}


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    parameters: dict[str, Any]
    model: type
    handler: Handler


def build_registry() -> dict[str, ToolSpec]:
    registry: dict[str, ToolSpec] = {}
    for definition in TOOL_DEFINITIONS:
        name = definition["name"]
        registry[name] = ToolSpec(
            name=name,
            description=definition["description"],
            parameters=_parameters(definition),
            model=model_for(name),
            handler=_HANDLERS[name],
        )
    return registry


def _parameters(definition: dict[str, Any]) -> dict[str, Any]:
    parameters = dict(definition["model"].model_json_schema())
    for prop in parameters.get("properties", {}).values():
        prop.pop("title", None)
    return parameters


__all__ = ["ToolSpec", "build_registry", "tool_schemas"]
