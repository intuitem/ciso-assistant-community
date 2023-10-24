from django.contrib.auth import get_user_model
from django.db import models
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.utils.html import mark_safe
from django.conf import settings

from core.base_models import *
from .validators import validate_file_size, validate_file_name
from iam.models import Folder, FolderMixin, RootFolderMixin

import os

User = get_user_model()


class Project(AbstractBaseModel, I18nMixin, NameDescriptionMixin):
    folder = models.ForeignKey(
        Folder, on_delete=models.CASCADE, verbose_name=_("Domain")
    )

    class Meta:
        verbose_name = _("Project")
        verbose_name_plural = _("Projects")
    

    def overall_compliance(self):
        assessments_list = [assessment for assessment in self.assessment_set.all()]
        count = RequirementAssessment.objects.filter(status='compliant').filter(
                assessment__in=assessments_list).count()
        total = RequirementAssessment.objects.filter(
                assessment__in=assessments_list).count()
        if total == 0:
            return 0
        return round(count*100/total)


class Threat(AbstractBaseModel, I18nMixin, NameDescriptionMixin, RootFolderMixin):
    urn = models.CharField(
        max_length=100, null=True, blank=True, unique=True, verbose_name=_("URN")
    )
    version = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text=_("Version of the threat (eg. 1.0, 2.0, etc.)"),
        verbose_name=_("Version"),
        default="1.0",
    )

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


class Framework(AbstractBaseModel, I18nMixin, NameDescriptionMixin, FolderMixin):
    urn = models.CharField(
        max_length=100, null=True, blank=True, unique=True, verbose_name=_("URN")
    )
    version = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text=_("Version of the framework (eg. 1.0, 2.0, etc.)"),
        verbose_name=_("Version"),
        default="1.0",
    )

    class Meta:
        verbose_name = _("Framework")
        verbose_name_plural = _("Frameworks")

    fields_to_check = ['urn']

    def get_next_order_id(self, obj_type: models.Model, _parent_urn: str = None) -> int:
        """
        Returns the next order id for a given object type
        """
        if _parent_urn:
            return obj_type.objects.filter(framework=self, parent_urn=_parent_urn).count() + 1
        else:
            return obj_type.objects.filter(framework=self).count() + 1
        
    def is_deletable(self) -> bool:
        """
        Returns True if the framework can be deleted
        """
        if self.assessment_set.count() > 0:
            return False
        return True


class RequirementGroup(AbstractBaseModel, I18nMixin, NameDescriptionMixin, FolderMixin):
    framework = models.ForeignKey(
        Framework,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name=_("Framework"),
    )
    urn = models.CharField(
        max_length=100, null=True, blank=True, unique=True, verbose_name=_("URN")
    )
    parent_urn = models.CharField(
        max_length=100, null=True, blank=True, verbose_name=_("Parent URN")
    )
    order_id = models.IntegerField(null=True, blank=True, verbose_name=_("Order ID"))
    level = models.IntegerField(null=True, blank=True, verbose_name=_("Level"))
    fields_to_check = ['urn']


class RequirementLevel(AbstractBaseModel, I18nMixin, FolderMixin):
    framework = models.ForeignKey(
        Framework,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name=_("Framework"),
    )
    urn = models.CharField(
        max_length=100, null=True, blank=True, unique=True, verbose_name=_("URN")
    )
    level = models.IntegerField(null=False, blank=False, verbose_name=_("Level"))
    description = models.TextField(null=True, blank=True, verbose_name=_("Description"))
    fields_to_check = ['urn']


class Requirement(AbstractBaseModel, I18nMixin, NameDescriptionMixin, FolderMixin):
    threats = models.ManyToManyField(
        Threat, blank=True, verbose_name=_("Threats"), related_name="requirements"
    )
    security_functions = models.ManyToManyField(
        "SecurityFunction",
        blank=True,
        verbose_name=_("Security functions"),
        related_name="requirements",
    )
    framework = models.ForeignKey(
        Framework,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name=_("Framework"),
    )
    urn = models.CharField(
        max_length=100, null=True, blank=True, unique=True, verbose_name=_("URN")
    )
    parent_urn = models.CharField(
        max_length=100, null=True, blank=True, verbose_name=_("Parent URN")
    )
    order_id = models.IntegerField(null=True, blank=True, verbose_name=_("Order ID"))
    level = models.IntegerField(null=True, blank=True, verbose_name=_("Level"))
    informative_reference = models.CharField(
        max_length=256,
        null=True,
        blank=True,
        verbose_name=_("Informative reference"),
    )
    fields_to_check = ['urn']

    class Meta:
        verbose_name = _("Requirement")
        verbose_name_plural = _("Requirements")

    def get_requirement_group(self):
        """
        Get name and description of requiremnt's group
        """
        return RequirementGroup.objects.get(urn=self.parent_urn)



class SecurityFunction(AbstractBaseModel, I18nMixin, NameDescriptionMixin, RootFolderMixin):
    urn = models.CharField(
        max_length=100, null=True, blank=True, unique=True, verbose_name=_("URN")
    )
    provider = models.CharField(
        max_length=200, blank=True, null=True, verbose_name=_("Provider")
    )
    typical_evidence = models.JSONField(verbose_name=_("Typical evidence"), null=True, blank=True)
    version = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text=_("Version of the security function (eg. 1.0, 2.0, etc.)"),
        verbose_name=_("Version"),
        default="1.0",
    )

    class Meta:
        verbose_name = _("Security function")
        verbose_name_plural = _("Security functions")

    def is_deletable(self) -> bool:
        """
        Returns True if the framework can be deleted
        """
        if self.requirements.count() or self.securitymeasure_set.count() > 0:
            return False
        return True
    
    @property
    def frameworks(self):
        return Framework.objects.filter(requirement__security_functions=self).distinct()


class SecurityMeasure(AbstractBaseModel, I18nMixin, NameDescriptionMixin):
    MITIGATION_STATUS = [
        ("open", _("Open")),
        ("in_progress", _("In progress")),
        ("on_hold", _("On hold")),
        ("done", _("Done")),
    ]

    folder = models.ForeignKey(
        Folder, on_delete=models.CASCADE, verbose_name=_("Domain")
    )
    security_function = models.ForeignKey(
        SecurityFunction,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Security Function"),
    )
    status = models.CharField(
        max_length=20,
        choices=MITIGATION_STATUS,
        default="open",
        verbose_name=_("Status"),
    )
    cost = models.IntegerField(null=True, blank=True, verbose_name=_("Cost"))
    eta = models.DateField(blank=True, null=True, help_text=_(
        "Estimated Time of Arrival"), verbose_name=_("ETA"))

    class Meta:
        verbose_name = _("Security measure")
        verbose_name_plural = _("Security measures")

        constraints = [
            models.UniqueConstraint(
                models.functions.Lower('name'),
                name='name_unique',
            ),
        ]

    def __str__(self) -> str:
        return self.folder.name + "/" + self.name

    def parent_project(self):
        pass

    @property
    def mid(self):
        return f"M.{self.scoped_id(scope=SecurityMeasure.objects.filter(folder=self.folder))}"

    @property
    def get_html_url(self):
        url = reverse("securitymeasure-detail", args=(self.id,))
        return format_html(
            '<a class="" href="{}"> <b>[MT-eta]</b> {}: {} </a>',
            url,
            self.folder.name,
            self.name,
        )
    
    def get_linked_requirements_count(self):
        return Requirement.objects.filter(requirementassessment__security_measures=self).count()


class Evidence(AbstractBaseModel, I18nMixin, NameDescriptionMixin, RootFolderMixin):
    measure = models.ForeignKey( # TODO: Rename to security_measure for consistency
        SecurityMeasure, on_delete=models.CASCADE, verbose_name=_("Security measure")
    )
    # TODO: Manage file upload to S3/MiniO
    attachment = models.FileField(
#        upload_to=settings.LOCAL_STORAGE_DIRECTORY,
        blank=True,
        null=True,
        help_text=_("File for evidence (eg. screenshot, log file, etc.)"),
        verbose_name=_("File"),
        validators=[validate_file_size, validate_file_name]
    )
    comment = models.TextField(
        blank=True,
        null=True,
        verbose_name=_("Comment"),
    )

    class Meta:
        verbose_name = _("Evidence")
        verbose_name_plural = _("Evidences")

    def filename(self):
        return os.path.basename(self.attachment.name)

    def preview(self):
        if self.attachment:
            if self.filename().endswith(('.png', '.jpg', '.jpeg')):
                return ("image", mark_safe('<img src="/evidence/{}/preview">'.format(self.id)))
            if self.filename().endswith('.txt'):
                with open(self.attachment.path, 'r') as text:
                    return ("text", text.read())
            if self.filename().endswith('.pdf'):
                return ("pdf", mark_safe('<embed class="h-full w-full" src="/evidence/{}/preview" type="application/pdf"/>'.format(self.id)))
            if self.filename().endswith('.docx'):
                return ("icon", mark_safe('<img src="{}">'.format('/static/icons/word.png')))
            if self.filename().endswith(('.xls', '.xlsx', '.csv')):
                return ("icon", mark_safe('<img src="{}">'.format('/static/icons/excel.png')))
        return ''


class Assessment(AbstractBaseModel, I18nMixin, NameDescriptionMixin):
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, verbose_name=_("Project")
    )
    framework = models.ForeignKey(
        Framework, on_delete=models.CASCADE, verbose_name=_("Framework")
    )
    version = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text=_("Version of the assessment (eg. 1.0, 2.0, etc.)"),
        verbose_name=_("Version"),
        default="1.0",
    )
    is_draft = models.BooleanField(_("draft"), default=True)  # type: ignore
    is_obsolete = models.BooleanField(_("obsolete"), default=False)  # type: ignore

    class Meta:
        verbose_name = _("Assessment")
        verbose_name_plural = _("Assessments")

    def get_requirements_status_count(self):
        requirements_status_count = []
        for st in RequirementAssessment.Status:
            requirements_status_count.append(
                (RequirementAssessment.objects.filter(status=st).filter(assessment=self).count(), st)
                )
        return requirements_status_count
    
    def get_measures_status_count(self):
        measures_status_count = []
        measures_list = []
        for requirement_assessment in self.requirementassessment_set.all():
            measures_list += requirement_assessment.security_measures.all().values_list("id", flat=True)
        for st in SecurityMeasure.MITIGATION_STATUS:
            measures_status_count.append(
                (SecurityMeasure.objects.filter(status=st[0]).filter(id__in=measures_list).count(), st)
                )
        print(SecurityMeasure.objects.filter(status=st[0]).filter(id__in=measures_list).count())
        return measures_status_count
    
    def donut_render(self) -> dict:
        assessments_status = {"values": [], "labels": []}
        color_map = {"in_progress": "#3b82f6", "non_compliant": "#f87171",
                 "to_do": "#d1d5db", "partially_compliant": "#fde047",
                 "not_applicable": "#000000", "compliant": "#86efac"}
        for st in RequirementAssessment.Status:
            count = RequirementAssessment.objects.filter(status=st).filter(
                assessment=self).count()
            total = RequirementAssessment.objects.filter(
                assessment=self).count()
            v = {
                "name": st.label + ": " + str(round(count*100/total)) + "%",
                "value": count,
                "itemStyle": {"color": color_map[st]}
            }
            assessments_status["values"].append(v)
            assessments_status["labels"].append(st.label)
        return assessments_status

    def quality_check(self) -> dict:

        errors_lst = list()
        warnings_lst = list()
        info_lst = list()
        # --- check on the assessment:
        if self.is_draft:
            info_lst.append({"msg": _("{}: Assessment is still in Draft mode").format(
                self), "obj_type": "assessment", "object": self})
        if self.is_draft and self.is_obsolete:
            errors_lst.append({"msg": _("{}: Assessment is both in Draft mode and obsolete.").format(
                self), "obj_type": "assessment", "object": self})
        # ---

        # --- check on requirement assessments:
        for requirement_assessment in self.requirementassessment_set.all():
            if requirement_assessment.status in ('C', 'PC') and requirement_assessment.security_measures.count() == 0:
                warnings_lst.append({"msg": _("{}: Requirement assessment status is compliant or partially compliant with no security measure applied").format(
                    requirement_assessment), "obj_type": "requirementassessment", "object": requirement_assessment})
        # ---

        # --- check on security measures:
        for security_measure in SecurityMeasure.objects.filter(requirement_assessments__assessment = self):
            if not security_measure.security_function:
                info_lst.append({"msg": _("{}: Security measure has no security function selected").format(
                    security_measure), "obj_type": "securitymeasure", "object": security_measure})
        # ---
                
        # --- check on evidence:
        for evidence in Evidence.objects.filter(measure__in=SecurityMeasure.objects.filter(requirement_assessments__assessment = self)):
            if not evidence.attachment:
                warnings_lst.append({"msg": _("{}: Evidence has no file uploaded").format(
                    evidence), "obj_type": "evidence", "object": evidence})
            if not evidence.ref_url:
                info_lst.append({"msg": _("{}: Evidence does not have an external link attached. This will help you for follow-up").format(
                    evidence), "obj_type": "evidence", "object": evidence})

        findings = {
            "errors": errors_lst,
            "warnings": warnings_lst,
            "info": info_lst,
            "count": len(errors_lst + warnings_lst + info_lst)
        }
        return findings


class RequirementAssessment(AbstractBaseModel, I18nMixin, FolderMixin):
    class Status(models.TextChoices):
        TODO = "to_do", _("To do")
        IN_PROGRESS = "in_progress", _("In progress")
        NON_COMPLIANT = "non_compliant", _("Non compliant")
        PARTIALLY_COMPLIANT = "partially_compliant", _("Partially compliant")
        COMPLIANT = "compliant", _("Compliant")
        NOT_APPLICABLE = "not_applicable", _("Not applicable")


    status = models.CharField(
        max_length=100,
        choices=Status.choices,
        default=Status.TODO,
        verbose_name=_("Status"),
    )
    comment = models.TextField(null=True, blank=True, verbose_name=_("Comment"))
    assessment = models.ForeignKey(
        Assessment, on_delete=models.CASCADE, verbose_name=_("Assessment")
    )
    requirement = models.ForeignKey(
        Requirement, on_delete=models.CASCADE, verbose_name=_("Requirement")
    )
    security_measures = models.ManyToManyField(
        SecurityMeasure,
        blank=True,
        verbose_name=_("Security measures"),
        related_name="requirement_assessments",
    )

    fields_to_check = []

    def __str__(self) -> str:
        if self.requirement.name not in ("", "-"):
            return f"{self.assessment} - {self.requirement.get_requirement_group()}. {self.requirement.get_requirement_group().description}/{self.requirement}"
        return f"{self.assessment} - {self.requirement.get_requirement_group()}. {self.requirement.get_requirement_group().description}"

    class Meta:
        verbose_name = _("Requirement assessment")
        verbose_name_plural = _("Requirement assessments")
