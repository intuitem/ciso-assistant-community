"""Seed the deterministic demo dataset.

Unlike the ``populate_*`` commands this one uses a seeded RNG and a fixed
vocabulary, so two runs on the same checkout produce identical content. The
content itself lives in per-app ``demo_builders`` modules (see ``core.demo``).

    manage.py seed_demo                    # live demo, dates relative to today
    manage.py seed_demo --docs --flush     # documentation screenshots
"""

from django.core.management.base import BaseCommand, CommandError

from core import demo
from global_settings.models import GlobalSettings


class Command(BaseCommand):
    help = "Seed the deterministic demo dataset."

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Delete the demo domain and everything under it before seeding.",
        )
        parser.add_argument(
            "--docs",
            action="store_true",
            help="Screenshot mode: freeze dates and hide the Get Started call to action.",
        )
        parser.add_argument(
            "--anchor",
            choices=["today", "frozen"],
            help="Date every offset is relative to (default: frozen with --docs, else today).",
        )
        parser.add_argument(
            "--modules",
            help="Comma-separated builders to run, dependencies included (default: all).",
        )
        parser.add_argument(
            "--domain",
            default=demo.DEFAULT_DOMAIN,
            help=f"Root-level domain to seed into (default: {demo.DEFAULT_DOMAIN}).",
        )
        parser.add_argument(
            "--list",
            action="store_true",
            help="List the available builders and exit.",
        )

    def handle(self, *args, **options):
        if options["list"]:
            for builder in demo.builders():
                deps = (
                    f" (needs {', '.join(builder.depends)})" if builder.depends else ""
                )
                self.stdout.write(f"{builder.name}{deps}")
            return

        anchor = options["anchor"] or ("frozen" if options["docs"] else "today")
        modules = options["modules"]
        try:
            demo.seed(
                domain_name=options["domain"],
                modules=[m.strip() for m in modules.split(",")] if modules else None,
                frozen=anchor == "frozen",
                reset=options["flush"],
                out=self.stdout.write,
                err=self.stderr.write,
            )
        except demo.NotADemoDomain as e:
            raise CommandError(e) from e
        if options["docs"]:
            self.hide_get_started()
        self.stdout.write(self.style.SUCCESS("demo dataset ready"))

    def hide_get_started(self):
        """Drop chrome that is meaningful in a live instance but noise in a doc."""
        setting, _ = GlobalSettings.objects.get_or_create(
            name=GlobalSettings.Names.GENERAL,
            defaults={"value": dict(GlobalSettings.GENERAL_DEFAULT_VALUE)},
        )
        value = dict(setting.value or {})
        value["show_get_started"] = False
        setting.value = value
        setting.save(update_fields=["value"])
