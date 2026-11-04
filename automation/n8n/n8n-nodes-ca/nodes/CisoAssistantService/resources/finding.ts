import type { INodeProperties } from "n8n-workflow";

export const operations: INodeProperties = {
  displayName: "Operation",
  name: "operation",
  type: "options",
  noDataExpression: true,
  displayOptions: {
    show: {
      resource: ["finding"],
    },
  },
  options: [
    {
      name: "Create",
      value: "create",
      description: "Create a new finding",
      action: "Create finding",
    },
    {
      name: "Get",
      value: "get",
      description: "Get a finding by ID",
      action: "Get a finding",
    },
    {
      name: "Get by Name",
      value: "getByName",
      description: "Get a finding by its name (case-sensitive)",
      action: "Get finding by name",
    },
    {
      name: "Get Many",
      value: "list",
      description: "Get all findings",
      action: "Get many findings",
    },
    {
      name: "Update",
      value: "update",
      description: "Update a finding by UUID",
      action: "Update finding",
    },
  ],
  default: "create",
};

export const fields: INodeProperties[] = [
  {
    displayName: "Finding Name",
    name: "findingName",
    type: "string",
    displayOptions: {
      show: {
        resource: ["finding"],
        operation: ["create", "getByName"],
      },
    },
    default: "",
    placeholder: "SQL Injection vulnerability",
    description: "Name of the finding (case-sensitive)",
    required: true,
  },
  {
    displayName: "Findings Tracking UUID",
    name: "findingsAssessmentId",
    type: "string",
    displayOptions: {
      show: {
        resource: ["finding"],
        operation: ["create"],
      },
    },
    default: "",
    placeholder: "findings-tracking-uuid-here",
    description: "The UUID of the parent findings tracking",
    required: true,
  },
  {
    displayName: "Folder UUID",
    name: "folderId",
    type: "string",
    displayOptions: {
      show: {
        resource: ["finding"],
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
    name: "findingDescription",
    type: "string",
    typeOptions: {
      rows: 3,
    },
    displayOptions: {
      show: {
        resource: ["finding"],
        operation: ["create"],
      },
    },
    default: "",
    placeholder: "Description of the finding",
    description: "Finding description",
  },
  {
    displayName: "Severity",
    name: "findingSeverity",
    type: "options",
    displayOptions: {
      show: {
        resource: ["finding"],
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
    description: "Severity of the finding",
  },
  {
    displayName: "Status",
    name: "findingStatus",
    type: "options",
    displayOptions: {
      show: {
        resource: ["finding"],
        operation: ["create"],
      },
    },
    options: [
      {
        name: "Assigned",
        value: "assigned",
      },
      {
        name: "Closed",
        value: "closed",
      },
      {
        name: "Confirmed",
        value: "confirmed",
      },
      {
        name: "Deprecated",
        value: "deprecated",
      },
      {
        name: "Dismissed",
        value: "dismissed",
      },
      {
        name: "Identified",
        value: "identified",
      },
      {
        name: "In Progress",
        value: "in_progress",
      },
      {
        name: "Mitigated",
        value: "mitigated",
      },
      {
        name: "Resolved",
        value: "resolved",
      },
      {
        name: "Undefined",
        value: "--",
      },
    ],
    default: "identified",
    description: "Status of the finding",
  },
  {
    displayName: "Finding UUID",
    name: "findingId",
    type: "string",
    displayOptions: {
      show: {
        resource: ["finding"],
        operation: ["update"],
      },
    },
    default: "",
    placeholder: "finding-uuid-here",
    description: "The UUID of the finding to update",
    required: true,
  },
  {
    displayName: "Status",
    name: "findingStatusUpdate",
    type: "options",
    displayOptions: {
      show: {
        resource: ["finding"],
        operation: ["update"],
      },
    },
    options: [
      {
        name: "Assigned",
        value: "assigned",
      },
      {
        name: "Closed",
        value: "closed",
      },
      {
        name: "Confirmed",
        value: "confirmed",
      },
      {
        name: "Deprecated",
        value: "deprecated",
      },
      {
        name: "Dismissed",
        value: "dismissed",
      },
      {
        name: "Identified",
        value: "identified",
      },
      {
        name: "In Progress",
        value: "in_progress",
      },
      {
        name: "Mitigated",
        value: "mitigated",
      },
      {
        name: "Resolved",
        value: "resolved",
      },
      {
        name: "Undefined",
        value: "--",
      },
    ],
    default: "identified",
    description: "Status of the finding",
  },
  {
    displayName: "Severity",
    name: "findingSeverityUpdate",
    type: "options",
    displayOptions: {
      show: {
        resource: ["finding"],
        operation: ["update"],
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
    description: "Severity of the finding",
  },
];
