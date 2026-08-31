"""Tests for entity-based campaigns: fan-out, landing rule, scope rules.

See documentation/entities-and-campaigns.md. Internal campaign audits land in
the entity's own folder ("an entity's audits live where the entity lives").
"""

from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from core.models import Campaign, ComplianceAssessment, Framework
from core.serializers import CampaignWriteSerializer
from iam.models import Folder
from tprm.models import Entity, EntityAssessment
from tprm.serializers import EntityWriteSerializer, RepresentativeWriteSerializer
from tprm.services import fan_out_campaign

User = get_user_model()


class MainEntityTests(TestCase):
    def test_get_main_entity_uses_is_main(self):
        main = Entity.get_main_entity()
        if main is None:
            main = Entity.objects.create(
                name="Main",
                folder=Folder.get_root_folder(),
                builtin=True,
                is_main=True,
            )
        self.assertTrue(main.is_main)
        self.assertEqual(Entity.get_main_entity(), main)

    def test_single_main_entity_enforced(self):
        from django.db import IntegrityError

        if Entity.get_main_entity() is None:
            Entity.objects.create(
                name="Main", folder=Folder.get_root_folder(), is_main=True
            )
        with self.assertRaises(IntegrityError):
            Entity.objects.create(
                name="Second main",
                folder=Folder.get_root_folder(),
                is_main=True,
            )


class InternalFanOutTests(TestCase):
    def setUp(self):
        self.domain = Folder.objects.create(name="Domain")
        self.framework = Framework.objects.create(
            name="Framework A", min_score=0, max_score=100
        )
        self.user = User.objects.create_user(
            email="alice@example.com", password="password"
        )
        self.entity = Entity.objects.create(
            name="BU France", folder=self.domain, scope=Entity.Scope.INTERNAL
        )
        self.entity.default_assignee.add(self.user.actor)
        self.campaign = Campaign.objects.create(
            name="ISO campaign",
            folder=self.domain,
            target_scope=Campaign.TargetScope.INTERNAL,
        )
        self.campaign.frameworks.add(self.framework)
        self.campaign.entities.add(self.entity)

    def test_audit_lands_in_entity_folder_with_authors(self):
        fan_out_campaign(self.campaign)

        audits = ComplianceAssessment.objects.filter(campaign=self.campaign)
        self.assertEqual(audits.count(), 1)
        audit = audits.first()
        self.assertEqual(audit.folder, self.domain)
        self.assertIsNone(audit.perimeter)
        self.assertEqual(
            audit.name, f"ISO campaign - BU France - {self.framework.name}"
        )
        self.assertListEqual(list(audit.authors.all()), [self.user.actor])

    def test_entity_without_assignee_gets_unassigned_audit(self):
        other_domain = Folder.objects.create(name="Other domain")
        entity = Entity.objects.create(
            name="BU Germany", folder=other_domain, scope=Entity.Scope.INTERNAL
        )
        self.campaign.entities.add(entity)

        fan_out_campaign(self.campaign)

        audit = ComplianceAssessment.objects.get(
            campaign=self.campaign, folder=other_domain
        )
        self.assertIsNone(audit.perimeter)
        self.assertEqual(audit.authors.count(), 0)

    def test_matrix_entities_times_frameworks(self):
        framework_b = Framework.objects.create(
            name="Framework B", min_score=0, max_score=100
        )
        self.campaign.frameworks.add(framework_b)
        entity_b = Entity.objects.create(
            name="BU Germany",
            folder=Folder.objects.create(name="DE domain"),
            scope=Entity.Scope.INTERNAL,
        )
        self.campaign.entities.add(entity_b)

        fan_out_campaign(self.campaign)

        self.assertEqual(
            ComplianceAssessment.objects.filter(campaign=self.campaign).count(), 4
        )

    def test_entities_sharing_a_domain_land_side_by_side(self):
        entity_b = Entity.objects.create(
            name="BU Germany", folder=self.domain, scope=Entity.Scope.INTERNAL
        )
        self.campaign.entities.add(entity_b)

        fan_out_campaign(self.campaign)

        audits = ComplianceAssessment.objects.filter(
            campaign=self.campaign, folder=self.domain
        )
        self.assertEqual(audits.count(), 2)
        self.assertSetEqual(
            {audit.name for audit in audits},
            {
                f"ISO campaign - BU France - {self.framework.name}",
                f"ISO campaign - BU Germany - {self.framework.name}",
            },
        )


class ExternalFanOutTests(TestCase):
    def setUp(self):
        self.domain = Folder.objects.create(name="TPRM domain")
        self.framework = Framework.objects.create(
            name="Questionnaire", min_score=0, max_score=100
        )
        self.entity = Entity.objects.create(
            name="Vendor", folder=self.domain, scope=Entity.Scope.EXTERNAL
        )
        self.campaign = Campaign.objects.create(
            name="Vendor campaign",
            folder=self.domain,
            target_scope=Campaign.TargetScope.EXTERNAL,
        )
        self.campaign.frameworks.add(self.framework)
        self.campaign.entities.add(self.entity)

    def test_creates_entity_assessment_with_enclave_audit(self):
        fan_out_campaign(self.campaign)

        assessments = EntityAssessment.objects.filter(entity=self.entity)
        self.assertEqual(assessments.count(), 1)
        assessment = assessments.first()
        self.assertEqual(assessment.folder, self.domain)
        audit = assessment.compliance_assessment
        self.assertIsNotNone(audit)
        self.assertEqual(audit.campaign, self.campaign)
        self.assertEqual(audit.folder.content_type, Folder.ContentType.ENCLAVE)
        self.assertEqual(audit.folder.parent_folder, self.domain)


class CampaignWriteSerializerValidationTests(TestCase):
    def setUp(self):
        self.domain = Folder.objects.create(name="Domain")
        self.framework = Framework.objects.create(
            name="Framework", min_score=0, max_score=100
        )
        self.internal_entity = Entity.objects.create(
            name="BU", folder=self.domain, scope=Entity.Scope.INTERNAL
        )
        self.external_entity = Entity.objects.create(
            name="Vendor", folder=self.domain, scope=Entity.Scope.EXTERNAL
        )

    def _serializer(self, data, instance=None):
        mock_request = MagicMock()
        mock_request.user = MagicMock()
        return CampaignWriteSerializer(
            instance=instance, data=data, context={"request": mock_request}
        )

    def _base_data(self, **overrides):
        data = {
            "name": "Campaign",
            "folder": str(self.domain.id),
            "target_scope": Campaign.TargetScope.INTERNAL,
            "entities": [str(self.internal_entity.id)],
            "frameworks": [str(self.framework.id)],
        }
        data.update(overrides)
        return data

    @patch("core.serializers.BaseModelSerializer._check_m2m_visibility")
    def test_valid_internal_campaign(self, _):
        serializer = self._serializer(self._base_data())
        self.assertTrue(serializer.is_valid(), serializer.errors)

    @patch("core.serializers.BaseModelSerializer._check_m2m_visibility")
    def test_entities_required(self, _):
        serializer = self._serializer(self._base_data(entities=[]))
        self.assertFalse(serializer.is_valid())
        self.assertIn("entities", serializer.errors)

    @patch("core.serializers.BaseModelSerializer._check_m2m_visibility")
    def test_scope_mismatch_refused(self, _):
        serializer = self._serializer(
            self._base_data(entities=[str(self.external_entity.id)])
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("entities", serializer.errors)

    @patch("core.serializers.BaseModelSerializer._check_m2m_visibility")
    def test_mixed_scopes_refused(self, _):
        serializer = self._serializer(
            self._base_data(
                entities=[
                    str(self.internal_entity.id),
                    str(self.external_entity.id),
                ]
            )
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("entities", serializer.errors)

    @patch("core.serializers.BaseModelSerializer._check_m2m_visibility")
    def test_internal_entity_in_root_folder_refused(self, _):
        root = Folder.get_root_folder()
        self.assertIsNotNone(root)
        entity = Entity.objects.create(
            name="Lives in root", folder=root, scope=Entity.Scope.INTERNAL
        )
        serializer = self._serializer(self._base_data(entities=[str(entity.id)]))
        self.assertFalse(serializer.is_valid())
        self.assertIn("entities", serializer.errors)

    @patch("core.serializers.BaseModelSerializer._check_m2m_visibility")
    def test_target_scope_immutable(self, _):
        campaign = Campaign.objects.create(
            name="Existing",
            folder=self.domain,
            target_scope=Campaign.TargetScope.INTERNAL,
        )
        campaign.entities.add(self.internal_entity)
        serializer = self._serializer(
            {"target_scope": Campaign.TargetScope.EXTERNAL},
            instance=campaign,
        )
        serializer.partial = True
        self.assertFalse(serializer.is_valid())
        self.assertIn("target_scope", serializer.errors)


class EntityScopeImmutabilityTests(TestCase):
    def setUp(self):
        self.domain = Folder.objects.create(name="Domain")
        self.entity = Entity.objects.create(
            name="BU", folder=self.domain, scope=Entity.Scope.INTERNAL
        )

    def _serializer(self, data, instance):
        mock_request = MagicMock()
        mock_request.user = MagicMock()
        serializer = EntityWriteSerializer(
            instance=instance, data=data, context={"request": mock_request}
        )
        serializer.partial = True
        return serializer

    @patch("core.serializers.BaseModelSerializer._check_m2m_visibility")
    def test_internal_to_external_refused(self, _):
        serializer = self._serializer(
            {"scope": Entity.Scope.EXTERNAL}, instance=self.entity
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("scope", serializer.errors)

    @patch("core.serializers.BaseModelSerializer._check_m2m_visibility")
    def test_external_to_internal_refused(self, _):
        vendor = Entity.objects.create(
            name="Vendor", folder=self.domain, scope=Entity.Scope.EXTERNAL
        )
        serializer = self._serializer(
            {"scope": Entity.Scope.INTERNAL}, instance=vendor
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("scope", serializer.errors)

    @patch("core.serializers.BaseModelSerializer._check_m2m_visibility")
    def test_same_scope_update_allowed(self, _):
        serializer = self._serializer(
            {"scope": Entity.Scope.INTERNAL, "name": "BU renamed"},
            instance=self.entity,
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

    @patch("core.serializers.BaseModelSerializer._check_m2m_visibility")
    def test_entity_actor_refused_as_default_assignee(self, _):
        other = Entity.objects.create(
            name="Other BU", folder=self.domain, scope=Entity.Scope.INTERNAL
        )
        serializer = self._serializer(
            {"default_assignee": [str(other.actor.id)]}, instance=self.entity
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("default_assignee", serializer.errors)

    @patch("core.serializers.BaseModelSerializer._check_m2m_visibility")
    def test_user_actor_allowed_as_default_assignee(self, _):
        user = User.objects.create_user(
            email="assignee@example.com", password="password"
        )
        serializer = self._serializer(
            {"default_assignee": [str(user.actor.id)]}, instance=self.entity
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)


class RepresentativeScopeTests(TestCase):
    def setUp(self):
        self.domain = Folder.objects.create(name="Domain")

    def _data(self, entity):
        return {
            "email": "rep@example.com",
            "entity": str(entity.id),
            "create_user": False,
        }

    @patch("core.serializers.BaseModelSerializer._check_m2m_visibility")
    def test_refused_on_internal_entity(self, _):
        entity = Entity.objects.create(
            name="BU", folder=self.domain, scope=Entity.Scope.INTERNAL
        )
        mock_request = MagicMock()
        mock_request.user = MagicMock()
        serializer = RepresentativeWriteSerializer(
            data=self._data(entity), context={"request": mock_request}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("entity", serializer.errors)

    @patch("core.serializers.BaseModelSerializer._check_m2m_visibility")
    def test_allowed_on_external_entity(self, _):
        entity = Entity.objects.create(
            name="Vendor", folder=self.domain, scope=Entity.Scope.EXTERNAL
        )
        mock_request = MagicMock()
        mock_request.user = MagicMock()
        serializer = RepresentativeWriteSerializer(
            data=self._data(entity), context={"request": mock_request}
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
