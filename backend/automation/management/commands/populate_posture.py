import random
import uuid
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from automation.models import PostureAssessment, PostureResult, PostureRun
from core.models import (
    Asset,
    Finding,
    FindingsAssessment,
    Framework,
    LoadedLibrary,
    RequirementNode,
    StoredLibrary,
)
from iam.models import Folder

K8S_LIBRARY_URN = "urn:intuitem:risk:library:cis-benchmark-kubernetes"
DOMAIN_NAME = "TEST-Posture"


class Command(BaseCommand):
    help = "Populates a posture assessment with a simulated scan history for testing"

    def add_arguments(self, parser):
        parser.add_argument(
            "--assets",
            type=int,
            default=6,
            help="Number of fleet assets to create (default: 6)",
        )
        parser.add_argument(
            "--days",
            type=int,
            default=14,
            help="Days of scan history, one run per asset per day (default: 14)",
        )
        parser.add_argument(
            "--clean",
            action="store_true",
            help="Delete the TEST-Posture domain and its data (does not create new data)",
        )
        parser.add_argument(
            "--fresh",
            action="store_true",
            help="Delete existing test data and create fresh data",
        )

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("populate_posture requires DJANGO_DEBUG=True")
        if options["clean"] or options["fresh"]:
            self.clean()
            if options["clean"]:
                return
        self.populate(options["assets"], options["days"])

    def clean(self):
        domain = Folder.objects.filter(name=DOMAIN_NAME).first()
        if domain:
            results = PostureResult.objects.filter(
                run__posture_assessment__folder=domain
            ).count()
            domain.delete()
            self.stdout.write(
                self.style.SUCCESS(
                    f"Cleaned domain '{DOMAIN_NAME}' ({results} posture results)"
                )
            )
        else:
            self.stdout.write("Nothing to clean")
        Framework.objects.filter(name__startswith="TEST-Posture").delete()

    def get_framework(self):
        framework = Framework.objects.filter(library__urn=K8S_LIBRARY_URN).first()
        if framework:
            return framework
        stored = StoredLibrary.objects.filter(urn=K8S_LIBRARY_URN).first()
        if stored and not LoadedLibrary.objects.filter(urn=K8S_LIBRARY_URN).exists():
            error = stored.load()
            if not error:
                return Framework.objects.get(library__urn=K8S_LIBRARY_URN)
        root = Folder.get_root_folder()
        framework = Framework.objects.create(
            name="TEST-Posture benchmark", folder=root, is_published=True
        )
        for section in range(1, 4):
            for item in range(1, 11):
                RequirementNode.objects.create(
                    framework=framework,
                    urn=f"urn:test:posture-demo:req:{section}.{item}",
                    ref_id=f"{section}.{item}",
                    name=f"Ensure demo setting {section}.{item} is hardened",
                    assessable=True,
                    folder=root,
                    is_published=True,
                )
        return framework

    @transaction.atomic
    def populate(self, asset_count, days):
        if Folder.objects.filter(name=DOMAIN_NAME).exists():
            self.stdout.write(
                self.style.WARNING(
                    f"Domain '{DOMAIN_NAME}' already exists — use --fresh to recreate"
                )
            )
            return

        random.seed(42)
        framework = self.get_framework()
        checks = list(
            RequirementNode.objects.filter(
                framework=framework, assessable=True
            ).exclude(ref_id="")
        )

        domain = Folder.objects.create(
            parent_folder=Folder.get_root_folder(),
            name=DOMAIN_NAME,
            content_type=Folder.ContentType.DOMAIN,
        )
        assets = [
            Asset.objects.create(name=f"TEST-vm-{i + 1:02d}", folder=domain)
            for i in range(asset_count)
        ]
        pa = PostureAssessment.objects.create(
            name="TEST-Posture fleet",
            folder=domain,
            framework=framework,
            history_depth=days,
        )
        pa.assets.set(assets)

        not_applicable = set(random.sample(checks, min(4, len(checks))))
        persistent_fails = {
            (check, asset)
            for check in random.sample(checks, min(3, len(checks)))
            for asset in random.sample(assets, max(1, asset_count // 3))
        }

        now = timezone.now()
        rows = []
        runs = []
        for day in range(days):
            timestamp = now - timedelta(days=days - 1 - day, hours=random.randint(0, 5))
            pass_probability = 0.6 + 0.32 * (day / max(days - 1, 1))
            for asset in assets:
                run = PostureRun(
                    id=uuid.uuid4(),
                    posture_assessment=pa,
                    started_at=timestamp,
                    tool="populate-posture 1.0",
                )
                runs.append(run)
                for check in checks:
                    if check in not_applicable:
                        result = "not_applicable"
                    elif (check, asset) in persistent_fails:
                        result = "fail"
                    else:
                        roll = random.random()
                        if roll < pass_probability:
                            result = "pass"
                        elif roll < pass_probability + 0.03:
                            result = "error"
                        elif roll < pass_probability + 0.06:
                            result = "not_checked"
                        else:
                            result = "fail"
                    rows.append(
                        PostureResult(
                            requirement=check,
                            asset=asset,
                            result=result,
                            timestamp=timestamp,
                            run=run,
                            actual="PermissionsMode=0666" if result == "fail" else "",
                            expected="PermissionsMode=0644" if result == "fail" else "",
                            message="scan timeout" if result == "error" else "",
                            source=PostureResult.Source.IMPORT,
                        )
                    )
        PostureRun.objects.bulk_create(runs, batch_size=2000)
        PostureResult.objects.bulk_create(rows, batch_size=2000)

        follow_up = FindingsAssessment.objects.create(
            name=f"{pa.name} — follow-up",
            folder=domain,
            category=FindingsAssessment.Category.POSTURE,
        )
        pa.follow_up_assessment = follow_up
        pa.save(update_fields=["follow_up_assessment"])
        planned = random.sample(sorted(persistent_fails, key=lambda p: p[0].ref_id), 2)
        for i, (check, asset) in enumerate(planned):
            Finding.objects.create(
                findings_assessment=follow_up,
                folder=domain,
                requirement_node=check,
                asset=asset,
                name=f"{check.ref_id} failing on {asset.name}"[:200],
                description="actual: PermissionsMode=0666\nexpected: PermissionsMode=0644",
                status=Finding.Status.IN_PROGRESS
                if i == 0
                else Finding.Status.IDENTIFIED,
                eta=(now + timedelta(days=14)).date() if i == 0 else None,
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Created '{pa.name}' in domain '{DOMAIN_NAME}': "
                f"{len(assets)} assets, {len(checks)} checks, {days} days of runs "
                f"({len(rows)} results), score {pa.get_score()}%, "
                f"{len(planned)}/{len(persistent_fails)} persistent fails planned"
            )
        )
        self.stdout.write(f"→ /posture-assessments/{pa.id}")
