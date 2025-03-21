from rest_framework.response import Response
from iam.models import Folder, RoleAssignment, UserGroup
from core.views import BaseModelViewSet as AbstractBaseModelViewSet
from tprm.models import Entity, Representative, Solution, EntityAssessment
from rest_framework.decorators import action
import structlog

from rest_framework.request import Request
from rest_framework.response import Response

from django.utils.formats import date_format

logger = structlog.get_logger(__name__)


class BaseModelViewSet(AbstractBaseModelViewSet):
    serializers_module = "tprm.serializers"


# Create your views here.
class EntityViewSet(BaseModelViewSet):
    """
    API endpoint that allows entities to be viewed or edited.
    """

    model = Entity
    filterset_fields = ["folder"]


class EntityAssessmentViewSet(BaseModelViewSet):
    """
    API endpoint that allows entity assessments to be viewed or edited.
    """

    model = EntityAssessment
    filterset_fields = ["status", "perimeter", "perimeter__folder", "authors", "entity"]

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.compliance_assessment:
            folder = instance.compliance_assessment.folder
            instance.compliance_assessment.delete()
            if folder.content_type == Folder.ContentType.ENCLAVE:
                folder.delete()
            else:
                logger.warning("Compliance assessment folder is not an Enclave", folder)

        return super().destroy(request, *args, **kwargs)

    @action(detail=False, name="Get status choices")
    def status(self, request):
        return Response(dict(EntityAssessment.Status.choices))

    @action(detail=False, name="Get conclusion choices")
    def conclusion(self, request):
        return Response(dict(EntityAssessment.Conclusion.choices))

    @action(detail=False, name="Get TPRM metrics")
    def metrics(self, request):
        assessments_data = []

        (viewable_items, _, _) = RoleAssignment.get_accessible_object_ids(
            folder=Folder.get_root_folder(),
            user=request.user,
            object_type=EntityAssessment,
        )

        for ea in EntityAssessment.objects.filter(id__in=viewable_items):
            entry = {
                "provider": ea.entity.name,
                "solutions": ",".join([sol.name for sol in ea.solutions.all()])
                if len(ea.solutions.all()) > 0
                else "-",
                "baseline": ea.compliance_assessment.framework.name,
                "due_date": ea.due_date.strftime("%Y-%m-%d") if ea.due_date else "-",
                "last_update": ea.updated_at.strftime("%Y-%m-%d")
                if ea.updated_at
                else "-",
                "conclusion": ea.conclusion if ea.conclusion else "ongoing",
            }

            progress = 70
            entry.update({"progress": progress})

            assessments_data.append(entry)

        return Response(assessments_data)


class RepresentativeViewSet(BaseModelViewSet):
    """
    API endpoint that allows representatives to be viewed or edited.
    """

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.user:
            instance.user.delete()

        return super().destroy(request, *args, **kwargs)

    model = Representative
    filterset_fields = ["entity"]


class SolutionViewSet(BaseModelViewSet):
    """
    API endpoint that allows solutions to be viewed or edited.
    """

    model = Solution
    filterset_fields = ["provider_entity"]

    def perform_create(self, serializer):
        serializer.save()
        solution = serializer.instance
        solution.recipient_entity = Entity.objects.get(builtin=True)
        solution.save()
