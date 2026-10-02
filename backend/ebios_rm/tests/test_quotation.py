import pytest

from ebios_rm.models import EbiosRMStudy, KillChain, OperatingMode
from ebios_rm.quotation import (
    FICHE_LIKELIHOOD_GRID,
    UNRATED,
    Step,
    compute,
    default_likelihood_grid,
)
from ebios_rm.tests.test_kill_chain_steps import _operating_mode, _save_graph


def _diamond(operator, probabilities, difficulties=(UNRATED,) * 4):
    """recon -> (phishing | watering hole) -> exfiltration"""
    ids = ["recon", "phishing", "watering", "exfiltration"]
    antecedents = [[], ["recon"], ["recon"], ["phishing", "watering"]]
    return [
        Step(
            id=step_id,
            antecedents=antecedents[i],
            logic_operator=operator if i == 3 else None,
            probability=probabilities[i],
            difficulty=difficulties[i],
        )
        for i, step_id in enumerate(ids)
    ]


class TestLikelihoodGrid:
    def test_five_levels_is_the_fiche_grid(self):
        assert default_likelihood_grid(5) == FICHE_LIKELIHOOD_GRID

    def test_four_levels_resampling(self):
        assert default_likelihood_grid(4) == [
            [1, 1, 0, 0],
            [2, 2, 1, 0],
            [3, 2, 2, 1],
            [3, 3, 2, 1],
        ]

    @pytest.mark.parametrize("size", [2, 3, 4, 5, 6, 7])
    def test_grid_is_monotonic(self, size):
        grid = default_likelihood_grid(size)
        for p in range(size):
            for d in range(size):
                assert 0 <= grid[p][d] < size
                if p + 1 < size:
                    assert grid[p + 1][d] >= grid[p][d]
                if d + 1 < size:
                    assert grid[p][d + 1] <= grid[p][d]


class TestStandardRollUp:
    def test_linear_chain_takes_the_weakest_step(self):
        steps = [
            Step("a", [], None, probability=3),
            Step("b", ["a"], None, probability=1),
            Step("c", ["b"], None, probability=2),
        ]
        result = compute(steps, "standard")
        assert result.probability == {"a": 3, "b": 1, "c": 1}
        assert result.likelihood == 1
        assert result.critical_path == {"a", "b", "c"}

    def test_or_keeps_the_best_alternative(self):
        result = compute(_diamond("OR", (3, 1, 2, 3)), "standard")
        assert result.probability["exfiltration"] == 2
        assert result.likelihood == 2
        assert result.critical_path == {"recon", "watering", "exfiltration"}

    def test_and_needs_every_antecedent(self):
        result = compute(_diamond("AND", (3, 1, 2, 3)), "standard")
        assert result.probability["exfiltration"] == 1
        assert result.critical_path == {"recon", "phishing", "watering", "exfiltration"}

    def test_missing_operator_behaves_as_or(self):
        result = compute(_diamond(None, (3, 1, 2, 3)), "standard")
        assert result.likelihood == 2

    def test_global_value_is_the_best_final_step(self):
        steps = [
            Step("a", [], None, probability=3),
            Step("b", ["a"], None, probability=1),
            Step("c", ["a"], None, probability=2),
        ]
        result = compute(steps, "standard")
        assert result.likelihood == 2
        assert result.critical_path == {"a", "c"}

    def test_unrated_step_leaves_the_mode_unrated(self):
        result = compute(_diamond("OR", (3, UNRATED, 2, 3)), "standard")
        assert result.probability["phishing"] == UNRATED
        assert result.probability["exfiltration"] == UNRATED
        assert result.likelihood == UNRATED
        assert result.critical_path == set()

    def test_empty_graph(self):
        assert compute([], "standard").likelihood == UNRATED

    def test_order_independent(self):
        steps = list(reversed(_diamond("OR", (3, 1, 2, 3))))
        assert compute(steps, "standard").likelihood == 2


class TestAdvancedRollUp:
    grid = default_likelihood_grid(4)

    def test_difficulty_takes_the_easiest_alternative(self):
        result = compute(
            _diamond("OR", (3, 3, 3, 3), (0, 3, 1, 0)), "advanced", self.grid
        )
        assert result.difficulty == {
            "recon": 0,
            "phishing": 3,
            "watering": 1,
            "exfiltration": 1,
        }
        assert result.likelihood == self.grid[3][1]
        assert result.critical_path == {"recon", "watering", "exfiltration"}

    def test_and_difficulty_takes_the_hardest_antecedent(self):
        result = compute(
            _diamond("AND", (3, 3, 3, 3), (0, 3, 1, 0)), "advanced", self.grid
        )
        assert result.difficulty["exfiltration"] == 3
        assert result.likelihood == self.grid[3][3]

    def test_crossing_at_each_step(self):
        result = compute(
            _diamond("OR", (2, 1, 2, 3), (1, 0, 2, 0)), "advanced", self.grid
        )
        assert result.probability["exfiltration"] == 2
        assert result.difficulty["exfiltration"] == 1
        assert result.step_likelihood["exfiltration"] == self.grid[2][1]

    def test_unrated_difficulty_leaves_the_mode_unrated(self):
        result = compute(
            _diamond("OR", (3, 3, 3, 3), (0, UNRATED, UNRATED, 0)),
            "advanced",
            self.grid,
        )
        assert result.likelihood == UNRATED


@pytest.mark.django_db
class TestOperatingModeLikelihood:
    def _chain(self, operating_mode, actions, ratings):
        steps = []
        for action, (probability, difficulty) in zip(actions, ratings):
            step = KillChain.objects.create(
                operating_mode=operating_mode,
                elementary_action=action,
                success_probability=probability,
                technical_difficulty=difficulty,
            )
            if steps:
                step.antecedents.set([steps[-1]])
            steps.append(step)
        operating_mode.refresh_likelihood()
        operating_mode.refresh_from_db()
        return steps

    @pytest.mark.parametrize(
        "method, expected", [("standard", 1), ("advanced", 2), ("express", -1)]
    )
    def test_method_drives_the_operating_mode(
        self, basic_ebios_rm_study_fixture, elementary_actions_fixture, method, expected
    ):
        study = basic_ebios_rm_study_fixture
        study.quotation_method = method
        study.save()
        operating_mode = _operating_mode(study)
        self._chain(
            operating_mode, elementary_actions_fixture, [(3, 0), (1, 0), (3, 1)]
        )

        # advanced: probability 1, difficulty 1 -> 4-level grid [1][1] == 2
        assert operating_mode.effective_likelihood == expected

    def test_operational_scenario_follows_its_most_likely_mode(
        self, basic_ebios_rm_study_fixture, elementary_actions_fixture
    ):
        study = basic_ebios_rm_study_fixture
        study.quotation_method = "standard"
        study.save()
        operating_mode = _operating_mode(study)
        steps = self._chain(
            operating_mode, elementary_actions_fixture, [(3, -1), (2, -1), (3, -1)]
        )
        scenario = operating_mode.operational_scenario
        scenario.refresh_from_db()
        assert scenario.likelihood == 2
        assert scenario.computed_likelihood == 2

        steps[1].success_probability = 0
        steps[1].save()
        operating_mode.refresh_likelihood()
        scenario.refresh_from_db()
        assert scenario.likelihood == 0

    def test_typed_likelihood_is_kept_beside_the_roll_up(
        self, basic_ebios_rm_study_fixture, elementary_actions_fixture
    ):
        study = basic_ebios_rm_study_fixture
        study.quotation_method = "standard"
        study.save()
        operating_mode = _operating_mode(study)
        self._chain(operating_mode, elementary_actions_fixture, [(1, -1)] * 3)

        operating_mode.likelihood = 3
        operating_mode.save()
        operating_mode.refresh_from_db()
        assert operating_mode.effective_likelihood == 1
        assert operating_mode.likelihood == 3

    def test_switching_method_recomputes(
        self, basic_ebios_rm_study_fixture, elementary_actions_fixture
    ):
        study = basic_ebios_rm_study_fixture
        study.quotation_method = "express"
        study.save()
        operating_mode = _operating_mode(study)
        self._chain(operating_mode, elementary_actions_fixture, [(2, -1)] * 3)
        operating_mode.refresh_from_db()
        assert operating_mode.effective_likelihood == -1

        study.quotation_method = "standard"
        study.save()
        operating_mode.refresh_from_db()
        assert operating_mode.effective_likelihood == 2

    def test_forced_scenario_likelihood_still_wins(
        self, basic_ebios_rm_study_fixture, elementary_actions_fixture
    ):
        study = basic_ebios_rm_study_fixture
        study.quotation_method = "standard"
        study.save()
        operating_mode = _operating_mode(study)
        scenario = operating_mode.operational_scenario
        scenario.likelihood_forced = 0
        scenario.save()
        self._chain(operating_mode, elementary_actions_fixture, [(3, -1)] * 3)

        scenario.refresh_from_db()
        assert operating_mode.effective_likelihood == 3
        assert scenario.likelihood == 0
        assert scenario.computed_likelihood == 3


@pytest.mark.django_db
class TestQuotationApi:
    def test_save_graph_updates_likelihood_and_exposes_steps(
        self, admin_client, basic_ebios_rm_study_fixture, elementary_actions_fixture
    ):
        study = basic_ebios_rm_study_fixture
        study.quotation_method = "standard"
        study.save()
        operating_mode = _operating_mode(study)
        know, enter, exploit = elementary_actions_fixture

        _save_graph(
            admin_client,
            operating_mode,
            [
                {
                    "id": "a",
                    "elementary_action": str(know.id),
                    "success_probability": 3,
                },
                {
                    "id": "b",
                    "elementary_action": str(enter.id),
                    "antecedents": ["a"],
                    "success_probability": 2,
                },
                {
                    "id": "c",
                    "elementary_action": str(enter.id),
                    "antecedents": ["a"],
                    "success_probability": 1,
                },
                {
                    "id": "d",
                    "elementary_action": str(exploit.id),
                    "antecedents": ["b", "c"],
                    "logic_operator": "OR",
                    "success_probability": 3,
                },
            ],
        )
        operating_mode.refresh_from_db()
        assert operating_mode.effective_likelihood == 2

        response = admin_client.get(
            f"/api/ebios-rm/operating-modes/{operating_mode.id}/quotation/"
        )
        assert response.status_code == 200, response.content
        data = response.json()
        assert data["method"] == "standard"
        assert data["likelihood"] == 2
        steps = {
            KillChain.objects.get(id=step_id).success_probability: value
            for step_id, value in data["steps"].items()
        }
        assert steps[1] == {
            "probability": 1,
            "difficulty": None,
            "likelihood": 1,
            "critical": False,
        }
        assert steps[2]["critical"] is True

    def test_kill_chain_endpoint_recomputes(
        self, admin_client, basic_ebios_rm_study_fixture, elementary_actions_fixture
    ):
        study = basic_ebios_rm_study_fixture
        study.quotation_method = "standard"
        study.save()
        operating_mode = _operating_mode(study)
        know, _, _ = elementary_actions_fixture
        step = KillChain.objects.create(
            operating_mode=operating_mode,
            elementary_action=know,
            success_probability=1,
        )

        response = admin_client.patch(
            f"/api/ebios-rm/kill-chains/{step.id}/",
            {"success_probability": 3},
            format="json",
        )
        assert response.status_code == 200, response.content
        operating_mode.refresh_from_db()
        assert operating_mode.effective_likelihood == 3

        admin_client.delete(f"/api/ebios-rm/kill-chains/{step.id}/")
        operating_mode.refresh_from_db()
        assert operating_mode.effective_likelihood == -1

    def test_express_has_no_roll_up(self, admin_client, basic_ebios_rm_study_fixture):
        operating_mode = _operating_mode(basic_ebios_rm_study_fixture)
        response = admin_client.get(
            f"/api/ebios-rm/operating-modes/{operating_mode.id}/quotation/"
        )
        assert response.json() == {"method": "express"}


@pytest.mark.parametrize("method", EbiosRMStudy.AVAILABLE_QUOTATION_METHODS)
def test_every_method_is_available(method):
    assert method in EbiosRMStudy.QuotationMethod.values


@pytest.mark.django_db
class TestMostLikelyOperatingMode:
    def _mode(self, scenario, name, actions, ratings):
        operating_mode = OperatingMode.objects.create(
            name=name, operational_scenario=scenario
        )
        previous = None
        for action, (probability, difficulty) in zip(actions, ratings):
            step = KillChain.objects.create(
                operating_mode=operating_mode,
                elementary_action=action,
                success_probability=probability,
                technical_difficulty=difficulty,
            )
            if previous:
                step.antecedents.set([previous])
            previous = step
        operating_mode.refresh_likelihood()
        return operating_mode

    def _scenario(self, study, method):
        study.quotation_method = method
        study.save()
        return _operating_mode(study, name="seed").operational_scenario

    def test_standard_picks_the_most_likely_mode_with_its_critical_steps(
        self, basic_ebios_rm_study_fixture, elementary_actions_fixture
    ):
        scenario = self._scenario(basic_ebios_rm_study_fixture, "standard")
        self._mode(scenario, "weak", elementary_actions_fixture, [(1, -1)] * 3)
        strong = self._mode(
            scenario, "strong", elementary_actions_fixture, [(3, -1), (2, -1), (3, -1)]
        )

        result = scenario.most_likely_operating_mode()

        assert result["id"] == str(strong.id)
        assert result["likelihood"]["value"] == 2
        assert [step["name"] for step in result["critical_steps"]] == [
            "Reconnaissance",
            "Phishing",
            "Exfiltration",
        ]

    def test_advanced_tie_goes_to_the_least_effort(
        self, basic_ebios_rm_study_fixture, elementary_actions_fixture
    ):
        scenario = self._scenario(basic_ebios_rm_study_fixture, "advanced")
        # 4-level grid: [3][0] == 3 and [3][1] == 3 — same likelihood, different effort
        self._mode(scenario, "harder", elementary_actions_fixture, [(3, 1)] * 3)
        easier = self._mode(
            scenario, "easier", elementary_actions_fixture, [(3, 0)] * 3
        )

        assert scenario.most_likely_operating_mode()["id"] == str(easier.id)

    def test_express_names_the_mode_without_steps(self, basic_ebios_rm_study_fixture):
        scenario = self._scenario(basic_ebios_rm_study_fixture, "express")
        OperatingMode.objects.create(
            name="low", operational_scenario=scenario, likelihood=1
        )
        high = OperatingMode.objects.create(
            name="high", operational_scenario=scenario, likelihood=3
        )

        result = scenario.most_likely_operating_mode()
        assert result["id"] == str(high.id)
        assert result["critical_steps"] == []

    def test_direct_estimate_has_none(self, basic_ebios_rm_study_fixture):
        scenario = self._scenario(basic_ebios_rm_study_fixture, "manual")
        assert scenario.most_likely_operating_mode() is None
