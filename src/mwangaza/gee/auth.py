from __future__ import annotations

import argparse
import importlib
import json
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Callable, Literal

from mwangaza.config import ConfigurationError, Settings, load_settings

GeeStatus = Literal["ok", "auth_error", "permission_error", "quota_error", "network_error"]

STATUSES: tuple[GeeStatus, ...] = (
    "ok",
    "auth_error",
    "permission_error",
    "quota_error",
    "network_error",
)
DEFAULT_MAX_ATTEMPTS = 3
DEFAULT_BASE_DELAY_SECONDS = 0.1
REQUIRED_SECRET_FIELDS = ("private_key",)


@dataclass(frozen=True, repr=False)
class GeeAuthResult:
    status: GeeStatus
    configured: bool
    project_configured: bool
    service_account_configured: bool
    checked_at: str
    attempts: int
    max_attempts: int
    message: str
    missing_required_variables: tuple[str, ...] = ()
    error_code: str | None = None

    def __repr__(self) -> str:
        return (
            "GeeAuthResult("
            f"status={self.status!r}, configured={self.configured!r}, "
            f"project_configured={self.project_configured!r}, "
            f"service_account_configured={self.service_account_configured!r}, "
            f"attempts={self.attempts!r}, max_attempts={self.max_attempts!r}, "
            f"message={self.message!r}, "
            f"missing_required_variables={self.missing_required_variables!r}, "
            f"error_code={self.error_code!r})"
        )

    def to_public_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "configured": self.configured,
            "project_configured": self.project_configured,
            "service_account_configured": self.service_account_configured,
            "checked_at": self.checked_at,
            "attempts": self.attempts,
            "max_attempts": self.max_attempts,
            "message": self.message,
            "missing_required_variables": list(self.missing_required_variables),
            "error_code": self.error_code,
        }


def check_gee_auth(
    settings: Settings | None = None,
    *,
    ee_module: object | None = None,
    max_attempts: int | None = None,
    base_delay_seconds: float = DEFAULT_BASE_DELAY_SECONDS,
    sleep: Callable[[float], None] | None = None,
) -> GeeAuthResult:
    attempts_limit = max_attempts or DEFAULT_MAX_ATTEMPTS
    sleeper = sleep or time.sleep
    checked_at = _utc_now()

    try:
        resolved = settings or load_settings()
    except ConfigurationError as exc:
        missing = tuple(
            name
            for name in exc.missing_variables
            if name
            in {
                "MWANGAZA_GEE_PROJECT",
                "MWANGAZA_GEE_SERVICE_ACCOUNT",
                "MWANGAZA_GEE_PRIVATE_KEY_JSON",
            }
        )
        return GeeAuthResult(
            status="auth_error",
            configured=False,
            project_configured=False,
            service_account_configured=False,
            checked_at=checked_at,
            attempts=0,
            max_attempts=attempts_limit,
            message="Earth Engine credentials are not configured.",
            missing_required_variables=missing,
            error_code="missing_credentials",
        )

    missing = _missing_gee_variables(resolved)
    configured = not missing
    if missing:
        return GeeAuthResult(
            status="auth_error",
            configured=False,
            project_configured=resolved.gee_project is not None,
            service_account_configured=resolved.gee_service_account is not None,
            checked_at=checked_at,
            attempts=0,
            max_attempts=attempts_limit,
            message="Earth Engine credentials are not configured.",
            missing_required_variables=missing,
            error_code="missing_credentials",
        )

    secret = _load_secret_json(resolved.gee_private_key_json)
    if secret is None or any(not secret.get(field) for field in REQUIRED_SECRET_FIELDS):
        return GeeAuthResult(
            status="auth_error",
            configured=False,
            project_configured=True,
            service_account_configured=True,
            checked_at=checked_at,
            attempts=0,
            max_attempts=attempts_limit,
            message="Earth Engine service account JSON is invalid.",
            error_code="invalid_service_account_json",
        )

    module = ee_module
    if module is None:
        try:
            module = importlib.import_module("ee")
        except Exception:
            return GeeAuthResult(
                status="auth_error",
                configured=True,
                project_configured=True,
                service_account_configured=True,
                checked_at=checked_at,
                attempts=0,
                max_attempts=attempts_limit,
                message="Earth Engine SDK is not installed.",
                error_code="sdk_unavailable",
            )

    last_result: GeeAuthResult | None = None
    for attempt in range(1, attempts_limit + 1):
        try:
            credentials = module.ServiceAccountCredentials(
                resolved.gee_service_account,
                key_data=resolved.gee_private_key_json,
            )
            module.Initialize(credentials, project=resolved.gee_project)
            data = getattr(module, "data", None)
            if data is not None and hasattr(data, "getAssetRoots"):
                data.getAssetRoots()
            return GeeAuthResult(
                status="ok",
                configured=True,
                project_configured=True,
                service_account_configured=True,
                checked_at=checked_at,
                attempts=attempt,
                max_attempts=attempts_limit,
                message="Earth Engine authentication check succeeded.",
            )
        except Exception as exc:
            status, code = _classify_error(exc)
            last_result = GeeAuthResult(
                status=status,
                configured=True,
                project_configured=True,
                service_account_configured=True,
                checked_at=checked_at,
                attempts=attempt,
                max_attempts=attempts_limit,
                message=_message_for_status(status),
                error_code=code,
            )
            if attempt < attempts_limit:
                sleeper(base_delay_seconds * (2 ** (attempt - 1)))

    return last_result or GeeAuthResult(
        status="network_error",
        configured=True,
        project_configured=True,
        service_account_configured=True,
        checked_at=checked_at,
        attempts=0,
        max_attempts=attempts_limit,
        message="Earth Engine authentication check failed.",
        error_code="unknown_error",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check Google Earth Engine authentication.")
    parser.add_argument("--check", action="store_true", help="Run the GEE authentication health check.")
    args = parser.parse_args(argv)
    if not args.check:
        parser.print_help()
        return 2
    result = check_gee_auth()
    print(json.dumps({"gee": result.to_public_dict()}, sort_keys=True))
    return 0 if result.status == "ok" else 1


def _missing_gee_variables(settings: Settings) -> tuple[str, ...]:
    missing = []
    if settings.gee_project is None:
        missing.append("MWANGAZA_GEE_PROJECT")
    if settings.gee_service_account is None:
        missing.append("MWANGAZA_GEE_SERVICE_ACCOUNT")
    if settings.gee_private_key_json is None:
        missing.append("MWANGAZA_GEE_PRIVATE_KEY_JSON")
    return tuple(missing)


def _load_secret_json(raw: str | None) -> dict[str, object] | None:
    if raw is None:
        return None
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def _classify_error(exc: Exception) -> tuple[GeeStatus, str]:
    text = str(exc).lower()
    if any(token in text for token in ("401", "auth", "credential", "unauthorized", "revoked")):
        return "auth_error", "auth_error"
    if any(token in text for token in ("403", "forbidden", "permission")):
        return "permission_error", "permission_error"
    if any(token in text for token in ("429", "quota", "rate", "resource exhausted")):
        return "quota_error", "quota_error"
    if any(token in text for token in ("timeout", "dns", "connection", "unavailable", "500", "502", "503", "504")):
        return "network_error", "network_error"
    return "network_error", "unknown_error"


def _message_for_status(status: GeeStatus) -> str:
    return {
        "ok": "Earth Engine authentication check succeeded.",
        "auth_error": "Earth Engine credentials could not be authenticated.",
        "permission_error": "Earth Engine credentials lack required permissions.",
        "quota_error": "Earth Engine quota or rate limit prevented the check.",
        "network_error": "Earth Engine authentication check could not reach the service.",
    }[status]


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


if __name__ == "__main__":
    raise SystemExit(main())
