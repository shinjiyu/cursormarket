# Security Policy

## Product posture

`cursor-agent-memory` is **local-first**:

- The exporter and MCP server do **not** make outbound network calls.
- They only **read** files Cursor already writes on disk (`state.vscdb`, workspace storage, `agent-transcripts`).
- The export directory holds conversation text and code snippets in plain JSON. Treat it like shell history: keep it off public remotes and shared drives you do not trust.

Optional `cursor-agent-memory-web` is a separate local FastAPI app for curated team bundles. It is **not** required for Marketplace MCP install.

## Reporting a vulnerability

Email **security-reports** related to this project to the maintainer via GitHub Issues (private security advisory preferred) or the contact on the GitHub profile for [shinjiyu/cursormarket](https://github.com/shinjiyu/cursormarket).

Please include:

- Affected component (`exporter`, `mcp`, `sync`, or `web`)
- Reproduction steps
- Impact (e.g. unexpected network use, path traversal, secrets in logs)

We aim to acknowledge reports within a few business days.
