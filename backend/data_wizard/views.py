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
from core.serializers import (
    AssetWriteSerializer,
    AppliedControlWriteSerializer,
    ComplianceAssessmentWriteSerializer,
    RequirementAssessmentWriteSerializer,
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

        # Collection to track successes and errors
        results = {"successful": 0, "failed": 0, "errors": []}

        # Assets processing
        if model_type == "Asset":
            for record in records:
                # if folder is set use it on the folder map to get the id, otherwise fallback to folder_id passed
                domain = folder_id
                if record.get("domain") != "":
                    domain = folders_map.get(record.get("domain"), folder_id)
                # Check if name is provided as it's mandatory
                if not record.get("name"):
                    results["failed"] += 1
                    results["errors"].append(
                        {"record": record, "error": "Name field is mandatory"}
                    )
                    continue

                # Prepare data for serializer
                asset_data = {
                    "ref_id": record.get("ref_id", ""),
                    "name": record.get("name"),  # Name is mandatory
                    "type": record.get("type", ""),
                    "folder": domain,
                    "description": record.get("description", ""),
                }
                # Use the serializer for validation and saving
                serializer = AssetWriteSerializer(
                    data=asset_data, context={"request": request}
                )
                try:
                    if serializer.is_valid(raise_exception=True):
                        serializer.save()
                        results["successful"] += 1
                    else:
                        results["failed"] += 1
                        results["errors"].append(
                            {"record": record, "errors": serializer.errors}
                        )
                except Exception as e:
                    logger.warning(
                        f"Error creating asset {record.get('name')}: {str(e)}"
                    )
                    results["failed"] += 1
                    results["errors"].append({"record": record, "error": str(e)})
            logger.info(
                f"Asset import complete. Success: {results['successful']}, Failed: {results['failed']}"
            )

        # Applied Controls processing
        if model_type == "AppliedControl":
            # Reset results counter for this model type
            results = {"successful": 0, "failed": 0, "errors": []}

            for record in records:
                domain = folder_id
                if record.get("domain") != "":
                    domain = folders_map.get(record.get("domain"), folder_id)

                # Handle priority conversion with error checking
                priority = None
                if record.get("priority", ""):
                    try:
                        priority = int(record.get("priority"))
                    except (ValueError, TypeError):
                        priority = None

                # Check if name is provided as it's mandatory
                if not record.get("name"):
                    results["failed"] += 1
                    results["errors"].append(
                        {"record": record, "error": "Name field is mandatory"}
                    )
                    continue

                # Prepare data for serializer
                control_data = {
                    "ref_id": record.get("ref_id", ""),
                    "name": record.get("name"),  # Name is mandatory
                    "folder": domain,
                    "status": record.get("status", ""),
                    "priority": priority,
                    "csf_function": record.get("csf_function", ""),
                }

                # Use the serializer for validation and saving
                serializer = AppliedControlWriteSerializer(
                    data=control_data, context={"request": request}
                )
                try:
                    if serializer.is_valid(raise_exception=True):
                        serializer.save()
                        results["successful"] += 1
                    else:
                        results["failed"] += 1
                        results["errors"].append(
                            {"record": record, "errors": serializer.errors}
                        )
                except Exception as e:
                    logger.warning(
                        f"Error creating applied control {record.get('name')}: {str(e)}"
                    )
                    results["failed"] += 1
                    results["errors"].append({"record": record, "error": str(e)})

            logger.info(
                f"Applied Control import complete. Success: {results['successful']}, Failed: {results['failed']}"
            )

        if model_type == "ComplianceAssessment":
            # create an audit on the perimeter_id with the framework_id - use a timestamp based name
            # get back the compliance assessment id
            # crawl the records and update the requirement assessment matching the ref_id if available and fallback to the urn otherwise
            pass

        return Response(results)

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
