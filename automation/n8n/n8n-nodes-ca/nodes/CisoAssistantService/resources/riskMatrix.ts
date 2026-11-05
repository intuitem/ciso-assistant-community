import type { INodeProperties } from "n8n-workflow";

export const operations: INodeProperties = {
  displayName: "Operation",
  name: "operation",
  type: "options",
  noDataExpression: true,
  displayOptions: {
    show: {
      resource: ["riskMatrix"],
    },
  },
  options: [
    {
      name: "Get",
      value: "get",
      description: "Get a risk matrix by ID",
      action: "Get a risk matrix",
    },
    {
      name: "Get Many",
      value: "list",
      description: "Get all risk matrices",
      action: "Get many risk matrices",
    },
  ],
  default: "list",
};

export const fields: INodeProperties[] = [];
