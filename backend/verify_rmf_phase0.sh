#!/bin/bash

# Phase 0 Verification Script for RMF Operations Bounded Context
# This script verifies the setup without requiring Poetry installation

set -e  # Exit on error

echo "=========================================="
echo "RMF Operations Phase 0 Verification"
echo "=========================================="
echo ""

# Check if we're in the backend directory
if [ ! -f "manage.py" ]; then
    echo "Error: This script must be run from the backend directory"
    echo "Usage: cd backend && bash verify_rmf_phase0.sh"
    exit 1
fi

echo "Step 1: Verifying app registration..."
if grep -q "core.bounded_contexts.rmf_operations" ciso_assistant/settings.py; then
    echo "✅ RMF Operations app is registered in settings.py"
else
    echo "❌ Error: RMF Operations app not found in settings.py"
    exit 1
fi

echo ""
echo "Step 2: Verifying URL routing..."
if grep -q "rmf/" core/urls.py; then
    echo "✅ RMF URL routing is configured"
else
    echo "❌ Error: RMF URL routing not found in core/urls.py"
    exit 1
fi

echo ""
echo "Step 3: Verifying directory structure..."
REQUIRED_DIRS=(
    "core/bounded_contexts/rmf_operations"
    "core/bounded_contexts/rmf_operations/aggregates"
    "core/bounded_contexts/rmf_operations/associations"
    "core/bounded_contexts/rmf_operations/supporting_entities"
    "core/bounded_contexts/rmf_operations/repositories"
    "core/bounded_contexts/rmf_operations/read_models"
    "core/bounded_contexts/rmf_operations/projections"
    "core/bounded_contexts/rmf_operations/value_objects"
    "core/bounded_contexts/rmf_operations/tests"
    "core/bounded_contexts/rmf_operations/migrations"
)

ALL_DIRS_EXIST=true
for dir in "${REQUIRED_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        echo "✅ $dir exists"
    else
        echo "❌ Error: $dir does not exist"
        ALL_DIRS_EXIST=false
    fi
done

if [ "$ALL_DIRS_EXIST" = false ]; then
    exit 1
fi

echo ""
echo "Step 4: Verifying required files..."
REQUIRED_FILES=(
    "core/bounded_contexts/rmf_operations/__init__.py"
    "core/bounded_contexts/rmf_operations/apps.py"
    "core/bounded_contexts/rmf_operations/domain_events.py"
    "core/bounded_contexts/rmf_operations/urls.py"
    "core/bounded_contexts/rmf_operations/README.md"
)

ALL_FILES_EXIST=true
for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "✅ $file exists"
    else
        echo "❌ Error: $file does not exist"
        ALL_FILES_EXIST=false
    fi
done

if [ "$ALL_FILES_EXIST" = false ]; then
    exit 1
fi

echo ""
echo "Step 5: Checking for lxml dependency..."
if grep -q "lxml" pyproject.toml; then
    echo "✅ lxml dependency is in pyproject.toml"
else
    echo "❌ Error: lxml dependency not found in pyproject.toml"
    exit 1
fi

echo ""
echo "Step 6: Verifying domain events..."
if grep -q "class SystemGroupCreated" core/bounded_contexts/rmf_operations/domain_events.py; then
    echo "✅ Domain events are defined"
else
    echo "❌ Error: Domain events not found"
    exit 1
fi

echo ""
echo "Step 7: Verifying apps.py configuration..."
if grep -q "RmfOperationsConfig" core/bounded_contexts/rmf_operations/apps.py; then
    echo "✅ App configuration is correct"
else
    echo "❌ Error: App configuration not found"
    exit 1
fi

echo ""
echo "=========================================="
echo "✅ Phase 0 Verification Complete!"
echo "=========================================="
echo ""
echo "All Phase 0 requirements are met:"
echo "  ✅ Directory structure created"
echo "  ✅ Core files in place"
echo "  ✅ App registered in Django"
echo "  ✅ URL routing configured"
echo "  ✅ Dependencies added"
echo "  ✅ Domain events defined"
echo ""
echo "Next steps:"
echo "1. Install dependencies: poetry install (or pip install lxml)"
echo "2. Review the RMF Integration Plan: CISO_ASSISTANT_RMF_INTEGRATION_PLAN.md"
echo "3. Begin Phase 1: Create aggregates and implement CKL parsing"
echo ""
echo "For more information, see:"
echo "- core/bounded_contexts/rmf_operations/README.md"
echo "- CISO_ASSISTANT_RMF_INTEGRATION_PLAN.md"
echo ""

