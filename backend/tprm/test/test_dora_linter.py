"""
Tests for tprm.dora_linter.

Scope: the subcontracting-chain linter (`lint_subcontracting_chains`) introduced
by the DORA Art. 28(2) subcontracting data model. Other linters in `dora_linter`
are covered implicitly by the broader tprm test suite; this file focuses on
invariants specific to SolutionSubcontractor chains.
"""

from django.test import TestCase

from iam.models import Folder
from tprm.dora_linter import lint_subcontracting_chains
from tprm.models import (
    Contract,
    Entity,
    Solution,
    SolutionSubcontractor,
)


class LintSubcontractingChainsBase(TestCase):
    """Shared fixtures for the linter tests."""

    def setUp(self):
        self.folder = Folder.objects.create(name="Test Folder")
        self.main_entity = Entity.objects.create(
            name="Main FE",
            folder=self.folder,
            builtin=True,
            legal_identifiers={"LEI": "MAIN1234567890123456"},
        )
        self.direct_provider = Entity.objects.create(
            name="Direct Provider",
            folder=self.folder,
            legal_identifiers={"LEI": "DIRE1234567890123456"},
        )
        self.subcontractor = Entity.objects.create(
            name="Valid Sub",
            folder=self.folder,
            legal_identifiers={"LEI": "SUBX1234567890123456"},
        )
        self.solution = Solution.objects.create(
            name="Test Solution",
            provider_entity=self.direct_provider,
            dora_ict_service_type="eba_TA:S09",
        )
        self.contract = Contract.objects.create(
            name="Test Contract",
            ref_id="CA-LINT",
            folder=self.folder,
            provider_entity=self.direct_provider,
            beneficiary_entity=self.main_entity,
            is_intragroup=False,
            status=Contract.Status.ACTIVE,
        )
        self.contract.solutions.add(self.solution)

    def _errors(self, results):
        return [r for r in results if r["severity"] == "error"]

    def _warnings(self, results):
        return [r for r in results if r["severity"] == "warning"]

    def _oks(self, results):
        return [r for r in results if r["severity"] == "ok"]


class TestLintSubcontractingChainsEmpty(LintSubcontractingChainsBase):
    def test_empty_returns_no_results(self):
        """No chains anywhere → linter returns an empty result list."""
        results = lint_subcontracting_chains()
        self.assertEqual(results, [])


class TestLintSubcontractingChainsHappyPath(LintSubcontractingChainsBase):
    def test_valid_chain_produces_ok(self):
        """A well-formed chain returns an 'ok' result and no errors/warnings."""
        SolutionSubcontractor.objects.create(
            solution=self.solution, subcontractor=self.subcontractor, rank=2
        )
        results = lint_subcontracting_chains()
        self.assertEqual(len(self._errors(results)), 0)
        self.assertEqual(len(self._warnings(results)), 0)
        self.assertEqual(len(self._oks(results)), 1)
        self.assertEqual(self._oks(results)[0]["category"], "Supply Chain (B_05.02)")


class TestLintSubcontractingChainsMissingLEI(LintSubcontractingChainsBase):
    def test_subcontractor_without_legal_identifier_errors(self):
        """Subcontractor with empty legal_identifiers → error severity."""
        no_id_sub = Entity.objects.create(
            name="Subcontractor Without LEI",
            folder=self.folder,
            legal_identifiers={},
        )
        SolutionSubcontractor.objects.create(
            solution=self.solution, subcontractor=no_id_sub, rank=2
        )
        results = lint_subcontracting_chains()
        errors = self._errors(results)
        self.assertEqual(len(errors), 1)
        self.assertIn("no legal identifier", errors[0]["message"])
        self.assertEqual(errors[0]["object_id"], str(no_id_sub.id))

    def test_subcontractor_with_empty_string_lei_errors(self):
        """legal_identifiers with empty-string values also fails."""
        empty_id_sub = Entity.objects.create(
            name="Empty LEI Sub",
            folder=self.folder,
            legal_identifiers={"LEI": ""},
        )
        SolutionSubcontractor.objects.create(
            solution=self.solution, subcontractor=empty_id_sub, rank=2
        )
        results = lint_subcontracting_chains()
        self.assertEqual(len(self._errors(results)), 1)


class TestLintSubcontractingChainsSelfLoop(LintSubcontractingChainsBase):
    def test_subcontractor_equal_to_direct_provider_errors(self):
        """Self-loop: subcontractor == solution.provider_entity → error.

        AbstractBaseModel.save() calls clean() which rejects this, so bypass
        via bulk_create to simulate a management command or raw SQL path that
        skipped validation. The linter is the safety net for exactly that case.
        """
        SolutionSubcontractor.objects.bulk_create(
            [
                SolutionSubcontractor(
                    solution=self.solution,
                    subcontractor=self.direct_provider,
                    rank=2,
                )
            ]
        )
        results = lint_subcontracting_chains()
        errors = self._errors(results)
        self.assertEqual(len(errors), 1)
        self.assertIn("direct provider", errors[0]["message"])


class TestLintSubcontractingChainsInvalidRank(LintSubcontractingChainsBase):
    def test_rank_below_2_errors(self):
        """Rank 1 or 0 stored anyway (via .update bypassing clean) → error."""
        row = SolutionSubcontractor.objects.create(
            solution=self.solution, subcontractor=self.subcontractor, rank=2
        )
        # Bypass clean() via queryset update.
        SolutionSubcontractor.objects.filter(pk=row.pk).update(rank=1)
        results = lint_subcontracting_chains()
        errors = self._errors(results)
        self.assertTrue(any("rank" in e["message"].lower() for e in errors))


class TestLintSubcontractingChainsIntragroupBeneficiary(LintSubcontractingChainsBase):
    def test_intragroup_beneficiary_can_be_subcontractor_elsewhere(self):
        """
        An intragroup entity that is a beneficiary of some contracts can
        legitimately be a subcontractor in another solution's chain. The
        linter must NOT flag this — DORA's b.02.03 / b.03.03 templates exist
        for exactly this case.

        Explicit non-rule test: guards against over-broad validation.
        """
        # Create a subsidiary that's a beneficiary of another contract.
        subsidiary = Entity.objects.create(
            name="Subsidiary beneficiary",
            folder=self.folder,
            parent_entity=self.main_entity,
            legal_identifiers={"LEI": "SUBS1234567890123456"},
        )
        other_contract = Contract.objects.create(
            name="Other Contract",
            ref_id="CA-OTHER",
            folder=self.folder,
            provider_entity=self.direct_provider,
            beneficiary_entity=subsidiary,  # subsidiary as beneficiary
            is_intragroup=False,
            status=Contract.Status.ACTIVE,
        )
        other_sol = Solution.objects.create(
            name="Other Solution",
            provider_entity=self.direct_provider,
            dora_ict_service_type="eba_TA:S09",
        )
        other_contract.solutions.add(other_sol)

        # The same subsidiary is a subcontractor in a different solution's chain.
        SolutionSubcontractor.objects.create(
            solution=self.solution, subcontractor=subsidiary, rank=2
        )
        results = lint_subcontracting_chains()
        # No errors or warnings for the legit intragroup-subcontractor case.
        self.assertEqual(len(self._errors(results)), 0)
        self.assertEqual(len(self._warnings(results)), 0)
        self.assertEqual(len(self._oks(results)), 1)


class TestLintSubcontractingChainsDraftExcluded(LintSubcontractingChainsBase):
    def test_draft_contract_chains_ignored(self):
        """Chains on draft-contract solutions are out of scope for the linter."""
        draft_contract = Contract.objects.create(
            name="Draft Contract",
            ref_id="CA-DRAFT",
            folder=self.folder,
            provider_entity=self.direct_provider,
            beneficiary_entity=self.main_entity,
            is_intragroup=False,
            status=Contract.Status.DRAFT,
        )
        no_id_sub = Entity.objects.create(
            name="Would-Error Sub",
            folder=self.folder,
            legal_identifiers={},
        )
        draft_solution = Solution.objects.create(
            name="Draft Solution",
            provider_entity=self.direct_provider,
            dora_ict_service_type="eba_TA:S09",
        )
        draft_contract.solutions.add(draft_solution)
        SolutionSubcontractor.objects.create(
            solution=draft_solution, subcontractor=no_id_sub, rank=2
        )
        # Even though the subcontractor has no LEI, it's behind a Draft contract
        # and should be out of scope.
        results = lint_subcontracting_chains()
        self.assertEqual(len(self._errors(results)), 0)

    def test_dora_excluded_contract_chains_ignored(self):
        """Chains on dora_exclude=True contract solutions are out of scope."""
        excluded_contract = Contract.objects.create(
            name="Excluded Contract",
            ref_id="CA-EXCL",
            folder=self.folder,
            provider_entity=self.direct_provider,
            beneficiary_entity=self.main_entity,
            is_intragroup=False,
            status=Contract.Status.ACTIVE,
            dora_exclude=True,
        )
        no_id_sub = Entity.objects.create(
            name="Would-Error Sub 2",
            folder=self.folder,
            legal_identifiers={},
        )
        excl_solution = Solution.objects.create(
            name="Excluded Solution",
            provider_entity=self.direct_provider,
            dora_ict_service_type="eba_TA:S09",
        )
        excluded_contract.solutions.add(excl_solution)
        SolutionSubcontractor.objects.create(
            solution=excl_solution, subcontractor=no_id_sub, rank=2
        )
        results = lint_subcontracting_chains()
        self.assertEqual(len(self._errors(results)), 0)
