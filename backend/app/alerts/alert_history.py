"""Rolling in-memory alert history with search, filtering and export.

Retains a bounded window of past alerts so operators and reports can
answer questions like "what happened in the last hour?" or "which rule
fires most?" without a database.

The window is deliberately bounded: a long-running shift would
otherwise grow this list without limit. Durable, unbounded retention is
a database concern and is intentionally out of scope here — this is a
recent-activity buffer, not a system of record.
"""

import csv
import io
import json
from collections import Counter, deque
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, Iterator, List, Optional, Sequence, Tuple

from app.alerts.alert import Alert, AlertCategory, AlertLevel, AlertStatus
from app.logger import logger


@dataclass
class AlertStatistics:
    """Aggregate figures describing a set of alerts.

    Attributes:
        total: Number of alerts summarized.
        by_level: Count per urgency level, keyed by level name.
        by_category: Count per category, keyed by category value.
        by_status: Count per lifecycle status, keyed by status value.
        by_rule: Count per originating rule name.
        top_tracks: The most frequently offending track IDs, as
            ``(track_id, count)`` pairs, most frequent first.
        escalated_count: How many alerts rose above their initial level.
        acknowledged_count: How many alerts an operator acknowledged.
        resolved_count: How many alerts reached a resolved state.
        total_occurrences: Sum of every alert's observation count.
        time_span: Seconds between the oldest and newest alert.
        first_timestamp: Timestamp of the oldest alert, if any.
        last_timestamp: Timestamp of the newest alert, if any.
    """

    total: int = 0
    by_level: Dict[str, int] = field(default_factory=dict)
    by_category: Dict[str, int] = field(default_factory=dict)
    by_status: Dict[str, int] = field(default_factory=dict)
    by_rule: Dict[str, int] = field(default_factory=dict)
    top_tracks: List[Tuple[int, int]] = field(default_factory=list)
    escalated_count: int = 0
    acknowledged_count: int = 0
    resolved_count: int = 0
    total_occurrences: int = 0
    time_span: float = 0.0
    first_timestamp: Optional[float] = None
    last_timestamp: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serializable representation of the statistics."""
        return {
            "total": self.total,
            "by_level": dict(self.by_level),
            "by_category": dict(self.by_category),
            "by_status": dict(self.by_status),
            "by_rule": dict(self.by_rule),
            "top_tracks": [list(pair) for pair in self.top_tracks],
            "escalated_count": self.escalated_count,
            "acknowledged_count": self.acknowledged_count,
            "resolved_count": self.resolved_count,
            "total_occurrences": self.total_occurrences,
            "time_span": self.time_span,
            "first_timestamp": self.first_timestamp,
            "last_timestamp": self.last_timestamp,
        }


#: Column order used by :meth:`AlertHistory.to_csv`.
_CSV_COLUMNS = (
    "alert_id",
    "timestamp",
    "rule_name",
    "level",
    "category",
    "status",
    "track_id",
    "frame_number",
    "occurrence_count",
    "acknowledged",
    "acknowledged_by",
    "resolved",
    "duration",
    "was_escalated",
    "message",
)


class AlertHistory:
    """A bounded, queryable log of alerts.

    Attributes:
        max_length: Maximum alerts retained; the oldest are discarded
            as new ones arrive.
    """

    def __init__(self, max_length: int = 1000) -> None:
        """Initialize the history buffer.

        Args:
            max_length: Maximum number of alerts to retain.

        Raises:
            ValueError: If ``max_length`` is not positive.
        """
        if max_length <= 0:
            raise ValueError(f"max_length must be positive, got {max_length}")

        self.max_length = max_length
        self._alerts: Deque[Alert] = deque(maxlen=max_length)

    def __len__(self) -> int:
        """Return the number of alerts currently retained."""
        return len(self._alerts)

    def __iter__(self) -> Iterator[Alert]:
        """Iterate over retained alerts, oldest first."""
        return iter(self._alerts)

    @property
    def is_empty(self) -> bool:
        """Whether no alerts have been recorded."""
        return len(self._alerts) == 0

    def record(self, alert: Alert) -> None:
        """Add an alert to the history.

        The alert is stored by reference, so later lifecycle changes
        (acknowledgement, resolution, escalation) are reflected here
        without needing to re-record it.

        Args:
            alert: The alert to record.
        """
        self._alerts.append(alert)

        if len(self._alerts) == self.max_length:
            logger.debug(
                f"Alert history at capacity ({self.max_length}); "
                f"oldest entries are being discarded."
            )

    def record_many(self, alerts: Sequence[Alert]) -> None:
        """Add several alerts to the history.

        Args:
            alerts: The alerts to record.
        """
        for alert in alerts:
            self.record(alert)

    def all(self, newest_first: bool = True) -> List[Alert]:
        """Return every retained alert.

        Args:
            newest_first: Whether to return the newest alert first.

        Returns:
            The retained alerts.
        """
        alerts = list(self._alerts)
        return list(reversed(alerts)) if newest_first else alerts

    def recent(self, count: int = 10) -> List[Alert]:
        """Return the most recent alerts, newest first.

        Args:
            count: Maximum number of alerts to return.

        Returns:
            Up to ``count`` alerts.
        """
        if count <= 0:
            return []
        return list(reversed(list(self._alerts)[-count:]))

    def get(self, alert_id: str) -> Optional[Alert]:
        """Return a recorded alert by ID.

        Args:
            alert_id: The alert identifier to look up.

        Returns:
            The alert, or ``None`` if it is not in the retained window.
        """
        for alert in self._alerts:
            if alert.alert_id == alert_id:
                return alert
        return None

    def filter(
        self,
        level: Optional[AlertLevel] = None,
        min_level: Optional[AlertLevel] = None,
        category: Optional[AlertCategory] = None,
        status: Optional[AlertStatus] = None,
        rule_name: Optional[str] = None,
        track_id: Optional[int] = None,
        since: Optional[float] = None,
        until: Optional[float] = None,
        escalated_only: bool = False,
        newest_first: bool = True,
    ) -> List[Alert]:
        """Return alerts matching every supplied criterion.

        Unset criteria are ignored, so calling with no arguments returns
        everything.

        Args:
            level: Match this exact urgency level.
            min_level: Match this urgency level or higher.
            category: Match this category.
            status: Match this lifecycle status.
            rule_name: Match this originating rule name.
            track_id: Match this track identity.
            since: Only alerts at or after this timestamp.
            until: Only alerts at or before this timestamp.
            escalated_only: Only alerts whose urgency rose after being
                raised.
            newest_first: Whether to return the newest alert first.

        Returns:
            The matching alerts.
        """
        results: List[Alert] = []

        for alert in self._alerts:
            if level is not None and alert.level != level:
                continue
            if min_level is not None and alert.level < min_level:
                continue
            if category is not None and alert.category != category:
                continue
            if status is not None and alert.status != status:
                continue
            if rule_name is not None and alert.rule_name != rule_name:
                continue
            if track_id is not None and alert.track_id != track_id:
                continue
            if since is not None and alert.timestamp < since:
                continue
            if until is not None and alert.timestamp > until:
                continue
            if escalated_only and not alert.was_escalated:
                continue

            results.append(alert)

        return list(reversed(results)) if newest_first else results

    def search(self, text: str, newest_first: bool = True) -> List[Alert]:
        """Find alerts whose text fields contain a substring.

        Matches case-insensitively against the message, rule name, and
        category — the fields an operator would actually recall.

        Args:
            text: The substring to search for. Empty or whitespace-only
                input matches nothing, rather than everything, so an
                empty search box does not dump the whole history.
            newest_first: Whether to return the newest alert first.

        Returns:
            The matching alerts.
        """
        needle = (text or "").strip().lower()
        if not needle:
            return []

        results = [
            alert
            for alert in self._alerts
            if needle in alert.message.lower()
            or needle in alert.rule_name.lower()
            or needle in alert.category.value.lower()
        ]

        return list(reversed(results)) if newest_first else results

    def statistics(self, alerts: Optional[Sequence[Alert]] = None) -> AlertStatistics:
        """Summarize a set of alerts.

        Args:
            alerts: The alerts to summarize. Defaults to the full
                retained history, letting callers instead summarize a
                filtered subset.

        Returns:
            The aggregated statistics.
        """
        population = list(self._alerts) if alerts is None else list(alerts)

        if not population:
            return AlertStatistics()

        timestamps = [alert.timestamp for alert in population]
        track_counter = Counter(
            alert.track_id for alert in population if alert.track_id is not None
        )

        return AlertStatistics(
            total=len(population),
            by_level=dict(Counter(str(alert.level) for alert in population)),
            by_category=dict(Counter(alert.category.value for alert in population)),
            by_status=dict(Counter(alert.status.value for alert in population)),
            by_rule=dict(Counter(alert.rule_name for alert in population)),
            top_tracks=track_counter.most_common(5),
            escalated_count=sum(1 for alert in population if alert.was_escalated),
            acknowledged_count=sum(1 for alert in population if alert.acknowledged),
            resolved_count=sum(1 for alert in population if alert.resolved),
            total_occurrences=sum(alert.occurrence_count for alert in population),
            time_span=max(timestamps) - min(timestamps),
            first_timestamp=min(timestamps),
            last_timestamp=max(timestamps),
        )

    def to_dicts(self, alerts: Optional[Sequence[Alert]] = None) -> List[Dict[str, Any]]:
        """Export alerts as plain dictionaries.

        Args:
            alerts: The alerts to export. Defaults to the full history,
                newest first.

        Returns:
            One dictionary per alert.
        """
        population = self.all() if alerts is None else list(alerts)
        return [alert.to_dict() for alert in population]

    def to_json(
        self,
        alerts: Optional[Sequence[Alert]] = None,
        indent: Optional[int] = 2,
    ) -> str:
        """Export alerts as a JSON string.

        Args:
            alerts: The alerts to export. Defaults to the full history.
            indent: Indentation passed to :func:`json.dumps`; ``None``
                produces compact output.

        Returns:
            The JSON document.
        """
        return json.dumps(self.to_dicts(alerts), indent=indent, default=str)

    def to_csv(self, alerts: Optional[Sequence[Alert]] = None) -> str:
        """Export alerts as a CSV string.

        Nested fields (metadata, bounding box) are omitted, since they
        do not fit a flat tabular form; use :meth:`to_json` when those
        are needed.

        Args:
            alerts: The alerts to export. Defaults to the full history.

        Returns:
            The CSV document, including a header row.
        """
        buffer = io.StringIO()
        writer = csv.DictWriter(
            buffer, fieldnames=_CSV_COLUMNS, extrasaction="ignore", lineterminator="\n"
        )
        writer.writeheader()

        for row in self.to_dicts(alerts):
            writer.writerow({column: row.get(column, "") for column in _CSV_COLUMNS})

        return buffer.getvalue()

    def prune_before(self, cutoff: float) -> int:
        """Discard alerts older than a cutoff timestamp.

        Args:
            cutoff: Alerts with a timestamp strictly before this are
                removed.

        Returns:
            The number of alerts removed.
        """
        retained = [alert for alert in self._alerts if alert.timestamp >= cutoff]
        removed = len(self._alerts) - len(retained)

        if removed:
            self._alerts = deque(retained, maxlen=self.max_length)
            logger.debug(f"Pruned {removed} alert(s) older than {cutoff}.")

        return removed

    def clear(self) -> None:
        """Discard every retained alert."""
        self._alerts.clear()
        logger.debug("Alert history cleared.")
