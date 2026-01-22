"""
Tests for Asset aggregate
"""

import uuid
from django.test import TestCase

from core.bounded_contexts.asset_and_service.aggregates.asset import Asset
from core.bounded_contexts.asset_and_service.domain_events import (
    AssetCreated,
    AssetActivated,
    AssetArchived,
    ControlAssignedToAsset,
    RiskAssignedToAsset,
)


class AssetTests(TestCase):
    """Tests for Asset aggregate"""
    
    def test_create_asset(self):
        """Test creating an asset"""
        asset = Asset()
        asset.create(
            name="Web Server",
            description="Production web server",
            ref_id="WS-001"
        )
        asset.save()
        
        self.assertEqual(asset.name, "Web Server")
        self.assertEqual(asset.lifecycle_state, Asset.LifecycleState.DRAFT)
        self.assertEqual(asset.ref_id, "WS-001")
        
        # Check event was raised
        events = asset.get_uncommitted_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "AssetCreated")
    
    def test_activate_asset(self):
        """Test activating an asset"""
        asset = Asset()
        asset.create(name="Web Server")
        asset.save()
        
        asset.activate()
        asset.save()
        
        self.assertEqual(asset.lifecycle_state, Asset.LifecycleState.IN_USE)
        
        # Check event was raised
        events = asset.get_uncommitted_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "AssetActivated")
    
    def test_archive_asset(self):
        """Test archiving an asset"""
        asset = Asset()
        asset.create(name="Web Server")
        asset.save()
        asset.activate()
        asset.save()
        
        asset.archive()
        asset.save()
        
        self.assertEqual(asset.lifecycle_state, Asset.LifecycleState.ARCHIVED)
        
        # Check event was raised
        events = asset.get_uncommitted_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "AssetArchived")
    
    def test_assign_control(self):
        """Test assigning a control to an asset"""
        asset = Asset()
        asset.create(name="Web Server")
        asset.save()
        
        control_id = uuid.uuid4()
        asset.assign_control(control_id)
        asset.save()
        
        self.assertIn(control_id, asset.controlIds)
        
        # Check event was raised
        events = asset.get_uncommitted_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "ControlAssignedToAsset")
    
    def test_assign_risk(self):
        """Test assigning a risk to an asset"""
        asset = Asset()
        asset.create(name="Web Server")
        asset.save()
        
        risk_id = uuid.uuid4()
        asset.assign_risk(risk_id)
        asset.save()
        
        self.assertIn(risk_id, asset.riskIds)
        
        # Check event was raised
        events = asset.get_uncommitted_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "RiskAssignedToAsset")
    
    def test_link_service(self):
        """Test linking a service to an asset"""
        asset = Asset()
        asset.create(name="Web Server")
        asset.save()
        
        service_id = uuid.uuid4()
        asset.link_service(service_id)
        asset.save()
        
        self.assertIn(service_id, asset.serviceIds)
        
        # Check event was raised
        events = asset.get_uncommitted_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "ServiceLinkedToAsset")

