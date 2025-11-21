set -e

CERT_PATH="${CUSTOM_CA_CERT_PATH:-}"

echo "[init-cert] Starting container initialization..."

if [ -n "$CERT_PATH" ] && [ -f "$CERT_PATH" ]; then
  echo "[init-cert] Found certificate at: $CERT_PATH"
  update-ca-certificates
else
  echo "[init-cert] No custom CA certificate found or CUSTOM_CA_CERT_PATH not set."
fi

exec "$@"
