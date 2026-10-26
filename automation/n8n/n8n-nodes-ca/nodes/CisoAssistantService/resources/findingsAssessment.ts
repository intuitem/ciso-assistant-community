import type { INodeProperties } from "n8n-workflow";

export const operations: INodeProperties = {
  displayName: "Operation",
  name: "operation",
  type: "options",
  noDataExpression: true,
  displayOptions: {
    show: {
      resource: ["findingsAssessment"],
    },
  },
  options: [
    {
      name: "Create",
      value: "create",
      description: "Create a new findings tracking assessment",
      action: "Create findings tracking",
    },
    {
      name: "Get",
      value: "get",
      description: "Get a findings tracking by ID",
      action: "Get a findings tracking",
    },
    {
      name: "Get by Name",
      value: "getByName",
      description: "Get a findings tracking by its name (case-sensitive)",
      action: "Get findings tracking by name",
    },
    {
      name: "Get by Ref ID",
      value: "getByRefId",
      description: "Get a findings tracking by its reference ID",
      action: "Get findings tracking by ref ID",
    },
    {
      name: "Get Many",
      value: "list",
      description: "Get all findings tracking assessments",
      action: "Get many findings tracking",
    },
    {
      name: "Update",
      value: "update",
      description: "Update a findings tracking by UUID",
      action: "Update findings tracking",
    },
  ],
  default: "create",
};

export const fields: INodeProperties[] = [
  {
    displayName: "Findings Tracking Name",
    name: "findingsAssessmentName",
    type: "string",
    displayOptions: {
      show: {
        resource: ["findingsAssessment"],
        operation: ["create", "getByName"],
      },
    },
    default: "",
    placeholder: "Pentest 2025-Q1",
    description: "Name of the findings tracking (case-sensitive)",
    required: true,
  },
  {
    displayName: "Folder UUID",
    name: "folderId",
    type: "string",
    displayOptions: {
      show: {
        resource: ["findingsAssessment"],
        operation: ["create"],
      },
    },
    default: "",
    placeholder: "domain-uuid-here",
    description: "The UUID of the folder (domain)",
    required: true,
  },
  {
    displayName: "Folder UUID (Optional)",
    name: "folderIdFilter",
    type: "string",
    displayOptions: {
      show: {
        resource: ["findingsAssessment"],
        operation: ["getByName", "getByRefId"],
      },
    },
    default: "",
    placeholder: "domain-uuid-here",
    description: "Filter by folder (domain) UUID",
  },
  {
    displayName: "Ref ID",
    name: "findingsAssessmentRefId",
    type: "string",
    displayOptions: {
      show: {
        resource: ["findingsAssessment"],
        operation: ["getByRefId"],
      },
    },
    default: "",
    placeholder: "PENT-2025-01",
    description: "Reference ID of the findings tracking",
    required: true,
  },
  {
    displayName: "Perimeter UUID (Optional)",
    name: "perimeterIdFilter",
    type: "string",
    displayOptions: {
      show: {
        resource: ["findingsAssessment"],
        operation: ["getByName", "getByRefId"],
      },
    },
    default: "",
    placeholder: "perimeter-uuid-here",
    description: "Filter by perimeter UUID",
  },
  {
    displayName: "Perimeter UUID",
    name: "perimeterId",
    type: "string",
    displayOptions: {
      show: {
        resource: ["findingsAssessment"],
        operation: ["create"],
      },
    },
    default: "",
    placeholder: "perimeter-uuid-here",
    description: "The UUID of the perimeter",
    required: true,
  },
  {
    displayName: "Description",
    name: "findingsAssessmentDescription",
    type: "string",
    typeOptions: {
      rows: 3,
    },
    displayOptions: {
      show: {
        resource: ["findingsAssessment"],
        operation: ["create"],
      },
    },
    default: "",
    placeholder: "Description of the findings tracking",
    description: "Findings tracking description",
  },
  {
    displayName: "Category",
    name: "findingsAssessmentCategory",
    type: "options",
    displayOptions: {
      show: {
        resource: ["findingsAssessment"],
        operation: ["create"],
      },
    },
    options: [
      {
        name: "Audit",
        value: "audit",
      },
      {
        name: "Pentest",
        value: "pentest",
      },
      {
        name: "Self-Identified",
        value: "self_identified",
      },
      {
        name: "Undefined",
        value: "--",
      },
    ],
    default: "--",
    description: "Category of findings tracking",
  },
  {
    displayName: "Findings Tracking UUID",
    name: "findingsAssessmentId",
    type: "string",
    displayOptions: {
      show: {
        resource: ["findingsAssessment"],
        operation: ["update"],
      },
    },
    default: "",
    placeholder: "findings-tracking-uuid-here",
    description: "The UUID of the findings tracking to update",
    required: true,
  },
  {
    displayName: "Status",
    name: "findingsAssessmentStatus",
    type: "options",
    displayOptions: {
      show: {
        resource: ["findingsAssessment"],
        operation: ["update"],
      },
    },
    options: [
      {
        name: "Deprecated",
        value: "deprecated",
      },
      {
        name: "Done",
        value: "done",
      },
      {
        name: "In Progress",
        value: "in_progress",
      },
      {
        name: "In Review",
        value: "in_review",
      },
      {
        name: "Planned",
        value: "planned",
      },
    ],
    default: "planned",
    description: "Status of the findings tracking",
  },
];
