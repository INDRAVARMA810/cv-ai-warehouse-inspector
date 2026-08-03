"""Alert management.

Turns the rule engine's per-frame violations into durable, de-duplicated
incidents with an operational lifecycle.

The subsystem separates four concerns so each can change independently:

* :class:`AlertEngine` decides *when* an alert should exist — grouping,
  deduplication, cooldown and escalation.
* :class:`AlertManager` owns *what state* each alert is in, and is the
  entry point the rest of the application uses.
* :class:`AlertHistory` remembers *what has happened*, with search,
  filtering, export and statistics.
* :class:`NotificationPolicy` decides *who should be told* — routing
  decisions only, with no delivery code anywhere in this package.
"""

from app.alerts.alert import (
    Alert,
    AlertCategory,
    AlertLevel,
    AlertStatus,
)
from app.alerts.alert_engine import AlertEngine, AlertEngineConfig
from app.alerts.alert_history import AlertHistory, AlertStatistics
from app.alerts.alert_manager import AlertManager, AlertSummary, build_default_manager
from app.alerts.cooldown import CooldownTracker
from app.alerts.notification_policy import (
    NotificationChannel,
    NotificationDecision,
    NotificationPolicy,
    NotificationRule,
    build_default_policy,
)

__all__ = [
    "Alert",
    "AlertLevel",
    "AlertCategory",
    "AlertStatus",
    "AlertEngine",
    "AlertEngineConfig",
    "AlertManager",
    "AlertSummary",
    "build_default_manager",
    "AlertHistory",
    "AlertStatistics",
    "CooldownTracker",
    "NotificationPolicy",
    "NotificationRule",
    "NotificationChannel",
    "NotificationDecision",
    "build_default_policy",
]
