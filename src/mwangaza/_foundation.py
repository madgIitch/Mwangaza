from __future__ import annotations

from dataclasses import dataclass

from mwangaza import FOUNDATION_STATUS, PROJECT_NAME, TAGLINE, __version__


@dataclass(frozen=True)
class FoundationStatus:
    project: str = PROJECT_NAME
    tagline: str = TAGLINE
    version: str = __version__
    status: str = FOUNDATION_STATUS
    remote_calls_enabled: bool = False

    def as_dict(self) -> dict[str, str | bool]:
        return {
            "project": self.project,
            "tagline": self.tagline,
            "version": self.version,
            "status": self.status,
            "remote_calls_enabled": self.remote_calls_enabled,
        }


def foundation_status() -> FoundationStatus:
    return FoundationStatus()
