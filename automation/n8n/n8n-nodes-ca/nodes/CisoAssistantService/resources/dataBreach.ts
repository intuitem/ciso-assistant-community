import type { INodeProperties } from "n8n-workflow";

export const operations: INodeProperties = {
  displayName: "Operation",
  name: "operation",
  type: "options",
  noDataExpression: true,
  displayOptions: {
    show: {
      resource: ["dataBreach"],
    },
  },
  options: [
    {
      name: "Create",
      value: "create",
      description: "Create a new data breach",
      action: "Create data breach",
    },
    {
      name: "Get",
      value: "get",
      description: "Get a data breach by ID",
      action: "Get a data breach",
    },
    {
      name: "Get by Name",
      value: "getByName",
      description: "Get a data breach by its name (case-sensitive)",
      action: "Get data breach by name",
    },
    {
      name: "Get Many",
      value: "list",
      description: "Get all data breaches",
      action: "Get many data breaches",
    },
    {
      name: "Update",
      value: "update",
      description: "Update an existing data breach",
      action: "Update data breach",
    },
  ],
  default: "create",
};

export const fields: INodeProperties[] = [
  {
    displayName: "Data Breach Name",
    name: "dataBreachName",
    type: "string",
    displayOptions: {
      show: {
        resource: ["dataBreach"],
        operation: ["create", "getByName"],
      },
    },
    default: "",
    placeholder: "Q1 2025 Data Breach",
    description: "Name of the data breach (case-sensitive)",
    required: true,
  },
  {
    displayName: "Folder UUID",
    name: "folderId",
    type: "string",
    displayOptions: {
      show: {
        resource: ["dataBreach"],
        operation: ["create", "getByName"],
      },
    },
    default: "",
    placeholder: "domain-uuid-here",
    description: "The UUID of the folder (domain)",
    required: true,
  },
  {
    displayName: "Data Breach UUID",
    name: "dataBreachId",
    type: "string",
    displayOptions: {
      show: {
        resource: ["dataBreach"],
        operation: ["update"],
      },
    },
    default: "",
    placeholder: "data-breach-uuid-here",
    description: "The UUID of the data breach to update",
    required: true,
  },
  {
    displayName: "Discovered On",
    name: "dataBreachDiscoveredOn",
    type: "string",
    displayOptions: {
      show: {
        resource: ["dataBreach"],
        operation: ["create"],
      },
    },
    default: "",
    placeholder: "2025-01-15T14:30:00Z",
    description:
      "Date and time when the breach was discovered (ISO 8601 format)",
    required: true,
  },
  {
    displayName: "Breach Type",
    name: "dataBreachType",
    type: "options",
    displayOptions: {
      show: {
        resource: ["dataBreach"],
        operation: ["create", "update"],
      },
    },
    options: [
      {
        name: "Alteration",
        value: "privacy_alteration",
      },
      {
        name: "Destruction",
        value: "privacy_destruction",
      },
      {
        name: "Loss",
        value: "privacy_loss",
      },
      {
        name: "Other",
        value: "privacy_other",
      },
      {
        name: "Unauthorized Access",
        value: "privacy_unauthorized_access",
      },
      {
        name: "Unauthorized Disclosure",
        value: "privacy_unauthorized_disclosure",
      },
    ],
    default: "privacy_other",
    description: "Type of the data breach",
  },
  {
    displayName: "Risk Level",
    name: "dataBreachRiskLevel",
    type: "options",
    displayOptions: {
      show: {
        resource: ["dataBreach"],
        operation: ["create", "update"],
      },
    },
    options: [
      {
        name: "High Risk",
        value: "privacy_high_risk",
      },
      {
        name: "No Risk",
        value: "privacy_no_risk",
      },
      {
        name: "Risk",
        value: "privacy_risk",
      },
    ],
    default: "privacy_risk",
    description: "Risk level of the breach",
  },
  {
    displayName: "Status",
    name: "dataBreachStatus",
    type: "options",
    displayOptions: {
      show: {
        resource: ["dataBreach"],
        operation: ["create", "update"],
      },
    },
    options: [
      {
        name: "Authority Notified",
        value: "privacy_authority_notified",
      },
      {
        name: "Closed",
        value: "privacy_closed",
      },
      {
        name: "Data Subjects Notified",
        value: "privacy_subjects_notified",
      },
      {
        name: "Discovered",
        value: "privacy_discovered",
      },
      {
        name: "Under Investigation",
        value: "privacy_under_investigation",
      },
    ],
    default: "privacy_discovered",
    description: "Status of the data breach",
  },
  {
    displayName: "Description",
    name: "dataBreachDescription",
    type: "string",
    typeOptions: {
      rows: 3,
    },
    displayOptions: {
      show: {
        resource: ["dataBreach"],
        operation: ["create", "update"],
      },
    },
    default: "",
    placeholder: "Description of the data breach",
    description: "Data breach description",
  },
  {
    displayName: "Affected Subjects Count",
    name: "dataBreachAffectedSubjectsCount",
    type: "number",
    displayOptions: {
      show: {
        resource: ["dataBreach"],
        operation: ["create", "update"],
      },
    },
    default: 0,
    description: "Approximate number of affected data subjects",
  },
  {
    displayName: "Observation",
    name: "dataBreachObservation",
    type: "string",
    typeOptions: {
      rows: 3,
    },
    displayOptions: {
      show: {
        resource: ["dataBreach"],
        operation: ["create", "update"],
      },
    },
    default: "",
    placeholder: "Additional observations",
    description: "Observation notes",
  },
];
