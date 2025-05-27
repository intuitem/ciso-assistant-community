import subprocess
import argparse
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Prowler security scanner wrapper"

    def add_arguments(self, parser):
        parser.add_argument(
            "--binary-path", type=str, default="prowler", help="Path to prowler binary"
        )

        # Use REMAINDER to capture everything after the first positional arg
        parser.add_argument(
            "prowler_args",
            nargs=argparse.REMAINDER,
            help="All arguments to pass to prowler (use after first positional arg)",
        )

    def handle(self, *args, **options):
        binary_path = options["binary_path"]
        prowler_args = options["prowler_args"]

        # Build the full command
        cmd = [binary_path] + prowler_args

        self.stdout.write(f"Executing: {' '.join(cmd)}")

        try:
            # Execute prowler with real-time output
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
            )

            # Stream output in real-time
            for line in process.stdout:
                self.stdout.write(line.rstrip())

            process.wait()

            if process.returncode != 0:
                self.stderr.write(f"Prowler exited with code {process.returncode}")

        except FileNotFoundError:
            raise CommandError(f"Prowler binary not found: {binary_path}")
