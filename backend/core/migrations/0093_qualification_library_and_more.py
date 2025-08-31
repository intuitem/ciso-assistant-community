from django.db import migrations

def forwards(apps, schema_editor):
    Qualification = apps.get_model("core", "Qualification")
    RiskScenario = apps.get_model("core", "RiskScenario")

    # index of qualifications by name
    q_by_name = {q.name: q for q in Qualification.objects.all()}

    for rs in RiskScenario.objects.all():
        raw = getattr(rs, "qualifications", None)
        if not raw:
            continue
        # old field = JSON list of names
        names = raw if isinstance(raw, list) else []
        ids = []
        for name in names:
            q = q_by_name.get(name)
            if not q:
                raise RuntimeError(f"Unkonwn qualfiication: {name}")
            ids.append(q.pk)
        if ids:
            rs.qualifications_new.add(*ids)

class Migration(migrations.Migration):

    dependencies = [
        ("core", "0092_terminology"),
    ]

    operations = [
        migrations.AddField(
            model_name="riskscenario",
            name="qualifications_new",
            field=migrations.fields.ManyToManyField(
                to="core.qualification",
                related_name="risk_scenarios",
                blank=True,
                verbose_name="Qualifications",
            ),
        ),
        migrations.RunPython(forwards),
        migrations.RemoveField(
            model_name="riskscenario",
            name="qualifications",
        ),
        migrations.RenameField(
            model_name="riskscenario",
            old_name="qualifications_new",
            new_name="qualifications",
        ),
    ]
