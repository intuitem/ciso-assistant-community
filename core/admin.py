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


@admin.register(Threat)
class ThreatAdmin(VersionAdmin, ImportExportActionModelAdmin, admin.ModelAdmin):
    ...


@admin.register(SecurityFunction)
class SecurityFunctionAdmin(VersionAdmin, ImportExportActionModelAdmin, admin.ModelAdmin):
    ...


@admin.register(RiskAcceptance)
class RiskAcceptanceAdmin(VersionAdmin, ImportExportActionModelAdmin, admin.ModelAdmin):
    list_display = ('__str__', 'type', 'validator', 'expiry_date')


class SecurityMeasureInline(admin.StackedInline):
    model = SecurityMeasure
    extra = 0


class RiskScenarioInline(admin.StackedInline):
    model = RiskScenario
    extra = 0
    show_change_link = True
    fieldsets = [
        (None, {'fields': ['analysis', 'threat']}),
        (_('Threat description'), {'fields': ['title', 'scenario']}),
        (_('Current level'), {'fields': ['existing_measures', 'current_proba', 'current_impact', 'current_level']}),
        (_('Residual level'), {'fields': ['associated_security_measures','residual_proba', 'residual_impact', 'residual_level']}),
        (_('Follow-up'), {'fields': ['treatment', 'comments', 'created_at', 'updated_at']}),
    ]

    def associated_security_measures(self, obj):
        return obj.associated_security_measures()

    associated_security_measures.short_description = 'Associated SecurityMeasures (Click CHANGE next to the scenario title to Edit)'
    readonly_fields = ('current_level', 'residual_level', 'created_at', 'updated_at', 'associated_security_measures')


class RiskScenarioResource(resources.ModelResource):

    class Meta:
        model = RiskScenario


@admin.register(RiskScenario)
class RiskScenarioAdmin(VersionAdmin, FieldsetsInlineMixin, ImportExportActionModelAdmin, admin.ModelAdmin):
    model = RiskScenario

    list_display = ('__str__', 'threat', 'parent_project', 'treatment')

    fieldsets_with_inlines = [
        (None, {'fields': ['analysis', 'threat',]}),
        (_('Threat description'), {'fields': ['title', 'scenario']}),
        (_('Current level'), {'fields': ['existing_measures', 'current_proba', 'current_impact', 'current_level']}),
        SecurityMeasureInline,
        (_('Residual level'), {'fields': ['residual_proba', 'residual_impact', 'residual_level']}),
        (_('Follow-up'), {'fields': ['treatment', 'comments', 'created_at', 'updated_at']}),
    ]
    inlines = [SecurityMeasureInline]

    readonly_fields = ('current_level', 'residual_level', 'created_at', 'updated_at')
    list_filter = ('threat', 'treatment', 'current_level', 'residual_level', 'analysis__project__name')

@admin.register(Analysis)
class AnalysisAdmin(VersionAdmin, ImportExportActionModelAdmin, admin.ModelAdmin):
    model = Analysis
    inlines = [RiskScenarioInline]

    list_display = ('__str__', 'project', 'auditor', 'is_draft')
    list_filter = ('project', 'auditor', 'is_draft')

    class Meta:
        verbose_name = _("Analysis")
        verbose_name_plural = _("Analyses")

    def __str__(self):
        return self.Meta.verbose_name


@admin.register(SecurityMeasure)
class SecurityMeasureAdmin(VersionAdmin, ImportExportActionModelAdmin, admin.ModelAdmin):
    model = SecurityMeasure

    list_display = ('title', 'parent_project', 'type', 'security_function', 'effort', 'status')
    list_filter = ('type', 'security_function', 'effort', 'status', 'eta')


@admin.register(Project)
class ProjectAdmin(VersionAdmin, ImportExportActionModelAdmin, admin.ModelAdmin):
    model = Project

    list_display = ('name', 'folder', 'description', 'lc_status')




