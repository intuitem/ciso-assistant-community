"""
Tests for TPRM ecosystem coverage in domain export / import.

Two layers:
1. Scope tests on ``get_domain_export_objects`` , the third party graph
   (entity assessments, solutions, subcontracting, representatives, contracts)
   is collected, and the required (non-null) FK closure pulls in referenced
   entities even when they live outside the exported domain folder.
2. A full export -> import round-trip through ``export_domain`` /
   ``import_objects`` asserting FKs are remapped into the new (flattened)
   domain and the deliberate losses (builtin recipient) degrade to null.
"""

import io

import pytest
from django.conf import settings
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError as DjangoValidationError

from serdes.domain_io import export_domain, import_objects, process_uploaded_file
from serdes.utils import get_domain_export_objects
from core.models import (
    Answer,
    AppliedControl,
    Asset,
    Campaign,
    ComplianceAssessment,
    Evidence,
    Framework,
    Perimeter,
    StoredLibrary,
    TaskTemplate,
)
from core.utils import build_initial_field_visibility
from tprm.services import grant_respondent_access
from iam.models import Folder, Role, RoleAssignment, User
from tprm.models import (
    Contract,
    Entity,
    EntityAssessment,
    Representative,
    Solution,
    SolutionSubcontractor,
)


# ============ Fixtures ============


@pytest.fixture
def root_folder():
    return Folder.get_root_folder()


@pytest.fixture
def tprm_domain(root_folder):
    """A domain populated with the full TPRM graph.

    Layout:
      provider  (in domain)  ── parent_entity ─▶ parent (in domain)
      subcontractor (in domain)
      main_org  (builtin, in root)             ← left out of the export

      solution SOL-1: provider=provider, recipient=main_org, asset=A
      subcontracting: SOL-1 ── subcontractor
      representative REP-1 on provider
      entity assessment EA on provider, solutions={SOL-1}
      contract CONTRACT-1 (in domain), solutions={SOL-1}
    """
    domain = Folder.objects.create(
        name="TPRM Source",
        content_type=Folder.ContentType.DOMAIN,
        parent_folder=root_folder,
    )

    parent = Entity.objects.create(name="Parent Co", ref_id="PARENT-1", folder=domain)
    provider = Entity.objects.create(
        name="Provider Co",
        ref_id="PROV-1",
        folder=domain,
        parent_entity=parent,
    )
    subcontractor = Entity.objects.create(
        name="Subcontractor Co", ref_id="SUB-1", folder=domain
    )
    # Builtin main organisation lives in the root folder: a nullable FK target
    # that must NOT be exported (the target instance keeps its own).
    main_org = Entity.objects.create(
        name="Main Org", ref_id="MAIN-1", folder=root_folder, builtin=True
    )

    asset = Asset.objects.create(name="Provider Asset", folder=domain)

    solution = Solution.objects.create(
        name="Managed Service",
        ref_id="SOL-1",
        provider_entity=provider,
        recipient_entity=main_org,
    )
    solution.assets.add(asset)

    subcontract = SolutionSubcontractor.objects.create(
        solution=solution, subcontractor=subcontractor
    )

    representative = Representative.objects.create(
        entity=provider, ref_id="REP-1", email="rep@provider.example"
    )

    entity_assessment = EntityAssessment.objects.create(
        name="Provider assessment", folder=domain, entity=provider
    )
    entity_assessment.solutions.add(solution)

    contract = Contract.objects.create(
        name="MSA", ref_id="CONTRACT-1", folder=domain, provider_entity=provider
    )
    contract.solutions.add(solution)

    return {
        "domain": domain,
        "parent": parent,
        "provider": provider,
        "subcontractor": subcontractor,
        "main_org": main_org,
        "asset": asset,
        "solution": solution,
        "subcontract": subcontract,
        "representative": representative,
        "entity_assessment": entity_assessment,
        "contract": contract,
    }


@pytest.fixture
def framework_fixture():
    """A questionnaire framework: its requirements carry library-backed
    questions, so answers exercise the question / choice URN references."""
    library = StoredLibrary.objects.filter(
        urn="urn:intuitem:risk:library:enisa-sme-cra-maturity"
    ).last()
    assert library is not None
    library.load()
    return Framework.objects.get(
        urn="urn:intuitem:risk:framework:enisa-sme-cra-maturity"
    )


@pytest.fixture
def admin_user(root_folder):
    """A user holding every permission recursively from the root folder."""
    user = User.objects.create(email="tprm-admin@test.com", password="test")
    role = Role.objects.create(name="tprm-all-perms")
    role.permissions.set(Permission.objects.all())
    role.save()
    assignment = RoleAssignment.objects.create(
        user=user, role=role, folder=root_folder, is_recursive=True
    )
    assignment.perimeter_folders.add(root_folder)
    assignment.save()
    return user


# ============ Scope tests ============


class TestTPRMExportScope:
    @pytest.mark.django_db
    def test_full_ecosystem_is_collected(self, tprm_domain):
        data = get_domain_export_objects(tprm_domain["domain"])

        assert tprm_domain["provider"] in data["entity"]
        assert tprm_domain["parent"] in data["entity"]
        assert tprm_domain["subcontractor"] in data["entity"]
        assert tprm_domain["solution"] in data["solution"]
        assert tprm_domain["subcontract"] in data["solutionsubcontractor"]
        assert tprm_domain["representative"] in data["representative"]
        assert tprm_domain["entity_assessment"] in data["entityassessment"]
        assert tprm_domain["contract"] in data["contract"]

    @pytest.mark.django_db
    def test_required_fk_target_outside_domain_is_pulled_in(self, root_folder):
        """EntityAssessment.entity is a non-null FK: even when the assessed
        entity lives outside the exported domain folder, it must travel or the
        import would crash on a missing lookup."""
        domain = Folder.objects.create(
            name="EA Domain",
            content_type=Folder.ContentType.DOMAIN,
            parent_folder=root_folder,
        )
        external_entity = Entity.objects.create(
            name="External Provider", ref_id="EXT-1", folder=root_folder
        )
        ea = EntityAssessment.objects.create(
            name="External assessment", folder=domain, entity=external_entity
        )

        data = get_domain_export_objects(domain)

        assert ea in data["entityassessment"]
        assert external_entity in data["entity"]

    @pytest.mark.django_db
    def test_builtin_optional_target_is_excluded(self, tprm_domain):
        """The builtin main organisation is only a nullable recipient: it must
        stay out of the export so it is not duplicated on the target."""
        data = get_domain_export_objects(tprm_domain["domain"])
        assert tprm_domain["main_org"] not in data["entity"]


# ============ Round-trip test ============


class TestTPRMRoundTrip:
    @pytest.mark.django_db
    def test_export_import_preserves_tprm_graph(self, tprm_domain, admin_user):
        response = export_domain(tprm_domain["domain"], admin_user)
        assert response.status_code == 200

        json_dump = process_uploaded_file(io.BytesIO(response.content))
        result = import_objects(
            json_dump,
            domain_name="TPRM Imported",
            load_missing_libraries=True,
            user=admin_user,
        )
        assert result["message"] == "Import successful"

        imported = Folder.objects.get(
            name="TPRM Imported", content_type=Folder.ContentType.DOMAIN
        )

        # Entities: provider, parent, subcontractor land flat in the new
        # domain; the builtin main org does not travel.
        imported_entities = Entity.objects.filter(folder=imported)
        assert imported_entities.count() == 3
        provider = imported_entities.get(ref_id="PROV-1")
        parent = imported_entities.get(ref_id="PARENT-1")
        subcontractor = imported_entities.get(ref_id="SUB-1")

        # parent_entity link (in-scope self-reference) is preserved.
        assert provider.parent_entity == parent

        # Solution FKs remapped into the new domain; the builtin recipient is
        # dropped to null (graceful degradation).
        solution = Solution.objects.get(ref_id="SOL-1", provider_entity=provider)
        assert solution.recipient_entity is None
        imported_asset = Asset.objects.get(folder=imported)
        assert list(solution.assets.all()) == [imported_asset]

        # Subcontracting chain remapped.
        subcontract = SolutionSubcontractor.objects.get(solution=solution)
        assert subcontract.subcontractor == subcontractor

        # Representative attached to the imported provider.
        assert Representative.objects.filter(ref_id="REP-1", entity=provider).exists()

        # Entity assessment: required entity FK + solutions M2M remapped.
        ea = EntityAssessment.objects.get(folder=imported)
        assert ea.entity == provider
        assert list(ea.solutions.all()) == [solution]

        # Contract in the new domain, solutions M2M remapped.
        contract = Contract.objects.get(folder=imported, ref_id="CONTRACT-1")
        assert list(contract.solutions.all()) == [solution]


# ============ Import error reporting ============


class TestImportValidationErrorReporting:
    @pytest.mark.django_db
    def test_validation_errors_are_surfaced_not_swallowed(self, admin_user):
        """A dump with an invalid object must raise a ValidationError carrying
        the real per-object errors, not the opaque "errorOccuredDuringImport"
        the old AttributeError crash degraded into."""
        parsed = {
            "meta": {
                "media_version": settings.VERSION,
                "schema_version": settings.SCHEMA_VERSION,
                "exported_at": "2026-01-01T00:00:00Z",
            },
            # core.asset with no name fails the ImportExport serializer.
            "objects": [
                {"model": "core.asset", "id": "aaaaaaaaaaaa", "fields": {}},
            ],
        }

        with pytest.raises(DjangoValidationError) as exc_info:
            import_objects(
                parsed,
                domain_name="Broken Import",
                load_missing_libraries=True,
                user=admin_user,
            )

        message_dict = exc_info.value.message_dict
        assert "validation_errors" in message_dict
        assert "non_field_errors" not in message_dict
        # The flattened message must keep the model, the offending object id and
        # the field-level serializer detail so failures stay actionable.
        assert any(
            "core.asset" in msg and "aaaaaaaaaaaa" in msg and "name" in msg
            for msg in message_dict["validation_errors"]
        )


# ============ Entity-assessment audit ============


class TestEntityAssessmentAuditRoundTrip:
    @pytest.mark.django_db
    def test_audit_in_enclave_is_exported_and_relinked(
        self, root_folder, admin_user, framework_fixture
    ):
        """The audit of an entity assessment lives in an enclave sub-folder
        (excluded from the exported folders) and inherits the assessment's empty
        perimeter, so it used to be dropped entirely."""
        domain = Folder.objects.create(
            name="Audit Source",
            content_type=Folder.ContentType.DOMAIN,
            parent_folder=root_folder,
        )
        provider = Entity.objects.create(
            name="Audited Provider", ref_id="PROV-A", folder=domain
        )
        entity_assessment = EntityAssessment.objects.create(
            name="Provider audit assessment", folder=domain, entity=provider
        )

        # Built the way the TPRM flow builds it: enclave folder, no perimeter.
        audit = ComplianceAssessment.objects.create(
            name="Provider audit",
            framework=framework_fixture,
            perimeter=entity_assessment.perimeter,
            field_visibility=build_initial_field_visibility(framework_fixture),
        )
        enclave = Folder.objects.create(
            content_type=Folder.ContentType.ENCLAVE,
            name=f"{provider.name}/{entity_assessment.name}",
            parent_folder=domain,
        )
        audit.folder = enclave
        audit.save()
        audit.create_requirement_assessments()
        entity_assessment.compliance_assessment = audit
        entity_assessment.save()

        requirement_assessment = audit.requirement_assessments.first()
        evidence = Evidence.objects.create(name="Audit proof", folder=enclave)
        requirement_assessment.evidences.add(evidence)
        # Answer a real library-backed question: questions and their choices
        # travel as URN references, never as exported rows.
        answered_ra = (
            audit.requirement_assessments.filter(requirement__questions__isnull=False)
            .distinct()
            .first()
        )
        question = answered_ra.requirement.questions.first()
        choice = question.choices.first()
        # create_requirement_assessments() already seeded an empty answer per
        # question, so fill one in rather than adding a duplicate row.
        answer = Answer.objects.get(
            requirement_assessment=answered_ra, question=question
        )
        answer.selected_choices.set([choice])
        source_ra_count = audit.requirement_assessments.count()
        source_answer_count = Answer.objects.filter(
            requirement_assessment__compliance_assessment=audit
        ).count()

        assert audit.perimeter is None
        assert source_ra_count > 0

        scope = get_domain_export_objects(domain)
        assert audit in scope["complianceassessment"]
        assert evidence in scope["evidence"]
        assert scope["requirementassessment"].count() == source_ra_count

        response = export_domain(domain, admin_user)
        json_dump = process_uploaded_file(io.BytesIO(response.content))
        import_objects(
            json_dump,
            domain_name="Audit Imported",
            load_missing_libraries=True,
            user=admin_user,
        )

        imported = Folder.objects.get(
            name="Audit Imported", content_type=Folder.ContentType.DOMAIN
        )
        imported_ea = EntityAssessment.objects.get(folder=imported)

        # The audit came back in its own enclave, carried by the dump rather
        # than rebuilt: same name, re-parented under the new domain.
        imported_audit = imported_ea.compliance_assessment
        assert imported_audit is not None
        assert imported_audit.folder.content_type == Folder.ContentType.ENCLAVE
        assert imported_audit.folder.parent_folder == imported
        assert imported_audit.folder.name == enclave.name
        assert imported_audit.folder != enclave
        assert imported_audit.framework == framework_fixture
        assert imported_audit.requirement_assessments.count() == source_ra_count
        assert set(
            imported_audit.requirement_assessments.values_list("folder", flat=True)
        ) == {imported_audit.folder_id}
        imported_answers = Answer.objects.filter(
            requirement_assessment__compliance_assessment=imported_audit
        )
        assert imported_answers.count() == source_answer_count
        assert set(imported_answers.values_list("folder", flat=True)) == {
            imported_audit.folder_id
        }
        # The question and its selected choice resolved from their library URNs.
        imported_answer = imported_answers.get(question__urn=question.urn)
        assert list(imported_answer.selected_choices.values_list("urn", flat=True)) == [
            choice.urn
        ]

        # Granting a representative access must not reach beyond the enclave.
        respondent = User.objects.create(email="rep@provider.test", is_third_party=True)
        imported_ea.representatives.add(respondent)
        grant_respondent_access(imported_ea)
        granted = {
            folder
            for ra in RoleAssignment.get_role_assignments_from_user(respondent)
            for folder in ra.perimeter_folders.all()
        }
        assert granted == {imported_audit.folder}
        assert imported not in granted

        imported_evidence_names = [
            e.name
            for ra in imported_audit.requirement_assessments.all()
            for e in ra.evidences.all()
        ]
        assert any(name.startswith("Audit proof") for name in imported_evidence_names)

    @pytest.mark.django_db
    def test_successive_rounds_share_one_enclave(
        self, root_folder, admin_user, framework_fixture
    ):
        """One workspace per entity, not per round: two assessments of the same
        entity must come back sharing a single enclave."""
        domain = Folder.objects.create(
            name="Rounds Source",
            content_type=Folder.ContentType.DOMAIN,
            parent_folder=root_folder,
        )
        provider = Entity.objects.create(
            name="Recurring Provider", ref_id="PROV-R", folder=domain
        )
        enclave = Folder.objects.create(
            content_type=Folder.ContentType.ENCLAVE,
            name=provider.name,
            parent_folder=domain,
        )
        for round_name in ("Round 1", "Round 2"):
            entity_assessment = EntityAssessment.objects.create(
                name=round_name, folder=domain, entity=provider
            )
            audit = ComplianceAssessment.objects.create(
                name=round_name,
                framework=framework_fixture,
                field_visibility=build_initial_field_visibility(framework_fixture),
            )
            audit.folder = enclave
            audit.save()
            entity_assessment.compliance_assessment = audit
            entity_assessment.save()

        response = export_domain(domain, admin_user)
        json_dump = process_uploaded_file(io.BytesIO(response.content))
        import_objects(
            json_dump,
            domain_name="Rounds Imported",
            load_missing_libraries=True,
            user=admin_user,
        )

        imported = Folder.objects.get(
            name="Rounds Imported", content_type=Folder.ContentType.DOMAIN
        )
        imported_eas = EntityAssessment.objects.filter(folder=imported)
        assert imported_eas.count() == 2
        enclaves = {ea.compliance_assessment.folder for ea in imported_eas}
        assert len(enclaves) == 1
        imported_enclave = next(iter(enclaves))
        assert imported_enclave.parent_folder == imported


# ============ Flattened name collisions ============


class TestFlattenedNameCollision:
    @pytest.mark.django_db
    def test_same_named_objects_in_two_subdomains_import(self, root_folder, admin_user):
        """Two sub-domains each holding a same-named evidence collide once the
        import flattens them into one folder; the clash must be de-duplicated
        instead of aborting the whole import."""
        domain = Folder.objects.create(
            name="Collision Source",
            content_type=Folder.ContentType.DOMAIN,
            parent_folder=root_folder,
        )
        sub_a = Folder.objects.create(
            name="Sub A",
            content_type=Folder.ContentType.DOMAIN,
            parent_folder=domain,
        )
        sub_b = Folder.objects.create(
            name="Sub B",
            content_type=Folder.ContentType.DOMAIN,
            parent_folder=domain,
        )
        Evidence.objects.create(name="Shared proof", folder=sub_a)
        Evidence.objects.create(name="Shared proof", folder=sub_b)

        response = export_domain(domain, admin_user)
        json_dump = process_uploaded_file(io.BytesIO(response.content))
        import_objects(
            json_dump,
            domain_name="Collision Imported",
            load_missing_libraries=True,
            user=admin_user,
        )

        imported = Folder.objects.get(
            name="Collision Imported", content_type=Folder.ContentType.DOMAIN
        )
        names = list(
            Evidence.objects.filter(folder=imported).values_list("name", flat=True)
        )
        assert len(names) == 2
        assert len(set(names)) == 2
        assert all(name.startswith("Shared proof") for name in names)

    @pytest.mark.django_db
    def test_near_max_length_names_are_truncated_not_grown(
        self, root_folder, admin_user
    ):
        """The UUID suffix must not push a de-duplicated name past max_length."""
        max_length = Evidence._meta.get_field("name").max_length
        long_name = "L" * (max_length - 10)
        domain = Folder.objects.create(
            name="Long Name Source",
            content_type=Folder.ContentType.DOMAIN,
            parent_folder=root_folder,
        )
        for sub_name in ("Sub A", "Sub B"):
            sub = Folder.objects.create(
                name=sub_name,
                content_type=Folder.ContentType.DOMAIN,
                parent_folder=domain,
            )
            Evidence.objects.create(name=long_name, folder=sub)

        response = export_domain(domain, admin_user)
        json_dump = process_uploaded_file(io.BytesIO(response.content))
        import_objects(
            json_dump,
            domain_name="Long Name Imported",
            load_missing_libraries=True,
            user=admin_user,
        )

        imported = Folder.objects.get(
            name="Long Name Imported", content_type=Folder.ContentType.DOMAIN
        )
        names = list(
            Evidence.objects.filter(folder=imported).values_list("name", flat=True)
        )
        assert len(set(names)) == 2
        assert all(len(name) <= max_length for name in names)


# ============ Cross-domain scope ============


class TestCrossDomainCampaignScope:
    @pytest.mark.django_db
    def test_campaign_perimeter_does_not_drag_another_domain(
        self, root_folder, framework_fixture
    ):
        """Campaign.perimeters is unrestricted, so a campaign can target another
        domain. Its perimeter row travels so the M2M resolves on import, but that
        domain's assessments must never enter the export."""
        domain_d = Folder.objects.create(
            name="Campaign Domain",
            content_type=Folder.ContentType.DOMAIN,
            parent_folder=root_folder,
        )
        domain_e = Folder.objects.create(
            name="Foreign Domain",
            content_type=Folder.ContentType.DOMAIN,
            parent_folder=root_folder,
        )

        foreign_perimeter = Perimeter.objects.create(
            name="Foreign Perimeter", folder=domain_e
        )
        foreign_audit = ComplianceAssessment.objects.create(
            name="Foreign audit",
            framework=framework_fixture,
            perimeter=foreign_perimeter,
            folder=domain_e,
            field_visibility=build_initial_field_visibility(framework_fixture),
        )
        foreign_audit.create_requirement_assessments()

        campaign = Campaign.objects.create(name="Cross campaign", folder=domain_d)
        campaign.perimeters.add(foreign_perimeter)

        data = get_domain_export_objects(domain_d)

        assert campaign in data["campaign"]
        # The perimeter row travels: the campaign's M2M has to resolve on import.
        assert foreign_perimeter in data["perimeter"]
        # Nothing else from the foreign domain does.
        assert foreign_audit not in data["complianceassessment"]
        assert (
            not data["requirementassessment"]
            .filter(compliance_assessment=foreign_audit)
            .exists()
        )
        assert (
            not data["answer"]
            .filter(requirement_assessment__compliance_assessment=foreign_audit)
            .exists()
        )


# ============ Questionnaire evidence placement ============


class TestQuestionnaireEvidencePlacement:
    @pytest.mark.django_db
    def test_owned_evidence_moves_to_enclave_shared_evidence_stays(
        self, root_folder, admin_user, framework_fixture
    ):
        """A respondent is granted the enclave only, so evidence the
        questionnaire owns must land there. Evidence shared with the domain stays
        put, otherwise the import would expose it to the third party."""
        domain = Folder.objects.create(
            name="Evidence Source",
            content_type=Folder.ContentType.DOMAIN,
            parent_folder=root_folder,
        )
        provider = Entity.objects.create(
            name="Evidence Provider", ref_id="PROV-E", folder=domain
        )
        entity_assessment = EntityAssessment.objects.create(
            name="Evidence assessment", folder=domain, entity=provider
        )
        audit = ComplianceAssessment.objects.create(
            name="Evidence audit",
            framework=framework_fixture,
            perimeter=entity_assessment.perimeter,
            field_visibility=build_initial_field_visibility(framework_fixture),
        )
        enclave = Folder.objects.create(
            content_type=Folder.ContentType.ENCLAVE,
            name=provider.name,
            parent_folder=domain,
        )
        audit.folder = enclave
        audit.save()
        audit.create_requirement_assessments()
        entity_assessment.compliance_assessment = audit
        entity_assessment.save()

        requirement_assessment = audit.requirement_assessments.first()
        owned = Evidence.objects.create(name="Questionnaire proof", folder=enclave)
        shared = Evidence.objects.create(name="Shared proof", folder=domain)
        # Also the assessment's own summary evidence: still the questionnaire's,
        # so being pointed at by *this* entity assessment must not hold it back.
        summary = Evidence.objects.create(name="Summary proof", folder=enclave)
        entity_assessment.evidence = summary
        entity_assessment.save()
        requirement_assessment.evidences.add(owned, shared, summary)
        # The shared one is also a domain control's evidence, so it must not
        # follow the questionnaire into the enclave.
        control = AppliedControl.objects.create(name="Domain control", folder=domain)
        control.evidences.add(shared)
        # Shared with an internal task instead: also has to stay behind.
        task_shared = Evidence.objects.create(name="Task proof", folder=domain)
        requirement_assessment.evidences.add(task_shared)
        task = TaskTemplate.objects.create(name="Internal task", folder=domain)
        task.evidences.add(task_shared)
        # Attached straight to the audit, never through a requirement: it lives
        # in the enclave, which no exported folder covers.
        direct = Evidence.objects.create(name="Direct proof", folder=enclave)
        audit.evidences.add(direct)
        # Homonyms across the boundary: dedup fires in the flat folder, but the
        # one landing in the enclave must not keep a UUID the respondent sees.
        enclave_dup = Evidence.objects.create(name="Duplicate proof", folder=enclave)
        requirement_assessment.evidences.add(enclave_dup)
        domain_dup = Evidence.objects.create(name="Duplicate proof", folder=domain)
        control.evidences.add(domain_dup)

        response = export_domain(domain, admin_user)
        json_dump = process_uploaded_file(io.BytesIO(response.content))
        import_objects(
            json_dump,
            domain_name="Evidence Imported",
            load_missing_libraries=True,
            user=admin_user,
        )

        imported = Folder.objects.get(
            name="Evidence Imported", content_type=Folder.ContentType.DOMAIN
        )
        imported_audit = EntityAssessment.objects.get(
            folder=imported
        ).compliance_assessment
        assert imported_audit.folder.content_type == Folder.ContentType.ENCLAVE

        def imported_evidence(prefix):
            return (
                Evidence.objects.filter(
                    name__startswith=prefix,
                    requirement_assessments__compliance_assessment=imported_audit,
                )
                .distinct()
                .get()
            )

        assert imported_evidence("Questionnaire proof").folder == imported_audit.folder
        assert imported_evidence("Summary proof").folder == imported_audit.folder
        assert imported_evidence("Shared proof").folder == imported
        assert imported_evidence("Task proof").folder == imported

        imported_direct = Evidence.objects.filter(
            name__startswith="Direct proof", compliance_assessments=imported_audit
        ).distinct()
        assert imported_direct.count() == 1
        assert imported_direct.get().folder == imported_audit.folder

        # Exact name: dedup happened in the flat folder, the enclave frees it.
        assert Evidence.objects.filter(
            name="Duplicate proof", folder=imported_audit.folder
        ).exists()

    @pytest.mark.django_db
    def test_assessment_only_evidence_stays_in_the_domain(
        self, root_folder, admin_user, framework_fixture
    ):
        """EntityAssessment.evidence is often an internal analysis the vendor
        never sees. Being pointed at by the assessment is not, on its own, a
        reason to move it into the respondent's enclave."""
        domain = Folder.objects.create(
            name="Internal Source",
            content_type=Folder.ContentType.DOMAIN,
            parent_folder=root_folder,
        )
        provider = Entity.objects.create(
            name="Internal Provider", ref_id="PROV-I", folder=domain
        )
        entity_assessment = EntityAssessment.objects.create(
            name="Internal assessment", folder=domain, entity=provider
        )
        audit = ComplianceAssessment.objects.create(
            name="Internal questionnaire",
            framework=framework_fixture,
            field_visibility=build_initial_field_visibility(framework_fixture),
        )
        audit.folder = Folder.objects.create(
            content_type=Folder.ContentType.ENCLAVE,
            name=provider.name,
            parent_folder=domain,
        )
        audit.save()
        audit.create_requirement_assessments()
        entity_assessment.compliance_assessment = audit
        # Referenced by the assessment only: never joined to the questionnaire.
        internal = Evidence.objects.create(name="Internal analysis", folder=domain)
        entity_assessment.evidence = internal
        entity_assessment.save()

        response = export_domain(domain, admin_user)
        json_dump = process_uploaded_file(io.BytesIO(response.content))
        import_objects(
            json_dump,
            domain_name="Internal Imported",
            load_missing_libraries=True,
            user=admin_user,
        )

        imported = Folder.objects.get(
            name="Internal Imported", content_type=Folder.ContentType.DOMAIN
        )
        imported_ea = EntityAssessment.objects.get(folder=imported)
        assert imported_ea.compliance_assessment.folder != imported
        assert imported_ea.evidence is not None
        assert imported_ea.evidence.folder == imported

    @pytest.mark.django_db
    def test_same_named_audits_keep_their_version(
        self, root_folder, admin_user, framework_fixture
    ):
        """clean() flags every fields_to_check field it re-checks alone, and
        version is always "1.0", so dedup must suffix the name only."""
        domain = Folder.objects.create(
            name="Version Source",
            content_type=Folder.ContentType.DOMAIN,
            parent_folder=root_folder,
        )
        for ref in ("A", "B"):
            provider = Entity.objects.create(
                name=f"Version Provider {ref}", ref_id=f"P-{ref}", folder=domain
            )
            entity_assessment = EntityAssessment.objects.create(
                name=f"Assessment {ref}", folder=domain, entity=provider
            )
            audit = ComplianceAssessment.objects.create(
                name="Security questionnaire",
                framework=framework_fixture,
                field_visibility=build_initial_field_visibility(framework_fixture),
            )
            audit.folder = Folder.objects.create(
                content_type=Folder.ContentType.ENCLAVE,
                name=provider.name,
                parent_folder=domain,
            )
            audit.save()
            entity_assessment.compliance_assessment = audit
            entity_assessment.save()

        response = export_domain(domain, admin_user)
        json_dump = process_uploaded_file(io.BytesIO(response.content))
        import_objects(
            json_dump,
            domain_name="Version Imported",
            load_missing_libraries=True,
            user=admin_user,
        )

        imported = Folder.objects.get(
            name="Version Imported", content_type=Folder.ContentType.DOMAIN
        )
        imported_audits = ComplianceAssessment.objects.filter(
            folder__parent_folder=imported
        )
        assert imported_audits.count() == 2
        assert set(imported_audits.values_list("version", flat=True)) == {"1.0"}
        # Deduped against the flat folder, but they end up in separate enclaves:
        # both keep the title they were exported with.
        assert set(imported_audits.values_list("name", flat=True)) == {
            "Security questionnaire"
        }
        assert len({audit.folder_id for audit in imported_audits}) == 2

    @pytest.mark.django_db
    def test_evidence_shared_between_rounds_follows_the_common_enclave(
        self, root_folder, admin_user, framework_fixture
    ):
        """Successive rounds for one entity share an enclave and can share
        evidence (baseline reuse). Belonging to a second questionnaire of the
        same workspace must not strand it in the domain."""
        domain = Folder.objects.create(
            name="Rounds Evidence Source",
            content_type=Folder.ContentType.DOMAIN,
            parent_folder=root_folder,
        )
        provider = Entity.objects.create(
            name="Rounds Provider", ref_id="PROV-RR", folder=domain
        )
        enclave = Folder.objects.create(
            content_type=Folder.ContentType.ENCLAVE,
            name=provider.name,
            parent_folder=domain,
        )
        reused = Evidence.objects.create(name="Reused proof", folder=enclave)

        for round_name in ("Round 1", "Round 2"):
            entity_assessment = EntityAssessment.objects.create(
                name=round_name, folder=domain, entity=provider
            )
            audit = ComplianceAssessment.objects.create(
                name=round_name,
                framework=framework_fixture,
                field_visibility=build_initial_field_visibility(framework_fixture),
            )
            audit.folder = enclave
            audit.save()
            audit.create_requirement_assessments()
            entity_assessment.compliance_assessment = audit
            entity_assessment.save()
            audit.requirement_assessments.first().evidences.add(reused)

        response = export_domain(domain, admin_user)
        json_dump = process_uploaded_file(io.BytesIO(response.content))
        import_objects(
            json_dump,
            domain_name="Rounds Evidence Imported",
            load_missing_libraries=True,
            user=admin_user,
        )

        imported = Folder.objects.get(
            name="Rounds Evidence Imported", content_type=Folder.ContentType.DOMAIN
        )
        imported_enclaves = {
            entity_assessment.compliance_assessment.folder
            for entity_assessment in EntityAssessment.objects.filter(folder=imported)
        }
        assert len(imported_enclaves) == 1
        common_enclave = imported_enclaves.pop()

        imported_reused = (
            Evidence.objects.filter(
                name__startswith="Reused proof",
                requirement_assessments__compliance_assessment__folder=common_enclave,
            )
            .distinct()
            .get()
        )
        assert imported_reused.folder == common_enclave


# ============ Exported enclaves ============


class TestExportedEnclaves:
    @pytest.mark.django_db
    def test_enclaves_travel_but_domains_do_not(self, root_folder, framework_fixture):
        """Enclaves carry who may see what, so they are exported. Domain folders
        are not: that is what still flattens sub-domains away on Community."""
        domain = Folder.objects.create(
            name="Carried Source",
            content_type=Folder.ContentType.DOMAIN,
            parent_folder=root_folder,
        )
        sub_domain = Folder.objects.create(
            name="Carried Sub",
            content_type=Folder.ContentType.DOMAIN,
            parent_folder=domain,
        )
        enclave = Folder.objects.create(
            name="Carried Enclave",
            content_type=Folder.ContentType.ENCLAVE,
            parent_folder=domain,
        )

        data = get_domain_export_objects(domain)

        assert enclave in data["folder"]
        assert domain not in data["folder"]
        assert sub_domain not in data["folder"]

    @pytest.mark.django_db
    def test_dump_carrying_a_domain_folder_is_rejected(self, root_folder, admin_user):
        """The guard still refuses a foreign dump: only enclaves may travel."""
        parsed = {
            "meta": {
                "media_version": settings.VERSION,
                "schema_version": settings.SCHEMA_VERSION,
                "exported_at": "2026-01-01T00:00:00Z",
            },
            "objects": [
                {
                    "model": "iam.folder",
                    "id": "aaaaaaaaaaaa",
                    "fields": {
                        "name": "Smuggled domain",
                        "content_type": Folder.ContentType.DOMAIN,
                        "parent_folder": None,
                    },
                }
            ],
        }

        with pytest.raises(DjangoValidationError) as exc_info:
            import_objects(
                parsed,
                domain_name="Rejected",
                load_missing_libraries=True,
                user=admin_user,
            )
        assert "Dump contains a domain" in str(exc_info.value)
        assert not Folder.objects.filter(name="Rejected").exists()

    @pytest.mark.django_db
    def test_enclave_evidence_lands_in_the_enclave_without_inference(
        self, root_folder, admin_user, framework_fixture
    ):
        """No ownership is derived any more: an evidence sitting in the enclave
        goes back to the enclave, one sitting in the domain stays in the domain,
        even when both hang off the same requirement."""
        domain = Folder.objects.create(
            name="Carried Evidence Source",
            content_type=Folder.ContentType.DOMAIN,
            parent_folder=root_folder,
        )
        provider = Entity.objects.create(
            name="Carried Provider", ref_id="PROV-C", folder=domain
        )
        entity_assessment = EntityAssessment.objects.create(
            name="Carried assessment", folder=domain, entity=provider
        )
        enclave = Folder.objects.create(
            content_type=Folder.ContentType.ENCLAVE,
            name=provider.name,
            parent_folder=domain,
        )
        audit = ComplianceAssessment.objects.create(
            name="Carried audit",
            framework=framework_fixture,
            field_visibility=build_initial_field_visibility(framework_fixture),
        )
        audit.folder = enclave
        audit.save()
        audit.create_requirement_assessments()
        entity_assessment.compliance_assessment = audit
        entity_assessment.save()

        requirement_assessment = audit.requirement_assessments.first()
        in_enclave = Evidence.objects.create(name="Vendor file", folder=enclave)
        in_domain = Evidence.objects.create(name="Internal file", folder=domain)
        requirement_assessment.evidences.add(in_enclave, in_domain)

        response = export_domain(domain, admin_user)
        json_dump = process_uploaded_file(io.BytesIO(response.content))
        import_objects(
            json_dump,
            domain_name="Carried Evidence Imported",
            load_missing_libraries=True,
            user=admin_user,
        )

        imported = Folder.objects.get(
            name="Carried Evidence Imported", content_type=Folder.ContentType.DOMAIN
        )
        imported_audit = EntityAssessment.objects.get(
            folder=imported
        ).compliance_assessment
        imported_enclave = imported_audit.folder
        assert imported_enclave.content_type == Folder.ContentType.ENCLAVE

        def imported_evidence(name):
            return (
                Evidence.objects.filter(
                    name=name,
                    requirement_assessments__compliance_assessment=imported_audit,
                )
                .distinct()
                .get()
            )

        assert imported_evidence("Vendor file").folder == imported_enclave
        assert imported_evidence("Internal file").folder == imported

    @pytest.mark.django_db
    def test_legacy_dump_without_enclaves_still_isolates_the_audit(
        self, root_folder, admin_user, framework_fixture
    ):
        """Dumps predating schema 3 carry no folders, so their questionnaires
        would land flat in the domain — where grant_respondent_access would hand
        the respondent everything. The fallback puts them back in an enclave."""
        domain = Folder.objects.create(
            name="Legacy Source",
            content_type=Folder.ContentType.DOMAIN,
            parent_folder=root_folder,
        )
        provider = Entity.objects.create(
            name="Legacy Provider", ref_id="PROV-L", folder=domain
        )
        entity_assessment = EntityAssessment.objects.create(
            name="Legacy assessment", folder=domain, entity=provider
        )
        audit = ComplianceAssessment.objects.create(
            name="Legacy audit",
            framework=framework_fixture,
            field_visibility=build_initial_field_visibility(framework_fixture),
        )
        audit.folder = Folder.objects.create(
            content_type=Folder.ContentType.ENCLAVE,
            name=provider.name,
            parent_folder=domain,
        )
        audit.save()
        audit.create_requirement_assessments()
        entity_assessment.compliance_assessment = audit
        entity_assessment.save()

        response = export_domain(domain, admin_user)
        json_dump = process_uploaded_file(io.BytesIO(response.content))
        # Drop the folders: that is exactly what an older dump looks like.
        json_dump["meta"]["schema_version"] = 2
        json_dump["objects"] = [
            obj for obj in json_dump["objects"] if obj["model"] != "iam.folder"
        ]
        import_objects(
            json_dump,
            domain_name="Legacy Imported",
            load_missing_libraries=True,
            user=admin_user,
        )

        imported = Folder.objects.get(
            name="Legacy Imported", content_type=Folder.ContentType.DOMAIN
        )
        imported_audit = EntityAssessment.objects.get(
            folder=imported
        ).compliance_assessment
        assert imported_audit.folder.content_type == Folder.ContentType.ENCLAVE
        assert imported_audit.folder.parent_folder == imported
        assert set(
            imported_audit.requirement_assessments.values_list("folder", flat=True)
        ) == {imported_audit.folder_id}
