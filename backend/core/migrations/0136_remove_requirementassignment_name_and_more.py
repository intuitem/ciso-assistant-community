from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0135_requirementassignment"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="requirementassignment",
            name="name",
        ),
        migrations.RemoveField(
            model_name="requirementassignment",
            name="description",
        ),
        migrations.AlterModelOptions(
            name="requirementassignment",
            options={
                "ordering": ["created_at"],
                "verbose_name": "Requirement Assignment",
                "verbose_name_plural": "Requirement Assignments",
            },
        ),
    ]
