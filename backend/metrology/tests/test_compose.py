"""A computed metric started from instances: an ordinary definition and an
instance pinning the picked instances, made in one go; an identical
definition reused; who may make it, and what they may pick."""

import uuid

import pytest
from django.contrib.auth.models import Permission
from rest_framework.test import APIRequestFactory, force_authenticate

from iam.models import Folder, Role, RoleAssignment, User, UserGroup
from metrology.compose import common_domain, least_frequent
from metrology.derived import DerivedMetricError, compute_sample
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


def definition_of(response):
    return MetricInstance.objects.get(id=response.data["id"]).metric_definition_id


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
        assert definition_of(third) == definition_of(first)

    def test_a_different_unit_or_formula_makes_a_new_one(self, acme):
        group, _fr, _de, i = acme
        first = call(
            "post", "compose", payload(group, {"a": i["clicks_fr"]}, "a"), admin()
        )
        other = call(
            "post", "compose", payload(group, {"a": i["clicks_fr"]}, "a * 2"), admin()
        )
        assert definition_of(other) != definition_of(first)
        other = call(
            "post",
            "compose",
            payload(group, {"a": i["clicks_fr"]}, "a", higher_is_better=False),
            admin(),
        )
        assert definition_of(other) != definition_of(first)

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


LEVELS = [{"ref_id": "G", "name": "Good"}, {"ref_id": "P", "name": "Poor"}]


@pytest.mark.django_db
class TestLevels:
    def test_a_level_result_records_the_level(self, acme):
        group, _fr, _de, i = acme
        response = call(
            "post",
            "compose",
            payload(
                group,
                {"clicks": i["clicks_fr"]},
                'clicks > 5.0 ? "Poor" : "Good"',
                category="qualitative",
                choices_definition=LEVELS,
            ),
            admin(),
        )
        assert response.status_code == 201, response.data
        made = MetricInstance.objects.get(id=response.data["id"])
        definition = made.metric_definition
        assert definition.category == "qualitative"
        assert definition.choices_definition == LEVELS
        assert definition.unit is None
        compute_sample(made)
        # France clicks: 10, so "Poor", the second level.
        assert stored(made) == {"2026-05-01": 2}

    def test_a_text_the_levels_do_not_know_is_refused(self, acme):
        group, _fr, _de, i = acme
        response = call(
            "post",
            "compose",
            payload(
                group,
                {"clicks": i["clicks_fr"]},
                "clicks > 5.0 ? 'Bad' : 'G'",
                category="qualitative",
                choices_definition=LEVELS,
            ),
            admin(),
        )
        assert response.status_code == 400
        # A level answers to its reference too: 'G' is Good.
        assert response.data["expression"] == ["'Bad' is not one of the levels"]

    @pytest.mark.parametrize(
        "levels, message",
        [
            ([{"ref_id": "G", "name": "Good"}], "at least two levels"),
            (
                [{"ref_id": "G", "name": "Good"}, {"ref_id": "", "name": "Poor"}],
                "a reference and a name",
            ),
            (
                [{"ref_id": "G", "name": "Good"}, {"ref_id": "g", "name": "Poor"}],
                "names two levels",
            ),
        ],
    )
    def test_levels_are_named_once(self, acme, levels, message):
        group, _fr, _de, i = acme
        response = call(
            "post",
            "compose",
            payload(
                group,
                {"clicks": i["clicks_fr"]},
                "1",
                category="qualitative",
                choices_definition=levels,
            ),
            admin(),
        )
        assert response.status_code == 400
        assert message in " ".join(response.data["choices_definition"])

    def test_reuse_needs_the_same_levels(self, acme):
        group, _fr, _de, i = acme
        body = {
            "category": "qualitative",
            "choices_definition": LEVELS,
        }
        expression = 'clicks > 5.0 ? "Poor" : "Good"'
        first = call(
            "post",
            "compose",
            payload(group, {"clicks": i["clicks_fr"]}, expression, **body),
            admin(),
        )
        same = call(
            "post",
            "compose",
            payload(group, {"clicks": i["clicks_fr"]}, expression, **body),
            admin(),
        )
        assert definition_of(same) == definition_of(first)
        reordered = call(
            "post",
            "compose",
            payload(
                group,
                {"clicks": i["clicks_fr"]},
                expression,
                category="qualitative",
                choices_definition=list(reversed(LEVELS)),
            ),
            admin(),
        )
        assert definition_of(reordered) != definition_of(first)
        numeric = call(
            "post",
            "compose",
            payload(group, {"clicks": i["clicks_fr"]}, "clicks"),
            admin(),
        )
        assert (
            MetricInstance.objects.get(id=numeric.data["id"]).metric_definition.category
            == "quantitative"
        )


@pytest.mark.django_db
class TestEdit:
    """What an edit changes: the instance alone, its definition in place, or
    this metric moved to a definition of its own."""

    def made(self, acme, user=None, **extra):
        group, _fr, _de, i = acme
        response = call(
            "post",
            "compose",
            payload(
                group,
                {"clicks": i["clicks_fr"], "heads": i["heads_fr"]},
                "clicks * 100.0 / heads",
                **extra,
            ),
            user or admin(),
        )
        assert response.status_code == 201, response.data
        return MetricInstance.objects.get(id=response.data["id"])

    def edit(self, instance, user=None, **changes):
        state = call("get", "composition", {}, admin(), pk=str(instance.id)).data
        body = {
            "name": state["name"],
            "folder": state["folder"]["id"],
            "collection_frequency": state["collection_frequency"],
            "expression": state["expression"],
            "inputs": [
                {"key": item["key"], "instance": item["instance"]["id"]}
                for item in state["inputs"]
            ],
            **changes,
        }
        return call("put", "composition", body, user or admin(), pk=str(instance.id))

    def test_reads_back_what_the_modal_shows(self, acme):
        made = self.made(acme)
        response = call("get", "composition", {}, admin(), pk=str(made.id))
        assert response.status_code == 200, response.data
        assert response.data["composable"] is True
        assert response.data["definition"]["shared_with"] == 0
        assert [(x["key"], x["instance"]["name"]) for x in response.data["inputs"]] == [
            ("clicks", "Clicks France"),
            ("heads", "Headcount France"),
        ]

    def test_a_formula_over_combined_inputs_is_edited_on_its_definition(self, acme):
        group, _fr, _de, i = acme
        clicks = i["clicks_fr"].metric_definition
        summed = make_definition(
            "Summed",
            inputs=[{"key": "c", "definition": str(clicks.id), "combine": "sum"}],
            expression="c",
        )
        instance = make_instance(group, summed)
        response = call("get", "composition", {}, admin(), pk=str(instance.id))
        assert response.data["composable"] is False
        assert response.data["definition"]["id"] == str(summed.id)
        assert self.edit_raw(instance).status_code == 400

    def edit_raw(self, instance):
        return call("put", "composition", {}, admin(), pk=str(instance.id))

    def test_instance_only_changes_keep_the_definition(self, acme):
        _group, _fr, _de, i = acme
        made = self.made(acme)
        definition_id = made.metric_definition_id
        # Germany's clicks: another instance of the same metric.
        response = self.edit(
            made,
            name="Rate renamed",
            inputs=[
                {"key": "clicks", "instance": str(i["clicks_de"].id)},
                {"key": "heads", "instance": str(i["heads_fr"].id)},
            ],
        )
        assert response.status_code == 200, response.data
        assert response.data["outcome"] == "unchanged"
        made.refresh_from_db()
        assert made.name == "Rate renamed"
        assert made.metric_definition_id == definition_id
        assert made.input_choices["clicks"] == {"pick": str(i["clicks_de"].id)}
        compute_sample(made, full=True)
        assert stored(made) == {"2026-05-01": 30.0}

    def test_an_unshared_definition_is_edited_in_place(self, acme):
        made = self.made(acme)
        definition_id = made.metric_definition_id
        response = self.edit(made, expression="clicks * 1000.0 / heads")
        assert response.data["outcome"] == "updated"
        made.refresh_from_db()
        assert made.metric_definition_id == definition_id
        assert made.metric_definition.expression == "clicks * 1000.0 / heads"

    def test_a_shared_definition_always_forks(self, acme):
        first = self.made(acme, name="First")
        second = self.made(acme, name="Second")
        assert first.metric_definition_id == second.metric_definition_id
        shared = first.metric_definition_id
        state = call("get", "composition", {}, admin(), pk=str(first.id)).data
        assert state["definition"]["shared_with"] == 1

        response = self.edit(first, expression="clicks * 1000.0 / heads")
        assert response.data["outcome"] == "forked"
        first.refresh_from_db()
        second.refresh_from_db()
        assert first.metric_definition_id != shared
        assert second.metric_definition.expression == "clicks * 100.0 / heads"
        # What an edit form left open must adopt, or its save undoes the fork.
        assert response.data["metric_definition"] == str(first.metric_definition_id)
        assert response.data["input_choices"] == first.input_choices

        # Asking for every metric using it changes nothing: a shared
        # definition is never edited from one of its metrics.
        third = self.made(acme, name="Third")
        assert third.metric_definition_id == shared
        response = self.edit(
            third, expression="clicks * 10.0 / heads", definition_scope="all"
        )
        assert response.data["outcome"] == "forked"
        second.refresh_from_db()
        assert second.metric_definition.expression == "clicks * 100.0 / heads"

    def test_without_the_right_to_change_the_definition_it_forks(self, acme):
        group, _fr, _de, _i = acme
        first = self.made(acme, name="First")
        self.made(acme, name="Second")
        user = member(
            group, codenames=[c for c in WRITE if c != "change_metricdefinition"]
        )
        response = self.edit(
            first, user=user, expression="clicks / heads", definition_scope="all"
        )
        assert response.status_code == 200, response.data
        assert response.data["outcome"] == "forked"

    def test_a_metric_cannot_read_itself(self, acme):
        made = self.made(acme)
        response = self.edit(
            made,
            inputs=[{"key": "clicks", "instance": str(made.id)}],
            expression="clicks",
        )
        assert response.status_code == 400
        assert "cannot read itself" in response.data["inputs"][0]

    def test_needs_the_right_to_change_the_metric(self, acme):
        group, _fr, _de, _i = acme
        made = self.made(acme)
        reader = member(
            group, codenames=["view_metricinstance", "view_metricdefinition"]
        )
        assert self.edit(made, user=reader).status_code == 403


@pytest.mark.django_db
class TestHardening:
    """What trying to break the modal and its endpoints turned up."""

    DEEP = "(" * 80 + "a" + ")" * 80
    LONG_CHAIN = "a" + " + a" * 349

    def test_a_formula_nested_too_deep_is_refused_on_save(self, acme):
        group, _fr, _de, i = acme
        for expression in (self.DEEP, self.LONG_CHAIN):
            response = call(
                "post",
                "compose",
                payload(group, {"a": i["clicks_fr"]}, expression),
                admin(),
            )
            assert response.status_code == 400, expression[:20]
            assert "nested too deeply" in response.data["expression"][0]

    def test_a_formula_nested_too_deep_is_recorded_when_computed(self, acme):
        """Saved before the guard (or by any other path): computing records
        the error on the instance instead of crashing the sweep."""
        group, _fr, _de, i = acme
        clicks = i["clicks_fr"].metric_definition
        definition = make_definition(
            "Deep",
            inputs=[{"key": "a", "definition": str(clicks.id), "combine": "one"}],
            expression=self.DEEP,
        )
        instance = make_instance(
            group, definition, input_choices={"a": {"pick": str(i["clicks_fr"].id)}}
        )
        with pytest.raises(DerivedMetricError):
            compute_sample(instance, full=True)
        instance.refresh_from_db()
        assert "nested too deeply" in instance.last_computation_error

    def test_a_formula_over_the_length_cap_is_refused(self, acme):
        group, _fr, _de, i = acme
        expression = 'a + size("' + "x" * 3000 + '")'
        response = call(
            "post",
            "compose",
            payload(group, {"a": i["clicks_fr"]}, expression),
            admin(),
        )
        assert response.status_code == 400
        assert response.data["expression"] == ["The expression is too long"]

    @pytest.mark.parametrize("target", ["inf", "-inf", "Infinity", "1e999", "NaN"])
    def test_a_target_that_is_not_a_finite_number_is_refused(self, acme, target):
        group, _fr, _de, i = acme
        response = call(
            "post",
            "compose",
            payload(group, {"a": i["clicks_fr"]}, "a", target_value=target),
            admin(),
        )
        assert response.status_code == 400
        assert "target_value" in response.data

    @pytest.mark.parametrize("key", ["a\n", "k" * 65])
    def test_input_names_are_whole_short_identifiers(self, acme, key):
        group, _fr, _de, i = acme
        response = call(
            "post", "compose", payload(group, {key: i["clicks_fr"]}, "1.0"), admin()
        )
        assert response.status_code == 400
        assert "not a valid input name" in response.data["inputs"][0]

    def test_a_level_text_is_short(self, acme):
        group, _fr, _de, i = acme
        response = call(
            "post",
            "compose",
            payload(
                group,
                {"a": i["clicks_fr"]},
                '"Good"',
                category="qualitative",
                choices_definition=[
                    {"ref_id": "G", "name": "Good"},
                    {"ref_id": "P" * 101, "name": "Poor"},
                ],
            ),
            admin(),
        )
        assert response.status_code == 400
        assert "at most 100" in response.data["choices_definition"][0]

    def test_a_name_at_the_limit_survives_a_definition_name_clash(self, acme):
        group, _fr, _de, i = acme
        name = "N" * 200
        MetricDefinition.objects.create(name=name, folder=group)
        response = call(
            "post",
            "compose",
            payload(group, {"a": i["clicks_fr"]}, "a", name=name),
            admin(),
        )
        assert response.status_code == 201, response.data
        made = MetricInstance.objects.get(id=response.data["id"])
        assert len(made.metric_definition.name) <= 200

    def test_the_result_type_of_a_metric_other_formulas_read_cannot_change(self, acme):
        group, _fr, _de, i = acme
        edit = TestEdit()
        read = edit.made(acme, name="Read")
        reader = call(
            "post",
            "compose",
            payload(group, {"r": read}, "r * 2.0", name="Reader"),
            admin(),
        )
        assert reader.status_code == 201, reader.data
        response = edit.edit(
            read,
            expression='clicks > 5.0 ? "High" : "Low"',
            category="qualitative",
            choices_definition=[
                {"ref_id": "low", "name": "Low"},
                {"ref_id": "high", "name": "High"},
            ],
        )
        assert response.status_code == 400
        assert "result type cannot change" in response.data["category"][0]
        read.refresh_from_db()
        assert read.metric_definition.category == "quantitative"

    def test_reordering_levels_recomputes_the_history(
        self, acme, django_capture_on_commit_callbacks
    ):
        """A stored level is a position in the list: reordering the list
        changes what every stored sample means."""
        group, _fr, _de, i = acme
        levels = [{"ref_id": "G", "name": "Good"}, {"ref_id": "P", "name": "Poor"}]
        response = call(
            "post",
            "compose",
            payload(
                group,
                {"clicks": i["clicks_fr"]},
                'clicks > 5.0 ? "Poor" : "Good"',
                category="qualitative",
                choices_definition=levels,
            ),
            admin(),
        )
        made = MetricInstance.objects.get(id=response.data["id"])
        compute_sample(made, full=True)
        MetricInstance.objects.filter(id=made.id).update(recompute_from=None)
        definition = made.metric_definition
        with django_capture_on_commit_callbacks(execute=True):
            definition.choices_definition = list(reversed(levels))
            definition.save()
        made.refresh_from_db()
        assert made.recompute_from is not None

    def test_a_metric_other_formulas_pick_cannot_move_to_its_own_definition(self, acme):
        group, _fr, _de, i = acme
        edit = TestEdit()
        first = edit.made(acme, name="First")
        edit.made(acme, name="Second")  # shares First's definition
        reader = call(
            "post",
            "compose",
            payload(group, {"f": first}, "f * 2.0", name="Reader"),
            admin(),
        )
        assert reader.status_code == 201, reader.data
        response = edit.edit(first, expression="clicks * 1000.0 / heads")
        assert response.status_code == 400
        assert "Reader" in response.data["form"][0]
        first.refresh_from_db()
        assert first.metric_definition.expression == "clicks * 100.0 / heads"


@pytest.mark.django_db
class TestPreviewHardening:
    def post(self, body, user):
        view = MetricDefinitionViewSet.as_view({"post": "preview_formula"})
        request = APIRequestFactory().post("/x/", body, format="json")
        force_authenticate(request, user=user)
        return view(request)

    def test_names_only_what_the_author_may_read(self, acme):
        group, _fr, _de, i = acme
        clicks = str(i["clicks_fr"].metric_definition_id)
        response = self.post(
            {
                "folder": str(group.id),
                "frequency": "monthly",
                "inputs": [{"key": "a", "definition": clicks, "combine": "sum"}],
                "expression": "a",
            },
            member(group, recursive=False),
        )
        assert response.data["ok"] is True, response.data
        # The value is the domain's, as the metric would compute it; which
        # instances it read stays hidden.
        assert response.data["value"] == 40
        assert response.data["inputs"] == {"a": []}
        assert response.data["hidden_inputs"] == {"a": 2}

    @pytest.mark.parametrize("levels", [[1, 2], "abc", {"x": 1}])
    def test_malformed_levels_do_not_crash(self, acme, levels):
        group, _fr, _de, i = acme
        clicks = str(i["clicks_fr"].metric_definition_id)
        response = self.post(
            {
                "folder": str(group.id),
                "inputs": [{"key": "a", "definition": clicks, "combine": "sum"}],
                "expression": '"low"',
                "category": "qualitative",
                "choices_definition": levels,
            },
            admin(),
        )
        assert response.status_code == 200
        assert response.data["ok"] is False

    def test_a_malformed_exclusion_does_not_crash(self, acme):
        group, _fr, _de, i = acme
        clicks = str(i["clicks_fr"].metric_definition_id)
        response = self.post(
            {
                "folder": str(group.id),
                "inputs": [{"key": "a", "definition": clicks, "combine": "sum"}],
                "input_choices": {"a": {"exclude": 5}},
                "expression": "a",
            },
            admin(),
        )
        assert response.status_code == 200
        assert response.data["value"] == 40
