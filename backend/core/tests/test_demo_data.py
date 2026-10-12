"""The demo dataset: coverage of API models, determinism, date anchoring, scoping.

If ``test_every_api_model_is_classified`` fails on your new model, either add
it to a builder's ``covers`` (see ``core/demo_builders.py``) or list it in
``core/demo/coverage.py`` with a reason.
"""

from datetime import date, timedelta

import pytest
from django.urls import URLResolver, get_resolver
from knox.models import AuthToken
from rest_framework.test import APIClient

from core import demo
from core.apps import startup
from core.demo.coverage import MAX_PENDING, PENDING, classification
from core.models import AppliedControl, ComplianceAssessment, DemoManifest
from iam.models import Folder, User, UserGroup

DOMAIN = "Demo coverage test"


def api_models() -> set[str]:
    """Labels of every model served by an API ViewSet."""
    found = set()

    def walk(patterns):
        for pattern in patterns:
            if isinstance(pattern, URLResolver):
                walk(pattern.url_patterns)
                continue
            cls = getattr(pattern.callback, "cls", None)
            model = getattr(cls, "model", None) or getattr(
                getattr(cls, "queryset", None), "model", None
            )
            if model is not None:
                found.add(model._meta.label)

    walk(get_resolver().url_patterns)
    return found


def covered_models() -> set[str]:
    return {m._meta.label for b in demo.builders() for m in b.covers}


def signature(ctx) -> dict[str, list]:
    """Everything a builder created, as text: str() plus sorted M2M targets."""
    folders = ctx.folders()
    result = {}
    for builder in demo.builders():
        for model, lookup in builder.covers.items():
            rows = []
            for obj in model.objects.filter(**{f"{lookup}__in": folders}):
                links = [
                    sorted(str(r) for r in getattr(obj, f.name).all())
                    for f in model._meta.many_to_many
                ]
                rows.append(repr((str(obj), links)))
            result[model._meta.label] = sorted(rows)
    return result


def test_every_api_model_is_classified():
    excluded, pending = classification()
    unclassified = api_models() - covered_models() - set(excluded) - pending
    assert not unclassified, (
        "API models with no demo data and no stated reason; add a builder or "
        f"list them in core/demo/coverage.py: {sorted(unclassified)}"
    )


def test_classification_has_no_stale_entries():
    excluded, pending = classification()
    covered = covered_models()
    served = api_models()
    assert not (covered & pending), (
        f"covered by a builder, remove from PENDING: {sorted(covered & pending)}"
    )
    assert not (covered & set(excluded)), (
        f"covered by a builder, remove from EXCLUDED: {sorted(covered & set(excluded))}"
    )
    assert not (set(excluded) & pending), sorted(set(excluded) & pending)
    stale = (set(excluded) | pending) - served
    assert not stale, f"no longer served by the API: {sorted(stale)}"


def test_pending_backlog_only_shrinks():
    assert len(PENDING) <= MAX_PENDING, (
        f"PENDING grew to {len(PENDING)} (max {MAX_PENDING}): new models need a "
        "builder, or a reason in EXCLUDED"
    )
    assert len(PENDING) == MAX_PENDING, (
        f"PENDING shrank to {len(PENDING)}: lower MAX_PENDING in "
        "core/demo/coverage.py to lock in the progress"
    )


def test_module_selection_pulls_dependencies():
    names = [b.name for b in demo.builders(["risk"])]
    assert names == ["core", "risk"]
    with pytest.raises(ValueError):
        demo.builders(["no-such-module"])


@pytest.mark.django_db
def test_seed_populates_every_covered_model():
    ctx = demo.seed(domain_name=DOMAIN, out=lambda _: None, err=pytest.fail)
    folders = ctx.folders()
    empty = [
        model._meta.label
        for builder in demo.builders()
        for model, lookup in builder.covers.items()
        if not model.objects.filter(**{f"{lookup}__in": folders}).exists()
    ]
    assert not empty, f"builders declare these but created none: {empty}"


@pytest.mark.django_db
def test_seed_is_deterministic():
    quiet = {"out": lambda _: None, "err": pytest.fail}
    first = signature(demo.seed(domain_name=DOMAIN, **quiet))
    second = signature(demo.seed(domain_name=DOMAIN, reset=True, **quiet))
    assert first == second


@pytest.mark.django_db
def test_seed_is_idempotent():
    quiet = {"out": lambda _: None, "err": pytest.fail}
    first = signature(demo.seed(domain_name=DOMAIN, **quiet))
    again = signature(demo.seed(domain_name=DOMAIN, **quiet))
    assert first == again


@pytest.mark.django_db
@pytest.mark.parametrize(
    "frozen, anchor",
    [(True, demo.FROZEN_ANCHOR), (False, date.today())],
)
def test_dates_follow_the_anchor(frozen, anchor):
    ctx = demo.seed(
        domain_name=DOMAIN, frozen=frozen, out=lambda _: None, err=pytest.fail
    )
    control = AppliedControl.objects.get(folder=ctx.domain, ref_id="AC.001")
    assert control.eta == anchor + timedelta(days=30)
    audit = ComplianceAssessment.objects.get(folder=ctx.domain, ref_id="AUD.2026.01")
    assert audit.due_date == anchor + timedelta(days=45)
    assert control.created_at.date() <= date.today()


@pytest.mark.django_db
def test_flush_clears_protected_rows_inside_the_demo_tree():
    from metrology.models import MetricDefinition, MetricInstance

    ctx = demo.seed(
        domain_name=DOMAIN, modules=["core"], out=lambda _: None, err=pytest.fail
    )
    definition = MetricDefinition.objects.create(
        name="Demo metric", ref_id="T-MET", folder=ctx.domain
    )
    # MetricInstance -> MetricDefinition is PROTECT, which a plain cascade trips on.
    MetricInstance.objects.create(
        name="Demo instance", metric_definition=definition, folder=ctx.domain
    )
    demo.flush(DOMAIN)
    assert not Folder.objects.filter(**demo.demo_domain_filter(DOMAIN)).exists()


@pytest.mark.django_db
def test_flush_refuses_when_user_data_depends_on_the_demo():
    from django.db.models import ProtectedError

    from metrology.models import MetricDefinition, MetricInstance

    ctx = demo.seed(
        domain_name=DOMAIN, modules=["core"], out=lambda _: None, err=pytest.fail
    )
    definition = MetricDefinition.objects.create(
        name="Demo metric", ref_id="T-MET", folder=ctx.domain
    )
    customer = Folder.objects.create(
        name="Customer domain",
        content_type=Folder.ContentType.DOMAIN,
        parent_folder=Folder.get_root_folder(),
    )
    theirs = MetricInstance.objects.create(
        name="Their instance", metric_definition=definition, folder=customer
    )
    with pytest.raises(ProtectedError):
        demo.flush(DOMAIN)
    assert MetricInstance.objects.filter(pk=theirs.pk).exists()
    assert Folder.objects.filter(**demo.demo_domain_filter(DOMAIN)).exists()


@pytest.mark.django_db
def test_flush_only_touches_the_root_level_demo_domain():
    unrelated = Folder.objects.create(
        name="Unrelated parent",
        content_type=Folder.ContentType.DOMAIN,
        parent_folder=Folder.get_root_folder(),
    )
    namesake = Folder.objects.create(
        name=DOMAIN, content_type=Folder.ContentType.DOMAIN, parent_folder=unrelated
    )
    demo.seed(domain_name=DOMAIN, out=lambda _: None, err=pytest.fail)
    demo.flush(DOMAIN)
    assert Folder.objects.filter(pk=namesake.pk).exists()
    assert not Folder.objects.filter(**demo.demo_domain_filter(DOMAIN)).exists()


@pytest.mark.django_db
def test_manifest_lists_what_the_seed_created_and_nothing_else():
    quiet = {"out": lambda _: None, "err": pytest.fail}
    ctx = demo.seed(domain_name=DOMAIN, modules=["core"], **quiet)
    manifest = DemoManifest.objects.get(domain=ctx.domain)
    assert manifest.version == demo.DEMO_VERSION
    assert manifest.anchor == ctx.anchor
    contents = {tuple(e) for e in manifest.contents}
    seeded = AppliedControl.objects.get(folder=ctx.domain, ref_id="AC.001")
    assert ("iam.Folder", str(ctx.domain.pk)) in contents
    assert ("core.AppliedControl", str(seeded.pk)) in contents
    assert UserGroup.objects.filter(folder=ctx.domain).exists()

    theirs = AppliedControl.objects.create(name="Their control", folder=ctx.domain)
    demo.seed(domain_name=DOMAIN, modules=["core"], **quiet)
    contents = {tuple(e) for e in DemoManifest.objects.get(domain=ctx.domain).contents}
    assert ("core.AppliedControl", str(seeded.pk)) in contents
    assert ("core.AppliedControl", str(theirs.pk)) not in contents

    demo.flush(DOMAIN)
    assert not DemoManifest.objects.exists()


def api_client(admin: bool) -> APIClient:
    startup(sender=None)
    user = User.objects.create_user(f"{'admin' if admin else 'reader'}@demo.test")
    if admin:
        UserGroup.objects.get(name="BI-UG-ADM").user_set.add(user)
    client = APIClient()
    client.credentials(
        HTTP_AUTHORIZATION=f"Token {AuthToken.objects.create(user=user)[1]}"
    )
    return client


LOAD_DEMO = "/api/folders/import-dummy/"


@pytest.mark.django_db
def test_load_demo_endpoint_seeds_once():
    client = api_client(admin=True)
    response = client.post(LOAD_DEMO)
    assert response.status_code == 200, response.content
    domain = Folder.objects.get(**demo.demo_domain_filter(demo.DEFAULT_DOMAIN))
    assert str(domain.pk) == response.json()["id"]
    assert DemoManifest.objects.filter(domain=domain).exists()

    again = client.post(LOAD_DEMO)
    assert again.status_code == 409
    assert again.json()["error"] == "demoDataAlreadyLoaded"


@pytest.mark.django_db
def test_load_demo_endpoint_never_seeds_into_a_namesake_domain():
    client = api_client(admin=True)
    theirs = Folder.objects.create(
        name=demo.DEFAULT_DOMAIN,
        content_type=Folder.ContentType.DOMAIN,
        parent_folder=Folder.get_root_folder(),
    )
    response = client.post(LOAD_DEMO)
    assert response.status_code == 409
    assert response.json()["error"] == "demoDomainNameTaken"
    assert not AppliedControl.objects.filter(folder=theirs).exists()


@pytest.mark.django_db
def test_load_demo_endpoint_requires_domain_creation_rights():
    response = api_client(admin=False).post(LOAD_DEMO)
    assert response.status_code == 403
    assert not Folder.objects.filter(name=demo.DEFAULT_DOMAIN).exists()


@pytest.mark.django_db
def test_demo_domain_can_be_deleted_from_the_api():
    client = api_client(admin=True)
    ctx = demo.seed(domain_name=DOMAIN, out=lambda _: None, err=pytest.fail)
    response = client.delete(f"/api/folders/{ctx.domain.pk}/")
    assert response.status_code == 204, response.content
    assert not Folder.objects.filter(pk=ctx.domain.pk).exists()


@pytest.mark.django_db
def test_domain_delete_still_refuses_references_from_other_domains():
    from metrology.models import MetricDefinition, MetricInstance

    client = api_client(admin=True)
    ctx = demo.seed(domain_name=DOMAIN, out=lambda _: None, err=pytest.fail)
    definition = MetricDefinition.objects.create(
        name="Demo metric", ref_id="T-MET", folder=ctx.domain
    )
    customer = Folder.objects.create(
        name="Customer domain",
        content_type=Folder.ContentType.DOMAIN,
        parent_folder=Folder.get_root_folder(),
    )
    MetricInstance.objects.create(
        name="Their instance", metric_definition=definition, folder=customer
    )
    response = client.delete(f"/api/folders/{ctx.domain.pk}/")
    assert response.status_code == 409
    assert AppliedControl.objects.filter(folder=ctx.domain).exists()


def test_builder_feature_flags_exist():
    from global_settings.utils import get_supported_feature_flags

    declared = {f for b in demo.builders() for f in b.feature_flags}
    assert declared <= get_supported_feature_flags(), sorted(
        declared - get_supported_feature_flags()
    )


@pytest.mark.django_db
def test_seed_switches_on_the_modules_it_fills():
    from global_settings.utils import ff_is_enabled

    demo.seed(domain_name=DOMAIN, out=lambda _: None, err=pytest.fail)
    for flag in {f for b in demo.builders() for f in b.feature_flags}:
        assert ff_is_enabled(flag), flag
