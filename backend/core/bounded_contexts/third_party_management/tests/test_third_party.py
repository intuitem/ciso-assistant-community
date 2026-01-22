"""
Tests for ThirdParty aggregate
"""

import uuid
from django.test import TestCase

from core.bounded_contexts.third_party_management.aggregates.third_party import ThirdParty
from core.bounded_contexts.third_party_management.domain_events import (
    ThirdPartyCreated,
    ThirdPartyActivated,
    ThirdPartyOffboardingStarted,
    ThirdPartyArchived,
)


class ThirdPartyTests(TestCase):
    """Tests for ThirdParty aggregate"""
    
    def test_create_third_party(self):
        """Test creating a third party"""
        third_party = ThirdParty()
        third_party.create(
            name="Cloud Provider Inc",
            description="Primary cloud infrastructure provider",
            criticality="high"
        )
        third_party.save()
        
        self.assertEqual(third_party.name, "Cloud Provider Inc")
        self.assertEqual(third_party.criticality, "high")
        self.assertEqual(third_party.lifecycle_state, ThirdParty.LifecycleState.PROSPECT)
        
        # Check event was raised
        events = third_party.get_uncommitted_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "ThirdPartyCreated")
    
    def test_activate_third_party(self):
        """Test activating a third party"""
        third_party = ThirdParty()
        third_party.create(name="Cloud Provider Inc")
        third_party.save()
        
        third_party.activate()
        third_party.save()
        
        self.assertEqual(third_party.lifecycle_state, ThirdParty.LifecycleState.ACTIVE)
        
        # Check events were raised (Activated + LifecycleChanged)
        events = third_party.get_uncommitted_events()
        self.assertEqual(len(events), 2)
        event_types = [e.event_type for e in events]
        self.assertIn("ThirdPartyActivated", event_types)
        self.assertIn("ThirdPartyLifecycleChanged", event_types)
    
    def test_start_offboarding(self):
        """Test starting offboarding"""
        third_party = ThirdParty()
        third_party.create(name="Cloud Provider Inc")
        third_party.save()
        third_party.activate()
        third_party.save()
        
        third_party.start_offboarding()
        third_party.save()
        
        self.assertEqual(third_party.lifecycle_state, ThirdParty.LifecycleState.OFFBOARDING)
    
    def test_add_service(self):
        """Test adding a service"""
        third_party = ThirdParty()
        third_party.create(name="Cloud Provider Inc")
        third_party.save()
        
        service_id = uuid.uuid4()
        third_party.add_service(service_id)
        third_party.save()
        
        self.assertIn(service_id, third_party.serviceIds)
    
    def test_add_contract(self):
        """Test adding a contract"""
        third_party = ThirdParty()
        third_party.create(name="Cloud Provider Inc")
        third_party.save()
        
        contract_id = uuid.uuid4()
        third_party.add_contract(contract_id)
        third_party.save()
        
        self.assertIn(contract_id, third_party.contractIds)

