#!/bin/bash
 
set -e  # Exit immediately if any command fails
 
# === CONFIGURATION ===
DB_NAME="forkedd_ciso_assistant_enterprise"
DB_USER="raqib_final_user"
DB_PASSWORD="raqib_final_pass"
DB_HOST="localhost"
DB_PORT="5432"
 
# Optional superuser setup
SUPERUSER_EMAIL="admin@gmail.com"
SUPERUSER_PASSWORD="Admin@123456"
 
# === 1. Delete all migration files except __init__.py ===
echo "🔁 Removing old migration files..."
find . -path "*/migrations/*.py" -not -name "__init__.py" -delete
find . ../../backend -path "*/migrations/*.py" -not -name "__init__.py" -delete
find . ../../backend -path "*/migrations/*.pyc" -delete
find . -path "*/migrations/*.pyc" -delete
 
echo "🔒 Terminating active connections to $DB_NAME..."
sudo -u postgres psql -c "
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = '$DB_NAME'
  AND pid <> pg_backend_pid();
"
 
# === 2. Drop and recreate PostgreSQL database ===
echo "🧨 Dropping and recreating database..."
 
# Drop active connections
echo "🔒 Terminating active connections to $DB_NAME..."
sudo -u postgres psql -c "
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = '$DB_NAME'
  AND pid <> pg_backend_pid();
"
 
# Drop DB if exists
sudo -u postgres psql -c "DROP DATABASE IF EXISTS $DB_NAME;"
 
# Reassign and drop user-owned privileges
echo "🚫 Revoking privileges from $DB_USER..."
sudo -u postgres psql -c "REASSIGN OWNED BY $DB_USER TO postgres;"
sudo -u postgres psql -c "DROP OWNED BY $DB_USER;"
 
# Drop user if exists
# sudo -u postgres psql -c "DROP USER IF EXISTS $DB_USER;"
 
# Recreate user and DB
# sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';"
sudo -u postgres psql -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;"
sudo -u postgres psql -c "ALTER DATABASE $DB_NAME SET client_encoding TO 'UTF8';"
sudo -u postgres psql -c "ALTER DATABASE $DB_NAME SET default_transaction_isolation TO 'read committed';"
sudo -u postgres psql -c "ALTER DATABASE $DB_NAME SET timezone TO 'UTC';"
 
 
# === 3. Recreate migrations ===
echo "📦 Creating fresh migrations..."
poetry run ./manage.sh makemigrations
 
# === 4. Apply migrations ===
echo "⚙️ Applying migrations..."
poetry run ./manage.sh migrate
 
 
echo "✅ Reset complete. Fresh database, migrations, and superuser are ready."