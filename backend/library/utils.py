import json
import time
import os
from pathlib import Path
import re
from typing import List, Union
from django.core.exceptions import SuspiciousFileOperation
from django.http import Http404

import yaml

# interesting thread: https://stackoverflow.com/questions/27743711/can-i-speedup-yaml
from ciso_assistant import settings
from core.models import (
    Framework,
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

URN_REGEX = r"^urn:([a-zA-Z0-9_-]+):([a-zA-Z0-9_-]+):([a-zA-Z0-9_-]+)(?::([a-zA-Z0-9_-]+))?:([0-9A-Za-z\[\]\(\)\-\._:]+)$"


def match_urn(urn_string):
    match = re.match(URN_REGEX, urn_string)
    if match:
        return match.groups()  # Returns all captured groups from the regex match
    else:
        return None


class RequirementNodeImporter:
    REQUIRED_FIELDS = {"urn"}

    def __init__(self, requirement_data: dict, index: int):
        self.requirement_data = requirement_data
        self.index = index

    def is_valid(self) -> Union[str, None]:
        if missing_fields := self.REQUIRED_FIELDS - set(self.requirement_data.keys()):
            return "Missing the following fields : {}".format(", ".join(missing_fields))

    def import_requirement_node(self, framework_object: Framework):
        requirement_node = RequirementNode.objects.create(
            # Should i just inherit the folder from Framework or this is useless ?
            folder=Folder.get_root_folder(),
            framework=framework_object,
            urn=self.requirement_data["urn"],
            parent_urn=self.requirement_data.get("parent_urn"),
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
            is_published=True,
        )

        for threat in self.requirement_data.get("threats", []):
            requirement_node.threats.add(
                Threat.objects.get(urn=threat.lower())
            )  # URN are not case insensitive in the whole codebase yet, we should fix that and make sure URNs are always transformed into lowercase before being used.

        for reference_control in self.requirement_data.get("reference_controls", []):
            requirement_node.reference_controls.add(
                ReferenceControl.objects.get(urn=reference_control.lower())
            )


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
            urn=self.framework_data["urn"],
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
            urn=self.threat_data.get("urn"),
            ref_id=self.threat_data["ref_id"],
            name=self.threat_data.get("name"),
            description=self.threat_data.get("description"),
            provider=library_object.provider,
            is_published=True,
            locale=library_object.locale,
            default_locale=library_object.default_locale,  # Change this in the future ?
        )


# The couple (URN, locale) is unique. ===> Check it in the future
class ReferenceControlImporter:
    REQUIRED_FIELDS = {"ref_id", "urn"}
    CATEGORIES = set(_category[0] for _category in ReferenceControl.CATEGORY)

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

    def import_reference_control(self, library_object: LoadedLibrary):
        ReferenceControl.objects.create(
            library=library_object,
            urn=self.reference_control_data.get("urn"),
            ref_id=self.reference_control_data["ref_id"],
            name=self.reference_control_data.get("name"),
            description=self.reference_control_data.get("description"),
            provider=library_object.provider,
            typical_evidence=self.reference_control_data.get("typical_evidence"),
            category=self.reference_control_data.get("category"),
            is_published=True,
            locale=library_object.locale,
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
            urn=self.risk_matrix_data.get("urn"),
            provider=library_object.provider,
            ref_id=self.risk_matrix_data.get("ref_id"),
            json_definition=json.dumps(matrix_data),
            is_enabled=self.risk_matrix_data.get("is_enabled", True),
            locale=library_object.locale,
            default_locale=library_object.default_locale,  # Change this in the future ?
            is_published=True,
        )
        logger.info("Risk matrix created", matrix=matrix)
        return matrix


class LibraryImporter:
    # The word "import" must be replaced by "load" in all classes/methods/variables declared in this file.

    REQUIRED_FIELDS = {"ref_id", "urn", "locale", "objects", "version"}
    OBJECT_FIELDS = ["threats", "reference_controls", "risk_matrix", "framework"]

    def __init__(self, library: StoredLibrary):
        self._library = library
        self._framework_importer = None
        self._threats = []
        self._reference_controls = []
        self._risk_matrices = []

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

    @transaction.atomic
    def _import_library(self):
        library_object = self.create_or_update_library()
        self.import_objects(library_object)
        if dependencies := self._library.dependencies:
            library_object.dependencies.set(
                LoadedLibrary.objects.filter(urn__in=dependencies)
            )

    def import_library(self):
        """Main method to import a library."""
        if (error_message := self.init()) is not None:
            return error_message  # This error check should be done when storing the Library but no after.

        error_msg = self.check_and_import_dependencies()
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
