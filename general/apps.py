from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


def startup():
    """Implement Mira 1.0 default Roles and User Groups"""
    import os
    if os.environ.get('RUN_MAIN'):
        from .models import Folder
        from back_office.models import Role, UserGroup, RoleAssignment
        from django.contrib.auth.models import Permission, User

        auditor_permissions = Permission.objects.filter(codename__in=[
            "view_project",
            "view_analysis",
            "view_securitymeasure",
            "view_riskscenario",
            "view_riskacceptance",
            "view_asset",
            "view_threat",
            "view_securityfunction",
            "view_folder",
        ])

        analyst_permissions = Permission.objects.filter(codename__in=[
            "add_project",
            "view_project",
            "change_project",
            "delete_project",

            "add_analysis",
            "view_analysis",
            "change_analysis",
            "delete_analysis"

            "add_securitymeasure",
            "view_securitymeasure",
            "change_securitymeasure",
            "delete_securitymeasure",

            "add_riskscenario",
            "view_riskscenario",
            "change_riskscenario",
            "delete_riskscenario",

            "add_riskacceptance",
            "view_riskacceptance",
            "change_riskacceptance",
            "delete_riskacceptance",

            "view_asset",
            "view_threat",
            "view_securityfunction",
            "view_folder",
        ])

        domain_manager_permissions = Permission.objects.filter(codename__in=[
            "change_usergroup",
            "view_usergroup",

            "add_project",
            "change_project",
            "delete_project",
            "view_project",

            "add_analysis",
            "view_analysis",
            "change_analysis",
            "delete_analysis",

            "add_securitymeasure",
            "view_securitymeasure",
            "change_securitymeasure",
            "delete_securitymeasure",

            "add_riskscenario",
            "view_riskscenario",
            "change_riskscenario",
            "delete_riskscenario",

            "add_riskacceptance",
            "view_riskacceptance",
            "change_riskacceptance",
            "delete_riskacceptance",

            "view_asset",
            "view_threat",
            "view_securityfunction",
            "view_folder",
            "change_folder",
        ])

        administrator_permissions = Permission.objects.filter(codename__in=[
            "add_user",
            "view_user",
            "change_user",
            "delete_user",

            "add_roleassignment",
            "view_roleassignment",
            "change_roleassignment",
            "delete_roleassignment",

            "add_usergroup",
            "view_usergroup",
            "change_usergroup",
            "delete_usergroup",

            "add_event",
            "view_event",
            "change_event",
            "delete_event",

            "add_asset",
            "view_asset",
            "change_asset",
            "delete_asset",

            "add_threat",
            "view_threat",
            "change_threat",
            "delete_threat",

            "add_securityfunction",
            "view_securityfunction",
            "change_securityfunction",
            "delete_securityfunction",

            "add_folder",
            "view_folder",
            "delete_folder",
        ])

        if not Folder.objects.filter(content_type=Folder.ContentType.ROOT).exists():
            Folder.objects.create(
                name="Global", content_type=Folder.ContentType.ROOT, builtin=True)
            auditor = Role.objects.create(name="BI-RL-AUD", builtin=True)
            auditor.permissions.set(auditor_permissions)
            analyst = Role.objects.create(name="BI-RL-ANA", builtin=True)
            analyst.permissions.set(analyst_permissions)
            domain_manager = Role.objects.create(
                name="BI-RL-DMA", builtin=True)
            domain_manager.permissions.set(domain_manager_permissions)
            administrator = Role.objects.create(name="BI-RL-ADM", builtin=True)
            administrator.permissions.set(administrator_permissions)
        if not UserGroup.objects.filter(name="BI-UG-ADM", folder=Folder.objects.get(content_type=Folder.ContentType.ROOT)).exists():
            administrators = UserGroup.objects.create(
                name="BI-UG-ADM", folder=Folder.objects.get(content_type=Folder.ContentType.ROOT), builtin=True)
            ra1 = RoleAssignment.objects.create(
                user_group=administrators, role=Role.objects.get(name="BI-RL-ADM"), builtin=True,
                folder=Folder.objects.get(content_type=Folder.ContentType.ROOT))
            ra1.perimeter_folders.add(administrators.folder)
        if not UserGroup.objects.filter(name="BI-UG-GAD", folder=Folder.objects.get(content_type=Folder.ContentType.ROOT)).exists():
            global_auditors = UserGroup.objects.create(name="BI-UG-GAD", folder=Folder.objects.get(
                content_type=Folder.ContentType.ROOT), builtin=True)
            ra2 = RoleAssignment.objects.create(user_group=global_auditors, role=Role.objects.get(
                name="BI-RL-AUD"), is_recursive=True, builtin=True,
                folder=Folder.objects.get(content_type=Folder.ContentType.ROOT))
            ra2.perimeter_folders.add(global_auditors.folder)
        for superuser in User.objects.filter(is_superuser=True):
                UserGroup.objects.get(
                name="BI-UG-ADM").user_set.add(superuser)

class GeneralConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'general'
    verbose_name = _("General")

    def ready(self):
        startup()
