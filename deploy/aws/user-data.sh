#!/bin/bash
# EC2 bootstrap for CISO Assistant. Placeholders (__X__) are filled in by deploy.sh.
set -euxo pipefail
exec > >(tee /var/log/ciso-assistant-bootstrap.log) 2>&1

REPO_URL="__REPO_URL__"
REPO_REF="__REPO_REF__"
MODE="__MODE__"            # build = build images from this repo, prebuilt = pull upstream images
DOMAIN="__DOMAIN__"        # optional; empty = use the instance public IP with a self-signed cert
ADMIN_EMAIL="__ADMIN_EMAIL__"
PASSWORD_PARAM="__PASSWORD_PARAM__"
REGION="__REGION__"

# Swap helps the frontend build on smaller instances.
if [ ! -f /swapfile ]; then
  fallocate -l 4G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile
  echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y ca-certificates curl git
curl -fsSL https://get.docker.com | sh
snap install aws-cli --classic

if [ -n "$DOMAIN" ]; then
  HOST="$DOMAIN"
  TLS_LINE=""                 # Caddy obtains a Let's Encrypt cert automatically
else
  TOKEN=$(curl -sX PUT http://169.254.169.254/latest/api/token -H 'X-aws-ec2-metadata-token-ttl-seconds: 300')
  HOST=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/public-ipv4)
  TLS_LINE="tls internal"     # self-signed; public CAs won't issue for a bare EC2 address
fi
URL="https://${HOST}"

ADMIN_PASSWORD=$(/snap/bin/aws ssm get-parameter --region "$REGION" --name "$PASSWORD_PARAM" \
  --with-decryption --query Parameter.Value --output text)

APP_DIR=/opt/ciso-assistant
if [ ! -d "$APP_DIR/.git" ]; then
  git clone --depth 1 --branch "$REPO_REF" "$REPO_URL" "$APP_DIR"
fi
cd "$APP_DIR"
mkdir -p db/caddy
chown -R 1001:1001 db

if [ "$MODE" = "build" ]; then
  BASE=docker-compose-build.yml
else
  BASE=docker-compose.yml
fi

cat > docker-compose.aws.yml <<YAML
services:
  backend:
    environment:
      - ALLOWED_HOSTS=backend,localhost,${HOST}
      - CISO_ASSISTANT_URL=${URL}
      - DJANGO_DEBUG=False
      - DJANGO_SUPERUSER_EMAIL=${ADMIN_EMAIL}
      - DJANGO_SUPERUSER_PASSWORD=${ADMIN_PASSWORD}
  huey:
    environment:
      - ALLOWED_HOSTS=backend,localhost,${HOST}
      - CISO_ASSISTANT_URL=${URL}
  frontend:
    environment:
      - PUBLIC_BACKEND_API_EXPOSED_URL=${URL}/api
  caddy:
    environment:
      - CISO_ASSISTANT_URL=${URL}
    ports: !override
      - "80:80"
      - "443:443"
    command: |
      sh -c 'echo \$\$CISO_ASSISTANT_URL "{
      reverse_proxy /api/* backend:8000
      reverse_proxy /mcp* mcp:8001
      reverse_proxy /* frontend:3000
      ${TLS_LINE}
      }" > Caddyfile && caddy run'
YAML
chmod 600 docker-compose.aws.yml

COMPOSE="docker compose -f $BASE -f docker-compose.aws.yml"
if [ "$MODE" = "build" ]; then
  $COMPOSE build
else
  $COMPOSE pull
fi
$COMPOSE up -d

# Remember the compose command for later operations (updates, logs).
echo "cd $APP_DIR && $COMPOSE \"\$@\"" > /usr/local/bin/ciso-compose
chmod +x /usr/local/bin/ciso-compose

echo "CISO Assistant bootstrap finished: ${URL}"
