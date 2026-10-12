"""A computed metric started from instances: an ordinary definition and an
instance pinning the picked instances, made in one go; an identical
definition reused; who may make it, and what they may pick."""

import uuid

import pytest
from django.contrib.auth.models import Permission
from rest_framework.test import APIRequestFactory, force_authenticate

from iam.models import Folder, Role, RoleAssignment, User, UserGroup
from metrology.compose import common_domain, least_frequent
from metrology.derived import compute_sample
from metrology.models import MetricDefinition, MetricInstance
from metrology.serializers import MetricInstanceWriteSerializer
from metrology.views import MetricDefinitionViewSet, MetricInstanceViewSet

from .test_metric_formulas import (
    at,
    frozen,  # noqa: F401 (fixture)
    make_definition,
    make_domain,
    make_instance,
    sample,
    stored,
)

WRITE = [
    "view_metricinstance",
    "add_metricinstance",
    "change_metricinstance",
    "view_metricdefinition",
    "add_metricdefinition",
    "change_metricdefinition",
]


def admin():
    return User.objects.create_superuser(
        email=f"admin-{uuid.uuid4().hex[:6]}@tests.local"
    )


def member(folder, codenames=WRITE, recursive=True):
    user = User.objects.create_user(email=f"user-{uuid.uuid4().hex[:6]}@tests.local")
    group = UserGroup.objects.create(name=f"g {uuid.uuid4().hex[:4]}", folder=folder)
    group.user_set.add(user)
    role = Role.objects.create(
        name=f"r {uuid.uuid4().hex[:4]}", folder=Folder.get_root_folder()
    )
    role.permissions.add(*Permission.objects.filter(codename__in=codenames))
    assignment = RoleAssignment.objects.create(
        user_group=group,
        role=role,
        folder=Folder.get_root_folder(),
        is_recursive=recursive,
    )
    assignment.perimeter_folders.add(folder)
    return user


def call(method, action, data, user, path="/x/", **kwargs):
    view = MetricInstanceViewSet.as_view({method: action})
    factory = APIRequestFactory()
    if method == "get":
        request = factory.get(path, data)
    else:
        request = getattr(factory, method)(path, data, format="json")
    force_authenticate(request, user=user)
    return view(request, **kwargs)


@pytest.fixture
def acme(frozen):  # noqa: F811
    """Clicks and headcount in France and Germany, under ACME."""
    group = make_domain("ACME")
    fr, de = make_domain("France", group), make_domain("Germany", group)
    clicks, headcount = make_definition("Clicks"), make_definition("Headcount")
    instances = {
        "clicks_fr": make_instance(fr, clicks, name="Clicks France"),
        "clicks_de": make_instance(de, clicks, name="Clicks Germany"),
        "heads_fr": make_instance(fr, headcount, name="Headcount France"),
        "heads_de": make_instance(de, headcount, name="Headcount Germany"),
    }
    for key, value in [
        ("clicks_fr", 10),
        ("clicks_de", 30),
        ("heads_fr", 100),
        ("heads_de", 200),
    ]:
        sample(instances[key], value, at(2026, 5, 3))
    return group, fr, de, instances


def payload(folder, instances, expression, **extra):
    return {
        "name": extra.pop("name", f"Rate {uuid.uuid4().hex[:6]}"),
        "folder": str(folder.id),
        "inputs": [
            {"key": key, "instance": str(instance.id)}
            for key, instance in instances.items()
        ],
        "expression": expression,
        **extra,
    }


class TestHelpers:
    def test_frequency_is_the_least_frequent_input(self):
        assert least_frequent(["monthly", "quarterly", "daily"]) == "quarterly"
        assert least_frequent([None]) == "monthly"

    @pytest.mark.django_db
    def test_the_domain_is_the_lowest_holding_every_pick(self):
        group = make_domain("ACME")
        fr, de = make_domain("France", group), make_domain("Germany", group)
        paris = make_domain("Paris", fr)
        assert common_domain([paris, de]) == group
        assert common_domain([paris, fr]) == fr
        assert common_domain([paris]) == paris
        assert common_domain([group, make_domain("Other")]) == Folder.get_root_folder()


@pytest.mark.django_db
class TestCompose:
    def test_makes_an_ordinary_definition_and_a_pinned_instance(self, acme):
        group, _fr, _de, i = acme
        response = call(
            "post",
            "compose",
            payload(
                group,
                {"clicks_fr": i["clicks_fr"], "clicks_de": i["clicks_de"]},
                "clicks_fr + clicks_de",
            ),
            admin(),
        )
        assert response.status_code == 201, response.data
        assert response.data["definition"]["reused"] is False
        made = MetricInstance.objects.get(id=response.data["id"])
        definition = made.metric_definition
        assert definition.folder == group
        assert definition.expression == "clicks_fr + clicks_de"
        # Both inputs read the same metric; the picks tell them apart.
        assert [s["definition"] for s in definition.inputs] == [
            str(i["clicks_fr"].metric_definition_id)
        ] * 2
        assert made.input_choices == {
            "clicks_fr": {"pick": str(i["clicks_fr"].id)},
            "clicks_de": {"pick": str(i["clicks_de"].id)},
        }
        assert made.status == MetricInstance.Status.ACTIVE
        assert made.collection_frequency == "monthly"
        compute_sample(made)
        assert stored(made) == {"2026-05-01": 40}

    def test_picks_read_one_instance_each_across_metrics(self, acme):
        group, _fr, _de, i = acme
        response = call(
            "post",
            "compose",
            payload(
                group,
                {"clicks": i["clicks_de"], "heads": i["heads_de"]},
                "clicks * 100.0 / heads",
            ),
            admin(),
        )
        made = MetricInstance.objects.get(id=response.data["id"])
        compute_sample(made)
        assert stored(made) == {"2026-05-01": 15.0}

    def test_a_pick_outside_the_domain_is_refused(self, acme):
        _group, fr, _de, i = acme
        response = call(
            "post",
            "compose",
            payload(fr, {"a": i["clicks_fr"], "b": i["clicks_de"]}, "a + b"),
            admin(),
        )
        assert response.status_code == 400
        assert "outside" in response.data["inputs"][0]
        assert not MetricDefinition.objects.filter(expression="a + b").exists()

    def test_formula_and_name_problems_come_back_by_field(self, acme):
        group, _fr, _de, i = acme
        response = call(
            "post",
            "compose",
            payload(group, {"previous": i["clicks_fr"]}, "a +", name=""),
            admin(),
        )
        assert response.status_code == 400
        assert set(response.data) == {"name", "inputs", "expression"}

    def test_a_deprecated_instance_cannot_be_picked(self, acme):
        group, _fr, _de, i = acme
        i["clicks_fr"].status = MetricInstance.Status.DEPRECATED
        i["clicks_fr"].save()
        response = call(
            "post", "compose", payload(group, {"a": i["clicks_fr"]}, "a"), admin()
        )
        assert response.status_code == 400
        assert "deprecated" in response.data["inputs"][0]

    def test_needs_the_right_to_add_in_the_domain(self, acme):
        group, fr, _de, i = acme
        response = call(
            "post",
            "compose",
            payload(group, {"a": i["clicks_fr"]}, "a"),
            member(fr),
        )
        assert response.status_code == 403
        response = call(
            "post", "compose", payload(fr, {"a": i["clicks_fr"]}, "a"), member(fr)
        )
        assert response.status_code == 201, response.data

    def test_an_instance_the_user_cannot_read_looks_missing(self, acme):
        """Rights on ACME alone, not below: France's clicks are in the tree
        but not the user's to read, so a formula must not show them."""
        group, _fr, _de, i = acme
        user = member(group, recursive=False)
        response = call(
            "post", "compose", payload(group, {"a": i["clicks_fr"]}, "a"), user
        )
        assert response.status_code == 400
        assert response.data["inputs"] == ["'a': no such metric instance"]

    def test_a_definition_name_clash_is_not_the_authors(self, acme):
        group, _fr, _de, i = acme
        MetricDefinition.objects.create(name="Phishing rate", folder=group)
        response = call(
            "post",
            "compose",
            payload(group, {"a": i["clicks_fr"]}, "a", name="Phishing rate"),
            admin(),
        )
        assert response.status_code == 201, response.data
        made = MetricInstance.objects.get(id=response.data["id"])
        assert made.name == "Phishing rate"
        assert made.metric_definition.name == "Phishing rate (2)"

    def test_an_instance_name_clash_is(self, acme):
        group, _fr, _de, i = acme
        body = payload(group, {"a": i["clicks_fr"]}, "a", name="Rate")
        assert call("post", "compose", body, admin()).status_code == 201
        response = call("post", "compose", body, admin())
        assert response.status_code == 400
        assert "name" in response.data
        assert (
            MetricDefinition.objects.filter(folder=group, expression="a").count() == 1
        )


@pytest.mark.django_db
class TestReuse:
    def test_the_same_formula_elsewhere_reuses_the_definition(self, acme):
        _group, fr, de, i = acme
        first = call(
            "post",
            "compose",
            payload(
                fr, {"clicks": i["clicks_fr"], "heads": i["heads_fr"]}, "clicks / heads"
            ),
            admin(),
        )
        # Germany sits beside France: the definition, in France, is not
        # visible from there, so Germany gets its own.
        second = call(
            "post",
            "compose",
            payload(
                de, {"clicks": i["clicks_de"], "heads": i["heads_de"]}, "clicks / heads"
            ),
            admin(),
        )
        assert second.data["definition"]["reused"] is False
        paris = make_domain("Paris", fr)
        third = call(
            "post",
            "compose",
            payload(
                paris,
                {"clicks": i["clicks_fr"], "heads": i["heads_fr"]},
                "clicks / heads",
            ),
            admin(),
        )
        assert third.status_code == 400  # France's picks are outside Paris
        third = call(
            "post",
            "compose",
            payload(
                fr,
                {"clicks": i["clicks_fr"], "heads": i["heads_fr"]},
                "clicks / heads",
                name="Rate again",
            ),
            admin(),
        )
        assert third.data["definition"] == {**first.data["definition"], "reused": True}

    def test_a_different_unit_or_formula_makes_a_new_one(self, acme):
        group, _fr, _de, i = acme
        first = call(
            "post", "compose", payload(group, {"a": i["clicks_fr"]}, "a"), admin()
        )
        other = call(
            "post", "compose", payload(group, {"a": i["clicks_fr"]}, "a * 2"), admin()
        )
        assert other.data["definition"]["id"] != first.data["definition"]["id"]
        other = call(
            "post",
            "compose",
            payload(group, {"a": i["clicks_fr"]}, "a", higher_is_better=False),
            admin(),
        )
        assert other.data["definition"]["id"] != first.data["definition"]["id"]

    def test_the_definition_outlives_its_first_instance(self, acme):
        group, _fr, _de, i = acme
        response = call(
            "post", "compose", payload(group, {"a": i["clicks_fr"]}, "a"), admin()
        )
        made = MetricInstance.objects.get(id=response.data["id"])
        definition_id = made.metric_definition_id
        made.delete()
        assert MetricDefinition.objects.filter(id=definition_id).exists()


@pytest.mark.django_db
class TestCandidates:
    def test_quantitative_live_and_readable_only(self, acme):
        group, fr, _de, i = acme
        levels = make_definition("Maturity", category="qualitative")
        make_instance(fr, levels, name="Maturity France")
        i["heads_fr"].status = MetricInstance.Status.DEPRECATED
        i["heads_fr"].save()
        response = call("get", "compose_candidates", {}, member(fr))
        assert [x["name"] for x in response.data] == ["Clicks France"]
        response = call("get", "compose_candidates", {"search": "germ"}, admin())
        assert [x["name"] for x in response.data] == [
            "Clicks Germany",
            "Headcount Germany",
        ]
        response = call(
            "get",
            "compose_candidates",
            {"instance": [str(i["clicks_de"].id), str(i["heads_fr"].id)]},
            admin(),
        )
        assert [x["name"] for x in response.data] == ["Clicks Germany"]
        response = call(
            "get", "compose_candidates", {"search": "headcount germ"}, admin()
        )
        assert [x["name"] for x in response.data] == ["Headcount Germany"]
        response = call("get", "compose_candidates", {"search": "headc"}, admin())
        assert response.data[0]["definition"]["id"] == str(
            i["heads_de"].metric_definition_id
        )


@pytest.mark.django_db
class TestContext:
    def test_domains_from_the_lowest_up_and_the_frequency(self, acme):
        group, _fr, _de, i = acme
        i["heads_de"].collection_frequency = "quarterly"
        i["heads_de"].save()
        response = call(
            "get",
            "compose_context",
            {"instance": [str(i["clicks_fr"].id), str(i["heads_de"].id)]},
            admin(),
        )
        assert response.status_code == 200
        assert [d["id"] for d in response.data["domains"]] == [
            str(group.id),
            str(Folder.get_root_folder().id),
        ]
        assert response.data["frequency"] == "quarterly"

    def test_only_domains_the_user_may_create_in(self, acme):
        _group, fr, _de, i = acme
        paris = make_domain("Paris", fr)
        pick = make_instance(
            paris, i["clicks_fr"].metric_definition, name="Clicks Paris"
        )
        response = call(
            "get", "compose_context", {"instance": [str(pick.id)]}, member(fr)
        )
        assert [d["id"] for d in response.data["domains"]] == [
            str(paris.id),
            str(fr.id),
        ]

    def test_leaves_out_what_the_user_cannot_read(self, acme):
        _group, fr, _de, i = acme
        response = call(
            "get",
            "compose_context",
            {"instance": [str(i["clicks_fr"].id), str(i["clicks_de"].id)]},
            member(fr),
        )
        assert [d["id"] for d in response.data["domains"]] == [str(fr.id)]


@pytest.mark.django_db
class TestPicksMustBeReadable:
    def test_the_preview_reads_the_picks(self, acme):
        group, _fr, _de, i = acme
        view = MetricDefinitionViewSet.as_view({"post": "preview_formula"})
        clicks = str(i["clicks_fr"].metric_definition_id)
        body = {
            "folder": str(group.id),
            "frequency": "monthly",
            "inputs": [{"key": "a", "definition": clicks, "combine": "one"}],
            "input_choices": {"a": {"pick": str(i["clicks_de"].id)}},
            "expression": "a",
        }
        request = APIRequestFactory().post("/x/", body, format="json")
        force_authenticate(request, user=admin())
        response = view(request)
        assert response.data["ok"] is True, response.data
        assert response.data["value"] == 30

        request = APIRequestFactory().post("/x/", body, format="json")
        force_authenticate(request, user=member(group, recursive=False))
        response = view(request)
        assert response.data["ok"] is False
        assert response.data["errors"][0]["code"] == "derived_input_invalid"

    def test_the_instance_form_refuses_an_unreadable_pick(self, acme):
        group, _fr, _de, i = acme
        clicks = i["clicks_fr"].metric_definition
        reader = make_definition(
            "Reader",
            inputs=[{"key": "a", "definition": str(clicks.id), "combine": "one"}],
            expression="a",
        )
        request = APIRequestFactory().post("/x/")
        request.user = member(group, recursive=False)
        serializer = MetricInstanceWriteSerializer(
            data={
                "name": "R",
                "folder": str(group.id),
                "metric_definition": str(reader.id),
                "input_choices": {"a": {"pick": str(i["clicks_fr"].id)}},
            },
            context={"request": request},
        )
        assert not serializer.is_valid()
        assert "input_choices" in serializer.errors
