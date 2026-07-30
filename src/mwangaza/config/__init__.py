from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

Environment = str

ALLOWED_ENVIRONMENTS = ("local", "test", "demo", "production")
ALLOWED_LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
ALLOWED_COUNTRIES = ("KEN", "ETH", "SOM", "SDN", "SSD", "UGA", "DJI", "ERI")
PRIVATE_VARIABLES = ("MWANGAZA_GEE_SERVICE_ACCOUNT", "MWANGAZA_GEE_PRIVATE_KEY_JSON")
PUBLIC_VARIABLES = (
    "MWANGAZA_ENV",
    "MWANGAZA_LOG_LEVEL",
    "MWANGAZA_DATA_DIR",
    "MWANGAZA_CACHE_DIR",
    "MWANGAZA_REFRESH_CACHE_DIR",
    "MWANGAZA_API_DATA_MODE",
    "MWANGAZA_DEMO_FIXTURE_DIR",
    "MWANGAZA_ENABLED_COUNTRIES",
    "MWANGAZA_CLIMATOLOGY_START_YEAR",
    "MWANGAZA_CLIMATOLOGY_END_YEAR",
    "MWANGAZA_CLIMATOLOGY_MIN_YEARS",
    "MWANGAZA_MAX_REMOTE_PIXELS",
    "MWANGAZA_GEE_PROJECT",
    "MWANGAZA_NDVI_COLLECTION",
    "MWANGAZA_RAINFALL_COLLECTION",
)
PRODUCTION_REQUIRED_VARIABLES = (
    "MWANGAZA_GEE_PROJECT",
    "MWANGAZA_GEE_SERVICE_ACCOUNT",
    "MWANGAZA_GEE_PRIVATE_KEY_JSON",
)
REDACTED = "***REDACTED***"


class ConfigurationError(ValueError):
    def __init__(
        self,
        message: str,
        *,
        environment: str = "unknown",
        missing_variables: tuple[str, ...] = (),
        invalid_fields: tuple[str, ...] = (),
    ) -> None:
        self.environment = environment
        self.missing_variables = missing_variables
        self.invalid_fields = invalid_fields
        detail = message
        if missing_variables:
            detail += f"; missing required variables: {', '.join(missing_variables)}"
        if invalid_fields:
            detail += f"; invalid fields: {', '.join(invalid_fields)}"
        detail += "; set the documented MWANGAZA_* variables and retry"
        super().__init__(f"Invalid Mwangaza configuration for {environment}: {detail}")

    def to_public_dict(self) -> dict[str, object]:
        return {
            "environment": self.environment,
            "config_valid": False,
            "missing_required_variables": list(self.missing_variables),
            "invalid_fields": list(self.invalid_fields),
            "message": str(self),
        }


@dataclass(frozen=True, repr=False)
class Settings:
    environment: Environment
    log_level: str
    data_dir: Path
    cache_dir: Path
    demo_fixture_dir: Path
    enabled_countries: tuple[str, ...]
    climatology_start_year: int
    climatology_end_year: int
    climatology_min_years: int
    gee_project: str | None
    gee_service_account: str | None
    gee_private_key_json: str | None
    max_remote_pixels: int
    ndvi_collection: str
    rainfall_collection: str

    def __repr__(self) -> str:
        return (
            "Settings("
            f"environment={self.environment!r}, "
            f"log_level={self.log_level!r}, "
            f"data_dir={str(self.data_dir)!r}, "
            f"cache_dir={str(self.cache_dir)!r}, "
            f"demo_fixture_dir={str(self.demo_fixture_dir)!r}, "
            f"enabled_countries={self.enabled_countries!r}, "
            f"climatology_start_year={self.climatology_start_year!r}, "
            f"climatology_end_year={self.climatology_end_year!r}, "
            f"climatology_min_years={self.climatology_min_years!r}, "
            f"gee_project={self.gee_project!r}, "
            f"gee_service_account={REDACTED!r}, "
            f"gee_private_key_json={REDACTED!r}, "
            f"max_remote_pixels={self.max_remote_pixels!r}, "
            f"ndvi_collection={self.ndvi_collection!r}, "
            f"rainfall_collection={self.rainfall_collection!r})"
        )

    @property
    def climatology_period(self) -> dict[str, int]:
        return {
            "start_year": self.climatology_start_year,
            "end_year": self.climatology_end_year,
            "min_years": self.climatology_min_years,
        }

    def to_public_dict(self) -> dict[str, object]:
        return {
            "environment": self.environment,
            "config_valid": True,
            "log_level": self.log_level,
            "data_dir": str(self.data_dir),
            "cache_dir": str(self.cache_dir),
            "demo_fixture_dir": str(self.demo_fixture_dir),
            "enabled_countries": list(self.enabled_countries),
            "climatology_period": self.climatology_period,
            "max_remote_pixels": self.max_remote_pixels,
            "ndvi_collection": self.ndvi_collection,
            "rainfall_collection": self.rainfall_collection,
            "gee_project_configured": self.gee_project is not None,
            "gee_service_account_configured": self.gee_service_account is not None,
            "gee_private_key_json_configured": self.gee_private_key_json is not None,
        }


def load_settings(env: Mapping[str, str] | None = None) -> Settings:
    source = _runtime_env() if env is None else env
    environment = _get(source, "MWANGAZA_ENV", "local").lower()
    invalid_fields: list[str] = []

    if environment not in ALLOWED_ENVIRONMENTS:
        raise ConfigurationError(
            "unknown environment",
            environment=environment,
            invalid_fields=("MWANGAZA_ENV",),
        )

    log_level = _get(source, "MWANGAZA_LOG_LEVEL", "INFO").upper()
    if log_level not in ALLOWED_LOG_LEVELS:
        invalid_fields.append("MWANGAZA_LOG_LEVEL")

    data_dir = _path(source, "MWANGAZA_DATA_DIR", "./data", invalid_fields)
    cache_dir = _path(source, "MWANGAZA_CACHE_DIR", "./.cache/mwangaza", invalid_fields)
    demo_fixture_dir = _path(source, "MWANGAZA_DEMO_FIXTURE_DIR", "./demo_data", invalid_fields)
    enabled_countries = _countries(source, invalid_fields)
    start_year = _int(source, "MWANGAZA_CLIMATOLOGY_START_YEAR", "2001", invalid_fields)
    end_year = _int(source, "MWANGAZA_CLIMATOLOGY_END_YEAR", "2020", invalid_fields)
    min_years = _int(source, "MWANGAZA_CLIMATOLOGY_MIN_YEARS", "10", invalid_fields)
    max_remote_pixels = _int(source, "MWANGAZA_MAX_REMOTE_PIXELS", "100000000", invalid_fields)
    ndvi_collection = _get(source, "MWANGAZA_NDVI_COLLECTION", "MODIS/061/MOD13Q1")
    rainfall_collection = _get(source, "MWANGAZA_RAINFALL_COLLECTION", "UCSB-CHG/CHIRPS/DAILY")

    if start_year is not None and end_year is not None and start_year > end_year:
        invalid_fields.extend(["MWANGAZA_CLIMATOLOGY_START_YEAR", "MWANGAZA_CLIMATOLOGY_END_YEAR"])
    if max_remote_pixels is not None and max_remote_pixels <= 0:
        invalid_fields.append("MWANGAZA_MAX_REMOTE_PIXELS")
    if min_years is not None and min_years <= 0:
        invalid_fields.append("MWANGAZA_CLIMATOLOGY_MIN_YEARS")
    if not ndvi_collection:
        invalid_fields.append("MWANGAZA_NDVI_COLLECTION")
    if not rainfall_collection:
        invalid_fields.append("MWANGAZA_RAINFALL_COLLECTION")

    gee_project = _optional(source, "MWANGAZA_GEE_PROJECT")
    gee_service_account = _optional(source, "MWANGAZA_GEE_SERVICE_ACCOUNT")
    gee_private_key_json = _optional(source, "MWANGAZA_GEE_PRIVATE_KEY_JSON")
    if gee_private_key_json is not None:
        try:
            parsed = json.loads(gee_private_key_json)
        except json.JSONDecodeError:
            invalid_fields.append("MWANGAZA_GEE_PRIVATE_KEY_JSON")
        else:
            if not isinstance(parsed, dict):
                invalid_fields.append("MWANGAZA_GEE_PRIVATE_KEY_JSON")

    missing = _missing_required(source, environment)
    if missing or invalid_fields:
        raise ConfigurationError(
            "configuration values failed validation",
            environment=environment,
            missing_variables=tuple(missing),
            invalid_fields=tuple(dict.fromkeys(invalid_fields)),
        )

    return Settings(
        environment=environment,
        log_level=log_level,
        data_dir=data_dir,
        cache_dir=cache_dir,
        demo_fixture_dir=demo_fixture_dir,
        enabled_countries=enabled_countries,
        climatology_start_year=start_year if start_year is not None else 2001,
        climatology_end_year=end_year if end_year is not None else 2020,
        climatology_min_years=min_years if min_years is not None else 10,
        gee_project=gee_project,
        gee_service_account=gee_service_account,
        gee_private_key_json=gee_private_key_json,
        max_remote_pixels=max_remote_pixels if max_remote_pixels is not None else 100000000,
        ndvi_collection=ndvi_collection,
        rainfall_collection=rainfall_collection,
    )


def public_config_status(env: Mapping[str, str] | None = None) -> dict[str, object]:
    try:
        return load_settings(env).to_public_dict()
    except ConfigurationError as exc:
        return exc.to_public_dict()


def _runtime_env() -> Mapping[str, str]:
    dot_env = _read_dotenv(Path.cwd() / ".env")
    if not dot_env:
        return os.environ
    merged = dict(dot_env)
    merged.update(os.environ)
    return merged


def _read_dotenv(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        name = name.strip()
        if not name or not name.startswith("MWANGAZA_"):
            continue
        values[name] = _strip_dotenv_quotes(value.strip())
    return values


def _strip_dotenv_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _get(source: Mapping[str, str], name: str, default: str) -> str:
    value = source.get(name, default)
    return value.strip() if isinstance(value, str) else default


def _optional(source: Mapping[str, str], name: str) -> str | None:
    value = source.get(name)
    if value is None:
        return None
    value = value.strip()
    if not value or value == "replace-me":
        return None
    return value


def _path(source: Mapping[str, str], name: str, default: str, invalid_fields: list[str]) -> Path:
    value = _get(source, name, default)
    if not value:
        invalid_fields.append(name)
        value = default
    return Path(value)


def _int(
    source: Mapping[str, str],
    name: str,
    default: str,
    invalid_fields: list[str],
) -> int | None:
    value = _get(source, name, default)
    try:
        return int(value)
    except ValueError:
        invalid_fields.append(name)
        return None


def _countries(source: Mapping[str, str], invalid_fields: list[str]) -> tuple[str, ...]:
    raw = _get(source, "MWANGAZA_ENABLED_COUNTRIES", ",".join(ALLOWED_COUNTRIES))
    countries = tuple(part.strip().upper() for part in raw.split(",") if part.strip())
    if not countries:
        invalid_fields.append("MWANGAZA_ENABLED_COUNTRIES")
        return ()
    unknown = [country for country in countries if country not in ALLOWED_COUNTRIES]
    if unknown:
        invalid_fields.append("MWANGAZA_ENABLED_COUNTRIES")
    return countries


def _missing_required(source: Mapping[str, str], environment: str) -> list[str]:
    if environment != "production":
        return []
    if _optional(source, "MWANGAZA_API_DATA_MODE") == "cache":
        return []
    return [name for name in PRODUCTION_REQUIRED_VARIABLES if _optional(source, name) is None]
