"""One third-party workspace per entity per domain, named after the entity.

Assessments used to get a workspace each, so a vendor assessed several times holds
several. Merging them is what lets evidence, tasks and access carry from one round to
the next. Object ids do not change — only their folder — so links and exports keep
working.

Consolidation merges the respondent groups, so every contact of a vendor ends up able
to see that vendor's rounds. That is the point of a shared workspace, and it is called
out in the release notes.
"""

import structlog
from django.db import migrations

logger = structlog.get_logger(__name__)


def normalize(apps, schema_editor):
    # Real models, not historical ones: this reuses the service the API and the
    # support command call, and it needs model behaviour (auditlog, folder rules).
    from tprm.services import normalize_entity_workspaces

    for row in normalize_entity_workspaces(apply=True):
        if row["error"]:
            # One awkward entity must not block an upgrade.
            logger.warning(
                "Could not normalise third-party workspace",
                entity=row["entity"].name,
                domain=row["domain"].name,
                error=row["error"],
            )
        else:
            logger.info(
                "Normalised third-party workspace",
                entity=row["entity"].name,
                action=row["action"],
            )


class Migration(migrations.Migration):
    dependencies = [
        ("tprm", "0020_entityscore"),
    ]

    operations = [migrations.RunPython(normalize, migrations.RunPython.noop)]
