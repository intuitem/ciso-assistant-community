import pytest
from django.db.models import BooleanField, ExpressionWrapper, OuterRef

from core.models import (
    ComplianceAssessment,
    Framework,
    Perimeter,
    Question,
    QuestionChoice,
    RequirementAssessment,
    RequirementNode,
)
from core.serializers import ComplianceAssessmentWriteSerializer
from iam.models import Folder


@pytest.fixture
def setup():
    folder = Folder.get_root_folder()
    perimeter = Perimeter.objects.create(name="p-scale", folder=folder)
    fw = Framework.objects.create(
        name="FW scale",
        urn="urn:test:fw-scale",
        min_score=0,
        max_score=100,
        folder=folder,
    )
    rn = RequirementNode.objects.create(
        urn="urn:test:rn-scale", framework=fw, assessable=True, folder=folder
    )
    ca = ComplianceAssessment.objects.create(
        name="CA scale", framework=fw, folder=folder, perimeter=perimeter
    )
    ra = RequirementAssessment.objects.create(
        compliance_assessment=ca, requirement=rn, folder=folder
    )
    return {"fw": fw, "rn": rn, "ca": ca, "ra": ra, "folder": folder}


def _update(ca, data, confirm=True):
    if confirm:
        data = {"confirm_rescale": True, **data}
    serializer = ComplianceAssessmentWriteSerializer(
        instance=ca, data=data, partial=True
    )
    valid = serializer.is_valid()
    return serializer, valid


def _levels(*scores):
    return [{"score": s, "translations": {"fr": {"name": f"n{s}"}}} for s in scores]


@pytest.mark.django_db
class TestScoreScalePreset:
    def test_new_audit_inherits_framework_scale(self, setup):
        ca = setup["ca"]
        assert (ca.min_score, ca.max_score, ca.score_scale_preset) == (0, 100, None)

    def test_preset_sets_range(self, setup):
        serializer, valid = _update(setup["ca"], {"score_scale_preset": "0-5"})
        assert valid, serializer.errors
        ca = serializer.save()
        assert (ca.min_score, ca.max_score, ca.score_scale_preset) == (0, 5, "0-5")

    def test_preset_rejects_mismatched_range(self, setup):
        serializer, valid = _update(
            setup["ca"], {"score_scale_preset": "0-5", "max_score": 4}
        )
        assert not valid
        assert "max_score" in serializer.errors

    def test_unknown_preset_rejected(self, setup):
        _, valid = _update(setup["ca"], {"score_scale_preset": "2-7"})
        assert not valid

    def test_custom_range_must_increase(self, setup):
        serializer, valid = _update(setup["ca"], {"min_score": 3, "max_score": 3})
        assert not valid
        assert "max_score" in serializer.errors

    def test_min_and_max_go_together(self, setup):
        _, valid = _update(setup["ca"], {"min_score": None})
        assert not valid

    def test_custom_range_clears_stale_preset(self, setup):
        ca = setup["ca"]
        serializer, _ = _update(ca, {"score_scale_preset": "0-5"})
        serializer.save()
        serializer, valid = _update(ca, {"min_score": 0, "max_score": 3})
        assert valid, serializer.errors
        assert serializer.save().score_scale_preset is None

    def test_back_to_framework_default(self, setup):
        ca = setup["ca"]
        _update(ca, {"score_scale_preset": "0-5"})[0].save()
        serializer, valid = _update(
            ca,
            {
                "score_scale_preset": None,
                "min_score": None,
                "max_score": None,
                "scores_definition": None,
            },
        )
        assert valid, serializer.errors
        ca = serializer.save()
        assert (ca.min_score, ca.max_score, ca.score_scale_preset) == (0, 100, None)

    def test_levels_outside_range_rejected(self, setup):
        serializer, valid = _update(
            setup["ca"],
            {"score_scale_preset": "1-4", "scores_definition": _levels(0, 1)},
        )
        assert not valid
        assert "scores_definition" in serializer.errors

    def test_translations_are_stored(self, setup):
        serializer, valid = _update(
            setup["ca"],
            {"score_scale_preset": "0-5", "scores_definition": _levels(3)},
        )
        assert valid, serializer.errors
        ca = serializer.save()
        assert ca.scores_definition[0]["translations"]["fr"]["name"] == "n3"


@pytest.mark.django_db
class TestScoredRequirements:
    def _score(self, setup, value):
        setup["ra"].is_scored = True
        setup["ra"].score = value
        setup["ra"].save()

    def test_scored_requirements_are_converted(self, setup):
        self._score(setup, 40)
        serializer, valid = _update(setup["ca"], {"score_scale_preset": "0-5"})
        assert valid, serializer.errors
        serializer.save()
        setup["ra"].refresh_from_db()
        assert (setup["ra"].score, setup["ra"].is_scored) == (2, True)

    def test_scored_requirements_are_counted_separately(self, setup):
        from core.serializers import ScoreRescaleConfirmationRequired

        self._score(setup, 40)
        with pytest.raises(ScoreRescaleConfirmationRequired) as exc:
            _update(setup["ca"], {"score_scale_preset": "0-5"}, confirm=False)
        impact = exc.value.impact
        assert (impact["scored"], impact["scores"]) == (1, 0)

    def test_todays_metric_uses_converted_scores(self, setup):
        from core.models import HistoricalMetric

        self._score(setup, 80)
        _update(setup["ca"], {"score_scale_preset": "1-5"})[0].save()
        metric = HistoricalMetric.objects.filter(object_id=setup["ca"].id).latest(
            "date"
        )
        assert metric.data["reqs"]["score"] == pytest.approx(4)

    def test_wording_editable_once_scored(self, setup):
        ca = setup["ca"]
        _update(ca, {"score_scale_preset": "0-5"})[0].save()
        self._score(setup, 4)
        serializer, valid = _update(
            ca, {"score_scale_preset": "0-5", "scores_definition": _levels(4)}
        )
        assert valid, serializer.errors


@pytest.mark.django_db
class TestScaleBoundFramework:
    def _add_scored_question(self, setup):
        question = Question.objects.create(
            requirement_node=setup["rn"],
            urn="urn:test:q-scale",
            ref_id="Q",
            text="Q",
            type=Question.Type.UNIQUE_CHOICE,
            order=0,
            weight=1,
            folder=setup["folder"],
        )
        QuestionChoice.objects.create(
            question=question,
            urn="urn:test:c-scale",
            value="ok",
            add_score=30,
            order=0,
            folder=setup["folder"],
        )

    def _annotated(self, fw):
        return (
            Framework.objects.filter(pk=fw.pk)
            .annotate(
                scale_bound_flag=ExpressionWrapper(
                    Framework.scale_bound_q(OuterRef("pk")),
                    output_field=BooleanField(),
                )
            )
            .get()
            .scale_bound_flag
        )

    def test_plain_framework_not_bound(self, setup):
        assert setup["fw"].is_scale_bound is False
        assert self._annotated(setup["fw"]) is False

    def test_add_score_binds_scale(self, setup):
        self._add_scored_question(setup)
        assert setup["fw"].is_scale_bound is True
        assert self._annotated(setup["fw"]) is True

    def test_node_override_binds_scale(self, setup):
        setup["rn"].min_score = 1
        setup["rn"].max_score = 3
        setup["rn"].save()
        assert setup["fw"].is_scale_bound is True
        assert self._annotated(setup["fw"]) is True

    def test_bound_framework_rejects_range_change(self, setup):
        self._add_scored_question(setup)
        serializer, valid = _update(setup["ca"], {"score_scale_preset": "0-5"})
        assert not valid
        assert "score_scale_preset" in serializer.errors

    def test_bound_framework_accepts_same_range(self, setup):
        self._add_scored_question(setup)
        serializer, valid = _update(setup["ca"], {"score_scale_preset": "0-100"})
        assert valid, serializer.errors


@pytest.mark.django_db
class TestScaleLevelExpansion:
    def test_preset_expands_to_full_range(self, setup):
        ca = setup["ca"]
        _update(ca, {"score_scale_preset": "0-5", "scores_definition": _levels(3)})[
            0
        ].save()
        levels = ca.get_scale_levels()
        assert [lvl["score"] for lvl in levels] == [0, 1, 2, 3, 4, 5]
        assert all(lvl["preset"] == "0-5" for lvl in levels)
        assert levels[3]["translations"]["fr"]["name"] == "n3"
        assert "translations" not in levels[0]

    def test_requirement_resolution_uses_expansion(self, setup):
        ca = setup["ca"]
        _update(ca, {"score_scale_preset": "1-4"})[0].save()
        setup["ra"].refresh_from_db()
        resolved = setup["ra"].get_resolved_scoring()
        assert (resolved["min_score"], resolved["max_score"]) == (1, 4)
        assert [lvl["score"] for lvl in resolved["scores_definition"]] == [1, 2, 3, 4]

    def test_percentage_preset_has_no_levels(self, setup):
        ca = setup["ca"]
        _update(ca, {"score_scale_preset": "0-100"})[0].save()
        assert not ca.get_scale_levels()

    def test_custom_scale_returned_as_stored(self, setup):
        ca = setup["ca"]
        _update(
            ca, {"min_score": 0, "max_score": 2, "scores_definition": _levels(0, 2)}
        )[0].save()
        assert [lvl["score"] for lvl in ca.get_scale_levels()] == [0, 2]


def _set_instance_default(value):
    from global_settings.models import GlobalSettings

    general, _ = GlobalSettings.objects.get_or_create(
        name="general", defaults={"value": {}}
    )
    general.value = {**(general.value or {}), "default_score_scale": value}
    general.save()
    return general


def _new_audit(setup, framework=None, **fields):
    return ComplianceAssessment.objects.create(
        name="CA default",
        framework=framework or setup["fw"],
        folder=setup["folder"],
        **fields,
    )


@pytest.mark.django_db
class TestInstanceDefaultScale:
    def test_preset_default_applies_to_undeclared_framework(self, setup):
        _set_instance_default(
            {"score_scale_preset": "1-4", "min_score": 1, "max_score": 4}
        )
        ca = _new_audit(setup)
        assert (ca.min_score, ca.max_score, ca.score_scale_preset) == (1, 4, "1-4")

    def test_custom_default_is_copied(self, setup):
        levels = [{"score": 1, "name": "Low", "translations": {"nl": {"name": "Laag"}}}]
        _set_instance_default(
            {
                "score_scale_preset": None,
                "min_score": 1,
                "max_score": 3,
                "scores_definition": levels,
            }
        )
        ca = _new_audit(setup)
        assert (ca.min_score, ca.max_score, ca.score_scale_preset) == (1, 3, None)
        assert ca.scores_definition == levels
        levels[0]["name"] = "changed"
        assert ca.scores_definition[0]["name"] == "Low"

    def test_declared_framework_keeps_its_scale(self, setup):
        _set_instance_default(
            {"score_scale_preset": "1-4", "min_score": 1, "max_score": 4}
        )
        fw = Framework.objects.create(
            name="FW declared",
            urn="urn:test:fw-declared",
            min_score=0,
            max_score=5,
            folder=setup["folder"],
        )
        ca = _new_audit(setup, framework=fw)
        assert (ca.min_score, ca.max_score, ca.score_scale_preset) == (0, 5, None)

    def test_bound_framework_keeps_its_scale(self, setup):
        _set_instance_default(
            {"score_scale_preset": "1-4", "min_score": 1, "max_score": 4}
        )
        TestScaleBoundFramework()._add_scored_question(setup)
        ca = _new_audit(setup)
        assert (ca.min_score, ca.max_score) == (0, 100)

    def test_existing_audits_untouched(self, setup):
        _set_instance_default(
            {"score_scale_preset": "1-4", "min_score": 1, "max_score": 4}
        )
        setup["ca"].save()
        setup["ca"].refresh_from_db()
        assert (setup["ca"].min_score, setup["ca"].max_score) == (0, 100)

    def test_default_chip_resolution(self, setup):
        _set_instance_default(
            {"score_scale_preset": "0-5", "min_score": 0, "max_score": 5}
        )
        scale = setup["fw"].default_audit_scale()
        assert scale["source"] == "instance"
        assert (scale["min_score"], scale["max_score"]) == (0, 5)

    def test_back_to_default_on_edit_uses_instance_default(self, setup):
        _set_instance_default(
            {"score_scale_preset": "1-4", "min_score": 1, "max_score": 4}
        )
        serializer, valid = _update(
            setup["ca"],
            {
                "score_scale_preset": None,
                "min_score": None,
                "max_score": None,
                "scores_definition": None,
            },
        )
        assert valid, serializer.errors
        ca = serializer.save()
        assert (ca.min_score, ca.max_score, ca.score_scale_preset) == (1, 4, "1-4")


@pytest.mark.django_db
class TestDefaultScoreScaleSetting:
    def _update(self, value):
        from global_settings.serializers import GeneralSettingsSerializer

        general = _set_instance_default(None)
        GeneralSettingsSerializer().update(
            general, {"value": {"default_score_scale": value}}
        )
        general.refresh_from_db()
        return general.value["default_score_scale"]

    def test_preset_normalized(self):
        stored = self._update({"score_scale_preset": "0-5"})
        assert stored == {
            "score_scale_preset": "0-5",
            "min_score": 0,
            "max_score": 5,
            "scores_definition": [],
        }

    def test_clear(self):
        assert self._update(None) is None

    @pytest.mark.parametrize(
        "value",
        [
            {"score_scale_preset": "9-9"},
            {"min_score": 3, "max_score": 3},
            {"min_score": 1},
            {"min_score": 1, "max_score": 4, "scores_definition": [{"score": 7}]},
            {},
            "0-5",
        ],
    )
    def test_invalid_rejected(self, value):
        from rest_framework.exceptions import ValidationError

        with pytest.raises(ValidationError):
            self._update(value)


@pytest.mark.django_db
class TestLabelsWithoutRange:
    def test_create_keeps_labels_on_default_range(self, setup):
        levels = [{"score": 50, "translations": {"fr": {"name": "Moyen"}}}]
        serializer = ComplianceAssessmentWriteSerializer(
            data={
                "name": "CA labels only",
                "folder": str(setup["folder"].id),
                "framework": str(setup["fw"].id),
                "scores_definition": levels,
            }
        )
        assert serializer.is_valid(), serializer.errors
        ca = serializer.save()
        assert (ca.min_score, ca.max_score) == (0, 100)
        assert ca.scores_definition == levels

    def test_reset_without_labels_drops_old_labels(self, setup):
        ca = setup["ca"]
        _update(
            ca, {"min_score": 1, "max_score": 3, "scores_definition": _levels(1, 3)}
        )[0].save()
        serializer, valid = _update(ca, {"min_score": None, "max_score": None})
        assert valid, serializer.errors
        ca = serializer.save()
        assert (ca.min_score, ca.max_score) == (0, 100)
        assert ca.scores_definition is None


@pytest.mark.django_db
class TestWrappedFrameworkScale:
    """Loaded frameworks store {"scale": [...]}, not a bare list."""

    def test_wrapped_scale_flows_to_audit_and_api(self, setup):
        from core.serializers import FrameworkReadSerializer

        wrapped = {
            "scale": [
                {"score": s, "name": f"L{s}", "translations": {"fr": {"name": f"N{s}"}}}
                for s in range(1, 5)
            ]
        }
        fw = Framework.objects.create(
            name="FW wrapped",
            urn="urn:test:fw-wrapped",
            min_score=1,
            max_score=4,
            scores_definition=wrapped,
            folder=setup["folder"],
        )
        assert fw.declares_scale()
        ca = _new_audit(setup, framework=fw)
        assert ca.scores_definition == wrapped
        assert [lvl["score"] for lvl in ca.get_scale_levels()] == [1, 2, 3, 4]
        default = FrameworkReadSerializer(fw).data["audit_default_scale"]
        assert default["source"] == "framework"
        assert [lvl["score"] for lvl in default["scores_definition"]] == [1, 2, 3, 4]


class TestRescaleScore:
    @pytest.mark.parametrize(
        "value, expected",
        [(0, 1), (50, 3), (100, 5), (75, 4), (-10, 1), (150, 5)],
    )
    def test_percentage_to_one_five(self, value, expected):
        from core.models import rescale_score

        assert rescale_score(value, (0, 100), (1, 5)) == expected

    def test_float_target(self):
        from core.models import rescale_score

        assert rescale_score(80, (0, 100), (0, 5), integer=False) == 4.0


@pytest.mark.django_db
class TestStaleScoresFollowRangeChange:
    def test_unscored_values_are_converted(self, setup):
        ra = setup["ra"]
        ra.score, ra.documentation_score, ra.is_scored = 75, 40, False
        ra.save()
        serializer, valid = _update(setup["ca"], {"score_scale_preset": "0-5"})
        assert valid, serializer.errors
        serializer.save()
        ra.refresh_from_db()
        assert (ra.score, ra.documentation_score, ra.is_scored) == (4, 2, False)

    def test_target_follows_unless_given(self, setup):
        ca = setup["ca"]
        ca.target_score = 80
        ca.save()
        serializer, valid = _update(ca, {"score_scale_preset": "0-5"})
        assert valid, serializer.errors
        assert serializer.save().target_score == 4.0

        serializer, valid = _update(
            ca, {"score_scale_preset": "1-4", "target_score": 2}
        )
        assert valid, serializer.errors
        assert serializer.save().target_score == 2

    def test_reset_to_default_converts_back(self, setup):
        ca, ra = setup["ca"], setup["ra"]
        _update(ca, {"score_scale_preset": "1-5"})[0].save()
        ra.score = 5
        ra.save()
        serializer, valid = _update(
            ca, {"score_scale_preset": None, "min_score": None, "max_score": None}
        )
        assert valid, serializer.errors
        serializer.save()
        ra.refresh_from_db()
        assert ra.score == 100

    def test_wording_change_leaves_scores_alone(self, setup):
        ca, ra = setup["ca"], setup["ra"]
        _update(ca, {"score_scale_preset": "0-5"})[0].save()
        ra.score = 3
        ra.save()
        serializer, valid = _update(
            ca, {"score_scale_preset": "0-5", "scores_definition": _levels(3)}
        )
        assert valid, serializer.errors
        serializer.save()
        ra.refresh_from_db()
        assert ra.score == 3


@pytest.mark.django_db
class TestTargetWithFullFormPayload:
    """The edit form PUTs every field, target_score included."""

    def test_unchanged_target_is_converted_down(self, setup):
        ca = setup["ca"]
        ca.target_score = 80
        ca.save()
        serializer, valid = _update(
            ca, {"score_scale_preset": "1-5", "target_score": 80}
        )
        assert valid, serializer.errors
        assert serializer.save().target_score == 4.2

    def test_unchanged_target_is_converted_up(self, setup):
        ca = setup["ca"]
        _update(ca, {"score_scale_preset": "1-5"})[0].save()
        ca.target_score = 4
        ca.save()
        serializer, valid = _update(
            ca,
            {
                "score_scale_preset": None,
                "min_score": 0,
                "max_score": 100,
                "target_score": 4,
            },
        )
        assert valid, serializer.errors
        assert serializer.save().target_score == 75.0

    def test_edited_target_is_checked_against_new_range(self, setup):
        ca = setup["ca"]
        ca.target_score = 80
        ca.save()
        serializer, valid = _update(
            ca, {"score_scale_preset": "1-5", "target_score": 9}
        )
        assert not valid
        assert "target_score" in serializer.errors

    def test_target_checked_against_default_range(self, setup):
        ca = setup["ca"]
        _update(ca, {"score_scale_preset": "0-5"})[0].save()
        serializer, valid = _update(
            ca,
            {
                "score_scale_preset": None,
                "min_score": None,
                "max_score": None,
                "target_score": 150,
            },
        )
        assert not valid
        assert "target_score" in serializer.errors


@pytest.mark.django_db
class TestRescaleConfirmation:
    def _impact(self, exc):
        return exc.impact

    def test_conversion_needs_confirmation(self, setup):
        from core.serializers import ScoreRescaleConfirmationRequired

        ca, ra = setup["ca"], setup["ra"]
        ra.score, ra.documentation_score = 75, 40
        ra.save()
        ca.target_score = 80
        ca.save()
        with pytest.raises(ScoreRescaleConfirmationRequired) as exc:
            _update(
                ca, {"score_scale_preset": "1-5", "target_score": 80}, confirm=False
            )
        assert exc.value.status_code == 409
        assert self._impact(exc.value) == {
            "from": [0, 100],
            "to": [1, 5],
            "scored": 0,
            "scores": 1,
            "documentation_scores": 1,
            "target": [80.0, 4.2],
        }
        ca.refresh_from_db()
        ra.refresh_from_db()
        assert (ca.min_score, ca.max_score, ra.score) == (0, 100, 75)

    def test_nothing_to_convert_needs_no_confirmation(self, setup):
        serializer, valid = _update(
            setup["ca"], {"score_scale_preset": "1-5"}, confirm=False
        )
        assert valid, serializer.errors
        assert serializer.save().max_score == 5

    def test_wording_change_needs_no_confirmation(self, setup):
        ca, ra = setup["ca"], setup["ra"]
        ra.score = 50
        ra.save()
        serializer, valid = _update(
            ca, {"scores_definition": [{"score": 50, "name": "Half"}]}, confirm=False
        )
        assert valid, serializer.errors

    def test_edited_target_alone_needs_no_confirmation(self, setup):
        ca = setup["ca"]
        ca.target_score = 80
        ca.save()
        serializer, valid = _update(
            ca, {"score_scale_preset": "1-5", "target_score": 3}, confirm=False
        )
        assert valid, serializer.errors
        assert serializer.save().target_score == 3

    def test_api_returns_409(self, setup, client):
        from rest_framework.test import APIClient
        from iam.models import User

        admin = User.objects.create_superuser(
            email="scale-admin@test.local", password="x"
        )
        api = APIClient()
        api.force_authenticate(admin)
        setup["ra"].score = 60
        setup["ra"].save()
        url = f"/api/compliance-assessments/{setup['ca'].id}/"
        response = api.patch(url, {"score_scale_preset": "0-5"}, format="json")
        assert response.status_code == 409
        body = response.json()
        assert body["confirm_rescale"] == ["scoreScaleConfirmRequired"]
        assert body["rescale_impact"]["scored"] == "0"
        assert body["rescale_impact"]["scores"] == "1"
        response = api.patch(
            url, {"score_scale_preset": "0-5", "confirm_rescale": True}, format="json"
        )
        assert response.status_code == 200, response.json()
        setup["ra"].refresh_from_db()
        assert setup["ra"].score == 3


_LIB = """
urn: urn:intuitem:test:library:scale-update
locale: en
ref_id: SCALE-UPDATE
name: Scale update
description: Scale update
copyright: Test
version: {version}
publication_date: 2026-09-26
provider: test
packager: test
objects:
  framework:
    urn: urn:intuitem:test:framework:scale-update
    ref_id: SCALE-UPDATE
    name: Scale update
    description: Scale update
{scale}    requirement_nodes:
    - urn: urn:intuitem:test:req_node:scale-update:req-1
      assessable: true
      depth: 1
      ref_id: REQ-1
      name: Requirement 1
""".lstrip()

_SCALE_V2 = """    min_score: 1
    max_score: 4
    scores_definition:
    - score: 1
      name: Low
      description: Low level
    - score: 2
      name: Medium
    - score: 3
      name: High
    - score: 4
      name: Very high
"""


@pytest.mark.django_db
class TestLibraryUpdateWithPreset:
    def test_preset_follows_framework_scale_change(self):
        from core.models import LoadedLibrary, StoredLibrary

        folder = Folder.get_root_folder()
        stored, _ = StoredLibrary.store_library_content(
            _LIB.format(version=1, scale="").encode("utf-8")
        )
        stored.load()
        fw = Framework.objects.get(urn="urn:intuitem:test:framework:scale-update")
        preset_ca = ComplianceAssessment.objects.create(
            name="On preset",
            framework=fw,
            folder=folder,
            score_scale_preset="0-100",
            min_score=0,
            max_score=100,
            scores_definition=[],
        )
        custom_ca = ComplianceAssessment.objects.create(
            name="Custom",
            framework=fw,
            folder=folder,
            min_score=1,
            max_score=3,
            scores_definition=[{"score": 1, "name": "Mine"}],
        )

        StoredLibrary.store_library_content(
            _LIB.format(version=2, scale=_SCALE_V2).encode("utf-8")
        )
        error = LoadedLibrary.objects.get(urn=stored.urn).update(strategy="clamp")
        assert error is None

        preset_ca.refresh_from_db()
        assert (preset_ca.min_score, preset_ca.max_score) == (1, 4)
        assert preset_ca.score_scale_preset is None
        levels = preset_ca.get_scale_levels()
        assert [lvl["name"] for lvl in levels] == ["Low", "Medium", "High", "Very high"]
        assert levels[0]["description"] == "Low level"

        custom_ca.refresh_from_db()
        assert (custom_ca.min_score, custom_ca.max_score) == (1, 3)
        assert custom_ca.scores_definition == [{"score": 1, "name": "Mine"}]


@pytest.mark.django_db
class TestRescaleReevaluatesOutcomes:
    def test_outcomes_evaluated_once_after_commit(
        self, setup, django_capture_on_commit_callbacks, monkeypatch
    ):
        calls = []
        monkeypatch.setattr(
            "core.cel_service.evaluate_outcomes", lambda ca: calls.append(ca.pk)
        )
        ca, ra = setup["ca"], setup["ra"]
        ra.is_scored, ra.score = True, 80
        ra.save()
        with django_capture_on_commit_callbacks(execute=True):
            _update(ca, {"score_scale_preset": "1-5"})[0].save()
        assert calls.count(ca.pk) == 1
        ra.refresh_from_db()
        assert ra.score == 4


@pytest.mark.django_db
class TestUnlockWithScaleChange:
    def _locked_scored(self, setup):
        ca, ra = setup["ca"], setup["ra"]
        ra.is_scored, ra.score = True, 80
        ra.save()
        ca.is_locked = True
        ca.save()
        return ca, ra

    def test_unlock_and_rescale_needs_confirmation(self, setup):
        from core.serializers import ScoreRescaleConfirmationRequired

        ca, _ = self._locked_scored(setup)
        with pytest.raises(ScoreRescaleConfirmationRequired):
            _update(
                ca, {"is_locked": False, "score_scale_preset": "1-5"}, confirm=False
            )

    def test_unlock_and_rescale_converts(self, setup):
        ca, ra = self._locked_scored(setup)
        serializer, valid = _update(
            ca, {"is_locked": False, "score_scale_preset": "1-5"}
        )
        assert valid, serializer.errors
        ca = serializer.save()
        ra.refresh_from_db()
        assert (ca.is_locked, ca.min_score, ca.max_score, ra.score) == (False, 1, 5, 4)

    def test_unlock_still_validates_target(self, setup):
        ca, _ = self._locked_scored(setup)
        serializer, valid = _update(
            ca, {"is_locked": False, "score_scale_preset": "1-5", "target_score": 9}
        )
        assert not valid
        assert "target_score" in serializer.errors

    def test_locked_audit_still_refuses_changes(self, setup):
        ca, _ = self._locked_scored(setup)
        serializer, valid = _update(ca, {"score_scale_preset": "1-5"})
        assert not valid


@pytest.mark.django_db
class TestBaselineCopy:
    def _api(self):
        from iam.models import User
        from rest_framework.test import APIClient

        admin = User.objects.create_superuser(
            email="baseline-admin@test.local", password="x"
        )
        api = APIClient()
        api.force_authenticate(admin)
        return api

    def _baseline(self, setup):
        ra = setup["ra"]
        ra.is_scored, ra.score, ra.documentation_score = True, 80, 40
        ra.save()
        return setup["ca"]

    def _create(self, setup, **extra):
        response = self._api().post(
            "/api/compliance-assessments/",
            {
                "name": "From baseline",
                "folder": str(setup["folder"].id),
                "framework": str(setup["fw"].id),
                "baseline": str(setup["ca"].id),
                **extra,
            },
            format="json",
        )
        assert response.status_code == 201, response.json()
        new = ComplianceAssessment.objects.get(id=response.json()["id"])
        ra = new.requirement_assessments.get(requirement=setup["rn"])
        return new, ra

    def test_copy_keeps_baseline_scale_over_instance_default(self, setup):
        self._baseline(setup)
        _set_instance_default(
            {"score_scale_preset": "1-5", "min_score": 1, "max_score": 5}
        )
        new, ra = self._create(setup)
        assert (new.min_score, new.max_score, new.score_scale_preset) == (0, 100, None)
        assert (ra.score, ra.documentation_score) == (80, 40)

    def test_explicit_scale_converts_copied_scores(self, setup):
        self._baseline(setup)
        new, ra = self._create(setup, score_scale_preset="1-5")
        assert (new.min_score, new.max_score) == (1, 5)
        assert (ra.score, ra.documentation_score) == (4, 3)


@pytest.mark.django_db
class TestSameFrameworkMergeConversion:
    def test_scores_follow_target_scale(self, setup):
        from core.mappings.merge import rescaled_to_target

        target = ComplianceAssessment.objects.create(
            name="Target",
            framework=setup["fw"],
            folder=setup["folder"],
            score_scale_preset="1-5",
            min_score=1,
            max_score=5,
        )
        results = {
            "min_score": 0,
            "max_score": 100,
            "requirement_assessments": {
                setup["rn"].urn: {
                    "score": 80,
                    "documentation_score": 40,
                    "result": "compliant",
                }
            },
        }
        converted = rescaled_to_target(results, target)
        ra = converted["requirement_assessments"][setup["rn"].urn]
        assert (ra["score"], ra["documentation_score"], ra["result"]) == (
            4,
            3,
            "compliant",
        )
        assert results["requirement_assessments"][setup["rn"].urn]["score"] == 80

    def test_same_scale_is_untouched(self, setup):
        from core.mappings.merge import rescaled_to_target

        results = {"min_score": 0, "max_score": 100, "requirement_assessments": {}}
        assert rescaled_to_target(results, setup["ca"]) is results


@pytest.mark.django_db
class TestWrappedDefinitionValidation:
    def test_wrapped_levels_are_range_checked(self, setup):
        serializer, valid = _update(
            setup["ca"],
            {
                "score_scale_preset": "1-5",
                "scores_definition": {"scale": [{"score": 80}]},
            },
        )
        assert not valid
        assert "scores_definition" in serializer.errors

    def test_wrapped_levels_in_range_pass(self, setup):
        serializer, valid = _update(
            setup["ca"],
            {
                "score_scale_preset": "1-5",
                "scores_definition": {"scale": [{"score": 3}]},
            },
        )
        assert valid, serializer.errors


_LIB_TWO_NODES = """
urn: urn:intuitem:test:library:scale-update-2
locale: en
ref_id: SCALE-UPDATE-2
name: Scale update 2
description: Scale update 2
copyright: Test
version: {version}
publication_date: 2026-09-26
provider: test
packager: test
objects:
  framework:
    urn: urn:intuitem:test:framework:scale-update-2
    ref_id: SCALE-UPDATE-2
    name: Scale update 2
    description: Scale update 2
{scale}    requirement_nodes:
    - urn: urn:intuitem:test:req_node:scale-update-2:req-1
      assessable: true
      depth: 1
      ref_id: REQ-1
      name: Requirement 1
    - urn: urn:intuitem:test:req_node:scale-update-2:req-2
      assessable: true
      depth: 1
      ref_id: REQ-2
      name: Requirement 2
""".lstrip()


@pytest.mark.django_db
class TestLibraryUpdateConvertsAllStoredValues:
    def test_stale_and_documentation_scores_follow(
        self, django_capture_on_commit_callbacks, monkeypatch
    ):
        from core.models import LoadedLibrary, StoredLibrary

        folder = Folder.get_root_folder()
        stored, _ = StoredLibrary.store_library_content(
            _LIB_TWO_NODES.format(version=1, scale="").encode("utf-8")
        )
        stored.load()
        fw = Framework.objects.get(urn="urn:intuitem:test:framework:scale-update-2")
        ca = ComplianceAssessment.objects.create(
            name="Lib", framework=fw, folder=folder
        )
        ca.create_requirement_assessments()
        scored, stale = sorted(
            ca.requirement_assessments.all(), key=lambda r: r.requirement.ref_id
        )
        # Queryset updates: RequirementAssessment.save() would queue an outcome
        # evaluation for this audit and mask the one under test.
        RequirementAssessment.objects.filter(pk=scored.pk).update(
            is_scored=True, score=80, documentation_score=40
        )
        RequirementAssessment.objects.filter(pk=stale.pk).update(
            is_scored=False, score=60
        )

        calls = []
        monkeypatch.setattr(
            "core.cel_service.evaluate_outcomes", lambda audit: calls.append(audit.pk)
        )
        StoredLibrary.store_library_content(
            _LIB_TWO_NODES.format(
                version=2, scale="    min_score: 1\n    max_score: 4\n"
            ).encode("utf-8")
        )
        with django_capture_on_commit_callbacks(execute=True):
            error = LoadedLibrary.objects.get(urn=stored.urn).update(
                strategy="rule_of_three"
            )
        assert error is None

        scored.refresh_from_db()
        stale.refresh_from_db()
        assert (scored.score, scored.documentation_score, scored.is_scored) == (
            3,
            2,
            True,
        )
        assert (stale.score, stale.is_scored) == (3, False)
        assert ca.pk in calls


@pytest.mark.django_db
class TestTargetOnCreation:
    def _post(self, setup, **extra):
        from iam.models import User
        from rest_framework.test import APIClient

        admin = User.objects.create_superuser(
            email="target-admin@test.local", password="x"
        )
        api = APIClient()
        api.force_authenticate(admin)
        return api.post(
            "/api/compliance-assessments/",
            {
                "name": "Created",
                "folder": str(setup["folder"].id),
                "framework": str(setup["fw"].id),
                **extra,
            },
            format="json",
        )

    def test_target_checked_against_baseline_scale(self, setup):
        _update(setup["ca"], {"score_scale_preset": "1-5"})[0].save()
        response = self._post(setup, baseline=str(setup["ca"].id), target_score=80)
        assert response.status_code == 400
        assert "target_score" in response.json()

    def test_valid_target_on_baseline_scale_despite_instance_default(self, setup):
        _set_instance_default(
            {"score_scale_preset": "1-5", "min_score": 1, "max_score": 5}
        )
        response = self._post(setup, baseline=str(setup["ca"].id), target_score=80)
        assert response.status_code == 201, response.json()
        created = ComplianceAssessment.objects.get(id=response.json()["id"])
        assert (created.min_score, created.max_score, created.target_score) == (
            0,
            100,
            80,
        )

    def test_baseline_scale_and_labels_are_copied(self, setup):
        _update(
            setup["ca"],
            {"score_scale_preset": "0-5", "scores_definition": _levels(3)},
        )[0].save()
        response = self._post(setup, baseline=str(setup["ca"].id))
        assert response.status_code == 201, response.json()
        created = ComplianceAssessment.objects.get(id=response.json()["id"])
        assert (created.min_score, created.max_score) == (0, 5)
        assert created.score_scale_preset == "0-5"
        assert created.scores_definition == _levels(3)

    def test_target_checked_without_any_scale_field(self, setup):
        response = self._post(setup, target_score=150)
        assert response.status_code == 400
        assert "target_score" in response.json()


def _labelled_framework(setup, urn="urn:test:fw-labelled"):
    return Framework.objects.create(
        name="FW labelled",
        urn=urn,
        min_score=1,
        max_score=5,
        scores_definition=[
            {"score": s, "name": n}
            for s, n in zip(
                range(1, 6), ["Initial", "Managed", "Defined", "Measured", "Optimizing"]
            )
        ],
        folder=setup["folder"],
    )


@pytest.mark.django_db
class TestAuditCopyIsTheOnlyLabelSource:
    def _global_score_levels(self, ca):
        from iam.models import User
        from rest_framework.test import APIClient

        admin = User.objects.create_superuser(email="gs-admin@test.local", password="x")
        api = APIClient()
        api.force_authenticate(admin)
        response = api.get(f"/api/compliance-assessments/{ca.id}/global_score/")
        assert response.status_code == 200, response.json()
        return response.json()["scores_definition"]

    def test_wide_preset_shows_no_framework_labels(self, setup):
        fw = _labelled_framework(setup)
        ca = ComplianceAssessment.objects.create(
            name="Percent",
            framework=fw,
            folder=setup["folder"],
            score_scale_preset="0-100",
            min_score=0,
            max_score=100,
            scores_definition=[],
        )
        assert self._global_score_levels(ca) == []

    def test_custom_scale_without_labels_stays_empty(self, setup):
        fw = _labelled_framework(setup)
        ca = ComplianceAssessment.objects.create(
            name="Bare",
            framework=fw,
            folder=setup["folder"],
            min_score=1,
            max_score=5,
            scores_definition=[],
        )
        assert self._global_score_levels(ca) == []

    def test_framework_labels_copied_at_creation(self, setup):
        fw = _labelled_framework(setup)
        ca = ComplianceAssessment.objects.create(
            name="Default", framework=fw, folder=setup["folder"]
        )
        assert [lvl["name"] for lvl in self._global_score_levels(ca)][:2] == [
            "Initial",
            "Managed",
        ]


@pytest.mark.django_db
class TestLibraryUpdateLabelsFollowRange:
    def test_own_range_audit_does_not_pick_up_new_labels(self):
        from core.models import LoadedLibrary, StoredLibrary

        folder = Folder.get_root_folder()
        stored, _ = StoredLibrary.store_library_content(
            _LIB.format(version=1, scale="").encode("utf-8")
        )
        stored.load()
        fw = Framework.objects.get(urn="urn:intuitem:test:framework:scale-update")
        own_range = ComplianceAssessment.objects.create(
            name="Own range",
            framework=fw,
            folder=folder,
            min_score=0,
            max_score=4,
            scores_definition=[],
        )
        following = ComplianceAssessment.objects.create(
            name="Following", framework=fw, folder=folder
        )

        StoredLibrary.store_library_content(
            _LIB.format(version=2, scale=_SCALE_V2).encode("utf-8")
        )
        assert (
            LoadedLibrary.objects.get(urn=stored.urn).update(strategy="clamp") is None
        )

        own_range.refresh_from_db()
        assert (own_range.min_score, own_range.max_score) == (0, 4)
        assert own_range.scores_definition == []
        following.refresh_from_db()
        assert (following.min_score, following.max_score) == (1, 4)
        assert [lvl["name"] for lvl in following.get_scale_levels()][0] == "Low"


@pytest.mark.django_db
class TestLabelMigration:
    def _run(self):
        import importlib

        from django.apps import apps

        module = importlib.import_module(
            "core.migrations.0191_copy_framework_scale_labels_to_audits"
        )
        module.copy_framework_labels(apps, None)

    def test_fills_only_audits_on_framework_range(self, setup):
        fw = _labelled_framework(setup)
        folder = setup["folder"]
        on_range = ComplianceAssessment.objects.create(
            name="On range", framework=fw, folder=folder, min_score=1, max_score=5
        )
        ComplianceAssessment.objects.filter(pk=on_range.pk).update(
            scores_definition=None
        )
        other_range = ComplianceAssessment.objects.create(
            name="Other",
            framework=fw,
            folder=folder,
            min_score=0,
            max_score=3,
            scores_definition=[],
        )
        preset = ComplianceAssessment.objects.create(
            name="Preset",
            framework=fw,
            folder=folder,
            score_scale_preset="1-5",
            min_score=1,
            max_score=5,
            scores_definition=[],
        )
        own = [{"score": 1, "name": "Mine"}]
        labelled = ComplianceAssessment.objects.create(
            name="Labelled",
            framework=fw,
            folder=folder,
            min_score=1,
            max_score=5,
            scores_definition=own,
        )

        self._run()

        for ca in (on_range, other_range, preset, labelled):
            ca.refresh_from_db()
        assert on_range.scores_definition == fw.scores_definition
        assert other_range.scores_definition == []
        assert preset.scores_definition == []
        assert labelled.scores_definition == own


class TestHalfUpRounding:
    @pytest.mark.parametrize(
        "value, expected",
        [(10, 1), (30, 2), (50, 3), (70, 4), (90, 5), (0, 0), (100, 5)],
    )
    def test_percentages_to_zero_five_round_halves_up(self, value, expected):
        from core.models import rescale_score

        assert rescale_score(value, (0, 100), (0, 5)) == expected

    def test_float_target_rounds_half_up(self):
        from core.models import rescale_score

        assert rescale_score(1, (0, 8), (0, 1), integer=False) == 0.13


@pytest.mark.django_db
class TestGlobalScoreScaleSummary:
    def test_includes_framework_and_preset(self, setup):
        from iam.models import User
        from rest_framework.test import APIClient

        _update(setup["ca"], {"score_scale_preset": "1-4"})[0].save()
        admin = User.objects.create_superuser(
            email="gs2-admin@test.local", password="x"
        )
        api = APIClient()
        api.force_authenticate(admin)
        body = api.get(
            f"/api/compliance-assessments/{setup['ca'].id}/global_score/"
        ).json()
        assert body["framework"] == str(setup["fw"].id)
        assert body["score_scale_preset"] == "1-4"
        assert (body["min_score"], body["max_score"]) == (1, 4)
