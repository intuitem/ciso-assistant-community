import type { INodeProperties } from "n8n-workflow";

export const operations: INodeProperties = {
  displayName: "Operation",
  name: "operation",
  type: "options",
  noDataExpression: true,
  displayOptions: {
    show: {
      resource: ["appliedControl"],
    },
  },
  options: [
    {
      name: "Create",
      value: "create",
      description: "Create a new applied control",
      action: "Create an applied control",
    },
    {
      name: "Get",
      value: "get",
      description: "Get an applied control by ID",
      action: "Get an applied control",
    },
    {
      name: "Get by Name",
      value: "getByName",
      description: "Get an applied control by its name",
      action: "Get applied control by name",
    },
    {
      name: "Get Many",
      value: "list",
      description: "Get all applied controls",
      action: "Get many applied controls",
    },
    {
      name: "Update",
      value: "update",
      description: "Update an applied control by UUID",
      action: "Update applied control",
    },
  ],
  default: "create",
};

export const fields: INodeProperties[] = [
  {
    displayName: "Applied Control Name",
    name: "appliedControlName",
    type: "string",
    displayOptions: {
      show: {
        resource: ["appliedControl"],
        operation: ["create", "getByName"],
      },
    },
    default: "",
    placeholder: "Access Control Implementation",
    description:
      "The name of the applied control (case sensitive for getByName)",
    required: true,
  },
  {
    displayName: "Folder ID",
    name: "folderId",
    type: "string",
    displayOptions: {
      show: {
        resource: ["appliedControl"],
        operation: ["create", "getByName"],
      },
    },
    default: "",
    placeholder: "domain-uuid-here",
    description: "The UUID of the folder (domain)",
    required: true,
  },
  {
    displayName: "Applied Control Description",
    name: "appliedControlDescription",
    type: "string",
    typeOptions: {
      rows: 3,
    },
    displayOptions: {
      show: {
        resource: ["appliedControl"],
        operation: ["create"],
      },
    },
    default: "",
    placeholder: "Description of the applied control",
    description: "The description of the applied control",
  },
  {
    displayName: "Status",
    name: "appliedControlStatus",
    type: "options",
    displayOptions: {
      show: {
        resource: ["appliedControl"],
        operation: ["create", "update"],
      },
    },
    options: [
      {
        name: "Active",
        value: "active",
      },
      {
        name: "Deprecated",
        value: "deprecated",
      },
      {
        name: "In Progress",
        value: "in_progress",
      },
      {
        name: "On Hold",
        value: "on_hold",
      },
      {
        name: "To Do",
        value: "to_do",
      },
      {
        name: "Undefined",
        value: "--",
      },
    ],
    default: "to_do",
    description: "The status of the applied control",
  },
  {
    displayName: "Applied Control UUID",
    name: "appliedControlId",
    type: "string",
    displayOptions: {
      show: {
        resource: ["appliedControl"],
        operation: ["update"],
      },
    },
    default: "",
    placeholder: "applied-control-uuid-here",
    description: "The UUID of the applied control to update",
    required: true,
  },
];
