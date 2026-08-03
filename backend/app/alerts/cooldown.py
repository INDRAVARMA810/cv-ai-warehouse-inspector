"""Reusable cooldown (rate-limiting) primitive.

A cooldown suppresses repeat activity for a key until a timeout
elapses. The alert layer uses it to stop a single ongoing hazard from
producing an alert on every frame — at 30 fps, an unacknowledged
intrusion would otherwise generate 1,800 alerts a minute and bury the
operator.

The implementation is deliberately generic and owns no alert-specific
knowledge, so it can be reused for notification throttling or any other
rate-limited concern.

Every method accepts an optional ``now`` timestamp. Passing it makes
behaviour deterministic under test and lets callers evaluate a whole
frame against a single consistent clock reading.
"""

import time
from typing import Dict, Iterator, List, Optional, Tuple

from app.logger import logger


class CooldownTracker:
    """Tracks per-key cooldown windows.

    A key is "cooling down" from the moment it is triggered until its
    timeout elapses. Keys are opaque strings, so callers choose their
    own granularity (per rule, per rule+track, per zone, ...).

    Attributes:
        default_timeout: Cooldown duration, in seconds, used for keys
            without a specific override.
    """

    def __init__(
        self,
        default_timeout: float = 30.0,
        overrides: Optional[Dict[str, float]] = None,
    ) -> None:
        """Initialize the tracker.

        Args:
            default_timeout: Default cooldown duration, in seconds.
            overrides: Optional per-key timeouts overriding the default.

        Raises:
            ValueError: If ``default_timeout`` is negative, or any
                override is negative.
        """
        if default_timeout < 0:
            raise ValueError(
                f"default_timeout must be non-negative, got {default_timeout}"
            )

        for key, timeout in (overrides or {}).items():
            if timeout < 0:
                raise ValueError(
                    f"Cooldown override for '{key}' must be non-negative, got {timeout}"
                )

        self.default_timeout = float(default_timeout)
        self._overrides: Dict[str, float] = dict(overrides or {})
        self._last_triggered: Dict[str, float] = {}

    def __len__(self) -> int:
        """Return the number of keys currently being tracked."""
        return len(self._last_triggered)

    def __contains__(self, key: object) -> bool:
        """Return whether a key has ever been triggered."""
        return key in self._last_triggered

    def timeout_for(self, key: str) -> float:
        """Return the cooldown duration that applies to a key.

        Args:
            key: The key to look up.

        Returns:
            The key's override timeout, or the default if none is set.
        """
        return self._overrides.get(key, self.default_timeout)

    def set_timeout(self, key: str, timeout: float) -> None:
        """Set a per-key cooldown duration.

        Args:
            key: The key to configure.
            timeout: Cooldown duration, in seconds.

        Raises:
            ValueError: If ``timeout`` is negative.
        """
        if timeout < 0:
            raise ValueError(f"timeout must be non-negative, got {timeout}")

        self._overrides[key] = float(timeout)

    def is_cooling_down(self, key: str, now: Optional[float] = None) -> bool:
        """Return whether a key is currently suppressed.

        Args:
            key: The key to test.
            now: Timestamp to evaluate against. Defaults to the current
                time.

        Returns:
            ``True`` if the key was triggered recently enough that its
            timeout has not yet elapsed. A key that has never been
            triggered is never cooling down.
        """
        last = self._last_triggered.get(key)
        if last is None:
            return False

        timeout = self.timeout_for(key)
        if timeout == 0:
            return False

        current = time.time() if now is None else now
        return (current - last) < timeout

    def remaining(self, key: str, now: Optional[float] = None) -> float:
        """Return the seconds left before a key is released.

        Args:
            key: The key to inspect.
            now: Timestamp to evaluate against. Defaults to the current
                time.

        Returns:
            Seconds remaining, or ``0.0`` if the key is not cooling down.
        """
        last = self._last_triggered.get(key)
        if last is None:
            return 0.0

        current = time.time() if now is None else now
        return max(0.0, self.timeout_for(key) - (current - last))

    def trigger(self, key: str, now: Optional[float] = None) -> None:
        """Start (or restart) a key's cooldown window.

        Args:
            key: The key to trigger.
            now: Timestamp to record. Defaults to the current time.
        """
        self._last_triggered[key] = time.time() if now is None else now

    def try_trigger(self, key: str, now: Optional[float] = None) -> bool:
        """Trigger a key only if it is not already cooling down.

        Combines the check and the trigger into one atomic-feeling
        operation, which is the pattern callers almost always want::

            if cooldown.try_trigger(key):
                emit_alert()

        Args:
            key: The key to trigger.
            now: Timestamp to evaluate and record. Defaults to the
                current time.

        Returns:
            ``True`` if the key was free and has now been triggered,
            ``False`` if it was still cooling down (and was left
            untouched).
        """
        current = time.time() if now is None else now

        if self.is_cooling_down(key, now=current):
            return False

        self.trigger(key, now=current)
        return True

    def reset(self, key: str) -> bool:
        """Clear a single key's cooldown, releasing it immediately.

        Args:
            key: The key to release.

        Returns:
            ``True`` if the key was being tracked, ``False`` otherwise.
        """
        return self._last_triggered.pop(key, None) is not None

    def clear(self) -> None:
        """Clear every tracked cooldown."""
        self._last_triggered.clear()
        logger.debug("Cooldown tracker cleared.")

    def active_keys(self, now: Optional[float] = None) -> List[str]:
        """Return the keys currently cooling down.

        Args:
            now: Timestamp to evaluate against. Defaults to the current
                time.

        Returns:
            The suppressed keys.
        """
        current = time.time() if now is None else now
        return [
            key for key in self._last_triggered if self.is_cooling_down(key, now=current)
        ]

    def prune(self, now: Optional[float] = None) -> int:
        """Forget keys whose cooldown has elapsed.

        Without this, a long-running process accumulates one entry per
        key ever seen. Track IDs are unbounded over a long shift, so
        callers should prune periodically.

        Args:
            now: Timestamp to evaluate against. Defaults to the current
                time.

        Returns:
            The number of keys removed.
        """
        current = time.time() if now is None else now
        expired = [
            key
            for key in self._last_triggered
            if not self.is_cooling_down(key, now=current)
        ]

        for key in expired:
            del self._last_triggered[key]

        if expired:
            logger.debug(f"Pruned {len(expired)} elapsed cooldown key(s).")

        return len(expired)

    def items(self) -> Iterator[Tuple[str, float]]:
        """Iterate over ``(key, last_triggered_timestamp)`` pairs."""
        return iter(self._last_triggered.items())
