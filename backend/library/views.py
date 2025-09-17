from itertools import chain
import json
from django.db import IntegrityError
from django.db.models import F, Q, IntegerField, OuterRef, Subquery
from rest_framework import viewsets, status
from django.conf import settings

from rest_framework.status import (
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_400_BAD_REQUEST,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_422_UNPROCESSABLE_ENTITY,
)
from rest_framework.parsers import FileUploadParser

from django.http import HttpResponse

import django_filters as df
from core.helpers import get_sorted_requirement_nodes
from core.models import StoredLibrary, LoadedLibrary, Framework
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
    mapping_suggested = df.BooleanFilter(
        method="filter_mapping_suggested",
    )

    def filter_mapping_suggested(self, queryset, name, value):
        """
        Returns StoredLibraries containing at least one mapping with a source framework already loaded
        """

        def _extract_requirement_mappings(content):
            """Extract requirement mappings from library content, handling both dict and list formats."""
            mapping_set = content.get("requirement_mapping_set") or content.get(
                "requirement_mapping_sets", []
            )

            if isinstance(mapping_set, dict):
                return [mapping_set]
            elif isinstance(mapping_set, list):
                return mapping_set
            else:
                return []

        def _has_matching_source_framework(requirement_mappings, loaded_framework_urns):
            """Check if any mapping has a source framework that's loaded."""
            return any(
                mapping.get("source_framework_urn") in loaded_framework_urns
                for mapping in requirement_mappings
            )

        if not value:
            return queryset

        # Get all loaded framework URNs and library URNs in single queries
        loaded_framework_urns = set(Framework.objects.values_list("urn", flat=True))
        loaded_library_urns = set(LoadedLibrary.objects.values_list("urn", flat=True))

        # Early return if no loaded frameworks
        if not loaded_framework_urns:
            return queryset.none()

        # Filter to libraries that have requirement mappings
        queryset_with_mappings = queryset.filter(
            Q(content__requirement_mapping_set__isnull=False)
            | Q(content__requirement_mapping_sets__isnull=False)
        ).exclude(urn__in=loaded_library_urns)

        # Extract libraries with matching source frameworks
        matching_library_pks = []

        for (
            library
        ) in queryset_with_mappings.iterator():  # Use iterator for memory efficiency
            requirement_mappings = _extract_requirement_mappings(library.content)

            if _has_matching_source_framework(
                requirement_mappings, loaded_framework_urns
            ):
                matching_library_pks.append(library.pk)

        return queryset.filter(pk__in=matching_library_pks)

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
        ]


class StoredLibraryViewSet(BaseModelViewSet):
    parser_classes = [FileUploadParser]
    filterset_class = StoredLibraryFilterSet

    # solve issue with URN containing dot, see https://stackoverflow.com/questions/27963899/django-rest-framework-using-dot-in-url
    lookup_value_regex = r"[\w.:-]+"
    model = StoredLibrary
    queryset = StoredLibrary.objects.all()

    search_fields = ["name", "description", "urn", "ref_id"]

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
        except Exception:
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
                data="This library does not include a framework.",
                status=HTTP_400_BAD_REQUEST,
            )

        preview = preview_library(framework)
        return Response(
            get_sorted_requirement_nodes(preview.get("requirement_nodes"), None, None)
        )

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
        return Response(LibraryImporter.NON_DEPRECATED_OBJECT_FIELDS)


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
        except:
            return Response(data="Library not found.", status=HTTP_404_NOT_FOUND)
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
        except:
            return Response(data="Library not found.", status=HTTP_404_NOT_FOUND)

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
        except:
            return Response("Library not found.", status=HTTP_404_NOT_FOUND)
        return Response(lib._objects)

    @action(detail=True, methods=["get"])
    def tree(
        self, request, pk
    ):  # We must ensure that users that are not allowed to read the content of libraries can't have any access to them either from the /api/{URLModel/{library_urn}/tree view or the /api/{URLModel}/{library_urn} view.
        try:
            key = "urn" if pk.startswith("urn:") else "id"
            lib = LoadedLibrary.objects.get(**{key: pk})
        except:
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
        try:
            key = "urn" if pk.startswith("urn:") else "id"
            library = LoadedLibrary.objects.get(**{key: pk})
        except Exception:
            return Response(
                data="libraryNotFound", status=HTTP_404_NOT_FOUND
            )  # Error messages could be returned as JSON instead

        error_msg = library.update()
        if error_msg is None:
            return Response(status=HTTP_204_NO_CONTENT)
        return Response(
            error_msg, status=HTTP_422_UNPROCESSABLE_ENTITY
        )  # We must make at least one error message

    @action(methods=("get",), detail=False, url_path="available-updates")
    def available_updates(self, request):
        return Response(
            LoadedLibrarySerializer(LoadedLibrary.updatable_libraries(), many=True).data
        )
