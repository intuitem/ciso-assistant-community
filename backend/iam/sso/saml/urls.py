from django.urls import include, path, re_path

from . import views


urlpatterns = [
    re_path(
        r"^saml/(?P<organization_slug>[^/]+)/",
        include(
            [
                path(
                    "acs/",
                    views.ACSView.as_view(),
                    name="saml_acs",
                ),
                path(
                    "acs/finish/",
                    views.FinishACSView.as_view(),
                    name="saml_finish_acs",
                ),
            ]
        ),
    )
]
