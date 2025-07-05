from allauth.socialaccount.providers.saml.views import AuthError as AllauthAuthError


class AuthError(AllauthAuthError):
    IDP_INITIATED_SSO_REJECTED = "idpInitiatedSSORejected"
    SIGNUP_CLOSED = "signupClosed"
    PERMISSION_DENIED = "permissionDenied"
    FAILED_SSO = "failedSSO"
    FAILED_TO_CONTACT_PROVIDER = "failedToContactProvider"
    USER_DOES_NOT_EXIST = "UserDoesNotExist"
    USER_IS_NOT_SSO = "userIsNotSSO"
