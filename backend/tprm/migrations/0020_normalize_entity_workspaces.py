"""One third-party workspace per entity per domain, named after the entity.

Assessments used to get a workspace each, so a vendor assessed several times holds
several. Merging them lets evidence, tasks and access carry across rounds, and merges
the respondent groups. Only folders change, so links and exports keep working.
"""

from django.db import migrations


class Migration(migrations.Migration):
    """The consolidation itself runs from `post_migrate` (core/startup.py), not here.

    A real model inside `RunPython` is read with today's fields while the schema is only
    as far as this migration — which is what broke on `iam.0028`. Kept as a no-op so the
    applied history stays linear.
    """

    dependencies = [
        ("tprm", "0019_null_perimeter_on_enclave_audits"),
    ]

    operations = [
        migrations.RunPython(migrations.RunPython.noop, migrations.RunPython.noop)
    ]
