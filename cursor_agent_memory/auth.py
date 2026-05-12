from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import httpx


@dataclass
class FeishuSettings:
    app_id: str
    app_secret: str
    redirect_uri: str

    @classmethod
    def from_env(cls) -> "FeishuSettings | None":
        app_id = os.environ.get("FEISHU_APP_ID")
        app_secret = os.environ.get("FEISHU_APP_SECRET")
        redirect_uri = os.environ.get("FEISHU_REDIRECT_URI")
        if not app_id or not app_secret or not redirect_uri:
            return None
        return cls(app_id=app_id, app_secret=app_secret, redirect_uri=redirect_uri)


class AuthService:
    def __init__(self) -> None:
        self.feishu = FeishuSettings.from_env()

    @property
    def feishu_enabled(self) -> bool:
        return self.feishu is not None

    def build_feishu_authorize_url(self, state: str) -> str:
        if self.feishu is None:
            raise RuntimeError("Feishu auth is not configured.")
        return (
            "https://accounts.feishu.cn/open-apis/authen/v1/authorize"
            f"?app_id={self.feishu.app_id}"
            f"&redirect_uri={self.feishu.redirect_uri}"
            f"&state={state}"
        )

    async def exchange_feishu_code(self, code: str) -> dict[str, Any]:
        if self.feishu is None:
            raise RuntimeError("Feishu auth is not configured.")

        # This flow is intentionally lightweight for MVP.
        # If credentials are configured, we try to fetch a basic profile.
        async with httpx.AsyncClient(timeout=10.0) as client:
            token_response = await client.post(
                "https://open.feishu.cn/open-apis/authen/v1/oauth/token",
                json={
                    "grant_type": "authorization_code",
                    "code": code,
                    "client_id": self.feishu.app_id,
                    "client_secret": self.feishu.app_secret,
                    "redirect_uri": self.feishu.redirect_uri,
                },
            )
            token_response.raise_for_status()
            token_payload = token_response.json()
            access_token = (
                token_payload.get("data", {}).get("access_token")
                or token_payload.get("access_token")
            )
            if not access_token:
                raise RuntimeError("Feishu token response did not include an access token.")

            profile_response = await client.get(
                "https://open.feishu.cn/open-apis/authen/v1/user_info",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            profile_response.raise_for_status()
            profile_payload = profile_response.json()
            data = profile_payload.get("data", {})
            return {
                "provider": "feishu",
                "external_id": data.get("open_id") or data.get("union_id") or "unknown",
                "display_name": data.get("name") or data.get("en_name") or "Feishu User",
                "email": data.get("email"),
                "department": None,
                "role": "viewer",
            }

    @staticmethod
    def demo_users() -> list[dict[str, str]]:
        return [
            {"external_id": "demo-viewer", "display_name": "Demo Viewer", "role": "viewer"},
            {"external_id": "demo-publisher", "display_name": "Demo Publisher", "role": "publisher"},
            {"external_id": "demo-admin", "display_name": "Demo Admin", "role": "admin"},
        ]

