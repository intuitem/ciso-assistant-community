import pytest
from django.db.models import BooleanField, Exists, ExpressionWrapper, OuterRef, Q

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


def _update(ca, data):
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
class TestRangeLock:
    def test_has_scores(self, setup):
        assert setup["ca"].has_scores is False
        setup["ra"].score = 40
        setup["ra"].save()
        assert setup["ca"].has_scores is True

    def test_range_locked_once_scored(self, setup):
        setup["ra"].score = 40
        setup["ra"].save()
        serializer, valid = _update(setup["ca"], {"score_scale_preset": "0-5"})
        assert not valid
        assert "score_scale_preset" in serializer.errors

    def test_wording_editable_once_scored(self, setup):
        ca = setup["ca"]
        _update(ca, {"score_scale_preset": "0-5"})[0].save()
        setup["ra"].score = 4
        setup["ra"].save()
        serializer, valid = _update(
            ca, {"score_scale_preset": "0-5", "scores_definition": _levels(4)}
        )
        assert valid, serializer.errors

    def test_documentation_score_counts_as_scored(self, setup):
        setup["ra"].documentation_score = 10
        setup["ra"].save()
        assert setup["ca"].has_scores is True


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
                    Q(
                        *(
                            Exists(qs)
                            for qs in Framework.scale_bound_querysets(OuterRef("pk"))
                        ),
                        _connector=Q.OR,
                    ),
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
