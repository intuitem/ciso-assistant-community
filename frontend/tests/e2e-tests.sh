#! /usr/bin/env bash
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DB_DIR=$APP_DIR/backend/db
DB_NAME=test-database.sqlite3
VENV_PATH=$APP_DIR

SCRIPT_LONG_ARGS=()
SCRIPT_SHORT_ARGS=()
TEST_PATHS=()

BACKEND_PORT=8173
MAILER_WEB_SERVER_PORT=8073
MAILER_SMTP_SERVER_PORT=1073

for arg in "$@"; do
	if [[ $arg == --port* ]]; then
		if [[ "${arg#*=}" =~ ^[0-9]+$ ]]; then
			BACKEND_PORT="${arg#*=}"
		else
			echo "Invalid format for --port argument. Please use --port=PORT"
			exit 1
		fi
	elif [[ $arg == --env* ]]; then
		if [[ "${arg#*=}" =~ ^(.+)\/([^\/.]+)$ ]]; then
			VENV_PATH="${arg#*=}"
		else
			echo "Invalid format for --env argument. Please use --env=PATH"
			exit 1
		fi
	elif [[ $arg == --mailer* ]]; then
		MAILER_PORTS="${arg#*=}"
		if [[ $MAILER_PORTS =~ ^[0-9]+/[0-9]+$ ]]; then
			IFS='/' read -ra PORTS <<<"$MAILER_PORTS"
			MAILER_SMTP_SERVER_PORT="${PORTS[0]}"
			MAILER_WEB_SERVER_PORT="${PORTS[1]}"
			SCRIPT_SHORT_ARGS+=("-m")
		else
			echo "Invalid format for --mailer argument. Please use --mailer=PORT/PORT"
			exit 1
		fi
	elif [[ $arg == --* ]]; then
		SCRIPT_LONG_ARGS+=("$arg")
	elif [[ $arg == -* ]]; then
		SCRIPT_SHORT_ARGS+=("$arg")
	elif [[ $arg != -* ]]; then
		TEST_PATHS+=("$arg")
	fi
done

if [[ " ${SCRIPT_SHORT_ARGS[@]} " =~ " -h " ]] || [[ " ${SCRIPT_LONG_ARGS[@]} " =~ " --help " ]]; then
	echo "Usage: e2e-tests.sh [options] [test_path]"
	echo "Run the end-to-end tests for the CISO Assistant application."
	echo "Options:"
	echo "  --browser=NAME          Run the tests in the specified browser (chromium, firefox, webkit)"
	echo "  --env=PATH              Path to the virtual environment to use for the tests (default: first one found in $VENV_PATH)"
	echo "  --global-timeout=MS     Maximum time this test suite can run in milliseconds (default: unlimited)"
	echo "  --grep=SEARCH           Only run tests matching this regular expression (default: \".*\")"
	echo "  --headed                Run the tests in headful mode"
	echo "  -h                      Show this help message and exit"
	echo "  --list                  List all the tests"
	echo "  -m, --mailer=PORT/PORT  Use an existing mailer service on the optionally defined ports (default: $MAILER_SMTP_SERVER_PORT/$MAILER_WEB_SERVER_PORT)"
	echo "  --port=PORT             Run the backend server on the specified port (default: $BACKEND_PORT)"
	echo "  --project=NAME          Run the tests in the specified project (chromium, firefox, webkit)"
	echo "  -q                      Quick mode: execute only the tests 1 time with no retries and only 1 project"
	echo "  --repeat-each=COUNT     Run the tests the specified number of times (default: 1)"
	echo "  --retries=COUNT         Set the number of retries for the tests"
	echo "  --timeout=MS            Set the timeout for the tests in milliseconds"
	echo "  -v                      Show the output of the backend server"
	echo -e "  --workers=COUNT         Number of concurrent workers or percentage of logical CPU cores, use 1 to run in a single worker (default: 1)"
	echo "                          Be aware that increasing the number of workers may reduce tests accuracy and stability"
	exit 0
fi

ENV_CFG=$(find "$VENV_PATH" -name "pyvenv.cfg" -print -quit)
if [[ ! -z $ENV_CFG ]]; then
	VENV_PATH=$(dirname $ENV_CFG)
	if [ -d "$VENV_PATH/bin" ]; then
		source "$VENV_PATH/bin/activate"
	else
		source "$VENV_PATH/Scripts/activate"
	fi
	echo "Using virtual environment at $VENV_PATH"
else
	echo "No virtual environment found at $VENV_PATH, using standard python environment instead."
fi

if python -c "import socket;exit(0 if 0 == socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect_ex(('127.0.0.1',$BACKEND_PORT)) else 1)"; then
	echo "The port $BACKEND_PORT is already in use!"
	echo "Please stop the running process using the port or change the backend test server port using --port=PORT and try again."
	exit 1
fi

for PORT in $MAILER_WEB_SERVER_PORT $MAILER_SMTP_SERVER_PORT; do
	if python -c "import socket;exit(0 if 0 == socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect_ex(('localhost',$PORT)) else 1)"; then
		if [[ ! " ${SCRIPT_SHORT_ARGS[@]} " =~ " -m " ]]; then
			echo "The port $PORT is already in use!"
			echo "Please stop the running process using the port or change the mailer port and try again."
			exit 1
		fi
	elif [[ " ${SCRIPT_SHORT_ARGS[@]} " =~ " -m " ]]; then
		echo "No mailer service is running on port $PORT!"
		echo "Please start a mailer service on port $PORT or change the mailer port using --mailer=PORT/PORT and try again."
		echo "You can also use the isolated test mailer service by removing the -m option."
		exit 1
	fi
done

cleanup() {
	echo -e "\nCleaning up..."
	if type deactivate >/dev/null 2>&1; then
		deactivate
	fi
	if [ -n "$BACKEND_PID" ]; then
		kill $BACKEND_PID >/dev/null 2>&1
		echo "| backend server stopped"
	fi
	if [ -n "$MAILER_PID" ]; then
		docker stop $MAILER_PID >/dev/null 2>&1
		docker rm $MAILER_PID >/dev/null 2>&1
		echo "| mailer service stopped"
	fi
	if [ -f "$DB_DIR/$DB_NAME" ]; then
		rm "$DB_DIR/$DB_NAME"
		echo "| test database deleted"
	fi
	if [ -d "$APP_DIR/frontend/tests/utils/.testhistory" ]; then
		rm -rf "$APP_DIR/frontend/tests/utils/.testhistory"
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

echo "Starting backend server..."
unset POSTGRES_NAME POSTGRES_USER POSTGRES_PASSWORD
export CISO_ASSISTANT_URL=http://localhost:4173
export ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0
export DJANGO_DEBUG=True
export DJANGO_SUPERUSER_EMAIL=admin@tests.com
export DJANGO_SUPERUSER_PASSWORD=1234
export SQLITE_FILE=db/$DB_NAME
export EMAIL_HOST_USER=tests@tests.com
export DEFAULT_FROM_EMAIL='ciso-assistant@tests.net'
export EMAIL_HOST=localhost
export EMAIL_HOST_PASSWORD=pwd
export EMAIL_PORT=$MAILER_SMTP_SERVER_PORT

cd $APP_DIR/backend/
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser --noinput
if [[ " ${SCRIPT_SHORT_ARGS[@]} " =~ " -v " ]]; then
	nohup python manage.py runserver $BACKEND_PORT >$APP_DIR/frontend/tests/utils/.testbackendoutput.out 2>&1 &
	echo "You can view the backend server output at $APP_DIR/frontend/tests/utils/.testbackendoutput.out"
else
	nohup python manage.py runserver $BACKEND_PORT >/dev/null 2>&1 &
fi
BACKEND_PID=$!
echo "Test backend server started on port $BACKEND_PORT (PID: $BACKEND_PID)"

if [[ ! " ${SCRIPT_SHORT_ARGS[@]} " =~ " -m " ]]; then
	if command -v docker >/dev/null 2>&1; then
		echo "Starting mailer service..."
		MAILER_PID=$(docker run -d -p $MAILER_SMTP_SERVER_PORT:1025 -p $MAILER_WEB_SERVER_PORT:8025 mailhog/mailhog)
		echo "Mailer service started on ports $MAILER_SMTP_SERVER_PORT/$MAILER_WEB_SERVER_PORT (Container ID: ${MAILER_PID:0:6})"
	else
		echo "Docker is not installed!"
		echo "Please install Docker to use the isolated test mailer service or use -m to tell the tests to use an existing one."
		exit 1
	fi
else
	echo "Using an existing mailer service on ports $MAILER_SMTP_SERVER_PORT/$MAILER_WEB_SERVER_PORT"
fi

echo "Starting playwright tests"
export ORIGIN=http://localhost:4173
export PUBLIC_BACKEND_API_URL=http://127.0.0.1:$BACKEND_PORT/api
export MAILER_WEB_SERVER_PORT=$MAILER_WEB_SERVER_PORT

cd $APP_DIR/frontend/

if ((${#TEST_PATHS[@]} == 0)); then
	echo "| running every functional test"
else
	echo "| running tests: ${TEST_PATHS[@]}"
fi
if ((${#SCRIPT_LONG_ARGS[@]} == 0)); then
	echo "| without args"
else
	echo "| with args: ${SCRIPT_LONG_ARGS[@]}"
fi
echo "=========================================================================================="

if [[ " ${SCRIPT_SHORT_ARGS[@]} " =~ " -q " ]]; then
	echo "| quick mode"
	npx playwright test ./tests/functional/"${TEST_PATHS[@]}" -x --project=chromium "${SCRIPT_LONG_ARGS[@]}"
else
	npx playwright test ./tests/functional/"${TEST_PATHS[@]}" "${SCRIPT_LONG_ARGS[@]}"
fi
