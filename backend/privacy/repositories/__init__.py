"""
Privacy Repositories Package
"""

from .data_asset_repository import DataAssetRepository
from .consent_record_repository import ConsentRecordRepository
from .data_subject_right_repository import DataSubjectRightRepository

__all__ = [
    'DataAssetRepository',
    'ConsentRecordRepository',
    'DataSubjectRightRepository',
]
