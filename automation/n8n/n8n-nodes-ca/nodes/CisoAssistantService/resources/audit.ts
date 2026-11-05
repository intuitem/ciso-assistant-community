import type { INodeProperties } from "n8n-workflow";

export const operations: INodeProperties = {
  displayName: "Operation",
  name: "operation",
  type: "options",
  noDataExpression: true,
  displayOptions: {
    show: {
      resource: ["audit"],
    },
  },
  options: [
    {
      name: "Get",
      value: "get",
      description: "Get an audit by ID",
      action: "Get an audit",
    },
    {
      name: "Get by Name",
      value: "getByName",
      description: "Get an audit by its name",
      action: "Get audit by name",
    },
    {
      name: "Get by Ref ID",
      value: "getByRefId",
      description: "Get an audit by its reference ID",
      action: "Get audit by ref id",
    },
    {
      name: "Get Many",
      value: "list",
      description: "Get all audits",
      action: "Get many audits",
    },
    {
      name: "Get Requirement Assessment",
      value: "getRequirementAssessment",
      description: "Get a requirement assessment by requirement ref_id",
      action: "Get requirement assessment by ref id",
    },
    {
      name: "Initiate",
      value: "initiate",
      description: "Initiate an audit for a perimeter with a framework",
      action: "Initiate an audit",
    },
    {
      name: "List Requirement Assessments",
      value: "listRequirementAssessments",
      description:
        "Get all requirement assessments for a compliance assessment",
      action: "List requirement assessments",
    },
    {
      name: "Update Requirement Assessment",
      value: "updateRequirementAssessment",
      description: "Update a requirement assessment by requirement ref_id",
      action: "Update requirement assessment",
    },
  ],
  default: "initiate",
};

export const fields: INodeProperties[] = [
  {
    displayName: "Perimeter ID",
    name: "perimeterId",
    type: "string",
    displayOptions: {
      show: {
        resource: ["audit", "riskAssessment"],
        operation: ["initiate"],
      },
    },
    default: "",
    placeholder: "perimeter-uuid-here",
    description: "The UUID of the perimeter",
    required: true,
  },
  {
    displayName: "Framework ID",
    name: "frameworkId",
    type: "string",
    displayOptions: {
      show: {
        resource: ["audit"],
        operation: ["initiate"],
      },
    },
    default: "",
    placeholder: "framework-uuid-here",
    description: "The UUID of the framework to use for the audit",
    required: true,
  },
  {
    displayName: "Audit Name",
    name: "auditName",
    type: "string",
    displayOptions: {
      show: {
        resource: ["audit"],
        operation: ["initiate", "getByName"],
      },
    },
    default: "",
    placeholder: "Security Audit 2025",
    description: "The name of the audit (case sensitive for getByName)",
    required: true,
  },
  {
    displayName: "Audit Ref ID",
    name: "auditRefId",
    type: "string",
    displayOptions: {
      show: {
        resource: ["audit"],
        operation: ["getByRefId"],
      },
    },
    default: "",
    placeholder: "AUDIT-2025-001",
    description: "The reference ID of the audit (case sensitive)",
    required: true,
  },
  {
    displayName: "Folder UUID (Optional)",
    name: "folderIdFilter",
    type: "string",
    displayOptions: {
      show: {
        resource: ["audit"],
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
        resource: ["audit"],
        operation: ["getByName", "getByRefId"],
      },
    },
    default: "",
    placeholder: "perimeter-uuid-here",
    description: "Filter by perimeter UUID",
  },
  {
    displayName: "Requirement Ref ID",
    name: "requirementRefId",
    type: "string",
    displayOptions: {
      show: {
        resource: ["audit"],
        operation: ["getRequirementAssessment", "updateRequirementAssessment"],
      },
    },
    default: "",
    placeholder: "REQ-001",
    description: "The reference ID of the requirement (case sensitive)",
    required: true,
  },
  {
    displayName: "Compliance Assessment ID",
    name: "complianceAssessmentId",
    type: "string",
    displayOptions: {
      show: {
        resource: ["audit"],
        operation: [
          "getRequirementAssessment",
          "updateRequirementAssessment",
          "listRequirementAssessments",
        ],
      },
    },
    default: "",
    placeholder: "audit-uuid-here",
    description: "The UUID of the compliance assessment (audit)",
    required: true,
  },
  {
    displayName: "Status",
    name: "requirementAssessmentStatus",
    type: "options",
    displayOptions: {
      show: {
        resource: ["audit"],
        operation: ["updateRequirementAssessment"],
        "@version": [1],
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
        name: "In Review",
        value: "in_review",
      },
      {
        name: "To Do",
        value: "to_do",
      },
    ],
    default: "to_do",
    description: "The status of the requirement assessment",
  },
  {
    displayName: "Status",
    name: "requirementAssessmentStatus",
    type: "options",
    displayOptions: {
      show: {
        resource: ["audit"],
        operation: ["updateRequirementAssessment"],
        "@version": [
          {
            _cnd: {
              gte: 2,
            },
          },
        ],
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
        name: "In Review",
        value: "in_review",
      },
      {
        name: "No Change",
        value: "",
      },
      {
        name: "To Do",
        value: "to_do",
      },
    ],
    default: "",
    description: "The status of the requirement assessment",
  },
  {
    displayName: "Result",
    name: "requirementAssessmentResult",
    type: "options",
    displayOptions: {
      show: {
        resource: ["audit"],
        operation: ["updateRequirementAssessment"],
        "@version": [1],
      },
    },
    options: [
      {
        name: "Compliant",
        value: "compliant",
      },
      {
        name: "Non-Compliant",
        value: "non_compliant",
      },
      {
        name: "Not Applicable",
        value: "not_applicable",
      },
      {
        name: "Not Assessed",
        value: "not_assessed",
      },
      {
        name: "Partially Compliant",
        value: "partially_compliant",
      },
    ],
    default: "not_assessed",
    description: "The compliance result",
  },
  {
    displayName: "Result",
    name: "requirementAssessmentResult",
    type: "options",
    displayOptions: {
      show: {
        resource: ["audit"],
        operation: ["updateRequirementAssessment"],
        "@version": [
          {
            _cnd: {
              gte: 2,
            },
          },
        ],
      },
    },
    options: [
      {
        name: "Compliant",
        value: "compliant",
      },
      {
        name: "No Change",
        value: "",
      },
      {
        name: "Non-Compliant",
        value: "non_compliant",
      },
      {
        name: "Not Applicable",
        value: "not_applicable",
      },
      {
        name: "Not Assessed",
        value: "not_assessed",
      },
      {
        name: "Partially Compliant",
        value: "partially_compliant",
      },
    ],
    default: "",
    description: "The compliance result",
  },
  {
    displayName: "Observation",
    name: "requirementAssessmentObservation",
    type: "string",
    typeOptions: {
      rows: 3,
    },
    displayOptions: {
      show: {
        resource: ["audit"],
        operation: ["updateRequirementAssessment"],
      },
    },
    default: "",
    placeholder: "Assessment observations and notes",
    description: "Observation notes for the requirement assessment",
  },
  {
    displayName: "Score",
    name: "requirementAssessmentScore",
    type: "number",
    displayOptions: {
      show: {
        resource: ["audit"],
        operation: ["updateRequirementAssessment"],
        "@version": [1],
      },
    },
    default: 0,
    placeholder: "0",
    description: "Score for the requirement assessment",
  },
  {
    displayName: "Score",
    name: "requirementAssessmentScore",
    type: "number",
    displayOptions: {
      show: {
        resource: ["audit"],
        operation: ["updateRequirementAssessment"],
        "@version": [
          {
            _cnd: {
              gte: 2,
            },
          },
        ],
      },
    },
    default: -1,
    placeholder: "0",
    description:
      "Score for the requirement assessment. Leave at -1 to keep the current score.",
  },
];
