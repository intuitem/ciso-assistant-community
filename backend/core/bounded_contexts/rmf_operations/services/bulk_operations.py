"""
Bulk Operations Service

Service for performing bulk operations on RMF data, particularly
vulnerability findings and checklist updates.
"""

import logging
from typing import List, Dict, Any, Optional
import uuid

from django.core.exceptions import ValidationError
from django.db import transaction

from ..aggregates.vulnerability_finding import VulnerabilityFinding
from ..repositories.vulnerability_finding_repository import VulnerabilityFindingRepository
from ..repositories.stig_checklist_repository import StigChecklistRepository
from ..value_objects import VulnerabilityStatus

logger = logging.getLogger(__name__)


class BulkOperationsService:
    """
    Service for bulk operations on RMF data.

    Handles bulk updates to vulnerability findings, checklist operations,
    and other mass data operations.
    """

    def __init__(self):
        """Initialize the bulk operations service"""
        self.finding_repo = VulnerabilityFindingRepository()
        self.checklist_repo = StigChecklistRepository()

    @transaction.atomic
    def bulk_update_vulnerability_status(self, finding_ids: List[uuid.UUID],
                                       new_status: str,
                                       finding_details: Optional[str] = None,
                                       comments: Optional[str] = None,
                                       user_id: Optional[uuid.UUID] = None) -> Dict[str, Any]:
        """
        Bulk update status for multiple vulnerability findings.

        Args:
            finding_ids: List of finding UUIDs to update
            new_status: New status for all findings
            finding_details: Optional finding details to apply
            comments: Optional comments to apply
            user_id: Optional user ID performing the update

        Returns:
            Dict with operation results
        """
        try:
            # Validate status
            status_obj = VulnerabilityStatus(new_status)

            # Perform bulk update
            updated_count = self.finding_repo.bulk_update_status(
                finding_ids, new_status, finding_details, comments
            )

            logger.info(f"Bulk updated {updated_count} vulnerability findings to status '{new_status}'")

            return {
                'success': True,
                'updated_count': updated_count,
                'status': new_status,
                'total_requested': len(finding_ids)
            }

        except ValidationError as e:
            logger.error(f"Bulk update validation error: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'updated_count': 0,
                'total_requested': len(finding_ids)
            }
        except Exception as e:
            logger.error(f"Bulk update error: {str(e)}")
            return {
                'success': False,
                'error': f"Unexpected error: {str(e)}",
                'updated_count': 0,
                'total_requested': len(finding_ids)
            }

    @transaction.atomic
    def bulk_update_checklist_lifecycle(self, checklist_ids: List[uuid.UUID],
                                       new_state: str,
                                       user_id: Optional[uuid.UUID] = None) -> Dict[str, Any]:
        """
        Bulk update lifecycle state for multiple checklists.

        Args:
            checklist_ids: List of checklist UUIDs to update
            new_state: New lifecycle state
            user_id: Optional user ID performing the update

        Returns:
            Dict with operation results
        """
        try:
            # Validate lifecycle state
            from ..aggregates.stig_checklist import StigChecklist
            if not hasattr(StigChecklist.LifecycleState, new_state.upper()):
                raise ValidationError(f"Invalid lifecycle state: {new_state}")

            # Perform bulk update
            updated_count = self.checklist_repo.bulk_update_lifecycle_state(
                checklist_ids, new_state
            )

            logger.info(f"Bulk updated {updated_count} checklists to lifecycle state '{new_state}'")

            return {
                'success': True,
                'updated_count': updated_count,
                'lifecycle_state': new_state,
                'total_requested': len(checklist_ids)
            }

        except ValidationError as e:
            logger.error(f"Bulk lifecycle update validation error: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'updated_count': 0,
                'total_requested': len(checklist_ids)
            }
        except Exception as e:
            logger.error(f"Bulk lifecycle update error: {str(e)}")
            return {
                'success': False,
                'error': f"Unexpected error: {str(e)}",
                'updated_count': 0,
                'total_requested': len(checklist_ids)
            }

    def bulk_assign_checklists_to_system(self, checklist_ids: List[uuid.UUID],
                                       system_group_id: uuid.UUID,
                                       user_id: Optional[uuid.UUID] = None) -> Dict[str, Any]:
        """
        Bulk assign multiple checklists to a system group.

        Args:
            checklist_ids: List of checklist UUIDs to assign
            system_group_id: System group UUID to assign to
            user_id: Optional user ID performing the assignment

        Returns:
            Dict with operation results
        """
        successful_assignments = 0
        failed_assignments = 0
        errors = []

        for checklist_id in checklist_ids:
            try:
                success = self.checklist_repo.assign_to_system(checklist_id, system_group_id)
                if success:
                    successful_assignments += 1
                else:
                    failed_assignments += 1
                    errors.append(f"Failed to assign checklist {checklist_id}")
            except Exception as e:
                failed_assignments += 1
                errors.append(f"Error assigning checklist {checklist_id}: {str(e)}")

        logger.info(f"Bulk assigned {successful_assignments} checklists to system {system_group_id}")

        return {
            'success': failed_assignments == 0,
            'successful_assignments': successful_assignments,
            'failed_assignments': failed_assignments,
            'total_requested': len(checklist_ids),
            'system_group_id': str(system_group_id),
            'errors': errors[:10]  # Limit error messages
        }

    def get_bulk_update_candidates(self, checklist_id: uuid.UUID,
                                 status_filter: str = 'not_reviewed') -> Dict[str, Any]:
        """
        Get findings that are candidates for bulk updates.

        Args:
            checklist_id: Checklist to get candidates from
            status_filter: Status to filter by (default: 'not_reviewed')

        Returns:
            Dict with candidate findings and summary
        """
        try:
            findings = self.finding_repo.get_findings_for_bulk_update(
                checklist_id, status_filter
            )

            # Convert to serializable format
            candidate_data = []
            for finding in findings:
                candidate_data.append({
                    'id': str(finding.id),
                    'vuln_id': finding.vulnId,
                    'rule_title': finding.ruleTitle,
                    'severity': finding.severity.category,
                    'status': finding.vulnerability_status.status
                })

            return {
                'success': True,
                'checklist_id': str(checklist_id),
                'status_filter': status_filter,
                'candidate_count': len(candidate_data),
                'candidates': candidate_data[:100]  # Limit for performance
            }

        except Exception as e:
            logger.error(f"Error getting bulk update candidates: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'candidate_count': 0,
                'candidates': []
            }

    def validate_bulk_operation(self, operation_type: str,
                              target_ids: List[uuid.UUID],
                              parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate parameters for a bulk operation before execution.

        Args:
            operation_type: Type of bulk operation
            target_ids: List of target object IDs
            parameters: Operation parameters

        Returns:
            Dict with validation results
        """
        errors = []
        warnings = []

        # Validate operation type
        valid_operations = [
            'update_vulnerability_status',
            'update_checklist_lifecycle',
            'assign_to_system'
        ]

        if operation_type not in valid_operations:
            errors.append(f"Invalid operation type: {operation_type}")

        # Validate target IDs
        if not target_ids:
            errors.append("No target IDs provided")
        elif len(target_ids) > 1000:
            warnings.append("Large number of targets (>1000) may impact performance")

        # Validate operation-specific parameters
        if operation_type == 'update_vulnerability_status':
            status = parameters.get('status')
            if not status:
                errors.append("Status parameter is required")
            else:
                try:
                    VulnerabilityStatus(status)
                except ValidationError as e:
                    errors.append(f"Invalid status: {e}")

        elif operation_type == 'update_checklist_lifecycle':
            lifecycle_state = parameters.get('lifecycle_state')
            if not lifecycle_state:
                errors.append("Lifecycle state parameter is required")
            else:
                from ..aggregates.stig_checklist import StigChecklist
                if not hasattr(StigChecklist.LifecycleState, lifecycle_state.upper()):
                    errors.append(f"Invalid lifecycle state: {lifecycle_state}")

        elif operation_type == 'assign_to_system':
            system_id = parameters.get('system_group_id')
            if not system_id:
                errors.append("System group ID parameter is required")

        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'target_count': len(target_ids)
        }

    def get_bulk_operation_history(self, user_id: Optional[uuid.UUID] = None,
                                 limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get history of bulk operations (for audit/logging purposes).

        Args:
            user_id: Optional user ID to filter by
            limit: Maximum number of records to return

        Returns:
            List of bulk operation records
        """
        # This would typically query an audit log or operation history table
        # For now, return empty list as this would be implemented with proper auditing
        return []

    def estimate_bulk_operation_time(self, operation_type: str,
                                   target_count: int) -> Dict[str, Any]:
        """
        Estimate time required for a bulk operation.

        Args:
            operation_type: Type of bulk operation
            target_count: Number of targets

        Returns:
            Dict with time estimates
        """
        # Base estimates (these would be calibrated based on actual performance)
        estimates = {
            'update_vulnerability_status': {
                'per_item_ms': 50,
                'base_overhead_ms': 1000
            },
            'update_checklist_lifecycle': {
                'per_item_ms': 30,
                'base_overhead_ms': 500
            },
            'assign_to_system': {
                'per_item_ms': 20,
                'base_overhead_ms': 300
            }
        }

        if operation_type not in estimates:
            return {
                'estimated_time_ms': None,
                'error': f"Unknown operation type: {operation_type}"
            }

        estimate = estimates[operation_type]
        total_time_ms = estimate['base_overhead_ms'] + (target_count * estimate['per_item_ms'])

        return {
            'estimated_time_ms': total_time_ms,
            'estimated_time_seconds': round(total_time_ms / 1000, 1),
            'target_count': target_count,
            'operation_type': operation_type
        }
