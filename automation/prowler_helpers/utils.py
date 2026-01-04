import tempfile
from pathlib import Path
import subprocess
import pandas as pd
from collections import defaultdict
from icecream import ic


def prowler_scan_k8s(config_path) -> str:
    """Run Prowler security scan with the CLI"""
    output_file = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False)
    output_file.close()

    try:
        cmd = [
            "prowler",
            "kubernetes",
            "--kubeconfig-file",
            config_path,
            "--output-filename",
            Path(output_file.name).stem,
            "--output-directory",
            Path(output_file.name).parent,
            "--output-formats",
            "csv",
        ]

        # "--output-directory=/tmp",
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        print(f"Prowler exit code: {result.returncode}")

        if result.returncode != 0:
            print(f"Prowler stderr: {result.stderr}")

        return output_file.name

    except subprocess.TimeoutExpired:
        print("Prowler scan timed out")
        return output_file.name
    except Exception as e:
        print(f"Prowler scan failed: {e}")
        return output_file.name


def parse_and_pass(filename) -> dict:
    """
    Parse Prowler CSV output and create nested dictionary structure

    Args:
        filename (str): Path to the CSV file

    Returns:
        dict: Nested dictionary with framework compliance data
    """
    try:
        df = pd.read_csv(filename, sep=";")

        required_columns = ["CHECK_ID", "STATUS", "COMPLIANCE", "CATEGORIES"]

        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            print(f"Missing columns in CSV: {missing_columns}")
            return {}

        df = df[required_columns]

        # Remove rows where COMPLIANCE is null/empty
        df = df.dropna(subset=["COMPLIANCE"])
        df = df[df["COMPLIANCE"].str.strip() != ""]

        result = defaultdict(
            lambda: defaultdict(
                lambda: {"aggregated_status": None, "checks": {}, "observation": ""}
            )
        )

        # Process each row
        for _, row in df.iterrows():
            check_id = row["CHECK_ID"]
            status = row["STATUS"]
            compliance_str = row["COMPLIANCE"]

            compliance_items = [
                item.strip() for item in compliance_str.split("|") if item.strip()
            ]

            for compliance_item in compliance_items:
                # Parse "framework: requirement_ref_id" format
                if ":" in compliance_item:
                    framework, requirement_refs = compliance_item.split(":", 1)
                    framework = framework.strip()
                    requirement_refs = requirement_refs.strip()

                    # Split multiple requirements (separated by commas)
                    individual_requirements = [
                        req.strip()
                        for req in requirement_refs.split(",")
                        if req.strip()
                    ]

                    for requirement_ref in individual_requirements:
                        result[framework][requirement_ref]["checks"][check_id] = status
                        current_checks = result[framework][requirement_ref]["checks"]

                        observation = "\n".join(
                            [f"{k}:{v}" for k, v in current_checks.items()]
                        )
                        # Determine aggregated status based on all checks for this requirement
                        statuses = list(current_checks.values())
                        aggregated_status = calculate_aggregated_status(statuses)

                        result[framework][requirement_ref]["aggregated_status"] = (
                            aggregated_status
                        )
                        result[framework][requirement_ref]["observation"] = observation
                else:
                    print(f"Invalid compliance format: {compliance_item}")

        final_result = {}
        for framework, requirements in result.items():
            final_result[framework] = {}
            for req_ref, data in requirements.items():
                final_result[framework][req_ref] = dict(data)

        print(
            f"Successfully parsed {len(df)} checks across {len(final_result)} frameworks"
        )
        return final_result

    except FileNotFoundError:
        print.error(f"CSV file not found: {filename}")
        return {}
    except pd.errors.EmptyDataError:
        print(f"CSV file is empty: {filename}")
        return {}
    except Exception as e:
        print(f"Error parsing CSV file {filename}: {str(e)}")
        return {}


def calculate_aggregated_status(statuses):
    if not statuses:
        return "UNKNOWN"

    # If only one check and it's MANUAL, return UNKNOWN
    if len(statuses) == 1 and statuses[0] == "MANUAL":
        return "UNKNOWN"

    # Count different status types
    unique_statuses = set(statuses)

    # If any check failed, overall status is FAIL
    if "FAIL" in unique_statuses:
        return "FAIL"

    # If all checks passed, overall status is PASS
    if len(unique_statuses) == 1 and "PASS" in unique_statuses:
        return "PASS"

    # If we have a mix of statuses or only non-PASS/non-FAIL statuses
    # (like MANUAL, INFO, etc.), it's PARTIAL
    return "PARTIAL"
