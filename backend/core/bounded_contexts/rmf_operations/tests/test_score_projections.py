"""
Unit tests for Score Projection Handlers
"""

import uuid
import pytest
from unittest.mock import Mock, patch

from ..projections.score_projections import ScoreProjectionHandler, SystemGroupProjectionHandler


class TestScoreProjectionHandler:
    """Test ScoreProjectionHandler."""

    def setup_method(self):
        """Set up test fixtures"""
        self.handler = ScoreProjectionHandler()

    @patch('core.bounded_contexts.rmf_operations.projections.score_projections.ChecklistScore')
    @patch('core.bounded_contexts.rmf_operations.projections.score_projections.ChecklistScoreRepository')
    def test_handle_stig_checklist_imported(self, mock_score_repo_class, mock_score_class):
        """Test handling StigChecklistImported event"""
        # Setup mocks
        mock_score_repo = Mock()
        mock_score_repo_class.return_value = mock_score_repo

        mock_score_instance = Mock()
        mock_score_class.return_value = mock_score_instance

        # Test event data
        event_data = {
            'aggregate_id': str(uuid.uuid4()),
            'host_name': 'test-server.local',
            'stig_type': 'Windows Server 2019'
        }

        # Call handler
        self.handler.handle_stig_checklist_imported(event_data)

        # Verify score creation
        mock_score_instance.create_score.assert_called_once()
        mock_score_repo.save.assert_called_once_with(mock_score_instance)

    @patch.object(ScoreProjectionHandler, '_recalculate_checklist_score')
    def test_handle_vulnerability_finding_created(self, mock_recalculate):
        """Test handling VulnerabilityFindingCreated event"""
        event_data = {
            'aggregate_id': str(uuid.uuid4()),
            'checklist_id': str(uuid.uuid4())
        }

        self.handler.handle_vulnerability_finding_created(event_data)

        mock_recalculate.assert_called_once()

    @patch.object(ScoreProjectionHandler, '_recalculate_checklist_score')
    def test_handle_vulnerability_finding_status_changed(self, mock_recalculate):
        """Test handling VulnerabilityFindingStatusChanged event"""
        event_data = {
            'aggregate_id': str(uuid.uuid4()),
            'checklist_id': str(uuid.uuid4()),
            'old_status': 'NotReviewed',
            'new_status': 'Open'
        }

        self.handler.handle_vulnerability_finding_status_changed(event_data)

        mock_recalculate.assert_called_once()

    @patch('core.bounded_contexts.rmf_operations.projections.score_projections.VulnerabilityFindingRepository')
    def test_recalculate_checklist_score(self, mock_finding_repo_class):
        """Test checklist score recalculation"""
        # Setup mocks
        mock_finding_repo = Mock()
        mock_finding_repo_class.return_value = mock_finding_repo

        mock_score_repo = Mock()
        self.handler.score_repo = mock_score_repo

        # Mock findings stats
        mock_finding_repo.get_finding_stats_for_checklist.return_value = {
            'details': {
                'cat1': {'open': 2, 'not_a_finding': 1},
                'cat2': {'open': 1, 'not_a_finding': 2},
                'cat3': {'open': 0, 'not_a_finding': 1}
            }
        }

        checklist_id = uuid.uuid4()

        # Call recalculation
        self.handler._recalculate_checklist_score(checklist_id)

        # Verify interactions
        mock_finding_repo.get_finding_stats_for_checklist.assert_called_once_with(checklist_id)
        mock_score_repo.update_score_from_findings.assert_called_once()


class TestSystemGroupProjectionHandler:
    """Test SystemGroupProjectionHandler."""

    def setup_method(self):
        """Set up test fixtures"""
        self.handler = SystemGroupProjectionHandler()

    @patch.object(SystemGroupProjectionHandler, '_update_system_compliance_stats')
    def test_handle_checklist_added_to_system(self, mock_update):
        """Test handling ChecklistAddedToSystem event"""
        event_data = {
            'aggregate_id': str(uuid.uuid4()),
            'system_name': 'Test System'
        }

        self.handler.handle_checklist_added_to_system(event_data)

        mock_update.assert_called_once()

    @patch.object(SystemGroupProjectionHandler, '_update_system_compliance_stats')
    def test_handle_asset_added_to_system(self, mock_update):
        """Test handling AssetAddedToSystem event"""
        event_data = {
            'aggregate_id': str(uuid.uuid4()),
            'system_name': 'Test System'
        }

        self.handler.handle_asset_added_to_system(event_data)

        mock_update.assert_called_once()

    @patch.object(SystemGroupProjectionHandler, '_update_system_compliance_stats')
    def test_handle_checklist_score_updated(self, mock_update):
        """Test handling ChecklistScoreUpdated event"""
        event_data = {
            'aggregate_id': str(uuid.uuid4()),
            'system_group_id': str(uuid.uuid4())
        }

        self.handler.handle_checklist_score_updated(event_data)

        mock_update.assert_called_once()

    @patch('core.bounded_contexts.rmf_operations.projections.score_projections.ChecklistScoreRepository')
    @patch('core.bounded_contexts.rmf_operations.repositories.system_group_repository.SystemGroupRepository')
    def test_update_system_compliance_stats(self, mock_system_repo_class, mock_score_repo_class):
        """Test updating system compliance statistics"""
        # Setup mocks
        mock_system_repo = Mock()
        mock_system_repo_class.return_value = mock_system_repo
        self.handler.system_repo = mock_system_repo

        mock_score_repo = Mock()
        mock_score_repo_class.return_value = mock_score_repo
        self.handler.score_repo = mock_score_repo

        # Mock score data
        mock_score_repo.get_system_level_score.return_value = {
            'total_checklists': 3,
            'total_open': 5,
            'total_cat1_open': 2,
            'total_cat2_open': 2,
            'total_cat3_open': 1
        }

        system_id = uuid.uuid4()

        # Call update
        self.handler._update_system_compliance_stats(system_id)

        # Verify interactions
        mock_score_repo.get_system_level_score.assert_called_once_with(system_id)
        mock_system_repo.update_system_stats.assert_called_once_with(
            system_id,
            total_checklists=3,
            total_open=5,
            cat1_open=2,
            cat2_open=2,
            cat3_open=3  # cat2_open + cat3_open
        )
