"""Notification routing policy — decisions only, no delivery.

This module answers one question: *given this alert, which channels
should be notified, and why?* It contains **no delivery code** and has
no I/O, no network access, and no third-party clients. Nothing here
sends an email, an SMS, a webhook, or a sound.

That separation is deliberate. Routing policy is business logic that
must be unit-testable and auditable; delivery is infrastructure with
credentials, retries, and rate limits. A future dispatcher will consume
the :class:`NotificationDecision` objects produced here and perform the
actual sending — at which point this module needs no changes.
"""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from app.alerts.alert import Alert, AlertCategory, AlertLevel
from app.logger import logger


class NotificationChannel(str, Enum):
    """A destination an alert can be routed to.

    Declaring the full set now — including channels with no
    implementation — keeps policy configuration stable as delivery
    backends are added one at a time.
    """

    DASHBOARD = "dashboard"
    EMAIL = "email"
    SMS = "sms"
    AUDIO = "audio"
    WEBHOOK = "webhook"


@dataclass(frozen=True)
class NotificationRule:
    """One routing rule: which alerts go to which channels.

    An alert matches when it satisfies *every* constraint set on the
    rule. Unset constraints match everything.

    Attributes:
        name: Human-readable identifier for the rule.
        channels: Channels to notify when this rule matches.
        min_level: Minimum urgency required to match.
        categories: Categories this rule applies to. Empty matches all.
        rule_names: Originating rule names this applies to. Empty
            matches all.
        require_unacknowledged: When ``True``, the rule stops matching
            once an operator has acknowledged the alert — useful for
            escalation paths that should go quiet on acknowledgement.
        throttle_seconds: Minimum spacing between notifications for the
            same alert through this rule. ``0`` disables throttling.
            Enforced by the dispatcher, not here.
        enabled: Whether the rule participates in routing.
    """

    name: str
    channels: Tuple[NotificationChannel, ...]
    min_level: AlertLevel = AlertLevel.INFO
    categories: Tuple[AlertCategory, ...] = ()
    rule_names: Tuple[str, ...] = ()
    require_unacknowledged: bool = False
    throttle_seconds: float = 0.0
    enabled: bool = True

    def matches(self, alert: Alert) -> bool:
        """Return whether this rule applies to an alert.

        Args:
            alert: The alert to test.

        Returns:
            ``True`` if every constraint is satisfied.
        """
        if not self.enabled:
            return False

        if alert.level < self.min_level:
            return False

        if self.categories and alert.category not in self.categories:
            return False

        if self.rule_names and alert.rule_name not in self.rule_names:
            return False

        if self.require_unacknowledged and alert.acknowledged:
            return False

        return True


@dataclass
class NotificationDecision:
    """The routing outcome for a single alert.

    This is a *description* of what should happen, not a record that it
    did. A dispatcher consumes it; nothing here acts on it.

    Attributes:
        alert_id: The alert this decision concerns.
        channels: Channels that should be notified, deduplicated.
        matched_rules: Names of the policy rules that matched.
        reasons: Human-readable justification per matched rule, for
            audit trails and debugging.
        decided_at: Unix timestamp (seconds) the decision was made.
    """

    alert_id: str
    channels: Set[NotificationChannel] = field(default_factory=set)
    matched_rules: List[str] = field(default_factory=list)
    reasons: List[str] = field(default_factory=list)
    decided_at: float = field(default_factory=time.time)

    @property
    def should_notify(self) -> bool:
        """Whether any channel should be notified at all."""
        return bool(self.channels)

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serializable representation of the decision."""
        return {
            "alert_id": self.alert_id,
            "channels": sorted(channel.value for channel in self.channels),
            "matched_rules": list(self.matched_rules),
            "reasons": list(self.reasons),
            "decided_at": self.decided_at,
            "should_notify": self.should_notify,
        }


class NotificationPolicy:
    """Decides which channels an alert should be routed to.

    Holds an ordered set of :class:`NotificationRule` objects and
    evaluates them all against each alert, unioning the channels of
    every rule that matches.
    """

    def __init__(self, rules: Optional[Sequence[NotificationRule]] = None) -> None:
        """Initialize the policy.

        Args:
            rules: The routing rules. Defaults to an empty policy, which
                routes nothing.
        """
        self._rules: List[NotificationRule] = list(rules or ())

    def __len__(self) -> int:
        """Return the number of configured rules."""
        return len(self._rules)

    @property
    def rules(self) -> List[NotificationRule]:
        """Return the configured rules, in evaluation order."""
        return list(self._rules)

    def add_rule(self, rule: NotificationRule) -> None:
        """Append a routing rule.

        Args:
            rule: The rule to add.
        """
        self._rules.append(rule)
        logger.debug(
            f"Notification rule '{rule.name}' added "
            f"(min_level={rule.min_level!s}, "
            f"channels={[c.value for c in rule.channels]})"
        )

    def remove_rule(self, name: str) -> bool:
        """Remove a routing rule by name.

        Args:
            name: Name of the rule to remove.

        Returns:
            ``True`` if a rule was removed, ``False`` otherwise.
        """
        before = len(self._rules)
        self._rules = [rule for rule in self._rules if rule.name != name]

        removed = len(self._rules) < before
        if not removed:
            logger.warning(f"Cannot remove unknown notification rule '{name}'.")

        return removed

    def decide(self, alert: Alert) -> NotificationDecision:
        """Determine which channels an alert should reach.

        Args:
            alert: The alert to route.

        Returns:
            The routing decision. Its ``channels`` set is empty when no
            rule matches, which means "do not notify".
        """
        decision = NotificationDecision(alert_id=alert.alert_id)

        for rule in self._rules:
            if not rule.matches(alert):
                continue

            decision.channels.update(rule.channels)
            decision.matched_rules.append(rule.name)
            decision.reasons.append(
                f"'{rule.name}' matched: level {alert.level!s} >= "
                f"{rule.min_level!s}, category '{alert.category.value}'"
            )

        return decision

    def decide_many(self, alerts: Sequence[Alert]) -> List[NotificationDecision]:
        """Route a batch of alerts.

        Args:
            alerts: The alerts to route.

        Returns:
            One decision per alert, in the same order.
        """
        return [self.decide(alert) for alert in alerts]


def build_default_policy() -> NotificationPolicy:
    """Create a sensible starting policy for a warehouse deployment.

    The tiers escalate with urgency: everything is visible on the
    dashboard, serious hazards additionally sound locally and notify
    supervisors, and critical hazards page out over SMS.

    Returns:
        A ready-to-use :class:`NotificationPolicy`.
    """
    return NotificationPolicy(
        [
            NotificationRule(
                name="dashboard-all",
                channels=(NotificationChannel.DASHBOARD,),
                min_level=AlertLevel.INFO,
            ),
            NotificationRule(
                name="audio-on-site",
                channels=(NotificationChannel.AUDIO,),
                min_level=AlertLevel.HIGH,
                require_unacknowledged=True,
            ),
            NotificationRule(
                name="supervisor-email",
                channels=(NotificationChannel.EMAIL,),
                min_level=AlertLevel.HIGH,
                throttle_seconds=300.0,
            ),
            NotificationRule(
                name="critical-escalation",
                channels=(NotificationChannel.SMS, NotificationChannel.WEBHOOK),
                min_level=AlertLevel.CRITICAL,
                throttle_seconds=60.0,
            ),
        ]
    )
