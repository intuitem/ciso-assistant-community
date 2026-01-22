"""
Tests for AwarenessCampaign association
"""

import uuid
from datetime import date
from django.test import TestCase

from core.bounded_contexts.security_operations.associations.awareness_campaign import AwarenessCampaign
from core.bounded_contexts.security_operations.domain_events import (
    AwarenessCampaignCreated,
    AwarenessCampaignStarted,
)


class AwarenessCampaignTests(TestCase):
    """Tests for AwarenessCampaign association"""
    
    def test_create_campaign(self):
        """Test creating an awareness campaign"""
        campaign = AwarenessCampaign()
        program_id = uuid.uuid4()
        
        campaign.create(
            program_id=program_id,
            name="Q1 Security Training",
            start_date=date(2024, 1, 1),
            description="First quarter training",
            end_date=date(2024, 3, 31)
        )
        campaign.save()
        
        self.assertEqual(campaign.programId, program_id)
        self.assertEqual(campaign.name, "Q1 Security Training")
        self.assertEqual(campaign.lifecycle_state, AwarenessCampaign.LifecycleState.PLANNED)
        
        # Check event was raised
        events = campaign.get_uncommitted_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "AwarenessCampaignCreated")
    
    def test_start_campaign(self):
        """Test starting a campaign"""
        campaign = AwarenessCampaign()
        campaign.create(program_id=uuid.uuid4(), name="Test Campaign", start_date=date.today())
        campaign.save()
        
        campaign.start()
        campaign.save()
        
        self.assertEqual(campaign.lifecycle_state, AwarenessCampaign.LifecycleState.RUNNING)
        
        # Check event was raised
        events = campaign.get_uncommitted_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "AwarenessCampaignStarted")

