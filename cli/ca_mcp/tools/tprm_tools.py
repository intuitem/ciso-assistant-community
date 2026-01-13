"""TPRM (Third-Party Risk Management) MCP tools for CISO Assistant"""

from ..client import (
    make_get_request,
    make_post_request,
    make_patch_request,
    get_paginated_results,
)
from ..resolvers import (
    resolve_folder_id,
    resolve_entity_id,
    resolve_solution_id,
    resolve_contract_id,
    resolve_entity_assessment_id,
    resolve_representative_id,
)
from ..config import GLOBAL_FOLDER_ID
from ..utils.response_formatter import (
    success_response,
    error_response,
    empty_response,
    http_error_response,
)


# ============================================================================
# READ TOOLS
# ============================================================================


async def get_entities(
    folder: str = None,
    is_active: bool = None,
    country: str = None,
):
    """List third-party entities (vendors, suppliers, partners)

    Args:
        folder: Folder ID/name filter
        is_active: Filter by active status
        country: Filter by country code (e.g. "US", "FR")
    """
    try:
        params = {}
        filters = {}

        if folder:
            params["folder"] = resolve_folder_id(folder)
            filters["folder"] = folder

        if is_active is not None:
            params["is_active"] = str(is_active).lower()
            filters["is_active"] = is_active

        if country:
            params["country"] = country
            filters["country"] = country

        res = make_get_request("/entities/", params=params)

        if res.status_code != 200:
            return http_error_response(res.status_code, res.text)

        data = res.json()
        entities = get_paginated_results(data)

        if not entities:
            return empty_response("entities", filters)

        result = f"Found {len(entities)} entities"
        if filters:
            result += f" ({', '.join(f'{k}={v}' for k, v in filters.items())})"
        result += "\n\n"
        result += "|ID|Ref|Name|Active|Country|Dependency|Maturity|Trust|Folder|\n"
        result += "|---|---|---|---|---|---|---|---|---|\n"

        for entity in entities:
            entity_id = entity.get("id", "N/A")
            ref_id = entity.get("ref_id") or "N/A"
            name = entity.get("name", "N/A")
            is_active_val = "Yes" if entity.get("is_active") else "No"
            country_val = entity.get("country") or "N/A"
            dependency = entity.get("default_dependency", 0)
            maturity = entity.get("default_maturity", 1)
            trust = entity.get("default_trust", 1)
            folder_name = (entity.get("folder") or {}).get("str", "N/A")

            result += f"|{entity_id}|{ref_id}|{name}|{is_active_val}|{country_val}|{dependency}|{maturity}|{trust}|{folder_name}|\n"

        return success_response(
            result,
            "get_entities",
            "Use this table to identify entity IDs for TPRM assessments",
        )
    except Exception as e:
        return error_response(
            "Internal Error",
            str(e),
            "Report this error to the user",
            retry_allowed=False,
        )


async def get_entity_assessments(
    folder: str = None,
    entity: str = None,
    status: str = None,
    conclusion: str = None,
):
    """List third-party entity assessments

    Args:
        folder: Folder ID/name filter
        entity: Entity ID/name filter
        status: Status filter (planned, in_progress, in_review, done, deprecated)
        conclusion: Conclusion filter (blocker, warning, ok, not_applicable)
    """
    try:
        params = {}
        filters = {}

        if folder:
            params["folder"] = resolve_folder_id(folder)
            filters["folder"] = folder

        if entity:
            params["entity"] = resolve_entity_id(entity)
            filters["entity"] = entity

        if status:
            params["status"] = status
            filters["status"] = status

        if conclusion:
            params["conclusion"] = conclusion
            filters["conclusion"] = conclusion

        res = make_get_request("/entity-assessments/", params=params)

        if res.status_code != 200:
            return http_error_response(res.status_code, res.text)

        data = res.json()
        assessments = get_paginated_results(data)

        if not assessments:
            return empty_response("entity assessments", filters)

        result = f"Found {len(assessments)} entity assessments"
        if filters:
            result += f" ({', '.join(f'{k}={v}' for k, v in filters.items())})"
        result += "\n\n"
        result += "|ID|Name|Entity|Status|Conclusion|Criticality|Perimeter|Folder|\n"
        result += "|---|---|---|---|---|---|---|---|\n"

        for assessment in assessments:
            assessment_id = assessment.get("id", "N/A")
            name = assessment.get("name", "N/A")
            entity_name = (assessment.get("entity") or {}).get("str", "N/A")
            status_val = assessment.get("status", "N/A")
            conclusion_val = assessment.get("conclusion") or "N/A"
            criticality = assessment.get("criticality", 0)
            perimeter = (assessment.get("perimeter") or {}).get("str", "N/A")
            folder_name = (assessment.get("folder") or {}).get("str", "N/A")

            result += f"|{assessment_id}|{name}|{entity_name}|{status_val}|{conclusion_val}|{criticality}|{perimeter}|{folder_name}|\n"

        return success_response(
            result,
            "get_entity_assessments",
            "Use this table to review third-party risk assessments",
        )
    except Exception as e:
        return error_response(
            "Internal Error",
            str(e),
            "Report this error to the user",
            retry_allowed=False,
        )


async def get_representatives(entity: str = None):
    """List representatives (contacts) for third-party entities

    Args:
        entity: Entity ID/name filter
    """
    try:
        params = {}
        filters = {}

        if entity:
            params["entity"] = resolve_entity_id(entity)
            filters["entity"] = entity

        res = make_get_request("/representatives/", params=params)

        if res.status_code != 200:
            return http_error_response(res.status_code, res.text)

        data = res.json()
        representatives = get_paginated_results(data)

        if not representatives:
            return empty_response("representatives", filters)

        result = f"Found {len(representatives)} representatives"
        if filters:
            result += f" ({', '.join(f'{k}={v}' for k, v in filters.items())})"
        result += "\n\n"
        result += "|ID|Email|First Name|Last Name|Role|Entity|Phone|\n"
        result += "|---|---|---|---|---|---|---|\n"

        for rep in representatives:
            rep_id = rep.get("id", "N/A")
            email = rep.get("email", "N/A")
            first_name = rep.get("first_name") or "N/A"
            last_name = rep.get("last_name") or "N/A"
            role = rep.get("role") or "N/A"
            entity_name = (rep.get("entity") or {}).get("str", "N/A")
            phone = rep.get("phone") or "N/A"

            result += f"|{rep_id}|{email}|{first_name}|{last_name}|{role}|{entity_name}|{phone}|\n"

        return success_response(
            result,
            "get_representatives",
            "Use this table to identify contacts for third-party entities",
        )
    except Exception as e:
        return error_response(
            "Internal Error",
            str(e),
            "Report this error to the user",
            retry_allowed=False,
        )


async def get_solutions(
    provider_entity: str = None,
    is_active: bool = None,
    criticality: int = None,
):
    """List solutions (products/services) from third-party entities

    Args:
        provider_entity: Provider entity ID/name filter
        is_active: Filter by active status
        criticality: Filter by criticality level (0-4)
    """
    try:
        params = {}
        filters = {}

        if provider_entity:
            params["provider_entity"] = resolve_entity_id(provider_entity)
            filters["provider_entity"] = provider_entity

        if is_active is not None:
            params["is_active"] = str(is_active).lower()
            filters["is_active"] = is_active

        if criticality is not None:
            params["criticality"] = criticality
            filters["criticality"] = criticality

        res = make_get_request("/solutions/", params=params)

        if res.status_code != 200:
            return http_error_response(res.status_code, res.text)

        data = res.json()
        solutions = get_paginated_results(data)

        if not solutions:
            return empty_response("solutions", filters)

        result = f"Found {len(solutions)} solutions"
        if filters:
            result += f" ({', '.join(f'{k}={v}' for k, v in filters.items())})"
        result += "\n\n"
        result += "|ID|Ref|Name|Active|Criticality|Provider|Recipient|\n"
        result += "|---|---|---|---|---|---|---|\n"

        for solution in solutions:
            solution_id = solution.get("id", "N/A")
            ref_id = solution.get("ref_id") or "N/A"
            name = solution.get("name", "N/A")
            is_active_val = "Yes" if solution.get("is_active") else "No"
            criticality_val = solution.get("criticality", 0)
            provider = (solution.get("provider_entity") or {}).get("str", "N/A")
            recipient = (solution.get("recipient_entity") or {}).get("str", "N/A")

            result += f"|{solution_id}|{ref_id}|{name}|{is_active_val}|{criticality_val}|{provider}|{recipient}|\n"

        return success_response(
            result,
            "get_solutions",
            "Use this table to identify third-party solutions/services",
        )
    except Exception as e:
        return error_response(
            "Internal Error",
            str(e),
            "Report this error to the user",
            retry_allowed=False,
        )


async def get_contracts(
    folder: str = None,
    provider_entity: str = None,
    beneficiary_entity: str = None,
    status: str = None,
):
    """List contracts with third-party entities

    Args:
        folder: Folder ID/name filter
        provider_entity: Provider entity ID/name filter
        beneficiary_entity: Beneficiary entity ID/name filter
        status: Status filter (draft, active, expired, terminated)
    """
    try:
        params = {}
        filters = {}

        if folder:
            params["folder"] = resolve_folder_id(folder)
            filters["folder"] = folder

        if provider_entity:
            params["provider_entity"] = resolve_entity_id(provider_entity)
            filters["provider_entity"] = provider_entity

        if beneficiary_entity:
            params["beneficiary_entity"] = resolve_entity_id(beneficiary_entity)
            filters["beneficiary_entity"] = beneficiary_entity

        if status:
            params["status"] = status
            filters["status"] = status

        res = make_get_request("/contracts/", params=params)

        if res.status_code != 200:
            return http_error_response(res.status_code, res.text)

        data = res.json()
        contracts = get_paginated_results(data)

        if not contracts:
            return empty_response("contracts", filters)

        result = f"Found {len(contracts)} contracts"
        if filters:
            result += f" ({', '.join(f'{k}={v}' for k, v in filters.items())})"
        result += "\n\n"
        result += "|ID|Ref|Name|Status|Provider|Beneficiary|Start|End|Currency|Annual Expense|\n"
        result += "|---|---|---|---|---|---|---|---|---|---|\n"

        for contract in contracts:
            contract_id = contract.get("id", "N/A")
            ref_id = contract.get("ref_id") or "N/A"
            name = contract.get("name", "N/A")
            status_val = contract.get("status", "N/A")
            provider = (contract.get("provider_entity") or {}).get("str", "N/A")
            beneficiary = (contract.get("beneficiary_entity") or {}).get("str", "N/A")
            start_date = contract.get("start_date") or "N/A"
            end_date = contract.get("end_date") or "N/A"
            currency = contract.get("currency") or "N/A"
            annual_expense = contract.get("annual_expense") or "N/A"

            result += f"|{contract_id}|{ref_id}|{name}|{status_val}|{provider}|{beneficiary}|{start_date}|{end_date}|{currency}|{annual_expense}|\n"

        return success_response(
            result,
            "get_contracts",
            "Use this table to review third-party contracts",
        )
    except Exception as e:
        return error_response(
            "Internal Error",
            str(e),
            "Report this error to the user",
            retry_allowed=False,
        )


# ============================================================================
# WRITE TOOLS
# ============================================================================


async def create_entity(
    name: str,
    folder_id: str,
    description: str = "",
    ref_id: str = "",
    mission: str = "",
    reference_link: str = "",
    country: str = "",
    currency: str = "",
    default_dependency: int = 0,
    default_penetration: int = 0,
    default_maturity: int = 1,
    default_trust: int = 1,
) -> str:
    """Create a third-party entity (vendor, supplier, partner)

    Args:
        name: Entity name (required)
        folder_id: Folder ID/name (required)
        description: Description
        ref_id: Reference ID
        mission: Entity mission/purpose
        reference_link: URL reference
        country: Country code (e.g. "US", "FR")
        currency: Currency code (e.g. "USD", "EUR")
        default_dependency: Dependency level 0-4 (0=none, 4=critical)
        default_penetration: Penetration level 0-4
        default_maturity: Maturity level 1-4
        default_trust: Trust level 1-4
    """
    try:
        folder_id = resolve_folder_id(folder_id)

        payload = {
            "name": name,
            "folder": folder_id,
            "description": description,
            "is_active": True,
        }

        if ref_id:
            payload["ref_id"] = ref_id
        if mission:
            payload["mission"] = mission
        if reference_link:
            payload["reference_link"] = reference_link
        if country:
            payload["country"] = country
        if currency:
            payload["currency"] = currency

        payload["default_dependency"] = default_dependency
        payload["default_penetration"] = default_penetration
        payload["default_maturity"] = default_maturity
        payload["default_trust"] = default_trust

        res = make_post_request("/entities/", payload)

        if res.status_code == 201:
            entity = res.json()
            return success_response(
                f"Created entity: {entity.get('name')} (ID: {entity.get('id')})",
                "create_entity",
                "Entity created successfully. You can now create solutions, contracts, or assessments for this entity",
            )
        else:
            return http_error_response(res.status_code, res.text)
    except Exception as e:
        return error_response(
            "Internal Error",
            str(e),
            "Report this error to the user",
            retry_allowed=False,
        )


async def create_entity_assessment(
    name: str,
    entity_id: str,
    perimeter_id: str,
    description: str = "",
    status: str = "planned",
    criticality: int = 0,
    conclusion: str = None,
) -> str:
    """Create a third-party entity assessment

    Args:
        name: Assessment name (required)
        entity_id: Entity ID/name (required)
        perimeter_id: Perimeter ID/name (required)
        description: Description
        status: planned | in_progress | in_review | done | deprecated
        criticality: Criticality level (0-4)
        conclusion: blocker | warning | ok | not_applicable
    """
    try:
        from ..resolvers import resolve_perimeter_id

        entity_id = resolve_entity_id(entity_id)
        perimeter_id = resolve_perimeter_id(perimeter_id)

        payload = {
            "name": name,
            "entity": entity_id,
            "perimeter": perimeter_id,
            "description": description,
            "status": status,
            "criticality": criticality,
        }

        if conclusion:
            payload["conclusion"] = conclusion

        res = make_post_request("/entity-assessments/", payload)

        if res.status_code == 201:
            assessment = res.json()
            return success_response(
                f"Created entity assessment: {assessment.get('name')} (ID: {assessment.get('id')})",
                "create_entity_assessment",
                "Entity assessment created successfully",
            )
        else:
            return http_error_response(res.status_code, res.text)
    except Exception as e:
        return error_response(
            "Internal Error",
            str(e),
            "Report this error to the user",
            retry_allowed=False,
        )


async def create_representative(
    email: str,
    entity_id: str,
    first_name: str = "",
    last_name: str = "",
    phone: str = "",
    role: str = "",
    description: str = "",
    ref_id: str = "",
) -> str:
    """Create a representative (contact) for a third-party entity

    Args:
        email: Email address (required, unique)
        entity_id: Entity ID/name (required)
        first_name: First name
        last_name: Last name
        phone: Phone number
        role: Role/position
        description: Description
        ref_id: Reference ID
    """
    try:
        entity_id = resolve_entity_id(entity_id)

        payload = {
            "email": email,
            "entity": entity_id,
        }

        if first_name:
            payload["first_name"] = first_name
        if last_name:
            payload["last_name"] = last_name
        if phone:
            payload["phone"] = phone
        if role:
            payload["role"] = role
        if description:
            payload["description"] = description
        if ref_id:
            payload["ref_id"] = ref_id

        res = make_post_request("/representatives/", payload)

        if res.status_code == 201:
            rep = res.json()
            return success_response(
                f"Created representative: {rep.get('email')} (ID: {rep.get('id')})",
                "create_representative",
                "Representative created successfully",
            )
        else:
            return http_error_response(res.status_code, res.text)
    except Exception as e:
        return error_response(
            "Internal Error",
            str(e),
            "Report this error to the user",
            retry_allowed=False,
        )


async def create_solution(
    name: str,
    provider_entity_id: str,
    description: str = "",
    ref_id: str = "",
    reference_link: str = "",
    criticality: int = 0,
    assets: list = None,
) -> str:
    """Create a solution (product/service) from a third-party entity

    Args:
        name: Solution name (required)
        provider_entity_id: Provider entity ID/name (required)
        description: Description
        ref_id: Reference ID
        reference_link: URL reference
        criticality: Criticality level (0-4)
        assets: List of asset IDs/names to link
    """
    try:
        from ..resolvers import resolve_asset_id

        provider_entity_id = resolve_entity_id(provider_entity_id)

        payload = {
            "name": name,
            "provider_entity": provider_entity_id,
            "description": description,
            "is_active": True,
            "criticality": criticality,
        }

        if ref_id:
            payload["ref_id"] = ref_id
        if reference_link:
            payload["reference_link"] = reference_link

        if assets:
            resolved_assets = []
            for asset in assets:
                resolved_asset_id = resolve_asset_id(asset)
                resolved_assets.append(resolved_asset_id)
            payload["assets"] = resolved_assets

        res = make_post_request("/solutions/", payload)

        if res.status_code == 201:
            solution = res.json()
            message = (
                f"Created solution: {solution.get('name')} (ID: {solution.get('id')})"
            )
            if assets:
                message += f"\n   Linked to {len(assets)} asset(s)"
            return success_response(
                message,
                "create_solution",
                "Solution created successfully. You can now link it to contracts",
            )
        else:
            return http_error_response(res.status_code, res.text)
    except Exception as e:
        return error_response(
            "Internal Error",
            str(e),
            "Report this error to the user",
            retry_allowed=False,
        )


async def create_contract(
    name: str,
    provider_entity_id: str,
    folder_id: str,
    description: str = "",
    ref_id: str = "",
    status: str = "draft",
    start_date: str = None,
    end_date: str = None,
    currency: str = "",
    annual_expense: float = None,
    solutions: list = None,
) -> str:
    """Create a contract with a third-party entity

    Args:
        name: Contract name (required)
        provider_entity_id: Provider entity ID/name (required)
        folder_id: Folder ID/name (required)
        description: Description
        ref_id: Reference ID
        status: draft | active | expired | terminated
        start_date: Start date YYYY-MM-DD
        end_date: End date YYYY-MM-DD
        currency: Currency code (e.g. "USD", "EUR")
        annual_expense: Annual expense amount
        solutions: List of solution IDs/names to link
    """
    try:
        provider_entity_id = resolve_entity_id(provider_entity_id)
        folder_id = resolve_folder_id(folder_id)

        payload = {
            "name": name,
            "provider_entity": provider_entity_id,
            "folder": folder_id,
            "description": description,
            "status": status,
        }

        if ref_id:
            payload["ref_id"] = ref_id
        if start_date:
            payload["start_date"] = start_date
        if end_date:
            payload["end_date"] = end_date
        if currency:
            payload["currency"] = currency
        if annual_expense is not None:
            payload["annual_expense"] = annual_expense

        if solutions:
            resolved_solutions = []
            for solution in solutions:
                resolved_solution_id = resolve_solution_id(solution)
                resolved_solutions.append(resolved_solution_id)
            payload["solutions"] = resolved_solutions

        res = make_post_request("/contracts/", payload)

        if res.status_code == 201:
            contract = res.json()
            message = (
                f"Created contract: {contract.get('name')} (ID: {contract.get('id')})"
            )
            if solutions:
                message += f"\n   Linked to {len(solutions)} solution(s)"
            return success_response(
                message,
                "create_contract",
                "Contract created successfully",
            )
        else:
            return http_error_response(res.status_code, res.text)
    except Exception as e:
        return error_response(
            "Internal Error",
            str(e),
            "Report this error to the user",
            retry_allowed=False,
        )


# ============================================================================
# UPDATE TOOLS
# ============================================================================


async def update_entity(
    entity_id: str,
    name: str = None,
    description: str = None,
    ref_id: str = None,
    is_active: bool = None,
    mission: str = None,
    reference_link: str = None,
    country: str = None,
    currency: str = None,
    default_dependency: int = None,
    default_penetration: int = None,
    default_maturity: int = None,
    default_trust: int = None,
) -> str:
    """Update a third-party entity

    Args:
        entity_id: Entity ID/name (required)
        name: New name
        description: New description
        ref_id: New reference ID
        is_active: Active status
        mission: Entity mission/purpose
        reference_link: URL reference
        country: Country code
        currency: Currency code
        default_dependency: Dependency level 0-4
        default_penetration: Penetration level 0-4
        default_maturity: Maturity level 1-4
        default_trust: Trust level 1-4
    """
    try:
        resolved_entity_id = resolve_entity_id(entity_id)

        payload = {}

        if name is not None:
            payload["name"] = name
        if description is not None:
            payload["description"] = description
        if ref_id is not None:
            payload["ref_id"] = ref_id
        if is_active is not None:
            payload["is_active"] = is_active
        if mission is not None:
            payload["mission"] = mission
        if reference_link is not None:
            payload["reference_link"] = reference_link
        if country is not None:
            payload["country"] = country
        if currency is not None:
            payload["currency"] = currency
        if default_dependency is not None:
            payload["default_dependency"] = default_dependency
        if default_penetration is not None:
            payload["default_penetration"] = default_penetration
        if default_maturity is not None:
            payload["default_maturity"] = default_maturity
        if default_trust is not None:
            payload["default_trust"] = default_trust

        if not payload:
            return "Error: No fields provided to update"

        res = make_patch_request(f"/entities/{resolved_entity_id}/", payload)

        if res.status_code == 200:
            entity = res.json()
            return success_response(
                f"Updated entity: {entity.get('name')} (ID: {entity.get('id')})",
                "update_entity",
                "Entity updated successfully",
            )
        else:
            return http_error_response(res.status_code, res.text)
    except Exception as e:
        return error_response(
            "Internal Error",
            str(e),
            "Report this error to the user",
            retry_allowed=False,
        )


async def update_entity_assessment(
    assessment_id: str,
    name: str = None,
    description: str = None,
    status: str = None,
    criticality: int = None,
    conclusion: str = None,
    dependency: int = None,
    maturity: int = None,
    trust: int = None,
    penetration: int = None,
) -> str:
    """Update a third-party entity assessment

    Args:
        assessment_id: Assessment ID/name (required)
        name: New name
        description: New description
        status: planned | in_progress | in_review | done | deprecated
        criticality: Criticality level (0-4)
        conclusion: blocker | warning | ok | not_applicable
        dependency: Dependency level (0-4)
        maturity: Maturity level (1-4)
        trust: Trust level (1-4)
        penetration: Penetration level (0-4)
    """
    try:
        resolved_assessment_id = resolve_entity_assessment_id(assessment_id)

        payload = {}

        if name is not None:
            payload["name"] = name
        if description is not None:
            payload["description"] = description
        if status is not None:
            payload["status"] = status
        if criticality is not None:
            payload["criticality"] = criticality
        if conclusion is not None:
            payload["conclusion"] = conclusion
        if dependency is not None:
            payload["dependency"] = dependency
        if maturity is not None:
            payload["maturity"] = maturity
        if trust is not None:
            payload["trust"] = trust
        if penetration is not None:
            payload["penetration"] = penetration

        if not payload:
            return "Error: No fields provided to update"

        res = make_patch_request(
            f"/entity-assessments/{resolved_assessment_id}/", payload
        )

        if res.status_code == 200:
            assessment = res.json()
            return success_response(
                f"Updated entity assessment: {assessment.get('name')} (ID: {assessment.get('id')})",
                "update_entity_assessment",
                "Entity assessment updated successfully",
            )
        else:
            return http_error_response(res.status_code, res.text)
    except Exception as e:
        return error_response(
            "Internal Error",
            str(e),
            "Report this error to the user",
            retry_allowed=False,
        )


async def update_representative(
    representative_id: str,
    first_name: str = None,
    last_name: str = None,
    phone: str = None,
    role: str = None,
    description: str = None,
    ref_id: str = None,
) -> str:
    """Update a representative (contact) for a third-party entity

    Args:
        representative_id: Representative ID/email (required)
        first_name: New first name
        last_name: New last name
        phone: New phone number
        role: New role/position
        description: New description
        ref_id: New reference ID
    """
    try:
        resolved_rep_id = resolve_representative_id(representative_id)

        payload = {}

        if first_name is not None:
            payload["first_name"] = first_name
        if last_name is not None:
            payload["last_name"] = last_name
        if phone is not None:
            payload["phone"] = phone
        if role is not None:
            payload["role"] = role
        if description is not None:
            payload["description"] = description
        if ref_id is not None:
            payload["ref_id"] = ref_id

        if not payload:
            return "Error: No fields provided to update"

        res = make_patch_request(f"/representatives/{resolved_rep_id}/", payload)

        if res.status_code == 200:
            rep = res.json()
            return success_response(
                f"Updated representative: {rep.get('email')} (ID: {rep.get('id')})",
                "update_representative",
                "Representative updated successfully",
            )
        else:
            return http_error_response(res.status_code, res.text)
    except Exception as e:
        return error_response(
            "Internal Error",
            str(e),
            "Report this error to the user",
            retry_allowed=False,
        )


async def update_solution(
    solution_id: str,
    name: str = None,
    description: str = None,
    ref_id: str = None,
    is_active: bool = None,
    reference_link: str = None,
    criticality: int = None,
    assets: list = None,
) -> str:
    """Update a solution (product/service)

    Args:
        solution_id: Solution ID/name (required)
        name: New name
        description: New description
        ref_id: New reference ID
        is_active: Active status
        reference_link: URL reference
        criticality: Criticality level (0-4)
        assets: List of asset IDs/names (replaces existing)
    """
    try:
        from ..resolvers import resolve_asset_id

        resolved_solution_id = resolve_solution_id(solution_id)

        payload = {}

        if name is not None:
            payload["name"] = name
        if description is not None:
            payload["description"] = description
        if ref_id is not None:
            payload["ref_id"] = ref_id
        if is_active is not None:
            payload["is_active"] = is_active
        if reference_link is not None:
            payload["reference_link"] = reference_link
        if criticality is not None:
            payload["criticality"] = criticality

        if assets is not None:
            resolved_assets = []
            for asset in assets:
                resolved_asset_id = resolve_asset_id(asset)
                resolved_assets.append(resolved_asset_id)
            payload["assets"] = resolved_assets

        if not payload:
            return "Error: No fields provided to update"

        res = make_patch_request(f"/solutions/{resolved_solution_id}/", payload)

        if res.status_code == 200:
            solution = res.json()
            return success_response(
                f"Updated solution: {solution.get('name')} (ID: {solution.get('id')})",
                "update_solution",
                "Solution updated successfully",
            )
        else:
            return http_error_response(res.status_code, res.text)
    except Exception as e:
        return error_response(
            "Internal Error",
            str(e),
            "Report this error to the user",
            retry_allowed=False,
        )


async def update_contract(
    contract_id: str,
    name: str = None,
    description: str = None,
    ref_id: str = None,
    status: str = None,
    start_date: str = None,
    end_date: str = None,
    currency: str = None,
    annual_expense: float = None,
    solutions: list = None,
) -> str:
    """Update a contract with a third-party entity

    Args:
        contract_id: Contract ID/name (required)
        name: New name
        description: New description
        ref_id: New reference ID
        status: draft | active | expired | terminated
        start_date: Start date YYYY-MM-DD
        end_date: End date YYYY-MM-DD
        currency: Currency code
        annual_expense: Annual expense amount
        solutions: List of solution IDs/names (replaces existing)
    """
    try:
        resolved_contract_id = resolve_contract_id(contract_id)

        payload = {}

        if name is not None:
            payload["name"] = name
        if description is not None:
            payload["description"] = description
        if ref_id is not None:
            payload["ref_id"] = ref_id
        if status is not None:
            payload["status"] = status
        if start_date is not None:
            payload["start_date"] = start_date
        if end_date is not None:
            payload["end_date"] = end_date
        if currency is not None:
            payload["currency"] = currency
        if annual_expense is not None:
            payload["annual_expense"] = annual_expense

        if solutions is not None:
            resolved_solutions = []
            for solution in solutions:
                resolved_solution_id = resolve_solution_id(solution)
                resolved_solutions.append(resolved_solution_id)
            payload["solutions"] = resolved_solutions

        if not payload:
            return "Error: No fields provided to update"

        res = make_patch_request(f"/contracts/{resolved_contract_id}/", payload)

        if res.status_code == 200:
            contract = res.json()
            return success_response(
                f"Updated contract: {contract.get('name')} (ID: {contract.get('id')})",
                "update_contract",
                "Contract updated successfully",
            )
        else:
            return http_error_response(res.status_code, res.text)
    except Exception as e:
        return error_response(
            "Internal Error",
            str(e),
            "Report this error to the user",
            retry_allowed=False,
        )
