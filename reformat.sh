cd frontend
pnpm exec prettier . --write
pnpm exec prettier ../enterprise/frontend/src/ --write
cd ../backend
ruff format .
cd ../enterprise/backend
ruff format .
