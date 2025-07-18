# Generated by Django 5.1.10 on 2025-07-12 08:12

import django.db.models.deletion
import iam.models
import uuid
from django.db import migrations, models


def modify_all_ebiosrmstudy(apps, schema_editor):
    EbiosRmStudy = apps.get_model("ebios_rm", "EbiosRmStudy")
    for study in EbiosRmStudy.objects.all():
        study.meta["workshops"][3]["steps"].insert(0, {"status": "to_do"})
        study.save()


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0082_riskscenario_inherent_impact_and_more"),
        ("ebios_rm", "0011_alter_roto_risk_origin"),
        ("iam", "0013_personalaccesstoken"),
    ]

    operations = [
        migrations.AddField(
            model_name="ebiosrmstudy",
            name="quotation_method",
            field=models.CharField(
                choices=[("manual", "Manual"), ("express", "Express")],
                default="manual",
                help_text="Method used to quote the study: 'manual' for manual likelihood assessment, 'express' for automatic propagation from operating modes",
                max_length=100,
                verbose_name="Quotation method",
            ),
        ),
        migrations.AlterField(
            model_name="roto",
            name="risk_origin",
            field=models.CharField(
                choices=[
                    ("state", "State"),
                    ("organized_crime", "Organized crime"),
                    ("terrorist", "Terrorist"),
                    ("activist", "Activist"),
                    ("competitor", "Competitor"),
                    ("amateur", "Amateur"),
                    ("avenger", "Avenger"),
                    ("pathological", "Pathological"),
                    ("other", "Other"),
                ],
                max_length=32,
                verbose_name="Risk origin",
            ),
        ),
        migrations.CreateModel(
            name="ElementaryAction",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="Created at"),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="Updated at"),
                ),
                (
                    "is_published",
                    models.BooleanField(default=False, verbose_name="published"),
                ),
                ("name", models.CharField(max_length=200, verbose_name="Name")),
                (
                    "description",
                    models.TextField(blank=True, null=True, verbose_name="Description"),
                ),
                (
                    "ref_id",
                    models.CharField(
                        blank=True, max_length=100, verbose_name="Reference ID"
                    ),
                ),
                (
                    "attack_stage",
                    models.SmallIntegerField(
                        choices=[
                            (0, "ebiosReconnaissance"),
                            (1, "ebiosInitialAccess"),
                            (2, "ebiosDiscovery"),
                            (3, "ebiosExploitation"),
                        ],
                        default=0,
                        help_text="Stage of the attack in the kill chain (e.g., 'Know', 'Enter', 'Discover', 'Exploit')",
                        verbose_name="Attack Stage",
                    ),
                ),
                (
                    "icon",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("server", "Server"),
                            ("computer", "Computer"),
                            ("cloud", "Cloud"),
                            ("file", "File"),
                            ("diamond", "Diamond"),
                            ("phone", "Phone"),
                            ("cube", "Cube"),
                            ("blocks", "Blocks"),
                            ("shapes", "Shapes"),
                            ("network", "Network"),
                            ("database", "Database"),
                            ("key", "Key"),
                            ("search", "Search"),
                            ("carrot", "Carrot"),
                            ("money", "Money"),
                            ("skull", "Skull"),
                            ("globe", "Globe"),
                            ("usb", "USB"),
                        ],
                        help_text="Icon representing the elementary action",
                        max_length=100,
                        null=True,
                        verbose_name="Icon",
                    ),
                ),
                (
                    "folder",
                    models.ForeignKey(
                        default=iam.models.Folder.get_root_folder_id,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="%(class)s_folder",
                        to="iam.folder",
                    ),
                ),
                (
                    "threat",
                    models.ForeignKey(
                        blank=True,
                        help_text="Threat that the elementary action is derived from",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="elementary_actions",
                        to="core.threat",
                        verbose_name="Threat",
                    ),
                ),
            ],
            options={
                "verbose_name": "Elementary Action",
                "verbose_name_plural": "Elementary Actions",
                "ordering": ["name"],
            },
        ),
        migrations.CreateModel(
            name="OperatingMode",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="Created at"),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="Updated at"),
                ),
                (
                    "is_published",
                    models.BooleanField(default=False, verbose_name="published"),
                ),
                ("name", models.CharField(max_length=200, verbose_name="Name")),
                (
                    "description",
                    models.TextField(blank=True, null=True, verbose_name="Description"),
                ),
                (
                    "ref_id",
                    models.CharField(
                        blank=True,
                        max_length=100,
                        null=True,
                        verbose_name="Reference ID",
                    ),
                ),
                (
                    "likelihood",
                    models.SmallIntegerField(default=-1, verbose_name="Likelihood"),
                ),
                (
                    "elementary_actions",
                    models.ManyToManyField(
                        blank=True,
                        help_text="Elementary actions that are part of the operating mode",
                        related_name="operating_modes",
                        to="ebios_rm.elementaryaction",
                        verbose_name="Elementary actions",
                    ),
                ),
                (
                    "folder",
                    models.ForeignKey(
                        default=iam.models.Folder.get_root_folder_id,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="%(class)s_folder",
                        to="iam.folder",
                    ),
                ),
                (
                    "operational_scenario",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="operating_modes",
                        to="ebios_rm.operationalscenario",
                        verbose_name="Operational scenario",
                    ),
                ),
            ],
            options={
                "verbose_name": "Operating Mode",
                "verbose_name_plural": "Operating Modes",
                "ordering": ["created_at"],
            },
        ),
        migrations.CreateModel(
            name="KillChain",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="Created at"),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="Updated at"),
                ),
                (
                    "is_published",
                    models.BooleanField(default=False, verbose_name="published"),
                ),
                ("is_highlighted", models.BooleanField(default=False)),
                (
                    "logic_operator",
                    models.CharField(
                        blank=True,
                        choices=[("AND", "AND"), ("OR", "OR")],
                        help_text="Logic operator to apply between antecedents",
                        max_length=10,
                        null=True,
                    ),
                ),
                (
                    "antecedents",
                    models.ManyToManyField(
                        blank=True,
                        help_text="Elementary actions that are antecedents to this action in the kill chain",
                        related_name="kill_chain_antecedents",
                        to="ebios_rm.elementaryaction",
                    ),
                ),
                (
                    "elementary_action",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="as_kill_chain",
                        to="ebios_rm.elementaryaction",
                    ),
                ),
                (
                    "folder",
                    models.ForeignKey(
                        default=iam.models.Folder.get_root_folder_id,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="%(class)s_folder",
                        to="iam.folder",
                    ),
                ),
                (
                    "operating_mode",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="kill_chain_steps",
                        to="ebios_rm.operatingmode",
                    ),
                ),
            ],
            options={
                "verbose_name": "Kill Chain",
                "verbose_name_plural": "Kill Chains",
                "ordering": ["created_at"],
            },
        ),
        migrations.RunPython(modify_all_ebiosrmstudy, migrations.RunPython.noop),
    ]
