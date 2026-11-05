import type { INodeProperties } from "n8n-workflow";

export const operations: INodeProperties = {
  displayName: "Operation",
  name: "operation",
  type: "options",
  noDataExpression: true,
  displayOptions: {
    show: {
      resource: ["solution"],
    },
  },
  options: [
    {
      name: "Create",
      value: "create",
      description: "Create a new solution from an entity",
      action: "Create solution",
    },
    {
      name: "Get",
      value: "get",
      description: "Get a solution by ID",
      action: "Get a solution",
    },
    {
      name: "Get by Name",
      value: "getByName",
      description: "Get a solution by its name (case-sensitive)",
      action: "Get solution by name",
    },
    {
      name: "Get Many",
      value: "list",
      description: "Get all solutions",
      action: "Get many solutions",
    },
  ],
  default: "create",
};

export const fields: INodeProperties[] = [
  {
    displayName: "Solution Name",
    name: "solutionName",
    type: "string",
    displayOptions: {
      show: {
        resource: ["solution"],
        operation: ["create", "getByName"],
      },
    },
    default: "",
    placeholder: "AWS Cloud Services",
    description: "Name of the solution (case-sensitive)",
    required: true,
  },
  {
    displayName: "Provider Entity UUID",
    name: "providerEntityId",
    type: "string",
    displayOptions: {
      show: {
        resource: ["solution"],
        operation: ["create", "getByName"],
      },
    },
    default: "",
    placeholder: "entity-uuid-here",
    description: "UUID of the provider entity",
    required: true,
  },
  {
    displayName: "Recipient Entity UUID",
    name: "recipientEntityId",
    type: "string",
    displayOptions: {
      show: {
        resource: ["solution"],
        operation: ["create"],
      },
    },
    default: "",
    placeholder: "entity-uuid-here",
    description: "UUID of the recipient entity (optional)",
  },
  {
    displayName: "Description",
    name: "solutionDescription",
    type: "string",
    typeOptions: {
      rows: 3,
    },
    displayOptions: {
      show: {
        resource: ["solution"],
        operation: ["create"],
      },
    },
    default: "",
    placeholder: "Description of the solution",
    description: "Solution description",
  },
  {
    displayName: "Reference ID",
    name: "solutionRefId",
    type: "string",
    displayOptions: {
      show: {
        resource: ["solution"],
        operation: ["create"],
      },
    },
    default: "",
    placeholder: "SOL-001",
    description: "Reference identifier for the solution",
  },
  {
    displayName: "Criticality",
    name: "solutionCriticality",
    type: "number",
    displayOptions: {
      show: {
        resource: ["solution"],
        operation: ["create"],
      },
    },
    default: 0,
    description: "Criticality level of the solution (0-4)",
  },
];
