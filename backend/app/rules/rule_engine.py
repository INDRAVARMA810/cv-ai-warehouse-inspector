"""Safety rule evaluation orchestration.

Provides :class:`RuleEngine`, the single entry point the rest of the
application should use to turn tracked objects into safety violations.
It owns no rule-specific logic — that lives in the individual
:class:`~app.rules.rule.BaseRule` subclasses — so the rule set can grow
without this module changing.
"""

import time
from typing import Any, Dict, List, Optional, Sequence, Tuple

from app.logger import logger
from app.rules.rule import BaseRule, RuleContext
from app.rules.rule_registry import RuleRegistry, build_default_registry
from app.rules.rule_result import RuleResult, RuleViolation, Severity
from app.rules.zone import Zone


class RuleEngine:
    """Evaluates the registered safety rules against each frame.

    A failure inside one rule is contained: it is logged, recorded in
    the result's ``failed_rules``, and the remaining rules still run.
    One misbehaving rule must never take down a live safety pipeline or
    silently suppress the others' findings.

    Attributes:
        registry: The registry supplying rules to evaluate.
        zones: The zones available to rules, keyed by name.
    """

    def __init__(
        self,
        registry: Optional[RuleRegistry] = None,
        zones: Optional[Sequence[Zone]] = None,
    ) -> None:
        """Configure the engine.

        Args:
            registry: The rule registry to evaluate from. Defaults to a
                registry pre-populated with the standard rule set.
            zones: Zones to make available to rules. Names must be
                unique.

        Raises:
            ValueError: If two zones share a name.
        """
        self.registry = registry if registry is not None else build_default_registry()
        self.zones: Dict[str, Zone] = {}

        if zones:
            self.add_zones(zones)

    def add_zone(self, zone: Zone, replace: bool = False) -> None:
        """Make a zone available to rules.

        Args:
            zone: The zone to add.
            replace: If ``True``, overwrite an existing zone of the same
                name instead of raising.

        Raises:
            ValueError: If the name is taken and ``replace`` is ``False``.
        """
        if zone.name in self.zones and not replace:
            raise ValueError(
                f"A zone named '{zone.name}' already exists. "
                f"Pass replace=True to override it."
            )

        self.zones[zone.name] = zone
        logger.debug(f"Zone '{zone.name}' ({zone.zone_type.value}) added to rule engine.")

    def add_zones(self, zones: Sequence[Zone], replace: bool = False) -> None:
        """Make several zones available to rules.

        Args:
            zones: The zones to add.
            replace: Whether to overwrite existing zones by name.

        Raises:
            ValueError: If a name is taken and ``replace`` is ``False``.
        """
        for zone in zones:
            self.add_zone(zone, replace=replace)

    def remove_zone(self, zone_name: str) -> bool:
        """Remove a zone.

        Args:
            zone_name: Name of the zone to remove.

        Returns:
            ``True`` if a zone was removed, ``False`` if the name was
            not present.
        """
        removed = self.zones.pop(zone_name, None)

        if removed is None:
            logger.warning(f"Cannot remove unknown zone '{zone_name}'.")
            return False

        logger.debug(f"Zone '{zone_name}' removed from rule engine.")
        return True

    def evaluate(
        self,
        tracked_objects: Sequence[Any],
        frame_number: Optional[int] = None,
        frame_shape: Optional[Tuple[int, int]] = None,
        timestamp: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> RuleResult:
        """Evaluate every enabled rule against one frame.

        Args:
            tracked_objects: The frame's tracked objects, as produced by
                :mod:`app.tracking`.
            frame_number: Index of the frame being evaluated.
            frame_shape: ``(height, width)`` of the source frame.
            timestamp: Unix timestamp (seconds) of the frame. Defaults
                to the current time.
            metadata: Free-form extra context passed through to rules.

        Returns:
            A :class:`RuleResult` describing every violation found, plus
            the names of any rules that failed and were skipped. Never
            raises on rule failure.
        """
        start_time = time.perf_counter()

        context = RuleContext(
            tracked_objects=tracked_objects or [],
            frame_number=frame_number,
            timestamp=timestamp if timestamp is not None else time.time(),
            frame_shape=frame_shape,
            zones=self.zones,
            metadata=metadata or {},
        )

        violations: List[RuleViolation] = []
        failed_rules: List[str] = []
        rules = self.registry.enabled_rules()

        for rule in rules:
            try:
                rule_violations = rule.evaluate(context)
            except Exception:
                # Contain the failure: log it, note it, keep evaluating.
                logger.exception(
                    f"Rule '{rule.name}' raised an unexpected error on frame "
                    f"{frame_number}; skipping it for this frame."
                )
                failed_rules.append(rule.name)
                continue

            if rule_violations:
                violations.extend(rule_violations)

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        result = RuleResult(
            violations=violations,
            frame_number=frame_number,
            timestamp=context.timestamp,
            rules_evaluated=len(rules),
            evaluation_time_ms=elapsed_ms,
            failed_rules=failed_rules,
        )

        self._log_result(result)
        return result

    @staticmethod
    def _log_result(result: RuleResult) -> None:
        """Emit a log line proportionate to the result's seriousness.

        Args:
            result: The result to report.
        """
        if result.is_safe:
            logger.debug(
                f"Frame {result.frame_number}: no violations "
                f"({result.rules_evaluated} rule(s), {result.evaluation_time_ms:.2f} ms)."
            )
            return

        highest = result.highest_severity
        message = (
            f"Frame {result.frame_number}: {len(result)} violation(s), "
            f"highest severity {highest!s} "
            f"({result.rules_evaluated} rule(s), {result.evaluation_time_ms:.2f} ms)."
        )

        if highest is not None and highest >= Severity.HIGH:
            logger.warning(message)
        else:
            logger.info(message)

    def add_rule(self, rule: BaseRule, replace: bool = False) -> None:
        """Register an additional rule with the underlying registry.

        Args:
            rule: The rule to register.
            replace: Whether to overwrite an existing rule of the same
                name.
        """
        self.registry.register(rule, replace=replace)

    def enabled_rule_names(self) -> List[str]:
        """Return the names of the rules that will be evaluated, in order."""
        return [rule.name for rule in self.registry.enabled_rules()]
