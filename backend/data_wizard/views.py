import io
import logging
import pandas as pd
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import FileUploadParser
from .serializers import LoadFileSerializer
from core.models import (
    AppliedControl,
    Folder,
    Perimeter,
    Asset,
    ComplianceAssessment,
    RequirementAssessment,
    Framework,
)
from iam.models import RoleAssignment

logger = logging.getLogger(__name__)


def get_accessible_objects(user):
    (viewable_folders_ids, _, _) = RoleAssignment.get_accessible_object_ids(
        Folder.get_root_folder(), user, Folder
    )
    (viewable_perimeters_ids, _, _) = RoleAssignment.get_accessible_object_ids(
        Folder.get_root_folder(), user, Perimeter
    )
    (viewable_frameworks_ids, _, _) = RoleAssignment.get_accessible_object_ids(
        Folder.get_root_folder(), user, Framework
    )

    folders_map = {
        f.name: f.id for f in Folder.objects.filter(id__in=viewable_folders_ids)
    }
    return folders_map


class LoadFileView(APIView):
    parser_classes = (FileUploadParser,)
    serializer_class = LoadFileSerializer

    def process_excel_file(self, request, excel_data):
        # Parse Excel data
        # Note: I can still pick the request.user for extra checks on the legit access for write operations
        model_type = request.META.get("HTTP_X_MODEL_TYPE")
        folder_id = request.META.get("HTTP_X_FOLDER_ID")
        perimeter_id = request.META.get("HTTP_X_PERIMETER_ID")
        framework_id = request.META.get("HTTP_X_FRAMEWORK_ID")

        logger.info(
            f"Processing file with model: {model_type}, folder: {folder_id}, perimeter: {perimeter_id}, framework: {framework_id}"
        )

        # get viewable and actionable folders, perimeters and frameworks
        # build a map from the name to the id
        try:
            # Read Excel file into a pandas DataFrame
            df = pd.read_excel(excel_data).fillna("")
            res = self.process_data(
                request, df, model_type, folder_id, perimeter_id, framework_id
            )

        except Exception as e:
            logger.error("Error parsing Excel file", exc_info=e)
            return Response(
                {"error": "ExcelParsingFailed"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {"message": "File loaded successfully"}, status=status.HTTP_200_OK
        )

    def process_data(
        self, request, dataframe, model_type, folder_id, perimeter_id, framework_id
    ):
        records = dataframe.to_dict(orient="records")
        print(records)
        logger.warning("I am here")
        folders_map = get_accessible_objects(request.user)

        # Assets processing
        if model_type == "Asset":
            for record in records:
                # if folder is set use it on the folder map to get the id, otherwise fallback to folder_id passed
                domain = folder_id
                if record.get("domain") != "":
                    domain = folders_map[record.get("domain")]

                domain_obj = Folder.objects.get(id=domain)
                try:
                    res = Asset(
                        ref_id=record.get("ref_id"),
                        name=record.get("name"),
                        type=record.get("type"),
                        folder=domain_obj,
                        description=record.get("description"),
                    ).save()
                except Exception as e:
                    logger.warning(e)
                    # we can improve this by collecting the error types and aggregate them
                # this will fail in case another object with the same name exists

        if model_type == "AppliedControl":
            for record in records:
                domain = folder_id
                if record.get("domain") != "":
                    domain = folders_map[record.get("domain")]

                domain_obj = Folder.objects.get(id=domain)
                # note to self: maybe we can do a dry run by just skipping the save to get the validators triggered
                try:
                    res = AppliedControl(
                        ref_id=record.get("ref_id"),
                        name=record.get("name"),
                        folder=domain_obj,
                        status=record.get("status"),
                        priority=int(record.get("priority"))
                        if record.get("priority") != ""
                        else None,
                        csf_function=record.get("csf_function"),
                    ).save()

                except Exception as e:
                    logger.warning(e)

        if model_type == "ComplianceAssessment":
            # create an audit on the perimeter_id with the framework_id - use a timestamp based name
            # get back the compliance assessment id
            # crawl the records and update the requirement assessment matching the ref_id if available and fallback to the urn otherwise
            pass

    def post(self, request, *args, **kwargs):
        # if not request.user.has_file_permission:
        #     logger.error("Unauthorized user tried to load a file", user=request.user)
        #     return Response({}, status=status.HTTP_403_FORBIDDEN)

        if not request.data:
            logger.error("Request has no data")
            return Response(
                {"error": "fileLoadNoData"}, status=status.HTTP_400_BAD_REQUEST
            )

        file_obj = request.data.get("file")
        if not file_obj:
            logger.error("No file provided")
            return Response(
                {"error": "noFileProvided"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Check if the file is an Excel file
        file_extension = file_obj.name.split(".")[-1].lower()
        if file_extension not in ["xlsx", "xls"]:
            logger.error(f"Unsupported file format: {file_extension}")
            return Response(
                {"error": "unsupportedFileFormat"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Read the file content
        file_data = file_obj.read()

        # Process the Excel file
        return self.process_excel_file(request, io.BytesIO(file_data))
