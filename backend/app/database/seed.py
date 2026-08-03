"""Demo data for development and manual testing.

Populates the database with a small, realistic slice of warehouse
activity so queries, reports and future dashboards have something to
show before a camera is ever connected.

All writes go through the repositories — this module contains no SQL
and no direct session manipulation beyond the transaction boundary.

Run from the ``backend/`` directory::

    python -m app.database.seed
"""

import sys
from dataclasses import dataclass
from datetime import timedelta
from typing import Dict, List, Optional

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database.database import Database, DatabaseError
from app.database.migrations import initialize
from app.database.models import utcnow
from app.database.repositories import RepositoryBundle
from app.database.session import SessionManager, session_scope
from app.logger import logger


@dataclass
class SeedResult:
    """Counts of the rows created by a seeding run.

    Attributes:
        alerts: Alert records created.
        violations: Violation records created.
        tracks: Track records created.
        events: System events created.
    """

    alerts: int = 0
    violations: int = 0
    tracks: int = 0
    events: int = 0

    @property
    def total(self) -> int:
        """Total rows created."""
        return self.alerts + self.violations + self.tracks + self.events

    def to_dict(self) -> Dict[str, int]:
        """Return the counts as a plain mapping."""
        return {
            "alerts": self.alerts,
            "violations": self.violations,
            "tracks": self.tracks,
            "events": self.events,
            "total": self.total,
        }


def _demo_alerts() -> List[Dict[str, object]]:
    """Build the demo alert rows.

    Returns:
        Column values for each demo alert, newest last.
    """
    now = utcnow()

    return [
        {
            "alert_id": "11111111-1111-4111-8111-111111111111",
            "occurred_at": now - timedelta(minutes=45),
            "rule_name": "RestrictedZoneRule",
            "level": "critical",
            "initial_level": "high",
            "category": "zone_intrusion",
            "status": "resolved",
            "message": "person (track 12) entered danger zone 'machinery-bay'",
            "track_id": 12,
            "frame_number": 8140,
            "bounding_box": {"x1": 148.0, "y1": 152.0, "x2": 251.0, "y2": 402.0},
            "occurrence_count": 284,
            "first_seen": now - timedelta(minutes=45),
            "last_seen": now - timedelta(minutes=44, seconds=51),
            "acknowledged": True,
            "acknowledged_at": now - timedelta(minutes=44),
            "acknowledged_by": "supervisor.chen",
            "resolved": True,
            "resolved_at": now - timedelta(minutes=43),
            "was_escalated": True,
            "extra_metadata": {"zone_name": "machinery-bay", "zone_type": "danger"},
        },
        {
            "alert_id": "22222222-2222-4222-8222-222222222222",
            "occurred_at": now - timedelta(minutes=18),
            "rule_name": "MinimumDistanceRule",
            "level": "high",
            "initial_level": "high",
            "category": "proximity",
            "status": "acknowledged",
            "message": "person (track 21) and forklift (track 22) are 63.4px apart",
            "track_id": 21,
            "frame_number": 31200,
            "bounding_box": {"x1": 410.0, "y1": 220.0, "x2": 505.0, "y2": 440.0},
            "occurrence_count": 47,
            "first_seen": now - timedelta(minutes=18),
            "last_seen": now - timedelta(minutes=17, seconds=58),
            "acknowledged": True,
            "acknowledged_at": now - timedelta(minutes=17),
            "acknowledged_by": "operator.diaz",
            "resolved": False,
            "was_escalated": False,
            "extra_metadata": {"distance_px": 63.4, "track_ids": [21, 22]},
        },
        {
            "alert_id": "33333333-3333-4333-8333-333333333333",
            "occurred_at": now - timedelta(minutes=4),
            "rule_name": "MaximumWorkersRule",
            "level": "medium",
            "initial_level": "medium",
            "category": "occupancy",
            "status": "active",
            "message": "7 person(s) in zone 'loading-dock', exceeding the limit of 5",
            "track_id": None,
            "frame_number": 56010,
            "bounding_box": None,
            "occurrence_count": 96,
            "first_seen": now - timedelta(minutes=4),
            "last_seen": now - timedelta(minutes=3, seconds=57),
            "acknowledged": False,
            "resolved": False,
            "was_escalated": False,
            "extra_metadata": {"count": 7, "max_count": 5, "zone_name": "loading-dock"},
        },
    ]


def _demo_violations(alert_id: str) -> List[Dict[str, object]]:
    """Build demo violation rows belonging to one alert.

    Args:
        alert_id: The owning alert's domain ID.

    Returns:
        Column values for each demo violation.
    """
    now = utcnow()

    return [
        {
            "alert_id": alert_id,
            "occurred_at": now - timedelta(minutes=45) + timedelta(seconds=offset / 30),
            "rule_name": "RestrictedZoneRule",
            "severity": "critical",
            "description": "person (track 12) entered danger zone 'machinery-bay'",
            "track_id": 12,
            "frame_number": 8140 + offset,
            "bounding_box": {
                "x1": 148.0 + offset,
                "y1": 152.0,
                "x2": 251.0 + offset,
                "y2": 402.0,
            },
            "extra_metadata": {"zone_name": "machinery-bay"},
        }
        for offset in (0, 15, 30, 45, 60)
    ]


def _demo_tracks() -> List[Dict[str, object]]:
    """Build the demo track rows.

    Returns:
        Column values for each demo track.
    """
    now = utcnow()

    return [
        {
            "track_id": 12,
            "class_id": 0,
            "class_name": "person",
            "confidence": 0.91,
            "first_seen": now - timedelta(minutes=45),
            "last_seen": now - timedelta(minutes=44),
            "first_frame": 8140,
            "last_frame": 8424,
            "observation_count": 284,
            "bounding_box": {"x1": 148.0, "y1": 152.0, "x2": 251.0, "y2": 402.0},
        },
        {
            "track_id": 21,
            "class_id": 0,
            "class_name": "person",
            "confidence": 0.88,
            "first_seen": now - timedelta(minutes=18),
            "last_seen": now - timedelta(minutes=17),
            "first_frame": 31200,
            "last_frame": 31247,
            "observation_count": 47,
            "bounding_box": {"x1": 410.0, "y1": 220.0, "x2": 505.0, "y2": 440.0},
        },
        {
            "track_id": 22,
            "class_id": 7,
            "class_name": "forklift",
            "confidence": 0.79,
            "first_seen": now - timedelta(minutes=18),
            "last_seen": now - timedelta(minutes=16),
            "first_frame": 31180,
            "last_frame": 31600,
            "observation_count": 420,
            "bounding_box": {"x1": 470.0, "y1": 250.0, "x2": 640.0, "y2": 470.0},
        },
    ]


def _demo_events() -> List[Dict[str, object]]:
    """Build the demo system-event rows.

    Returns:
        Arguments for :meth:`SystemRepository.log_event`.
    """
    now = utcnow()

    return [
        {
            "event_type": "pipeline_started",
            "message": "Safety pipeline started on device 'cuda' with weights 'yolov8n.pt'",
            "level": "info",
            "source": "run_detection",
            "occurred_at": now - timedelta(hours=1),
            "metadata": {"device": "cuda", "weights": "yolov8n.pt"},
        },
        {
            "event_type": "zones_loaded",
            "message": "Installed 2 zone(s) for a 640x480 frame",
            "level": "info",
            "source": "run_detection",
            "occurred_at": now - timedelta(hours=1) + timedelta(seconds=2),
            "metadata": {"zones": ["machinery-bay", "loading-dock"]},
        },
        {
            "event_type": "camera_frame_dropped",
            "message": "Camera returned no frame; retrying",
            "level": "warning",
            "source": "app.video.camera",
            "occurred_at": now - timedelta(minutes=30),
            "metadata": {"consecutive_failures": 3},
        },
        {
            "event_type": "alert_raised",
            "message": "Critical alert raised for danger-zone intrusion",
            "level": "warning",
            "source": "app.alerts.alert_engine",
            "occurred_at": now - timedelta(minutes=45),
            "metadata": {"alert_id": "11111111-1111-4111-8111-111111111111"},
        },
    ]


def seed_session(session: Session, skip_if_populated: bool = True) -> SeedResult:
    """Insert demo data using an existing session.

    Args:
        session: The session providing the unit of work.
        skip_if_populated: When ``True``, does nothing if alerts already
            exist, so re-running is safe and will not duplicate rows.

    Returns:
        Counts of the rows created.
    """
    repos = RepositoryBundle.for_session(session)
    result = SeedResult()

    if skip_if_populated and repos.alerts.count() > 0:
        logger.info("Database already contains alerts; skipping seed.")
        return result

    alerts = repos.alerts.bulk_create(_demo_alerts())
    result.alerts = len(alerts)

    violations = repos.violations.bulk_create(
        _demo_violations("11111111-1111-4111-8111-111111111111")
    )
    result.violations = len(violations)

    tracks = repos.tracks.bulk_create(_demo_tracks())
    result.tracks = len(tracks)

    for event in _demo_events():
        repos.system.log_event(**event)  # type: ignore[arg-type]
        result.events += 1

    logger.info(f"Seeded demo data: {result.to_dict()}")
    return result


def seed(
    database: Optional[Database] = None,
    skip_if_populated: bool = True,
    create_tables: bool = True,
) -> Optional[SeedResult]:
    """Insert demo data, creating the schema first if needed.

    Args:
        database: The database to seed. Defaults to the process-wide
            instance.
        skip_if_populated: Whether to skip when alerts already exist.
        create_tables: Whether to initialize the schema first.

    Returns:
        Counts of the rows created, or ``None`` if seeding failed.
    """
    try:
        if create_tables and not initialize(database=database):
            logger.error("Cannot seed: schema initialization failed.")
            return None

        if database is not None:
            manager = SessionManager(database)
            with manager.session_scope() as session:
                return seed_session(session, skip_if_populated=skip_if_populated)

        with session_scope() as session:
            return seed_session(session, skip_if_populated=skip_if_populated)

    except (SQLAlchemyError, DatabaseError) as exc:
        logger.error(f"Seeding failed: {exc}")
        return None


def main() -> int:
    """Seed the configured database from the command line.

    Returns:
        A process exit code.
    """
    result = seed()

    if result is None:
        logger.error("Seeding did not complete.")
        return 1

    logger.info(f"Seeding complete: {result.total} row(s) created.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
