import type { INodeProperties } from "n8n-workflow";

export const operations: INodeProperties = {
  displayName: "Operation",
  name: "operation",
  type: "options",
  noDataExpression: true,
  displayOptions: {
    show: {
      resource: ["system"],
    },
  },
  options: [
    {
      name: "Get Build Info",
      value: "getBuild",
      description: "Get build information from CISO Assistant",
      action: "Get build information",
    },
    {
      name: "Get Many Users",
      value: "listUsers",
      description: "Get all users in the system",
      action: "Get many users",
    },
    {
      name: "Get User by Email",
      value: "getUserByEmail",
      description: "Get a user by their email address",
      action: "Get user by email",
    },
  ],
  default: "getBuild",
};

export const fields: INodeProperties[] = [
  {
    displayName: "User Email",
    name: "userEmail",
    type: "string",
    displayOptions: {
      show: {
        resource: ["system"],
        operation: ["getUserByEmail"],
      },
    },
    default: "",
    placeholder: "user@example.com",
    description: "Email address of the user",
    required: true,
  },
];
