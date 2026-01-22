"""
Tests for ServiceContract association
"""

import uuid
from datetime import date, timedelta
from django.test import TestCase
from django.core.exceptions import ValidationError

from core.bounded_contexts.asset_and_service.associations.service_contract import ServiceContract
from core.bounded_contexts.asset_and_service.domain_events import (
    ServiceContractEstablished,
    ServiceContractRenewed,
    ServiceContractExpired,
)


class ServiceContractTests(TestCase):
    """Tests for ServiceContract association"""
    
    def test_establish_contract(self):
        """Test establishing a service contract"""
        contract = ServiceContract()
        service_id = uuid.uuid4()
        third_party_id = uuid.uuid4()
        
        contract.establish(
            service_id=service_id,
            third_party_id=third_party_id,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=365),
            key_terms="SLA: 99.9% uptime"
        )
        contract.save()
        
        self.assertEqual(contract.serviceId, service_id)
        self.assertEqual(contract.thirdPartyId, third_party_id)
        self.assertEqual(contract.lifecycle_state, ServiceContract.LifecycleState.ACTIVE)
        
        # Check event was raised
        events = contract.get_uncommitted_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "ServiceContractEstablished")
    
    def test_renew_contract(self):
        """Test renewing a service contract"""
        contract = ServiceContract()
        contract.establish(
            service_id=uuid.uuid4(),
            third_party_id=uuid.uuid4(),
            start_date=date.today(),
            end_date=date.today() + timedelta(days=365)
        )
        contract.save()
        
        new_end_date = date.today() + timedelta(days=730)
        contract.renew(new_end_date)
        contract.save()
        
        self.assertEqual(contract.end_date, new_end_date)
        
        # Check event was raised
        events = contract.get_uncommitted_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "ServiceContractRenewed")
    
    def test_expire_contract(self):
        """Test expiring a service contract"""
        contract = ServiceContract()
        contract.establish(
            service_id=uuid.uuid4(),
            third_party_id=uuid.uuid4(),
            start_date=date.today() - timedelta(days=365),
            end_date=date.today()
        )
        contract.save()
        
        contract.expire()
        contract.save()
        
        self.assertEqual(contract.lifecycle_state, ServiceContract.LifecycleState.EXPIRED)
        
        # Check event was raised
        events = contract.get_uncommitted_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "ServiceContractExpired")
    
    def test_is_active(self):
        """Test checking if contract is active"""
        contract = ServiceContract()
        contract.establish(
            service_id=uuid.uuid4(),
            third_party_id=uuid.uuid4(),
            start_date=date.today() - timedelta(days=1),
            end_date=date.today() + timedelta(days=1)
        )
        contract.save()
        
        self.assertTrue(contract.is_active())
        
        # Test expired contract
        contract.expire()
        contract.save()
        self.assertFalse(contract.is_active())
    
    def test_needs_renewal(self):
        """Test checking if contract needs renewal"""
        contract = ServiceContract()
        contract.establish(
            service_id=uuid.uuid4(),
            third_party_id=uuid.uuid4(),
            start_date=date.today() - timedelta(days=300),
            end_date=date.today() + timedelta(days=20)  # Within 30 days
        )
        contract.save()
        
        self.assertTrue(contract.needs_renewal())

