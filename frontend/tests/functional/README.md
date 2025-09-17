# E2E Tests Usage Guide

## Overview

This project uses **Playwright** for end-to-end (E2E) tests that allow comprehensive testing of the CISO Assistant application by simulating real user interactions.

Playwright Documentation: https://playwright.dev/docs/intro

## Test Structure

```
frontend/tests/
.
├── Dockerfile
├── docker-compose.e2e-tests.yml
├── e2e-tests.sh
├── functional
│   ├── backup-restore.test.ts
│   ├── detailed
│   │   ├── common.test.ts
│   │   ├── compliance-assessments.test.ts
│   │   ├── libraries.test.ts
│   │   └── login.test.ts
│   ├── domain-import.test.ts
│   ├── nav.test.ts
│   ├── startup.test.ts
│   ├── tests-frontend-README.md
│   ├── user-permissions.test.ts
│   └── user-route.test.ts
├── fuzz
│   └── open-redirect
│       ├── open-redirect.test.ts
│       └── payloads.txt
├── utils
│   ├── analytics-page.ts
│   ├── base-page.ts
│   ├── form-content.ts
│   ├── layout.ts
│   ├── login-page.ts
│   ├── mail-content.ts
│   ├── mailer.ts
│   ├── page-content.ts
│   ├── page-detail.ts
│   ├── sample-domain-schema-1.bak
│   ├── sample-domain-schema-2.bak
│   ├── sidebar.ts
│   ├── test-data.ts
│   ├── test-utils.ts
│   ├── test_file.txt
│   └── test_image.jpg
└── utilsv2
    ├── base
    │   ├── create-modal.ts
    │   ├── list-view-page.ts
    │   ├── model-form.ts
    │   └── model-table.ts
    ├── core
    │   ├── base.ts
    │   ├── element.ts
    │   ├── fixtures.ts
    │   ├── hot-reloader.ts
    │   ├── page.ts
    │   ├── test-data.ts
    │   └── utils.ts
    └── derived
        ├── analytics-page.ts
        ├── create-modal.ts
        ├── list-view.ts
        ├── login-page.ts
        ├── model-form
        │   └── folder-create-form.ts
        ├── sidebar.ts
        └── toast.ts
```

## Prerequisites

- **Node.js** and **pnpm** installed
- **Python 3** with **Poetry** for the backend
- **Docker** for the mail service (optional with `-m`)
- **Git** for version information

## Installation

```bash
# Install frontend dependencies
cd frontend
pnpm install
pnpm run build

# Install Playwright
pnpm exec playwright install

# Install backend dependencies
cd ../backend
poetry install
```

## Running Tests

### Basic Command

```bash
# From the frontend/tests directory
./e2e-tests.sh
```

### Main Options

#### Configuration Options

- `--port=8080` : Backend server port (default: 8173)
- `--mailer=1025/8025` : SMTP/Web ports for mail service
- `--no-sudo` : Run Docker without sudo

#### Execution Options

- `-q` : Quick mode (single project, no retry)
- `-v` : Show backend server logs
- `-k` : Keep initial database snapshot
- `-m` : Use existing mail service

#### Playwright Options

- `--browser=chromium` : Specific browser (chromium/firefox/webkit)
- `--headed` : Run with graphical interface
- `--grep="pattern"` : Filter tests by name
- `--project=chromium` : Specific project
- `--workers=1` : Number of parallel workers
- `--retries=2` : Number of retry attempts on failure

### Usage Examples

```bash
# Quick tests in headless mode
./e2e-tests.sh -q

# Tests with graphical interface on Firefox
./e2e-tests.sh --headed --browser=firefox

# Specific tests with pattern
./e2e-tests.sh --grep="backup"

# Tests with visible backend logs
./e2e-tests.sh -v

# Tests with existing mail service
./e2e-tests.sh -m --mailer=1025/8025

# Tests for a specific file
./e2e-tests.sh nav.test.ts
```
