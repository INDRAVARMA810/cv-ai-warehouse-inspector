"""Conversion of rule violations into managed alerts.

A rule engine reports violations *per frame*: an object standing in a
danger zone produces one violation every frame, thirty times a second.
Forwarding those directly to operators would be unusable. This module
turns that stream into a small number of durable incidents by applying
four policies:

* **Grouping** — violations sharing an identity (rule + track + zone)
  are treated as one incident.
* **Deduplication** — an ongoing incident updates its existing alert
  instead of raising a new one.
* **Cooldown** — a re-raise after an incident closes is suppressed
  until a timeout elapses, preventing flapping.
* **Escalation** — an incident that persists or worsens has its
  urgency raised.

The engine consumes rule results structurally (duck-typed), so it does
not depend on the rule layer's concrete types.
"""

import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from app.alerts.alert import Alert, AlertCategory, AlertLevel
from app.alerts.cooldown import CooldownTracker
from app.logger import logger


@dataclass
class AlertEngineConfig:
    """Tuning parameters for :class:`AlertEngine`.

    Attributes:
        cooldown_seconds: How long a closed incident's key stays
            suppressed before the same hazard may raise a fresh alert.
        escalate_after_occurrences: Observation count at which an
            incident escalates one level. ``0`` disables count-based
            escalation.
        escalate_after_seconds: Sustained duration, in seconds, after
            which an incident escalates one level. ``0`` disables
            duration-based escalation.
        max_level: Ceiling that escalation will not exceed.
        group_by_zone: Whether the zone named in a violation's metadata
            forms part of the incident identity. When ``True``, the same
            object entering two different zones raises two incidents.
        min_level: Violations below this level are discarded rather than
            becoming alerts.
    """

    cooldown_seconds: float = 30.0
    escalate_after_occurrences: int = 30
    escalate_after_seconds: float = 15.0
    max_level: AlertLevel = AlertLevel.CRITICAL
    group_by_zone: bool = True
    min_level: AlertLevel = AlertLevel.INFO


class AlertEngine:
    """Turns per-frame rule violations into durable, managed alerts.

    The engine holds the currently-open alert for each incident key.
    Alerts are held **by reference**, so lifecycle changes made
    elsewhere (an operator acknowledging or resolving via
    :class:`~app.alerts.alert_manager.AlertManager`) are visible here
    without any synchronization step.

    Attributes:
        config: The tuning parameters in effect.
        cooldown: The tracker enforcing re-raise suppression.
    """

    def __init__(
        self,
        config: Optional[AlertEngineConfig] = None,
        cooldown: Optional[CooldownTracker] = None,
    ) -> None:
        """Configure the engine.

        Args:
            config: Tuning parameters. Defaults to
                :class:`AlertEngineConfig`.
            cooldown: Cooldown tracker to use. Defaults to one built
                from ``config.cooldown_seconds``.
        """
        self.config = config or AlertEngineConfig()
        self.cooldown = cooldown or CooldownTracker(
            default_timeout=self.config.cooldown_seconds
        )
        self._open_alerts: Dict[str, Alert] = {}
        # Persistence escalations already applied per incident key. Each
        # further step requires another full threshold interval, so a
        # sustained hazard climbs gradually instead of racing to
        # CRITICAL on consecutive frames.
        self._escalation_steps: Dict[str, int] = {}

    @property
    def open_alerts(self) -> Dict[str, Alert]:
        """Return the currently-open alerts, keyed by incident key."""
        return dict(self._open_alerts)

    def process(
        self,
        rule_result: Any,
        now: Optional[float] = None,
    ) -> List[Alert]:
        """Convert one frame's rule result into alerts.

        Args:
            rule_result: A
                :class:`~app.rules.rule_result.RuleResult`, or any
                object exposing a ``violations`` sequence.
            now: Timestamp to evaluate against. Defaults to the current
                time. Supplying it keeps a whole frame on one consistent
                clock reading.

        Returns:
            Only the **newly raised** alerts. Alerts that already
            existed are updated in place and are not returned, so
            callers can treat the return value as "things that just
            started happening".
        """
        current = time.time() if now is None else now

        violations = getattr(rule_result, "violations", None)
        if violations is None:
            logger.warning(
                "AlertEngine.process() received an object without a "
                "'violations' attribute; skipping."
            )
            return []

        self._release_closed_alerts(current)

        new_alerts: List[Alert] = []

        for violation in violations:
            level = AlertLevel.from_severity(
                getattr(violation, "severity", AlertLevel.INFO)
            )
            if level < self.config.min_level:
                continue

            key = self._incident_key(violation)
            existing = self._open_alerts.get(key)
            if existing is not None:
                self._update_existing(existing, violation, level, current, key)
                continue

            if self.cooldown.is_cooling_down(key, now=current):
                logger.debug(
                    f"Suppressed alert for '{key}': cooling down for another "
                    f"{self.cooldown.remaining(key, now=current):.1f}s."
                )
                continue

            alert = self._create_alert(violation, level, current)
            self._open_alerts[key] = alert
            new_alerts.append(alert)

            logger.info(
                f"Alert raised [{alert.level!s}] {alert.rule_name}: {alert.message}"
            )

        return new_alerts

    def _incident_key(self, violation: Any) -> str:
        """Build the identity that groups violations into one incident.

        Args:
            violation: The violation to key.

        Returns:
            A stable string key combining the rule, the responsible
            track, and — when configured — the zone involved.
        """
        rule_name = str(getattr(violation, "rule_name", "unknown"))
        track_id = getattr(violation, "track_id", None)
        metadata = getattr(violation, "metadata", None) or {}

        parts = [rule_name, f"track={track_id}"]

        if self.config.group_by_zone:
            zone_name = metadata.get("zone_name")
            if zone_name:
                parts.append(f"zone={zone_name}")

        # Pairwise rules name two participants; key on both so the pair
        # is one incident regardless of which was reported first.
        track_ids = metadata.get("track_ids")
        if track_id is None and track_ids:
            parts.append("pair=" + ",".join(str(t) for t in sorted(map(str, track_ids))))

        return "|".join(parts)

    def _create_alert(
        self, violation: Any, level: AlertLevel, now: float
    ) -> Alert:
        """Build a new alert from a violation.

        Args:
            violation: The violation that triggered the alert.
            level: The alert's initial urgency.
            now: Timestamp to stamp the alert with.

        Returns:
            The new alert.
        """
        rule_name = str(getattr(violation, "rule_name", "unknown"))
        metadata = dict(getattr(violation, "metadata", None) or {})

        return Alert(
            rule_name=rule_name,
            level=level,
            category=AlertCategory.from_rule_name(rule_name),
            message=str(getattr(violation, "description", "")) or rule_name,
            timestamp=now,
            first_seen=now,
            last_seen=now,
            track_id=getattr(violation, "track_id", None),
            frame_number=getattr(violation, "frame_number", None),
            bounding_box=getattr(violation, "bounding_box", None),
            metadata=metadata,
        )

    def _update_existing(
        self, alert: Alert, violation: Any, level: AlertLevel, now: float, key: str
    ) -> None:
        """Fold a repeat observation into an existing alert.

        Args:
            alert: The open alert for this incident.
            violation: The newly observed violation.
            level: The observation's urgency.
            now: Timestamp of the observation.
            key: The incident key, used to track escalation steps.
        """
        alert.register_occurrence(
            now=now,
            frame_number=getattr(violation, "frame_number", None),
            bounding_box=getattr(violation, "bounding_box", None),
        )

        # The hazard itself became more serious.
        if level > alert.level:
            alert.escalate(level, reason="violation severity increased")
            logger.info(
                f"Alert {alert.alert_id[:8]} escalated to {alert.level!s} "
                f"(severity increased)."
            )
            return

        escalated_to = self._escalation_for_persistence(alert, now, key)
        if escalated_to is not None and alert.escalate(
            escalated_to, reason="hazard persisted"
        ):
            self._escalation_steps[key] = self._escalation_steps.get(key, 0) + 1
            logger.info(
                f"Alert {alert.alert_id[:8]} escalated to {alert.level!s} "
                f"(persisted {alert.duration:.1f}s / "
                f"{alert.occurrence_count} occurrences)."
            )

    def _escalation_for_persistence(
        self, alert: Alert, now: float, key: str
    ) -> Optional[AlertLevel]:
        """Determine whether a persisting alert should escalate.

        Each successive step requires another full threshold interval,
        so an ongoing hazard climbs one level per interval rather than
        one level per frame.

        Args:
            alert: The alert to assess.
            now: The current timestamp.
            key: The incident key, used to look up steps already applied.

        Returns:
            The level to escalate to, or ``None`` to leave it unchanged.
        """
        if alert.level >= self.config.max_level:
            return None

        steps_taken = self._escalation_steps.get(key, 0)
        next_step = steps_taken + 1

        by_count = (
            self.config.escalate_after_occurrences > 0
            and alert.occurrence_count
            >= self.config.escalate_after_occurrences * next_step
        )
        by_duration = (
            self.config.escalate_after_seconds > 0
            and (now - (alert.first_seen or now))
            >= self.config.escalate_after_seconds * next_step
        )

        if not (by_count or by_duration):
            return None

        # Escalate exactly one step, so a long-running medium hazard
        # does not jump straight to critical.
        higher = [level for level in AlertLevel if level > alert.level]
        if not higher:
            return None

        return min(min(higher), self.config.max_level)

    def _release_closed_alerts(self, now: float) -> None:
        """Stop tracking alerts that are no longer open.

        When an alert is resolved or expired elsewhere, its incident key
        is freed and placed on cooldown, so the same hazard does not
        immediately re-raise on the very next frame.

        Args:
            now: The current timestamp.
        """
        closed = [
            key for key, alert in self._open_alerts.items() if not alert.is_open
        ]

        for key in closed:
            del self._open_alerts[key]
            self._escalation_steps.pop(key, None)
            self.cooldown.trigger(key, now=now)
            logger.debug(f"Incident '{key}' closed; cooldown started.")

    def resolve_stale(
        self, max_idle_seconds: float = 5.0, now: Optional[float] = None
    ) -> List[Alert]:
        """Resolve open alerts whose hazard has stopped being observed.

        A hazard that clears produces no further violations, so its
        alert would otherwise stay open forever. Call this once per
        frame, or on a timer, to close them out.

        Args:
            max_idle_seconds: How long an alert may go unobserved before
                it is considered cleared.
            now: Timestamp to evaluate against. Defaults to now.

        Returns:
            The alerts that were resolved.
        """
        current = time.time() if now is None else now
        resolved: List[Alert] = []

        for key, alert in list(self._open_alerts.items()):
            if alert.age(now=current) < max_idle_seconds:
                continue

            if alert.resolve(now=current):
                resolved.append(alert)
                logger.info(
                    f"Alert {alert.alert_id[:8]} auto-resolved after "
                    f"{max_idle_seconds}s without recurrence."
                )

            del self._open_alerts[key]
            self._escalation_steps.pop(key, None)
            self.cooldown.trigger(key, now=current)

        return resolved

    def reset(self) -> None:
        """Discard all open-incident and cooldown state.

        Call this when switching video sources so incidents do not carry
        over between unrelated streams.
        """
        self._open_alerts.clear()
        self._escalation_steps.clear()
        self.cooldown.clear()
        logger.info("Alert engine reset; open incidents and cooldowns cleared.")
