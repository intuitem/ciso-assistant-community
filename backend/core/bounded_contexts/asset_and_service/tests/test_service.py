"""
Tests for Service aggregate
"""

import uuid
from django.test import TestCase

from core.bounded_contexts.asset_and_service.aggregates.service import Service
from core.bounded_contexts.asset_and_service.domain_events import (
    ServiceCreated,
    ServiceOperational,
    ServiceRetired,
)


class ServiceTests(TestCase):
    """Tests for Service aggregate"""
    
    def test_create_service(self):
        """Test creating a service"""
        service = Service()
        service.create(
            name="Web Hosting Service",
            description="Hosting service for web applications",
            ref_id="WHS-001"
        )
        service.save()
        
        self.assertEqual(service.name, "Web Hosting Service")
        self.assertEqual(service.lifecycle_state, Service.LifecycleState.DRAFT)
        self.assertEqual(service.ref_id, "WHS-001")
        
        # Check event was raised
        events = service.get_uncommitted_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "ServiceCreated")
    
    def test_make_operational(self):
        """Test making a service operational"""
        service = Service()
        service.create(name="Web Hosting Service")
        service.save()
        
        service.make_operational()
        service.save()
        
        self.assertEqual(service.lifecycle_state, Service.LifecycleState.OPERATIONAL)
        
        # Check event was raised
        events = service.get_uncommitted_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "ServiceOperational")
    
    def test_retire_service(self):
        """Test retiring a service"""
        service = Service()
        service.create(name="Web Hosting Service")
        service.save()
        service.make_operational()
        service.save()
        
        service.retire()
        service.save()
        
        self.assertEqual(service.lifecycle_state, Service.LifecycleState.RETIRED)
        
        # Check event was raised
        events = service.get_uncommitted_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "ServiceRetired")
    
    def test_link_asset(self):
        """Test linking an asset to a service"""
        service = Service()
        service.create(name="Web Hosting Service")
        service.save()
        
        asset_id = uuid.uuid4()
        service.link_asset(asset_id)
        service.save()
        
        self.assertIn(asset_id, service.assetIds)

