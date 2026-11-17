import type { INodeProperties } from "n8n-workflow";

export const operations: INodeProperties = {
  displayName: "Operation",
  name: "operation",
  type: "options",
  noDataExpression: true,
  displayOptions: {
    show: {
      resource: ["riskAssessment"],
    },
  },
  options: [
    {
      name: "Get",
      value: "get",
      description: "Get a risk assessment by ID",
      action: "Get a risk assessment",
    },
    {
      name: "Get by Name",
      value: "getByName",
      description: "Get a risk assessment by its name (case-sensitive)",
      action: "Get risk assessment by name",
    },
    {
      name: "Get by Ref ID",
      value: "getByRefId",
      description: "Get a risk assessment by its reference ID",
      action: "Get risk assessment by ref ID",
    },
    {
      name: "Get Many",
      value: "list",
      description: "Get all risk assessments",
      action: "Get many risk assessments",
    },
    {
      name: "Initiate",
      value: "initiate",
      description:
        "Initiate a risk assessment for a perimeter with a risk matrix",
      action: "Initiate a risk assessment",
    },
  ],
  default: "initiate",
};

export const fields: INodeProperties[] = [
  {
    displayName: "Risk Matrix ID",
    name: "riskMatrixId",
    type: "string",
    displayOptions: {
      show: {
        resource: ["riskAssessment"],
        operation: ["initiate"],
      },
    },
    default: "",
    placeholder: "risk-matrix-uuid-here",
    description: "The UUID of the risk matrix to use for the assessment",
    required: true,
  },
  {
    displayName: "Risk Assessment Name",
    name: "riskAssessmentName",
    type: "string",
    displayOptions: {
      show: {
        resource: ["riskAssessment"],
        operation: ["initiate"],
      },
    },
    default: "",
    placeholder: "Risk Assessment 2025",
    description: "The name of the risk assessment",
    required: true,
  },
  {
    displayName: "Risk Assessment Name",
    name: "riskAssessmentNameGet",
    type: "string",
    displayOptions: {
      show: {
        resource: ["riskAssessment"],
        operation: ["getByName"],
      },
    },
    default: "",
    placeholder: "Risk Assessment 2025",
    description: "The name of the risk assessment (case-sensitive)",
    required: true,
  },
  {
    displayName: "Risk Assessment Ref ID",
    name: "riskAssessmentRefId",
    type: "string",
    displayOptions: {
      show: {
        resource: ["riskAssessment"],
        operation: ["getByRefId"],
      },
    },
    default: "",
    placeholder: "RA-2025-001",
    description: "The reference ID of the risk assessment",
    required: true,
  },
  {
    displayName: "Folder UUID (Optional)",
    name: "folderIdFilter",
    type: "string",
    displayOptions: {
      show: {
        resource: ["riskAssessment"],
        operation: ["getByName", "getByRefId"],
      },
    },
    default: "",
    placeholder: "domain-uuid-here",
    description: "Filter by folder (domain) UUID",
  },
  {
    displayName: "Perimeter UUID (Optional)",
    name: "perimeterIdFilter",
    type: "string",
    displayOptions: {
      show: {
        resource: ["riskAssessment"],
        operation: ["getByName", "getByRefId"],
      },
    },
    default: "",
    placeholder: "perimeter-uuid-here",
    description: "Filter by perimeter UUID",
  },
];
