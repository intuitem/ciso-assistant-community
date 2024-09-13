from rest_framework.response import Response
from core.views import BaseModelViewSet as AbstractBaseModelViewSet
from tprm.models import Entity, Representative, Solution, EntityAssessment
from rest_framework.decorators import action

from tprm.serializers import EntityAssessmentCreateSerializer


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
    filterset_fields = ["status", "project", "project__folder", "authors", "entity"]

    def get_serializer_class(self, **kwargs):
        if self.action == "create":
            return EntityAssessmentCreateSerializer
        return super().get_serializer_class(**kwargs)
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.compliance_assessment:
            instance.compliance_assessment.delete()
        return super().destroy(request, *args, **kwargs)

    @action(detail=False, name="Get status choices")
    def status(self, request):
        return Response(dict(EntityAssessment.Status.choices))


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

    def perform_create(self, serializer):
        serializer.save()
        solution = serializer.instance
        solution.recipient_entity = Entity.objects.get(builtin=True)
        solution.save()
