import type { INodeProperties } from "n8n-workflow";

export const operations: INodeProperties = {
  displayName: "Operation",
  name: "operation",
  type: "options",
  noDataExpression: true,
  displayOptions: {
    show: {
      resource: ["entityAssessment"],
    },
  },
  options: [
    {
      name: "Create",
      value: "create",
      description:
        "Create a new entity assessment with optional compliance assessment",
      action: "Create entity assessment",
    },
    {
      name: "Get",
      value: "get",
      description: "Get an entity assessment by ID",
      action: "Get an entity assessment",
    },
    {
      name: "Get by Name",
      value: "getByName",
      description: "Get an entity assessment by its name (case-sensitive)",
      action: "Get entity assessment by name",
    },
    {
      name: "Get Many",
      value: "list",
      description: "Get all entity assessments",
      action: "Get many entity assessments",
    },
  ],
  default: "create",
};

export const fields: INodeProperties[] = [
  {
    displayName: "Entity Assessment Name",
    name: "entityAssessmentName",
    type: "string",
    displayOptions: {
      show: {
        resource: ["entityAssessment"],
        operation: ["create", "getByName"],
      },
    },
    default: "",
    placeholder: "Q1 2025 Entity Assessment",
    description: "Name of the entity assessment (case-sensitive)",
    required: true,
  },
  {
    displayName: "Entity UUID",
    name: "entityAssessmentEntityId",
    type: "string",
    displayOptions: {
      show: {
        resource: ["entityAssessment"],
        operation: ["create"],
      },
    },
    default: "",
    placeholder: "entity-uuid-here",
    description: "UUID of the entity being assessed",
    required: true,
  },
  {
    displayName: "Perimeter UUID",
    name: "entityAssessmentPerimeterId",
    type: "string",
    displayOptions: {
      show: {
        resource: ["entityAssessment"],
        operation: ["create"],
      },
    },
    default: "",
    placeholder: "perimeter-uuid-here",
    description: "UUID of the perimeter for this assessment",
    required: true,
  },
  {
    displayName: "Perimeter UUID (Optional)",
    name: "entityAssessmentPerimeterId",
    type: "string",
    displayOptions: {
      show: {
        resource: ["entityAssessment"],
        operation: ["getByName"],
      },
    },
    default: "",
    placeholder: "perimeter-uuid-here",
    description: "UUID of the perimeter to filter by",
  },
  {
    displayName: "Folder UUID (Optional)",
    name: "entityAssessmentFolderId",
    type: "string",
    displayOptions: {
      show: {
        resource: ["entityAssessment"],
        operation: ["getByName"],
      },
    },
    default: "",
    placeholder: "domain-uuid-here",
    description: "UUID of the folder to filter by",
  },
  {
    displayName: "Description",
    name: "entityAssessmentDescription",
    type: "string",
    typeOptions: {
      rows: 3,
    },
    displayOptions: {
      show: {
        resource: ["entityAssessment"],
        operation: ["create"],
      },
    },
    default: "",
    placeholder: "Description of the entity assessment",
    description: "Entity assessment description",
  },
  {
    displayName: "Compliance Assessment UUID",
    name: "entityAssessmentComplianceAssessmentId",
    type: "string",
    displayOptions: {
      show: {
        resource: ["entityAssessment"],
        operation: ["create"],
      },
    },
    default: "",
    placeholder: "compliance-assessment-uuid-here",
    description:
      "UUID of compliance assessment to link (optional - triggers compliance assessment)",
  },
  {
    displayName: "Conclusion",
    name: "entityAssessmentConclusion",
    type: "options",
    displayOptions: {
      show: {
        resource: ["entityAssessment"],
        operation: ["create"],
      },
    },
    options: [
      {
        name: "Blocker",
        value: "blocker",
      },
      {
        name: "Not Applicable",
        value: "not_applicable",
      },
      {
        name: "Not Set",
        value: "",
      },
      {
        name: "Ok",
        value: "ok",
      },
      {
        name: "Warning",
        value: "warning",
      },
    ],
    default: "",
    description: "Conclusion of the entity assessment",
  },
];
