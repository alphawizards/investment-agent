#!/bin/bash
# Generate self-signed certificates for local HTTPS development
# For production, use Let's Encrypt with Traefik ACME

set -e

CERT_DIR="./traefik/certs"
mkdir -p "$CERT_DIR"

# Generate private key
openssl genrsa -out "$CERT_DIR/key.pem" 2048

# Generate self-signed certificate
openssl req -new -x509 \
    -key "$CERT_DIR/key.pem" \
    -out "$CERT_DIR/cert.pem" \
    -days 365 \
    -subj "/C=AU/ST=State/L=City/O=QuantDash/CN=localhost" \
    -addext "subjectAltName=DNS:localhost,DNS:*.localhost,IP:127.0.0.1"

echo "✅ Self-signed certificates generated in $CERT_DIR"
echo "   - cert.pem: SSL certificate"
echo "   - key.pem: Private key"
echo ""
echo "⚠️  For production, configure Let's Encrypt in traefik.yml"
