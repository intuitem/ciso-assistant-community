from rest_framework.decorators import action
from rest_framework.response import Response

from core.views import BaseModelViewSet
from iam.models import Folder

from .models import CustomFieldDefinition, FieldType


class CustomFieldDefinitionViewSet(BaseModelViewSet):
    model = CustomFieldDefinition
    serializers_module = "custom_fields.serializers"
    filterset_fields = ["folder", "field_type", "required", "filterable", "visible"]
    search_fields = ["key", "label"]
    ordering = ["order", "key"]

    def get_queryset(self):
        queryset = super().get_queryset()
        params = self.request.query_params

        model = params.get("model")
        if model and "." in model:
            app_label, model_name = model.lower().split(".", 1)
            queryset = queryset.filter(
                content_type__app_label=app_label,
                content_type__model=model_name,
            )

        # ?for_folder=<id> returns the definitions that apply to objects in that
        # folder: global ones plus those owned by an ancestor-or-self folder.
        for_folder = params.get("for_folder")
        if for_folder:
            folder = Folder.objects.filter(pk=for_folder).first()
            folder_ids = {Folder.get_root_folder_id()}
            if folder is not None:
                folder_ids |= CustomFieldDefinition._ancestor_or_self_ids(folder)
            queryset = queryset.filter(folder_id__in=folder_ids)

        return queryset.prefetch_related("choices")

    @action(detail=False, name="Get field type choices")
    def field_type(self, request):
        return Response(
            [{"value": v, "label": str(label)} for v, label in FieldType.choices]
        )
