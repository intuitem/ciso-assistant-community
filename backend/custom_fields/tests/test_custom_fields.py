import datetime

import pytest
from decimal import Decimal

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.utils import translation
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from custom_fields.filters import CustomFieldFilterBackend, CustomFieldSearchFilter
from custom_fields.models import (
    CustomFieldChoice,
    CustomFieldDefinition,
    CustomFieldValue,
    FieldType,
    coerce_value,
)
from global_settings.models import GlobalSettings
from iam.models import Folder
from pmbok.models import Project


def _enable_custom_fields():
    gs, _ = GlobalSettings.objects.get_or_create(
        name=GlobalSettings.Names.FEATURE_FLAGS, defaults={"value": {}}
    )
    gs.value = {**(gs.value or {}), "custom_fields": True}
    gs.save()


@pytest.fixture
def root(db):
    folder, _ = Folder.objects.get_or_create(
        content_type=Folder.ContentType.ROOT, defaults={"name": "Global"}
    )
    return folder


@pytest.fixture
def domain(root):
    return Folder.objects.create(name="Domain A", parent_folder=root)


@pytest.fixture
def project_ct():
    return ContentType.objects.get_for_model(Project)


def make_def(ct, folder, key, field_type, **kwargs):
    return CustomFieldDefinition.objects.create(
        content_type=ct,
        folder=folder,
        key=key,
        label=key,
        field_type=field_type,
        **kwargs,
    )


# --------------------------------------------------------------------------- #
# coercion
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "field_type,raw,expected",
    [
        (FieldType.NUMBER, "12.5", Decimal("12.5")),
        (FieldType.BOOLEAN, "true", True),
        (FieldType.BOOLEAN, "0", False),
        (FieldType.BOOLEAN, True, True),
        (FieldType.DATE, "2026-01-15", datetime.date(2026, 1, 15)),
        (FieldType.TEXT, 42, "42"),
        (FieldType.TEXT, "", None),
    ],
)
def test_coerce_value(field_type, raw, expected):
    assert coerce_value(field_type, raw) == expected


@pytest.mark.parametrize(
    "field_type,raw",
    [(FieldType.NUMBER, "abc"), (FieldType.BOOLEAN, "maybe"), (FieldType.DATE, "nope")],
)
def test_coerce_value_invalid(field_type, raw):
    with pytest.raises(ValueError):
        coerce_value(field_type, raw)


# --------------------------------------------------------------------------- #
# definitions on multiple host scopes + key collision
# --------------------------------------------------------------------------- #
def test_for_object_resolves_global_and_ancestor_scopes(root, domain, project_ct):
    make_def(project_ct, root, "global_field", FieldType.TEXT)
    make_def(project_ct, domain, "domain_field", FieldType.TEXT)

    in_domain = Project.objects.create(name="P1", folder=domain)
    in_root = Project.objects.create(name="P2", folder=root)

    domain_keys = set(
        CustomFieldDefinition.for_object(in_domain).values_list("key", flat=True)
    )
    root_keys = set(
        CustomFieldDefinition.for_object(in_root).values_list("key", flat=True)
    )

    assert domain_keys == {"global_field", "domain_field"}
    assert root_keys == {"global_field"}  # domain field does not leak up


def test_sibling_domains_isolated(root, project_ct):
    a = Folder.objects.create(name="A", parent_folder=root)
    b = Folder.objects.create(name="B", parent_folder=root)
    make_def(project_ct, a, "only_a", FieldType.TEXT)
    p_b = Project.objects.create(name="P", folder=b)
    assert "only_a" not in set(
        CustomFieldDefinition.for_object(p_b).values_list("key", flat=True)
    )


def test_key_collision_in_overlapping_scope_rejected(root, domain, project_ct):
    make_def(project_ct, root, "shared", FieldType.TEXT)
    with pytest.raises(ValidationError):
        make_def(project_ct, domain, "shared", FieldType.TEXT)


def test_same_key_disjoint_siblings_allowed(root, project_ct):
    a = Folder.objects.create(name="A", parent_folder=root)
    b = Folder.objects.create(name="B", parent_folder=root)
    make_def(project_ct, a, "dup", FieldType.TEXT)
    make_def(project_ct, b, "dup", FieldType.TEXT)  # must not raise


# --------------------------------------------------------------------------- #
# value CRUD via host mixin
# --------------------------------------------------------------------------- #
def test_set_and_read_values_typed(root, project_ct):
    num = make_def(project_ct, root, "cost", FieldType.NUMBER)
    flag = make_def(project_ct, root, "critical", FieldType.BOOLEAN)
    p = Project.objects.create(name="P", folder=root)

    p.set_custom_field(num, "1500.50")
    p.set_custom_field(flag, True)

    assert p.custom_fields == {"cost": Decimal("1500.500000"), "critical": True}


def test_single_value_upsert_no_duplicates(root, project_ct):
    num = make_def(project_ct, root, "cost", FieldType.NUMBER)
    p = Project.objects.create(name="P", folder=root)
    p.set_custom_field(num, 10)
    p.set_custom_field(num, 20)
    assert CustomFieldValue.objects.filter(definition=num, object_id=p.pk).count() == 1
    assert p.custom_fields["cost"] == Decimal("20.000000")


def test_clearing_value(root, project_ct):
    txt = make_def(project_ct, root, "note", FieldType.TEXT)
    p = Project.objects.create(name="P", folder=root)
    p.set_custom_field(txt, "hello")
    p.set_custom_field(txt, None)
    assert "note" not in p.custom_fields


def test_choice_validation(root, project_ct):
    ch = make_def(project_ct, root, "tier", FieldType.CHOICE)
    CustomFieldChoice.objects.create(definition=ch, value="gold", label="Gold")
    p = Project.objects.create(name="P", folder=root)
    p.set_custom_field(ch, "gold")
    assert p.custom_fields["tier"] == "gold"
    with pytest.raises(ValueError):
        p.set_custom_field(ch, "platinum")


def test_label_localized_resolves_per_language(root, project_ct):
    d = make_def(project_ct, root, "crit", FieldType.TEXT)
    d.label = "Criticality"
    d.help_text = "Business criticality"
    d.translations = {"fr": {"label": "Criticité", "help_text": "Criticité métier"}}
    d.save()
    with translation.override("fr"):
        assert d.label_localized == "Criticité"
        assert d.help_text_localized == "Criticité métier"
    with translation.override("en"):
        assert d.label_localized == "Criticality"  # falls back to base
        assert d.help_text_localized == "Business criticality"


def test_deleting_definition_cascades_values(root, project_ct):
    txt = make_def(project_ct, root, "note", FieldType.TEXT)
    p = Project.objects.create(name="P", folder=root)
    p.set_custom_field(txt, "hello")
    assert CustomFieldValue.objects.filter(definition=txt).count() == 1
    txt.delete()  # must not raise ProtectedError
    assert CustomFieldValue.objects.filter(object_id=p.pk).count() == 0


def test_multi_choice_multiple_rows(root, project_ct):
    mc = make_def(project_ct, root, "tags", FieldType.MULTI_CHOICE)
    for v in ("a", "b", "c"):
        CustomFieldChoice.objects.create(definition=mc, value=v, label=v.upper())
    p = Project.objects.create(name="P", folder=root)
    p.set_custom_field(mc, ["a", "b"])
    assert CustomFieldValue.objects.filter(definition=mc, object_id=p.pk).count() == 2
    assert sorted(p.custom_fields["tags"]) == ["a", "b"]


# --------------------------------------------------------------------------- #
# filtering
# --------------------------------------------------------------------------- #
def _filtered(params):
    backend = CustomFieldFilterBackend()
    request = Request(APIRequestFactory().get("/", params))
    return backend.filter_queryset(request, Project.objects.all(), view=None)


def test_filter_two_fields_and_across_rows(root, project_ct):
    crit = make_def(project_ct, root, "crit", FieldType.CHOICE)
    for v in ("high", "low"):
        CustomFieldChoice.objects.create(definition=crit, value=v, label=v)
    owner = make_def(project_ct, root, "owner", FieldType.TEXT)

    p1 = Project.objects.create(name="P1", folder=root)
    p2 = Project.objects.create(name="P2", folder=root)
    p1.set_custom_field(crit, "high")
    p1.set_custom_field(owner, "alice")
    p2.set_custom_field(crit, "high")
    p2.set_custom_field(owner, "bob")

    result = _filtered({"cf__crit": "high", "cf__owner": "alice"})
    assert list(result.values_list("name", flat=True)) == ["P1"]


def test_filter_number_gte(root, project_ct):
    cost = make_def(project_ct, root, "cost", FieldType.NUMBER)
    cheap = Project.objects.create(name="cheap", folder=root)
    pricey = Project.objects.create(name="pricey", folder=root)
    cheap.set_custom_field(cost, 100)
    pricey.set_custom_field(cost, 5000)
    result = _filtered({"cf__cost__gte": "1000"})
    assert list(result.values_list("name", flat=True)) == ["pricey"]


def test_filter_multi_choice_in_matches_any(root, project_ct):
    mc = make_def(project_ct, root, "tags", FieldType.MULTI_CHOICE)
    for v in ("a", "b", "c"):
        CustomFieldChoice.objects.create(definition=mc, value=v, label=v)
    pa = Project.objects.create(name="pa", folder=root)
    pb = Project.objects.create(name="pb", folder=root)
    pc = Project.objects.create(name="pc", folder=root)
    pa.set_custom_field(mc, ["a"])
    pb.set_custom_field(mc, ["b"])
    pc.set_custom_field(mc, ["c"])
    result = _filtered({"cf__tags__in": "a,b"})
    assert set(result.values_list("name", flat=True)) == {"pa", "pb"}


def test_filter_text_icontains(root, project_ct):
    owner = make_def(project_ct, root, "owner", FieldType.TEXT)
    p = Project.objects.create(name="P", folder=root)
    p.set_custom_field(owner, "Alice Cooper")
    assert list(
        _filtered({"cf__owner__icontains": "cooper"}).values_list("name", flat=True)
    ) == ["P"]


def test_filter_bad_input_returns_empty(root, project_ct):
    make_def(project_ct, root, "cost", FieldType.NUMBER)
    Project.objects.create(name="P", folder=root)
    assert _filtered({"cf__cost__gte": "not-a-number"}).count() == 0


# --------------------------------------------------------------------------- #
# search
# --------------------------------------------------------------------------- #
class _SearchView:
    search_fields = ["name"]


def _search(term):
    backend = CustomFieldSearchFilter()
    request = Request(APIRequestFactory().get("/", {"search": term}))
    return set(
        backend.filter_queryset(
            request, Project.objects.all(), _SearchView()
        ).values_list("name", flat=True)
    )


def test_search_includes_searchable_custom_text(root, project_ct):
    _enable_custom_fields()
    notes = make_def(project_ct, root, "notes", FieldType.TEXT, searchable=True)
    secret = make_def(project_ct, root, "secret", FieldType.TEXT, searchable=False)

    hit = Project.objects.create(name="alpha", folder=root)
    miss = Project.objects.create(name="beta", folder=root)
    hit.set_custom_field(notes, "contains needle here")
    miss.set_custom_field(secret, "also has needle but not searchable")

    names = _search("needle")
    assert (
        "alpha" in names and "beta" not in names
    )  # matched via searchable custom value
    # the non-searchable field's value must not surface its object
    assert _search("not searchable") == set()


def test_search_unaffected_without_searchable_fields(root, project_ct):
    # No searchable definitions → custom-field search short-circuits to native search.
    _enable_custom_fields()
    notes = make_def(project_ct, root, "notes", FieldType.TEXT, searchable=False)
    p = Project.objects.create(name="alpha", folder=root)
    p.set_custom_field(notes, "contains needle here")

    assert _search("needle") == set()  # native name search only, custom value ignored
    assert _search("alpha") == {"alpha"}
