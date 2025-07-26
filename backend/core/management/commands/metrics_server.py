"""
Django management command to run a Prometheus metrics server.

This command starts a standalone HTTP server that exposes Prometheus metrics
on a separate port from the main application. It updates the metrics
periodically and serves them in Prometheus format.
"""

import time
import signal
import threading
import logging
from django.core.management.base import BaseCommand, CommandError
from prometheus_client import start_http_server

from core.helpers import get_instance_metrics
from core.instance_metrics import (
    nb_users_gauge,
    nb_first_login_gauge,
    nb_libraries_gauge,
    nb_domains_gauge,
    nb_perimeters_gauge,
    nb_assets_gauge,
    nb_threats_gauge,
    nb_functions_gauge,
    nb_measures_gauge,
    nb_evidences_gauge,
    nb_compliance_assessments_gauge,
    nb_risk_assessments_gauge,
    nb_risk_scenarios_gauge,
    nb_risk_acceptances_gauge,
    nb_seats_gauge,
    nb_editors_gauge,
    expiration_gauge,
    created_at_gauge,
    last_login_gauge,
)

logger = logging.getLogger(__name__)


class MetricsUpdater:
    """Class to handle periodic metrics updates."""

    def __init__(self, update_interval=60):
        self.update_interval = update_interval
        self.running = False
        self.thread = None

    def update_metrics(self):
        """Update all Prometheus metrics with current values."""
        try:
            metrics = get_instance_metrics()

            nb_users_gauge.set(metrics.get("nb_users", 0))
            nb_first_login_gauge.set(metrics.get("nb_first_login", 0))
            nb_libraries_gauge.set(metrics.get("nb_libraries", 0))
            nb_domains_gauge.set(metrics.get("nb_domains", 0))
            nb_perimeters_gauge.set(metrics.get("nb_perimeters", 0))
            nb_assets_gauge.set(metrics.get("nb_assets", 0))
            nb_threats_gauge.set(metrics.get("nb_threats", 0))
            nb_functions_gauge.set(metrics.get("nb_functions", 0))
            nb_measures_gauge.set(metrics.get("nb_measures", 0))
            nb_evidences_gauge.set(metrics.get("nb_evidences", 0))
            nb_compliance_assessments_gauge.set(
                metrics.get("nb_compliance_assessments", 0)
            )
            nb_risk_assessments_gauge.set(metrics.get("nb_risk_assessments", 0))
            nb_risk_scenarios_gauge.set(metrics.get("nb_risk_scenarios", 0))
            nb_risk_acceptances_gauge.set(metrics.get("nb_risk_acceptances", 0))
            nb_seats_gauge.set(metrics.get("nb_seats", 0))
            nb_editors_gauge.set(metrics.get("nb_editors", 0))
            expiration_gauge.set(metrics.get("expiration", 0))
            created_at_gauge.set(metrics.get("created_at", 0))
            last_login_gauge.set(metrics.get("last_login", 0))

            logger.debug("Metrics updated successfully")

        except Exception as e:
            logger.error("Error updating metrics: %s", e)

    def _update_loop(self):
        """Main loop for periodic metrics updates."""
        while self.running:
            self.update_metrics()
            time.sleep(self.update_interval)

    def start(self):
        """Start the metrics update thread."""
        if self.running:
            return

        self.running = True
        self.thread = threading.Thread(target=self._update_loop, daemon=True)
        self.thread.start()
        logger.info("Started metrics updater with %ss interval", self.update_interval)

    def stop(self):
        """Stop the metrics update thread."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("Stopped metrics updater")


class Command(BaseCommand):
    help = "Start a Prometheus metrics server on a separate port"

    def add_arguments(self, parser):
        parser.add_argument(
            "--port",
            type=int,
            default=8001,
            help="Port to run the metrics server on (default: 8001)",
        )
        parser.add_argument(
            "--host",
            type=str,
            default="0.0.0.0",
            help="Host to bind the metrics server to (default: 0.0.0.0)",
        )
        parser.add_argument(
            "--update-interval",
            type=int,
            default=60,
            help="Interval in seconds to update metrics (default: 60)",
        )
        parser.add_argument(
            "--no-update",
            action="store_true",
            help="Disable automatic metric updates "
            "(metrics will only be updated on request)",
        )

    def handle(self, *args, **options):
        port = options["port"]
        host = options["host"]
        update_interval = options["update_interval"]
        auto_update = not options["no_update"]

        # Validate port range
        if not (1 <= port <= 65535):
            raise CommandError(f"Port must be between 1 and 65535, got {port}")

        # Set up signal handlers for graceful shutdown
        shutdown_event = threading.Event()
        metrics_updater = None

        def signal_handler(signum, _frame):
            self.stdout.write(
                self.style.WARNING(f"Received signal {signum}, shutting down...")
            )
            shutdown_event.set()
            if metrics_updater:
                metrics_updater.stop()

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        try:
            # Initialize metrics updater if auto-update is enabled
            if auto_update:
                metrics_updater = MetricsUpdater(update_interval)
                metrics_updater.start()
                # Update metrics immediately on startup
                metrics_updater.update_metrics()
            else:
                # Update metrics once on startup even if auto-update
                # is disabled
                updater = MetricsUpdater()
                updater.update_metrics()

            # Start the Prometheus HTTP server
            self.stdout.write(
                self.style.SUCCESS(
                    f"Starting Prometheus metrics server on {host}:{port}"
                )
            )

            if auto_update:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Metrics will be updated every {update_interval} seconds"
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        "Auto-update disabled. Metrics will only be updated "
                        "on server startup."
                    )
                )

            # Start the server
            start_http_server(port, addr=host)

            self.stdout.write(
                self.style.SUCCESS(
                    f"Metrics server running at http://{host}:{port}/metrics"
                )
            )
            self.stdout.write("Press Ctrl+C to stop the server")

            # Keep the main thread alive
            while not shutdown_event.is_set():
                shutdown_event.wait(1)

        except OSError as e:
            if e.errno == 98:  # Address already in use
                raise CommandError(
                    f"Port {port} is already in use. Please choose a different port."
                )
            else:
                raise CommandError(f"Failed to start server: {e}")
        except KeyboardInterrupt:
            pass
        except Exception as e:
            raise CommandError(f"Unexpected error: {e}")
        finally:
            if metrics_updater:
                metrics_updater.stop()
            self.stdout.write(self.style.SUCCESS("Metrics server stopped"))
