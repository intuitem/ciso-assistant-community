from core.views import BaseModelViewSet as AbstractBaseModelViewSet
from .models import CVE, CWE


class BaseModelViewSet(AbstractBaseModelViewSet):
    serializers_module = "sec_intel.serializers"


class CVEViewSet(BaseModelViewSet):
    """
    API endpoint that allows CVEs to be viewed or edited.
    """

    model = CVE
    filterset_fields = [
        "folder",
        "provider",
        "library",
        "filtering_labels",
        "urn",
    ]
    search_fields = ["name", "ref_id", "description", "cvss_vector"]


class CWEViewSet(BaseModelViewSet):
    """
    API endpoint that allows CWEs to be viewed or edited.
    """

    model = CWE
    filterset_fields = [
        "folder",
        "provider",
        "library",
        "filtering_labels",
        "urn",
    ]
    search_fields = ["name", "ref_id", "description"]
