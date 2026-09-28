"""Normalise third-party workspaces: one per entity per domain, named after it.

For support: a dry run, or `--apply` to rerun after fixing what made an entity fail.
"""

from django.core.management.base import BaseCommand

from tprm.services import normalize_entity_workspaces


class Command(BaseCommand):
    help = "One third-party workspace per entity per domain, named after the entity."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="Write the changes.")
        parser.add_argument("--entity", help="Restrict to one entity name.")

    def handle(self, *args, **options):
        plan = normalize_entity_workspaces(
            apply=options["apply"], entity_name=options.get("entity")
        )
        if not plan:
            self.stdout.write("Nothing to do: every workspace is already the entity's.")
            return

        for row in plan:
            self.stdout.write("")
            self.stdout.write(f"{row['entity'].name}  (domain: {row['domain'].name})")
            if row["action"] == "rename":
                self.stdout.write(f"  rename '{row['from']}' -> '{row['to']}'")
            else:
                for folder, audits in row["workspaces"].items():
                    self.stdout.write(f"  - {folder.name}")
                    for audit in audits:
                        self.stdout.write(f"      audit: {audit}")
                moves = ", ".join(
                    f"{n} {m._meta.label.split('.')[-1]}"
                    for m, n in row["contents"].items()
                )
                self.stdout.write(f"    moves: {moves or 'nothing'}")
                self.stdout.write(
                    "    afterwards these can see every round: "
                    + (", ".join(row["members"]) or "none")
                )
            if row["error"]:
                self.stdout.write(self.style.ERROR(f"    -> skipped: {row['error']}"))
            elif row["result"]:
                self.stdout.write(self.style.SUCCESS("    -> done"))

        if not options["apply"]:
            self.stdout.write("")
            self.stdout.write("Dry run. Re-run with --apply to write these changes.")
