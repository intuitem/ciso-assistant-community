"""
Unit tests for Bulk Operations Service
"""

import uuid
import pytest
from unittest.mock import Mock, patch

from ..services.bulk_operations import BulkOperationsService
from ..aggregates.vulnerability_finding import VulnerabilityFinding
from ..aggregates.stig_checklist import StigChecklist


class TestBulkOperationsService:
    """Test BulkOperationsService."""

    def setup_method(self):
        """Set up test fixtures"""
        self.service = BulkOperationsService()

    @patch('core.bounded_contexts.rmf_operations.services.bulk_operations.VulnerabilityFindingRepository')
    def test_bulk_update_vulnerability_status_success(self, mock_finding_repo_class):
        """Test successful bulk vulnerability status update"""
        # Setup mock
        mock_finding_repo = Mock()
        mock_finding_repo_class.return_value = mock_finding_repo
        mock_finding_repo.bulk_update_status.return_value = 5

        self.service.finding_repo = mock_finding_repo

        # Test data
        finding_ids = [uuid.uuid4() for _ in range(5)]

        # Execute bulk update
        result = self.service.bulk_update_vulnerability_status(
            finding_ids, 'not_a_finding',
            finding_details='Bulk update',
            comments='Automated update'
        )

        # Verify results
        assert result['success'] is True
        assert result['updated_count'] == 5
        assert result['status'] == 'not_a_finding'
        assert result['total_requested'] == 5

        # Verify repository call
        mock_finding_repo.bulk_update_status.assert_called_once_with(
            finding_ids, 'not_a_finding', 'Bulk update', 'Automated update'
        )

    @patch('core.bounded_contexts.rmf_operations.services.bulk_operations.VulnerabilityFindingRepository')
    def test_bulk_update_vulnerability_status_validation_error(self, mock_finding_repo_class):
        """Test bulk update with validation error"""
        # Setup mock to raise ValidationError
        mock_finding_repo = Mock()
        mock_finding_repo_class.return_value = mock_finding_repo
        mock_finding_repo.bulk_update_status.side_effect = Exception("Invalid status")

        self.service.finding_repo = mock_finding_repo

        finding_ids = [uuid.uuid4() for _ in range(3)]

        result = self.service.bulk_update_vulnerability_status(finding_ids, 'invalid_status')

        assert result['success'] is False
        assert 'error' in result
        assert result['updated_count'] == 0

    @patch('core.bounded_contexts.rmf_operations.services.bulk_operations.StigChecklistRepository')
    def test_bulk_update_checklist_lifecycle_success(self, mock_checklist_repo_class):
        """Test successful bulk checklist lifecycle update"""
        # Setup mock
        mock_checklist_repo = Mock()
        mock_checklist_repo_class.return_value = mock_checklist_repo
        mock_checklist_repo.bulk_update_lifecycle_state.return_value = 3

        self.service.checklist_repo = mock_checklist_repo

        checklist_ids = [uuid.uuid4() for _ in range(3)]

        result = self.service.bulk_update_checklist_lifecycle(checklist_ids, 'active')

        assert result['success'] is True
        assert result['updated_count'] == 3
        assert result['lifecycle_state'] == 'active'

    @patch('core.bounded_contexts.rmf_operations.services.bulk_operations.StigChecklistRepository')
    def test_bulk_assign_checklists_to_system(self, mock_checklist_repo_class):
        """Test bulk assignment of checklists to system"""
        # Setup mock
        mock_checklist_repo = Mock()
        mock_checklist_repo_class.return_value = mock_checklist_repo
        mock_checklist_repo.assign_to_system.return_value = True

        self.service.checklist_repo = mock_checklist_repo

        checklist_ids = [uuid.uuid4() for _ in range(3)]
        system_id = uuid.uuid4()

        result = self.service.bulk_assign_checklists_to_system(checklist_ids, system_id)

        assert result['success'] is True
        assert result['successful_assignments'] == 3
        assert result['failed_assignments'] == 0
        assert result['system_group_id'] == str(system_id)

        # Verify repository calls
        assert mock_checklist_repo.assign_to_system.call_count == 3

    @patch('core.bounded_contexts.rmf_operations.services.bulk_operations.VulnerabilityFindingRepository')
    def test_get_bulk_update_candidates(self, mock_finding_repo_class):
        """Test getting bulk update candidates"""
        # Setup mock
        mock_finding_repo = Mock()
        mock_finding_repo_class.return_value = mock_finding_repo

        # Create mock findings
        mock_findings = []
        for i in range(3):
            mock_finding = Mock()
            mock_finding.id = uuid.uuid4()
            mock_finding.vulnId = f'V-1234{i}'
            mock_finding.ruleTitle = f'Rule {i}'
            mock_finding.severity.category = 'cat1'
            mock_finding.vulnerability_status.status = 'not_reviewed'
            mock_findings.append(mock_finding)

        mock_finding_repo.get_findings_for_bulk_update.return_value = mock_findings
        self.service.finding_repo = mock_finding_repo

        checklist_id = uuid.uuid4()

        result = self.service.get_bulk_update_candidates(checklist_id, 'not_reviewed')

        assert result['success'] is True
        assert result['checklist_id'] == str(checklist_id)
        assert result['candidate_count'] == 3
        assert len(result['candidates']) == 3

    def test_validate_bulk_operation_valid(self):
        """Test validating a valid bulk operation"""
        target_ids = [uuid.uuid4() for _ in range(5)]
        parameters = {'status': 'not_a_finding'}

        result = self.service.validate_bulk_operation(
            'update_vulnerability_status', target_ids, parameters
        )

        assert result['valid'] is True
        assert len(result['errors']) == 0
        assert result['target_count'] == 5

    def test_validate_bulk_operation_invalid_type(self):
        """Test validating an invalid operation type"""
        target_ids = [uuid.uuid4()]
        parameters = {}

        result = self.service.validate_bulk_operation(
            'invalid_operation', target_ids, parameters
        )

        assert result['valid'] is False
        assert len(result['errors']) > 0
        assert 'Invalid operation type' in result['errors'][0]

    def test_validate_bulk_operation_no_targets(self):
        """Test validating with no target IDs"""
        result = self.service.validate_bulk_operation(
            'update_vulnerability_status', [], {'status': 'open'}
        )

        assert result['valid'] is False
        assert 'No target IDs provided' in result['errors']

    def test_estimate_bulk_operation_time(self):
        """Test estimating bulk operation time"""
        result = self.service.estimate_bulk_operation_time(
            'update_vulnerability_status', 100
        )

        assert 'estimated_time_ms' in result
        assert 'estimated_time_seconds' in result
        assert result['target_count'] == 100
        assert result['operation_type'] == 'update_vulnerability_status'

        # Should be around 100 * 50ms + 1000ms base = 6000ms
        assert result['estimated_time_ms'] == 6000

    def test_estimate_bulk_operation_invalid_type(self):
        """Test estimating time for invalid operation type"""
        result = self.service.estimate_bulk_operation_time('invalid_type', 10)

        assert result['estimated_time_ms'] is None
        assert 'error' in result

    def test_get_bulk_operation_history(self):
        """Test getting bulk operation history"""
        # This returns empty list in current implementation
        history = self.service.get_bulk_operation_history()

        assert isinstance(history, list)
        assert len(history) == 0
