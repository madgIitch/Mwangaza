from __future__ import annotations

from dataclasses import dataclass

AVAILABLE_LANGUAGES = ("en", "sw", "so")
REQUIRED_KEYS = (
    "nav.overview",
    "nav.region",
    "nav.alerts",
    "nav.reports",
    "nav.about",
    "status.live",
    "status.cache",
    "status.demo",
    "risk.critical",
    "risk.warning",
    "risk.watch",
    "recommendation.prepare",
)

CATALOGS: dict[str, dict[str, str]] = {
    "en": {
        "nav.overview": "Overview",
        "nav.region": "Region",
        "nav.alerts": "Alerts",
        "nav.reports": "Reports",
        "nav.about": "About",
        "status.live": "Live data",
        "status.cache": "Cache data",
        "status.demo": "Demo data",
        "risk.critical": "Critical",
        "risk.warning": "Warning",
        "risk.watch": "Watch",
        "recommendation.prepare": "Prepare early action checklist.",
    },
    "sw": {
        "nav.overview": "Muhtasari",
        "nav.region": "Eneo",
        "nav.alerts": "Tahadhari",
        "nav.reports": "Ripoti",
        "nav.about": "Kuhusu",
        "status.live": "Data hai",
        "status.cache": "Data ya akiba",
        "status.demo": "Data ya mfano",
        "risk.critical": "Hatari kubwa",
        "risk.warning": "Onyo",
        "risk.watch": "Ufuatiliaji",
        "recommendation.prepare": "Andaa orodha ya hatua za mapema.",
    },
    "so": {
        "nav.overview": "Guudmar",
        "nav.region": "Gobol",
        "nav.alerts": "Digniino",
        "nav.reports": "Warbixinno",
        "nav.about": "Ku saabsan",
        "status.live": "Xog toos ah",
        "status.cache": "Xog kaydsan",
        "status.demo": "Xog tijaabo",
        "risk.critical": "Halis sare",
        "risk.warning": "Digniin",
        "risk.watch": "La socosho",
        "recommendation.prepare": "Diyaari liiska tallaabooyinka hore.",
    },
}


@dataclass(frozen=True)
class Translation:
    value: str
    language: str
    warnings: tuple[str, ...] = ()


def normalize_language(language: str | None) -> str:
    return language if language in AVAILABLE_LANGUAGES else "en"


def translate(key: str, *, language: str = "en") -> Translation:
    lang = normalize_language(language)
    catalog = CATALOGS[lang]
    if key in catalog:
        return Translation(catalog[key], lang)
    return Translation(CATALOGS["en"].get(key, key), lang, (f"missing translation: {lang}.{key}",))


def validate_catalogs(catalogs: dict[str, dict[str, str]] | None = None) -> None:
    checked = catalogs or CATALOGS
    if tuple(sorted(checked)) != tuple(sorted(AVAILABLE_LANGUAGES)):
        raise ValueError("catalogs must include exactly en, sw and so")
    for language, catalog in checked.items():
        missing = [key for key in REQUIRED_KEYS if key not in catalog]
        if missing:
            raise ValueError(f"missing i18n keys for {language}: {', '.join(missing)}")


def catalog_warnings(language: str) -> tuple[str, ...]:
    lang = normalize_language(language)
    return tuple(
        warning
        for key in REQUIRED_KEYS
        for warning in translate(key, language=lang).warnings
    )


__all__ = [
    "AVAILABLE_LANGUAGES",
    "CATALOGS",
    "REQUIRED_KEYS",
    "Translation",
    "catalog_warnings",
    "normalize_language",
    "translate",
    "validate_catalogs",
]
