"""
ServiceContract Association

First-class association representing a service contract between a service and third party.
"""

import uuid
from typing import Optional
from datetime import date
from django.db import models
from django.core.exceptions import ValidationError

from core.domain.aggregate import AggregateRoot
from ..domain_events import (
    ServiceContractEstablished,
    ServiceContractRenewed,
    ServiceContractExpired,
)


class ServiceContract(AggregateRoot):
    """
    Service Contract association.
    
    First-class entity representing a contract between a service and third party
    with dates, terms, and renewal information.
    """
    
    class LifecycleState(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        EXPIRED = "expired", "Expired"
    
    # Service and Third Party
    serviceId = models.UUIDField(db_index=True)
    thirdPartyId = models.UUIDField(db_index=True)
    
    # Lifecycle
    lifecycle_state = models.CharField(
        max_length=20,
        choices=LifecycleState.choices,
        default=LifecycleState.DRAFT,
        db_index=True
    )
    
    # Dates
    start_date = models.DateField(db_index=True)
    end_date = models.DateField(null=True, blank=True, db_index=True)
    renewal_date = models.DateField(null=True, blank=True, db_index=True)
    
    # Terms
    key_terms = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    
    class Meta:
        db_table = "asset_service_contracts"
        verbose_name = "Service Contract"
        verbose_name_plural = "Service Contracts"
        indexes = [
            models.Index(fields=["serviceId", "thirdPartyId"]),
            models.Index(fields=["lifecycle_state", "end_date"]),
        ]
        unique_together = [
            ["serviceId", "thirdPartyId", "start_date"]
        ]
    
    def clean(self):
        """Validate contract invariants"""
        super().clean()
        
        # Invariant: End date must be after start date
        if self.start_date and self.end_date:
            if self.end_date < self.start_date:
                raise ValidationError("End date must be after start date")
        
        # Invariant: Renewal date should be before end date
        if self.end_date and self.renewal_date:
            if self.renewal_date > self.end_date:
                raise ValidationError("Renewal date should be before end date")
    
    def establish(self, service_id: uuid.UUID, third_party_id: uuid.UUID,
                  start_date: date, end_date: Optional[date] = None,
                  renewal_date: Optional[date] = None, key_terms: str = None,
                  notes: str = None):
        """
        Establish a service contract.
        
        Domain method that enforces business rules and raises events.
        """
        self.serviceId = service_id
        self.thirdPartyId = third_party_id
        self.start_date = start_date
        self.end_date = end_date
        self.renewal_date = renewal_date
        self.key_terms = key_terms
        self.notes = notes
        self.lifecycle_state = self.LifecycleState.ACTIVE
        
        event = ServiceContractEstablished()
        event.payload = {
            "contract_id": str(self.id),
            "service_id": str(service_id),
            "third_party_id": str(third_party_id),
            "start_date": str(start_date),
        }
        self._raise_event(event)
    
    def renew(self, new_end_date: date, renewal_date: Optional[date] = None):
        """
        Renew the service contract.
        
        Args:
            new_end_date: New end date for the contract
            renewal_date: Date when renewal should be considered
        """
        if self.lifecycle_state != self.LifecycleState.ACTIVE:
            raise ValidationError("Can only renew active contracts")
        
        old_end_date = self.end_date
        self.end_date = new_end_date
        self.renewal_date = renewal_date or new_end_date
        
        event = ServiceContractRenewed()
        event.payload = {
            "contract_id": str(self.id),
            "old_end_date": str(old_end_date) if old_end_date else None,
            "new_end_date": str(new_end_date),
        }
        self._raise_event(event)
    
    def expire(self):
        """Mark the contract as expired"""
        if self.lifecycle_state != self.LifecycleState.EXPIRED:
            from django.utils import timezone
            if self.end_date is None:
                self.end_date = timezone.now().date()
            
            self.lifecycle_state = self.LifecycleState.EXPIRED
            
            event = ServiceContractExpired()
            event.payload = {
                "contract_id": str(self.id),
                "expired_at": str(self.end_date),
            }
            self._raise_event(event)
    
    def is_active(self) -> bool:
        """Check if contract is currently active"""
        from django.utils import timezone
        today = timezone.now().date()
        
        if self.lifecycle_state != self.LifecycleState.ACTIVE:
            return False
        if self.start_date > today:
            return False
        if self.end_date and self.end_date < today:
            return False
        return True
    
    def needs_renewal(self) -> bool:
        """Check if contract needs renewal attention"""
        if not self.is_active():
            return False
        
        from django.utils import timezone
        today = timezone.now().date()
        
        if self.renewal_date and self.renewal_date <= today:
            return True
        if self.end_date:
            # Check if within 30 days of expiration
            from datetime import timedelta
            if self.end_date - today <= timedelta(days=30):
                return True
        
        return False
    
    def __str__(self):
        return f"Contract {self.id} (Service: {self.serviceId}, Third Party: {self.thirdPartyId})"

