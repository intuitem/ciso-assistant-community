# Deploy CISO Assistant on AWS (single EC2 instance)

`deploy.sh` runs this repository on one Ubuntu 24.04 EC2 instance using Docker Compose:

- Builds the images from this repo (`MODE=build`, default) or pulls upstream images (`MODE=prebuilt`, faster).
- Caddy serves HTTPS on 443: a self-signed cert on the Elastic IP, or Let's Encrypt when `DOMAIN` is set.
- Ports 80/443 open only to `ALLOWED_CIDR` (defaults to your current IP). No SSH; shell access is via SSM Session Manager.
- The admin password is generated into SSM Parameter Store (`/<NAME>/admin-password`).

## Usage

Requires the AWS CLI v2 with credentials that can manage EC2, IAM and SSM.

```bash
ADMIN_EMAIL=you@example.com AWS_REGION=eu-west-1 ./deploy/aws/deploy.sh
```

Optional variables: `NAME` (default `ciso-assistant`), `INSTANCE_TYPE` (`t3.large`), `VOLUME_GB` (`40`),
`MODE`, `DOMAIN`, `ALLOWED_CIDR`, `REPO_URL`, `REPO_REF` (`main`).

On the instance, `sudo ciso-compose logs -f backend` (or `ps`, `restart`, ...) wraps the right compose files.

To update to the latest code: `cd /opt/ciso-assistant && sudo git pull && sudo ciso-compose up -d --build`.

## Teardown

```bash
AWS_REGION=eu-west-1 ./deploy/aws/destroy.sh
```

This terminates the instance (and its data), releases the Elastic IP and deletes the security group, IAM role and password parameter.
