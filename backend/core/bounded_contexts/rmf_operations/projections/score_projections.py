"""
Score Projection Handlers

Event handlers that update read models and perform calculations
when domain events are published.
"""

import logging
from typing import Dict, Any, List
import uuid

from core.domain.events import EventBus
from ..aggregates.checklist_score import ChecklistScore
from ..aggregates.vulnerability_finding import VulnerabilityFinding
from ..repositories.checklist_score_repository import ChecklistScoreRepository
from ..repositories.vulnerability_finding_repository import VulnerabilityFindingRepository
from ..repositories.stig_checklist_repository import StigChecklistRepository

logger = logging.getLogger(__name__)


class ScoreProjectionHandler:
    """
    Handles events that affect checklist scoring.

    Updates ChecklistScore aggregates when vulnerability findings change.
    """

    def __init__(self):
        self.score_repo = ChecklistScoreRepository()
        self.finding_repo = VulnerabilityFindingRepository()
        self.checklist_repo = StigChecklistRepository()

    def handle_stig_checklist_imported(self, event_data: Dict[str, Any]) -> None:
        """Handle StigChecklistImported event - create initial score"""
        checklist_id = uuid.UUID(event_data['aggregate_id'])

        # Create initial score record
        score = ChecklistScore()
        score.create_score(
            checklist_id=checklist_id,
            system_group_id=None,  # Will be set when checklist is assigned
            host_name=event_data.get('host_name', 'Unknown'),
            stig_type=event_data.get('stig_type', 'Unknown')
        )

        self.score_repo.save(score)
        logger.info(f"Created initial score for checklist {checklist_id}")

    def handle_vulnerability_finding_created(self, event_data: Dict[str, Any]) -> None:
        """Handle VulnerabilityFindingCreated event"""
        checklist_id = uuid.UUID(event_data.get('checklist_id', event_data['aggregate_id']))

        # Trigger score recalculation
        self._recalculate_checklist_score(checklist_id)

    def handle_vulnerability_finding_status_changed(self, event_data: Dict[str, Any]) -> None:
        """Handle VulnerabilityFindingStatusChanged event"""
        checklist_id = uuid.UUID(event_data.get('checklist_id', event_data['aggregate_id']))

        # Trigger score recalculation
        self._recalculate_checklist_score(checklist_id)

    def handle_vulnerability_finding_severity_overridden(self, event_data: Dict[str, Any]) -> None:
        """Handle VulnerabilityFindingSeverityOverridden event"""
        checklist_id = uuid.UUID(event_data.get('checklist_id', event_data['aggregate_id']))

        # Trigger score recalculation (severity changes affect scoring)
        self._recalculate_checklist_score(checklist_id)

    def _recalculate_checklist_score(self, checklist_id: uuid.UUID) -> None:
        """Recalculate score for a checklist based on current findings"""
        try:
            # Get findings stats for this checklist
            findings_stats = self.finding_repo.get_finding_stats_for_checklist(checklist_id)

            # Update score
            success = self.score_repo.update_score_from_findings(
                checklist_id,
                findings_stats.get('details', {})
            )

            if success:
                logger.info(f"Recalculated score for checklist {checklist_id}")
            else:
                logger.error(f"Failed to recalculate score for checklist {checklist_id}")

        except Exception as e:
            logger.error(f"Error recalculating score for checklist {checklist_id}: {str(e)}")


class SystemGroupProjectionHandler:
    """
    Handles events that affect system group statistics.

    Updates system-level compliance statistics when checklists are added/removed
    or when scores change.
    """

    def __init__(self):
        self.system_repo = None  # Import to avoid circular imports
        self.score_repo = ChecklistScoreRepository()

    def handle_checklist_added_to_system(self, event_data: Dict[str, Any]) -> None:
        """Handle ChecklistAddedToSystem event"""
        system_id = uuid.UUID(event_data['aggregate_id'])

        # Trigger system stats update
        self._update_system_compliance_stats(system_id)

    def handle_asset_added_to_system(self, event_data: Dict[str, Any]) -> None:
        """Handle AssetAddedToSystem event"""
        system_id = uuid.UUID(event_data['aggregate_id'])

        # Trigger system stats update
        self._update_system_compliance_stats(system_id)

    def handle_checklist_score_updated(self, event_data: Dict[str, Any]) -> None:
        """Handle ChecklistScoreUpdated event"""
        system_id_str = event_data.get('system_group_id')
        if system_id_str:
            system_id = uuid.UUID(system_id_str)
            self._update_system_compliance_stats(system_id)

    def _update_system_compliance_stats(self, system_id: uuid.UUID) -> None:
        """Update compliance statistics for a system group"""
        try:
            if not self.system_repo:
                from ..repositories.system_group_repository import SystemGroupRepository
                self.system_repo = SystemGroupRepository()

            # Get system-level score aggregation
            score_data = self.score_repo.get_system_level_score(system_id)

            # Update system statistics
            success = self.system_repo.update_system_stats(
                system_id,
                total_checklists=score_data.get('total_checklists', 0),
                total_open=score_data.get('total_open', 0),
                cat1_open=score_data.get('total_cat1_open', 0),
                cat2_open=score_data.get('total_cat2_open', 0),
                cat3_open=score_data.get('total_cat3_open', 0)
            )

            if success:
                logger.info(f"Updated compliance stats for system {system_id}")
            else:
                logger.warning(f"Failed to update compliance stats for system {system_id}")

        except Exception as e:
            logger.error(f"Error updating system compliance stats for {system_id}: {str(e)}")


# Event subscription setup
def setup_score_projections():
    """Set up event subscriptions for score projections"""
    event_bus = EventBus()

    score_handler = ScoreProjectionHandler()
    system_handler = SystemGroupProjectionHandler()

    # Subscribe to vulnerability finding events
    event_bus.subscribe("VulnerabilityFindingCreated", score_handler.handle_vulnerability_finding_created)
    event_bus.subscribe("VulnerabilityFindingStatusChanged", score_handler.handle_vulnerability_finding_status_changed)
    event_bus.subscribe("VulnerabilityFindingSeverityOverridden", score_handler.handle_vulnerability_finding_severity_overridden)

    # Subscribe to checklist events
    event_bus.subscribe("StigChecklistImported", score_handler.handle_stig_checklist_imported)

    # Subscribe to system events
    event_bus.subscribe("ChecklistAddedToSystem", system_handler.handle_checklist_added_to_system)
    event_bus.subscribe("AssetAddedToSystem", system_handler.handle_asset_added_to_system)

    # Subscribe to score events
    event_bus.subscribe("ChecklistScoreUpdated", system_handler.handle_checklist_score_updated)

    logger.info("Score projection handlers registered")
