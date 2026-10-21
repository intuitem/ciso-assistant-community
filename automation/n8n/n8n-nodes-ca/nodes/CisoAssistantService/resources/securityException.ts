import type { INodeProperties } from "n8n-workflow";

export const operations: INodeProperties = {
  displayName: "Operation",
  name: "operation",
  type: "options",
  noDataExpression: true,
  displayOptions: {
    show: {
      resource: ["securityException"],
    },
  },
  options: [
    {
      name: "Create",
      value: "create",
      description: "Create a new security exception",
      action: "Create security exception",
    },
    {
      name: "Get",
      value: "get",
      description: "Get a security exception by ID",
      action: "Get a security exception",
    },
    {
      name: "Get by Name",
      value: "getByName",
      description: "Get a security exception by its name (case-sensitive)",
      action: "Get security exception by name",
    },
    {
      name: "Get Many",
      value: "list",
      description: "Get all security exceptions",
      action: "Get many security exceptions",
    },
    {
      name: "Update",
      value: "update",
      description: "Update a security exception by UUID",
      action: "Update security exception",
    },
  ],
  default: "create",
};

export const fields: INodeProperties[] = [
  {
    displayName: "Security Exception Name",
    name: "securityExceptionName",
    type: "string",
    displayOptions: {
      show: {
        resource: ["securityException"],
        operation: ["create", "getByName"],
      },
    },
    default: "",
    placeholder: "Legacy System Exception",
    description: "Name of the security exception (case-sensitive)",
    required: true,
  },
  {
    displayName: "Folder UUID",
    name: "folderId",
    type: "string",
    displayOptions: {
      show: {
        resource: ["securityException"],
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
    name: "securityExceptionDescription",
    type: "string",
    typeOptions: {
      rows: 3,
    },
    displayOptions: {
      show: {
        resource: ["securityException"],
        operation: ["create"],
      },
    },
    default: "",
    placeholder: "Description of the security exception",
    description: "Security exception description",
  },
  {
    displayName: "Severity",
    name: "securityExceptionSeverity",
    type: "options",
    displayOptions: {
      show: {
        resource: ["securityException"],
        operation: ["create"],
      },
    },
    options: [
      {
        name: "Critical",
        value: 4,
      },
      {
        name: "High",
        value: 3,
      },
      {
        name: "Info",
        value: 0,
      },
      {
        name: "Low",
        value: 1,
      },
      {
        name: "Medium",
        value: 2,
      },
      {
        name: "Undefined",
        value: -1,
      },
    ],
    default: -1,
    description: "Severity of the security exception",
  },
  {
    displayName: "Status",
    name: "securityExceptionStatus",
    type: "options",
    displayOptions: {
      show: {
        resource: ["securityException"],
        operation: ["create"],
      },
    },
    options: [
      {
        name: "Approved",
        value: "approved",
      },
      {
        name: "Deprecated",
        value: "deprecated",
      },
      {
        name: "Draft",
        value: "draft",
      },
      {
        name: "Expired",
        value: "expired",
      },
      {
        name: "In Review",
        value: "in_review",
      },
      {
        name: "Resolved",
        value: "resolved",
      },
    ],
    default: "draft",
    description: "Status of the security exception",
  },
  {
    displayName: "Expiration Date",
    name: "securityExceptionExpirationDate",
    type: "string",
    displayOptions: {
      show: {
        resource: ["securityException"],
        operation: ["create"],
      },
    },
    default: "",
    placeholder: "2025-12-31",
    description: "Expiration date (YYYY-MM-DD format)",
  },
  {
    displayName: "Security Exception UUID",
    name: "securityExceptionId",
    type: "string",
    displayOptions: {
      show: {
        resource: ["securityException"],
        operation: ["update"],
      },
    },
    default: "",
    placeholder: "security-exception-uuid-here",
    description: "The UUID of the security exception to update",
    required: true,
  },
  {
    displayName: "Status",
    name: "securityExceptionStatusUpdate",
    type: "options",
    displayOptions: {
      show: {
        resource: ["securityException"],
        operation: ["update"],
      },
    },
    options: [
      {
        name: "Approved",
        value: "approved",
      },
      {
        name: "Deprecated",
        value: "deprecated",
      },
      {
        name: "Draft",
        value: "draft",
      },
      {
        name: "Expired",
        value: "expired",
      },
      {
        name: "In Review",
        value: "in_review",
      },
      {
        name: "Resolved",
        value: "resolved",
      },
    ],
    default: "draft",
    description: "Status of the security exception",
  },
];
