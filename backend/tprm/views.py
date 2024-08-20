from core.views import BaseModelViewSet as AbstractBaseModelViewSet
from tprm.models import Entity

class BaseModelViewSet(AbstractBaseModelViewSet):
    serializers_module = "tprm.serializers"

# Create your views here.
class EntityViewSet(BaseModelViewSet):
    """
    API endpoint that allows folders to be viewed or edited.
    """

    model = Entity