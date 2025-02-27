#!/bin/bash

# Create certs directory if it doesn't exist
mkdir -p certs

# Generate private key
openssl genrsa -out certs/key.pem 2048

# Generate Certificate Signing Request (CSR)
# This will prompt for some information - you can just hit enter for most fields
# but make sure to enter your domain name (e.g., localhost) for the Common Name
openssl req -new -key certs/key.pem -out certs/csr.pem

# Generate self-signed certificate
# Valid for 365 days
openssl x509 -req -days 365 -in certs/csr.pem -signkey certs/key.pem -out certs/cert.pem

# Remove CSR as it's no longer needed
rm certs/csr.pem

# Set correct permissions
chmod 600 certs/key.pem
chmod 644 certs/cert.pem

echo "Certificates generated in ./certs/"
echo "cert.pem - public certificate"
echo "key.pem  - private key"
