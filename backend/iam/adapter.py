from allauth.account.utils import perform_login
from allauth.socialaccount.helpers import ImmediateHttpResponse
from django.conf import settings
from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.core import context
from django.dispatch import receiver
from allauth.socialaccount.signals import pre_social_login
from django.contrib.auth import login, get_user_model
from rest_framework.response import Response
from rest_framework.status import HTTP_401_UNAUTHORIZED
from knox.views import LoginView
from django.utils.http import url_has_allowed_host_and_scheme
from urllib.parse import urlparse

User = get_user_model()


class MyAccountAdapter(DefaultAccountAdapter):
    def is_open_for_signup(self, request):
        return False
    
    def is_safe_url(self, url):
        
        allowed_hosts = {urlparse(settings.CISO_ASSISTANT_URL).hostname} | set(settings.ALLOWED_HOSTS)
        
        if urlparse(url).port:
            url = url.replace(':' + str(urlparse(url).port), '')
            
        return url_has_allowed_host_and_scheme(url, allowed_hosts=allowed_hosts)


class MySocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        email_address = next(iter(sociallogin.account.extra_data.values()))[0]
        try:
            user = User.objects.get(email=email_address)
            sociallogin.user = user
            sociallogin.connect(request, user)
        except User.DoesNotExist:
            return Response(
                {"message": "User not found."}, status=HTTP_401_UNAUTHORIZED
            )
