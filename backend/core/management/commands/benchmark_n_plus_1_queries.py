import importlib
import random
import string
import copy
import uuid
import json
import os
from typing import Final, Any, Callable, Optional
from collections import defaultdict

from django.core.management.base import BaseCommand
from django.apps import apps
from django.db import models, connection, transaction, reset_queries
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from django.urls import get_resolver, URLPattern, URLResolver
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework.serializers import Serializer

from global_settings.models import GlobalSettings
from iam.sso.models import SSOSettings
from core.models import (
    RiskMatrix,
    RequirementNode,
    RequirementMappingSet,
    Actor,
    Comment,
    AppliedControl,
    Commitment,
)
from tprm.models import SolutionSubcontractor
from ebios_rm.models import KillChain
from doc_management.models import ManagedDocument, DocumentRevision
from automation.workflows.models import WorkflowInstance, WorkflowToken
from knox.models import AuthToken
from allauth.idp.oidc.models import Client
from iam.models import User
from metrology.models import BuiltinMetricSample, DashboardWidget
from webhooks.models import WebhookEndpoint

import core.permissions
import core.views
import global_settings.utils


def _monkeypatch_every_flag_enabled(feature_flag: str) -> bool:
    return True


# Make sure an unset feature flag prevent the GET HTTP requests to DRF list views get in the way.
global_settings.utils.ff_is_enabled = _monkeypatch_every_flag_enabled
core.permissions.ff_is_enabled = _monkeypatch_every_flag_enabled
core.views.ff_is_enabled = _monkeypatch_every_flag_enabled

for app_config in apps.get_app_configs():
    try:
        # We need to import all the serializers modules (so `Serializer.__subclasses__()` can list all our serializer classes).
        importlib.import_module(f"{app_config.name}.serializers")
    except ModuleNotFoundError:
        pass


def generate_random_string(length: int) -> str:
    """Return a randomly generated ascii-lowercased string (of `length` length)."""
    return "".join(random.choices(string.ascii_lowercase, k=length))


class Global:
    """Namespace for global variables (globally avaiable/shared variables)."""

    model_to_serializer: dict[type[models.Model], type[Serializer]] = {}
    """Hashmap of model to their ReadSerializer class (e.g. `Folder => FolderReadSerializer`)"""
    serializer_set: set[type[Serializer]] = set()
    """Set of ReadSerializer classes found by the program."""
    all_models: list[type[models.Model]] = []
    """List of all the ciso-assistant models (django models) found by the program."""
    model_to_objects: defaultdict[type[models.Model], list[models.Model]] = defaultdict(
        list
    )
    """Map a django `models.Model` to its `(ViewSetClass, list_route_path)` (e.g. `AssetViewSet, "/assets"`)."""
    model_to_list_view: dict[type[models.Model], tuple[type, str]] = {}
    """Temporary admin user REQUIRED by this script to work (this user will be the one requesting the list views)."""
    test_user: User = User(email=f"{generate_random_string(16)}@gmail.com")

    @staticmethod
    def init_all_models():
        BLACKLISTED_MODULE_PREFIXES: Final[set[str]] = {
            "allauth",
            "knox",
            "django",
            "auditlog",
        }
        """Blacklist used to exclude non-ciso-assistant modules from the code."""
        unfiltered_models = apps.get_models()

        for model in unfiltered_models:
            module_name = model.__module__.split(".", 2)[0]

            if module_name not in BLACKLISTED_MODULE_PREFIXES:
                # print(app_label, model)
                Global.all_models.append(model)

    @staticmethod
    def init_serializer_set(serializer_class: type[Serializer] = Serializer):
        serializer_subclasses = serializer_class.__subclasses__()

        Global.serializer_set.update(serializer_subclasses)

        for serializer_subclass in serializer_subclasses:
            Global.init_serializer_set(serializer_subclass)

    @staticmethod
    def init_model_to_serializer():
        read_serializers = [
            serializer
            for serializer in Global.serializer_set
            if serializer.__name__.endswith("ReadSerializer")
            and hasattr(serializer.Meta, "model")
        ]

        for serializer in read_serializers:
            model: type[models.Model] = serializer.Meta.model
            Global.model_to_serializer[model] = serializer

    @staticmethod
    def init_model_to_objects(object_to_create_count: int):
        Global.model_to_objects[ContentType] = list(
            ContentType.objects.all()[:object_to_create_count]
        )

        Global.model_to_objects[Client] = [
            Client.objects.create(name=generate_random_string(16))
            for _ in range(object_to_create_count)
        ]

    @staticmethod
    def _build_model_to_list_view() -> dict[type[models.Model], tuple[type, str]]:
        """
        Map each model to `(ViewSetClass, list_route_path)` taken from the URL conf.

        Only `BaseModelViewSet`-style classes (those with a `model` attribute)
        and whose GET maps to `list` are kept. The path is needed because
        `BaseModelViewSet.get_queryset` inspects `request.path`.
        """
        model_to_list_view: dict[type[models.Model], tuple[type, str]] = {}

        def walk(patterns, prefix: str):
            for pattern in patterns:
                if isinstance(pattern, URLResolver):
                    walk(pattern.url_patterns, prefix + str(pattern.pattern))

                elif isinstance(pattern, URLPattern):
                    callback = pattern.callback
                    actions = getattr(callback, "actions", None) or {}
                    cls = getattr(callback, "cls", None)
                    model = getattr(cls, "model", None)

                    if actions.get("get") == "list" and model is not None:
                        # Keep the first registration; later duplicates are aliases.
                        model_to_list_view.setdefault(
                            model, (cls, "/" + prefix + str(pattern.pattern))
                        )

        walk(get_resolver().url_patterns, "")
        return model_to_list_view

    @staticmethod
    def init_model_to_list_view():
        Global.model_to_list_view = Global._build_model_to_list_view()

    @staticmethod
    def init_test_user():
        Global.test_user = User.objects.create_superuser(
            email=f"{generate_random_string(16)}@gmail.com"
        )

    @staticmethod
    def init(object_to_create_count: int):
        Global.init_all_models()
        Global.init_serializer_set(Serializer)
        Global.init_model_to_serializer()
        Global.init_model_to_objects(object_to_create_count)
        Global.init_model_to_list_view()
        Global.init_test_user()


class CustomObjectCreator:
    """Class used as a namespace for custom object creators."""

    @staticmethod
    def create_actor(
        object_creator: ObjectCreator,
    ):  # Should i pass the  `ObjectCreator` as an argument
        user_set = set(Global.model_to_objects[User])
        picked_users = object_creator.unique_field_picked_objects["user"]

        remaining_users = user_set - picked_users
        picked_user = random.choice(list(remaining_users))
        picked_users.add(picked_user)

        # We don't create actors as they are automatically created when a `User` is created.
        return Actor.objects.get(user=picked_user)

    @staticmethod
    def create_comment(object_creator: ObjectCreator):
        applied_control_set = set(Global.model_to_objects[AppliedControl])
        picked_applied_controls = object_creator.unique_field_picked_objects["user"]

        remaining_users = applied_control_set - picked_applied_controls
        picked_applied_control = random.choice(list(remaining_users))
        picked_applied_controls.add(picked_applied_control)

        return Comment.objects.create(
            body="xxx",
            applied_control=picked_applied_control,
        )


CUSTOM_OBJECT_CREATOR: dict[
    type[models.Model], Callable[[ObjectCreator], models.Model]
] = {
    Actor: CustomObjectCreator.create_actor,
    Comment: CustomObjectCreator.create_comment,
}
"""
Map models to their "custom object creator" (usefull for models with special creation rules).
If a custom object creator is defined for a model, it will be used instead of the generic object creation logic we have in the `ObjectCreator` class.
"""


class CustomFieldValueGenerator:
    """Class used as a namespace for custom field value generators."""

    @staticmethod
    def create_max_score(create_dict: dict) -> int:
        return create_dict["min_score"] + 1

    @staticmethod
    def create_url(create_dict: dict) -> str:
        return "https://google.com/"


type CustomFieldValueGeneratorMap = dict[str, Callable[[dict], Any]]
"""Map field to functions used to generate their value (for object creation)."""

CUSTOM_FIELD_VALUE_GENERATOR: dict[type[models.Model], CustomFieldValueGeneratorMap] = {
    RequirementNode: {
        "max_score": CustomFieldValueGenerator.create_max_score,
    },
    WebhookEndpoint: {
        "url": CustomFieldValueGenerator.create_url,
    },
}
"""
Map model to their `CustomFieldValueGeneratorMap` (which maps field to custom field value generator functions).

When a model maps one of its field to a custom field value generator, it will be used to generate the value for this field.

Note that field value genrator are invoked AFTER the generic field value generation loginc (in the `ObjectCreator` class) has been applied.

So field value generators ALL have access to the field values generated by the `ObjectCreator` class and can therefore use them (as seen in `CustomFieldValueGenerator.create_max_score`).
"""

CLEAN_LEVEL_UNIQUE_TOGETHER: dict[type[models.Model], tuple[str, ...]] = {
    # `KillChain.clean()` force the `("operating_mode", "elementary_action")` field pair to be unique.
    # (But no SQL UNIQUE constraint force them to be unique).
    KillChain: ("operating_mode", "elementary_action"),
}
"""
Map models to a tuple of some of their field's name.

- These field names represent a combination of fields chose value combination MUST be unique.
- AND whose uniquness isn't enforced by a real SQL UNIQUE constraint.

(So which can't be discovered by reading the `{model}._meta.unique_together` value).
"""


class ObjectCreator:
    def __init__(self, model: type[models.Model], object_to_create_count: int):
        self.model = model
        self.object_to_create_count = object_to_create_count
        self.fields: list[models.Field] = [
            field
            for field in self.model._meta.fields
            # `AutoField`/`BigAutoField` primary keys have no Django-level
            # `default=`, so `has_default()` is `False` for them too -- but
            # they must be left for the DB to auto-increment, not handed a
            # random integer (which collides across creation loops, e.g.
            # `UNIQUE constraint failed: iam_personalaccesstoken.id`).
            #
            # `RiskMatrix.json_definition` has `default=dict` (an empty
            # `{}`), which would otherwise skip our special-cased override
            # below (see `generate_value_from_field`'s `JSONField` branch) --
            # that default silently wins and `RiskMatrix.probability`/etc.
            # blow up on the missing keys later (e.g. `EbiosRMStudy.save()`).
            if (
                not field.has_default()
                or field.unique
                or (self.model is RiskMatrix and field.name == "json_definition")
            )
            and not field.primary_key
        ]
        self.unique_field_picked_values: dict[str, set[str]] = defaultdict(set)
        self.unique_field_picked_objects: dict[str, set[models.Model]] = defaultdict(
            set
        )
        # Values picked for the row currently being built by
        # `generate_create_dict` (reset there before each row), keyed by
        # field name. Lets a field's generation see what a sibling field on
        # the *same* row just got, for cross-field constraints (e.g.
        # `SolutionSubcontractor.recipient` must differ from `subcontractor`).
        self.current_row_picks: dict[str, models.Model] = {}

        # Field names that participate in *some* real multi-field DB
        # constraint (`unique_together` or a 2+-field `UniqueConstraint`) --
        # e.g. `WorkflowVersion`'s `UniqueConstraint(fields=["workflow",
        # "version_number"])`. A field's own `.unique` is only ever `True`
        # for a *single*-field constraint, so relying on that alone lets a
        # field like `workflow` repeat freely across rows and collide with
        # `version_number` on the pair. We never reuse a value for any field
        # in this set across rows of this model -- a stronger guarantee than
        # strictly necessary (it forbids otherwise-valid repeats where only
        # the *other* field in the pair differs), but cheap and safe, and it
        # must NOT be applied to fields outside a real constraint (like
        # `SolutionSubcontractor.recipient`, which is only a `clean()`-level
        # business rule, not a DB constraint) -- doing so exhausts the tiny
        # `self.object_to_create_count`-sized object pool for no reason.
        self.multi_field_constraint_fields: set[str] = set()
        for group in model._meta.unique_together or []:
            if len(group) >= 2:
                self.multi_field_constraint_fields.update(group)
        for constraint in getattr(model._meta, "constraints", []):
            if (
                isinstance(constraint, models.UniqueConstraint)
                and len(constraint.fields) >= 2
            ):
                self.multi_field_constraint_fields.update(constraint.fields)

        # A THIRD kind of uniqueness enforcement, on top of Django's own
        # `unique_together`/`UniqueConstraint`: `core.base_models.BaseModel`
        # runs its own app-level "unique in scope" check in `clean()` against
        # whatever `fields_to_check` a model declares (e.g.
        # `ClassificationLevel.fields_to_check = ["abbreviation",
        # "object_classification"]`) -- invisible to `model._meta`, so it
        # needs pulling in separately here.
        fields_to_check = getattr(model, "fields_to_check", None)
        if fields_to_check:
            self.multi_field_constraint_fields.update(fields_to_check)

        # FOURTH kind: pair rules living only in a model's `clean()` body
        # (see `CLEAN_LEVEL_UNIQUE_TOGETHER`).
        clean_level_group = CLEAN_LEVEL_UNIQUE_TOGETHER.get(model)
        if clean_level_group:
            self.multi_field_constraint_fields.update(clean_level_group)

        self.custom_fields_value_generators: CustomFieldValueGeneratorMap = (
            CUSTOM_FIELD_VALUE_GENERATOR.get(self.model, {})
        )

        choice_lengths = []
        for field in self.fields:
            choices = getattr(field, "choices", None)

            if choices is not None:
                choice_lengths.append(len(choices))

    @staticmethod
    def create_auth_token() -> AuthToken:
        """
        Return a newly created `AuthToken`, along with a throwaway `User` to "own" it.

        The `AuthToken` model comes from the `knox` app, which is blacklisted (by `BLACKLISTED_MODULE_PREFIXES`).

        The `ObjectCreator` class don't create any `AuthToken` as blacklisted models are excluded from (not in the) `DependencyTree`.
        """
        user = User.objects.create(
            email=f"{generate_random_string(12)}@wow.test",
        )

        instance, _token = AuthToken.objects.create(user=user)
        return instance

    def generate_value_from_field(self, field: models.Field):
        has_custom_value_generator = field.name in self.custom_fields_value_generators
        if has_custom_value_generator:
            return

        if isinstance(field, models.IntegerField):
            final_integer = random.randrange(1, 10)
            return final_integer

        elif isinstance(field, models.URLField):
            return "https://google.com/"

        elif isinstance(field, (models.CharField, models.TextField)):
            if self.model is RequirementNode and field.name == "scores_definition_ref":
                return ""  # optional; must match a key in framework.scores_definition["alternatives"] otherwise

            if field.choices:
                choices = {value for value, _ in field.choices}

                if field.unique:
                    picked_values = self.unique_field_picked_values[field.name]

                    remaining_choices = choices - picked_values
                    assert len(remaining_choices) > 0, (
                        f"No remaining choice for the {field.name!r} of the {self.model.__qualname__} model."
                    )

                    new_picked_value = random.choice(list(remaining_choices))
                    self.unique_field_picked_values[field.name].add(new_picked_value)

                    return new_picked_value
                else:
                    return random.choice(list(choices))

            length = min((field.max_length or 256), 16)
            final_string = generate_random_string(length)

            return final_string

        elif isinstance(field, models.JSONField):
            if self.model is RiskMatrix and field.name == "json_definition":
                return {
                    "grid": [[0]],
                    "probability": [{"name": "P1"}],
                    "impact": [{"name": "I1"}],
                }
            return {}

        elif isinstance(field, models.UUIDField):
            return uuid.uuid4()

        elif isinstance(field, models.FloatField):
            final_float = random.randrange(1, 100) / 10
            return final_float

        # `DateTimeField` is a subclass of `DateField` so this if statement MUST be before the `DateField` one.
        elif isinstance(field, models.DateTimeField):
            final_datetime = timezone.now()
            return final_datetime

        elif isinstance(field, models.DateField):
            final_date = timezone.now().date()
            return final_date

        elif isinstance(field, models.BooleanField):
            final_bool = True
            return final_bool

        elif isinstance(field, models.ForeignKey):
            related_model = field.related_model

            if related_model is AuthToken:
                return self.create_auth_token()

            object_choices = set(Global.model_to_objects[related_model])

            if len(object_choices) == 0:
                return [] if isinstance(field, models.ManyToManyField) else None

            if isinstance(field, models.ManyToManyField):
                # A `ManyToManyField` CANNOT be `unique=True` in django, and
                # gets the whole pool (not a single pick) -- untouched by the
                # per-row/per-field exclusion logic below.
                return list(object_choices)

            remaining_choices = set(object_choices)

            # A field that's `unique=True` on its own, OR that participates
            # in a real multi-field constraint (`unique_together`/
            # `UniqueConstraint`, e.g. `WorkflowVersion.workflow` in
            # `UniqueConstraint(fields=["workflow", "version_number"])`), may
            # never repeat an already-used object across every row created
            # for this model -- that alone guarantees the constrained tuple
            # can't collide. Applying this to every FK regardless (as a
            # previous `if True or field.unique:` debug override did) wrongly
            # treated fields with no real DB constraint at all (like
            # `SolutionSubcontractor.recipient`, only a `clean()`-level rule)
            # as globally exhausting: with only `self.object_to_create_count`
            # objects in the pool, a handful of rows permanently used up
            # every candidate and the assert below fired on a later row.
            if field.unique or field.name in self.multi_field_constraint_fields:
                remaining_choices -= self.unique_field_picked_objects[field.name]

            # `SolutionSubcontractor.clean()` rejects
            # `subcontractor_id == recipient_id` -- both fields draw from
            # the same `Entity` pool independently, so they can collide.
            # Exclude whatever `subcontractor` just picked on this same
            # row before picking `recipient`.
            if self.model is SolutionSubcontractor and field.name == "recipient":
                subcontractor_pick = self.current_row_picks.get("subcontractor")
                remaining_choices -= {subcontractor_pick}

            # `RequirementMappingSet.save()` rejects
            # `source_framework == target_framework` -- both fields draw from
            # the same `Framework` pool independently, so they can collide.
            # Exclude whatever `source_framework` just picked on this same
            # row before picking `target_framework` (declared first -- see
            # field order in `core.models.RequirementMappingSet`).
            if self.model is RequirementMappingSet and field.name == "target_framework":
                source_framework_pick = self.current_row_picks.get("source_framework")
                remaining_choices -= {source_framework_pick}

            # Same `clean()` also rejects
            # `subcontractor_id == solution.provider_entity_id` -- exclude
            # the solution's direct provider from the `subcontractor`
            # pool (`solution` is picked earlier -- see field declaration
            # order in `tprm.models.SolutionSubcontractor`).
            if self.model is SolutionSubcontractor and field.name == "subcontractor":
                solution_pick = self.current_row_picks.get("solution")
                if solution_pick is not None:
                    remaining_choices = {
                        entity
                        for entity in remaining_choices
                        if entity.pk != solution_pick.provider_entity_id
                    }

            assert len(remaining_choices) > 0, (
                f"No remaining object choice for the {field.name!r} of the {self.model.__qualname__} model. ({object_choices})"
            )

            new_picked_object = random.choice(list(remaining_choices))

            if field.unique or field.name in self.multi_field_constraint_fields:
                self.unique_field_picked_objects[field.name].add(new_picked_object)

            self.current_row_picks[field.name] = new_picked_object

            return new_picked_object

    def generate_create_dict(self) -> dict[str, Any]:
        self.current_row_picks = {}
        create_dict: dict[str, Any] = {
            field.name: self.generate_value_from_field(field)
            for field in self.fields
            if not isinstance(field, models.ManyToManyField)
        }
        return create_dict

    def generate_m2m_dict(self) -> dict[str, list[models.Model]]:
        m2m_dict: dict[str, Any] = {
            field.name: self.generate_value_from_field(field)
            for field in self.fields
            if isinstance(field, models.ManyToManyField)
        }
        return m2m_dict

    # This function isn't used by the script.
    # But it could be usefull to keep it for future use.
    """def count_queries_for_read_serializers(self) -> int:
        # Serialize queryset with the read serializer and return the query count.

        model = self.model

        queryset = model.objects.all()
        serializer_class = Global.model_to_serializer.get(model)

        if serializer_class is None:
            return 0

        # We need to avoid the django query log to be filled up.
        reset_queries()

        with CaptureQueriesContext(connection) as ctx:
            serializer_class(queryset, many=True).data

        return len(ctx.captured_queries)"""

    def count_queries(self) -> Optional[int]:
        """
        Return the query count (quantity of SQL queries executed by django) after sending a GET HTTP request on the model's list endpoint.

        Returns `None` when no list viewset exists for the model.
        """
        list_view = Global.model_to_list_view.get(self.model)
        if list_view is None:
            return

        viewset_class, path = list_view
        view = viewset_class.as_view({"get": "list"})

        factory = APIRequestFactory()
        request = factory.get(path, {"limit": 1000})
        force_authenticate(request, user=Global.test_user)

        reset_queries()
        with CaptureQueriesContext(connection) as ctx:
            try:
                response = view(request)
            except ValueError as error:
                # `SerializerFactory` raises an Exception when `<Model>ReadSerializer` missing from every serializers module.
                # This is a real bug in the app (the registered list route 500s), but there's nothing to measure here.
                # So we report it and skip the model.
                if "not found in any provided modules" not in str(error):
                    raise
                print(
                    f"!! {self.model.__qualname__}: list route {path} is broken "
                    f"({error}) -- no ReadSerializer, skipping measurement"
                )
                return
            # Force rendering: DRF serializes lazily until `.data`/render.
            response.render()

        assert response.status_code == 200, (
            f"{self.model.__qualname__} list returned {response.data}"
        )
        return len(ctx.captured_queries)

    def add_custom_fields(self, create_dict: dict[str, Any]) -> dict[str, Any]:
        for (
            field_name,
            custom_value_generator,
        ) in self.custom_fields_value_generators.items():
            create_dict[field_name] = custom_value_generator(create_dict)

        return create_dict

    def create_object(self) -> models.Model:
        custom_object_creator = CUSTOM_OBJECT_CREATOR.get(self.model)
        if custom_object_creator is not None:
            return custom_object_creator(self)

        create_dict = self.generate_create_dict()
        full_create_dict = self.add_custom_fields(create_dict)

        new_object = self.model.objects.create(**full_create_dict)
        m2m_dict = self.generate_m2m_dict()

        for field_name, related_objects in m2m_dict.items():
            field = getattr(new_object, field_name)
            field.set(related_objects)

        return new_object

    def create(self) -> float:
        """
        Return the average query count per object returned by the list view (after creating multiple `self.model` objects).

        E.g. If after adding `5` objects the query count increased by `20`, the returned value will be `4.0`.
        """
        if self.object_to_create_count <= 1:
            return 0

        start_query_count = 0
        end_query_count = 0

        for index in range(self.object_to_create_count):
            new_object = self.create_object()

            Global.model_to_objects[self.model].append(new_object)

            query_count = self.count_queries()

            if index == 0:
                start_query_count = query_count

            elif index == self.object_to_create_count - 1:
                end_query_count = query_count

        if start_query_count is None or end_query_count is None:
            return 0.0

        query_count_diff = end_query_count - start_query_count
        row_diff = self.object_to_create_count - 1

        extra_query_per_row = query_count_diff / row_diff
        return extra_query_per_row


CIRCULAR_DEPENDENCIES_TO_BREAK: dict[type[models.Model], set[type[models.Model]]] = {
    # The `ManagedDocument.current_revision` `ForeignKey` is nullable so it's fine to let it empty.
    # The `DocumentRevision.document` `ForeignKey` is REQUIRED however (so it can't be ignored).
    ManagedDocument: {DocumentRevision},
    # Same shape: `WorkflowInstance.parent_token` is a nullable `ForeignKey` so it's fine to let it empty.
    # The `WorkflowToken.instance` `ForeignKey` is REQUIRED however (so it can't be ignored).
    WorkflowInstance: {WorkflowToken},
}
"""
Map a `model` to the `dependencies` (`set` of models) it MUST ignore.

This is usefull to manually fix circular dependencies issues in the `DependencyTree`.

- E.g. The `WorkflowInstance.parent_token` field `ForeignKey` points to a `WorkflowToken`.
- AND the `WorkflowToken.instance` `ForeignKey` points to a `WorkflowInstance`.
"""


class DependencyTree:
    """
    Represent a dependency tree of models.

    Models can depend on each other (via `ForeignKey`/`ManyToManyField`/etc... relations).
    """

    def __init__(self):
        self.model_to_dependencies: dict[
            type[models.Model], set[type[models.Model]]
        ] = {}
        """
        `Hashmap(model => list of models it depends on)`.

        A `model` Model depends on a `DependencyModel` model IF:
        
        - `model` has a field `some_field = ForeignKey(DependencyModel, ...)`
        - OR `model` has a field `some_field = ManyToManyField(DependencyModel, ...)`
        - OR `model` has any other kind of `ForeignKey` field (like `OneToOneField`)
        """
        self.dependency_to_models: dict[
            type[models.Model], set[type[models.Model]]
        ] = {}
        """
        `Hashmap(model => models which depends on it)`.

        (Inverted hashmap of `self.model_to_dependencies` (inverted relation)).
        """

    def load_model(
        self, model: type[models.Model], known_models: set[type[models.Model]]
    ):
        """Add the model to the `self` dependency tree."""
        model_fields = model._meta.fields
        dependencies = set()

        for field in model_fields:
            if isinstance(field, models.ForeignKey):
                dependency = field.related_model

                # We blacklist self-dependencies (`dependency is not model`).
                # And dependencies that aren't nodes in the `self` dependency tree (e.g. blacklisted third-party apps like
                # `knox`/`allauth`/`django.contrib.contenttypes`)
                if dependency is not model and dependency in known_models:
                    dependencies.add(dependency)
                    self.dependency_to_models.setdefault(dependency, set()).add(model)

        self.model_to_dependencies[model] = dependencies

    def load_models(
        self,
        models_to_load: list[type[models.Model]],
        *,
        blacklisted_models: set[type[models.Model]] = set(),
    ):
        """Load the models in the `models_to_load` model list into the `self` dependency tree."""
        known_models = set(models_to_load)
        for model in models_to_load:
            self.load_model(model, known_models)

        for blacklisted_model in blacklisted_models:
            dependencies = self.model_to_dependencies.pop(blacklisted_model, set())
            for dependency in dependencies:
                self.dependency_to_models[dependency].discard(blacklisted_model)

            dependent_models = self.dependency_to_models.get(blacklisted_model, set())
            non_blacklisted_dependent_models = dependent_models - blacklisted_models

            dependency_count = len(non_blacklisted_dependent_models)

            assert dependency_count == 0, (
                f"Can't blacklist the model {blacklisted_model.__qualname__} as {dependency_count} models are depending on it (dependentm models: {[model.__qualname__ for model in non_blacklisted_dependent_models]})"
            )

    def __iter__(self):
        model_to_dependencies = copy.deepcopy(self.model_to_dependencies)
        dependency_to_models = copy.deepcopy(self.dependency_to_models)

        models_to_treat = []
        """List of models which will be iterated by `for model in self` (`iter(self)`)."""

        while len(model_to_dependencies) > 0:
            pure_models = [
                model
                for model, dependencies in model_to_dependencies.items()
                if len(dependencies) == 0
            ]
            """List of models with no remaining dependencies (which can thus be loaded)."""

            if len(pure_models) == 0:
                # No pure models have been found, so there's surely some circular dependency between 2 models.
                no_circular_dependency_was_fixed = True

                for (
                    model,
                    skippable_dependencies,
                ) in CIRCULAR_DEPENDENCIES_TO_BREAK.items():
                    dependencies = model_to_dependencies.get(model)

                    if dependencies is None:
                        # Model is already treated (already in `models_to_treat`).
                        continue

                    can_break_circular_dependency = dependencies.issubset(
                        skippable_dependencies
                    )
                    if can_break_circular_dependency:
                        no_circular_dependency_was_fixed = False

                        model_to_dependencies.pop(model)
                        models_to_treat.append(model)

                        for dependency in dependencies:
                            dependency_to_models[dependency].discard(model)

                        dependent_models = dependency_to_models.pop(model, set())
                        for dependent_model in dependent_models:
                            model_to_dependencies[dependent_model].discard(model)

                if no_circular_dependency_was_fixed:
                    raise ValueError(
                        f"Can't find new models without remaining dependencies (is there a circular dependency ?), here are the remaining models: {model_to_dependencies}"
                    )

            for model in pure_models:
                models_to_treat.append(model)

                dependent_models = dependency_to_models.pop(model, set())
                model_to_dependencies.pop(model, None)

                for dependent_model in dependent_models:
                    model_to_dependencies[dependent_model].discard(model)

        return iter(models_to_treat)


class Command(BaseCommand):
    help = "Benchmarks the list endpoints of every model to detect N+1 queries (display the count of extra SQL query per extra created object)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            type=str,
            default=None,
            help="Optional filename to write the JSON benchmark results to (default: stdout)",
        )
        parser.add_argument(
            "--object-to-create-count",
            type=int,
            default=5,
            help="Number of objects per model which will be created in order to check N+1 queries (default: 5)",
        )

    def handle(self, *args, **options):
        output_filename = options["output"]
        object_to_create_count = options["object_to_create_count"]

        if object_to_create_count <= 0:
            self.stdout.write(
                "The --object-to-create-count argument MUST be superior to 0."
            )

        # We increment by 1 as we need to create a first "initial object" before adding extra objects to calcualte the N+1 query count.
        object_to_create_count += 1

        with transaction.atomic():
            Global.init(object_to_create_count)

            model_to_query_count_diff: list[tuple[str, float]] = []
            dependency_tree = DependencyTree()
            dependency_tree.load_models(
                Global.all_models,
                blacklisted_models={
                    # Some models are blacklisted as they cause bugs.
                    BuiltinMetricSample,
                    GlobalSettings,
                    SSOSettings,
                    DashboardWidget,
                    Commitment,
                },
            )

            for index, model in enumerate(dependency_tree):
                object_creator = ObjectCreator(model, object_to_create_count)

                query_count_diff = object_creator.create()

                model_to_query_count_diff.append((model.__qualname__, query_count_diff))

            transaction.set_rollback(True)

        sorted_model_to_query_count_diff = sorted(
            model_to_query_count_diff,
            key=lambda pair: pair[1],  # Sort by query_count
            reverse=True,
        )
        n_plus_1_query_dict = dict(sorted_model_to_query_count_diff)
        stringified_n_plus1_query_data = json.dumps(n_plus_1_query_dict, indent=2)

        self.stdout.write(stringified_n_plus1_query_data)

        if output_filename is not None and output_filename != "":
            if os.path.exists(output_filename):
                self.stdout.write(
                    f"Can't export(output) results to {output_filename!r} this file/directory already exists."
                )
            else:
                with open(output_filename, "w") as f:
                    f.write(stringified_n_plus1_query_data)
