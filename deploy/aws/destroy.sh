#!/bin/bash
# Remove everything deploy.sh created. Deletes the instance and its data.
set -euo pipefail
NAME="${NAME:-ciso-assistant}"
REGION="${AWS_REGION:-${AWS_DEFAULT_REGION:-us-east-1}}"
aws() { command aws --region "$REGION" "$@"; }

IDS=$(aws ec2 describe-instances --filters Name=tag:Name,Values="$NAME" \
  Name=instance-state-name,Values=pending,running,stopping,stopped --query 'Reservations[].Instances[].InstanceId' --output text)
for ALLOC in $(aws ec2 describe-addresses --filters Name=tag:Name,Values="$NAME" --query 'Addresses[].AllocationId' --output text); do
  aws ec2 release-address --allocation-id "$ALLOC" 2>/dev/null || {
    aws ec2 disassociate-address --association-id "$(aws ec2 describe-addresses --allocation-ids "$ALLOC" --query 'Addresses[0].AssociationId' --output text)"
    aws ec2 release-address --allocation-id "$ALLOC"; }
done
if [ -n "$IDS" ]; then
  aws ec2 terminate-instances --instance-ids $IDS >/dev/null
  aws ec2 wait instance-terminated --instance-ids $IDS
fi
SG_ID=$(aws ec2 describe-security-groups --filters Name=group-name,Values="$NAME" --query 'SecurityGroups[0].GroupId' --output text)
[ "$SG_ID" != "None" ] && aws ec2 delete-security-group --group-id "$SG_ID"
ROLE="${NAME}-ec2"
if aws iam get-role --role-name "$ROLE" >/dev/null 2>&1; then
  aws iam remove-role-from-instance-profile --instance-profile-name "$ROLE" --role-name "$ROLE" || true
  aws iam delete-instance-profile --instance-profile-name "$ROLE" || true
  aws iam detach-role-policy --role-name "$ROLE" --policy-arn arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore
  aws iam delete-role-policy --role-name "$ROLE" --policy-name read-admin-password
  aws iam delete-role --role-name "$ROLE"
fi
aws ssm delete-parameter --name "/${NAME}/admin-password" 2>/dev/null || true
echo "Removed CISO Assistant deployment '$NAME' from $REGION."
