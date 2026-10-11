"""Convenience launcher so the agent runs without installing the package.

Prefer ``uv run mini-codex ...`` (or ``python -m mini_codex`` after an editable
install). This thin wrapper just puts ``src`` on the path for quick local runs.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from mini_codex.main import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
