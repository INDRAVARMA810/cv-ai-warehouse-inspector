"""Registration and lifecycle management for safety rules.

The registry is the single source of truth for which rules exist and
which are active. Keeping it separate from :mod:`app.rules.rule_engine`
means rules can be added, swapped, enabled, or disabled — at startup or
at runtime — without the engine knowing anything about specific rule
types.
"""

from typing import Callable, Dict, Iterable, List, Optional, Type

from app.logger import logger
from app.rules.rule import BaseRule
from app.rules.safety_rules import DEFAULT_RULES


class DuplicateRuleError(Exception):
    """Raised when registering a rule whose name is already taken."""


class RuleRegistry:
    """Holds the set of known safety rules, keyed by unique name.

    Rules are returned in priority order (lowest ``priority`` value
    first), so callers get a deterministic, configurable evaluation
    sequence.
    """

    def __init__(self) -> None:
        """Create an empty registry."""
        self._rules: Dict[str, BaseRule] = {}

    def __len__(self) -> int:
        """Return the number of registered rules, enabled or not."""
        return len(self._rules)

    def __contains__(self, rule_name: object) -> bool:
        """Return whether a rule with the given name is registered."""
        return rule_name in self._rules

    def register(self, rule: BaseRule, replace: bool = False) -> BaseRule:
        """Register a rule instance.

        Args:
            rule: The rule to register.
            replace: If ``True``, silently replace an existing rule with
                the same name instead of raising.

        Returns:
            The registered rule, for convenient chaining.

        Raises:
            TypeError: If ``rule`` is not a :class:`BaseRule`.
            DuplicateRuleError: If the name is taken and ``replace`` is
                ``False``.
        """
        if not isinstance(rule, BaseRule):
            raise TypeError(
                f"Expected a BaseRule instance, got {type(rule).__name__}"
            )

        if rule.name in self._rules and not replace:
            raise DuplicateRuleError(
                f"A rule named '{rule.name}' is already registered. "
                f"Pass replace=True to override it."
            )

        self._rules[rule.name] = rule
        logger.debug(
            f"Registered rule '{rule.name}' "
            f"(priority={rule.priority}, enabled={rule.enabled})"
        )
        return rule

    def register_many(self, rules: Iterable[BaseRule], replace: bool = False) -> None:
        """Register several rules at once.

        Args:
            rules: The rules to register.
            replace: Whether to overwrite existing rules by name.

        Raises:
            DuplicateRuleError: If a name is taken and ``replace`` is
                ``False``.
        """
        for rule in rules:
            self.register(rule, replace=replace)

    def unregister(self, rule_name: str) -> bool:
        """Remove a rule from the registry.

        Args:
            rule_name: Name of the rule to remove.

        Returns:
            ``True`` if a rule was removed, ``False`` if the name was
            not registered.
        """
        removed = self._rules.pop(rule_name, None)

        if removed is None:
            logger.warning(f"Cannot unregister unknown rule '{rule_name}'.")
            return False

        logger.debug(f"Unregistered rule '{rule_name}'.")
        return True

    def get(self, rule_name: str) -> Optional[BaseRule]:
        """Return a registered rule by name.

        Args:
            rule_name: The name to look up.

        Returns:
            The rule, or ``None`` if it is not registered.
        """
        return self._rules.get(rule_name)

    def all_rules(self) -> List[BaseRule]:
        """Return every registered rule, in priority order.

        Returns:
            All rules, enabled or not, lowest ``priority`` value first.
        """
        return sorted(self._rules.values(), key=lambda rule: (rule.priority, rule.name))

    def enabled_rules(self) -> List[BaseRule]:
        """Return only the rules the engine should evaluate.

        Returns:
            The enabled rules, lowest ``priority`` value first.
        """
        return [rule for rule in self.all_rules() if rule.enabled]

    def set_enabled(self, rule_name: str, enabled: bool) -> bool:
        """Enable or disable a registered rule at runtime.

        Args:
            rule_name: Name of the rule to update.
            enabled: The desired state.

        Returns:
            ``True`` if the rule was found and updated, ``False``
            otherwise.
        """
        rule = self._rules.get(rule_name)

        if rule is None:
            logger.warning(f"Cannot change state of unknown rule '{rule_name}'.")
            return False

        rule.enabled = enabled
        logger.info(f"Rule '{rule_name}' {'enabled' if enabled else 'disabled'}.")
        return True

    def clear(self) -> None:
        """Remove every registered rule."""
        self._rules.clear()
        logger.debug("Rule registry cleared.")

    def register_defaults(self, replace: bool = False) -> "RuleRegistry":
        """Register the project's standard rule set.

        Each class in :data:`~app.rules.safety_rules.DEFAULT_RULES` is
        instantiated with its own default configuration. Rules that ship
        disabled — such as ``PPEPlaceholderRule`` — are registered but
        not evaluated, so their existence is visible without them
        affecting results.

        Args:
            replace: Whether to overwrite existing rules by name.

        Returns:
            ``self``, for convenient chaining.
        """
        for rule_class in DEFAULT_RULES:
            try:
                self.register(rule_class(), replace=replace)
            except DuplicateRuleError:
                logger.debug(
                    f"Default rule '{rule_class.__name__}' already registered; skipping."
                )

        logger.info(
            f"Registered {len(self)} default rule(s); "
            f"{len(self.enabled_rules())} enabled."
        )
        return self

    def rule_class(self, **kwargs: object) -> Callable[[Type[BaseRule]], Type[BaseRule]]:
        """Return a decorator that registers a rule class on definition.

        Supports declaring custom rules without touching engine startup
        code::

            registry = RuleRegistry()

            @registry.rule_class(priority=15)
            class SpeedLimitRule(BaseRule):
                ...

        Args:
            **kwargs: Constructor arguments for the decorated class.

        Returns:
            A decorator that instantiates and registers the class, then
            returns the class unchanged.
        """

        def decorator(cls: Type[BaseRule]) -> Type[BaseRule]:
            self.register(cls(**kwargs))  # type: ignore[arg-type]
            return cls

        return decorator


def build_default_registry() -> RuleRegistry:
    """Create a registry pre-populated with the standard rule set.

    Returns:
        A ready-to-use :class:`RuleRegistry`.
    """
    return RuleRegistry().register_defaults()
