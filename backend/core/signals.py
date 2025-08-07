import logging
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.conf import settings
from core.models import ComplianceAssessment, AppliedControl
import requests

logger = logging.getLogger(__name__)

WEBHOOK_URL = getattr(settings, 'NOTIFICATION_WEBHOOK_URL', None)


def send_webhook_notification(payload):
    if not WEBHOOK_URL:
        logger.warning('Notification webhook URL is not set. Skipping notification.')
        return
    try:
        logger.info('Sending notification to webhook.')
        response = requests.post(WEBHOOK_URL, json=payload, timeout=5)
        response.raise_for_status()
        logger.info(f'Notification sent successfully. Response: {response.status_code}')
    except requests.RequestException as e:
        logger.error(f'Error sending notification: {e}')


def get_applied_control_payload(instance, old_status):
    return {
        'type': 'applied_control_status_changed',
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

def get_compliance_assessment_payload(instance, old_status):
    # Defensive programming for computed fields
    compliance_percentage = None
    progress_percentage = None
    try:
        if hasattr(instance, 'get_global_score'):
            compliance_percentage = instance.get_global_score()
    except Exception as e:
        logger.warning(f'Could not compute compliance_percentage: {e}')
    try:
        if hasattr(instance, 'get_progress'):
            progress_percentage = instance.get_progress()
    except Exception as e:
        logger.warning(f'Could not compute progress_percentage: {e}')
    return {
        'type': 'compliance_assessment_status_changed',
        'id': str(instance.pk),
        'name': instance.name,
        'old_status': old_status,
        'new_status': instance.status,
        'ref_id': instance.ref_id,
        'framework': str(instance.framework) if instance.framework else None,
        'perimeter': str(instance.perimeter) if hasattr(instance, 'perimeter') and instance.perimeter else None,
        'min_score': instance.min_score,
        'max_score': instance.max_score,
        'show_documentation_score': instance.show_documentation_score,
        'assets': [{'id': a.id, 'name': str(a)} for a in instance.assets.all()],
        'campaign': str(instance.campaign) if instance.campaign else None,
        'evidences': [{'id': e.id, 'name': str(e)} for e in instance.evidences.all()],
        'authors': [{'id': u.id, 'name': str(u)} for u in instance.authors.all()] if hasattr(instance, 'authors') else [],
        'compliance_percentage': compliance_percentage,
        'progress_percentage': progress_percentage,
        # Add other fields as needed
    } 