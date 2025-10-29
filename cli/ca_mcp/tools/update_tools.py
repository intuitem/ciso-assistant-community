"""Update MCP tools for CISO Assistant"""

from ..client import make_get_request, make_patch_request, get_paginated_results
from ..resolvers import resolve_asset_id


async def update_asset(
    asset_id: str,
    name: str = None,
    description: str = None,
    asset_type: str = None,
    business_value: str = None,
    parent_assets: list = None,
) -> str:
    """Update an existing asset in CISO Assistant

    Args:
        asset_id: ID or name of the asset to update
        name: Optional new name for the asset
        description: Optional new description
        asset_type: Optional new type - "PR" for Primary or "SP" for Supporting
        business_value: Optional business value (e.g., "low", "medium", "high", "very_high")
        parent_assets: Optional list of parent asset IDs or names (can use asset names instead of UUIDs)
    """
    try:
        # Resolve asset name to ID if needed
        resolved_asset_id = resolve_asset_id(asset_id)

        # Build update payload with only provided fields
        payload = {}

        if name is not None:
            payload["name"] = name
        if description is not None:
            payload["description"] = description
        if asset_type is not None:
            payload["type"] = asset_type
        if business_value is not None:
            payload["business_value"] = business_value

        # Resolve parent asset names to IDs if provided
        if parent_assets is not None:
            resolved_parents = []
            for parent in parent_assets:
                resolved_parent_id = resolve_asset_id(parent)
                resolved_parents.append(resolved_parent_id)

            payload["parent_assets"] = resolved_parents

        if not payload:
            return "Error: No fields provided to update"

        res = make_patch_request(f"/assets/{resolved_asset_id}/", payload)

        if res.status_code == 200:
            asset = res.json()
            return f"✅ Asset updated successfully: {asset.get('name')} (ID: {asset.get('id')})"
        else:
            return f"Error updating asset: {res.status_code} - {res.text}"
    except Exception as e:
        return f"Error in update_asset: {str(e)}"
