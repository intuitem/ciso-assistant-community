from django.apps import AppConfig
from django.db.models.signals import post_migrate
from ciso_assistant.settings import CISO_ASSISTANT_SUPERUSER_EMAIL
import os

AUDITOR_PERMISSIONS_LIST = [
    "view_project",
    "view_riskassessment",
    "view_appliedcontrol",
    "view_policy",
    "view_riskscenario",
    "view_riskacceptance",
    "view_asset",
    "view_threat",
    "view_referencecontrol",
    "view_folder",
    "view_usergroup",
    "view_riskmatrix",
    "view_complianceassessment",
    "view_requirementassessment",
    "view_requirementnode",
    "view_evidence",
    "view_framework",
    "view_library",
    "view_user",
]

APPROVER_PERMISSIONS_LIST = [
    "view_project",
    "view_riskassessment",
    "view_appliedcontrol",
    "view_policy",
    "view_riskscenario",
    "view_riskacceptance",
    "approve_riskacceptance",
    "view_asset",
    "view_threat",
    "view_referencecontrol",
    "view_folder",
    "view_usergroup",
    "view_riskmatrix",
    "view_complianceassessment",
    "view_requirementassessment",
    "view_requirementnode",
    "view_evidence",
    "view_framework",
    "view_library",
    "view_user",
]

ANALYST_PERMISSIONS_LIST = [
    "add_project",
    "view_project",
    "change_project",
    "delete_project",
    "add_riskassessment",
    "view_riskassessment",
    "change_riskassessment",
    "delete_riskassessment",
    "add_appliedcontrol",
    "view_appliedcontrol",
    "change_appliedcontrol",
    "delete_appliedcontrol",
    "add_policy",
    "view_policy",
    "change_policy",
    "delete_policy",
    "add_riskscenario",
    "view_riskscenario",
    "change_riskscenario",
    "delete_riskscenario",
    "add_riskacceptance",
    "view_riskacceptance",
    "change_riskacceptance",
    "delete_riskacceptance",
    "add_complianceassessment",
    "view_complianceassessment",
    "change_complianceassessment",
    "delete_complianceassessment",
    "view_requirementassessment",
    "change_requirementassessment",
    "add_evidence",
    "view_evidence",
    "change_evidence",
    "delete_evidence",
    "add_asset",
    "view_asset",
    "change_asset",
    "delete_asset",
    "add_threat",
    "view_threat",
    "change_threat",
    "delete_threat",
    "view_referencecontrol",
    "view_folder",
    "view_usergroup",
    "view_riskmatrix",
    "view_requirementnode",
    "view_framework",
    "view_library",
    "view_user",
]

DOMAIN_MANAGER_PERMISSIONS_LIST = [
    "change_usergroup",
    "view_usergroup",
    "add_project",
    "change_project",
    "delete_project",
    "view_project",
    "add_riskassessment",
    "view_riskassessment",
    "change_riskassessment",
    "delete_riskassessment",
    "add_appliedcontrol",
    "view_appliedcontrol",
    "change_appliedcontrol",
    "delete_appliedcontrol",
    "add_policy",
    "view_policy",
    "change_policy",
    "delete_policy",
    "add_riskscenario",
    "view_riskscenario",
    "change_riskscenario",
    "delete_riskscenario",
    "add_riskacceptance",
    "view_riskacceptance",
    "change_riskacceptance",
    "delete_riskacceptance",
    "add_asset",
    "view_asset",
    "change_asset",
    "delete_asset",
    "add_threat",
    "view_threat",
    "change_threat",
    "delete_threat",
    "view_referencecontrol",
    "view_folder",
    "change_folder",
    "add_riskmatrix",
    "view_riskmatrix",
    "change_riskmatrix",
    "delete_riskmatrix",
    "add_complianceassessment",
    "view_complianceassessment",
    "change_complianceassessment",
    "delete_complianceassessment",
    "view_requirementassessment",
    "change_requirementassessment",
    "add_evidence",
    "view_evidence",
    "change_evidence",
    "delete_evidence",
    "view_requirementnode",
    "view_framework",
    "view_library",
    "view_user",
]

ADMINISTRATOR_PERMISSIONS_LIST = [
    "add_user",
    "view_user",
    "change_user",
    "delete_user",
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
    "add_referencecontrol",
    "view_referencecontrol",
    "change_referencecontrol",
    "delete_referencecontrol",
    "add_folder",
    "change_folder",
    "view_folder",
    "delete_folder",
    "add_project",
    "change_project",
    "delete_project",
    "view_project",
    "add_riskassessment",
    "view_riskassessment",
    "change_riskassessment",
    "delete_riskassessment",
    "add_appliedcontrol",
    "view_appliedcontrol",
    "change_appliedcontrol",
    "delete_appliedcontrol",
    "add_policy",
    "view_policy",
    "change_policy",
    "delete_policy",
    "add_riskscenario",
    "view_riskscenario",
    "change_riskscenario",
    "delete_riskscenario",
    "add_riskacceptance",
    "view_riskacceptance",
    "change_riskacceptance",
    "delete_riskacceptance",
    "approve_riskacceptance",
    "add_riskmatrix",
    "view_riskmatrix",
    "change_riskmatrix",
    "delete_riskmatrix",
    "add_complianceassessment",
    "view_complianceassessment",
    "change_complianceassessment",
    "delete_complianceassessment",
    "view_requirementassessment",
    "change_requirementassessment",
    "add_evidence",
    "view_evidence",
    "change_evidence",
    "delete_evidence",
    "add_framework",
    "view_framework",
    "delete_framework",
    "view_requirementnode",
    "view_requirementlevel",  # Permits to see the object on api by an admin
    "view_library",
    "add_library",
    "delete_library",
    "backup",
    "restore",
]


def startup(**kwargs):
    """
    Implement CISO Assistant 1.0 default Roles and User Groups during migrate
    This makes sure root folder and global groups are defined before any other object is created
    Create superuser if CISO_ASSISTANT_SUPERUSER_EMAIL defined
    """
    from django.contrib.auth.models import Permission
    from iam.models import Folder, Role, RoleAssignment, User, UserGroup

    print("startup handler: initialize database")

    auditor_permissions = Permission.objects.filter(
        codename__in=AUDITOR_PERMISSIONS_LIST
    )

    approver_permissions = Permission.objects.filter(
        codename__in=APPROVER_PERMISSIONS_LIST
    )

    analyst_permissions = Permission.objects.filter(
        codename__in=ANALYST_PERMISSIONS_LIST
    )

    domain_manager_permissions = Permission.objects.filter(
        codename__in=DOMAIN_MANAGER_PERMISSIONS_LIST
    )

    administrator_permissions = Permission.objects.filter(
        codename__in=ADMINISTRATOR_PERMISSIONS_LIST
    )

    # if root folder does not exist, then create it
    if not Folder.objects.filter(content_type=Folder.ContentType.ROOT).exists():
        Folder.objects.create(
            name="Global", content_type=Folder.ContentType.ROOT, builtin=True
        )
    # update builtin roles to facilitate migrations
    auditor, created = Role.objects.get_or_create(name="BI-RL-AUD", builtin=True)
    auditor.permissions.set(auditor_permissions)
    approver, created = Role.objects.get_or_create(name="BI-RL-APP", builtin=True)
    approver.permissions.set(approver_permissions)
    analyst, created = Role.objects.get_or_create(name="BI-RL-ANA", builtin=True)
    analyst.permissions.set(analyst_permissions)
    domain_manager, created = Role.objects.get_or_create(name="BI-RL-DMA", builtin=True)
    domain_manager.permissions.set(domain_manager_permissions)
    administrator, created = Role.objects.get_or_create(name="BI-RL-ADM", builtin=True)
    administrator.permissions.set(administrator_permissions)
    # if global administrators user group does not exist, then create it
    if not UserGroup.objects.filter(
        name="BI-UG-ADM", folder=Folder.get_root_folder()
    ).exists():
        administrators = UserGroup.objects.create(
            name="BI-UG-ADM", folder=Folder.get_root_folder(), builtin=True
        )
        ra1 = RoleAssignment.objects.create(
            user_group=administrators,
            role=Role.objects.get(name="BI-RL-ADM"),
            is_recursive=True,
            builtin=True,
            folder=Folder.get_root_folder(),
        )
        ra1.perimeter_folders.add(administrators.folder)
    # if global auditors user group does not exist, then create it
    if not UserGroup.objects.filter(
        name="BI-UG-GAD", folder=Folder.get_root_folder()
    ).exists():
        global_auditors = UserGroup.objects.create(
            name="BI-UG-GAD",
            folder=Folder.objects.get(content_type=Folder.ContentType.ROOT),
            builtin=True,
        )
        ra2 = RoleAssignment.objects.create(
            user_group=global_auditors,
            role=Role.objects.get(name="BI-RL-AUD"),
            is_recursive=True,
            builtin=True,
            folder=Folder.get_root_folder(),
        )
        ra2.perimeter_folders.add(global_auditors.folder)
    # if global approvers user group does not exist, then create it
    if not UserGroup.objects.filter(
        name="BI-UG-GAP", folder=Folder.get_root_folder()
    ).exists():
        global_approvers = UserGroup.objects.create(
            name="BI-UG-GAP",
            folder=Folder.objects.get(content_type=Folder.ContentType.ROOT),
            builtin=True,
        )
        ra2 = RoleAssignment.objects.create(
            user_group=global_approvers,
            role=Role.objects.get(name="BI-RL-APP"),
            is_recursive=True,
            builtin=True,
            folder=Folder.get_root_folder(),
        )
        ra2.perimeter_folders.add(global_approvers.folder)

    # if superuser defined and does not exist, then create it
    if (
        CISO_ASSISTANT_SUPERUSER_EMAIL
        and not User.objects.filter(email=CISO_ASSISTANT_SUPERUSER_EMAIL).exists()
    ):
        try:
            User.objects.create_superuser(
                email=CISO_ASSISTANT_SUPERUSER_EMAIL, is_superuser=True
            )
        except Exception as e:
            print(e)  # NOTE: Add this exception in the logger


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"
    verbose_name = "Core"

    def ready(self):
        # avoid post_migrate handler if we are in the main, as it interferes with restore
        if not os.environ.get("RUN_MAIN"):
            post_migrate.connect(startup, sender=self)
