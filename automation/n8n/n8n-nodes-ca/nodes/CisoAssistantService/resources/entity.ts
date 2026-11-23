import type { INodeProperties } from "n8n-workflow";

export const operations: INodeProperties = {
  displayName: "Operation",
  name: "operation",
  type: "options",
  noDataExpression: true,
  displayOptions: {
    show: {
      resource: ["entity"],
    },
  },
  options: [
    {
      name: "Create",
      value: "create",
      description: "Create a new entity",
      action: "Create entity",
    },
    {
      name: "Get",
      value: "get",
      description: "Get an entity by ID",
      action: "Get an entity",
    },
    {
      name: "Get by Name",
      value: "getByName",
      description: "Get an entity by its name (case-sensitive)",
      action: "Get entity by name",
    },
    {
      name: "Get Many",
      value: "list",
      description: "Get all entities",
      action: "Get many entities",
    },
  ],
  default: "create",
};

export const fields: INodeProperties[] = [
  {
    displayName: "Entity Name",
    name: "entityName",
    type: "string",
    displayOptions: {
      show: {
        resource: ["entity"],
        operation: ["create", "getByName"],
      },
    },
    default: "",
    placeholder: "Cloud Provider Inc.",
    description: "Name of the entity (case-sensitive)",
    required: true,
  },
  {
    displayName: "Folder UUID",
    name: "folderId",
    type: "string",
    displayOptions: {
      show: {
        resource: ["entity"],
        operation: ["create", "getByName"],
      },
    },
    default: "",
    placeholder: "domain-uuid-here",
    description: "The UUID of the folder (domain)",
    required: true,
  },
  {
    displayName: "Description",
    name: "entityDescription",
    type: "string",
    typeOptions: {
      rows: 3,
    },
    displayOptions: {
      show: {
        resource: ["entity"],
        operation: ["create"],
      },
    },
    default: "",
    placeholder: "Description of the entity",
    description: "Entity description",
  },
  {
    displayName: "Mission",
    name: "entityMission",
    type: "string",
    typeOptions: {
      rows: 3,
    },
    displayOptions: {
      show: {
        resource: ["entity"],
        operation: ["create"],
      },
    },
    default: "",
    placeholder: "Mission statement of the entity",
    description: "Entity mission statement",
  },
  {
    displayName: "Reference Link",
    name: "entityReferenceLink",
    type: "string",
    displayOptions: {
      show: {
        resource: ["entity"],
        operation: ["create"],
      },
    },
    default: "",
    placeholder: "https://example.com",
    description: "Reference URL for the entity",
  },
];
