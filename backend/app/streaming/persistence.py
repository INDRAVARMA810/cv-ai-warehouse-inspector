"""Persists live pipeline output to the database.

The detect -> track -> evaluate loop in :mod:`app.streaming.stream`
(and the offline ``run_detection.py``) has always produced violations
and tracked objects purely in memory, for the overlay. Nothing wrote
them to PostgreSQL, so the Alerts/Violations/Tracks pages only ever
showed seeded demo data.

This module bridges that gap using the existing, previously-unwired
pieces: :class:`~app.alerts.alert_manager.AlertManager` already groups
per-frame violations into durable, deduplicated incidents (an object
standing in a danger zone for ten seconds is one alert, not three
hundred), and :class:`~app.database.repositories.TrackRepository`
already upserts by track ID rather than inserting a row per frame. This
class only calls them and adds a time-based debounce on top, so a
database session is opened only for frames that actually have
something new to write — not on every frame at capture frame rate.
"""

import time
import uuid
from typing import Any, Dict, List, Optional, Sequence, Tuple

from app.alerts.alert import Alert
from app.alerts.alert_manager import AlertManager, build_default_manager
from app.database.repositories import RepositoryBundle
from app.database.session import session_scope
from app.logger import logger


class LivePersistence:
    """Writes one frame's alerts, violations, and tracks to PostgreSQL.

    * A **newly raised** alert (an object entering a zone, a fresh rule
      breach) is written immediately, together with the violation that
      raised it.
    * An **ongoing** incident is re-synced — occurrence count, last
      seen, escalation — at most once every ``sync_interval`` seconds,
      so a stationary hazard does not write dozens of rows a second.
    * Every tracked object is upserted via
      :meth:`~app.database.repositories.TrackRepository.save_domain`,
      throttled the same way; the first sighting of a track is always
      written immediately.

    Each instance mints its own ``run_id`` and stamps every track it
    writes with it. This matters because ByteTrack's ``track_id``
    restarts from 1 on every pipeline start — a bare numeric ID is not
    a stable identity across restarts. One :class:`LivePersistence`
    instance is constructed per pipeline run (see
    :meth:`app.streaming.stream.VideoStream._run`), so one ``run_id``
    per instance exactly matches one tracker lifetime, and two objects
    that both happen to be "track #1" in different runs can never be
    merged into the same database row.

    Attributes:
        alert_manager: Converts rule violations into durable alerts.
        sync_interval: Minimum seconds between two persisted updates of
            the same open incident or track.
        run_id: Identity of the current pipeline run, stamped on every
            track this instance persists.
    """

    def __init__(
        self,
        alert_manager: Optional[AlertManager] = None,
        sync_interval: float = 2.0,
    ) -> None:
        """Configure the persistence bridge.

        Args:
            alert_manager: Alert engine to use. Defaults to a new one
                with the project's standard configuration.
            sync_interval: Debounce window, in seconds, for re-syncing
                an already-open incident or an already-seen track.
        """
        self.alert_manager = alert_manager or build_default_manager()
        self.sync_interval = sync_interval
        self.run_id = str(uuid.uuid4())
        self._last_synced: Dict[str, float] = {}

    def record(self, rule_result: Any, tracked_objects: Sequence[Any]) -> None:
        """Persist one frame's tracks, alerts, and violations.

        Lets the alert engine advance every frame (so incidents close
        and cool down on schedule), but only opens a database session
        when there is actually something due to write.

        Never raises: a database hiccup should not take down the video
        stream, so failures are logged and swallowed.

        Args:
            rule_result: The frame's rule evaluation, or ``None``.
            tracked_objects: The frame's tracked objects.
        """
        now = time.time()

        new_alerts: List[Alert] = []
        if rule_result is not None:
            new_alerts = self.alert_manager.process(rule_result, now=now)

        tracks_due = [
            obj for obj in tracked_objects if self._is_due(self._track_key(obj), now)
        ]
        violations_due = self._due_violations(rule_result, new_alerts, now)

        if not tracks_due and not violations_due:
            return

        try:
            with session_scope() as session:
                repos = RepositoryBundle.for_session(session)

                for tracked_object in tracks_due:
                    repos.tracks.save_domain(tracked_object, run_id=self.run_id)
                    self._last_synced[self._track_key(tracked_object)] = now

                synced_alert_ids = set()
                for alert, violation in violations_due:
                    if alert.alert_id not in synced_alert_ids:
                        repos.alerts.save_domain(alert)
                        synced_alert_ids.add(alert.alert_id)
                    repos.violations.save_domain(violation, alert_id=alert.alert_id)
                    self._last_synced[alert.alert_id] = now
        except Exception:
            logger.exception("Failed to persist live pipeline output for this frame.")

    def _due_violations(
        self, rule_result: Any, new_alerts: Sequence[Alert], now: float
    ) -> List[Tuple[Alert, Any]]:
        """Pair each violation with its alert, for the ones due to sync.

        A brand-new alert is always due (it has never been synced); an
        already-open incident is due once ``sync_interval`` has passed
        since its last write.

        Args:
            rule_result: The frame's rule evaluation, or ``None``.
            new_alerts: Alerts the engine just raised this frame.
            now: The current timestamp.

        Returns:
            ``(alert, violation)`` pairs ready to persist.
        """
        if rule_result is None:
            return []

        new_by_identity: Dict[Any, Alert] = {
            (alert.rule_name, alert.track_id): alert for alert in new_alerts
        }

        due: List[Tuple[Alert, Any]] = []

        for violation in getattr(rule_result, "violations", ()):
            identity = (violation.rule_name, violation.track_id)
            alert = new_by_identity.get(identity) or self._find_open_alert(identity)

            if alert is not None and self._is_due(alert.alert_id, now):
                due.append((alert, violation))

        return due

    def _find_open_alert(self, identity: Any) -> Optional[Alert]:
        """Find the open alert matching a violation's ``(rule, track)`` identity."""
        for alert in self.alert_manager.engine.open_alerts.values():
            if (alert.rule_name, alert.track_id) == identity:
                return alert
        return None

    def _is_due(self, key: str, now: float) -> bool:
        """Whether ``key`` has never synced, or last synced beyond the debounce window."""
        last_synced = self._last_synced.get(key)
        return last_synced is None or now - last_synced >= self.sync_interval

    @staticmethod
    def _track_key(tracked_object: Any) -> str:
        """Debounce key for one tracked object's identity."""
        return f"track:{tracked_object.track_id}"

    def reset(self) -> None:
        """Discard alert-engine and debounce state, and start a new run.

        Call when a stream restarts on a new source, so incidents from
        the previous run do not carry over. ``run_id`` is rotated here
        too: a restart is exactly the boundary at which ByteTrack's
        ``track_id`` counter also restarts from 1, so the two must move
        together or tracks from the old and new run could collide.
        """
        self.alert_manager.reset()
        self._last_synced.clear()
        self.run_id = str(uuid.uuid4())
