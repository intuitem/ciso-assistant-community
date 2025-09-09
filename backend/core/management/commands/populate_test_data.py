from django.core.management.base import BaseCommand
from core.models import Asset
from iam.models import Folder, User
import random


class Command(BaseCommand):
    help = "Creates 5 folders (domains) with 30 assets each for testing"

    def handle(self, *args, **kwargs):
        # Asset types and categories for variety
        asset_types = [
            "server",
            "database",
            "application",
            "network",
            "workstation",
            "mobile",
        ]
        categories = ["critical", "important", "moderate", "low"]

        # Create folders first
        folders_to_create = []
        for i in range(1, 6):
            folder_name = f"Test Domain {i}"
            if not Folder.objects.filter(name=folder_name).exists():
                folders_to_create.append(
                    Folder(
                        name=folder_name,
                        description=f"Test domain {i} for development and testing purposes",
                        content_type=Folder.ContentType.DOMAIN,
                    )
                )

        # Bulk create folders
        if folders_to_create:
            Folder.objects.bulk_create(folders_to_create)
            self.stdout.write(f"Created {len(folders_to_create)} folders")

        # Get all test domain folders
        folders = Folder.objects.filter(name__startswith="Test Domain")

        # Prepare assets for bulk creation
        assets_to_create = []
        for folder in folders:
            domain_num = folder.name.split()[-1]  # Extract domain number

            for j in range(1, 31):
                asset_name = f"Asset-{domain_num}-{j:02d}"

                # Skip if asset already exists
                if not Asset.objects.filter(name=asset_name, folder=folder).exists():
                    # Add some variety to asset properties
                    asset_type = random.choice(asset_types)
                    category = random.choice(categories)
                    asset_model_type = random.choice(
                        [Asset.Type.PRIMARY, Asset.Type.SUPPORT]
                    )

                    assets_to_create.append(
                        Asset(
                            name=asset_name,
                            description=f"Test asset {j} in domain {domain_num} - {asset_type} ({category})",
                            folder=folder,
                            type=asset_model_type,
                            business_value=f"{category} importance asset",
                        )
                    )

        # Bulk create assets
        if assets_to_create:
            Asset.objects.bulk_create(assets_to_create, batch_size=100)
            self.stdout.write(f"Created {len(assets_to_create)} assets")

        # Summary
        total_folders = Folder.objects.filter(content_type="DO").count()
        total_assets = Asset.objects.count()

        self.stdout.write(
            self.style.SUCCESS(
                f"\nSummary: {total_folders} domains, {total_assets} total assets"
            )
        )
