# CISO Assistant Dispatcher

The **CISO Assistant Dispatcher** is a command-line tool that bridges event-driven messaging with a REST API to orchestrate actions based on incoming Kafka messages.

---

## Features

- **Message dispatching:** Automatically routes messages to appropriate handlers based on their `message_type`.
- **Error handling:** Catches processing errors and publishes detailed error messages to a designated error topic.
- **REST API integration:** Supports authentication and interaction with the CISO Assistant REST API.
- **Dynamic configuration:** Reads configuration from a YAML file (`.dispatcher_config.yaml`) with defaults overridable via environment variables.
- **Extensible:** A modular design using a message registry makes it easy to add new message types and functionality.

---

## Quick start

1. **Clone the repository:**

   ```bash
   git clone https://github.com/intuitem/ciso-assistant-community.git
   cd ciso-assistant-community/dispatcher
   ```

2. **Run the sample full-stack docker compose deployment**

```bash
docker compose -f sample/fullstack-build-zk-single-kafka-single.yml up -d
```

This will start a full stack deployment with a single zookeeper and a single kafka broker. The dispatcher will be started as well.
The kafka bootstrap server will be available at `localhost:9092` and the dispatcher will be consuming messages from the `observation` topic.
You will also be able to access CISO Assistant through `https://localhost:8443`

## Prerequisites

- **Python 3.8+**
- A running Kafka cluster (e.g., [Redpanda](https://redpanda.com/))
- Access to the CISO Assistant REST API
- Required Python packages (see [Installation](#installation) below)

---

## Installation

1. **Clone the repository:**

   ```bash
   git clone https://github.com/intuitem/ciso-assistant-community.git
   cd ciso-assistant-community/dispatcher
   ```

2. **Install dependencies using `uv`:**

This project uses `uv` for dependency management. If you haven't installed uv yet, follow the instructions on its [documentation](https://docs.astral.sh/uv/).
To install the project dependencies, run:

```bash
uv sync
```

This command will install all required packages as specified in the `pyproject.toml`.

3. **Set environment variables:**

   You can override default settings using environment variables. For example:

   ```bash
   export BOOTSTRAP_SERVERS="localhost:9092"
   export API_URL="https://your-api.domain.com"
   export USER_EMAIL="your_email@company.org"
   export USER_PASSWORD="your_password"
   export ERRORS_TOPIC="errors"
   export S3_URL="http://localhost:9000"
   ```

---

## Configuration

The dispatcher uses a YAML configuration file (`.dispatcher_config.yaml`) to store API URL, credentials, and other settings.

- **Initializing the config file:**

  Run the `init_config` command to create or reset the configuration file:

  ```bash
  python dispatcher.py init-config
  ```

  This command creates a file with the following structure:

  ```yaml
  rest:
    url: "https://localhost:8443"
    verify_certificate: True
  credentials:
    email: "user@company.org"
    password: ""
  ```

  Update this file with your actual REST API credentials.

- **Authentication:**

  Use the `auth` command to authenticate with the REST API and store a temporary token:

  ```bash
  python dispatcher.py auth --email your_email@company.org --password your_password
  ```

  If you have specified the credentials in the configuration file, you can skip the `--email` and `--password` arguments.

  The authentication token will be saved in a temporary file (`.tmp.yaml`).

---

## Usage

The dispatcher is invoked via its CLI interface. Below are the available commands:

### Authenticate

Obtain a temporary token by authenticating with the REST API.

```bash
python dispatcher.py auth --email your_email@company.org --password your_password
```

If credentials are not provided on the command line, the tool will try to load them from the configuration file.

### Consume messages

Start the dispatcher to consume messages from the Kafka `observation` topic. The consumer will process each message, dispatch it to the corresponding handler, and send errors to the error topic if needed.

```bash
python dispatcher.py consume
```

### Example messages

Below are some example messages that can be consumed by the dispatcher. Save these messages as JSON and send them to the `observation` topic.

#### update_applied_control

```json
{
  "message_type": "update_applied_control",
  "selector": {
    "ref_id": "foo"
  },
  "values": {
    "priority": "1"
  }
}
```

#### update_requirement_assessment

```json
{
  "message_type": "update_requirement_assessment",
  "selector": {
    "compliance_assessment__ref_id": "ISO_001",
    "requirement__ref_id": "A.5.1"
  },
  "values": {
    "result": "compliant"
  }
}
```

#### upload_attachment

```json
{
  "message_type": "upload_attachment",
  "selector": {
    "name": "Sample evidence",
    "ref_id": "bar"
  },
  "values": {
    "applied_controls": {
      "ref_id": "foo"
    },
    "file_content": "base64_encoded_data",
    "file_name": "sample.jpeg"
  }
}
```

### Initialize configuration

Reset or create the configuration file used by the dispatcher.

```bash
python dispatcher.py init-config
```
