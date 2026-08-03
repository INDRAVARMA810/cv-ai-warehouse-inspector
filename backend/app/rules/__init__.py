"""Safety rule engine.

Provides a modular business-rule architecture: an abstract rule
contract (:class:`BaseRule`), concrete warehouse safety rules, spatial
zone primitives, a registry controlling which rules are active, and an
orchestrating engine. Rules are pure functions of a
:class:`RuleContext`, so new checks can be added without touching the
engine, and the engine can run without knowing any rule's internals.
"""

from app.rules.rule import BaseRule, RuleContext
from app.rules.rule_engine import RuleEngine
from app.rules.rule_registry import (
    DuplicateRuleError,
    RuleRegistry,
    build_default_registry,
)
from app.rules.rule_result import RuleResult, RuleViolation, Severity
from app.rules.safety_rules import (
    DEFAULT_RULES,
    MaximumWorkersRule,
    MinimumDistanceRule,
    PPEPlaceholderRule,
    RestrictedZoneRule,
)
from app.rules.zone import PolygonZone, RectangleZone, Zone, ZoneType

__all__ = [
    "BaseRule",
    "RuleContext",
    "RuleEngine",
    "RuleRegistry",
    "build_default_registry",
    "DuplicateRuleError",
    "RuleResult",
    "RuleViolation",
    "Severity",
    "RestrictedZoneRule",
    "MinimumDistanceRule",
    "MaximumWorkersRule",
    "PPEPlaceholderRule",
    "DEFAULT_RULES",
    "Zone",
    "ZoneType",
    "RectangleZone",
    "PolygonZone",
]
