"""Which API models the demo does not populate, and why.

Every model behind an API ViewSet must be covered by a builder, listed in
``EXCLUDED`` (never demo data) or listed in ``PENDING`` (should have demo data,
not built yet). ``core/tests/test_demo_data.py`` fails on any model in none of
them, so a new feature can't ship without deciding.

Apps can extend both lists from their own ``demo_builders`` module by defining
``DEMO_EXCLUDED`` / ``DEMO_PENDING`` dicts, which keeps enterprise models out
of this file.
"""

from core.demo import discover

LIBRARY = "library content, loaded from libraries rather than authored"
STARTUP = "instance configuration seeded at startup"
IDENTITY = "identity and access: the demo never creates accounts or grants access"
EXTERNAL = "talks to or publishes to external systems"
RUNTIME = "produced by the system at run time, not authored"
NEEDS_USERS = "only meaningful with real users, which the demo never creates"

EXCLUDED = {
    "automation.WorkflowSecret": EXTERNAL,
    "automation.WorkflowToken": IDENTITY,
    "chat.AgentAction": RUNTIME,
    "chat.AgentRun": RUNTIME,
    "chat.ChatSession": RUNTIME,
    "chat.IndexedDocument": RUNTIME,
    "chat.QuestionnaireQuestion": RUNTIME,
    "chat.QuestionnaireRun": RUNTIME,
    "core.AssetCapability": STARTUP,
    "core.Comment": NEEDS_USERS,
    "core.ValidationFlow": NEEDS_USERS,
    "pmbok.ResponsibilityRole": STARTUP,
    "tprm.Tier": STARTUP,
    "core.Actor": "wrapper created automatically for users, teams and entities",
    "core.AssetClass": STARTUP,
    "core.Framework": LIBRARY,
    "core.LibraryDraft": "library authoring workspace",
    "core.LibraryFilteringLabel": LIBRARY,
    "core.LoadedLibrary": LIBRARY,
    "core.Preset": LIBRARY,
    "core.PresetJourney": LIBRARY,
    "core.PresetJourneyStep": LIBRARY,
    "core.Question": LIBRARY,
    "core.QuestionChoice": LIBRARY,
    "core.QuickForm": LIBRARY,
    "core.QuickFormPage": LIBRARY,
    "core.ReferenceControl": LIBRARY,
    "core.RequirementNode": LIBRARY,
    "core.RiskMatrix": LIBRARY,
    "core.StoredLibrary": LIBRARY,
    "core.Terminology": STARTUP,
    "custom_fields.CustomFieldDefinition": "instance-wide: would alter every user's forms",
    "global_settings.GlobalSettings": STARTUP,
    "iam.IdPGroup": IDENTITY,
    "iam.Role": IDENTITY,
    "iam.RoleAssignment": IDENTITY,
    "iam.SSOSettings": IDENTITY,
    "iam.ServiceAccount": IDENTITY,
    "iam.User": IDENTITY,
    "iam.UserGroup": IDENTITY,
    "integrations.IntegrationConfiguration": EXTERNAL,
    "integrations.IntegrationProvider": EXTERNAL,
    "metrology.BuiltinMetricSample": RUNTIME,
    "notifications.Notification": RUNTIME,
    "portals.Portal": EXTERNAL,
    "portals.PortalPreset": EXTERNAL,
    "portals.PublicDocument": EXTERNAL,
    "portals.FrameworkSnapshot": EXTERNAL,
    "sec_intel.CWE": LIBRARY,
    "sec_intel.SecurityAdvisory": "synced from advisory feeds",
    "sec_intel.TTPCatalog": LIBRARY,
    "sec_intel.Tactic": LIBRARY,
    "sec_intel.Technique": LIBRARY,
    "webhooks.WebhookEndpoint": EXTERNAL,
}

# The backlog: delete an entry in the PR that adds its builder, and lower
# MAX_PENDING to match. The test holds them equal, so the list only shrinks.
MAX_PENDING = 0

PENDING: set[str] = set()


def classification() -> tuple[dict[str, str], set[str]]:
    """``EXCLUDED`` and ``PENDING`` merged with every app's own declarations."""
    excluded, pending = dict(EXCLUDED), set(PENDING)
    for module in discover():
        excluded.update(getattr(module, "DEMO_EXCLUDED", {}))
        pending.update(getattr(module, "DEMO_PENDING", ()))
    return excluded, pending
