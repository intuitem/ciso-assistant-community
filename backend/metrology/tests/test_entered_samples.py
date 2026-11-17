"""Entered samples, kept to the second: one per instance and second, the
last one written wins, whatever writes it (a person, the API, a workflow).
A formula's own samples keep their rule, one per period."""

import datetime
import uuid

import pytest
from django.contrib.auth.models import Permission
from django.db import IntegrityError, transaction
from rest_framework.test import APIRequestFactory, force_authenticate

from iam.models import Folder, Role, RoleAssignment, User, UserGroup
from metrology.models import CustomMetricSample, MetricDefinition, MetricInstance
from metrology.views import CustomMetricSampleViewSet

UTC = datetime.timezone.utc
NOON = datetime.datetime(2026, 5, 18, 12, 0, 0, tzinfo=UTC)


def make_domain():
    return Folder.objects.create(
        name=f"Domain {uuid.uuid4().hex[:6]}",
        parent_folder=Folder.get_root_folder(),
        content_type=Folder.ContentType.DOMAIN,
    )


def make_definition(**extra):
    return MetricDefinition.objects.create(
        name=f"Metric {uuid.uuid4().hex[:6]}", folder=Folder.get_root_folder(), **extra
    )


def make_instance(domain, definition=None):
    return MetricInstance.objects.create(
        name=f"Instance {uuid.uuid4().hex[:6]}",
        folder=domain,
        metric_definition=definition or make_definition(),
        status=MetricInstance.Status.ACTIVE,
    )


@pytest.mark.django_db
class TestRecord:
    def test_a_sample_for_a_taken_second_replaces_it_entirely(self):
        instance = make_instance(make_domain())
        first, created = CustomMetricSample.record(
            instance,
            NOON,
            value={"result": 1},
            observation="first reading",
            source=CustomMetricSample.Source.WORKFLOW,
        )
        assert created
        second, created = CustomMetricSample.record(
            instance, NOON + datetime.timedelta(microseconds=400), value={"result": 2}
        )
        assert not created and second.id == first.id
        second.refresh_from_db()
        assert second.value == {"result": 2}
        assert second.observation is None
        assert second.source == CustomMetricSample.Source.MANUAL
        assert instance.samples.count() == 1

    def test_samples_in_different_seconds_are_all_kept(self):
        instance = make_instance(make_domain())
        for second in range(3):
            CustomMetricSample.record(
                instance,
                NOON + datetime.timedelta(seconds=second),
                value={"result": second},
            )
        assert instance.samples.count() == 3

    def test_an_entered_sample_is_kept_to_the_second(self):
        instance = make_instance(make_domain())
        sample = CustomMetricSample.objects.create(
            metric_instance=instance,
            folder=instance.folder,
            timestamp=NOON + datetime.timedelta(milliseconds=750),
            value={"result": 1},
        )
        sample.refresh_from_db()
        assert sample.timestamp == NOON

    def test_the_database_refuses_two_entered_samples_in_one_second(self):
        instance = make_instance(make_domain())
        CustomMetricSample.objects.create(
            metric_instance=instance,
            folder=instance.folder,
            timestamp=NOON,
            value={"result": 1},
        )
        with pytest.raises(IntegrityError), transaction.atomic():
            CustomMetricSample.objects.create(
                metric_instance=instance,
                folder=instance.folder,
                timestamp=NOON + datetime.timedelta(milliseconds=10),
                value={"result": 2},
            )

    def test_formula_samples_keep_their_fraction_of_a_second(self):
        instance = make_instance(make_domain())
        moment = NOON + datetime.timedelta(microseconds=1)
        sample = CustomMetricSample.objects.create(
            metric_instance=instance,
            folder=instance.folder,
            timestamp=moment,
            value={"result": 1},
            source=CustomMetricSample.Source.DERIVED,
        )
        sample.refresh_from_db()
        assert sample.timestamp == moment

    def test_a_replaced_sample_marks_the_formulas_reading_it(
        self, django_capture_on_commit_callbacks, recompute_requests
    ):
        domain = make_domain()
        base = make_definition()
        source = make_instance(domain, base)
        reader = make_instance(
            domain,
            make_definition(
                inputs=[{"key": "x", "definition": str(base.id), "combine": "one"}],
                expression="x",
            ),
        )
        CustomMetricSample.record(source, NOON, value={"result": 1})
        with django_capture_on_commit_callbacks(execute=True):
            CustomMetricSample.record(source, NOON, value={"result": 2})
        reader.refresh_from_db()
        assert reader.recompute_from == NOON
        assert recompute_requests


@pytest.mark.django_db
class TestEndpoint:
    def user(self, folder, *codenames):
        user = User.objects.create_user(
            email=f"user-{uuid.uuid4().hex[:6]}@tests.local"
        )
        group = UserGroup.objects.create(
            name=f"group {uuid.uuid4().hex[:4]}", folder=folder
        )
        group.user_set.add(user)
        role = Role.objects.create(
            name=f"role {uuid.uuid4().hex[:4]}", folder=Folder.get_root_folder()
        )
        role.permissions.add(*Permission.objects.filter(codename__in=codenames))
        assignment = RoleAssignment.objects.create(
            user_group=group, role=role, folder=Folder.get_root_folder()
        )
        assignment.perimeter_folders.add(folder)
        return user

    def call(self, method, user, data, pk=None):
        path = "/metrology/custom-metric-samples/"
        actions = {"post": "create", "patch": "partial_update"}
        request = getattr(APIRequestFactory(), method)(
            f"{path}{pk}/" if pk else path, data, format="json"
        )
        force_authenticate(request, user=user)
        view = CustomMetricSampleViewSet.as_view({method: actions[method]})
        return view(request, pk=pk) if pk else view(request)

    def post(self, user, instance, value, moment):
        return self.call(
            "post",
            user,
            {
                "metric_instance": str(instance.id),
                "timestamp": moment.isoformat(),
                "value": {"result": value},
            },
        )

    def test_posting_a_taken_second_replaces_its_sample(self):
        domain = make_domain()
        instance = make_instance(domain)
        admin = User.objects.create_superuser(
            email=f"admin-{uuid.uuid4().hex[:6]}@tests.local"
        )
        first = self.post(admin, instance, 1, NOON)
        second = self.post(
            admin, instance, 2, NOON + datetime.timedelta(milliseconds=5)
        )
        assert (first.status_code, second.status_code) == (201, 201)
        assert first.data["id"] == second.data["id"]
        assert [s.value for s in instance.samples.all()] == [{"result": 2}]

    def test_replacing_a_sample_takes_the_right_to_change_samples(self):
        domain = make_domain()
        instance = make_instance(domain)
        adder = self.user(
            domain,
            "add_custommetricsample",
            "view_custommetricsample",
            "view_metricinstance",
        )
        assert self.post(adder, instance, 1, NOON).status_code == 201
        assert self.post(adder, instance, 2, NOON).status_code == 403
        assert [s.value for s in instance.samples.all()] == [{"result": 1}]
        later = NOON + datetime.timedelta(seconds=1)
        assert self.post(adder, instance, 3, later).status_code == 201

    def test_moving_a_sample_onto_a_taken_second_is_refused(self):
        domain = make_domain()
        instance = make_instance(domain)
        admin = User.objects.create_superuser(
            email=f"admin-{uuid.uuid4().hex[:6]}@tests.local"
        )
        self.post(admin, instance, 1, NOON)
        later = self.post(admin, instance, 2, NOON + datetime.timedelta(seconds=1))
        response = self.call(
            "patch", admin, {"timestamp": NOON.isoformat()}, pk=later.data["id"]
        )
        assert response.status_code == 400
        assert "timestamp" in response.data
        assert instance.samples.count() == 2
