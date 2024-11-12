import json
import os
import re
from datetime import date, datetime
from pathlib import Path
from typing import Self, Type, Union

from rest_framework.renderers import status
import yaml
from django.apps import apps
from django.contrib.auth import get_user_model
from django.core import serializers
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, RegexValidator
from django.db import models, transaction
from django.db.models import Q
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

from .base_models import AbstractBaseModel, ETADueDateMixin, NameDescriptionMixin
from .utils import camel_case, sha256
from .validators import validate_file_name, validate_file_size

logger = get_logger(__name__)

User = get_user_model()


URN_REGEX = r"^urn:([a-zA-Z0-9_-]+):([a-zA-Z0-9_-]+):([a-zA-Z0-9_-]+)(?::([a-zA-Z0-9_-]+))?:([0-9A-Za-z\[\]\(\)\-\._:]+)$"


def match_urn(urn_string):
    match = re.match(URN_REGEX, urn_string)
    if match:
        return match.groups()  # Returns all captured groups from the regex match
    else:
        return None


def transform_question_to_answer(json_data):
    """
    Used during Requirement Assessment creation to create a questionnaire base on
    the Requirement Node question JSON field

    Args:
        json_data (json): JSON describing a questionnaire from a Requirement Node

    Returns:
        json: JSON formatted for the frontend to display a form
    """
    question_type = json_data.get("question_type", "")
    question_choices = json_data.get("question_choices", [])
    questions = json_data.get("questions", [])

    form_fields = []

    for question in questions:
        field = {}
        field["urn"] = question.get("urn", "")
        field["text"] = question.get("text", "")

        if question_type == "unique_choice":
            field["type"] = "unique_choice"
            field["options"] = question_choices
        elif question_type == "date":
            field["type"] = "date"
        else:
            field["type"] = "text"

        field["answer"] = ""

        form_fields.append(field)

    form_json = {"questions": form_fields}
    return form_json


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


class StoredLibrary(LibraryMixin):
    is_loaded = models.BooleanField(default=False)
    hash_checksum = models.CharField(max_length=64)
    content = models.TextField()

    REQUIRED_FIELDS = {"urn", "name", "version", "objects"}
    FIELDS_VERIFIERS = {}
    HASH_CHECKSUM_SET = set()  # For now a library isn't updated if its SHA256 checksum has already been registered in the database.

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
            return None  # We do not store the library if its hash checksum is in the database.
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

        library_objects = json.dumps(library_data["objects"])
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
            translations=library_data.get("translations", {}),
            objects_meta=objects_meta,
            dependencies=dependencies,
            is_loaded=is_loaded,
            builtin=builtin,  # We have to add a "builtin: true" line to every builtin library file.
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
        library_content = json.loads(self.new_library.content)
        self.dependencies = self.new_library.dependencies
        if self.dependencies is None:
            self.dependencies = []
        self.new_framework = library_content.get("framework")
        self.new_matrices = library_content.get("risk_matrix")
        self.threats = library_content.get("threats", [])
        self.reference_controls = library_content.get("reference_controls", [])
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
            ("ref_id", self.new_library.ref_id),  # Should we even update the ref_id ?
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
                for key in ["maturity", "depth", "reference_controls", "threats"]:
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
                            folder=compliance_assessment.project.folder,
                            answer=transform_question_to_answer(
                                new_requirement_node.question
                            )
                            if new_requirement_node.question
                            else {},
                        )
                else:
                    for ra in RequirementAssessment.objects.filter(
                        requirement=new_requirement_node
                    ):
                        ra.name = new_requirement_node.name
                        ra.description = new_requirement_node.description
                        ra.answer = (
                            transform_question_to_answer(new_requirement_node.question)
                            if new_requirement_node.question
                            else {}
                        )
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
                matrix_dict["json_definition"] = json.dumps(
                    matrix_dict["json_definition"]
                )

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
    def update(self):
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


class Threat(ReferentialObjectMixin, I18nObjectMixin, PublishInRootFolderMixin):
    library = models.ForeignKey(
        LoadedLibrary,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="threats",
    )

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


class ReferenceControl(ReferentialObjectMixin, I18nObjectMixin):
    CATEGORY = [
        ("policy", _("Policy")),
        ("process", _("Process")),
        ("technical", _("Technical")),
        ("physical", _("Physical")),
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
    provider = models.CharField(
        max_length=200, blank=True, null=True, verbose_name=_("Provider")
    )

    @property
    def is_used(self) -> bool:
        return RiskAssessment.objects.filter(risk_matrix=self).exists()

    @property
    def risk_assessments(self) -> list:
        return RiskAssessment.objects.filter(risk_matrix=self)

    @property
    def projects(self) -> list:
        return Project.objects.filter(riskassessment__risk_matrix=self).distinct()

    def parse_json(self) -> dict:
        return json.loads(self.json_definition)

    def parse_json_translated(self) -> dict:
        return update_translations_in_object(json.loads(self.json_definition))

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
        return update_translations_as_string(self.json_definition, "fr")  # Why "fr" ?

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
    question = models.JSONField(blank=True, null=True, verbose_name=_("Question"))

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


########################### Domain objects #########################


class Project(NameDescriptionMixin, FolderMixin):
    PRJ_LC_STATUS = [
        ("undefined", _("Undefined")),
        ("in_design", _("Design")),
        ("in_dev", _("Development")),
        ("in_prod", _("Production")),
        ("eol", _("EndOfLife")),
        ("dropped", _("Dropped")),
    ]
    internal_reference = models.CharField(
        max_length=100, null=True, blank=True, verbose_name=_("Internal reference")
    )
    lc_status = models.CharField(
        max_length=20,
        default="in_design",
        choices=PRJ_LC_STATUS,
        verbose_name=_("Status"),
    )
    fields_to_check = ["name"]

    class Meta:
        verbose_name = _("Project")
        verbose_name_plural = _("Projects")

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


class Asset(NameDescriptionMixin, FolderMixin, PublishInRootFolderMixin):
    class Type(models.TextChoices):
        """
        The type of the asset.

        An asset can either be a primary or a support asset.
        A support asset can be linked to another "parent" asset of type primary or support.
        Cycles are not allowed
        """

        PRIMARY = "PR", _("Primary")
        SUPPORT = "SP", _("Support")

    business_value = models.CharField(
        max_length=200, blank=True, verbose_name=_("business value")
    )
    type = models.CharField(
        max_length=2, choices=Type.choices, default=Type.SUPPORT, verbose_name=_("type")
    )
    parent_assets = models.ManyToManyField(
        "self", blank=True, verbose_name=_("parent assets"), symmetrical=False
    )

    fields_to_check = ["name"]

    class Meta:
        verbose_name_plural = _("Assets")
        verbose_name = _("Asset")

    def __str__(self) -> str:
        return str(self.name)

    def is_primary(self) -> bool:
        """
        Returns True if the asset is a primary asset.
        """
        return self.type == Asset.Type.PRIMARY

    def is_support(self) -> bool:
        """
        Returns True if the asset is a support asset.
        """
        return self.type == Asset.Type.SUPPORT

    def ancestors_plus_self(self) -> list[Self]:
        result = {self}
        for x in self.parent_assets.all():
            result.update(x.ancestors_plus_self())
        return list(result)


class Evidence(NameDescriptionMixin, FolderMixin, PublishInRootFolderMixin):
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
        if not self.attachment:
            return None
        # get the attachment size with the correct unit
        size = self.attachment.size
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        else:
            return f"{size / 1024 / 1024:.1f} MB"


class AppliedControl(NameDescriptionMixin, FolderMixin, PublishInRootFolderMixin):
    class Status(models.TextChoices):
        TO_DO = "to_do", _("To do")
        IN_PROGRESS = "in_progress", _("In progress")
        ON_HOLD = "on_hold", _("On hold")
        ACTIVE = "active", _("Active")
        DEPRECATED = "deprecated", _("Deprecated")
        UNDEFINED = "--", _("Undefined")

    CATEGORY = ReferenceControl.CATEGORY
    CSF_FUNCTION = ReferenceControl.CSF_FUNCTION

    EFFORT = [
        ("S", _("Small")),
        ("M", _("Medium")),
        ("L", _("Large")),
        ("XL", _("Extra Large")),
    ]

    MAP_EFFORT = {None: -1, "S": 1, "M": 2, "L": 4, "XL": 8}
    # todo: think about a smarter model for ranking
    reference_control = models.ForeignKey(
        ReferenceControl,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name=_("Reference Control"),
    )
    evidences = models.ManyToManyField(
        Evidence,
        blank=True,
        verbose_name=_("Evidences"),
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
    cost = models.FloatField(
        null=True,
        help_text=_("Cost of the measure (using globally-chosen currency)"),
        verbose_name=_("Cost"),
    )

    fields_to_check = ["name"]

    class Meta:
        verbose_name = _("Applied control")
        verbose_name_plural = _("Applied controls")

    def save(self, *args, **kwargs):
        if self.reference_control and self.category is None:
            self.category = self.reference_control.category
        if self.reference_control and self.csf_function is None:
            self.csf_function = self.reference_control.csf_function
        super(AppliedControl, self).save(*args, **kwargs)

    @property
    def risk_scenarios(self):
        return self.risk_scenarios.all()

    @property
    def risk_assessments(self):
        return {scenario.risk_assessment for scenario in self.risk_scenarios}

    @property
    def projects(self):
        return {risk_assessment.project for risk_assessment in self.risk_assessments}

    def parent_project(self):
        pass

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
        return abs(round(value / self.MAP_EFFORT[self.effort], 4))

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

    def has_evidences(self):
        return self.evidences.count() > 0

    def eta_missed(self):
        return (
            self.eta < date.today() and self.status != "active" if self.eta else False
        )


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
    severity = models.IntegerField(
        default=-1,
        verbose_name=_("Severity"),
        help_text=_("The severity of the vulnerability"),
    )
    applied_controls = models.ManyToManyField(
        AppliedControl,
        blank=True,
        verbose_name=_("Applied controls"),
        related_name="vulnerabilities",
    )

    fields_to_check = ["name"]


########################### Secondary objects #########################


class Assessment(NameDescriptionMixin, ETADueDateMixin, FolderMixin):
    class Status(models.TextChoices):
        PLANNED = "planned", _("Planned")
        IN_PROGRESS = "in_progress", _("In progress")
        IN_REVIEW = "in_review", _("In review")
        DONE = "done", _("Done")
        DEPRECATED = "deprecated", _("Deprecated")

    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, verbose_name=_("Project")
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
            self.folder = self.project.folder
        return super().save(*args, **kwargs)


class RiskAssessment(Assessment):
    risk_matrix = models.ForeignKey(
        RiskMatrix,
        on_delete=models.PROTECT,
        help_text=_("WARNING! After choosing it, you will not be able to change it"),
        verbose_name=_("Risk matrix"),
    )

    class Meta:
        verbose_name = _("Risk assessment")
        verbose_name_plural = _("Risk assessments")

    def __str__(self) -> str:
        return f"{self.name} - {self.version}"

    @property
    def path_display(self) -> str:
        return f"{self.project.folder}/{self.project}/{self.name} - {self.version}"

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
    fields = json.loads(risk_matrix.json_definition)
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
        ("Financial", _("Financial")),
        ("Legal", _("Legal")),
        ("Reputation", _("Reputation")),
        ("Operational", _("Operational")),
        ("Confidentiality", _("Confidentiality")),
        ("Integrity", _("Integrity")),
        ("Availability", _("Availability")),
        ("Authenticity", _("Authenticity")),
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

    qualifications = models.JSONField(default=list, verbose_name=_("Qualifications"))

    strength_of_knowledge = models.IntegerField(
        default=-1,
        verbose_name=_("Strength of Knowledge"),
        help_text=_("The strength of the knowledge supporting the assessment"),
    )
    justification = models.CharField(
        max_length=500, blank=True, null=True, verbose_name=_("Justification")
    )

    fields_to_check = ["name"]

    class Meta:
        verbose_name = _("Risk scenario")
        verbose_name_plural = _("Risk scenarios")

    # def get_rating_options(self, field: str) -> list[tuple]:
    #     risk_matrix = self.risk_assessment.risk_matrix.parse_json()
    #     return [(k, v) for k, v in risk_matrix.fields[field].items()]

    def parent_project(self):
        return self.risk_assessment.project

    parent_project.short_description = _("Project")

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
        return str(self.parent_project()) + _(": ") + str(self.name)

    @property
    def rid(self):
        """return associated risk assessment id"""
        return f"R.{self.scoped_id(scope=RiskScenario.objects.filter(risk_assessment=self.risk_assessment))}"

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


class ComplianceAssessment(Assessment):
    framework = models.ForeignKey(
        Framework, on_delete=models.CASCADE, verbose_name=_("Framework")
    )
    selected_implementation_groups = models.JSONField(
        blank=True, null=True, verbose_name=_("Selected implementation groups")
    )
    # score system is suggested by the framework, but can be changed at the start of the assessment
    min_score = models.IntegerField(null=True, verbose_name=_("Minimum score"))
    max_score = models.IntegerField(null=True, verbose_name=_("Maximum score"))
    scores_definition = models.JSONField(
        blank=True, null=True, verbose_name=_("Score definition")
    )

    class Meta:
        verbose_name = _("Compliance assessment")
        verbose_name_plural = _("Compliance assessments")

    def save(self, *args, **kwargs) -> None:
        if self.min_score is None:
            self.min_score = self.framework.min_score
            self.max_score = self.framework.max_score
            self.scores_definition = self.framework.scores_definition
        super().save(*args, **kwargs)

    def create_requirement_assessments(
        self, baseline: Self | None = None
    ) -> list["RequirementAssessment"]:
        requirements = RequirementNode.objects.filter(framework=self.framework)
        requirement_assessments = []
        for requirement in requirements:
            requirement_assessment = RequirementAssessment.objects.create(
                compliance_assessment=self,
                requirement=requirement,
                folder=Folder.objects.get(id=self.folder.id),
                answer=transform_question_to_answer(requirement.question)
                if requirement.question
                else {},
            )
            if baseline and baseline.framework == self.framework:
                baseline_requirement_assessment = RequirementAssessment.objects.get(
                    compliance_assessment=baseline, requirement=requirement
                )
                requirement_assessment.result = baseline_requirement_assessment.result
                requirement_assessment.status = baseline_requirement_assessment.status
                requirement_assessment.score = baseline_requirement_assessment.score
                requirement_assessment.is_scored = (
                    baseline_requirement_assessment.is_scored
                )
                requirement_assessment.evidences.set(
                    baseline_requirement_assessment.evidences.all()
                )
                requirement_assessment.applied_controls.set(
                    baseline_requirement_assessment.applied_controls.all()
                )
                requirement_assessment.save()
            requirement_assessments.append(requirement_assessment)
        return requirement_assessments

    def get_global_score(self):
        requirement_assessments_scored = (
            RequirementAssessment.objects.filter(compliance_assessment=self)
            .exclude(score=None)
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
            if not (ig) or (ig & set(ras.requirement.implementation_groups)):
                score += ras.score
                n += 1
        if n > 0:
            return round(score / n, 1)
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

    def get_requirement_assessments(self, include_non_assessable=False):
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
        for rs in RequirementAssessment.Result:
            requirements_result_count.append(
                (
                    RequirementAssessment.objects.filter(result=rs)
                    .filter(compliance_assessment=self)
                    .count(),
                    rs,
                )
            )
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
            RequirementAssessment.Result.NON_COMPLIANT,
            RequirementAssessment.Result.PARTIALLY_COMPLIANT,
            RequirementAssessment.Result.COMPLIANT,
        )
        for requirement_assessment in self.requirement_assessments.all():
            mappings = mapping_set.mappings.filter(
                target_requirement=requirement_assessment.requirement
            )
            inferences = []
            refs = []
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
                inferred_result, inferred_status = requirement_assessment.infer_result(
                    mapping=mapping,
                    source_requirement_assessment=source_requirement_assessment,
                )
                if inferred_result in result_order:
                    inferences.append((inferred_result, inferred_status))
                    refs.append(source_requirement_assessment)
            if inferences:
                if len(inferences) == 1:
                    requirement_assessment.result = inferences[0][0]
                    if inferences[0][1]:
                        requirement_assessment.status = inferences[0][1]
                    ref = refs[0]
                else:
                    lowest_result = min(
                        inferences, key=lambda x: result_order.index(x[0])
                    )
                    requirement_assessment.result = lowest_result[0]
                    if lowest_result[1]:
                        requirement_assessment.status = lowest_result[1]
                    ref = refs[inferences.index(lowest_result)]
                requirement_assessment.mapping_inference = {
                    "result": requirement_assessment.result,
                    "source_requirement_assessment": {
                        "str": str(ref),
                        "id": str(ref.id),
                        "coverage": mapping.coverage,
                    },
                    # "mappings": [mapping.id for mapping in mappings],
                }
                requirement_assessments.append(requirement_assessment)
        return requirement_assessments

    def progress(self) -> int:
        requirements_all = RequirementAssessment.objects.filter(
            compliance_assessment=self, requirement__assessable=True
        )
        total_cnt = requirements_all.count()
        set_cnt = requirements_all.exclude(result="not_assessed").count()
        value = int((set_cnt / total_cnt) * 100) if total_cnt > 0 else 0
        return value


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
    score = models.IntegerField(
        blank=True,
        null=True,
        verbose_name=_("Score"),
    )
    is_scored = models.BooleanField(
        default=False,
        verbose_name=_("Is scored"),
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
    answer = models.JSONField(
        blank=True,
        null=True,
        verbose_name=_("Answer"),
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
    ) -> str | None:
        if mapping.coverage == RequirementMapping.Coverage.FULL:
            return (
                source_requirement_assessment.result,
                source_requirement_assessment.status,
            )
        if mapping.coverage == RequirementMapping.Coverage.PARTIAL:
            if source_requirement_assessment.result in (
                RequirementAssessment.Result.COMPLIANT,
                RequirementAssessment.Result.PARTIALLY_COMPLIANT,
            ):
                return (RequirementAssessment.Result.PARTIALLY_COMPLIANT, None)
            if (
                source_requirement_assessment.result
                == RequirementAssessment.Result.NON_COMPLIANT
            ):
                return (RequirementAssessment.Result.NON_COMPLIANT, None)
        return (None, None)

    def create_applied_controls_from_suggestions(self) -> list[AppliedControl]:
        applied_controls: list[AppliedControl] = []
        for reference_control in self.requirement.reference_controls.all():
            try:
                _name = reference_control.name or reference_control.ref_id
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


########################### RiskAcesptance is a domain object relying on secondary objects #########################


class RiskAcceptance(NameDescriptionMixin, FolderMixin, PublishInRootFolderMixin):
    ACCEPTANCE_STATE = [
        ("created", _("Created")),
        ("submitted", _("Submitted")),
        ("accepted", _("Accepted")),
        ("rejected", _("Rejected")),
        ("revoked", _("Revoked")),
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
