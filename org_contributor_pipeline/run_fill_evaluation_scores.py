"""Run Cursor ``agent`` CLI to fill ``evaluation_run_scores_patch.v1``, then merge into base JSON.

Uses subprocess UTF-8 capture to avoid PowerShell ``Set-Content`` mojibake on agent stdout.

``--stub`` skips the agent and merges **placeholder** scores only (no LLM); real judgment still
requires ``cursor agent`` or a human-supplied patch merged via ``merge_evaluation_scores``.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from org_contributor_pipeline.merge_evaluation_scores import (
    build_stub_scores_patch,
    extract_json_object,
    merge_patch,
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _resolve_agent() -> str:
    explicit = os.environ.get("ORG_CONTRIBUTOR_AGENT", "")
    if explicit and Path(explicit).is_file():
        return str(Path(explicit).resolve())
    from shutil import which

    w = which("agent")
    if w:
        return w
    home = Path.home()
    for c in (
        home / ".local" / "bin" / "agent.exe",
        home / ".local" / "bin" / "agent.cmd",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "cursor" / "resources" / "app" / "bin" / "agent.exe",
    ):
        if c.is_file():
            return str(c)
    raise FileNotFoundError(
        "Cursor CLI 'agent' not found. Install Cursor CLI or set ORG_CONTRIBUTOR_AGENT to agent.exe path."
    )


def _build_prompt(
    workspace: Path,
    evaluation_run_path: Path,
    *,
    embedded_evaluation_json: str | None,
) -> str:
    prompt_path = workspace / "org_contributor_pipeline" / "prompts" / "04_fill_evaluation_run_scores.md"
    body = prompt_path.read_text(encoding="utf-8")
    ep = str(evaluation_run_path.resolve())
    embed_block = ""
    if embedded_evaluation_json is not None:
        embed_block = f"""
## evaluation_run.v1 JSON (embedded — use as the source of truth; do not invent people or rows)
The document below is the full `evaluation_run.v1`. You do not need to open the file on disk unless you prefer.

```json
{embedded_evaluation_json}
```
"""
    header = f"""You are executing org_contributor_pipeline step 4 (fill scores into evaluation_run.v1).
Follow the repository root AGENTS.md and org_contributor_pipeline/AGENTS.md.
Your entire reply MUST be exactly one JSON object matching schema evaluation_run_scores_patch.v1 (no markdown, no commentary).

## evaluation_run.v1 file path (optional; same content may be embedded below)
{ep}
{embed_block}
Output ONLY the JSON patch object as specified in the prompt below.
"""
    return f"{header}\n\n---\n\n{body}"


def _decode_agent_output(raw: bytes) -> str:
    """Agent on Windows may emit UTF-8 or system code page (e.g. GBK)."""
    for enc in ("utf-8-sig", "utf-8", "gbk", "cp936"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def _materialize_cli_prompt(full_prompt: str, eval_path: Path, *, max_cli_bytes: int = 6000) -> tuple[str, Path | None]:
    """Windows ``CreateProcess`` has a short argv limit; spill large prompts to a UTF-8 sidecar file."""
    raw = full_prompt.encode("utf-8")
    if len(raw) <= max_cli_bytes:
        return full_prompt, None
    spool = eval_path.parent / f"{eval_path.stem}.fill-scores.prompt.txt"
    spool.write_text(full_prompt, encoding="utf-8")
    sp = str(spool.resolve())
    # Keep the file path on the SAME line as the label — some Windows/agent argv paths drop text after embedded newlines.
    sp_posix = spool.resolve().as_posix()
    short = (
        "Step 4: fill every mandatory_l2_scores cell for evaluation_run.v1. "
        f"Read the ENTIRE UTF-8 instruction file now (path): {sp_posix} "
        "That file contains prompts/04_fill_evaluation_run_scores.md body plus the evaluation_run JSON. "
        "Reply with exactly ONE JSON object, schema evaluation_run_scores_patch.v1 only — no markdown fences, no commentary."
    )
    return short, spool


def _run_agent_redirect_stdout_to_file(
    cmd: list[str],
    log_path: Path,
    timeout: int | None,
) -> tuple[int, str]:
    """Run agent with stdout+stderr merged and written directly to ``log_path`` (avoids Windows pipe issues)."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    wait_timeout = None if timeout in (None, 0) else float(timeout)
    with log_path.open("wb") as outf:
        try:
            r = subprocess.run(
                cmd,
                stdin=subprocess.DEVNULL,
                stdout=outf,
                stderr=subprocess.STDOUT,
                timeout=wait_timeout,
            )
        except subprocess.TimeoutExpired:
            raise
    raw = log_path.read_bytes() if log_path.exists() else b""
    text = _decode_agent_output(raw)
    log_path.write_text(text, encoding="utf-8", newline="\n")
    rc = int(r.returncode if r.returncode is not None else 1)
    return rc, text


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("-e", "--evaluation-run", type=Path, required=True, help="Base evaluation_run.v1 JSON")
    p.add_argument("-w", "--workspace", type=Path, default=None, help="Repo root (default: parent of org_contributor_pipeline)")
    p.add_argument("-l", "--log", type=Path, default=None, help="Agent stdout log (default: <evaluation-run>.fill-scores.log)")
    p.add_argument("-o", "--output", type=Path, default=None, help="Merged scored JSON (default: <stem>-scored.json)")
    p.add_argument(
        "--timeout-seconds",
        type=int,
        default=3600,
        help="Kill agent after N seconds (0 = no limit). Default 3600.",
    )
    p.add_argument(
        "--stub",
        action="store_true",
        help="Skip agent; merge a pipeline_stub placeholder patch (same output shape as LLM merge).",
    )
    p.add_argument(
        "--embed-evaluation-json",
        action="store_true",
        help="Put the full evaluation_run JSON inside the prompt (fewer agent tool round-trips; cap see --max-embed-bytes).",
    )
    p.add_argument(
        "--max-embed-bytes",
        type=int,
        default=600_000,
        help="Refuse --embed-evaluation-json if the file is larger than this (default 600000).",
    )
    p.add_argument(
        "--max-cli-prompt-bytes",
        type=int,
        default=6000,
        help="If the final prompt exceeds this size (UTF-8 bytes), write it to .fill-scores.prompt.txt and pass a short argv (Windows safe).",
    )
    args = p.parse_args()

    workspace = args.workspace or _repo_root()
    eval_path = args.evaluation_run.resolve()
    if args.stub:
        log_path = args.log or (eval_path.parent / f"{eval_path.stem}.stub-scores.patch.json")
    else:
        log_path = args.log or Path(str(eval_path) + ".fill-scores.log")
    out_path = args.output or (eval_path.parent / f"{eval_path.stem}-scored.json")

    raw_eval = eval_path.read_text(encoding="utf-8")
    base: dict[str, Any] = json.loads(raw_eval)

    if args.stub:
        patch = build_stub_scores_patch(base)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(json.dumps(patch, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        merged = merge_patch(base, patch)
        out_path.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Stub patch: {log_path}")
        print(f"Wrote {out_path}")
        return 0

    embed: str | None = None
    if args.embed_evaluation_json:
        if len(raw_eval.encode("utf-8")) > args.max_embed_bytes:
            print(
                f"evaluation run file exceeds --max-embed-bytes ({args.max_embed_bytes}); "
                "omit --embed-evaluation-json or raise the cap.",
                file=sys.stderr,
            )
            return 3
        embed = raw_eval

    agent = _resolve_agent()
    full_prompt = _build_prompt(workspace, eval_path, embedded_evaluation_json=embed)
    argv_prompt, spool_path = _materialize_cli_prompt(full_prompt, eval_path, max_cli_bytes=args.max_cli_prompt_bytes)
    if spool_path is not None:
        print("Prompt spooled (Windows argv limit):", spool_path, flush=True)

    cmd = [
        agent,
        "-p",
        "--workspace",
        str(workspace.resolve()),
        "--trust",
        "--output-format",
        "text",
        argv_prompt,
    ]
    print("Running:", agent, "(agent stdout+stderr ->", str(log_path), ")...", flush=True)
    try:
        tee_timeout: int | None = None if args.timeout_seconds == 0 else args.timeout_seconds
        rc, log_text = _run_agent_redirect_stdout_to_file(cmd, log_path, tee_timeout)
    except subprocess.TimeoutExpired:
        extra = f"\n\n[timeout after {args.timeout_seconds}s]\n"
        try:
            cur = log_path.read_text(encoding="utf-8")
            log_path.write_text(cur + extra, encoding="utf-8")
        except OSError:
            pass
        print(f"TIMEOUT after {args.timeout_seconds}s; partial log: {log_path}", file=sys.stderr)
        return 124

    if rc != 0:
        print(f"agent exit {rc}; log: {log_path}", file=sys.stderr)

    try:
        patch = extract_json_object(log_text)
    except ValueError as err:
        print(f"Could not parse patch JSON ({err}); see {log_path}", file=sys.stderr)
        return 2
    merged = merge_patch(base, patch)
    out_path.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Log: {log_path}")
    print(f"Wrote {out_path}")
    return 0 if rc == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
