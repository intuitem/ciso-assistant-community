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
    RiskAssessment,
    RiskScenario,
    RiskMatrix,
    AppliedControl,
)
from core.serializers import (
    AssetWriteSerializer,
    PerimeterWriteSerializer,
    AppliedControlWriteSerializer,
    ComplianceAssessmentWriteSerializer,
    RequirementAssessmentWriteSerializer,
    FindingsAssessmentWriteSerializer,
    FindingWriteSerializer,
    UserWriteSerializer,
    RiskAssessmentWriteSerializer,
    RiskScenarioWriteSerializer,
)
from ebios_rm.serializers import ElementaryActionWriteSerializer
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
        matrix_id = request.META.get("HTTP_X_MATRIX_ID")

        logger.info(
            f"Processing file with model: {model_type}, folder: {folder_id}, perimeter: {perimeter_id}, framework: {framework_id}, matrix: {matrix_id}"
        )

        # get viewable and actionable folders, perimeters and frameworks
        # build a map from the name to the id

        res = None
        try:
            # Read Excel file into a pandas DataFrame
            df = pd.read_excel(excel_data).fillna("")
            res = self.process_data(
                request,
                df,
                model_type,
                folder_id,
                perimeter_id,
                framework_id,
                matrix_id,
            )

        except Exception as e:
            logger.error("Error parsing Excel file", exc_info=e)
            return Response(
                {"error": "ExcelParsingFailed"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {"message": "File loaded successfully", "results": []},
            status=status.HTTP_200_OK,
        )

    def process_data(
        self,
        request,
        dataframe,
        model_type,
        folder_id,
        perimeter_id,
        framework_id,
        matrix_id=None,
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
        elif model_type == "User":
            return self._process_users(request, records)
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
        elif model_type == "RiskAssessment":
            return self._process_risk_assessment(
                request, records, folder_id, perimeter_id, matrix_id
            )
        elif model_type == "ElementaryAction":
            return self._process_elementary_actions(
                request, records, folders_map, folder_id
            )
        else:
            return {
                "successful": 0,
                "failed": 0,
                "errors": [{"error": f"Unknown model type: {model_type}"}],
            }

    def _process_users(self, request, records):
        results = {"successful": 0, "failed": 0, "errors": []}
        for record in records:
            # check if the email is available
            if not record.get("email"):
                results["failed"] += 1
                results["errors"].append(
                    {"record": record, "error": "email field is mandatory"}
                )
                continue
            # Prepare data for serializer
            user_data = {
                "email": record.get("email"),  # Email is mandatory
                "first_name": record.get("first_name"),
                "last_name": record.get("last_name"),
            }
            # Use the serializer for validation and saving
            serializer = UserWriteSerializer(
                data=user_data, context={"request": request}
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
                logger.warning(f"Error creating user {record.get('email')}: {str(e)}")
                results["failed"] += 1
                results["errors"].append({"record": record, "error": str(e)})
        logger.info(
            f"User import complete. Success: {results['successful']}, Failed: {results['failed']}"
        )
        return results

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

    def _process_elementary_actions(self, request, records, folders_map, folder_id):
        """Process elementary actions import from Excel"""
        results = {"successful": 0, "failed": 0, "errors": []}

        # Define attack stage mapping (supports English and French)
        ATTACK_STAGE_MAP = {
            # English
            "know": 0,
            "reconnaissance": 0,
            "ebiosreconnaissance": 0,
            "enter": 1,
            "initial access": 1,
            "ebiosinitialaccess": 1,
            "discover": 2,
            "discovery": 2,
            "ebiosdiscovery": 2,
            "exploit": 3,
            "exploitation": 3,
            "ebiosexploitation": 3,
            # French
            "connaitre": 0,
            "connaître": 0,
            "pénétrer": 1,
            "penetrer": 1,
            "entrer": 1,
            "trouver": 2,
            "découvrir": 2,
            "decouvrir": 2,
            "exploiter": 3,
        }

        # Define icon mapping
        ICON_MAP = {
            icon.lower(): icon
            for icon in [
                "server",
                "computer",
                "cloud",
                "file",
                "diamond",
                "phone",
                "cube",
                "blocks",
                "shapes",
                "network",
                "database",
                "key",
                "search",
                "carrot",
                "money",
                "skull",
                "globe",
                "usb",
            ]
        }

        for record in records:
            # Get domain from record or use fallback
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

            # Map attack stage
            attack_stage = 0  # Default to "Know"
            if record.get("attack_stage", ""):
                attack_stage_value = str(record.get("attack_stage")).strip().lower()
                attack_stage = ATTACK_STAGE_MAP.get(attack_stage_value, 0)

            # Map icon
            icon = None
            if record.get("icon", ""):
                icon_value = str(record.get("icon")).strip().lower()
                icon = ICON_MAP.get(icon_value)

            # Prepare data for serializer
            elementary_action_data = {
                "ref_id": record.get("ref_id", ""),
                "name": record.get("name"),  # Name is mandatory
                "description": record.get("description", ""),
                "folder": domain,
                "attack_stage": attack_stage,
            }

            # Add icon if valid
            if icon:
                elementary_action_data["icon"] = icon

            # Use the serializer for validation and saving
            serializer = ElementaryActionWriteSerializer(
                data=elementary_action_data, context={"request": request}
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
                    f"Error creating elementary action {record.get('name')}: {str(e)}"
                )
                results["failed"] += 1
                results["errors"].append({"record": record, "error": str(e)})

        logger.info(
            f"Elementary Action import complete. Success: {results['successful']}, Failed: {results['failed']}"
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
                    "info": 0,
                    "low": 1,
                    "medium": 2,
                    "high": 3,
                    "critical": 4,
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
                                logger.warning("Import attempt: unknown ref_id ")
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

    def _process_risk_assessment(
        self, request, records, folder_id, perimeter_id, matrix_id
    ):
        """Process risk assessment import with the specified column structure"""
        results = {"successful": 0, "failed": 0, "errors": []}

        try:
            # Get the perimeter and its domain
            perimeter = Perimeter.objects.get(id=perimeter_id)
            domain = perimeter.folder

            # Get the risk matrix
            risk_matrix = RiskMatrix.objects.get(id=matrix_id)

            # Generate a timestamp-based name for the risk assessment
            from datetime import datetime

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            assessment_name = f"Risk_Assessment_{timestamp}"

            # Create the risk assessment
            assessment_data = {
                "name": assessment_name,
                "perimeter": perimeter_id,
                "risk_matrix": matrix_id,
                "folder": domain.id,
                "description": f"Imported risk assessment from Excel on {timestamp}",
            }

            risk_assessment_serializer = RiskAssessmentWriteSerializer(
                data=assessment_data, context={"request": request}
            )

            if not risk_assessment_serializer.is_valid():
                return {
                    "successful": 0,
                    "failed": len(records),
                    "errors": [
                        {
                            "error": "Failed to create risk assessment",
                            "details": risk_assessment_serializer.errors,
                        }
                    ],
                }

            risk_assessment = risk_assessment_serializer.save()
            logger.info(
                f"Created risk assessment: {assessment_name} with ID {risk_assessment.id}"
            )

            # Build matrix mapping dictionaries
            matrix_mappings = self._build_matrix_mappings(risk_matrix)

            # Process controls first - collect all unique control names
            all_controls = set()
            for record in records:
                existing_controls = record.get("existing_controls", "").strip()
                additional_controls = record.get("additional_controls", "").strip()

                if existing_controls:
                    all_controls.update(
                        [
                            ctrl.strip()
                            for ctrl in existing_controls.split("\n")
                            if ctrl.strip()
                        ]
                    )
                if additional_controls:
                    all_controls.update(
                        [
                            ctrl.strip()
                            for ctrl in additional_controls.split("\n")
                            if ctrl.strip()
                        ]
                    )

            # Create or find controls in the domain
            control_mapping = self._create_or_find_controls(
                list(all_controls), domain, request
            )

            # Process each record to create risk scenarios
            for record in records:
                try:
                    scenario_data = self._process_risk_scenario_record(
                        record,
                        risk_assessment,
                        matrix_mappings,
                        control_mapping,
                        request,
                    )
                    if scenario_data:
                        results["successful"] += 1
                    else:
                        results["failed"] += 1
                        results["errors"].append(
                            {
                                "record": record,
                                "error": "Failed to create risk scenario",
                            }
                        )

                except Exception as e:
                    logger.warning(f"Error creating risk scenario: {str(e)}")
                    results["failed"] += 1
                    results["errors"].append({"record": record, "error": str(e)})

            logger.info(
                f"Risk Assessment import complete. Success: {results['successful']}, Failed: {results['failed']}"
            )
            return results

        except Perimeter.DoesNotExist:
            return {
                "successful": 0,
                "failed": len(records),
                "errors": [
                    {"error": f"Perimeter with ID {perimeter_id} does not exist"}
                ],
            }
        except RiskMatrix.DoesNotExist:
            return {
                "successful": 0,
                "failed": len(records),
                "errors": [
                    {"error": f"Risk matrix with ID {matrix_id} does not exist"}
                ],
            }
        except Exception as e:
            logger.error(f"Error in risk assessment processing: {str(e)}")
            return {
                "successful": 0,
                "failed": len(records),
                "errors": [{"error": f"Failed to process risk assessment: {str(e)}"}],
            }

    def _build_matrix_mappings(self, risk_matrix):
        """Build label-to-value mapping dictionaries for probability and impact"""
        mappings = {"probability": {}, "impact": {}}

        try:
            matrix_definition = risk_matrix.json_definition

            # Build probability mapping
            if "probability" in matrix_definition:
                for prob_def in matrix_definition["probability"]:
                    prob_id = prob_def.get("id")
                    name = prob_def.get("name", "")

                    # Add base name
                    if name and prob_id is not None:
                        mappings["probability"][name.lower()] = prob_id

                    # Add translated names
                    if "translations" in prob_def:
                        for lang, translation in prob_def["translations"].items():
                            translated_name = translation.get("name", "")
                            if translated_name and prob_id is not None:
                                mappings["probability"][translated_name.lower()] = (
                                    prob_id
                                )

            # Build impact mapping
            if "impact" in matrix_definition:
                for impact_def in matrix_definition["impact"]:
                    impact_id = impact_def.get("id")
                    name = impact_def.get("name", "")

                    # Add base name
                    if name and impact_id is not None:
                        mappings["impact"][name.lower()] = impact_id

                    # Add translated names
                    if "translations" in impact_def:
                        for lang, translation in impact_def["translations"].items():
                            translated_name = translation.get("name", "")
                            if translated_name and impact_id is not None:
                                mappings["impact"][translated_name.lower()] = impact_id

            # Note: Risk levels are automatically computed by the system
            # based on probability and impact values, so no need to map them

        except Exception as e:
            logger.warning(f"Error building matrix mappings: {str(e)}")
            logger.debug(f"Matrix definition structure: {matrix_definition}")

        return mappings

    def _create_or_find_controls(self, control_names, domain, request):
        """Create or find controls in the specified domain"""
        control_mapping = {}

        for control_name in control_names:
            if not control_name:
                continue

            # Try to find existing control in the domain
            existing_control = AppliedControl.objects.filter(
                name=control_name, folder=domain
            ).first()

            if existing_control:
                control_mapping[control_name] = existing_control.id
            else:
                # Create new control
                try:
                    control_data = {
                        "name": control_name,
                        "folder": domain.id,
                        "description": f"Control imported from risk assessment",
                        "status": "to_do",
                    }

                    control_serializer = AppliedControlWriteSerializer(
                        data=control_data, context={"request": request}
                    )

                    if control_serializer.is_valid():
                        control = control_serializer.save()
                        control_mapping[control_name] = control.id
                        logger.info(f"Created control: {control_name}")
                    else:
                        logger.warning(
                            f"Failed to create control {control_name}: {control_serializer.errors}"
                        )

                except Exception as e:
                    logger.warning(f"Error creating control {control_name}: {str(e)}")

        return control_mapping

    def _process_risk_scenario_record(
        self, record, risk_assessment, matrix_mappings, control_mapping, request
    ):
        """Process a single risk scenario record"""
        try:
            # Extract basic fields
            ref_id = record.get("ref_id", "")
            name = record.get("name", "")
            description = record.get("description", "")

            if not name:
                raise ValueError("Risk scenario name is required")

            # Map risk values using matrix mappings
            inherent_impact = self._map_risk_value(
                record.get("inherent_impact", ""), matrix_mappings["impact"]
            )
            inherent_proba = self._map_risk_value(
                record.get("inherent_proba", ""), matrix_mappings["probability"]
            )

            current_impact = self._map_risk_value(
                record.get("current_impact", ""), matrix_mappings["impact"]
            )
            current_proba = self._map_risk_value(
                record.get("current_proba", ""), matrix_mappings["probability"]
            )

            residual_impact = self._map_risk_value(
                record.get("residual_impact", ""), matrix_mappings["impact"]
            )
            residual_proba = self._map_risk_value(
                record.get("residual_proba", ""), matrix_mappings["probability"]
            )

            # Prepare risk scenario data
            # Note: inherent_level, current_level, and residual_level will be computed automatically
            scenario_data = {
                "ref_id": ref_id,
                "name": name,
                "description": description,
                "risk_assessment": risk_assessment.id,
                "inherent_impact": inherent_impact,
                "inherent_proba": inherent_proba,
                "current_impact": current_impact,
                "current_proba": current_proba,
                "residual_impact": residual_impact,
                "residual_proba": residual_proba,
                "existing_controls": record.get("existing_controls", ""),
            }

            # Create the risk scenario
            scenario_serializer = RiskScenarioWriteSerializer(
                data=scenario_data, context={"request": request}
            )

            if not scenario_serializer.is_valid():
                logger.warning(
                    f"Risk scenario validation failed: {scenario_serializer.errors}"
                )
                return None

            risk_scenario = scenario_serializer.save()

            # Link existing controls
            self._link_controls_to_scenario(
                risk_scenario,
                record.get("existing_controls", ""),
                control_mapping,
                "existing_applied_controls",
            )

            # Link additional controls
            self._link_controls_to_scenario(
                risk_scenario,
                record.get("additional_controls", ""),
                control_mapping,
                "applied_controls",
            )

            return risk_scenario

        except Exception as e:
            logger.warning(f"Error processing risk scenario record: {str(e)}")
            raise e

    def _map_risk_value(self, value, mapping_dict):
        """Map a risk value label to its numeric value using the mapping dictionary"""
        if not value or not isinstance(value, str):
            return -1

        # Try exact match first
        clean_value = value.strip().lower()
        if clean_value in mapping_dict:
            return mapping_dict[clean_value]

        # If no match found, return -1 (undefined)
        return -1

    def _link_controls_to_scenario(
        self, risk_scenario, controls_text, control_mapping, field_name
    ):
        """Link controls to a risk scenario based on control names"""
        if not controls_text:
            return

        control_names = [
            ctrl.strip() for ctrl in controls_text.split("\n") if ctrl.strip()
        ]
        control_ids = []

        for control_name in control_names:
            if control_name in control_mapping:
                control_ids.append(control_mapping[control_name])

        if control_ids:
            # Get the field and set the many-to-many relationship
            field = getattr(risk_scenario, field_name)
            field.set(control_ids)
