from rest_framework import serializers

from core.serializers import BaseModelSerializer
from iam.models import Folder, RoleAssignment
from .models import WebhookEndpoint, WebhookEventType


class WebhookEndpointSerializer(BaseModelSerializer):
    """
    Serializer for the WebhookEndpoint model.
    Handles the 'show once' secret logic.
    """

    # This field is write-only, for user-provided secrets
    secret = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        help_text="HMAC signing secret",
    )

    event_types = serializers.SlugRelatedField(
        many=True,
        slug_field="name",
        queryset=WebhookEventType.objects.all(),
        required=False,
    )

    target_folders = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Folder.objects.all(), required=False
    )

    has_secret = serializers.SerializerMethodField()

    class Meta:
        model = WebhookEndpoint
        fields = [
            "id",
            "name",
            "description",
            "payload_format",
            "url",
            "event_types",
            "is_active",
            "created_at",
            "secret",
            "has_secret",
            "target_folders",
        ]
        read_only_fields = ["id", "created_at"]

    def get_has_secret(self, obj):
        """
        Indicates whether the webhook endpoint has a secret set.
        """
        return bool(obj.secret)

    def validate_target_folders(self, value):
        return _validate_accessible_folders(self.context.get("request"), value)


def _validate_accessible_folders(request, value):
    if not request or not hasattr(request, "user"):
        raise serializers.ValidationError("Request context with user is required.")
    user = getattr(request, "user")
    viewable_folders_ids = RoleAssignment.get_viewable_object_ids(user, Folder)

    if not all(folder.id in viewable_folders_ids for folder in value):
        raise serializers.ValidationError(
            "One or more target folders are not accessible by the user."
        )
    return value


class AuditSinkSerializer(BaseModelSerializer):
    """
    Serializer for audit-sink endpoints (kind=AUDIT_SINK): admin-managed
    destinations that forward the audit log to an external SIEM. No HMAC secret
    or per-event subscription — the whole audit feed is forwarded in the chosen
    body_format, authenticated via static headers or OAuth2 client credentials.
    """

    target_folders = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Folder.objects.all(), required=False
    )

    # Auth secrets are write-only: never round-trip them to the client. headers
    # may carry a SIEM token; the Kafka SASL password lives inside kafka_config
    # and the OAuth client secret inside oauth_config.
    headers = serializers.JSONField(write_only=True, required=False)
    has_headers = serializers.SerializerMethodField()
    has_sasl_password = serializers.SerializerMethodField()
    has_client_secret = serializers.SerializerMethodField()

    class Meta:
        model = WebhookEndpoint
        fields = [
            "id",
            "name",
            "description",
            "url",
            "transport",
            "body_format",
            "body_wrapper",
            "headers",
            "has_headers",
            "auth_type",
            "oauth_config",
            "has_client_secret",
            "kafka_config",
            "has_sasl_password",
            "is_active",
            "target_folders",
            "folder",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def get_has_headers(self, obj):
        return bool(obj.headers)

    def get_has_sasl_password(self, obj):
        return bool(
            (obj.kafka_config or {}).get("config", {}).get("sasl_plain_password")
        )

    def get_has_client_secret(self, obj):
        return bool((obj.oauth_config or {}).get("client_secret"))

    def to_representation(self, instance):
        # Strip the Kafka SASL password from the rendered kafka_config; the rest
        # (servers, topic, mechanism, username) is needed for edit prefill.
        data = super().to_representation(instance)
        cfg = data.get("kafka_config") or {}
        inner = cfg.get("config") or {}
        if inner.get("sasl_plain_password"):
            inner = {k: v for k, v in inner.items() if k != "sasl_plain_password"}
            data["kafka_config"] = {**cfg, "config": inner}
        # Same for the OAuth client secret; token_url/client_id/scope are needed
        # for edit prefill.
        oauth = data.get("oauth_config") or {}
        if oauth.get("client_secret"):
            data["oauth_config"] = {
                k: v for k, v in oauth.items() if k != "client_secret"
            }
        return data

    def update(self, instance, validated_data):
        # oauth_config is sent whole like kafka_config; a blank client_secret
        # means "keep the stored one".
        new_oauth = validated_data.get("oauth_config")
        if new_oauth is not None and not new_oauth.get("client_secret"):
            old_secret = (instance.oauth_config or {}).get("client_secret")
            if old_secret:
                validated_data["oauth_config"] = {
                    **new_oauth,
                    "client_secret": old_secret,
                }

        # kafka_config is a single JSON field sent whole on update; if the client
        # omitted the password (kept blank), carry the stored one over.
        new_kafka = validated_data.get("kafka_config")
        if new_kafka is not None:
            inner = new_kafka.get("config") or {}
            if not inner.get("sasl_plain_password"):
                old_pw = (
                    (instance.kafka_config or {})
                    .get("config", {})
                    .get("sasl_plain_password")
                )
                if old_pw:
                    new_kafka["config"] = {**inner, "sasl_plain_password": old_pw}
                    validated_data["kafka_config"] = new_kafka
        return super().update(instance, validated_data)

    def validate_target_folders(self, value):
        return _validate_accessible_folders(self.context.get("request"), value)

    def validate_headers(self, value):
        # Sent verbatim as HTTP request headers, so only a flat string->string
        # map is valid; nested objects/arrays would break at send time.
        if not isinstance(value, dict):
            raise serializers.ValidationError("Headers must be a JSON object.")
        if any(not isinstance(v, str) for v in value.values()):
            raise serializers.ValidationError("Header values must be strings.")
        return value

    def validate_oauth_config(self, value):
        # Everything here becomes a form field on the token request, except
        # extra_params which is itself a flat string map merged into it.
        if not isinstance(value, dict):
            raise serializers.ValidationError("oauth_config must be a JSON object.")
        extra = value.get("extra_params", {})
        if not isinstance(extra, dict) or any(
            not isinstance(v, str) for v in extra.values()
        ):
            raise serializers.ValidationError(
                "extra_params must be an object of string values."
            )
        if any(not isinstance(v, str) for k, v in value.items() if k != "extra_params"):
            raise serializers.ValidationError("oauth_config values must be strings.")
        return value

    def validate(self, data):
        data = super().validate(data)
        transport = data.get("transport") or getattr(self.instance, "transport", None)
        auth_type = data.get("auth_type") or getattr(self.instance, "auth_type", None)
        if (
            transport == WebhookEndpoint.Transport.HTTP
            and auth_type == WebhookEndpoint.AuthType.OAUTH2_CC
        ):
            cfg = (
                data.get("oauth_config")
                or getattr(self.instance, "oauth_config", None)
                or {}
            )
            missing = [f for f in ("token_url", "client_id") if not cfg.get(f)]
            # A blank secret is legitimate on update: it means "keep the stored one".
            if not cfg.get("client_secret") and not (
                self.instance
                and (self.instance.oauth_config or {}).get("client_secret")
            ):
                missing.append("client_secret")
            if missing:
                raise serializers.ValidationError(
                    {
                        "oauth_config": f"{', '.join(missing)} "
                        "required for OAuth2 client credentials."
                    }
                )
        if transport == WebhookEndpoint.Transport.KAFKA:
            cfg = (
                data.get("kafka_config")
                or getattr(self.instance, "kafka_config", None)
                or {}
            )
            if not cfg.get("bootstrap_servers") or not cfg.get("topic"):
                raise serializers.ValidationError(
                    {
                        "kafka_config": "bootstrap_servers and topic are required "
                        "for Kafka transport."
                    }
                )
        return data
