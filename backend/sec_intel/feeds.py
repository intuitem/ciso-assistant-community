import csv
import gzip
import io
import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Optional

import httpx
import structlog

logger = structlog.get_logger(__name__)

# --- Settings helper ---

DEFAULT_SETTINGS = {
    "kev_feed_enabled": False,
    "epss_feed_enabled": False,
    "nvd_enrich_enabled": False,
    "network_timeout": 30,
}


def get_feed_settings() -> dict:
    """Return feed settings dict. Returns all-disabled defaults on any error."""
    try:
        from global_settings.models import GlobalSettings

        gs = GlobalSettings.objects.get(name="sec-intel-feeds")
        return gs.value if isinstance(gs.value, dict) else DEFAULT_SETTINGS
    except Exception:
        return DEFAULT_SETTINGS


def _get_timeout() -> int:
    return get_feed_settings().get("network_timeout", 30)


# --- KEV Feed ---

KEV_URL = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"


class KEVFeed:
    def __init__(self, file_path: Optional[Path] = None):
        self.file_path = file_path

    def fetch(self) -> dict:
        """Fetch KEV JSON from URL or local file."""
        if self.file_path:
            return json.loads(self.file_path.read_text())
        resp = httpx.get(KEV_URL, timeout=_get_timeout())
        resp.raise_for_status()
        return resp.json()

    def parse(self, raw: dict) -> list[dict]:
        """Extract KEV entries from JSON."""
        results = []
        for vuln in raw.get("vulnerabilities", []):
            try:
                results.append(
                    {
                        "cve_id": vuln["cveID"],
                        "name": vuln.get("vulnerabilityName", vuln["cveID"]),
                        "description": vuln.get("shortDescription", ""),
                        "date_added": datetime.strptime(
                            vuln["dateAdded"], "%Y-%m-%d"
                        ).date(),
                    }
                )
            except (KeyError, ValueError) as e:
                logger.warning("Skipping malformed KEV entry", error=str(e))
        return results

    def sync(self) -> dict:
        """Full sync: fetch, parse, create new + update existing CVEs.
        Returns {"created": N, "updated": N}."""
        from iam.models import Folder
        from sec_intel.models import CVE

        raw = self.fetch()
        entries = self.parse(raw)
        kev_map = {e["cve_id"]: e for e in entries}

        # Update existing CVEs
        existing = CVE.objects.filter(ref_id__in=kev_map.keys())
        existing_ids = set()
        to_update = []
        for cve in existing:
            existing_ids.add(cve.ref_id)
            cve.is_kev = True
            cve.kev_date_added = kev_map[cve.ref_id]["date_added"]
            to_update.append(cve)

        if to_update:
            CVE.objects.bulk_update(
                to_update, ["is_kev", "kev_date_added"], batch_size=1000
            )

        # Create new CVEs for KEV entries not yet in DB
        root_folder = Folder.get_root_folder()
        to_create = []
        for cve_id, entry in kev_map.items():
            if cve_id not in existing_ids:
                to_create.append(
                    CVE(
                        ref_id=cve_id,
                        name=entry["name"],
                        description=entry["description"],
                        is_kev=True,
                        kev_date_added=entry["date_added"],
                        folder=root_folder,
                    )
                )

        if to_create:
            CVE.objects.bulk_create(to_create, batch_size=1000, ignore_conflicts=True)

        return {"created": len(to_create), "updated": len(to_update)}


# --- EPSS Feed ---

EPSS_URL = "https://epss.cyentia.com/epss_scores-current.csv.gz"


class EPSSFeed:
    def __init__(self, file_path: Optional[Path] = None):
        self.file_path = file_path

    def fetch(self) -> bytes:
        """Fetch gzipped CSV from Cyentia or read local file."""
        if self.file_path:
            return self.file_path.read_bytes()
        resp = httpx.get(EPSS_URL, timeout=_get_timeout(), follow_redirects=True)
        resp.raise_for_status()
        return resp.content

    def parse(self, raw_gz: bytes) -> list[dict]:
        """Decompress and parse CSV. Returns list of {cve_id, epss, percentile}."""
        text = gzip.decompress(raw_gz).decode("utf-8")
        # Skip comment lines (EPSS CSV starts with a # comment line)
        lines = [line for line in text.splitlines() if not line.startswith("#")]
        reader = csv.DictReader(io.StringIO("\n".join(lines)))
        results = []
        for row in reader:
            cve_id = row.get("cve", "")
            if not cve_id.startswith("CVE-"):
                continue
            try:
                results.append(
                    {
                        "cve_id": cve_id,
                        "epss": Decimal(row["epss"]),
                        "percentile": Decimal(row["percentile"]),
                    }
                )
            except (KeyError, ValueError) as e:
                logger.warning(
                    "Skipping malformed EPSS entry", cve=cve_id, error=str(e)
                )
        return results

    def sync(self) -> int:
        """Full sync: fetch, parse, bulk-update existing CVEs."""
        from sec_intel.models import CVE

        raw = self.fetch()
        entries = self.parse(raw)
        epss_map = {e["cve_id"]: e for e in entries}

        cves = CVE.objects.filter(ref_id__in=epss_map.keys())
        to_update = []
        for cve in cves:
            data = epss_map[cve.ref_id]
            cve.epss_score = data["epss"]
            cve.epss_percentile = data["percentile"]
            to_update.append(cve)

        if to_update:
            CVE.objects.bulk_update(
                to_update, ["epss_score", "epss_percentile"], batch_size=1000
            )
        return len(to_update)


# --- NVD Single-CVE Lookup ---

NVD_CVE_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"


class NVDFeed:
    @staticmethod
    def fetch_cve(cve_id: str) -> Optional[dict]:
        """Fetch a single CVE from NVD API. Returns None on any failure."""
        try:
            resp = httpx.get(
                NVD_CVE_URL,
                params={"cveId": cve_id},
                timeout=_get_timeout(),
            )
            resp.raise_for_status()
            return resp.json()
        except Exception:
            logger.warning("NVD lookup failed", cve_id=cve_id, exc_info=True)
            return None

    @staticmethod
    def parse_cve(raw: dict) -> dict:
        """Extract fields from NVD 2.0 response."""
        vulns = raw.get("vulnerabilities", [])
        if not vulns:
            return {}
        cve_data = vulns[0].get("cve", {})
        result = {}

        # CVE ID as ref_id and name
        cve_id = cve_data.get("id")
        if cve_id:
            result["ref_id"] = cve_id
            result["name"] = cve_id

        # Published date
        pub = cve_data.get("published")
        if pub:
            try:
                result["published_date"] = datetime.fromisoformat(
                    pub.replace("Z", "+00:00")
                ).date()
            except ValueError:
                pass

        # Description (English)
        for desc in cve_data.get("descriptions", []):
            if desc.get("lang") == "en":
                result["description"] = desc.get("value", "")
                break

        # CVSS — prefer v3.1, fall back to v3.0, then v2.0
        metrics = cve_data.get("metrics", {})
        for key in ["cvssMetricV31", "cvssMetricV30", "cvssMetricV2"]:
            if key in metrics and metrics[key]:
                cvss = metrics[key][0].get("cvssData", {})
                score = cvss.get("baseScore")
                if score is not None:
                    result["cvss_base_score"] = Decimal(str(score))
                vector = cvss.get("vectorString")
                if vector:
                    result["cvss_vector"] = vector
                break

        # References (URLs)
        refs = cve_data.get("references", [])
        if refs:
            result["references"] = [
                {"url": r.get("url"), "source": r.get("source", "")}
                for r in refs
                if r.get("url")
            ]

        return result

    @staticmethod
    def enrich_cve(cve_instance) -> bool:
        """Fetch NVD data and update the given CVE instance. Returns True if enriched."""
        settings = get_feed_settings()
        if not settings.get("nvd_enrich_enabled", False):
            return False

        raw = NVDFeed.fetch_cve(cve_instance.ref_id)
        if raw is None:
            return False

        fields = NVDFeed.parse_cve(raw)
        if not fields:
            return False

        update_fields = []
        for k, v in fields.items():
            current = getattr(cve_instance, k, None)
            if current in (None, "", 0):
                setattr(cve_instance, k, v)
                update_fields.append(k)

        if update_fields:
            cve_instance.save(update_fields=update_fields)
        return bool(update_fields)


# --- CWE Feed ---

CWE_URL = "https://cwe.mitre.org/data/xml/cwec_latest.xml.zip"


class CWEFeed:
    def __init__(self, file_path: Optional[Path] = None):
        self.file_path = file_path

    def fetch(self) -> bytes:
        """Fetch zipped CWE JSON from MITRE or read local file."""
        if self.file_path:
            return self.file_path.read_bytes()
        resp = httpx.get(CWE_URL, timeout=_get_timeout(), follow_redirects=True)
        resp.raise_for_status()
        return resp.content

    def parse(self, raw_zip: bytes) -> list[dict]:
        """Extract CWE entries from zipped XML."""
        import zipfile
        import xml.etree.ElementTree as ET

        with zipfile.ZipFile(io.BytesIO(raw_zip)) as zf:
            xml_name = [n for n in zf.namelist() if n.endswith(".xml")][0]
            tree = ET.parse(zf.open(xml_name))

        root = tree.getroot()
        ns = {"cwe": root.tag.split("}")[0] + "}"} if "}" in root.tag else {"cwe": ""}
        prefix = ns["cwe"]

        results = []
        for weakness in root.iter(f"{prefix}Weakness"):
            cwe_id = weakness.get("ID")
            if not cwe_id:
                continue

            name = weakness.get("Name", f"CWE-{cwe_id}")

            description = ""
            desc_el = weakness.find(f"{prefix}Description")
            if desc_el is not None and desc_el.text:
                description = desc_el.text.strip()
            if not description:
                ext_el = weakness.find(f"{prefix}Extended_Description")
                if ext_el is not None:
                    description = "".join(ext_el.itertext()).strip()

            results.append(
                {
                    "cwe_id": f"CWE-{cwe_id}",
                    "name": name,
                    "description": description,
                }
            )
        return results

    def sync(self) -> dict:
        """Full sync: fetch, parse, create new + update existing CWEs.
        Returns {"created": N, "updated": N}."""
        from iam.models import Folder
        from sec_intel.models import CWE

        raw = self.fetch()
        entries = self.parse(raw)
        cwe_map = {e["cwe_id"]: e for e in entries}

        # Update existing
        existing = CWE.objects.filter(ref_id__in=cwe_map.keys())
        existing_ids = set()
        to_update = []
        for cwe in existing:
            existing_ids.add(cwe.ref_id)
            entry = cwe_map[cwe.ref_id]
            changed = False
            if not cwe.name and entry["name"]:
                cwe.name = entry["name"]
                changed = True
            if not cwe.description and entry["description"]:
                cwe.description = entry["description"]
                changed = True
            if changed:
                to_update.append(cwe)

        if to_update:
            CWE.objects.bulk_update(to_update, ["name", "description"], batch_size=1000)

        # Create new
        root_folder = Folder.get_root_folder()
        to_create = []
        for cwe_id, entry in cwe_map.items():
            if cwe_id not in existing_ids:
                to_create.append(
                    CWE(
                        ref_id=cwe_id,
                        name=entry["name"],
                        description=entry["description"],
                        folder=root_folder,
                    )
                )

        if to_create:
            CWE.objects.bulk_create(to_create, batch_size=1000, ignore_conflicts=True)

        return {"created": len(to_create), "updated": len(to_update)}
