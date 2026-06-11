from datetime import date

from django.core.management.base import BaseCommand

from core.models import Asset
from iam.models import Folder
from tprm.models import Contract, Entity, Solution


class Command(BaseCommand):
    help = "Populates DORA-specific test data for ROI export validation"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clean",
            action="store_true",
            help="Delete all DORA-TEST- prefixed data (does not create new data)",
        )
        parser.add_argument(
            "--fresh",
            action="store_true",
            help="Delete existing DORA test data and create fresh data",
        )

    def handle(self, *args, **options):
        clean = options["clean"]
        fresh = options["fresh"]

        if clean or fresh:
            self._clean()

        if clean and not fresh:
            self.stdout.write(
                self.style.SUCCESS("Clean completed. No new data created.")
            )
            return

        self._populate()

    def _clean(self):
        self.stdout.write("Cleaning existing DORA test data...")

        # Delete in reverse-dependency order
        deleted_contracts = Contract.objects.filter(
            ref_id__startswith="DORA-TEST-"
        ).count()
        Contract.objects.filter(ref_id__startswith="DORA-TEST-").delete()

        deleted_solutions = Solution.objects.filter(
            name__startswith="DORA-TEST-"
        ).count()
        Solution.objects.filter(name__startswith="DORA-TEST-").delete()

        deleted_assets = Asset.objects.filter(
            name__startswith="DORA-TEST-",
            ref_id__in=["F1", "F2"],
        ).count()
        Asset.objects.filter(
            name__startswith="DORA-TEST-",
            ref_id__in=["F1", "F2"],
        ).delete()

        deleted_entities = Entity.objects.filter(name__startswith="DORA-TEST-").count()
        Entity.objects.filter(name__startswith="DORA-TEST-").delete()

        # Revert main entity DORA fields
        main_entity = Entity.get_main_entity()
        if main_entity:
            main_entity.legal_identifiers = {}
            main_entity.country = ""
            main_entity.currency = ""
            main_entity.dora_entity_type = ""
            main_entity.dora_entity_hierarchy = ""
            main_entity.dora_competent_authority = ""
            main_entity.dora_assets_value = None
            main_entity.save()
            self.stdout.write("  Reverted main entity DORA fields to blank")

        self.stdout.write(
            self.style.SUCCESS(
                f"Cleaned {deleted_contracts} contracts, {deleted_solutions} solutions, "
                f"{deleted_assets} assets, {deleted_entities} entities"
            )
        )

    def _populate(self):
        root_folder = Folder.get_root_folder()
        main_entity = Entity.get_main_entity()
        if not main_entity:
            self.stdout.write(
                self.style.ERROR(
                    "No main entity found. Please create one first (builtin=True)."
                )
            )
            return

        # --- 1. Update main entity with DORA fields ---
        self.stdout.write("Updating main entity with DORA fields...")
        main_entity.legal_identifiers = {"LEI": "DORATEST00ENTITY0001"}
        main_entity.country = "BE"
        main_entity.currency = "EUR"
        main_entity.dora_entity_type = "eba_CT:x12"
        main_entity.dora_entity_hierarchy = "eba_RP:x53"
        main_entity.dora_competent_authority = "National Bank of Belgium (NBB)"
        main_entity.dora_assets_value = 5000000000.0
        main_entity.save()
        self.stdout.write(self.style.SUCCESS("  Main entity updated"))

        # --- 2. Subsidiary entity ---
        self.stdout.write("Creating subsidiary entity...")
        subsidiary = Entity.objects.create(
            name="DORA-TEST-Subsidiary Alpha",
            description="Subsidiary entity for DORA testing",
            folder=root_folder,
            builtin=False,
            parent_entity=main_entity,
            legal_identifiers={"LEI": "DORATEST00SUBSID0001"},
            country="BE",
            currency="EUR",
            dora_entity_type="eba_CT:x12",
            dora_entity_hierarchy="eba_RP:x56",
            dora_provider_person_type="eba_CT:x212",
        )
        self.stdout.write(self.style.SUCCESS(f"  Created: {subsidiary.name}"))

        # --- 3. Branch entity ---
        self.stdout.write("Creating branch entity...")
        branch = Entity.objects.create(
            name="DORA-TEST-Branch Brussels",
            description="Branch entity for DORA testing",
            folder=root_folder,
            builtin=False,
            parent_entity=main_entity,
            country="BE",
        )
        self.stdout.write(self.style.SUCCESS(f"  Created: {branch.name}"))

        # --- 4. Third-party provider entities ---
        self.stdout.write("Creating third-party provider entities...")
        providers_data = [
            {
                "name": "DORA-TEST-CloudCorp US",
                "description": "US-based cloud infrastructure provider",
                "legal_identifiers": {"LEI": "DORATEST00CLOUDC0001"},
                "country": "US",
                "dora_provider_person_type": "eba_CT:x212",
            },
            {
                "name": "DORA-TEST-SecureTech DE",
                "description": "German cybersecurity services provider",
                "legal_identifiers": {"LEI": "DORATEST00SECURT0001"},
                "country": "DE",
                "dora_provider_person_type": "eba_CT:x212",
            },
            {
                "name": "DORA-TEST-DataServices FR",
                "description": "French data analytics provider",
                "legal_identifiers": {"LEI": "DORATEST00DATAS00001"},
                "country": "FR",
                "dora_provider_person_type": "eba_CT:x212",
            },
        ]
        providers = []
        for pdata in providers_data:
            provider = Entity.objects.create(
                folder=root_folder,
                builtin=False,
                **pdata,
            )
            providers.append(provider)
            self.stdout.write(self.style.SUCCESS(f"  Created: {provider.name}"))

        # --- 5. Business functions (Assets) ---
        self.stdout.write("Creating business functions...")
        bf1 = Asset.objects.create(
            name="DORA-TEST-Core Banking Services",
            description="Core banking platform and transaction processing",
            folder=root_folder,
            ref_id="F1",
            type=Asset.Type.PRIMARY,
            is_business_function=True,
            dora_licenced_activity="eba_TA:x163",
            dora_criticality_assessment="eba_BT:x28",
            dora_criticality_justification=(
                "Core banking services are critical to the institution's operations. "
                "Disruption would directly impact customer transactions and regulatory compliance."
            ),
            dora_discontinuing_impact="eba_ZZ:x793",
            disaster_recovery_objectives={
                "objectives": {"rto": {"value": 4}, "rpo": {"value": 2}}
            },
        )
        bf2 = Asset.objects.create(
            name="DORA-TEST-Payment Processing",
            description="Payment processing and settlement services",
            folder=root_folder,
            ref_id="F2",
            type=Asset.Type.PRIMARY,
            is_business_function=True,
            dora_licenced_activity="eba_TA:x28",
            dora_criticality_assessment="eba_BT:x28",
            dora_criticality_justification=(
                "Payment processing is essential for daily operations and customer service. "
                "Outages would cause significant financial and reputational impact."
            ),
            dora_discontinuing_impact="eba_ZZ:x793",
            disaster_recovery_objectives={
                "objectives": {"rto": {"value": 4}, "rpo": {"value": 2}}
            },
        )
        business_functions = [bf1, bf2]
        for bf in business_functions:
            self.stdout.write(self.style.SUCCESS(f"  Created: {bf.name} ({bf.ref_id})"))

        # --- 6. Solutions ---
        self.stdout.write("Creating solutions...")
        solutions_data = [
            {
                "name": "DORA-TEST-Cloud Infrastructure Platform",
                "description": "IaaS platform for core banking workloads",
                "provider_entity": providers[0],
                "ref_id": "DORA-TEST-SOL-001",
                "dora_ict_service_type": "eba_TA:S17",
                "storage_of_data": True,
                "data_location_storage": "DE",
                "data_location_processing": "DE",
                "dora_data_sensitiveness": "eba_ZZ:x793",
                "dora_reliance_level": "eba_ZZ:x797",
                "dora_substitutability": "eba_ZZ:x960",
                "dora_non_substitutability_reason": "eba_ZZ:x964",
                "dora_has_exit_plan": "eba_BT:x28",
                "dora_reintegration_possibility": "eba_ZZ:x966",
                "dora_discontinuing_impact": "eba_ZZ:x793",
                "dora_alternative_providers_identified": "eba_BT:x28",
                "dora_alternative_providers": "AWS, Google Cloud",
                "business_functions": [bf1, bf2],
            },
            {
                "name": "DORA-TEST-Security Monitoring Suite",
                "description": "SOC and security monitoring services",
                "provider_entity": providers[1],
                "ref_id": "DORA-TEST-SOL-002",
                "dora_ict_service_type": "eba_TA:S04",
                "storage_of_data": True,
                "data_location_storage": "DE",
                "data_location_processing": "DE",
                "dora_data_sensitiveness": "eba_ZZ:x792",
                "dora_reliance_level": "eba_ZZ:x796",
                "dora_substitutability": "eba_ZZ:x961",
                "dora_has_exit_plan": "eba_BT:x28",
                "dora_reintegration_possibility": "eba_ZZ:x798",
                "dora_discontinuing_impact": "eba_ZZ:x792",
                "dora_alternative_providers_identified": "eba_BT:x28",
                "dora_alternative_providers": "CrowdStrike, Palo Alto Networks",
                "business_functions": [bf1],
            },
            {
                "name": "DORA-TEST-Data Analytics Platform",
                "description": "SaaS analytics and reporting platform",
                "provider_entity": providers[2],
                "ref_id": "DORA-TEST-SOL-003",
                "dora_ict_service_type": "eba_TA:S19",
                "storage_of_data": True,
                "data_location_storage": "FR",
                "data_location_processing": "FR",
                "dora_data_sensitiveness": "eba_ZZ:x791",
                "dora_reliance_level": "eba_ZZ:x795",
                "dora_substitutability": "eba_ZZ:x962",
                "dora_has_exit_plan": "eba_BT:x28",
                "dora_reintegration_possibility": "eba_ZZ:x798",
                "dora_discontinuing_impact": "eba_ZZ:x791",
                "dora_alternative_providers_identified": "eba_BT:x28",
                "dora_alternative_providers": "Tableau, Power BI",
                "business_functions": [bf2],
            },
        ]
        solutions = []
        for sdata in solutions_data:
            bfs = sdata.pop("business_functions")
            solution = Solution.objects.create(
                recipient_entity=main_entity,
                criticality=3,
                **sdata,
            )
            solution.assets.set(bfs)
            solutions.append(solution)
            self.stdout.write(self.style.SUCCESS(f"  Created: {solution.name}"))

        # --- 7. Contracts ---
        self.stdout.write("Creating contracts...")

        # Overarching contract with provider 1 (CloudCorp US)
        overarching_1 = Contract.objects.create(
            name="DORA-TEST-Cloud Services Master Agreement",
            description="Overarching contract for cloud infrastructure services",
            folder=root_folder,
            ref_id="DORA-TEST-CON-001",
            provider_entity=providers[0],
            beneficiary_entity=main_entity,
            dora_contractual_arrangement="eba_CO:x2",
            currency="EUR",
            annual_expense=1200000.0,
            start_date=date(2024, 1, 1),
            end_date=date(2027, 12, 31),
            governing_law_country="BE",
            status=Contract.Status.ACTIVE,
            notice_period_entity=90,
            notice_period_provider=90,
        )
        overarching_1.solutions.set([solutions[0]])
        self.stdout.write(self.style.SUCCESS(f"  Created: {overarching_1.name}"))

        # Subsequent contract under overarching_1
        subsequent_1 = Contract.objects.create(
            name="DORA-TEST-Cloud Support SLA",
            description="Subsequent contract for cloud support services",
            folder=root_folder,
            ref_id="DORA-TEST-CON-002",
            provider_entity=providers[0],
            beneficiary_entity=main_entity,
            dora_contractual_arrangement="eba_CO:x3",
            overarching_contract=overarching_1,
            currency="EUR",
            annual_expense=300000.0,
            start_date=date(2024, 3, 1),
            end_date=date(2027, 12, 31),
            governing_law_country="BE",
            status=Contract.Status.ACTIVE,
            notice_period_entity=60,
            notice_period_provider=60,
        )
        subsequent_1.solutions.set([solutions[0]])
        self.stdout.write(self.style.SUCCESS(f"  Created: {subsequent_1.name}"))

        # Standalone contract with provider 2 (SecureTech DE)
        standalone_1 = Contract.objects.create(
            name="DORA-TEST-Security Monitoring Contract",
            description="Standalone contract for security monitoring services",
            folder=root_folder,
            ref_id="DORA-TEST-CON-003",
            provider_entity=providers[1],
            beneficiary_entity=main_entity,
            dora_contractual_arrangement="eba_CO:x1",
            currency="EUR",
            annual_expense=450000.0,
            start_date=date(2024, 6, 1),
            end_date=date(2026, 5, 31),
            governing_law_country="DE",
            status=Contract.Status.ACTIVE,
            notice_period_entity=30,
            notice_period_provider=30,
        )
        standalone_1.solutions.set([solutions[1]])
        self.stdout.write(self.style.SUCCESS(f"  Created: {standalone_1.name}"))

        # Standalone contract with provider 3 (DataServices FR)
        standalone_2 = Contract.objects.create(
            name="DORA-TEST-Data Analytics Contract",
            description="Standalone contract for data analytics platform",
            folder=root_folder,
            ref_id="DORA-TEST-CON-004",
            provider_entity=providers[2],
            beneficiary_entity=main_entity,
            dora_contractual_arrangement="eba_CO:x1",
            currency="EUR",
            annual_expense=180000.0,
            start_date=date(2025, 1, 1),
            end_date=date(2027, 12, 31),
            governing_law_country="FR",
            status=Contract.Status.ACTIVE,
            notice_period_entity=60,
            notice_period_provider=60,
        )
        standalone_2.solutions.set([solutions[2]])
        self.stdout.write(self.style.SUCCESS(f"  Created: {standalone_2.name}"))

        # Intragroup contract with subsidiary as provider
        intragroup_1 = Contract.objects.create(
            name="DORA-TEST-Intragroup IT Services",
            description="Intragroup overarching contract for IT services from subsidiary",
            folder=root_folder,
            ref_id="DORA-TEST-CON-005",
            provider_entity=subsidiary,
            beneficiary_entity=main_entity,
            dora_contractual_arrangement="eba_CO:x2",
            is_intragroup=True,
            currency="EUR",
            annual_expense=600000.0,
            start_date=date(2024, 1, 1),
            end_date=date(2026, 12, 31),
            governing_law_country="BE",
            status=Contract.Status.ACTIVE,
            notice_period_entity=90,
            notice_period_provider=90,
        )
        self.stdout.write(self.style.SUCCESS(f"  Created: {intragroup_1.name}"))

        # --- Summary ---
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("DORA TEST DATA SUMMARY:")
        self.stdout.write("=" * 60)
        self.stdout.write(f"  Main entity updated:    1")
        self.stdout.write(f"  Subsidiary entities:    1")
        self.stdout.write(f"  Branch entities:        1")
        self.stdout.write(f"  Provider entities:      {len(providers)}")
        self.stdout.write(f"  Business functions:     {len(business_functions)}")
        self.stdout.write(f"  Solutions:              {len(solutions)}")
        self.stdout.write(f"  Contracts:              5")
        self.stdout.write("=" * 60)
        self.stdout.write(self.style.SUCCESS("DORA test data populated successfully!"))
