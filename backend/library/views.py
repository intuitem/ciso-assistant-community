import json
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db.models import QuerySet
from rest_framework import viewsets, permissions, status
from rest_framework.generics import get_object_or_404
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
    HTTP_422_UNPROCESSABLE_ENTITY,
)
from rest_framework.parsers import FileUploadParser
from rest_framework.views import APIView

from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.http import HttpResponse
import yaml

from core.helpers import get_sorted_requirement_nodes
from core.models import StoredLibrary, LoadedLibrary
from core.views import BaseModelViewSet
from iam.models import RoleAssignment, Folder, Permission
from library.validators import validate_file_extension
from .helpers import preview_library


from rest_framework.decorators import action
from rest_framework.response import Response
from .serializers import StoredLibrarySerializer, LoadedLibrarySerializer, LibraryUploadSerializer
from .utils import LibraryImporter, get_available_libraries, get_library, import_library_view

class StoredLibraryViewSet(viewsets.ModelViewSet):
    # serializer_class = StoredLibrarySerializer
    # parser_classes = [FileUploadParser]

    # solve issue with URN containing dot, see https://stackoverflow.com/questions/27963899/django-rest-framework-using-dot-in-url
    lookup_value_regex = r"[\w.:-]+"
    model = StoredLibrary

    def list(self, request, *args, **kwargs):
        if not "view_storedlibrary" in request.user.permissions:
            return Response(status=status.HTTP_403_FORBIDDEN)
        available_libraries = StoredLibrary.objects.filter(is_obsolete=False).values("name","description","urn","ref_id","locale","version","packager","provider","builtin","objects_meta") # The frontend doesn't receive the obsolete libraries for now.

        return Response({"results": available_libraries})

    def retrieve(self, request, *args, pk, **kwargs):
        if not "view_storedlibrary" in request.user.permissions:
            return Response(status=status.HTTP_403_FORBIDDEN)
        return StoredLibrary.objects.get(pk=urn) # Handle the exception if the pk urn doesn't exist
        # raise NotImplementedError() # This method must be implemented.

    @action(detail=True, methods=["get"], url_path="import")
    def import_library(self, request, pk=None):
        if not RoleAssignment.is_access_allowed(
            user=request.user,
            perm=Permission.objects.get(codename="add_loadedlibrary"),
            folder=Folder.get_root_folder(),
        ):
            return Response(status=status.HTTP_403_FORBIDDEN)
        library = StoredLibrary.objects.get(urn=pk) # This is only fetching the lib by URN without caring about the locale or the version, this must change in the future.

        # return Response({"error":f"ERROR !!! {str(lib)}"},status=status.HTTP_403_FORBIDDEN)
        # library = get_library(pk)
        try:
            error_msg = library.loads()
            if error_msg is not None :
                return Response({"status":"error","error":error_msg},status=status.HTTP_400_BAD_REQUEST) # This can cause translation issues
            return Response({"status": "success"})
        except Exception as e:
            """print(f"ERROR {type(e)}")
            print(str(e))
            raise e"""
            return Response(
                {
                    "error": "Failed to load library, please check if it has dependencies"
                }, # This must translated
                status=HTTP_422_UNPROCESSABLE_ENTITY,
            )

    @action(detail=True, methods=["get"])
    def tree(self, request, pk):
        lib = StoredLibrary.objects.get(urn=pk) # It should return a 404 error if the query doesn't return anything and therefore raise an exception
        library_objects = json.loads(lib.content) # We need caching for this
        """library = {
            "id": lib.id,
            "urn": lib.urn,
            "name": lib.name,
            "description": lib.description,
            "provider": lib.provider,
            "packager": lib.packager,
            "copyright": lib.copyright,
            "reference_count": lib.reference_count,
            "objects": library_objects,
        }"""
        """if not library:
            return Response(
                data="This library does not exist.", status=HTTP_404_NOT_FOUND
            )"""
        if not library_objects.get("framework"):
            return Response(
                data="This library does not include a framework.",
                status=HTTP_400_BAD_REQUEST,
            )
        preview = preview_library(library_objects)
        return Response(
            get_sorted_requirement_nodes(preview.get("requirement_nodes"), None)
        )

class LoadedLibraryViewSet(viewsets.ModelViewSet):
    serializer_class = LoadedLibrarySerializer
    parser_classes = [FileUploadParser]

    # solve issue with URN containing dot, see https://stackoverflow.com/questions/27963899/django-rest-framework-using-dot-in-url
    lookup_value_regex = r"[\w.:-]+"
    model = LoadedLibrary

    def list(self, request, *args, **kwargs):
        if not "view_storedlibrary" in request.user.permissions:
            return Response(status=status.HTTP_403_FORBIDDEN)
        available_libraries = LoadedLibrary.objects.all().values("name","description","urn","ref_id","locale","version","packager","provider","builtin","objects_meta")

        return Response({"results": available_libraries})
        # return Response({"results": get_available_libraries()})

    def retrieve(self, request, *args, pk, **kwargs):
        if not "view_loadedlibrary" in request.user.permissions:
            return Response(status=status.HTTP_403_FORBIDDEN)
        raise NotImplementedError() # This method must me implemented
        # library = get_library(pk)
        # return Response(library)

    def destroy(self, request, *args, pk, **kwargs):
        if not RoleAssignment.is_access_allowed(
            user=request.user,
            perm=Permission.objects.get(codename="delete_loadedlibrary"),
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
            LoadedLibrary.objects.get(id=library.get("id")).delete()
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
        lib = get_library(pk)
        # library_objects = json.loads(lib.content) # How to this for loaded libarries
        if not library:
            return Response(
                data="This library does not exist.", status=HTTP_404_NOT_FOUND
            )
        if not library["objects"].get("framework"):
            return Response(
                data="This library does not include a framework.",
                status=HTTP_400_BAD_REQUEST,
            )
        preview = preview_library(library_objects)
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
