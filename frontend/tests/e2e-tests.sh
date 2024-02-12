#! /usr/bin/env bash
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DB_DIR=$APP_DIR/backend/db
DATABASE_BACKUP_NAME=ciso-assistant-backup.sqlite3

cleanup() {
    echo -e "\nCleaning up..."
    if [ -n $BACKEND_PID ] ; then
        kill $BACKEND_PID > /dev/null 2>&1
        echo "| backend server stopped"
    fi
    if [ -f $DB_DIR/$DATABASE_BACKUP_NAME ] ; then
        mv $DB_DIR/$DATABASE_BACKUP_NAME $DB_DIR/ciso-assistant.sqlite3
    else 
        rm $DB_DIR/ciso-assistant.sqlite3
    fi
    echo "| database restored"
    if [ -d $APP_DIR/frontend/tests/utils/.testhistory ] ; then
        rm -rf $APP_DIR/frontend/tests/utils/.testhistory
        echo "| test data history removed"
    fi
    trap - SIGINT SIGTERM EXIT
    echo "Cleanup done"
    exit 0
}

interrupt() {
    echo "Test interrupted"
    cleanup
}

trap cleanup SIGINT SIGTERM
trap interrupt EXIT

if [ -f $DB_DIR/ciso-assistant.sqlite3 ] ; then
    echo "an existing database is already created"
    echo "backup of the existing database..."

    mv $DB_DIR/ciso-assistant.sqlite3 $DB_DIR/$DATABASE_BACKUP_NAME
    echo "backup completed"
fi

echo "starting backend server..."
unset POSTGRES_NAME POSTGRES_USER POSTGRES_PASSWORD
export CISO_ASSISTANT_URL=http://localhost:4173
export ALLOWED_HOSTS=localhost
export DJANGO_DEBUG=True
export DJANGO_SUPERUSER_EMAIL=admin@tests.com
export DJANGO_SUPERUSER_PASSWORD=1234

cd $APP_DIR/backend/
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser --noinput
nohup python manage.py runserver 8080 > /dev/null 2>&1 &
BACKEND_PID=$!
echo "test backend server started on port 8080 (PID: $BACKEND_PID)"

echo "starting playwright tests"
export ORIGIN=http://localhost:4173
export PUBLIC_BACKEND_API_URL=http://localhost:8080/api

cd $APP_DIR/frontend/
npx playwright test ./tests/functional/$1 $2 $3 $4 $5
