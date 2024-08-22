from django.apps import AppConfig
from django.db.models.signals import post_migrate
import os

from ciso_assistant.settings import CISO_ASSISTANT_SUPERUSER_EMAIL
from django.core.management import call_command

from structlog import get_logger

logger = get_logger(__name__)

READER_PERMISSIONS_LIST = [
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
    "view_loadedlibrary",
    "view_storedlibrary",
    "view_user",
    "view_requirementmappingset",
    "view_requirementmapping",
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
    "view_storedlibrary",
    "view_loadedlibrary",
    "view_user",
    "view_requirementmappingset",
    "view_requirementmapping",
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
    "view_storedlibrary",
    "view_loadedlibrary",
    "view_user",
    "view_requirementmappingset",
    "view_requirementmapping",
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
    "view_storedlibrary",
    "view_loadedlibrary",
    "view_user",
    "view_requirementmappingset",
    "view_requirementmapping",
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
    "view_storedlibrary",
    "add_storedlibrary",
    "delete_storedlibrary",
    "view_loadedlibrary",
    "add_loadedlibrary",
    "delete_loadedlibrary",
    "backup",
    "restore",
    "view_globalsettings",
    "change_globalsettings",
    "view_requirementmappingset",
    "view_requirementmapping",
    "add_entity",
    "change_entity",
    "view_entity",
    "delete_entity",
    "add_representative",
    "change_representative",
    "view_representative",
    "delete_representative",
    "add_solution",
    "change_solution",
    "view_solution",
    "delete_solution",
    "add_product",
    "change_product",
    "view_product",
    "delete_product",
    "add_entityassessment",
    "change_entityassessment",
    "view_entityassessment",
    "delete_entityassessment",
]


def startup(sender: AppConfig, **kwargs):
    """
    Implement CISO Assistant 1.0 default Roles and User Groups during migrate
    This makes sure root folder and global groups are defined before any other object is created
    Create superuser if CISO_ASSISTANT_SUPERUSER_EMAIL defined
    """
    from django.contrib.auth.models import Permission
    from allauth.socialaccount.providers.saml.provider import SAMLProvider
    from iam.models import Folder, Role, RoleAssignment, User, UserGroup
    from global_settings.models import GlobalSettings

    print("startup handler: initialize database")

    reader_permissions = Permission.objects.filter(codename__in=READER_PERMISSIONS_LIST)

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
    reader, created = Role.objects.get_or_create(name="BI-RL-AUD", builtin=True)
    reader.permissions.set(reader_permissions)
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
    # if global readers user group does not exist, then create it
    if not UserGroup.objects.filter(
        name="BI-UG-GAD", folder=Folder.get_root_folder()
    ).exists():
        global_readers = UserGroup.objects.create(
            name="BI-UG-GAD",
            folder=Folder.objects.get(content_type=Folder.ContentType.ROOT),
            builtin=True,
        )
        ra2 = RoleAssignment.objects.create(
            user_group=global_readers,
            role=Role.objects.get(name="BI-RL-AUD"),
            is_recursive=True,
            builtin=True,
            folder=Folder.get_root_folder(),
        )
        ra2.perimeter_folders.add(global_readers.folder)
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

    default_attribute_mapping = SAMLProvider.default_attribute_mapping

    settings = {
        "attribute_mapping": {
            "uid": default_attribute_mapping["uid"],
            "email_verified": default_attribute_mapping["email_verified"],
            "email": default_attribute_mapping["email"],
        },
        "idp": {
            "entity_id": "",
            "metadata_url": "",
            "sso_url": "",
            "slo_url": "",
            "x509cert": "",
        },
        "sp": {
            "entity_id": "ciso-assistant",
        },
        "advanced": {
            "allow_repeat_attribute_name": True,
            "allow_single_label_domains": False,
            "authn_request_signed": False,
            "digest_algorithm": "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256",
            "logout_request_signed": False,
            "logout_response_signed": False,
            "metadata_signed": False,
            "name_id_encrypted": False,
            "reject_deprecated_algorithm": True,
            "reject_idp_initiated_sso": True,
            "signature_algorithm": "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256",
            "want_assertion_encrypted": False,
            "want_assertion_signed": False,
            "want_attribute_statement": True,
            "want_message_signed": False,
            "want_name_id": False,
            "want_name_id_encrypted": False,
        },
    }

    if not GlobalSettings.objects.filter(name=GlobalSettings.Names.SSO).exists():
        logger.info("SSO settings not found, creating default settings")
        sso_settings = GlobalSettings.objects.create(
            name=GlobalSettings.Names.SSO,
            value={"client_id": "0", "settings": settings},
        )
        logger.info("SSO settings created", settings=sso_settings.value)

    call_command("storelibraries")


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"
    verbose_name = "Core"

    def ready(self):
        # avoid post_migrate handler if we are in the main, as it interferes with restore
        if not os.environ.get("RUN_MAIN"):
            post_migrate.connect(startup, sender=self)
