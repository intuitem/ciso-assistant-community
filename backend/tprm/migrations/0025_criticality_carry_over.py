from django.db import migrations
from django.db.models import Max
from django.utils import timezone

# Tiers did not exist before this release: the scale is the default one.
BY_CRITICALITY = {4: "critical", 3: "important", 2: "standard", 1: "low-impact"}
DEFAULT_TIERS = [
    ("critical", 4, "#dc2626"),
    ("important", 3, "#ea580c"),
    ("standard", 2, "#ca8a04"),
    ("low-impact", 1, "#16a34a"),
]


def carry_over(apps, schema_editor):
    Folder = apps.get_model("iam", "Folder")
    Tier = apps.get_model("tprm", "Tier")
    Entity = apps.get_model("tprm", "Entity")
    EntityAssessment = apps.get_model("tprm", "EntityAssessment")
    EntityTierChange = apps.get_model("tprm", "EntityTierChange")
    Solution = apps.get_model("tprm", "Solution")

    highest = dict(
        EntityAssessment.objects.filter(criticality__in=BY_CRITICALITY)
        .values("entity")
        .annotate(top=Max("criticality"))
        .values_list("entity", "top")
    )
    solutions = Solution.objects.filter(criticality__in=BY_CRITICALITY)
    if not highest and not solutions.exists():
        return

    # Normally seeded at startup, which runs after migrations.
    root = Folder.objects.filter(content_type="GL").first()
    if root is None:
        return
    if not Tier.objects.exists():
        for key, rank, hexcolor in DEFAULT_TIERS:
            Tier.objects.create(
                name=key,
                key=key,
                rank=rank,
                hexcolor=hexcolor,
                builtin=True,
                folder=root,
            )
    tiers = {t.key: t for t in Tier.objects.filter(key__in=BY_CRITICALITY.values())}

    now = timezone.now()
    for entity in Entity.objects.filter(pk__in=highest, tier__isnull=True):
        criticality = highest[entity.pk]
        tier = tiers.get(BY_CRITICALITY[criticality])
        if tier is None:
            continue
        entity.tier = tier
        entity.tier_source = "manual"
        entity.tier_set_at = now
        entity.save(update_fields=["tier", "tier_source", "tier_set_at"])
        EntityTierChange.objects.create(
            entity=entity,
            tier=tier,
            source="manual",
            folder_id=entity.folder_id,
            note=f"Set from the highest previous criticality ({criticality})",
        )

    for criticality, key in BY_CRITICALITY.items():
        if key in tiers:
            solutions.filter(criticality=criticality, tier__isnull=True).update(
                tier=tiers[key]
            )


class Migration(migrations.Migration):
    dependencies = [
        ("tprm", "0024_entity_tier"),
    ]

    operations = [
        # The former 1-4 criticality of entity assessments and solutions, carried
        # over to the scale; the old columns are kept, untouched.
        migrations.RunPython(carry_over, migrations.RunPython.noop),
    ]
