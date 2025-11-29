#!/bin/bash
set -euo pipefail

# CISO Assistant RPM Builder - Air-Gapped Edition
# This script builds a fully self-contained RPM with bundled Python and Node.js

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BUILD_DIR="${SCRIPT_DIR}/BUILD"
SOURCES_DIR="${SCRIPT_DIR}/SOURCES"

# Version info
VERSION="${VERSION:-$(git describe --tags --always 2>/dev/null || echo 'dev')}"
ARCH="x86_64"

# Runtime versions
PYTHON_VERSION="3.12.7"
NODE_VERSION="22.11.0"

echo "======================================"
echo "  CISO Assistant RPM Builder"
echo "======================================"
echo "Version: $VERSION"
echo "Architecture: $ARCH"
echo "Python: $PYTHON_VERSION"
echo "Node.js: $NODE_VERSION"
echo "======================================"
echo ""

# Clean previous builds
echo "[1/8] Cleaning previous build artifacts..."
rm -rf "$BUILD_DIR" "$SOURCES_DIR"
mkdir -p "$BUILD_DIR" "$SOURCES_DIR"/{backend,frontend,venv,node,systemd,templates}

# Download and extract Python
echo "[2/8] Downloading and extracting Python $PYTHON_VERSION..."
PYTHON_URL="https://www.python.org/ftp/python/${PYTHON_VERSION}/Python-${PYTHON_VERSION}.tar.xz"
PYTHON_BUILD_DIR="$BUILD_DIR/python-build"
mkdir -p "$PYTHON_BUILD_DIR"

if [ ! -f "$BUILD_DIR/Python-${PYTHON_VERSION}.tar.xz" ]; then
    curl -L "$PYTHON_URL" -o "$BUILD_DIR/Python-${PYTHON_VERSION}.tar.xz"
fi

tar -xf "$BUILD_DIR/Python-${PYTHON_VERSION}.tar.xz" -C "$PYTHON_BUILD_DIR" --strip-components=1

# Build Python from source
echo "[2/8] Building Python $PYTHON_VERSION (this may take a while)..."
cd "$PYTHON_BUILD_DIR"
./configure --prefix="$SOURCES_DIR/venv" --enable-optimizations --with-ensurepip=install
make -j$(nproc)
make install

# Clean up Python build
cd "$SCRIPT_DIR"
rm -rf "$PYTHON_BUILD_DIR"

# Create Python virtualenv with backend dependencies
echo "[3/8] Installing Python dependencies..."

# Install poetry into the bundled Python
"$SOURCES_DIR/venv/bin/pip3" install --no-cache-dir --upgrade pip poetry

# Configure poetry to use the bundled venv
"$SOURCES_DIR/venv/bin/poetry" config virtualenvs.create false

# Install dependencies using poetry
cd "$PROJECT_ROOT/backend"
"$SOURCES_DIR/venv/bin/poetry" install --no-root --only main

# Install gunicorn
"$SOURCES_DIR/venv/bin/pip3" install gunicorn

# Copy backend application code
echo "[4/8] Copying backend application..."
rsync -a \
    --exclude='*.pyc' \
    --exclude='__pycache__' \
    --exclude='*.sqlite3' \
    --exclude='db/' \
    --exclude='media/' \
    --exclude='.git' \
    --exclude='venv' \
    "$PROJECT_ROOT/backend/" \
    "$SOURCES_DIR/backend/"

# Download and extract Node.js
echo "[5/8] Downloading Node.js $NODE_VERSION..."
NODE_URL="https://nodejs.org/dist/v${NODE_VERSION}/node-v${NODE_VERSION}-linux-${ARCH}.tar.xz"

if [ ! -f "$BUILD_DIR/node-v${NODE_VERSION}-linux-${ARCH}.tar.xz" ]; then
    curl -L "$NODE_URL" -o "$BUILD_DIR/node-v${NODE_VERSION}-linux-${ARCH}.tar.xz"
fi

tar -xf "$BUILD_DIR/node-v${NODE_VERSION}-linux-${ARCH}.tar.xz" -C "$SOURCES_DIR/node" --strip-components=1

# Build frontend with bundled Node.js
echo "[6/8] Building frontend application..."
cd "$PROJECT_ROOT/frontend"

# Use the bundled Node.js for building
export PATH="$SOURCES_DIR/node/bin:$PATH"

# Install dependencies
pnpm install --frozen-lockfile

# Build for production
pnpm run build

# Copy built frontend and node_modules
echo "[6/8] Copying frontend build..."
mkdir -p "$SOURCES_DIR/frontend/build"
cp -r build/* "$SOURCES_DIR/frontend/build/"
cp package.json "$SOURCES_DIR/frontend/"

# Copy only production node_modules
pnpm install --prod --frozen-lockfile
cp -r node_modules "$SOURCES_DIR/frontend/"

# Copy systemd and template files
echo "[7/8] Copying configuration files..."
cp "$SCRIPT_DIR/systemd/"*.service "$SOURCES_DIR/systemd/"
cp "$SCRIPT_DIR/templates/"*.env "$SOURCES_DIR/templates/"

# Build RPM
echo "[8/8] Building RPM package..."
rpmbuild -bb \
    --define "_topdir $SCRIPT_DIR" \
    --define "_sourcedir $SOURCES_DIR" \
    --define "_version $VERSION" \
    "$SCRIPT_DIR/SPECS/ciso-assistant.spec"

# Find the built RPM
BUILT_RPM=$(find "$SCRIPT_DIR/RPMS" -name "*.rpm" -type f | head -n 1)

if [ -n "$BUILT_RPM" ]; then
    RPM_SIZE=$(du -h "$BUILT_RPM" | cut -f1)
    echo ""
    echo "======================================"
    echo " SUCCESS! RPM built successfully"
    echo "======================================"
    echo "Package: $BUILT_RPM"
    echo "Size: $RPM_SIZE"
    echo ""
    echo "To install:"
    echo "  sudo rpm -ivh $BUILT_RPM"
    echo ""
    echo "To transfer to air-gapped system:"
    echo "  scp $BUILT_RPM user@target-host:/tmp/"
    echo ""
else
    echo "ERROR: RPM build failed!"
    exit 1
fi
