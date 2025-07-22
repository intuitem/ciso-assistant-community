import logging
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.conf import settings
from core.models import ComplianceAssessment, AppliedControl
from django.db.models.signals import post_save

logger = logging.getLogger(__name__)
logger.info('signals.py loaded')

WEBHOOK_URL = getattr(settings, 'NOTIFICATION_WEBHOOK_URL', None)


def send_webhook_notification(payload):
    if not WEBHOOK_URL:
        logger.warning('Notification webhook URL is not set. Skipping notification.')
        return
    try:
        logger.info(f'Sending notification to webhook: {WEBHOOK_URL} with payload: {payload}')
        import requests
        response = requests.post(WEBHOOK_URL, json=payload, timeout=5)
        response.raise_for_status()
        logger.info(f'Notification sent successfully. Response: {response.status_code}')
    except Exception as e:
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
        'owners': [str(u) for u in instance.owner.all()],
        'assets': [str(a) for a in instance.assets.all()],
        'evidences': [str(e) for e in instance.evidences.all()],
        'security_exceptions': [str(se) for se in instance.security_exceptions.all()],
        # Ajoute d'autres champs si besoin
    }

def get_compliance_assessment_payload(instance, old_status):
    # Calcul des pourcentages de conformité et de progression
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
        'assets': [str(a) for a in instance.assets.all()],
        'campaign': str(instance.campaign) if instance.campaign else None,
        'evidences': [str(e) for e in instance.evidences.all()],
        'authors': [str(u) for u in instance.authors.all()] if hasattr(instance, 'authors') else [],
        'compliance_percentage': compliance_percentage,
        'progress_percentage': progress_percentage,
        # Ajoute d'autres champs si besoin
    }


@receiver(pre_save, sender=ComplianceAssessment)
def compliance_assessment_status_change(sender, instance, **kwargs):
    if not instance.pk:
        logger.info(f'[pre_save] ComplianceAssessment: new instance, will notify creation after save')
        # On ne peut pas envoyer la notification ici car l'ID n'est pas encore assigné
        # On la gère dans post_save ci-dessous
        return
    try:
        old = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        logger.info(f'[pre_save] ComplianceAssessment: instance with pk={instance.pk} does not exist in DB')
        return
    old_status = old.status
    new_status = instance.status
    logger.info(f'[pre_save] ComplianceAssessment: old_status={old_status}, new_status={new_status}')
    if old_status != new_status:
        logger.info(f'[pre_save] Status changed for ComplianceAssessment id={instance.pk}: {old_status} -> {new_status}')
        payload = get_compliance_assessment_payload(instance, old_status)
        send_webhook_notification(payload)
    else:
        logger.info(f'[pre_save] No status change for ComplianceAssessment id={instance.pk}: status remains {new_status}')

# Ajout : notification à la création d'un audit
@receiver(post_save, sender=ComplianceAssessment)
def compliance_assessment_created(sender, instance, created, **kwargs):
    if created:
        logger.info(f'[post_save] ComplianceAssessment created: id={instance.pk}, name={instance.name}')
        payload = get_compliance_assessment_payload(instance, old_status=None)
        payload['type'] = 'compliance_assessment_created'
        send_webhook_notification(payload)


@receiver(pre_save, sender=AppliedControl)
def applied_control_status_change(sender, instance, **kwargs):
    if not instance.pk:
        logger.info(f'[pre_save] AppliedControl: new instance, no status to compare (id will be assigned after save)')
        return
    try:
        old = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        logger.info(f'[pre_save] AppliedControl: instance with pk={instance.pk} does not exist in DB')
        return
    old_status = old.status
    new_status = instance.status
    logger.info(f'[pre_save] AppliedControl: old_status={old_status}, new_status={new_status}')
    if old_status != new_status:
        logger.info(f'[pre_save] Status changed for AppliedControl id={instance.pk}: {old_status} -> {new_status}')
        payload = get_applied_control_payload(instance, old_status)
        send_webhook_notification(payload)
    else:
        logger.info(f'[pre_save] No status change for AppliedControl id={instance.pk}: status remains {new_status}') 