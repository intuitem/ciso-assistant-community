"""A metric made in one step: its definition created with it, named after
it; the similar-name hint; merging two definitions of the same thing;
values answering for a period; direction and decimals."""

import uuid

import pytest
from rest_framework.test import APIRequestFactory, force_authenticate

from core.models import Terminology
from iam.models import Folder
from metrology.models import CustomMetricSample, MetricDefinition, MetricInstance
from metrology.views import (
    CustomMetricSampleViewSet,
    MetricDefinitionViewSet,
    MetricInstanceViewSet,
)

from .test_compose import WRITE, admin, member
from .test_metric_formulas import (
    at,
    frozen,  # noqa: F401 (fixture)
    make_definition,
    make_domain,
    make_instance,
    sample,
)

pytestmark = pytest.mark.django_db


def call(viewset, method, action, data, user, path="/x/", **kwargs):
    view = viewset.as_view({method: action})
    factory = APIRequestFactory()
    if method == "get":
        request = factory.get(path, data)
    else:
        request = getattr(factory, method)(path, data, format="json")
    force_authenticate(request, user=user)
    return view(request, **kwargs)


def unit(name="count"):
    return Terminology.objects.get_or_create(
        name=name,
        field_path=Terminology.FieldPath.METRIC_UNIT,
        defaults={"folder": Folder.get_root_folder(), "is_visible": True},
    )[0]


def one_step(folder, name="Number of assets", **extra):
    definition = extra.pop("definition", {})
    return {
        "name": name,
        "folder": str(folder.id),
        "collection_frequency": "monthly",
        "status": "active",
        "definition": {
            "category": "quantitative",
            "unit": str(unit().id),
            "higher_is_better": None,
            "decimals": 0,
            **definition,
        },
        **extra,
    }


class TestOneStepCreation:
    def test_the_definition_is_created_in_the_domain_named_after_the_metric(self):
        spain = make_domain("Spain")
        response = call(
            MetricInstanceViewSet, "post", "create", one_step(spain), admin()
        )
        assert response.status_code == 201, response.data
        instance = MetricInstance.objects.get(id=response.data["id"])
        definition = instance.metric_definition
        assert definition.name == "Number of assets"
        assert definition.folder == spain
        assert definition.higher_is_better is None
        assert definition.decimals == 0
        assert definition.unit.name == "count"
        assert instance.collection_frequency == "monthly"

    def test_a_taken_name_is_suffixed_as_compose_does(self):
        spain = make_domain("Spain")
        MetricDefinition.objects.create(name="Number of assets", folder=spain)
        response = call(
            MetricInstanceViewSet, "post", "create", one_step(spain), admin()
        )
        assert response.status_code == 201, response.data
        definition = MetricInstance.objects.get(
            id=response.data["id"]
        ).metric_definition
        assert definition.name == "Number of assets (2)"

    def test_both_a_picked_and_an_inline_definition_is_refused(self):
        spain = make_domain("Spain")
        data = one_step(spain, metric_definition=str(make_definition().id))
        response = call(MetricInstanceViewSet, "post", "create", data, admin())
        assert response.status_code == 400
        assert "definition" in response.data

    def test_neither_is_refused(self):
        spain = make_domain("Spain")
        data = one_step(spain)
        data.pop("definition")
        response = call(MetricInstanceViewSet, "post", "create", data, admin())
        assert response.status_code == 400
        assert "metric_definition" in response.data

    def test_an_invalid_definition_reports_its_errors_under_definition(self):
        spain = make_domain("Spain")
        data = one_step(spain, definition={"category": "nonsense"})
        response = call(MetricInstanceViewSet, "post", "create", data, admin())
        assert response.status_code == 400
        assert "category" in response.data["definition"]
        assert not MetricDefinition.objects.filter(name="Number of assets").exists()

    def test_creating_the_definition_takes_the_right_to_add_definitions(self):
        spain = make_domain("Spain")
        user = member(spain, ["view_metricinstance", "add_metricinstance"])
        response = call(MetricInstanceViewSet, "post", "create", one_step(spain), user)
        assert response.status_code == 403
        assert not MetricInstance.objects.filter(folder=spain).exists()

    def test_a_member_with_both_rights_creates_in_one_step(self):
        spain = make_domain("Spain")
        response = call(
            MetricInstanceViewSet,
            "post",
            "create",
            one_step(spain),
            member(spain, WRITE),
        )
        assert response.status_code == 201, response.data

    def test_a_metric_from_a_definition_starts_with_its_defaults(self):
        spain = make_domain("Spain")
        definition = make_definition(
            "Training coverage",
            default_target=90,
            default_collection_frequency="quarterly",
        )
        data = {
            "name": "Training coverage · Spain",
            "folder": str(spain.id),
            "metric_definition": str(definition.id),
        }
        response = call(MetricInstanceViewSet, "post", "create", data, admin())
        assert response.status_code == 201, response.data
        instance = MetricInstance.objects.get(id=response.data["id"])
        assert instance.collection_frequency == "quarterly"
        assert instance.target_value == 90

    def test_a_picked_definition_with_a_null_inline_one_is_fine(self):
        spain = make_domain("Spain")
        data = one_step(spain, metric_definition=str(make_definition().id))
        data["definition"] = None
        response = call(MetricInstanceViewSet, "post", "create", data, admin())
        assert response.status_code == 201, response.data

    def test_editing_ignores_an_inline_definition(self):
        spain = make_domain("Spain")
        instance = make_instance(spain, make_definition())
        data = {
            "name": "Renamed",
            "folder": str(spain.id),
            "metric_definition": str(instance.metric_definition_id),
            "definition": {"category": "quantitative"},
        }
        response = call(
            MetricInstanceViewSet,
            "patch",
            "partial_update",
            data,
            admin(),
            pk=instance.id,
        )
        assert response.status_code == 200, response.data
        assert MetricDefinition.objects.count() == 1


class TestSimilarDefinitions:
    def test_readable_definitions_with_the_domains_measuring_them(self):
        group = make_domain("ACME")
        fr, de = make_domain("France", group), make_domain("Germany", group)
        assets = MetricDefinition.objects.create(name="Number of assets", folder=group)
        make_instance(fr, assets)
        make_instance(de, assets)
        MetricDefinition.objects.create(name="Number of users", folder=group)
        response = call(
            MetricDefinitionViewSet,
            "get",
            "similar",
            {"name": "number of ass", "category": "quantitative"},
            admin(),
        )
        assert response.status_code == 200
        assert [d["name"] for d in response.data] == ["Number of assets"]
        assert response.data[0]["folder"]["name"] == group.name
        assert sorted(response.data[0]["domains"]) == sorted([fr.name, de.name])

    def test_a_sibling_domain_s_definition_is_not_revealed(self):
        group = make_domain("ACME")
        fr, es = make_domain("France", group), make_domain("Spain", group)
        MetricDefinition.objects.create(name="Number of assets", folder=fr)
        response = call(
            MetricDefinitionViewSet,
            "get",
            "similar",
            {"name": "assets"},
            member(es, ["view_metricdefinition", "view_metricinstance"]),
        )
        assert response.status_code == 200
        assert response.data == []

    def test_short_names_match_nothing(self):
        MetricDefinition.objects.create(
            name="Number of assets", folder=Folder.get_root_folder()
        )
        response = call(
            MetricDefinitionViewSet, "get", "similar", {"name": "as"}, admin()
        )
        assert response.data == []


class TestMerge:
    def test_instances_move_and_the_source_is_deleted(self):
        group = make_domain("ACME")
        es = make_domain("Spain", group)
        count = unit()
        kept = MetricDefinition.objects.create(
            name="Number of assets", folder=group, unit=count, higher_is_better=None
        )
        mine = MetricDefinition.objects.create(
            name="Number of assets", folder=es, unit=count, higher_is_better=True
        )
        instance = make_instance(es, mine, target_value=1000)
        sample(instance, 1290, at(2026, 10, 1))
        response = call(
            MetricDefinitionViewSet,
            "post",
            "merge",
            {"into": str(kept.id)},
            admin(),
            pk=mine.id,
        )
        assert response.status_code == 200, response.data
        assert response.data == {"into": str(kept.id), "moved": 1}
        instance.refresh_from_db()
        assert instance.metric_definition == kept
        assert instance.target_value == 1000
        assert instance.samples.count() == 1
        assert not MetricDefinition.objects.filter(id=mine.id).exists()

    @pytest.mark.parametrize(
        "source_extra, target_extra, reason",
        [
            ({"unit": "count"}, {"unit": "percentage"}, "unit"),
            ({"category": "qualitative"}, {"category": "quantitative"}, "kind"),
            ({"expression": "1 + 1"}, {}, "computed"),
        ],
    )
    def test_mismatches_are_refused(self, source_extra, target_extra, reason):
        group = make_domain("ACME")
        es = make_domain("Spain", group)

        def build(folder, extra):
            extra = dict(extra)
            if "unit" in extra:
                extra["unit"] = unit(extra["unit"])
            return MetricDefinition.objects.create(
                name=f"D {uuid.uuid4().hex[:4]}", folder=folder, **extra
            )

        source, target = build(es, source_extra), build(group, target_extra)
        response = call(
            MetricDefinitionViewSet,
            "post",
            "merge",
            {"into": str(target.id)},
            admin(),
            pk=source.id,
        )
        assert response.status_code == 400
        assert reason in response.data["into"][0]
        assert MetricDefinition.objects.filter(id=source.id).exists()

    def test_a_definition_read_by_a_formula_is_not_merged_away(self):
        group = make_domain("ACME")
        es = make_domain("Spain", group)
        kept = MetricDefinition.objects.create(name="Assets", folder=group)
        mine = MetricDefinition.objects.create(name="Assets", folder=es)
        make_definition(
            "Rate",
            inputs=[{"key": "a", "definition": str(mine.id)}],
            expression="a * 2",
        )
        response = call(
            MetricDefinitionViewSet,
            "post",
            "merge",
            {"into": str(kept.id)},
            admin(),
            pk=mine.id,
        )
        assert response.status_code == 400
        assert "formula" in response.data["into"][0]
        assert MetricDefinition.objects.filter(id=mine.id).exists()

    def test_level_definitions_merge_only_with_the_same_levels(self):
        group = make_domain("ACME")
        es = make_domain("Spain", group)
        levels = [{"ref_id": "l", "name": "Low"}, {"ref_id": "h", "name": "High"}]
        kept = MetricDefinition.objects.create(
            name="Maturity",
            folder=group,
            category="qualitative",
            choices_definition=levels,
        )
        mine = MetricDefinition.objects.create(
            name="Maturity",
            folder=es,
            category="qualitative",
            choices_definition=list(reversed(levels)),
        )
        response = call(
            MetricDefinitionViewSet,
            "post",
            "merge",
            {"into": str(kept.id)},
            admin(),
            pk=mine.id,
        )
        assert response.status_code == 400
        assert "levels" in response.data["into"][0]

    def test_the_merge_takes_change_rights_on_both_and_on_the_metrics(self):
        group = make_domain("ACME")
        es = make_domain("Spain", group)
        kept = MetricDefinition.objects.create(name="Assets", folder=group)
        mine = MetricDefinition.objects.create(name="Assets", folder=es)
        make_instance(es, mine)
        # Can change in Spain, can only read the group.
        user = member(es, WRITE)
        member_group = member(group, ["view_metricdefinition"])
        user.user_groups.add(*member_group.user_groups.all())
        response = call(
            MetricDefinitionViewSet,
            "post",
            "merge",
            {"into": str(kept.id)},
            user,
            pk=mine.id,
        )
        assert response.status_code == 403
        assert MetricDefinition.objects.filter(id=mine.id).exists()


class TestPeriodOnEnteredValues:
    def test_a_value_answers_for_the_period_its_moment_names(self, frozen):  # noqa: F811
        es = make_domain("Spain")
        instance = make_instance(es, make_definition())
        data = {
            "metric_instance": str(instance.id),
            "timestamp": at(2026, 5, 3, 10).isoformat(),
            "period_start": at(2026, 4, 14).isoformat(),
            "value": {"result": 1290},
        }
        response = call(CustomMetricSampleViewSet, "post", "create", data, admin())
        assert response.status_code == 201, response.data
        stored = instance.samples.get()
        assert stored.period_start == at(2026, 4, 1)
        assert stored.timestamp == at(2026, 5, 3, 10)

    def test_a_second_value_for_the_period_replaces_the_first(self, frozen):  # noqa: F811
        es = make_domain("Spain")
        instance = make_instance(es, make_definition())
        for moment, value in ((at(2026, 5, 3, 10), 1290), (at(2026, 5, 4, 9), 1300)):
            data = {
                "metric_instance": str(instance.id),
                "timestamp": moment.isoformat(),
                "period_start": at(2026, 4, 1).isoformat(),
                "value": {"result": value},
                "observation": f"v{value}",
            }
            response = call(CustomMetricSampleViewSet, "post", "create", data, admin())
            assert response.status_code == 201, response.data
        stored = instance.samples.get()
        assert stored.raw_value() == 1300
        assert stored.observation == "v1300"
        assert stored.timestamp == at(2026, 5, 4, 9)

    def test_replacing_a_period_s_value_takes_the_right_to_change(self, frozen):  # noqa: F811
        es = make_domain("Spain")
        instance = make_instance(es, make_definition())
        CustomMetricSample.objects.create(
            metric_instance=instance,
            folder=es,
            timestamp=at(2026, 5, 3),
            period_start=at(2026, 4, 1),
            value={"result": 1},
        )
        data = {
            "metric_instance": str(instance.id),
            "timestamp": at(2026, 5, 4).isoformat(),
            "period_start": at(2026, 4, 1).isoformat(),
            "value": {"result": 2},
        }
        user = member(es, ["view_metricinstance", "add_custommetricsample"])
        response = call(CustomMetricSampleViewSet, "post", "create", data, user)
        assert response.status_code == 403
        assert instance.samples.get().raw_value() == 1

    def test_a_future_period_is_refused(self, frozen):  # noqa: F811
        es = make_domain("Spain")
        instance = make_instance(es, make_definition())
        data = {
            "metric_instance": str(instance.id),
            "timestamp": at(2026, 5, 3).isoformat(),
            "period_start": at(2027, 1, 1).isoformat(),
            "value": {"result": 1},
        }
        response = call(CustomMetricSampleViewSet, "post", "create", data, admin())
        assert response.status_code == 400
        assert "period_start" in response.data

    def test_two_periods_typed_in_the_same_second_both_keep_their_value(self, frozen):  # noqa: F811
        es = make_domain("Spain")
        instance = make_instance(es, make_definition())
        for period, value in ((at(2026, 3, 1), 10), (at(2026, 4, 1), 20)):
            data = {
                "metric_instance": str(instance.id),
                "timestamp": at(2026, 5, 3, 10, 0, 0).isoformat(),
                "period_start": period.isoformat(),
                "value": {"result": value},
            }
            response = call(CustomMetricSampleViewSet, "post", "create", data, admin())
            assert response.status_code == 201, response.data
        assert sorted(s.raw_value() for s in instance.samples.all()) == [10, 20]

    def test_a_value_typed_without_a_period_over_a_period_s_second_drops_the_period(
        self, frozen
    ):  # noqa: F811
        es = make_domain("Spain")
        instance = make_instance(es, make_definition())
        moment = at(2026, 5, 3, 10)
        CustomMetricSample.objects.create(
            metric_instance=instance,
            folder=es,
            timestamp=moment,
            period_start=at(2026, 4, 1),
            value={"result": 1},
        )
        data = {
            "metric_instance": str(instance.id),
            "timestamp": moment.isoformat(),
            "value": {"result": 2},
        }
        response = call(CustomMetricSampleViewSet, "post", "create", data, admin())
        assert response.status_code == 201, response.data
        stored = instance.samples.get()
        assert stored.raw_value() == 2
        assert stored.period_start is None

    def test_a_value_without_a_period_keeps_today_s_rule(self, frozen):  # noqa: F811
        es = make_domain("Spain")
        instance = make_instance(es, make_definition())
        data = {
            "metric_instance": str(instance.id),
            "timestamp": at(2026, 5, 3).isoformat(),
            "value": {"result": 1},
        }
        response = call(CustomMetricSampleViewSet, "post", "create", data, admin())
        assert response.status_code == 201, response.data
        assert instance.samples.get().period_start is None


class TestDirectionAndDecimals:
    def test_a_definition_has_no_direction_unless_one_is_stated(self):
        es = make_domain("Spain")
        data = {"name": "Assets", "folder": str(es.id)}
        response = call(MetricDefinitionViewSet, "post", "create", data, admin())
        assert response.status_code == 201, response.data
        assert (
            MetricDefinition.objects.get(id=response.data["id"]).higher_is_better
            is None
        )

    def test_more_than_six_decimals_is_refused(self):
        es = make_domain("Spain")
        data = {"name": "Assets", "folder": str(es.id), "decimals": 9}
        response = call(MetricDefinitionViewSet, "post", "create", data, admin())
        assert response.status_code == 400
        assert "decimals" in response.data

    def test_a_metric_cannot_lose_its_definition_on_edit(self):
        es = make_domain("Spain")
        instance = make_instance(es, make_definition())
        response = call(
            MetricInstanceViewSet,
            "patch",
            "partial_update",
            {"metric_definition": None},
            admin(),
            pk=instance.id,
        )
        assert response.status_code == 400
        assert "metric_definition" in response.data

    def test_direction_can_be_unset(self):
        es = make_domain("Spain")
        data = {"name": "Assets", "folder": str(es.id), "higher_is_better": None}
        response = call(MetricDefinitionViewSet, "post", "create", data, admin())
        assert response.status_code == 201, response.data
        assert (
            MetricDefinition.objects.get(id=response.data["id"]).higher_is_better
            is None
        )

    @pytest.mark.parametrize(
        "unit_name, decimals, value, shown",
        [
            ("percentage", None, 89.0756, "89.1 %"),
            ("percentage", 2, 89.0756, "89.08 %"),
            ("count", None, 1290.0, "1290"),
            ("count", None, 1290.5, "1291"),
            ("users", None, 12.3456, "12.3456 users"),
            ("users", 1, 12.3456, "12.3 users"),
            ("percentage", 2, 1, "1.00 %"),
            ("count", None, 1e30, "1e+30"),
        ],
    )
    def test_shown_values_round_to_the_definition_s_decimals(
        self, unit_name, decimals, value, shown
    ):
        es = make_domain("Spain")
        definition = make_definition(unit=unit(unit_name), decimals=decimals)
        instance = make_instance(es, definition)
        stored = sample(instance, value, at(2026, 10, 1))
        assert stored.display_value().lower() == shown
        assert stored.raw_value() == value
