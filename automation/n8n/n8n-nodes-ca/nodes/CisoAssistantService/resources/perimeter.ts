import type { INodeProperties } from "n8n-workflow";

export const operations: INodeProperties = {
  displayName: "Operation",
  name: "operation",
  type: "options",
  noDataExpression: true,
  displayOptions: {
    show: {
      resource: ["perimeter"],
    },
  },
  options: [
    {
      name: "Create",
      value: "create",
      description: "Create a new perimeter",
      action: "Create a perimeter",
    },
    {
      name: "Get",
      value: "get",
      description: "Get a perimeter by ID",
      action: "Get a perimeter",
    },
    {
      name: "Get by Name",
      value: "getByName",
      description: "Get a perimeter by its name",
      action: "Get perimeter by name",
    },
    {
      name: "Get Many",
      value: "list",
      description: "Get all perimeters",
      action: "Get many perimeters",
    },
  ],
  default: "create",
};

export const fields: INodeProperties[] = [
  {
    displayName: "Perimeter Name",
    name: "perimeterName",
    type: "string",
    displayOptions: {
      show: {
        resource: ["perimeter"],
        operation: ["create", "getByName"],
      },
    },
    default: "",
    placeholder: "My Security Perimeter",
    description: "The name of the perimeter (case sensitive for getByName)",
    required: true,
  },
  {
    displayName: "Folder ID",
    name: "folderId",
    type: "string",
    displayOptions: {
      show: {
        resource: ["perimeter"],
        operation: ["getByName"],
      },
    },
    default: "",
    placeholder: "domain-uuid-here",
    description: "The UUID of the folder (domain) to search within",
    required: true,
  },
  {
    displayName: "Perimeter Description",
    name: "perimeterDescription",
    type: "string",
    typeOptions: {
      rows: 3,
    },
    displayOptions: {
      show: {
        resource: ["perimeter"],
        operation: ["create"],
      },
    },
    default: "",
    placeholder: "Description of the security perimeter",
    description: "The description of the perimeter",
  },
  {
    displayName: "Folder ID",
    name: "folderId",
    type: "string",
    displayOptions: {
      show: {
        resource: ["perimeter"],
        operation: ["create"],
      },
    },
    default: "",
    placeholder: "domain-uuid-here",
    description: "The UUID of the folder (domain) this perimeter belongs to",
    required: true,
  },
];
