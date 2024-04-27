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
from .serializers import StoredLibraryDetailedSerializer, LoadedLibrarySerializer, LoadedLibraryDetailedSerializer, LibraryUploadSerializer
from .utils import LibraryImporter, get_available_libraries, get_library, import_library_view

class StoredLibraryViewSet(viewsets.ModelViewSet):
    # serializer_class = StoredLibrarySerializer
    parser_classes = [FileUploadParser]

    # solve issue with URN containing dot, see https://stackoverflow.com/questions/27963899/django-rest-framework-using-dot-in-url
    lookup_value_regex = r"[\w.:-]+"
    model = StoredLibrary
    queryset = StoredLibrary.objects.filter(is_obsolete=False)

    def list(self, request, *args, **kwargs):
        if not "view_storedlibrary" in request.user.permissions:
            return Response(status=status.HTTP_403_FORBIDDEN)
        available_libraries = self.queryset.values("id","name","description","urn","ref_id","locale","version","packager","provider","builtin","objects_meta","is_imported") # The frontend doesn't receive the obsolete libraries for now.

        return Response({"results": available_libraries})

    def destroy(self, request, pk): # We may have to also get the locale of the library we want to delete in the future for this method and all other libary viewset methods which goal is to apply an operation on a specific library
        if not RoleAssignment.is_access_allowed(
            user=request.user,
            perm=Permission.objects.get(codename="delete_storedlibrary"),
            folder=Folder.get_root_folder(),
        ):
            return Response(status=status.HTTP_403_FORBIDDEN)

        try :
            lib = self.queryset.get(urn=pk) # the libraries with is_obsolete=True are not displayed in the frontend and therefore not meant to be destroyable (at least yet)
        except :
            return Response(data="Library not found.", status=status.HTTP_404_NOT_FOUND)

        lib.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def retrieve(self, request, *args, pk, **kwargs):
        if not "view_storedlibrary" in request.user.permissions:
            return Response(status=status.HTTP_403_FORBIDDEN)
        try :
            lib = self.queryset.get(urn=pk)
        except :
            return Response(data="Library not found.", status=status.HTTP_404_NOT_FOUND)
        return Response(StoredLibraryDetailedSerializer(lib).data)

    @action(detail=True, methods=["get"], url_path="import")
    def import_library(self, request, pk):
        if not RoleAssignment.is_access_allowed(
            user=request.user,
            perm=Permission.objects.get(codename="add_loadedlibrary"),
            folder=Folder.get_root_folder(),
        ):
            return Response(status=status.HTTP_403_FORBIDDEN)
        try :
            library = StoredLibrary.objects.get(urn=pk) # This is only fetching the lib by URN without caring about the locale or the version, this must change in the future.
        except :
            return Response(data="Library not found.", status=status.HTTP_404_NOT_FOUND)

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
        try :
            lib = StoredLibrary.objects.get(urn=pk)
        except :
            return Response(data="Library not found.", status=status.HTTP_404_NOT_FOUND)

        library_objects = json.loads(lib.content) # We may need caching for this
        if not (framework := library_objects.get("framework")) :
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

            content = attachment.read() # Should we read it chunck by chunck or ensure that the file size of the libary content is reasonnable before reading ?

            error_msg = StoredLibrary.store_libary_content(content)

            if error_msg is not None:
                return HttpResponse(
                    json.dumps({"error": error_msg}),
                    status=HTTP_422_UNPROCESSABLE_ENTITY,
                )

            return HttpResponse(json.dumps({}), status=HTTP_200_OK)
        except IntegrityError:
            return HttpResponse(
                json.dumps({"error": "libraryAlreadyImportedError"}),
                status=HTTP_400_BAD_REQUEST,
            )
        except :
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
        if not "view_storedlibrary" in request.user.permissions:
            return Response(status=status.HTTP_403_FORBIDDEN)

        loaded_libraries = [{
                key: getattr(library,key)
                for key in ["id","name","description","urn","ref_id","locale","version","packager","provider","builtin","objects_meta","reference_count"]
            }
            for library in LoadedLibrary.objects.all()
        ]
        return Response({"results": loaded_libraries})

    def retrieve(self, request, *args, pk, **kwargs):
        if not "view_loadedlibrary" in request.user.permissions:
            return Response(status=status.HTTP_403_FORBIDDEN)
        try :
            lib = LoadedLibrary.objects.get(urn=pk) # There is no "locale" value involved in the fetch + we have to handle the exception if the pk urn doesn't exist
        except :
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

        try :
            lib = LoadedLibrary.objects.get(urn=pk)
        except :
            return Response(data="Library not found.", status=status.HTTP_404_NOT_FOUND)

        if lib.reference_count != 0:
            return Response(
                data="Library cannot be deleted because it has references.",
                status=status.HTTP_400_BAD_REQUEST,
            )

        lib.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["get"])
    def tree(self, request, pk): # We must ensure that users that are not allowed to read the content of libraries can't have any access to them either from the /api/{URLModel/{library_urn}/tree view or the /api/{URLModel}/{library_urn} view.
        try :
            lib = LoadedLibrary.objects.get(urn=pk)
        except :
            return Response(data="Library not found.", status=status.HTTP_404_NOT_FOUND)

        if lib.frameworks.count() == 0:
            return Response(
                data="This library doesn't contain any framework.", status=HTTP_404_NOT_FOUND
            )

        framework = lib.frameworks.first()
        requirement_nodes = framework.requirement_nodes.all()
        return Response(
            get_sorted_requirement_nodes(requirement_nodes, None)
        )

