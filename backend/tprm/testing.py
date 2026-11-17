"""Test helpers for the tier scale."""

from tprm.models import Tier

FOUR_LEVEL_SCALE = [
    ("critical", 4, "#dc2626"),
    ("high", 3, "#ea580c"),
    ("medium", 2, "#ca8a04"),
    ("low", 1, "#16a34a"),
]


def seed_four_level_scale() -> None:
    """Replace the scale with four fixed built-in levels, so tier tests do not
    depend on the shipped default (`Tier.DEFAULT_TIERS`)."""
    Tier.objects.all().delete()
    for name, rank, hexcolor in FOUR_LEVEL_SCALE:
        Tier.objects.create(name=name, rank=rank, hexcolor=hexcolor, builtin=True)
