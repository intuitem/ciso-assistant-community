import type { INodeProperties } from "n8n-workflow";

export const operations: INodeProperties = {
  displayName: "Operation",
  name: "operation",
  type: "options",
  noDataExpression: true,
  displayOptions: {
    show: {
      resource: ["domain"],
    },
  },
  options: [
    {
      name: "Create",
      value: "create",
      description: "Create a new domain",
      action: "Create a domain",
    },
    {
      name: "Get",
      value: "get",
      description: "Get a domain by ID",
      action: "Get a domain",
    },
    {
      name: "Get by Name",
      value: "getByName",
      description: "Get a domain by its name",
      action: "Get domain by name",
    },
    {
      name: "Get Many",
      value: "list",
      description: "Get all domains",
      action: "Get many domains",
    },
  ],
  default: "create",
};

export const fields: INodeProperties[] = [
  {
    displayName: "Domain Name",
    name: "domainName",
    type: "string",
    displayOptions: {
      show: {
        resource: ["domain"],
        operation: ["create", "getByName"],
      },
    },
    default: "",
    placeholder: "IT Infrastructure",
    description: "The name of the domain (case sensitive for getByName)",
    required: true,
  },
  {
    displayName: "Domain Description",
    name: "domainDescription",
    type: "string",
    typeOptions: {
      rows: 3,
    },
    displayOptions: {
      show: {
        resource: ["domain"],
        operation: ["create"],
      },
    },
    default: "",
    placeholder: "Description of the domain",
    description: "The description of the domain",
  },
];
