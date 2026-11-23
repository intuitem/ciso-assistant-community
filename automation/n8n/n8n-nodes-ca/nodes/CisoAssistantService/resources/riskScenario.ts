import type { INodeProperties } from "n8n-workflow";

export const operations: INodeProperties = {
  displayName: "Operation",
  name: "operation",
  type: "options",
  noDataExpression: true,
  displayOptions: {
    show: {
      resource: ["riskScenario"],
    },
  },
  options: [
    {
      name: "Create",
      value: "create",
      description: "Create a new risk scenario",
      action: "Create risk scenario",
    },
    {
      name: "Get",
      value: "get",
      description: "Get a risk scenario by ID",
      action: "Get a risk scenario",
    },
    {
      name: "Get by Name",
      value: "getByName",
      description: "Get a risk scenario by its name (case-sensitive)",
      action: "Get risk scenario by name",
    },
    {
      name: "Get Many",
      value: "list",
      description: "Get all risk scenarios",
      action: "Get many risk scenarios",
    },
    {
      name: "Update",
      value: "update",
      description: "Update an existing risk scenario",
      action: "Update risk scenario",
    },
  ],
  default: "create",
};

export const fields: INodeProperties[] = [
  {
    displayName: "Risk Scenario Name",
    name: "riskScenarioName",
    type: "string",
    displayOptions: {
      show: {
        resource: ["riskScenario"],
        operation: ["create", "getByName"],
      },
    },
    default: "",
    placeholder: "Data Loss via Ransomware",
    description: "Name of the risk scenario (case-sensitive)",
    required: true,
  },
  {
    displayName: "Risk Assessment UUID",
    name: "riskScenarioRiskAssessmentId",
    type: "string",
    displayOptions: {
      show: {
        resource: ["riskScenario"],
        operation: ["create", "getByName"],
      },
    },
    default: "",
    placeholder: "risk-assessment-uuid-here",
    description: "UUID of the risk assessment this scenario belongs to",
    required: true,
  },
  {
    displayName: "Risk Scenario UUID",
    name: "riskScenarioId",
    type: "string",
    displayOptions: {
      show: {
        resource: ["riskScenario"],
        operation: ["update"],
      },
    },
    default: "",
    placeholder: "risk-scenario-uuid-here",
    description: "The UUID of the risk scenario to update",
    required: true,
  },
  {
    displayName: "Description",
    name: "riskScenarioDescription",
    type: "string",
    typeOptions: {
      rows: 3,
    },
    displayOptions: {
      show: {
        resource: ["riskScenario"],
        operation: ["create", "update"],
      },
    },
    default: "",
    placeholder: "Description of the risk scenario",
    description: "Risk scenario description",
  },
  {
    displayName: "Reference ID",
    name: "riskScenarioRefId",
    type: "string",
    displayOptions: {
      show: {
        resource: ["riskScenario"],
        operation: ["create", "update"],
      },
    },
    default: "",
    placeholder: "RISK-001",
    description: "Reference identifier for the risk scenario",
  },
  {
    displayName: "Treatment",
    name: "riskScenarioTreatment",
    type: "options",
    displayOptions: {
      show: {
        resource: ["riskScenario"],
        operation: ["create", "update"],
      },
    },
    options: [
      {
        name: "Accept",
        value: "accept",
      },
      {
        name: "Avoid",
        value: "avoid",
      },
      {
        name: "Mitigate",
        value: "mitigate",
      },
      {
        name: "Open",
        value: "open",
      },
      {
        name: "Transfer",
        value: "transfer",
      },
    ],
    default: "open",
    description: "Treatment status for the risk",
  },
  {
    displayName: "Existing Controls",
    name: "riskScenarioExistingControls",
    type: "string",
    typeOptions: {
      rows: 3,
    },
    displayOptions: {
      show: {
        resource: ["riskScenario"],
        operation: ["create", "update"],
      },
    },
    default: "",
    placeholder: "Description of existing controls",
    description: "The existing controls to manage this risk",
  },
  {
    displayName: "Inherent Probability",
    name: "riskScenarioInherentProba",
    type: "number",
    displayOptions: {
      show: {
        resource: ["riskScenario"],
        operation: ["create", "update"],
      },
    },
    default: -1,
    description: "Inherent probability level (-1 for undefined)",
  },
  {
    displayName: "Inherent Impact",
    name: "riskScenarioInherentImpact",
    type: "number",
    displayOptions: {
      show: {
        resource: ["riskScenario"],
        operation: ["create", "update"],
      },
    },
    default: -1,
    description: "Inherent impact level (-1 for undefined)",
  },
  {
    displayName: "Current Probability",
    name: "riskScenarioCurrentProba",
    type: "number",
    displayOptions: {
      show: {
        resource: ["riskScenario"],
        operation: ["create", "update"],
      },
    },
    default: -1,
    description: "Current probability level (-1 for undefined)",
  },
  {
    displayName: "Current Impact",
    name: "riskScenarioCurrentImpact",
    type: "number",
    displayOptions: {
      show: {
        resource: ["riskScenario"],
        operation: ["create", "update"],
      },
    },
    default: -1,
    description: "Current impact level (-1 for undefined)",
  },
  {
    displayName: "Residual Probability",
    name: "riskScenarioResidualProba",
    type: "number",
    displayOptions: {
      show: {
        resource: ["riskScenario"],
        operation: ["create", "update"],
      },
    },
    default: -1,
    description: "Residual probability level (-1 for undefined)",
  },
  {
    displayName: "Residual Impact",
    name: "riskScenarioResidualImpact",
    type: "number",
    displayOptions: {
      show: {
        resource: ["riskScenario"],
        operation: ["create", "update"],
      },
    },
    default: -1,
    description: "Residual impact level (-1 for undefined)",
  },
  {
    displayName: "Strength of Knowledge",
    name: "riskScenarioStrengthOfKnowledge",
    type: "number",
    displayOptions: {
      show: {
        resource: ["riskScenario"],
        operation: ["create", "update"],
      },
    },
    default: -1,
    description:
      "Strength of knowledge supporting the assessment (-1 for undefined, 0=Low, 1=Medium, 2=High)",
  },
];
