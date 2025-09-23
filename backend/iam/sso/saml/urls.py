from django.urls import include, path, re_path

from . import views


urlpatterns = [
    re_path(
        r"^(?P<organization_slug>[^/]+)/",
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
                path(
                    "generate-keys/",
                    views.GenerateSAMLKeyView.as_view(),
                    name="generate_saml_keys",
                ),
                path(
                    "download-cert/",
                    views.DownloadSAMLPublicCertView.as_view(),
                    name="download_saml_cert",
                ),
            ]
        ),
    )
]
