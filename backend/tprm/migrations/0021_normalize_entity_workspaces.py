"""One third-party workspace per entity per domain, named after the entity.

Assessments used to get a workspace each, so a vendor assessed several times holds
several. Merging them is what lets evidence, tasks and access carry from one round to
the next. Object ids do not change — only their folder — so links and exports keep
working.

Consolidation merges the respondent groups, so every contact of a vendor ends up able
to see that vendor's rounds. That is the point of a shared workspace, and it is called
out in the release notes.
"""

from django.db import migrations


class Migration(migrations.Migration):
    """The consolidation itself runs from `post_migrate` (core/startup.py), not here.

    It reuses the service the API and the support command call, which means real
    models — and a real model inside `RunPython` is read with today's fields while
    the schema is only as far along as this migration. A later migration adding a
    column to User, Folder or Entity then breaks the upgrade partway through, which
    is exactly what `iam.0028` did. `post_migrate` runs once the schema is complete.

    Kept as a no-op so the applied history stays linear for anyone who already ran it.
    """

    dependencies = [
        ("tprm", "0020_entityscore"),
    ]

    operations = [
        migrations.RunPython(migrations.RunPython.noop, migrations.RunPython.noop)
    ]
