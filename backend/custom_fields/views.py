from rest_framework.decorators import action
from rest_framework.response import Response

from core.views import BaseModelViewSet

from .models import CustomFieldDefinition, FieldType


class CustomFieldDefinitionViewSet(BaseModelViewSet):
    model = CustomFieldDefinition
    serializers_module = "custom_fields.serializers"
    filterset_fields = ["folder", "field_type", "required", "filterable"]
    search_fields = ["key", "label"]
    ordering = ["order", "key"]

    def get_queryset(self):
        queryset = super().get_queryset()
        model = self.request.query_params.get("model")
        if model and "." in model:
            app_label, model_name = model.lower().split(".", 1)
            queryset = queryset.filter(
                content_type__app_label=app_label,
                content_type__model=model_name,
            )
        return queryset.prefetch_related("choices")

    @action(detail=False, name="Get field type choices")
    def field_type(self, request):
        return Response(
            [{"value": v, "label": label} for v, label in FieldType.choices]
        )
