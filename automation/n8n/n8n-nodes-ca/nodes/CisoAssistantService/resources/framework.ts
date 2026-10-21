import type { INodeProperties } from "n8n-workflow";

export const operations: INodeProperties = {
  displayName: "Operation",
  name: "operation",
  type: "options",
  noDataExpression: true,
  displayOptions: {
    show: {
      resource: ["framework"],
    },
  },
  options: [
    {
      name: "Get",
      value: "get",
      description: "Get a framework by ID",
      action: "Get a framework",
    },
    {
      name: "Get Many",
      value: "list",
      description: "Get all loaded frameworks",
      action: "Get many frameworks",
    },
  ],
  default: "list",
};

export const fields: INodeProperties[] = [];
