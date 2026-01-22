"""
Tests for DataFlow aggregate
"""

import uuid
from django.test import TestCase

from core.bounded_contexts.privacy.aggregates.data_flow import DataFlow
from core.bounded_contexts.privacy.domain_events import (
    DataFlowEstablished,
    DataFlowChanged,
    DataFlowActivated,
)


class DataFlowTests(TestCase):
    """Tests for DataFlow aggregate"""
    
    def test_create_data_flow(self):
        """Test creating a data flow"""
        flow = DataFlow()
        source_id = uuid.uuid4()
        dest_id = uuid.uuid4()
        
        flow.create(
            name="Customer Data Sync",
            source_system_asset_id=source_id,
            destination_system_asset_id=dest_id,
            purpose="Sync customer data to analytics platform",
            transfer_mechanisms=["API", "SFTP"],
            encryption_in_transit=True
        )
        flow.save()
        
        self.assertEqual(flow.name, "Customer Data Sync")
        self.assertEqual(flow.source_system_asset_id, source_id)
        self.assertEqual(flow.destination_system_asset_id, dest_id)
        self.assertEqual(flow.encryption_in_transit, True)
        self.assertEqual(len(flow.transfer_mechanisms), 2)
        self.assertEqual(flow.lifecycle_state, DataFlow.LifecycleState.DRAFT)
        
        # Check event was raised
        events = flow.get_uncommitted_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "DataFlowEstablished")
    
    def test_activate_data_flow(self):
        """Test activating a data flow"""
        flow = DataFlow()
        flow.create(
            name="Customer Data Sync",
            source_system_asset_id=uuid.uuid4(),
            destination_system_asset_id=uuid.uuid4()
        )
        flow.save()
        
        flow.activate()
        flow.save()
        
        self.assertEqual(flow.lifecycle_state, DataFlow.LifecycleState.ACTIVE)
        
        # Check event was raised
        events = flow.get_uncommitted_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "DataFlowActivated")
    
    def test_change_data_flow(self):
        """Test changing a data flow"""
        flow = DataFlow()
        flow.create(
            name="Customer Data Sync",
            source_system_asset_id=uuid.uuid4(),
            destination_system_asset_id=uuid.uuid4(),
            encryption_in_transit=False
        )
        flow.save()
        
        flow.change({
            "encryption_in_transit": True,
            "purpose": "Updated purpose"
        })
        flow.save()
        
        self.assertEqual(flow.encryption_in_transit, True)
        self.assertEqual(flow.purpose, "Updated purpose")
        
        # Check event was raised
        events = flow.get_uncommitted_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "DataFlowChanged")
    
    def test_add_data_asset(self):
        """Test adding a data asset to a flow"""
        flow = DataFlow()
        flow.create(
            name="Customer Data Sync",
            source_system_asset_id=uuid.uuid4(),
            destination_system_asset_id=uuid.uuid4()
        )
        flow.save()
        
        data_asset_id = uuid.uuid4()
        flow.add_data_asset(data_asset_id)
        flow.save()
        
        self.assertIn(data_asset_id, flow.dataAssetIds)

