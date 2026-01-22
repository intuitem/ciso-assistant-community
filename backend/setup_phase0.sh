#!/bin/bash
# Phase 0 Setup Script
# Sets up development environment for DDD migration

set -e

echo "🚀 Setting up Phase 0 DDD Infrastructure..."

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if Poetry is installed
if ! command -v poetry &> /dev/null; then
    echo -e "${RED}❌ Poetry is not installed. Please install Poetry first.${NC}"
    echo "Visit: https://python-poetry.org/docs/#installation"
    exit 1
fi

echo -e "${GREEN}✅ Poetry found${NC}"

# Install dependencies
echo -e "${YELLOW}📦 Installing dependencies...${NC}"
poetry install --no-interaction

# Check if PostgreSQL is running
if ! command -v psql &> /dev/null; then
    echo -e "${YELLOW}⚠️  PostgreSQL client not found. Skipping database checks.${NC}"
else
    echo -e "${GREEN}✅ PostgreSQL client found${NC}"
fi

# Run migrations
echo -e "${YELLOW}🗄️  Running migrations...${NC}"
poetry run python manage.py migrate
poetry run python manage.py migrate core.domain

# Run DDD tests
echo -e "${YELLOW}🧪 Running DDD infrastructure tests...${NC}"
poetry run pytest core/domain/tests/ -c pytest_ddd.ini -v || {
    echo -e "${RED}❌ Tests failed. Please fix issues before proceeding.${NC}"
    exit 1
}

# Check test coverage
echo -e "${YELLOW}📊 Checking test coverage...${NC}"
coverage_output=$(poetry run pytest core/domain/tests/ -c pytest_ddd.ini --cov=core.domain --cov-report=term-missing 2>&1)
echo "$coverage_output"

# Verify EventStore table exists
echo -e "${YELLOW}🔍 Verifying EventStore table...${NC}"
poetry run python manage.py shell << EOF
from core.domain.events import EventStore
count = EventStore.objects.count()
print(f"✅ EventStore table exists. Current event count: {count}")
EOF

# Create example aggregate (optional)
read -p "Create example aggregate migration? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}📝 Creating example aggregate migration...${NC}"
    poetry run python manage.py makemigrations core.domain
fi

echo -e "${GREEN}✅ Phase 0 setup complete!${NC}"
echo ""
echo "Next steps:"
echo "1. Review core/domain/README.md for usage examples"
echo "2. Run 'make test-ddd' to run DDD tests"
echo "3. Check PHASE_0_COMPLETION_CHECKLIST.md for verification"
echo ""
echo "Ready to proceed with Phase 1! 🎉"

