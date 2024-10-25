from allauth.socialaccount.providers.saml.provider import SAMLProvider


DEFAULT_SAML_ATTRIBUTE_MAPPING = SAMLProvider.default_attribute_mapping

DEFAULT_SAML_SETTINGS = {
    "attribute_mapping": {
        "uid": DEFAULT_SAML_ATTRIBUTE_MAPPING["uid"],
        "email_verified": DEFAULT_SAML_ATTRIBUTE_MAPPING["email_verified"],
        "email": DEFAULT_SAML_ATTRIBUTE_MAPPING["email"],
    },
    "idp": {
        "entity_id": "",
        "metadata_url": "",
        "sso_url": "",
        "slo_url": "",
        "x509cert": "",
    },
    "sp": {
        "entity_id": "ciso-assistant",
    },
    "advanced": {
        "allow_repeat_attribute_name": True,
        "allow_single_label_domains": False,
        "authn_request_signed": False,
        "digest_algorithm": "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256",
        "logout_request_signed": False,
        "logout_response_signed": False,
        "metadata_signed": False,
        "name_id_encrypted": False,
        "reject_deprecated_algorithm": True,
        "reject_idp_initiated_sso": True,
        "signature_algorithm": "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256",
        "want_assertion_encrypted": False,
        "want_assertion_signed": False,
        "want_attribute_statement": True,
        "want_message_signed": False,
        "want_name_id": False,
        "want_name_id_encrypted": False,
    },
}
