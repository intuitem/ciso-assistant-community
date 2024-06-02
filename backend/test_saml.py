from onelogin.saml2.auth import OneLogin_Saml2_Auth
from onelogin.saml2.settings import OneLogin_Saml2_Settings
from onelogin.saml2.utils import OneLogin_Saml2_Utils
import json

SETTINGS_DATA = """{
    // If strict is True, then the Python Toolkit will reject unsigned
    // or unencrypted messages if it expects them to be signed or encrypted.
    // Also it will reject the messages if the SAML standard is not strictly
    // followed. Destination, NameId, Conditions ... are validated too.
    "strict": true,
    // Enable debug mode (outputs errors).
    "debug": true,
    // Service Provider Data that we are deploying.
    "sp": {
        // Identifier of the SP entity  (must be a URI)
        "entityId": "https://localhost:8443/metadata/",
        // Specifies info about where and how the <AuthnResponse> message MUST be
        // returned to the requester, in this case our SP.
        "assertionConsumerService": {
            // URL Location where the <Response> from the IdP will be returned
            "url": "https://localhost:8443/?acs",
            // SAML protocol binding to be used when returning the <Response>
            // message. SAML Toolkit supports this endpoint for the
            // HTTP-POST binding only.
            "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
        },
        // Specifies info about where and how the <Logout Request/Response> message MUST be sent.
        "singleLogoutService": {
            // URL Location where the <LogoutRequest> from the IdP will be sent (IdP-initiated logout)
            "url": "https://localhost:8443/?sls",
            // URL Location where the <LogoutResponse> from the IdP will sent (SP-initiated logout, reply)
            // OPTIONAL: only specify if different from url parameter
            //"responseUrl": "https://localhost:8443/?sls",
            // SAML protocol binding to be used when returning the <Response>
            // message. SAML Toolkit supports the HTTP-Redirect binding
            // only for this endpoint.
            "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
        },
        // If you need to specify requested attributes, set a
        // attributeConsumingService. nameFormat, attributeValue and
        // friendlyName can be omitted
        //"attributeConsumingService": {
                // OPTIONAL: only specify if SP requires this.
                // index is an integer which identifies the attributeConsumingService used
                // to the SP. SAML toolkit supports configuring only one attributeConsumingService
                // but in certain cases the SP requires a different value.  Defaults to '1'.
                // "index": '1',
        //        "serviceName": "SP test",
        //       "serviceDescription": "Test Service",
        //        "requestedAttributes": [
        //            {
        //               "name": "",
        //                "isRequired": false,
        //                "nameFormat": "",
        //                "friendlyName": "",
        //                "attributeValue": []
        //            }
        //        ]
        //},
        // Specifies the constraints on the name identifier to be used to
        // represent the requested subject.
        // Take a look on src/onelogin/saml2/constants.py to see the NameIdFormat that are supported.
        "NameIDFormat": "urn:oasis:names:tc:SAML:1.1:nameid-format:unspecified"
        // Usually X.509 cert and privateKey of the SP are provided by files placed at
        // the certs folder. But we can also provide them with the following parameters
        //"x509cert": "",
        //"privateKey": ""
        //
        // Key rollover
        // If you plan to update the SP X.509cert and privateKey
        // you can define here the new X.509cert and it will be
        // published on the SP metadata so Identity Providers can
        // read them and get ready for rollover.
        //
        // 'x509certNew': '',
    },
    // Identity Provider Data that we want connected with our SP.
    "idp": {
        // Identifier of the IdP entity  (must be a URI)
        "entityId": "https://app.onelogin.com/saml/metadata/<onelogin_connector_id>",
        // SSO endpoint info of the IdP. (Authentication Request protocol)
        "singleSignOnService": {
            // URL Target of the IdP where the Authentication Request Message
            // will be sent.
            "url": "https://app.onelogin.com/trust/saml2/http-post/sso/<onelogin_connector_id>",
            // SAML protocol binding to be used when returning the <Response>
            // message. SAML Toolkit supports the HTTP-Redirect binding
            // only for this endpoint.
            "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
        },
        // SLO endpoint info of the IdP.
        "singleLogoutService": {
            // URL Location where the <LogoutRequest> from the IdP will be sent (IdP-initiated logout)
            "url": "https://app.onelogin.com/trust/saml2/http-redirect/slo/<onelogin_connector_id>",
            // URL Location where the <LogoutResponse> from the IdP will sent (SP-initiated logout, reply)
            // OPTIONAL: only specify if different from url parameter
            "responseUrl": "https://app.onelogin.com/trust/saml2/http-redirect/slo_return/<onelogin_connector_id>",
            // SAML protocol binding to be used when returning the <Response>
            // message. SAML Toolkit supports the HTTP-Redirect binding
            // only for this endpoint.
            "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
        },
        // Public X.509 certificate of the IdP
        "x509cert": "<onelogin_connector_cert>"
        //
        //  Instead of using the whole X.509cert you can use a fingerprint in order to
        //  validate a SAMLResponse (but you still need the X.509cert to validate LogoutRequest and LogoutResponse using the HTTP-Redirect binding).
        //  But take in mind that the algorithm for the fingerprint should be as strong as the algorithm in a normal certificate signature
	    //  e.g. SHA256 or strong)
        //
        //  (openssl x509 -noout -fingerprint -in "idp.crt" to generate it,
        //  or add for example the -sha256 , -sha384 or -sha512 parameter)
        //
        //  If a fingerprint is provided, then the certFingerprintAlgorithm is required in order to
        //  let the toolkit know which algorithm was used.
        //ossible values: sha1, sha256, sha384 or sha512
        //  'sha1' is the default value.
        //
        //  Notice that if you want to validate any SAML Message sent by the HTTP-Redirect binding, you
        //  will need to provide the whole X.509cert.
        //
        // "certFingerprint": "",
        // "certFingerprintAlgorithm": "sha1",
        // In some scenarios the IdP uses different certificates for
        // signing/encryption, or is under key rollover phase and
        // more than one certificate is published on IdP metadata.
        // In order to handle that the toolkit offers that parameter.
        // (when used, 'X.509cert' and 'certFingerprint' values are
        // ignored).
        //
        // 'x509certMulti': {
        //      'signing': [
        //          '<cert1-string>'
        //      ],
        //      'encryption': [
        //          '<cert2-string>'
        //      ]
        // }
    }
}
"""

s = ''.join(l+'\n' if not l.lstrip().startswith('//') else '' for l in SETTINGS_DATA.split('\n'))
for i, s2 in enumerate(s.split('\n'), start=1): 
    print(i, s2)
settings = OneLogin_Saml2_Settings(json.loads(s))