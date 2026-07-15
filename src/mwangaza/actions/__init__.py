from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from mwangaza.contracts import RiskSnapshot


class RecommendationError(ValueError):
    pass


@dataclass(frozen=True)
class ActionTemplate:
    level: str
    action: str
    suggested_actor: str
    urgency: str


@dataclass(frozen=True)
class ActionCatalog:
    recommendation_version: str
    templates: dict[str, ActionTemplate]


@dataclass(frozen=True)
class ActionRecommendation:
    action: str
    suggested_actor: str
    urgency: str
    evidence: dict[str, Any]
    recommendation_version: str
    disclaimer: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "suggested_actor": self.suggested_actor,
            "urgency": self.urgency,
            "evidence": dict(self.evidence),
            "recommendation_version": self.recommendation_version,
            "disclaimer": self.disclaimer,
        }


def default_action_catalog() -> ActionCatalog:
    return ActionCatalog(
        recommendation_version="actions-v1",
        templates={
            "green": ActionTemplate("green", "Continue routine monitoring", "Analyst", "monitoring"),
            "watch": ActionTemplate("watch", "Prepare early action checklist", "Program lead", "preparation"),
            "warning": ActionTemplate("warning", "Preposition supplies and brief partners", "Operations lead", "prepositioning"),
            "emergency": ActionTemplate("emergency", "Activate urgent coordination review", "Incident lead", "urgent_activation"),
            "unknown": ActionTemplate("unknown", "Review data quality before intervention", "Data lead", "data_review"),
        },
    )


def recommend_actions(
    risk_snapshot: RiskSnapshot,
    catalog: ActionCatalog | None = None,
) -> tuple[ActionRecommendation, ...]:
    resolved = catalog or default_action_catalog()
    _validate_catalog(resolved)
    level = risk_snapshot.metadata.get("risk_level_override", risk_snapshot.risk_level)
    if risk_snapshot.composite_score is None or level == "unknown":
        level = "unknown"
    template = resolved.templates.get(str(level))
    if template is None:
        raise RecommendationError(f"no action template for risk level: {level}")
    return (
        ActionRecommendation(
            action=template.action,
            suggested_actor=template.suggested_actor,
            urgency=template.urgency,
            evidence={
                "region_id": risk_snapshot.region_id,
                "risk_level": level,
                "composite_score": risk_snapshot.composite_score,
                "quality_flag": risk_snapshot.quality_flag,
                "source": risk_snapshot.source,
            },
            recommendation_version=resolved.recommendation_version,
            disclaimer="Prototype guidance only; not an official order or medical advice.",
        ),
    )


def _validate_catalog(catalog: ActionCatalog) -> None:
    if not catalog.recommendation_version:
        raise RecommendationError("recommendation_version is required")
    for level in ("green", "watch", "warning", "emergency", "unknown"):
        if level not in catalog.templates:
            raise RecommendationError(f"missing action template: {level}")


__all__ = [
    "ActionCatalog",
    "ActionRecommendation",
    "ActionTemplate",
    "RecommendationError",
    "default_action_catalog",
    "recommend_actions",
]
