"""
Management command that audits RBAC visibility for a given folder (domain).

It delegates to `core.audit_visibility.audit_visibility_leaks` and exits with a
non-zero status if leaks are detected. Useful in CI or ad-hoc diagnostics.
"""

from django.core.management.base import BaseCommand, CommandError

from core.models import Folder
from core.audit_visibility import audit_visibility_leaks
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = (
        "Audit RBAC visibility across the whole folder tree (starting from the root)."
    )

    def handle(self, *args, **options):
        root = Folder.get_root_folder()
        if not root:
            raise CommandError("Root folder not found. Run the startup routine first.")

        User = get_user_model()
        admin = User.objects.filter(is_superuser=True).order_by("id").first()
        if not admin:
            raise RuntimeError("Visibility audit requires at least one superuser.")

        leaks = audit_visibility_leaks(admin)

        if not leaks:
            self.stdout.write(self.style.SUCCESS("No visibility leaks detected."))
            return

        self.stdout.write(self.style.WARNING(f"{len(leaks)} leak(s) detected:"))
        for leak in leaks:
            reference_name = leak.get("reference_name") or f"#{leak['reference_id']}"
            secondary_name = leak.get("secondary_name") or f"#{leak['secondary_id']}"
            reference_folder_label = leak.get("reference_folder_name") or leak.get(
                "reference_folder"
            )
            secondary_folder_label = leak.get("secondary_folder_name") or leak.get(
                "secondary_folder"
            )
            self.stdout.write(
                f"Scope={leak['scope_folder_name']}  -  "
                f'{leak["reference_model"]}="{reference_name}"'
                f' -> {leak["relation"]} -> {leak["secondary_model"]} "{secondary_name}" '
                f"[reference folder={reference_folder_label}, secondary folder={secondary_folder_label}]"
            )

        raise CommandError("Visibility leaks detected.")
