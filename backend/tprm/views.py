from core.views import BaseModelViewSet as AbstractBaseModelViewSet
from tprm.models import Entity, Representative, Solution, Product, EntityAssessment


class BaseModelViewSet(AbstractBaseModelViewSet):
    serializers_module = "tprm.serializers"


# Create your views here.
class EntityViewSet(BaseModelViewSet):
    """
    API endpoint that allows entities to be viewed or edited.
    """

    model = Entity


class EntityAssessmentViewSet(BaseModelViewSet):
    """
    API endpoint that allows entity assessments to be viewed or edited.
    """

    model = EntityAssessment


class RepresentativeViewSet(BaseModelViewSet):
    """
    API endpoint that allows representatives to be viewed or edited.
    """

    model = Representative
    filterset_fields = ["entity"]


class SolutionViewSet(BaseModelViewSet):
    """
    API endpoint that allows solutions to be viewed or edited.
    """

    model = Solution


class ProductViewSet(BaseModelViewSet):
    """
    API endpoint that allows products to be viewed or edited.
    """

    model = Product
