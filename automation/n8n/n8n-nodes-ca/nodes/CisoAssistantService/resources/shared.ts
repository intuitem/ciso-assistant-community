import type { INodeProperties } from "n8n-workflow";

export const sharedFields: INodeProperties[] = [
  {
    displayName: "ID",
    name: "id",
    type: "string",
    required: true,
    default: "",
    displayOptions: {
      show: {
        operation: ["get"],
      },
    },
    description: "UUID of the object to retrieve",
  },
  {
    displayName: "Folder UUID (Optional)",
    name: "folderIdFilter",
    type: "string",
    displayOptions: {
      show: {
        resource: [
          "domain",
          "perimeter",
          "asset",
          "audit",
          "riskAssessment",
          "incident",
          "vulnerability",
          "appliedControl",
          "taskOccurrence",
          "taskDefinition",
          "findingsAssessment",
          "finding",
          "securityException",
          "evidence",
          "entity",
          "solution",
          "representative",
          "entityAssessment",
          "rightRequest",
          "dataBreach",
          "riskScenario",
        ],
        operation: ["list"],
      },
    },
    default: "",
    placeholder: "domain-uuid-here",
    description: "Filter results by folder (domain) UUID",
  },
  {
    displayName: "Perimeter UUID (Optional)",
    name: "perimeterIdFilter",
    type: "string",
    displayOptions: {
      show: {
        resource: ["audit", "riskAssessment", "findingsAssessment"],
        operation: ["list"],
      },
    },
    default: "",
    placeholder: "perimeter-uuid-here",
    description: "Filter results by perimeter UUID",
  },
  {
    displayName: "Additional Fields",
    name: "additionalFields",
    type: "collection",
    default: {},
    placeholder: "Add Field",
    displayOptions: {
      show: {
        resource: ["asset", "domain", "perimeter"],
        operation: ["create"],
      },
    },
    options: [
      {
        displayName: "Business Value",
        name: "businessValue",
        type: "options",
        displayOptions: {
          show: {
            "/resource": ["asset"],
          },
        },
        options: [
          {
            name: "Critical",
            value: "critical",
          },
          {
            name: "High",
            value: "high",
          },
          {
            name: "Low",
            value: "low",
          },
          {
            name: "Medium",
            value: "medium",
          },
        ],
        default: "medium",
        description: "Business value of the asset",
      },
      {
        displayName: "Owner",
        name: "owner",
        type: "string",
        default: "",
        description: "Owner of the resource",
      },
      {
        displayName: "Tags",
        name: "tags",
        type: "string",
        default: "",
        placeholder: "tag1,tag2,tag3",
        description: "Comma-separated list of tags",
      },
    ],
  },
];
