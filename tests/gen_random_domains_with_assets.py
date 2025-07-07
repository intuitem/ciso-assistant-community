import requests
import json
import os
from dotenv import load_dotenv
import random
import string
from faker import Faker

# Load environment variables from .env file
load_dotenv()

# Initialize Faker for generating realistic data
fake = Faker()

# Read configuration from environment variables
API_URL = os.getenv("API_URL", "")
TOKEN = os.getenv("TOKEN", "")
VERIFY_CERTIFICATE = os.getenv("VERIFY_CERTIFICATE", "true").lower() in (
    "true",
    "1",
    "yes",
    "on",
)

# Domain and asset generation constants
DOMAIN_TYPES = [
    "Finance",
    "HR",
    "IT",
    "Operations",
    "Marketing",
    "Sales",
    "Legal",
    "Compliance",
    "Security",
    "R&D",
    "Manufacturing",
    "Logistics",
]

ASSET_TYPES = ["primary", "supporting"]

ASSET_CATEGORIES = ["Hardware", "Software", "Data", "Network", "Cloud", "Mobile", "IoT"]

CRITICALITY_LEVELS = ["Critical", "High", "Medium", "Low"]
ENVIRONMENTS = ["Production", "Development", "Testing", "Staging", "DR"]


def generate_domain_name():
    """Generate a realistic domain name"""
    prefix = random.choice(["Corporate", "Regional", "Global", "Local", "Digital"])
    domain_type = random.choice(DOMAIN_TYPES)
    suffix = random.choice(["Division", "Department", "Unit", "Center", "Hub"])
    return f"{prefix} {domain_type} {suffix}"


def generate_asset_name(asset_type):
    """Generate a realistic asset name"""
    env = random.choice(ENVIRONMENTS)
    identifier = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"{env}-{asset_type}-{identifier}"


def generate_asset_data():
    """Generate realistic asset data"""
    asset_type = random.choice(ASSET_TYPES)
    return {
        "name": generate_asset_name(asset_type),
        "description": fake.text(max_nb_chars=200),
    }


def generate_domain_data():
    """Generate realistic domain data"""
    return {
        "name": generate_domain_name(),
        "description": fake.text(max_nb_chars=300),
        "owner": fake.name(),
        "manager": fake.name(),
        "business_unit": random.choice(DOMAIN_TYPES),
        "location": fake.city(),
        "created_date": fake.date_between(
            start_date="-2y", end_date="today"
        ).isoformat(),
        "risk_level": random.choice(CRITICALITY_LEVELS),
        "compliance_requirements": [
            random.choice(["ISO 27001", "SOX", "GDPR", "HIPAA", "PCI DSS"])
            for _ in range(random.randint(1, 3))
        ],
    }


def create_domains_with_assets(num_domains=5, num_assets_per_domain=10):
    """Create N random domains, each with M random assets"""
    if not API_URL or not TOKEN:
        print("Error: API_URL and TOKEN must be configured in .env file")
        return

    headers = {"Authorization": f"Token {TOKEN}", "Content-Type": "application/json"}

    created_domains = []
    total_assets_created = 0

    try:
        for i in range(num_domains):
            # Generate domain data
            domain_data = generate_domain_data()

            # Create domain
            domain_url = f"{API_URL}/folders/"
            domain_response = requests.post(
                domain_url, headers=headers, json=domain_data, verify=VERIFY_CERTIFICATE
            )

            if domain_response.status_code not in [200, 201]:
                print(f"Error creating domain {i + 1}: {domain_response.status_code}")
                continue

            domain_result = domain_response.json()
            domain_id = domain_result.get("id")

            print(f"✓ Created domain: {domain_data['name']} (ID: {domain_id})")

            # Create assets for this domain
            domain_assets = []
            for j in range(num_assets_per_domain):
                asset_data = generate_asset_data()
                asset_data["folder"] = domain_id

                # Create asset
                asset_url = f"{API_URL}/assets/"
                asset_response = requests.post(
                    asset_url,
                    headers=headers,
                    json=asset_data,
                    verify=VERIFY_CERTIFICATE,
                )

                if asset_response.status_code not in [200, 201]:
                    print(
                        f"  Error creating asset {j + 1} for domain {i + 1}: {asset_response.status_code}"
                    )
                    continue

                asset_result = asset_response.json()
                domain_assets.append(asset_result)
                total_assets_created += 1

                print(f"  ✓ Created asset: {asset_data['name']}")

            created_domains.append({"domain": domain_result, "assets": domain_assets})

        print(f"\nSummary:")
        print(f"Total Domains Created: {len(created_domains)}")
        print(f"Total Assets Created: {total_assets_created}")

    except Exception as e:
        print(f"Error during creation process: {str(e)}")


if __name__ == "__main__":
    # Default values - change these as needed
    NUM_DOMAINS = 5
    NUM_ASSETS_PER_DOMAIN = 10

    print(f"Creating {NUM_DOMAINS} domains with {NUM_ASSETS_PER_DOMAIN} assets each...")
    create_domains_with_assets(NUM_DOMAINS, NUM_ASSETS_PER_DOMAIN)
