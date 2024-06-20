#!/bin/bash

if [[ -f "Caddyfile" ]]; then
    echo "Caddyfile already exists. Please remove it before generating a new one."
    exit 0
fi

prompt_for_input() {
    local var_name="$1"
    local prompt_message="$2"
    local default_value="$3"
    local input_value

    if [[ -z "${!var_name}" ]]; then
        read -p "$prompt_message (press Enter to use default $default_value): " input_value
        input_value="${input_value:-$default_value}"
        export "$var_name"="$input_value"
    fi
}

DEFAULT_FRONTEND_URL="https://localhost:8443"
DEFAULT_BACKEND_URL="https://localhost:9443"

prompt_for_input "CISO_FRONTEND_URL" "Enter the frontend URL" "$DEFAULT_FRONTEND_URL"
prompt_for_input "CISO_BACKEND_URL" "Enter the backend URL" "$DEFAULT_BACKEND_URL"

extract_domain() {
    local url="$1"
    if [[ "$url" =~ https://([^/]+) ]]; then
        echo "${BASH_REMATCH[1]}"
    else
        echo "Invalid URL: $url"
        exit 1
    fi
}

frontend_target=$(extract_domain "$CISO_FRONTEND_URL")
backend_target=$(extract_domain "$CISO_BACKEND_URL")

caddyfile_content="${frontend_target} {
    reverse_proxy frontend:3000
}

${backend_target} {
    reverse_proxy /api/iam/sso/redirect backend:8000
    reverse_proxy /api/accounts/saml/0/acs/ backend:8000
    reverse_proxy /api/accounts/saml/0/acs/finish/ backend:8000
}
"

echo "$caddyfile_content" > Caddyfile
