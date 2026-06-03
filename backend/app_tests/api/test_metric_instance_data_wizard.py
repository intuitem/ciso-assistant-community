"""
Constraint / behaviour harness for the MetricInstance data-wizard import
introduced in PR #3800 (feat/add_metric_instance_and_refactor).

The tests drive `MetricInstanceRecordConsumer.process_records()` directly with
plain record dicts (the same shape the wizard produces from a CSV/Excel row).

They are split in two groups:

  * NOMINAL VALIDATION  - asserts the new Field constraints reject bad input.
                          These are expected to PASS on the current PR code.

  * EXPECTED-TO-FAIL     - encodes the behaviour we intend to ship (per the
                          review findings). These are expected to FAIL on the
                          current PR code and should pass once the findings are
                          fixed. Each is tagged with the finding number.

Findings under test:
  #1  Optional fields are mandatory in practice (owner / filtering_labels /
      empty status all error out because the Field defaults are blank=False).
  #2  Imported instances ignore the selected folder and land in the root folder
      (no FolderField in FIELDS, no folder injection).
  #3  Owner resolution by team name is broken: get_viewable_object_ids(Actor,
      ["user"]) collapses every team/entity actor onto the key (None,), so all
      but one team actor disappear from the viewable set.
"""

import pytest
from django.test import RequestFactory

from iam.models import Folder, User, UserGroup
from core.models import Team
from metrology.models import MetricInstance, MetricDefinition

from data_wizard.views import MetricInstanceRecordConsumer, BaseContext, ConflictMode


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #
class WizardEnv:
    def __init__(self, admin, domain, metric_def):
        self.admin = admin
        self.domain = domain
        self.metric_def = metric_def
        self._factory = RequestFactory()

    def run(self, records, folder_id=None, on_conflict=ConflictMode.STOP):
        """Run the consumer on `records` and return the Result object."""
        request = self._factory.post("/")
        request.user = self.admin
        ctx = BaseContext(
            request=request,
            folder_id=str(folder_id) if folder_id is not None else None,
            on_conflict=on_conflict,
        )
        return MetricInstanceRecordConsumer(ctx).process_records(records)


@pytest.fixture
def env(app_config):
    """A global-admin user, a target domain, and a metric definition to point at."""
    admin = User.objects.create_superuser("wizard-admin@tests.com", is_published=True)
    admin_group = UserGroup.objects.get(name="BI-UG-ADM")
    admin.folder = admin_group.folder
    admin.save()
    admin_group.user_set.add(admin)

    domain = Folder.objects.create(name="Metrics Domain")
    metric_def = MetricDefinition.objects.create(name="Availability")

    return WizardEnv(admin, domain, metric_def)


def _errors(result):
    return [e.error for e in result.errors]


# --------------------------------------------------------------------------- #
# NOMINAL VALIDATION  (expected to PASS on current code)
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
class TestFieldConstraints:
    def test_missing_required_name_is_rejected(self, env):
        result = env.run(
            [{"metric_definition": "Availability", "status": "active"}],
            folder_id=env.domain.id,
        )
        assert result.created == 0
        assert result.failed == 1, _errors(result)

    def test_invalid_status_choice_is_rejected(self, env):
        result = env.run(
            [
                {
                    "name": "M1",
                    "metric_definition": "Availability",
                    "status": "bogus-status",
                    "filtering_labels": "L1",
                    "owner": "wizard-admin@tests.com",
                }
            ],
            folder_id=env.domain.id,
        )
        assert result.created == 0
        assert result.failed == 1, _errors(result)

    def test_unknown_metric_definition_is_rejected(self, env):
        result = env.run(
            [
                {
                    "name": "M1",
                    "metric_definition": "Does Not Exist",
                    "status": "active",
                    "filtering_labels": "L1",
                    "owner": "wizard-admin@tests.com",
                }
            ],
            folder_id=env.domain.id,
        )
        assert result.created == 0
        assert result.failed == 1, _errors(result)

    def test_non_numeric_target_value_is_rejected(self, env):
        result = env.run(
            [
                {
                    "name": "M1",
                    "metric_definition": "Availability",
                    "status": "active",
                    "target_value": "not-a-number",
                    "filtering_labels": "L1",
                    "owner": "wizard-admin@tests.com",
                }
            ],
            folder_id=env.domain.id,
        )
        assert result.created == 0
        assert result.failed == 1, _errors(result)

    def test_name_exceeding_max_length_is_rejected(self, env):
        result = env.run(
            [
                {
                    "name": "x" * 201,
                    "metric_definition": "Availability",
                    "status": "active",
                    "filtering_labels": "L1",
                    "owner": "wizard-admin@tests.com",
                }
            ],
            folder_id=env.domain.id,
        )
        assert result.created == 0
        assert result.failed == 1, _errors(result)


# --------------------------------------------------------------------------- #
# Finding #1 - optional fields must be optional  (expected to FAIL on current code)
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
class TestOptionalFields:
    def test_minimal_record_creates_instance(self, env):
        """Only the genuinely-required fields (name, metric_definition, status)."""
        result = env.run(
            [
                {
                    "name": "Minimal Metric",
                    "metric_definition": "Availability",
                    "status": "active",
                }
            ],
            folder_id=env.domain.id,
        )
        assert result.failed == 0, _errors(result)
        assert result.created == 1
        assert MetricInstance.objects.filter(name="Minimal Metric").exists()

    def test_owner_is_optional(self, env):
        """owner is blank=True on the model and documented as optional."""
        result = env.run(
            [
                {
                    "name": "No Owner Metric",
                    "metric_definition": "Availability",
                    "status": "active",
                    "filtering_labels": "L1",
                }
            ],
            folder_id=env.domain.id,
        )
        assert result.failed == 0, _errors(result)
        assert result.created == 1

    def test_filtering_labels_is_optional(self, env):
        """filtering_labels is documented as optional."""
        result = env.run(
            [
                {
                    "name": "No Labels Metric",
                    "metric_definition": "Availability",
                    "status": "active",
                    "owner": "wizard-admin@tests.com",
                }
            ],
            folder_id=env.domain.id,
        )
        assert result.failed == 0, _errors(result)
        assert result.created == 1

    def test_empty_status_falls_back_to_model_default(self, env):
        """An empty status cell should use the model default ('draft'), not error."""
        result = env.run(
            [
                {
                    "name": "Default Status Metric",
                    "metric_definition": "Availability",
                    "status": "",
                }
            ],
            folder_id=env.domain.id,
        )
        assert result.failed == 0, _errors(result)
        assert result.created == 1
        mi = MetricInstance.objects.get(name="Default Status Metric")
        assert mi.status == MetricInstance.Status.DRAFT


# --------------------------------------------------------------------------- #
# Finding #2 - imported instances must respect the selected folder
# (expected to FAIL on current code: they land in the root folder)
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
class TestFolderScoping:
    def test_instance_created_in_selected_domain(self, env):
        # owner + labels supplied so finding #1 does not mask this assertion.
        result = env.run(
            [
                {
                    "name": "Scoped Metric",
                    "metric_definition": "Availability",
                    "status": "active",
                    "filtering_labels": "L1",
                    "owner": "wizard-admin@tests.com",
                }
            ],
            folder_id=env.domain.id,
        )
        assert result.created == 1, _errors(result)
        mi = MetricInstance.objects.get(name="Scoped Metric")
        assert mi.folder_id == env.domain.id, (
            f"expected folder {env.domain.id} (selected domain), "
            f"got {mi.folder_id} (root={Folder.get_root_folder().id})"
        )


# --------------------------------------------------------------------------- #
# Owner resolution
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
class TestOwnerResolution:
    def test_owner_resolves_user_email(self, env):
        """Nominal: user-email owners resolve. Expected to PASS on current code."""
        User.objects.create_user("owner.user@tests.com", is_published=True)
        result = env.run(
            [
                {
                    "name": "User Owned Metric",
                    "metric_definition": "Availability",
                    "status": "active",
                    "filtering_labels": "L1",
                    "owner": "owner.user@tests.com",
                }
            ],
            folder_id=env.domain.id,
        )
        assert result.created == 1, _errors(result)
        mi = MetricInstance.objects.get(name="User Owned Metric")
        owner_emails = [a.user.email for a in mi.owner.all() if a.user]
        assert "owner.user@tests.com" in owner_emails

    def test_owner_resolves_team_names(self, env):
        """
        Finding #3: every team should be resolvable as an owner.

        Two teams exist; importing one record per team must create both with the
        correct team actor. Under the current bug only one team actor survives in
        the viewable-id cache, so at least one record fails to resolve its owner.
        """
        team_a = Team.objects.create(name="Security Team")
        team_b = Team.objects.create(name="Ops Team")

        result = env.run(
            [
                {
                    "name": "Team A Metric",
                    "metric_definition": "Availability",
                    "status": "active",
                    "filtering_labels": "L1",
                    "owner": "Security Team",
                },
                {
                    "name": "Team B Metric",
                    "metric_definition": "Availability",
                    "status": "active",
                    "filtering_labels": "L2",
                    "owner": "Ops Team",
                },
            ],
            folder_id=env.domain.id,
            on_conflict=ConflictMode.SKIP,  # don't stop on first failure
        )
        assert result.created == 2, _errors(result)

        mi_a = MetricInstance.objects.get(name="Team A Metric")
        mi_b = MetricInstance.objects.get(name="Team B Metric")
        assert team_a.actor.id in {a.id for a in mi_a.owner.all()}
        assert team_b.actor.id in {a.id for a in mi_b.owner.all()}


# --------------------------------------------------------------------------- #
# Full nominal happy path (every field provided) - documents intended behaviour
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
class TestFullHappyPath:
    def test_full_valid_record(self, env):
        result = env.run(
            [
                {
                    "ref_id": "MI-001",
                    "name": "Full Metric",
                    "description": "A complete record",
                    "metric_definition": "Availability",
                    "status": "active",
                    "collection_frequency": "daily",
                    "target_value": "99.9",
                    "filtering_labels": "Gold|Silver",
                    "owner": "wizard-admin@tests.com",
                }
            ],
            folder_id=env.domain.id,
        )
        assert result.failed == 0, _errors(result)
        assert result.created == 1
        mi = MetricInstance.objects.get(name="Full Metric")
        assert mi.status == MetricInstance.Status.ACTIVE
        assert mi.collection_frequency == MetricInstance.Frequency.DAILY
        assert mi.target_value == pytest.approx(99.9)
        assert mi.metric_definition_id == env.metric_def.id
        assert mi.owner.count() == 1
        assert mi.filtering_labels.count() == 2
