"""Alert lifecycle ownership and querying.

:class:`AlertManager` is the system of record for alerts while the
application is running. It owns the transitions an alert can undergo —
acknowledged, resolved, expired — and answers questions about the
current state of the floor.

Responsibilities are split deliberately:
:class:`~app.alerts.alert_engine.AlertEngine` decides *when* an alert
should exist, the manager tracks *what state it is in*, and
:class:`~app.alerts.alert_history.AlertHistory` remembers *what has
happened*. The manager wires them together without any of them
depending on each other.
"""

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

from app.alerts.alert import Alert, AlertCategory, AlertLevel, AlertStatus
from app.alerts.alert_engine import AlertEngine, AlertEngineConfig
from app.alerts.alert_history import AlertHistory, AlertStatistics
from app.alerts.notification_policy import (
    NotificationDecision,
    NotificationPolicy,
    build_default_policy,
)
from app.logger import logger


@dataclass
class AlertSummary:
    """A snapshot count of alerts by state.

    Attributes:
        total: Every alert the manager currently holds.
        active: Alerts awaiting operator attention.
        acknowledged: Alerts seen but not yet resolved.
        resolved: Alerts whose hazard has cleared.
        expired: Alerts that aged out without resolution.
        by_level: Count of open alerts per urgency level.
        highest_open_level: Most urgent level among open alerts.
    """

    total: int = 0
    active: int = 0
    acknowledged: int = 0
    resolved: int = 0
    expired: int = 0
    by_level: Dict[str, int] = field(default_factory=dict)
    highest_open_level: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serializable representation of the summary."""
        return {
            "total": self.total,
            "active": self.active,
            "acknowledged": self.acknowledged,
            "resolved": self.resolved,
            "expired": self.expired,
            "by_level": dict(self.by_level),
            "highest_open_level": self.highest_open_level,
        }


class AlertManager:
    """Owns alert state and coordinates the alert subsystem.

    Typical per-frame use::

        alerts = manager.process(rule_result)
        for alert in alerts:
            decision = manager.route(alert)

    Attributes:
        engine: Converts rule violations into alerts.
        history: Rolling record of past alerts.
        policy: Notification routing policy.
    """

    def __init__(
        self,
        engine: Optional[AlertEngine] = None,
        history: Optional[AlertHistory] = None,
        policy: Optional[NotificationPolicy] = None,
        auto_resolve_after: float = 5.0,
        expire_after: float = 3600.0,
    ) -> None:
        """Configure the manager.

        Args:
            engine: Alert engine to use. Defaults to a new engine with
                default configuration.
            history: History buffer to use. Defaults to a new buffer.
            policy: Notification policy. Defaults to
                :func:`~app.alerts.notification_policy.build_default_policy`.
            auto_resolve_after: Seconds a hazard may go unobserved
                before its alert is automatically resolved. ``0``
                disables auto-resolution.
            expire_after: Seconds an unresolved alert may persist before
                it is expired. ``0`` disables expiry.

        Raises:
            ValueError: If either timeout is negative.
        """
        if auto_resolve_after < 0:
            raise ValueError(
                f"auto_resolve_after must be non-negative, got {auto_resolve_after}"
            )
        if expire_after < 0:
            raise ValueError(f"expire_after must be non-negative, got {expire_after}")

        self.engine = engine or AlertEngine()
        self.history = history or AlertHistory()
        self.policy = policy or build_default_policy()
        self.auto_resolve_after = auto_resolve_after
        self.expire_after = expire_after

        self._alerts: Dict[str, Alert] = {}

    def __len__(self) -> int:
        """Return the total number of alerts held."""
        return len(self._alerts)

    def __contains__(self, alert_id: object) -> bool:
        """Return whether an alert ID is held by the manager."""
        return alert_id in self._alerts

    def process(self, rule_result: Any, now: Optional[float] = None) -> List[Alert]:
        """Turn a frame's rule result into alerts and record them.

        Also performs the periodic maintenance the alert lifecycle
        needs — auto-resolving cleared hazards and expiring stale
        alerts — so callers only need this one call per frame.

        Args:
            rule_result: The frame's rule evaluation.
            now: Timestamp to evaluate against. Defaults to now.

        Returns:
            The newly raised alerts. Ongoing incidents are updated in
            place and are not returned.
        """
        current = time.time() if now is None else now

        new_alerts = self.engine.process(rule_result, now=current)

        for alert in new_alerts:
            self._alerts[alert.alert_id] = alert
            self.history.record(alert)

        if self.auto_resolve_after > 0:
            self.engine.resolve_stale(
                max_idle_seconds=self.auto_resolve_after, now=current
            )

        if self.expire_after > 0:
            self.expire_stale(now=current)

        return new_alerts

    def route(self, alert: Alert) -> NotificationDecision:
        """Decide which channels an alert should reach.

        This returns a decision only; nothing is delivered. See
        :mod:`app.alerts.notification_policy`.

        Args:
            alert: The alert to route.

        Returns:
            The routing decision.
        """
        return self.policy.decide(alert)

    def route_many(self, alerts: Sequence[Alert]) -> List[NotificationDecision]:
        """Decide routing for several alerts.

        Args:
            alerts: The alerts to route.

        Returns:
            One decision per alert, in the same order.
        """
        return self.policy.decide_many(alerts)

    def add(self, alert: Alert) -> Alert:
        """Register an externally-created alert.

        Args:
            alert: The alert to register.

        Returns:
            The registered alert.
        """
        self._alerts[alert.alert_id] = alert
        self.history.record(alert)
        return alert

    def get(self, alert_id: str) -> Optional[Alert]:
        """Return an alert by ID.

        Args:
            alert_id: The identifier to look up.

        Returns:
            The alert, or ``None`` if unknown.
        """
        return self._alerts.get(alert_id)

    def acknowledge(
        self,
        alert_id: str,
        by: Optional[str] = None,
        now: Optional[float] = None,
    ) -> bool:
        """Mark an alert as seen by an operator.

        Args:
            alert_id: The alert to acknowledge.
            by: Identifier of the acknowledging operator.
            now: Timestamp of the acknowledgement.

        Returns:
            ``True`` if the alert transitioned, ``False`` if it is
            unknown or was not in an acknowledgeable state.
        """
        alert = self._alerts.get(alert_id)

        if alert is None:
            logger.warning(f"Cannot acknowledge unknown alert '{alert_id}'.")
            return False

        if not alert.acknowledge(by=by, now=now):
            return False

        logger.info(
            f"Alert {alert.alert_id[:8]} acknowledged"
            f"{f' by {by}' if by else ''}."
        )
        return True

    def resolve(self, alert_id: str, now: Optional[float] = None) -> bool:
        """Mark an alert's hazard as cleared.

        Args:
            alert_id: The alert to resolve.
            now: Timestamp of resolution.

        Returns:
            ``True`` if the alert transitioned, ``False`` if it is
            unknown or already terminal.
        """
        alert = self._alerts.get(alert_id)

        if alert is None:
            logger.warning(f"Cannot resolve unknown alert '{alert_id}'.")
            return False

        if not alert.resolve(now=now):
            return False

        logger.info(f"Alert {alert.alert_id[:8]} resolved.")
        return True

    def acknowledge_all(
        self, by: Optional[str] = None, now: Optional[float] = None
    ) -> int:
        """Acknowledge every currently active alert.

        Args:
            by: Identifier of the acknowledging operator.
            now: Timestamp of the acknowledgement.

        Returns:
            The number of alerts acknowledged.
        """
        count = sum(
            1 for alert in self.active_alerts() if alert.acknowledge(by=by, now=now)
        )

        if count:
            logger.info(f"Acknowledged {count} active alert(s).")

        return count

    def expire_stale(self, now: Optional[float] = None) -> List[Alert]:
        """Expire open alerts older than the configured lifetime.

        Args:
            now: Timestamp to evaluate against. Defaults to now.

        Returns:
            The alerts that were expired.
        """
        if self.expire_after <= 0:
            return []

        current = time.time() if now is None else now
        expired: List[Alert] = []

        for alert in self._alerts.values():
            if not alert.is_open:
                continue
            if (current - alert.timestamp) < self.expire_after:
                continue
            if alert.expire(now=current):
                expired.append(alert)

        if expired:
            logger.info(f"Expired {len(expired)} stale alert(s).")

        return expired

    def all_alerts(self) -> List[Alert]:
        """Return every alert held, newest first."""
        return sorted(
            self._alerts.values(), key=lambda alert: alert.timestamp, reverse=True
        )

    def active_alerts(self) -> List[Alert]:
        """Return alerts awaiting operator attention, most urgent first."""
        return self._by_status(AlertStatus.ACTIVE)

    def acknowledged_alerts(self) -> List[Alert]:
        """Return acknowledged but unresolved alerts, most urgent first."""
        return self._by_status(AlertStatus.ACKNOWLEDGED)

    def resolved_alerts(self) -> List[Alert]:
        """Return resolved alerts, most urgent first."""
        return self._by_status(AlertStatus.RESOLVED)

    def expired_alerts(self) -> List[Alert]:
        """Return expired alerts, most urgent first."""
        return self._by_status(AlertStatus.EXPIRED)

    def open_alerts(self) -> List[Alert]:
        """Return every alert still representing a live concern."""
        return sorted(
            (alert for alert in self._alerts.values() if alert.is_open),
            key=lambda alert: (alert.level, alert.timestamp),
            reverse=True,
        )

    def _by_status(self, status: AlertStatus) -> List[Alert]:
        """Return alerts in a given status, most urgent first.

        Args:
            status: The status to filter by.

        Returns:
            The matching alerts.
        """
        return sorted(
            (alert for alert in self._alerts.values() if alert.status == status),
            key=lambda alert: (alert.level, alert.timestamp),
            reverse=True,
        )

    def query(
        self,
        status: Optional[AlertStatus] = None,
        level: Optional[AlertLevel] = None,
        min_level: Optional[AlertLevel] = None,
        category: Optional[AlertCategory] = None,
        rule_name: Optional[str] = None,
        track_id: Optional[int] = None,
        since: Optional[float] = None,
        until: Optional[float] = None,
    ) -> List[Alert]:
        """Return alerts matching every supplied criterion.

        Unset criteria are ignored, so calling with no arguments returns
        every alert.

        Args:
            status: Match this lifecycle status.
            level: Match this exact urgency level.
            min_level: Match this urgency level or higher.
            category: Match this category.
            rule_name: Match this originating rule name.
            track_id: Match this track identity.
            since: Only alerts at or after this timestamp.
            until: Only alerts at or before this timestamp.

        Returns:
            The matching alerts, most urgent first.
        """
        results: List[Alert] = []

        for alert in self._alerts.values():
            if status is not None and alert.status != status:
                continue
            if level is not None and alert.level != level:
                continue
            if min_level is not None and alert.level < min_level:
                continue
            if category is not None and alert.category != category:
                continue
            if rule_name is not None and alert.rule_name != rule_name:
                continue
            if track_id is not None and alert.track_id != track_id:
                continue
            if since is not None and alert.timestamp < since:
                continue
            if until is not None and alert.timestamp > until:
                continue

            results.append(alert)

        return sorted(results, key=lambda a: (a.level, a.timestamp), reverse=True)

    def summary(self) -> AlertSummary:
        """Return a snapshot count of alerts by state.

        Returns:
            The current :class:`AlertSummary`.
        """
        alerts = list(self._alerts.values())
        open_alerts = [alert for alert in alerts if alert.is_open]

        by_level: Dict[str, int] = {}
        for alert in open_alerts:
            key = str(alert.level)
            by_level[key] = by_level.get(key, 0) + 1

        return AlertSummary(
            total=len(alerts),
            active=sum(1 for a in alerts if a.status == AlertStatus.ACTIVE),
            acknowledged=sum(1 for a in alerts if a.status == AlertStatus.ACKNOWLEDGED),
            resolved=sum(1 for a in alerts if a.status == AlertStatus.RESOLVED),
            expired=sum(1 for a in alerts if a.status == AlertStatus.EXPIRED),
            by_level=by_level,
            highest_open_level=(
                str(max(alert.level for alert in open_alerts)) if open_alerts else None
            ),
        )

    def statistics(self) -> AlertStatistics:
        """Return aggregate statistics over the recorded history.

        Returns:
            The history's :class:`AlertStatistics`.
        """
        return self.history.statistics()

    def purge_closed(self) -> int:
        """Drop terminal alerts from the manager's working set.

        The history retains them, so this only bounds the manager's live
        state — it does not lose the audit trail.

        Returns:
            The number of alerts dropped.
        """
        closed = [
            alert_id
            for alert_id, alert in self._alerts.items()
            if alert.status.is_terminal
        ]

        for alert_id in closed:
            del self._alerts[alert_id]

        if closed:
            logger.debug(f"Purged {len(closed)} closed alert(s) from working set.")

        return len(closed)

    def reset(self) -> None:
        """Discard all alerts, history and engine state.

        Call this when switching video sources.
        """
        self._alerts.clear()
        self.history.clear()
        self.engine.reset()
        logger.info("Alert manager reset; all alerts and history discarded.")


def build_default_manager() -> AlertManager:
    """Create an alert manager with the project's standard configuration.

    Returns:
        A ready-to-use :class:`AlertManager`.
    """
    return AlertManager(
        engine=AlertEngine(AlertEngineConfig()),
        history=AlertHistory(max_length=1000),
        policy=build_default_policy(),
    )
