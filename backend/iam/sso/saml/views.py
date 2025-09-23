# === Python standard library ===
import json
from datetime import datetime, timedelta
from django.http import HttpRequest, HttpResponseRedirect, HttpResponse
from django.http.response import Http404
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View

# === Third-party packages ===
import structlog
from rest_framework.views import APIView
from django.views.decorators.csrf import csrf_exempt
from rest_framework.response import Response
from rest_framework import status

from cryptography import x509
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from allauth.account.models import EmailAddress
from allauth.core.exceptions import SignupClosedException
from allauth.socialaccount.adapter import get_account_adapter
from allauth.socialaccount.internal.flows.login import (
    pre_social_login,
    record_authentication,
)
from allauth.socialaccount.models import PermissionDenied, SocialLogin
from allauth.socialaccount.providers.saml.provider import SAMLProvider
from allauth.socialaccount.providers.saml.views import (
    AuthProcess,
    LoginSession,
    OneLogin_Saml2_Error,
    SAMLViewMixin,
    binascii,
    build_auth,
    decode_relay_state,
    httpkit,
    render_authentication_error,
)
from allauth.utils import ValidationError

# === Application-specific imports ===
from core.permissions import IsAdministrator  # ou une permission plus adaptée
from iam.models import User
from iam.sso.errors import AuthError
from iam.sso.models import SSOSettings
from iam.utils import generate_token
from global_settings.models import GlobalSettings

DEFAULT_SAML_ATTRIBUTE_MAPPING_EMAIL = SAMLProvider.default_attribute_mapping["email"]

logger = structlog.get_logger(__name__)


@method_decorator(csrf_exempt, name="dispatch")
class ACSView(SAMLViewMixin, View):
    def dispatch(self, request, organization_slug):
        url = reverse(
            "saml_finish_acs",
            kwargs={"organization_slug": organization_slug},
        )
        response = HttpResponseRedirect(url)
        acs_session = LoginSession(request, "saml_acs_session", "saml-acs-session")
        acs_session.store.update({"request": httpkit.serialize_request(request)})
        acs_session.save(response)
        return response


class FinishACSView(SAMLViewMixin, View):
    def dispatch(self, request, organization_slug):
        error = None
        next_url = "/"
        if len(SSOSettings.objects.all()) == 0:
            raise Http404()
        try:
            provider = self.get_provider(organization_slug)
        except:
            logger.error("Could not get provider")
            return render_authentication_error(
                request, None, error=AuthError.FAILED_TO_CONTACT_PROVIDER
            )
        acs_session = LoginSession(request, "saml_acs_session", "saml-acs-session")
        acs_request = None
        acs_request_data = acs_session.store.get("request")
        if acs_request_data:
            acs_request = httpkit.deserialize_request(acs_request_data, HttpRequest())
        acs_session.delete()
        if not acs_request:
            logger.error("Unable to finish login, SAML ACS session missing")
            return render_authentication_error(request, provider)

        auth = build_auth(acs_request, provider)
        error_reason = None
        errors = []
        user = None
        try:
            # We're doing the check for a valid `InResponeTo` ourselves later on
            # (*) by checking if there is a matching state stashed.
            auth.process_response(request_id=None)
        except binascii.Error:
            errors = ["invalid_response"]
            error_reason = "Invalid response"
        except OneLogin_Saml2_Error as e:
            errors = ["error"]
            error_reason = str(e)
        if not errors:
            errors = auth.get_errors()
        if errors:
            # e.g. ['invalid_response']
            error_reason = auth.get_last_error_reason() or error_reason
            logger.error(
                "Error processing SAML ACS response: %s: %s"
                % (", ".join(errors), error_reason)
            )
            return render_authentication_error(
                request,
                provider,
                extra_context={
                    "saml_errors": errors,
                    "saml_last_error_reason": error_reason,
                },
            )
        if not auth.is_authenticated():
            return render_authentication_error(
                request, provider, error=AuthError.CANCELLED
            )
        login: SocialLogin = provider.sociallogin_from_response(request, auth)
        # (*) If we (the SP) initiated the login, there should be a matching
        # state.
        state_id = auth.get_last_response_in_response_to()
        if state_id:
            login.state = provider.unstash_redirect_state(request, state_id)
        else:
            # IdP initiated SSO
            reject = provider.app.settings.get("advanced", {}).get(
                "reject_idp_initiated_sso", True
            )
            if reject:
                logger.error("IdP initiated SSO rejected")
                return render_authentication_error(
                    request, provider, error=AuthError.IDP_INITIATED_SSO_REJECTED
                )
            next_url = (
                decode_relay_state(acs_request.POST.get("RelayState")) or next_url
            )
            login.state["process"] = AuthProcess.LOGIN
            login.state["next"] = next_url
        try:
            attribute_mapping = provider.app.settings.get("attribute_mapping", {})
            # our parameter is either:
            #   - a list with attributes (normal case)
            #   - a list with a comma-separated string of attributes (frontend non-optimal behavior)
            email_attributes_string = attribute_mapping.get("email", [])
            email_attributes = [
                item.strip() for y in email_attributes_string for item in y.split(",")
            ] or DEFAULT_SAML_ATTRIBUTE_MAPPING_EMAIL
            emails = [auth.get_attribute(x) or [] for x in email_attributes]
            emails = [x for xs in emails for x in xs]  # flatten
            emails.append(auth.get_nameid())  # default behavior
            user = User.objects.get(email__in=emails)
            idp_first_names = auth.get_attribute(
                "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname"
            )
            idp_last_names = auth.get_attribute(
                "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname"
            )
            user.first_name = idp_first_names[0] if idp_first_names else user.first_name
            user.last_name = idp_last_names[0] if idp_last_names else user.last_name
            user.save()
            token = generate_token(user)
            login.state["next"] += f"sso/authenticate/{token}"
            pre_social_login(request, login)
            if request.user.is_authenticated:
                get_account_adapter(request).logout(request)
            login._accept_login(request)  # complete_social_login not working
            record_authentication(request, login)
        except User.DoesNotExist as e:
            # NOTE: We might want to allow signup some day
            error = AuthError.USER_DOES_NOT_EXIST
            logger.error("User does not exist", exc_info=e)
        except SignupClosedException as e:
            error = AuthError.SIGNUP_CLOSED
            logger.error("Signup closed", exc_info=e)
        except PermissionDenied as e:
            error = AuthError.PERMISSION_DENIED
            logger.error("Permission denied", exc_info=e)
        except ValidationError as e:
            error = e.code
            logger.error("Validation error", exc_info=e)
        except NotImplementedError as e:
            error = AuthError.USER_IS_NOT_SSO
            logger.error("SSO not permitted error", exc_info=e)
        except Exception as e:
            error = AuthError.FAILED_SSO
            logger.error("SSO failed", exc_info=e)
        finally:
            next_url = login.state["next"]
            if error:
                next_url = httpkit.add_query_params(
                    next_url,
                    {"error": error, "error_process": login.state["process"]},
                )
            elif user:
                email_object = EmailAddress.objects.filter(user=user).first()
                if email_object and not email_object.verified:
                    email_object.verified = True
                    email_object.save()
                    logger.info("Email verified", user=user)
            return HttpResponseRedirect(next_url)


class GenerateSAMLKeyView(SAMLViewMixin, APIView):
    """
    Endpoint to generate a key pair (private key + self-signed X.509 certificate).
    Accessible only to admins (to be adapted as needed).
    """

    permission_classes = [IsAdministrator]

    def post(self, request, organization_slug):
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            data = {}
        cn = data.get("common_name", "saml-sp.example.com")
        days = int(data.get("days", 365))

        # RSA key generation
        key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )

        # Self-signed certificate generation
        subject = issuer = x509.Name(
            [
                x509.NameAttribute(NameOID.COMMON_NAME, cn),
            ]
        )
        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.utcnow())
            .not_valid_after(datetime.utcnow() + timedelta(days=days))
            .sign(private_key=key, algorithm=hashes.SHA256())
        )

        private_key_pem = key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )

        cert_pem = cert.public_bytes(serialization.Encoding.PEM)

        provider = self.get_provider(organization_slug)
        # Retrieves the 'advanced' dictionary, or creates it if it doesn't exist
        advanced_settings = provider.app.settings.get("advanced", {})
        advanced_settings["private_key"] = private_key_pem.decode("utf-8")
        advanced_settings["x509cert"] = cert_pem.decode("utf-8")

        # Re-injects the dict into the application configuration
        settings = GlobalSettings.objects.get(name=GlobalSettings.Names.SSO)
        settings.value["settings"]["advanced"] = advanced_settings
        settings.save()

        return Response(
            {
                "message": f"Key and certificate saved in advanced settings of SP {organization_slug}",
                "cert": cert_pem.decode("utf-8"),
            },
            status=status.HTTP_201_CREATED,
        )


class DownloadSAMLPublicCertView(SAMLViewMixin, APIView):
    permission_classes = [IsAdministrator]

    def get(self, request, organization_slug):
        provider = self.get_provider(organization_slug)
        cert_pem = provider.app.settings.get("advanced", {}).get("x509cert")
        if not cert_pem:
            return HttpResponse(status=404)

        response = HttpResponse(cert_pem, content_type="application/x-pem-file")
        response["Content-Disposition"] = (
            'attachment; filename="ciso-saml-public-cert.pem"'
        )
        return response
