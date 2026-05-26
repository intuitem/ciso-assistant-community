cd frontend
echo "Formatting frontend..."
pnpm exec prettier . --write

echo ""
echo "Formatting enterprise frontend..."
pnpm exec prettier ../enterprise/frontend/src/ --write

echo ""
echo "Formatting backend..."
cd ../backend
ruff format .

echo ""
echo "Formatting enterprise backend..."
cd ../enterprise/backend
ruff format .
