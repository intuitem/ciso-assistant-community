import io
import logging
import pandas as pd
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import FileUploadParser
from .serializers import LoadFileSerializer
from core.models import (
    Folder,
    Perimeter,
    RequirementAssessment,
    Framework,
    RequirementNode,
)
from core.serializers import (
    AssetWriteSerializer,
    PerimeterWriteSerializer,
    AppliedControlWriteSerializer,
    ComplianceAssessmentWriteSerializer,
    RequirementAssessmentWriteSerializer,
    FindingsAssessmentWriteSerializer,
    FindingWriteSerializer,
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

        res = None
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
            {"message": "File loaded successfully", "results": res},
            status=status.HTTP_200_OK,
        )

    def process_data(
        self, request, dataframe, model_type, folder_id, perimeter_id, framework_id
    ):
        records = dataframe.to_dict(orient="records")
        logger.warning("I am here")
        folders_map = get_accessible_objects(request.user)

        # Dispatch to appropriate handler
        if model_type == "Asset":
            return self._process_assets(request, records, folders_map, folder_id)
        elif model_type == "AppliedControl":
            return self._process_applied_controls(
                request, records, folders_map, folder_id
            )
        elif model_type == "Perimeter":
            return self._process_perimeters(request, records, folders_map, folder_id)
        elif model_type == "ComplianceAssessment":
            return self._process_compliance_assessment(
                request, records, folder_id, perimeter_id, framework_id
            )
        elif model_type == "FindingsAssessment":
            return self._process_findings_assessment(
                request,
                records,
                folder_id,
                perimeter_id,
            )
        else:
            return {
                "successful": 0,
                "failed": 0,
                "errors": [{"error": f"Unknown model type: {model_type}"}],
            }

    def _process_assets(self, request, records, folders_map, folder_id):
        # Collection to track successes and errors
        results = {"successful": 0, "failed": 0, "errors": []}

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
                "type": record.get("type", "SP"),
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
                logger.warning(f"Error creating asset {record.get('name')}: {str(e)}")
                results["failed"] += 1
                results["errors"].append({"record": record, "error": str(e)})
        logger.info(
            f"Asset import complete. Success: {results['successful']}, Failed: {results['failed']}"
        )
        return results

    def _process_applied_controls(self, request, records, folders_map, folder_id):
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
                "description": record.get("description", ""),
                "category": record.get("category", ""),
                "folder": domain,
                "status": record.get("status", "to_do"),
                "priority": priority,
                "csf_function": record.get("csf_function", "govern"),
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
        return results

    def _process_perimeters(self, request, records, folders_map, folder_id):
        # Collection to track successes and errors
        results = {"successful": 0, "failed": 0, "errors": []}

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
            perimeter_data = {
                "ref_id": record.get("ref_id", ""),
                "name": record.get("name"),  # Name is mandatory
                "folder": domain,
                "description": record.get("description", ""),
                "status": record.get("status"),
            }
            # Use the serializer for validation and saving
            serializer = PerimeterWriteSerializer(
                data=perimeter_data, context={"request": request}
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
                    f"Error creating perimeter {record.get('name')}: {str(e)}"
                )
                results["failed"] += 1
                results["errors"].append({"record": record, "error": str(e)})
        logger.info(
            f"Perimeter import complete. Success: {results['successful']}, Failed: {results['failed']}"
        )
        return results

    def _process_findings_assessment(self, request, records, folder_id, perimeter_id):
        results = {"successful": 0, "failed": 0, "errors": []}
        try:
            perimeter = Perimeter.objects.get(id=perimeter_id)
            folder_id = perimeter.folder.id

            from datetime import datetime

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            assessment_name = f"Followup_{timestamp}"
            assessment_data = {
                "name": assessment_name,
                "perimeter": perimeter_id,
                "folder": folder_id,
            }

            # Use the serializer for validation and saving
            serializer = FindingsAssessmentWriteSerializer(
                data=assessment_data,
                context={"request": request},
            )

            if serializer.is_valid(raise_exception=True):
                findings_assessment = serializer.save()
                logger.info(
                    f"Created follow-up: {assessment_name} with ID {findings_assessment.id}"
                )

                SEVERITY_MAP = {
                    "low": 0,
                    "medium": 1,
                    "high": 2,
                    "critical": 3,
                }

                for record in records:
                    try:
                        if record.get("name") == "":
                            results["failed"] += 1
                            results["errors"].append(
                                {"record": record, "error": "Name field is mandatory"}
                            )
                            continue
                        finding_data = {
                            "ref_id": record.get("ref_id"),
                            "name": record.get("name"),
                            "description": record.get("description"),
                            "status": record.get("status"),
                            "findings_assessment": findings_assessment.id,
                        }
                        severity = -1
                        if record.get("severity") != "":
                            severity = SEVERITY_MAP.get(record.get("severity"), -1)
                        finding_data.update({"severity": severity})

                        finding_writer = FindingWriteSerializer(
                            data=finding_data, context={"request": request}
                        )
                        if finding_writer.is_valid(raise_exception=True):
                            finding_writer.save()
                            results["successful"] += 1
                        else:
                            logger.info(f"Data validation failed for finding creation")
                            results["failed"] += 1
                            results["errors"].append(
                                {
                                    "record": record,
                                }
                            )
                    except Exception as e:
                        logger.warning(f"Error creating finding: {str(e)}")
                        results["failed"] += 1
                        results["errors"].append({"record": record, "error": str(e)})
        except Exception as e:
            logger.error(f"Error in findings assessment processing: {str(e)}")
            results["failed"] += len(records)
            results["errors"].append({"error": str(e)})
        return results

    def _process_compliance_assessment(
        self, request, records, folder_id, perimeter_id, framework_id
    ):
        results = {"successful": 0, "failed": 0, "errors": []}
        try:
            # Get the perimeter object to extract its folder ID
            perimeter = Perimeter.objects.get(id=perimeter_id)
            folder_id = perimeter.folder.id

            # Generate a timestamp-based name if not provided
            from datetime import datetime

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            assessment_name = f"Assessment_{timestamp}"

            # Prepare data for serializer
            assessment_data = {
                "name": assessment_name,
                "perimeter": perimeter_id,
                "framework": framework_id,
                "folder": folder_id,
            }

            # Use the serializer for validation and saving
            serializer = ComplianceAssessmentWriteSerializer(
                data=assessment_data,
                context={"request": request},
            )

            if serializer.is_valid(raise_exception=True):
                # Save the compliance assessment
                compliance_assessment = serializer.save()
                compliance_assessment.create_requirement_assessments()
                logger.info(
                    f"Created compliance assessment: {assessment_name} with ID {compliance_assessment.id}"
                )

                # Now process all the requirement assessments from the records
                for record in records:
                    # Check if we have a requirement reference
                    ref_id = record.get("ref_id")
                    urn = record.get("urn")
                    if not record.get("assessable"):
                        logger.debug("Skipping unassessable item.")
                        continue
                    if not (ref_id or urn):
                        results["failed"] += 1
                        results["errors"].append(
                            {
                                "record": record,
                                "error": "Neither ref_id nor urn provided for requirement",
                            }
                        )
                        continue

                    try:
                        requirement_assessment = None
                        # Try to find the requirement assessment using ref_id first, then urn
                        if ref_id:
                            ReqNode = RequirementNode.objects.filter(
                                framework__id=framework_id, ref_id=ref_id
                            ).first()
                            if ReqNode:
                                requirement_assessment = (
                                    RequirementAssessment.objects.filter(
                                        compliance_assessment=compliance_assessment
                                    )
                                    .filter(requirement=ReqNode)
                                    .first()
                                )
                            else:
                                logger.warn("Import attempt: unknown ref_id ")
                        elif urn:
                            ReqNode = RequirementNode.objects.filter(
                                framework__id=framework_id, urn=urn
                            ).first()
                            if ReqNode:
                                requirement_assessment = (
                                    RequirementAssessment.objects.filter(
                                        compliance_assessment=compliance_assessment
                                    )
                                    .filter(requirement=ReqNode)
                                    .first()
                                )
                            else:
                                logger.error("Import attempt: unknown urn")

                        if requirement_assessment:
                            # Update the requirement assessment with the data from the record
                            requirement_data = {
                                "result": record.get("compliance_result")
                                if record.get("compliance_result") != ""
                                else "not_assessed",
                                "status": record.get("requirement_progress")
                                if record.get("requirement_progress") != ""
                                else "to_do",
                                "observation": record.get("observations", ""),
                            }
                            if record.get("score") != "":
                                requirement_data.update(
                                    {"score": record.get("score"), "is_scored": True}
                                )
                            # Use the serializer for validation and saving
                            req_serializer = RequirementAssessmentWriteSerializer(
                                instance=requirement_assessment,
                                data=requirement_data,
                                partial=True,
                                context={"request": request},
                            )
                            if req_serializer.is_valid(raise_exception=True):
                                req_serializer.save()
                                results["successful"] += 1
                            else:
                                results["failed"] += 1
                                results["errors"].append(
                                    {
                                        "record": record,
                                        "errors": req_serializer.errors,
                                    }
                                )
                        else:
                            results["failed"] += 1
                            results["errors"].append(
                                {
                                    "record": record,
                                    "error": f"No matching requirement found with ref_id '{ref_id}' or urn '{urn}'",
                                }
                            )
                    except Exception as e:
                        logger.warning(
                            f"Error updating requirement assessment: {str(e)}"
                        )
                        results["failed"] += 1
                        results["errors"].append({"record": record, "error": str(e)})
                logger.info(
                    f"Compliance Assessment import complete. Success: {results['successful']}, Failed: {results['failed']}"
                )
                # print(results)
                return results

        except Perimeter.DoesNotExist:
            logger.error(f"Perimeter with ID {perimeter_id} does not exist")
            return Response(
                {"error": f"Perimeter with ID {perimeter_id} does not exist"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            logger.error(f"Error creating compliance assessment: {str(e)}")
            return Response(
                {"error": f"Failed to create compliance assessment: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return results

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
