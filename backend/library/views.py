import json
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db.models import QuerySet
from rest_framework import permissions, status
from rest_framework.generics import get_object_or_404
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_400_BAD_REQUEST,
    HTTP_422_UNPROCESSABLE_ENTITY,
)
from rest_framework.parsers import FileUploadParser
from rest_framework.views import APIView


from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.http import HttpResponse
import yaml

from core.helpers import get_sorted_requirement_nodes
from core.models import Library
from core.views import BaseModelViewSet
from iam.models import RoleAssignment, Folder, Permission
from library.validators import validate_file_extension
from .helpers import preview_library


from rest_framework.decorators import action
from rest_framework.response import Response
from .serializers import LibrarySerializer, LibraryUploadSerializer
from .utils import get_available_libraries, get_library, import_library_view

class LibraryViewSet(BaseModelViewSet):
    serializer_class = LibrarySerializer
    parser_classes = [FileUploadParser]

    # solve issue with URN containing dot, see https://stackoverflow.com/questions/27963899/django-rest-framework-using-dot-in-url
    lookup_value_regex = r"[\w.:-]+"
    model = Library

    def list(self, request, *args, **kwargs):
        if not "view_library" in request.user.permissions:
            return Response(status=status.HTTP_403_FORBIDDEN)
        return Response({"results": get_available_libraries()})

    def retrieve(self, request, *args, pk, **kwargs):
        if not "view_library" in request.user.permissions:
            return Response(status=status.HTTP_403_FORBIDDEN)
            return Response(
                status=status.HTTP_403_FORBIDDEN,
            )
        library = get_library(pk)
        return Response(library)

    def destroy(self, request, *args, pk, **kwargs):
        if not RoleAssignment.is_access_allowed(
            user=request.user,
            perm=Permission.objects.get(codename="delete_library"),
            folder=Folder.get_root_folder(),
        ):
            return Response(status=status.HTTP_403_FORBIDDEN)

        library = get_library(pk)

        if library is None:
            return Response(data="Library not found.", status=status.HTTP_404_NOT_FOUND)

        # "reference_count" is not always defined (is this normal ?)
        if library.get("reference_count",0) != 0 :
            return Response(
                data="Library cannot be deleted because it has references.",
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            Library.objects.get(id=library.get("id")).delete()
        except IntegrityError as e:
            # TODO: Log the exception if logging is set up
            # logging.exception("Integrity error while deleting library: %s", e)
            print(e)
        except Exception as e:
            # TODO: Log the exception if logging is set up
            # logging.exception("Unexpected error while deleting library: %s", e)
            print(e)
            return Response(
                data="Unexpected error occurred while deleting the library.",
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["get"])
    def tree(self, request, pk):
        library = get_library(pk)
        if not library:
            return Response(
                data="This library does not exist.", status=HTTP_400_BAD_REQUEST
            )
        if not library["objects"].get("framework"):
            return Response(
                data="This library does not include a framework.",
                status=HTTP_400_BAD_REQUEST,
            )
        preview = preview_library(library)
        return Response(
            get_sorted_requirement_nodes(preview.get("requirement_nodes"), None)
        )

    @action(detail=True, methods=["get"], url_path="import")
    def import_library(self, request, pk=None):
        if not RoleAssignment.is_access_allowed(
            user=request.user,
            perm=Permission.objects.get(codename="add_library"),
            folder=Folder.get_root_folder(),
        ):
            return Response(status=status.HTTP_403_FORBIDDEN)
        library = get_library(pk)
        try:
            import_library_view(library)
            return Response({"status": "success"})
        except Exception as e:
            return Response(
                {
                    "error": "Failed to load library, please check if it has dependencies"
                },
                status=HTTP_422_UNPROCESSABLE_ENTITY,
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
            library = yaml.safe_load(attachment)

            # This code doesn't handle the library "dependencies" field yet as decribed in the architecture.

            error_msg = import_library_view(library)

            if error_msg is not None:
                return HttpResponse(
                    json.dumps({"error": error_msg}),
                    status=HTTP_422_UNPROCESSABLE_ENTITY,
                )

            return HttpResponse(json.dumps({}), status=HTTP_200_OK)
        except IntegrityError:
            return HttpResponse(
                json.dumps({"error" : "libraryAlreadyImportedError"}), status=HTTP_400_BAD_REQUEST
            )
        except :
            return HttpResponse(
                json.dumps({"error": "invalidLibraryFileError"}), status=HTTP_400_BAD_REQUEST
            )
