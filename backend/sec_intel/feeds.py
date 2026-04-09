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
        """Extract list of {cve_id, date_added} from KEV JSON."""
        results = []
        for vuln in raw.get("vulnerabilities", []):
            try:
                results.append(
                    {
                        "cve_id": vuln["cveID"],
                        "date_added": datetime.strptime(
                            vuln["dateAdded"], "%Y-%m-%d"
                        ).date(),
                    }
                )
            except (KeyError, ValueError) as e:
                logger.warning("Skipping malformed KEV entry", error=str(e))
        return results

    def sync(self) -> int:
        """Full sync: fetch, parse, bulk-update existing CVEs. Returns count updated."""
        from sec_intel.models import CVE

        raw = self.fetch()
        entries = self.parse(raw)
        kev_map = {e["cve_id"]: e["date_added"] for e in entries}

        cves = CVE.objects.filter(ref_id__in=kev_map.keys())
        to_update = []
        for cve in cves:
            cve.is_kev = True
            cve.kev_date_added = kev_map[cve.ref_id]
            to_update.append(cve)

        if to_update:
            CVE.objects.bulk_update(
                to_update, ["is_kev", "kev_date_added"], batch_size=1000
            )
        return len(to_update)


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
