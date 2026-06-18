from django.core.exceptions import ValidationError
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import SAFE_METHODS
from rest_framework.response import Response

from core.views import BaseModelViewSet
from global_settings.utils import ff_is_enabled
from iam.models import Folder

from .models import CustomFieldDefinition, FieldType


class CustomFieldDefinitionViewSet(BaseModelViewSet):
    model = CustomFieldDefinition
    serializers_module = "custom_fields.serializers"
    filterset_fields = ["folder", "field_type", "required", "filterable", "visible"]
    search_fields = ["key", "label"]
    ordering = ["order", "key"]

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        # Reads degrade to an empty list when the feature is off (see get_queryset);
        # writes are rejected.
        if request.method not in SAFE_METHODS and not ff_is_enabled("custom_fields"):
            raise PermissionDenied("Custom fields are not enabled.")

    def get_queryset(self):
        queryset = super().get_queryset()
        if not ff_is_enabled("custom_fields"):
            return queryset.none()
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
            try:
                folder = Folder.objects.filter(pk=for_folder).first()
            except ValueError, ValidationError:
                return queryset.none()
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
