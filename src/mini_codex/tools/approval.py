"""Tool 5: show the pending diff and apply it only after human approval."""

from __future__ import annotations

from typing import Any

from ..console import confirm
from ..context import ToolContext
from ..errors import ToolError
from ..safety.patch_validation import (
    atomic_write_text,
    create_backup,
    fingerprint,
    read_text_raw,
)
from ..safety.paths import resolve_within_root
from ..state import Patch, Status


def _display(ctx: ToolContext, patch: Patch) -> None:
    console = ctx.console
    console.rule("Proposed change")
    console.write(f"File:   {patch.relative_path}")
    console.write(f"Reason: {patch.reason}")
    console.write("")
    console.write("--- Diff ---")
    diff = patch.unified_diff.rstrip("\n")
    if diff.strip():
        console.block(diff.splitlines())
    else:
        console.write("(no textual difference)")
    console.write("--- End diff ---")


def run(args: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    patch_id = args["patch_id"]
    patch = ctx.state.patches.get(patch_id)

    if patch is None:
        raise ToolError("Unknown patch_id. Prepare a patch with propose_edit first.")
    if ctx.state.pending_patch_id != patch_id:
        raise ToolError("This patch is not the current pending patch.")
    if patch.status != "pending":
        raise ToolError(f"Patch is not pending (status={patch.status}).")

    ctx.state.transition(Status.AWAITING_APPROVAL)
    _display(ctx, patch)

    approved = confirm("Apply this change? [y/N] ", ctx.console)

    if not approved:
        patch.status = "rejected"
        ctx.state.approval_decision = "rejected"
        ctx.state.pending_patch_id = None
        ctx.state.transition(Status.REJECTED)
        return {
            "patch_id": patch_id,
            "approved": False,
            "applied": False,
            "stop": True,
            "message": "Patch rejected. No source changes were applied.",
        }

    ctx.state.approval_decision = "approved"
    path = resolve_within_root(ctx.root, patch.relative_path)

    content = read_text_raw(path)
    if fingerprint(content) != patch.source_fingerprint:
        patch.status = "failed"
        ctx.state.pending_patch_id = None
        ctx.state.transition(Status.FAILED)
        raise ToolError(
            "The file changed after the patch was prepared (stale patch). Refusing to apply."
        )

    backup = create_backup(path, ctx.backups_root, patch.patch_id)
    updated = content.replace(patch.old_text, patch.new_text, 1)
    atomic_write_text(path, updated)

    patch.status = "applied"
    ctx.state.changed_files.append(patch.relative_path)
    ctx.state.pending_patch_id = None
    ctx.state.transition(Status.PATCH_APPLIED)

    return {
        "patch_id": patch_id,
        "approved": True,
        "applied": True,
        "path": patch.relative_path,
        "backup": str(backup),
        "message": "Patch applied. Call run_tests to verify the fix with the project's tests.",
    }
