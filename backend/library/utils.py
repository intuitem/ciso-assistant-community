import json
import time
import re

from .helpers import get_referential_translation
from typing import Union, Callable, Dict, Set, List, Tuple, Any, Type
from django.core.exceptions import SuspiciousFileOperation, ValidationError
from django.http import Http404
from django.db import models
from django.db.models import fields
from core.models import URN_REGEX

# interesting thread: https://stackoverflow.com/questions/27743711/can-i-speedup-yaml
from ciso_assistant import settings
from core.models import (
    Framework,
    RequirementMapping,
    RequirementMappingSet,
    StoredLibrary,
    LoadedLibrary,
    RequirementNode,
    RiskMatrix,
    ReferenceControl,
    Threat,
)
from django.db import transaction
from iam.models import Folder

from django.db.utils import OperationalError
import structlog

logger = structlog.get_logger(__name__)


def preview_library(framework: dict) -> Dict[str, list]:
    """
    Function to create temporary requirement nodes list
    Used to display requirements in tree view inside library detail view
    """
    preview = {}
    requirement_nodes_list = []
    if framework.get("requirement_nodes"):
        index = 0
        for requirement_node in framework["requirement_nodes"]:
            parent_urn = requirement_node.get("parent_urn")
            if parent_urn:
                parent_urn = parent_urn.lower()
            index += 1
            requirement_nodes_list.append(
                RequirementNode(
                    description=get_referential_translation(
                        requirement_node, "description"
                    ),
                    ref_id=requirement_node.get("ref_id"),
                    name=get_referential_translation(requirement_node, "name"),
                    urn=requirement_node["urn"].lower(),
                    parent_urn=parent_urn,
                    order_id=index,
                )
            )
    preview["requirement_nodes"] = requirement_nodes_list
    return preview


class RequirementNodeImporter:
    REQUIRED_FIELDS = {"urn"}

    def __init__(self, requirement_data: dict, index: int):
        self.requirement_data = requirement_data
        self.index = index

    def is_valid(self) -> Union[str, None]:
        if missing_fields := self.REQUIRED_FIELDS - set(self.requirement_data.keys()):
            return "Missing the following fields : {}".format(", ".join(missing_fields))

    def import_requirement_node(self, framework_object: Framework):
        parent_urn = self.requirement_data.get("parent_urn")
        if parent_urn:
            parent_urn = parent_urn.lower()
        requirement_node = RequirementNode.objects.create(
            # Should i just inherit the folder from Framework or this is useless ?
            folder=Folder.get_root_folder(),
            framework=framework_object,
            urn=self.requirement_data["urn"].lower(),
            parent_urn=parent_urn,
            assessable=self.requirement_data.get("assessable"),
            ref_id=self.requirement_data.get("ref_id"),
            annotation=self.requirement_data.get("annotation"),
            typical_evidence=self.requirement_data.get("typical_evidence"),
            provider=framework_object.provider,
            order_id=self.index,
            name=self.requirement_data.get("name"),
            description=self.requirement_data.get("description"),
            implementation_groups=self.requirement_data.get("implementation_groups"),
            locale=framework_object.locale,
            default_locale=framework_object.default_locale,
            translations=self.requirement_data.get("translations", {}),
            is_published=True,
            question=self.requirement_data.get("question"),
        )

        for threat in self.requirement_data.get("threats", []):
            requirement_node.threats.add(
                Threat.objects.get(urn=threat.lower())
            )  # URN are not case insensitive in the whole codebase yet, we should fix that and make sure URNs are always transformed into lowercase before being used.

        for reference_control in self.requirement_data.get("reference_controls", []):
            requirement_node.reference_controls.add(
                ReferenceControl.objects.get(urn=reference_control.lower())
            )


class RequirementMappingImporter:
    REQUIRED_FIELDS = {
        "target_requirement_urn",
        "relationship",
        "source_requirement_urn",
    }

    def __init__(self, data: dict):
        self.data = data

    def is_valid(self) -> bool:
        if missing_fields := self.REQUIRED_FIELDS - set(self.data.keys()):
            raise ValueError(
                "Missing the following fields : {}".format(", ".join(missing_fields))
            )
        return True

    def load(
        self,
        mapping_set: RequirementMappingSet,
    ):
        try:
            target_requirement = RequirementNode.objects.get(
                urn=self.data["target_requirement_urn"].lower(), default_locale=True
            )
        except RequirementNode.DoesNotExist:
            err_msg = f"ERROR: target requirement with URN {self.data['target_requirement_urn']} does not exist"
            print(err_msg)
            raise Http404(err_msg)
        try:
            source_requirement = RequirementNode.objects.get(
                urn=self.data["source_requirement_urn"].lower(), default_locale=True
            )
        except RequirementNode.DoesNotExist:
            err_msg = f"ERROR: source requirement with URN {self.data['source_requirement_urn']} does not exist"
            print(err_msg)
            raise Http404(err_msg)
        return RequirementMapping.objects.create(
            mapping_set=mapping_set,
            target_requirement=target_requirement,
            source_requirement=source_requirement,
            relationship=self.data["relationship"],
            annotation=self.data.get("annotation"),
            strength_of_relationship=self.data.get("strength_of_relationship"),
            rationale=self.data.get("rationale"),
        )


class RequirementMappingSetImporter:
    REQUIRED_FIELDS = {"urn", "name", "mapping"}
    OBJECT_FIELDS = {"requirement_mappings"}

    def __init__(self, data: dict):
        self.data = data
        self._requirement_mappings = []

    def init_requirement_mappings(
        self, requirement_mappings: List[dict]
    ) -> list[RequirementMappingImporter]:
        requirement_mapping_importers: list[RequirementMappingImporter] = []
        for mapping in requirement_mappings:
            importer = RequirementMappingImporter(data=mapping)
            try:
                if importer.is_valid():
                    requirement_mapping_importers.append(importer)
            except ValidationError:
                raise ValueError("Invalid requirement mapping data: {}".format(mapping))
        self._requirement_mappings = requirement_mapping_importers
        return requirement_mapping_importers

    def load(
        self,
        library_object: LoadedLibrary,
    ):
        self.init_requirement_mappings(self.data["requirement_mappings"])
        _target_framework = Framework.objects.get(
            urn=self.data["target_framework_urn"].lower(), default_locale=True
        )
        _source_framework = Framework.objects.get(
            urn=self.data["source_framework_urn"].lower(), default_locale=True
        )
        mapping_set = RequirementMappingSet.objects.create(
            name=self.data["name"],
            urn=self.data["urn"].lower(),
            target_framework=_target_framework,
            source_framework=_source_framework,
            library=library_object,
        )
        for mapping in self._requirement_mappings:
            mapping.load(mapping_set)
        return mapping_set

    def init(self):
        return None


# The couple (URN, locale) is unique. ===> Check it in the future
class FrameworkImporter:
    REQUIRED_FIELDS = {"ref_id", "urn"}
    OBJECT_FIELDS = {"requirement_nodes", "requirements"}

    def __init__(self, framework_data: dict):
        self.framework_data = framework_data
        self._requirement_nodes = []

    def init_requirement_nodes(self, requirement_nodes: List[dict]) -> Union[str, None]:
        requirement_node_importers = []
        import_errors = []
        for index, requirement_node_data in enumerate(requirement_nodes):
            requirement_node_importer = RequirementNodeImporter(
                requirement_node_data, index
            )
            requirement_node_importers.append(requirement_node_importer)
            if (
                requirement_node_error := requirement_node_importer.is_valid()
            ) is not None:
                import_errors.append((index, requirement_node_error))

        self._requirement_nodes = requirement_node_importers

        if import_errors:
            invalid_requirement_index, invalid_requirement_error = import_errors[0]
            return "[REQUIREMENT_ERROR] {} invalid requirement node{} detected, the {}{} requirement node has the following error : {}".format(
                len(import_errors),
                "s" if len(import_errors) > 1 else "",
                invalid_requirement_index + 1,
                {1: "st", 2: "nd", 3: "rd"}.get(invalid_requirement_index, "th"),
                invalid_requirement_error,
            )

    def is_empty(self):
        return (
            sum(
                len(self.framework_data.get(object_field, []))
                for object_field in self.OBJECT_FIELDS
            )
            == 0
        )

    def init(self) -> Union[str, None]:
        if missing_fields := self.REQUIRED_FIELDS - set(self.framework_data.keys()):
            return "Missing the following fields : {}".format(", ".join(missing_fields))

        detected_object_fields = self.OBJECT_FIELDS.union(self.framework_data.keys())

        if not detected_object_fields:
            return "The data must contain at least one of the following fields : {}".format(
                ", ".join(self.OBJECT_FIELDS)
            )

        if self.is_empty():
            return "No object has been detected among the object fields : {}".format(
                ", ".join(detected_object_fields)
            )

        if "requirement_nodes" in self.framework_data:
            requirement_node_data = self.framework_data["requirement_nodes"]
            if (
                requirement_node_import_error := self.init_requirement_nodes(
                    requirement_node_data
                )
            ) is not None:
                return requirement_node_import_error

    def import_framework(self, library_object: LoadedLibrary):
        min_score = self.framework_data.get("min_score", 0)
        max_score = self.framework_data.get("max_score", 100)

        if (
            min_score > max_score
            or min_score < 0
            or max_score < 0
            or min_score == max_score
        ):
            raise ValueError(
                "minimum score must be less than maximum score and equal or greater than 0."
            )

        framework_object = Framework.objects.create(
            folder=Folder.get_root_folder(),
            library=library_object,
            urn=self.framework_data["urn"].lower(),
            ref_id=self.framework_data["ref_id"],
            name=self.framework_data.get("name"),
            description=self.framework_data.get("description"),
            min_score=min_score,
            max_score=max_score,
            scores_definition=self.framework_data.get("scores_definition"),
            implementation_groups_definition=self.framework_data.get(
                "implementation_groups_definition"
            ),
            provider=library_object.provider,
            locale=library_object.locale,
            default_locale=library_object.default_locale,  # Change this in the future ?
            translations=self.framework_data.get("translations", {}),
            is_published=True,
        )
        for requirement_node in self._requirement_nodes:
            requirement_node.import_requirement_node(framework_object)


class ThreatImporter:
    REQUIRED_FIELDS = {"ref_id", "urn"}

    def __init__(self, threat_data: dict):
        self.threat_data = threat_data
        self._object = None

    def is_valid(self) -> Union[str, None]:
        if missing_fields := self.REQUIRED_FIELDS - set(self.threat_data.keys()):
            return "Missing the following fields : {}".format(", ".join(missing_fields))

    def import_threat(self, library_object: LoadedLibrary):
        Threat.objects.create(
            library=library_object,
            urn=self.threat_data["urn"].lower(),
            ref_id=self.threat_data["ref_id"],
            name=self.threat_data.get("name"),
            description=self.threat_data.get("description"),
            provider=library_object.provider,
            is_published=True,
            locale=library_object.locale,
            translations=self.threat_data.get("translations", {}),
            default_locale=library_object.default_locale,  # Change this in the future ?
        )


# The couple (URN, locale) is unique. ===> Check it in the future
class ReferenceControlImporter:
    REQUIRED_FIELDS = {"ref_id", "urn"}
    CATEGORIES = set(_category[0] for _category in ReferenceControl.CATEGORY)
    CSF_FUNCTIONS = set(
        _csf_function[0] for _csf_function in ReferenceControl.CSF_FUNCTION
    )

    def __init__(self, reference_control_data: dict):
        self.reference_control_data = reference_control_data

    def is_valid(self) -> Union[str, None]:
        if missing_fields := self.REQUIRED_FIELDS - set(
            self.reference_control_data.keys()
        ):
            return "Missing the following fields : {}".format(", ".join(missing_fields))

        if (category := self.reference_control_data.get("category")) is not None:
            if category not in ReferenceControlImporter.CATEGORIES:
                return "Invalid category '{}', the category must be among the following list : {}".format(
                    category, ", ".join(ReferenceControlImporter.CATEGORIES)
                )

        if (
            csf_function := self.reference_control_data.get("csf_function")
        ) is not None:
            if csf_function not in ReferenceControlImporter.CSF_FUNCTIONS:
                return "Invalid CSF function '{}', the function must be among the following list : {}".format(
                    csf_function, ", ".join(ReferenceControlImporter.CSF_FUNCTIONS)
                )

    def import_reference_control(self, library_object: LoadedLibrary):
        ReferenceControl.objects.create(
            library=library_object,
            urn=self.reference_control_data["urn"].lower(),
            ref_id=self.reference_control_data["ref_id"],
            name=self.reference_control_data.get("name"),
            description=self.reference_control_data.get("description"),
            provider=library_object.provider,
            typical_evidence=self.reference_control_data.get("typical_evidence"),
            category=self.reference_control_data.get("category"),
            csf_function=self.reference_control_data.get("csf_function"),
            is_published=True,
            locale=library_object.locale,
            translations=self.reference_control_data.get("translations", {}),
            default_locale=library_object.default_locale,  # Change this in the future ?
        )


# The couple (URN, locale) is unique. ===> Check this in the future
class RiskMatrixImporter:
    REQUIRED_FIELDS = {"ref_id", "urn", "json_definition"}
    MATRIX_FIELDS = {"probability", "impact", "risk", "grid", "strength_of_knowledge"}

    def __init__(self, risk_matrix_data):
        self.risk_matrix_data = risk_matrix_data

    @staticmethod
    def is_valid_matrix(json_definition: dict) -> Union[str, None]:
        return None  # Do not verify anything for now

    def is_valid(self) -> Union[str, None]:
        return None  # Do not verify anything for now

        # Create function to check if the "JSON definition" of the matrix is wrong or not, this function will be called within this is_valid function and return an error string is an error occured or return None or success exactly like this one.

        if missing_fields := self.REQUIRED_FIELDS - set(self.risk_matrix_data.keys()):
            return "Missing the following fields : {}".format(", ".join(missing_fields))

    def import_risk_matrix(self, library_object: LoadedLibrary):
        matrix_data = {
            key: value
            for key, value in self.risk_matrix_data.items()
            if key in self.MATRIX_FIELDS
        }
        matrix = RiskMatrix.objects.create(
            library=library_object,
            folder=Folder.get_root_folder(),
            name=self.risk_matrix_data.get("name"),
            description=self.risk_matrix_data.get("description"),
            urn=self.risk_matrix_data["urn"].lower(),
            provider=library_object.provider,
            ref_id=self.risk_matrix_data.get("ref_id"),
            json_definition=json.dumps(matrix_data),
            is_enabled=self.risk_matrix_data.get("is_enabled", True),
            locale=library_object.locale,
            default_locale=library_object.default_locale,  # Change this in the future ?
            translations=self.risk_matrix_data.get("translations", {}),
            is_published=True,
        )
        logger.info("Risk matrix created", matrix=matrix)
        return matrix


class LibraryImporter:
    # The word "import" must be replaced by "load" in all classes/methods/variables declared in this file.

    REQUIRED_FIELDS = {"ref_id", "urn", "locale", "objects", "version"}
    OBJECT_FIELDS = [
        "threats",
        "reference_controls",
        "risk_matrix",
        "framework",
        "requirement_mapping_set",
    ]

    def __init__(self, library: StoredLibrary):
        self._library = library
        self._framework_importer = None
        self._threats = []
        self._reference_controls = []
        self._risk_matrices = []
        self._requirement_mapping_set = None

    def init_threats(self, threats: List[dict]) -> Union[str, None]:
        threat_importers = []
        import_errors = []
        for index, threat_data in enumerate(threats):
            threat_importer = ThreatImporter(threat_data)
            threat_importers.append(threat_importer)
            if (threat_error := threat_importer.is_valid()) is not None:
                import_errors.append((index, threat_error))

        self._threats = threat_importers

        if import_errors:
            # We will have to think about error message internationalization later
            invalid_threat_index, invalid_threat_error = import_errors[0]
            return "[THREAT_ERROR] {} invalid threat{} detected, the {}{} threat has the following error : {}".format(
                len(import_errors),
                "s" if len(import_errors) > 1 else "",
                invalid_threat_index + 1,
                {1: "st", 2: "nd", 3: "rd"}.get(invalid_threat_index, "th"),
                invalid_threat_error,
            )

    def init_reference_controls(
        self, reference_controls: List[dict]
    ) -> Union[str, None]:
        reference_controls_importers = []
        import_errors = []
        for index, reference_controls_data in enumerate(reference_controls):
            reference_control_importer = ReferenceControlImporter(
                reference_controls_data
            )
            reference_controls_importers.append(reference_control_importer)
            if (
                reference_control_error := reference_control_importer.is_valid()
            ) is not None:
                import_errors.append((index, reference_control_error))

        self._reference_controls = reference_controls_importers

        if import_errors:
            (
                invalid_reference_control_index,
                invalid_reference_control_error,
            ) = import_errors[0]
            return "[REFERENCE_CONTROL_ERROR] {} invalid reference control{} detected, the {}{} reference control has the following error : {}".format(
                len(import_errors),
                "s" if len(import_errors) > 1 else "",
                invalid_reference_control_index + 1,
                {1: "st", 2: "nd", 3: "rd"}.get(invalid_reference_control_index, "th"),
                invalid_reference_control_error,
            )

    def init_risk_matrices(self, risk_matrices: List[dict]) -> Union[str, None]:
        risk_matrix_importers = []
        import_errors = []
        for index, risk_matrix_data in enumerate(risk_matrices):
            risk_matrix_importer = RiskMatrixImporter(risk_matrix_data)
            risk_matrix_importers.append(risk_matrix_importer)
            if (risk_matrix_error := risk_matrix_importer.is_valid()) is not None:
                import_errors.append((index, risk_matrix_error))

        self._risk_matrices = risk_matrix_importers

        if import_errors:
            invalid_risk_matrix_index, invalid_risk_matrix_error = import_errors[0]
            return "[RISK_MATRIX_ERROR] {} invalid matri{} detected, the {}{} risk matrix has the following error : {}".format(
                len(import_errors),
                "ces" if len(import_errors) > 1 else "x",
                invalid_risk_matrix_index + 1,
                {1: "st", 2: "nd", 3: "rd"}.get(invalid_risk_matrix_index, "th"),
                invalid_risk_matrix_error,
            )

    def init_requirement_mapping_set(self, data: dict):
        self._requirement_mapping_set = RequirementMappingSetImporter(data)
        return self._requirement_mapping_set.init()

    def init_framework(self, framework_data: dict) -> Union[str, None]:
        self._framework_importer = FrameworkImporter(framework_data)
        return self._framework_importer.init()

    def init(self) -> Union[str, None]:
        """missing_fields = self.REQUIRED_FIELDS - set(self._library_data.keys())
        if missing_fields:
            return "The following fields are missing in the library: {}".format(
                ", ".join(missing_fields)
            )"""

        library_objects = json.loads(self._library.content)

        if not any(
            object_field in library_objects for object_field in self.OBJECT_FIELDS
        ):
            return "The library 'objects' field data must contain at least one of the following fields : {}".format(
                ", ".join(self.OBJECT_FIELDS)
            )

        if "framework" in library_objects:
            framework_data = library_objects["framework"]
            if (
                framework_import_error := self.init_framework(framework_data)
            ) is not None:
                print("framework_import_error", framework_import_error)
                return framework_import_error

        if "requirement_mapping_set" in library_objects:
            requirement_mapping_set_data = library_objects["requirement_mapping_set"]
            self.init_requirement_mapping_set(requirement_mapping_set_data)

        if "threats" in library_objects:
            threat_data = library_objects["threats"]
            if (threat_import_error := self.init_threats(threat_data)) is not None:
                print("threat errors", threat_import_error)
                return threat_import_error

        if "risk_matrix" in library_objects:
            risk_matrix_data = library_objects["risk_matrix"]
            if (
                risk_matrix_import_error := self.init_risk_matrices(risk_matrix_data)
            ) is not None:
                return risk_matrix_import_error

        if "reference_controls" in library_objects:
            reference_control_data = library_objects["reference_controls"]
            if (
                reference_control_import_error := self.init_reference_controls(
                    reference_control_data
                )
            ) is not None:
                return reference_control_import_error

    def check_and_import_dependencies(self):
        """Check and import library dependencies."""
        if not self._library.dependencies:
            return None
        for dependency_urn in self._library.dependencies:
            if not LoadedLibrary.objects.filter(urn=dependency_urn).exists():
                dependency = StoredLibrary.objects.get(
                    urn=dependency_urn
                )  # We only fetch by URN without thinking about what locale, that may be a problem in the future.
                error_msg = dependency.load()
                if error_msg is not None:
                    return error_msg

    def create_or_update_library(self):
        """Create or update the library object."""
        _urn = self._library.urn
        _locale = self._library.locale
        _default_locale = not LoadedLibrary.objects.filter(urn=_urn).exists()

        logger.info(
            "Loading library",
            urn=_urn,
            locale=_locale,
            default_locale=_default_locale,
            library=self._library,
        )
        library_object, _created = LoadedLibrary.objects.update_or_create(
            defaults={
                "ref_id": self._library.ref_id,
                "name": self._library.name,
                "description": self._library.description,
                "urn": _urn,
                "locale": _locale,
                "default_locale": _default_locale,
                "version": self._library.version,
                "provider": self._library.provider,
                "packager": self._library.packager,
                "copyright": self._library.copyright,
                "folder": Folder.get_root_folder(),  # TODO: make this configurable,
                "is_published": True,
                "builtin": self._library.builtin,
                "objects_meta": self._library.objects_meta,
                "translations": self._library.translations,
            },
            urn=_urn,
            locale=_locale,
        )
        return library_object

    def import_objects(self, library_object):
        """Import library objects."""

        for threat in self._threats:
            threat.import_threat(library_object)

        for reference_control in self._reference_controls:
            reference_control.import_reference_control(library_object)

        for risk_matrix in self._risk_matrices:
            risk_matrix.import_risk_matrix(library_object)

        if self._framework_importer is not None:
            self._framework_importer.import_framework(library_object)

        if self._requirement_mapping_set is not None:
            self._requirement_mapping_set.load(library_object)

    @transaction.atomic
    def _import_library(self):
        library_object = self.create_or_update_library()
        self.import_objects(library_object)
        if dependencies := self._library.dependencies:
            library_object.dependencies.set(
                LoadedLibrary.objects.filter(urn__in=dependencies)
            )

    def import_library(self) -> Union[str, None]:
        """Main method to import a library."""
        if (error_message := self.init()) is not None:
            return error_message  # This error check should be done when storing the Library but no after.
        print("::: Getting Dependencies :::")
        error_msg = self.check_and_import_dependencies()
        print("::: Dependencies are ok :::")
        if error_msg is not None:
            return error_msg

        for _ in range(10):
            try:
                self._import_library()
                break
            except OperationalError as e:
                if e.args and e.args[0] == "database is locked":
                    time.sleep(1)
                else:
                    raise e
            except Exception as e:
                print("Library import error", e)
                logger.error("Library import error", error=e, library=self._library)
                raise e


def merge_location(
    error: Tuple[str, dict, List[str]], location: List[str]
) -> Tuple[str, dict, List[str]]:
    for field in reversed(location):
        error[2].insert(0, field)
    return error


def get_object_ident(obj: dict, index: int) -> str:
    for field in ["urn", "name"]:
        if field in obj:
            return f'{field}="{obj[field]}"'
    return str(index)


# This function must be used to avoid overly long output when passing a value representation in the error message.
def repr_value(value: Any) -> str:
    """This function will raise an exception if the __repr__ method is not implemented for the value"""
    stringified_value = repr(value)
    if len(stringified_value) > 100:
        stringified_value = f"{stringified_value[:100]}..."
    return stringified_value


class LibraryFormatUtils:
    @staticmethod
    def generic_check_from_model_field(
        value: Any, model: Type[models.Model], field_name: str
    ) -> Union[None, Tuple[str, dict]]:
        """
        This function only supports checking CharField, TextField and IntegerField.
        The shape of a JsonField is too complex for a simple helper function like it to verify its validity.
        """
        deferred_attribute = getattr(model, field_name)
        field = deferred_attribute.field

        if value is None:
            if field.null or field.default is not fields.NOT_PROVIDED:
                return None
            return ("libraryErrorNonNull", {})

        if isinstance(field, (fields.CharField, fields.TextField)):
            if not isinstance(value, str):
                return (
                    "libraryErrorBadType",
                    {
                        "value": repr_value(value),
                        "type": type(value).__name__,
                        "expected_type": "str",
                    },
                )

            if not value:
                if field.blank:
                    return None
                return ("libraryErrorNonBlank", {})

            if field.choices is not None:
                choices = field.choices
                if not isinstance(choices[0], str):
                    choices = [choice[0] for choice in choices]
                if value in choices:
                    return None
                return (
                    "libraryErrorBadChoice",
                    {"value": repr_value(value), "choices": repr_value(choices)},
                )

            max_length = field.max_length
            if max_length and len(value) > max_length:
                return (
                    "libraryErrorTooLong",
                    {
                        "value": repr_value(value),
                        "length": repr_value(len(value)),
                        "max_length": repr_value(max_length),
                    },
                )

        elif isinstance(field, fields.IntegerField):
            if not isinstance(value, int):
                return (
                    "libraryErrorBadType",
                    {
                        "value": repr_value(value),
                        "type": type(value).__name__,
                        "expected_type": "int",
                    },
                )

        elif isinstance(field, fields.BooleanField):
            if not isinstance(value, bool):
                return (
                    "libraryErrorBadType",
                    {
                        "value": repr_value(value),
                        "type": type(value).__name__,
                        "expected_type": "bool",
                    },
                )

    @staticmethod
    def check_version(version: int, obj=None) -> Union[None, Tuple[str, dict]]:
        minimum_version = 1
        if obj and (urn := obj.get("urn")):
            try:
                current_library = StoredLibrary.objects.get(urn=urn)
                minimum_version = str(current_library.version + 1)
            except:
                pass

        if version < minimum_version:
            return (
                "libraryErrorOutOfRange",
                {
                    "value": repr_value(version),
                    "minimum": str(minimum_version),
                    "maximum": "infinity",
                },
            )

    @staticmethod
    def check_urn(urn: str, obj=None) -> Union[None, Tuple[str, dict]]:
        if not re.match(URN_REGEX, urn):
            return (
                "libraryErrorInvalidString",
                {"regex_pattern": URN_REGEX, "urn": repr_value(urn)},
            )

    @staticmethod
    def check_locale(locale: str, obj=None) -> Union[None, Tuple[str, dict]]:
        available_locales = [lang[0] for lang in settings.LANGUAGES]
        if locale not in available_locales:
            return (
                "libraryErrorBadChoice",
                {
                    "value": repr_value(locale),
                    "choices": "[{}]".format(", ".join(available_locales)),
                },
            )

    @staticmethod
    def check_dependencies(dependencies: List[Any]) -> Union[None, Tuple[str, dict]]:
        for urn in dependencies:
            if not isinstance(urn, str):
                return (
                    "libraryErrorBadType",
                    {
                        "value": repr_value(urn),
                        "type": type(urn).__name__,
                        "expected_type": "str",
                    },
                )
            # We do this because there is no generic checks used for the dependencies field
            LibraryFormatUtils.generic_check_from_model_field(urn, LoadedLibrary, "urn")

            # We do not verify if the URN correspond to any loaded library because the dependencies are lazy loaded.
            if (result := LibraryFormatUtils.check_urn(urn)) is not None:
                return result

    @staticmethod
    def check_translations(
        translations: Dict[str, Dict[str, str]], obj: dict
    ) -> Union[None, Tuple[str, dict]]:
        for locale, translation_dict in translations.items():
            if error := LibraryFormatUtils.check_locale(locale):
                return error

            for translation_text in translation_dict.values():
                # It would be better to also display the "translation key" to the client, but it's would require making the signature of this function more complex and the value is already quite good to easy locate the non-string value.
                if not isinstance(translation_text, str):
                    return (
                        "libraryErrorBadType",
                        {
                            "value": repr_value(translation_text),
                            "type": type(translation_text).__name__,
                            "expected_type": "str",
                        },
                    )

            translated_fields = set(translation_dict)
            obj_fields = set(obj)
            if diff := translated_fields - obj_fields:
                return (
                    "libraryErrorUnknownFieldTranslation",
                    {
                        "fields": repr_value(sorted(obj_fields)),
                        "bad_fields": repr_value(sorted(diff)),
                    },
                )

    @staticmethod
    def check_grid(
        grid: Any, risk_ids: Set[int], probabilities: List[dict], impacts: List[dict]
    ) -> Union[None, Tuple[str, dict]]:
        if not isinstance(grid, list):
            return (
                "libraryErrorBadType",
                {
                    "value": repr_value(grid),
                    "type": type(grid).__name__,
                    "expected_type": "list",
                },
            )

        for row in grid:
            if not isinstance(row, list):
                return (
                    "libraryErrorBadType",
                    {
                        "value": repr_value(row),
                        "type": type(row).__name__,
                        "expected_type": "list",
                    },
                )
            for risk_id in row:
                if not isinstance(risk_id, int):
                    return (
                        "libraryErrorBadType",
                        {
                            "value": repr_value(risk_id),
                            "type": type(risk_id).__name__,
                            "expected_type": "int",
                        },
                    )
                if risk_id not in risk_ids:
                    return (
                        "libraryErrorInvalidMatrix",
                        {
                            "reason": "libraryErrorUndefinedRiskId",
                            # The "description" field must disappear if we ever translate the error messages.
                            "description": f"One of the risk have the ID {risk_id} but this ID doesn't exist among the existing risk IDs: {sorted(risk_ids)}.",
                        },
                    )

        if len(grid) != len(probabilities):
            return (
                "libraryErrorInvalidMatrix",
                {
                    "reason": "invalidProbabilityNumber",
                    # The "description" field must disappear if we ever translate the error messages.
                    "description": f"The number of defined probabilities ({len(probabilities)}) must be equal to the number of rows ({len(grid)}) in the grid matrix.",
                },
            )

        invalid_row_lengths = []
        valid_row_length = len(impacts)
        for index, row in enumerate(grid):
            if len(row) != valid_row_length:
                invalid_row_lengths.append((index, len(row)))

        if invalid_row_lengths:
            invalid_rows_string = ", ".join(
                f"row[{index}].length={length}" for index, length in invalid_row_lengths
            )
            return (
                "libraryErrorInvalidMatrix",
                {
                    "reason": "invalidImpactNumber",
                    # The "description" field must disappear if we ever translate the error messages.
                    "description": f"Some rows have an invalid length (expected_length={valid_row_length}) invalid rows: {invalid_rows_string}",
                },
            )

    @staticmethod
    def check_risk_matrix(
        risk_matrix: Any, location: List[str]
    ) -> Union[None, Tuple[str, dict, List[str]]]:
        if error := RiskMatrixChecker.check(risk_matrix):
            return merge_location(error, location)

        probabilities = risk_matrix["probability"]
        impacts = risk_matrix["impact"]
        risks = risk_matrix["risk"]
        grid = risk_matrix["grid"]

        for field_name, matrix_field_data in [
            ("probability", probabilities),
            ("impact", impacts),
            ("risk", risks),
        ]:
            for index, obj in enumerate(matrix_field_data):
                ident = get_object_ident(obj, index)
                if not isinstance(obj, dict):
                    return (
                        "libraryErrorBadType",
                        {
                            "value": repr_value(obj),
                            "type": type(obj).__name__,
                            "expected_type": "dict",
                        },
                        [*location, field_name],
                    )
                if (error := RiskMatrixProbabilityChecker.check(obj)) is not None:
                    return merge_location(error, [*location, field_name, ident])

        if all("id" in risk for risk in risks):
            risk_ids = {risk.get["id"] for risk in risks}
        elif not any("id" in risk for risk in risks):
            risk_ids = set(range(len(risks)))
        else:
            # If some risks have id but others don't this is invalid.
            return (
                "libraryErrorInvalidMatrix",
                {
                    "reason": "inconsistentRiskIds",
                    # The "description" field must disappear if we ever translate the error messages.
                    "description": "You can't have risks with an explicit id while other risks don't.",
                },
                [*location, "risk", "...id"],
            )  # "The ..." notation is cryptic but it makes it easier to understand the origin of the error.

        if (
            error := LibraryFormatUtils.check_grid(
                grid, risk_ids, probabilities, impacts
            )
        ) is not None:
            return (*error, [*location, "grid"])

    @staticmethod
    def check_str(
        value: Any,
        null: bool = False,
        blank: bool = False,
        max_length: Union[int, None] = None,
        regex_pattern: Union[str, None] = None,
        obj=None,
    ) -> Union[None, Tuple[str, dict]]:
        if null and value is None:
            return None

        if not isinstance(value, str):
            return (
                "libraryErrorBadType",
                {
                    "value": repr_value(value),
                    "type": type(value).__name__,
                    "expected_type": "str",
                },
            )

        if blank and not value:
            return None

        if max_length is not None and len(value) > max_length:
            return (
                "libraryErrorTooLong",
                {
                    "value": repr_value(value),
                    "length": repr_value(len(value)),
                    "max_length": repr_value(max_length),
                },
            )

        if regex_pattern is not None:
            if not re.fullmatch(regex_pattern, value):
                return (
                    "libraryErrorInvalidString",
                    {"regex_pattern": regex_pattern, "string": repr_value(value)},
                )

    @staticmethod
    def check_int(
        value: Any,
        null: bool = False,
        min_value: Union[int, None] = None,
        max_value: Union[int, None] = None,
        obj=None,
    ) -> Union[None, Tuple[str, dict]]:
        if null and value is None:
            return None

        if not isinstance(value, int):
            return (
                "libraryErrorBadType",
                {
                    "value": repr_value(value),
                    "type": type(value).__name__,
                    "expected_type": "int",
                },
            )

        if min_value is not None and value < min_value:
            return (
                "libraryErrorOutOfRange",
                {
                    "value": repr_value(value),
                    "minimum": repr_value(min_value),
                    "maximum": "infinity"
                    if max_value is None
                    else repr_value(max_value),
                },
            )

        if max_value is not None and value > max_value:
            return (
                "libraryErrorOutOfRange",
                {
                    "value": repr_value(value),
                    "minimum": "-infinity"
                    if min_value is None
                    else repr_value(min_value),
                    "maximum": repr_value(max_value),
                },
            )

    @staticmethod
    def check_bool(value: Any, obj=None) -> Union[None, Tuple[str, dict]]:
        if not isinstance(value, bool):
            return (
                "libraryErrorBadType",
                {
                    "value": repr_value(value),
                    "type": type(value).__name__,
                    "expected_type": "bool",
                },
            )

    @staticmethod
    def make_str_checker(**kwargs) -> Callable[[Any], Union[None, Tuple[str, dict]]]:
        return lambda value, **kw: LibraryFormatUtils.check_str(value, **kw, **kwargs)

    @staticmethod
    def make_int_checker(**kwargs) -> Callable[[Any], Union[None, Tuple[str, dict]]]:
        return lambda value, **kw: LibraryFormatUtils.check_int(value, **kw, **kwargs)

    @staticmethod
    def make_bool_checker() -> Callable[[Any], Union[None, Tuple[str, dict]]]:
        return lambda value, **kw: LibraryFormatUtils.check_bool(value, **kw)


class ObjectFieldsChecker:
    # A set of fields that must be present in the object
    REQUIRED_FIELDS: Set[str]
    # The set of all the valid fields for an object
    ALL_FIELDS: Set[str]
    # The list of fields on which the generic check will be used
    # The generic checks the validity of the value by using the information provided by the field defined in the model.
    # Example (name = models.CharField(max_length=200)) will check if the name if the name is a non blank and non null string with a length <= to 200.
    # The validators are not checked in the the generic check
    GENERIC_CHECKED_FIELDS: List[str]  # Dict[str, bool] # This should be a list right ?
    # A dictionary where a field can be linked to an extra check required when the generic check isn't enough to verify the validity of the value in this field.
    EXTRA_CHECKS: Dict[str, Callable[[dict], Union[None, Tuple[str, dict]]]]
    # The model used as the source for field information in the generic checker.
    MODEL: models.Model
    # Reperesent the root location of the error e.g. ["threats"], ["threats", "translations"]

    def __init_subclass__(cls):
        """This function verifies that all static attributes requred to make this class work as expected are defined.
        It also checks some mandatory subset relations between different attributes."""
        REQUIRED_STATIC_ATTRS = set(ObjectFieldsChecker.__annotations__)
        missing_fields = REQUIRED_STATIC_ATTRS - set(dir(cls))
        if missing_fields:
            raise AttributeError(
                f"Some fields are missing in the ObjectFieldsChecker subclass '{cls}'. Missing fields: {missing_fields}"
            )

        if diff := cls.REQUIRED_FIELDS - cls.ALL_FIELDS:
            raise ValueError(
                f"The REQUIRED_FIELDS attribute must be a subset of the ALL_FIELDS attribute for the ObjectFieldsChecker subclass '{cls}' invalid values: {diff}"
            )

        if diff := set(cls.GENERIC_CHECKED_FIELDS) - cls.ALL_FIELDS:
            raise ValueError(
                f"The GENERIC_CHECKED_FIELDS attribute must be a subset of the ALL_FIELDS attribute for the ObjectFieldsChecker subclass '{cls}' invalid values: {diff}"
            )

        if diff := (set(cls.EXTRA_CHECKS) - cls.ALL_FIELDS):
            raise ValueError(
                f"The EXTRA_CHECKS attribute dictionary keys must form a subset of the ALL_FIELDS attribute for the ObjectFieldsChecker subclass '{cls}' invalid keys: {diff}"
            )

    @classmethod
    def check(cls, obj: dict, strict=True) -> Union[None, Tuple[str, dict, List[str]]]:
        """
        Check that all fields are valid in an object.

        Parameters
        ----------
        obj : dict
            The object to check.
        strict : bool
            If True this function will return an error if an unknown field is present in the keys of the object.

        Returns
        -------
        Union[None, Tuple[str, dict, List[str]]]
            The result of the computation, which may be:
            - None: If the check doesn't detect any error.
            - Tuple[str, dict, List[str]]: The error data composed of:
                - error_name : str
                    The name of the error (a camel case error name starting with "libaryError").
                - error_data: Dict[str, str]
                    A dictionary giving the necessary details about the error.
                - error_traceback: List[str]
                    A list of string indicating the precise location of the error within the whole library object contained in the yaml file.

        Notes
        -----
        This function starts by checking for missing fields, it will check that all fields defined in cls.REQUIRED_FIELDS are present in the object.
        If strict is set to True it will check if any field not defined in cls.ALL_FIELDS is present, if so it will return an error.
        It will then check if the values of the fields are correct based on the fields declared in cls.GENERIC_CHECKED_FIELDS are valid based on the fields definition in the cls.MODEL Django model (note that validators in the Django field definition will not be check by these generic checks).
        And then the fields present in the object and declared as keys in cls.EXTRA_CHECKS will be checked by using their own custom checker function as defined in the values of cls.EXTRA_CHECKS.
        """
        object_fields = set(obj)
        missing_fields = cls.REQUIRED_FIELDS - object_fields
        if missing_fields:
            return (
                "libraryErrorMissingField",
                {"fields": repr_value(sorted(missing_fields))},
                [],
            )

        if strict:
            invalid_fields = object_fields - cls.ALL_FIELDS
            if invalid_fields:
                return (
                    "libraryErrorInvalidFields",
                    {"fields": repr_value(sorted(invalid_fields))},
                    [],
                )

        for field, value in obj.items():
            if field in cls.GENERIC_CHECKED_FIELDS:
                value = obj[field]
                if (
                    error := LibraryFormatUtils.generic_check_from_model_field(
                        value, cls.MODEL, field
                    )
                ) is not None:
                    return (*error, [field])

            if field in cls.EXTRA_CHECKS:
                extra_check = cls.EXTRA_CHECKS[field]
                if error := extra_check(value, obj=obj):
                    return (*error, [field])


class ThreatFieldsChecker(ObjectFieldsChecker):
    REQUIRED_FIELDS = {"urn", "ref_id", "name"}
    # Should we accept the "annotation" field for threat ?
    # It exists in the Threat model after all.
    ALL_FIELDS = {"urn", "ref_id", "name", "description", "translations"}
    GENERIC_CHECKED_FIELDS = ["urn", "ref_id", "name", "description"]
    EXTRA_CHECKS = {
        "urn": LibraryFormatUtils.check_urn,
        "translations": LibraryFormatUtils.check_translations,
    }
    MODEL = Threat
    DEFAULT_LOCATION = ["threats"]


class ReferenceControlChecker(ObjectFieldsChecker):
    """
    urn: urn:intuitem:risk:reference_control:asf-baseline-v2:asf-rec-12
    ref_id: ASF-REC-12
    category: policy
    description: Data Retention and Destruction Policy
    csf_function: detect
    annotation: 'PDPDPPDPD'
    """

    REQUIRED_FIELDS = {"urn", "ref_id", "name"}
    ALL_FIELDS = {
        "urn",
        "ref_id",
        "name",
        "description",
        "translations",
        "annotation",
        "category",
        "csf_function",
    }
    # We must test that the choice fields like category and csf_function are correctly checked by the generic checker.
    GENERIC_CHECKED_FIELDS = [
        "urn",
        "ref_id",
        "name",
        "description",
        "annotation",
        "category",
        "csf_function",
    ]
    EXTRA_CHECKS = {
        "urn": LibraryFormatUtils.check_urn,
        "translations": LibraryFormatUtils.check_translations,
    }
    MODEL = ReferenceControl


class RiskMatrixChecker(ObjectFieldsChecker):
    REQUIRED_FIELDS = {"urn", "ref_id", "name", "impact", "probability", "risk", "grid"}
    # Should we accept the "annotation" field for threat ?
    # It exists in the RiskMatrix model after all.
    ALL_FIELDS = {
        "urn",
        "ref_id",
        "name",
        "description",
        "translations",
        "impact",
        "probability",
        "risk",
        "grid",
    }
    # "strength_of_knowledge" is in MATRIX_FIELDS, how is it used though ?
    # Should i put it in the verifier, i really think so
    GENERIC_CHECKED_FIELDS = ["urn", "ref_id", "name", "description"]
    EXTRA_CHECKS = {
        "urn": LibraryFormatUtils.check_urn,
        "translations": LibraryFormatUtils.check_translations,
    }
    MODEL = RiskMatrix


class RiskMatrixProbabilityChecker(ObjectFieldsChecker):
    REQUIRED_FIELDS = {"abbreviation", "name", "description"}
    ALL_FIELDS = {
        "abbreviation",
        "name",
        "description",
        "hexcolor",
        "translations",
        "id",
    }
    GENERIC_CHECKED_FIELDS = []  # This must be an empty list if MODEL is None
    EXTRA_CHECKS = {
        "abbreviation": LibraryFormatUtils.make_str_checker(),
        "name": LibraryFormatUtils.make_str_checker(),
        "description": LibraryFormatUtils.make_str_checker(),
        "hexcolor": LibraryFormatUtils.make_str_checker(
            regex_pattern=r"#[0-9A-Fa-f]{6}"
        ),
        "translations": LibraryFormatUtils.check_translations,
        "id": LibraryFormatUtils.make_int_checker(min_value=0),
    }
    MODEL = None


class FrameworkChecker(ObjectFieldsChecker):
    REQUIRED_FIELDS = {"urn", "ref_id", "name"}
    ALL_FIELDS = {
        "urn",
        "ref_id",
        "name",
        "description",
        "translations",
        "requirement_nodes",
    }
    GENERIC_CHECKED_FIELDS = ["urn", "ref_id", "name", "description"]
    EXTRA_CHECKS = {
        "urn": LibraryFormatUtils.check_urn,
        "translations": LibraryFormatUtils.check_translations,
    }
    MODEL = Framework


class RequirementNodeChecker(ObjectFieldsChecker):
    REQUIRED_FIELDS = {"urn", "ref_id", "name"}
    # Remove the "depth" field later on (since it's useless)
    ALL_FIELDS = {
        "urn",
        "ref_id",
        "name",
        "description",
        "parent_urn",
        "translations",
        "depth",
        "assessable",
        "reference_controls",
    }
    GENERIC_CHECKED_FIELDS = ["urn", "ref_id", "name", "description", "assessable"]
    """
    parent_urn: urn
    assessable: bool
    reference_controls List[urn]
    """
    EXTRA_CHECKS = {
        "urn": LibraryFormatUtils.check_urn,
        "parent_urn": LibraryFormatUtils.check_urn,
        "translations": LibraryFormatUtils.check_translations,
        # The "refence_controls" fields are a list of lazy loaded referential objects
        # Their verification process is the same as the one for library dependencies
        "reference_controls": LibraryFormatUtils.check_dependencies,
    }
    MODEL = RequirementNode


class LibraryFieldsChecker(ObjectFieldsChecker):
    REQUIRED_FIELDS = {"urn", "name", "version", "objects", "locale", "ref_id"}
    ALL_FIELDS = {
        "urn",
        "name",
        "description",
        "copyright",
        "locale",
        "ref_id",
        "dependencies",
        "version",
        "provider",
        "packager",
        "translations",
        "annotation",
        "objects",
    }
    GENERIC_CHECKED_FIELDS = [
        "urn",
        "name",
        "description",
        "copyright",
        "locale",
        "ref_id",
        "version",
        "provider",
        "packager",
        "annotation",
    ]
    EXTRA_CHECKS = {
        "urn": LibraryFormatUtils.check_urn,
        "locale": LibraryFormatUtils.check_locale,
        "version": LibraryFormatUtils.check_version,
        "translations": LibraryFormatUtils.check_translations,
        "dependencies": LibraryFormatUtils.check_dependencies,
    }
    MODEL = StoredLibrary


class LibraryFormatChecker:
    OBJECT_FIELDS = {  # List of valid keys for the library["objects"] dictionary.
        "threats",
        "reference_controls",
        "risk_matrix",
        "framework",
        "requirement_mapping_set",
    }
    NON_UNIQUE_OBJECTS = ["threats", "reference_controls", "risk_matrix"]
    UNIQUE_OBJECTS = list(OBJECT_FIELDS - set(NON_UNIQUE_OBJECTS))

    def __init__(self, library_data: dict):
        self._library = library_data
        self._objects = {}
        self._framework_importer = None
        self._threats = []
        self._reference_controls = []
        self._risk_matrices = []
        self._requirement_mapping_set = None

    def check_metadata_validity(self) -> Union[None, Tuple[str, dict, List[str]]]:
        """
        Check the validity of all the libary metadatas.
        The metadatas are all the fields contained directly within the dictionary of the library.
        """

        if error := LibraryFieldsChecker.check(self._library):
            return error

    def check_objects_emptyness(self) -> Union[None, Tuple[str, dict, List[str]]]:
        if not self._objects:
            return ("libraryErrorObjectsEmpty", {}, ["objects"])

        object_fields = set(self._objects.keys())
        invalid_object_fields = object_fields - LibraryFormatChecker.OBJECT_FIELDS
        if invalid_object_fields:
            return (
                "libraryErrorInvalidFields",
                {"fields": repr_value(sorted(invalid_object_fields))},
                ["objects"],
            )

        for object_typename in LibraryFormatChecker.NON_UNIQUE_OBJECTS:
            object_data = self._objects.get(object_typename, NotImplemented)
            if object_data is not NotImplemented and not isinstance(object_data, list):
                return (
                    "libraryErrorBadType",
                    {
                        "value": repr_value(object_data),
                        "type": type(object_data).__name__,
                        "expected_type": "list",
                    },
                    ["objects", object_typename],
                )

        for object_typename in LibraryFormatChecker.UNIQUE_OBJECTS:
            object_data = self._objects.get(object_typename, NotImplemented)
            if object_data is not NotImplemented and not isinstance(object_data, dict):
                return (
                    "libraryErrorBadType",
                    {
                        "value": repr_value(object_data),
                        "type": type(object_data).__name__,
                        "expected_type": "dict",
                    },
                    ["objects", object_typename],
                )

    # Returning a list of errors to the client instead of the first detected error would be even better.
    # But it wouldn't be good to put a lot of text in a toast message so it would require creating a dedicated feature for library validity checking/custom library creation.
    def check_threats(self) -> Union[None, Tuple[str, dict, List[str]]]:
        threats = self._objects.get("threats", [])
        for index, threat in enumerate(threats):
            ident = get_object_ident(threat, index)
            if (error := ThreatFieldsChecker.check(threat)) is not None:
                return merge_location(error, ["objects", "threats", ident])

    def check_reference_controls(self) -> Union[None, Tuple[str, dict, List[str]]]:
        reference_controls = self._objects.get("reference_controls", [])
        for index, reference_control in enumerate(reference_controls):
            ident = get_object_ident(reference_control, index)
            if (error := ReferenceControlChecker.check(reference_control)) is not None:
                return merge_location(error, ["objects", "reference_controls", ident])

    def check_risk_matrices(self) -> Union[None, Tuple[str, dict, List[str]]]:
        matrices = self._objects.get("risk_matrix", [])
        for index, matrix in enumerate(matrices):
            ident = get_object_ident(matrix, index)
            if (
                error := LibraryFormatUtils.check_risk_matrix(
                    matrix, ["objects", "risk_matrix", ident]
                )
            ) is not None:
                return error

    def check_framework(self) -> Union[None, Tuple[str, dict, List[str]]]:
        framework = self._objects.get("framework")
        if framework is None:
            return None

        requirement_nodes = framework.get("requirement_nodes", [])
        if not isinstance(requirement_nodes, list):
            return (
                "libraryErrorBadType",
                {
                    "value": "[...]",
                    "type": type(requirement_nodes).__name__,
                    "expected_type": "list",
                },
                ["objects", "framework", "requirement_nodes"],
            )

        for requirement_node in requirement_nodes:
            if (error := RequirementNodeChecker.check(requirement_node)) is not None:
                return merge_location(error, ["objects", "framework"])

        for requirement_node in requirement_nodes:
            urn = requirement_node["urn"]
            urn_chain = [urn]
            while (parent_urn := requirement_node.get("parent_urn")) is not None:
                urn_chain.append(parent_urn)
                if urn == parent_urn:
                    return (
                        "libraryErrorCircularRequirementNode",
                        {"urns": "===>".join(urn_chain)},
                        ["objects", "framework", "requirement_nodes"],
                    )

    def run(self) -> Union[None, Tuple[str, dict, List[str]]]:
        """
        We must check :
        - Mandatory fields (some objects require specific fields to be valid)
        - Invalid fields (unknown fields)
        - Invalid types (possible types for each field)
        - Invalid values (empty, too big, too high, too short, too long, regex not matching)
        - Dependencies issues (circular dependency of requirement nodes)
        - Check the existence of the parent_urn within the library (does it have the same behavior when using dependencies ? => depencies will be checked during the loading phase not during the store phase)
        ===> Therefore some checks will be disabled if the libary has dependencies

        The order of these checks must always be like this:
        - Check if the value exist
        - Check if the value has the right type
        - Check if the value is valid
        - Check if the value is valid compared to other values which validity has already been verified in previous tests
        """

        if (error := self.check_metadata_validity()) is not None:
            return error

        self._objects = self._library["objects"]

        # The unit tests that check if the Validity verifier works should only focus on if an error is detected or not and but not check what type of error is returned as it would be too annoying to do and not that much usefull anyway.
        for check_function in [
            self.check_objects_emptyness,
            self.check_threats,
            self.check_reference_controls,
            self.check_risk_matrices,
            self.check_framework,
            # self.check_requirement_mapping_set
        ]:
            # The pattern for the error location will generally be :
            # [object][urn=... OR {nth}][...fields]
            if (error := check_function()) is not None:
                return error

        return ("libraryErrorNotAnError", {}, [])
