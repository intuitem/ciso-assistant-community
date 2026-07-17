"""
SCIM 2.0 schema and resource-type definitions exposed via /Schemas and
/ResourceTypes. These advertise which attributes and resources CISO Assistant
supports, so IdP provisioning connectors can configure themselves automatically.

Each schema dict closely follows RFC 7643 (Core Schema) — only the attributes we
actually accept/return are declared. Adding a new field to a viewset means
adding it here too so the IdP knows it exists.
"""

USER_SCHEMA = {
    "id": "urn:ietf:params:scim:schemas:core:2.0:User",
    "name": "User",
    "description": "User Account",
    "schemas": ["urn:ietf:params:scim:schemas:core:2.0:Schema"],
    "attributes": [
        {
            "name": "userName",
            "type": "string",
            "multiValued": False,
            "description": "Unique identifier for the User, typically the user's email.",
            "required": True,
            "caseExact": False,
            "mutability": "readWrite",
            "returned": "default",
            "uniqueness": "server",
        },
        {
            "name": "name",
            "type": "complex",
            "multiValued": False,
            "description": "The components of the user's real name.",
            "required": False,
            "mutability": "readWrite",
            "returned": "default",
            "uniqueness": "none",
            "subAttributes": [
                {
                    "name": "formatted",
                    "type": "string",
                    "multiValued": False,
                    "required": False,
                    "caseExact": False,
                    "mutability": "readWrite",
                    "returned": "default",
                    "uniqueness": "none",
                },
                {
                    "name": "familyName",
                    "type": "string",
                    "multiValued": False,
                    "required": False,
                    "caseExact": False,
                    "mutability": "readWrite",
                    "returned": "default",
                    "uniqueness": "none",
                },
                {
                    "name": "givenName",
                    "type": "string",
                    "multiValued": False,
                    "required": False,
                    "caseExact": False,
                    "mutability": "readWrite",
                    "returned": "default",
                    "uniqueness": "none",
                },
            ],
        },
        {
            "name": "emails",
            "type": "complex",
            "multiValued": True,
            "description": (
                "Email addresses for the user. CISO Assistant stores a single "
                "email per user; only the entry marked as primary is persisted "
                "(or the first entry if none is marked primary). Additional "
                "entries are accepted for SCIM compatibility but not retained."
            ),
            "required": False,
            "mutability": "readWrite",
            "returned": "default",
            "uniqueness": "none",
            "subAttributes": [
                {
                    "name": "value",
                    "type": "string",
                    "multiValued": False,
                    "required": False,
                    "caseExact": False,
                    "mutability": "readWrite",
                    "returned": "default",
                    "uniqueness": "none",
                },
                {
                    "name": "primary",
                    "type": "boolean",
                    "multiValued": False,
                    "required": False,
                    "mutability": "readWrite",
                    "returned": "default",
                },
                {
                    "name": "type",
                    "type": "string",
                    "multiValued": False,
                    "required": False,
                    "caseExact": False,
                    "mutability": "readWrite",
                    "returned": "default",
                    "uniqueness": "none",
                    "canonicalValues": ["work", "home", "other"],
                },
            ],
        },
        {
            "name": "active",
            "type": "boolean",
            "multiValued": False,
            "description": "A Boolean value indicating the user's administrative status.",
            "required": False,
            "mutability": "readWrite",
            "returned": "default",
        },
    ],
    "meta": {
        "resourceType": "Schema",
        "location": "/api/scim/v2/Schemas/urn:ietf:params:scim:schemas:core:2.0:User",
    },
}


GROUP_SCHEMA = {
    "id": "urn:ietf:params:scim:schemas:core:2.0:Group",
    "name": "Group",
    "description": "Group resource",
    "schemas": ["urn:ietf:params:scim:schemas:core:2.0:Schema"],
    "attributes": [
        {
            "name": "displayName",
            "type": "string",
            "multiValued": False,
            "description": "A human-readable name for the Group.",
            "required": True,
            "caseExact": False,
            "mutability": "readWrite",
            "returned": "default",
            "uniqueness": "none",
        },
        {
            "name": "members",
            "type": "complex",
            "multiValued": True,
            "description": "A list of members of the Group.",
            "required": False,
            "mutability": "readWrite",
            "returned": "default",
            "subAttributes": [
                {
                    "name": "value",
                    "type": "string",
                    "multiValued": False,
                    "description": "Identifier of the member of this Group.",
                    "required": False,
                    "caseExact": False,
                    "mutability": "immutable",
                    "returned": "default",
                    "uniqueness": "none",
                },
                {
                    "name": "$ref",
                    "type": "reference",
                    "multiValued": False,
                    "description": "The URI corresponding to a SCIM resource that is a member of this Group.",
                    "referenceTypes": ["User"],
                    "required": False,
                    "caseExact": False,
                    "mutability": "immutable",
                    "returned": "default",
                    "uniqueness": "none",
                },
                {
                    "name": "display",
                    "type": "string",
                    "multiValued": False,
                    "required": False,
                    "caseExact": False,
                    "mutability": "immutable",
                    "returned": "default",
                    "uniqueness": "none",
                },
            ],
        },
    ],
    "meta": {
        "resourceType": "Schema",
        "location": "/api/scim/v2/Schemas/urn:ietf:params:scim:schemas:core:2.0:Group",
    },
}


USER_RESOURCE_TYPE = {
    "schemas": ["urn:ietf:params:scim:schemas:core:2.0:ResourceType"],
    "id": "User",
    "name": "User",
    "endpoint": "/Users",
    "description": "User Account",
    "schema": "urn:ietf:params:scim:schemas:core:2.0:User",
    "meta": {
        "resourceType": "ResourceType",
        "location": "/api/scim/v2/ResourceTypes/User",
    },
}


GROUP_RESOURCE_TYPE = {
    "schemas": ["urn:ietf:params:scim:schemas:core:2.0:ResourceType"],
    "id": "Group",
    "name": "Group",
    "endpoint": "/Groups",
    "description": "Group",
    "schema": "urn:ietf:params:scim:schemas:core:2.0:Group",
    "meta": {
        "resourceType": "ResourceType",
        "location": "/api/scim/v2/ResourceTypes/Group",
    },
}


ALL_SCHEMAS = {
    USER_SCHEMA["id"]: USER_SCHEMA,
    GROUP_SCHEMA["id"]: GROUP_SCHEMA,
}

ALL_RESOURCE_TYPES = {
    USER_RESOURCE_TYPE["id"]: USER_RESOURCE_TYPE,
    GROUP_RESOURCE_TYPE["id"]: GROUP_RESOURCE_TYPE,
}
