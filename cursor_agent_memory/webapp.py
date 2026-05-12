from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from .auth import AuthService
from .plugins import PluginEngine
from .storage import AppStore, utc_now_iso


BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"
SESSION_SECRET = os.environ.get("CURSOR_AGENT_MEMORY_SESSION_SECRET", "cursor-agent-memory-dev-secret")

app = FastAPI(title="Cursor Agent Memory Web")
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET, same_site="lax")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

store = AppStore()
plugins = PluginEngine(store)
auth = AuthService()


def current_user(request: Request) -> dict[str, Any] | None:
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    return store.get_user(user_id)


def require_user(request: Request) -> dict[str, Any]:
    user = current_user(request)
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required.")
    return user


def role_rank(role: str) -> int:
    return {"viewer": 1, "publisher": 2, "moderator": 3, "admin": 4}.get(role, 0)


def require_role(request: Request, minimum_role: str) -> dict[str, Any]:
    user = require_user(request)
    if role_rank(user["role"]) < role_rank(minimum_role):
        raise HTTPException(status_code=403, detail="Insufficient permissions.")
    return user


def render(request: Request, template_name: str, context: dict[str, Any]) -> Any:
    context.update(
        {
            "request": request,
            "current_user": current_user(request),
            "feishu_enabled": auth.feishu_enabled,
        }
    )
    return templates.TemplateResponse(request, template_name, context)


def bundle_access_allowed(user: dict[str, Any], bundle: dict[str, Any]) -> bool:
    if user["role"] == "admin":
        return True
    sensitivity = bundle.get("sensitivity", "internal")
    if sensitivity == "restricted" and user["role"] not in {"moderator", "admin"}:
        return False
    return True


@app.get("/")
async def root(request: Request) -> Any:
    if current_user(request):
        return RedirectResponse(url="/catalog", status_code=302)
    return RedirectResponse(url="/login", status_code=302)


@app.get("/login")
async def login_page(request: Request) -> Any:
    return render(
        request,
        "login.html",
        {
            "demo_users": auth.demo_users(),
        },
    )


@app.get("/auth/demo")
async def demo_login(request: Request, role: str = "viewer") -> Any:
    allowed_roles = {"viewer", "publisher", "admin"}
    selected_role = role if role in allowed_roles else "viewer"
    demo_map = {
        item["role"]: item for item in auth.demo_users()
    }
    item = demo_map[selected_role]
    user = store.upsert_user(
        provider="demo",
        external_id=item["external_id"],
        display_name=item["display_name"],
        email=f"{item['external_id']}@example.com",
        department="Demo Org",
        role=item["role"],
    )
    request.session["user_id"] = user["id"]
    store.record_usage_event("login", user["id"], payload={"provider": "demo"})
    return RedirectResponse(url="/catalog", status_code=302)


@app.get("/auth/feishu/start")
async def feishu_start() -> Any:
    if not auth.feishu_enabled:
        return RedirectResponse(url="/login?error=feishu_not_configured", status_code=302)
    return RedirectResponse(url=auth.build_feishu_authorize_url(state="cursor-agent-memory"), status_code=302)


@app.get("/auth/feishu/callback")
async def feishu_callback(request: Request, code: str | None = None) -> Any:
    if not auth.feishu_enabled or not code:
        return RedirectResponse(url="/login?error=feishu_callback_failed", status_code=302)
    try:
        identity = await auth.exchange_feishu_code(code)
    except Exception:
        return RedirectResponse(url="/login?error=feishu_exchange_failed", status_code=302)
    user = store.upsert_user(**identity)
    request.session["user_id"] = user["id"]
    store.record_usage_event("login", user["id"], payload={"provider": "feishu"})
    return RedirectResponse(url="/catalog", status_code=302)


@app.get("/logout")
async def logout(request: Request) -> Any:
    user = current_user(request)
    if user:
        store.record_usage_event("logout", user["id"])
    request.session.clear()
    return RedirectResponse(url="/login", status_code=302)


@app.get("/catalog")
async def catalog(
    request: Request,
    q: str = "",
    project: str = "",
    problem_type: str = "",
    sensitivity: str = "",
) -> Any:
    user = require_user(request)
    bundles = [
        bundle
        for bundle in store.list_catalog(q, project, problem_type, sensitivity)
        if bundle_access_allowed(user, bundle)
    ]
    return render(
        request,
        "catalog.html",
        {
            "bundles": bundles,
            "filters": store.list_filter_values(),
            "query": {"q": q, "project": project, "problem_type": problem_type, "sensitivity": sensitivity},
            "stats": {
                "bundle_count": len(bundles),
                "project_count": len({item["project"] for item in bundles if item.get("project")}),
                "download_count": len(store.list_downloads_for_user(user["id"])),
            },
        },
    )


@app.get("/bundles/{bundle_id}")
async def bundle_detail(request: Request, bundle_id: str) -> Any:
    user = require_user(request)
    bundle = store.get_bundle(bundle_id)
    if bundle is None:
        raise HTTPException(status_code=404, detail="Bundle not found.")
    if not bundle_access_allowed(user, bundle):
        raise HTTPException(status_code=403, detail="Bundle is restricted.")
    return render(
        request,
        "detail.html",
        {
            "bundle": bundle,
        },
    )


@app.get("/upload")
async def upload_page(request: Request) -> Any:
    require_role(request, "publisher")
    return render(
        request,
        "upload.html",
        {
            "result": None,
            "errors": [],
            "form_data": {},
        },
    )


@app.post("/upload")
async def upload_bundle(
    request: Request,
    bundle_file: UploadFile = File(...),
    title: str = Form(""),
    project: str = Form(""),
    repo: str = Form(""),
    problem_type: str = Form("analysis"),
    tags: str = Form(""),
    sensitivity: str = Form("internal"),
    short_note: str = Form(""),
) -> Any:
    user = require_role(request, "publisher")
    errors: list[str] = []
    result: dict[str, Any] | None = None
    form_data = {
        "title": title,
        "project": project,
        "repo": repo,
        "problem_type": problem_type,
        "tags": tags,
        "sensitivity": sensitivity,
        "short_note": short_note,
    }

    if not bundle_file.filename:
        errors.append("Please choose a bundle file.")
        return render(request, "upload.html", {"result": result, "errors": errors, "form_data": form_data})

    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(bundle_file.filename).suffix) as handle:
            handle.write(await bundle_file.read())
            tmp_path = Path(handle.name)

        metadata = {
            "title": title or Path(bundle_file.filename).stem,
            "project": project,
            "repo": repo,
            "problem_type": problem_type,
            "tags": [part.strip() for part in tags.split(",") if part.strip()],
            "sensitivity": sensitivity,
            "short_note": short_note,
        }
        if bundle_file.filename.lower().endswith(".json"):
            extracted = store.build_metadata_from_json(tmp_path)
            for key in ("title", "project", "repo", "problem_type", "short_note"):
                if not metadata.get(key):
                    metadata[key] = extracted.get(key)
            if not metadata.get("tags"):
                metadata["tags"] = extracted.get("tags", [])
            metadata["manifest"] = extracted["manifest"]
            metadata["preview"] = extracted["preview"]
        else:
            metadata["manifest"] = {
                "message_count": None,
                "tool_count": None,
                "transcript_event_count": None,
                "workspace_count": None,
                "touched_file_count": None,
                "tools_used": [],
            }
            metadata["preview"] = {"first_user_message": None, "snippets": []}

        hook_context = {
            "actor_id": user["id"],
            "file_path": str(tmp_path),
            "file_name": bundle_file.filename,
            "metadata": metadata,
        }
        hook_results = plugins.run("before_upload", hook_context)
        for item in hook_results:
            if item.get("metadata"):
                metadata.update(item["metadata"])
            if item.get("status") == "reject":
                errors.append(item.get("message") or "Upload rejected by plugin.")

        if errors:
            result = {"plugin_results": hook_results}
            return render(request, "upload.html", {"result": result, "errors": errors, "form_data": form_data})

        bundle = store.create_bundle_from_existing_file(
            uploader_id=user["id"],
            metadata=metadata,
            file_path=tmp_path,
            visibility="internal",
        )
        latest_version = bundle["versions"][0] if bundle.get("versions") else None
        after_context = {
            "actor_id": user["id"],
            "bundle_id": bundle["id"],
            "version_id": latest_version["id"] if latest_version else None,
            "metadata": metadata,
        }
        after_results = plugins.run("after_upload", after_context)
        plugins.run("after_publish", after_context)
        result = {"bundle": bundle, "plugin_results": hook_results + after_results}
        store.record_usage_event("uploaded", user["id"], bundle_id=bundle["id"], version_id=latest_version["id"] if latest_version else None)
    finally:
        if tmp_path and tmp_path.exists():
            tmp_path.unlink(missing_ok=True)

    return render(request, "upload.html", {"result": result, "errors": errors, "form_data": form_data})


@app.post("/bundles/{bundle_id}/download")
async def create_download(request: Request, bundle_id: str, version_id: str | None = Form(None)) -> Any:
    user = require_user(request)
    bundle = store.get_bundle(bundle_id)
    if bundle is None:
        raise HTTPException(status_code=404, detail="Bundle not found.")
    if not bundle_access_allowed(user, bundle):
        raise HTTPException(status_code=403, detail="Not allowed to download this bundle.")

    selected_version = None
    for version in bundle["versions"]:
        if version_id and version["id"] == version_id:
            selected_version = version
            break
    if selected_version is None:
        selected_version = bundle["versions"][0]

    before_context = {
        "actor_id": user["id"],
        "bundle_id": bundle["id"],
        "version_id": selected_version["id"],
        "policy": bundle.get("policy"),
    }
    before_results = plugins.run("before_download", before_context)
    for result in before_results:
        if result.get("status") == "reject":
            raise HTTPException(status_code=403, detail=result.get("message") or "Download rejected.")

    token = store.create_download_grant(
        actor_id=user["id"],
        bundle_id=bundle["id"],
        version_id=selected_version["id"],
        decision_reason="allowed",
    )
    store.record_usage_event(
        "download_requested",
        user["id"],
        bundle_id=bundle["id"],
        version_id=selected_version["id"],
        payload={"plugin_results": before_results},
    )
    plugins.run("after_download", before_context)
    store.record_usage_event(
        "downloaded",
        user["id"],
        bundle_id=bundle["id"],
        version_id=selected_version["id"],
        payload={"granted_at": utc_now_iso()},
    )
    return RedirectResponse(url=f"/download-grants/{token}", status_code=302)


@app.get("/download-grants/{token}")
async def use_download_grant(request: Request, token: str) -> Any:
    require_user(request)
    grant = store.resolve_download_grant(token)
    if grant is None:
        raise HTTPException(status_code=404, detail="Download grant expired or missing.")
    return FileResponse(path=grant["storage_path"], filename=grant["filename"], media_type="application/octet-stream")


@app.get("/downloads")
async def downloads_page(request: Request) -> Any:
    user = require_user(request)
    return render(
        request,
        "downloads.html",
        {
            "downloads": store.list_downloads_for_user(user["id"]),
        },
    )


@app.get("/admin")
async def admin_page(request: Request) -> Any:
    require_role(request, "admin")
    return render(
        request,
        "admin.html",
        {
            "plugins": store.list_plugins(),
            "audit_events": store.list_recent_audit(),
            "auth_status": {
                "feishu_enabled": auth.feishu_enabled,
            },
        },
    )


@app.post("/admin/plugins/{plugin_id}/toggle")
async def toggle_plugin(request: Request, plugin_id: str) -> Any:
    require_role(request, "admin")
    store.toggle_plugin(plugin_id)
    return RedirectResponse(url="/admin", status_code=302)


def main() -> None:
    import uvicorn

    uvicorn.run("cursor_agent_memory.webapp:app", host="127.0.0.1", port=8008, reload=False)

