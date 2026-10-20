import type { INodeProperties } from "n8n-workflow";

export const operations: INodeProperties = {
  displayName: "Operation",
  name: "operation",
  type: "options",
  noDataExpression: true,
  displayOptions: {
    show: {
      resource: ["taskOccurrence"],
    },
  },
  options: [
    {
      name: "Create",
      value: "create",
      description: "Create a new task occurrence",
      action: "Create a task occurrence",
    },
    {
      name: "Get",
      value: "get",
      description: "Get a task occurrence by ID",
      action: "Get a task occurrence",
    },
    {
      name: "Get Many",
      value: "list",
      description: "Get all task occurrences",
      action: "Get many task occurrences",
    },
    {
      name: "Update",
      value: "update",
      description: "Update a task occurrence by UUID",
      action: "Update task occurrence",
    },
  ],
  default: "create",
};

export const fields: INodeProperties[] = [
  {
    displayName: "Folder ID",
    name: "folderId",
    type: "string",
    displayOptions: {
      show: {
        resource: ["taskOccurrence"],
        operation: ["create"],
      },
    },
    default: "",
    placeholder: "domain-uuid-here",
    description: "The UUID of the folder (domain)",
    required: true,
  },
  {
    displayName: "Due Date",
    name: "taskDueDate",
    type: "string",
    displayOptions: {
      show: {
        resource: ["taskOccurrence"],
        operation: ["create", "update"],
      },
    },
    default: "",
    placeholder: "2025-12-31",
    description: "Due date for the task (YYYY-MM-DD format)",
  },
  {
    displayName: "Status",
    name: "taskStatus",
    type: "options",
    displayOptions: {
      show: {
        resource: ["taskOccurrence"],
        operation: ["create", "update"],
      },
    },
    options: [
      {
        name: "Cancelled",
        value: "cancelled",
      },
      {
        name: "Completed",
        value: "completed",
      },
      {
        name: "In Progress",
        value: "in_progress",
      },
      {
        name: "Pending",
        value: "pending",
      },
    ],
    default: "pending",
    description: "The status of the task",
  },
  {
    displayName: "Observation",
    name: "taskObservation",
    type: "string",
    typeOptions: {
      rows: 3,
    },
    displayOptions: {
      show: {
        resource: ["taskOccurrence"],
        operation: ["create", "update"],
      },
    },
    default: "",
    placeholder: "Task observations and notes",
    description: "Observation notes for the task",
  },
  {
    displayName: "Task UUID",
    name: "taskId",
    type: "string",
    displayOptions: {
      show: {
        resource: ["taskOccurrence"],
        operation: ["update"],
      },
    },
    default: "",
    placeholder: "task-uuid-here",
    description: "The UUID of the task to update",
    required: true,
  },
];
