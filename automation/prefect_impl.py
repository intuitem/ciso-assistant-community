from prefect import flow, task
from prefect.artifacts import create_table_artifact
import httpx
import json
import os
import tempfile
from prowler_helpers.utils import prowler_scan_k8s, parse_and_pass
from datetime import datetime
from icecream import ic

api_url = os.getenv("API_URL", "http://localhost:8000/api")
pat_token = os.getenv("PAT_TOKEN", "copy_from_ca")


@task(retries=1, log_prints=True)
def extract_config() -> dict:
    """Extract configuration from API"""
    try:
        with httpx.Client() as client:
            cfg = dict()
            # response = client.get(
            #     f"{api_url}/settings/feeds-settings/",
            #     headers={"Authorization": f"Token {pat_token}"},
            # )
            # response.raise_for_status()
            # cfg = response.json()
            # flip this one, once settings endpoint is aligned
            with open("settings.json") as f:
                cfg = json.load(f)
            return cfg
    except Exception as e:
        print(f"Failed to fetch config, using fallback: {e}")
        return {}


@task(log_prints=True)
def create_tmp_config_files(config):
    """Create temporary config files"""
    kubeconfig_content = config.get("kubernetes", {})

    tmp_file = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
    tmp_file.write(kubeconfig_content)
    tmp_file.close()

    print(f"Created temp config: {tmp_file.name}")
    return tmp_file.name


@task(log_prints=True)
def delete_tmp_files(config_path, scan_output_path):
    """Clean up temporary files"""
    for path in [config_path, scan_output_path]:
        try:
            if path and os.path.exists(path):
                os.unlink(path)
                print(f"Deleted: {path}")
        except Exception as e:
            print(f"Failed to delete {path}: {e}")


@task(log_prints=True)
def run_prowler_scan(config_path):
    return prowler_scan_k8s(config_path)


@task(log_prints=True)
def transform_results(scan_output_path):
    """Transform scan results"""
    scan_data = dict()
    try:
        if os.path.exists(scan_output_path):
            scan_data = parse_and_pass(scan_output_path)
            ic(scan_data.keys())
            available_scans_mapping = [{"framework": key} for key in scan_data.keys()]
            create_table_artifact(
                key="available-frameworks", table=available_scans_mapping
            )
        return scan_data

    except Exception as e:
        print(f"Transform failed: {e}")
        return {
            "scan_id": f"scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "timestamp": datetime.now().isoformat(),
            "findings_count": 0,
            "error": str(e),
        }


@task(retries=3, log_prints=True)
def update_audit(audit_id, prepared_data, mode="std"):
    # mode = "std" #"lax"
    mode = "lax"

    decision_mapping = {
        "UNKNOWN": "not_assessed",
        "PASS": "partially_compliant",
        "FAIL": "non_compliant",
        "PARTIAL": "partially_compliant",
    }

    if mode == "lax":
        decision_mapping = {
            "UNKNOWN": "not_assessed",
            "PASS": "compliant",
            "FAIL": "non_compliant",
            "PARTIAL": "partially_compliant",
        }

    with httpx.Client() as client:
        for ref_id, check_status in prepared_data.items():
            payload = {
                "ref_id": ref_id,
                "result": decision_mapping[check_status.get("aggregated_status")],
                "observation": check_status.get("observation"),
            }
            response = client.post(
                f"{api_url}/compliance-assessments/{audit_id}/update_requirement/",
                json=payload,
                headers={"Authorization": f"Token {pat_token}"},
                timeout=30,
            )
            response.raise_for_status()


@task(log_prints=True)
def match_framework_urn(audit_id) -> str:
    PROWLER_FWK_KEYS = {
        "urn:intuitem:risk:framework:iso27001-2022": "ISO27001-2022",
        "urn:intuitem:risk:framework:cis-benchmark-kubernetes": "CIS-1.10",
    }
    with httpx.Client() as client:
        response = client.get(
            f"{api_url}/compliance-assessments/{audit_id}/",
            headers={"Authorization": f"Token {pat_token}"},
        )
        response.raise_for_status()
        fwk_id = response.json().get("framework")["id"]

        response = client.get(
            f"{api_url}/frameworks/{fwk_id}/",
            headers={"Authorization": f"Token {pat_token}"},
        )
        response.raise_for_status()

        fwk_meta = response.json()
        return PROWLER_FWK_KEYS[fwk_meta["urn"]]


@flow(name="Security Scan ETL")
def scan_etl_pipeline():
    """Main ETL pipeline for security scanning"""
    config_path = None
    scan_output_path = None

    try:
        config = extract_config()
        for source in config:
            for name, feed in source.items():
                if feed["scanner"] == "prowler":
                    config_path = create_tmp_config_files(feed["settings"]["config"])
                    scan_output_path = run_prowler_scan(config_path)
                    transformed = transform_results(scan_output_path)

                    for audit_uuid in feed["scoped_audits"]:
                        prowler_key = match_framework_urn(audit_uuid)
                        checks_results = transformed[prowler_key]
                        if checks_results is None:
                            print(
                                "couldn't find a match for this framework on the checks data"
                            )
                            continue
                        update_audit(audit_uuid, checks_results)
                else:
                    print(f"the scanner on {name} is not supported yet. Moving on")

        return {}

    finally:
        # Always cleanup
        if config_path or scan_output_path:
            delete_tmp_files(config_path, scan_output_path)


# Run the flow
if __name__ == "__main__":
    # Run once
    result = scan_etl_pipeline()
    print(f"Pipeline completed: {result}")

    # Or schedule it (requires Prefect server running)
    # scan_etl_pipeline.serve(
    #     name="scheduled-scan",
    #     cron="0 */6 * * *"  # Every 6 hours
    # )
