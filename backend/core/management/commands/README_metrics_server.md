# Prometheus Metrics Server

This document explains how to use the new Prometheus metrics server management command.

## Overview

The `metrics_server` management command runs a standalone HTTP server that exposes Prometheus metrics on a separate port from the main CISO Assistant application. This approach provides better security and performance by isolating metrics collection from the main application.

## Usage

### Basic Usage

```bash
python manage.py metrics_server
```

This starts the metrics server on `0.0.0.0:8001` by default with automatic metric updates every 60 seconds.

### Command Options

- `--port PORT`: Port to run the metrics server on (default: 8001)
- `--host HOST`: Host to bind the metrics server to (default: 0.0.0.0)
- `--update-interval SECONDS`: Interval in seconds to update metrics (default: 60)
- `--no-update`: Disable automatic metric updates (metrics will only be updated on server startup)

### Examples

```bash
# Run on a different port
python manage.py metrics_server --port 9090

# Run with custom update interval (5 minutes)
python manage.py metrics_server --update-interval 300

# Run without automatic updates
python manage.py metrics_server --no-update

# Run on localhost only
python manage.py metrics_server --host 127.0.0.1 --port 8080
```

## Accessing Metrics

Once the server is running, you can access the metrics at:

```
http://HOST:PORT/metrics
```

For example, with default settings: `http://localhost:8001/metrics`

## Available Metrics

The following metrics are exposed:

- `ciso_assistant_nb_users`: Number of users in the instance
- `ciso_assistant_nb_first_login`: Number of users who have logged in for the first time
- `ciso_assistant_nb_libraries`: Number of loaded libraries
- `ciso_assistant_nb_domains`: Number of domains
- `ciso_assistant_nb_perimeters`: Number of perimeters
- `ciso_assistant_nb_assets`: Number of assets
- `ciso_assistant_nb_threats`: Number of threats
- `ciso_assistant_nb_functions`: Number of reference control functions
- `ciso_assistant_nb_measures`: Number of applied control measures
- `ciso_assistant_nb_evidences`: Number of evidences
- `ciso_assistant_nb_compliance_assessments`: Number of compliance assessments
- `ciso_assistant_nb_risk_assessments`: Number of risk assessments
- `ciso_assistant_nb_risk_scenarios`: Number of risk scenarios
- `ciso_assistant_nb_risk_acceptances`: Number of risk acceptances
- `ciso_assistant_nb_seats`: Number of seats
- `ciso_assistant_nb_editors`: Number of editors
- `ciso_assistant_license_expiration`: License expiration timestamp
- `ciso_assistant_created_at`: Instance creation timestamp
- `ciso_assistant_last_login`: Last login timestamp
- `ciso_assistant_build_info`: Build information (version, build, schema_version, debug)

## Prometheus Configuration

To scrape these metrics with Prometheus, add the following job to your `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: "ciso-assistant"
    static_configs:
      - targets: ["ciso-assistant-host:8001"]
    scrape_interval: 60s
    metrics_path: /metrics
```

## Security Considerations

- The metrics server runs on a separate port from the main application
- Consider using firewall rules to restrict access to the metrics port
- For production deployments, consider binding to `127.0.0.1` instead of `0.0.0.0` if metrics collection runs on the same host as Prometheus
- No authentication is required for the metrics endpoint (standard for Prometheus)

## Troubleshooting

### Port Already in Use

If you get a "Port already in use" error, either:

- Use a different port with `--port`
- Stop any service using that port
- Check what's using the port: `sudo lsof -i :8001`

### Permission Errors

Ensure the user running the command has:

- Read access to the Django project
- Database connection permissions
- Permission to bind to the specified port (ports < 1024 require root)

### Database Connection Issues

The metrics server requires a working database connection to collect metrics. Ensure:

- Database is running and accessible
- Django settings are properly configured
- Database credentials are correct
