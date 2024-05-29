import json
from django.db import IntegrityError
from rest_framework import viewsets, status
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_204_NO_CONTENT,
    HTTP_400_BAD_REQUEST,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_422_UNPROCESSABLE_ENTITY,
)
from rest_framework.parsers import FileUploadParser

from django.http import HttpResponse

from core.helpers import get_sorted_requirement_nodes
from core.models import StoredLibrary, LoadedLibrary
from core.views import BaseModelViewSet
from iam.models import RoleAssignment, Folder, Permission
from library.validators import validate_file_extension
from .helpers import preview_library


from rest_framework.decorators import action
from rest_framework.response import Response
from .serializers import (
    StoredLibraryDetailedSerializer,
    LoadedLibraryDetailedSerializer,
    StoredLibrarySerializer,
)

import structlog

logger = structlog.get_logger(__name__)


class StoredLibraryViewSet(BaseModelViewSet):
    parser_classes = [FileUploadParser]

    # solve issue with URN containing dot, see https://stackoverflow.com/questions/27963899/django-rest-framework-using-dot-in-url
    lookup_value_regex = r"[\w.:-]+"
    model = StoredLibrary
    queryset = StoredLibrary.objects.all()

    filterset_fields = ["urn", "locale", "version", "packager", "provider"]
    search_fields = ["name", "description", "urn"]

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

    def content(self, request, pk):
        try:
            key = "urn" if pk.startswith("urn:") else "id"
            lib = StoredLibrary.objects.get(**{key: pk})
        except:
            return Response("Library not found.", status=HTTP_404_NOT_FOUND)
        return Response(lib.content)

    @action(detail=True, methods=["get"])
    def content(self, request, pk):
        try:
            key = "urn" if pk.startswith("urn:") else "id"
            lib = StoredLibrary.objects.get(**{key: pk})
        except:
            return Response("Library not found.", status=HTTP_404_NOT_FOUND)
        return Response(lib.content)

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

    @action(detail=True, methods=["get"], url_path="import")
    def import_library(self, request, pk):
        if not RoleAssignment.is_access_allowed(
            user=request.user,
            perm=Permission.objects.get(codename="add_loadedlibrary"),
            folder=Folder.get_root_folder(),
        ):
            return Response(status=HTTP_403_FORBIDDEN)
        try:
            key = "urn" if pk.startswith("urn:") else "id"
            for _ in range(10):
                print(f"Looking for {key} {pk}")
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
            return Response(
                {"error": f"Failed to load library ({e})"},  # This must translated
                status=HTTP_422_UNPROCESSABLE_ENTITY,
            )

    @action(detail=True, methods=["get"])
    def tree(self, request, pk):
        try:
            key = "urn" if pk.startswith("urn:") else "id"
            lib = StoredLibrary.objects.get(**{key: pk})
        except:
            return Response(data="Library not found.", status=HTTP_404_NOT_FOUND)

        library_objects = json.loads(lib.content)  # We may need caching for this
        if not (framework := library_objects.get("framework")):
            return Response(
                data="This library does not include a framework.",
                status=HTTP_400_BAD_REQUEST,
            )

        preview = preview_library(framework)
        return Response(
            get_sorted_requirement_nodes(preview.get("requirement_nodes"), None)
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
                StoredLibrary.store_library_content(content)
            except ValueError as e:
                logger.error("Failed to store library content", error=e)
                return HttpResponse(
                    json.dumps({"error": "Failed to store library content."}),
                    status=HTTP_422_UNPROCESSABLE_ENTITY,
                )

            return HttpResponse(json.dumps({}), status=HTTP_200_OK)
        except IntegrityError:
            return HttpResponse(
                json.dumps({"error": "libraryAlreadyLoadedError"}),
                status=HTTP_400_BAD_REQUEST,
            )
        except yaml.YAMLError:
            return HttpResponse(
                json.dumps({"error": "invalidLibraryFileError"}),
                status=HTTP_400_BAD_REQUEST,
            )


class LoadedLibraryViewSet(viewsets.ModelViewSet):
    # serializer_class = LoadedLibrarySerializer
    # parser_classes = [FileUploadParser]

    # solve issue with URN containing dot, see https://stackoverflow.com/questions/27963899/django-rest-framework-using-dot-in-url
    lookup_value_regex = r"[\w.:-]+"
    model = LoadedLibrary
    queryset = LoadedLibrary.objects.all()

    def list(self, request, *args, **kwargs):
        if "view_loadedlibrary" not in request.user.permissions:
            return Response(status=HTTP_403_FORBIDDEN)

        stored_libraries = [*StoredLibrary.objects.all()]
        last_version = {}
        for stored_library in stored_libraries:
            if last_version.get(stored_library.urn, -1) < stored_library.version:
                last_version[stored_library.urn] = stored_library.version

        loaded_libraries = []
        for library in LoadedLibrary.objects.all():
            loaded_library = {
                key: getattr(library, key)
                for key in [
                    "id",
                    "name",
                    "description",
                    "urn",
                    "ref_id",
                    "locale",
                    "version",
                    "packager",
                    "provider",
                    "builtin",
                    "objects_meta",
                    "reference_count",
                ]
            }
            loaded_library["has_update"] = (
                last_version.get(library.urn, -1) > library.version
            )
            loaded_libraries.append(loaded_library)

        return Response({"results": loaded_libraries})

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

        if lib.frameworks.count() == 0:
            return Response(
                data="This library doesn't contain any framework.",
                status=HTTP_404_NOT_FOUND,
            )

        framework = lib.frameworks.first()
        requirement_nodes = framework.requirement_nodes.all()
        return Response(get_sorted_requirement_nodes(requirement_nodes, None))

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
        except Exception as e:
            return Response(
                data="libraryNotFound", status=HTTP_404_NOT_FOUND
            )  # Error messages could be returned as JSON instead

        error_msg = library.update()
        if error_msg is None:
            return Response(status=HTTP_204_NO_CONTENT)
        return Response(
            error_msg, status=HTTP_422_UNPROCESSABLE_ENTITY
        )  # We must make at least one error message
