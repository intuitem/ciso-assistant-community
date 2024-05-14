import json
from django.db import IntegrityError
from rest_framework import viewsets, status
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_400_BAD_REQUEST,
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
    queryset = StoredLibrary.objects.filter(is_obsolete=False)

    filterset_fields = ["urn", "locale", "version", "packager", "provider"]
    search_fields = ["name", "description", "urn"]

    def get_serializer_class(self):
        if self.action == "list":
            return StoredLibrarySerializer
        return StoredLibraryDetailedSerializer

    @action(detail=True, methods=["get"])
    def content(self, request, pk):
        lib = StoredLibrary.objects.get(id=pk)
        return Response(lib.content)

    @action(detail=True, methods=["get"], url_path="import")
    def import_library(self, request, pk):
        if not RoleAssignment.is_access_allowed(
            user=request.user,
            perm=Permission.objects.get(codename="add_loadedlibrary"),
            folder=Folder.get_root_folder(),
        ):
            return Response(status=status.HTTP_403_FORBIDDEN)
        try:
            library = StoredLibrary.objects.get(
                urn=pk
            )  # This is only fetching the lib by URN without caring about the locale or the version, this must change in the future.
        except:
            return Response(data="Library not found.", status=status.HTTP_404_NOT_FOUND)

        try:
            error_msg = library.load()
            if error_msg is not None:
                return Response(
                    {"status": "error", "error": error_msg},
                    status=status.HTTP_400_BAD_REQUEST,
                )  # This can cause translation issues
            return Response({"status": "success"})
        except Exception:
            return Response(
                {
                    "error": "Failed to load library, please check if it has dependencies"
                },  # This must translated
                status=HTTP_422_UNPROCESSABLE_ENTITY,
            )

    @action(detail=True, methods=["get"])
    def tree(self, request, pk):
        try:
            lib = StoredLibrary.objects.get(id=pk)
        except:
            return Response(data="Library not found.", status=status.HTTP_404_NOT_FOUND)

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
                    json.dumps({"error": "Failed to store library content"}),
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
        if "view_storedlibrary" not in request.user.permissions:
            return Response(status=status.HTTP_403_FORBIDDEN)

        loaded_libraries = [
            {
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
            for library in LoadedLibrary.objects.all()
        ]
        return Response({"results": loaded_libraries})

    def retrieve(self, request, *args, pk, **kwargs):
        if "view_loadedlibrary" not in request.user.permissions:
            return Response(status=status.HTTP_403_FORBIDDEN)
        try:
            lib = LoadedLibrary.objects.get(
                urn=pk
            )  # There is no "locale" value involved in the fetch + we have to handle the exception if the pk urn doesn't exist
        except:
            return Response(data="Library not found.", status=status.HTTP_404_NOT_FOUND)
        data = LoadedLibraryDetailedSerializer(lib).data
        data["objects"] = lib._objects
        return Response(data)

    def destroy(self, request, *args, pk, **kwargs):
        if not RoleAssignment.is_access_allowed(
            user=request.user,
            perm=Permission.objects.get(codename="delete_loadedlibrary"),
            folder=Folder.get_root_folder(),
        ):
            return Response(status=status.HTTP_403_FORBIDDEN)

        try:
            lib = LoadedLibrary.objects.get(urn=pk)
        except:
            return Response(data="Library not found.", status=status.HTTP_404_NOT_FOUND)

        if lib.reference_count != 0:
            return Response(
                data="Library cannot be deleted because it has references.",
                status=status.HTTP_400_BAD_REQUEST,
            )

        lib.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["get"])
    def tree(
        self, request, pk
    ):  # We must ensure that users that are not allowed to read the content of libraries can't have any access to them either from the /api/{URLModel/{library_urn}/tree view or the /api/{URLModel}/{library_urn} view.
        try:
            lib = LoadedLibrary.objects.get(urn=pk)
        except:
            return Response(data="Library not found.", status=status.HTTP_404_NOT_FOUND)

        if lib.frameworks.count() == 0:
            return Response(
                data="This library doesn't contain any framework.",
                status=HTTP_404_NOT_FOUND,
            )

        framework = lib.frameworks.first()
        requirement_nodes = framework.requirement_nodes.all()
        return Response(get_sorted_requirement_nodes(requirement_nodes, None))
