import type { INodeProperties } from "n8n-workflow";

export const operations: INodeProperties = {
  displayName: "Operation",
  name: "operation",
  type: "options",
  noDataExpression: true,
  displayOptions: {
    show: {
      resource: ["asset"],
    },
  },
  options: [
    {
      name: "Create",
      value: "create",
      description: "Create a new asset",
      action: "Create an asset",
    },
    {
      name: "Get",
      value: "get",
      description: "Get an asset by ID",
      action: "Get an asset",
    },
    {
      name: "Get by Name",
      value: "getByName",
      description: "Get an asset by its name (case-sensitive)",
      action: "Get asset by name",
    },
    {
      name: "Get Many",
      value: "list",
      description: "Get all assets",
      action: "Get many assets",
    },
    {
      name: "Update",
      value: "update",
      description: "Update an existing asset",
      action: "Update asset",
    },
  ],
  default: "create",
};

export const fields: INodeProperties[] = [
  {
    displayName: "Asset Name",
    name: "assetName",
    type: "string",
    displayOptions: {
      show: {
        resource: ["asset"],
        operation: ["create", "getByName"],
      },
    },
    default: "",
    placeholder: "Web Server",
    description: "The name of the asset (case-sensitive)",
    required: true,
  },
  {
    displayName: "Folder UUID",
    name: "folderId",
    type: "string",
    displayOptions: {
      show: {
        resource: ["asset"],
        operation: ["create"],
      },
    },
    default: "",
    placeholder: "domain-uuid-here",
    description: "The UUID of the folder (domain) this asset belongs to",
    required: true,
  },
  {
    displayName: "Folder UUID (Optional)",
    name: "folderId",
    type: "string",
    displayOptions: {
      show: {
        resource: ["asset"],
        operation: ["getByName"],
      },
    },
    default: "",
    placeholder: "domain-uuid-here",
    description: "The UUID of the folder (domain) to filter by",
  },
  {
    displayName: "Asset UUID",
    name: "assetId",
    type: "string",
    displayOptions: {
      show: {
        resource: ["asset"],
        operation: ["update"],
      },
    },
    default: "",
    placeholder: "asset-uuid-here",
    description: "The UUID of the asset to update",
    required: true,
  },
  {
    displayName: "Asset Description",
    name: "assetDescription",
    type: "string",
    typeOptions: {
      rows: 3,
    },
    displayOptions: {
      show: {
        resource: ["asset"],
        operation: ["create", "update"],
      },
    },
    default: "",
    placeholder: "Description of the asset",
    description: "The description of the asset",
  },
  {
    displayName: "Asset Type",
    name: "assetType",
    type: "options",
    displayOptions: {
      show: {
        resource: ["asset"],
        operation: ["create", "update"],
      },
    },
    options: [
      {
        name: "Primary",
        value: "PR",
      },
      {
        name: "Support",
        value: "SP",
      },
    ],
    default: "PR",
    description: "The type of the asset",
  },
  {
    displayName: "Asset Name (Update)",
    name: "assetNameUpdate",
    type: "string",
    displayOptions: {
      show: {
        resource: ["asset"],
        operation: ["update"],
      },
    },
    default: "",
    placeholder: "New Asset Name",
    description: "New name for the asset (optional)",
  },
];
