#! /usr/bin/env bash
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DB_DIR=$APP_DIR/backend/db
DATABASE_BACKUP_NAME=ciso-assistant-backup.sqlite3

SCRIPT_LONG_ARGS=()
SCRIPT_SHORT_ARGS=()
TEST_PATHS=()

if lsof -Pi :8080 -sTCP:LISTEN -t > /dev/null ; then
    echo "The port 8080 is already in use!"
    echo "Please stop the running process using the port and try again."
    exit 1
fi

for arg in "$@"
do
    if [[ $arg == --* ]]; then
        SCRIPT_LONG_ARGS+=("$arg")
    elif [[ $arg == -* ]]; then
        SCRIPT_SHORT_ARGS+=("$arg")
    elif [[ $arg != -* ]]; then
        TEST_PATHS+=("$arg")
    fi
done

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

finish() {
    echo "Test successfully completed!"
    cleanup
}

trap cleanup SIGINT SIGTERM
trap finish EXIT

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
if [[ " ${SCRIPT_SHORT_ARGS[@]} " =~ " -v " ]]; then
    nohup python manage.py runserver 8080 > $APP_DIR/frontend/tests/utils/.testbackendoutput.out 2>&1 &
else
    nohup python manage.py runserver 8080 > /dev/null 2>&1 &
fi
BACKEND_PID=$!
echo "test backend server started on port 8080 (PID: $BACKEND_PID)"

echo "starting playwright tests"
export ORIGIN=http://localhost:4173
export PUBLIC_BACKEND_API_URL=http://localhost:8080/api

cd $APP_DIR/frontend/

if (( ${#TEST_PATHS[@]} == 0 )); then
    echo "running every functional test"
else
    echo "running tests: ${TEST_PATHS[@]}"
fi
if (( ${#SCRIPT_LONG_ARGS[@]} == 0 )); then
    echo "without args"
else
    echo "with args: ${SCRIPT_LONG_ARGS[@]}"
fi

npx playwright test ./tests/functional/"${TEST_PATHS[@]}" "${SCRIPT_LONG_ARGS[@]}"
