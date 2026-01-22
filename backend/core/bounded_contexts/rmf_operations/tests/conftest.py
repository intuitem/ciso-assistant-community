"""
Pytest configuration for RMF Operations Bounded Context tests.

Provides fixtures and configuration for testing the RMF operations
aggregates, repositories, and services.
"""

import pytest
import uuid
from django.test import TransactionTestCase

from core.domain.events import EventBus, get_event_bus
from ..aggregates.system_group import SystemGroup
from ..aggregates.stig_checklist import StigChecklist
from ..aggregates.vulnerability_finding import VulnerabilityFinding
from ..aggregates.checklist_score import ChecklistScore
from ..repositories.system_group_repository import SystemGroupRepository
from ..repositories.stig_checklist_repository import StigChecklistRepository
from ..repositories.vulnerability_finding_repository import VulnerabilityFindingRepository
from ..repositories.checklist_score_repository import ChecklistScoreRepository


@pytest.fixture
def event_bus():
    """Provide a clean event bus for each test"""
    bus = EventBus()
    bus._store_events = False  # Don't store events in tests unless needed
    return bus


@pytest.fixture
def stored_event_bus():
    """Provide an event bus that stores events"""
    bus = EventBus()
    bus._store_events = True
    return bus


@pytest.fixture(autouse=True)
def reset_event_bus():
    """Reset event bus handlers before each test"""
    bus = get_event_bus()
    if hasattr(bus, '_handlers'):
        bus._handlers.clear()
    yield
    if hasattr(bus, '_handlers'):
        bus._handlers.clear()


@pytest.fixture
def system_group_repository():
    """Provide a SystemGroupRepository instance"""
    return SystemGroupRepository()


@pytest.fixture
def stig_checklist_repository():
    """Provide a StigChecklistRepository instance"""
    return StigChecklistRepository()


@pytest.fixture
def vulnerability_finding_repository():
    """Provide a VulnerabilityFindingRepository instance"""
    return VulnerabilityFindingRepository()


@pytest.fixture
def checklist_score_repository():
    """Provide a ChecklistScoreRepository instance"""
    return ChecklistScoreRepository()


@pytest.fixture
def sample_system_group():
    """Create a sample system group for testing"""
    system = SystemGroup()
    system.create_system(
        name="Test System Group",
        description="A test system group for unit tests"
    )
    return system


@pytest.fixture
def sample_stig_checklist():
    """Create a sample STIG checklist for testing"""
    checklist = StigChecklist()
    checklist.create_checklist(
        host_name="test-server.local",
        stig_type="Windows Server 2019",
        stig_release="Release: 2.5",
        version="1.0"
    )
    return checklist


@pytest.fixture
def sample_vulnerability_finding():
    """Create a sample vulnerability finding for testing"""
    finding = VulnerabilityFinding()
    finding.create_finding(
        checklist_id=uuid.uuid4(),
        vuln_id="V-12345",
        stig_id="Windows_2019_STIG",
        rule_id="SV-12345r1_rule",
        rule_title="Test Rule",
        severity_category="cat1"
    )
    return finding


@pytest.fixture
def sample_checklist_score():
    """Create a sample checklist score for testing"""
    score = ChecklistScore()
    score.create_score(
        checklist_id=uuid.uuid4(),
        system_group_id=None,
        host_name="test-server.local",
        stig_type="Windows Server 2019"
    )
    return score


@pytest.fixture
def sample_ckl_parsed_data():
    """Sample parsed CKL data for import testing"""
    return {
        'stig_type': 'Windows Server 2019',
        'stig_release': 'Release: 3.0',
        'stig_version': '2.0',
        'host_name': 'updated-server.local',
        'host_ip': '192.168.1.100',
        'host_fqdn': 'updated-server.local.domain.com',
        'asset_info': {
            'web_or_database': False,
            'web_db_site': '',
            'web_db_instance': '',
            'inferred_asset_type': 'computing'
        }
    }
