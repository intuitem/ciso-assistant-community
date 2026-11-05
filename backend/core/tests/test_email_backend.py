"""Regression tests for the EMAIL_FORCE_TLS_1_2 SMTP backend.

Django 6 dropped the ``ssl_context`` kwarg on the SMTP backend, which turned
the setting into a silent no-op. The pin now lives in ``core.email_backend``.
"""

import datetime
import socket
import ssl
import threading
from unittest.mock import patch

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

from django.test import override_settings
from django.utils.module_loading import import_string

from ciso_assistant.mailers import build_mailers
from core.email_backend import EmailBackend


@override_settings(EMAIL_FORCE_TLS_1_2=True)
def test_ssl_context_is_pinned_to_tls12_when_flag_on():
    context = EmailBackend(alias="test", host="smtp.example").ssl_context
    assert context.minimum_version == ssl.TLSVersion.TLSv1_2
    assert context.maximum_version == ssl.TLSVersion.TLSv1_2
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname is True


@override_settings(EMAIL_FORCE_TLS_1_2=True)
def test_tls12_pin_keeps_client_certificate():
    with patch.object(ssl.SSLContext, "load_cert_chain") as load_cert_chain:
        context = EmailBackend(
            alias="test",
            host="smtp.example",
            ssl_certfile="/etc/ssl/client.pem",
            ssl_keyfile="/etc/ssl/client.key",
        ).ssl_context
    load_cert_chain.assert_called_once_with(
        "/etc/ssl/client.pem", "/etc/ssl/client.key"
    )
    assert context.minimum_version == ssl.TLSVersion.TLSv1_2
    assert context.maximum_version == ssl.TLSVersion.TLSv1_2


@override_settings(EMAIL_FORCE_TLS_1_2=False)
def test_ssl_context_is_default_when_flag_off():
    context = EmailBackend(alias="test", host="smtp.example").ssl_context
    default = ssl.create_default_context()
    assert isinstance(context, ssl.SSLContext)
    assert context.minimum_version == default.minimum_version
    assert context.maximum_version == default.maximum_version
    assert context.maximum_version == ssl.TLSVersion.MAXIMUM_SUPPORTED
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname is True


def test_environment_smtp_mailers_use_the_pinned_backend():
    mailers = build_mailers(
        {"EMAIL_HOST": "smtp.example", "EMAIL_HOST_RESCUE": "smtp2.example"}
    )
    assert list(mailers) == ["default", "rescue"]
    for mailer in mailers.values():
        assert import_string(mailer["BACKEND"]) is EmailBackend


# --- a real handshake with a client certificate ------------------------------


def _issue(tmp_path, name, *, ca=None, server=False):
    """Write a key and certificate for ``name``; self-signed CA when ``ca`` is
    None. Returns (cert_path, key_path, cert, key)."""
    key = ec.generate_private_key(ec.SECP256R1())
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, name)])
    issuer_cert, issuer_key = (ca[2], ca[3]) if ca else (None, key)
    now = datetime.datetime.now(datetime.UTC)
    builder = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer_cert.subject if issuer_cert else subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(minutes=1))
        .not_valid_after(now + datetime.timedelta(hours=1))
        .add_extension(
            x509.SubjectKeyIdentifier.from_public_key(key.public_key()), False
        )
    )
    if ca is None:
        builder = builder.add_extension(
            x509.BasicConstraints(ca=True, path_length=None), True
        ).add_extension(
            x509.KeyUsage(
                digital_signature=False,
                content_commitment=False,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=True,
                crl_sign=True,
                encipher_only=False,
                decipher_only=False,
            ),
            True,
        )
    else:
        usage = (
            ExtendedKeyUsageOID.SERVER_AUTH
            if server
            else (ExtendedKeyUsageOID.CLIENT_AUTH)
        )
        builder = (
            builder.add_extension(
                x509.BasicConstraints(ca=False, path_length=None), True
            )
            .add_extension(x509.ExtendedKeyUsage([usage]), False)
            .add_extension(
                x509.AuthorityKeyIdentifier.from_issuer_public_key(
                    issuer_key.public_key()
                ),
                False,
            )
        )
        if server:
            builder = builder.add_extension(
                x509.SubjectAlternativeName([x509.DNSName("localhost")]), False
            )
    cert = builder.sign(issuer_key, hashes.SHA256())
    cert_path, key_path = tmp_path / f"{name}.crt", tmp_path / f"{name}.key"
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    return cert_path, key_path, cert, key


def test_client_certificate_still_verifies_the_server(tmp_path, monkeypatch):
    # Django's own context for a client certificate trusts no CA at all, so
    # the handshake failed against every server. The server here requires
    # the client certificate, so the handshake also proves it is presented.
    ca = _issue(tmp_path, "test-ca")
    server_cert, server_key, *_ = _issue(tmp_path, "localhost", ca=ca, server=True)
    client_cert, client_key, *_ = _issue(tmp_path, "ciso-client", ca=ca)
    monkeypatch.setenv("SSL_CERT_FILE", str(ca[0]))

    server_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    server_context.load_cert_chain(server_cert, server_key)
    server_context.load_verify_locations(ca[0])
    server_context.verify_mode = ssl.CERT_REQUIRED
    listener = socket.create_server(("127.0.0.1", 0))
    seen = {}

    def serve():
        connection, _ = listener.accept()
        with server_context.wrap_socket(connection, server_side=True) as tls:
            seen["client"] = dict(item[0] for item in tls.getpeercert()["subject"])

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()

    context = EmailBackend(
        alias="test",
        host="localhost",
        ssl_certfile=str(client_cert),
        ssl_keyfile=str(client_key),
    ).ssl_context
    with socket.create_connection(listener.getsockname(), timeout=5) as raw:
        with context.wrap_socket(raw, server_hostname="localhost"):
            pass
    thread.join(timeout=5)
    listener.close()
    assert seen["client"]["commonName"] == "ciso-client"
