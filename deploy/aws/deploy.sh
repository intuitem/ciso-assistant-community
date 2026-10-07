#!/bin/bash
# Deploy CISO Assistant to a single EC2 instance in your AWS account.
# Usage: ./deploy.sh   (configure with the environment variables below)
set -euo pipefail

NAME="${NAME:-ciso-assistant}"
REGION="${AWS_REGION:-${AWS_DEFAULT_REGION:-us-east-1}}"
INSTANCE_TYPE="${INSTANCE_TYPE:-t3.large}"
VOLUME_GB="${VOLUME_GB:-40}"
REPO_URL="${REPO_URL:-https://github.com/ksoleski/cac.git}"
REPO_REF="${REPO_REF:-main}"
MODE="${MODE:-build}"                 # build | prebuilt
DOMAIN="${DOMAIN:-}"                  # optional DNS name already pointing at the instance's Elastic IP
ADMIN_EMAIL="${ADMIN_EMAIL:?set ADMIN_EMAIL to the email for the first admin account}"
# Who may reach the app; defaults to your current public IP only.
ALLOWED_CIDR="${ALLOWED_CIDR:-$(curl -fsS https://checkip.amazonaws.com | tr -d '\n')/32}"

HERE="$(cd "$(dirname "$0")" && pwd)"
aws() { command aws --region "$REGION" "$@"; }
TAG_SPEC="Key=Project,Value=${NAME}"

echo "Account: $(aws sts get-caller-identity --query Account --output text), region: $REGION"

# Admin password lives in SSM Parameter Store; the instance reads it at boot.
PASSWORD_PARAM="/${NAME}/admin-password"
if ! aws ssm get-parameter --name "$PASSWORD_PARAM" >/dev/null 2>&1; then
  aws ssm put-parameter --name "$PASSWORD_PARAM" --type SecureString \
    --value "$(openssl rand -base64 18 | tr -d '/+=')" --tags "$TAG_SPEC" >/dev/null
fi

# IAM role: Session Manager access + read of the password parameter.
ROLE="${NAME}-ec2"
if ! aws iam get-role --role-name "$ROLE" >/dev/null 2>&1; then
  aws iam create-role --role-name "$ROLE" --tags "$TAG_SPEC" --assume-role-policy-document '{
    "Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"ec2.amazonaws.com"},"Action":"sts:AssumeRole"}]}' >/dev/null
  aws iam attach-role-policy --role-name "$ROLE" --policy-arn arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore
  ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
  aws iam put-role-policy --role-name "$ROLE" --policy-name read-admin-password --policy-document "{
    \"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Action\":\"ssm:GetParameter\",
    \"Resource\":\"arn:aws:ssm:${REGION}:${ACCOUNT}:parameter${PASSWORD_PARAM}\"}]}"
  aws iam create-instance-profile --instance-profile-name "$ROLE" >/dev/null
  aws iam add-role-to-instance-profile --instance-profile-name "$ROLE" --role-name "$ROLE"
  sleep 15  # instance profiles take a moment to propagate
fi

# Security group in the default VPC: HTTP/HTTPS from ALLOWED_CIDR only, no SSH (use Session Manager).
VPC_ID=$(aws ec2 describe-vpcs --filters Name=isDefault,Values=true --query 'Vpcs[0].VpcId' --output text)
SG_ID=$(aws ec2 describe-security-groups --filters Name=group-name,Values="$NAME" Name=vpc-id,Values="$VPC_ID" \
  --query 'SecurityGroups[0].GroupId' --output text)
if [ "$SG_ID" = "None" ]; then
  SG_ID=$(aws ec2 create-security-group --group-name "$NAME" --description "CISO Assistant web access" \
    --vpc-id "$VPC_ID" --query GroupId --output text)
  for port in 80 443; do
    aws ec2 authorize-security-group-ingress --group-id "$SG_ID" --protocol tcp --port $port --cidr "$ALLOWED_CIDR" >/dev/null
  done
fi

AMI_ID=$(aws ssm get-parameter --name /aws/service/canonical/ubuntu/server/24.04/stable/current/amd64/hvm/ebs-gp3/ami-id \
  --query Parameter.Value --output text)

USER_DATA=$(sed -e "s|__REPO_URL__|${REPO_URL}|" -e "s|__REPO_REF__|${REPO_REF}|" -e "s|__MODE__|${MODE}|" \
  -e "s|__DOMAIN__|${DOMAIN}|" -e "s|__ADMIN_EMAIL__|${ADMIN_EMAIL}|" \
  -e "s|__PASSWORD_PARAM__|${PASSWORD_PARAM}|" -e "s|__REGION__|${REGION}|" "$HERE/user-data.sh")

INSTANCE_ID=$(aws ec2 run-instances --image-id "$AMI_ID" --instance-type "$INSTANCE_TYPE" \
  --security-group-ids "$SG_ID" --iam-instance-profile Name="$ROLE" \
  --metadata-options HttpTokens=required \
  --block-device-mappings "DeviceName=/dev/sda1,Ebs={VolumeSize=${VOLUME_GB},VolumeType=gp3,Encrypted=true}" \
  --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=${NAME}},{Key=Project,Value=${NAME}}]" \
  --user-data "$USER_DATA" --query 'Instances[0].InstanceId' --output text)
echo "Launched $INSTANCE_ID, waiting for it to run..."
aws ec2 wait instance-running --instance-ids "$INSTANCE_ID"

# Elastic IP keeps the address stable across stop/start.
ALLOC_ID=$(aws ec2 allocate-address --domain vpc \
  --tag-specifications "ResourceType=elastic-ip,Tags=[{Key=Name,Value=${NAME}}]" --query AllocationId --output text)
aws ec2 associate-address --instance-id "$INSTANCE_ID" --allocation-id "$ALLOC_ID" >/dev/null
PUBLIC_IP=$(aws ec2 describe-addresses --allocation-ids "$ALLOC_ID" --query 'Addresses[0].PublicIp' --output text)

cat <<MSG

Instance:   $INSTANCE_ID ($INSTANCE_TYPE, $REGION)
URL:        https://${DOMAIN:-$PUBLIC_IP}   (ready in ~5 min with MODE=prebuilt, ~20-30 min with MODE=build)
Admin:      $ADMIN_EMAIL
Password:   aws ssm get-parameter --region $REGION --name $PASSWORD_PARAM --with-decryption --query Parameter.Value --output text
Progress:   aws ssm start-session --region $REGION --target $INSTANCE_ID   then: sudo tail -f /var/log/ciso-assistant-bootstrap.log
MSG
