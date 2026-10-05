"""Targets a quick form publication may write to when a response is accepted.

A fixed list, never "write any field": each target knows its subject model,
the permission the reviewer needs on the subject, how to check its config
against the form, how to work out the value from a response, and how to write
it. Forms reference targets by key in `on_accept`.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Proposal:
    """What a target would write, or why it cannot."""

    ok: bool
    value: Any = None
    display: str = ""
    reason: str = ""
    overridden: bool = False
    note: str = ""
    extra: dict = field(default_factory=dict)

    @classmethod
    def refuse(cls, reason: str) -> "Proposal":
        return cls(ok=False, reason=reason)


class Target:
    key: str = ""
    #: app_label.ModelName of the subject this target writes to.
    subject_model: str = ""
    #: Permission codename the reviewer needs on the subject.
    permission: str = ""
    #: i18n key of the target's name.
    label: str = ""

    def validate_config(self, config: dict, quick_form) -> list[str]:
        """Errors that make the config unusable with this form."""
        return []

    def health(self, config: dict, quick_form) -> list[str]:
        """Why the config cannot apply on this instance: its own errors, plus
        what it names that is missing here."""
        return self.validate_config(config, quick_form)

    def current(self, subject) -> tuple[Any, str]:
        """The subject's current value and its display."""
        raise NotImplementedError

    def resolve(self, response, config: dict, override: dict | None = None) -> Proposal:
        raise NotImplementedError

    def apply(self, subject, proposal: Proposal, *, response, user) -> None:
        raise NotImplementedError


TARGETS: dict[str, Target] = {}


def register(target_cls: type[Target]) -> type[Target]:
    TARGETS[target_cls.key] = target_cls()
    return target_cls


def get_target(key: str) -> Target | None:
    return TARGETS.get(key)
