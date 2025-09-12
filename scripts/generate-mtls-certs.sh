#!/bin/bash
# GameForge AI mTLS Certificate Generation Script
set -e

CERTS_DIR="certs"
mkdir -p $CERTS_DIR

echo "=== Generating mTLS Certificates for GameForge AI ==="

# Generate CA private key
openssl genrsa -out $CERTS_DIR/ca-key.pem 4096

# Generate CA certificate
openssl req -new -x509 -days 3650 -key $CERTS_DIR/ca-key.pem -out $CERTS_DIR/ca-cert.pem -subj "/C=US/ST=CA/L=San Francisco/O=GameForge AI/OU=Security/CN=GameForge CA"

# Generate server private key
openssl genrsa -out $CERTS_DIR/server-key.pem 4096

# Generate server certificate signing request
openssl req -new -key $CERTS_DIR/server-key.pem -out $CERTS_DIR/server.csr -subj "/C=US/ST=CA/L=San Francisco/O=GameForge AI/OU=Security/CN=gameforge.local"

# Create server certificate extensions
cat > $CERTS_DIR/server-ext.conf << EOF
authorityKeyIdentifier=keyid,issuer
basicConstraints=CA:FALSE
keyUsage = digitalSignature, nonRepudiation, keyEncipherment, dataEncipherment
subjectAltName = @alt_names

[alt_names]
DNS.1 = gameforge.local
DNS.2 = localhost
DNS.3 = nginx
DNS.4 = gameforge-app
DNS.5 = gpu-inference
IP.1 = 127.0.0.1
IP.2 = 172.18.0.1
EOF

# Generate server certificate signed by CA
openssl x509 -req -days 365 -in $CERTS_DIR/server.csr -CA $CERTS_DIR/ca-cert.pem -CAkey $CERTS_DIR/ca-key.pem -CAcreateserial -out $CERTS_DIR/server-cert.pem -extensions v3_req -extfile $CERTS_DIR/server-ext.conf

# Generate client private key
openssl genrsa -out $CERTS_DIR/client-key.pem 4096

# Generate client certificate signing request
openssl req -new -key $CERTS_DIR/client-key.pem -out $CERTS_DIR/client.csr -subj "/C=US/ST=CA/L=San Francisco/O=GameForge AI/OU=Security/CN=gameforge-client"

# Generate client certificate signed by CA
openssl x509 -req -days 365 -in $CERTS_DIR/client.csr -CA $CERTS_DIR/ca-cert.pem -CAkey $CERTS_DIR/ca-key.pem -CAcreateserial -out $CERTS_DIR/client-cert.pem

# Generate DH parameters for enhanced security
openssl dhparam -out $CERTS_DIR/dhparam.pem 2048

# Set proper permissions
chmod 600 $CERTS_DIR/*-key.pem
chmod 644 $CERTS_DIR/*-cert.pem $CERTS_DIR/ca-cert.pem $CERTS_DIR/dhparam.pem

echo "Certificates generated successfully:"
echo "  CA Certificate: $CERTS_DIR/ca-cert.pem"
echo "  Server Certificate: $CERTS_DIR/server-cert.pem"
echo "  Client Certificate: $CERTS_DIR/client-cert.pem"

# Verify certificates
echo "Verifying certificates..."
openssl verify -CAfile $CERTS_DIR/ca-cert.pem $CERTS_DIR/server-cert.pem
openssl verify -CAfile $CERTS_DIR/ca-cert.pem $CERTS_DIR/client-cert.pem

echo "mTLS certificates ready for production deployment"
