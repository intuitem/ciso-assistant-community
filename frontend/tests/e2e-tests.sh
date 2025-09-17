#! /usr/bin/env bash
APP_DIR=$(realpath "$(dirname $0)/../..")
DB_DIR=$APP_DIR/backend/db
DB_NAME=test-database.sqlite3
DB_INIT_NAME=test-database-initial.sqlite3

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
  elif [[ $arg == -q ]]; then
    QUICK_MODE_ACTIVATED=1
  elif [[ $arg == -v ]]; then
    STORE_BACKEND_OUTPUT=1
  elif [[ $arg == -k ]]; then
    KEEP_DATABASE_SNAPSHOT=1
  elif [[ $arg == --no-sudo ]]; then
    DO_NOT_USE_SUDO=1
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
  echo "  -q                      Quick mode: execute only the tests 1 time with no retries and only 1 project"
  echo "  -k                      Keep a saved snapshot of the initial database and use it to avoid executing useless migrations."
  echo "                          If the initial database hasn't been created running the tests with this option will create it."
  echo "                          Running the tests without this option will delete the saved initial database."
  echo "  --no-sudo               Run docker commands without using sudo as a prefix."
  echo "  --port=PORT             Run the backend server on the specified port (default: $BACKEND_PORT)"
  echo "  -m, --mailer=PORT/PORT  Use an existing mailer service on the optionally defined ports (default: $MAILER_SMTP_SERVER_PORT/$MAILER_WEB_SERVER_PORT)"

  echo "Playwright options:"
  echo "  --browser=NAME          Run the tests in the specified browser (chromium, firefox, webkit)"
  echo "  --global-timeout=MS     Maximum time this test suite can run in milliseconds (default: unlimited)"
  echo "  --grep=SEARCH           Only run tests matching this regular expression (default: \".*\")"
  echo "  --headed                Run the tests in headful mode"
  echo "  -h                      Show this help message and exit"
  echo "  --list                  List all the tests"
  echo "  --project=NAME          Run the tests in the specified project (chromium, firefox, webkit)"
  echo "  --repeat-each=COUNT     Run the tests the specified number of times (default: 1)"
  echo "  --retries=COUNT         Set the number of retries for the tests"
  echo "  --timeout=MS            Set the timeout for the tests in milliseconds"
  echo "  -v                      Show the output of the backend server"
  echo -e "  --workers=COUNT         Number of concurrent workers or percentage of logical CPU cores, use 1 to run in a single worker (default: 1)"
  echo "                          Be aware that increasing the number of workers may reduce tests accuracy and stability"
  exit 0
fi

if [[ "$(id -u "$(whoami)")" -eq 0 ]]; then
  echo "Running this script with a root account is highly discouraged as it can cause bugs with playwright."
fi

if python3 -c "
import socket
try :
	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	# Using python to check if the port is opened is safer for compatibility
	# But it increase the execution time of the script with the timeout
	# A local TCP connection should never reach a 1s delay
	s.settimeout(1)
	s.connect(('127.0.0.1', $BACKEND_PORT))
	port_already_in_used = True
except :
	port_already_in_used = False
s.close()
# We use "not" because 0 is True and 1 is False in bash
exit(not port_already_in_used)
"; then
  echo "The port $BACKEND_PORT is already in use!"
  echo "You can either:"
  echo "- Kill the process which is currently using this port."
  echo "- Change the backend test server port using --port=NEW_PORT and try again."
  exit 1
fi

for PORT in $MAILER_WEB_SERVER_PORT $MAILER_SMTP_SERVER_PORT; do
  if python3 -c "import socket;exit(0 if 0 == socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect_ex(('localhost',$PORT)) else 1)"; then
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
  if [[ -n "$BACKEND_PID" ]]; then
    kill $BACKEND_PID >/dev/null 2>&1
    echo "| backend server stopped"
  fi
  if [[ -f "$DB_DIR/$DB_NAME" ]]; then
    rm "$DB_DIR/$DB_NAME"
    echo "| test database deleted"
  fi
  if [[ -z "$KEEP_DATABASE_SNAPSHOT" && -f "$DB_DIR/$DB_INIT_NAME" ]]; then
    rm "$DB_DIR/$DB_INIT_NAME"
    echo "| test initial database snapshot deleted"
  fi
  if [[ -n "$MAILER_PID" ]]; then
    if [[ -z "$DO_NOT_USE_SUDO" ]]; then
      sudo docker stop $MAILER_PID &>/dev/null
      sudo docker rm $MAILER_PID &>/dev/null
    else
      docker stop $MAILER_PID &>/dev/null
      docker rm $MAILER_PID &>/dev/null
    fi
    echo "| mailer service stopped"
  fi
  if [[ -d "$APP_DIR/frontend/tests/utils/.testhistory" ]]; then
    rm -rf "$APP_DIR/frontend/tests/utils/.testhistory"
    echo "| test data history removed"
  fi
  # This must be at the end of the cleanup as the sudo command can block the script
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

if [[ ! " ${SCRIPT_SHORT_ARGS[@]} " =~ " -m " ]]; then
  if command -v docker &>/dev/null; then
    echo "Starting mailer service..."
    if [[ -z "$DO_NOT_USE_SUDO" ]]; then
      MAILER_PID=$(sudo docker run -d -p $MAILER_SMTP_SERVER_PORT:1025 -p $MAILER_WEB_SERVER_PORT:8025 mailhog/mailhog)
    else
      MAILER_PID=$(docker run -d -p $MAILER_SMTP_SERVER_PORT:1025 -p $MAILER_WEB_SERVER_PORT:8025 mailhog/mailhog)
    fi
    echo "Mailer service started on ports $MAILER_SMTP_SERVER_PORT/$MAILER_WEB_SERVER_PORT (Container ID: ${MAILER_PID:0:6})"
  else
    echo "Docker is not installed!"
    echo "Please install Docker to use the isolated test mailer service or use -m to tell the tests to use an existing one."
    exit 1
  fi
else
  echo "Using an existing mailer service on ports $MAILER_SMTP_SERVER_PORT/$MAILER_WEB_SERVER_PORT"
fi

echo "Starting backend server..."
unset POSTGRES_NAME POSTGRES_USER POSTGRES_PASSWORD
export CISO_ASSISTANT_URL=http://localhost:4173
export CISO_ASSISTANT_VERSION=$(git describe --tags --always)
export CISO_ASSISTANT_BUILD=$(git rev-parse --short HEAD)
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
export CISO_ASSISTANT_VERSION=$(git describe --tags --always)
export CISO_ASSISTANT_BUILD=$(git rev-parse --short HEAD)

cd $APP_DIR/backend/ || exit 1
if [[ -z $KEEP_DATABASE_SNAPSHOT ]]; then
  poetry run python3 manage.py makemigrations
  poetry run python3 manage.py migrate
elif [[ ! -f "$DB_DIR/$DB_INIT_NAME" ]]; then
  poetry run python3 manage.py makemigrations
  poetry run python3 manage.py migrate
  cp "$DB_DIR/$DB_NAME" "$DB_DIR/$DB_INIT_NAME"
else
  # Copying the initial database instead of applying the migrations saves a lot of time
  cp "$DB_DIR/$DB_INIT_NAME" "$DB_DIR/$DB_NAME"
fi

poetry run python3 manage.py createsuperuser --noinput
if [[ -n "$STORE_BACKEND_OUTPUT" ]]; then
  nohup poetry run python3 manage.py runserver $BACKEND_PORT >$APP_DIR/frontend/tests/utils/.testbackendoutput.out 2>&1 &
  echo "You can view the backend server output at $APP_DIR/frontend/tests/utils/.testbackendoutput.out"
else
  nohup poetry run python3 manage.py runserver $BACKEND_PORT >/dev/null 2>&1 &
fi
BACKEND_PID=$!
echo "Test backend server started on port $BACKEND_PORT (PID: $BACKEND_PID)"

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

FRONTEND_HASH_FILE="$APP_DIR/frontend/tests/.frontend_hash"
FRONTEND_HASH=$(find "$APP_DIR"/frontend/{src,messages} -type f \( -name "*.ts" -o -name "*.svelte" -o -name "*.json" \) -print0 | xargs -0 md5sum | md5sum)

if [ "$(cat "$FRONTEND_HASH_FILE")" != "$FRONTEND_HASH" ]; then
  pnpm run build # Required for the "pnpm run preview" command of playwright.config.ts
  echo "$FRONTEND_HASH" >"$FRONTEND_HASH_FILE"
fi

if [[ -n "$QUICK_MODE_ACTIVATED" ]]; then
  pnpm playwright test ./tests/functional/"${TEST_PATHS[@]}" --project=chromium "${SCRIPT_LONG_ARGS[@]}" "${SCRIPT_SHORT_ARGS[@]}"
else
  pnpm playwright test ./tests/functional/"${TEST_PATHS[@]}" "${SCRIPT_LONG_ARGS[@]}" "${SCRIPT_SHORT_ARGS[@]}"
fi
