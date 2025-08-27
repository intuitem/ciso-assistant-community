from global_settings.models import GlobalSettings
from global_settings.serializers import FeatureFlagsSerializer
import structlog

logger = structlog.get_logger(__name__)


def ff_is_enabled(feature_flag: str):
    """
    Checks if a feature flag is enabled.
    Parameters:
        `feature_flag` (str): The name of the feature flag to check.
    Returns:
        `True` if the feature flag is enabled, `False` otherwise.
    """
    ff_settings = GlobalSettings.objects.filter(
        name=GlobalSettings.Names.FEATURE_FLAGS
    ).first()
    if ff_settings is None:
        logger.warning(
            "Feature flags settings not found, returning False",
            feature_flag=feature_flag,
        )
        return False

    flags: dict[str, bool] = FeatureFlagsSerializer(instance=ff_settings.value).data

    if (flag := flags.get(feature_flag)) is None:
        logger.warning(
            "Feature flag not found, returning False", feature_flag=feature_flag
        )
        return False

    return flag
