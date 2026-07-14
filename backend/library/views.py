from itertools import chain
import json
import re
import uuid

import yaml
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import F, Q, IntegerField, OuterRef, Subquery, Exists
from django.db import models
from django.utils.timezone import now
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
    HTTP_500_INTERNAL_SERVER_ERROR,
    HTTP_504_GATEWAY_TIMEOUT,
)
from rest_framework.parsers import (
    FileUploadParser,
    FormParser,
    JSONParser,
    MultiPartParser,
)

from django.http import HttpResponse

import django_filters as df
from core.excel import ExcelUploadHandler
from core.helpers import get_sorted_requirement_nodes
from core.models import (
    ComplianceAssessment,
    Framework,
    LibraryDraft,
    LibraryUpdater,
    LoadedLibrary,
    Question,
    QuestionChoice,
    RequirementNode,
    StoredLibrary,
    match_urn,
)
from core.sandbox import SandboxTimeoutError, SandboxViolationError
from core.views import BaseModelViewSet, GenericFilterSet
from iam.models import RoleAssignment, Folder, Permission
from library import builder
from library import framework_editor as fw_editor
from library.validators import validate_file_extension
from .helpers import update_translations
from .utils import LibraryImporter, preview_library


from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.response import Response
from .serializers import (
    LibraryDraftReadSerializer,
    LibraryDraftWriteSerializer,
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
    is_preset = df.BooleanFilter(
        method="filter_is_preset",
    )

    def filter_is_preset(self, queryset, name, value):
        if value:
            return queryset.filter(content__preset__isnull=False)
        return queryset.exclude(content__preset__isnull=False)

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


import magic

MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MB


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

    def get_serializer_class(self, **kwargs):
        if self.action == "list":
            return StoredLibrarySerializer
        return StoredLibraryDetailedSerializer

    def retrieve(self, request, *args, pk, **kwargs):
        # Folder-scoped RBAC like any other object read (never a bare
        # permission-possession check); unreadable == missing.
        lib = _get_readable_stored_library(request.user, pk)
        if lib is None:
            return Response(data="Library not found.", status=HTTP_404_NOT_FOUND)
        data = StoredLibrarySerializer(lib).data
        return Response(data)

    @action(detail=True, methods=["get"])
    def content(self, request, pk):
        lib = _get_readable_stored_library(request.user, pk)
        if lib is None:
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

        # Loading implies reading the source: same folder-scoped check as
        # every other stored-library read (latest version when several).
        library = _get_readable_stored_library(request.user, pk)
        if library is None:
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
        lib = _get_readable_stored_library(request.user, pk)
        if lib is None:
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
        if not RoleAssignment.is_access_allowed(
            user=request.user,
            perm=Permission.objects.get(codename="add_storedlibrary"),
            folder=Folder.get_root_folder(),
        ):
            return Response(status=HTTP_403_FORBIDDEN)

        if not request.data:
            return HttpResponse(
                json.dumps({"error": "noFileDetected"}), status=HTTP_400_BAD_REQUEST
            )

        library = None

        try:
            attachment = request.FILES["file"]
            validate_file_extension(attachment)

            if attachment.size > MAX_UPLOAD_SIZE:
                return HttpResponse(
                    json.dumps({"error": "fileTooLarge"}), status=HTTP_400_BAD_REQUEST
                )

            # Check MIME type
            mime = magic.from_buffer(attachment.read(2048), mime=True)
            attachment.seek(0)

            allowed_mimes = [
                "text/plain",
                "application/yaml",
                "text/yaml",
                "application/x-yaml",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ]

            if mime not in allowed_mimes:
                logger.warning(
                    "Invalid MIME type",
                    expected_mime=" or ".join(allowed_mimes),
                    actual_mime=mime,
                    filename=attachment.name,
                )
                if not (
                    mime == "text/plain" and attachment.name.endswith((".yaml", ".yml"))
                ) and not (
                    mime in ("application/octet-stream", "application/zip")
                    and attachment.name.endswith(".xlsx")
                ):
                    return HttpResponse(
                        json.dumps({"error": "invalidFileFormat"}),
                        status=HTTP_400_BAD_REQUEST,
                    )

            try:
                if attachment.name.endswith(".xlsx"):
                    if mime not in (
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        "application/octet-stream",
                        "application/zip",
                    ):
                        return HttpResponse(
                            json.dumps({"error": "invalidFileFormat"}),
                            expected_mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            actual_mime=mime,
                            status=HTTP_400_BAD_REQUEST,
                        )

                    # Handle Excel conversion with sandbox
                    try:
                        # Get compatibility mode from request (default 0)
                        try:
                            compat_mode = int(request.POST.get("compat_mode", 0))
                            if compat_mode not in settings.LIBRARY_COMPATIBILITY_MODES:
                                return HttpResponse(
                                    json.dumps(
                                        {
                                            "error": "invalidCompatMode",
                                            "allowed_modes": list(
                                                settings.LIBRARY_COMPATIBILITY_MODES.keys()
                                            ),
                                        }
                                    ),
                                    status=HTTP_400_BAD_REQUEST,
                                )
                        except ValueError, TypeError:
                            compat_mode = 0

                        # Initialize handler (uses ENABLE_SANDBOX setting automatically)
                        handler = ExcelUploadHandler(
                            max_file_size=MAX_UPLOAD_SIZE,
                            compat_mode=compat_mode,
                            memory_limit_mb=512,
                            time_limit_sec=30,
                        )

                        result = handler.process_upload(attachment)

                        if result["status"] != 200:
                            error_map = {
                                400: "invalidExcelFile",
                                413: "fileTooLarge",
                                504: "processingTimeout",
                                500: "processingError",
                            }
                            error_code = error_map.get(
                                result["status"], "invalidExcelFile"
                            )

                            # Log security violations specifically
                            if result["status"] == 400:
                                logger.warning(
                                    "Excel security violation detected",
                                    filename=attachment.name,
                                    error=result.get("error"),
                                )

                            error_payload = {"error": error_code}
                            detail = result.get("detail") or result.get("error")
                            if detail:
                                error_payload["detail"] = detail

                            return HttpResponse(
                                json.dumps(error_payload),
                                status=result["status"],
                            )

                        # Convert YAML string to bytes for storage
                        content = result["yaml"].encode("utf-8")

                    except SandboxViolationError as e:
                        logger.warning(
                            "Security violation in Excel upload",
                            error=e,
                            filename=attachment.name,
                            user=request.user.username,
                            exc_info=True,
                        )
                        return HttpResponse(
                            json.dumps({"error": "maliciousFileDetected"}),
                            status=HTTP_400_BAD_REQUEST,
                        )
                    except SandboxTimeoutError:
                        logger.warning(
                            "Excel conversion timeout",
                            filename=attachment.name,
                            exc_info=True,
                        )
                        return HttpResponse(
                            json.dumps({"error": "processingTimeout"}),
                            status=HTTP_504_GATEWAY_TIMEOUT,
                        )
                    except FileNotFoundError as e:
                        logger.error(f"Conversion script not found: {e}", exc_info=True)
                        return HttpResponse(
                            json.dumps({"error": "serverConfigurationError"}),
                            status=HTTP_500_INTERNAL_SERVER_ERROR,
                        )

                else:
                    # YAML file - read directly
                    content = attachment.read()

                dry_run = request.query_params.get("dry_run", "false").lower() == "true"

                # Store the library content (YAML bytes)
                library, error = StoredLibrary.store_library_content(
                    content, dry_run=dry_run
                )
                if error is not None:
                    return HttpResponse(
                        json.dumps({"error": error}),
                        status=HTTP_422_UNPROCESSABLE_ENTITY,
                    )

                if dry_run:
                    logger.info("Dry run library upload successful")
                    return Response(library)

                if library is not None:
                    logger.info("Attempting to load newly uploaded library")
                    # Check if a LoadedLibrary already exists for this urn/locale.
                    # If so, this is an update scenario: the StoredLibrary must be
                    # kept so the user can trigger the update via the _update endpoint.
                    already_loaded = LoadedLibrary.objects.filter(
                        urn=library.urn
                    ).exists()

                    try:
                        load_error = library.load()
                    except (ValueError, ValidationError) as load_exc:
                        validation_detail = load_exc.args[0] if load_exc.args else None
                        logger.error(
                            "Validation error while loading newly uploaded library",
                            urn=library.urn,
                            error=validation_detail,
                        )
                        if not already_loaded:
                            library.delete()
                        return HttpResponse(
                            json.dumps(
                                {
                                    "error": "libraryLoadFailed",
                                    "detail": validation_detail
                                    or "Invalid library content.",
                                }
                            ),
                            status=HTTP_422_UNPROCESSABLE_ENTITY,
                        )
                    except Exception as load_exc:
                        logger.exception(
                            "Unexpected exception while loading newly uploaded library",
                            urn=library.urn,
                        )
                        if not already_loaded:
                            library.delete()
                        return HttpResponse(
                            json.dumps(
                                {
                                    "error": "libraryLoadFailed",
                                    "detail": "An unexpected error occurred while loading the library.",
                                }
                            ),
                            status=HTTP_422_UNPROCESSABLE_ENTITY,
                        )

                    if load_error is not None:
                        if not already_loaded:
                            logger.error(
                                "Failed to load newly uploaded library, removing stored entry",
                                error=load_error,
                                urn=library.urn,
                            )
                            library.delete()
                            return HttpResponse(
                                json.dumps(
                                    {
                                        "error": "libraryLoadFailed",
                                        "detail": load_error,
                                    }
                                ),
                                status=HTTP_422_UNPROCESSABLE_ENTITY,
                            )
                        else:
                            logger.info(
                                "Library already loaded, stored new version for update",
                                urn=library.urn,
                            )
                            return Response(
                                {
                                    **StoredLibrarySerializer(library).data,
                                    "warning": "libraryStoredForUpdate",
                                },
                                status=HTTP_201_CREATED,
                            )

                return Response(
                    StoredLibrarySerializer(library).data, status=HTTP_201_CREATED
                )

            except ValueError as e:
                logger.error("Failed to store library content", error=e)
                if (
                    library is not None
                    and not LoadedLibrary.objects.filter(urn=library.urn).exists()
                ):
                    library.delete()
                return HttpResponse(
                    json.dumps({"error": "Failed to store library content."}),
                    status=HTTP_422_UNPROCESSABLE_ENTITY,
                )

        except IntegrityError:
            return HttpResponse(
                json.dumps({"error": "libraryAlreadyLoadedError"}),
                status=HTTP_400_BAD_REQUEST,
            )
        except Exception:
            logger.exception("Upload library failed")
            if (
                library is not None
                and not LoadedLibrary.objects.filter(urn=library.urn).exists()
            ):
                library.delete()
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

    def get_serializer_class(self, **kwargs):
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
                status=HTTP_400_BAD_REQUEST,
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
                status=HTTP_409_CONFLICT,
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


def _get_stored_library(pk_or_urn) -> StoredLibrary | None:
    """Fetch a stored library by id or URN; latest version when several."""
    if not pk_or_urn:
        return None
    key = "urn" if str(pk_or_urn).startswith("urn:") else "id"
    try:
        libraries = list(StoredLibrary.objects.filter(**{key: pk_or_urn}))
    except ValidationError, ValueError:
        return None
    if not libraries:
        return None
    return max(libraries, key=lambda lib: lib.version)


def _get_readable_stored_library(user, pk_or_urn) -> StoredLibrary | None:
    """RBAC-checked variant of _get_stored_library.

    Reading a stored library follows the regular folder-scoped RBAC model
    like any other object; an unreadable library is indistinguishable from
    a missing one. (Stored rows are is_published, so any role holding
    view_storedlibrary keeps seeing the catalog — the check only bites
    where visibility is actually restricted.)
    """
    stored = _get_stored_library(pk_or_urn)
    if stored is not None and RoleAssignment.is_object_readable(
        user, StoredLibrary, stored.id
    ):
        return stored
    return None


def _get_readable_draft(user, pk) -> "LibraryDraft | None":
    """Fetch a LibraryDraft by id, RBAC-checked; unreadable == missing."""
    if not pk:
        return None
    try:
        draft = LibraryDraft.objects.filter(id=pk).first()
    except ValidationError, ValueError:
        return None
    if draft is not None and RoleAssignment.is_object_readable(
        user, LibraryDraft, draft.id
    ):
        return draft
    return None


class LibraryDraftViewSet(BaseModelViewSet):
    """
    Interactive library packager. A draft is a document that serializes to
    the same library YAML the tools/ Excel converter produces; publishing
    feeds that YAML to the existing stored-library loader — the single
    writer of live referential objects. The builder never touches live
    Framework/ReferenceControl/Threat/... rows itself.
    """

    model = LibraryDraft
    filterset_fields = ["folder", "packager", "locale"]
    search_fields = ["name", "description", "packager", "ref_id"]

    # Detail actions default to the perms_map of their HTTP method (POST →
    # add_librarydraft); align them with what they actually do to the draft.
    permission_overrides = {
        "publish": "change_librarydraft",
        "import_objects": "change_librarydraft",
        "validate": "view_librarydraft",
        "conflicts": "view_librarydraft",
        "export": "view_librarydraft",
        "framework_editor_preview": "view_librarydraft",
        "add_framework": "change_librarydraft",
        "upsert_object": "change_librarydraft",
        "delete_object": "change_librarydraft",
        "preset_editor_preview": "view_librarydraft",
        "reference_catalog": "view_librarydraft",
    }

    # Object kinds editable through the generic upsert action; frameworks go
    # through the visual framework editor, mapping sets have their own tooling.
    UPSERTABLE_FIELDS = (
        "threats",
        "reference_controls",
        "risk_matrices",
        "metric_definitions",
    )

    def get_serializer_class(self, **kwargs):
        if self.action in ("create", "update", "partial_update"):
            return LibraryDraftWriteSerializer
        return LibraryDraftReadSerializer

    @action(detail=False, methods=["get"], url_path="check-identity")
    def check_identity(self, request):
        """Advisory identity check for the creation form, before a draft exists.

        Collection actions bypass the object-level RBAC machinery, so the
        check is explicit — and the answer spans the whole corpus (stored,
        loaded, drafts), so it is reserved for root-level draft creators.
        """
        if not RoleAssignment.is_access_allowed(
            user=request.user,
            perm=Permission.objects.get(codename="add_librarydraft"),
            folder=Folder.get_root_folder(),
        ):
            return Response(status=HTTP_403_FORBIDDEN)
        packager = request.query_params.get("packager", "")
        ref_id = request.query_params.get("ref_id", "")
        if not (
            re.match(LibraryDraft.IDENTITY_REGEX, packager)
            and re.match(LibraryDraft.IDENTITY_REGEX, ref_id)
        ):
            return Response(
                {"error": "invalidLibraryIdentity"}, status=HTTP_400_BAD_REQUEST
            )
        exclude_draft = request.query_params.get("exclude_draft")
        if exclude_draft:
            try:
                uuid.UUID(str(exclude_draft))
            except ValueError, TypeError:
                return Response(
                    {"error": "invalidExcludeDraft"}, status=HTTP_400_BAD_REQUEST
                )
        return Response(
            {
                "urn": builder.library_urn(packager, ref_id),
                "conflicts": builder.check_identity_conflicts(
                    packager,
                    ref_id,
                    exclude_draft_id=exclude_draft,
                    user=request.user,
                ),
            }
        )

    @action(detail=True, methods=["get"])
    def conflicts(self, request, pk):
        draft = self.get_object()
        if draft.identity_locked:
            # The identity is published: hitting the existing stored/loaded
            # rows again is the update-by-URN path, not a conflict.
            return Response({"identity_locked": True, "conflicts": []})
        return Response(
            {
                "identity_locked": False,
                "conflicts": builder.check_identity_conflicts(
                    draft.packager,
                    draft.ref_id,
                    exclude_draft_id=draft.id,
                    user=request.user,
                ),
            }
        )

    @action(detail=True, methods=["get"])
    def validate(self, request, pk):
        """Dry-run the loader-level validation and reference integrity checks."""
        draft = self.get_object()
        return Response(builder.validate_draft_document(draft, user=request.user))

    @action(detail=True, methods=["get"])
    def export(self, request, pk):
        """Pure GET, no state change. A published-and-clean draft exports as
        the canonical artifact; anything else is a working copy whose URNs may
        still change, so the filename says so."""
        draft = self.get_object()
        library_yaml = yaml.safe_dump(
            draft.to_library_dict(), sort_keys=False, allow_unicode=True
        )
        response = HttpResponse(library_yaml, content_type="application/yaml")
        safe_ref = re.sub(r"[^A-Za-z0-9._-]+", "-", draft.ref_id or "library")
        clean = draft.identity_locked and not draft.has_unpublished_changes
        suffix = "" if clean else "-draft"
        response["Content-Disposition"] = (
            f'attachment; filename="{safe_ref}-v{draft.version}{suffix}.yaml"'
        )
        return response

    @action(detail=False, methods=["post"])
    def adopt(self, request):
        """Import a custom library into a draft, identity preserved.

        The inverse of publish (YAML → draft): the library is then maintained
        in the builder and re-published as updates of the same URN family.
        Built-in libraries can never acquire an identity-preserving draft.
        """
        folder_id = request.data.get("folder")
        try:
            folder = (
                Folder.objects.get(id=folder_id)
                if folder_id
                else Folder.get_root_folder()
            )
        except Folder.DoesNotExist, ValidationError, ValueError:
            return Response({"error": "folderNotFound"}, status=HTTP_404_NOT_FOUND)
        if not RoleAssignment.is_access_allowed(
            user=request.user,
            perm=Permission.objects.get(codename="add_librarydraft"),
            folder=folder,
        ):
            return Response(status=HTTP_403_FORBIDDEN)

        if request.data.get("framework"):
            return self._adopt_live_framework(request, folder)

        source = _get_readable_stored_library(
            request.user, request.data.get("stored_library")
        )
        if source is None:
            return Response({"error": "libraryNotFound"}, status=HTTP_404_NOT_FOUND)
        if source.builtin:
            return Response(
                {"error": "builtinLibrariesCannotBeAdopted"},
                status=HTTP_400_BAD_REQUEST,
            )
        existing_draft = LibraryDraft.objects.filter(urn=source.urn).first()
        if existing_draft is not None:
            return Response(
                {"error": "draftAlreadyExists", "draft": str(existing_draft.id)},
                status=HTTP_409_CONFLICT,
            )

        content = builder.normalize_objects(source.content or {})
        if shape_errors := builder.check_document_shape(content):
            # Adoption bypasses the write serializer: don't seed a draft
            # from a structurally malformed stored library.
            return Response(
                {"error": "adoptInvalidContent", "details": shape_errors},
                status=HTTP_422_UNPROCESSABLE_ENTITY,
            )

        urn_groups = match_urn(source.urn)
        try:
            # atomic + unique urn: a concurrent adopt of the same library that
            # slipped past the existence check above loses here cleanly.
            with transaction.atomic():
                draft = LibraryDraft.objects.create(
                    name=source.name,
                    description=source.description,
                    folder=folder,
                    packager=source.packager
                    or (urn_groups[0] if urn_groups else "unknown"),
                    ref_id=source.ref_id or source.urn.rsplit(":", 1)[-1],
                    locale=source.locale,
                    version=source.version,
                    provider=source.provider,
                    copyright=source.copyright,
                    publication_date=source.publication_date,
                    annotation=source.annotation,
                    translations=source.translations or {},
                    dependencies=list(source.dependencies or []),
                    labels=[label.label for label in source.filtering_labels.all()],
                    content=content,
                    urn=source.urn,
                    # The identity already exists in the wild: frozen from the start.
                    first_published_at=now(),
                    last_published_at=now(),
                )
        except IntegrityError:
            existing_draft = LibraryDraft.objects.filter(urn=source.urn).first()
            return Response(
                {
                    "error": "draftAlreadyExists",
                    "draft": str(existing_draft.id) if existing_draft else None,
                },
                status=HTTP_409_CONFLICT,
            )
        # Snapshot the adopted (already-loaded) state so the draft reads as
        # published-and-unchanged until the user edits it.
        draft.mark_published()
        draft.save(update_fields=["last_published_version", "last_published_hash"])
        return Response(LibraryDraftReadSerializer(draft).data, status=HTTP_201_CREATED)

    def _adopt_live_framework(self, request, folder):
        """Adopt a library-less live framework (retired standalone editor).

        Serializes the live rows into a draft document; missing URNs are
        minted onto the live rows first so a later publish updates these
        very rows in place (audits keep pointing at them). The identity is
        frozen from the start — the family is pinned to the live rows.
        """
        from library import live

        try:
            framework = Framework.objects.filter(
                id=request.data.get("framework")
            ).first()
        except ValidationError, ValueError:
            framework = None
        if framework is None or not RoleAssignment.is_object_readable(
            request.user, Framework, framework.id
        ):
            return Response({"error": "frameworkNotFound"}, status=HTTP_404_NOT_FOUND)
        if framework.library_id:
            # Library-backed frameworks are adopted through their library.
            return Response(
                {"error": "frameworkBelongsToALibrary"}, status=HTTP_400_BAD_REQUEST
            )

        # Adopting a live framework backfills missing URNs and normalizes
        # mixed-case ones onto the live rows so a later publish updates those
        # very rows in place — that is a live-row write, so it requires
        # change_framework (mint_missing_urns is a no-op when already clean).
        if not RoleAssignment.is_access_allowed(
            user=request.user,
            perm=Permission.objects.get(codename="change_framework"),
            folder=framework.folder,
        ):
            return Response(status=HTTP_403_FORBIDDEN)
        live.mint_missing_urns(framework)
        framework.refresh_from_db()

        draft_urn = framework.urn.lower().replace(":framework:", ":library:", 1)
        existing_draft = LibraryDraft.objects.filter(urn=draft_urn).first()
        if existing_draft is not None:
            return Response(
                {"error": "draftAlreadyExists", "draft": str(existing_draft.id)},
                status=HTTP_409_CONFLICT,
            )

        packager, ref = live.framework_identity(framework)
        try:
            # atomic + unique urn: a concurrent adopt of the same framework
            # that slipped past the existence check above loses here cleanly.
            with transaction.atomic():
                draft = LibraryDraft.objects.create(
                    name=framework.name,
                    description=framework.description,
                    folder=folder,
                    packager=packager,
                    ref_id=ref,
                    locale=getattr(framework, "locale", None) or "en",
                    version=1,
                    provider=framework.provider or packager,
                    content={"frameworks": [live.live_framework_to_object(framework)]},
                    dependencies=[],
                    urn=draft_urn,
                    # Proof-published: the live rows already carry this URN
                    # family and are in use, so the identity is committed
                    # from the start.
                    first_published_at=now(),
                    last_published_at=None,
                )
        except IntegrityError:
            existing_draft = LibraryDraft.objects.filter(urn=draft_urn).first()
            return Response(
                {
                    "error": "draftAlreadyExists",
                    "draft": str(existing_draft.id) if existing_draft else None,
                },
                status=HTTP_409_CONFLICT,
            )
        # Snapshot the adopted state so later edits read as unpublished changes.
        draft.mark_published()
        draft.save(update_fields=["last_published_version", "last_published_hash"])
        return Response(LibraryDraftReadSerializer(draft).data, status=HTTP_201_CREATED)

    @action(
        detail=False,
        methods=["post"],
        url_path="import-yaml",
        parser_classes=[MultiPartParser, FormParser],
    )
    def import_yaml(self, request):
        """Seed a NEW editable draft from an uploaded library YAML file.

        A library YAML is just a serialized draft document, so this is the
        inverse of Export — without routing through a StoredLibrary first.
        Unlike adopt (which keeps a stored/loaded library in sync and freezes
        its identity), the imported file is not loaded anywhere: the draft's
        identity stays editable (renaming rebases the whole URN family) until
        it is published. Dependencies are resolved only at publish, as usual.
        """
        folder_id = request.data.get("folder")
        try:
            folder = (
                Folder.objects.get(id=folder_id)
                if folder_id
                else Folder.get_root_folder()
            )
        except Folder.DoesNotExist, ValidationError, ValueError:
            return Response({"error": "folderNotFound"}, status=HTTP_404_NOT_FOUND)
        if not RoleAssignment.is_access_allowed(
            user=request.user,
            perm=Permission.objects.get(codename="add_librarydraft"),
            folder=folder,
        ):
            return Response(status=HTTP_403_FORBIDDEN)

        attachment = request.FILES.get("file")
        if attachment is None:
            return Response({"error": "noFileDetected"}, status=HTTP_400_BAD_REQUEST)
        if attachment.size > MAX_UPLOAD_SIZE:
            return Response({"error": "fileTooLarge"}, status=HTTP_400_BAD_REQUEST)
        try:
            validate_file_extension(attachment)
            document = yaml.safe_load(attachment.read())
        except (yaml.YAMLError, ValidationError, DRFValidationError) as e:
            return Response(
                {"error": "invalidYamlFile", "detail": str(e)},
                status=HTTP_422_UNPROCESSABLE_ENTITY,
            )
        if not isinstance(document, dict):
            return Response(
                {"error": "invalidLibraryFile"}, status=HTTP_422_UNPROCESSABLE_ENTITY
            )

        # Same shape gate adopt uses: a raw file is untrusted client data.
        content = builder.normalize_objects(document.get("objects") or {})
        if shape_errors := builder.check_document_shape(content):
            return Response(
                {"error": "importInvalidContent", "details": shape_errors},
                status=HTTP_422_UNPROCESSABLE_ENTITY,
            )
        if not content:
            return Response(
                {"error": "libraryFileHasNoObjects"},
                status=HTTP_422_UNPROCESSABLE_ENTITY,
            )

        # Derive the identity from the library URN so the minted effective_urn
        # matches the objects' URN family (a later rename rebases both). Fall
        # back to the metadata fields for non-standard files.
        groups = match_urn(str(document.get("urn") or ""))
        if groups:
            packager, ref_id = groups[0], str(groups[-1]).lower()
        else:
            packager = document.get("packager") or "custom"
            ref_id = str(document.get("ref_id") or "imported-library").lower()

        draft = LibraryDraft.objects.create(
            name=document.get("name") or ref_id,
            description=document.get("description"),
            folder=folder,
            packager=str(packager),
            ref_id=ref_id,
            locale=document.get("locale") or "en",
            version=document.get("version") or 1,
            provider=document.get("provider"),
            copyright=document.get("copyright"),
            publication_date=document.get("publication_date"),
            annotation=document.get("annotation"),
            translations=document.get("translations") or {},
            dependencies=list(document.get("dependencies") or []),
            labels=list(document.get("labels") or []),
            content=content,
            # No urn / first_published_at: the file is not loaded anywhere,
            # so the identity is editable until this draft is published.
        )
        return Response(LibraryDraftReadSerializer(draft).data, status=HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="import-objects")
    def import_objects(self, request, pk):
        """Selective extraction (clone): copy objects from a source library
        into this draft, rebased onto the draft's URN family. The source is
        a stored library (id/urn) or another draft (``draft:<id>``) — a
        draft is just a library document, so its work-in-progress objects
        can be borrowed without publishing it first."""
        draft = self.get_object()
        raw_source = str(request.data.get("source") or "")
        if raw_source.startswith("draft:"):
            source_draft = _get_readable_draft(
                request.user, raw_source[len("draft:") :]
            )
            if source_draft is None:
                return Response({"error": "libraryNotFound"}, status=HTTP_404_NOT_FOUND)
            if source_draft.id == draft.id:
                return Response(
                    {"error": "cannotImportFromSelf"}, status=HTTP_400_BAD_REQUEST
                )
            source_content = source_draft.content or {}
            source_urn = source_draft.effective_urn
            source_dependencies = source_draft.dependencies or []
        else:
            source = _get_readable_stored_library(request.user, raw_source)
            if source is None:
                return Response({"error": "libraryNotFound"}, status=HTTP_404_NOT_FOUND)
            source_content = source.content or {}
            source_urn = source.urn
            source_dependencies = source.dependencies or []
        if builder.check_document_shape(builder.normalize_objects(source_content)):
            # Extraction assumes well-formed structure; a structurally
            # malformed source cannot be used as a clone source.
            return Response(
                {"error": "sourceLibraryMalformed"},
                status=HTTP_422_UNPROCESSABLE_ENTITY,
            )
        if not (
            re.match(LibraryDraft.IDENTITY_REGEX, draft.packager)
            and re.match(LibraryDraft.IDENTITY_REGEX, draft.ref_id)
        ):
            # Adopted legacy identities may not be URN-safe; they cannot mint
            # new object URNs.
            return Response(
                {"error": "identityNotMintable"}, status=HTTP_400_BAD_REQUEST
            )
        try:
            extraction = builder.extract_objects(
                source_content=source_content,
                source_library_urn=source_urn,
                source_dependencies=source_dependencies,
                target_packager=draft.packager,
                target_ref_id=draft.ref_id,
                selected_types=request.data.get("object_types"),
                selected_urns=request.data.get("urns"),
                default_policy=request.data.get("default_policy", builder.POLICY_STRIP),
                per_urn_policies=request.data.get("policies"),
                resolve_owner=lambda ref: builder.find_owning_library_urn(
                    ref, user=request.user
                ),
            )
            # The builder allows at most one framework and one risk matrix per
            # library. An import may replace the existing one (same minted
            # URN + overwrite) but never take the draft beyond one.
            current = builder.normalize_objects(draft.content or {})
            for field in builder.SINGLETON_OBJECT_FIELDS:
                combined = {
                    str(obj.get("urn", "")).lower()
                    for obj in (extraction["objects"].get(field) or [])
                } | {
                    str(obj.get("urn", "")).lower() for obj in current.get(field) or []
                }
                if len(combined) > 1:
                    return Response(
                        {"error": "singleObjectOfKindPerLibrary", "field": field},
                        status=HTTP_400_BAD_REQUEST,
                    )
            draft.content = builder.merge_objects(
                draft.content,
                extraction["objects"],
                overwrite=bool(request.data.get("overwrite")),
            )
        except builder.BuilderError as e:
            return Response({"error": str(e)}, status=HTTP_400_BAD_REQUEST)
        dependencies = set(draft.dependencies or []) | set(extraction["dependencies"])
        dependencies.discard(draft.effective_urn)
        draft.dependencies = sorted(dependencies)
        draft.save()
        return Response(
            {
                "status": "success",
                "report": extraction["report"],
                "draft": LibraryDraftReadSerializer(draft).data,
            }
        )

    @staticmethod
    def _pick_framework(content: dict, framework_urn):
        """Resolve the target framework object from a normalized document.

        Returns (framework, error_response): exactly one of the two is None.
        """
        frameworks = content.get("frameworks") or []
        if not frameworks:
            return None, Response(
                {"error": "noFrameworkInDraft"}, status=HTTP_404_NOT_FOUND
            )
        if framework_urn:
            lowered = str(framework_urn).lower()
            for framework in frameworks:
                if str(framework.get("urn", "")).lower() == lowered:
                    return framework, None
            return None, Response(
                {"error": "frameworkNotFoundInDraft"}, status=HTTP_404_NOT_FOUND
            )
        if len(frameworks) > 1:
            return None, Response(
                {
                    "error": "frameworkUrnRequired",
                    "frameworks": [
                        {"urn": f.get("urn"), "name": f.get("name")} for f in frameworks
                    ],
                },
                status=HTTP_400_BAD_REQUEST,
            )
        return frameworks[0], None

    @staticmethod
    def _readable_audits_on(framework, user):
        """Audits on a live framework the user is allowed to see. We only ever
        surface what the caller may read (RBAC), never the raw cross-scope set.
        """
        viewable, _, _ = RoleAssignment.get_accessible_object_ids(
            Folder.get_root_folder(), user, ComplianceAssessment
        )
        return ComplianceAssessment.objects.filter(framework=framework, id__in=viewable)

    @action(detail=True, methods=["get", "put"], url_path="framework-editor")
    def framework_editor(self, request, pk):
        """Bridge to the visual framework editor.

        GET returns the framework object of the draft converted to the
        editor-doc shape; PUT converts an editor doc back and saves it into
        the draft document. No live Framework rows are involved.
        """
        draft = self.get_object()
        content = builder.normalize_objects(draft.content or {})

        if request.method == "GET":
            framework, error = self._pick_framework(
                content, request.query_params.get("framework_urn")
            )
            if error is not None:
                return error
            framework_urn = str(framework.get("urn", "")).lower()
            live = Framework.objects.filter(urn=framework_urn).first()
            return Response(
                {
                    "status": "ok",
                    "framework_urn": framework_urn,
                    "frameworks": [
                        {"urn": f.get("urn"), "name": f.get("name")}
                        for f in content.get("frameworks") or []
                    ],
                    "has_compliance_assessments": bool(
                        live and self._readable_audits_on(live, request.user).exists()
                    ),
                    "editing_draft": fw_editor.framework_to_editor_doc(
                        framework, locale=draft.locale
                    ),
                }
            )

        editor_doc = request.data.get("editing_draft")
        if not isinstance(editor_doc, dict):
            return Response(
                {"error": "editingDraftMustBeAnObject"}, status=HTTP_400_BAD_REQUEST
            )
        framework, error = self._pick_framework(
            content, request.data.get("framework_urn")
        )
        if error is not None:
            return error
        try:
            new_framework = fw_editor.editor_doc_to_framework_object(
                editor_doc, existing=framework
            )
        except builder.BuilderError as e:
            return Response({"error": str(e)}, status=HTTP_400_BAD_REQUEST)
        frameworks = content["frameworks"]
        frameworks[frameworks.index(framework)] = new_framework
        # Shape gate before persisting, like every other content door: the
        # editor doc can carry duplicate node/question/choice URNs that would
        # poison the loader's urn_map (dropped questions, merged choices).
        if shape_errors := builder.check_document_shape(content):
            return Response(
                {"error": "draftShapeInvalid", "details": shape_errors},
                status=HTTP_400_BAD_REQUEST,
            )
        draft.content = content
        update_fields = ["content", "updated_at"]
        if self._sync_link_dependencies(draft, content, new_framework, request.user):
            update_fields.append("dependencies")
        draft.save(update_fields=update_fields)
        return Response({"status": "ok", "framework_urn": new_framework["urn"]})

    @staticmethod
    def _sync_link_dependencies(draft, content, framework, user) -> bool:
        """Auto-declare the dependencies backing external node links.

        References are dependency-scoped: linking a threat/reference control
        from a library that is not yet a dependency of the draft declares it
        (the picker offers external objects; the save records the provenance).
        Resolution reads with the requesting user's eyes — a stored library
        the user cannot read is never named in the dependencies. Unresolvable
        references are left for validate/publish to flag.
        """
        refs = set()
        for node in framework.get("requirement_nodes") or []:
            for ref_field in ("threats", "reference_controls"):
                refs.update(str(ref).lower() for ref in node.get(ref_field) or [])
        refs -= set(builder.index_objects(content).keys())
        if not refs:
            return False
        declared = {str(dep).lower() for dep in draft.dependencies or []}
        accessible = builder.accessible_stored_library_ids(user)
        covered = set()
        if declared:
            queryset = StoredLibrary.objects.filter(urn__in=declared)
            if accessible is not None:
                queryset = queryset.filter(id__in=accessible)
            for stored in queryset:
                covered.update(
                    builder.index_objects(
                        builder.normalize_objects(stored.content or {})
                    ).keys()
                )
        own_urn = draft.effective_urn.lower()
        added = set()
        stored_index_cache: dict = {}  # one content parse per candidate library
        for ref in refs - covered:
            owner = builder.find_owning_library_urn(
                ref, user=user
            ) or builder.find_stored_owner_urn(
                ref, index_cache=stored_index_cache, accessible_ids=accessible
            )
            if owner and owner.lower() not in declared and owner.lower() != own_urn:
                declared.add(owner.lower())
                added.add(owner.lower())
        if not added:
            return False
        draft.dependencies = sorted(set(draft.dependencies or []) | added)
        return True

    @action(detail=True, methods=["post"], url_path="framework-editor-preview")
    def framework_editor_preview(self, request, pk):
        """What would change on the live (loaded) framework if the draft were
        published now — diffed by URN against the loaded rows."""
        draft = self.get_object()
        content = builder.normalize_objects(draft.content or {})
        framework, error = self._pick_framework(
            content, request.data.get("framework_urn")
        )
        if error is not None:
            return error
        editor_doc = request.data.get("editing_draft")
        if isinstance(editor_doc, dict):
            try:
                framework = fw_editor.editor_doc_to_framework_object(
                    editor_doc, existing=framework
                )
            except builder.BuilderError as e:
                return Response({"error": str(e)}, status=HTTP_400_BAD_REQUEST)

        framework_urn = str(framework.get("urn", "")).lower()
        live = Framework.objects.filter(urn=framework_urn).first()
        live_nodes = (
            {node.urn: node for node in RequirementNode.objects.filter(framework=live)}
            if live
            else {}
        )
        doc_nodes = {
            # urn absence is legal WIP (completeness, not shape): an urnless
            # node simply has no live counterpart yet.
            node["urn"]: node
            for node in framework.get("requirement_nodes") or []
            if node.get("urn")
        }
        added = [urn for urn in doc_nodes if urn not in live_nodes]
        removed = [urn for urn in live_nodes if urn not in doc_nodes]

        doc_question_urns = set()
        doc_choice_urns = set()
        for node in doc_nodes.values():
            for q_urn, q_data in (node.get("questions") or {}).items():
                doc_question_urns.add(str(q_urn).lower())
                for choice in q_data.get("choices") or []:
                    if choice.get("urn"):
                        doc_choice_urns.add(str(choice["urn"]).lower())
        live_question_urns = (
            set(
                Question.objects.filter(requirement_node__framework=live).values_list(
                    "urn", flat=True
                )
            )
            if live
            else set()
        )
        live_choice_urns = (
            set(
                QuestionChoice.objects.filter(
                    question__requirement_node__framework=live
                ).values_list("urn", flat=True)
            )
            if live
            else set()
        )

        def details(urns, source, limit=20):
            entries = []
            for urn in urns[:limit]:
                node = source[urn]
                name = node.get("name") if isinstance(node, dict) else node.name
                assessable = (
                    node.get("assessable")
                    if isinstance(node, dict)
                    else node.assessable
                )
                entries.append({"name": name or urn, "assessable": bool(assessable)})
            return entries

        return Response(
            {
                "added": {
                    "requirements": len(added),
                    "questions": len(doc_question_urns - live_question_urns),
                    "choices": len(doc_choice_urns - live_choice_urns),
                    "details": details(added, doc_nodes),
                },
                "removed": {
                    "requirements": len(removed),
                    "questions": len(live_question_urns - doc_question_urns),
                    "choices": len(live_choice_urns - doc_choice_urns),
                    "details": details(removed, live_nodes),
                },
                "breaking_changes": [],
                "affected_audits": [
                    {"id": str(audit.id), "name": audit.name}
                    for audit in self._readable_audits_on(live, request.user)
                ]
                if live
                else [],
            }
        )

    @action(detail=True, methods=["get"], url_path="reference-catalog")
    def reference_catalog(self, request, pk):
        """Pickable threats and reference controls for framework-node links.

        Without a parameter: the draft's own objects, each declared
        dependency's, and the list of other stored libraries holding such
        objects. With ?library=<id or urn>: that library's objects alone
        (browse-on-demand; linking from it auto-declares the dependency on
        the next framework-editor save).
        """
        draft = self.get_object()

        def source_entry(library_urn, name, kind, objects) -> dict:
            entry = {
                "library_urn": library_urn,
                "name": name,
                "kind": kind,
                "threats": [],
                "reference_controls": [],
            }
            for field in ("threats", "reference_controls"):
                items = objects.get(field)
                if not isinstance(items, list):
                    continue  # stored content is not shape-checked
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    urn = str(item.get("urn", "")).lower()
                    if not urn:
                        continue  # work-in-progress objects cannot be linked
                    picked = {
                        "urn": urn,
                        "ref_id": item.get("ref_id"),
                        "name": item.get("name"),
                    }
                    if field == "reference_controls":
                        picked["category"] = item.get("category")
                        picked["csf_function"] = item.get("csf_function")
                    entry[field].append(picked)
            return entry

        browse = request.query_params.get("library")
        if browse:
            stored = _get_readable_stored_library(request.user, browse)
            if stored is None:
                return Response({"error": "libraryNotFound"}, status=HTTP_404_NOT_FOUND)
            return Response(
                {
                    "source": source_entry(
                        stored.urn,
                        stored.name,
                        "external",
                        builder.normalize_objects(stored.content or {}),
                    )
                }
            )

        sources = [
            source_entry(
                draft.effective_urn,
                draft.name,
                "draft",
                builder.normalize_objects(draft.content or {}),
            )
        ]
        for dep_urn in draft.dependencies or []:
            # Unreadable dependencies degrade to the missing presentation.
            stored = _get_readable_stored_library(request.user, str(dep_urn).lower())
            if stored is None:
                sources.append(
                    {
                        "library_urn": dep_urn,
                        "name": dep_urn,
                        "kind": "dependency",
                        "missing": True,
                        "threats": [],
                        "reference_controls": [],
                    }
                )
                continue
            sources.append(
                source_entry(
                    stored.urn,
                    stored.name,
                    "dependency",
                    builder.normalize_objects(stored.content or {}),
                )
            )

        known = {str(s.get("library_urn", "")).lower() for s in sources}
        latest: dict = {}
        accessible_ids = RoleAssignment.get_accessible_object_ids(
            Folder.get_root_folder(), request.user, StoredLibrary
        )[0]
        rows = (
            StoredLibrary.objects.filter(id__in=accessible_ids)
            .filter(
                Q(content__threats__isnull=False)
                | Q(content__reference_controls__isnull=False)
            )
            .only("id", "urn", "name", "provider", "version")
        )
        for row in rows:
            lowered = str(row.urn or "").lower()
            if not lowered or lowered in known:
                continue
            current = latest.get(lowered)
            if current is None or row.version > current.version:
                latest[lowered] = row
        libraries = sorted(
            (
                {
                    "id": str(row.id),
                    "library_urn": row.urn,
                    "name": row.name,
                    "provider": row.provider,
                }
                for row in latest.values()
            ),
            key=lambda entry: str(entry["name"] or "").lower(),
        )
        return Response({"sources": sources, "libraries": libraries})

    @action(detail=True, methods=["post"], url_path="add-framework")
    def add_framework(self, request, pk):
        """Add a skeleton framework object to the draft document."""
        draft = self.get_object()
        if not (
            re.match(LibraryDraft.IDENTITY_REGEX, draft.packager)
            and re.match(LibraryDraft.IDENTITY_REGEX, draft.ref_id)
        ):
            return Response(
                {"error": "identityNotMintable"}, status=HTTP_400_BAD_REQUEST
            )
        content = builder.normalize_objects(draft.content or {})
        frameworks = content.setdefault("frameworks", [])
        if frameworks:
            # Single-framework convention: one framework per library.
            return Response(
                {"error": "singleObjectOfKindPerLibrary", "field": "frameworks"},
                status=HTTP_400_BAD_REQUEST,
            )
        framework_urn = builder.object_urn_base(
            draft.packager, draft.ref_id, "frameworks"
        )
        frameworks.append(
            {
                "urn": framework_urn,
                "ref_id": request.data.get("ref_id") or draft.ref_id,
                "name": request.data.get("name") or draft.name,
                "requirement_nodes": [],
            }
        )
        draft.content = content
        draft.save(update_fields=["content", "updated_at"])
        return Response(
            {"status": "ok", "framework_urn": framework_urn},
            status=HTTP_201_CREATED,
        )

    def _preset_editor_draft(self, draft, content: dict) -> dict:
        """The preset object viewed in the editor-draft shape.

        The preset carries its own name/description; legacy preset libraries
        (which are one-to-one with their preset) fall back to the library
        metadata, mirroring upsert_preset_from_stored_library.
        """
        preset = content.get("preset") or {}
        journey = preset.get("journey") or {}
        return {
            "journey_meta": {
                "name": preset.get("name") or draft.name or "",
                "description": preset.get("description") or draft.description or "",
                "translations": preset.get("translations") or {},
            },
            "scaffolded_objects": list(preset.get("scaffolded_objects") or []),
            "steps": list(journey.get("steps") or []),
        }

    @action(detail=True, methods=["get", "put"], url_path="preset-editor")
    def preset_editor(self, request, pk):
        """Bridge to the journey preset editor.

        GET returns the draft's preset object in the editor-draft shape
        ({journey_meta, scaffolded_objects, steps}); PUT validates an editor
        draft and saves it back into the document, creating the preset object
        on first save. profile/feature_flags and unknown keys are preserved.
        """
        from core.preset_editor import validate_draft as validate_preset_draft

        draft = self.get_object()
        content = builder.normalize_objects(draft.content or {})

        if request.method == "GET":
            return Response(
                {"editing_draft": self._preset_editor_draft(draft, content)}
            )

        editor_draft = request.data.get("editing_draft")
        if not isinstance(editor_draft, dict):
            return Response(
                {"error": "editingDraftMustBeAnObject"}, status=HTTP_400_BAD_REQUEST
            )
        try:
            normalized = validate_preset_draft(editor_draft, strict=False)
        except ValidationError as e:
            detail = getattr(e, "message_dict", None) or {
                "detail": "; ".join(getattr(e, "messages", [str(e)]))
            }
            return Response(detail, status=HTTP_400_BAD_REQUEST)

        preset = dict(content.get("preset") or {})
        preset["scaffolded_objects"] = normalized["scaffolded_objects"]
        journey = dict(preset.get("journey") or {})
        journey["steps"] = normalized["steps"]
        preset["journey"] = journey
        # The preset's own title, independent from the library name. Empty
        # values are dropped: the loader falls back to the library metadata.
        for field in ("name", "description", "translations"):
            if normalized["journey_meta"][field]:
                preset[field] = normalized["journey_meta"][field]
            else:
                preset.pop(field, None)
        content["preset"] = preset
        draft.content = content
        draft.save(update_fields=["content", "updated_at"])
        return Response({"editing_draft": self._preset_editor_draft(draft, content)})

    @action(detail=True, methods=["post"], url_path="preset-editor-preview")
    def preset_editor_preview(self, request, pk):
        """Steps removed from the document's preset compared to the loaded
        Preset, with the user journey state that would be lost — mirrors the
        retired standalone preset editor's publish preview."""
        from core.models import Preset, PresetJourneyStep

        draft = self.get_object()
        content = builder.normalize_objects(draft.content or {})
        preset = content.get("preset") or {}
        draft_keys = {
            step.get("key")
            for step in (preset.get("journey") or {}).get("steps") or []
            if step.get("key")
        }
        live = Preset.objects.filter(urn=draft.effective_urn).first()
        if live is None:
            return Response({"deleted_steps": []})
        live_keys = {step.get("key") for step in (live.steps or []) if step.get("key")}
        warnings = []
        for key in sorted(live_keys - draft_keys):
            journey_steps = PresetJourneyStep.objects.filter(
                journey__preset=live, key=key
            )
            with_user_state = journey_steps.exclude(
                status=PresetJourneyStep.Status.NOT_STARTED, notes=""
            ).count()
            warnings.append(
                {
                    "key": key,
                    "journey_step_count": journey_steps.count(),
                    "with_user_state": with_user_state,
                }
            )
        return Response({"deleted_steps": warnings})

    @action(detail=True, methods=["post"], url_path="upsert-object")
    def upsert_object(self, request, pk):
        """Create or update a leaf object (threat, reference control, risk
        matrix, metric definition) in the draft document.

        Without `urn` a new object is created, its URN minted server-side
        under the library's family base; with `urn` the matching object is
        updated (URN untouched, unknown keys preserved, null values clear
        their key). Payloads are validated with the loader's own importers.
        """
        from library.utils import (
            MetricDefinitionImporter,
            ReferenceControlImporter,
            RiskMatrixImporter,
            ThreatImporter,
        )

        importers = {
            "threats": ThreatImporter,
            "reference_controls": ReferenceControlImporter,
            "risk_matrices": RiskMatrixImporter,
            "metric_definitions": MetricDefinitionImporter,
        }

        draft = self.get_object()
        raw_field = request.data.get("field")
        # Non-string payloads (e.g. a list) are unhashable and would crash the
        # dict lookup (500); normalize them to fail the allowlist check below.
        field = (
            builder.CANONICAL_OBJECT_FIELDS.get(raw_field, raw_field)
            if isinstance(raw_field, str)
            else None
        )
        if field not in self.UPSERTABLE_FIELDS:
            return Response(
                {"error": "unsupportedObjectField"}, status=HTTP_400_BAD_REQUEST
            )
        payload = request.data.get("object")
        if not isinstance(payload, dict):
            return Response({"error": "objectMustBeADict"}, status=HTTP_400_BAD_REQUEST)

        content = builder.normalize_objects(draft.content or {})
        items = content.setdefault(field, [])
        target_urn = request.data.get("urn")

        if target_urn:
            target_urn = str(target_urn).lower()
            index = next(
                (
                    i
                    for i, item in enumerate(items)
                    if str(item.get("urn", "")).lower() == target_urn
                ),
                None,
            )
            if index is None:
                return Response(
                    {"error": "objectNotFoundInDraft"}, status=HTTP_404_NOT_FOUND
                )
            merged = dict(items[index])
            for key, value in payload.items():
                if key == "urn":
                    continue  # pinned identity, never rewritten from a payload
                if value is None:
                    merged.pop(key, None)
                else:
                    merged[key] = value
            candidate = merged
        else:
            if field in builder.SINGLETON_OBJECT_FIELDS and items:
                # Single-object convention (one risk matrix per library).
                return Response(
                    {"error": "singleObjectOfKindPerLibrary", "field": field},
                    status=HTTP_400_BAD_REQUEST,
                )
            try:
                base = builder.leaf_object_base(draft.effective_urn, field)
            except builder.BuilderError as e:
                return Response({"error": str(e)}, status=HTTP_400_BAD_REQUEST)
            if field in builder.SINGLETON_OBJECT_FIELDS:
                # The single object of its kind takes the bare family URN,
                # matching the shipped-library convention.
                urn = base
            else:
                leaf = builder.urn_safe_leaf(str(payload.get("ref_id") or ""))
                if not leaf:
                    return Response(
                        {"error": "refIdRequired"}, status=HTTP_400_BAD_REQUEST
                    )
                urn = f"{base}:{leaf}"
            if any(str(item.get("urn", "")).lower() == urn for item in items):
                return Response(
                    {"error": "objectUrnAlreadyExists", "urn": urn},
                    status=HTTP_409_CONFLICT,
                )
            candidate = {"urn": urn}
            for key, value in payload.items():
                if key != "urn" and value is not None:
                    candidate[key] = value
            index = None

        if error := importers[field](candidate).is_valid():
            return Response({"error": error}, status=HTTP_400_BAD_REQUEST)
        if field == "risk_matrices":
            # RiskMatrixImporter.is_valid is currently a no-op; reuse the
            # matrix editor's structural validation instead.
            from core.views import RiskMatrixViewSet

            definition = {
                key: candidate.get(key)
                for key in ("probability", "impact", "risk", "grid")
            }
            if matrix_errors := RiskMatrixViewSet._validate_json_definition(definition):
                return Response(
                    {"error": " ".join(matrix_errors)}, status=HTTP_400_BAD_REQUEST
                )

        if index is None:
            items.append(candidate)
        else:
            items[index] = candidate
        draft.content = content
        draft.save(update_fields=["content", "updated_at"])
        return Response(
            {
                "status": "ok",
                "object": candidate,
                "draft": LibraryDraftReadSerializer(draft).data,
            }
        )

    @action(detail=True, methods=["post"], url_path="delete-object")
    def delete_object(self, request, pk):
        """Remove a top-level object from the draft document.

        Framework-node links to the object block the deletion unless `force`
        is set, in which case they are stripped. A requirement mapping set
        pointing at the object always blocks (its framework fields are
        mandatory): delete the mapping set first.
        """
        draft = self.get_object()
        content = builder.normalize_objects(draft.content or {})

        # The journey preset is a singular top-level key (not a URN-keyed list
        # object), so it is removed by name rather than by URN.
        if request.data.get("field") == "preset" or request.data.get("urn") == "preset":
            if "preset" not in content:
                return Response(
                    {"error": "objectNotFoundInDraft"}, status=HTTP_404_NOT_FOUND
                )
            del content["preset"]
            draft.content = content
            draft.save(update_fields=["content", "updated_at"])
            return Response(
                {"status": "ok", "draft": LibraryDraftReadSerializer(draft).data}
            )

        target_urn = str(request.data.get("urn") or "").lower()
        if not target_urn:
            return Response({"error": "urnRequired"}, status=HTTP_400_BAD_REQUEST)

        located = next(
            (
                (field, index)
                for field in builder.LIST_OBJECT_FIELDS
                for index, item in enumerate(content.get(field) or [])
                if str(item.get("urn", "")).lower() == target_urn
            ),
            None,
        )
        if located is None:
            return Response(
                {"error": "objectNotFoundInDraft"}, status=HTTP_404_NOT_FOUND
            )
        field, index = located

        node_references = []
        for framework in content.get("frameworks") or []:
            for node in framework.get("requirement_nodes") or []:
                for ref_field in ("threats", "reference_controls"):
                    refs = [str(ref).lower() for ref in node.get(ref_field) or []]
                    if target_urn in refs:
                        node_references.append(str(node.get("urn", "")).lower())
        mapping_references = [
            str(mapping_set.get("urn", "")).lower()
            for mapping_set in content.get("requirement_mapping_sets") or []
            if target_urn
            in (
                str(mapping_set.get("source_framework_urn", "")).lower(),
                str(mapping_set.get("target_framework_urn", "")).lower(),
            )
        ]

        if mapping_references:
            return Response(
                {
                    "error": "objectIsReferencedByMappingSet",
                    "references": mapping_references,
                },
                status=HTTP_409_CONFLICT,
            )
        if node_references and not request.data.get("force"):
            return Response(
                {"error": "objectIsReferenced", "references": node_references},
                status=HTTP_409_CONFLICT,
            )
        if node_references:
            for framework in content.get("frameworks") or []:
                for node in framework.get("requirement_nodes") or []:
                    for ref_field in ("threats", "reference_controls"):
                        refs = node.get(ref_field)
                        if refs:
                            node[ref_field] = [
                                ref for ref in refs if str(ref).lower() != target_urn
                            ]

        del content[field][index]
        if not content[field]:
            del content[field]
        draft.content = content
        draft.save(update_fields=["content", "updated_at"])
        return Response(
            {"status": "ok", "draft": LibraryDraftReadSerializer(draft).data}
        )

    @action(detail=True, methods=["post"])
    def publish(self, request, pk):
        """Publish = the user's commit: freeze the identity and snapshot the
        content (version + fingerprint). With load=true (the default) the
        draft is also serialized to library YAML and fed to the existing
        stored-library loader — loading is proof of publication, so it always
        implies the commit. Re-publishing an already-loaded URN goes through
        the loader's update path (update-by-URN). load=false commits without
        touching the corpus (publish-for-export)."""
        draft = self.get_object()
        for codename in ("add_storedlibrary", "add_loadedlibrary"):
            if not RoleAssignment.is_access_allowed(
                user=request.user,
                perm=Permission.objects.get(codename=codename),
                folder=Folder.get_root_folder(),
            ):
                return Response(status=HTTP_403_FORBIDDEN)

        validation = builder.validate_draft_document(draft, user=request.user)
        if validation["errors"]:
            return Response(
                {"error": "draftValidationFailed", "details": validation["errors"]},
                status=HTTP_422_UNPROCESSABLE_ENTITY,
            )

        # A published artifact is identified by URN + version: re-publishing
        # different content under the version already snapshotted would put
        # two different v{n} YAMLs in the wild.
        if (
            draft.last_published_hash is not None
            and draft.version == draft.last_published_version
            and draft.publish_fingerprint() != draft.last_published_hash
        ):
            if request.data.get("bump_version"):
                draft.version += 1
                draft.save(update_fields=["version", "updated_at"])
            else:
                return Response(
                    {
                        "error": "versionBumpRequired",
                        "published_version": draft.last_published_version,
                    },
                    status=HTTP_409_CONFLICT,
                )

        if not request.data.get("load", True):
            # Commit only: freeze identity + snapshot, no corpus effect.
            if (
                draft.last_published_hash is not None
                and draft.publish_fingerprint() == draft.last_published_hash
            ):
                return Response({"error": "nothingToPublish"}, status=HTTP_409_CONFLICT)
            if draft.first_published_at is None:
                draft.first_published_at = now()
            draft.last_published_at = now()
            draft.mark_published()
            draft.save(
                update_fields=[
                    "first_published_at",
                    "last_published_at",
                    "last_published_version",
                    "last_published_hash",
                    "updated_at",
                ]
            )
            return Response(
                {
                    "status": "published",
                    "urn": draft.effective_urn,
                    "version": draft.version,
                    "loaded": False,
                }
            )

        urn = draft.effective_urn
        # Another draft already owns this URN (published under the same
        # identity first): refuse before touching the corpus — the unique
        # constraint would reject our urn stamp at the end anyway, after the
        # load already went through.
        conflicting = LibraryDraft.objects.filter(urn=urn).exclude(id=draft.id).first()
        if conflicting is not None:
            return Response(
                {"error": "draftAlreadyExists", "draft": str(conflicting.id)},
                status=HTTP_409_CONFLICT,
            )

        # Unchanged since the last publication AND that exact version is
        # already loaded: there is nothing to commit and nothing to load.
        # Refusing here (instead of falling into the version guard below)
        # avoids nudging the user into bumping the version of identical
        # content. A committed-but-not-loaded draft still passes: loading it
        # IS the pending work.
        if (
            draft.last_published_hash is not None
            and draft.version == draft.last_published_version
            and draft.publish_fingerprint() == draft.last_published_hash
            and LoadedLibrary.objects.filter(
                urn=urn, locale=draft.locale, version__gte=draft.version
            ).exists()
        ):
            return Response({"error": "nothingToPublish"}, status=HTTP_409_CONFLICT)

        max_existing = max(
            [
                *StoredLibrary.objects.filter(urn=urn, locale=draft.locale).values_list(
                    "version", flat=True
                ),
                *LoadedLibrary.objects.filter(urn=urn, locale=draft.locale).values_list(
                    "version", flat=True
                ),
            ],
            default=None,
        )
        if max_existing is not None and max_existing >= draft.version:
            if request.data.get("bump_version"):
                draft.version = max_existing + 1
                draft.save(update_fields=["version", "updated_at"])
            else:
                return Response(
                    {"error": "libraryVersionOutdated", "max_version": max_existing},
                    status=HTTP_409_CONFLICT,
                )

        library_yaml = yaml.safe_dump(
            draft.to_library_dict(), sort_keys=False, allow_unicode=True
        ).encode()
        try:
            stored, error = StoredLibrary.store_library_content(library_yaml)
        except ValueError, ValidationError, yaml.YAMLError:
            # Full detail goes to the log, not to the client: validation
            # exceptions can carry internal state.
            logger.exception(
                "Failed to store published draft", urn=urn, locale=draft.locale
            )
            return Response(
                {"error": "libraryPublishFailed"},
                status=HTTP_422_UNPROCESSABLE_ENTITY,
            )
        if error is not None:
            # Publish is stateless (failed attempts leave no stored row
            # behind), so a store refusal genuinely means the content or
            # version already exists — nothing new to publish.
            return Response({"error": error}, status=HTTP_409_CONFLICT)

        # Publish is all-or-nothing: if loading does not complete, remove the
        # stored row this request created so the version guard is back to its
        # pre-publish state and a retry (e.g. with a score-change strategy,
        # same version) starts from a clean slate — no phantom "update
        # available" rows, no skipped version numbers.
        loaded = LoadedLibrary.objects.filter(urn=urn, locale=draft.locale).first()
        try:
            if loaded is not None:
                error_msg = loaded.update(strategy=request.data.get("strategy"))
            else:
                error_msg = stored.load()
        except LibraryUpdater.ScoreChangeDetected as e:
            stored.delete()
            return Response(
                {
                    "error": "score_change_detected",
                    "framework_urn": e.framework_urn,
                    "prev_scores": e.prev_scores,
                    "new_scores": e.new_scores,
                    "affected_assessments": e.affected_assessments,
                    "strategies": e.strategies,
                },
                status=HTTP_409_CONFLICT,
            )
        except Exception:
            # Full detail goes to the log, not to the client: a bare Exception
            # here can carry internal state (DB, filesystem, paths).
            logger.exception("Failed to load published draft", urn=urn)
            stored.delete()
            return Response(
                {"error": "libraryLoadFailed"},
                status=HTTP_422_UNPROCESSABLE_ENTITY,
            )
        if error_msg is not None:
            stored.delete()
            if error_msg == "libraryHasNoUpdate":
                return Response(
                    {"error": "noChangesToPublish"}, status=HTTP_409_CONFLICT
                )
            return Response(
                {"error": "libraryLoadFailed", "detail": error_msg},
                status=HTTP_422_UNPROCESSABLE_ENTITY,
            )

        draft.urn = urn
        if draft.first_published_at is None:
            draft.first_published_at = now()
        draft.last_published_at = now()
        draft.mark_published()  # snapshot for has_unpublished_changes
        draft.save(
            update_fields=[
                "urn",
                "first_published_at",
                "last_published_at",
                "last_published_version",
                "last_published_hash",
                "updated_at",
            ]
        )
        loaded = LoadedLibrary.objects.filter(urn=urn, locale=draft.locale).first()
        return Response(
            {
                "status": "success",
                "urn": urn,
                "version": stored.version,
                "stored_library": str(stored.id),
                "loaded_library": str(loaded.id) if loaded else None,
            }
        )
