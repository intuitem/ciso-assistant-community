from itertools import chain
import json
from django.db import IntegrityError
from django.db.models import F, Q, IntegerField, OuterRef, Subquery, Exists
from django.db import models
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, generics
from django.conf import settings

from rest_framework.status import (
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_400_BAD_REQUEST,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
    HTTP_422_UNPROCESSABLE_ENTITY,
)
from rest_framework.parsers import FileUploadParser

from django.http import HttpResponse

import django_filters as df
from core.helpers import get_sorted_requirement_nodes
from core.models import StoredLibrary, LoadedLibrary, Framework, LibraryUpdater
from core.views import BaseModelViewSet, GenericFilterSet
from iam.models import RoleAssignment, Folder, Permission
from library.validators import validate_file_extension
from .helpers import update_translations, update_translations_in_object
from .utils import LibraryImporter, preview_library


from rest_framework.decorators import action
from rest_framework.response import Response
from .serializers import (
    StoredLibraryDetailedSerializer,
    LoadedLibraryDetailedSerializer,
    LoadedLibrarySerializer,
    StoredLibrarySerializer,
)

import structlog

logger = structlog.get_logger(__name__)


class MultiStringFilter(df.CharFilter):
    def filter(self, qs, value):
        values = self.parent.data.getlist(self.field_name)
        if values:
            return qs.filter(**{f"{self.field_name}__in": values})
        return qs


class LibraryMixinFilterSet(GenericFilterSet):
    locale = df.MultipleChoiceFilter(
        choices=[(language[0], language[0]) for language in settings.LANGUAGES],
        method="filter_locale",
    )
    provider = MultiStringFilter(field_name="provider")

    def filter_locale(self, queryset, name, value: list[str]):
        union_qs = Q(locale__in=value)
        for _value in value:
            union_qs |= Q(translations__has_key=_value)

        return queryset.filter(union_qs)


class StoredLibraryFilterSet(LibraryMixinFilterSet):
    object_type = df.MultipleChoiceFilter(
        choices=list(
            zip(
                LibraryImporter.OBJECT_FIELDS,
                LibraryImporter.OBJECT_FIELDS,
            )
        ),
        method="filter_object_type",
    )
    is_loaded = df.BooleanFilter(
        method="filter_is_loaded",
    )
    is_custom = df.BooleanFilter(
        method="filter_is_custom",
    )
    is_update = df.BooleanFilter(
        method="filter_is_update",
    )

    def filter_is_loaded(self, queryset, name, value):
        return queryset.filter(is_loaded=value)

    def filter_is_custom(self, queryset, name, value):
        return queryset.filter(builtin=not value)

    def filter_is_update(self, queryset, name, value):
        return queryset.annotate(
            _is_update=Exists(
                LoadedLibrary.objects.filter(
                    urn=OuterRef("urn"), version__lt=OuterRef("version")
                )
            )
        ).filter(_is_update=value)

    def filter_object_type(self, queryset, name, value: list[str]):
        # For backward compatibility
        if "risk_matrices" in value:
            value.append("risk_matrix")
        if "requirement_mapping_sets" in value:
            value.append("requirement_mapping_set")
        if "frameworks" in value:
            value.append("framework")
        union_qs = Q()
        _value = {f"content__{v}__isnull": False for v in value}
        for item in _value:
            union_qs |= Q(**{item: _value[item]})
        return queryset.filter(union_qs)

    class Meta:
        model = StoredLibrary
        fields = [
            "urn",
            "locale",
            "version",
            "packager",
            "provider",
            "object_type",
            "filtering_labels",
        ]


class StoredLibraryViewSet(BaseModelViewSet):
    parser_classes = [FileUploadParser]
    filterset_class = StoredLibraryFilterSet

    # solve issue with URN containing dot, see https://stackoverflow.com/questions/27963899/django-rest-framework-using-dot-in-url
    lookup_value_regex = r"[\w.:-]+"
    model = StoredLibrary
    queryset = StoredLibrary.objects.all()

    search_fields = ["name", "description", "urn", "ref_id"]

    def get_queryset(self) -> models.query.QuerySet:
        return super().get_queryset().prefetch_related("filtering_labels")

    def get_serializer_class(self):
        if self.action == "list":
            return StoredLibrarySerializer
        return StoredLibraryDetailedSerializer

    def retrieve(self, request, *args, pk, **kwargs):
        if "view_storedlibrary" not in request.user.permissions:
            return Response(status=HTTP_403_FORBIDDEN)
        try:
            key = "urn" if pk.startswith("urn:") else "id"
            lib = StoredLibrary.objects.get(
                **{key: pk}
            )  # There is no "locale" value involved in the fetch + we have to handle the exception if the pk urn doesn't exist
        except:
            return Response(data="Library not found.", status=HTTP_404_NOT_FOUND)
        data = StoredLibrarySerializer(lib).data
        return Response(data)

    @action(detail=True, methods=["get"])
    def content(self, request, pk):
        try:
            key = "urn" if pk.startswith("urn:") else "id"
            lib = StoredLibrary.objects.get(**{key: pk})
        except:
            return Response("Library not found.", status=HTTP_404_NOT_FOUND)
        return Response(update_translations(lib.content))

    def destroy(self, request, *args, pk, **kwargs):
        if not RoleAssignment.is_access_allowed(
            user=request.user,
            perm=Permission.objects.get(codename="delete_storedlibrary"),
            folder=Folder.get_root_folder(),
        ):
            return Response(status=HTTP_403_FORBIDDEN)

        try:
            key = "urn" if pk.startswith("urn:") else "id"
            lib = StoredLibrary.objects.get(**{key: pk})
        except:
            return Response(data="Library not found.", status=HTTP_404_NOT_FOUND)

        lib.delete()
        return Response(status=HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"])
    def unload(self, request, pk):
        if not RoleAssignment.is_access_allowed(
            user=request.user,
            perm=Permission.objects.get(codename="delete_loadedlibrary"),
            folder=Folder.get_root_folder(),
        ):
            return Response(status=HTTP_403_FORBIDDEN)

        try:
            key = "urn" if pk.startswith("urn:") else "id"
            libraries = StoredLibrary.objects.filter(**{key: pk})
            library = max(libraries, key=lambda lib: lib.version)
        except:
            return Response(data="Library not found.", status=HTTP_404_NOT_FOUND)

        loaded_library = library.get_loaded_library()
        if loaded_library is None:
            return Response(data="Loaded library not found.", status=HTTP_404_NOT_FOUND)

        try:
            loaded_library.delete()
        except:
            return Response(
                data="Loaded library can't be deleted because it's currently being used.",
                status=HTTP_409_CONFLICT,
            )

        # Delete a libary if it's a "fake" one (one created by the storelibraries django command to prevent invisible loaded libraries.)
        if not library.content:
            library.delete()

        return Response({"status": "success"})

    @action(detail=True, methods=["post"], url_path="import")
    def import_library(self, request, pk):
        if not RoleAssignment.is_access_allowed(
            user=request.user,
            perm=Permission.objects.get(codename="add_loadedlibrary"),
            folder=Folder.get_root_folder(),
        ):
            return Response(status=HTTP_403_FORBIDDEN)

        try:
            key = "urn" if pk.startswith("urn:") else "id"
            libraries = StoredLibrary.objects.filter(  # The get method raise an exception if multiple objects are found
                **{key: pk}
            )  # This is only fetching the lib by URN without caring about the locale or the version, this must change in the future.
            library = max(
                libraries, key=lambda lib: lib.version
            )  # Which mean we can only import the latest version of the library, if that so library that has a most recent version stored shouldn't be displayed and should even be erased from the database
        except:
            return Response(data="Library not found.", status=HTTP_404_NOT_FOUND)

        try:
            error_msg = library.load()
            if error_msg is not None:
                return Response(
                    {"status": "error", "error": error_msg},
                    status=HTTP_400_BAD_REQUEST,
                )  # This can cause translation issues
            return Response({"status": "success"})
        except Exception as e:
            logger.error("Failed to load library", error=e)
            return Response(
                {"error": "Failed to load library"},  # This must translated
                status=HTTP_422_UNPROCESSABLE_ENTITY,
            )

    @action(detail=True, methods=["get"])
    def tree(self, request, pk):
        try:
            key = "urn" if pk.startswith("urn:") else "id"
            lib = StoredLibrary.objects.get(**{key: pk})
        except:
            return Response(data="Library not found.", status=HTTP_404_NOT_FOUND)

        library_objects = lib.content  # We may need caching for this
        if not (framework := library_objects.get("framework")):
            return Response(
                data="This library doesn't contain any framework.",
                status=HTTP_400_BAD_REQUEST,
            )

        preview = preview_library(framework)
        requirement_nodes = preview.get("requirement_nodes")
        return Response(get_sorted_requirement_nodes(requirement_nodes, None, None))

    @action(detail=False, methods=["post"], url_path="upload")
    def upload_library(self, request):
        if not request.data:
            return HttpResponse(
                json.dumps({"error": "noFileDetected"}), status=HTTP_400_BAD_REQUEST
            )

        try:
            attachment = request.FILES["file"]
            validate_file_extension(attachment)
            # Use safe_load to prevent arbitrary code execution.

            content = attachment.read()  # Should we read it chunck by chunck or ensure that the file size of the library content is reasonnable before reading ?

            try:
                library = StoredLibrary.store_library_content(content)
                if library is not None:
                    library.load()

                return Response(
                    StoredLibrarySerializer(library).data, status=HTTP_201_CREATED
                )
            except ValueError as e:
                logger.error("Failed to store library content", error=e)
                return HttpResponse(
                    json.dumps({"error": "Failed to store library content."}),
                    status=HTTP_422_UNPROCESSABLE_ENTITY,
                )

        except IntegrityError:
            return HttpResponse(
                json.dumps({"error": "libraryAlreadyLoadedError"}),
                status=HTTP_400_BAD_REQUEST,
            )
        except:
            return HttpResponse(
                json.dumps({"error": "invalidLibraryFileError"}),
                status=HTTP_400_BAD_REQUEST,
            )

    @action(detail=False, name="Get provider choices")
    def provider(self, request):
        providers = set(
            StoredLibrary.objects.filter(provider__isnull=False).values_list(
                "provider", flat=True
            )
        )
        return Response({p: p for p in providers})

    @action(detail=False, name="Get locale choices")
    def locale(self, request):
        locales = set(
            chain.from_iterable([l.get_locales for l in StoredLibrary.objects.all()])
        )
        return Response({l: l for l in locales})

    @action(detail=False, name="Get all library objects types")
    def object_type(self, request):
        return Response(
            [
                f
                for f in LibraryImporter.NON_DEPRECATED_OBJECT_FIELDS
                if "requirement_mapping_sets" not in f
            ]
        )


class LoadedLibraryFilterSet(LibraryMixinFilterSet):
    object_type = df.MultipleChoiceFilter(
        choices=list(
            zip(
                LibraryImporter.OBJECT_FIELDS,
                LibraryImporter.OBJECT_FIELDS,
            )
        ),
        method="filter_object_type",
    )
    has_update = df.BooleanFilter(method="filter_has_update")

    def filter_has_update(self, queryset, name, value):
        # Build a subquery to get the highest version for the given urn.
        max_version_subquery = (
            StoredLibrary.objects.filter(urn=OuterRef("urn"))
            .order_by("-version")
            .values("version")[:1]
        )
        # Annotate each LoadedLibrary with max_version from StoredLibrary.
        qs = queryset.annotate(
            max_version=Subquery(max_version_subquery, output_field=IntegerField())
        )
        if value:
            # Filter for libraries that have an update: max_version > version.
            return qs.filter(max_version__gt=F("version"))
        else:
            # Filter for libraries that do not have an update.
            return qs.filter(
                Q(max_version__isnull=True) | Q(max_version__lte=F("version"))
            )

    def filter_object_type(self, queryset, name, value: list[str]):
        value_set = set(value)

        risk_matrix_keys = {"risk_matrix", "risk_matrices"}
        requirement_mapping_set_keys = {
            "requirement_mapping_set",
            "requirement_mapping_sets",
        }
        framework_set = {"framework", "frameworks"}

        # For backward compatibility
        for key_set in [risk_matrix_keys, requirement_mapping_set_keys, framework_set]:
            if value_set & key_set:
                value_set |= key_set

        value = list(value_set)
        union_qs = Q()
        _value = {
            k: v
            for v in value
            for k, v in zip(
                (f"objects_meta__{v}__isnull", f"objects_meta__{v}__gte"), (False, 1)
            )
        }
        for item in _value:
            union_qs |= Q(**{item: _value[item]})

        return queryset.filter(union_qs)

    class Meta:
        model = LoadedLibrary
        fields = [
            "urn",
            "locale",
            "version",
            "packager",
            "provider",
            "object_type",
            "has_update",
        ]


class LoadedLibraryViewSet(BaseModelViewSet):
    serializer_class = LoadedLibrarySerializer
    filterset_class = LoadedLibraryFilterSet

    lookup_value_regex = r"[\w.:-]+"
    model = LoadedLibrary
    queryset = LoadedLibrary.objects.all()

    search_fields = ["name", "description", "urn", "ref_id"]

    def get_serializer_class(self):
        if self.action == "list":
            return LoadedLibrarySerializer
        return LoadedLibraryDetailedSerializer

    def retrieve(self, request, *args, pk, **kwargs):
        if "view_loadedlibrary" not in request.user.permissions:
            return Response(status=HTTP_403_FORBIDDEN)
        try:
            key = "urn" if pk.startswith("urn:") else "id"
            lib = LoadedLibrary.objects.get(
                **{key: pk}
            )  # There is no "locale" value involved in the fetch + we have to handle the exception if the pk urn doesn't exist
        except LoadedLibrary.DoesNotExist:
            return Response(data="Library not found.", status=HTTP_404_NOT_FOUND)
        except Exception:
            logger.error("Error retrieving library", pk=pk, exc_info=True)
            return Response(
                data="Error retrieving library.", status=HTTP_400_BAD_REQUEST
            )
        data = LoadedLibraryDetailedSerializer(lib).data
        data["objects"] = lib._objects
        return Response(data)

    def destroy(self, request, *args, pk, **kwargs):
        if not RoleAssignment.is_access_allowed(
            user=request.user,
            perm=Permission.objects.get(codename="delete_loadedlibrary"),
            folder=Folder.get_root_folder(),
        ):
            return Response(status=HTTP_403_FORBIDDEN)

        try:
            key = "urn" if pk.startswith("urn:") else "id"
            lib = LoadedLibrary.objects.get(**{key: pk})
        except LoadedLibrary.DoesNotExist:
            return Response(data="Library not found.", status=HTTP_404_NOT_FOUND)
        except Exception:
            logger.error("Error unloading library", pk=pk, exc_info=True)
            return Response(
                data="Error unloading library.", status=HTTP_400_BAD_REQUEST
            )

        if lib.reference_count != 0:
            return Response(
                data="Library cannot be deleted because it has references.",
                status=HTTP_400_BAD_REQUEST,
            )

        lib.delete()
        return Response(status=HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["get"])
    def content(self, request, pk):
        try:
            key = "urn" if pk.startswith("urn:") else "id"
            lib = LoadedLibrary.objects.get(**{key: pk})
        except Exception:
            return Response("Library not found.", status=HTTP_404_NOT_FOUND)
        return Response(lib._objects)

    @action(detail=True, methods=["get"])
    def tree(
        self, request, pk
    ):  # We must ensure that users that are not allowed to read the content of libraries can't have any access to them either from the /api/{URLModel/{library_urn}/tree view or the /api/{URLModel}/{library_urn} view.
        try:
            key = "urn" if pk.startswith("urn:") else "id"
            lib = LoadedLibrary.objects.get(**{key: pk})
        except Exception:
            return Response(data="Library not found.", status=HTTP_404_NOT_FOUND)

        if not lib.frameworks.exists():
            return Response(
                data="This library doesn't contain any framework.",
                status=HTTP_404_NOT_FOUND,
            )

        framework = lib.frameworks.first()
        requirement_nodes = framework.requirement_nodes.all()
        return Response(get_sorted_requirement_nodes(requirement_nodes, None, None))

    @action(detail=True, methods=["get"], url_path="update")
    def _update(self, request, pk):
        if not RoleAssignment.is_access_allowed(
            user=request.user,
            perm=Permission.objects.get(
                codename="add_loadedlibrary"
            ),  # We should use either this permission or making a new permission "update_loadedlibrary"
            folder=Folder.get_root_folder(),
        ):
            return Response(status=HTTP_403_FORBIDDEN)
        strategy = request.query_params.get("action")
        if strategy and strategy not in ["rule_of_three", "reset", "clamp"]:
            return Response(
                {
                    "error": "Invalid strategy. Must be one of 'rule_of_three', 'reset', 'clamp'."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            key = "urn" if pk.startswith("urn:") else "id"
            library = LoadedLibrary.objects.get(**{key: pk})
        except Exception:
            return Response(
                data="libraryNotFound", status=HTTP_404_NOT_FOUND
            )  # Error messages could be returned as JSON instead
        try:
            error_msg = library.update(strategy=strategy)
        except LibraryUpdater.ScoreChangeDetected as e:
            # Score boundaries changed - need user decision
            return Response(
                {
                    "error": "score_change_detected",
                    "framework_urn": e.framework_urn,
                    "prev_scores": e.prev_scores,
                    "new_scores": e.new_scores,
                    "affected_assessments": e.affected_assessments,
                    "strategies": e.strategies,
                    "message": "Score boundaries have changed. Please choose a strategy.",
                },
                status=status.HTTP_409_CONFLICT,
            )
        except Exception as e:
            logger.error("Failed to update library", error=e)
            return Response(
                {"error": "libraryUpdateFailed"},
                status=HTTP_422_UNPROCESSABLE_ENTITY,
            )
        if error_msg is None:
            return Response({"status": "success"})
        else:
            return Response(
                {"status": "error", "error": error_msg},
                status=HTTP_400_BAD_REQUEST,
            )

    @action(methods=("get",), detail=False, url_path="available-updates")
    def available_updates(self, request):
        return Response(
            LoadedLibrarySerializer(LoadedLibrary.updatable_libraries(), many=True).data
        )


class MappingLibrariesList(generics.ListAPIView):
    filterset_fields = {
        "provider": ["exact"],
        "packager": ["exact"],
        "locale": ["exact"],
    }
    search_fields = ["name", "description", "urn", "ref_id"]

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    ordering_fields = "__all__"

    serializer_class = StoredLibrarySerializer

    def get_queryset(self):
        """RBAC not automatic as we don't inherit from BaseModelViewSet -> enforce it explicitly"""
        qs = StoredLibrary.objects.filter(
            Q(content__requirement_mapping_set__isnull=False)
            | Q(content__requirement_mapping_sets__isnull=False)
        ).distinct()

        viewable_libraries, _, _ = RoleAssignment.get_accessible_object_ids(
            Folder.get_root_folder(),
            self.request.user,
            StoredLibrary,
        )
        return qs.filter(id__in=viewable_libraries)
