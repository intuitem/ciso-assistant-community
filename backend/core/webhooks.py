import logging
from django.conf import settings
from core.models import ComplianceAssessment, AppliedControl, RequirementAssessment
import requests

logger = logging.getLogger(__name__)


def send_webhook_notification(payload):
    webhook_url = getattr(settings, 'NOTIFICATION_WEBHOOK_URL', None)
    if not webhook_url:
        logger.warning('Notification webhook URL is not set. Skipping notification.')
        return None
    try:
        logger.info('Sending notification to webhook.')
        response = requests.post(webhook_url, json=payload, timeout=5)
        response.raise_for_status()
        logger.info(f'Notification sent successfully. Response: {response.status_code}')
        return response
    except requests.RequestException as e:
        logger.error(f'Error sending notification: {e}')
        raise


def get_applied_control_payload(instance, old_status, event_type='applied_control_status_changed'):
    return {
        'type': event_type,
        'id': str(instance.pk),
        'name': instance.name,
        'old_status': old_status,
        'new_status': instance.status,
        'ref_id': instance.ref_id,
        'category': instance.category,
        'csf_function': instance.csf_function,
        'priority': instance.priority,
        'effort': instance.effort,
        'control_impact': instance.control_impact,
        'cost': instance.cost,
        'progress_field': instance.progress_field,
        'start_date': str(instance.start_date) if instance.start_date else None,
        'eta': str(instance.eta) if instance.eta else None,
        'expiry_date': str(instance.expiry_date) if instance.expiry_date else None,
        'link': instance.link,
        'reference_control': str(instance.reference_control) if instance.reference_control else None,
        'owners': [{'id': u.id, 'name': str(u)} for u in instance.owner.all()],
        'assets': [{'id': a.id, 'name': str(a)} for a in instance.assets.all()],
        'evidences': [{'id': e.id, 'name': str(e)} for e in instance.evidences.all()],
        'security_exceptions': [{'id': se.id, 'name': str(se)} for se in instance.security_exceptions.all()],
        # Add other fields as needed for more context
    }

def get_compliance_assessment_payload(instance, old_status, event_type='compliance_assessment_status_changed'):
    # Defensive programming for computed fields
    compliance_percentage = None
    progress_percentage = None
    
    try:
        compliance_percentage = instance.get_compliance_percentage()
        logger.info(f'ComplianceAssessment {instance.pk}: compliance_percentage={compliance_percentage}%')
    except Exception as e:
        logger.warning(f'Could not compute compliance_percentage for ComplianceAssessment {instance.pk}: {e}')
    
    try:
        progress_percentage = instance.get_progress()
        logger.info(f'ComplianceAssessment {instance.pk}: progress_percentage={progress_percentage}')
    except Exception as e:
        logger.warning(f'Could not compute progress_percentage for ComplianceAssessment {instance.pk}: {e}')
    
    return {
        'type': event_type,
        'id': str(instance.pk),
        'name': instance.name,
        'old_status': old_status,
        'new_status': instance.status,
        'ref_id': instance.ref_id,
        'framework': instance.framework.name if instance.framework else None,
        'perimeter': instance.perimeter.name if instance.perimeter else None,
        'min_score': instance.min_score,
        'max_score': instance.max_score,
        'compliance_percentage': compliance_percentage,
        'progress_percentage': progress_percentage,
        # Add other fields as needed
    } 