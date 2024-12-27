from allauth.headless.base.views import APIView
from allauth.headless.socialaccount.forms import RedirectToProviderForm
from allauth.socialaccount import providers
from allauth.socialaccount.providers.saml.views import render_authentication_error
from core.views import BaseModelViewSet as AbstractBaseModelViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from structlog import get_logger

from .models import SSOSettings
from .serializers import SSOSettingsWriteSerializer

logger = get_logger(__name__)


class RedirectToProviderView(APIView):
    handle_json_input = False

    def post(self, request, *args, **kwargs):
        form = RedirectToProviderForm(request.POST)
        if not form.is_valid():
            return render_authentication_error(
                request,
                provider=request.POST.get("provider"),
                exception=ValidationError(form.errors),
            )
        provider = form.cleaned_data["provider"]
        next_url = form.cleaned_data["callback_url"]
        process = form.cleaned_data["process"]
        try:
            return provider.redirect(
                request,
                process,
                next_url=next_url,
                headless=True,
            )
        except:
            logger.error("Cannot perform redirection, Check your IdP URLs")
            return render_authentication_error(request, provider, error="failedSSO")


class BaseModelViewSet(AbstractBaseModelViewSet):
    serializers_module = "iam.sso.serializers"


class SSOSettingsViewSet(BaseModelViewSet):
    model = SSOSettings

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @action(detail=True, name="Get provider choices")
    def provider(self, request):
        _providers = providers.registry.as_choices()
        return Response({p[0]: p[1] for p in _providers})

    def get_object(self):
        obj = self.model.objects.get()
        self.check_object_permissions(self.request, obj)
        return obj

    @action(detail=True, name="Get write data")
    def object(self, request, pk=None):
        return Response(SSOSettingsWriteSerializer(self.get_object()).data)
