"""
Tests for DataAsset aggregate
"""

import uuid
from django.test import TestCase

from core.bounded_contexts.privacy.aggregates.data_asset import DataAsset
from core.bounded_contexts.privacy.domain_events import (
    DataAssetCreated,
    DataAssetActivated,
    DataAssetRetired,
)


class DataAssetTests(TestCase):
    """Tests for DataAsset aggregate"""
    
    def test_create_data_asset(self):
        """Test creating a data asset"""
        asset = DataAsset()
        asset.create(
            name="Customer Database",
            description="Database containing customer information",
            data_categories=["contact_details", "financial_data"],
            contains_personal_data=True,
            retention_policy="Retain for 7 years after account closure"
        )
        asset.save()
        
        self.assertEqual(asset.name, "Customer Database")
        self.assertEqual(asset.contains_personal_data, True)
        self.assertEqual(len(asset.data_categories), 2)
        self.assertEqual(asset.lifecycle_state, DataAsset.LifecycleState.DRAFT)
        
        # Check event was raised
        events = asset.get_uncommitted_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "DataAssetCreated")
    
    def test_activate_data_asset(self):
        """Test activating a data asset"""
        asset = DataAsset()
        asset.create(name="Customer Database", contains_personal_data=True)
        asset.save()
        
        asset.activate()
        asset.save()
        
        self.assertEqual(asset.lifecycle_state, DataAsset.LifecycleState.ACTIVE)
        
        # Check event was raised
        events = asset.get_uncommitted_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "DataAssetActivated")
    
    def test_add_data_category(self):
        """Test adding a data category"""
        asset = DataAsset()
        asset.create(name="Customer Database")
        asset.save()
        
        asset.add_data_category("contact_details")
        asset.save()
        
        self.assertIn("contact_details", asset.data_categories)
    
    def test_add_asset(self):
        """Test adding an asset that stores this data"""
        asset = DataAsset()
        asset.create(name="Customer Database")
        asset.save()
        
        storage_asset_id = uuid.uuid4()
        asset.add_asset(storage_asset_id)
        asset.save()
        
        self.assertIn(storage_asset_id, asset.assetIds)

