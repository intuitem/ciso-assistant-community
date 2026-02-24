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
    RequirementNode,
    RiskMatrix,
    AppliedControl,
    FindingsAssessment,
    RiskScenario,
    Policy,
    SecurityException,
    Incident,
)
from core.serializers import (
    BaseModelSerializer,
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
    EvidenceWriteSerializer,
    FolderWriteSerializer,
    PolicyWriteSerializer,
    SecurityExceptionWriteSerializer,
    IncidentWriteSerializer,
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
from .ebios_rm_excel_helpers import (
    extract_elementary_actions,
    process_excel_file as process_ebios_rm_excel,
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
from uuid import UUID
from django.core.files.uploadedfile import UploadedFile
from django.http import HttpRequest
from datetime import datetime
from typing import Optional, Final, ClassVar
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import enum

logger = logging.getLogger(__name__)


def get_accessible_folders_map(user: User) -> dict[str, UUID]:
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


ZIP_MAGIC_NUMBER: Final[bytes] = bytes([0x50, 0x4B, 0x03, 0x04])


def is_excel_file(file: io.BytesIO) -> bool:
    file_data = file.read(len(ZIP_MAGIC_NUMBER))
    is_excel = file_data == ZIP_MAGIC_NUMBER
    file.seek(0)
    return is_excel


def normalize_datetime_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert datetime columns to ISO format strings.
    Uses date-only format (YYYY-MM-DD) when there is no time component,
    full ISO format otherwise. NaT values become empty strings.
    """
    for col in df.select_dtypes(include=["datetime64", "datetimetz"]).columns:
        df[col] = df[col].apply(
            lambda x: (
                x.strftime("%Y-%m-%d")
                if pd.notna(x) and x == x.normalize()
                else (x.isoformat() if pd.notna(x) else "")
            )
        )
    return df


def _parse_date(value) -> Optional[str]:
    """Normalize a value to a YYYY-MM-DD string for DRF DateField."""
    if not value or value == "":
        return None
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, str) and "T" in value:
        return value.split("T")[0]
    return value


def _parse_datetime(value) -> Optional[str]:
    """Normalize a value to an ISO datetime string for DRF DateTimeField."""
    if not value or value == "":
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _resolve_filtering_labels(value) -> list[UUID]:
    """Parse pipe- or comma-separated label names and return list of FilteringLabel IDs.

    Labels that do not yet exist are created on the fly.
    """
    if not value or not isinstance(value, str):
        return []
    separator = "|" if "|" in value else ","
    label_names = [name.strip() for name in value.split(separator) if name.strip()]
    label_ids: list[UUID] = []
    for label_name in label_names:
        label = FilteringLabel.objects.filter(label=label_name).first()
        if label is None:
            try:
                label = FilteringLabel(label=label_name)
                label.full_clean()
                label.save()
            except Exception:
                continue
        label_ids.append(label.id)
    return label_ids


class RecordFileType(enum.StrEnum):
    XLSX = "Excel"
    CSV = "CSV"

    def get_error(self) -> str:
        match self:
            case RecordFileType.XLSX:
                return "ExcelParsingFailed"
            case RecordFileType.CSV:
                return "CSVParsingFailed"
            case _:
                raise NotImplementedError(
                    f"Unreachable code detected (unknown {type(self).__name__} enum variant)."
                )


class ConflictMode(enum.StrEnum):
    STOP = "stop"
    SKIP = "skip"
    UPDATE = "update"


class ModelType(enum.StrEnum):
    TPRM = "TPRM"
    EBIOS_RM_STUDY_ARM = "EbiosRMStudyARM"
    EBIOS_RM_STUDY_EXCEL = "EbiosRMStudyExcel"
    ASSET = "Asset"
    APPLIED_CONTROL = "AppliedControl"
    PERIMETER = "Perimeter"
    USER = "User"
    COMPLIANCE_ASSESSMENT = "ComplianceAssessment"
    FINDINGS_ASSESSMENT = "FindingsAssessment"
    RISK_ASSESSMENT = "RiskAssessment"
    ELEMENTARY_ACTION = "ElementaryAction"
    REFERENCE_CONTROL = "ReferenceControl"
    THREAT = "Threat"
    PROCESSING = "Processing"
    FOLDER = "Folder"
    EVIDENCE = "Evidence"
    POLICY = "Policy"
    SECURITY_EXCEPTION = "SecurityException"
    INCIDENT = "Incident"

    @staticmethod
    def from_string(model_type: str) -> Optional["ModelType"]:
        """Returns a ModelType on success, otherwise return None."""
        try:
            return ModelType(model_type)
        except ValueError:
            return


@dataclass(frozen=True)
class Error:
    record: dict
    error: str

    def to_dict(self) -> dict:
        return {"record": self.record, "error": self.error}


@dataclass
class Result:
    created: int = 0
    updated: int = 0
    skipped: int = 0
    failed: int = 0
    errors: list[Error] = field(default_factory=list)
    details: dict = field(default_factory=dict)

    @property
    def successful(self) -> int:
        return self.created + self.updated

    def add_created(self):
        self.created += 1

    def add_updated(self):
        self.updated += 1

    def add_skipped(self):
        self.skipped += 1

    def add_error(self, error: Error, fail_count: int = 1):
        self.failed += fail_count
        self.errors.append(error)

    def to_dict(self) -> dict:
        return {
            "successful": self.successful,
            "created": self.created,
            "updated": self.updated,
            "skipped": self.skipped,
            "failed": self.failed,
            "errors": [error.to_dict() for error in self.errors],
            **({"details": self.details} if self.details else {}),
        }


@dataclass(frozen=True)
class BaseContext:
    request: HttpRequest
    folders_map: dict[str, UUID] = field(default_factory=dict)
    folder_id: Optional[str] = None
    perimeter_id: Optional[str] = None
    matrix_id: Optional[str] = None
    framework_id: Optional[str] = None
    on_conflict: ConflictMode = ConflictMode.STOP


class RecordConsumer[Context](ABC):
    SERIALIZER_CLASS: ClassVar[type[BaseModelSerializer]]
    # Maps record_data keys to possible source record keys when they differ.
    # Override in subclasses that use alternative/aliased column names.
    SOURCE_KEY_MAP: ClassVar[dict[str, tuple[str, ...]]] = {}

    def __init__(self, base_context: BaseContext):
        self.request = base_context.request
        self.folders_map = base_context.folders_map
        self.folder_id = base_context.folder_id
        self.perimeter_id = base_context.perimeter_id
        self.matrix_id = base_context.matrix_id
        self.framework_id = base_context.framework_id
        self.on_conflict = base_context.on_conflict

    def __init_subclass__(cls):
        provided_class = getattr(cls, "SERIALIZER_CLASS", None)
        is_defined = provided_class is not None
        is_serializer = is_defined and issubclass(provided_class, BaseModelSerializer)

        assert is_serializer, f"Invalid serializer for class {cls.__name__}"

    @abstractmethod
    def create_context(self) -> tuple[Context, Optional[Error]]:
        pass

    @abstractmethod
    def prepare_create(
        self, record: dict, context: Context
    ) -> tuple[dict, Optional[Error]]:
        pass

    def find_existing(self, record_data: dict):
        """Find an existing record matching this data based on the model's fields_to_check."""
        model_class = self.SERIALIZER_CLASS.Meta.model
        fields_to_check = getattr(model_class, "fields_to_check", [])
        if not fields_to_check:
            return None
        query = {}
        for f in fields_to_check:
            value = record_data.get(f)
            if value is None or value == "":
                continue
            if isinstance(value, str):
                query[f"{f}__iexact"] = value
            else:
                query[f] = value
        if not query:
            return None
        folder = record_data.get("folder")
        if folder and hasattr(model_class, "folder"):
            query["folder"] = folder
        return model_class.objects.filter(**query).first()

    def _build_update_data(self, record: dict, record_data: dict) -> dict:
        """
        Filter record_data to only include fields that the user actually
        provided with non-empty values in the source record.
        Identity fields (used for matching) are always preserved.
        """
        model_class = self.SERIALIZER_CLASS.Meta.model
        identity_fields = set(getattr(model_class, "fields_to_check", []))
        if hasattr(model_class, "folder"):
            identity_fields.add("folder")

        update_data = {}
        for key, value in record_data.items():
            if key in identity_fields:
                update_data[key] = value
                continue
            source_keys = self.SOURCE_KEY_MAP.get(key, (key,))
            if any(record.get(sk) not in (None, "") for sk in source_keys):
                update_data[key] = value

        return update_data

    def process_records(self, records: list[dict]) -> Result:
        results = Result()

        context, error = self.create_context()
        if error is not None:
            results.add_error(error, fail_count=len(records))
            return results

        model_class = self.SERIALIZER_CLASS.Meta.model
        (viewable_ids, _, _) = RoleAssignment.get_accessible_object_ids(
            Folder.get_root_folder(), self.request.user, model_class
        )
        viewable_ids = set(viewable_ids)

        for record in records:
            record_data, error = self.prepare_create(record, context)
            if error is not None:
                results.add_error(error)
                if self.on_conflict == ConflictMode.STOP:
                    break
                continue

            existing = None
            internal_id = record.get("internal_id")
            if internal_id:
                existing = model_class.objects.filter(
                    pk=internal_id, id__in=viewable_ids
                ).first()
            if existing is None:
                existing = self.find_existing(record_data)

            if existing:
                match self.on_conflict:
                    case ConflictMode.SKIP:
                        results.add_skipped()
                        continue
                    case ConflictMode.STOP:
                        results.add_error(
                            Error(record=record, error="Record already exists")
                        )
                        break
                    case ConflictMode.UPDATE:
                        update_data = self._build_update_data(record, record_data)
                        serializer = self.SERIALIZER_CLASS(
                            instance=existing,
                            data=update_data,
                            partial=True,
                            context={"request": self.request},
                        )
                        if serializer.is_valid():
                            try:
                                serializer.save()
                                results.add_updated()
                            except Exception as e:
                                results.add_error(Error(record=record, error=str(e)))
                        else:
                            results.add_error(
                                Error(
                                    record=record,
                                    error=str(serializer.errors),
                                )
                            )
                        continue

            serializer = self.SERIALIZER_CLASS(
                data=record_data, context={"request": self.request}
            )
            if serializer.is_valid():
                try:
                    serializer.save()
                    results.add_created()
                except Exception as e:
                    results.add_error(Error(record=record, error=str(e)))
                    if self.on_conflict == ConflictMode.STOP:
                        break
            else:
                results.add_error(Error(record=record, error=str(serializer.errors)))
                if self.on_conflict == ConflictMode.STOP:
                    break

        logger.info(
            f"{self.__class__.__name__} record processing complete. "
            f"Created: {results.created}, Updated: {results.updated}, "
            f"Skipped: {results.skipped}, Failed: {results.failed}"
        )
        return results


class AssetRecordConsumer(RecordConsumer[None]):
    """
    Consumer for importing Asset records.
    Supports parent_assets linking via ref_id in a second pass.
    """

    SERIALIZER_CLASS = AssetWriteSerializer
    SOURCE_KEY_MAP: ClassVar[dict[str, tuple[str, ...]]] = {
        "reference_link": ("reference_link", "link"),
    }
    TYPE_MAP: Final[dict[str, str]] = {
        "primary": "PR",
        "pr": "PR",
        "support": "SP",
        "sp": "SP",
    }

    def create_context(self):
        return None, None

    def prepare_create(
        self, record: dict, context: None
    ) -> tuple[dict, Optional[Error]]:
        domain = self.folder_id
        domain_name = record.get("domain")
        if domain_name is not None:
            domain = self.folders_map.get(domain_name.lower(), self.folder_id)

        name = record.get("name")
        if not name:
            return {}, Error(record=record, error="Name field is mandatory")

        # Map type field
        asset_type = record.get("type", "SP")
        if isinstance(asset_type, str):
            asset_type = self.TYPE_MAP.get(
                asset_type.lower().strip(), asset_type.upper()
            )

        data = {
            "ref_id": record.get("ref_id", ""),
            "name": name,
            "type": asset_type,
            "folder": domain,
            "description": record.get("description", ""),
            "business_value": record.get("business_value", ""),
            "reference_link": record.get("reference_link", "")
            or record.get("link", ""),
            "observation": record.get("observation", ""),
        }

        filtering_labels = _resolve_filtering_labels(record.get("filtering_labels"))
        if filtering_labels:
            data["filtering_labels"] = filtering_labels

        return data, None

    def process_records(self, records: list[dict]) -> Result:
        """
        Override to add second pass for parent_assets linking.
        """
        # First pass: create all assets
        results = super().process_records(records)

        # Second pass: link parent_assets by ref_id
        for record in records:
            parent_assets_ref = record.get("parent_assets") or record.get(
                "parent_asset_ref_id"
            )
            if not parent_assets_ref:
                continue

            asset_ref_id = record.get("ref_id")
            if not asset_ref_id:
                continue

            # Find the created asset
            asset = Asset.objects.filter(ref_id=asset_ref_id).first()
            if not asset:
                continue

            # Parse parent ref_ids (comma or pipe separated)
            if isinstance(parent_assets_ref, str):
                parent_ref_ids = [
                    ref.strip()
                    for ref in parent_assets_ref.replace("|", ",").split(",")
                    if ref.strip()
                ]
            else:
                parent_ref_ids = [str(parent_assets_ref)]

            # Link parent assets
            for parent_ref_id in parent_ref_ids:
                parent_asset = Asset.objects.filter(ref_id=parent_ref_id).first()
                if parent_asset and parent_asset.id != asset.id:
                    asset.parent_assets.add(parent_asset)

        return results


class AppliedControlRecordConsumer(RecordConsumer[None]):
    """
    Consumer for importing AppliedControl records.
    Supports reference_control linking via ref_id.
    """

    SERIALIZER_CLASS = AppliedControlWriteSerializer
    SOURCE_KEY_MAP: ClassVar[dict[str, tuple[str, ...]]] = {
        "control_impact": ("control_impact", "impact"),
        "reference_control": ("reference_control", "reference_control_ref_id"),
    }
    IMPACT_MAP: Final[dict[str, int]] = {
        "very low": 1,
        "low": 2,
        "medium": 3,
        "high": 4,
        "very high": 5,
    }
    EFFORT_MAP: Final[dict[str, str]] = {
        "extra small": "XS",
        "extrasmall": "XS",
        "xs": "XS",
        "small": "S",
        "s": "S",
        "medium": "M",
        "m": "M",
        "large": "L",
        "l": "L",
        "extra large": "XL",
        "extralarge": "XL",
        "xl": "XL",
    }

    def create_context(self):
        return None, None

    def prepare_create(
        self, record: dict, context: None
    ) -> tuple[dict, Optional[Error]]:
        domain = self.folder_id
        domain_name = record.get("domain")
        if domain_name is not None:
            domain = self.folders_map.get(domain_name.lower(), self.folder_id)

        name = record.get("name")
        if not name:
            return {}, Error(record=record, error="Name field is mandatory")

        # Parse priority
        priority = record.get("priority")
        if isinstance(priority, (int, float)):
            priority = int(priority)
        elif isinstance(priority, str) and priority.isdigit():
            priority = int(priority)
        else:
            priority = None

        # Parse effort
        effort = record.get("effort")
        if isinstance(effort, str):
            effort = self.EFFORT_MAP.get(effort.lower().strip(), effort.upper())
            if effort not in ("XS", "S", "M", "L", "XL"):
                effort = None

        # Parse control_impact (1-5 scale)
        control_impact = record.get("control_impact") or record.get("impact")
        if isinstance(control_impact, (int, float)):
            control_impact = int(control_impact)
        elif isinstance(control_impact, str):
            if control_impact.isdigit():
                control_impact = int(control_impact)
            else:
                control_impact = self.IMPACT_MAP.get(control_impact.lower().strip())
        if isinstance(control_impact, int) and not (1 <= control_impact <= 5):
            control_impact = None

        # Look up reference_control by ref_id
        reference_control_id = None
        reference_control_ref = record.get("reference_control") or record.get(
            "reference_control_ref_id"
        )
        if reference_control_ref:
            from core.models import ReferenceControl

            ref_control = ReferenceControl.objects.filter(
                ref_id=reference_control_ref
            ).first()
            if ref_control:
                reference_control_id = ref_control.id

        data = {
            "ref_id": record.get("ref_id", ""),
            "name": name,
            "description": record.get("description", ""),
            "category": record.get("category", ""),
            "folder": domain,
            "status": record.get("status", "to_do"),
            "priority": priority,
            "csf_function": record.get("csf_function", "govern"),
            "effort": effort,
            "control_impact": control_impact,
            "link": record.get("link", ""),
            "eta": _parse_date(record.get("eta")),
            "expiry_date": _parse_date(record.get("expiry_date")),
            "start_date": _parse_date(record.get("start_date")),
        }

        if reference_control_id:
            data["reference_control"] = reference_control_id

        filtering_labels = _resolve_filtering_labels(record.get("filtering_labels"))
        if filtering_labels:
            data["filtering_labels"] = filtering_labels

        return data, None


class EvidenceRecordConsumer(RecordConsumer[None]):
    SERIALIZER_CLASS = EvidenceWriteSerializer

    def create_context(self):
        return None, None

    def prepare_create(
        self, record: dict, context: None
    ) -> tuple[dict, Optional[Error]]:
        domain = self.folder_id
        domain_name = record.get("domain")
        if domain_name is not None:
            domain = self.folders_map.get(domain_name.lower(), self.folder_id)

        name = record.get("name")
        if not name:
            return {}, Error(record=record, error="Name field is mandatory")

        data = {
            "name": name,
            "description": record.get("description", ""),
            "ref_id": record.get("ref_id", ""),
            "folder": domain,
        }

        filtering_labels = _resolve_filtering_labels(record.get("filtering_labels"))
        if filtering_labels:
            data["filtering_labels"] = filtering_labels

        return data, None


class UserRecordConsumer(RecordConsumer[None]):
    SERIALIZER_CLASS = UserWriteSerializer

    def find_existing(self, record_data: dict):
        email = record_data.get("email")
        if not email:
            return None
        return User.objects.filter(email__iexact=email).first()

    def create_context(self):
        return None, None

    def prepare_create(
        self, record: dict, context: None
    ) -> tuple[dict, Optional[Error]]:
        email = record.get("email")
        if email is None:
            return {}, Error(record=record, error="email field is mandatory")

        return {
            "email": email,
            "first_name": record.get("first_name"),
            "last_name": record.get("last_name"),
        }, None


class PerimeterRecordConsumer(RecordConsumer[None]):
    SERIALIZER_CLASS = PerimeterWriteSerializer

    def create_context(self):
        return None, None

    def prepare_create(
        self, record: dict, context: None
    ) -> tuple[dict, Optional[Error]]:
        domain = self.folder_id
        domain_name = record.get("domain")
        if domain_name is not None:
            domain = self.folders_map.get(domain_name.lower(), self.folder_id)

        name = record.get("name")
        if not name:
            return {}, Error(record=record, error="Name field is mandatory")

        return {
            "name": name,
            "folder": domain,
            "ref_id": record.get("ref_id", ""),
            "description": record.get("description", ""),
            "status": record.get("status"),
        }, None


class ThreatRecordConsumer(RecordConsumer[None]):
    SERIALIZER_CLASS = ThreatWriteSerializer

    def create_context(self):
        return None, None

    def prepare_create(
        self, record: dict, context: None
    ) -> tuple[dict, Optional[Error]]:
        domain = self.folder_id
        domain_name = record.get("domain")
        if domain_name is not None:
            domain = self.folders_map.get(domain_name.lower(), self.folder_id)

        name = record.get("name")
        if not name:
            return {}, Error(record=record, error="Name field is mandatory")

        return {
            "name": name,
            "description": record.get("description", ""),
            "folder": domain,
            "ref_id": record.get("ref_id", ""),
        }, None


class ReferenceControlRecordConsumer(RecordConsumer[None]):
    SERIALIZER_CLASS = ReferenceControlWriteSerializer
    SOURCE_KEY_MAP: ClassVar[dict[str, tuple[str, ...]]] = {
        "csf_function": ("function",),
    }
    CATEGORY_MAP: Final[dict[str, str]] = {
        "policy": "policy",
        "process": "process",
        "technical": "technical",
        "physical": "physical",
        "procedure": "procedure",
    }
    FUNCTION_MAP: Final[dict[str, str]] = {
        "govern": "govern",
        "identify": "identify",
        "protect": "protect",
        "detect": "detect",
        "respond": "respond",
        "recover": "recover",
        "governance": "govern",
    }

    def create_context(self):
        return None, None

    def prepare_create(
        self, record: dict, context: None
    ) -> tuple[dict, Optional[Error]]:
        domain = self.folder_id
        domain_name = record.get("domain")
        if domain_name is not None:
            domain = self.folders_map.get(domain_name.lower(), self.folder_id)

        name = record.get("name")
        if not name:
            return {}, Error(record=record, error="Name field is mandatory")

        category = None
        if record.get("category", ""):
            category_value = str(record.get("category")).strip().lower()
            category = self.CATEGORY_MAP.get(category_value)

        csf_function = None
        if record.get("function", ""):
            function_value = str(record.get("function")).strip().lower()
            csf_function = self.FUNCTION_MAP.get(function_value)

        reference_control_data = {
            "name": name,
            "description": record.get("description", ""),
            "ref_id": record.get("ref_id", ""),
            "folder": domain,
        }

        if category:
            reference_control_data["category"] = category
        if csf_function:
            reference_control_data["csf_function"] = csf_function

        return reference_control_data, None


@dataclass(frozen=True)
class FindingsAssessmentContext:
    findings_assessment: FindingsAssessment


class FindingsAssessmentRecordConsumer(RecordConsumer[FindingsAssessmentContext]):
    SERIALIZER_CLASS = FindingWriteSerializer
    SEVERITY_MAP: Final[dict[Optional[str], int]] = {
        None: -1,
        "info": 0,
        "low": 1,
        "medium": 2,
        "high": 3,
        "critical": 4,
    }

    def create_context(self):
        try:
            perimeter_id = self.perimeter_id
            perimeter = Perimeter.objects.get(id=perimeter_id)
            folder_id = perimeter.folder.id

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            assessment_name = f"Followup_{timestamp}"
            assessment_data = {
                "name": assessment_name,
                "perimeter": perimeter_id,
                "folder": folder_id,
            }

            serializer = FindingsAssessmentWriteSerializer(
                data=assessment_data,
                context={"request": self.request},
            )

            if serializer.is_valid():
                findings_assessment: FindingsAssessment = serializer.save()
                logger.info(
                    f"Created follow-up: {assessment_name} with ID {findings_assessment.id}"
                )

                return FindingsAssessmentContext(
                    findings_assessment=findings_assessment
                ), None
            return None, Error(record=assessment_data, error=str(serializer.errors))

        except Exception as e:
            return None, Error(record={}, error=str(e))

    def prepare_create(
        self, record: dict, context: FindingsAssessmentContext
    ) -> tuple[dict, Optional[Error]]:
        name = record.get("name")
        if not name:
            return {}, Error(record=record, error="Name field is mandatory")

        record_severity = record.get("severity")
        severity = self.SEVERITY_MAP.get(record_severity, -1)

        filtering_label_ids = _resolve_filtering_labels(record.get("filtering_labels"))

        finding_data = {
            "name": name,
            "description": record.get("description"),
            "ref_id": record.get("ref_id"),
            "status": record.get("status"),
            "findings_assessment": context.findings_assessment.id,
            "severity": severity,
            "filtering_labels": filtering_label_ids,
        }

        return finding_data, None


class PolicyRecordConsumer(RecordConsumer[None]):
    """
    Consumer for importing Policy records.
    Policy is a proxy model of AppliedControl with category='policy'.
    """

    SERIALIZER_CLASS = PolicyWriteSerializer

    def create_context(self):
        return None, None

    def prepare_create(
        self, record: dict, context: None
    ) -> tuple[dict, Optional[Error]]:
        domain = self.folder_id
        domain_name = record.get("domain")
        if domain_name is not None:
            domain = self.folders_map.get(domain_name.lower(), self.folder_id)

        name = record.get("name")
        if not name:
            return {}, Error(record=record, error="Name field is mandatory")

        priority = record.get("priority")
        if isinstance(priority, (int, float)):
            priority = int(priority)
        elif isinstance(priority, str) and priority.isdigit():
            priority = int(priority)
        else:
            priority = None

        data = {
            "ref_id": record.get("ref_id", ""),
            "name": name,
            "description": record.get("description", ""),
            "folder": domain,
            "status": record.get("status", "to_do"),
            "priority": priority,
            "csf_function": record.get("csf_function", "govern"),
            "eta": _parse_date(record.get("eta")),
            "expiry_date": _parse_date(record.get("expiry_date")),
            "link": record.get("link", ""),
            "effort": record.get("effort"),
        }

        filtering_labels = _resolve_filtering_labels(record.get("filtering_labels"))
        if filtering_labels:
            data["filtering_labels"] = filtering_labels

        return data, None


class SecurityExceptionRecordConsumer(RecordConsumer[None]):
    """
    Consumer for importing SecurityException records.
    """

    SERIALIZER_CLASS = SecurityExceptionWriteSerializer
    SEVERITY_MAP: Final[dict[Optional[str], int]] = {
        None: -1,
        "undefined": -1,
        "info": 0,
        "informational": 0,
        "low": 1,
        "medium": 2,
        "high": 3,
        "critical": 4,
    }
    STATUS_MAP: Final[dict[str, str]] = {
        "draft": "draft",
        "in_review": "in_review",
        "in review": "in_review",
        "approved": "approved",
        "resolved": "resolved",
        "expired": "expired",
        "deprecated": "deprecated",
    }

    def create_context(self):
        return None, None

    def prepare_create(
        self, record: dict, context: None
    ) -> tuple[dict, Optional[Error]]:
        domain = self.folder_id
        domain_name = record.get("domain")
        if domain_name is not None:
            domain = self.folders_map.get(domain_name.lower(), self.folder_id)

        name = record.get("name")
        if not name:
            return {}, Error(record=record, error="Name field is mandatory")

        # Map severity
        record_severity = record.get("severity")
        if isinstance(record_severity, str):
            severity = self.SEVERITY_MAP.get(record_severity.lower().strip(), -1)
        else:
            severity = -1

        # Map status
        record_status = record.get("status")
        if isinstance(record_status, str):
            status_value = self.STATUS_MAP.get(record_status.lower().strip(), "draft")
        else:
            status_value = "draft"

        return {
            "ref_id": record.get("ref_id", ""),
            "name": name,
            "description": record.get("description", ""),
            "folder": domain,
            "severity": severity,
            "status": status_value,
            "expiration_date": _parse_date(record.get("expiration_date")),
            "observation": record.get("observation", ""),
        }, None


class IncidentRecordConsumer(RecordConsumer[None]):
    """
    Consumer for importing Incident records.
    """

    SERIALIZER_CLASS = IncidentWriteSerializer
    SEVERITY_MAP: Final[dict[Optional[str], int]] = {
        None: 6,
        "undefined": 6,
        "unknown": 6,
        "critical": 1,
        "sev1": 1,
        "major": 2,
        "sev2": 2,
        "moderate": 3,
        "sev3": 3,
        "minor": 4,
        "sev4": 4,
        "low": 5,
        "sev5": 5,
    }
    STATUS_MAP: Final[dict[str, str]] = {
        "new": "new",
        "ongoing": "ongoing",
        "in progress": "ongoing",
        "in_progress": "ongoing",
        "resolved": "resolved",
        "closed": "closed",
        "dismissed": "dismissed",
    }
    DETECTION_MAP: Final[dict[str, str]] = {
        "internal": "internally_detected",
        "internally_detected": "internally_detected",
        "external": "externally_detected",
        "externally_detected": "externally_detected",
    }

    def create_context(self):
        return None, None

    def prepare_create(
        self, record: dict, context: None
    ) -> tuple[dict, Optional[Error]]:
        domain = self.folder_id
        domain_name = record.get("domain")
        if domain_name is not None:
            domain = self.folders_map.get(domain_name.lower(), self.folder_id)

        name = record.get("name")
        if not name:
            return {}, Error(record=record, error="Name field is mandatory")

        # Map severity
        record_severity = record.get("severity")
        if isinstance(record_severity, str):
            severity = self.SEVERITY_MAP.get(record_severity.lower().strip(), 6)
        elif isinstance(record_severity, int) and 1 <= record_severity <= 6:
            severity = record_severity
        else:
            severity = 6

        # Map status
        record_status = record.get("status")
        if isinstance(record_status, str):
            status_value = self.STATUS_MAP.get(record_status.lower().strip(), "new")
        else:
            status_value = "new"

        # Map detection
        record_detection = record.get("detection")
        if isinstance(record_detection, str):
            detection_value = self.DETECTION_MAP.get(
                record_detection.lower().strip(), "internally_detected"
            )
        else:
            detection_value = "internally_detected"

        data = {
            "ref_id": record.get("ref_id", ""),
            "name": name,
            "description": record.get("description", ""),
            "folder": domain,
            "severity": severity,
            "status": status_value,
            "detection": detection_value,
            "link": record.get("link", ""),
            "reported_at": _parse_datetime(record.get("reported_at")),
        }

        filtering_labels = _resolve_filtering_labels(record.get("filtering_labels"))
        if filtering_labels:
            data["filtering_labels"] = filtering_labels

        return data, None


class LoadFileView(APIView):
    parser_classes = (FileUploadParser,)
    serializer_class = LoadFileSerializer

    def process_excel_file(self, request, record_file: io.BytesIO) -> Response:
        # Parse Excel data
        # Note: I can still pick the request.user for extra checks on the legit access for write operations
        model_type_string = request.META.get("HTTP_X_MODEL_TYPE")
        model_type = ModelType.from_string(model_type_string)
        folder_id = request.META.get("HTTP_X_FOLDER_ID")
        perimeter_id = request.META.get("HTTP_X_PERIMETER_ID")
        framework_id = request.META.get("HTTP_X_FRAMEWORK_ID")
        matrix_id = request.META.get("HTTP_X_MATRIX_ID")
        on_conflict_str = request.META.get("HTTP_X_ON_CONFLICT", "stop")
        try:
            on_conflict = ConflictMode(on_conflict_str)
        except ValueError:
            on_conflict = ConflictMode.STOP

        logger.info(
            f"Processing file with model: {model_type}, folder: {folder_id}, perimeter: {perimeter_id}, framework: {framework_id}, matrix: {matrix_id}"
        )

        # get viewable and actionable folders, perimeters and frameworks
        # build a map from the name to the id

        folders_map = get_accessible_folders_map(request.user)
        file_type: RecordFileType = RecordFileType.XLSX
        res = None
        try:
            if model_type is None:
                logger.error(f"Unknown model type: {repr(model_type_string)}")
                return Response(
                    {"error": "UnknownModelType"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Special handling for TPRM multi-sheet import
            match model_type:
                case ModelType.TPRM:
                    res = self._process_tprm_file(
                        request, record_file, folders_map, folder_id, on_conflict
                    )
                # Special handling for EBIOS RM Study ARM format (multi-sheet)
                case ModelType.EBIOS_RM_STUDY_ARM:
                    res = self._process_ebios_rm_study_arm(
                        request, record_file, folder_id, matrix_id, on_conflict
                    )
                # Special handling for EBIOS RM Study Excel export format
                case ModelType.EBIOS_RM_STUDY_EXCEL:
                    res = self._process_ebios_rm_study_excel(
                        request, record_file, folder_id, matrix_id, on_conflict
                    )
                case _:
                    is_excel = is_excel_file(record_file)
                    if is_excel:
                        df = normalize_datetime_columns(
                            pd.read_excel(record_file)
                        ).fillna("")
                    else:
                        file_type = RecordFileType.CSV
                        df = pd.read_csv(record_file).fillna("")

                    base_context = BaseContext(
                        request,
                        folders_map=folders_map,
                        folder_id=folder_id,
                        perimeter_id=perimeter_id,
                        matrix_id=matrix_id,
                        framework_id=framework_id,
                        on_conflict=on_conflict,
                    )
                    records = df.to_dict(orient="records")

                    match model_type:
                        case ModelType.ASSET:
                            res = (
                                AssetRecordConsumer(base_context)
                                .process_records(records)
                                .to_dict()
                            )
                        case ModelType.APPLIED_CONTROL:
                            res = (
                                AppliedControlRecordConsumer(base_context)
                                .process_records(records)
                                .to_dict()
                            )
                        case ModelType.EVIDENCE:
                            res = (
                                EvidenceRecordConsumer(base_context)
                                .process_records(records)
                                .to_dict()
                            )
                        case ModelType.USER:
                            res = (
                                UserRecordConsumer(base_context)
                                .process_records(records)
                                .to_dict()
                            )
                        case ModelType.PERIMETER:
                            res = (
                                PerimeterRecordConsumer(base_context)
                                .process_records(records)
                                .to_dict()
                            )
                        case ModelType.THREAT:
                            res = (
                                ThreatRecordConsumer(base_context)
                                .process_records(records)
                                .to_dict()
                            )
                        case ModelType.REFERENCE_CONTROL:
                            res = (
                                ReferenceControlRecordConsumer(base_context)
                                .process_records(records)
                                .to_dict()
                            )
                        case ModelType.FINDINGS_ASSESSMENT:
                            res = (
                                FindingsAssessmentRecordConsumer(base_context)
                                .process_records(records)
                                .to_dict()
                            )
                        case ModelType.POLICY:
                            res = (
                                PolicyRecordConsumer(base_context)
                                .process_records(records)
                                .to_dict()
                            )
                        case ModelType.SECURITY_EXCEPTION:
                            res = (
                                SecurityExceptionRecordConsumer(base_context)
                                .process_records(records)
                                .to_dict()
                            )
                        case ModelType.INCIDENT:
                            res = (
                                IncidentRecordConsumer(base_context)
                                .process_records(records)
                                .to_dict()
                            )
                        case _:
                            res = self.process_data(
                                request,
                                records,
                                model_type,
                                folder_id,
                                perimeter_id,
                                framework_id,
                                matrix_id,
                            )

        except Exception as e:
            logger.error(f"Error parsing {file_type} file", exc_info=e)
            return Response(
                {"error": file_type.get_error()},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {"message": "File loaded successfully", "results": res},
            status=status.HTTP_200_OK,
        )

    def process_data(
        self,
        request,
        records,
        model_type: ModelType,
        folder_id,
        perimeter_id,
        framework_id,
        matrix_id=None,
    ):
        folders_map = get_accessible_folders_map(request.user)

        # Dispatch to appropriate handler
        match model_type:
            case ModelType.COMPLIANCE_ASSESSMENT:
                return self._process_compliance_assessment(
                    request, records, folder_id, perimeter_id, framework_id
                )
            case ModelType.RISK_ASSESSMENT:
                return self._process_risk_assessment(
                    request, records, folder_id, perimeter_id, matrix_id
                )
            case ModelType.ELEMENTARY_ACTION:
                return self._process_elementary_actions(
                    request, records, folders_map, folder_id
                )
            case ModelType.PROCESSING:
                return self._process_processings(
                    request, records, folders_map, folder_id
                )
            case ModelType.FOLDER:
                return self._process_folders(request, records)
            case _:
                return {
                    "successful": 0,
                    "failed": 0,
                    "errors": [{"error": f"Unknown model type: {model_type}"}],
                }

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
                "name": record.get("name"),  # Name is mandatory
                "description": record.get("description", ""),
                "ref_id": record.get("ref_id", ""),
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
                "name": record.get("name"),
                "description": record.get("description", ""),
                "ref_id": record.get("ref_id", ""),
                "folder": domain_id,
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

    def _process_compliance_assessment(
        self, request, records, folder_id, perimeter_id, framework_id
    ):
        results = {"successful": 0, "failed": 0, "errors": []}
        try:
            # Get the perimeter object to extract its folder ID
            perimeter = Perimeter.objects.get(id=perimeter_id)
            folder_id = perimeter.folder.id

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

    def _process_tprm_file(
        self,
        request,
        excel_file: io.BytesIO,
        folders_map,
        folder_id,
        on_conflict=ConflictMode.STOP,
    ):
        """
        Process TPRM multi-sheet Excel file with Entities, Solutions, and Contracts
        """
        try:
            # Read all sheets from Excel file
            excel_data = pd.ExcelFile(excel_file)

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
            if "Entities" in excel_data.sheet_names:
                logger.info("Processing Entities sheet")
                entities_df = normalize_datetime_columns(
                    pd.read_excel(excel_file, sheet_name="Entities")
                ).fillna("")
                entities_records = entities_df.to_dict(orient="records")
                entities_result, entity_ref_map = self._process_entities(
                    request, entities_records, folders_map, folder_id, on_conflict
                )
                overall_results["entities"] = entities_result
                if entities_result.get("stopped"):
                    return overall_results
            else:
                logger.warning("No 'Entities' sheet found in Excel file")

            # Process Solutions sheet second (requires entities to exist)
            if "Solutions" in excel_data.sheet_names:
                logger.info("Processing Solutions sheet")
                solutions_df = normalize_datetime_columns(
                    pd.read_excel(excel_file, sheet_name="Solutions")
                ).fillna("")
                solutions_records = solutions_df.to_dict(orient="records")
                solutions_result, solution_ref_map = self._process_solutions(
                    request,
                    solutions_records,
                    folders_map,
                    folder_id,
                    entity_ref_map,
                    on_conflict,
                )
                overall_results["solutions"] = solutions_result
                if solutions_result.get("stopped"):
                    return overall_results
            else:
                logger.warning("No 'Solutions' sheet found in Excel file")

            # Process Contracts sheet last (requires entities and solutions)
            if "Contracts" in excel_data.sheet_names:
                logger.info("Processing Contracts sheet")
                contracts_df = normalize_datetime_columns(
                    pd.read_excel(excel_file, sheet_name="Contracts")
                ).fillna("")
                contracts_records = contracts_df.to_dict(orient="records")
                contracts_result = self._process_contracts(
                    request,
                    contracts_records,
                    folders_map,
                    folder_id,
                    entity_ref_map,
                    solution_ref_map,
                    on_conflict,
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

    def _process_entities(
        self, request, records, folders_map, folder_id, on_conflict=ConflictMode.STOP
    ):
        """Process entities from TPRM import"""
        results = {
            "successful": 0,
            "failed": 0,
            "skipped": 0,
            "updated": 0,
            "errors": [],
        }
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

                # Check for existing entity by ref_id or name
                existing_entity = Entity.objects.filter(ref_id=ref_id).first()
                if not existing_entity:
                    existing_entity = Entity.objects.filter(
                        name__iexact=record.get("name"),
                        folder_id=domain,
                    ).first()

                if existing_entity:
                    ref_id_map[ref_id] = str(existing_entity.id)
                    match on_conflict:
                        case ConflictMode.SKIP:
                            results["skipped"] += 1
                            continue
                        case ConflictMode.STOP:
                            results["failed"] += 1
                            results["errors"].append(
                                {
                                    "record": record,
                                    "error": "Entity already exists (conflict policy: stop)",
                                }
                            )
                            results["stopped"] = True
                            break
                        case ConflictMode.UPDATE:
                            update_data = {
                                "ref_id": ref_id,
                                "name": record.get("name"),
                                "description": record.get("description", ""),
                                "mission": record.get("mission", ""),
                                "folder": domain,
                            }
                            if record.get("country"):
                                update_data["country"] = record.get("country")
                            if record.get("currency"):
                                update_data["currency"] = record.get("currency")
                            for field in [
                                "dependency",
                                "penetration",
                                "maturity",
                                "trust",
                            ]:
                                value = record.get(field)
                                if value != "" and value is not None:
                                    try:
                                        update_data[f"default_{field}"] = int(value)
                                    except (ValueError, TypeError):
                                        pass
                            legal_ids = {}
                            for id_type in ["lei", "euid", "duns", "vat"]:
                                value = record.get(id_type, "")
                                if value and str(value).strip():
                                    legal_ids[id_type.upper()] = str(value).strip()
                            if legal_ids:
                                update_data["legal_identifiers"] = legal_ids
                            serializer = EntityWriteSerializer(
                                instance=existing_entity,
                                data=update_data,
                                partial=True,
                                context={"request": request},
                            )
                            if serializer.is_valid():
                                serializer.save()
                                results["updated"] += 1
                            else:
                                results["failed"] += 1
                                results["errors"].append(
                                    {"record": record, "errors": serializer.errors}
                                )
                            continue

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
        self,
        request,
        records,
        folders_map,
        folder_id,
        entity_ref_map,
        on_conflict=ConflictMode.STOP,
    ):
        """Process solutions from TPRM import"""
        results = {
            "successful": 0,
            "failed": 0,
            "skipped": 0,
            "updated": 0,
            "errors": [],
        }
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

                # Check for existing solution by ref_id or name
                existing_solution = Solution.objects.filter(ref_id=ref_id).first()
                if not existing_solution:
                    existing_solution = Solution.objects.filter(
                        name__iexact=record.get("name"),
                    ).first()

                if existing_solution:
                    ref_id_map[ref_id] = str(existing_solution.id)
                    match on_conflict:
                        case ConflictMode.SKIP:
                            results["skipped"] += 1
                            continue
                        case ConflictMode.STOP:
                            results["failed"] += 1
                            results["errors"].append(
                                {
                                    "record": record,
                                    "error": "Solution already exists (conflict policy: stop)",
                                }
                            )
                            results["stopped"] = True
                            break
                        case ConflictMode.UPDATE:
                            update_data = {
                                "ref_id": ref_id,
                                "name": record.get("name"),
                                "description": record.get("description", ""),
                                "provider_entity": provider_entity_id,
                            }
                            if (
                                record.get("criticality") != ""
                                and record.get("criticality") is not None
                            ):
                                try:
                                    update_data["criticality"] = int(
                                        record.get("criticality")
                                    )
                                except (ValueError, TypeError):
                                    pass
                            serializer = SolutionWriteSerializer(
                                instance=existing_solution,
                                data=update_data,
                                partial=True,
                                context={"request": request},
                            )
                            if serializer.is_valid():
                                serializer.save()
                                results["updated"] += 1
                            else:
                                results["failed"] += 1
                                results["errors"].append(
                                    {"record": record, "errors": serializer.errors}
                                )
                            continue

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
        self,
        request,
        records,
        folders_map,
        folder_id,
        entity_ref_map,
        solution_ref_map,
        on_conflict=ConflictMode.STOP,
    ):
        """Process contracts from TPRM import"""
        results = {
            "successful": 0,
            "failed": 0,
            "skipped": 0,
            "updated": 0,
            "errors": [],
        }

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
                start_date = _parse_date(record.get("start_date"))
                if start_date:
                    contract_data["start_date"] = start_date
                end_date = _parse_date(record.get("end_date"))
                if end_date:
                    contract_data["end_date"] = end_date
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

                # Check for existing contract by ref_id or name
                existing_contract = Contract.objects.filter(ref_id=ref_id).first()
                if not existing_contract:
                    existing_contract = Contract.objects.filter(
                        name__iexact=record.get("name"),
                        folder_id=domain,
                    ).first()

                if existing_contract:
                    match on_conflict:
                        case ConflictMode.SKIP:
                            results["skipped"] += 1
                            continue
                        case ConflictMode.STOP:
                            results["failed"] += 1
                            results["errors"].append(
                                {
                                    "record": record,
                                    "error": "Contract already exists (conflict policy: stop)",
                                }
                            )
                            results["stopped"] = True
                            break
                        case ConflictMode.UPDATE:
                            serializer = ContractWriteSerializer(
                                instance=existing_contract,
                                data=contract_data,
                                partial=True,
                                context={"request": request},
                            )
                            if serializer.is_valid():
                                serializer.save()
                                results["updated"] += 1
                            else:
                                results["failed"] += 1
                                results["errors"].append(
                                    {"record": record, "errors": serializer.errors}
                                )
                            continue

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

    def post(self, request, *args, **kwargs) -> Response:
        # if not request.user.has_file_permission:
        #     logger.error("Unauthorized user tried to load a file", user=request.user)
        #     return Response({}, status=status.HTTP_403_FORBIDDEN)

        if not request.data:
            logger.error("Request has no data")
            return Response(
                {"error": "fileLoadNoData"}, status=status.HTTP_400_BAD_REQUEST
            )

        file_obj: Optional[UploadedFile] = request.data.get("file")
        if file_obj is None:
            logger.error("No file provided")
            return Response(
                {"error": "noFileProvided"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Check if the file is an Excel file
        file_extension = file_obj.name.split(".")[-1].lower()
        if file_extension not in ["xlsx", "xls", "csv"]:
            logger.error(f"Unsupported file format: {repr(file_extension)}")
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

            # Get treatment status
            treatment = record.get("treatment", "").strip().lower()

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
                "treatment": next(
                    (
                        opt
                        for opt, _ in RiskScenario.TREATMENT_OPTIONS
                        if treatment == opt
                    ),
                    "open",
                ),
            }

            # Create the risk scenario
            scenario_serializer = RiskScenarioWriteSerializer(
                data=scenario_data, context={"request": request}
            )

            logger.debug(
                f"Validating scenario serializer for '{name}' with data: {scenario_serializer.initial_data}"
            )

            if not scenario_serializer.is_valid():
                logger.warning(
                    f"Risk scenario validation failed: {scenario_serializer.errors}"
                )
                return None

            risk_scenario = scenario_serializer.save()

            # Link filtering labels
            filtering_label_ids = _resolve_filtering_labels(
                record.get("filtering_labels")
            )
            if filtering_label_ids:
                risk_scenario.filtering_labels.set(filtering_label_ids)

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

    def _process_ebios_rm_study_arm(
        self,
        request,
        excel_file: io.BytesIO,
        folder_id,
        matrix_id,
        on_conflict=ConflictMode.STOP,
    ):
        """
        Process EBIOS RM Study import from ARM Excel format.
        This creates an EbiosRMStudy with Workshop 1, 2, and 3 objects:
        - Workshop 1: Assets, Feared Events, Applied Controls
        - Workshop 2: RoTo Couples
        - Workshop 3: Stakeholders, Strategic Scenarios, Attack Paths
        """

        results = {
            "successful": 0,
            "failed": 0,
            "errors": [],
            "details": {
                "study": None,
                "assets_created": 0,
                "assets_updated": 0,
                "assets_skipped": 0,
                "feared_events_created": 0,
                "feared_events_updated": 0,
                "feared_events_skipped": 0,
                "applied_controls_created": 0,
                "applied_controls_updated": 0,
                "applied_controls_skipped": 0,
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
            excel_file.seek(0)
            arm_data = process_arm_file(excel_file.read())

            # Generate study name
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            study_name = f"EBIOS_RM_Study_{timestamp}"

            # Use missions as description
            study_description = arm_data.get("study_description", "")

            # =========================================================
            # Step 1: Create Assets (primary and supporting)
            # =========================================================
            stopped = False
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
                    asset_name = asset_data["name"]
                    # Check for existing asset with the same name in this folder
                    existing_asset = Asset.objects.filter(
                        name__iexact=asset_name,
                        folder=folder,
                    ).first()

                    if existing_asset:
                        match on_conflict:
                            case ConflictMode.SKIP:
                                asset_name_to_id[asset_name.lower()] = existing_asset.id
                                results["details"]["assets_skipped"] += 1
                                if asset_data.get("parent_name"):
                                    supporting_asset_parents[asset_name.lower()] = (
                                        asset_data["parent_name"]
                                    )
                                continue
                            case ConflictMode.STOP:
                                results["errors"].append(
                                    {
                                        "asset": asset_name,
                                        "error": "Asset already exists (conflict policy: stop)",
                                    }
                                )
                                stopped = True
                                break
                            case ConflictMode.UPDATE:
                                existing_asset.description = asset_data.get(
                                    "description", existing_asset.description
                                )
                                existing_asset.type = "SP"
                                existing_asset.save()
                                asset_name_to_id[asset_name.lower()] = existing_asset.id
                                results["details"]["assets_updated"] += 1
                                if asset_data.get("parent_name"):
                                    supporting_asset_parents[asset_name.lower()] = (
                                        asset_data["parent_name"]
                                    )
                                continue

                    serializer = AssetWriteSerializer(
                        data={
                            "name": asset_name,
                            "description": asset_data["description"],
                            "type": "SP",
                            "folder": folder_id,
                        },
                        context={"request": request},
                    )
                    if serializer.is_valid():
                        asset = serializer.save()
                        asset_name_to_id[asset_name.lower()] = asset.id
                        results["details"]["assets_created"] += 1

                        # Track parent relationship if specified
                        if asset_data.get("parent_name"):
                            supporting_asset_parents[asset_name.lower()] = asset_data[
                                "parent_name"
                            ]
                    else:
                        results["errors"].append(
                            {"asset": asset_name, "error": serializer.errors}
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
                            # Check for existing asset
                            existing_sp = Asset.objects.filter(
                                name__iexact=supporting_name,
                                folder=folder,
                            ).first()

                            if existing_sp:
                                asset_name_to_id[supporting_name.lower()] = (
                                    existing_sp.id
                                )
                                match on_conflict:
                                    case ConflictMode.SKIP:
                                        results["details"]["assets_skipped"] += 1
                                    case ConflictMode.STOP:
                                        results["errors"].append(
                                            {
                                                "asset": supporting_name,
                                                "error": "Asset already exists (conflict policy: stop)",
                                            }
                                        )
                                        stopped = True
                                        break
                                    case ConflictMode.UPDATE:
                                        existing_sp.type = "SP"
                                        existing_sp.save()
                                        results["details"]["assets_updated"] += 1
                                continue

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

                    if stopped:
                        break

                    # Check for existing primary asset
                    primary_name = asset_data["name"]
                    existing_primary = Asset.objects.filter(
                        name__iexact=primary_name,
                        folder=folder,
                    ).first()

                    if existing_primary:
                        match on_conflict:
                            case ConflictMode.SKIP:
                                asset_name_to_id[primary_name.lower()] = (
                                    existing_primary.id
                                )
                                results["details"]["assets_skipped"] += 1
                                continue
                            case ConflictMode.STOP:
                                results["errors"].append(
                                    {
                                        "asset": primary_name,
                                        "error": "Asset already exists (conflict policy: stop)",
                                    }
                                )
                                stopped = True
                                break
                            case ConflictMode.UPDATE:
                                existing_primary.description = asset_data.get(
                                    "description", existing_primary.description
                                )
                                existing_primary.type = "PR"
                                existing_primary.save()
                                asset_name_to_id[primary_name.lower()] = (
                                    existing_primary.id
                                )
                                results["details"]["assets_updated"] += 1
                                continue

                    # Create the primary asset
                    serializer = AssetWriteSerializer(
                        data={
                            "name": primary_name,
                            "description": asset_data["description"],
                            "type": "PR",
                            "folder": folder_id,
                        },
                        context={"request": request},
                    )
                    if serializer.is_valid():
                        asset = serializer.save()
                        asset_name_to_id[primary_name.lower()] = asset.id
                        results["details"]["assets_created"] += 1
                    else:
                        results["errors"].append(
                            {"asset": primary_name, "error": serializer.errors}
                        )
                except Exception as e:
                    results["errors"].append(
                        {"asset": asset_data["name"], "error": str(e)}
                    )

            if stopped:
                return results

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

            if stopped:
                return results

            # =========================================================
            # Step 2: Create Applied Controls
            # =========================================================
            for control_data in arm_data.get("applied_controls", []):
                try:
                    control_name = control_data["name"]
                    # Check for existing applied control with the same name in this folder
                    existing_control = AppliedControl.objects.filter(
                        name__iexact=control_name,
                        folder=folder,
                    ).first()

                    if existing_control:
                        match on_conflict:
                            case ConflictMode.SKIP:
                                results["details"]["applied_controls_skipped"] += 1
                                continue
                            case ConflictMode.STOP:
                                results["errors"].append(
                                    {
                                        "control": control_name,
                                        "error": "Applied control already exists (conflict policy: stop)",
                                    }
                                )
                                stopped = True
                                break
                            case ConflictMode.UPDATE:
                                existing_control.description = control_data.get(
                                    "description", existing_control.description
                                )
                                if control_data.get("ref_id"):
                                    existing_control.ref_id = control_data["ref_id"]
                                existing_control.save()
                                results["details"]["applied_controls_updated"] += 1
                                continue

                    serializer = AppliedControlWriteSerializer(
                        data={
                            "name": control_name,
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
                                "control": control_name,
                                "error": serializer.errors,
                            }
                        )
                except Exception as e:
                    results["errors"].append(
                        {"control": control_data["name"], "error": str(e)}
                    )

            if stopped:
                return results

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
                        fe_name = fe_data["name"]
                        # Find linked assets
                        linked_asset_ids = []
                        for asset_name in fe_data.get("asset_names", []):
                            asset_id = asset_name_to_id.get(asset_name.lower())
                            if asset_id:
                                linked_asset_ids.append(asset_id)

                        # Check for existing feared event
                        existing_fe = FearedEvent.objects.filter(
                            ebios_rm_study=study,
                            name__iexact=fe_name,
                        ).first()

                        if existing_fe:
                            match on_conflict:
                                case ConflictMode.SKIP:
                                    results["details"]["feared_events_skipped"] += 1
                                    continue
                                case ConflictMode.STOP:
                                    results["errors"].append(
                                        {
                                            "feared_event": fe_name,
                                            "error": "Feared event already exists (conflict policy: stop)",
                                        }
                                    )
                                    stopped = True
                                    break
                                case ConflictMode.UPDATE:
                                    existing_fe.justification = fe_data.get(
                                        "justification", existing_fe.justification
                                    )
                                    existing_fe.gravity = fe_data.get(
                                        "gravity", existing_fe.gravity
                                    )
                                    existing_fe.is_selected = fe_data.get(
                                        "is_selected", existing_fe.is_selected
                                    )
                                    existing_fe.save()
                                    if linked_asset_ids:
                                        existing_fe.assets.set(linked_asset_ids)
                                    results["details"]["feared_events_updated"] += 1
                                    continue

                        # Create feared event
                        feared_event = FearedEvent.objects.create(
                            ebios_rm_study=study,
                            name=fe_name,
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

                # Mark step 3 (index 2) as done if we created or updated feared events
                fe_count = (
                    results["details"]["feared_events_created"]
                    + results["details"]["feared_events_updated"]
                )
                if fe_count > 0:
                    study.meta["workshops"][0]["steps"][2]["status"] = "done"
                    meta_updated = True

                if stopped:
                    if meta_updated:
                        study.save()
                    return results

                # =========================================================
                # Step 5: Create RoTo Couples (Workshop 2)
                # =========================================================
                results["details"]["roto_couples_created"] = 0
                results["details"]["roto_couples_updated"] = 0
                results["details"]["roto_couples_skipped"] = 0

                roto_couples_data = arm_data.get("roto_couples", [])
                logger.info(
                    f"[RoTo Import] Received {len(roto_couples_data)} RoTo couples from extraction"
                )
                for idx, roto_data in enumerate(roto_couples_data):
                    logger.info(f"[RoTo Import] Processing #{idx + 1}: {roto_data}")

                for roto_data in roto_couples_data:
                    try:
                        # Find or create the risk origin terminology
                        risk_origin_name = roto_data["risk_origin"]
                        normalized_name = risk_origin_name.lower().replace(" ", "_")

                        # Try to find existing terminology by name (case-insensitive)
                        # Check both the original name and the normalized form
                        risk_origin = Terminology.objects.filter(
                            field_path=Terminology.FieldPath.ROTO_RISK_ORIGIN,
                            name__iexact=risk_origin_name,
                        ).first()

                        if not risk_origin:
                            risk_origin = Terminology.objects.filter(
                                field_path=Terminology.FieldPath.ROTO_RISK_ORIGIN,
                                name__iexact=normalized_name,
                            ).first()

                        if not risk_origin:
                            # Create a new terminology entry for this risk origin
                            risk_origin = Terminology.objects.create(
                                field_path=Terminology.FieldPath.ROTO_RISK_ORIGIN,
                                name=normalized_name,
                                is_visible=True,
                                builtin=False,
                            )
                            logger.info(
                                f"Created new risk origin terminology: {risk_origin_name}"
                            )

                        # Check if a RoTo couple already exists for this study + risk_origin + target_objective
                        existing_roto = RoTo.objects.filter(
                            ebios_rm_study=study,
                            risk_origin=risk_origin,
                            target_objective__iexact=roto_data["target_objective"],
                        ).first()

                        if existing_roto:
                            match on_conflict:
                                case ConflictMode.SKIP:
                                    results["details"]["roto_couples_skipped"] += 1
                                    logger.info(
                                        f"[RoTo Import] Skipped existing RoTo couple: "
                                        f"{risk_origin_name} - {roto_data['target_objective']}"
                                    )
                                    continue
                                case ConflictMode.STOP:
                                    results["errors"].append(
                                        {
                                            "roto_couple": f"{roto_data.get('risk_origin', 'unknown')} - {roto_data.get('target_objective', 'unknown')}",
                                            "error": "RoTo couple already exists (conflict policy: stop)",
                                        }
                                    )
                                    stopped = True
                                    break
                                case ConflictMode.UPDATE:
                                    existing_roto.motivation = roto_data.get(
                                        "motivation", existing_roto.motivation
                                    )
                                    existing_roto.resources = roto_data.get(
                                        "resources", existing_roto.resources
                                    )
                                    existing_roto.activity = roto_data.get(
                                        "activity", existing_roto.activity
                                    )
                                    existing_roto.is_selected = roto_data.get(
                                        "is_selected", existing_roto.is_selected
                                    )
                                    existing_roto.justification = roto_data.get(
                                        "justification", existing_roto.justification
                                    )
                                    existing_roto.save()
                                    results["details"]["roto_couples_updated"] += 1
                                    logger.info(
                                        f"[RoTo Import] Updated existing RoTo couple: "
                                        f"{risk_origin_name} - {roto_data['target_objective']}"
                                    )
                                    continue
                        else:
                            # Create the RoTo couple
                            RoTo.objects.create(
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

                # Mark workshop 2 step 1 (index 0) as done if we created or updated RoTo couples
                roto_count = (
                    results["details"]["roto_couples_created"]
                    + results["details"]["roto_couples_updated"]
                )
                if roto_count > 0:
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

                if stopped:
                    if meta_updated:
                        study.save()
                    return results

                # =========================================================
                # Step 6: Create Stakeholders (Workshop 3)
                # =========================================================
                results["details"]["entities_created"] = 0
                results["details"]["stakeholders_created"] = 0
                results["details"]["stakeholders_updated"] = 0
                results["details"]["stakeholders_skipped"] = 0

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
                            # Check for existing stakeholder
                            existing_stakeholder = Stakeholder.objects.filter(
                                ebios_rm_study=study,
                                entity=entity,
                                category=category,
                            ).first()

                            if existing_stakeholder:
                                match on_conflict:
                                    case ConflictMode.SKIP:
                                        results["details"]["stakeholders_skipped"] += 1
                                        continue
                                    case ConflictMode.STOP:
                                        results["errors"].append(
                                            {
                                                "stakeholder": entity_name,
                                                "error": "Stakeholder already exists (conflict policy: stop)",
                                            }
                                        )
                                        stopped = True
                                        break
                                    case ConflictMode.UPDATE:
                                        existing_stakeholder.is_selected = (
                                            stakeholder_data.get(
                                                "is_selected",
                                                existing_stakeholder.is_selected,
                                            )
                                        )
                                        existing_stakeholder.current_dependency = (
                                            stakeholder_data.get(
                                                "current_dependency",
                                                existing_stakeholder.current_dependency,
                                            )
                                        )
                                        existing_stakeholder.current_penetration = stakeholder_data.get(
                                            "current_penetration",
                                            existing_stakeholder.current_penetration,
                                        )
                                        existing_stakeholder.current_maturity = (
                                            stakeholder_data.get(
                                                "current_maturity",
                                                existing_stakeholder.current_maturity,
                                            )
                                        )
                                        existing_stakeholder.current_trust = (
                                            stakeholder_data.get(
                                                "current_trust",
                                                existing_stakeholder.current_trust,
                                            )
                                        )
                                        existing_stakeholder.residual_dependency = stakeholder_data.get(
                                            "residual_dependency",
                                            existing_stakeholder.residual_dependency,
                                        )
                                        existing_stakeholder.residual_penetration = stakeholder_data.get(
                                            "residual_penetration",
                                            existing_stakeholder.residual_penetration,
                                        )
                                        existing_stakeholder.residual_maturity = (
                                            stakeholder_data.get(
                                                "residual_maturity",
                                                existing_stakeholder.residual_maturity,
                                            )
                                        )
                                        existing_stakeholder.residual_trust = (
                                            stakeholder_data.get(
                                                "residual_trust",
                                                existing_stakeholder.residual_trust,
                                            )
                                        )
                                        existing_stakeholder.save()
                                        results["details"]["stakeholders_updated"] += 1
                                        logger.debug(
                                            f"Updated stakeholder: {entity_name} ({category.name})"
                                        )
                                        continue

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

                # Mark workshop 3 step 1 (index 0) as done if we created or updated stakeholders
                stakeholder_count = (
                    results["details"]["stakeholders_created"]
                    + results["details"]["stakeholders_updated"]
                )
                if stakeholder_count > 0:
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

                if stopped:
                    if meta_updated:
                        study.save()
                    return results

                # =========================================================
                # Step 7: Create Strategic Scenarios and Attack Paths (Workshop 3)
                # =========================================================
                results["details"]["strategic_scenarios_created"] = 0
                results["details"]["strategic_scenarios_updated"] = 0
                results["details"]["strategic_scenarios_skipped"] = 0
                results["details"]["attack_paths_created"] = 0

                logger.info(
                    "[Strategic Scenarios Import] Starting strategic scenario creation"
                )

                # Build a lookup for RoTo couples by risk_origin + target_objective
                roto_lookup = {}
                for roto in study.roto_set.all():
                    # Store both the normalized name and the original for flexible matching
                    key = (
                        roto.risk_origin.name.lower(),
                        roto.target_objective.lower(),
                    )
                    roto_lookup[key] = roto
                    logger.info(
                        f"[Strategic Scenarios Import] RoTo lookup entry: "
                        f"key={key}, roto_id={roto.id}, "
                        f"risk_origin_name='{roto.risk_origin.name}', "
                        f"target_objective='{roto.target_objective}'"
                    )

                logger.info(
                    f"[Strategic Scenarios Import] RoTo lookup built with {len(roto_lookup)} entries"
                )
                logger.info(
                    f"[Strategic Scenarios Import] RoTo lookup keys: {list(roto_lookup.keys())}"
                )

                scenarios_from_arm = arm_data.get("strategic_scenarios", [])
                logger.info(
                    f"[Strategic Scenarios Import] Processing {len(scenarios_from_arm)} scenarios from ARM data"
                )

                for scenario_data in scenarios_from_arm:
                    try:
                        scenario_name = scenario_data["name"]
                        if not scenario_name:
                            logger.debug(
                                "[Strategic Scenarios Import] Skipping scenario with no name"
                            )
                            continue

                        logger.info(
                            f"[Strategic Scenarios Import] Processing scenario: '{scenario_name}'"
                        )

                        # Find the matching RoTo couple
                        # Normalize the risk origin name the same way we do when creating terminologies
                        risk_origin_raw = scenario_data.get("risk_origin", "")
                        risk_origin_name = risk_origin_raw.lower().replace(" ", "_")
                        target_objective = scenario_data.get(
                            "target_objective", ""
                        ).lower()

                        logger.info(
                            f"[Strategic Scenarios Import] Looking for RoTo match: "
                            f"risk_origin_raw='{risk_origin_raw}', "
                            f"risk_origin_normalized='{risk_origin_name}', "
                            f"target_objective='{target_objective}'"
                        )

                        # Attempt 1: Exact match with underscore normalization
                        lookup_key_1 = (risk_origin_name, target_objective)
                        roto = roto_lookup.get(lookup_key_1)
                        logger.info(
                            f"[Strategic Scenarios Import] Attempt 1 (underscore normalized): "
                            f"key={lookup_key_1}, found={roto is not None}"
                        )

                        if not roto:
                            # Attempt 2: Try without underscore normalization
                            risk_origin_name_alt = risk_origin_raw.lower()
                            lookup_key_2 = (risk_origin_name_alt, target_objective)
                            roto = roto_lookup.get(lookup_key_2)
                            logger.info(
                                f"[Strategic Scenarios Import] Attempt 2 (lowercase only): "
                                f"key={lookup_key_2}, found={roto is not None}"
                            )

                        if not roto:
                            # Attempt 3: Try partial matching on target objective
                            logger.info(
                                f"[Strategic Scenarios Import] Attempt 3 (partial match): "
                                f"searching for risk_origin containing '{risk_origin_name}' "
                                f"and target_objective containing '{target_objective}'"
                            )
                            for key, r in roto_lookup.items():
                                if (
                                    key[0] == risk_origin_name
                                    and target_objective in key[1]
                                ):
                                    roto = r
                                    logger.info(
                                        f"[Strategic Scenarios Import] Attempt 3: Partial match found with key={key}"
                                    )
                                    break

                        if not roto:
                            error_msg = f"Could not find RoTo couple for '{risk_origin_name}' - '{target_objective}'"
                            logger.warning(
                                f"[Strategic Scenarios Import] FAILED to match scenario '{scenario_name}': {error_msg}"
                            )
                            results["errors"].append(
                                {
                                    "strategic_scenario": scenario_name,
                                    "error": error_msg,
                                }
                            )
                            continue

                        logger.info(
                            f"[Strategic Scenarios Import] SUCCESS: Matched scenario '{scenario_name}' "
                            f"to RoTo id={roto.id} ('{roto.risk_origin.name}' - '{roto.target_objective}')"
                        )

                        # Check if a strategic scenario already exists for this study + name + ref_id
                        existing_scenario = StrategicScenario.objects.filter(
                            ebios_rm_study=study,
                            name__iexact=scenario_name,
                        ).first()

                        if existing_scenario:
                            match on_conflict:
                                case ConflictMode.SKIP:
                                    results["details"][
                                        "strategic_scenarios_skipped"
                                    ] += 1
                                    logger.info(
                                        f"[Strategic Scenarios Import] Skipped existing scenario: '{scenario_name}'"
                                    )
                                    continue
                                case ConflictMode.STOP:
                                    results["errors"].append(
                                        {
                                            "strategic_scenario": scenario_name,
                                            "error": "Strategic scenario already exists (conflict policy: stop)",
                                        }
                                    )
                                    stopped = True
                                    break
                                case ConflictMode.UPDATE:
                                    existing_scenario.ro_to_couple = roto
                                    existing_scenario.ref_id = scenario_data.get(
                                        "ref_id", existing_scenario.ref_id
                                    )
                                    existing_scenario.save()
                                    results["details"][
                                        "strategic_scenarios_updated"
                                    ] += 1
                                    logger.info(
                                        f"[Strategic Scenarios Import] Updated existing scenario: '{scenario_name}'"
                                    )
                                    # Still create attack path if missing
                                    attack_path_name = scenario_data.get(
                                        "attack_path_name", ""
                                    )
                                    if (
                                        attack_path_name
                                        and not AttackPath.objects.filter(
                                            ebios_rm_study=study,
                                            strategic_scenario=existing_scenario,
                                            name__iexact=attack_path_name,
                                        ).exists()
                                    ):
                                        AttackPath.objects.create(
                                            ebios_rm_study=study,
                                            strategic_scenario=existing_scenario,
                                            name=attack_path_name,
                                            ref_id=scenario_data.get(
                                                "attack_path_ref_id", ""
                                            ),
                                        )
                                        results["details"]["attack_paths_created"] += 1
                                    continue

                        # Create the strategic scenario
                        strategic_scenario = StrategicScenario.objects.create(
                            ebios_rm_study=study,
                            ro_to_couple=roto,
                            name=scenario_name,
                            ref_id=scenario_data.get("ref_id", ""),
                        )
                        results["details"]["strategic_scenarios_created"] += 1
                        logger.info(
                            f"[Strategic Scenarios Import] Created StrategicScenario id={strategic_scenario.id}, name='{scenario_name}'"
                        )

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
                            logger.info(
                                f"[Strategic Scenarios Import] Created AttackPath id={attack_path.id}, name='{attack_path_name}'"
                            )

                    except Exception as e:
                        logger.error(
                            f"[Strategic Scenarios Import] Exception processing scenario '{scenario_data.get('name', 'unknown')}': {str(e)}",
                            exc_info=True,
                        )
                        results["errors"].append(
                            {
                                "strategic_scenario": scenario_data.get(
                                    "name", "unknown"
                                ),
                                "error": str(e),
                            }
                        )

                # Mark workshop 3 step 3 (index 2) as done if we created or updated strategic scenarios
                scenario_count = (
                    results["details"]["strategic_scenarios_created"]
                    + results["details"]["strategic_scenarios_updated"]
                )
                if scenario_count > 0:
                    study.meta["workshops"][2]["steps"][2]["status"] = "done"
                    meta_updated = True
                    logger.info(
                        f"Created {results['details']['strategic_scenarios_created']} strategic scenarios, "
                        f"{results['details']['attack_paths_created']} attack paths"
                    )

                if stopped:
                    if meta_updated:
                        study.save()
                    return results

                # =========================================================
                # Step 8: Create Elementary Actions (Workshop 4)
                # =========================================================
                results["details"]["elementary_actions_created"] = 0
                results["details"]["elementary_actions_updated"] = 0
                results["details"]["elementary_actions_skipped"] = 0

                for ea_data in arm_data.get("elementary_actions", []):
                    try:
                        ea_name = ea_data["name"]
                        if not ea_name:
                            continue

                        # Check for existing elementary action
                        existing_ea = ElementaryAction.objects.filter(
                            name__iexact=ea_name,
                            folder=folder,
                        ).first()

                        if existing_ea:
                            match on_conflict:
                                case ConflictMode.SKIP:
                                    results["details"][
                                        "elementary_actions_skipped"
                                    ] += 1
                                    continue
                                case ConflictMode.STOP:
                                    results["errors"].append(
                                        {
                                            "elementary_action": ea_name,
                                            "error": "Elementary action already exists (conflict policy: stop)",
                                        }
                                    )
                                    stopped = True
                                    break
                                case ConflictMode.UPDATE:
                                    existing_ea.description = ea_data.get(
                                        "description", existing_ea.description
                                    )
                                    if ea_data.get("ref_id"):
                                        existing_ea.ref_id = ea_data["ref_id"]
                                    existing_ea.save()
                                    results["details"][
                                        "elementary_actions_updated"
                                    ] += 1
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

                # Mark workshop 4 step 1 (index 0) as done if we created or updated elementary actions
                ea_count = (
                    results["details"]["elementary_actions_created"]
                    + results["details"]["elementary_actions_updated"]
                )
                if ea_count > 0:
                    study.meta["workshops"][3]["steps"][0]["status"] = "done"
                    meta_updated = True
                    logger.info(
                        f"Created {results['details']['elementary_actions_created']} elementary actions"
                    )

                # Save the study if meta was updated
                if meta_updated:
                    study.save()

                if not stopped:
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

    def _process_ebios_rm_study_excel(
        self,
        request,
        excel_file: io.BytesIO,
        folder_id,
        matrix_id,
        on_conflict=ConflictMode.STOP,
    ):
        """
        Process EBIOS RM Study from the Excel export format.
        This format uses sheet prefixes like "1.1 Study", "1.3 Feared Events", etc.
        """
        from ebios_rm.models import OperatingMode

        results = {
            "successful": 0,
            "failed": 0,
            "errors": [],
            "details": {
                "study": None,
                "assets_created": 0,
                "assets_updated": 0,
                "assets_skipped": 0,
                "feared_events_created": 0,
                "feared_events_updated": 0,
                "feared_events_skipped": 0,
                "ro_to_couples_created": 0,
                "ro_to_couples_updated": 0,
                "ro_to_couples_skipped": 0,
                "stakeholders_created": 0,
                "stakeholders_updated": 0,
                "stakeholders_skipped": 0,
                "strategic_scenarios_created": 0,
                "strategic_scenarios_updated": 0,
                "strategic_scenarios_skipped": 0,
                "attack_paths_created": 0,
                "attack_paths_updated": 0,
                "attack_paths_skipped": 0,
                "elementary_actions_created": 0,
                "elementary_actions_updated": 0,
                "elementary_actions_skipped": 0,
                "operational_scenarios_created": 0,
                "operational_scenarios_updated": 0,
                "operational_scenarios_skipped": 0,
                "operating_modes_created": 0,
                "operating_modes_updated": 0,
                "operating_modes_skipped": 0,
            },
        }

        try:
            folder = Folder.objects.get(id=folder_id)
            risk_matrix = RiskMatrix.objects.get(id=matrix_id) if matrix_id else None

            # Build matrix mappings for looking up likelihood/gravity by display name
            matrix_mappings = {"probability": {}, "impact": {}}
            if risk_matrix:
                matrix_mappings = self._build_matrix_mappings(risk_matrix)

            # Parse the Excel file
            data = process_ebios_rm_excel(excel_file.read())
            study_data = data.get("study", {})

            # Create the study
            study_payload = {
                "name": study_data.get("name") or f"Imported Study",
                "description": study_data.get("description", ""),
                "ref_id": study_data.get("ref_id", ""),
                "version": study_data.get("version", ""),
                "folder": str(folder.id),
            }
            if risk_matrix:
                study_payload["risk_matrix"] = str(risk_matrix.id)

            serializer = EbiosRMStudyWriteSerializer(
                data=study_payload, context={"request": request}
            )

            if serializer.is_valid():
                study = serializer.save()
                results["details"]["study"] = str(study.id)
                stopped = False

                # Create assets and build name->id mapping
                asset_name_to_id = {}
                for asset_data in data.get("assets", []):
                    existing_asset = Asset.objects.filter(
                        name__iexact=asset_data["name"],
                        folder=folder,
                    ).first()

                    if existing_asset:
                        match on_conflict:
                            case ConflictMode.SKIP:
                                asset_name_to_id[existing_asset.name] = existing_asset
                                results["details"]["assets_skipped"] += 1
                                continue
                            case ConflictMode.STOP:
                                results["errors"].append(
                                    {
                                        "asset": asset_data["name"],
                                        "error": "Asset already exists (conflict policy: stop)",
                                    }
                                )
                                stopped = True
                                break
                            case ConflictMode.UPDATE:
                                if asset_data.get("description"):
                                    existing_asset.description = asset_data[
                                        "description"
                                    ]
                                if asset_data.get("ref_id"):
                                    existing_asset.ref_id = asset_data["ref_id"]
                                if asset_data.get("type"):
                                    existing_asset.type = asset_data["type"]
                                existing_asset.save()
                                asset_name_to_id[existing_asset.name] = existing_asset
                                results["details"]["assets_updated"] += 1
                                continue

                    asset, created = Asset.objects.get_or_create(
                        name=asset_data["name"],
                        folder=folder,
                        defaults={
                            "ref_id": asset_data.get("ref_id", ""),
                            "description": asset_data.get("description", ""),
                            "type": asset_data.get("type", ""),
                        },
                    )
                    asset_name_to_id[asset.name] = asset
                    if created:
                        results["details"]["assets_created"] += 1

                # Link assets to study
                study.assets.set(asset_name_to_id.values())

                if stopped:
                    return results

                # Create feared events and build name lookup
                feared_event_lookup = {}
                for fe_data in data.get("feared_events", []):
                    fe_name = fe_data["name"]
                    # Map gravity display name to value
                    gravity_val = self._map_risk_value(
                        fe_data.get("gravity", ""), matrix_mappings["impact"]
                    )

                    existing_fe = FearedEvent.objects.filter(
                        ebios_rm_study=study,
                        name__iexact=fe_name,
                    ).first()

                    if existing_fe:
                        feared_event_lookup[existing_fe.name] = existing_fe
                        match on_conflict:
                            case ConflictMode.SKIP:
                                results["details"]["feared_events_skipped"] += 1
                                continue
                            case ConflictMode.STOP:
                                results["errors"].append(
                                    {
                                        "feared_event": fe_name,
                                        "error": "Feared event already exists (conflict policy: stop)",
                                    }
                                )
                                stopped = True
                                break
                            case ConflictMode.UPDATE:
                                existing_fe.gravity = gravity_val
                                existing_fe.is_selected = fe_data.get(
                                    "is_selected", existing_fe.is_selected
                                )
                                existing_fe.justification = fe_data.get(
                                    "justification", existing_fe.justification
                                )
                                existing_fe.description = fe_data.get(
                                    "description", existing_fe.description
                                )
                                existing_fe.save()
                                for asset_name in fe_data.get("assets", []):
                                    if asset_name in asset_name_to_id:
                                        existing_fe.assets.add(
                                            asset_name_to_id[asset_name]
                                        )
                                results["details"]["feared_events_updated"] += 1
                                continue

                    fe = FearedEvent.objects.create(
                        ebios_rm_study=study,
                        name=fe_name,
                        ref_id=fe_data.get("ref_id", ""),
                        description=fe_data.get("description", ""),
                        gravity=gravity_val,
                        is_selected=fe_data.get("is_selected", False),
                        justification=fe_data.get("justification", ""),
                        folder=folder,
                    )
                    # Link assets to feared event
                    for asset_name in fe_data.get("assets", []):
                        if asset_name in asset_name_to_id:
                            fe.assets.add(asset_name_to_id[asset_name])
                    feared_event_lookup[fe.name] = fe
                    results["details"]["feared_events_created"] += 1

                if stopped:
                    return results

                # Create RO/TO couples
                roto_lookup = {}
                for roto_data in data.get("ro_to_couples", []):
                    risk_origin_name = roto_data.get("risk_origin", "")
                    # Find or create risk origin terminology
                    risk_origin = None
                    if risk_origin_name:
                        # Try to find existing terminology by name (case-insensitive)
                        risk_origin = Terminology.objects.filter(
                            field_path=Terminology.FieldPath.ROTO_RISK_ORIGIN,
                            name__iexact=risk_origin_name,
                        ).first()
                        if not risk_origin:
                            risk_origin = Terminology.objects.create(
                                name=risk_origin_name,
                                field_path=Terminology.FieldPath.ROTO_RISK_ORIGIN,
                                folder=Folder.get_root_folder(),
                                is_visible=True,
                            )

                    target_objective = roto_data.get("target_objective", "")

                    # Check for existing RoTo couple
                    existing_roto = (
                        RoTo.objects.filter(
                            ebios_rm_study=study,
                            risk_origin=risk_origin,
                            target_objective__iexact=target_objective,
                        ).first()
                        if risk_origin
                        else None
                    )

                    if existing_roto:
                        key = (
                            risk_origin_name.lower() if risk_origin_name else "",
                            target_objective.lower(),
                        )
                        roto_lookup[key] = existing_roto
                        match on_conflict:
                            case ConflictMode.SKIP:
                                results["details"]["ro_to_couples_skipped"] += 1
                                continue
                            case ConflictMode.STOP:
                                results["errors"].append(
                                    {
                                        "roto_couple": f"{risk_origin_name} - {target_objective}",
                                        "error": "RoTo couple already exists (conflict policy: stop)",
                                    }
                                )
                                stopped = True
                                break
                            case ConflictMode.UPDATE:
                                existing_roto.is_selected = roto_data.get(
                                    "is_selected", existing_roto.is_selected
                                )
                                existing_roto.justification = roto_data.get(
                                    "justification", existing_roto.justification
                                )
                                existing_roto.save()
                                for fe_name in roto_data.get("feared_events", []):
                                    if fe_name in feared_event_lookup:
                                        existing_roto.feared_events.add(
                                            feared_event_lookup[fe_name]
                                        )
                                results["details"]["ro_to_couples_updated"] += 1
                                continue

                    roto = RoTo.objects.create(
                        ebios_rm_study=study,
                        risk_origin=risk_origin,
                        target_objective=target_objective,
                        is_selected=roto_data.get("is_selected", False),
                        justification=roto_data.get("justification", ""),
                        folder=folder,
                    )
                    # Link feared events to RO/TO
                    for fe_name in roto_data.get("feared_events", []):
                        if fe_name in feared_event_lookup:
                            roto.feared_events.add(feared_event_lookup[fe_name])
                    # Build lookup key
                    key = (
                        risk_origin_name.lower() if risk_origin_name else "",
                        target_objective.lower(),
                    )
                    roto_lookup[key] = roto
                    results["details"]["ro_to_couples_created"] += 1

                if stopped:
                    return results

                # Create stakeholders
                stakeholder_lookup = {}
                for sh_data in data.get("stakeholders", []):
                    entity_name = sh_data.get("entity", "")
                    entity = None
                    if entity_name:
                        entity, _ = Entity.objects.get_or_create(
                            name=entity_name,
                            folder=folder,
                        )

                    category_name = sh_data.get("category", "")
                    category = None
                    if category_name:
                        # Try to find existing terminology by name (case-insensitive)
                        category = Terminology.objects.filter(
                            field_path=Terminology.FieldPath.ENTITY_RELATIONSHIP,
                            name__iexact=category_name,
                        ).first()
                        if not category:
                            category = Terminology.objects.create(
                                name=category_name,
                                field_path=Terminology.FieldPath.ENTITY_RELATIONSHIP,
                                folder=Folder.get_root_folder(),
                                is_visible=True,
                            )

                    # Check for existing stakeholder
                    existing_sh = None
                    if entity and category:
                        existing_sh = Stakeholder.objects.filter(
                            ebios_rm_study=study,
                            entity=entity,
                            category=category,
                        ).first()

                    if existing_sh:
                        stakeholder_lookup[str(existing_sh)] = existing_sh
                        match on_conflict:
                            case ConflictMode.SKIP:
                                results["details"]["stakeholders_skipped"] += 1
                                continue
                            case ConflictMode.STOP:
                                results["errors"].append(
                                    {
                                        "stakeholder": entity_name,
                                        "error": "Stakeholder already exists (conflict policy: stop)",
                                    }
                                )
                                stopped = True
                                break
                            case ConflictMode.UPDATE:
                                val = sh_data.get("current_dependency")
                                if val is not None:
                                    existing_sh.current_dependency = val
                                val = sh_data.get("current_penetration")
                                if val is not None:
                                    existing_sh.current_penetration = val
                                val = sh_data.get("current_maturity")
                                if val is not None:
                                    existing_sh.current_maturity = val
                                val = sh_data.get("current_trust")
                                if val is not None:
                                    existing_sh.current_trust = val
                                val = sh_data.get("residual_dependency")
                                if val is not None:
                                    existing_sh.residual_dependency = val
                                val = sh_data.get("residual_penetration")
                                if val is not None:
                                    existing_sh.residual_penetration = val
                                val = sh_data.get("residual_maturity")
                                if val is not None:
                                    existing_sh.residual_maturity = val
                                val = sh_data.get("residual_trust")
                                if val is not None:
                                    existing_sh.residual_trust = val
                                existing_sh.is_selected = sh_data.get(
                                    "is_selected", existing_sh.is_selected
                                )
                                existing_sh.justification = sh_data.get(
                                    "justification", existing_sh.justification
                                )
                                existing_sh.save()
                                results["details"]["stakeholders_updated"] += 1
                                continue

                    stakeholder = Stakeholder.objects.create(
                        ebios_rm_study=study,
                        entity=entity,
                        category=category,
                        current_dependency=sh_data.get("current_dependency") or 0,
                        current_penetration=sh_data.get("current_penetration") or 0,
                        current_maturity=sh_data.get("current_maturity") or 0,
                        current_trust=sh_data.get("current_trust") or 0,
                        residual_dependency=sh_data.get("residual_dependency") or 0,
                        residual_penetration=sh_data.get("residual_penetration") or 0,
                        residual_maturity=sh_data.get("residual_maturity") or 0,
                        residual_trust=sh_data.get("residual_trust") or 0,
                        is_selected=sh_data.get("is_selected", False),
                        justification=sh_data.get("justification", ""),
                        folder=folder,
                    )
                    stakeholder_lookup[str(stakeholder)] = stakeholder
                    results["details"]["stakeholders_created"] += 1

                if stopped:
                    return results

                # Create strategic scenarios
                scenario_lookup = {}
                for ss_data in data.get("strategic_scenarios", []):
                    ro_name = ss_data.get("risk_origin", "").lower()
                    to_name = ss_data.get("target_objective", "").lower()
                    roto = roto_lookup.get((ro_name, to_name))
                    ss_name = ss_data["name"]

                    existing_ss = StrategicScenario.objects.filter(
                        ebios_rm_study=study,
                        name__iexact=ss_name,
                    ).first()

                    if existing_ss:
                        scenario_lookup[existing_ss.name] = existing_ss
                        match on_conflict:
                            case ConflictMode.SKIP:
                                results["details"]["strategic_scenarios_skipped"] += 1
                                continue
                            case ConflictMode.STOP:
                                results["errors"].append(
                                    {
                                        "strategic_scenario": ss_name,
                                        "error": "Strategic scenario already exists (conflict policy: stop)",
                                    }
                                )
                                stopped = True
                                break
                            case ConflictMode.UPDATE:
                                if roto:
                                    existing_ss.ro_to_couple = roto
                                if ss_data.get("ref_id"):
                                    existing_ss.ref_id = ss_data["ref_id"]
                                if ss_data.get("description"):
                                    existing_ss.description = ss_data["description"]
                                existing_ss.save()
                                results["details"]["strategic_scenarios_updated"] += 1
                                continue

                    scenario = StrategicScenario.objects.create(
                        ebios_rm_study=study,
                        name=ss_name,
                        ref_id=ss_data.get("ref_id", ""),
                        description=ss_data.get("description", ""),
                        ro_to_couple=roto,
                        folder=folder,
                    )
                    scenario_lookup[scenario.name] = scenario
                    results["details"]["strategic_scenarios_created"] += 1

                if stopped:
                    return results

                # Create attack paths
                attack_path_lookup = {}
                for ap_data in data.get("attack_paths", []):
                    scenario_name = ap_data.get("strategic_scenario", "")
                    scenario = scenario_lookup.get(scenario_name)
                    ap_name = ap_data["name"]

                    existing_ap = AttackPath.objects.filter(
                        ebios_rm_study=study,
                        name__iexact=ap_name,
                    ).first()

                    if existing_ap:
                        attack_path_lookup[existing_ap.name] = existing_ap
                        match on_conflict:
                            case ConflictMode.SKIP:
                                results["details"]["attack_paths_skipped"] += 1
                                continue
                            case ConflictMode.STOP:
                                results["errors"].append(
                                    {
                                        "attack_path": ap_name,
                                        "error": "Attack path already exists (conflict policy: stop)",
                                    }
                                )
                                stopped = True
                                break
                            case ConflictMode.UPDATE:
                                if scenario:
                                    existing_ap.strategic_scenario = scenario
                                if ap_data.get("ref_id"):
                                    existing_ap.ref_id = ap_data["ref_id"]
                                if ap_data.get("description"):
                                    existing_ap.description = ap_data["description"]
                                existing_ap.is_selected = ap_data.get(
                                    "is_selected", existing_ap.is_selected
                                )
                                existing_ap.justification = ap_data.get(
                                    "justification", existing_ap.justification
                                )
                                existing_ap.save()
                                for sh_str in ap_data.get("stakeholders", []):
                                    if sh_str in stakeholder_lookup:
                                        existing_ap.stakeholders.add(
                                            stakeholder_lookup[sh_str]
                                        )
                                results["details"]["attack_paths_updated"] += 1
                                continue

                    attack_path = AttackPath.objects.create(
                        ebios_rm_study=study,
                        name=ap_name,
                        ref_id=ap_data.get("ref_id", ""),
                        description=ap_data.get("description", ""),
                        strategic_scenario=scenario,
                        is_selected=ap_data.get("is_selected", False),
                        justification=ap_data.get("justification", ""),
                        folder=folder,
                    )
                    # Link stakeholders
                    for sh_str in ap_data.get("stakeholders", []):
                        if sh_str in stakeholder_lookup:
                            attack_path.stakeholders.add(stakeholder_lookup[sh_str])
                    attack_path_lookup[attack_path.name] = attack_path
                    results["details"]["attack_paths_created"] += 1

                if stopped:
                    return results

                # Create elementary actions
                ea_lookup = {}
                for ea_data in data.get("elementary_actions", []):
                    ea_name = ea_data["name"]
                    # Map attack_stage display name back to value
                    attack_stage = 0  # Default to KNOW
                    stage_name = ea_data.get("attack_stage", "").lower()
                    if "initial" in stage_name or "enter" in stage_name:
                        attack_stage = 1
                    elif "discovery" in stage_name or "discover" in stage_name:
                        attack_stage = 2
                    elif "exploit" in stage_name:
                        attack_stage = 3

                    existing_ea = ElementaryAction.objects.filter(
                        name__iexact=ea_name,
                        folder=folder,
                    ).first()

                    if existing_ea:
                        ea_lookup[existing_ea.name] = existing_ea
                        match on_conflict:
                            case ConflictMode.SKIP:
                                results["details"]["elementary_actions_skipped"] += 1
                                continue
                            case ConflictMode.STOP:
                                results["errors"].append(
                                    {
                                        "elementary_action": ea_name,
                                        "error": "Elementary action already exists (conflict policy: stop)",
                                    }
                                )
                                stopped = True
                                break
                            case ConflictMode.UPDATE:
                                if ea_data.get("ref_id"):
                                    existing_ea.ref_id = ea_data["ref_id"]
                                if ea_data.get("description"):
                                    existing_ea.description = ea_data["description"]
                                existing_ea.attack_stage = attack_stage
                                existing_ea.save()
                                results["details"]["elementary_actions_updated"] += 1
                                continue

                    ea = ElementaryAction.objects.create(
                        name=ea_name,
                        ref_id=ea_data.get("ref_id", ""),
                        description=ea_data.get("description", ""),
                        attack_stage=attack_stage,
                        folder=folder,
                    )
                    ea_lookup[ea.name] = ea
                    results["details"]["elementary_actions_created"] += 1

                if stopped:
                    return results

                # Create operational scenarios
                # Note: OperationalScenario.name is a computed property from attack_path
                op_scenario_lookup = {}
                for os_data in data.get("operational_scenarios", []):
                    from ebios_rm.models import OperationalScenario

                    ap_name = os_data.get("attack_path", "")
                    attack_path = attack_path_lookup.get(ap_name)

                    if not attack_path:
                        continue

                    # Map likelihood display name to value
                    likelihood_val = self._map_risk_value(
                        os_data.get("likelihood", ""), matrix_mappings["probability"]
                    )

                    # Check for existing operational scenario by attack_path
                    existing_os = OperationalScenario.objects.filter(
                        ebios_rm_study=study,
                        attack_path=attack_path,
                    ).first()

                    if existing_os:
                        op_scenario_lookup[existing_os.name] = existing_os
                        match on_conflict:
                            case ConflictMode.SKIP:
                                results["details"]["operational_scenarios_skipped"] += 1
                                continue
                            case ConflictMode.STOP:
                                results["errors"].append(
                                    {
                                        "operational_scenario": ap_name,
                                        "error": "Operational scenario already exists (conflict policy: stop)",
                                    }
                                )
                                stopped = True
                                break
                            case ConflictMode.UPDATE:
                                existing_os.operating_modes_description = os_data.get(
                                    "operating_modes_description",
                                    existing_os.operating_modes_description,
                                )
                                existing_os.likelihood = likelihood_val
                                existing_os.is_selected = os_data.get(
                                    "is_selected", existing_os.is_selected
                                )
                                existing_os.justification = os_data.get(
                                    "justification", existing_os.justification
                                )
                                existing_os.save()
                                results["details"]["operational_scenarios_updated"] += 1
                                continue

                    op_scenario = OperationalScenario.objects.create(
                        ebios_rm_study=study,
                        attack_path=attack_path,
                        operating_modes_description=os_data.get(
                            "operating_modes_description", ""
                        ),
                        likelihood=likelihood_val,
                        is_selected=os_data.get("is_selected", False),
                        justification=os_data.get("justification", ""),
                        folder=folder,
                    )
                    op_scenario_lookup[op_scenario.name] = op_scenario
                    results["details"]["operational_scenarios_created"] += 1

                if stopped:
                    return results

                # Create operating modes
                for om_data in data.get("operating_modes", []):
                    os_name = om_data.get("operational_scenario", "")
                    op_scenario = op_scenario_lookup.get(os_name)
                    om_name = om_data["name"]

                    if op_scenario:
                        # Map likelihood display name to value
                        om_likelihood = self._map_risk_value(
                            om_data.get("likelihood", ""),
                            matrix_mappings["probability"],
                        )

                        # Check for existing operating mode
                        existing_om = OperatingMode.objects.filter(
                            name__iexact=om_name,
                            operational_scenario=op_scenario,
                        ).first()

                        if existing_om:
                            match on_conflict:
                                case ConflictMode.SKIP:
                                    results["details"]["operating_modes_skipped"] += 1
                                    continue
                                case ConflictMode.STOP:
                                    results["errors"].append(
                                        {
                                            "operating_mode": om_name,
                                            "error": "Operating mode already exists (conflict policy: stop)",
                                        }
                                    )
                                    stopped = True
                                    break
                                case ConflictMode.UPDATE:
                                    if om_data.get("ref_id"):
                                        existing_om.ref_id = om_data["ref_id"]
                                    if om_data.get("description"):
                                        existing_om.description = om_data["description"]
                                    existing_om.likelihood = om_likelihood
                                    existing_om.save()
                                    for ea_name in om_data.get(
                                        "elementary_actions", []
                                    ):
                                        if ea_name in ea_lookup:
                                            existing_om.elementary_actions.add(
                                                ea_lookup[ea_name]
                                            )
                                    results["details"]["operating_modes_updated"] += 1
                                    continue

                        om = OperatingMode.objects.create(
                            name=om_name,
                            ref_id=om_data.get("ref_id", ""),
                            description=om_data.get("description", ""),
                            operational_scenario=op_scenario,
                            likelihood=om_likelihood,
                            folder=folder,
                        )
                        # Link elementary actions
                        for ea_name in om_data.get("elementary_actions", []):
                            if ea_name in ea_lookup:
                                om.elementary_actions.add(ea_lookup[ea_name])
                        results["details"]["operating_modes_created"] += 1

                if not stopped:
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
            logger.error(
                f"Error processing EBIOS RM Study Excel: {str(e)}", exc_info=True
            )
            results["failed"] = 1
            results["errors"].append({"error": str(e)})

        return results
