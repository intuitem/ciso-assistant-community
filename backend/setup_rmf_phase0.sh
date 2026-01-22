#!/bin/bash

# Phase 0 Setup Script for RMF Operations Bounded Context
# This script sets up the initial infrastructure for RMF integration

set -e  # Exit on error

echo "=========================================="
echo "RMF Operations Phase 0 Setup"
echo "=========================================="
echo ""

# Check if we're in the backend directory
if [ ! -f "manage.py" ]; then
    echo "Error: This script must be run from the backend directory"
    echo "Usage: cd backend && bash setup_rmf_phase0.sh"
    exit 1
fi

echo "Step 1: Installing dependencies..."
poetry install --no-root

echo ""
echo "Step 2: Verifying app registration..."
if grep -q "core.bounded_contexts.rmf_operations" ciso_assistant/settings.py; then
    echo "✅ RMF Operations app is registered in settings.py"
else
    echo "❌ Error: RMF Operations app not found in settings.py"
    exit 1
fi

echo ""
echo "Step 3: Verifying URL routing..."
if grep -q "rmf/" core/urls.py; then
    echo "✅ RMF URL routing is configured"
else
    echo "❌ Error: RMF URL routing not found in core/urls.py"
    exit 1
fi

echo ""
echo "Step 4: Verifying directory structure..."
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

for dir in "${REQUIRED_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        echo "✅ $dir exists"
    else
        echo "❌ Error: $dir does not exist"
        exit 1
    fi
done

echo ""
echo "Step 5: Verifying required files..."
REQUIRED_FILES=(
    "core/bounded_contexts/rmf_operations/__init__.py"
    "core/bounded_contexts/rmf_operations/apps.py"
    "core/bounded_contexts/rmf_operations/domain_events.py"
    "core/bounded_contexts/rmf_operations/urls.py"
    "core/bounded_contexts/rmf_operations/README.md"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "✅ $file exists"
    else
        echo "❌ Error: $file does not exist"
        exit 1
    fi
done

echo ""
echo "Step 6: Checking for lxml dependency..."
if grep -q "lxml" pyproject.toml; then
    echo "✅ lxml dependency is in pyproject.toml"
else
    echo "❌ Error: lxml dependency not found in pyproject.toml"
    exit 1
fi

echo ""
echo "Step 7: Testing Django app loading..."
if poetry run python manage.py check --deploy 2>&1 | grep -q "System check identified no issues"; then
    echo "✅ Django app loads successfully"
else
    echo "⚠️  Warning: Django check found issues (this may be expected in Phase 0)"
    poetry run python manage.py check 2>&1 | head -20
fi

echo ""
echo "=========================================="
echo "Phase 0 Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Review the RMF Integration Plan: CISO_ASSISTANT_RMF_INTEGRATION_PLAN.md"
echo "2. Begin Phase 1: Create aggregates and implement CKL parsing"
echo "3. Run tests: poetry run pytest core/bounded_contexts/rmf_operations/tests/ -v"
echo ""
echo "For more information, see:"
echo "- core/bounded_contexts/rmf_operations/README.md"
echo "- CISO_ASSISTANT_RMF_INTEGRATION_PLAN.md"
echo ""

