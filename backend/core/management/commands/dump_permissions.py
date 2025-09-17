from django.core.management.base import BaseCommand
from django.contrib.auth.models import Permission
from iam.models import Role, UserGroup, RoleAssignment, Folder
from django.apps import apps
import json


class Command(BaseCommand):
    help = "Dump permissions, roles, and user groups for debugging"

    def add_arguments(self, parser):
        parser.add_argument(
            "--format",
            type=str,
            choices=["json", "text"],
            default="text",
            help="Output format (json or text)",
        )

    def handle(self, *args, **options):
        format_type = options["format"]

        # Collect all data
        data = {
            "permissions": self.get_permissions_data(),
            "roles": self.get_roles_data(),
            "user_groups": self.get_user_groups_data(),
            "role_assignments": self.get_role_assignments_data(),
            "folders": self.get_folders_data(),
            "models": self.get_models_data(),
            "enterprise_data": self.get_enterprise_data(),
        }

        if format_type == "json":
            self.stdout.write(json.dumps(data, indent=2))
        else:
            self.print_text_format(data)

    def get_permissions_data(self):
        permissions = []
        for perm in Permission.objects.all().order_by(
            "content_type__app_label", "codename"
        ):
            permissions.append(
                {
                    "id": str(perm.id),
                    "codename": perm.codename,
                    "name": perm.name,
                    "app_label": perm.content_type.app_label,
                    "model": perm.content_type.model,
                }
            )
        return permissions

    def get_roles_data(self):
        roles = []
        for role in Role.objects.all().order_by("name"):
            role_perms = list(role.permissions.values_list("codename", flat=True))
            roles.append(
                {
                    "id": str(role.id),
                    "name": role.name,
                    "builtin": role.builtin,
                    "permissions_count": len(role_perms),
                    "permissions": sorted(role_perms),
                }
            )
        return roles

    def get_user_groups_data(self):
        user_groups = []
        for ug in UserGroup.objects.all().order_by("name"):
            user_groups.append(
                {
                    "id": str(ug.id),
                    "name": ug.name,
                    "builtin": ug.builtin,
                    "folder": ug.folder.name if ug.folder else None,
                }
            )
        return user_groups

    def get_role_assignments_data(self):
        assignments = []
        for ra in RoleAssignment.objects.all():
            assignments.append(
                {
                    "id": str(ra.id),
                    "user_group": ra.user_group.name if ra.user_group else None,
                    "role": ra.role.name if ra.role else None,
                    "folder": ra.folder.name if ra.folder else None,
                    "is_recursive": ra.is_recursive,
                    "builtin": ra.builtin,
                }
            )
        return assignments

    def get_folders_data(self):
        folders = []
        for folder in Folder.objects.all().order_by("name"):
            folders.append(
                {
                    "id": str(folder.id),
                    "name": folder.name,
                    "content_type": folder.content_type,
                    "builtin": folder.builtin,
                    "parent": folder.parent_folder.name
                    if folder.parent_folder
                    else None,
                }
            )
        return folders

    def get_models_data(self):
        models_info = []
        for app_config in apps.get_app_configs():
            for model in app_config.get_models():
                models_info.append(
                    {
                        "app_label": model._meta.app_label,
                        "model_name": model._meta.model_name,
                        "table_name": model._meta.db_table,
                    }
                )
        return models_info

    def get_enterprise_data(self):
        try:
            from enterprise_core.models import ClientSettings

            client_settings = []
            for cs in ClientSettings.objects.all():
                client_settings.append(
                    {
                        "id": str(cs.id),
                        "created_at": cs.created_at.isoformat()
                        if hasattr(cs, "created_at")
                        else None,
                    }
                )
            return {"client_settings": client_settings, "available": True}
        except Exception as e:
            return {"client_settings": [], "available": False, "error": str(e)}

    def print_text_format(self, data):
        self.stdout.write(self.style.SUCCESS("=== PERMISSIONS DUMP ==="))

        self.stdout.write(f"\n📋 PERMISSIONS ({len(data['permissions'])} total):")
        for perm in data["permissions"]:
            self.stdout.write(
                f"  {perm['app_label']}.{perm['codename']} - {perm['name']}"
            )

        self.stdout.write(f"\n🎭 ROLES ({len(data['roles'])} total):")
        for role in data["roles"]:
            builtin_marker = " [BUILTIN]" if role["builtin"] else ""
            self.stdout.write(
                f"  {role['name']}{builtin_marker} ({role['permissions_count']} permissions)"
            )
            if role["permissions"]:
                for perm in role["permissions"][:10]:  # Show first 10
                    self.stdout.write(f"    - {perm}")
                if len(role["permissions"]) > 10:
                    self.stdout.write(
                        f"    ... and {len(role['permissions']) - 10} more"
                    )

        self.stdout.write(f"\n👥 USER GROUPS ({len(data['user_groups'])} total):")
        for ug in data["user_groups"]:
            builtin_marker = " [BUILTIN]" if ug["builtin"] else ""
            folder_info = f" (folder: {ug['folder']})" if ug["folder"] else ""
            self.stdout.write(f"  {ug['name']}{builtin_marker}{folder_info}")

        self.stdout.write(
            f"\n🔗 ROLE ASSIGNMENTS ({len(data['role_assignments'])} total):"
        )
        for ra in data["role_assignments"]:
            builtin_marker = " [BUILTIN]" if ra["builtin"] else ""
            recursive_marker = " [RECURSIVE]" if ra["is_recursive"] else ""
            self.stdout.write(
                f"  {ra['user_group']} -> {ra['role']} in {ra['folder']}{builtin_marker}{recursive_marker}"
            )

        # Summary of key items
        self.stdout.write(f"\n📊 SUMMARY:")
        key_roles = ["BI-RL-ADM", "BI-RL-AUD", "BI-RL-ANA", "BI-RL-DMA", "BI-RL-APP"]
        key_groups = ["BI-UG-ADM", "BI-UG-GAD", "BI-UG-GAN", "BI-UG-GAP"]

        existing_roles = [r["name"] for r in data["roles"]]
        existing_groups = [g["name"] for g in data["user_groups"]]

        self.stdout.write("  Key Roles:")
        for role in key_roles:
            status = "✅" if role in existing_roles else "❌"
            self.stdout.write(f"    {status} {role}")

        self.stdout.write("  Key User Groups:")
        for group in key_groups:
            status = "✅" if group in existing_groups else "❌"
            self.stdout.write(f"    {status} {group}")

        # Check for Event permissions specifically
        event_perms = [p for p in data["permissions"] if "event" in p["codename"]]
        self.stdout.write(f"\n🎫 EVENT PERMISSIONS ({len(event_perms)} total):")
        for perm in event_perms:
            self.stdout.write(f"  {perm['app_label']}.{perm['codename']}")

        # Check folders
        self.stdout.write(f"\n📁 FOLDERS ({len(data['folders'])} total):")
        for folder in data["folders"]:
            builtin_marker = " [BUILTIN]" if folder["builtin"] else ""
            parent_info = f" (parent: {folder['parent']})" if folder["parent"] else ""
            self.stdout.write(
                f"  {folder['name']} ({folder['content_type']}){builtin_marker}{parent_info}"
            )

        # Check enterprise data
        enterprise = data["enterprise_data"]
        self.stdout.write(f"\n🏢 ENTERPRISE DATA:")
        if enterprise["available"]:
            self.stdout.write(
                f"  ✅ ClientSettings available ({len(enterprise['client_settings'])} records)"
            )
            for cs in enterprise["client_settings"]:
                self.stdout.write(f"    - {cs['id']} (created: {cs['created_at']})")
        else:
            self.stdout.write(
                f"  ❌ ClientSettings not available: {enterprise['error']}"
            )

        # Check models
        self.stdout.write(f"\n📦 MODELS ({len(data['models'])} total):")
        app_models = {}
        for model in data["models"]:
            app_label = model["app_label"]
            if app_label not in app_models:
                app_models[app_label] = []
            app_models[app_label].append(model["model_name"])

        for app_label in sorted(app_models.keys()):
            models_list = ", ".join(sorted(app_models[app_label]))
            self.stdout.write(f"  {app_label}: {models_list}")
