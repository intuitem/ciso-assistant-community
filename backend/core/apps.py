from django.apps import AppConfig


def startup():
    """Implement CISO Assistant 1.0 default Roles and User Groups"""

    from ciso_assistant.settings import (
        CISO_ASSISTANT_SUPERUSER_EMAIL,
    )
    from django.contrib.auth.models import Permission
    from iam.models import Folder, Role, RoleAssignment, User, UserGroup

    auditor_permissions = Permission.objects.filter(
        codename__in=[
            "view_project",
            "view_riskassessment",
            "view_securitymeasure",
            "view_policy",
            "view_riskscenario",
            "view_riskacceptance",
            "view_asset",
            "view_threat",
            "view_securityfunction",
            "view_folder",
            "view_usergroup",
            "view_riskmatrix" "view_complianceassessment",
            "view_requirementassessment",
            "view_requirement",
            "view_evidence",
            "view_framework",
        ]
    )

    approver_permissions = Permission.objects.filter(
        codename__in=[
            "view_project",
            "view_riskassessment",
            "view_securitymeasure",
            "view_policy",
            "view_riskscenario",
            "view_riskacceptance",
            "approve_riskacceptance",
            "view_asset",
            "view_threat",
            "view_securityfunction",
            "view_folder",
            "view_usergroup",
            "view_riskmatrix",
            "view_complianceassessment",
            "view_requirementassessment",
            "view_requirement",
            "view_evidence",
            "view_framework",
        ]
    )

    analyst_permissions = Permission.objects.filter(
        codename__in=[
            "add_project",
            "view_project",
            "change_project",
            "delete_project",
            "add_riskassessment",
            "view_riskassessment",
            "change_riskassessment",
            "delete_riskassessment",
            "add_securitymeasure",
            "view_securitymeasure",
            "change_securitymeasure",
            "delete_securitymeasure",
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
            "view_asset",
            "view_threat",
            "view_securityfunction",
            "view_folder",
            "view_usergroup",
            "view_riskmatrix",
            "view_requirement",
            "view_framework",
        ]
    )

    domain_manager_permissions = Permission.objects.filter(
        codename__in=[
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
            "add_securitymeasure",
            "view_securitymeasure",
            "change_securitymeasure",
            "delete_securitymeasure",
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
            "view_asset",
            "view_threat",
            "view_securityfunction",
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
            "view_requirement",
            "view_framework",
        ]
    )

    administrator_permissions = Permission.objects.filter(
        codename__in=[
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
            "add_securityfunction",
            "view_securityfunction",
            "change_securityfunction",
            "delete_securityfunction",
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
            "add_securitymeasure",
            "view_securitymeasure",
            "change_securitymeasure",
            "delete_securitymeasure",
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
            "delete_library",
            "backup",
            "restore",
        ]
    )

    # if superuser defined and does not exist, then create it
    if (
        CISO_ASSISTANT_SUPERUSER_EMAIL
        and not User.objects.filter(email=CISO_ASSISTANT_SUPERUSER_EMAIL).exists()
    ):
        User.objects.create_superuser(
            email=CISO_ASSISTANT_SUPERUSER_EMAIL, is_superuser=True
        )
    # if root folder does not exist, then create it
    if not Folder.objects.filter(content_type=Folder.ContentType.ROOT).exists():
        Folder.objects.create(
            name="Global", content_type=Folder.ContentType.ROOT, builtin=True
        )
        auditor = Role.objects.create(name="BI-RL-AUD", builtin=True)
        auditor.permissions.set(auditor_permissions)
        approver = Role.objects.create(name="BI-RL-VAL", builtin=True)
        approver.permissions.set(approver_permissions)
        analyst = Role.objects.create(name="BI-RL-ANA", builtin=True)
        analyst.permissions.set(analyst_permissions)
        domain_manager = Role.objects.create(name="BI-RL-DMA", builtin=True)
        domain_manager.permissions.set(domain_manager_permissions)
        administrator = Role.objects.create(name="BI-RL-ADM", builtin=True)
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
    # if global validators user group does not exist, then create it
    if not UserGroup.objects.filter(
        name="BI-UG-GVA", folder=Folder.get_root_folder()
    ).exists():
        global_validators = UserGroup.objects.create(
            name="BI-UG-GVA",
            folder=Folder.objects.get(content_type=Folder.ContentType.ROOT),
            builtin=True,
        )
        ra2 = RoleAssignment.objects.create(
            user_group=global_validators,
            role=Role.objects.get(name="BI-RL-VAL"),
            is_recursive=True,
            builtin=True,
            folder=Folder.get_root_folder(),
        )
        ra2.perimeter_folders.add(global_validators.folder)
    # add any superuser to the global administrors group, in case it is not yet done
    for superuser in User.objects.filter(is_superuser=True):
        UserGroup.objects.get(name="BI-UG-ADM").user_set.add(superuser)
    # fix administrator role, to facilitate migrations
    administrator = Role.objects.filter(name="BI-RL-ADM").first()
    administrator.permissions.set(administrator_permissions)


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"
    verbose_name = "Core"

    def ready(self):
        import os

        if os.environ.get("RUN_MAIN"):
            """Only called in main, not during makemigrations or migrate"""
            startup()
