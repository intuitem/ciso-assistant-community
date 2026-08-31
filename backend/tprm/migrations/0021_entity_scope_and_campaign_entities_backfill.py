# Data migration for the move to entity-based campaigns
# (documentation/entities-and-campaigns.md):
#   1. Identify the main entity through the legacy convention (builtin + owns
#      the root folder — owned_folders is removed in 0022) and stamp it with
#      is_main=True; mark it and its parent_entity descendants internal
#      (every other entity keeps the AddField default "external").
#   2. For each perimeter referenced by a campaign, create an internal entity
#      in that perimeter's folder (carrying the perimeter's default_assignee)
#      and attach it to the campaign's entities. Internal campaign audits land
#      in the entity's folder, so placement is preserved. Existing campaigns
#      keep target_scope="internal" from the AddField default, and their
#      perimeters M2M is left untouched for provenance.

from django.db import migrations

INTERNAL = "internal"
ROOT_CONTENT_TYPE = "GL"


def _mark_main_and_internal_lineage(Entity, Folder):
    root = Folder.objects.filter(content_type=ROOT_CONTENT_TYPE).first()
    if root is None:
        return
    main = (
        Entity.objects.filter(builtin=True, owned_folders=root)
        .order_by("created_at")
        .first()
    )
    if main is None:
        return
    main.is_main = True
    main.save(update_fields=["is_main"])
    internal_ids = {main.id}
    frontier = [main.id]
    while frontier:
        children = list(
            Entity.objects.filter(parent_entity_id__in=frontier)
            .exclude(id__in=internal_ids)
            .values_list("id", flat=True)
        )
        internal_ids.update(children)
        frontier = children
    Entity.objects.filter(id__in=internal_ids).update(scope=INTERNAL)


def _entities_from_campaign_perimeters(Entity, Actor, Campaign):
    # Reuse one entity per perimeter across campaigns.
    entity_by_perimeter = {}
    for campaign in Campaign.objects.prefetch_related("perimeters").all():
        entity_ids = []
        for perimeter in campaign.perimeters.all():
            entity = entity_by_perimeter.get(perimeter.id)
            if entity is None:
                entity = (
                    Entity.objects.filter(
                        name=perimeter.name,
                        folder_id=perimeter.folder_id,
                        scope=INTERNAL,
                    )
                    .order_by("created_at")
                    .first()
                )
            if entity is None:
                entity = Entity.objects.create(
                    name=perimeter.name,
                    folder_id=perimeter.folder_id,
                    scope=INTERNAL,
                )
                entity.default_assignee.set(perimeter.default_assignee.all())
                # Historical models bypass ActorSyncMixin.save(); create the
                # Actor row the live model would have created.
                Actor.objects.get_or_create(
                    entity=entity, defaults={"is_published": True}
                )
            entity_by_perimeter[perimeter.id] = entity
            entity_ids.append(entity.id)
        if entity_ids:
            campaign.entities.add(*entity_ids)


def forwards(apps, schema_editor):
    Entity = apps.get_model("tprm", "Entity")
    Actor = apps.get_model("core", "Actor")
    Campaign = apps.get_model("core", "Campaign")
    Folder = apps.get_model("iam", "Folder")

    _mark_main_and_internal_lineage(Entity, Folder)
    _entities_from_campaign_perimeters(Entity, Actor, Campaign)


class Migration(migrations.Migration):
    dependencies = [
        ("tprm", "0020_entity_scope_default_assignee_is_main"),
        ("core", "0186_campaign_entities_campaign_target_scope"),
        ("iam", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
