from global_settings.models import GlobalSettings
from global_settings.serializers import FeatureFlagsSerializer
import structlog

logger = structlog.get_logger(__name__)


def ff_is_enabled(feature_flag: str):
    ff_settings = GlobalSettings.objects.filter(
        name=GlobalSettings.Names.FEATURE_FLAGS
    ).first()
    if ff_settings is None:
        logger.warning(
            "Feature flags settings not found, returning False",
            feature_flag=feature_flag,
        )
        return False

    flags: dict[str, bool] = ff_settings.value

    if (flag := flags.get(feature_flag)) is None:
        logger.warning(
            "Feature flag not found, returning False", feature_flag=feature_flag
        )
        return False

    return flag


def general_setting_is_enabled(key: str) -> bool:
    """Check whether a boolean key in the 'general' GlobalSettings is enabled.
    Returns False when the settings row or the key is missing."""
    gs = GlobalSettings.objects.filter(name="general").only("value").first()
    if gs is None or not isinstance(gs.value, dict):
        return False
    return bool(gs.value.get(key, False))
