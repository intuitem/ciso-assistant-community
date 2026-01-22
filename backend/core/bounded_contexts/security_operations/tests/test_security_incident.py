"""
Tests for SecurityIncident aggregate
"""

import uuid
from django.test import TestCase

from core.bounded_contexts.security_operations.aggregates.security_incident import SecurityIncident
from core.bounded_contexts.security_operations.domain_events import (
    SecurityIncidentReported,
    SecurityIncidentTriaged,
    SecurityIncidentContained,
)


class SecurityIncidentTests(TestCase):
    """Tests for SecurityIncident aggregate"""
    
    def test_create_incident(self):
        """Test creating a security incident"""
        incident = SecurityIncident()
        incident.create(
            title="Data Breach Detected",
            description="Unauthorized access to customer database",
            severity="high",
            detection_source="external"
        )
        incident.save()
        
        self.assertEqual(incident.title, "Data Breach Detected")
        self.assertEqual(incident.severity, "high")
        self.assertEqual(incident.lifecycle_state, SecurityIncident.LifecycleState.REPORTED)
        self.assertIsNotNone(incident.reported_at)
        self.assertEqual(len(incident.timeline), 1)
        
        # Check event was raised
        events = incident.get_uncommitted_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "SecurityIncidentReported")
    
    def test_triage_incident(self):
        """Test triaging an incident"""
        incident = SecurityIncident()
        incident.create(title="Test Incident")
        incident.save()
        
        incident.triage(notes="Assigned to security team")
        incident.save()
        
        self.assertEqual(incident.lifecycle_state, SecurityIncident.LifecycleState.TRIAGED)
        self.assertIsNotNone(incident.triaged_at)
        
        # Check event was raised
        events = incident.get_uncommitted_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "SecurityIncidentTriaged")
    
    def test_contain_incident(self):
        """Test containing an incident"""
        incident = SecurityIncident()
        incident.create(title="Test Incident")
        incident.save()
        incident.triage()
        incident.save()
        
        incident.contain(notes="Isolated affected systems")
        incident.save()
        
        self.assertEqual(incident.lifecycle_state, SecurityIncident.LifecycleState.CONTAINED)
        self.assertIsNotNone(incident.contained_at)
    
    def test_add_timeline_event(self):
        """Test adding a timeline event"""
        incident = SecurityIncident()
        incident.create(title="Test Incident")
        incident.save()
        
        actor_id = uuid.uuid4()
        incident.add_timeline_event("Investigation started", actor_id, "Initial analysis")
        incident.save()
        
        self.assertEqual(len(incident.timeline), 2)  # 1 from create + 1 added
        self.assertEqual(incident.timeline[-1]["action"], "Investigation started")

