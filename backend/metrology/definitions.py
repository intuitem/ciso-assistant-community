"""A metric made in one step, and definitions kept tidy afterwards: the
definition a metric creates for itself, the readable definitions whose name
looks like one being typed, and merging two definitions of the same thing."""

from django.db import transaction
from django.db.models import Count

from iam.models import RoleAssignment
from metrology.models import MetricDefinition, MetricInstance

# What creating a metric with its definition takes, in the metric's domain.
CREATE = ["add_metricinstance", "add_metricdefinition"]
# MetricDefinition.name's length.
MAX_NAME_LENGTH = 200
# How many definitions the similar-name hint shows, and the shortest name it
# looks for: two letters match too much.
SIMILAR_LIMIT = 5
SIMILAR_MIN_LENGTH = 3
# The error key the form shows a merge refusal under.
MERGE_FIELD = "into"


class MergeError(Exception):
    def __init__(self, message):
        super().__init__(message)
        self.message = message


def permitted(user, codenames, folder):
    """Whether the user holds every one of ``codenames`` in ``folder``."""
    from django.contrib.auth.models import Permission

    permissions = list(Permission.objects.filter(codename__in=codenames))
    return len(permissions) == len(codenames) and all(
        RoleAssignment.is_access_allowed(user=user, perm=permission, folder=folder)
        for permission in permissions
    )


def creatable_in(user, folder):
    """Whether the user may create both the definition and the instance in
    ``folder``."""
    return permitted(user, CREATE, folder)


def definition_name(name, folder):
    """The definition created for a metric is named after it, suffixed when
    the domain already has one of that name."""
    name = name.strip()
    taken = MetricDefinition.objects.filter(folder=folder)
    candidate, n = name, 2
    while taken.filter(name__iexact=candidate).exists():
        suffix = f" ({n})"
        # Room for the suffix: a name at the limit stays valid.
        candidate = name[: MAX_NAME_LENGTH - len(suffix)] + suffix
        n += 1
    return candidate


def new_definition(folder, name, **fields):
    """The definition a metric creates for itself: in the metric's domain,
    named after the metric, with ``fields`` as its own columns."""
    return MetricDefinition.objects.create(
        folder=folder, name=definition_name(name, folder), **fields
    )


def create_metric(user, folder, name, definition, instance):
    """A metric made in one step, the way both the metric form and the
    compose modal make one: ``definition`` (the definition's own columns)
    becomes a definition in ``folder`` named after the metric, and
    ``instance`` (called with it) the metric measuring it. Both rights are
    checked before either write, and both writes share a transaction: a
    refused metric leaves no definition behind. Returns (definition,
    instance); raises PermissionError."""
    if not creatable_in(user, folder):
        raise PermissionError
    with transaction.atomic():
        created = new_definition(folder, name, **definition)
        return created, instance(created)


def similar_definitions(user, name, category=None, exclude=None, mergeable=False):
    """Definitions the user can read whose name contains ``name``, with the
    domains measuring them: the hint shown while a metric's name is typed.
    Never a definition from a domain the user cannot read. ``exclude`` and
    ``mergeable`` narrow the list before it is cut, so a merge target is never
    pushed out by what the modal would drop anyway."""
    name = (name or "").strip()
    if len(name) < SIMILAR_MIN_LENGTH:
        return []
    readable_ids = RoleAssignment.get_viewable_object_ids(user, MetricDefinition)
    definitions = (
        MetricDefinition.objects.filter(id__in=readable_ids, name__icontains=name)
        .select_related("folder", "unit")
        .order_by("name", "created_at")
    )
    if category:
        definitions = definitions.filter(category=category)
    if exclude is not None:
        definitions = definitions.exclude(id=exclude)
    if mergeable:
        # A merge target is what merge_definitions accepts: no formula (a
        # blank expression is none, as is_derived reads it), the source's
        # kind and unit, and for levels the same list. Filtered before the
        # cut, so a real target is never pushed out by a refused one.
        definitions = definitions.exclude(expression__regex=r"\S")
        source = MetricDefinition.objects.filter(id=exclude).first()
        if source is not None:
            definitions = definitions.filter(
                category=source.category, unit_id=source.unit_id
            )
            if source.category == MetricDefinition.Category.QUALITATIVE:
                definitions = definitions.filter(
                    choices_definition=source.choices_definition
                )
    definitions = list(definitions[:SIMILAR_LIMIT])
    if not definitions:
        return []
    readable_instances = RoleAssignment.get_viewable_object_ids(user, MetricInstance)
    measured = {}
    for row in (
        MetricInstance.objects.filter(
            id__in=readable_instances,
            metric_definition__in=[d.id for d in definitions],
        )
        .values("metric_definition_id", "folder__name")
        .annotate(count=Count("id"))
        .order_by("folder__name")
    ):
        measured.setdefault(row["metric_definition_id"], []).append(row["folder__name"])
    return [
        {
            "id": str(definition.id),
            "name": definition.name,
            "folder": {"id": str(definition.folder_id), "name": definition.folder.name},
            "category": definition.category,
            "unit": (
                {"id": str(definition.unit_id), "name": definition.unit.name}
                if definition.unit_id
                else None
            ),
            "higher_is_better": definition.higher_is_better,
            "decimals": definition.decimals,
            "default_target": definition.default_target,
            "default_collection_frequency": definition.default_collection_frequency,
            "is_derived": definition.is_derived,
            "library": definition.library_id is not None,
            "domains": measured.get(definition.id, []),
        }
        for definition in definitions
    ]


def merge_definitions(user, source, target):
    """Move every instance of ``source`` under ``target`` and delete
    ``source``: two domains defined the same metric, and the group keeps
    one. Instances keep their values, targets, owners and tasks; the
    target's direction, decimals and defaults apply from now on. Returns
    the number of instances moved. Raises MergeError with the reason, or
    PermissionError."""
    from metrology.series import dependents_of

    if source.id == target.id:
        raise MergeError("A definition cannot be merged into itself")
    if source.library_id is not None or source.urn:
        raise MergeError("A definition from a library cannot be merged away")
    if source.is_derived or target.is_derived:
        raise MergeError("A computed definition cannot be merged")
    if source.category != target.category:
        raise MergeError("The two definitions must have the same kind")
    if source.unit_id != target.unit_id:
        raise MergeError("The two definitions must have the same unit")
    if source.category == MetricDefinition.Category.QUALITATIVE and _level_names(
        source
    ) != _level_names(target):
        # A level value is an index into its definition's levels: moved under
        # other levels, every past value would read as another level.
        raise MergeError("The two definitions must have the same levels")
    if dependents_of(source):
        # A formula names the definition it reads; deleting it would leave
        # that input dangling.
        raise MergeError("A formula reads this definition; it cannot be merged away")
    if not RoleAssignment.is_object_readable(user, MetricDefinition, target.id):
        raise PermissionError
    # The source is deleted and the target changed: each takes its right.
    if not permitted(
        user, ["change_metricdefinition", "delete_metricdefinition"], source.folder
    ):
        raise PermissionError
    if not permitted(user, ["change_metricdefinition"], target.folder):
        raise PermissionError
    with transaction.atomic():
        # Checked and moved under one lock: an instance added or moved to
        # another domain meanwhile is seen here, not in a stale snapshot.
        instances = list(
            source.metricinstance_set.select_for_update().select_related("folder")
        )
        for instance in instances:
            if not permitted(user, ["change_metricinstance"], instance.folder):
                raise PermissionError
        for instance in instances:
            # Saved one by one: the signals mark the formulas reading the
            # target, whose combined inputs just gained an instance.
            instance.metric_definition = target
            instance.save(update_fields=["metric_definition", "updated_at"])
        source.delete()
    return len(instances)


def _level_names(definition):
    levels = definition.choices_definition
    if not isinstance(levels, list):
        return []
    return [level.get("name") if isinstance(level, dict) else None for level in levels]
