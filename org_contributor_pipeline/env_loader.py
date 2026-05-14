"""Load key=value pairs from a ``.env`` file into ``os.environ`` (minimal, no extra deps)."""

from __future__ import annotations

import os
from pathlib import Path


def load_dotenv_file(path: Path, *, override: bool = False) -> bool:
    """Parse ``KEY=VALUE`` lines; skip blanks and ``#`` comments.

    Values may be single- or double-quoted. If ``override`` is False, existing
    ``os.environ`` keys are left unchanged.
    """
    if not path.is_file():
        return False
    raw = path.read_text(encoding="utf-8")
    for line in raw.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if "=" not in s:
            continue
        key, _, val = s.partition("=")
        key = key.strip()
        if not key:
            continue
        val = val.strip()
        if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
            val = val[1:-1]
        if not override and key in os.environ:
            continue
        os.environ[key] = val
    return True


def load_repo_dotenv(repo_root: Path | None = None) -> Path | None:
    """Load ``<repo_root>/.env`` if present.

    - Uses ``override=True`` so values in ``.env`` win over stale vars inherited
      from the parent process (e.g. a short placeholder ``GITLAB_TOKEN``).
    - If the file is a **single non-comment line without ``=``**, it is treated
      as ``GITLAB_TOKEN`` (convenience for one-line secrets files).
    """
    if repo_root is None:
        repo_root = Path(__file__).resolve().parent.parent
    env_path = repo_root / ".env"
    if not env_path.is_file():
        return None
    raw = env_path.read_text(encoding="utf-8")
    non_comment = [ln.strip() for ln in raw.splitlines() if ln.strip() and not ln.strip().startswith("#")]
    if len(non_comment) == 1 and "=" not in non_comment[0]:
        os.environ["GITLAB_TOKEN"] = non_comment[0]
        return env_path
    load_dotenv_file(env_path, override=True)
    return env_path
