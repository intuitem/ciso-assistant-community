from django.contrib import admin
from .models import *
from reversion.admin import VersionAdmin
from fieldsets_with_inlines import FieldsetsInlineMixin
from import_export.admin import ImportExportModelAdmin
from import_export.admin import ImportExportActionModelAdmin
from import_export import resources
from django.utils.translation import gettext_lazy as _

# HINT: Whenever you register a model with django-reversion, run createinitialrevisions.
# TODO: we could consider nested inlines at some point


@admin.register(Folder)
class FolderAdmin(VersionAdmin, ImportExportActionModelAdmin, admin.ModelAdmin):
    ...


@admin.register(ParentRisk)
class ParentRiskAdmin(VersionAdmin, ImportExportActionModelAdmin, admin.ModelAdmin):
    ...


@admin.register(Solution)
class SolutionAdmin(VersionAdmin, ImportExportActionModelAdmin, admin.ModelAdmin):
    ...


@admin.register(RiskAcceptance)
class RiskAcceptanceAdmin(VersionAdmin, ImportExportActionModelAdmin, admin.ModelAdmin):
    list_display = ('__str__', 'type', 'validator', 'expiry_date')


class MitigationInline(admin.StackedInline):
    model = Mitigation
    extra = 0


class RiskInstanceInline(admin.StackedInline):
    model = RiskInstance
    extra = 0
    show_change_link = True
    fieldsets = [
        (None, {'fields': ['analysis', 'parent_risk']}),
        (_('Threat description'), {'fields': ['title', 'scenario']}),
        (_('Current level'), {'fields': ['existing_measures', 'current_proba', 'current_impact', 'current_level']}),
        (_('Residual level'), {'fields': ['associated_mitigations','residual_proba', 'residual_impact', 'residual_level']}),
        (_('Follow-up'), {'fields': ['treatment', 'comments', 'created_at', 'updated_at']}),
    ]

    def associated_mitigations(self, obj):
        return obj.associated_mitigations()

    associated_mitigations.short_description = 'Associated Mitigations (Click CHANGE next to the instance title to Edit)'
    readonly_fields = ('current_level', 'residual_level', 'created_at', 'updated_at', 'associated_mitigations')


class RiskInstanceResource(resources.ModelResource):

    class Meta:
        model = RiskInstance


@admin.register(RiskInstance)
class RiskInstanceAdmin(VersionAdmin, FieldsetsInlineMixin, ImportExportActionModelAdmin, admin.ModelAdmin):
    model = RiskInstance

    list_display = ('__str__', 'parent_risk', 'parent_project', 'treatment')

    fieldsets_with_inlines = [
        (None, {'fields': ['analysis', 'parent_risk',]}),
        (_('Threat description'), {'fields': ['title', 'scenario']}),
        (_('Current level'), {'fields': ['existing_measures', 'current_proba', 'current_impact', 'current_level']}),
        MitigationInline,
        (_('Residual level'), {'fields': ['residual_proba', 'residual_impact', 'residual_level']}),
        (_('Follow-up'), {'fields': ['treatment', 'comments', 'created_at', 'updated_at']}),
    ]
    inlines = [MitigationInline]

    readonly_fields = ('current_level', 'residual_level', 'created_at', 'updated_at')
    list_filter = ('parent_risk', 'treatment', 'current_level', 'residual_level', 'analysis__project__name')

@admin.register(Analysis)
class AnalysisAdmin(VersionAdmin, ImportExportActionModelAdmin, admin.ModelAdmin):
    model = Analysis
    inlines = [RiskInstanceInline]

    list_display = ('__str__', 'project', 'auditor', 'is_draft')
    list_filter = ('project', 'auditor', 'is_draft')

    class Meta:
        verbose_name = _("Analysis")
        verbose_name_plural = _("Analyses")

    def __str__(self):
        return self.Meta.verbose_name


@admin.register(Mitigation)
class MitigationAdmin(VersionAdmin, ImportExportActionModelAdmin, admin.ModelAdmin):
    model = Mitigation

    list_display = ('title', 'parent_project', 'type', 'solution', 'effort', 'status')
    list_filter = ('type', 'solution', 'effort', 'status', 'eta')


@admin.register(Project)
class ProjectAdmin(VersionAdmin, ImportExportActionModelAdmin, admin.ModelAdmin):
    model = Project

    list_display = ('name', 'folder', 'department', 'lc_status')




