cd frontend
echo "Formatting frontend..."
pnpm exec prettier . --write

echo ""
echo "Formatting enterprise frontend..."
pnpm exec prettier ../enterprise/frontend/src/ --write

# Pin ruff to the version enforced by CI (.github/workflows/backend-linters.yaml)
# and the pre-commit hook (.pre-commit-config.yaml). Using uvx keeps this aligned
# regardless of the globally installed ruff version.
RUFF="uvx ruff@0.15.17"

echo ""
echo "Formatting backend..."
cd ../backend
$RUFF format .

echo ""
echo "Formatting enterprise backend..."
cd ../enterprise/backend
$RUFF format .
