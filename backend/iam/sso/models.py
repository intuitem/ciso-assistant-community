from allauth.socialaccount import models as socialaccount_models
from django.db import models


class IdentityProvider(socialaccount_models.SocialApp):
    created_at = models.DateTimeField(auto_now_add=True)
