import json
import os
import re
import hashlib
from datetime import date, datetime
from pathlib import Path
from typing import Self, Type, Union

from icecream import ic
from auditlog.registry import auditlog

from django.utils.functional import cached_property
import yaml
from django.apps import apps
from django.contrib.auth import get_user_model
from django.core import serializers
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, RegexValidator, MinValueValidator
from django.db import models, transaction
from django.db.models import F, Q, OuterRef, Subquery
from django.forms.models import model_to_dict
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import get_language
from django.utils.translation import gettext_lazy as _
from structlog import get_logger
from django.utils.timezone import now

from iam.models import Folder, FolderMixin, PublishInRootFolderMixin
from library.helpers import (
    get_referential_translation,
    update_translations,
    update_translations_as_string,
    update_translations_in_object,
)
from global_settings.models import GlobalSettings

from .base_models import AbstractBaseModel, ETADueDateMixin, NameDescriptionMixin
from .utils import camel_case, sha256
from .validators import (
    validate_file_name,
    validate_file_size,
    JSONSchemaInstanceValidator,
)

logger = get_logger(__name__)

User = get_user_model()


URN_REGEX = r"^urn:([a-zA-Z0-9_-]+):([a-zA-Z0-9_-]+):([a-zA-Z0-9_-]+)(?::([a-zA-Z0-9_-]+))?:([0-9A-Za-z\[\]\(\)\-\._:]+)$"


def match_urn(urn_string):
    match = re.match(URN_REGEX, urn_string)
    if match:
        return match.groups()  # Returns all captured groups from the regex match
    else:
        return None


def transform_questions_to_answers(questions):
    """
    Used during Requirement Assessment creation to prepare the answers from the questions

    Args:
        questions (json): the questions from the requirement

    Returns:
        json: the answers formatted as a json
    """
    answers = {}
    for question_urn, question in questions.items():
        answers[question_urn] = [] if question["type"] == "multiple_choice" else None
    return answers


########################### Referential objects #########################


class ReferentialObjectMixin(AbstractBaseModel, FolderMixin):
    """
    Mixin for referential objects.
    """

    urn = models.CharField(
        max_length=255, null=True, blank=True, unique=True, verbose_name=_("URN")
    )
    ref_id = models.CharField(  # Should this field be nullable ?
        max_length=100, blank=True, null=True, verbose_name=_("Reference ID")
    )
    provider = models.CharField(
        max_length=200, blank=True, null=True, verbose_name=_("Provider")
    )
    name = models.CharField(
        null=True, max_length=200, verbose_name=_("Name"), unique=False
    )
    description = models.TextField(null=True, blank=True, verbose_name=_("Description"))
    annotation = models.TextField(null=True, blank=True, verbose_name=_("Annotation"))
    translations = models.JSONField(
        null=True, blank=True, verbose_name=_("Translations")
    )

    class Meta:
        abstract = True

    @property
    def get_name_translated(self) -> str:
        translations = self.translations if self.translations else {}
        locale_translations = translations.get(get_language(), {})
        return locale_translations.get("name", self.name)

    @property
    def get_description_translated(self) -> str:
        translations = self.translations if self.translations else {}
        locale_translations = translations.get(get_language(), {})
        return locale_translations.get("description", self.description)

    @property
    def get_annotation_translated(self) -> str:
        translations = self.translations if self.translations else {}
        locale_translations = translations.get(get_language(), {})
        return locale_translations.get("annotation", self.annotation)

    @property
    def display_short(self) -> str:
        _name = (
            self.ref_id
            if not self.get_name_translated
            else self.get_name_translated
            if not self.ref_id
            else f"{self.ref_id} - {self.get_name_translated}"
        )
        _name = "" if not _name else _name
        return _name

    @property
    def display_long(self) -> str:
        _name = self.display_short
        _display = (
            _name
            if not self.get_description_translated
            else self.get_description_translated
            if _name == ""
            else f"{_name}: {self.get_description_translated}"
        )
        return _display

    def __str__(self) -> str:
        return self.display_short


class I18nObjectMixin(models.Model):
    locale = models.CharField(
        max_length=100, null=False, blank=False, default="en", verbose_name=_("Locale")
    )
    default_locale = models.BooleanField(default=True, verbose_name=_("Default locale"))

    class Meta:
        abstract = True


class FilteringLabel(FolderMixin, AbstractBaseModel, PublishInRootFolderMixin):
    label = models.CharField(
        max_length=100,
        verbose_name=_("Label"),
        validators=[
            RegexValidator(
                regex=r"^[\w-]{1,36}$",
                message="invalidLabel",
                code="invalid_label",
            )
        ],
    )

    def __str__(self) -> str:
        return self.label

    fields_to_check = ["label"]


class FilteringLabelMixin(models.Model):
    filtering_labels = models.ManyToManyField(
        FilteringLabel, blank=True, verbose_name=_("Labels")
    )

    class Meta:
        abstract = True


class LibraryMixin(ReferentialObjectMixin, I18nObjectMixin):
    class Meta:
        abstract = True
        unique_together = [["urn", "locale", "version"]]

    urn = models.CharField(max_length=255, null=True, blank=True, verbose_name=_("URN"))
    copyright = models.CharField(
        max_length=4096, null=True, blank=True, verbose_name=_("Copyright")
    )
    version = models.IntegerField(null=False, verbose_name=_("Version"))
    packager = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text=_("Packager of the library"),
        verbose_name=_("Packager"),
    )
    publication_date = models.DateField(null=True)
    builtin = models.BooleanField(default=False)
    objects_meta = models.JSONField(default=dict)
    dependencies = models.JSONField(
        null=True
    )  # models.CharField(blank=False,null=True,max_length=16384)

    @property
    def get_locales(self):
        return (
            [self.locale] + list(self.translations.keys())
            if self.translations
            else [self.locale]
        )


class Severity(models.IntegerChoices):
    UNDEFINED = -1, "undefined"
    LOW = 0, "low"
    MEDIUM = 1, "medium"
    HIGH = 2, "high"
    CRITICAL = 3, "critical"


class StoredLibrary(LibraryMixin):
    is_loaded = models.BooleanField(default=False)
    hash_checksum = models.CharField(max_length=64)
    content = models.JSONField()

    REQUIRED_FIELDS = {"urn", "name", "version", "objects"}
    FIELDS_VERIFIERS = {}
    # For now a library isn't updated if its SHA256 checksum has already been registered in the database.
    HASH_CHECKSUM_SET = set()

    @classmethod
    def __init_class__(cls):
        cls.HASH_CHECKSUM_SET = set(
            value["hash_checksum"] for value in cls.objects.values("hash_checksum")
        )

    @classmethod
    def store_library_content(
        cls, library_content: bytes, builtin: bool = False
    ) -> "StoredLibrary | None":
        hash_checksum = sha256(library_content)
        if hash_checksum in StoredLibrary.HASH_CHECKSUM_SET:
            # We do not store the library if its hash checksum is in the database.
            return None
        try:
            library_data = yaml.safe_load(library_content)
            if not isinstance(library_data, dict):
                raise yaml.YAMLError(
                    f"The YAML content must be a dictionary but it's been interpreted as a {type(library_data).__name__} !"
                )
        except yaml.YAMLError as e:
            logger.error("Error while loading library content", error=e)
            raise e
        missing_fields = StoredLibrary.REQUIRED_FIELDS - set(library_data.keys())

        if missing_fields:
            err = "The following fields are missing : {}".format(
                ", ".join(repr(field) for field in missing_fields)
            )
            logger.error("Error while loading library content", error=err)
            raise ValueError(err)

        urn = library_data["urn"].lower()
        if not match_urn(urn):
            raise ValueError("Library URN is badly formatted")
        locale = library_data.get("locale", "en")
        version = int(library_data["version"])
        is_loaded = LoadedLibrary.objects.filter(  # We consider the library as loaded even if the loaded version is different
            urn=urn, locale=locale
        ).exists()
        same_version_lib = StoredLibrary.objects.filter(
            urn=urn, locale=locale, version=version
        ).first()
        if same_version_lib:
            # update hash following cosmetic change (e.g. when we added publication date)
            logger.info("update hash", urn=urn)
            same_version_lib.hash_checksum = hash_checksum
            same_version_lib.save()
            return None

        if StoredLibrary.objects.filter(urn=urn, locale=locale, version__gte=version):
            return None  # We do not accept to store outdated libraries

        # This code allows adding outdated libraries in the library store but they will be erased if a greater version of this library is stored.
        for outdated_library in StoredLibrary.objects.filter(
            urn=urn, locale=locale, version__lt=version
        ):
            outdated_library.delete()

        objects_meta = {
            key: (1 if key in ["framework", "requirement_mapping_set"] else len(value))
            for key, value in library_data["objects"].items()
        }

        dependencies = library_data.get(
            "dependencies", []
        )  # I don't want whitespaces in URN anymore nontheless

        library_objects = library_data["objects"]
        return StoredLibrary.objects.create(
            name=library_data["name"],
            is_published=True,
            urn=urn,
            locale=locale,
            version=version,
            ref_id=library_data["ref_id"],
            default_locale=False,  # We don't care about this value yet.
            description=library_data.get("description"),
            annotation=library_data.get("annotation"),
            copyright=library_data.get("copyright"),
            provider=library_data.get("provider"),
            packager=library_data.get("packager"),
            publication_date=library_data.get("publication_date"),
            translations=library_data.get("translations", {}),
            objects_meta=objects_meta,
            dependencies=dependencies,
            is_loaded=is_loaded,
            # We have to add a "builtin: true" line to every builtin library file.
            builtin=builtin,
            hash_checksum=hash_checksum,
            content=library_objects,
        )

    @classmethod
    def store_library_file(
        cls, fname: Path, builtin: bool = False
    ) -> "StoredLibrary | None":
        with open(fname, "rb") as f:
            library_content = f.read()

        return StoredLibrary.store_library_content(library_content, builtin)

    def load(self) -> Union[str, None]:
        from library.utils import LibraryImporter

        if LoadedLibrary.objects.filter(urn=self.urn, locale=self.locale):
            return "This library has already been loaded."

        library_importer = LibraryImporter(self)
        error_msg = library_importer.import_library()
        if error_msg is None:
            self.is_loaded = True
            self.save()
        return error_msg


class LibraryUpdater:
    def __init__(self, old_library: Type["LoadedLibrary"], new_library: StoredLibrary):
        self.old_library = old_library
        self.old_objects = [
            *old_library.threats.all(),
            *old_library.reference_controls.all(),
            *old_library.threats.all(),
            *old_library.risk_matrices.all(),
        ]
        self.new_library = new_library
        new_library_content = self.new_library.content
        self.dependencies = self.new_library.dependencies
        if self.dependencies is None:
            self.dependencies = []
        self.new_framework = new_library_content.get("framework")
        self.new_matrices = new_library_content.get("risk_matrix")
        self.threats = new_library_content.get("threats", [])
        self.reference_controls = new_library_content.get("reference_controls", [])
        self.new_objects = {obj["urn"].lower(): obj for obj in self.threats}
        self.new_objects.update(
            {obj["urn"].lower(): obj for obj in self.reference_controls}
        )
        if self.new_framework:
            self.new_objects[self.new_framework["urn"].lower()] = self.new_framework
        if self.new_matrices:
            for matrix in self.new_matrices:
                self.new_objects[matrix["urn"].lower()] = matrix

    def update_dependencies(self) -> Union[str, None]:
        for dependency_urn in self.dependencies:
            possible_dependencies = [*LoadedLibrary.objects.filter(urn=dependency_urn)]
            if (
                not possible_dependencies
            ):  # This part of the code hasn't been tested yet
                stored_dependencies = [
                    *StoredLibrary.objects.filter(urn=dependency_urn)
                ]
                if not stored_dependencies:
                    return "dependencyNotFound"
                dependency = stored_dependencies[0]
                for i in range(1, len(stored_dependencies)):
                    stored_dependency = stored_dependencies[i]
                    if stored_dependency.locale == self.old_library.locale:
                        dependency = stored_dependency
                if err_msg := dependency.load():
                    return err_msg
                continue

            dependency = possible_dependencies[0]
            for i in range(1, len(possible_dependencies)):
                possible_dependency = possible_dependencies[i]
                if possible_dependency.locale == self.old_library.locale:
                    dependency = possible_dependency

            if (err_msg := dependency.update()) not in [None, "libraryHasNoUpdate"]:
                return err_msg

    # We should create a LibraryVerifier class in the future that check if the library is valid and use it for a better error handling.
    def update_library(self) -> Union[str, None]:
        if (error_msg := self.update_dependencies()) is not None:
            return error_msg

        old_dependencies_urn = {
            dependency.urn for dependency in self.old_library.dependencies.all()
        }
        dependencies_urn = set(self.dependencies)
        new_dependencies_urn = dependencies_urn - old_dependencies_urn

        if not set(dependencies_urn).issuperset(old_dependencies_urn):
            return "invalidLibraryUpdate"

        new_dependencies = []
        for new_dependency_urn in new_dependencies_urn:
            try:
                new_dependency = LoadedLibrary.objects.filter(
                    urn=new_dependency_urn
                ).first()  # The locale is not handled by this code
            except:
                return "dependencyNotFound"
            new_dependencies.append(new_dependency)
        for key, value in [
            ("name", self.new_library.name),
            ("version", self.new_library.version),
            ("provider", self.new_library.provider),
            (
                "packager",
                self.new_library.packager,
            ),  # A user can fake a builtin library in this case because he can update a builtin library by adding its own library with the same URN as a builtin library.
            ("publication_date", self.new_library.publication_date),
            # Should we even update the ref_id ?
            ("ref_id", self.new_library.ref_id),
            ("description", self.new_library.description),
            ("annotation", self.new_library.annotation),
            ("translations", self.new_library.translations),
            ("copyright", self.new_library.copyright),
            ("objects_meta", self.new_library.objects_meta),
        ]:
            setattr(self.old_library, key, value)
        self.old_library.save()

        for new_dependency in new_dependencies:
            self.old_library.dependencies.add(new_dependency)

        referential_object_dict = {
            "locale": self.old_library.locale,
            "default_locale": self.old_library.default_locale,
            "provider": self.new_library.provider,
            "is_published": True,
        }

        for threat in self.threats:
            Threat.objects.update_or_create(
                urn=threat["urn"].lower(),
                defaults=threat,
                create_defaults={
                    **referential_object_dict,
                    **threat,
                    "library": self.old_library,
                },
            )

        for reference_control in self.reference_controls:
            ReferenceControl.objects.update_or_create(
                urn=reference_control["urn"].lower(),
                defaults=reference_control,
                create_defaults={
                    **referential_object_dict,
                    **reference_control,
                    "library": self.old_library,
                },
            )

        if self.new_framework is not None:
            framework_dict = {**self.new_framework}
            del framework_dict["requirement_nodes"]

            new_framework, _ = Framework.objects.update_or_create(
                urn=self.new_framework["urn"],
                defaults=framework_dict,
                create_defaults={
                    **referential_object_dict,
                    **framework_dict,
                    "library": self.old_library,
                },
            )

            requirement_node_urns = set(
                rc.urn for rc in RequirementNode.objects.filter(framework=new_framework)
            )
            new_requirement_node_urns = set(
                rc["urn"].lower() for rc in self.new_framework["requirement_nodes"]
            )
            deleted_requirement_node_urns = (
                requirement_node_urns - new_requirement_node_urns
            )

            for requirement_node_urn in deleted_requirement_node_urns:
                requirement_node = RequirementNode.objects.filter(
                    urn=requirement_node_urn
                ).first()  # locale is not used, so if there are more than one requirement node with this URN only the first fetched requirement node will be deleted.
                if requirement_node is not None:
                    requirement_node.delete()

            requirement_nodes = self.new_framework["requirement_nodes"]
            involved_library_urns = [*self.dependencies, self.old_library.urn]
            involved_libraries = set(
                LoadedLibrary.objects.filter(urn__in=involved_library_urns)
            )
            objects_tracked = {}

            for threat in Threat.objects.filter(library__in=involved_libraries):
                objects_tracked[threat.urn] = threat

            for rc in ReferenceControl.objects.filter(library__in=involved_libraries):
                objects_tracked[rc.urn] = rc

            compliance_assessments = [
                *ComplianceAssessment.objects.filter(framework=new_framework)
            ]

            order_id = 0
            for requirement_node in requirement_nodes:
                requirement_node_dict = {**requirement_node}
                for key in ["depth", "reference_controls", "threats"]:
                    requirement_node_dict.pop(key, None)
                requirement_node_dict["order_id"] = order_id
                order_id += 1

                (
                    new_requirement_node,
                    created,
                ) = RequirementNode.objects.update_or_create(
                    urn=requirement_node["urn"].lower(),
                    defaults=requirement_node_dict,
                    create_defaults={
                        **referential_object_dict,
                        **requirement_node_dict,
                        "framework": new_framework,
                    },
                )

                if created:
                    for compliance_assessment in compliance_assessments:
                        ra = RequirementAssessment.objects.create(
                            compliance_assessment=compliance_assessment,
                            requirement=new_requirement_node,
                            folder=compliance_assessment.perimeter.folder,
                            answers=transform_questions_to_answers(
                                new_requirement_node.questions
                            )
                            if new_requirement_node.questions
                            else {},
                        )
                else:
                    questions = requirement_node.get("questions")

                    for ra in RequirementAssessment.objects.filter(
                        requirement=new_requirement_node
                    ):
                        ra.name = new_requirement_node.name
                        ra.description = new_requirement_node.description
                        if not questions:
                            ra.save()
                            continue

                        answers = ra.answers

                        # Remove answers corresponding to questions that have been removed
                        for urn in list(answers.keys()):
                            if urn not in questions:
                                del answers[urn]
                        # Add answers corresponding to questions that have been updated/added
                        for urn, question in questions.items():
                            # If the question is not present in answers, initialize it
                            if urn not in answers:
                                answers[urn] = None
                                continue

                            answer_val = answers[urn]
                            type = question.get("type")

                            if type == "multiple_choice":
                                # Keep only the choices that exist in the question
                                if isinstance(answer_val, list):
                                    valid_choices = {
                                        choice["urn"]
                                        for choice in question.get("choices", [])
                                    }
                                    answers[urn] = [
                                        choice
                                        for choice in answer_val
                                        if choice in valid_choices
                                    ]
                                else:
                                    answers[urn] = []

                            elif type == "unique_choice":
                                # If the answer does not match a valid choice, reset it to None
                                valid_choices = {
                                    choice["urn"]
                                    for choice in question.get("choices", [])
                                }
                                if isinstance(answer_val, list):
                                    answers[urn] = None
                                else:
                                    answers[urn] = (
                                        answer_val
                                        if answer_val in valid_choices
                                        else None
                                    )

                            elif type == "text":
                                # For a text question, simply check that it is a string
                                if isinstance(answer_val, list):
                                    answers[urn] = None
                                else:
                                    answers[urn] = (
                                        answer_val
                                        if isinstance(answer_val, str)
                                        and answer_val.split(":")[0] != "urn"
                                        else None
                                    )

                            elif type == "date":
                                # For a date question, check the expected format (e.g., "YYYY-MM-DD")
                                if isinstance(answer_val, list):
                                    answers[urn] = None
                                else:
                                    try:
                                        datetime.strptime(answer_val, "%Y-%m-%d")
                                        answers[urn] = answer_val
                                    except Exception:
                                        answers[urn] = None
                        ra.answers = answers
                        ra.save()

                for threat_urn in requirement_node_dict.get("threats", []):
                    thread_to_add = objects_tracked.get(threat_urn)
                    if thread_to_add is None:  # I am not 100% this condition is usefull
                        thread_to_add = Threat.objects.filter(
                            urn=threat_urn
                        ).first()  # No locale support
                    if thread_to_add is not None:
                        new_requirement_node.threats.add(thread_to_add)

                for reference_control_urn in requirement_node.get(
                    "reference_controls", []
                ):
                    reference_control_to_add = objects_tracked.get(
                        reference_control_urn
                    )
                    if (
                        reference_control_to_add is None
                    ):  # I am not 100% this condition is useful
                        reference_control_to_add = ReferenceControl.objects.filter(
                            urn=reference_control_urn.lower()
                        ).first()  # No locale support

                    if reference_control_to_add is not None:
                        new_requirement_node.reference_controls.add(
                            reference_control_to_add
                        )

        if self.new_matrices is not None:
            for matrix in self.new_matrices:
                json_definition_keys = {
                    "grid",
                    "probability",
                    "impact",
                    "risk",
                }  # Store this as a constant somewhere (as a static attribute of the class)
                other_keys = set(matrix.keys()) - json_definition_keys
                matrix_dict = {key: matrix[key] for key in other_keys}
                matrix_dict["json_definition"] = {}
                for key in json_definition_keys:
                    if (
                        key in matrix
                    ):  # If all keys are mandatory this condition is useless
                        matrix_dict["json_definition"][key] = matrix[key]

                RiskMatrix.objects.update_or_create(
                    urn=matrix["urn"].lower(),
                    defaults=matrix_dict,
                    create_defaults={
                        **referential_object_dict,
                        **matrix_dict,
                        "library": self.old_library,
                    },
                )


class LoadedLibrary(LibraryMixin):
    dependencies = models.ManyToManyField(
        "self", blank=True, verbose_name=_("Dependencies"), symmetrical=False
    )

    @transaction.atomic
    def update(self) -> Union[str, None]:
        new_libraries = [
            *StoredLibrary.objects.filter(
                urn=self.urn, locale=self.locale, version__gt=self.version
            )
        ]

        if not new_libraries:
            return "libraryHasNoUpdate"

        new_library = max(new_libraries, key=lambda lib: lib.version)
        library_updater = LibraryUpdater(self, new_library)
        return library_updater.update_library()

    @property
    def _objects(self):
        res = {}
        if self.frameworks.count() > 0:
            res["framework"] = update_translations_in_object(
                model_to_dict(self.frameworks.first())
            )
            res["framework"].update(self.frameworks.first().library_entry)
        if self.threats.count() > 0:
            res["threats"] = [
                update_translations_in_object(model_to_dict(threat))
                for threat in self.threats.all()
            ]
        if self.reference_controls.count() > 0:
            res["reference_controls"] = [
                update_translations_in_object(model_to_dict(reference_control))
                for reference_control in self.reference_controls.all()
            ]
        if self.risk_matrices.count() > 0:
            matrix = self.risk_matrices.first()
            res["risk_matrix"] = update_translations_in_object(model_to_dict(matrix))
            res["risk_matrix"]["probability"] = update_translations(matrix.probability)
            res["risk_matrix"]["impact"] = update_translations(matrix.impact)
            res["risk_matrix"]["risk"] = update_translations(matrix.risk)
            res["risk_matrix"]["grid"] = matrix.grid
            res["strength_of_knowledge"] = matrix.strength_of_knowledge
            res["risk_matrix"] = [res["risk_matrix"]]
        return res

    @property
    def reference_count(self) -> int:
        """
        Returns the number of distinct dependent libraries and risk and compliance assessments that reference objects from this library
        """
        return (
            RiskAssessment.objects.filter(
                Q(risk_scenarios__threats__library=self)
                | Q(risk_matrix__library=self)
                | Q(risk_scenarios__applied_controls__reference_control__library=self)
            )
            .distinct()
            .count()
            + ComplianceAssessment.objects.filter(
                Q(framework__library=self)
                | Q(
                    requirement_assessments__applied_controls__reference_control__library=self
                )
            )
            .distinct()
            .count()
            + LoadedLibrary.objects.filter(dependencies=self).distinct().count()
        )

    @property
    def has_update(self) -> bool:
        max_version = (
            StoredLibrary.objects.filter(urn=self.urn)
            .values_list("version", flat=True)
            .order_by("-version")
            .first()
        )
        return max_version > self.version if max_version is not None else False

    @classmethod
    def updatable_libraries(cls):
        # Create a subquery to get the highest version in StoredLibrary for the same urn.
        latest_version_qs = (
            StoredLibrary.objects.filter(urn=OuterRef("urn"))
            .order_by("-version")
            .values("version")[:1]
        )

        # Annotate each LoadedLibrary with the latest stored version and filter.
        return cls.objects.annotate(
            latest_stored_version=Subquery(latest_version_qs)
        ).filter(latest_stored_version__gt=F("version"))

    def delete(self, *args, **kwargs):
        if self.reference_count > 0:
            raise ValueError(
                "This library is still referenced by some risk or compliance assessments"
            )
        dependent_libraries = LoadedLibrary.objects.filter(dependencies=self)
        if dependent_libraries:
            raise ValueError(
                f"This library is a dependency of {dependent_libraries.count()} other libraries"
            )
        super(LoadedLibrary, self).delete(*args, **kwargs)
        StoredLibrary.objects.filter(urn=self.urn, locale=self.locale).update(
            is_loaded=False
        )


class Threat(
    ReferentialObjectMixin,
    I18nObjectMixin,
    PublishInRootFolderMixin,
    FilteringLabelMixin,
):
    library = models.ForeignKey(
        LoadedLibrary,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="threats",
    )

    is_published = models.BooleanField(_("published"), default=True)

    fields_to_check = ["ref_id", "name"]

    class Meta:
        verbose_name = _("Threat")
        verbose_name_plural = _("Threats")

    def is_deletable(self) -> bool:
        """
        Returns True if the framework can be deleted
        """
        if self.requirements.count() > 0:
            return False
        return True

    @property
    def frameworks(self):
        return Framework.objects.filter(requirement__threats=self).distinct()

    def __str__(self):
        return self.name


class ReferenceControl(ReferentialObjectMixin, I18nObjectMixin, FilteringLabelMixin):
    CATEGORY = [
        ("policy", _("Policy")),
        ("process", _("Process")),
        ("technical", _("Technical")),
        ("physical", _("Physical")),
        ("procedure", _("Procedure")),
    ]

    CSF_FUNCTION = [
        ("govern", _("Govern")),
        ("identify", _("Identify")),
        ("protect", _("Protect")),
        ("detect", _("Detect")),
        ("respond", _("Respond")),
        ("recover", _("Recover")),
    ]

    library = models.ForeignKey(
        LoadedLibrary,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="reference_controls",
    )
    category = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        choices=CATEGORY,
        verbose_name=_("Category"),
    )
    csf_function = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        choices=CSF_FUNCTION,
        verbose_name=_("CSF Function"),
    )
    typical_evidence = models.JSONField(
        verbose_name=_("Typical evidence"), null=True, blank=True
    )
    is_published = models.BooleanField(_("published"), default=True)

    fields_to_check = ["ref_id", "name"]

    class Meta:
        verbose_name = _("Reference control")
        verbose_name_plural = _("Reference controls")

    def is_deletable(self) -> bool:
        """
        Returns True if the framework can be deleted
        """
        if self.requirements.count() or self.appliedcontrol_set.count() > 0:
            return False
        return True

    @property
    def frameworks(self):
        return Framework.objects.filter(requirement__reference_controls=self).distinct()

    def __str__(self):
        if self.name:
            return self.ref_id + " - " + self.name if self.ref_id else self.name
        else:
            return (
                self.ref_id + " - " + self.description
                if self.ref_id
                else self.description
            )


class RiskMatrix(ReferentialObjectMixin, I18nObjectMixin):
    library = models.ForeignKey(
        LoadedLibrary,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="risk_matrices",
    )

    json_definition = models.JSONField(
        verbose_name=_("JSON definition"),
        help_text=_(
            "JSON definition of the risk matrix. \
        See the documentation for more information."
        ),
        default=dict,
    )
    is_enabled = models.BooleanField(
        _("enabled"),
        default=True,
        help_text=_(
            "If the risk matrix is set as disabled, it will not be available for selection for new risk assessments."
        ),
    )

    @property
    def is_used(self) -> bool:
        return RiskAssessment.objects.filter(risk_matrix=self).exists()

    @property
    def risk_assessments(self) -> list:
        return RiskAssessment.objects.filter(risk_matrix=self)

    @property
    def perimeters(self) -> list:
        return Perimeter.objects.filter(riskassessment__risk_matrix=self).distinct()

    def parse_json(self) -> dict:
        return self.json_definition

    def parse_json_translated(self) -> dict:
        return update_translations_in_object(self.json_definition)

    @property
    def grid(self) -> list:
        risk_matrix = self.parse_json()
        grid = []
        for row in risk_matrix["grid"]:
            grid.append([item for item in row])
        return grid

    @property
    def probability(self) -> list:
        risk_matrix = self.parse_json()
        return risk_matrix["probability"]

    @property
    def impact(self) -> list:
        risk_matrix = self.parse_json()
        return risk_matrix["impact"]

    @property
    def risk(self) -> list:
        risk_matrix = self.parse_json()
        return risk_matrix["risk"]

    @property
    def strength_of_knowledge(self):
        risk_matrix = self.parse_json()
        return risk_matrix.get("strength_of_knowledge")

    def render_grid_as_colors(self):
        risk_matrix = self.parse_json()
        grid = risk_matrix["grid"]
        res = [[risk_matrix["risk"][i] for i in row] for row in grid]

        return res

    @property
    def get_json_translated(self):
        # Why "fr" ?
        return update_translations_as_string(self.json_definition, "fr")

    def __str__(self) -> str:
        return self.get_name_translated


class Framework(ReferentialObjectMixin, I18nObjectMixin):
    min_score = models.IntegerField(default=0, verbose_name=_("Minimum score"))
    max_score = models.IntegerField(default=100, verbose_name=_("Maximum score"))
    scores_definition = models.JSONField(
        blank=True, null=True, verbose_name=_("Score definition")
    )
    implementation_groups_definition = models.JSONField(
        blank=True, null=True, verbose_name=_("Implementation groups definition")
    )
    library = models.ForeignKey(
        LoadedLibrary,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="frameworks",
    )

    class Meta:
        verbose_name = _("Framework")
        verbose_name_plural = _("Frameworks")

    def is_deletable(self) -> bool:
        """
        Returns True if the framework can be deleted
        """
        if self.compliance_assessment_set.count() > 0:
            return False
        return True

    @property
    def library_entry(self):
        res = {}
        requirement_nodes = self.get_requirement_nodes()
        if requirement_nodes:
            res["requirement_nodes"] = requirement_nodes

        return res

    @property
    def reference_controls(self):
        _reference_controls = ReferenceControl.objects.filter(
            requirements__framework=self
        ).distinct()
        reference_controls = []
        for control in _reference_controls:
            reference_controls.append(
                {"str": control.display_long, "urn": control.urn, "id": control.id}
            )
        return reference_controls

    def get_requirement_nodes(self):
        # Prefetch related objects if they exist to reduce database queries.
        # Adjust prefetch_related paths according to your model relationships.
        nodes_queryset = self.requirement_nodes.prefetch_related(
            "threats", "reference_controls"
        )
        if nodes_queryset.exists():
            return [self.process_node(node) for node in nodes_queryset]
        return []

    def process_node(self, node):
        # Convert the node to dict and process threats and security functions.
        node_dict = model_to_dict(node)
        if node.threats.exists():
            node_dict["threats"] = [
                model_to_dict(threat) for threat in node.threats.all()
            ]
        if node.reference_controls.exists():
            node_dict["reference_controls"] = [
                model_to_dict(reference_control)
                for reference_control in node.reference_controls.all()
            ]
        return node_dict

    def __str__(self) -> str:
        return f"{self.provider} - {self.name}"


class RequirementNode(ReferentialObjectMixin, I18nObjectMixin):
    threats = models.ManyToManyField(
        "Threat",
        blank=True,
        verbose_name=_("Threats"),
        related_name="requirements",
    )
    reference_controls = models.ManyToManyField(
        "ReferenceControl",
        blank=True,
        verbose_name=_("Reference controls"),
        related_name="requirements",
    )
    framework = models.ForeignKey(
        Framework,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name=_("Framework"),
        related_name="requirement_nodes",
    )
    parent_urn = models.CharField(
        max_length=255, null=True, blank=True, verbose_name=_("Parent URN")
    )
    order_id = models.IntegerField(null=True, verbose_name=_("Order ID"))
    implementation_groups = models.JSONField(
        null=True, verbose_name=_("Implementation groups")
    )
    assessable = models.BooleanField(null=False, verbose_name=_("Assessable"))
    typical_evidence = models.TextField(
        null=True, blank=True, verbose_name=_("Typical evidence")
    )
    questions = models.JSONField(blank=True, null=True, verbose_name=_("Questions"))

    @property
    def associated_reference_controls(self):
        _reference_controls = self.reference_controls.all()
        reference_controls = []
        for control in _reference_controls:
            reference_controls.append(
                {"str": control.display_long, "urn": control.urn, "id": control.id}
            )
        return reference_controls

    @property
    def associated_threats(self):
        _threats = self.threats.all()
        threats = []
        for control in _threats:
            threats.append(
                {"str": control.display_long, "urn": control.urn, "id": control.id}
            )
        return threats

    @property
    def parent_requirement(self):
        parent_requirement = RequirementNode.objects.filter(urn=self.parent_urn).first()
        if not parent_requirement:
            return None
        return {
            "str": parent_requirement.display_long,
            "urn": parent_requirement.urn,
            "id": parent_requirement.id,
            "ref_id": parent_requirement.ref_id,
            "name": parent_requirement.name,
            "description": parent_requirement.description,
        }

    class Meta:
        verbose_name = _("RequirementNode")
        verbose_name_plural = _("RequirementNodes")


class RequirementMappingSet(ReferentialObjectMixin):
    library = models.ForeignKey(
        LoadedLibrary,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="requirement_mapping_sets",
    )

    source_framework = models.ForeignKey(
        Framework,
        on_delete=models.CASCADE,
        verbose_name=_("Source framework"),
        related_name="source_framework",
    )
    target_framework = models.ForeignKey(
        Framework,
        on_delete=models.CASCADE,
        verbose_name=_("Target framework"),
        related_name="target_framework",
    )

    def save(self, *args, **kwargs) -> None:
        if self.source_framework == self.target_framework:
            raise ValidationError(_("Source and related frameworks must be different"))
        return super().save(*args, **kwargs)


class RequirementMapping(models.Model):
    class Coverage(models.TextChoices):
        FULL = "full", _("Full")
        PARTIAL = "partial", _("Partial")
        NOT_RELATED = "not_related", _("Not related")

    class Relationship(models.TextChoices):
        SUBSET = "subset", _("Subset")
        INTERSECT = "intersect", _("Intersect")
        EQUAL = "equal", _("Equal")
        SUPERSET = "superset", _("Superset")
        NOT_RELATED = "not_related", _("Not related")

    class Rationale(models.TextChoices):
        SYNTACTIC = "syntactic", _("Syntactic")
        SEMANTIC = "semantic", _("Semantic")
        FUNCTIONAL = "functional", _("Functional")

    FULL_COVERAGE_RELATIONSHIPS = [
        Relationship.EQUAL,
        Relationship.SUPERSET,
    ]

    PARTIAL_COVERAGE_RELATIONSHIPS = [
        Relationship.INTERSECT,
        Relationship.SUBSET,
    ]

    mapping_set = models.ForeignKey(
        RequirementMappingSet,
        on_delete=models.CASCADE,
        verbose_name=_("Mapping set"),
        related_name="mappings",
    )
    target_requirement = models.ForeignKey(
        RequirementNode,
        on_delete=models.CASCADE,
        verbose_name=_("Target requirement"),
        related_name="target_requirement",
    )
    relationship = models.CharField(
        max_length=20,
        choices=Relationship.choices,
        default=Relationship.NOT_RELATED,
        verbose_name=_("Relationship"),
    )
    rationale = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        choices=Rationale.choices,
        verbose_name=_("Rationale"),
    )
    source_requirement = models.ForeignKey(
        RequirementNode,
        on_delete=models.CASCADE,
        verbose_name=_("Source requirement"),
        related_name="source_requirement",
    )
    strength_of_relationship = models.PositiveSmallIntegerField(
        null=True,
        verbose_name=_("Strength of relationship"),
        validators=[MaxValueValidator(10)],
    )
    annotation = models.TextField(null=True, blank=True, verbose_name=_("Annotation"))

    @property
    def coverage(self) -> str:
        if self.relationship == RequirementMapping.Relationship.NOT_RELATED:
            return RequirementMapping.Coverage.NOT_RELATED
        if self.relationship in self.FULL_COVERAGE_RELATIONSHIPS:
            return RequirementMapping.Coverage.FULL
        return RequirementMapping.Coverage.PARTIAL


class Qualification(ReferentialObjectMixin, I18nObjectMixin):
    DEFAULT_QUALIFICATIONS = [
        {
            "abbreviation": "C",
            "qualification_ordering": 1,
            "security_objective_ordering": 1,
            "name": "Confidentiality",
            "urn": "urn:intuitem:risk:qualification:confidentiality",
        },
        {
            "abbreviation": "I",
            "qualification_ordering": 2,
            "security_objective_ordering": 2,
            "name": "Integrity",
            "urn": "urn:intuitem:risk:qualification:integrity",
        },
        {
            "abbreviation": "A",
            "qualification_ordering": 3,
            "security_objective_ordering": 3,
            "name": "Availability",
            "urn": "urn:intuitem:risk:qualification:availability",
        },
        {
            "abbreviation": "P",
            "qualification_ordering": 4,
            "security_objective_ordering": 4,
            "name": "Proof",
            "urn": "urn:intuitem:risk:qualification:proof",
        },
        {
            "abbreviation": "Aut",
            "qualification_ordering": 5,
            "security_objective_ordering": 5,
            "name": "Authenticity",
            "urn": "urn:intuitem:risk:qualification:authenticity",
        },
        {
            "abbreviation": "Priv",
            "qualification_ordering": 6,
            "security_objective_ordering": 6,
            "name": "Privacy",
            "urn": "urn:intuitem:risk:qualification:privacy",
        },
        {
            "abbreviation": "Safe",
            "qualification_ordering": 7,
            "security_objective_ordering": 7,
            "name": "Safety",
            "urn": "urn:intuitem:risk:qualification:safety",
        },
        {
            "abbreviation": "Rep",
            "qualification_ordering": 8,
            "name": "Reputation",
            "urn": "urn:intuitem:risk:qualification:reputation",
        },
        {
            "abbreviation": "Ope",
            "qualification_ordering": 9,
            "name": "Operational",
            "urn": "urn:intuitem:risk:qualification:operational",
        },
        {
            "abbreviation": "Leg",
            "qualification_ordering": 10,
            "name": "Legal",
            "urn": "urn:intuitem:risk:qualification:legal",
        },
        {
            "abbreviation": "Fin",
            "qualification_ordering": 11,
            "name": "Financial",
            "urn": "urn:intuitem:risk:qualification:financial",
        },
        {
            "abbreviation": "Gov",
            "qualification_ordering": 12,
            "name": "Governance",
            "urn": "urn:intuitem:risk:qualification:governance",
        },
        {
            "abbreviation": "Mis",
            "qualification_ordering": 13,
            "name": "Missions and Organizational Services",
            "urn": "urn:intuitem:risk:qualification:missions",
        },
        {
            "abbreviation": "Hum",
            "qualification_ordering": 14,
            "name": "Human",
            "urn": "urn:intuitem:risk:qualification:human",
        },
        {
            "abbreviation": "Mat",
            "qualification_ordering": 15,
            "name": "Material",
            "urn": "urn:intuitem:risk:qualification:material",
        },
        {
            "abbreviation": "Env",
            "qualification_ordering": 16,
            "name": "Environmental",
            "urn": "urn:intuitem:risk:qualification:environmental",
        },
        {
            "abbreviation": "Img",
            "qualification_ordering": 17,
            "name": "Image",
            "urn": "urn:intuitem:risk:qualification:image",
        },
        {
            "abbreviation": "Tru",
            "qualification_ordering": 18,
            "name": "Trust",
            "urn": "urn:intuitem:risk:qualification:trust",
        },
    ]

    abbreviation = models.CharField(
        max_length=20, null=True, blank=True, verbose_name=_("Abbreviation")
    )
    qualification_ordering = models.PositiveSmallIntegerField(
        verbose_name=_("Ordering"), default=0
    )
    security_objective_ordering = models.PositiveSmallIntegerField(
        verbose_name=_("Security objective ordering"), default=0
    )

    class Meta:
        verbose_name = _("Qualification")
        verbose_name_plural = _("Qualifications")
        ordering = ["qualification_ordering"]

    @classmethod
    def create_default_qualifications(cls):
        for qualification in cls.DEFAULT_QUALIFICATIONS:
            Qualification.objects.update_or_create(
                urn=qualification["urn"],
                defaults=qualification,
                create_defaults=qualification,
            )


########################### Domain objects #########################


class Perimeter(NameDescriptionMixin, FolderMixin):
    PRJ_LC_STATUS = [
        ("undefined", _("Undefined")),
        ("in_design", _("Design")),
        ("in_dev", _("Development")),
        ("in_prod", _("Production")),
        ("eol", _("EndOfLife")),
        ("dropped", _("Dropped")),
    ]

    ref_id = models.CharField(
        max_length=100, null=True, blank=True, verbose_name=_("reference id")
    )
    lc_status = models.CharField(
        max_length=20,
        default="in_design",
        choices=PRJ_LC_STATUS,
        verbose_name=_("Status"),
    )
    fields_to_check = ["name"]

    class Meta:
        verbose_name = _("Perimeter")
        verbose_name_plural = _("Perimeters")

    def overall_compliance(self):
        compliance_assessments_list = [
            compliance_assessment
            for compliance_assessment in self.compliance_assessment_set.all()
        ]
        count = (
            RequirementAssessment.objects.filter(status="compliant")
            .filter(compliance_assessment__in=compliance_assessments_list)
            .count()
        )
        total = RequirementAssessment.objects.filter(
            compliance_assessment__in=compliance_assessments_list
        ).count()
        if total == 0:
            return 0
        return round(count * 100 / total)

    def __str__(self):
        return self.folder.name + "/" + self.name


class SecurityException(NameDescriptionMixin, FolderMixin, PublishInRootFolderMixin):
    class Status(models.TextChoices):
        DRAFT = "draft", "draft"
        IN_REVIEW = "in_review", "in review"
        APPROVED = "approved", "approved"
        RESOLVED = "resolved", "resolved"
        EXPIRED = "expired", "expired"
        DEPRECATED = "deprecated", "deprecated"

    ref_id = models.CharField(
        max_length=100, null=True, blank=True, verbose_name=_("Reference ID")
    )
    severity = models.SmallIntegerField(
        verbose_name="Severity", choices=Severity.choices, default=Severity.UNDEFINED
    )
    status = models.CharField(
        verbose_name="Status",
        choices=Status.choices,
        null=False,
        default=Status.DRAFT,
        max_length=20,
    )
    expiration_date = models.DateField(
        help_text="Specify when the security exception will no longer apply",
        null=True,
        verbose_name="Expiration date",
    )
    owners = models.ManyToManyField(
        User,
        blank=True,
        verbose_name="Owner",
        related_name="security_exceptions",
    )
    approver = models.ForeignKey(
        User,
        max_length=200,
        verbose_name=_("Approver"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    is_published = models.BooleanField(_("published"), default=True)

    fields_to_check = ["name"]

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()
        if self.expiration_date and self.expiration_date < now().date():
            raise ValidationError(
                {"expiration_date": "Expiration date must be in the future"}
            )


class Asset(
    NameDescriptionMixin, FolderMixin, PublishInRootFolderMixin, FilteringLabelMixin
):
    class Type(models.TextChoices):
        """
        The type of the asset.

        An asset can either be a primary or a support asset.
        A support asset can be linked to another "parent" asset of type primary or support.
        Cycles are not allowed
        """

        PRIMARY = "PR", _("Primary")
        SUPPORT = "SP", _("Support")

    DEFAULT_SECURITY_OBJECTIVES = (
        "confidentiality",
        "integrity",
        "availability",
        "proof",
        "authenticity",
        "privacy",
        "safety",
    )

    SECURITY_OBJECTIVES_JSONSCHEMA = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://ciso-assistant.com/schemas/assets/security_objectives.schema.json",
        "title": "Security objectives",
        "description": "The security objectives of the asset",
        "type": "object",
        "properties": {
            "objectives": {
                "type": "object",
                "patternProperties": {
                    "^[a-z_]+$": {
                        "type": "object",
                        "properties": {
                            "value": {
                                "type": "integer",
                                "minimum": 0,
                                "maximum": 4,
                            },
                            "is_enabled": {
                                "type": "boolean",
                            },
                        },
                    },
                },
            }
        },
    }

    DEFAULT_DISASTER_RECOVERY_OBJECTIVES = ("rto", "rpo", "mtd")

    DISASTER_RECOVERY_OBJECTIVES_JSONSCHEMA = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://ciso-assistant.com/schemas/assets/security_objectives.schema.json",
        "title": "Security objectives",
        "description": "The security objectives of the asset",
        "type": "object",
        "properties": {
            "objectives": {
                "type": "object",
                "patternProperties": {
                    "^[a-z_]+$": {
                        "type": "object",
                        "properties": {
                            "value": {
                                "type": "integer",
                                "minimum": 0,
                            },
                        },
                    },
                },
            }
        },
    }

    SECURITY_OBJECTIVES_SCALES = {
        "1-4": [1, 2, 3, 4, 4],
        "1-5": [1, 2, 3, 4, 5],
        "0-3": [0, 1, 2, 3, 3],
        "0-4": [0, 1, 2, 3, 4],
        "FIPS-199": ["low", "moderate", "moderate", "high", "high"],
    }

    business_value = models.CharField(
        max_length=200, blank=True, verbose_name=_("business value")
    )
    type = models.CharField(
        max_length=2, choices=Type.choices, default=Type.SUPPORT, verbose_name=_("type")
    )
    parent_assets = models.ManyToManyField(
        "self", blank=True, verbose_name=_("parent assets"), symmetrical=False
    )
    reference_link = models.URLField(
        null=True,
        blank=True,
        max_length=2048,
        help_text=_("External url for action follow-up (eg. Jira ticket)"),
        verbose_name=_("Link"),
    )
    security_objectives = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Security objectives"),
        help_text=_("The security objectives of the asset"),
        validators=[JSONSchemaInstanceValidator(SECURITY_OBJECTIVES_JSONSCHEMA)],
    )
    disaster_recovery_objectives = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Disaster recovery objectives"),
        help_text=_("The disaster recovery objectives of the asset"),
        validators=[
            JSONSchemaInstanceValidator(DISASTER_RECOVERY_OBJECTIVES_JSONSCHEMA)
        ],
    )
    ref_id = models.CharField(
        max_length=100, blank=True, verbose_name=_("Reference ID")
    )
    owner = models.ManyToManyField(
        User,
        blank=True,
        verbose_name=_("Owner"),
        related_name="assets",
    )
    security_exceptions = models.ManyToManyField(
        SecurityException,
        blank=True,
        verbose_name="Security exceptions",
        related_name="assets",
    )
    asset_class = models.ForeignKey(
        "AssetClass", on_delete=models.SET_NULL, blank=True, null=True
    )
    is_published = models.BooleanField(_("published"), default=True)

    fields_to_check = ["name"]

    class Meta:
        verbose_name_plural = _("Assets")
        verbose_name = _("Asset")

    def __str__(self) -> str:
        return str(self.name)

    @property
    def is_primary(self) -> bool:
        """
        Returns True if the asset is a primary asset.
        """
        return self.type == Asset.Type.PRIMARY

    @property
    def is_support(self) -> bool:
        """
        Returns True if the asset is a support asset.
        """
        return self.type == Asset.Type.SUPPORT

    def ancestors_plus_self(self) -> set[Self]:
        result = {self}
        for x in self.parent_assets.all():
            result.update(x.ancestors_plus_self())
        return set(result)

    def get_children(self):
        return Asset.objects.filter(parent_assets=self)

    def get_descendants(self) -> set[Self]:
        children = self.get_children()
        sub_children = set()
        for child in children:
            sub_children.add(child)
            sub_children.update(child.get_descendants())
        return sub_children

    @property
    def children_assets(self):
        descendants = self.get_descendants()
        descendant_ids = [d.id for d in descendants]
        return Asset.objects.filter(id__in=descendant_ids).exclude(id=self.id)

    def get_security_objectives(self) -> dict[str, dict[str, dict[str, int | bool]]]:
        """
        Gets the security objectives of a given asset.
        If the asset is a primary asset, the security objectives are directly stored in the asset.
        If the asset is a supporting asset, the security objectives are the union of the security objectives of all the primary assets it supports.
        If multiple ancestors share the same security objective, its value in the result is its highest value among the ancestors.
        """
        if self.security_objectives.get("objectives"):
            self.security_objectives["objectives"] = {
                key: self.security_objectives["objectives"][key]
                for key in Asset.DEFAULT_SECURITY_OBJECTIVES
                if key in self.security_objectives["objectives"]
            }

        if self.is_primary:
            return self.security_objectives

        ancestors = self.ancestors_plus_self()
        primary_assets = {asset for asset in ancestors if asset.is_primary}
        if not primary_assets:
            return {}

        security_objectives = {}
        for asset in primary_assets:
            for key, content in asset.security_objectives.get("objectives", {}).items():
                if not content.get("is_enabled", False):
                    continue
                if key not in security_objectives:
                    security_objectives[key] = content
                else:
                    security_objectives[key]["value"] = max(
                        security_objectives[key].get("value", 0),
                        content.get("value", 0),
                    )
        return {"objectives": security_objectives}

    def get_disaster_recovery_objectives(self) -> dict[str, dict[str, dict[str, int]]]:
        """
        Gets the disaster recovery objectives of a given asset.
        If the asset is a primary asset, the disaster recovery objectives are directly stored in the asset.
        If the asset is a supporting asset, the disaster recovery objectives are the union of the disaster recovery objectives of all the primary assets it supports.
        If multiple ancestors share the same disaster recovery objective, its value in the result is its lowest value among the ancestors.
        """
        if self.is_primary:
            return self.disaster_recovery_objectives

        ancestors = self.ancestors_plus_self()
        primary_assets = {asset for asset in ancestors if asset.is_primary}
        if not primary_assets:
            return {}

        disaster_recovery_objectives = {}
        for asset in primary_assets:
            for key, content in asset.disaster_recovery_objectives.get(
                "objectives", {}
            ).items():
                if key not in disaster_recovery_objectives:
                    disaster_recovery_objectives[key] = content
                else:
                    disaster_recovery_objectives[key]["value"] = min(
                        disaster_recovery_objectives[key].get("value", 0),
                        content.get("value", 0),
                    )

        return {"objectives": disaster_recovery_objectives}

    def get_security_objectives_display(self) -> list[dict[str, str]]:
        """
        Gets the security objectives of a given asset as strings.
        """
        security_objectives = self.get_security_objectives()
        if len(security_objectives) == 0:
            return []
        general_settings = GlobalSettings.objects.filter(name="general").first()
        scale = (
            general_settings.value.get("security_objective_scale", "1-4")
            if general_settings
            else "1-4"
        )
        return [
            {
                "str": f"{key}: {self.SECURITY_OBJECTIVES_SCALES[scale][content.get('value', 0)]}",
            }
            for key, content in sorted(
                security_objectives.get("objectives", {}).items(),
                key=lambda x: self.DEFAULT_SECURITY_OBJECTIVES.index(x[0]),
            )
            if content.get("is_enabled", False)
            and content.get("value", -1) in range(0, 5)
        ]

    def get_disaster_recovery_objectives_display(self) -> list[dict[str, str]]:
        def format_seconds(seconds: int) -> str:
            hours, remainder = divmod(seconds, 3600)
            minutes, secs = divmod(remainder, 60)

            parts = []
            if hours > 0:
                parts.append(f"{hours}h")
            if minutes > 0:
                parts.append(f"{minutes:02d}m")
            if secs > 0 or (
                not parts
            ):  # Always show seconds if no other parts, or if > 0
                parts.append(f"{secs:02d}s")

            return "".join(parts)

        """
        Gets the disaster recovery objectives of a given asset as strings.
        """
        disaster_recovery_objectives = self.get_disaster_recovery_objectives()
        return [
            {"str": f"{key}: {format_seconds(content.get('value', 0))}"}
            for key, content in sorted(
                disaster_recovery_objectives.get("objectives", {}).items(),
                key=lambda x: self.DEFAULT_DISASTER_RECOVERY_OBJECTIVES.index(x[0]),
            )
            if content.get("value", 0)
        ]

    def save(self, *args, **kwargs) -> None:
        self.full_clean()
        return super().save(*args, **kwargs)


class AssetClass(NameDescriptionMixin, FolderMixin, PublishInRootFolderMixin):
    parent = models.ForeignKey(
        "AssetClass", on_delete=models.PROTECT, blank=True, null=True
    )

    @cached_property
    def full_path(self):
        if self.parent is None:
            return self.name
        else:
            return f"{self.parent.full_path}/{self.name}"

    @classmethod
    def build_tree(cls):
        all_nodes = list(cls.objects.all())
        nodes_by_id = {
            node.id: {"name": node.name, "children": []} for node in all_nodes
        }

        tree = []

        for node in all_nodes:
            node_dict = nodes_by_id[node.id]

            if node.parent_id is None:
                tree.append(node_dict)
            else:
                parent_dict = nodes_by_id.get(node.parent_id)
                if parent_dict:  # Check if parent exists
                    parent_dict["children"].append(node_dict)

        return tree

    @classmethod
    def create_hierarchy(cls, hierarchy_data, parent=None):
        created_nodes = []

        for item in hierarchy_data:
            # Get or create the asset class
            asset_class, created = cls.objects.get_or_create(
                name=item["name"],
                parent=parent,
                defaults={
                    "description": item.get("description", ""),
                },
            )

            created_nodes.append(asset_class)

            if "children" in item and item["children"]:
                cls.create_hierarchy(item["children"], parent=asset_class)

        return created_nodes

    @classmethod
    def create_default_values(cls):
        cis_hierarchy = [
            {
                "name": "assetClassDevices",
                "description": "Assets that may exist in physical spaces, virtual infrastructure, or cloud-based environments",
                "children": [
                    {
                        "name": "assetClassEnterpriseAssets",
                        "description": "Assets with the potential to store or process data",
                        "children": [
                            {
                                "name": "assetClassEndUserDevices",
                                "description": "IT assets used among members of an enterprise",
                                "children": [
                                    {
                                        "name": "assetClassPortable",
                                        "description": "Transportable, end-user devices with wireless connectivity capability",
                                        "children": [
                                            {
                                                "name": "assetClassMobile",
                                                "description": "Small, enterprise-issued end-user devices with intrinsic wireless capability",
                                            }
                                        ],
                                    }
                                ],
                            },
                            {
                                "name": "assetClassServers",
                                "description": "Devices or systems that provide resources, data, services, or programs to other devices",
                            },
                            {
                                "name": "assetClassCloudInfrastructure",
                                "description": "Cloud Infrastructure and resources",
                            },
                            {
                                "name": "assetClassIotAndNonComputingDevices",
                                "description": "Devices embedded with sensors, software, and other technologies for connecting and exchanging data",
                            },
                            {
                                "name": "assetClassNetworkDevices",
                                "description": "Electronic devices required for communication and interaction between devices on a network",
                            },
                        ],
                    },
                    {
                        "name": "assetClassRemovableMedia",
                        "description": "Storage devices that can be removed from a computer while the system is running",
                    },
                ],
            },
            {
                "name": "assetClassSoftware",
                "description": "Sets of data and instructions used to direct a computer to complete a specific task",
                "children": [
                    {
                        "name": "assetClassApplications",
                        "description": "Programs running on top of an operating system",
                        "children": [
                            {
                                "name": "assetClassServices",
                                "description": "Specialized programs that perform well-defined critical tasks",
                            },
                            {
                                "name": "assetClassLibraries",
                                "description": "Shareable pre-compiled codebase used to develop software programs and applications",
                            },
                            {
                                "name": "assetClassAPIs",
                                "description": "Set of rules and interfaces for software components to interact with each other",
                            },
                            {
                                "name": "assetClassSaas",
                                "description": "Software as a Service",
                            },
                        ],
                    },
                    {
                        "name": "assetClassOperatingSystems",
                        "description": "Software that manages computer hardware and software resources",
                        "children": [
                            {
                                "name": "assetClassServices",
                                "description": "Specialized programs that perform well-defined critical tasks",
                            },
                            {
                                "name": "assetClassLibraries",
                                "description": "Shareable pre-compiled codebase used to develop software programs and applications",
                            },
                            {
                                "name": "assetClassAPIs",
                                "description": "Set of rules and interfaces for software components to interact with each other",
                            },
                        ],
                    },
                    {
                        "name": "assetClassFirmware",
                        "description": "Software stored within a device's non-volatile memory",
                    },
                ],
            },
            {
                "name": "assetClassData",
                "description": "Collection of facts that can be examined, considered, and used for decision-making",
                "children": [
                    {
                        "name": "assetClassSensitiveData",
                        "description": "Data that must be kept private, accurate, reliable, and available",
                    },
                    {
                        "name": "assetClassLogData",
                        "description": "Computer-generated data file that records events occurring within the enterprise",
                    },
                    {
                        "name": "assetClassPhysicalData",
                        "description": "Data stored in physical documents or on physical types of removable devices",
                    },
                ],
            },
            {
                "name": "assetClassUsers",
                "description": "Authorized individuals who access enterprise assets",
                "children": [
                    {
                        "name": "assetClassWorkforce",
                        "description": "Individuals employed or engaged by an organization with access to its information systems",
                    },
                    {
                        "name": "assetClassServiceProviders",
                        "description": "Entities that offer platforms, software, and services to other enterprises",
                    },
                    {
                        "name": "assetClassUserAccounts",
                        "description": "Identity with a set of credentials that defines a user on a computing system",
                    },
                    {
                        "name": "assetClassAdministratorAccounts",
                        "description": "Accounts for users requiring escalated privileges",
                    },
                    {
                        "name": "assetClassServiceAccounts",
                        "description": "Accounts created specifically to run applications, services, and automated tasks",
                    },
                ],
            },
            {
                "name": "assetClassNetwork",
                "description": "Group of interconnected devices that exchange data",
                "children": [
                    {
                        "name": "assetClassNetworkInfrastructure",
                        "description": "Collection of network resources that provide connectivity, management, and communication",
                    },
                    {
                        "name": "assetClassNetworkArchitecture",
                        "description": "How a network is designed, both physically and logically",
                    },
                ],
            },
            {
                "name": "assetClassDocumentation",
                "description": "Policies, processes, procedures, plans, and other written material",
                "children": [
                    {
                        "name": "assetClassPlans",
                        "description": "Implements policies and may include groups of policies, processes, and procedures",
                    },
                    {
                        "name": "assetClassPolicies",
                        "description": "Official governance statements that outline specific objectives of an information security program",
                    },
                    {
                        "name": "assetClassProcesses",
                        "description": "Set of general tasks and activities to achieve a series of security-related goals",
                    },
                    {
                        "name": "assetClassProcedures",
                        "description": "Ordered set of steps that must be followed to accomplish a specific task",
                    },
                ],
            },
        ]
        extra = [
            {
                "name": "assetClassBusinessProcess",
                "description": "Organized set of activities and related procedures by which an organization operates",
                "children": [
                    {
                        "name": "assetClassCoreOperations",
                        "description": "Primary processes that directly deliver value to customers",
                        "children": [
                            {
                                "name": "assetClassProductOrServiceDevelopment",
                                "description": "Processes for designing, creating, and improving products and services",
                            },
                            {
                                "name": "assetClassProductOrServiceDelivery",
                                "description": "Processes for manufacturing products or delivering services to customers",
                            },
                            {
                                "name": "assetClassSalesAndMarketing",
                                "description": "Processes for attracting customers and selling products/services",
                            },
                            {
                                "name": "assetClassCustomerService",
                                "description": "Processes for supporting customers after sales",
                            },
                            {
                                "name": "assetClassSupplyChainManagement",
                                "description": "Processes for managing the flow of goods, services, and information",
                            },
                        ],
                    },
                    {
                        "name": "assetClassManagementAndGovernance",
                        "description": "Processes that provide oversight, direction, and accountability",
                        "children": [
                            {
                                "name": "assetClassStrategicPlanning",
                                "description": "Processes for defining long-term objectives and allocation of resources",
                            },
                            {
                                "name": "assetClassFinancialManagement",
                                "description": "Processes for budgeting, accounting, and financial reporting",
                            },
                            {
                                "name": "assetClassRiskManagement",
                                "description": "Processes for identifying, assessing, and mitigating risks",
                            },
                            {
                                "name": "assetClassComplianceManagement",
                                "description": "Processes for ensuring adherence to laws, regulations, and policies",
                            },
                            {
                                "name": "assetClassPerformanceManagement",
                                "description": "Processes for monitoring and improving organizational performance",
                            },
                        ],
                    },
                    {
                        "name": "assetClassSupportFunctions",
                        "description": "Processes that enable and facilitate the core business operations",
                        "children": [
                            {
                                "name": "assetClassHumanResources",
                                "description": "Processes for recruiting, developing, and retaining personnel",
                            },
                            {
                                "name": "assetClassInformationTechnology",
                                "description": "Processes for managing IT infrastructure, applications, and services",
                            },
                            {
                                "name": "assetClassFacilitiesManagement",
                                "description": "Processes for maintaining physical infrastructure and workspaces",
                            },
                            {
                                "name": "assetClassProcurement",
                                "description": "Processes for acquiring goods and services from external suppliers",
                            },
                            {
                                "name": "assetClassLegalServices",
                                "description": "Processes for managing legal affairs and intellectual property",
                            },
                            {
                                "name": "assetClassAdministrativeServices",
                                "description": "Processes for general administrative support functions",
                            },
                        ],
                    },
                    {
                        "name": "assetClassExternalRelationships",
                        "description": "Processes for managing relationships outside the organization",
                        "children": [
                            {
                                "name": "assetClassVendorManagement",
                                "description": "Processes for managing relationships with suppliers and vendors",
                            },
                            {
                                "name": "assetClassPartnerManagement",
                                "description": "Processes for establishing and maintaining strategic partnerships",
                            },
                            {
                                "name": "assetClassGovernmentRelations",
                                "description": "Processes for interacting with government entities",
                            },
                            {
                                "name": "assetClassCommunityRelations",
                                "description": "Processes for engaging with local communities and society",
                            },
                            {
                                "name": "assetClassInvestorRelations",
                                "description": "Processes for managing relationships with investors and shareholders",
                            },
                        ],
                    },
                ],
            }
        ]

        AssetClass.create_hierarchy(cis_hierarchy)
        AssetClass.create_hierarchy(extra)

    def __str__(self):
        return self.full_path

    class Meta:
        unique_together = ["name", "parent"]
        constraints = [
            models.UniqueConstraint(
                fields=["name"],
                condition=models.Q(parent__isnull=True),
                name="unique_name_for_root_items",
            )
        ]


class Evidence(
    NameDescriptionMixin, FolderMixin, PublishInRootFolderMixin, FilteringLabelMixin
):
    # TODO: Manage file upload to S3/MiniO
    attachment = models.FileField(
        #        upload_to=settings.LOCAL_STORAGE_DIRECTORY,
        blank=True,
        null=True,
        help_text=_("Attachment for evidence (eg. screenshot, log file, etc.)"),
        verbose_name=_("Attachment"),
        validators=[validate_file_size, validate_file_name],
    )
    link = models.URLField(
        blank=True,
        null=True,
        max_length=2048,
        help_text=_("Link to the evidence (eg. Jira ticket, etc.)"),
        verbose_name=_("Link"),
    )
    is_published = models.BooleanField(_("published"), default=True)

    fields_to_check = ["name"]

    class Meta:
        verbose_name = _("Evidence")
        verbose_name_plural = _("Evidences")

    def get_folder(self):
        if self.applied_controls:
            return self.applied_controls.first().folder
        elif self.requirement_assessments:
            return self.requirement_assessments.first().folder
        else:
            return None

    def filename(self):
        return os.path.basename(self.attachment.name)

    def get_size(self):
        if not self.attachment or not self.attachment.storage.exists(
            self.attachment.name
        ):
            return None
        # get the attachment size with the correct unit
        size = self.attachment.size
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        else:
            return f"{size / 1024 / 1024:.1f} MB"

    def delete(self, *args, **kwargs):
        if self.attachment:
            self.attachment.delete()
        super().delete(*args, **kwargs)

    @property
    def attachment_hash(self):
        if not self.attachment:
            return None
        return hashlib.sha256(self.attachment.read()).hexdigest()


class Incident(NameDescriptionMixin, FolderMixin):
    class Status(models.TextChoices):
        NEW = "new", "New"
        ONGOING = "ongoing", "Ongoing"
        RESOLVED = "resolved", "Resolved"
        CLOSED = "closed", "Closed"
        DISMISSED = "dismissed", "Dismissed"

    class Severity(models.IntegerChoices):
        SEV1 = 1, "Critical"
        SEV2 = 2, "Major"
        SEV3 = 3, "Moderate"
        SEV4 = 4, "Minor"
        SEV5 = 5, "Low"
        UNDEFINED = 6, "unknown"

    ref_id = models.CharField(
        max_length=100, blank=True, verbose_name=_("Reference ID")
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.NEW,
    )
    severity = models.PositiveSmallIntegerField(
        choices=Severity.choices,
        default=Severity.SEV3,
    )
    threats = models.ManyToManyField(
        Threat,
        related_name="incidents",
        verbose_name="Threats",
        blank=True,
    )
    owners = models.ManyToManyField(
        User,
        related_name="incidents",
        verbose_name="Owners",
        blank=True,
    )
    assets = models.ManyToManyField(
        Asset,
        related_name="incidents",
        verbose_name="Assets",
        blank=True,
    )
    qualifications = models.ManyToManyField(
        Qualification,
        related_name="incidents",
        verbose_name="Qualifications",
        blank=True,
    )
    is_published = models.BooleanField(_("published"), default=True)

    fields_to_check = ["name"]

    class Meta:
        verbose_name = "Incident"
        verbose_name_plural = "Incidents"


class TimelineEntry(AbstractBaseModel, FolderMixin):
    """
    Timeline entry objects describe the evolution of an incident
    """

    class EntryType(models.TextChoices):
        DETECTION = "detection", "Detection"
        MITIGATION = "mitigation", "Mitigation"
        OBSERVATION = "observation", "Observation"
        SEVERITY_CHANGED = "severity_changed", "Severity changed"
        STATUS_CHANGED = "status_changed", "Status changed"

        @classmethod
        def get_manual_entry_types(cls):
            return filter(
                lambda x: x[0] in ["detection", "mitigation", "observation"],
                cls.choices,
            )

    incident = models.ForeignKey(
        Incident,
        on_delete=models.CASCADE,
        related_name="timeline_entries",
        verbose_name=_("Incident"),
    )
    entry = models.CharField(max_length=200, verbose_name="Entry", unique=False)
    entry_type = models.CharField(
        max_length=20,
        choices=EntryType.choices,
        default=EntryType.OBSERVATION,
        verbose_name="Entry type",
    )
    timestamp = models.DateTimeField(
        verbose_name="Timestamp", unique=False, default=now
    )
    author = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name="timeline_entries",
        verbose_name="Author",
        null=True,
        blank=True,
    )
    observation = models.TextField(verbose_name="Observation", blank=True, null=True)
    evidences = models.ManyToManyField(
        Evidence,
        related_name="timeline_entries",
        verbose_name="Evidence",
        blank=True,
    )
    is_published = models.BooleanField(_("published"), default=True)

    def __str__(self):
        return f"{self.entry}"

    def save(self, *args, **kwargs):
        if self.timestamp > now():
            raise ValidationError("Timestamp cannot be in the future.")
        if not self.folder and self.incident:
            self.folder = self.incident.folder
        super().save(*args, **kwargs)


class AppliedControl(
    NameDescriptionMixin, FolderMixin, PublishInRootFolderMixin, FilteringLabelMixin
):
    class Status(models.TextChoices):
        TO_DO = "to_do", _("To do")
        IN_PROGRESS = "in_progress", _("In progress")
        ON_HOLD = "on_hold", _("On hold")
        ACTIVE = "active", _("Active")
        DEPRECATED = "deprecated", _("Deprecated")
        UNDEFINED = "--", _("Undefined")

    PRIORITY = [
        (1, _("P1")),
        (2, _("P2")),
        (3, _("P3")),
        (4, _("P4")),
    ]

    priority = models.PositiveSmallIntegerField(
        choices=PRIORITY,
        null=True,
        blank=True,
        verbose_name=_("Priority"),
    )

    CATEGORY = ReferenceControl.CATEGORY
    CSF_FUNCTION = ReferenceControl.CSF_FUNCTION

    EFFORT = [
        ("XS", "Extra Small"),
        ("S", "Small"),
        ("M", "Medium"),
        ("L", "Large"),
        ("XL", "Extra Large"),
    ]

    IMPACT = [(1, "Very Low"), (2, "Low"), (3, "Medium"), (4, "High"), (5, "Very High")]
    MAP_EFFORT = {None: -1, "XS": 1, "S": 2, "M": 3, "L": 4, "XL": 5}
    # todo: think about a smarter model for ranking
    reference_control = models.ForeignKey(
        ReferenceControl,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name=_("Reference Control"),
    )
    ref_id = models.CharField(
        max_length=100, null=True, blank=True, verbose_name=_("reference id")
    )
    evidences = models.ManyToManyField(
        Evidence,
        blank=True,
        verbose_name=_("Evidences"),
        related_name="applied_controls",
    )

    assets = models.ManyToManyField(
        Asset,
        blank=True,
        verbose_name=_("Assets"),
        related_name="applied_controls",
    )

    category = models.CharField(
        max_length=20,
        choices=CATEGORY,
        null=True,
        blank=True,
        verbose_name=_("Category"),
    )
    csf_function = models.CharField(
        max_length=20,
        choices=CSF_FUNCTION,
        null=True,
        blank=True,
        verbose_name=_("CSF Function"),
    )
    status = models.CharField(  # Should this field be nullable since there is a default value ?
        max_length=20,
        choices=Status.choices,
        default=Status.UNDEFINED,
        blank=True,
        verbose_name=_("Status"),
    )
    owner = models.ManyToManyField(
        User,
        blank=True,
        verbose_name=_("Owner"),
        related_name="applied_controls",
    )
    start_date = models.DateField(
        blank=True,
        null=True,
        help_text=_("Start date (useful for timeline)"),
        verbose_name=_("Start date"),
    )
    eta = models.DateField(
        blank=True,
        null=True,
        help_text=_("Estimated Time of Arrival"),
        verbose_name=_("ETA"),
    )
    expiry_date = models.DateField(
        blank=True,
        null=True,
        help_text=_("Date after which the applied control is no longer valid"),
        verbose_name=_("Expiry date"),
    )
    link = models.CharField(
        null=True,
        blank=True,
        max_length=2048,
        help_text=_("External url for action follow-up (eg. Jira ticket)"),
        verbose_name=_("Link"),
    )
    effort = models.CharField(
        null=True,
        blank=True,
        max_length=2,
        choices=EFFORT,
        help_text=_("Relative effort of the measure (using T-Shirt sizing)"),
        verbose_name=_("Effort"),
    )

    control_impact = models.SmallIntegerField(
        verbose_name="Impact", choices=IMPACT, null=True, blank=True
    )

    cost = models.FloatField(
        null=True,
        help_text=_("Cost of the measure (using globally-chosen currency)"),
        verbose_name=_("Cost"),
    )
    progress_field = models.IntegerField(
        default=0,
        verbose_name=_("Progress Field"),
        validators=[
            MinValueValidator(0, message="Progress cannot be less than 0"),
            MaxValueValidator(100, message="Progress cannot be more than 100"),
        ],
    )
    security_exceptions = models.ManyToManyField(
        SecurityException,
        blank=True,
        verbose_name="Security exceptions",
        related_name="applied_controls",
    )
    is_published = models.BooleanField(_("published"), default=True)

    fields_to_check = ["name"]

    class Meta:
        verbose_name = _("Applied control")
        verbose_name_plural = _("Applied controls")

    def save(self, *args, **kwargs):
        if self.reference_control and self.category is None:
            self.category = self.reference_control.category
        if self.reference_control and self.csf_function is None:
            self.csf_function = self.reference_control.csf_function
        if self.status == "active":
            self.progress_field = 100
        super(AppliedControl, self).save(*args, **kwargs)

    @property
    def risk_scenarios(self):
        return self.risk_scenarios.all()

    @property
    def risk_assessments(self):
        return {scenario.risk_assessment for scenario in self.risk_scenarios}

    @property
    def perimeters(self):
        return {risk_assessment.perimeter for risk_assessment in self.risk_assessments}

    def __str__(self):
        return self.name

    @property
    def mid(self):
        return f"M.{self.scoped_id(scope=AppliedControl.objects.filter(folder=self.folder))}"

    @property
    def csv_value(self):
        return f"[{self.status}] {self.name}" if self.status else self.name

    def get_ranking_score(self):
        value = 0
        for risk_scenario in self.risk_scenarios.all():
            current = risk_scenario.current_level
            residual = risk_scenario.residual_level
            if current >= 0 and residual >= 0:
                value += (1 + current - residual) * (current + 1)
        return abs(round(value / self.MAP_EFFORT[self.effort], 4)) if self.effort else 0

    @property
    def get_html_url(self):
        url = reverse("appliedcontrol-detail", args=(self.id,))
        return format_html(
            '<a class="" href="{}"> <b>[MT-eta]</b> {}: {} </a>',
            url,
            self.folder.name,
            self.name,
        )

    def get_linked_requirements_count(self):
        return RequirementNode.objects.filter(
            requirementassessment__applied_controls=self
        ).count()

    @property
    def links_count(self):
        reqs = 0  # compliance requirements
        scenarios = 0  # risk scenarios
        sh_actions = 0  # stakeholder tprm actions
        reqs = RequirementNode.objects.filter(
            requirementassessment__applied_controls=self
        ).count()
        scenarios = RiskScenario.objects.filter(applied_controls=self).count()

        return reqs + scenarios + sh_actions

    def has_evidences(self):
        return self.evidences.count() > 0

    def eta_missed(self):
        return (
            self.eta < date.today() and self.status != "active" if self.eta else False
        )

    @property
    def days_until_eta(self):
        if not self.eta:
            return None
        days_remaining = (self.eta - date.today()).days

        return max(-1, days_remaining)


class PolicyManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(category="policy")

    def create(self, *args, **kwargs):
        kwargs["category"] = "policy"  # Ensure category is always "policy"
        return super().create(*args, **kwargs)


class Policy(AppliedControl):
    class Meta:
        proxy = True
        verbose_name = _("Policy")
        verbose_name_plural = _("Policies")

    objects = PolicyManager()  # Use the custom manager

    def save(self, *args, **kwargs):
        self.category = "policy"
        super(Policy, self).save(*args, **kwargs)


class Vulnerability(
    NameDescriptionMixin, FolderMixin, PublishInRootFolderMixin, FilteringLabelMixin
):
    class Status(models.TextChoices):
        UNDEFINED = "--", _("Undefined")
        POTENTIAL = "potential", _("Potential")
        EXPLOITABLE = "exploitable", _("Exploitable")
        MITIGATED = "mitigated", _("Mitigated")
        FIXED = "fixed", _("Fixed")

    ref_id = models.CharField(
        max_length=100, blank=True, verbose_name=_("Reference ID")
    )
    status = models.CharField(
        max_length=100,
        choices=Status.choices,
        default=Status.UNDEFINED,
        verbose_name=_("Status"),
    )
    severity = models.SmallIntegerField(
        verbose_name="Severity", choices=Severity.choices, default=Severity.UNDEFINED
    )
    applied_controls = models.ManyToManyField(
        AppliedControl,
        blank=True,
        verbose_name=_("Applied controls"),
        related_name="vulnerabilities",
    )
    assets = models.ManyToManyField(
        Asset,
        blank=True,
        verbose_name=_("Assets"),
        related_name="vulnerabilities",
    )
    security_exceptions = models.ManyToManyField(
        SecurityException,
        blank=True,
        verbose_name="Security exceptions",
        related_name="vulnerabilities",
    )
    is_published = models.BooleanField(_("published"), default=True)

    fields_to_check = ["name"]


# historical data
class HistoricalMetric(models.Model):
    date = models.DateField(verbose_name=_("Date"), db_index=True)
    data = models.JSONField(verbose_name=_("Historical Data"))
    model = models.TextField(verbose_name=_("Model"), db_index=True)
    object_id = models.UUIDField(verbose_name=_("Object ID"), db_index=True)
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated at"))

    class Meta:
        unique_together = ("model", "object_id", "date")
        indexes = [
            models.Index(fields=["model", "object_id", "date"]),
            models.Index(fields=["date", "model"]),
        ]

    @classmethod
    def update_daily_metric(cls, model, object_id, data):
        """
        Upsert method to update or create a daily metric. Should be generic enough for other metrics.
        """
        return cls.objects.update_or_create(
            model=model,
            object_id=object_id,
            date=now().date(),
            defaults={"data": data},
        )


########################### Secondary objects #########################


class Assessment(NameDescriptionMixin, ETADueDateMixin, FolderMixin):
    class Status(models.TextChoices):
        PLANNED = "planned", _("Planned")
        IN_PROGRESS = "in_progress", _("In progress")
        IN_REVIEW = "in_review", _("In review")
        DONE = "done", _("Done")
        DEPRECATED = "deprecated", _("Deprecated")

    perimeter = models.ForeignKey(
        Perimeter,
        on_delete=models.CASCADE,
        verbose_name=_("Perimeter"),
        null=True,
    )
    version = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text=_("Version of the compliance assessment (eg. 1.0, 2.0, etc.)"),
        verbose_name=_("Version"),
        default="1.0",
    )
    status = models.CharField(
        max_length=100,
        choices=Status.choices,
        default=Status.PLANNED,
        verbose_name=_("Status"),
        blank=True,
        null=True,
    )
    authors = models.ManyToManyField(
        User,
        blank=True,
        verbose_name=_("Authors"),
        related_name="%(class)s_authors",
    )
    reviewers = models.ManyToManyField(
        User,
        blank=True,
        verbose_name=_("Reviewers"),
        related_name="%(class)s_reviewers",
    )
    observation = models.TextField(null=True, blank=True, verbose_name=_("Observation"))

    fields_to_check = ["name", "version"]

    class Meta:
        abstract = True

    def save(self, *args, **kwargs) -> None:
        if not self.folder or self.folder == Folder.get_root_folder():
            self.folder = self.perimeter.folder
        return super().save(*args, **kwargs)


class RiskAssessment(Assessment):
    risk_matrix = models.ForeignKey(
        RiskMatrix,
        on_delete=models.PROTECT,
        help_text=_("WARNING! After choosing it, you will not be able to change it"),
        verbose_name=_("Risk matrix"),
    )
    ref_id = models.CharField(
        max_length=100, null=True, blank=True, verbose_name=_("reference id")
    )
    ebios_rm_study = models.ForeignKey(
        "ebios_rm.EbiosRMStudy",
        verbose_name=_("EBIOS RM study"),
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="risk_assessments",
    )

    class Meta:
        verbose_name = _("Risk assessment")
        verbose_name_plural = _("Risk assessments")

    def upsert_daily_metrics(self):
        per_treatment = self.get_per_treatment()

        total = RiskScenario.objects.filter(risk_assessment=self).count()
        data = {
            "scenarios": {
                "total": total,
                "per_treatment": per_treatment,
            },
        }

        HistoricalMetric.update_daily_metric(
            model=self.__class__.__name__, object_id=self.id, data=data
        )

    def __str__(self) -> str:
        return f"{self.name} - {self.version}"

    def get_per_treatment(self) -> dict:
        output = dict()
        for treatment in RiskScenario.TREATMENT_OPTIONS:
            output[treatment[0]] = (
                RiskScenario.objects.filter(risk_assessment=self)
                .filter(treatment=treatment[0])
                .count()
            )
        return output

    def save(self, *args, **kwargs) -> None:
        super().save(*args, **kwargs)
        self.upsert_daily_metrics()

    @property
    def path_display(self) -> str:
        return f"{self.perimeter.folder}/{self.perimeter}/{self.name} - {self.version}"

    def get_scenario_count(self) -> int:
        count = RiskScenario.objects.filter(risk_assessment=self.id).count()
        scenario_count = count
        return scenario_count

    def quality_check(self) -> dict:
        errors_lst = list()
        warnings_lst = list()
        info_lst = list()
        # --- check on the risk risk_assessment:
        _object = serializers.serialize("json", [self])
        _object = json.loads(_object)
        if self.status == Assessment.Status.IN_PROGRESS:
            info_lst.append(
                {
                    "msg": _("{}: Risk assessment is still in progress").format(
                        str(self)
                    ),
                    "msgid": "riskAssessmentInProgress",
                    "obj_type": "risk_assessment",
                    "object": _object,
                }
            )
        if not self.authors.all():
            info_lst.append(
                {
                    "msg": _("{}: No author assigned to this risk assessment").format(
                        str(self)
                    ),
                    "msgid": "riskAssessmentNoAuthor",
                    "obj_type": "risk_assessment",
                    "object": _object,
                }
            )
        if not self.risk_scenarios.all():
            warnings_lst.append(
                {
                    "msg": _(
                        "{}: RiskAssessment is empty. No risk scenario declared yet"
                    ).format(self),
                    "msgid": "riskAssessmentEmpty",
                    "obj_type": "risk_assessment",
                    "object": _object,
                }
            )
        # ---

        # --- checks on the risk scenarios
        # TODO: Refactor this
        _scenarios = serializers.serialize(
            "json", self.risk_scenarios.all().order_by("created_at")
        )
        scenarios = [x["fields"] for x in json.loads(_scenarios)]
        for i in range(len(scenarios)):
            scenarios[i]["id"] = json.loads(_scenarios)[i]["pk"]
        for ri in scenarios:
            if ri["current_level"] < 0:
                warnings_lst.append(
                    {
                        "msg": _("{} current risk level has not been assessed").format(
                            ri["name"]
                        ),
                        "msgid": "riskScenarioNoCurrentLevel",
                        "link": f"risk-scenarios/{ri['id']}",
                        "obj_type": "riskscenario",
                        "object": ri,
                    }
                )
            if ri["residual_level"] < 0 and ri["current_level"] >= 0:
                errors_lst.append(
                    {
                        "msg": _(
                            "{} residual risk level has not been assessed. If no additional measures are applied, it should be at the same level as the current risk"
                        ).format(ri["name"]),
                        "msgid": "riskScenarioNoResidualLevel",
                        "obj_type": "riskscenario",
                        "object": ri,
                    }
                )
            if ri["residual_level"] > ri["current_level"]:
                errors_lst.append(
                    {
                        "msg": _(
                            "{} residual risk level is higher than the current one"
                        ).format(ri["name"]),
                        "msgid": "riskScenarioResidualHigherThanCurrent",
                        "link": f"risk-scenarios/{ri['id']}",
                        "obj_type": "riskscenario",
                        "object": ri,
                    }
                )
            if ri["residual_proba"] > ri["current_proba"]:
                errors_lst.append(
                    {
                        "msg": _(
                            "{} residual risk probability is higher than the current one"
                        ).format(ri["name"]),
                        "msgid": "riskScenarioResidualProbaHigherThanCurrent",
                        "link": f"risk-scenarios/{ri['id']}",
                        "obj_type": "riskscenario",
                        "object": ri,
                    }
                )
            if ri["residual_impact"] > ri["current_impact"]:
                errors_lst.append(
                    {
                        "msg": _(
                            "{} residual risk impact is higher than the current one"
                        ).format(ri["name"]),
                        "msgid": "riskScenarioResidualImpactHigherThanCurrent",
                        "link": f"risk-scenarios/{ri['id']}",
                        "obj_type": "riskscenario",
                        "object": ri,
                    }
                )

            if (
                ri["residual_level"] < ri["current_level"]
                or ri["residual_proba"] < ri["current_proba"]
                or ri["residual_impact"] < ri["current_impact"]
            ):
                if (
                    len(ri.get("applied_controls", {})) == 0
                    and ri["residual_level"] >= 0
                ):
                    errors_lst.append(
                        {
                            "msg": _(
                                "{}: residual risk level has been lowered without any specific measure"
                            ).format(ri["name"]),
                            "msgid": "riskScenarioResidualLoweredWithoutMeasures",
                            "link": f"risk-scenarios/{ri['id']}",
                            "obj_type": "riskscenario",
                            "object": ri,
                        }
                    )

            if ri["treatment"] == "accepted":
                if not ri.get("riskacceptance_set", {}).get("exists", lambda: False)():
                    warnings_lst.append(
                        {
                            "msg": _(
                                "{} risk accepted but no risk acceptance attached"
                            ).format(ri),
                            "msgid": "riskScenarioAcceptedNoAcceptance",
                            "link": f"risk-scenarios/{ri['id']}",
                            "obj_type": "riskscenario",
                            "object": ri,
                        }
                    )
        # --- checks on the applied controls
        _measures = serializers.serialize(
            "json",
            AppliedControl.objects.filter(
                risk_scenarios__risk_assessment=self
            ).order_by("created_at"),
        )
        measures = [x["fields"] for x in json.loads(_measures)]
        for i in range(len(measures)):
            measures[i]["id"] = json.loads(_measures)[i]["pk"]

        for mtg in measures:
            if not mtg["eta"] and not mtg["status"] == "active":
                warnings_lst.append(
                    {
                        "msg": _("{} does not have an ETA").format(mtg["name"]),
                        "msgid": "appliedControlNoETA",
                        "link": f"applied-controls/{mtg['id']}",
                        "obj_type": "appliedcontrol",
                        "object": {"name": mtg["name"], "id": mtg["id"]},
                    }
                )
            elif mtg["eta"] and not mtg["status"] == "active":
                if date.today() > datetime.strptime(mtg["eta"], "%Y-%m-%d").date():
                    errors_lst.append(
                        {
                            "msg": _(
                                "{} ETA is in the past now. Consider updating its status or the date"
                            ).format(mtg["name"]),
                            "msgid": "appliedControlETAInPast",
                            "link": f"applied-controls/{mtg['id']}",
                            "obj_type": "appliedcontrol",
                            "object": {"name": mtg["name"], "id": mtg["id"]},
                        }
                    )

            if not mtg["effort"]:
                warnings_lst.append(
                    {
                        "msg": _(
                            "{} does not have an estimated effort. This will help you for prioritization"
                        ).format(mtg["name"]),
                        "msgid": "appliedControlNoEffort",
                        "link": f"applied-controls/{mtg['id']}",
                        "obj_type": "appliedcontrol",
                        "object": {"name": mtg["name"], "id": mtg["id"]},
                    }
                )

            if not mtg["cost"]:
                warnings_lst.append(
                    {
                        "msg": _(
                            "{} does not have an estimated cost. This will help you for prioritization"
                        ).format(mtg["name"]),
                        "msgid": "appliedControlNoCost",
                        "link": f"applied-controls/{mtg['id']}",
                        "obj_type": "appliedcontrol",
                        "object": {"name": mtg["name"], "id": mtg["id"]},
                    }
                )

            if not mtg["link"]:
                info_lst.append(
                    {
                        "msg": _(
                            "{}: Applied control does not have an external link attached. This will help you for follow-up"
                        ).format(mtg["name"]),
                        "msgid": "appliedControlNoLink",
                        "link": f"applied-controls/{mtg['id']}",
                        "obj_type": "appliedcontrol",
                        "object": {"name": mtg["name"], "id": mtg["id"]},
                    }
                )

        # --- checks on the risk acceptances
        _acceptances = serializers.serialize(
            "json",
            RiskAcceptance.objects.filter(risk_scenarios__risk_assessment=self)
            .distinct()
            .order_by("created_at"),
        )
        acceptances = [x["fields"] for x in json.loads(_acceptances)]
        for i in range(len(acceptances)):
            acceptances[i]["id"] = json.loads(_acceptances)[i]["pk"]
        for ra in acceptances:
            if not ra["expiry_date"]:
                warnings_lst.append(
                    {
                        "msg": _("{}: Acceptance has no expiry date").format(
                            ra["name"]
                        ),
                        "msgid": "riskAcceptanceNoExpiryDate",
                        "link": f"risk-acceptances/{ra['id']}",
                        "obj_type": "appliedcontrol",
                        "object": ra,
                    }
                )
                continue
            if date.today() > datetime.strptime(ra["expiry_date"], "%Y-%m-%d").date():
                errors_lst.append(
                    {
                        "msg": _(
                            "{}: Acceptance has expired. Consider updating the status or the date"
                        ).format(ra["name"]),
                        "msgid": "riskAcceptanceExpired",
                        "link": f"risk-acceptances/{ra['id']}",
                        "obj_type": "riskacceptance",
                        "object": ra,
                    }
                )

        findings = {
            "errors": errors_lst,
            "warnings": warnings_lst,
            "info": info_lst,
            "count": sum([len(errors_lst), len(warnings_lst), len(info_lst)]),
        }
        return findings

    # NOTE: if your save() method throws an exception, you might want to override the clean() method to prevent
    # 500 errors when the form submitted. See https://docs.djangoproject.com/en/dev/ref/models/instances/#django.db.models.Model.clean


def risk_scoring(probability, impact, risk_matrix: RiskMatrix) -> int:
    fields = risk_matrix.json_definition
    risk_index = fields["grid"][probability][impact]
    return risk_index


class RiskScenario(NameDescriptionMixin):
    TREATMENT_OPTIONS = [
        ("open", _("Open")),
        ("mitigate", _("Mitigate")),
        ("accept", _("Accept")),
        ("avoid", _("Avoid")),
        ("transfer", _("Transfer")),
    ]

    QUALIFICATIONS = [
        ("Confidentiality", _("Confidentiality")),
        ("Integrity", _("Integrity")),
        ("Availability", _("Availability")),
        ("Proof", _("Proof")),
        ("Authenticity", _("Authenticity")),
        ("Privacy", _("Privacy")),
        ("Safety", _("Safety")),
        ("Reputation", _("Reputation")),
        ("Operational", _("Operational")),
        ("Legal", _("Legal")),
        ("Financial", _("Financial")),
    ]

    DEFAULT_SOK_OPTIONS = {
        -1: {
            "name": _("--"),
            "description": _(
                "The strength of the knowledge supporting the assessment is undefined"
            ),
        },
        0: {
            "name": _("Low"),
            "description": _(
                "The strength of the knowledge supporting the assessment is low"
            ),
            "symbol": "◇",
        },
        1: {
            "name": _("Medium"),
            "description": _(
                "The strength of the knowledge supporting the assessment is medium"
            ),
            "symbol": "⬙",
        },
        2: {
            "name": _("High"),
            "description": _(
                "The strength of the knowledge supporting the assessment is high"
            ),
            "symbol": "◆",
        },
    }

    risk_assessment = models.ForeignKey(
        RiskAssessment,
        on_delete=models.CASCADE,
        verbose_name=_("RiskAssessment"),
        related_name="risk_scenarios",
    )
    assets = models.ManyToManyField(
        Asset,
        verbose_name=_("Assets"),
        blank=True,
        help_text=_("Assets impacted by the risk scenario"),
        related_name="risk_scenarios",
    )
    vulnerabilities = models.ManyToManyField(
        Vulnerability,
        verbose_name=_("Vulnerabilities"),
        blank=True,
        help_text=_("Vulnerabities exploited by the risk scenario"),
        related_name="risk_scenarios",
    )
    applied_controls = models.ManyToManyField(
        AppliedControl,
        verbose_name=_("Applied controls"),
        blank=True,
        related_name="risk_scenarios",
    )
    threats = models.ManyToManyField(
        Threat,
        verbose_name=_("Threats"),
        blank=True,
        related_name="risk_scenarios",
    )
    existing_controls = models.TextField(
        max_length=2000,
        help_text=_(
            "The existing controls to manage this risk. Edit the risk scenario to add extra applied controls."
        ),
        verbose_name=_("Existing controls"),
        blank=True,
    )
    existing_applied_controls = models.ManyToManyField(
        AppliedControl,
        verbose_name=_("Existing Applied controls"),
        blank=True,
        related_name="risk_scenarios_e",
    )

    owner = models.ManyToManyField(
        User,
        blank=True,
        verbose_name=_("Owner"),
        related_name="risk_scenarios",
    )
    # current
    current_proba = models.SmallIntegerField(
        default=-1, verbose_name=_("Current probability")
    )
    current_impact = models.SmallIntegerField(
        default=-1, verbose_name=_("Current impact")
    )
    current_level = models.SmallIntegerField(
        default=-1,
        verbose_name=_("Current level"),
        help_text=_(
            "The risk level given the current measures. Automatically updated on Save, based on the chosen risk matrix"
        ),
    )

    # residual
    residual_proba = models.SmallIntegerField(
        default=-1, verbose_name=_("Residual probability")
    )
    residual_impact = models.SmallIntegerField(
        default=-1, verbose_name=_("Residual impact")
    )
    residual_level = models.SmallIntegerField(
        default=-1,
        verbose_name=_("Residual level"),
        help_text=_(
            "The risk level when all the extra measures are done. Automatically updated on Save, based on the chosen risk matrix"
        ),
    )

    treatment = models.CharField(
        max_length=20,
        choices=TREATMENT_OPTIONS,
        default="open",
        verbose_name=_("Treatment status"),
    )

    ref_id = models.CharField(
        max_length=100, blank=True, verbose_name=_("Reference ID")
    )

    qualifications = models.JSONField(default=list, verbose_name=_("Qualifications"))

    strength_of_knowledge = models.IntegerField(
        default=-1,
        verbose_name=_("Strength of Knowledge"),
        help_text=_("The strength of the knowledge supporting the assessment"),
    )
    justification = models.CharField(
        max_length=500, blank=True, null=True, verbose_name=_("Justification")
    )
    security_exceptions = models.ManyToManyField(
        SecurityException,
        blank=True,
        verbose_name="Security exceptions",
        related_name="risk_scenarios",
    )

    fields_to_check = ["name"]

    class Meta:
        verbose_name = _("Risk scenario")
        verbose_name_plural = _("Risk scenarios")

    # def get_rating_options(self, field: str) -> list[tuple]:
    #     risk_matrix = self.risk_assessment.risk_matrix.parse_json()
    #     return [(k, v) for k, v in risk_matrix.fields[field].items()]

    @classmethod
    def get_default_ref_id(cls, risk_assessment: RiskAssessment):
        """return associated risk assessment id"""
        scenarios_ref_ids = [x.ref_id for x in risk_assessment.risk_scenarios.all()]
        nb_scenarios = len(scenarios_ref_ids) + 1
        candidates = [f"R.{i}" for i in range(1, nb_scenarios + 1)]
        return next(x for x in candidates if x not in scenarios_ref_ids)

    def parent_perimeter(self):
        return self.risk_assessment.perimeter

    parent_perimeter.short_description = _("Perimeter")

    def get_matrix(self):
        return self.risk_assessment.risk_matrix.parse_json_translated()

    def get_current_risk(self):
        if self.current_level < 0:
            return {
                "abbreviation": "--",
                "name": "--",
                "description": "not rated",
                "hexcolor": "#A9A9A9",
                "value": -1,
            }
        risk_matrix = self.get_matrix()
        current_risk = {
            **risk_matrix["risk"][self.current_level],
            "value": self.current_level,
        }
        update_translations_in_object(current_risk)
        return current_risk

    def get_current_impact(self):
        if self.current_impact < 0:
            return {
                "abbreviation": "--",
                "name": "--",
                "description": "not rated",
                "value": -1,
            }
        risk_matrix = self.get_matrix()
        return {
            **risk_matrix["impact"][self.current_impact],
            "value": self.current_impact,
        }

    def get_current_proba(self):
        if self.current_proba < 0:
            return {
                "abbreviation": "--",
                "name": "--",
                "description": "not rated",
                "value": -1,
            }
        risk_matrix = self.get_matrix()
        return {
            **risk_matrix["probability"][self.current_proba],
            "value": self.current_proba,
        }

    def get_residual_risk(self):
        if self.residual_level < 0:
            return {
                "abbreviation": "--",
                "name": "--",
                "description": "not rated",
                "hexcolor": "#A9A9A9",
                "value": -1,
            }
        risk_matrix = self.get_matrix()
        residual_risk = {
            **risk_matrix["risk"][self.residual_level],
            "value": self.residual_level,
        }
        update_translations_in_object(residual_risk)
        return residual_risk

    def get_residual_impact(self):
        if self.residual_impact < 0:
            return {
                "abbreviation": "--",
                "name": "--",
                "description": "not rated",
                "value": -1,
            }
        risk_matrix = self.get_matrix()
        return {
            **risk_matrix["impact"][self.residual_impact],
            "value": self.residual_impact,
        }

    def get_residual_proba(self):
        if self.residual_proba < 0:
            return {
                "abbreviation": "--",
                "name": "--",
                "description": "not rated",
                "value": -1,
            }
        risk_matrix = self.get_matrix()
        return {
            **risk_matrix["probability"][self.residual_proba],
            "value": self.residual_proba,
        }

    def get_strength_of_knowledge(self):
        if self.strength_of_knowledge < 0:
            return self.DEFAULT_SOK_OPTIONS[-1]
        return self.DEFAULT_SOK_OPTIONS[self.strength_of_knowledge]

    def __str__(self):
        return str(self.parent_perimeter()) + _(": ") + str(self.name)

    def save(self, *args, **kwargs):
        if self.current_proba >= 0 and self.current_impact >= 0:
            self.current_level = risk_scoring(
                self.current_proba,
                self.current_impact,
                self.risk_assessment.risk_matrix,
            )
        else:
            self.current_level = -1
        if self.residual_proba >= 0 and self.residual_impact >= 0:
            self.residual_level = risk_scoring(
                self.residual_proba,
                self.residual_impact,
                self.risk_assessment.risk_matrix,
            )
        else:
            self.residual_level = -1
        super(RiskScenario, self).save(*args, **kwargs)
        self.risk_assessment.upsert_daily_metrics()


class ComplianceAssessment(Assessment):
    framework = models.ForeignKey(
        Framework, on_delete=models.CASCADE, verbose_name=_("Framework")
    )
    selected_implementation_groups = models.JSONField(
        blank=True, null=True, verbose_name=_("Selected implementation groups")
    )
    ref_id = models.CharField(
        max_length=100, null=True, blank=True, verbose_name=_("reference id")
    )
    # score system is suggested by the framework, but can be changed at the start of the assessment
    min_score = models.IntegerField(null=True, verbose_name=_("Minimum score"))
    max_score = models.IntegerField(null=True, verbose_name=_("Maximum score"))
    scores_definition = models.JSONField(
        blank=True, null=True, verbose_name=_("Score definition")
    )
    show_documentation_score = models.BooleanField(default=False)

    assets = models.ManyToManyField(
        Asset,
        verbose_name=_("Related assets"),
        blank=True,
        help_text=_("Assets related to the compliance assessment"),
        related_name="compliance_assessments",
    )

    fields_to_check = ["name", "version"]

    class Meta:
        verbose_name = _("Compliance assessment")
        verbose_name_plural = _("Compliance assessments")

    def upsert_daily_metrics(self):
        per_status = dict()
        per_result = dict()
        for item in self.get_requirements_status_count():
            per_status[item[1]] = item[0]

        for item in self.get_requirements_result_count():
            per_result[item[1]] = item[0]
        total = RequirementAssessment.objects.filter(compliance_assessment=self).count()
        data = {
            "reqs": {
                "total": total,
                "per_status": per_status,
                "per_result": per_result,
                "progress_perc": self.get_progress(),
                "score": self.get_global_score(),
            },
        }

        HistoricalMetric.update_daily_metric(
            model=self.__class__.__name__, object_id=self.id, data=data
        )

    def save(self, *args, **kwargs) -> None:
        if self.min_score is None:
            self.min_score = self.framework.min_score
            self.max_score = self.framework.max_score
            self.scores_definition = self.framework.scores_definition
        super().save(*args, **kwargs)
        self.upsert_daily_metrics()

    def create_requirement_assessments(
        self, baseline: Self | None = None
    ) -> list["RequirementAssessment"]:
        # Fetch all requirements in a single query
        requirements = RequirementNode.objects.filter(
            framework=self.framework
        ).select_related()

        # If there's a baseline, prefetch all related baseline assessments in one query
        baseline_assessments = {}
        if baseline and baseline.framework == self.framework:
            baseline_assessments = {
                ra.requirement_id: ra
                for ra in RequirementAssessment.objects.filter(
                    compliance_assessment=baseline, requirement__in=requirements
                ).prefetch_related("evidences", "applied_controls")
            }

        # Create all RequirementAssessment objects in bulk
        requirement_assessments = [
            RequirementAssessment(
                compliance_assessment=self,
                requirement=requirement,
                folder_id=self.folder.id,  # Use foreign key directly
                answers=transform_questions_to_answers(requirement.questions)
                if requirement.questions
                else {},
            )
            for requirement in requirements
        ]

        # Bulk create all assessments
        created_assessments = RequirementAssessment.objects.bulk_create(
            requirement_assessments
        )

        # If there's a baseline, update the created assessments with baseline data
        if baseline_assessments:
            updates = []
            m2m_operations = []

            for assessment in created_assessments:
                baseline_assessment = baseline_assessments.get(
                    assessment.requirement_id
                )
                if baseline_assessment:
                    # Update scalar fields
                    assessment.result = baseline_assessment.result
                    assessment.status = baseline_assessment.status
                    assessment.score = baseline_assessment.score
                    assessment.documentation_score = (
                        baseline_assessment.documentation_score
                    )
                    assessment.is_scored = baseline_assessment.is_scored
                    assessment.observation = baseline_assessment.observation
                    updates.append(assessment)

                    # Store M2M operations for later
                    m2m_operations.append(
                        (
                            assessment,
                            baseline_assessment.evidences.all(),
                            baseline_assessment.applied_controls.all(),
                        )
                    )

            # Bulk update scalar fields
            if updates:
                RequirementAssessment.objects.bulk_update(
                    updates,
                    [
                        "result",
                        "status",
                        "score",
                        "documentation_score",
                        "is_scored",
                        "observation",
                    ],
                )

            # Handle M2M relationships
            for assessment, evidences, controls in m2m_operations:
                assessment.evidences.set(evidences)
                assessment.applied_controls.set(controls)

        return created_assessments

    def sync_to_applied_controls(self, dry_run=True):
        """
        the logic is to get the requirement assessments that have applied controls attached
        then for each:
        if one applied control attached:
            if the AC status is active, toggle requirement assessment to compliant
            if the AC status is in any other status, toggle the requirement assessment to non_compliant
        if two or more applied controls are attached:
            if all AC are active, toggle to compliant
            if at least one AC is active, toggle to partially compliant
            else toggle to non_compliant
        """

        def infer_result(applied_controls):
            if not applied_controls:
                return RequirementAssessment.Result.NOT_ASSESSED

            if len(applied_controls) == 1:
                ac_status = applied_controls[0].status
                if ac_status == AppliedControl.Status.ACTIVE:
                    return RequirementAssessment.Result.COMPLIANT
                else:
                    return RequirementAssessment.Result.NON_COMPLIANT

            statuses = [ac.status for ac in applied_controls]

            if all(status == AppliedControl.Status.ACTIVE for status in statuses):
                return RequirementAssessment.Result.COMPLIANT
            elif AppliedControl.Status.ACTIVE in statuses:
                return RequirementAssessment.Result.PARTIALLY_COMPLIANT
            else:
                return RequirementAssessment.Result.NON_COMPLIANT

        changes = dict()
        requirement_assessments_with_ac = RequirementAssessment.objects.filter(
            compliance_assessment=self, applied_controls__isnull=False
        ).distinct()
        with transaction.atomic():
            for ra in requirement_assessments_with_ac:
                ac = AppliedControl.objects.filter(requirement_assessments=ra)
                ic(ac)
                new_result = infer_result(ac)
                if ra.result != new_result:
                    changes[str(ra.id)] = {
                        "str": str(ra),
                        "current": ra.result,
                        "new": new_result,
                    }
                    if not dry_run:
                        ra.result = new_result
                        ra.save(update_fields=["result"])

        ic(changes)

        if dry_run:
            return changes

    def get_global_score(self):
        requirement_assessments_scored = (
            RequirementAssessment.objects.filter(compliance_assessment=self)
            .exclude(status=RequirementAssessment.Result.NOT_APPLICABLE)
            .exclude(is_scored=False)
            .exclude(requirement__assessable=False)
        )
        ig = (
            set(self.selected_implementation_groups)
            if self.selected_implementation_groups
            else None
        )
        score = 0
        n = 0

        for ras in requirement_assessments_scored:
            if not (ig) or (ig & set(ras.requirement.implementation_groups or [])):
                score += ras.score or 0
                n += 1
                if self.show_documentation_score:
                    score += ras.documentation_score or 0
                    n += 1
        if n > 0:
            global_score = score / n
            # We use this instead of using the python round function so that the python backend outputs the same result as the javascript frontend.
            return int(global_score * 10) / 10
        else:
            return -1

    def get_selected_implementation_groups(self):
        framework = self.framework
        if (
            not framework.implementation_groups_definition
            or not self.selected_implementation_groups
        ):
            return []
        return [
            group.get("name")
            for group in framework.implementation_groups_definition
            if group.get("ref_id") in self.selected_implementation_groups
        ]

    def get_requirement_assessments(self, include_non_assessable: bool):
        """
        Returns sorted assessable requirement assessments based on the selected implementation groups.
        If include_non_assessable is True, it returns all requirements regardless of their assessable status.
        """
        if not self.selected_implementation_groups:
            requirements = RequirementAssessment.objects.filter(
                compliance_assessment=self
            )
            if not include_non_assessable:
                requirements = requirements.filter(requirement__assessable=True)
            return requirements.order_by("requirement__order_id")

        selected_implementation_groups_set = set(self.selected_implementation_groups)
        requirements = RequirementAssessment.objects.filter(compliance_assessment=self)
        if not include_non_assessable:
            requirements = requirements.filter(requirement__assessable=True)

        requirements = requirements.order_by("requirement__order_id")

        requirement_assessments_list = [
            requirement
            for requirement in requirements
            if selected_implementation_groups_set
            & set(
                requirement.requirement.implementation_groups
                if requirement.requirement.implementation_groups
                else []
            )
        ]

        return requirement_assessments_list

    def get_threats_metrics(self):
        # Check if the framework has any threats mappings
        has_threats = RequirementNode.objects.filter(
            framework=self.framework, threats__isnull=False
        ).exists()

        if not has_threats:
            return {
                "threats": [],
                "total_unique_threats": 0,
                "total_non_compliant": 0,
                "total_partially_compliant": 0,
            }

        problematic_assessments = [
            assessment
            for assessment in self.get_requirement_assessments(
                include_non_assessable=False
            )
            if assessment.result
            in [
                RequirementAssessment.Result.PARTIALLY_COMPLIANT,
                RequirementAssessment.Result.NON_COMPLIANT,
            ]
        ]

        threat_metrics = {}

        # Process each problematic requirement assessment
        for assessment in problematic_assessments:
            threats = assessment.requirement.threats.all()

            for threat in threats:
                if threat.id not in threat_metrics:
                    threat_metrics[threat.id] = {
                        "id": threat.id,
                        "name": threat.name,
                        "display_long": threat.display_long,
                        "urn": threat.urn,
                        "non_compliant_count": 0,
                        "partially_compliant_count": 0,
                        "total_issues": 0,
                        "requirement_assessments": [],
                    }

                if assessment.result == RequirementAssessment.Result.NON_COMPLIANT:
                    threat_metrics[threat.id]["non_compliant_count"] += 1
                elif (
                    assessment.result
                    == RequirementAssessment.Result.PARTIALLY_COMPLIANT
                ):
                    threat_metrics[threat.id]["partially_compliant_count"] += 1

                threat_metrics[threat.id]["total_issues"] += 1

                if assessment.id not in [
                    ra.get("id")
                    for ra in threat_metrics[threat.id]["requirement_assessments"]
                ]:
                    threat_metrics[threat.id]["requirement_assessments"].append(
                        {
                            "id": assessment.id,
                            "requirement_id": assessment.requirement.id,
                            "requirement_name": assessment.requirement.display_short,
                            "result": assessment.result,
                        }
                    )

        return {
            "threats": list(threat_metrics.values()),
            "total_unique_threats": len(threat_metrics),
            "total_non_compliant": sum(
                t["non_compliant_count"] for t in threat_metrics.values()
            ),
            "total_partially_compliant": sum(
                t["partially_compliant_count"] for t in threat_metrics.values()
            ),
        }

    def get_requirements_status_count(self):
        requirements_status_count = []
        for st in RequirementAssessment.Status:
            requirements_status_count.append(
                (
                    RequirementAssessment.objects.filter(status=st)
                    .filter(compliance_assessment=self)
                    .count(),
                    st,
                )
            )
        return requirements_status_count

    def get_requirements_result_count(self):
        requirements_result_count = []
        selected_implementation_groups_set = (
            set(self.selected_implementation_groups)
            if self.selected_implementation_groups
            else None
        )

        requirements = RequirementAssessment.objects.filter(
            compliance_assessment=self, requirement__assessable=True
        ).select_related("requirement")

        if selected_implementation_groups_set is not None:
            result_groups = {}
            for req in requirements:
                req_groups = set(req.requirement.implementation_groups or [])
                if selected_implementation_groups_set & req_groups:
                    result_groups.setdefault(req.result, []).append(req)

            for rs in RequirementAssessment.Result:
                count = len(result_groups.get(rs, []))
                requirements_result_count.append((count, rs))
        else:
            for rs in RequirementAssessment.Result:
                count = requirements.filter(result=rs).count()
                requirements_result_count.append((count, rs))

        return requirements_result_count

    def get_measures_status_count(self):
        measures_status_count = []
        measures_list = []
        for requirement_assessment in self.requirement_assessments.all():
            measures_list += requirement_assessment.applied_controls.all().values_list(
                "id", flat=True
            )
        for st in "AppliedControl".Status.choices:
            measures_status_count.append(
                (
                    "AppliedControl".objects.filter(status=st[0])
                    .filter(id__in=measures_list)
                    .count(),
                    st,
                )
            )
        return measures_status_count

    def donut_render(self) -> dict:
        def union_queries(base_query, groups, field_name):
            queries = [
                base_query.filter(**{f"{field_name}__icontains": group}).distinct()
                for group in groups
            ]
            return queries[0].union(*queries[1:]) if queries else base_query.none()

        color_map = {
            RequirementAssessment.Result.NOT_ASSESSED: "#d1d5db",
            RequirementAssessment.Result.NON_COMPLIANT: "#f87171",
            RequirementAssessment.Result.PARTIALLY_COMPLIANT: "#fde047",
            RequirementAssessment.Result.COMPLIANT: "#86efac",
            RequirementAssessment.Result.NOT_APPLICABLE: "#000000",
            RequirementAssessment.Status.TODO: "#9ca3af",
            RequirementAssessment.Status.IN_PROGRESS: "#f59e0b",
            RequirementAssessment.Status.IN_REVIEW: "#3b82f6",
            RequirementAssessment.Status.DONE: "#86efac",
        }

        compliance_assessments_result = {"values": [], "labels": []}
        for result in RequirementAssessment.Result.values:
            assessable_requirements_filter = {
                "compliance_assessment": self,
                "requirement__assessable": True,
            }

            base_query = RequirementAssessment.objects.filter(
                result=result, **assessable_requirements_filter
            ).distinct()

            if self.selected_implementation_groups:
                union_query = union_queries(
                    base_query,
                    self.selected_implementation_groups,
                    "requirement__implementation_groups",
                )
            else:
                union_query = base_query

            count = union_query.count()
            value_entry = {
                "name": result,
                "localName": camel_case(result),
                "value": count,
                "itemStyle": {"color": color_map[result]},
            }

            compliance_assessments_result["values"].append(value_entry)
            compliance_assessments_result["labels"].append(result)

        compliance_assessments_status = {"values": [], "labels": []}
        for status in RequirementAssessment.Status.values:
            assessable_requirements_filter = {
                "compliance_assessment": self,
                "requirement__assessable": True,
            }

            base_query = RequirementAssessment.objects.filter(
                status=status, **assessable_requirements_filter
            ).distinct()

            if self.selected_implementation_groups:
                union_query = union_queries(
                    base_query,
                    self.selected_implementation_groups,
                    "requirement__implementation_groups",
                )
            else:
                union_query = base_query

            count = union_query.count()
            value_entry = {
                "name": status,
                "localName": camel_case(status),
                "value": count,
                "itemStyle": {"color": color_map[status]},
            }

            compliance_assessments_status["values"].append(value_entry)
            compliance_assessments_status["labels"].append(status)

        return {
            "result": compliance_assessments_result,
            "status": compliance_assessments_status,
        }

    def quality_check(self) -> dict:
        AppliedControl = apps.get_model("core", "AppliedControl")

        errors_lst = list()
        warnings_lst = list()
        info_lst = list()
        # --- check on the assessment:
        _object = serializers.serialize("json", [self])
        _object = json.loads(_object)
        if self.status == Assessment.Status.IN_PROGRESS:
            info_lst.append(
                {
                    "msg": _("{}: Compliance assessment is still in progress").format(
                        str(self)
                    ),
                    "msgid": "complianceAssessmentInProgress",
                    "obj_type": "complianceassessment",
                    "object": _object,
                }
            )

        if not self.authors.all():
            info_lst.append(
                {
                    "msg": _(
                        "{}: No author assigned to this compliance assessment"
                    ).format(str(self)),
                    "msgid": "complianceAssessmentNoAuthor",
                    "obj_type": "complianceassessment",
                    "object": _object,
                }
            )
        # ---

        # --- check on requirement assessments:
        _requirement_assessments = self.requirement_assessments.all().order_by(
            "created_at"
        )
        requirement_assessments = []
        for ra in _requirement_assessments:
            ra_dict = json.loads(serializers.serialize("json", [ra]))[0]["fields"]
            ra_dict["name"] = str(ra)
            ra_dict["id"] = ra.id
            requirement_assessments.append(ra_dict)
        for requirement_assessment in requirement_assessments:
            if (
                requirement_assessment["result"] in ("compliant", "partially_compliant")
                and len(requirement_assessment["applied_controls"]) == 0
            ):
                warnings_lst.append(
                    {
                        "msg": _(
                            "{}: Requirement assessment result is compliant or partially compliant with no applied control applied"
                        ).format(requirement_assessment["name"]),
                        "msgid": "requirementAssessmentNoAppliedControl",
                        "link": f"requirement-assessments/{requirement_assessment['id']}",
                        "obj_type": "requirementassessment",
                        "object": requirement_assessment,
                    }
                )
        # ---

        # --- check on applied controls:
        _applied_controls = serializers.serialize(
            "json",
            AppliedControl.objects.filter(
                requirement_assessments__compliance_assessment=self
            ).order_by("created_at"),
        )
        applied_controls = [x["fields"] for x in json.loads(_applied_controls)]
        for i in range(len(applied_controls)):
            applied_controls[i]["id"] = json.loads(_applied_controls)[i]["pk"]
        for applied_control in applied_controls:
            if not applied_control["reference_control"]:
                info_lst.append(
                    {
                        "msg": _(
                            "{}: Applied control has no reference control selected"
                        ).format(applied_control["name"]),
                        "msgid": "appliedControlNoReferenceControl",
                        "link": f"applied-controls/{applied_control['id']}",
                        "obj_type": "appliedcontrol",
                        "object": applied_control,
                    }
                )
        # ---

        # --- check on evidence:
        _evidences = serializers.serialize(
            "json",
            Evidence.objects.filter(
                applied_controls__in=AppliedControl.objects.filter(
                    requirement_assessments__compliance_assessment=self
                )
            ).order_by("created_at"),
        )
        evidences = [x["fields"] for x in json.loads(_evidences)]
        for i in range(len(evidences)):
            evidences[i]["id"] = json.loads(_evidences)[i]["pk"]
        for evidence in evidences:
            if not evidence["attachment"]:
                warnings_lst.append(
                    {
                        "msg": _("{}: Evidence has no file uploaded").format(
                            evidence["name"]
                        ),
                        "msgid": "evidenceNoFile",
                        "link": f"evidences/{evidence['id']}",
                        "obj_type": "evidence",
                        "object": evidence,
                    }
                )

        findings = {
            "errors": errors_lst,
            "warnings": warnings_lst,
            "info": info_lst,
            "count": sum([len(errors_lst), len(warnings_lst), len(info_lst)]),
        }
        return findings

    def compute_requirement_assessments_results(
        self, mapping_set: RequirementMappingSet, source_assessment: Self
    ) -> list["RequirementAssessment"]:
        requirement_assessments: list[RequirementAssessment] = []
        result_order = (
            RequirementAssessment.Result.NOT_ASSESSED,
            RequirementAssessment.Result.NOT_APPLICABLE,
            RequirementAssessment.Result.NON_COMPLIANT,
            RequirementAssessment.Result.PARTIALLY_COMPLIANT,
            RequirementAssessment.Result.COMPLIANT,
        )

        def assign_attributes(target, attributes):
            """
            Helper function to assign attributes to a target object.
            Only assigns if the attribute is not None.
            """
            keys = ["result", "status", "score", "is_scored", "observation"]
            for key, value in zip(keys, attributes):
                if value is not None:
                    setattr(target, key, value)

        for requirement_assessment in self.requirement_assessments.all():
            mappings = mapping_set.mappings.filter(
                target_requirement=requirement_assessment.requirement
            )
            inferences = []
            refs = []

            # Filter for full coverage relationships if applicable
            if mappings.filter(
                relationship__in=RequirementMapping.FULL_COVERAGE_RELATIONSHIPS
            ).exists():
                mappings = mappings.filter(
                    relationship__in=RequirementMapping.FULL_COVERAGE_RELATIONSHIPS
                )

            for mapping in mappings:
                source_requirement_assessment = RequirementAssessment.objects.get(
                    compliance_assessment=source_assessment,
                    requirement=mapping.source_requirement,
                )
                inferred_result = requirement_assessment.infer_result(
                    mapping=mapping,
                    source_requirement_assessment=source_requirement_assessment,
                )
                if inferred_result.get("result") in result_order:
                    inferences.append(
                        (
                            inferred_result.get("result"),
                            inferred_result.get("status"),
                            inferred_result.get("score"),
                            inferred_result.get("is_scored"),
                            inferred_result.get("observation"),
                        )
                    )
                    refs.append(source_requirement_assessment)

            if inferences:
                if len(inferences) == 1:
                    selected_inference = inferences[0]
                    ref = refs[0]
                else:
                    selected_inference = min(
                        inferences, key=lambda x: result_order.index(x[0])
                    )
                    ref = refs[inferences.index(selected_inference)]

                assign_attributes(requirement_assessment, selected_inference)
                requirement_assessment.mapping_inference = {
                    "result": requirement_assessment.result,
                    "source_requirement_assessment": {
                        "str": str(ref),
                        "id": str(ref.id),
                        "is_scored": ref.is_scored,
                        "score": ref.score,
                        "coverage": mapping.coverage,
                    },
                    # "mappings": [mapping.id for mapping in mappings],
                }
                requirement_assessment.save()
                requirement_assessments.append(requirement_assessment)

        return requirement_assessments

    def get_progress(self) -> int:
        requirement_assessments = list(
            self.get_requirement_assessments(include_non_assessable=False)
        )
        total_cnt = len(requirement_assessments)
        assessed_cnt = len(
            [
                r
                for r in requirement_assessments
                if r.result != RequirementAssessment.Result.NOT_ASSESSED
            ]
        )
        return int((assessed_cnt / total_cnt) * 100) if total_cnt > 0 else 0

    @property
    def answers_progress(self) -> int:
        requirement_assessments = self.get_requirement_assessments(
            include_non_assessable=False
        )
        total_questions_count = 0
        answered_questions_count = 0
        for ra in requirement_assessments:
            # if it has question set it should count
            if ra.requirement.questions:
                total_questions_count += len(ra.requirement.questions)
                answers = ra.answers
                if answers:
                    for answer in answers.values():
                        answered_questions_count += 1 if answer else 0

        if total_questions_count > 0:
            return int((answered_questions_count / total_questions_count) * 100)
        else:
            return 0

    @property
    def has_questions(self) -> bool:
        requirement_assessments = self.get_requirement_assessments(
            include_non_assessable=False
        )
        for ra in requirement_assessments:
            if ra.requirement.question:
                return True
        return False


class RequirementAssessment(AbstractBaseModel, FolderMixin, ETADueDateMixin):
    class Status(models.TextChoices):
        TODO = "to_do", _("To do")
        IN_PROGRESS = "in_progress", _("In progress")
        IN_REVIEW = "in_review", _("In review")
        DONE = "done", _("Done")

    class Result(models.TextChoices):
        NOT_ASSESSED = "not_assessed", _("Not assessed")
        PARTIALLY_COMPLIANT = "partially_compliant", _("Partially compliant")
        NON_COMPLIANT = "non_compliant", _("Non-compliant")
        COMPLIANT = "compliant", _("Compliant")
        NOT_APPLICABLE = "not_applicable", _("Not applicable")

    status = models.CharField(
        max_length=100,
        choices=Status.choices,
        default=Status.TODO,
        verbose_name=_("Status"),
    )
    result = models.CharField(
        max_length=64,
        choices=Result.choices,
        verbose_name=_("Result"),
        default=Result.NOT_ASSESSED,
    )
    is_scored = models.BooleanField(
        default=False,
        verbose_name=_("Is scored"),
    )
    score = models.IntegerField(
        blank=True,
        null=True,
        verbose_name=_("Score"),
    )
    documentation_score = models.IntegerField(
        blank=True, null=True, verbose_name=_("Documentation Score")
    )
    evidences = models.ManyToManyField(
        Evidence,
        blank=True,
        verbose_name=_("Evidences"),
        related_name="requirement_assessments",
    )
    observation = models.TextField(null=True, blank=True, verbose_name=_("Observation"))
    compliance_assessment = models.ForeignKey(
        ComplianceAssessment,
        on_delete=models.CASCADE,
        verbose_name=_("Compliance assessment"),
        related_name="requirement_assessments",
    )
    requirement = models.ForeignKey(
        RequirementNode, on_delete=models.CASCADE, verbose_name=_("Requirement")
    )
    applied_controls = models.ManyToManyField(
        "AppliedControl",
        blank=True,
        verbose_name=_("Applied controls"),
        related_name="requirement_assessments",
    )
    selected = models.BooleanField(
        default=True,
        verbose_name=_("Selected"),
    )
    mapping_inference = models.JSONField(
        default=dict,
        verbose_name=_("Mapping inference"),
    )
    answers = models.JSONField(
        blank=True,
        null=True,
        verbose_name=_("Answers"),
    )
    security_exceptions = models.ManyToManyField(
        SecurityException,
        blank=True,
        verbose_name="Security exceptions",
        related_name="requirement_assessments",
    )

    def __str__(self) -> str:
        return self.requirement.display_short

    def get_requirement_description(self) -> str:
        return get_referential_translation(
            {
                "description": self.requirement.description,
                "translations": self.requirement.translations,
            },
            "description",
        )

    def infer_result(
        self, mapping: RequirementMapping, source_requirement_assessment: Self
    ) -> dict | None:
        if mapping.coverage == RequirementMapping.Coverage.FULL:
            if (
                source_requirement_assessment.compliance_assessment.min_score
                == self.compliance_assessment.min_score
                and source_requirement_assessment.compliance_assessment.max_score
                == self.compliance_assessment.max_score
            ):
                return {
                    "result": source_requirement_assessment.result,
                    "status": source_requirement_assessment.status,
                    "score": source_requirement_assessment.score,
                    "is_scored": source_requirement_assessment.is_scored,
                    "observation": source_requirement_assessment.observation,
                }
            else:
                return {
                    "result": source_requirement_assessment.result,
                    "status": source_requirement_assessment.status,
                    "observation": source_requirement_assessment.observation,
                }
        if mapping.coverage == RequirementMapping.Coverage.PARTIAL:
            if source_requirement_assessment.result in (
                RequirementAssessment.Result.COMPLIANT,
                RequirementAssessment.Result.PARTIALLY_COMPLIANT,
            ):
                return {"result": RequirementAssessment.Result.PARTIALLY_COMPLIANT}
            if (
                source_requirement_assessment.result
                == RequirementAssessment.Result.NON_COMPLIANT
            ):
                return {"result": RequirementAssessment.Result.NON_COMPLIANT}
        return {}

    def create_applied_controls_from_suggestions(self) -> list[AppliedControl]:
        applied_controls: list[AppliedControl] = []
        for reference_control in self.requirement.reference_controls.all():
            try:
                _name = (
                    reference_control.get_name_translated or reference_control.ref_id
                )
                applied_control, created = AppliedControl.objects.get_or_create(
                    name=_name,
                    folder=self.folder,
                    reference_control=reference_control,
                    category=reference_control.category,
                )
                if created:
                    logger.info(
                        "Successfully created applied control from reference_control",
                        applied_control=applied_control,
                        reference_control=reference_control,
                    )
                else:
                    logger.info(
                        "Applied control already exists, skipping creation and using existing one",
                        applied_control=applied_control,
                        reference_control=reference_control,
                    )
                applied_controls.append(applied_control)
            except Exception as e:
                logger.error(
                    "An error occurred while creating applied control from reference control",
                    reference_control=reference_control,
                    exc_info=e,
                )
                continue
        if applied_controls:
            self.applied_controls.add(*applied_controls)
        return applied_controls

    class Meta:
        verbose_name = _("Requirement assessment")
        verbose_name_plural = _("Requirement assessments")

    def save(self, *args, **kwargs) -> None:
        super().save(*args, **kwargs)
        self.compliance_assessment.upsert_daily_metrics()


class FindingsAssessment(Assessment):
    class Category(models.TextChoices):
        UNDEFINED = "--", "Undefined"
        PENTEST = "pentest", "Pentest"
        AUDIT = "audit", "Audit"
        SELF_IDENTIFIED = "self_identified", "Self-identified"

    owner = models.ManyToManyField(
        User,
        blank=True,
        verbose_name=_("Owner"),
        related_name="findings_assessments",
    )

    category = models.CharField(
        verbose_name=_("Category"),
        choices=Category.choices,
        max_length=32,
        default=Category.UNDEFINED,
    )

    ref_id = models.CharField(
        max_length=100, null=True, blank=True, verbose_name=_("reference id")
    )

    def get_findings_metrics(self):
        findings = self.findings.all()
        total_count = findings.count()

        # Skip calculations if there are no findings
        if total_count == 0:
            return {
                "total_count": 0,
                "status_distribution": {},
                "severity_distribution": {},
                "unresolved_important_count": 0,
            }

        status_counts = {}
        for status_code, _ in Finding.Status.choices:
            status_counts[status_code] = findings.filter(status=status_code).count()

        # Severity distribution using the defined severity levels - we need a better way for this
        severity_values = {
            -1: "undefined",
            0: "low",
            1: "medium",
            2: "high",
            3: "critical",
        }

        severity_distribution = {}
        for value, label in severity_values.items():
            severity_distribution[label] = findings.filter(severity=value).count()

        # Count of unresolved important findings (severity is HIGH or CRITICAL)
        # Excludes findings that are mitigated, resolved, or dismissed
        unresolved_important = (
            findings.filter(
                severity__gte=2  # HIGH or CRITICAL (>=2)
            )
            .exclude(
                status__in=[
                    Finding.Status.MITIGATED,
                    Finding.Status.RESOLVED,
                    Finding.Status.DISMISSED,
                ]
            )
            .count()
        )

        return {
            "total_count": total_count,
            "status_distribution": status_counts,
            "severity_distribution": severity_distribution,
            "unresolved_important_count": unresolved_important,
        }


class Finding(NameDescriptionMixin, FolderMixin, FilteringLabelMixin):
    class Status(models.TextChoices):
        UNDEFINED = "--", _("Undefined")
        IDENTIFIED = "identified", _("Identified")
        CONFIRMED = "confirmed", _("Confirmed")
        DISMISSED = "dismissed", _("Dismissed")
        ASSIGNED = "assigned", _("Assigned")
        IN_PROGRESS = "in_progress", _("In Progress")
        MITIGATED = "mitigated", _("Mitigated")
        RESOLVED = "resolved", _("Resolved")
        DEPRECATED = "deprecated", _("Deprecated")

    findings_assessment = models.ForeignKey(
        FindingsAssessment, on_delete=models.CASCADE, related_name="findings"
    )
    vulnerabilities = models.ManyToManyField(
        Vulnerability,
        verbose_name=_("Vulnerabilities"),
        related_name="findings",
        blank=True,
    )
    reference_controls = models.ManyToManyField(
        ReferenceControl,
        verbose_name=_("Reference controls"),
        related_name="findings",
        blank=True,
    )
    applied_controls = models.ManyToManyField(
        AppliedControl,
        verbose_name=_("Applied controls"),
        related_name="findings",
        blank=True,
    )
    owner = models.ManyToManyField(
        User,
        blank=True,
        verbose_name=_("Owner"),
        related_name="findings",
    )

    ref_id = models.CharField(
        max_length=100, blank=True, verbose_name=_("Reference ID")
    )
    severity = models.SmallIntegerField(
        verbose_name="Severity", choices=Severity.choices, default=Severity.UNDEFINED
    )
    status = models.CharField(
        verbose_name="Status",
        choices=Status.choices,
        null=False,
        default=Status.UNDEFINED,
        max_length=32,
    )

    class Meta:
        verbose_name = _("Finding")
        verbose_name_plural = _("Findings")


########################### RiskAcesptance is a domain object relying on secondary objects #########################


class RiskAcceptance(NameDescriptionMixin, FolderMixin, PublishInRootFolderMixin):
    ACCEPTANCE_STATE = [
        ("created", "Created"),
        ("submitted", "Submitted"),
        ("accepted", "Accepted"),
        ("rejected", "Rejected"),
        ("revoked", "Revoked"),
    ]

    risk_scenarios = models.ManyToManyField(
        RiskScenario,
        verbose_name=_("Risk scenarios"),
        help_text=_(
            "Select the risk scenarios to be accepted, attention they must be part of the chosen domain"
        ),
    )
    approver = models.ForeignKey(
        User,
        max_length=200,
        help_text=_("Risk owner and approver identity"),
        verbose_name=_("Approver"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    state = models.CharField(
        max_length=20,
        choices=ACCEPTANCE_STATE,
        default="created",
        verbose_name=_("State"),
    )
    expiry_date = models.DateField(
        help_text=_("Specify when the risk acceptance will no longer apply"),
        null=True,
        verbose_name=_("Expiry date"),
    )
    accepted_at = models.DateTimeField(
        blank=True, null=True, verbose_name=_("Acceptance date")
    )
    rejected_at = models.DateTimeField(
        blank=True, null=True, verbose_name=_("Rejection date")
    )
    revoked_at = models.DateTimeField(
        blank=True, null=True, verbose_name=_("Revocation date")
    )
    justification = models.CharField(
        max_length=500, blank=True, null=True, verbose_name=_("Justification")
    )

    fields_to_check = ["name"]

    class Meta:
        permissions = [
            ("approve_riskacceptance", "Can validate/rejected risk acceptances")
        ]
        verbose_name = _("Risk acceptance")
        verbose_name_plural = _("Risk acceptances")

    def __str__(self):
        if self.name:
            return self.name
        scenario_names: str = ", ".join(
            [str(scenario) for scenario in self.risk_scenarios.all()]
        )
        return f"{scenario_names}"

    @property
    def get_html_url(self):
        url = reverse("riskacceptance-detail", args=(self.id,))
        return format_html(
            '<a class="" href="{}"> <b>[RA-exp]</b> {}: {} </a>',
            url,
            self.folder.name,
            self.name,
        )

    def set_state(self, state):
        self.state = state
        if state == "accepted":
            self.accepted_at = datetime.now()
            # iterate over the risk scenarios to set their treatment to accepted
            for scenario in self.risk_scenarios.all():
                scenario.treatment = "accept"
                scenario.save()
        if state == "rejected":
            self.rejected_at = datetime.now()
        elif state == "revoked":
            self.revoked_at = datetime.now()
        self.save()


# tasks management
class TaskTemplateManager(models.Manager):
    def create_task_template(self, **kwargs):
        return super().create(**kwargs)


class TaskTemplate(NameDescriptionMixin, FolderMixin):
    objects = TaskTemplateManager()

    SCHEDULE_JSONSCHEMA = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Schedule Definition",
        "type": "object",
        "properties": {
            "interval": {
                "type": "integer",
                "minimum": 1,
                "description": "Number of periods to wait before repeating (e.g., every 2 days, 3 weeks).",
            },
            "frequency": {
                "type": "string",
                "enum": ["DAILY", "WEEKLY", "MONTHLY", "YEARLY"],
            },
            "days_of_week": {
                "type": "array",
                "items": {"type": "integer", "minimum": 1, "maximum": 7},
                "description": "Optional. Days of the week (Monday=1, Sunday=7)",
            },
            "weeks_of_month": {
                "type": "array",
                "items": {
                    "type": "integer",
                    "minimum": -1,
                    "maximum": 4,
                },
                "description": "Optional. for a given weekday, which one in the month (1 for first, -1 for last)",
            },
            "months_of_year": {
                "type": "array",
                "items": {"type": "integer", "minimum": 1, "maximum": 12},
                "description": "Optional. Months of the year (1=January, 12=December)",
            },
            "end_date": {
                "type": ["string", "null"],
                "format": "date",
                "description": "Optional. Date when recurrence ends.",
            },
            "occurrences": {
                "type": ["integer", "null"],
                "minimum": 1,
                "description": "Optional. Number of occurrences before recurrence stops.",
            },
            "overdue_behavior": {
                "type": "string",
                "enum": ["DELAY_NEXT", "NO_IMPACT"],
                "default": "NO_IMPACT",
                "description": "Optional. Behavior when tasks become overdue.",
            },
            "exceptions": {
                "type": ["object", "null"],
                "description": "Optional. JSON object for future exceptions handling.",
            },
        },
        "required": ["interval", "frequency"],
        "additionalProperties": False,
    }

    task_date = models.DateField(null=True, blank=True, verbose_name="Date")

    is_recurrent = models.BooleanField(default=False)

    ref_id = models.CharField(
        max_length=100, null=True, blank=True, verbose_name="reference id"
    )

    schedule = models.JSONField(
        verbose_name="Schedule definition",
        blank=True,
        null=True,
        validators=[JSONSchemaInstanceValidator(SCHEDULE_JSONSCHEMA)],
    )
    enabled = models.BooleanField(default=True)

    assigned_to = models.ManyToManyField(
        User,
        verbose_name="Assigned to",
        blank=True,
    )
    assets = models.ManyToManyField(
        Asset,
        verbose_name="Related assets",
        blank=True,
        help_text="Assets related to the task",
        related_name="task_templates",
    )
    applied_controls = models.ManyToManyField(
        AppliedControl,
        verbose_name="Applied controls",
        blank=True,
        help_text="Applied controls related to the task",
        related_name="task_templates",
    )
    compliance_assessments = models.ManyToManyField(
        ComplianceAssessment,
        verbose_name="Compliance assessments",
        blank=True,
        help_text="Compliance assessments related to the task",
        related_name="task_templates",
    )
    risk_assessments = models.ManyToManyField(
        RiskAssessment,
        verbose_name="Risk assessments",
        blank=True,
        help_text="Risk assessments related to the task",
        related_name="task_templates",
    )

    @property
    def next_occurrence(self):
        today = datetime.today().date()
        task_nodes = TaskNode.objects.filter(
            task_template=self, due_date__gte=today
        ).order_by("due_date")
        return task_nodes.first().due_date if task_nodes.exists() else None

    @property
    def last_occurrence_status(self):
        today = datetime.today().date()
        task_nodes = TaskNode.objects.filter(
            task_template=self, due_date__lte=today
        ).order_by("-due_date")
        return task_nodes[0].status if task_nodes.exists() else None

    class Meta:
        verbose_name = "Task template"
        verbose_name_plural = "Task templates"

    def save(self, *args, **kwargs):
        if self.schedule and "days_of_week" in self.schedule:
            # Only modify values that are not already in range 0-6
            self.schedule["days_of_week"] = [
                day % 7 if day > 6 else day for day in self.schedule["days_of_week"]
            ]

        # Check if there are any TaskNode instances that are not within the date range
        if self.schedule and "end_date" in self.schedule:
            end_date = self.schedule["end_date"]
            end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
            # Delete TaskNode instances that have a due date after the end date
            TaskNode.objects.filter(task_template=self, due_date__gt=end_date).delete()
        super().save(*args, **kwargs)


class TaskNode(AbstractBaseModel, FolderMixin):
    TASK_STATUS_CHOICES = [
        ("pending", "Pending"),
        ("in_progress", "In progress"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]

    due_date = models.DateField(null=True, blank=True, verbose_name="Due date")

    status = models.CharField(
        max_length=50, default="pending", choices=TASK_STATUS_CHOICES
    )

    observation = models.TextField(verbose_name="Observation", blank=True, null=True)

    task_template = models.ForeignKey(
        "TaskTemplate",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    evidences = models.ManyToManyField(
        Evidence,
        blank=True,
        help_text="Evidences related to the task",
        related_name="task_nodes",
    )

    to_delete = models.BooleanField(default=False)

    @property
    def assigned_to(self):
        return self.task_template.assigned_to

    @property
    def assets(self):
        return self.task_template.assets.all()

    @property
    def applied_controls(self):
        return self.task_template.applied_controls.all()

    @property
    def compliance_assessments(self):
        return self.task_template.compliance_assessments.all()

    @property
    def risk_assessments(self):
        return self.task_template.risk_assessments.all()

    class Meta:
        verbose_name = "Task node"
        verbose_name_plural = "Task nodes"


common_exclude = ["created_at", "updated_at"]

auditlog.register(
    ReferenceControl,
    exclude_fields=common_exclude,
)
auditlog.register(
    AppliedControl,
    m2m_fields={"owner", "evidences"},
    exclude_fields=common_exclude,
)
auditlog.register(
    Threat,
    exclude_fields=common_exclude,
)
auditlog.register(
    ComplianceAssessment,
    m2m_fields={"authors"},
    exclude_fields=common_exclude,
)
auditlog.register(
    RequirementAssessment,
    m2m_fields={"applied_controls"},
    exclude_fields=common_exclude,
)
auditlog.register(
    RiskAssessment,
    m2m_fields={"authors"},
    exclude_fields=common_exclude,
)
auditlog.register(
    RiskScenario,
    m2m_fields={"owner", "applied_controls", "existing_applied_controls"},
    exclude_fields=common_exclude,
)
auditlog.register(
    FindingsAssessment,
    m2m_fields={"authors"},
    exclude_fields=common_exclude,
)
auditlog.register(
    Finding,
    m2m_fields={"applied_controls", "owner"},
    exclude_fields=common_exclude,
)
auditlog.register(
    Framework,
    exclude_fields=common_exclude,
)
auditlog.register(
    RiskAcceptance,
    m2m_fields={"risk_scenarios"},
    exclude_fields=common_exclude,
)
auditlog.register(
    Folder,
    exclude_fields=common_exclude,
)
auditlog.register(
    Perimeter,
    exclude_fields=common_exclude,
)
auditlog.register(
    Evidence,
    exclude_fields=common_exclude,
)
auditlog.register(
    Asset,
    exclude_fields=common_exclude,
    m2m_fields={"parent_assets"},
)
auditlog.register(
    SecurityException,
    exclude_fields=common_exclude,
)
auditlog.register(
    Vulnerability,
    exclude_fields=common_exclude,
)
auditlog.register(
    Incident,
    exclude_fields=common_exclude,
)
auditlog.register(
    TimelineEntry,
    exclude_fields=common_exclude,
)
# actions - 0: create, 1: update, 2: delete
