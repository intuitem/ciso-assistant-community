"""
Unit tests for RMF Operations value objects.
"""

import pytest
from django.core.exceptions import ValidationError

from ..value_objects import VulnerabilityStatus, SeverityCategory


class TestVulnerabilityStatus:
    """Test VulnerabilityStatus value object."""

    def test_create_valid_status(self):
        """Test creating a valid vulnerability status."""
        status = VulnerabilityStatus('open', 'Test finding', 'Test comments')
        assert status.status == 'open'
        assert status.finding_details == 'Test finding'
        assert status.comments == 'Test comments'
        assert not status.has_severity_override()

    def test_create_invalid_status(self):
        """Test creating an invalid vulnerability status."""
        with pytest.raises(ValidationError):
            VulnerabilityStatus('invalid_status')

    def test_severity_override_validation(self):
        """Test severity override validation."""
        # Valid override
        status = VulnerabilityStatus('open', severity_override='high', severity_justification='Test justification')
        assert status.has_severity_override()
        assert status.severity_override == 'high'
        assert status.severity_justification == 'Test justification'

        # Invalid override
        with pytest.raises(ValidationError):
            VulnerabilityStatus('open', severity_override='invalid', severity_justification='Test')

        # Override without justification
        with pytest.raises(ValidationError):
            VulnerabilityStatus('open', severity_override='high')

    def test_status_methods(self):
        """Test status checking methods."""
        open_status = VulnerabilityStatus('open')
        closed_status = VulnerabilityStatus('not_a_finding')

        assert open_status.is_open()
        assert not open_status.is_closed()
        assert open_status.requires_review()

        assert not closed_status.is_open()
        assert closed_status.is_closed()
        assert not closed_status.requires_review()

    def test_display_methods(self):
        """Test display methods."""
        status = VulnerabilityStatus('not_a_finding')
        assert status.get_display_status() == 'Not a Finding'

        status_with_override = VulnerabilityStatus('open', severity_override='high', severity_justification='Test')
        assert status_with_override.get_display_severity_override() == 'High'

    def test_bulk_update_eligibility(self):
        """Test bulk update eligibility."""
        not_reviewed = VulnerabilityStatus('not_reviewed')
        open_status = VulnerabilityStatus('open')

        assert not_reviewed.can_be_bulk_updated()
        assert not open_status.can_be_bulk_updated()


class TestSeverityCategory:
    """Test SeverityCategory value object."""

    def test_create_valid_categories(self):
        """Test creating valid severity categories."""
        cat1 = SeverityCategory('cat1')
        cat2 = SeverityCategory('cat2')
        cat3 = SeverityCategory('cat3')

        assert cat1.category == 'cat1'
        assert cat1.name == 'CAT I'
        assert cat1.description == 'High'
        assert cat1.weight == 3

        assert cat2.category == 'cat2'
        assert cat2.name == 'CAT II'
        assert cat2.description == 'Medium'
        assert cat2.weight == 2

        assert cat3.category == 'cat3'
        assert cat3.name == 'CAT III'
        assert cat3.description == 'Low'
        assert cat3.weight == 1

    def test_create_invalid_category(self):
        """Test creating an invalid severity category."""
        with pytest.raises(ValidationError):
            SeverityCategory('invalid')

    def test_category_methods(self):
        """Test category checking methods."""
        cat1 = SeverityCategory('cat1')
        cat2 = SeverityCategory('cat2')
        cat3 = SeverityCategory('cat3')

        assert cat1.is_high()
        assert cat1.is_critical()
        assert not cat1.is_medium()
        assert not cat1.is_low()

        assert cat2.is_medium()
        assert not cat2.is_high()

        assert cat3.is_low()
        assert not cat3.is_high()

    def test_sorting(self):
        """Test category sorting by weight."""
        cat1 = SeverityCategory('cat1')
        cat2 = SeverityCategory('cat2')
        cat3 = SeverityCategory('cat3')

        # Higher weight (more severe) should sort first
        categories = [cat3, cat1, cat2]
        categories.sort(reverse=True)  # Highest first
        assert categories == [cat1, cat2, cat3]

    def test_string_representation(self):
        """Test string representation."""
        cat1 = SeverityCategory('cat1')
        assert str(cat1) == 'CAT I'
        assert cat1.name == 'CAT I'

    def test_class_factory_methods(self):
        """Test class factory methods."""
        high = SeverityCategory.high()
        medium = SeverityCategory.medium()
        low = SeverityCategory.low()

        assert high.is_high()
        assert medium.is_medium()
        assert low.is_low()

    def test_from_weight(self):
        """Test creating category from weight."""
        high = SeverityCategory.from_weight(3)
        medium = SeverityCategory.from_weight(2)
        low = SeverityCategory.from_weight(1)

        assert high.is_high()
        assert medium.is_medium()
        assert low.is_low()

        # Invalid weight
        with pytest.raises(ValidationError):
            SeverityCategory.from_weight(99)
