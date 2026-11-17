import type { INodeProperties } from "n8n-workflow";

export const operations: INodeProperties = {
  displayName: "Operation",
  name: "operation",
  type: "options",
  noDataExpression: true,
  displayOptions: {
    show: {
      resource: ["incident"],
    },
  },
  options: [
    {
      name: "Create",
      value: "create",
      description: "Create a new incident",
      action: "Create an incident",
    },
    {
      name: "Get",
      value: "get",
      description: "Get an incident by ID",
      action: "Get an incident",
    },
    {
      name: "Get Many",
      value: "list",
      description: "Get all incidents",
      action: "Get many incidents",
    },
    {
      name: "Update",
      value: "update",
      description: "Update an existing incident",
      action: "Update incident",
    },
  ],
  default: "create",
};

export const fields: INodeProperties[] = [
  {
    displayName: "Incident Name",
    name: "incidentName",
    type: "string",
    displayOptions: {
      show: {
        resource: ["incident"],
        operation: ["create"],
      },
    },
    default: "",
    placeholder: "Security Incident",
    description: "The name of the incident",
    required: true,
  },
  {
    displayName: "Incident UUID",
    name: "incidentId",
    type: "string",
    displayOptions: {
      show: {
        resource: ["incident"],
        operation: ["update"],
      },
    },
    default: "",
    placeholder: "incident-uuid-here",
    description: "The UUID of the incident to update",
    required: true,
  },
  {
    displayName: "Folder ID",
    name: "folderId",
    type: "string",
    displayOptions: {
      show: {
        resource: ["incident"],
        operation: ["create"],
      },
    },
    default: "",
    placeholder: "domain-uuid-here",
    description: "The UUID of the folder (domain) this incident belongs to",
    required: true,
  },
  {
    displayName: "Incident Description",
    name: "incidentDescription",
    type: "string",
    typeOptions: {
      rows: 3,
    },
    displayOptions: {
      show: {
        resource: ["incident"],
        operation: ["create", "update"],
      },
    },
    default: "",
    placeholder: "Description of the incident",
    description: "The description of the incident",
  },
  {
    displayName: "Status",
    name: "incidentStatus",
    type: "options",
    displayOptions: {
      show: {
        resource: ["incident"],
        operation: ["create", "update"],
      },
    },
    options: [
      {
        name: "Closed",
        value: "closed",
      },
      {
        name: "Dismissed",
        value: "dismissed",
      },
      {
        name: "New",
        value: "new",
      },
      {
        name: "No Change",
        value: "",
      },
      {
        name: "Ongoing",
        value: "ongoing",
      },
      {
        name: "Resolved",
        value: "resolved",
      },
    ],
    default: "",
    description:
      'The status of the incident (use "No Change" for updates to keep existing value)',
  },
  {
    displayName: "Severity",
    name: "incidentSeverity",
    type: "options",
    displayOptions: {
      show: {
        resource: ["incident"],
        operation: ["create", "update"],
      },
    },
    options: [
      {
        name: "Critical",
        value: 1,
      },
      {
        name: "Low",
        value: 5,
      },
      {
        name: "Major",
        value: 2,
      },
      {
        name: "Minor",
        value: 4,
      },
      {
        name: "Moderate",
        value: 3,
      },
      {
        name: "No Change",
        value: -1,
      },
      {
        name: "Unknown",
        value: 6,
      },
    ],
    default: -1,
    description:
      'The severity of the incident (use "No Change" for updates to keep existing value)',
  },
  {
    displayName: "Detection",
    name: "incidentDetection",
    type: "options",
    displayOptions: {
      show: {
        resource: ["incident"],
        operation: ["create", "update"],
      },
    },
    options: [
      {
        name: "External",
        value: "externally_detected",
      },
      {
        name: "Internal",
        value: "internally_detected",
      },
      {
        name: "No Change",
        value: "",
      },
    ],
    default: "",
    description:
      'How the incident was detected (use "No Change" for updates to keep existing value)',
  },
  {
    displayName: "Reference ID",
    name: "incidentRefId",
    type: "string",
    displayOptions: {
      show: {
        resource: ["incident"],
        operation: ["create", "update"],
      },
    },
    default: "",
    placeholder: "INC-2025-001",
    description: "Reference ID for the incident",
  },
];
