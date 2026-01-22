"""
ThirdPartyManagement Bounded Context

Manages third parties (suppliers, vendors, partners) and their lifecycle.
"""

from .aggregates.third_party import ThirdParty

__all__ = [
    "ThirdParty",
]

