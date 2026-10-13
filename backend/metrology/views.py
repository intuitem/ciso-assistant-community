import uuid

from django.contrib.contenttypes.models import ContentType
from django.db.models import Count
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework import status, serializers
from rest_framework.decorators import action
from rest_framework.response import Response

from core.views import BaseModelViewSet, LONG_CACHE_TTL
from iam.models import Folder, RoleAssignment
from django.contrib.auth.models import Permission
from metrology.models import (
    MetricDefinition,
    MetricInstance,
    CustomMetricSample,
    BuiltinMetricSample,
    Dashboard,
    DashboardWidget,
)
from metrology.builtin_metrics import BUILTIN_METRICS, METRIC_TYPE_CHART_TYPES
from metrology.serializers import (
    DERIVED_SAMPLE_READ_ONLY,
    BuiltinMetricSampleReadSerializer,
)


def _as_uuid(value):
    try:
        return uuid.UUID(str(value))
    except ValueError, TypeError:
        return None


def _composable(instance):
    """A metric instance as the "new computed metric" modal lists it."""
    definition = instance.metric_definition
    return {
        "id": str(instance.id),
        "name": instance.name,
        "folder": {"id": str(instance.folder_id), "str": str(instance.folder)},
        "frequency": instance.collection_frequency,
        "current_value": instance.current_value(),
        "definition": {"id": str(definition.id), "name": definition.name},
    }


def _user_can_read_target(user, content_type, object_id):
    target_model = content_type.model_class()
    if target_model is None:
        return False
    try:
        object_uuid = (
            object_id if isinstance(object_id, uuid.UUID) else uuid.UUID(str(object_id))
        )
    except ValueError, TypeError:
        return False
    try:
        return RoleAssignment.is_object_readable(user, target_model, object_uuid)
    except NotImplementedError:
        return False


class MetricDefinitionViewSet(BaseModelViewSet):
    model = MetricDefinition
    serializers_module = "metrology.serializers"
    filterset_fields = [
        "folder",
        "category",
        "unit",
        "library",
        "provider",
        "filtering_labels",
    ]
    search_fields = ["name", "description", "ref_id", "provider"]

    def get_queryset(self):
        # folder, library and unit are each rendered by FieldsRelatedField.
        return (
            super()
            .get_queryset()
            .select_related("folder", "library", "unit")
            .prefetch_related("filtering_labels")
        )

    @method_decorator(cache_page(60 * LONG_CACHE_TTL))
    @action(detail=False, name="Get readable models", url_path="readable-models")
    def readable_models(self, request):
        """The models a dataset may read, with their fields and the aggregate
        functions: the same registry the workflow builder uses, served here
        so the metric form does not depend on the workflows feature flag."""
        from core.reads.registry import registry_payload

        return Response(registry_payload())

    @action(detail=False, methods=["post"], url_path="preview-formula")
    def preview_formula(self, request):
        """Evaluate a derived metric's formula against a folder, writing
        nothing. The datasets' aggregates and the result come back so an author
        sees what the expression reads; an evaluation failure is a 200 with
        ok: false. Needs the right to add metric instances in that folder, the
        same right that would make the number visible."""
        from metrology.derived import (
            DerivedMetricError,
            evaluate_formula,
            validate_formula,
        )

        data = request.data if isinstance(request.data, dict) else {}
        folder = Folder.objects.filter(id=_as_uuid(data.get("folder"))).first()
        if folder is None:
            return Response(
                {"error": "folderNotFound"}, status=status.HTTP_400_BAD_REQUEST
            )
        permission = Permission.objects.filter(codename="add_metricinstance").first()
        if permission is None or not RoleAssignment.is_access_allowed(
            user=request.user, perm=permission, folder=folder
        ):
            return Response(status=status.HTTP_403_FORBIDDEN)
        datasets = data.get("datasets")
        expression = data.get("expression") or ""
        inputs = data.get("inputs")
        definition = MetricDefinition.objects.filter(
            id=_as_uuid(data.get("definition"))
        ).first()
        errors = validate_formula(datasets, expression, inputs, definition)
        if errors:
            return Response(
                {"ok": False, "errors": [{"code": c, "message": m} for c, m in errors]}
            )
        if inputs:
            return self._preview_series(data, inputs, expression, folder)
        try:
            evaluation = evaluate_formula(datasets, expression, folder)
        except DerivedMetricError as e:
            return Response(
                {
                    "ok": False,
                    "errors": [
                        {"code": "derived_evaluation_failed", "message": e.message}
                    ],
                }
            )
        return Response(
            {"ok": True, "value": evaluation.value, "datasets": evaluation.datasets}
        )

    PREVIEW_PERIODS = 24

    def _preview_series(self, data, inputs, expression, folder):
        """A metric formula's last periods at the frequency the author picks,
        and what each input resolved to in the folder."""
        from types import SimpleNamespace

        from metrology.compose import unreadable_picks
        from metrology.derived import DerivedMetricError
        from metrology.series import evaluate_series, period_start, shift_period
        from django.utils import timezone

        frequency = data.get("frequency")
        if frequency not in MetricInstance.Frequency.values:
            frequency = MetricInstance.Frequency.MONTHLY
        shape = SimpleNamespace(
            category=data.get("category") or MetricDefinition.Category.QUANTITATIVE,
            choices_definition=data.get("choices_definition") or [],
        )
        since = shift_period(
            period_start(timezone.now(), frequency),
            frequency,
            -(self.PREVIEW_PERIODS - 1),
        )
        choices = data.get("input_choices")
        if choices is not None and not isinstance(choices, dict):
            choices = None
        if unreadable_picks(self.request.user, choices):
            # A pick the author may not read would show them its values.
            return Response(
                {
                    "ok": False,
                    "errors": [
                        {
                            "code": "derived_input_invalid",
                            "message": "A picked metric instance does not exist",
                        }
                    ],
                }
            )
        try:
            evaluation = evaluate_series(
                inputs,
                expression,
                folder,
                frequency,
                shape,
                since=since,
                choices=choices,
            )
        except DerivedMetricError as e:
            return Response(
                {
                    "ok": False,
                    "errors": [
                        {"code": "derived_evaluation_failed", "message": e.message}
                    ],
                }
            )
        return Response(
            {
                "ok": True,
                "value": evaluation.value,
                "periods": [
                    {
                        "start": period.start.isoformat(),
                        "value": period.value,
                        "skipped": period.skipped,
                        "inputs": period.inputs,
                    }
                    for period in evaluation.periods
                ],
                "inputs": {
                    item.key: [
                        {
                            "id": str(instance.id),
                            "name": instance.name,
                            "folder": instance.folder.name,
                        }
                        for instance in item.instances
                    ]
                    for item in evaluation.resolved
                },
            }
        )

    @method_decorator(cache_page(60 * LONG_CACHE_TTL))
    @action(detail=False, name="Get category choices")
    def category(self, request):
        return Response(dict(MetricDefinition.Category.choices))

    @action(detail=False, name="Get provider choices")
    def provider(self, request):
        providers = (
            MetricDefinition.objects.exclude(provider__isnull=True)
            .exclude(provider="")
            .values_list("provider", flat=True)
            .distinct()
            .order_by("provider")
        )
        return Response({p: p for p in providers})


class MetricInstanceViewSet(BaseModelViewSet):
    model = MetricInstance
    serializers_module = "metrology.serializers"
    filterset_fields = [
        "folder",
        "metric_definition",
        "status",
        "collection_frequency",
        "owner",
        "filtering_labels",
        "organisation_objectives",
        "evidences",
    ]
    search_fields = ["name", "description", "ref_id"]

    def get_queryset(self):
        # `samples` is prefetched so get_latest_sample() reads the cache instead of
        # querying per row. It pulls every sample for the page's instances, which
        # is the right trade at current volumes; if sample counts per instance grow
        # large, swap it for a latest-sample Subquery annotation.
        return (
            super()
            .get_queryset()
            .select_related("folder", "metric_definition__unit", "evidences")
            .prefetch_related(
                "owner", "organisation_objectives", "filtering_labels", "samples"
            )
        )

    @action(detail=False, methods=["get"], url_path="input-candidates")
    def input_candidates(self, request):
        """For the instance form: each input of a metric formula and the
        instances it could read from a domain, so the author can pick one or
        leave some out. Needs the right to add or change metric instances
        there, as creating or editing the instance would."""
        from metrology.series import input_candidates, resolve_definition

        definition = MetricDefinition.objects.filter(
            id=_as_uuid(request.query_params.get("definition"))
        ).first()
        folder = Folder.objects.filter(
            id=_as_uuid(request.query_params.get("folder"))
        ).first()
        if definition is None or folder is None:
            return Response(
                {"error": "definitionOrFolderNotFound"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        allowed = any(
            RoleAssignment.is_access_allowed(
                user=request.user, perm=permission, folder=folder
            )
            for permission in Permission.objects.filter(
                codename__in=["add_metricinstance", "change_metricinstance"]
            )
        )
        if not allowed:
            return Response(status=status.HTTP_403_FORBIDDEN)
        if not definition.reads_metrics:
            return Response({"inputs": []})
        inputs = []
        for spec in definition.inputs or []:
            if not isinstance(spec, dict):
                continue
            target = resolve_definition(spec.get("definition"))
            inputs.append(
                {
                    "key": spec.get("key"),
                    "combine": spec.get("combine") or "one",
                    "definition": (
                        {"id": str(target.id), "name": target.name} if target else None
                    ),
                    "candidates": [
                        {
                            "id": str(instance.id),
                            "name": instance.name,
                            "folder": instance.folder.name,
                        }
                        for instance in (
                            input_candidates(target, folder) if target else []
                        )
                    ],
                }
            )
        return Response({"inputs": inputs})

    COMPOSE_CANDIDATES = 20

    @action(detail=False, methods=["get"], url_path="compose-candidates")
    def compose_candidates(self, request):
        """For the "new computed metric" modal: the instances a formula may
        read, each word of the search matching their name, their metric or
        their domain, or the ones named by ``instance``. Quantitative, not
        deprecated, and readable by the user."""
        from django.db.models import Q

        search = (request.query_params.get("search") or "").strip()
        found = (
            self.get_queryset()
            .filter(metric_definition__category=MetricDefinition.Category.QUANTITATIVE)
            .exclude(status=MetricInstance.Status.DEPRECATED)
        )
        ids = [_as_uuid(i) for i in request.query_params.getlist("instance")]
        if ids:
            # The rows a list selection opens the modal with.
            found = found.filter(id__in=[i for i in ids if i is not None])
        # Every word somewhere: "clicks france" finds "Phishing clicks"
        # in ACME France.
        for word in search.split():
            found = found.filter(
                Q(name__icontains=word)
                | Q(metric_definition__name__icontains=word)
                | Q(folder__name__icontains=word)
            )
        return Response(
            [
                _composable(instance)
                for instance in found.order_by("name", "id")[: self.COMPOSE_CANDIDATES]
            ]
        )

    @action(detail=False, methods=["get"], url_path="compose-context")
    def compose_context(self, request):
        """For the "new computed metric" modal: where the metric may live
        and how often it computes, given the picked instances. The domains
        run from the lowest holding every pick up to the root, keeping those
        the user may create metrics in; the frequency is the least frequent
        pick's. Instances the user may not read are left out, as if they did
        not exist."""
        from metrology.compose import (
            common_domain,
            creatable_in,
            least_frequent,
            readable_instances,
        )

        ids = [_as_uuid(i) for i in request.query_params.getlist("instance")]
        found = readable_instances(request.user, [i for i in ids if i is not None])
        picked = [found[i] for i in ids if i in found]
        lowest = common_domain([instance.folder for instance in picked])
        domains = (
            [
                folder
                for folder in lowest.get_parent_folders(include_self=True)
                if creatable_in(request.user, folder)
            ]
            if lowest
            else []
        )
        return Response(
            {
                "domains": [
                    {"id": str(folder.id), "str": str(folder)} for folder in domains
                ],
                "frequency": least_frequent(
                    [instance.collection_frequency for instance in picked]
                ),
            }
        )

    @action(detail=False, methods=["post"], url_path="compose")
    def compose(self, request):
        """Create a computed metric from instances: the instance and its
        definition (an identical one is reused), in one go."""
        from metrology.compose import CompositionError, compose

        try:
            instance, outcome = compose(request.user, request.data)
        except PermissionError:
            return Response(status=status.HTTP_403_FORBIDDEN)
        except CompositionError as e:
            return Response(e.errors, status=status.HTTP_400_BAD_REQUEST)
        definition = instance.metric_definition
        return Response(
            {
                "id": str(instance.id),
                "definition": {"name": definition.name, "reused": outcome == "reused"},
            },
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=True,
        methods=["get", "put"],
        url_path="composition",
        url_name="composition",
    )
    def composition(self, request, pk=None):
        """A computed metric as the modal edits it, and the edit. Only for a
        formula made of picked instances (compose.is_composable): the answer
        says so, and the page sends the author to the definition otherwise.
        The definition's other users, and whether this user may change it,
        let the modal ask before an edit reaches beyond this metric."""
        from metrology.compose import (
            CompositionError,
            compose,
            is_composable,
            permitted,
            readable_instances,
        )

        instance = self.get_object()
        definition = instance.metric_definition
        if request.method == "PUT":
            if not is_composable(instance):
                return Response(
                    {"error": "metricNotComposable"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            try:
                instance, outcome = compose(request.user, request.data, instance)
            except PermissionError:
                return Response(status=status.HTTP_403_FORBIDDEN)
            except CompositionError as e:
                return Response(e.errors, status=status.HTTP_400_BAD_REQUEST)
            return Response(
                {
                    "id": str(instance.id),
                    "outcome": outcome,
                    "definition": {"name": instance.metric_definition.name},
                    # Before the recomputation the save queued: a page can
                    # follow it until this stamp moves.
                    "last_computed_at": instance.last_computed_at,
                }
            )
        about = {
            "id": str(definition.id),
            "name": definition.name,
            "shared_with": definition.metricinstance_set.exclude(
                id=instance.id
            ).count(),
            "can_change": permitted(
                request.user, ["change_metricdefinition"], definition.folder
            ),
        }
        if not is_composable(instance):
            return Response(
                {
                    "composable": False,
                    "definition": about,
                    "expression": definition.expression,
                }
            )
        picks = {
            key: _as_uuid(choice.get("pick"))
            for key, choice in instance.input_choices.items()
            if isinstance(choice, dict)
        }
        found = readable_instances(request.user, [i for i in picks.values() if i])
        return Response(
            {
                "composable": True,
                "definition": about,
                "name": instance.name,
                "description": instance.description,
                "folder": {"id": str(instance.folder_id), "str": str(instance.folder)},
                "collection_frequency": instance.collection_frequency,
                "target_value": instance.target_value,
                "category": definition.category,
                "choices_definition": [
                    {"ref_id": choice.get("ref_id"), "name": choice.get("name")}
                    for choice in definition.choices_definition or []
                    if isinstance(choice, dict)
                ],
                "unit": str(definition.unit_id) if definition.unit_id else None,
                "higher_is_better": definition.higher_is_better,
                "expression": definition.expression,
                # An input whose instance is gone or not the user's to read
                # comes back without one, for the author to pick again.
                "inputs": [
                    {
                        "key": spec.get("key"),
                        "instance": (
                            _composable(found[picks[spec.get("key")]])
                            if picks.get(spec.get("key")) in found
                            else None
                        ),
                    }
                    for spec in definition.inputs or []
                    if isinstance(spec, dict)
                ],
            }
        )

    @action(detail=True, methods=["post"], url_path="refresh")
    def refresh(self, request, pk=None):
        """Recompute a derived metric now. The task is enqueued, never run
        inline, so a refresh and a scheduled run share one code path and a
        slow worker-side aggregate never sits on a request."""
        from metrology.tasks import compute_derived_metric_task

        instance = self.get_object()
        if not instance.is_derived:
            return Response(
                {"error": "metricNotDerived"}, status=status.HTTP_400_BAD_REQUEST
            )
        permission = Permission.objects.filter(codename="change_metricinstance").first()
        if permission is None or not RoleAssignment.is_access_allowed(
            user=request.user, perm=permission, folder=instance.folder
        ):
            return Response(status=status.HTTP_403_FORBIDDEN)
        # A refresh recomputes a metric formula's whole series.
        compute_derived_metric_task(str(instance.id), full=True)
        return Response({"queued": True}, status=status.HTTP_202_ACCEPTED)

    @method_decorator(cache_page(60 * LONG_CACHE_TTL))
    @action(detail=False, name="Get status choices")
    def status(self, request):
        return Response(dict(MetricInstance.Status.choices))

    @method_decorator(cache_page(60 * LONG_CACHE_TTL))
    @action(detail=False, name="Get collection frequency choices")
    def collection_frequency(self, request):
        return Response(dict(MetricInstance.Frequency.choices))


class CustomMetricSampleViewSet(BaseModelViewSet):
    model = CustomMetricSample
    serializers_module = "metrology.serializers"
    filterset_fields = ["folder", "metric_instance", "evidence_revision"]
    search_fields = ["observation"]
    ordering = ["-timestamp"]  # Most recent first

    def perform_destroy(self, instance):
        # Same refusal as the write serializer: a derived series is its
        # formula's. A period deleted by hand would never be recomputed, and a
        # deleted latest sample would change the next computation's `previous`.
        if instance.metric_instance.is_derived:
            raise serializers.ValidationError(
                {"metric_instance": DERIVED_SAMPLE_READ_ONLY}
            )
        super().perform_destroy(instance)

    def get_queryset(self):
        # raw_value()/display_value() walk metric_instance -> metric_definition to
        # decide how to read the JSON value, and the serializer nests the
        # instance's evidence.
        return (
            super()
            .get_queryset()
            .select_related(
                "folder",
                # EvidenceRevision.__str__ reads self.evidence.name, so the
                # revision alone still costs a query per row.
                "evidence_revision__evidence",
                "metric_instance__metric_definition__unit",
                "metric_instance__evidences",
            )
        )


class DashboardViewSet(BaseModelViewSet):
    model = Dashboard
    serializers_module = "metrology.serializers"
    filterset_fields = ["folder", "filtering_labels"]
    search_fields = ["name", "description", "ref_id"]

    def get_queryset(self):
        # widget_count would otherwise be one COUNT per dashboard.
        return (
            super()
            .get_queryset()
            .select_related("folder")
            .prefetch_related("filtering_labels")
            .annotate(_widget_count=Count("widgets"))
        )


class DashboardWidgetViewSet(BaseModelViewSet):
    model = DashboardWidget
    serializers_module = "metrology.serializers"
    filterset_fields = [
        "folder",
        "dashboard",
        "metric_instance",
        "chart_type",
        "time_range",
        "aggregation",
    ]
    search_fields = ["title"]
    ordering = ["position_y", "position_x"]

    def get_queryset(self):
        # The read serializer walks the metric's definition and unit for every
        # widget and lists each widget's extra series, so a dashboard of N
        # widgets is otherwise N+1 several times over.
        return (
            super()
            .get_queryset()
            .select_related(
                "folder",
                "dashboard",
                "target_content_type",
                "metric_instance__metric_definition__unit",
            )
        )

    @method_decorator(cache_page(60 * LONG_CACHE_TTL))
    @action(detail=False, name="Get chart type choices")
    def chart_type(self, request):
        return Response(dict(DashboardWidget.ChartType.choices))

    @method_decorator(cache_page(60 * LONG_CACHE_TTL))
    @action(detail=False, name="Get time range choices")
    def time_range(self, request):
        return Response(dict(DashboardWidget.TimeRange.choices))

    @method_decorator(cache_page(60 * LONG_CACHE_TTL))
    @action(detail=False, name="Get aggregation choices")
    def aggregation(self, request):
        return Response(dict(DashboardWidget.Aggregation.choices))


class BuiltinMetricSampleViewSet(BaseModelViewSet):
    model = BuiltinMetricSample
    serializers_module = "metrology.serializers"
    filterset_fields = ["content_type", "object_id", "date"]
    search_fields = []
    ordering = ["-date"]

    def get_queryset(self):
        queryset = super().get_queryset()
        # ?model=ComplianceAssessment maps to a ContentType filter.
        model_name = self.request.query_params.get("model")
        if model_name:
            try:
                content_type = ContentType.objects.get(model=model_name.lower())
                queryset = queryset.filter(content_type=content_type)
            except ContentType.DoesNotExist:
                queryset = queryset.none()

        return queryset

    @action(detail=False, methods=["get"], name="Get supported models")
    def supported_models(self, request):
        # chart_types are derived per-metric from each metric's declared type.
        result = {}
        for model_name, metrics in BUILTIN_METRICS.items():
            result[model_name] = {
                key: {
                    "label": str(meta["label"]),
                    "type": meta["type"],
                    "description": str(meta["description"]),
                    "chart_types": METRIC_TYPE_CHART_TYPES.get(meta["type"], []),
                }
                for key, meta in metrics.items()
            }
        return Response(result)

    @action(detail=False, methods=["get"], name="Get metrics for object")
    def for_object(self, request):
        # Query params: object_id + (content_type_id | model).
        object_id = request.query_params.get("object_id")
        if not object_id:
            return Response(
                {"error": "object_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        content_type_id = request.query_params.get("content_type_id")
        model_name = request.query_params.get("model")

        if content_type_id:
            content_type = ContentType.objects.filter(id=content_type_id).first()
        elif model_name:
            content_type = ContentType.objects.filter(model=model_name.lower()).first()
        else:
            return Response(
                {"error": "content_type_id or model is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not content_type:
            return Response(
                {"error": "Content type not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not _user_can_read_target(request.user, content_type, object_id):
            return Response(
                {"error": "Not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        samples = (
            BuiltinMetricSample.objects.filter(
                content_type=content_type, object_id=object_id
            )
            .select_related("content_type")
            .order_by("-date")
        )

        serializer = BuiltinMetricSampleReadSerializer(samples, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["post"], name="Refresh metrics for object")
    def refresh(self, request):
        # Body: object_id + (content_type_id | model).
        object_id = request.data.get("object_id")
        if not object_id:
            return Response(
                {"error": "object_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        content_type_id = request.data.get("content_type_id")
        model_name = request.data.get("model")

        if content_type_id:
            content_type = ContentType.objects.filter(id=content_type_id).first()
        elif model_name:
            content_type = ContentType.objects.filter(model=model_name.lower()).first()
        else:
            return Response(
                {"error": "content_type_id or model is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not content_type:
            return Response(
                {"error": "Content type not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not _user_can_read_target(request.user, content_type, object_id):
            return Response(
                {"error": "Not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        model_class = content_type.model_class()
        try:
            obj = model_class.objects.get(id=object_id)
        except model_class.DoesNotExist:
            return Response(
                {"error": "Object not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        sample, created = BuiltinMetricSample.update_or_create_snapshot(obj)
        serializer = BuiltinMetricSampleReadSerializer(sample)
        return Response(
            {
                "created": created,
                "sample": serializer.data,
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )
