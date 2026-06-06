import hashlib
import hmac
import json
import os
import re
import secrets
import smtplib
import string
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from pathlib import Path
from typing import Any, Optional

import streamlit as st

from Utilities.PathConfiguration import PathConfiguration


AUTH_STATE_KEY = "avisk_authenticated"
AUTH_USER_KEY = "avisk_authenticated_user"
AUTH_ERROR_KEY = "avisk_auth_error"
AUTH_ROLES_KEY = "avisk_authenticated_roles"
AUTH_FORCE_PASSWORD_CHANGE_KEY = "avisk_force_password_change"
DEFAULT_INVITE_EXPIRY_HOURS = 72


_path_config = PathConfiguration()


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _isoformat(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _auth_storage_dir() -> Path:
    configured_dir = os.getenv("AVISK_AUTH_DATA_DIR", "").strip()
    if configured_dir:
        base_dir = Path(configured_dir)
    elif os.path.exists("/Users/mohanganadal"):
        base_dir = Path(_path_config.base_config.get(
            "project_root", ".")) / ".auth"
    else:
        base_dir = Path("/opt/avisk/local-data/auth")

    base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir


def _managed_users_path() -> Path:
    return _auth_storage_dir() / "managed_users.json"


def _managed_invites_path() -> Path:
    return _auth_storage_dir() / "invites.json"


def _load_json_file(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _save_json_file(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2,
                    sort_keys=True), encoding="utf-8")


def _secret_value(key: str, nested_key: Optional[str] = None) -> Optional[str]:
    try:
        if nested_key:
            auth_config = st.secrets.get(key, {})
            if isinstance(auth_config, dict):
                value = auth_config.get(nested_key)
                return str(value) if value else None
            return None
        value = st.secrets.get(key)
        return str(value) if value else None
    except Exception:
        return None


def _secret_manager_text(secret_name: str) -> Optional[str]:
    normalized_secret_name = str(secret_name).strip()
    if not normalized_secret_name:
        return None

    try:
        from google.cloud import secretmanager
        client = secretmanager.SecretManagerServiceClient()
        project_id = os.getenv(
            "GOOGLE_CLOUD_PROJECT", "avisk-ai-platform").strip() or "avisk-ai-platform"
        name = f"projects/{project_id}/secrets/{normalized_secret_name}/versions/latest"
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("utf-8").strip() or None
    except Exception:
        return None


def _smtp_config_value(
    env_key: str,
    nested_key: str,
    secret_name_env_key: Optional[str] = None,
    default: str = "",
) -> str:
    direct_value = os.getenv(env_key, "").strip()
    if direct_value:
        return direct_value

    nested_secret_value = _secret_value("smtp", nested_key)
    if nested_secret_value:
        return nested_secret_value.strip()

    flat_secret_value = _secret_value(env_key)
    if flat_secret_value:
        return flat_secret_value.strip()

    if secret_name_env_key:
        secret_name = os.getenv(secret_name_env_key, "").strip()
        if secret_name:
            secret_text = _secret_manager_text(secret_name)
            if secret_text:
                return secret_text.strip()

    return default


def _normalize_roles(raw_roles: Any, default_roles: Optional[list[str]] = None) -> list[str]:
    if raw_roles is None:
        return list(default_roles or [])

    if isinstance(raw_roles, str):
        roles = [role.strip().lower()
                 for role in raw_roles.split(",") if role.strip()]
        return roles or list(default_roles or [])

    if isinstance(raw_roles, (list, tuple, set)):
        roles = [str(role).strip().lower()
                 for role in raw_roles if str(role).strip()]
        return roles or list(default_roles or [])

    return list(default_roles or [])


def _normalize_email_address(email: Optional[str], required: bool = False) -> Optional[str]:
    normalized_email = str(email or "").strip().lower()
    if not normalized_email:
        if required:
            raise ValueError("Email is required.")
        return None

    if not re.fullmatch(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", normalized_email):
        raise ValueError("Enter a valid email address.")

    return normalized_email


def generate_temporary_password(length: int = 14) -> str:
    if length < 12:
        length = 12

    alphabet = string.ascii_letters + string.digits
    special_chars = "!@#$%^&*"
    password_chars = [
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.digits),
        secrets.choice(special_chars),
    ]

    for _ in range(length - len(password_chars)):
        password_chars.append(secrets.choice(alphabet + special_chars))

    secrets.SystemRandom().shuffle(password_chars)
    return "".join(password_chars)


def _normalize_user_record(record: dict[str, Any], default_roles: Optional[list[str]] = None) -> Optional[dict[str, Any]]:
    username = str(record.get("username", "")).strip()
    if not username:
        return None

    password = record.get("password")
    password_hash = record.get("password_sha256")
    if password is None and password_hash is None:
        return None

    normalized = {
        "username": username,
        "password": str(password) if password is not None else None,
        "password_sha256": str(password_hash) if password_hash is not None else None,
        "roles": _normalize_roles(record.get("roles"), default_roles or ["user"]),
        "email": str(record.get("email", "")).strip() or None,
        "is_active": bool(record.get("is_active", True)),
        "source": str(record.get("source", "managed") or "managed"),
        "created_at": str(record.get("created_at", "") or "") or None,
        "registered_at": str(record.get("registered_at", "") or "") or None,
        "must_change_password": bool(record.get("must_change_password", False)),
        "last_password_change_at": str(record.get("last_password_change_at", "") or "") or None,
    }
    return normalized


def _load_managed_users() -> list[dict[str, Any]]:
    raw_users = _load_json_file(_managed_users_path(), [])
    users: list[dict[str, Any]] = []
    if not isinstance(raw_users, list):
        return users

    for raw_user in raw_users:
        if not isinstance(raw_user, dict):
            continue
        normalized = _normalize_user_record({**raw_user, "source": "managed"})
        if normalized:
            users.append(normalized)
    return users


def _save_managed_users(users: list[dict[str, Any]]) -> None:
    _save_json_file(_managed_users_path(), users)


def _normalize_invite_record(record: dict[str, Any]) -> Optional[dict[str, Any]]:
    invite_id = str(record.get("invite_id", "")).strip()
    token = str(record.get("token", "")).strip()
    email = str(record.get("email", "")).strip().lower()
    if not invite_id or not token or not email:
        return None

    return {
        "invite_id": invite_id,
        "token": token,
        "email": email,
        "invite_type": str(record.get("invite_type", "registration") or "registration").strip().lower(),
        "target_username": str(record.get("target_username", "") or "") or None,
        "roles": _normalize_roles(record.get("roles"), ["user"]),
        "status": str(record.get("status", "pending") or "pending").strip().lower(),
        "invited_by": str(record.get("invited_by", "") or "") or None,
        "created_at": str(record.get("created_at", "") or "") or None,
        "expires_at": str(record.get("expires_at", "") or "") or None,
        "accepted_at": str(record.get("accepted_at", "") or "") or None,
        "sent_at": str(record.get("sent_at", "") or "") or None,
        "registered_username": str(record.get("registered_username", "") or "") or None,
        "last_email_error": str(record.get("last_email_error", "") or "") or None,
    }


def _load_invites() -> list[dict[str, Any]]:
    raw_invites = _load_json_file(_managed_invites_path(), [])
    invites: list[dict[str, Any]] = []
    if not isinstance(raw_invites, list):
        return invites

    for raw_invite in raw_invites:
        if not isinstance(raw_invite, dict):
            continue
        normalized = _normalize_invite_record(raw_invite)
        if normalized:
            invites.append(normalized)
    return invites


def _save_invites(invites: list[dict[str, Any]]) -> None:
    _save_json_file(_managed_invites_path(), invites)


def _invite_is_expired(invite: dict[str, Any]) -> bool:
    expires_at = _parse_datetime(invite.get("expires_at"))
    if not expires_at:
        return False
    return expires_at < _utc_now()


def _auth_users_from_secrets() -> list[dict[str, Any]]:
    try:
        auth_config = st.secrets.get("auth", {})
    except Exception:
        return []

    if not isinstance(auth_config, dict):
        return []

    users = auth_config.get("users")
    normalized_users: list[dict[str, Any]] = []

    if isinstance(users, list):
        for record in users:
            if isinstance(record, dict):
                normalized = _normalize_user_record(record)
                if normalized:
                    normalized_users.append(normalized)
    elif isinstance(users, dict):
        for username, value in users.items():
            if isinstance(value, dict):
                record = {"username": username, **value}
                normalized = _normalize_user_record(record)
                if normalized:
                    normalized_users.append(normalized)

    return normalized_users


def _auth_users_from_env() -> list[dict[str, Any]]:
    raw_users = os.getenv("AVISK_APP_USERS_JSON", "").strip()
    if not raw_users:
        return []

    try:
        parsed = json.loads(raw_users)
    except json.JSONDecodeError:
        return []

    normalized_users: list[dict[str, Any]] = []
    if isinstance(parsed, list):
        for record in parsed:
            if isinstance(record, dict):
                normalized = _normalize_user_record(record)
                if normalized:
                    normalized["source"] = "env"
                    normalized_users.append(normalized)
    elif isinstance(parsed, dict):
        for username, value in parsed.items():
            if isinstance(value, dict):
                record = {"username": username, **value}
                normalized = _normalize_user_record(record)
                if normalized:
                    normalized["source"] = "env"
                    normalized_users.append(normalized)

    return normalized_users


def _auth_users_from_secret_manager() -> list[dict[str, Any]]:
    secret_name = os.getenv("AVISK_APP_USERS_JSON_SECRET", "").strip()
    if not secret_name:
        return []

    raw_users = _secret_manager_text(secret_name)
    if not raw_users:
        return []

    try:
        parsed = json.loads(raw_users)
    except json.JSONDecodeError:
        return []

    normalized_users: list[dict[str, Any]] = []
    if isinstance(parsed, list):
        for record in parsed:
            if isinstance(record, dict):
                normalized = _normalize_user_record(record)
                if normalized:
                    normalized["source"] = "secret_manager"
                    normalized_users.append(normalized)
    elif isinstance(parsed, dict):
        for username, value in parsed.items():
            if isinstance(value, dict):
                record = {"username": username, **value}
                normalized = _normalize_user_record(record)
                if normalized:
                    normalized["source"] = "secret_manager"
                    normalized_users.append(normalized)

    return normalized_users


def _legacy_user_record() -> Optional[dict[str, Any]]:
    username = os.getenv("AVISK_APP_USERNAME") or _secret_value(
        "AVISK_APP_USERNAME") or _secret_value("auth", "username")
    password = os.getenv("AVISK_APP_PASSWORD") or _secret_value(
        "AVISK_APP_PASSWORD") or _secret_value("auth", "password")
    password_hash = (
        os.getenv("AVISK_APP_PASSWORD_SHA256")
        or _secret_value("AVISK_APP_PASSWORD_SHA256")
        or _secret_value("auth", "password_sha256")
    )

    if not username or (not password and not password_hash):
        return None

    return _normalize_user_record(
        {
            "username": username,
            "password": password,
            "password_sha256": password_hash,
            "roles": ["admin"],
            "source": "legacy",
            "must_change_password": True,
        },
        default_roles=["admin"],
    )


def _configured_users() -> list[dict[str, Any]]:
    users_by_username: dict[str, dict[str, Any]] = {}

    for user_record in _auth_users_from_env():
        users_by_username[user_record["username"].lower()] = user_record

    for user_record in _auth_users_from_secret_manager():
        users_by_username[user_record["username"].lower()] = user_record

    for user_record in _auth_users_from_secrets():
        user_record["source"] = "secrets"
        users_by_username[user_record["username"].lower()] = user_record

    for user_record in _load_managed_users():
        users_by_username[user_record["username"].lower()] = user_record

    legacy_user = _legacy_user_record()
    if legacy_user:
        users_by_username[legacy_user["username"].lower()] = legacy_user

    return list(users_by_username.values())


def _credentials_configured() -> bool:
    return bool(_configured_users())


def _password_matches(provided_password: str, user_record: dict[str, Any]) -> bool:
    configured_hash = user_record.get("password_sha256")
    if configured_hash:
        candidate_hash = hashlib.sha256(
            provided_password.encode("utf-8")).hexdigest()
        return hmac.compare_digest(candidate_hash, configured_hash)

    configured_password = str(user_record.get("password") or "")
    return hmac.compare_digest(provided_password, configured_password)


def _authenticate_user(username: str, password: str) -> Optional[dict[str, Any]]:
    candidate_username = username.strip()
    for user_record in _configured_users():
        configured_username = str(user_record.get("username", ""))
        if not hmac.compare_digest(candidate_username, configured_username):
            continue
        if not bool(user_record.get("is_active", True)):
            continue
        if _password_matches(password, user_record):
            return user_record
    return None


def _get_user_record(username: str) -> Optional[dict[str, Any]]:
    candidate_username = username.strip().lower()
    for user_record in _configured_users():
        if user_record["username"].strip().lower() == candidate_username:
            return user_record
    return None


def _current_roles() -> list[str]:
    return _normalize_roles(st.session_state.get(AUTH_ROLES_KEY), [])


def _has_required_role(required_roles: Optional[list[str]]) -> bool:
    if not required_roles:
        return True
    current_roles = set(_current_roles())
    return any(role in current_roles for role in required_roles)


def _hide_sidebar_navigation() -> None:
    st.markdown(
        """
        <style>
        [data-testid="stSidebar"] {
            display: none;
        }
        [data-testid="stSidebarNav"] {
            display: none;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _clear_auth_state() -> None:
    st.session_state[AUTH_STATE_KEY] = False
    st.session_state.pop(AUTH_USER_KEY, None)
    st.session_state.pop(AUTH_ROLES_KEY, None)
    st.session_state.pop(AUTH_ERROR_KEY, None)
    st.session_state.pop(AUTH_FORCE_PASSWORD_CHANGE_KEY, None)


def _render_access_denied(required_roles: list[str]) -> None:
    st.error(
        "You do not have permission to access this page. "
        f"Required role: {', '.join(required_roles)}."
    )
    with st.sidebar:
        st.caption(
            f"Signed in as {st.session_state.get(AUTH_USER_KEY, 'user')}")
        st.caption(f"Roles: {', '.join(_current_roles()) or 'none'}")
        if st.button("Log out", use_container_width=True):
            _clear_auth_state()
            st.rerun()


def _render_login_form() -> None:
    _hide_sidebar_navigation()
    st.title("Avisk Login")
    st.caption("Sign in to access Avisk Core Services.")

    if not _credentials_configured():
        st.error(
            "Login is enabled but credentials are not configured. Set auth users in "
            "AVISK_APP_USERS_JSON, the legacy AVISK_APP_USERNAME/AVISK_APP_PASSWORD pair, "
            "or Streamlit secrets."
        )
        return

    if st.session_state.get(AUTH_ERROR_KEY):
        st.error(st.session_state[AUTH_ERROR_KEY])

    with st.form("avisk_login_form", clear_on_submit=False):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign in", use_container_width=True)

    if not submitted:
        return

    authenticated_user = _authenticate_user(username, password)
    if authenticated_user:
        st.session_state[AUTH_STATE_KEY] = True
        st.session_state[AUTH_USER_KEY] = authenticated_user["username"]
        st.session_state[AUTH_ROLES_KEY] = authenticated_user.get("roles", [])
        st.session_state[AUTH_FORCE_PASSWORD_CHANGE_KEY] = bool(
            authenticated_user.get("must_change_password", False))
        st.session_state.pop(AUTH_ERROR_KEY, None)
        st.rerun()

    st.session_state[AUTH_STATE_KEY] = False
    st.session_state[AUTH_ERROR_KEY] = "Invalid username or password."
    st.rerun()


def _base_app_url() -> Optional[str]:
    configured = os.getenv("AVISK_APP_BASE_URL", "").strip().rstrip("/")
    if configured:
        return configured

    fallback_url = os.getenv("AVISK_PUBLIC_APP_URL", "").strip().rstrip("/")
    if fallback_url:
        return fallback_url

    # Current VM-hosted default. Explicit env vars still take precedence.
    return "http://35.184.56.147:8501"


def build_invite_link(token: str) -> str:
    base_url = _base_app_url() or ""
    if base_url:
        return f"{base_url}/?invite_token={token}"
    return f"/?invite_token={token}"


def get_user_directory() -> list[dict[str, Any]]:
    return sorted(_configured_users(), key=lambda row: row["username"].lower())


def get_managed_users() -> list[dict[str, Any]]:
    return sorted(_load_managed_users(), key=lambda row: row["username"].lower())


def get_invites() -> list[dict[str, Any]]:
    invites = _load_invites()
    normalized: list[dict[str, Any]] = []
    changed = False
    for invite in invites:
        if invite.get("status") == "pending" and _invite_is_expired(invite):
            invite = {**invite, "status": "expired"}
            changed = True
        normalized.append(invite)
    if changed:
        _save_invites(normalized)
    return sorted(normalized, key=lambda row: row.get("created_at") or "", reverse=True)


def _smtp_settings() -> dict[str, Any]:
    port_value = _smtp_config_value(
        "AVISK_SMTP_PORT",
        "port",
        secret_name_env_key="AVISK_SMTP_PORT_SECRET",
        default="587",
    )

    return {
        "host": _smtp_config_value(
            "AVISK_SMTP_HOST",
            "host",
            secret_name_env_key="AVISK_SMTP_HOST_SECRET",
        ),
        "port": int(port_value or "587"),
        "username": _smtp_config_value(
            "AVISK_SMTP_USERNAME",
            "username",
            secret_name_env_key="AVISK_SMTP_USERNAME_SECRET",
        ),
        "password": _smtp_config_value(
            "AVISK_SMTP_PASSWORD",
            "password",
            secret_name_env_key="AVISK_SMTP_PASSWORD_SECRET",
        ),
        "from_email": _smtp_config_value(
            "AVISK_SMTP_FROM_EMAIL",
            "from_email",
            secret_name_env_key="AVISK_SMTP_FROM_EMAIL_SECRET",
        ),
        "from_name": _smtp_config_value(
            "AVISK_SMTP_FROM_NAME",
            "from_name",
            secret_name_env_key="AVISK_SMTP_FROM_NAME_SECRET",
            default="Avisk Core Services",
        ) or "Avisk Core Services",
        "use_tls": _smtp_config_value(
            "AVISK_SMTP_USE_TLS",
            "use_tls",
            secret_name_env_key="AVISK_SMTP_USE_TLS_SECRET",
            default="true",
        ).lower() != "false",
    }


def email_delivery_configured() -> bool:
    settings = _smtp_settings()
    return all([settings["host"], settings["from_email"]])


def create_invite(email: str, roles: list[str] | str, invited_by: str, expires_in_hours: int = DEFAULT_INVITE_EXPIRY_HOURS) -> dict[str, Any]:
    normalized_email = _normalize_email_address(email, required=True)

    normalized_roles = _normalize_roles(roles, ["user"])
    if not normalized_roles:
        raise ValueError("At least one role is required.")

    invites = get_invites()
    for invite in invites:
        if invite["email"] == normalized_email and invite.get("status") == "pending" and not _invite_is_expired(invite):
            raise ValueError(
                "A pending invite already exists for this email address.")

    invite = {
        "invite_id": secrets.token_hex(8),
        "token": secrets.token_urlsafe(24),
        "email": normalized_email,
        "invite_type": "registration",
        "target_username": None,
        "roles": normalized_roles,
        "status": "pending",
        "invited_by": invited_by,
        "created_at": _isoformat(_utc_now()),
        "expires_at": _isoformat(_utc_now() + timedelta(hours=max(1, int(expires_in_hours)))),
        "accepted_at": None,
        "sent_at": None,
        "registered_username": None,
        "last_email_error": None,
    }
    invites.append(invite)
    _save_invites(invites)
    return invite


def create_password_setup_invite(
    username: str,
    invited_by: str,
    expires_in_hours: int = DEFAULT_INVITE_EXPIRY_HOURS,
) -> dict[str, Any]:
    user_record = _get_user_record(username)
    if not user_record:
        raise ValueError("User not found.")

    email = user_record.get("email")
    if not email:
        raise ValueError(
            "User must have an email address to generate a password setup link.")

    invites = get_invites()
    for invite in invites:
        if (
            invite.get("invite_type") == "password_setup"
            and (invite.get("target_username") or "").lower() == username.strip().lower()
            and invite.get("status") == "pending"
        ):
            invite["status"] = "revoked"

    invite = {
        "invite_id": secrets.token_hex(8),
        "token": secrets.token_urlsafe(24),
        "email": email,
        "invite_type": "password_setup",
        "target_username": user_record["username"],
        "roles": user_record.get("roles", ["user"]),
        "status": "pending",
        "invited_by": invited_by,
        "created_at": _isoformat(_utc_now()),
        "expires_at": _isoformat(_utc_now() + timedelta(hours=max(1, int(expires_in_hours)))),
        "accepted_at": None,
        "sent_at": None,
        "registered_username": user_record["username"],
        "last_email_error": None,
    }
    invites.append(invite)
    _save_invites(invites)
    return invite


def get_password_setup_invite(username: str) -> Optional[dict[str, Any]]:
    normalized_username = username.strip().lower()
    for invite in get_invites():
        if (
            invite.get("invite_type") == "password_setup"
            and (invite.get("target_username") or "").lower() == normalized_username
            and invite.get("status") == "pending"
            and not _invite_is_expired(invite)
        ):
            return invite
    return None


def revoke_invite(invite_id: str) -> None:
    invites = get_invites()
    updated = False
    for invite in invites:
        if invite["invite_id"] == invite_id and invite.get("status") == "pending":
            invite["status"] = "revoked"
            updated = True
    if updated:
        _save_invites(invites)


def update_managed_user(username: str, roles: list[str] | str, is_active: bool) -> None:
    update_managed_user_settings(username, roles, is_active)


def update_managed_user_settings(
    username: str,
    roles: list[str] | str,
    is_active: bool,
    must_change_password: Optional[bool] = None,
) -> None:
    managed_users = _load_managed_users()
    normalized_roles = _normalize_roles(roles, ["user"])
    updated = False
    for user in managed_users:
        if user["username"].lower() == username.strip().lower():
            user["roles"] = normalized_roles
            user["is_active"] = bool(is_active)
            if must_change_password is not None:
                user["must_change_password"] = bool(must_change_password)
            updated = True
            break
    if not updated:
        raise ValueError("Managed user not found.")
    _save_managed_users(managed_users)


def delete_managed_user(username: str) -> None:
    managed_users = _load_managed_users()
    filtered_users = [user for user in managed_users if user["username"].lower(
    ) != username.strip().lower()]
    if len(filtered_users) == len(managed_users):
        raise ValueError("Managed user not found.")
    _save_managed_users(filtered_users)


def _find_invite_by_token(token: str) -> Optional[dict[str, Any]]:
    for invite in get_invites():
        if hmac.compare_digest(invite.get("token", ""), token):
            return invite
    return None


def register_invited_user(token: str, username: str, password: str) -> dict[str, Any]:
    invite = _find_invite_by_token(token)
    if not invite:
        raise ValueError("Invite not found.")
    if invite.get("status") != "pending":
        raise ValueError("Invite is no longer active.")
    if _invite_is_expired(invite):
        revoke_invite(invite["invite_id"])
        raise ValueError("Invite has expired.")

    normalized_username = username.strip()
    if not normalized_username:
        raise ValueError("Username is required.")
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long.")

    existing_users = get_user_directory()
    if any(user["username"].lower() == normalized_username.lower() for user in existing_users):
        raise ValueError("Username already exists.")

    managed_users = _load_managed_users()
    user_record = {
        "username": normalized_username,
        "password": None,
        "password_sha256": hashlib.sha256(password.encode("utf-8")).hexdigest(),
        "roles": invite.get("roles", ["user"]),
        "email": invite.get("email"),
        "is_active": True,
        "source": "managed",
        "created_at": invite.get("created_at") or _isoformat(_utc_now()),
        "registered_at": _isoformat(_utc_now()),
        "must_change_password": False,
        "last_password_change_at": _isoformat(_utc_now()),
    }
    managed_users.append(user_record)
    _save_managed_users(managed_users)

    invites = get_invites()
    for existing_invite in invites:
        if existing_invite["invite_id"] == invite["invite_id"]:
            existing_invite["status"] = "accepted"
            existing_invite["accepted_at"] = _isoformat(_utc_now())
            existing_invite["registered_username"] = normalized_username
    _save_invites(invites)
    return user_record


def create_managed_user(
    username: str,
    email: Optional[str],
    roles: list[str] | str,
    password: Optional[str] = None,
    is_active: bool = True,
    must_change_password: bool = False,
) -> dict[str, Any]:
    normalized_username = username.strip()
    normalized_email = _normalize_email_address(email, required=False)
    if not normalized_username:
        raise ValueError("Username is required.")
    if password is None:
        password = generate_temporary_password()
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long.")

    existing_users = get_user_directory()
    if any(user["username"].lower() == normalized_username.lower() for user in existing_users):
        raise ValueError("Username already exists.")

    managed_users = _load_managed_users()
    if normalized_email and any((user.get("email") or "").lower() == normalized_email for user in managed_users):
        raise ValueError(
            "Email address is already associated with another managed user.")

    user_record = {
        "username": normalized_username,
        "password": None,
        "password_sha256": hashlib.sha256(password.encode("utf-8")).hexdigest(),
        "roles": _normalize_roles(roles, ["user"]),
        "email": normalized_email,
        "is_active": bool(is_active),
        "source": "managed",
        "created_at": _isoformat(_utc_now()),
        "registered_at": _isoformat(_utc_now()),
        "must_change_password": bool(must_change_password),
        "last_password_change_at": _isoformat(_utc_now()),
    }
    managed_users.append(user_record)
    _save_managed_users(managed_users)
    return user_record


def set_password(username: str, new_password: str, force_change_next_login: bool = False) -> dict[str, Any]:
    normalized_username = username.strip()
    if not normalized_username:
        raise ValueError("Username is required.")
    if len(new_password) < 8:
        raise ValueError("Password must be at least 8 characters long.")

    existing_user = _get_user_record(normalized_username)
    if not existing_user:
        raise ValueError("User not found.")

    managed_users = _load_managed_users()
    new_hash = hashlib.sha256(new_password.encode("utf-8")).hexdigest()
    updated = False

    for user in managed_users:
        if user["username"].lower() == normalized_username.lower():
            user["password"] = None
            user["password_sha256"] = new_hash
            user["roles"] = existing_user.get("roles", ["user"])
            user["email"] = existing_user.get("email")
            user["is_active"] = bool(existing_user.get("is_active", True))
            user["must_change_password"] = bool(force_change_next_login)
            user["last_password_change_at"] = _isoformat(_utc_now())
            user["registered_at"] = user.get(
                "registered_at") or _isoformat(_utc_now())
            user["source"] = "managed"
            updated = True
            user_record = user
            break

    if not updated:
        user_record = {
            "username": normalized_username,
            "password": None,
            "password_sha256": new_hash,
            "roles": existing_user.get("roles", ["user"]),
            "email": existing_user.get("email"),
            "is_active": bool(existing_user.get("is_active", True)),
            "source": "managed",
            "created_at": existing_user.get("created_at") or _isoformat(_utc_now()),
            "registered_at": existing_user.get("registered_at") or _isoformat(_utc_now()),
            "must_change_password": bool(force_change_next_login),
            "last_password_change_at": _isoformat(_utc_now()),
        }
        managed_users.append(user_record)

    _save_managed_users(managed_users)
    return user_record


def _render_force_password_change() -> None:
    username = str(st.session_state.get(AUTH_USER_KEY, "")).strip()
    st.title("Change Password")
    st.caption("You must change your password before continuing.")

    with st.form("force_password_change_form"):
        new_password = st.text_input("New password", type="password")
        confirm_password = st.text_input(
            "Confirm new password", type="password")
        submitted = st.form_submit_button(
            "Update password", use_container_width=True)

    if not submitted:
        return

    if new_password != confirm_password:
        st.error("Passwords do not match.")
        return

    try:
        updated_user = set_password(
            username, new_password, force_change_next_login=False)
    except ValueError as exc:
        st.error(str(exc))
        return

    st.session_state[AUTH_ROLES_KEY] = updated_user.get("roles", [])
    st.session_state[AUTH_FORCE_PASSWORD_CHANGE_KEY] = False
    st.success("Password updated.")
    st.rerun()


def send_invite_email(invite_id: str) -> tuple[bool, str]:
    settings = _smtp_settings()
    if not email_delivery_configured():
        return False, "SMTP is not configured."

    invites = get_invites()
    target_invite: Optional[dict[str, Any]] = None
    for invite in invites:
        if invite["invite_id"] == invite_id:
            target_invite = invite
            break

    if not target_invite:
        return False, "Invite not found."
    if target_invite.get("status") != "pending":
        return False, "Only pending invites can be emailed."

    invite_link = build_invite_link(target_invite["token"])
    msg = EmailMessage()
    msg["Subject"] = "Avisk Core Services invitation"
    msg["From"] = f'{settings["from_name"]} <{settings["from_email"]}>'
    msg["To"] = target_invite["email"]
    msg.set_content(
        "You have been invited to Avisk Core Services.\n\n"
        f"Roles: {', '.join(target_invite.get('roles', []))}\n"
        f"Register here: {invite_link}\n\n"
        f"This invite expires on {target_invite.get('expires_at')}."
    )

    try:
        with smtplib.SMTP(settings["host"], settings["port"], timeout=20) as smtp:
            if settings["use_tls"]:
                smtp.starttls()
            if settings["username"]:
                smtp.login(settings["username"], settings["password"])
            smtp.send_message(msg)
    except Exception as exc:
        for invite in invites:
            if invite["invite_id"] == invite_id:
                invite["last_email_error"] = str(exc)
        _save_invites(invites)
        return False, str(exc)

    for invite in invites:
        if invite["invite_id"] == invite_id:
            invite["sent_at"] = _isoformat(_utc_now())
            invite["last_email_error"] = None
    _save_invites(invites)
    return True, invite_link


def render_invite_registration() -> bool:
    token = str(st.query_params.get("invite_token", "") or "").strip()
    if not token:
        return False

    _hide_sidebar_navigation()
    invite = _find_invite_by_token(token)

    if not invite:
        st.title("Setup Link")
        st.error("This invite link is invalid.")
        return True
    if invite.get("status") != "pending":
        st.title("Setup Link")
        st.error("This invite is no longer active.")
        return True
    if _invite_is_expired(invite):
        st.title("Setup Link")
        st.error("This invite has expired.")
        return True

    invite_type = invite.get("invite_type", "registration")
    if invite_type == "password_setup":
        target_username = str(invite.get("target_username") or "").strip()
        st.title("Set Your Password")
        st.caption(f"Username: {target_username}")
        st.caption(f"Email: {invite.get('email')}")
        st.caption(f"Roles: {', '.join(invite.get('roles', []))}")

        with st.form("avisk_password_setup_form"):
            password = st.text_input("Create password", type="password")
            confirm_password = st.text_input(
                "Confirm password", type="password")
            submitted = st.form_submit_button(
                "Set password", use_container_width=True)

        if not submitted:
            return True

        if password != confirm_password:
            st.error("Passwords do not match.")
            return True

        try:
            updated_user = set_password(
                target_username, password, force_change_next_login=False)
        except ValueError as exc:
            st.error(str(exc))
            return True

        invites = get_invites()
        for existing_invite in invites:
            if existing_invite["invite_id"] == invite["invite_id"]:
                existing_invite["status"] = "accepted"
                existing_invite["accepted_at"] = _isoformat(_utc_now())
        _save_invites(invites)

        st.session_state[AUTH_STATE_KEY] = True
        st.session_state[AUTH_USER_KEY] = updated_user["username"]
        st.session_state[AUTH_ROLES_KEY] = updated_user.get("roles", [])
        st.session_state[AUTH_FORCE_PASSWORD_CHANGE_KEY] = False
        st.session_state.pop(AUTH_ERROR_KEY, None)
        st.query_params.clear()
        st.success("Password set. You are now signed in.")
        st.rerun()
        return True

    st.title("Complete Your Registration")

    st.caption(f"Invited email: {invite.get('email')}")
    st.caption(f"Roles: {', '.join(invite.get('roles', []))}")

    with st.form("avisk_registration_form"):
        username = st.text_input("Choose a username")
        password = st.text_input("Choose a password", type="password")
        confirm_password = st.text_input("Confirm password", type="password")
        submitted = st.form_submit_button(
            "Create account", use_container_width=True)

    if not submitted:
        return True

    if password != confirm_password:
        st.error("Passwords do not match.")
        return True

    try:
        registered_user = register_invited_user(token, username, password)
    except ValueError as exc:
        st.error(str(exc))
        return True

    st.session_state[AUTH_STATE_KEY] = True
    st.session_state[AUTH_USER_KEY] = registered_user["username"]
    st.session_state[AUTH_ROLES_KEY] = registered_user.get("roles", [])
    st.session_state.pop(AUTH_ERROR_KEY, None)
    st.query_params.clear()
    st.success("Registration complete. You are now signed in.")
    st.rerun()
    return True


def require_login(required_roles: Optional[list[str] | str] = None) -> None:
    normalized_required_roles = _normalize_roles(required_roles, [])

    if AUTH_STATE_KEY not in st.session_state:
        st.session_state[AUTH_STATE_KEY] = False

    if not st.session_state.get(AUTH_STATE_KEY):
        if render_invite_registration():
            st.stop()
        _render_login_form()
        st.stop()

    current_user = _get_user_record(
        str(st.session_state.get(AUTH_USER_KEY, "")))
    if current_user is not None:
        st.session_state[AUTH_FORCE_PASSWORD_CHANGE_KEY] = bool(
            current_user.get("must_change_password", False))

    if st.session_state.get(AUTH_FORCE_PASSWORD_CHANGE_KEY):
        _hide_sidebar_navigation()
        _render_force_password_change()
        st.stop()

    if not _has_required_role(normalized_required_roles):
        _render_access_denied(normalized_required_roles)
        st.stop()

    with st.sidebar:
        st.caption(
            f"Signed in as {st.session_state.get(AUTH_USER_KEY, 'user')}")
        st.caption(f"Roles: {', '.join(_current_roles()) or 'none'}")
        if st.button("Log out", use_container_width=True):
            _clear_auth_state()
            st.rerun()
