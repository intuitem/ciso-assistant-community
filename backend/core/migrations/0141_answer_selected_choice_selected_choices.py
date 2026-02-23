import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0140_questionnaire_cleanup"),
    ]

    operations = [
        migrations.AddField(
            model_name="answer",
            name="selected_choice",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="single_choice_answers",
                to="core.questionchoice",
                verbose_name="Selected choice",
            ),
        ),
        migrations.AddField(
            model_name="answer",
            name="selected_choices",
            field=models.ManyToManyField(
                blank=True,
                related_name="multiple_choice_answers",
                to="core.questionchoice",
                verbose_name="Selected choices",
            ),
        ),
    ]
