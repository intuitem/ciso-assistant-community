import io
import logging
import pandas as pd
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import FileUploadParser
from .serializers import LoadFileSerializer
from core.models import (
    Asset,
    Folder,
    Perimeter,
    RequirementAssessment,
    Framework,
    RequirementNode,
    RiskAssessment,
    RiskScenario,
    RiskMatrix,
    AppliedControl,
    ReferenceControl,
    Threat,
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
    ReferenceControlWriteSerializer,
    ThreatWriteSerializer,
    FolderWriteSerializer,
)
from ebios_rm.models import (
    EbiosRMStudy,
    FearedEvent,
    RoTo,
    Stakeholder,
    StrategicScenario,
    AttackPath,
    ElementaryAction,
)
from ebios_rm.serializers import (
    ElementaryActionWriteSerializer,
    EbiosRMStudyWriteSerializer,
)
from core.models import Terminology
from data_wizard.arm_helpers import process_arm_file
from tprm.models import Entity, Solution, Contract
from tprm.serializers import (
    EntityWriteSerializer,
    SolutionWriteSerializer,
    ContractWriteSerializer,
)
from privacy.models import Processing, ProcessingNature
from privacy.serializers import ProcessingWriteSerializer
from iam.models import RoleAssignment, User
from core.models import FilteringLabel

logger = logging.getLogger(__name__)


def get_accessible_folders_map(user):
    """
    Build a map of folder names to IDs that the provided user can access.
    Used by the data wizard import flow to validate targets.
    """
    (viewable_folders_ids, _, _) = RoleAssignment.get_accessible_object_ids(
        Folder.get_root_folder(), user, Folder
    )
    folders_map = {
        f.name.lower(): f.id for f in Folder.objects.filter(id__in=viewable_folders_ids)
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
            # Special handling for TPRM multi-sheet import
            if model_type == "TPRM":
                folders_map = get_accessible_folders_map(request.user)
                res = self._process_tprm_file(
                    request, excel_data, folders_map, folder_id
                )
            # Special handling for EBIOS RM Study ARM format (multi-sheet)
            elif model_type == "EbiosRMStudyARM":
                res = self._process_ebios_rm_study_arm(
                    request, excel_data, folder_id, matrix_id
                )
            else:
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
            {"message": "File loaded successfully", "results": res},
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
        folders_map = get_accessible_folders_map(request.user)

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
        elif model_type == "ReferenceControl":
            return self._process_reference_controls(
                request, records, folders_map, folder_id
            )
        elif model_type == "Threat":
            return self._process_threats(request, records, folders_map, folder_id)
        elif model_type == "TPRM":
            return self._process_tprm(request, records, folders_map, folder_id)
        elif model_type == "Processing":
            return self._process_processings(request, records, folders_map, folder_id)
        elif model_type == "Folder":
            return self._process_folders(request, records)
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
                domain = folders_map.get(str(record.get("domain")).lower(), folder_id)
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
                domain = folders_map.get(str(record.get("domain")).lower(), folder_id)

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
                domain = folders_map.get(str(record.get("domain")).lower(), folder_id)
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
                domain = folders_map.get(str(record.get("domain")).lower(), folder_id)

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

    def _process_reference_controls(self, request, records, folders_map, folder_id):
        """Process reference controls import from Excel"""
        results = {"successful": 0, "failed": 0, "errors": []}

        # Define category mapping
        CATEGORY_MAP = {
            # English
            "policy": "policy",
            "process": "process",
            "technical": "technical",
            "physical": "physical",
            "procedure": "procedure",
        }

        # Define CSF function mapping
        FUNCTION_MAP = {
            # English
            "govern": "govern",
            "identify": "identify",
            "protect": "protect",
            "detect": "detect",
            "respond": "respond",
            "recover": "recover",
            # Variations
            "governance": "govern",
        }

        for record in records:
            # Get domain from record or use fallback
            domain = folder_id
            if record.get("domain") != "":
                domain = folders_map.get(str(record.get("domain")).lower(), folder_id)

            # Check if name is provided as it's mandatory
            if not record.get("name"):
                results["failed"] += 1
                results["errors"].append(
                    {"record": record, "error": "Name field is mandatory"}
                )
                continue

            # Map category
            category = None
            if record.get("category", ""):
                category_value = str(record.get("category")).strip().lower()
                category = CATEGORY_MAP.get(category_value)

            # Map function (csf_function)
            csf_function = None
            if record.get("function", ""):
                function_value = str(record.get("function")).strip().lower()
                csf_function = FUNCTION_MAP.get(function_value)

            # Prepare data for serializer
            reference_control_data = {
                "ref_id": record.get("ref_id", ""),
                "name": record.get("name"),  # Name is mandatory
                "description": record.get("description", ""),
                "folder": domain,
            }

            # Add optional fields if valid
            if category:
                reference_control_data["category"] = category
            if csf_function:
                reference_control_data["csf_function"] = csf_function

            # Use the serializer for validation and saving
            serializer = ReferenceControlWriteSerializer(
                data=reference_control_data, context={"request": request}
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
                    f"Error creating reference control {record.get('name')}: {str(e)}"
                )
                results["failed"] += 1
                results["errors"].append({"record": record, "error": str(e)})

        logger.info(
            f"Reference Control import complete. Success: {results['successful']}, Failed: {results['failed']}"
        )
        return results

    def _process_processings(self, request, records, folders_map, folder_id):
        results = {"successful": 0, "failed": 0, "errors": []}

        # Create reverse mapping: display value -> database value
        status_mapping = {v: k for k, v in Processing.STATUS_CHOICES}

        for record in records:
            domain_id = folder_id

            if record.get("domain") != "":
                domain_id = folders_map.get(
                    str(record.get("domain")).lower(), folder_id
                )

            if not record.get("name"):
                results["failed"] += 1
                results["errors"].append(
                    {"record": record, "error": "Name field is mandatory"}
                )
                continue

            status_value = record.get("status", "privacy_draft")
            if status_value in status_mapping:
                status_value = status_mapping[status_value]

            processing_data = {
                "ref_id": record.get("ref_id", ""),
                "name": record.get("name"),
                "folder": domain_id,
                "description": record.get("description", ""),
                "status": status_value,
                "dpia_required": record.get("dpia_required", False),
                "dpia_reference": record.get("dpia_reference", ""),
            }

            serializer = ProcessingWriteSerializer(
                data=processing_data, context={"request": request}
            )
            try:
                if serializer.is_valid(raise_exception=True):
                    processing_instance = serializer.save()

                    if record.get("processing_nature"):
                        nature_names = [
                            n.strip()
                            for n in str(record.get("processing_nature")).split(",")
                            if n.strip()
                        ]
                        nature_objects = ProcessingNature.objects.filter(
                            name__in=nature_names
                        )
                        processing_instance.nature.set(nature_objects)

                    if record.get("assigned_to"):
                        user_emails = [
                            e.strip()
                            for e in str(record.get("assigned_to")).split(",")
                            if e.strip()
                        ]
                        user_objects = User.objects.filter(email__in=user_emails)
                        processing_instance.assigned_to.set(user_objects)

                    if record.get("labels"):
                        label_names = [
                            label.strip()
                            for label in str(record.get("labels")).split(",")
                            if label.strip()
                        ]
                        label_objects = FilteringLabel.objects.filter(
                            label__in=label_names
                        )
                        processing_instance.filtering_labels.set(label_objects)

                    results["successful"] += 1
                else:
                    results["failed"] += 1
                    results["errors"].append(
                        {"record": record, "errors": serializer.errors}
                    )
            except Exception as e:
                logger.warning(
                    f"Error creating processing {record.get('name')}: {str(e)}"
                )
                results["failed"] += 1
                results["errors"].append({"record": record, "error": str(e)})
        logger.info(
            f"Processing import complete. Success: {results['successful']}, Failed: {results['failed']}"
        )
        return results

    def _process_threats(self, request, records, folders_map, folder_id):
        """Process threats import from Excel"""
        results = {"successful": 0, "failed": 0, "errors": []}

        for record in records:
            # Get domain from record or use fallback
            domain = folder_id
            if record.get("domain") != "":
                domain = folders_map.get(str(record.get("domain")).lower(), folder_id)

            # Check if name is provided as it's mandatory
            if not record.get("name"):
                results["failed"] += 1
                results["errors"].append(
                    {"record": record, "error": "Name field is mandatory"}
                )
                continue

            # Prepare data for serializer
            threat_data = {
                "ref_id": record.get("ref_id", ""),
                "name": record.get("name"),  # Name is mandatory
                "description": record.get("description", ""),
                "folder": domain,
            }

            # Use the serializer for validation and saving
            serializer = ThreatWriteSerializer(
                data=threat_data, context={"request": request}
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
                logger.warning(f"Error creating threat {record.get('name')}: {str(e)}")
                results["failed"] += 1
                results["errors"].append({"record": record, "error": str(e)})

        logger.info(
            f"Threat import complete. Success: {results['successful']}, Failed: {results['failed']}"
        )
        return results

    def _process_folders(self, request, records):
        """Process folders (domains) import from Excel"""
        results = {"successful": 0, "failed": 0, "errors": []}

        # Get the global (root) folder as the default parent
        global_folder = Folder.get_root_folder()

        for record in records:
            # Check if name is provided as it's mandatory
            if not record.get("name"):
                results["failed"] += 1
                results["errors"].append(
                    {"record": record, "error": "Name field is mandatory"}
                )
                continue

            # Handle parent folder lookup
            parent_folder_id = global_folder.id  # Default to global folder
            parent_folder_name = record.get("domain", "").strip()

            if parent_folder_name:
                # Try to find the parent folder by name
                try:
                    parent_folder = Folder.objects.get(name__iexact=parent_folder_name)
                    parent_folder_id = parent_folder.id
                except Folder.DoesNotExist:
                    results["failed"] += 1
                    results["errors"].append(
                        {
                            "record": record,
                            "error": f"Parent folder '{parent_folder_name}' not found",
                        }
                    )
                    continue
                except Folder.MultipleObjectsReturned:
                    results["failed"] += 1
                    results["errors"].append(
                        {
                            "record": record,
                            "error": f"Multiple folders found with name '{parent_folder_name}'",
                        }
                    )
                    continue

            # Prepare data for serializer
            folder_data = {
                "name": record.get("name"),  # Name is mandatory
                "description": record.get("description", ""),
                "parent_folder": parent_folder_id,
            }

            # Use the serializer for validation and saving
            serializer = FolderWriteSerializer(
                data=folder_data, context={"request": request}
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
                logger.warning(f"Error creating folder {record.get('name')}: {str(e)}")
                results["failed"] += 1
                results["errors"].append({"record": record, "error": str(e)})

        logger.info(
            f"Folder import complete. Success: {results['successful']}, Failed: {results['failed']}"
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
                            if (
                                record.get("implementation_score") != ""
                                and record.get("documentation_score") != ""
                            ):
                                if not compliance_assessment.show_documentation_score:
                                    compliance_assessment.show_documentation_score = (
                                        True
                                    )
                                    compliance_assessment.save(
                                        update_fields=["show_documentation_score"]
                                    )
                                requirement_data.update(
                                    {
                                        "score": record.get("implementation_score"),
                                        "documentation_score": record.get(
                                            "documentation_score"
                                        ),
                                        "is_scored": True,
                                    }
                                )
                            elif (
                                record.get("score") != ""
                                and record.get("score") is not None
                            ):
                                requirement_data.update(
                                    {"score": record.get("score"), "is_scored": True}
                                )
                            else:
                                requirement_data.update({"is_scored": False})
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

    def _process_tprm_file(self, request, excel_data, folders_map, folder_id):
        """
        Process TPRM multi-sheet Excel file with Entities, Solutions, and Contracts
        """
        try:
            # Read all sheets from Excel file
            excel_file = pd.ExcelFile(excel_data)

            # Track overall results
            overall_results = {
                "entities": {"successful": 0, "failed": 0, "errors": []},
                "solutions": {"successful": 0, "failed": 0, "errors": []},
                "contracts": {"successful": 0, "failed": 0, "errors": []},
            }

            # Track ref_id to actual ID mappings
            entity_ref_map = {}  # ref_id -> actual UUID
            solution_ref_map = {}  # ref_id -> actual UUID

            # Process Entities sheet first
            if "Entities" in excel_file.sheet_names:
                logger.info("Processing Entities sheet")
                entities_df = pd.read_excel(excel_data, sheet_name="Entities").fillna(
                    ""
                )
                entities_records = entities_df.to_dict(orient="records")
                entities_result, entity_ref_map = self._process_entities(
                    request, entities_records, folders_map, folder_id
                )
                overall_results["entities"] = entities_result
            else:
                logger.warning("No 'Entities' sheet found in Excel file")

            # Process Solutions sheet second (requires entities to exist)
            if "Solutions" in excel_file.sheet_names:
                logger.info("Processing Solutions sheet")
                solutions_df = pd.read_excel(excel_data, sheet_name="Solutions").fillna(
                    ""
                )
                solutions_records = solutions_df.to_dict(orient="records")
                solutions_result, solution_ref_map = self._process_solutions(
                    request, solutions_records, folders_map, folder_id, entity_ref_map
                )
                overall_results["solutions"] = solutions_result
            else:
                logger.warning("No 'Solutions' sheet found in Excel file")

            # Process Contracts sheet last (requires entities and solutions)
            if "Contracts" in excel_file.sheet_names:
                logger.info("Processing Contracts sheet")
                contracts_df = pd.read_excel(excel_data, sheet_name="Contracts").fillna(
                    ""
                )
                contracts_records = contracts_df.to_dict(orient="records")
                contracts_result = self._process_contracts(
                    request,
                    contracts_records,
                    folders_map,
                    folder_id,
                    entity_ref_map,
                    solution_ref_map,
                )
                overall_results["contracts"] = contracts_result
            else:
                logger.warning("No 'Contracts' sheet found in Excel file")

            # Calculate totals
            total_successful = (
                overall_results["entities"]["successful"]
                + overall_results["solutions"]["successful"]
                + overall_results["contracts"]["successful"]
            )
            total_failed = (
                overall_results["entities"]["failed"]
                + overall_results["solutions"]["failed"]
                + overall_results["contracts"]["failed"]
            )

            logger.info(
                f"TPRM import complete. Total success: {total_successful}, Total failed: {total_failed}"
            )

            return overall_results

        except Exception as e:
            logger.error(f"Error processing TPRM file: {str(e)}")
            return {
                "entities": {
                    "successful": 0,
                    "failed": 0,
                    "errors": [{"error": str(e)}],
                },
                "solutions": {"successful": 0, "failed": 0, "errors": []},
                "contracts": {"successful": 0, "failed": 0, "errors": []},
            }

    def _process_entities(self, request, records, folders_map, folder_id):
        """Process entities from TPRM import"""
        results = {"successful": 0, "failed": 0, "errors": []}
        ref_id_map = {}  # Map ref_id to actual UUID

        for record in records:
            try:
                ref_id = record.get("ref_id", "").strip()
                if not ref_id:
                    results["failed"] += 1
                    results["errors"].append(
                        {"record": record, "error": "ref_id field is mandatory"}
                    )
                    continue

                # Check if name is provided
                if not record.get("name"):
                    results["failed"] += 1
                    results["errors"].append(
                        {"record": record, "error": "name field is mandatory"}
                    )
                    continue

                # Get domain from record or use fallback
                domain = folder_id
                if record.get("domain") != "":
                    domain = folders_map.get(
                        str(record.get("domain")).lower(), folder_id
                    )

                # Prepare entity data
                entity_data = {
                    "ref_id": ref_id,
                    "name": record.get("name"),
                    "description": record.get("description", ""),
                    "mission": record.get("mission", ""),
                    "folder": domain,
                }

                # Add optional fields
                if record.get("country"):
                    entity_data["country"] = record.get("country")
                if record.get("currency"):
                    entity_data["currency"] = record.get("currency")

                # Add EBIOS RM fields with type conversion
                for field in ["dependency", "penetration", "maturity", "trust"]:
                    value = record.get(field)
                    if value != "" and value is not None:
                        try:
                            entity_data[f"default_{field}"] = int(value)
                        except (ValueError, TypeError):
                            pass

                # Handle legal identifiers (LEI, EUID, DUNS, VAT, etc.)
                legal_identifiers = {}
                for identifier_type in ["lei", "euid", "duns", "vat"]:
                    value = record.get(identifier_type, "")
                    if value and str(value).strip():
                        legal_identifiers[identifier_type.upper()] = str(value).strip()

                if legal_identifiers:
                    entity_data["legal_identifiers"] = legal_identifiers

                # Create the entity first, then handle parent relationship
                serializer = EntityWriteSerializer(
                    data=entity_data, context={"request": request}
                )

                if serializer.is_valid(raise_exception=True):
                    entity = serializer.save()
                    ref_id_map[ref_id] = str(entity.id)
                    results["successful"] += 1
                    logger.debug(f"Created entity: {entity.name} with ref_id: {ref_id}")
                else:
                    results["failed"] += 1
                    results["errors"].append(
                        {"record": record, "errors": serializer.errors}
                    )

            except Exception as e:
                logger.warning(f"Error creating entity: {str(e)}")
                results["failed"] += 1
                results["errors"].append({"record": record, "error": str(e)})

        # Second pass: handle parent_entity relationships
        for record in records:
            try:
                ref_id = record.get("ref_id", "").strip()
                parent_ref_id = record.get("parent_entity_ref_id", "").strip()

                if ref_id and parent_ref_id and ref_id in ref_id_map:
                    if parent_ref_id in ref_id_map:
                        entity = Entity.objects.get(id=ref_id_map[ref_id])
                        entity.parent_entity_id = ref_id_map[parent_ref_id]
                        entity.save()
                        logger.debug(
                            f"Linked entity {ref_id} to parent {parent_ref_id}"
                        )
                    else:
                        logger.warning(
                            f"Parent entity ref_id '{parent_ref_id}' not found for entity '{ref_id}'"
                        )
            except Exception as e:
                logger.warning(f"Error linking parent entity: {str(e)}")

        logger.info(
            f"Entity import complete. Success: {results['successful']}, Failed: {results['failed']}"
        )
        return results, ref_id_map

    def _process_solutions(
        self, request, records, folders_map, folder_id, entity_ref_map
    ):
        """Process solutions from TPRM import"""
        results = {"successful": 0, "failed": 0, "errors": []}
        ref_id_map = {}  # Map ref_id to actual UUID

        for record in records:
            try:
                ref_id = record.get("ref_id", "").strip()
                if not ref_id:
                    results["failed"] += 1
                    results["errors"].append(
                        {"record": record, "error": "ref_id field is mandatory"}
                    )
                    continue

                # Check if name is provided
                if not record.get("name"):
                    results["failed"] += 1
                    results["errors"].append(
                        {"record": record, "error": "name field is mandatory"}
                    )
                    continue

                # Check provider_entity_ref_id
                provider_ref_id = record.get("provider_entity_ref_id", "").strip()
                if not provider_ref_id:
                    results["failed"] += 1
                    results["errors"].append(
                        {
                            "record": record,
                            "error": "provider_entity_ref_id field is mandatory",
                        }
                    )
                    continue

                # Lookup provider entity UUID
                if provider_ref_id not in entity_ref_map:
                    results["failed"] += 1
                    results["errors"].append(
                        {
                            "record": record,
                            "error": f"Provider entity with ref_id '{provider_ref_id}' not found",
                        }
                    )
                    continue

                provider_entity_id = entity_ref_map[provider_ref_id]

                # Prepare solution data
                solution_data = {
                    "ref_id": ref_id,
                    "name": record.get("name"),
                    "description": record.get("description", ""),
                    "provider_entity": provider_entity_id,
                }

                # Add criticality if provided
                if (
                    record.get("criticality") != ""
                    and record.get("criticality") is not None
                ):
                    try:
                        solution_data["criticality"] = int(record.get("criticality"))
                    except (ValueError, TypeError):
                        pass

                # Create the solution
                serializer = SolutionWriteSerializer(
                    data=solution_data, context={"request": request}
                )

                if serializer.is_valid(raise_exception=True):
                    solution = serializer.save()
                    ref_id_map[ref_id] = str(solution.id)
                    results["successful"] += 1
                    logger.debug(
                        f"Created solution: {solution.name} with ref_id: {ref_id}"
                    )
                else:
                    results["failed"] += 1
                    results["errors"].append(
                        {"record": record, "errors": serializer.errors}
                    )

            except Exception as e:
                logger.warning(f"Error creating solution: {str(e)}")
                results["failed"] += 1
                results["errors"].append({"record": record, "error": str(e)})

        logger.info(
            f"Solution import complete. Success: {results['successful']}, Failed: {results['failed']}"
        )
        return results, ref_id_map

    def _process_contracts(
        self, request, records, folders_map, folder_id, entity_ref_map, solution_ref_map
    ):
        """Process contracts from TPRM import"""
        results = {"successful": 0, "failed": 0, "errors": []}

        for record in records:
            try:
                ref_id = record.get("ref_id", "").strip()
                if not ref_id:
                    results["failed"] += 1
                    results["errors"].append(
                        {"record": record, "error": "ref_id field is mandatory"}
                    )
                    continue

                # Check if name is provided
                if not record.get("name"):
                    results["failed"] += 1
                    results["errors"].append(
                        {"record": record, "error": "name field is mandatory"}
                    )
                    continue

                # Check provider_entity_ref_id
                provider_ref_id = record.get("provider_entity_ref_id", "").strip()
                if not provider_ref_id:
                    results["failed"] += 1
                    results["errors"].append(
                        {
                            "record": record,
                            "error": "provider_entity_ref_id field is mandatory",
                        }
                    )
                    continue

                # Lookup provider entity UUID
                if provider_ref_id not in entity_ref_map:
                    results["failed"] += 1
                    results["errors"].append(
                        {
                            "record": record,
                            "error": f"Provider entity with ref_id '{provider_ref_id}' not found",
                        }
                    )
                    continue

                provider_entity_id = entity_ref_map[provider_ref_id]

                # Get domain from record or use fallback
                domain = folder_id
                if record.get("domain") != "":
                    domain = folders_map.get(
                        str(record.get("domain")).lower(), folder_id
                    )

                # Prepare contract data
                contract_data = {
                    "ref_id": ref_id,
                    "name": record.get("name"),
                    "description": record.get("description", ""),
                    "provider_entity": provider_entity_id,
                    "folder": domain,
                }

                # Add optional solution reference
                solution_ref_id = str(record.get("solution_ref_id", "")).strip()
                if solution_ref_id:
                    if solution_ref_id in solution_ref_map:
                        contract_data["solution"] = solution_ref_map[solution_ref_id]
                    else:
                        logger.warning(
                            f"Solution with ref_id '{solution_ref_id}' not found for contract '{ref_id}'"
                        )

                # Add optional fields
                if record.get("status"):
                    contract_data["status"] = record.get("status")
                if record.get("start_date"):
                    contract_data["start_date"] = record.get("start_date")
                if record.get("end_date"):
                    contract_data["end_date"] = record.get("end_date")
                if (
                    record.get("annual_expense") != ""
                    and record.get("annual_expense") is not None
                ):
                    try:
                        contract_data["annual_expense"] = float(
                            record.get("annual_expense")
                        )
                    except (ValueError, TypeError):
                        pass
                if record.get("currency"):
                    contract_data["currency"] = record.get("currency")

                # Create the contract
                serializer = ContractWriteSerializer(
                    data=contract_data, context={"request": request}
                )

                if serializer.is_valid(raise_exception=True):
                    contract = serializer.save()
                    results["successful"] += 1
                    logger.debug(
                        f"Created contract: {contract.name} with ref_id: {ref_id}"
                    )
                else:
                    results["failed"] += 1
                    results["errors"].append(
                        {"record": record, "errors": serializer.errors}
                    )

            except Exception as e:
                logger.warning(f"Error creating contract: {str(e)}")
                results["failed"] += 1
                results["errors"].append({"record": record, "error": str(e)})

        logger.info(
            f"Contract import complete. Success: {results['successful']}, Failed: {results['failed']}"
        )
        return results

    def _process_tprm(self, request, records, folders_map, folder_id):
        """Legacy handler - TPRM should use _process_tprm_file for multi-sheet support"""
        return {
            "successful": 0,
            "failed": 0,
            "errors": [
                {
                    "error": "TPRM import requires multi-sheet Excel file. Please use the proper TPRM template."
                }
            ],
        }

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
                existing_controls = record.get("existing_applied_controls", "").strip()
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

            logger.debug(
                f"Risk scenario '{name}': current_proba={current_proba}, current_impact={current_impact}, "
                f"residual_proba={residual_proba}, residual_impact={residual_impact}"
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
                record.get("existing_applied_controls", ""),
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
        if not value:
            return -1

        # Convert to string if needed (pandas may read Excel cells as numbers, etc.)
        original_value = value
        if not isinstance(value, str):
            value = str(value)

        # Try exact match first
        clean_value = value.strip().lower()
        if clean_value in mapping_dict:
            mapped_value = mapping_dict[clean_value]
            logger.debug(f"Mapped risk value '{original_value}' -> {mapped_value}")
            return mapped_value

        # If no match found, return -1 (undefined)
        logger.warning(
            f"Failed to map risk value '{original_value}' (type: {type(original_value).__name__}). "
            f"Available values: {list(mapping_dict.keys())}"
        )
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

    def _process_ebios_rm_study_arm(self, request, excel_data, folder_id, matrix_id):
        """
        Process EBIOS RM Study import from ARM Excel format.
        This creates an EbiosRMStudy with Workshop 1, 2, and 3 objects:
        - Workshop 1: Assets, Feared Events, Applied Controls
        - Workshop 2: RoTo Couples
        - Workshop 3: Stakeholders, Strategic Scenarios, Attack Paths
        """
        from datetime import datetime

        results = {
            "successful": 0,
            "failed": 0,
            "errors": [],
            "details": {
                "study": None,
                "assets_created": 0,
                "feared_events_created": 0,
                "applied_controls_created": 0,
            },
        }

        try:
            # Validate folder exists
            folder = Folder.objects.get(id=folder_id)

            # Validate matrix exists
            risk_matrix = None
            if matrix_id:
                risk_matrix = RiskMatrix.objects.get(id=matrix_id)

            # Parse ARM Excel file
            excel_data.seek(0)
            arm_data = process_arm_file(excel_data.read())

            # Generate study name
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            study_name = f"EBIOS_RM_Study_{timestamp}"

            # Use missions as description
            study_description = arm_data.get("study_description", "")

            # =========================================================
            # Step 1: Create Assets (primary and supporting)
            # =========================================================
            asset_name_to_id = {}
            # Track parent relationships to set up after all assets are created
            # Format: {child_name_lower: parent_name}
            supporting_asset_parents = {}
            # Track primary -> supporting relationships from Base de valeurs métier
            # Format: {primary_name_lower: [supporting_name1, supporting_name2, ...]}
            primary_to_supporting = {}

            # Create supporting assets first (from dedicated sheet)
            for asset_data in arm_data.get("supporting_assets", []):
                try:
                    serializer = AssetWriteSerializer(
                        data={
                            "name": asset_data["name"],
                            "description": asset_data["description"],
                            "type": "SP",
                            "folder": folder_id,
                        },
                        context={"request": request},
                    )
                    if serializer.is_valid():
                        asset = serializer.save()
                        asset_name_to_id[asset_data["name"].lower()] = asset.id
                        results["details"]["assets_created"] += 1

                        # Track parent relationship if specified
                        if asset_data.get("parent_name"):
                            supporting_asset_parents[asset_data["name"].lower()] = (
                                asset_data["parent_name"]
                            )
                    else:
                        results["errors"].append(
                            {"asset": asset_data["name"], "error": serializer.errors}
                        )
                except Exception as e:
                    results["errors"].append(
                        {"asset": asset_data["name"], "error": str(e)}
                    )

            # Create primary assets and their linked supporting assets
            for asset_data in arm_data.get("primary_assets", []):
                try:
                    # Track supporting assets for this primary asset
                    supporting_names = asset_data.get("supporting_asset_names", [])
                    if supporting_names:
                        primary_to_supporting[asset_data["name"].lower()] = (
                            supporting_names
                        )

                    # Create any supporting assets mentioned in this primary asset
                    for supporting_name in supporting_names:
                        if supporting_name.lower() not in asset_name_to_id:
                            serializer = AssetWriteSerializer(
                                data={
                                    "name": supporting_name,
                                    "type": "SP",
                                    "folder": folder_id,
                                },
                                context={"request": request},
                            )
                            if serializer.is_valid():
                                asset = serializer.save()
                                asset_name_to_id[supporting_name.lower()] = asset.id
                                results["details"]["assets_created"] += 1

                    # Create the primary asset
                    serializer = AssetWriteSerializer(
                        data={
                            "name": asset_data["name"],
                            "description": asset_data["description"],
                            "type": "PR",
                            "folder": folder_id,
                        },
                        context={"request": request},
                    )
                    if serializer.is_valid():
                        asset = serializer.save()
                        asset_name_to_id[asset_data["name"].lower()] = asset.id
                        results["details"]["assets_created"] += 1
                    else:
                        results["errors"].append(
                            {"asset": asset_data["name"], "error": serializer.errors}
                        )
                except Exception as e:
                    results["errors"].append(
                        {"asset": asset_data["name"], "error": str(e)}
                    )

            # =========================================================
            # Step 1b: Set up asset parent relationships
            # =========================================================
            logger.info(
                f"Setting up asset hierarchy: "
                f"{len(supporting_asset_parents)} explicit parents, "
                f"{len(primary_to_supporting)} primary->supporting mappings"
            )

            # First, apply explicit parent relationships from "Bien support parent"
            for child_name_lower, parent_name in supporting_asset_parents.items():
                child_id = asset_name_to_id.get(child_name_lower)
                parent_id = asset_name_to_id.get(parent_name.lower())
                if child_id and parent_id:
                    try:
                        child_asset = Asset.objects.get(id=child_id)
                        child_asset.parent_assets.add(parent_id)
                        logger.info(
                            f"Set explicit parent '{parent_name}' for asset '{child_name_lower}'"
                        )
                    except Exception as e:
                        logger.warning(f"Failed to set parent for asset: {e}")

            # Then, for supporting assets, use primary asset from "Base de valeurs métier" as parent
            for primary_name_lower, supporting_names in primary_to_supporting.items():
                primary_id = asset_name_to_id.get(primary_name_lower)
                if not primary_id:
                    logger.warning(
                        f"Primary asset '{primary_name_lower}' not found in asset_name_to_id"
                    )
                    continue

                primary_asset = Asset.objects.get(id=primary_id)

                for supporting_name in supporting_names:
                    supporting_name_lower = supporting_name.lower()
                    supporting_id = asset_name_to_id.get(supporting_name_lower)

                    if supporting_id:
                        try:
                            supporting_asset = Asset.objects.get(id=supporting_id)
                            # Add primary as parent of supporting (supporting.parent_assets contains primary)
                            supporting_asset.parent_assets.add(primary_id)
                            logger.info(
                                f"Linked: '{supporting_name}' -> parent: '{primary_asset.name}'"
                            )
                        except Exception as e:
                            logger.warning(
                                f"Failed to set parent for asset '{supporting_name}': {e}"
                            )
                    else:
                        logger.debug(
                            f"Supporting asset '{supporting_name}' not found in asset_name_to_id"
                        )

            # =========================================================
            # Step 2: Create Applied Controls
            # =========================================================
            for control_data in arm_data.get("applied_controls", []):
                try:
                    serializer = AppliedControlWriteSerializer(
                        data={
                            "name": control_data["name"],
                            "description": control_data["description"],
                            "ref_id": control_data["ref_id"] or None,
                            "folder": folder_id,
                        },
                        context={"request": request},
                    )
                    if serializer.is_valid():
                        serializer.save()
                        results["details"]["applied_controls_created"] += 1
                    else:
                        results["errors"].append(
                            {
                                "control": control_data["name"],
                                "error": serializer.errors,
                            }
                        )
                except Exception as e:
                    results["errors"].append(
                        {"control": control_data["name"], "error": str(e)}
                    )

            # =========================================================
            # Step 3: Create EBIOS RM Study
            # =========================================================
            study_data = {
                "name": study_name,
                "folder": folder_id,
                "description": study_description,
            }

            if risk_matrix:
                study_data["risk_matrix"] = matrix_id

            serializer = EbiosRMStudyWriteSerializer(
                data=study_data, context={"request": request}
            )

            if serializer.is_valid(raise_exception=True):
                study = serializer.save()
                results["details"]["study"] = study.id
                logger.info(f"Created EBIOS RM Study: {study_name} with ID {study.id}")

                # Track workshop progress
                meta_updated = False

                # Mark step 1 (index 0) as done if we have a description
                if study_description:
                    study.meta["workshops"][0]["steps"][0]["status"] = "done"
                    meta_updated = True

                # Link assets to study
                asset_ids = list(asset_name_to_id.values())
                if asset_ids:
                    study.assets.set(asset_ids)
                    # Mark step 2 (index 1) as done if we have assets
                    study.meta["workshops"][0]["steps"][1]["status"] = "done"
                    meta_updated = True

                # =========================================================
                # Step 4: Create Feared Events
                # =========================================================
                for fe_data in arm_data.get("feared_events", []):
                    try:
                        # Find linked assets
                        linked_asset_ids = []
                        for asset_name in fe_data.get("asset_names", []):
                            asset_id = asset_name_to_id.get(asset_name.lower())
                            if asset_id:
                                linked_asset_ids.append(asset_id)

                        # Create feared event
                        feared_event = FearedEvent.objects.create(
                            ebios_rm_study=study,
                            name=fe_data["name"],
                            justification=fe_data.get("justification", ""),
                            gravity=fe_data.get("gravity", -1),
                            is_selected=fe_data.get("is_selected", False),
                        )

                        # Link assets
                        if linked_asset_ids:
                            feared_event.assets.set(linked_asset_ids)

                        results["details"]["feared_events_created"] += 1

                    except Exception as e:
                        results["errors"].append(
                            {"feared_event": fe_data["name"], "error": str(e)}
                        )

                # Mark step 3 (index 2) as done if we created feared events
                if results["details"]["feared_events_created"] > 0:
                    study.meta["workshops"][0]["steps"][2]["status"] = "done"
                    meta_updated = True

                # =========================================================
                # Step 5: Create RoTo Couples (Workshop 2)
                # =========================================================
                results["details"]["roto_couples_created"] = 0

                for roto_data in arm_data.get("roto_couples", []):
                    try:
                        # Find or create the risk origin terminology
                        risk_origin_name = roto_data["risk_origin"]

                        # Try to find existing terminology by name (case-insensitive)
                        risk_origin = Terminology.objects.filter(
                            field_path=Terminology.FieldPath.ROTO_RISK_ORIGIN,
                            name__iexact=risk_origin_name,
                        ).first()

                        if not risk_origin:
                            # Create a new terminology entry for this risk origin
                            risk_origin = Terminology.objects.create(
                                field_path=Terminology.FieldPath.ROTO_RISK_ORIGIN,
                                name=risk_origin_name.lower().replace(" ", "_"),
                                is_visible=True,
                                builtin=False,
                            )
                            logger.info(
                                f"Created new risk origin terminology: {risk_origin_name}"
                            )

                        # Create the RoTo couple
                        roto = RoTo.objects.create(
                            ebios_rm_study=study,
                            risk_origin=risk_origin,
                            target_objective=roto_data["target_objective"],
                            motivation=roto_data.get("motivation", 0),
                            resources=roto_data.get("resources", 0),
                            activity=roto_data.get("activity", 0),
                            is_selected=roto_data.get("is_selected", False),
                            justification=roto_data.get("justification", ""),
                        )

                        results["details"]["roto_couples_created"] += 1
                        logger.debug(
                            f"Created RoTo couple: {risk_origin_name} - {roto_data['target_objective']}"
                        )

                    except Exception as e:
                        results["errors"].append(
                            {
                                "roto_couple": f"{roto_data.get('risk_origin', 'unknown')} - {roto_data.get('target_objective', 'unknown')}",
                                "error": str(e),
                            }
                        )

                # Mark workshop 2 step 1 (index 0) as done if we created RoTo couples
                if results["details"]["roto_couples_created"] > 0:
                    study.meta["workshops"][1]["steps"][0]["status"] = "done"
                    meta_updated = True
                    logger.info(
                        f"Created {results['details']['roto_couples_created']} RoTo couples"
                    )

                    # Check if any RoTo couple has motivation or resources data
                    # If so, mark workshop 2 step 2 (index 1) as done
                    has_quotation_data = any(
                        roto.get("motivation", 0) > 0 or roto.get("resources", 0) > 0
                        for roto in arm_data.get("roto_couples", [])
                    )
                    if has_quotation_data:
                        study.meta["workshops"][1]["steps"][1]["status"] = "done"
                        logger.info(
                            "Marked workshop 2 step 2 as done (motivation/resources data captured)"
                        )

                # =========================================================
                # Step 6: Create Stakeholders (Workshop 3)
                # =========================================================
                results["details"]["entities_created"] = 0
                results["details"]["stakeholders_created"] = 0

                # First, create or find category terminologies
                category_name_to_terminology = {}
                for cat_data in arm_data.get("stakeholder_categories", []):
                    normalized_name = cat_data["normalized_name"]
                    if not normalized_name:
                        continue

                    # Try to find existing terminology
                    terminology = Terminology.objects.filter(
                        field_path=Terminology.FieldPath.ENTITY_RELATIONSHIP,
                        name__iexact=normalized_name,
                    ).first()

                    if not terminology:
                        # Also try without the trailing 's' stripped
                        terminology = Terminology.objects.filter(
                            field_path=Terminology.FieldPath.ENTITY_RELATIONSHIP,
                            name__iexact=cat_data["name"].lower(),
                        ).first()

                    if not terminology:
                        # Create a new terminology entry
                        terminology = Terminology.objects.create(
                            field_path=Terminology.FieldPath.ENTITY_RELATIONSHIP,
                            name=normalized_name,
                            is_visible=True,
                            builtin=False,
                        )
                        logger.info(
                            f"Created new stakeholder category: {normalized_name}"
                        )

                    category_name_to_terminology[normalized_name] = terminology
                    # Also map the raw name for direct lookups
                    category_name_to_terminology[cat_data["name"].lower()] = terminology

                # Now create entities and stakeholders
                for stakeholder_data in arm_data.get("stakeholders", []):
                    try:
                        entity_name = stakeholder_data["name"]

                        # Create or get the entity
                        entity, created = Entity.objects.get_or_create(
                            name=entity_name,
                            defaults={
                                "folder": folder,
                                "description": stakeholder_data.get("description", ""),
                            },
                        )
                        if created:
                            results["details"]["entities_created"] += 1
                            logger.debug(f"Created entity: {entity_name}")

                        # Find the category terminology
                        category_normalized = stakeholder_data.get("category", "")
                        category = category_name_to_terminology.get(category_normalized)

                        if not category:
                            # Try to find by normalized name directly
                            category = Terminology.objects.filter(
                                field_path=Terminology.FieldPath.ENTITY_RELATIONSHIP,
                                name__iexact=category_normalized,
                            ).first()

                        if not category:
                            # Use 'other' as fallback
                            category = Terminology.objects.filter(
                                field_path=Terminology.FieldPath.ENTITY_RELATIONSHIP,
                                name="other",
                            ).first()

                        if category:
                            # Create the stakeholder
                            stakeholder = Stakeholder.objects.create(
                                ebios_rm_study=study,
                                entity=entity,
                                category=category,
                                is_selected=stakeholder_data.get("is_selected", False),
                                current_dependency=stakeholder_data.get(
                                    "current_dependency", 0
                                ),
                                current_penetration=stakeholder_data.get(
                                    "current_penetration", 0
                                ),
                                current_maturity=stakeholder_data.get(
                                    "current_maturity", 1
                                ),
                                current_trust=stakeholder_data.get("current_trust", 1),
                                # Set residual to same as current initially
                                residual_dependency=stakeholder_data.get(
                                    "current_dependency", 0
                                ),
                                residual_penetration=stakeholder_data.get(
                                    "current_penetration", 0
                                ),
                                residual_maturity=stakeholder_data.get(
                                    "current_maturity", 1
                                ),
                                residual_trust=stakeholder_data.get("current_trust", 1),
                            )

                            results["details"]["stakeholders_created"] += 1
                            logger.debug(
                                f"Created stakeholder: {entity_name} ({category.name})"
                            )
                        else:
                            results["errors"].append(
                                {
                                    "stakeholder": entity_name,
                                    "error": "Could not find or create category terminology",
                                }
                            )

                    except Exception as e:
                        results["errors"].append(
                            {
                                "stakeholder": stakeholder_data.get("name", "unknown"),
                                "error": str(e),
                            }
                        )

                # Mark workshop 3 step 1 (index 0) as done if we created stakeholders
                if results["details"]["stakeholders_created"] > 0:
                    study.meta["workshops"][2]["steps"][0]["status"] = "done"
                    meta_updated = True
                    logger.info(
                        f"Created {results['details']['stakeholders_created']} stakeholders "
                        f"({results['details']['entities_created']} new entities)"
                    )

                    # Check if any stakeholder has assessment data (dependency or penetration > 0)
                    has_assessment_data = any(
                        s.get("current_dependency", 0) > 0
                        or s.get("current_penetration", 0) > 0
                        for s in arm_data.get("stakeholders", [])
                    )
                    if has_assessment_data:
                        study.meta["workshops"][2]["steps"][1]["status"] = "done"
                        logger.info(
                            "Marked workshop 3 step 2 as done (assessment data captured)"
                        )

                # =========================================================
                # Step 7: Create Strategic Scenarios and Attack Paths (Workshop 3)
                # =========================================================
                results["details"]["strategic_scenarios_created"] = 0
                results["details"]["attack_paths_created"] = 0

                # Build a lookup for RoTo couples by risk_origin + target_objective
                roto_lookup = {}
                for roto in study.roto_set.all():
                    # Store both the normalized name and the original for flexible matching
                    key = (
                        roto.risk_origin.name.lower(),
                        roto.target_objective.lower(),
                    )
                    roto_lookup[key] = roto

                for scenario_data in arm_data.get("strategic_scenarios", []):
                    try:
                        scenario_name = scenario_data["name"]
                        if not scenario_name:
                            continue

                        # Find the matching RoTo couple
                        # Normalize the risk origin name the same way we do when creating terminologies
                        risk_origin_raw = scenario_data.get("risk_origin", "")
                        risk_origin_name = risk_origin_raw.lower().replace(" ", "_")
                        target_objective = scenario_data.get(
                            "target_objective", ""
                        ).lower()

                        roto = roto_lookup.get((risk_origin_name, target_objective))

                        if not roto:
                            # Try without underscore normalization
                            risk_origin_name_alt = risk_origin_raw.lower()
                            roto = roto_lookup.get(
                                (risk_origin_name_alt, target_objective)
                            )

                        if not roto:
                            # Try partial matching on target objective
                            for key, r in roto_lookup.items():
                                if (
                                    key[0] == risk_origin_name
                                    and target_objective in key[1]
                                ):
                                    roto = r
                                    break

                        if not roto:
                            results["errors"].append(
                                {
                                    "strategic_scenario": scenario_name,
                                    "error": f"Could not find RoTo couple for '{risk_origin_name}' - '{target_objective}'",
                                }
                            )
                            continue

                        # Create the strategic scenario
                        strategic_scenario = StrategicScenario.objects.create(
                            ebios_rm_study=study,
                            ro_to_couple=roto,
                            name=scenario_name,
                            ref_id=scenario_data.get("ref_id", ""),
                        )
                        results["details"]["strategic_scenarios_created"] += 1

                        # Create the attack path if provided
                        attack_path_name = scenario_data.get("attack_path_name", "")
                        if attack_path_name:
                            attack_path = AttackPath.objects.create(
                                ebios_rm_study=study,
                                strategic_scenario=strategic_scenario,
                                name=attack_path_name,
                                ref_id=scenario_data.get("attack_path_ref_id", ""),
                            )
                            results["details"]["attack_paths_created"] += 1

                    except Exception as e:
                        results["errors"].append(
                            {
                                "strategic_scenario": scenario_data.get(
                                    "name", "unknown"
                                ),
                                "error": str(e),
                            }
                        )

                # Mark workshop 3 step 3 (index 2) as done if we created strategic scenarios
                if results["details"]["strategic_scenarios_created"] > 0:
                    study.meta["workshops"][2]["steps"][2]["status"] = "done"
                    meta_updated = True
                    logger.info(
                        f"Created {results['details']['strategic_scenarios_created']} strategic scenarios, "
                        f"{results['details']['attack_paths_created']} attack paths"
                    )

                # =========================================================
                # Step 8: Create Elementary Actions (Workshop 4)
                # =========================================================
                results["details"]["elementary_actions_created"] = 0

                for ea_data in arm_data.get("elementary_actions", []):
                    try:
                        ea_name = ea_data["name"]
                        if not ea_name:
                            continue

                        # Create the elementary action
                        elementary_action = ElementaryAction.objects.create(
                            name=ea_name,
                            description=ea_data.get("description", ""),
                            ref_id=ea_data.get("ref_id", ""),
                            folder=folder,
                        )

                        results["details"]["elementary_actions_created"] += 1
                        logger.debug(f"Created elementary action: {ea_name}")

                    except Exception as e:
                        results["errors"].append(
                            {
                                "elementary_action": ea_data.get("name", "unknown"),
                                "error": str(e),
                            }
                        )

                # Mark workshop 4 step 1 (index 0) as done if we created elementary actions
                if results["details"]["elementary_actions_created"] > 0:
                    study.meta["workshops"][3]["steps"][0]["status"] = "done"
                    meta_updated = True
                    logger.info(
                        f"Created {results['details']['elementary_actions_created']} elementary actions"
                    )

                # Save the study if meta was updated
                if meta_updated:
                    study.save()

                results["successful"] = 1

            else:
                results["failed"] = 1
                results["errors"].append(
                    {"error": "Failed to create study", "details": serializer.errors}
                )

        except Folder.DoesNotExist:
            results["failed"] = 1
            results["errors"].append(
                {"error": f"Folder with ID {folder_id} does not exist"}
            )
        except RiskMatrix.DoesNotExist:
            results["failed"] = 1
            results["errors"].append(
                {"error": f"Risk matrix with ID {matrix_id} does not exist"}
            )
        except Exception as e:
            logger.error(f"Error processing EBIOS RM Study: {str(e)}", exc_info=True)
            results["failed"] = 1
            results["errors"].append({"error": str(e)})

        return results
