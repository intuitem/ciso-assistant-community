"""Metric formulas: a metric computed from other metrics, period by period.
Calendar periods, as-of alignment with the staleness threshold as maximum
age, input resolution and combination, skipped periods, `previous`, one
stored sample per period, backfill bounds, recompute marks, formulas on
formulas, validation and the preview."""

import datetime
import uuid

import pytest
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate

from iam.models import Folder, User
from metrology import series
from metrology.derived import DerivedMetricError, compute_sample, validate_formula
from metrology.models import CustomMetricSample, MetricDefinition, MetricInstance
from metrology.series import FULL, evaluate_series, period_start, shift_period
from metrology.views import MetricDefinitionViewSet

UTC = datetime.timezone.utc
# A Monday, mid-month, mid-quarter.
NOW = datetime.datetime(2026, 5, 18, 12, 0, tzinfo=UTC)


def at(*args):
    return datetime.datetime(*args, tzinfo=UTC)


@pytest.fixture
def frozen(monkeypatch):
    monkeypatch.setattr(timezone, "now", lambda: NOW)
    cache.clear()
    return NOW


def make_domain(name, parent=None):
    return Folder.objects.create(
        name=f"{name} {uuid.uuid4().hex[:6]}",
        parent_folder=parent or Folder.get_root_folder(),
        content_type=Folder.ContentType.DOMAIN,
    )


def make_definition(name="Metric", **extra):
    return MetricDefinition.objects.create(
        name=f"{name} {uuid.uuid4().hex[:6]}",
        folder=Folder.get_root_folder(),
        **extra,
    )


def make_instance(folder, definition, frequency="monthly", **extra):
    return MetricInstance.objects.create(
        name=f"{definition.name} in {folder.name}",
        folder=folder,
        metric_definition=definition,
        collection_frequency=frequency,
        status=MetricInstance.Status.ACTIVE,
        **extra,
    )


def sample(instance, value, when):
    return CustomMetricSample.objects.create(
        metric_instance=instance,
        folder=instance.folder,
        timestamp=when,
        value={"result": value},
    )


def formula(expression, *inputs, **extra):
    return make_definition(
        "Formula",
        inputs=[
            {"key": key, "definition": str(definition.id), "combine": combine}
            for key, definition, combine in inputs
        ],
        expression=expression,
        **extra,
    )


def stored(instance):
    return {
        s.period_start.date().isoformat(): s.raw_value()
        for s in instance.samples.filter(period_start__isnull=False).order_by(
            "period_start"
        )
    }


# ---------- periods ----------


class TestPeriods:
    moment = at(2026, 5, 20, 13, 37, 12)

    @pytest.mark.parametrize(
        "frequency, expected",
        [
            ("realtime", at(2026, 5, 20, 13, 30)),
            ("hourly", at(2026, 5, 20, 13)),
            ("daily", at(2026, 5, 20)),
            (None, at(2026, 5, 20)),
            ("weekly", at(2026, 5, 18)),
            ("monthly", at(2026, 5, 1)),
            ("quarterly", at(2026, 4, 1)),
            ("yearly", at(2026, 1, 1)),
        ],
    )
    def test_calendar_starts(self, frequency, expected):
        assert period_start(self.moment, frequency) == expected

    def test_shifts_follow_the_calendar(self):
        assert shift_period(at(2026, 1, 1), "monthly") == at(2026, 2, 1)
        assert shift_period(at(2026, 11, 1), "quarterly") == at(2027, 2, 1)
        assert shift_period(at(2026, 1, 1), "monthly", -1) == at(2025, 12, 1)
        assert shift_period(at(2026, 1, 1), "yearly", 2) == at(2028, 1, 1)
        assert shift_period(at(2026, 5, 18), "weekly", -1) == at(2026, 5, 11)


# ---------- evaluation ----------


@pytest.mark.django_db
class TestSeries:
    def test_a_ratio_period_by_period(self, frozen):
        domain = make_domain("Domain")
        clicks, trained = make_definition("Clicks"), make_definition("Trained")
        c, t = make_instance(domain, clicks), make_instance(domain, trained)
        for month, (n_clicks, n_trained) in enumerate([(12, 400), (9, 400), (15, 420)]):
            sample(c, n_clicks, at(2026, 3 + month, 10))
            sample(t, n_trained, at(2026, 3 + month, 5))
        rate = make_instance(
            domain,
            formula("c * 100.0 / t", ("c", clicks, "one"), ("t", trained, "one")),
        )
        compute_sample(rate)
        assert stored(rate) == {
            "2026-03-01": 3.0,
            "2026-04-01": 2.25,
            "2026-05-01": pytest.approx(15 * 100 / 420),
        }

    def test_slower_inputs_carry_until_their_staleness_threshold(self, frozen):
        """Weekly output, monthly input: the March value stands until it is
        older than 32 days, then the week has no value and is skipped."""
        domain = make_domain("Domain")
        monthly = make_definition("Monthly")
        source = make_instance(domain, monthly, "monthly")
        sample(source, 10, at(2026, 3, 30))
        out = make_instance(domain, formula("m", ("m", monthly, "one")), "weekly")
        evaluation = compute_sample(out)
        values = {p.start.date().isoformat(): p.value for p in evaluation.periods}
        assert values["2026-03-30"] == 10
        assert values["2026-04-20"] == 10  # 27 days old at the end of the week
        assert values["2026-04-27"] is None  # 35 days old: missing
        assert "2026-04-20" in stored(out)
        assert "2026-04-27" not in stored(out)

    def test_a_missing_input_skips_the_period_unless_handled(self, frozen):
        domain = make_domain("Domain")
        a_def, b_def = make_definition("A"), make_definition("B")
        a, b = make_instance(domain, a_def), make_instance(domain, b_def)
        sample(a, 5, at(2026, 4, 10))
        sample(a, 6, at(2026, 5, 10))
        sample(b, 1, at(2026, 5, 10))
        plain = make_instance(
            domain, formula("a + b", ("a", a_def, "one"), ("b", b_def, "one"))
        )
        compute_sample(plain)
        assert stored(plain) == {"2026-05-01": 7}
        handled = make_instance(
            domain,
            formula(
                "a + (b == null ? 0 : b)", ("a", a_def, "one"), ("b", b_def, "one")
            ),
        )
        compute_sample(handled)
        assert stored(handled) == {"2026-04-01": 5, "2026-05-01": 7}

    def test_previous_is_the_period_before(self, frozen):
        domain = make_domain("Domain")
        total = make_definition("Total")
        source = make_instance(domain, total)
        for month, value in ((3, 100), (4, 130), (5, 120)):
            sample(source, value, at(2026, month, 2))
        delta = make_instance(
            domain, formula("previous == null ? 0 : x - previous", ("x", total, "one"))
        )
        # `previous` is this formula's own result, so x - previous on the
        # deltas: 0, 130 - 0, 120 - 130.
        compute_sample(delta)
        assert stored(delta) == {"2026-03-01": 0, "2026-04-01": 130, "2026-05-01": -10}

    def test_combinations_over_the_subtree(self, frozen):
        hq = make_domain("HQ")
        sites = [make_domain(name, hq) for name in ("FR", "DE", "ES")]
        outside = make_domain("Outside")
        incidents = make_definition("Incidents")
        for value, site in zip((3, 5, 4), sites):
            sample(make_instance(site, incidents), value, at(2026, 5, 3))
        sample(make_instance(outside, incidents), 100, at(2026, 5, 3))
        for combine, expected in (
            ("sum", 12),
            ("avg", 4),
            ("min", 3),
            ("max", 5),
            ("count", 3),
        ):
            out = make_instance(hq, formula("x", ("x", incidents, combine)))
            compute_sample(out)
            assert stored(out)["2026-05-01"] == expected, combine

    def test_one_value_needs_exactly_one_instance(self, frozen):
        hq = make_domain("HQ")
        incidents = make_definition("Incidents")
        make_instance(make_domain("FR", hq), incidents)
        make_instance(make_domain("DE", hq), incidents)
        out = make_instance(hq, formula("x", ("x", incidents, "one")))
        with pytest.raises(DerivedMetricError, match="2 instances of"):
            compute_sample(out)
        out.refresh_from_db()
        assert "'one value' needs exactly one" in out.last_computation_error

    def test_no_input_sample_means_no_series(self, frozen):
        domain = make_domain("Domain")
        empty = make_definition("Empty")
        make_instance(domain, empty)
        out = make_instance(domain, formula("x", ("x", empty, "one")))
        evaluation = compute_sample(out)
        assert evaluation.periods == [] and stored(out) == {}

    def test_a_qualitative_output_takes_a_level(self, frozen):
        domain = make_domain("Domain")
        score = make_definition("Score")
        sample(make_instance(domain, score), 80, at(2026, 5, 2))
        level = make_instance(
            domain,
            formula(
                "s >= 75 ? 'good' : 'poor'",
                ("s", score, "one"),
                category=MetricDefinition.Category.QUALITATIVE,
                choices_definition=[{"name": "poor"}, {"name": "good"}],
            ),
        )
        compute_sample(level)
        assert stored(level) == {"2026-05-01": 2}


# ---------- storage ----------


@pytest.mark.django_db
class TestStorage:
    def test_one_sample_per_period_replaced_in_place(self, frozen):
        domain = make_domain("Domain")
        base = make_definition("Base")
        source = make_instance(domain, base)
        sample(source, 1, at(2026, 4, 2))
        point = sample(source, 2, at(2026, 5, 2))
        out = make_instance(domain, formula("x * 10", ("x", base, "one")))
        compute_sample(out)
        april = out.samples.get(period_start=at(2026, 4, 1))
        point.value = {"result": 3}
        point.save()
        compute_sample(out, full=True)
        assert stored(out) == {"2026-04-01": 10, "2026-05-01": 30}
        assert out.samples.get(period_start=at(2026, 4, 1)).id == april.id
        assert out.samples.count() == 2

    def test_a_period_that_no_longer_computes_loses_its_sample(self, frozen):
        domain = make_domain("Domain")
        base = make_definition("Base")
        source = make_instance(domain, base)
        early = sample(source, 1, at(2026, 3, 2))
        sample(source, 2, at(2026, 5, 2))
        out = make_instance(domain, formula("x", ("x", base, "one")))
        compute_sample(out)
        assert "2026-03-01" in stored(out)
        early.delete()
        compute_sample(out, full=True)
        assert stored(out) == {"2026-05-01": 2}

    def test_the_open_period_is_stamped_now(self, frozen):
        domain = make_domain("Domain")
        base = make_definition("Base")
        # Late April: still fresh enough (32 days) for the open May period.
        sample(make_instance(domain, base), 1, at(2026, 4, 25))
        out = make_instance(domain, formula("x", ("x", base, "one")))
        compute_sample(out)
        stamps = {
            s.period_start: s.timestamp for s in out.samples.order_by("period_start")
        }
        assert stamps[at(2026, 4, 1)] == at(2026, 5, 1) - datetime.timedelta(
            microseconds=1
        )
        assert stamps[at(2026, 5, 1)] == NOW

    def test_backfill_is_capped(self, frozen, monkeypatch):
        monkeypatch.setattr(series, "MAX_PERIODS", 3)
        domain = make_domain("Domain")
        base = make_definition("Base")
        source = make_instance(domain, base, "yearly")
        for year in range(2020, 2027):
            sample(source, year, at(year, 1, 2))
        out = make_instance(domain, formula("x", ("x", base, "one")), "yearly")
        compute_sample(out)
        assert list(stored(out)) == ["2024-01-01", "2025-01-01", "2026-01-01"]

    def test_sub_daily_periods_stay_inside_the_downsampling_window(self, frozen):
        domain = make_domain("Domain")
        base = make_definition("Base")
        source = make_instance(domain, base, None)
        sample(source, 1, NOW - datetime.timedelta(days=10))
        out = make_instance(domain, formula("x", ("x", base, "one")), "hourly")
        evaluation = compute_sample(out)
        assert evaluation.periods[0].start >= NOW - datetime.timedelta(days=7, hours=1)


# ---------- recompute marks ----------


@pytest.mark.django_db
class TestMarks:
    def setup_series(self):
        domain = make_domain("Domain")
        base = make_definition("Base")
        source = make_instance(domain, base)
        sample(source, 1, at(2026, 3, 2))
        sample(source, 2, at(2026, 5, 2))
        out = make_instance(domain, formula("x", ("x", base, "one")))
        compute_sample(out)
        out.refresh_from_db()
        assert out.recompute_from is None
        return domain, base, source, out

    def test_a_new_input_sample_marks_its_period(
        self, frozen, django_capture_on_commit_callbacks
    ):
        _domain, _base, source, out = self.setup_series()
        with django_capture_on_commit_callbacks(execute=True):
            sample(source, 5, at(2026, 4, 9))
        out.refresh_from_db()
        # The moment itself: each reader turns it into its own period.
        assert out.recompute_from == at(2026, 4, 9)
        # The next run recomputes from April, March untouched.
        march = out.samples.get(period_start=at(2026, 3, 1))
        compute_sample(out, only_if_due=True)
        assert stored(out) == {"2026-03-01": 1, "2026-04-01": 5, "2026-05-01": 2}
        assert out.samples.get(period_start=at(2026, 3, 1)).updated_at == (
            march.updated_at
        )

    def test_an_edit_marks_from_the_earlier_timestamp(
        self, frozen, django_capture_on_commit_callbacks
    ):
        _domain, _base, source, out = self.setup_series()
        point = source.samples.get(timestamp=at(2026, 5, 2))
        with django_capture_on_commit_callbacks(execute=True):
            point.timestamp = at(2026, 3, 20)
            point.save()
        out.refresh_from_db()
        assert out.recompute_from == at(2026, 3, 20)

    def test_a_deleted_sample_marks_its_period(
        self, frozen, django_capture_on_commit_callbacks
    ):
        _domain, _base, source, out = self.setup_series()
        with django_capture_on_commit_callbacks(execute=True):
            source.samples.get(timestamp=at(2026, 5, 2)).delete()
        out.refresh_from_db()
        assert out.recompute_from == at(2026, 5, 2)

    def test_an_earlier_mark_is_kept(self, frozen, django_capture_on_commit_callbacks):
        _domain, _base, source, out = self.setup_series()
        with django_capture_on_commit_callbacks(execute=True):
            sample(source, 5, at(2026, 3, 9))
            sample(source, 6, at(2026, 5, 9))
        out.refresh_from_db()
        assert out.recompute_from == at(2026, 3, 9)

    def test_a_new_input_instance_marks_the_whole_series(
        self, frozen, django_capture_on_commit_callbacks
    ):
        domain, base, _source, out = self.setup_series()
        with django_capture_on_commit_callbacks(execute=True):
            make_instance(make_domain("Sub", domain), base)
        out.refresh_from_db()
        assert out.recompute_from == FULL

    def test_bookkeeping_on_an_input_marks_nothing(
        self, frozen, django_capture_on_commit_callbacks
    ):
        _domain, _base, source, out = self.setup_series()
        with django_capture_on_commit_callbacks(execute=True):
            source.status = MetricInstance.Status.STALE
            source.save()
        out.refresh_from_db()
        assert out.recompute_from is None

    def test_a_new_input_frequency_marks_the_whole_series(
        self, frozen, django_capture_on_commit_callbacks
    ):
        """The frequency sets how old a value may be when a reader aligns on
        it, so every period may differ."""
        _domain, _base, source, out = self.setup_series()
        with django_capture_on_commit_callbacks(execute=True):
            source.collection_frequency = "weekly"
            source.save()
        out.refresh_from_db()
        assert out.recompute_from == FULL

    def test_a_deleted_input_instance_marks_once(
        self, frozen, django_capture_on_commit_callbacks
    ):
        """Its samples go first and would each queue a mark of their own;
        the instance's single FULL mark is the one that counts."""
        _domain, _base, source, out = self.setup_series()
        sample(source, 3, at(2026, 4, 2))
        with django_capture_on_commit_callbacks(execute=True) as callbacks:
            source.delete()
        assert len(callbacks) == 1
        out.refresh_from_db()
        assert out.recompute_from == FULL

    def test_editing_the_formula_marks_every_instance(
        self, frozen, django_capture_on_commit_callbacks
    ):
        _domain, _base, _source, out = self.setup_series()
        definition = out.metric_definition
        with django_capture_on_commit_callbacks(execute=True):
            definition.expression = "x * 2"
            definition.save()
        out.refresh_from_db()
        assert out.recompute_from == FULL
        compute_sample(out, only_if_due=True)
        assert stored(out)["2026-05-01"] == 4

    def test_a_marked_formula_is_due_for_the_sweep(
        self, frozen, django_capture_on_commit_callbacks
    ):
        from metrology.derived import due_instances

        _domain, _base, source, out = self.setup_series()
        assert out.id not in {i.id for i in due_instances()}
        with django_capture_on_commit_callbacks(execute=True):
            sample(source, 9, at(2026, 5, 10))
        assert out.id in {i.id for i in due_instances()}


# ---------- formulas on formulas ----------


@pytest.mark.django_db
class TestComposition:
    def test_the_sweep_computes_inputs_before_their_readers(self, frozen):
        from metrology.tasks import compute_due_derived_metrics

        domain = make_domain("Domain")
        base = make_definition("Base")
        sample(make_instance(domain, base), 4, at(2026, 5, 2))
        middle_def = formula("x * 2", ("x", base, "one"))
        top_def = formula("y + 1", ("y", middle_def, "one"))
        # Created top first, so creation order alone would be wrong.
        top = make_instance(domain, top_def)
        middle = make_instance(domain, middle_def)
        compute_due_derived_metrics.call_local()
        assert stored(middle) == {"2026-05-01": 8}
        assert stored(top) == {"2026-05-01": 9}

    def test_the_sweep_computes_a_dataset_input_before_its_reader(
        self, frozen, monkeypatch
    ):
        """A dataset formula is queued on its own, unless a due metric formula
        reads it: then it runs first, in the sweep, so the reader does not
        see the previous tick's value."""
        from core.models import AppliedControl
        from metrology import tasks

        queued = []
        monkeypatch.setattr(
            tasks, "compute_derived_metric_task", lambda *a, **k: queued.append(a)
        )
        domain = make_domain("Domain")
        AppliedControl.objects.create(name="AC", folder=domain, status="active")
        counting = make_definition(
            "Controls",
            datasets={
                "c": {"model": "applied_control", "aggregates": [{"fn": "count"}]}
            },
            expression="c.count",
        )
        unrelated = make_definition(
            "Other",
            datasets={
                "c": {"model": "applied_control", "aggregates": [{"fn": "count"}]}
            },
            expression="c.count * 10",
        )
        count = make_instance(domain, counting)
        other = make_instance(domain, unrelated)
        reader = make_instance(domain, formula("x + 1", ("x", counting, "one")))
        tasks.compute_due_derived_metrics.call_local()
        assert count.raw_value() == 1
        assert stored(reader) == {"2026-05-01": 2}
        # The one nobody reads went to the queue as before.
        assert queued == [(str(other.id),)]

    def test_a_reader_is_marked_when_its_input_formula_changes(self, frozen):
        domain = make_domain("Domain")
        base = make_definition("Base")
        sample(make_instance(domain, base), 4, at(2026, 5, 2))
        middle_def = formula("x * 2", ("x", base, "one"))
        middle = make_instance(domain, middle_def)
        top = make_instance(domain, formula("y + 1", ("y", middle_def, "one")))
        compute_sample(middle)
        top.refresh_from_db()
        assert top.recompute_from == at(2026, 5, 1)

    def test_an_input_named_by_urn_resolves(self, frozen):
        domain = make_domain("Domain")
        base = make_definition("Base", urn=f"urn:test:metric:{uuid.uuid4().hex[:6]}")
        sample(make_instance(domain, base), 4, at(2026, 5, 2))
        out_def = make_definition(
            "Formula",
            inputs=[{"key": "x", "definition": base.urn.upper(), "combine": "one"}],
            expression="x",
        )
        out = make_instance(domain, out_def)
        compute_sample(out)
        assert stored(out) == {"2026-05-01": 4}


# ---------- validation ----------


@pytest.mark.django_db
class TestValidation:
    def codes(self, *args, **kwargs):
        return [code for code, _message in validate_formula(*args, **kwargs)]

    def inputs(self, *pairs):
        return [
            {"key": key, "definition": str(definition.id), "combine": "one"}
            for key, definition in pairs
        ]

    def test_a_clean_formula_passes(self):
        base = make_definition("Base")
        assert validate_formula(None, "x + 1", self.inputs(("x", base))) == []

    def test_datasets_and_inputs_do_not_mix(self):
        base = make_definition("Base")
        datasets = {"c": {"model": "applied_control", "aggregates": [{"fn": "count"}]}}
        assert self.codes(datasets, "x", self.inputs(("x", base))) == [
            "derived_formula_mixed"
        ]

    def test_inputs_are_named_once_and_never_after_context_names(self):
        base = make_definition("Base")
        assert self.codes(None, "x", self.inputs(("x", base), ("x", base))) == [
            "derived_input_key_invalid"
        ]
        for key in ("previous", "now", "today", "metrics", "1x"):
            assert "derived_input_key_invalid" in self.codes(
                None, "1", self.inputs((key, base))
            ), key

    def test_inputs_are_quantitative_existing_metrics(self):
        level = make_definition(
            "Level",
            category=MetricDefinition.Category.QUALITATIVE,
            choices_definition=[{"name": "low"}],
        )
        assert self.codes(None, "x", self.inputs(("x", level))) == [
            "derived_input_invalid"
        ]
        missing = [{"key": "x", "definition": str(uuid.uuid4()), "combine": "one"}]
        assert self.codes(None, "x", missing) == ["derived_input_invalid"]
        base = make_definition("Base")
        bad = [{"key": "x", "definition": str(base.id), "combine": "median"}]
        assert self.codes(None, "x", bad) == ["derived_input_invalid"]

    def test_a_formula_cannot_read_itself(self):
        base = make_definition("Base")
        middle = formula("x", ("x", base, "one"))
        top = formula("y", ("y", middle, "one"))
        assert self.codes(None, "z", self.inputs(("z", top)), definition=middle) == [
            "derived_input_cycle"
        ]
        assert self.codes(None, "z", self.inputs(("z", middle)), definition=middle) == [
            "derived_input_cycle"
        ]

    def test_the_expression_reads_inputs_not_latest_values(self):
        base = make_definition("Base")
        assert self.codes(None, "y", self.inputs(("x", base))) == [
            "derived_expression_unknown_name"
        ]
        assert self.codes(None, "metrics.a.value", self.inputs(("x", base))) == [
            "derived_expression_unknown_name"
        ]
        assert self.codes(None, "", self.inputs(("x", base))) == [
            "derived_expression_missing"
        ]

    def test_the_serializer_holds_a_definition_to_it(self):
        from metrology.serializers import MetricDefinitionWriteSerializer

        base = make_definition("Base")
        middle = formula("x", ("x", base, "one"))
        top = formula("y", ("y", middle, "one"))
        serializer = MetricDefinitionWriteSerializer(
            middle,
            data={"inputs": self.inputs(("z", top)), "expression": "z"},
            partial=True,
        )
        assert not serializer.is_valid()
        assert "depends on this metric" in str(serializer.errors["expression"])


# ---------- preview ----------


@pytest.mark.django_db
class TestPreview:
    def post(self, data):
        view = MetricDefinitionViewSet.as_view({"post": "preview_formula"})
        request = APIRequestFactory().post(
            "/metrology/metric-definitions/preview-formula/", data, format="json"
        )
        force_authenticate(
            request,
            user=User.objects.create_superuser(
                email=f"admin-{uuid.uuid4().hex[:6]}@tests.local"
            ),
        )
        return view(request)

    def test_periods_and_what_each_input_resolved_to(self, frozen):
        hq = make_domain("HQ")
        fr = make_domain("FR", hq)
        incidents = make_definition("Incidents")
        site = make_instance(fr, incidents)
        sample(site, 3, at(2026, 4, 3))
        sample(site, 5, at(2026, 5, 3))
        response = self.post(
            {
                "folder": str(hq.id),
                "frequency": "monthly",
                "inputs": [
                    {"key": "x", "definition": str(incidents.id), "combine": "sum"}
                ],
                "expression": "x * 2",
            }
        )
        assert response.status_code == 200, response.data
        assert response.data["ok"] is True
        assert response.data["value"] == 10
        assert [(p["start"][:10], p["value"]) for p in response.data["periods"]] == [
            ("2026-04-01", 6),
            ("2026-05-01", 10),
        ]
        assert response.data["inputs"] == {
            "x": [{"id": str(site.id), "name": site.name, "folder": fr.name}]
        }
        assert (
            CustomMetricSample.objects.filter(period_start__isnull=False).count() == 0
        )

    def test_a_resolution_failure_is_answered(self, frozen):
        hq = make_domain("HQ")
        incidents = make_definition("Incidents")
        response = self.post(
            {
                "folder": str(hq.id),
                "inputs": [
                    {"key": "x", "definition": str(incidents.id), "combine": "one"}
                ],
                "expression": "x",
            }
        )
        assert response.data["ok"] is False
        assert "0 instances of" in response.data["errors"][0]["message"]

    def test_the_preview_only_reaches_back_two_years_of_months(self, frozen):
        domain = make_domain("Domain")
        base = make_definition("Base")
        sample(make_instance(domain, base), 1, at(2020, 1, 3))
        response = self.post(
            {
                "folder": str(domain.id),
                "frequency": "monthly",
                "inputs": [{"key": "x", "definition": str(base.id), "combine": "one"}],
                "expression": "x == null ? 0 : x",
            }
        )
        assert len(response.data["periods"]) == 24


def test_evaluate_series_writes_nothing():
    """evaluate_series is the preview's path; only compute_series stores."""
    assert "CustomMetricSample.objects.bulk" not in evaluate_series.__code__.co_names


@pytest.mark.django_db
def test_a_library_ships_a_formula_whose_inputs_name_urns(frozen):
    """The importer used to drop datasets and expression; inputs name other
    definitions by URN since a library cannot know their ids."""
    from core.models import LoadedLibrary
    from library.utils import MetricDefinitionImporter

    suffix = uuid.uuid4().hex[:6]
    library = LoadedLibrary.objects.create(
        urn=f"urn:test:metrics:{suffix}",
        locale="en",
        version=1,
        name="Metrics library",
        folder=Folder.get_root_folder(),
        objects_meta={},
    )
    base_urn = f"urn:test:metric:{suffix}:clicks"
    for data in (
        {"urn": base_urn, "ref_id": "CLICKS", "name": "Clicks"},
        {
            "urn": f"urn:test:metric:{suffix}:double",
            "ref_id": "DOUBLE",
            "name": "Double clicks",
            "inputs": [{"key": "c", "definition": base_urn, "combine": "sum"}],
            "expression": "c * 2",
        },
    ):
        importer = MetricDefinitionImporter(data)
        assert importer.is_valid() is None
        importer.import_metric_definition(library)
    base = MetricDefinition.objects.get(urn=base_urn)
    double = MetricDefinition.objects.get(urn=f"urn:test:metric:{suffix}:double")
    assert double.reads_metrics and double.expression == "c * 2"
    domain = make_domain("Domain")
    sample(make_instance(domain, base), 21, at(2026, 5, 2))
    out = make_instance(domain, double)
    compute_sample(out)
    assert stored(out) == {"2026-05-01": 42}
