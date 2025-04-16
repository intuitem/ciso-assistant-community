# CISO Assistant Dispatcher

The **CISO Assistant Dispatcher** is a command-line tool that bridges event-driven messaging with the CISO Assistant API to orchestrate actions based on incoming Kafka messages.

## Prerequisites

- **Python 3.8+**
- A running Kafka cluster (can be any Kafka-compatible cluster, e.g. [Redpanda](https://redpanda.com/))
- Access to the CISO Assistant REST API
- Required Python packages (see [Installation](#installation) below)

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

3. **Run the interactive configuration script:**

   ```bash
   uv run dispatcher.py init-config -i
   ```

4. Consume messages from the `observation` topic

   ```bash
   uv run dispatcher.py consume
   ```

## Configuration

You can configure the dispatcher using environment variables, the `init-config` command, or the `.dispatcher_config` configuration file.

### Environment variables reference

```bash
DEBUG=True/False # Set to true to enable debug logging

API_URL=https://localhost:8443 # The URL of the CISO Assistant REST API
USER_EMAIL=user@company.org
USER_PASSWORD=your_password
AUTO_RENEW_SESSION=True/False # Set to true to enable automatic token refresh, do not set if using token-based authentication
USER_TOKEN=your_ciso_assistant_access_token # Personal Access Token, do not set if using credentials-based authentication
VERIFY_CERTIFICATE=True/False # Set to trure to verify SSL certificates between the dispatcher and API
BOOTSTRAP_SERVERS=localhost:9092 # The Kafka bootstrap servers, comma separated list
ERRORS_TOPIC=errors # The Kafka topic to send errors to
S3_URL=localhost:9000 # The URL of the S3 storage
S3_ACCESS_KEY=your_access_key # The access key for S3 storage
S3_SECRET_KEY=your_secret_key # The secret key for S3 storage
```

### Initializing the config file

Run the `init-config` command to create or reset the configuration file:

```bash
python dispatcher.py init-config
```

You can add the `-i` flag for an interactive mode, which will prompt you for the necessary information.

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

### Authentication

Use the `auth` command to authenticate with the REST API.
There are currently two modes of authentication supported by the dispatcher:

- Token-based authentication
- Credentials-based authentication

#### Token-based authentication

This is done using a Personal Access Token (PAT) that you can generate in CISO Assistant.
To use token-based authentication, you need to set the `USER_TOKEN` environment variable or specify it in the configuration file or during interactive configuration definition using the `init-config` with the `-i` flag enabled.

#### Credentials-based authentication

This is done using your email and password. You can specify these credentials in the configuration file or pass them as command-line arguments to the `auth` command.

```bash
python dispatcher.py auth --email your_email@company.org --password your_password
```

If you have specified the credentials in the configuration file, or in the `USER_EMAIL` and `USER_PASSWORD` environment variables, you can skip the `--email` and `--password` arguments.

> [!WARNING]
> Multi-factor authentication is not yet supported in the dispatcher. Accounts with MFA enabled will not be able to authenticate using the dispatcher.

#### Automatic token refresh

Using credentials-based authentication, it is possible to enable silent re-authentication on token expiration. You can do so using the `auto_renew_session` setting. As usual, it can be set either as environment variable or in the configuration file.

The authentication token will be saved in a temporary file (`.tmp.yaml`).

### S3 storage configuration

The URL of the S3 storage can be set in the configuration file or via the `S3_URL` environment variable. The dispatcher will use this URL to upload files when processing messages.

#### Authenticate requests to the S3 storage

Requests to the S3 storage are authenticated using the `S3_ACCESS_KEY` and `S3_SECRET_KEY` settings as environment variables or in the configuration file.

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

Attachments can be uploaded either as base64 encoded data or fetched from a S3 bucket.

##### Using base64 encoded data

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

##### Using S3

```bash
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
    "file_s3_bucket": "my_bucket",
    "file_s3_key": "sample.jpeg"
  }
}
```

## Deployment

The dispatcher can be used as a CLI tool or deployed as a service. To deploy it as a service, you can use Docker or any other containerization tool.

Out of the box, we provide a Dockerfile and the `make_config.py` script to generate a docker compose file containing CISO Assistant and the dispatcher.

The `make_config.py` script is accessible under `config/make_config.py`. Please refer to the readme file in the `config` directory for more information on how to use it.
