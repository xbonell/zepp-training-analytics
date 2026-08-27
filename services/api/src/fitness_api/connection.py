from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel


class ConnectionSecrets(BaseModel):
    user_id: str | None = None
    app_token: str | None = None


def load_connection(path: Path) -> ConnectionSecrets:
    if not path.exists():
        return ConnectionSecrets()
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip().strip('"').strip("'")
    return ConnectionSecrets(
        user_id=values.get("ZEPP_USER_ID") or None,
        app_token=values.get("ZEPP_APP_TOKEN") or None,
    )


def save_connection(
    path: Path,
    *,
    user_id: str | None,
    app_token: str | None,
    replace_token: bool,
) -> ConnectionSecrets:
    current = load_connection(path)
    token = app_token if replace_token and app_token else current.app_token
    if replace_token and app_token == "":
        token = None
    secrets = ConnectionSecrets(user_id=user_id or None, app_token=token)
    path.parent.mkdir(parents=True, exist_ok=True)
    body = (
        f"ZEPP_USER_ID={secrets.user_id or ''}\n"
        f"ZEPP_APP_TOKEN={secrets.app_token or ''}\n"
    )
    path.write_text(body, encoding="utf-8")
    path.chmod(0o600)
    return secrets


def connection_public_view(secrets: ConnectionSecrets) -> dict:
    token = secrets.app_token
    token_set = bool(token)
    hint = token[-4:] if token and len(token) >= 4 else (token if token else None)
    return {
        "user_id": secrets.user_id,
        "token_set": token_set,
        "token_hint": hint if token_set else None,
    }
