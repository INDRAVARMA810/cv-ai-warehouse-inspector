"""Structured data types produced by the safety rule engine.

These dataclasses form the stable contract between the rule layer
(:mod:`app.rules`) and any downstream consumer (a future alerting
service, dashboard, or incident store), independent of which rules
produced them.
"""

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Dict, List, Optional, Tuple


class Severity(IntEnum):
    """Severity of a safety violation, ordered least to most serious.

    Declared as an :class:`~enum.IntEnum` so severities compare and sort
    naturally (``Severity.HIGH > Severity.LOW``), which lets consumers
    filter by a minimum threshold without a lookup table.
    """

    INFO = 10
    LOW = 20
    MEDIUM = 30
    HIGH = 40
    CRITICAL = 50

    def __str__(self) -> str:
        """Return the lowercase severity name, for logs and serialization."""
        return self.name.lower()


@dataclass
class RuleViolation:
    """A single safety violation raised by one rule.

    Attributes:
        rule_name: Name of the rule that raised this violation.
        severity: How serious the violation is.
        description: Human-readable explanation of what went wrong.
        timestamp: Unix timestamp (seconds) when the violation was raised.
        frame_number: Index of the frame the violation was detected in.
        track_id: Identity of the object responsible, or ``None`` for
            violations that concern the scene as a whole (e.g. an
            occupancy limit) rather than one object.
        bounding_box: Location of the offending object as
            ``(x1, y1, x2, y2)`` in pixels, or ``None`` if not
            applicable. Stored as a plain tuple to keep this layer
            decoupled from the detection and tracking types and to stay
            trivially serializable.
        metadata: Free-form, rule-specific detail (measured distances,
            zone names, involved track IDs, ...). Kept open so new rules
            can attach context without changing this contract.
    """

    rule_name: str
    severity: Severity
    description: str
    timestamp: float
    frame_number: Optional[int] = None
    track_id: Optional[int] = None
    bounding_box: Optional[Tuple[float, float, float, float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RuleResult:
    """The complete outcome of evaluating all rules against one frame.

    Attributes:
        violations: Every violation raised for this frame.
        frame_number: Index of the frame that was evaluated.
        timestamp: Unix timestamp (seconds) of the evaluation.
        rules_evaluated: How many rules actually ran.
        evaluation_time_ms: Wall-clock evaluation time, in milliseconds.
        failed_rules: Names of rules that raised an unexpected error and
            were skipped. Empty on a healthy evaluation.
    """

    violations: List[RuleViolation] = field(default_factory=list)
    frame_number: Optional[int] = None
    timestamp: Optional[float] = None
    rules_evaluated: int = 0
    evaluation_time_ms: Optional[float] = None
    failed_rules: List[str] = field(default_factory=list)

    def __len__(self) -> int:
        """Return the number of violations recorded."""
        return len(self.violations)

    @property
    def is_safe(self) -> bool:
        """Whether the frame produced no violations at all."""
        return len(self.violations) == 0

    @property
    def highest_severity(self) -> Optional[Severity]:
        """The most serious severity present, or ``None`` if there are no violations."""
        if not self.violations:
            return None
        return max(violation.severity for violation in self.violations)

    def by_severity(self, minimum: Severity) -> List[RuleViolation]:
        """Return violations at or above a severity threshold.

        Args:
            minimum: The lowest severity to include.

        Returns:
            The matching violations, most severe first.
        """
        matches = [v for v in self.violations if v.severity >= minimum]
        return sorted(matches, key=lambda v: v.severity, reverse=True)

    def by_rule(self, rule_name: str) -> List[RuleViolation]:
        """Return only the violations raised by a given rule.

        Args:
            rule_name: The rule name to filter by.

        Returns:
            The matching violations, in the order they were raised.
        """
        return [v for v in self.violations if v.rule_name == rule_name]

    def by_track(self, track_id: int) -> List[RuleViolation]:
        """Return only the violations attributed to a given track identity.

        Args:
            track_id: The track identity to filter by.

        Returns:
            The matching violations, in the order they were raised.
        """
        return [v for v in self.violations if v.track_id == track_id]
