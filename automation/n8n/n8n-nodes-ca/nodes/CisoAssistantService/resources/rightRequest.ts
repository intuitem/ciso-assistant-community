import type { INodeProperties } from "n8n-workflow";

export const operations: INodeProperties = {
  displayName: "Operation",
  name: "operation",
  type: "options",
  noDataExpression: true,
  displayOptions: {
    show: {
      resource: ["rightRequest"],
    },
  },
  options: [
    {
      name: "Create",
      value: "create",
      description: "Create a new right request",
      action: "Create right request",
    },
    {
      name: "Get",
      value: "get",
      description: "Get a right request by ID",
      action: "Get a right request",
    },
    {
      name: "Get by Name",
      value: "getByName",
      description: "Get a right request by its name (case-sensitive)",
      action: "Get right request by name",
    },
    {
      name: "Get Many",
      value: "list",
      description: "Get all right requests",
      action: "Get many right requests",
    },
    {
      name: "Update",
      value: "update",
      description: "Update an existing right request",
      action: "Update right request",
    },
  ],
  default: "create",
};

export const fields: INodeProperties[] = [
  {
    displayName: "Right Request Name",
    name: "rightRequestName",
    type: "string",
    displayOptions: {
      show: {
        resource: ["rightRequest"],
        operation: ["create", "getByName"],
      },
    },
    default: "",
    placeholder: "GDPR Access Request",
    description: "Name of the right request (case-sensitive)",
    required: true,
  },
  {
    displayName: "Folder UUID",
    name: "folderId",
    type: "string",
    displayOptions: {
      show: {
        resource: ["rightRequest"],
        operation: ["create", "getByName"],
      },
    },
    default: "",
    placeholder: "domain-uuid-here",
    description: "The UUID of the folder (domain)",
    required: true,
  },
  {
    displayName: "Right Request UUID",
    name: "rightRequestId",
    type: "string",
    displayOptions: {
      show: {
        resource: ["rightRequest"],
        operation: ["update"],
      },
    },
    default: "",
    placeholder: "right-request-uuid-here",
    description: "The UUID of the right request to update",
    required: true,
  },
  {
    displayName: "Requested On",
    name: "rightRequestRequestedOn",
    type: "string",
    displayOptions: {
      show: {
        resource: ["rightRequest"],
        operation: ["create"],
      },
    },
    default: "",
    placeholder: "2025-01-15",
    description: "Date when the request was made (YYYY-MM-DD format)",
    required: true,
  },
  {
    displayName: "Request Type",
    name: "rightRequestType",
    type: "options",
    displayOptions: {
      show: {
        resource: ["rightRequest"],
        operation: ["create", "update"],
      },
    },
    options: [
      {
        name: "Access / Extract",
        value: "access",
      },
      {
        name: "Deletion / Erasure",
        value: "deletion",
      },
      {
        name: "Objection",
        value: "objection",
      },
      {
        name: "Other",
        value: "other",
      },
      {
        name: "Portability",
        value: "portability",
      },
      {
        name: "Rectification",
        value: "rectification",
      },
      {
        name: "Restriction",
        value: "restriction",
      },
    ],
    default: "other",
    description: "Type of the right request",
  },
  {
    displayName: "Status",
    name: "rightRequestStatus",
    type: "options",
    displayOptions: {
      show: {
        resource: ["rightRequest"],
        operation: ["create", "update"],
      },
    },
    options: [
      {
        name: "Done",
        value: "done",
      },
      {
        name: "In Progress",
        value: "in_progress",
      },
      {
        name: "New",
        value: "new",
      },
      {
        name: "On Hold",
        value: "on_hold",
      },
    ],
    default: "new",
    description: "Status of the right request",
  },
  {
    displayName: "Description",
    name: "rightRequestDescription",
    type: "string",
    typeOptions: {
      rows: 3,
    },
    displayOptions: {
      show: {
        resource: ["rightRequest"],
        operation: ["create", "update"],
      },
    },
    default: "",
    placeholder: "Description of the right request",
    description: "Right request description",
  },
  {
    displayName: "Due Date",
    name: "rightRequestDueDate",
    type: "string",
    displayOptions: {
      show: {
        resource: ["rightRequest"],
        operation: ["create", "update"],
      },
    },
    default: "",
    placeholder: "2025-02-15",
    description: "Due date for the request (YYYY-MM-DD format)",
  },
  {
    displayName: "Observation",
    name: "rightRequestObservation",
    type: "string",
    typeOptions: {
      rows: 3,
    },
    displayOptions: {
      show: {
        resource: ["rightRequest"],
        operation: ["create", "update"],
      },
    },
    default: "",
    placeholder: "Additional observations",
    description: "Observation notes",
  },
];
