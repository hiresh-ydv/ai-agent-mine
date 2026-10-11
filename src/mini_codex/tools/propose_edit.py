"""Tool 4: prepare a minimal patch without modifying the source file."""

from __future__ import annotations

import uuid
from typing import Any

from ..context import ToolContext
from ..errors import PatchError
from ..safety.patch_validation import (
    build_unified_diff,
    detect_newline,
    fingerprint,
    find_unique_match,
    normalize_newlines,
    read_text_raw,
)
from ..safety.paths import relative_to_root, resolve_within_root
from ..state import Patch, Status
from ._files import check_readable

MAX_PATCH_BYTES = 100_000


def run(args: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    path = resolve_within_root(ctx.root, args["path"])
    check_readable(path, ctx.config)

    content = read_text_raw(path)
    newline = detect_newline(content)

    old_text = normalize_newlines(args["old_text"])
    new_text = normalize_newlines(args["new_text"])
    if newline != "\n":
        old_text = old_text.replace("\n", newline)
        new_text = new_text.replace("\n", newline)

    if old_text == new_text:
        raise PatchError("The proposed new_text is identical to old_text; nothing to change.")
    if len(old_text) > MAX_PATCH_BYTES or len(new_text) > MAX_PATCH_BYTES:
        raise PatchError("The proposed patch exceeds the maximum allowed size.")

    find_unique_match(content, old_text)

    relative = relative_to_root(path, ctx.root)
    diff = build_unified_diff(relative, old_text, new_text)

    patch_id = uuid.uuid4().hex[:12]
    patch = Patch(
        patch_id=patch_id,
        task_id=ctx.state.task_id,
        relative_path=relative,
        old_text=old_text,
        new_text=new_text,
        reason=args["reason"],
        unified_diff=diff,
        source_fingerprint=fingerprint(content),
    )
    ctx.state.patches[patch_id] = patch
    ctx.state.pending_patch_id = patch_id
    ctx.state.transition(Status.PATCH_PROPOSED)

    return {
        "patch_id": patch_id,
        "path": relative,
        "reason": patch.reason,
        "unified_diff": diff,
        "status": "pending",
        "message": (
            "Patch prepared but NOT applied. Call request_approval_and_apply with this "
            "patch_id to show it to the user and apply it if approved."
        ),
    }
