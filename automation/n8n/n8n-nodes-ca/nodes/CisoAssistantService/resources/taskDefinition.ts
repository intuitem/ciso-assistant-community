import type { INodeProperties } from "n8n-workflow";

export const operations: INodeProperties = {
  displayName: "Operation",
  name: "operation",
  type: "options",
  noDataExpression: true,
  displayOptions: {
    show: {
      resource: ["taskDefinition"],
    },
  },
  options: [
    {
      name: "Create",
      value: "create",
      description: "Create a new task definition",
      action: "Create a task definition",
    },
    {
      name: "Get",
      value: "get",
      description: "Get a task definition by ID",
      action: "Get a task definition",
    },
    {
      name: "Get by Name",
      value: "getByName",
      description: "Get a task definition by its name",
      action: "Get task definition by name",
    },
    {
      name: "Get Many",
      value: "list",
      description: "Get all task definitions",
      action: "Get many task definitions",
    },
    {
      name: "Update",
      value: "update",
      description: "Update a task definition by UUID",
      action: "Update task definition",
    },
  ],
  default: "create",
};

export const fields: INodeProperties[] = [
  {
    displayName: "Task Definition Name",
    name: "taskDefinitionName",
    type: "string",
    displayOptions: {
      show: {
        resource: ["taskDefinition"],
        operation: ["create", "getByName"],
      },
    },
    default: "",
    placeholder: "Weekly Security Review",
    description: "Name of the task definition (case-sensitive)",
    required: true,
  },
  {
    displayName: "Folder UUID",
    name: "folderId",
    type: "string",
    displayOptions: {
      show: {
        resource: ["taskDefinition"],
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
    name: "taskDefinitionDescription",
    type: "string",
    typeOptions: {
      rows: 3,
    },
    displayOptions: {
      show: {
        resource: ["taskDefinition"],
        operation: ["create"],
      },
    },
    default: "",
    placeholder: "Description of the task definition",
    description: "Task definition description",
  },
  {
    displayName: "Task Date",
    name: "taskDefinitionTaskDate",
    type: "string",
    displayOptions: {
      show: {
        resource: ["taskDefinition"],
        operation: ["create"],
      },
    },
    default: "",
    placeholder: "2025-12-31",
    description: "Task date for non-recurrent tasks (YYYY-MM-DD format)",
  },
  {
    displayName: "Is Recurrent",
    name: "taskDefinitionIsRecurrent",
    type: "boolean",
    displayOptions: {
      show: {
        resource: ["taskDefinition"],
        operation: ["create"],
      },
    },
    default: false,
    description: "Whether this task definition is recurrent",
  },
  {
    displayName: "Enabled",
    name: "taskDefinitionEnabled",
    type: "boolean",
    displayOptions: {
      show: {
        resource: ["taskDefinition"],
        operation: ["create"],
      },
    },
    default: true,
    description: "Whether this task definition is enabled",
  },
  {
    displayName: "Task Definition UUID",
    name: "taskDefinitionId",
    type: "string",
    displayOptions: {
      show: {
        resource: ["taskDefinition"],
        operation: ["update"],
      },
    },
    default: "",
    placeholder: "task-definition-uuid-here",
    description: "The UUID of the task definition to update",
    required: true,
  },
  {
    displayName: "Task Date",
    name: "taskDefinitionTaskDateUpdate",
    type: "string",
    displayOptions: {
      show: {
        resource: ["taskDefinition"],
        operation: ["update"],
      },
    },
    default: "",
    placeholder: "2025-12-31",
    description: "Task date (YYYY-MM-DD format)",
  },
  {
    displayName: "Enabled",
    name: "taskDefinitionEnabledUpdate",
    type: "boolean",
    displayOptions: {
      show: {
        resource: ["taskDefinition"],
        operation: ["update"],
      },
    },
    default: true,
    description: "Whether this task definition is enabled",
  },
];
