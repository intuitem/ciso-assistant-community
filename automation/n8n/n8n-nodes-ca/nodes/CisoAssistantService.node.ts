import type {
  INodeType,
  INodeTypeDescription,
  IExecuteFunctions,
  INodeExecutionData,
} from "n8n-workflow";

import type {
  ICisoAssistantCredentials,
  IResourceContext,
  ResourceType,
} from "./types";

import { resourceRegistry } from "./registry/ResourceRegistry";

export class CisoAssistantService implements INodeType {
  description: INodeTypeDescription = {
    displayName: "CISO Assistant",
    name: "cisoAssistantService",
    icon: "fa:robot",
    group: ["transform"],
    version: 1,
    subtitle: '={{$parameter["resource"] + ": " + $parameter["operation"]}}',
    description: "Interact with CISO Assistant API",
    defaults: {
      name: "CA node ",
    },
    inputs: ["main"],
    outputs: ["main"],
    credentials: [
      {
        name: "cisoAssistantApi",
        required: true,
      },
    ],
    properties: [
      // Resource selector
      {
        displayName: "Resource",
        name: "resource",
        type: "options",
        noDataExpression: true,
        options: [
          {
            name: "System",
            value: "system",
          },
          {
            name: "Domain",
            value: "domain",
          },
          {
            name: "Perimeter",
            value: "perimeter",
          },
          {
            name: "Asset",
            value: "asset",
          },
          {
            name: "Audit",
            value: "audit",
          },
          {
            name: "Risk Assessment",
            value: "riskAssessment",
          },
          {
            name: "Incident",
            value: "incident",
          },
          {
            name: "Vulnerability",
            value: "vulnerability",
          },
          {
            name: "Applied Control",
            value: "appliedControl",
          },
          {
            name: "Task Occurrence",
            value: "taskOccurrence",
          },
          {
            name: "Task Definition",
            value: "taskDefinition",
          },
          {
            name: "Findings Tracking",
            value: "findingsAssessment",
          },
          {
            name: "Finding",
            value: "finding",
          },
          {
            name: "Security Exception",
            value: "securityException",
          },
          {
            name: "Evidence",
            value: "evidence",
          },
          {
            name: "Entity",
            value: "entity",
          },
          {
            name: "Solution",
            value: "solution",
          },
          {
            name: "Representative",
            value: "representative",
          },
          {
            name: "Entity Assessment",
            value: "entityAssessment",
          },
          {
            name: "Right Request",
            value: "rightRequest",
          },
          {
            name: "Data Breach",
            value: "dataBreach",
          },
          {
            name: "Risk Scenario",
            value: "riskScenario",
          },
          {
            name: "Framework",
            value: "framework",
          },
          {
            name: "Risk Matrix",
            value: "riskMatrix",
          },
        ],
        default: "system",
      },
      // System operations
      {
        displayName: "Operation",
        name: "operation",
        type: "options",
        noDataExpression: true,
        displayOptions: {
          show: {
            resource: ["system"],
          },
        },
        options: [
          {
            name: "Get Build Info",
            value: "getBuild",
            description: "Get build information from CISO Assistant",
            action: "Get build information",
          },
          {
            name: "Get User by Email",
            value: "getUserByEmail",
            description: "Get a user by their email address",
            action: "Get user by email",
          },
          {
            name: "List Users",
            value: "listUsers",
            description: "Get all users in the system",
            action: "List users",
          },
        ],
        default: "getBuild",
      },
      // Domain operations
      {
        displayName: "Operation",
        name: "operation",
        type: "options",
        noDataExpression: true,
        displayOptions: {
          show: {
            resource: ["domain"],
          },
        },
        options: [
          {
            name: "Create",
            value: "create",
            description: "Create a new domain",
            action: "Create a domain",
          },
          {
            name: "Get by Name",
            value: "getByName",
            description: "Get a domain by its name",
            action: "Get domain by name",
          },
          {
            name: "List",
            value: "list",
            description: "Get all domains",
            action: "List domains",
          },
        ],
        default: "create",
      },
      // Perimeter operations
      {
        displayName: "Operation",
        name: "operation",
        type: "options",
        noDataExpression: true,
        displayOptions: {
          show: {
            resource: ["perimeter"],
          },
        },
        options: [
          {
            name: "Create",
            value: "create",
            description: "Create a new perimeter",
            action: "Create a perimeter",
          },
          {
            name: "Get by Name",
            value: "getByName",
            description: "Get a perimeter by its name",
            action: "Get perimeter by name",
          },
          {
            name: "List",
            value: "list",
            description: "Get all perimeters",
            action: "List perimeters",
          },
        ],
        default: "create",
      },
      // Asset operations
      {
        displayName: "Operation",
        name: "operation",
        type: "options",
        noDataExpression: true,
        displayOptions: {
          show: {
            resource: ["asset"],
          },
        },
        options: [
          {
            name: "Create",
            value: "create",
            description: "Create a new asset",
            action: "Create an asset",
          },
          {
            name: "Get by Name",
            value: "getByName",
            description: "Get an asset by its name (case-sensitive)",
            action: "Get asset by name",
          },
          {
            name: "List",
            value: "list",
            description: "Get all assets",
            action: "List assets",
          },
          {
            name: "Update",
            value: "update",
            description: "Update an existing asset",
            action: "Update asset",
          },
        ],
        default: "create",
      },
      // Audit operations
      {
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
            name: "Initiate",
            value: "initiate",
            description: "Initiate an audit for a perimeter with a framework",
            action: "Initiate an audit",
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
            action: "Get audit by ref_id",
          },
          {
            name: "Get Requirement Assessment",
            value: "getRequirementAssessment",
            description: "Get a requirement assessment by requirement ref_id",
            action: "Get requirement assessment by ref_id",
          },
          {
            name: "Update Requirement Assessment",
            value: "updateRequirementAssessment",
            description:
              "Update a requirement assessment by requirement ref_id",
            action: "Update requirement assessment",
          },
          {
            name: "List Requirement Assessments",
            value: "listRequirementAssessments",
            description:
              "Get all requirement assessments for a compliance assessment",
            action: "List requirement assessments",
          },
          {
            name: "List",
            value: "list",
            description: "Get all audits",
            action: "List audits",
          },
        ],
        default: "initiate",
      },
      // Risk Assessment operations
      {
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
            name: "Initiate",
            value: "initiate",
            description:
              "Initiate a risk assessment for a perimeter with a risk matrix",
            action: "Initiate a risk assessment",
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
            name: "List",
            value: "list",
            description: "Get all risk assessments",
            action: "List risk assessments",
          },
        ],
        default: "initiate",
      },
      // Incident operations
      {
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
            name: "List",
            value: "list",
            description: "Get all incidents",
            action: "List incidents",
          },
          {
            name: "Update",
            value: "update",
            description: "Update an existing incident",
            action: "Update incident",
          },
        ],
        default: "create",
      },
      // Vulnerability operations
      {
        displayName: "Operation",
        name: "operation",
        type: "options",
        noDataExpression: true,
        displayOptions: {
          show: {
            resource: ["vulnerability"],
          },
        },
        options: [
          {
            name: "Create",
            value: "create",
            description: "Create a new vulnerability",
            action: "Create a vulnerability",
          },
          {
            name: "List",
            value: "list",
            description: "Get all vulnerabilities",
            action: "List vulnerabilities",
          },
          {
            name: "Update",
            value: "update",
            description: "Update an existing vulnerability",
            action: "Update vulnerability",
          },
        ],
        default: "create",
      },
      // Applied Control operations
      {
        displayName: "Operation",
        name: "operation",
        type: "options",
        noDataExpression: true,
        displayOptions: {
          show: {
            resource: ["appliedControl"],
          },
        },
        options: [
          {
            name: "Create",
            value: "create",
            description: "Create a new applied control",
            action: "Create an applied control",
          },
          {
            name: "Get by Name",
            value: "getByName",
            description: "Get an applied control by its name",
            action: "Get applied control by name",
          },
          {
            name: "List",
            value: "list",
            description: "Get all applied controls",
            action: "List applied controls",
          },
          {
            name: "Update",
            value: "update",
            description: "Update an applied control by UUID",
            action: "Update applied control",
          },
        ],
        default: "create",
      },
      // Task Occurrence operations
      {
        displayName: "Operation",
        name: "operation",
        type: "options",
        noDataExpression: true,
        displayOptions: {
          show: {
            resource: ["taskOccurrence"],
          },
        },
        options: [
          {
            name: "Create",
            value: "create",
            description: "Create a new task occurrence",
            action: "Create a task occurrence",
          },
          {
            name: "List",
            value: "list",
            description: "Get all task occurrences",
            action: "List task occurrences",
          },
          {
            name: "Update",
            value: "update",
            description: "Update a task occurrence by UUID",
            action: "Update task occurrence",
          },
        ],
        default: "create",
      },
      // Task Definition operations
      {
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
            name: "Get by Name",
            value: "getByName",
            description: "Get a task definition by its name",
            action: "Get task definition by name",
          },
          {
            name: "List",
            value: "list",
            description: "Get all task definitions",
            action: "List task definitions",
          },
          {
            name: "Update",
            value: "update",
            description: "Update a task definition by UUID",
            action: "Update task definition",
          },
        ],
        default: "create",
      },
      // Findings Assessment operations
      {
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
            name: "List",
            value: "list",
            description: "Get all findings tracking assessments",
            action: "List findings tracking",
          },
          {
            name: "Update",
            value: "update",
            description: "Update a findings tracking by UUID",
            action: "Update findings tracking",
          },
        ],
        default: "create",
      },
      // Finding operations
      {
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
            name: "Get by Name",
            value: "getByName",
            description: "Get a finding by its name (case-sensitive)",
            action: "Get finding by name",
          },
          {
            name: "List",
            value: "list",
            description: "Get all findings",
            action: "List findings",
          },
          {
            name: "Update",
            value: "update",
            description: "Update a finding by UUID",
            action: "Update finding",
          },
        ],
        default: "create",
      },
      // Security Exception operations
      {
        displayName: "Operation",
        name: "operation",
        type: "options",
        noDataExpression: true,
        displayOptions: {
          show: {
            resource: ["securityException"],
          },
        },
        options: [
          {
            name: "Create",
            value: "create",
            description: "Create a new security exception",
            action: "Create security exception",
          },
          {
            name: "Get by Name",
            value: "getByName",
            description:
              "Get a security exception by its name (case-sensitive)",
            action: "Get security exception by name",
          },
          {
            name: "List",
            value: "list",
            description: "Get all security exceptions",
            action: "List security exceptions",
          },
          {
            name: "Update",
            value: "update",
            description: "Update a security exception by UUID",
            action: "Update security exception",
          },
        ],
        default: "create",
      },
      // Evidence operations
      {
        displayName: "Operation",
        name: "operation",
        type: "options",
        noDataExpression: true,
        displayOptions: {
          show: {
            resource: ["evidence"],
          },
        },
        options: [
          {
            name: "Create",
            value: "create",
            description: "Create a new evidence",
            action: "Create evidence",
          },
          {
            name: "Get by Name",
            value: "getByName",
            description: "Get an evidence by its name (case-sensitive)",
            action: "Get evidence by name",
          },
          {
            name: "List",
            value: "list",
            description: "Get all evidences",
            action: "List evidences",
          },
          {
            name: "Update Envelope",
            value: "update",
            description:
              "Update evidence envelope data (name, description, status, etc.)",
            action: "Update evidence envelope",
          },
          {
            name: "Submit Revision",
            value: "submitRevision",
            description:
              "Submit a new revision of the evidence (link or attachment)",
            action: "Submit evidence revision",
          },
          {
            name: "List Revisions",
            value: "listRevisions",
            description: "List all revisions of an evidence",
            action: "List evidence revisions",
          },
        ],
        default: "create",
      },
      // Entity operations
      {
        displayName: "Operation",
        name: "operation",
        type: "options",
        noDataExpression: true,
        displayOptions: {
          show: {
            resource: ["entity"],
          },
        },
        options: [
          {
            name: "Create",
            value: "create",
            description: "Create a new entity",
            action: "Create entity",
          },
          {
            name: "Get by Name",
            value: "getByName",
            description: "Get an entity by its name (case-sensitive)",
            action: "Get entity by name",
          },
          {
            name: "List",
            value: "list",
            description: "Get all entities",
            action: "List entities",
          },
        ],
        default: "create",
      },
      // Solution operations
      {
        displayName: "Operation",
        name: "operation",
        type: "options",
        noDataExpression: true,
        displayOptions: {
          show: {
            resource: ["solution"],
          },
        },
        options: [
          {
            name: "Create",
            value: "create",
            description: "Create a new solution from an entity",
            action: "Create solution",
          },
          {
            name: "Get by Name",
            value: "getByName",
            description: "Get a solution by its name (case-sensitive)",
            action: "Get solution by name",
          },
          {
            name: "List",
            value: "list",
            description: "Get all solutions",
            action: "List solutions",
          },
        ],
        default: "create",
      },
      // Representative operations
      {
        displayName: "Operation",
        name: "operation",
        type: "options",
        noDataExpression: true,
        displayOptions: {
          show: {
            resource: ["representative"],
          },
        },
        options: [
          {
            name: "Create",
            value: "create",
            description: "Create a new representative for an entity",
            action: "Create representative",
          },
          {
            name: "List",
            value: "list",
            description: "Get all representatives",
            action: "List representatives",
          },
        ],
        default: "create",
      },
      // Entity Assessment operations
      {
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
            name: "Get by Name",
            value: "getByName",
            description:
              "Get an entity assessment by its name (case-sensitive)",
            action: "Get entity assessment by name",
          },
          {
            name: "List",
            value: "list",
            description: "Get all entity assessments",
            action: "List entity assessments",
          },
        ],
        default: "create",
      },
      // Right Request operations
      {
        displayName: "Operation",
        name: "operation",
        type: "options",
        noDataExpression: true,
        displayOptions: {
          show: {
            resource: ["rightRequest"],
          },
        },
        options: [
          {
            name: "Create",
            value: "create",
            description: "Create a new right request",
            action: "Create right request",
          },
          {
            name: "Get by Name",
            value: "getByName",
            description: "Get a right request by its name (case-sensitive)",
            action: "Get right request by name",
          },
          {
            name: "List",
            value: "list",
            description: "Get all right requests",
            action: "List right requests",
          },
          {
            name: "Update",
            value: "update",
            description: "Update an existing right request",
            action: "Update right request",
          },
        ],
        default: "create",
      },
      // Data Breach operations
      {
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
            name: "Get by Name",
            value: "getByName",
            description: "Get a data breach by its name (case-sensitive)",
            action: "Get data breach by name",
          },
          {
            name: "List",
            value: "list",
            description: "Get all data breaches",
            action: "List data breaches",
          },
          {
            name: "Update",
            value: "update",
            description: "Update an existing data breach",
            action: "Update data breach",
          },
        ],
        default: "create",
      },
      // Risk Scenario operations
      {
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
            name: "Get by Name",
            value: "getByName",
            description: "Get a risk scenario by its name (case-sensitive)",
            action: "Get risk scenario by name",
          },
          {
            name: "List",
            value: "list",
            description: "Get all risk scenarios",
            action: "List risk scenarios",
          },
          {
            name: "Update",
            value: "update",
            description: "Update an existing risk scenario",
            action: "Update risk scenario",
          },
        ],
        default: "create",
      },
      // Framework operations
      {
        displayName: "Operation",
        name: "operation",
        type: "options",
        noDataExpression: true,
        displayOptions: {
          show: {
            resource: ["framework"],
          },
        },
        options: [
          {
            name: "List",
            value: "list",
            description: "Get all loaded frameworks",
            action: "List frameworks",
          },
        ],
        default: "list",
      },
      // Risk Matrix operations
      {
        displayName: "Operation",
        name: "operation",
        type: "options",
        noDataExpression: true,
        displayOptions: {
          show: {
            resource: ["riskMatrix"],
          },
        },
        options: [
          {
            name: "List",
            value: "list",
            description: "Get all risk matrices",
            action: "List risk matrices",
          },
        ],
        default: "list",
      },
      // System fields
      {
        displayName: "User Email",
        name: "userEmail",
        type: "string",
        displayOptions: {
          show: {
            resource: ["system"],
            operation: ["getUserByEmail"],
          },
        },
        default: "",
        placeholder: "user@example.com",
        description: "Email address of the user",
        required: true,
      },
      // Perimeter fields
      {
        displayName: "Perimeter Name",
        name: "perimeterName",
        type: "string",
        displayOptions: {
          show: {
            resource: ["perimeter"],
            operation: ["create", "getByName"],
          },
        },
        default: "",
        placeholder: "My Security Perimeter",
        description: "The name of the perimeter (case sensitive for getByName)",
        required: true,
      },
      {
        displayName: "Folder ID",
        name: "folderId",
        type: "string",
        displayOptions: {
          show: {
            resource: ["perimeter"],
            operation: ["getByName"],
          },
        },
        default: "",
        placeholder: "domain-uuid-here",
        description: "The UUID of the folder (domain) to search within",
        required: true,
      },
      {
        displayName: "Perimeter Description",
        name: "perimeterDescription",
        type: "string",
        typeOptions: {
          rows: 3,
        },
        displayOptions: {
          show: {
            resource: ["perimeter"],
            operation: ["create"],
          },
        },
        default: "",
        placeholder: "Description of the security perimeter",
        description: "The description of the perimeter",
      },
      {
        displayName: "Folder ID",
        name: "folderId",
        type: "string",
        displayOptions: {
          show: {
            resource: ["perimeter"],
            operation: ["create"],
          },
        },
        default: "",
        placeholder: "domain-uuid-here",
        description:
          "The UUID of the folder (domain) this perimeter belongs to",
        required: true,
      },
      // Domain fields
      {
        displayName: "Domain Name",
        name: "domainName",
        type: "string",
        displayOptions: {
          show: {
            resource: ["domain"],
            operation: ["create", "getByName"],
          },
        },
        default: "",
        placeholder: "IT Infrastructure",
        description: "The name of the domain (case sensitive for getByName)",
        required: true,
      },
      {
        displayName: "Domain Description",
        name: "domainDescription",
        type: "string",
        typeOptions: {
          rows: 3,
        },
        displayOptions: {
          show: {
            resource: ["domain"],
            operation: ["create"],
          },
        },
        default: "",
        placeholder: "Description of the domain",
        description: "The description of the domain",
      },
      // Asset fields
      {
        displayName: "Asset Name",
        name: "assetName",
        type: "string",
        displayOptions: {
          show: {
            resource: ["asset"],
            operation: ["create", "getByName"],
          },
        },
        default: "",
        placeholder: "Web Server",
        description: "The name of the asset (case-sensitive)",
        required: true,
      },
      {
        displayName: "Folder UUID",
        name: "folderId",
        type: "string",
        displayOptions: {
          show: {
            resource: ["asset"],
            operation: ["create"],
          },
        },
        default: "",
        placeholder: "domain-uuid-here",
        description: "The UUID of the folder (domain) this asset belongs to",
        required: true,
      },
      {
        displayName: "Folder UUID (Optional)",
        name: "folderId",
        type: "string",
        displayOptions: {
          show: {
            resource: ["asset"],
            operation: ["getByName"],
          },
        },
        default: "",
        placeholder: "domain-uuid-here",
        description: "The UUID of the folder (domain) to filter by",
      },
      {
        displayName: "Asset UUID",
        name: "assetId",
        type: "string",
        displayOptions: {
          show: {
            resource: ["asset"],
            operation: ["update"],
          },
        },
        default: "",
        placeholder: "asset-uuid-here",
        description: "The UUID of the asset to update",
        required: true,
      },
      {
        displayName: "Asset Description",
        name: "assetDescription",
        type: "string",
        typeOptions: {
          rows: 3,
        },
        displayOptions: {
          show: {
            resource: ["asset"],
            operation: ["create", "update"],
          },
        },
        default: "",
        placeholder: "Description of the asset",
        description: "The description of the asset",
      },
      {
        displayName: "Asset Type",
        name: "assetType",
        type: "options",
        displayOptions: {
          show: {
            resource: ["asset"],
            operation: ["create", "update"],
          },
        },
        options: [
          {
            name: "Primary",
            value: "PR",
          },
          {
            name: "Support",
            value: "SP",
          },
        ],
        default: "PR",
        description: "The type of the asset",
      },
      {
        displayName: "Asset Name (Update)",
        name: "assetNameUpdate",
        type: "string",
        displayOptions: {
          show: {
            resource: ["asset"],
            operation: ["update"],
          },
        },
        default: "",
        placeholder: "New Asset Name",
        description: "New name for the asset (optional)",
      },
      // Audit fields
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
      // Requirement Assessment fields
      {
        displayName: "Requirement Ref ID",
        name: "requirementRefId",
        type: "string",
        displayOptions: {
          show: {
            resource: ["audit"],
            operation: [
              "getRequirementAssessment",
              "updateRequirementAssessment",
            ],
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
          },
        },
        options: [
          { name: "To Do", value: "to_do" },
          { name: "In Progress", value: "in_progress" },
          { name: "In Review", value: "in_review" },
          { name: "Done", value: "done" },
        ],
        default: "to_do",
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
          },
        },
        options: [
          { name: "Not Assessed", value: "not_assessed" },
          { name: "Compliant", value: "compliant" },
          { name: "Partially Compliant", value: "partially_compliant" },
          { name: "Non-Compliant", value: "non_compliant" },
          { name: "Not Applicable", value: "not_applicable" },
        ],
        default: "not_assessed",
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
          },
        },
        default: 0,
        placeholder: "0",
        description: "Score for the requirement assessment",
      },
      // Risk Assessment fields
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
      // Incident fields
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
          { name: "New", value: "new" },
          { name: "Ongoing", value: "ongoing" },
          { name: "Resolved", value: "resolved" },
          { name: "Closed", value: "closed" },
          { name: "Dismissed", value: "dismissed" },
        ],
        default: "new",
        description: "The status of the incident",
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
          { name: "Critical", value: 1 },
          { name: "Major", value: 2 },
          { name: "Moderate", value: 3 },
          { name: "Minor", value: 4 },
          { name: "Low", value: 5 },
          { name: "Unknown", value: 6 },
        ],
        default: 3,
        description: "The severity of the incident",
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
          { name: "Internal", value: "internally_detected" },
          { name: "External", value: "externally_detected" },
        ],
        default: "internally_detected",
        description: "How the incident was detected",
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
      // Vulnerability fields
      {
        displayName: "Vulnerability Name",
        name: "vulnerabilityName",
        type: "string",
        displayOptions: {
          show: {
            resource: ["vulnerability"],
            operation: ["create"],
          },
        },
        default: "",
        placeholder: "CVE-2025-0001",
        description: "The name of the vulnerability",
        required: true,
      },
      {
        displayName: "Vulnerability UUID",
        name: "vulnerabilityId",
        type: "string",
        displayOptions: {
          show: {
            resource: ["vulnerability"],
            operation: ["update"],
          },
        },
        default: "",
        placeholder: "vulnerability-uuid-here",
        description: "The UUID of the vulnerability to update",
        required: true,
      },
      {
        displayName: "Folder ID",
        name: "folderId",
        type: "string",
        displayOptions: {
          show: {
            resource: ["vulnerability"],
            operation: ["create"],
          },
        },
        default: "",
        placeholder: "domain-uuid-here",
        description:
          "The UUID of the folder (domain) this vulnerability belongs to",
        required: true,
      },
      {
        displayName: "Vulnerability Description",
        name: "vulnerabilityDescription",
        type: "string",
        typeOptions: {
          rows: 3,
        },
        displayOptions: {
          show: {
            resource: ["vulnerability"],
            operation: ["create", "update"],
          },
        },
        default: "",
        placeholder: "Description of the vulnerability",
        description: "The description of the vulnerability",
      },
      {
        displayName: "Status",
        name: "vulnerabilityStatus",
        type: "options",
        displayOptions: {
          show: {
            resource: ["vulnerability"],
            operation: ["create", "update"],
          },
        },
        options: [
          { name: "Undefined", value: "--" },
          { name: "Potential", value: "potential" },
          { name: "Exploitable", value: "exploitable" },
          { name: "Mitigated", value: "mitigated" },
          { name: "Fixed", value: "fixed" },
          { name: "Not Exploitable", value: "not_exploitable" },
          { name: "Unaffected", value: "unaffected" },
        ],
        default: "--",
        description: "The status of the vulnerability",
      },
      {
        displayName: "Severity",
        name: "vulnerabilitySeverity",
        type: "options",
        displayOptions: {
          show: {
            resource: ["vulnerability"],
            operation: ["create", "update"],
          },
        },
        options: [
          { name: "Undefined", value: -1 },
          { name: "Info", value: 0 },
          { name: "Low", value: 1 },
          { name: "Medium", value: 2 },
          { name: "High", value: 3 },
          { name: "Critical", value: 4 },
        ],
        default: -1,
        description: "The severity of the vulnerability",
      },
      {
        displayName: "Reference ID",
        name: "vulnerabilityRefId",
        type: "string",
        displayOptions: {
          show: {
            resource: ["vulnerability"],
            operation: ["create", "update"],
          },
        },
        default: "",
        placeholder: "VULN-2025-001",
        description: "Reference ID for the vulnerability",
      },
      // Applied Control fields
      {
        displayName: "Applied Control Name",
        name: "appliedControlName",
        type: "string",
        displayOptions: {
          show: {
            resource: ["appliedControl"],
            operation: ["create", "getByName"],
          },
        },
        default: "",
        placeholder: "Access Control Implementation",
        description:
          "The name of the applied control (case sensitive for getByName)",
        required: true,
      },
      {
        displayName: "Folder ID",
        name: "folderId",
        type: "string",
        displayOptions: {
          show: {
            resource: ["appliedControl"],
            operation: ["create", "getByName"],
          },
        },
        default: "",
        placeholder: "domain-uuid-here",
        description: "The UUID of the folder (domain)",
        required: true,
      },
      {
        displayName: "Applied Control Description",
        name: "appliedControlDescription",
        type: "string",
        typeOptions: {
          rows: 3,
        },
        displayOptions: {
          show: {
            resource: ["appliedControl"],
            operation: ["create"],
          },
        },
        default: "",
        placeholder: "Description of the applied control",
        description: "The description of the applied control",
      },
      {
        displayName: "Status",
        name: "appliedControlStatus",
        type: "options",
        displayOptions: {
          show: {
            resource: ["appliedControl"],
            operation: ["create", "update"],
          },
        },
        options: [
          { name: "To Do", value: "to_do" },
          { name: "In Progress", value: "in_progress" },
          { name: "On Hold", value: "on_hold" },
          { name: "Active", value: "active" },
          { name: "Deprecated", value: "deprecated" },
          { name: "Undefined", value: "--" },
        ],
        default: "to_do",
        description: "The status of the applied control",
      },
      {
        displayName: "Applied Control UUID",
        name: "appliedControlId",
        type: "string",
        displayOptions: {
          show: {
            resource: ["appliedControl"],
            operation: ["update"],
          },
        },
        default: "",
        placeholder: "applied-control-uuid-here",
        description: "The UUID of the applied control to update",
        required: true,
      },
      // Task fields
      {
        displayName: "Folder ID",
        name: "folderId",
        type: "string",
        displayOptions: {
          show: {
            resource: ["taskOccurrence"],
            operation: ["create"],
          },
        },
        default: "",
        placeholder: "domain-uuid-here",
        description: "The UUID of the folder (domain)",
        required: true,
      },
      {
        displayName: "Due Date",
        name: "taskDueDate",
        type: "string",
        displayOptions: {
          show: {
            resource: ["taskOccurrence"],
            operation: ["create", "update"],
          },
        },
        default: "",
        placeholder: "2025-12-31",
        description: "Due date for the task (YYYY-MM-DD format)",
      },
      {
        displayName: "Status",
        name: "taskStatus",
        type: "options",
        displayOptions: {
          show: {
            resource: ["taskOccurrence"],
            operation: ["create", "update"],
          },
        },
        options: [
          { name: "Pending", value: "pending" },
          { name: "In Progress", value: "in_progress" },
          { name: "Completed", value: "completed" },
          { name: "Cancelled", value: "cancelled" },
        ],
        default: "pending",
        description: "The status of the task",
      },
      {
        displayName: "Observation",
        name: "taskObservation",
        type: "string",
        typeOptions: {
          rows: 3,
        },
        displayOptions: {
          show: {
            resource: ["taskOccurrence"],
            operation: ["create", "update"],
          },
        },
        default: "",
        placeholder: "Task observations and notes",
        description: "Observation notes for the task",
      },
      {
        displayName: "Task UUID",
        name: "taskId",
        type: "string",
        displayOptions: {
          show: {
            resource: ["taskOccurrence"],
            operation: ["update"],
          },
        },
        default: "",
        placeholder: "task-uuid-here",
        description: "The UUID of the task to update",
        required: true,
      },
      // Task Definition fields
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
      // Findings Assessment fields
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
          { name: "Undefined", value: "--" },
          { name: "Pentest", value: "pentest" },
          { name: "Audit", value: "audit" },
          { name: "Self-identified", value: "self_identified" },
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
          { name: "Planned", value: "planned" },
          { name: "In progress", value: "in_progress" },
          { name: "In review", value: "in_review" },
          { name: "Done", value: "done" },
          { name: "Deprecated", value: "deprecated" },
        ],
        default: "planned",
        description: "Status of the findings tracking",
      },
      // Finding fields
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
          { name: "Undefined", value: -1 },
          { name: "Info", value: 0 },
          { name: "Low", value: 1 },
          { name: "Medium", value: 2 },
          { name: "High", value: 3 },
          { name: "Critical", value: 4 },
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
          { name: "Undefined", value: "--" },
          { name: "Identified", value: "identified" },
          { name: "Confirmed", value: "confirmed" },
          { name: "Dismissed", value: "dismissed" },
          { name: "Assigned", value: "assigned" },
          { name: "In Progress", value: "in_progress" },
          { name: "Mitigated", value: "mitigated" },
          { name: "Resolved", value: "resolved" },
          { name: "Closed", value: "closed" },
          { name: "Deprecated", value: "deprecated" },
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
          { name: "Undefined", value: "--" },
          { name: "Identified", value: "identified" },
          { name: "Confirmed", value: "confirmed" },
          { name: "Dismissed", value: "dismissed" },
          { name: "Assigned", value: "assigned" },
          { name: "In Progress", value: "in_progress" },
          { name: "Mitigated", value: "mitigated" },
          { name: "Resolved", value: "resolved" },
          { name: "Closed", value: "closed" },
          { name: "Deprecated", value: "deprecated" },
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
          { name: "Undefined", value: -1 },
          { name: "Info", value: 0 },
          { name: "Low", value: 1 },
          { name: "Medium", value: 2 },
          { name: "High", value: 3 },
          { name: "Critical", value: 4 },
        ],
        default: -1,
        description: "Severity of the finding",
      },
      // Security Exception fields
      {
        displayName: "Security Exception Name",
        name: "securityExceptionName",
        type: "string",
        displayOptions: {
          show: {
            resource: ["securityException"],
            operation: ["create", "getByName"],
          },
        },
        default: "",
        placeholder: "Legacy System Exception",
        description: "Name of the security exception (case-sensitive)",
        required: true,
      },
      {
        displayName: "Folder UUID",
        name: "folderId",
        type: "string",
        displayOptions: {
          show: {
            resource: ["securityException"],
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
        name: "securityExceptionDescription",
        type: "string",
        typeOptions: {
          rows: 3,
        },
        displayOptions: {
          show: {
            resource: ["securityException"],
            operation: ["create"],
          },
        },
        default: "",
        placeholder: "Description of the security exception",
        description: "Security exception description",
      },
      {
        displayName: "Severity",
        name: "securityExceptionSeverity",
        type: "options",
        displayOptions: {
          show: {
            resource: ["securityException"],
            operation: ["create"],
          },
        },
        options: [
          { name: "Undefined", value: -1 },
          { name: "Info", value: 0 },
          { name: "Low", value: 1 },
          { name: "Medium", value: 2 },
          { name: "High", value: 3 },
          { name: "Critical", value: 4 },
        ],
        default: -1,
        description: "Severity of the security exception",
      },
      {
        displayName: "Status",
        name: "securityExceptionStatus",
        type: "options",
        displayOptions: {
          show: {
            resource: ["securityException"],
            operation: ["create"],
          },
        },
        options: [
          { name: "Draft", value: "draft" },
          { name: "In Review", value: "in_review" },
          { name: "Approved", value: "approved" },
          { name: "Resolved", value: "resolved" },
          { name: "Expired", value: "expired" },
          { name: "Deprecated", value: "deprecated" },
        ],
        default: "draft",
        description: "Status of the security exception",
      },
      {
        displayName: "Expiration Date",
        name: "securityExceptionExpirationDate",
        type: "string",
        displayOptions: {
          show: {
            resource: ["securityException"],
            operation: ["create"],
          },
        },
        default: "",
        placeholder: "2025-12-31",
        description: "Expiration date (YYYY-MM-DD format)",
      },
      {
        displayName: "Security Exception UUID",
        name: "securityExceptionId",
        type: "string",
        displayOptions: {
          show: {
            resource: ["securityException"],
            operation: ["update"],
          },
        },
        default: "",
        placeholder: "security-exception-uuid-here",
        description: "The UUID of the security exception to update",
        required: true,
      },
      {
        displayName: "Status",
        name: "securityExceptionStatusUpdate",
        type: "options",
        displayOptions: {
          show: {
            resource: ["securityException"],
            operation: ["update"],
          },
        },
        options: [
          { name: "Draft", value: "draft" },
          { name: "In Review", value: "in_review" },
          { name: "Approved", value: "approved" },
          { name: "Resolved", value: "resolved" },
          { name: "Expired", value: "expired" },
          { name: "Deprecated", value: "deprecated" },
        ],
        default: "draft",
        description: "Status of the security exception",
      },
      // Evidence fields
      {
        displayName: "Evidence Name",
        name: "evidenceName",
        type: "string",
        displayOptions: {
          show: {
            resource: ["evidence"],
            operation: ["create", "getByName"],
          },
        },
        default: "",
        placeholder: "Compliance Report 2025",
        description: "Name of the evidence (case-sensitive)",
        required: true,
      },
      {
        displayName: "Folder UUID",
        name: "folderId",
        type: "string",
        displayOptions: {
          show: {
            resource: ["evidence"],
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
        name: "evidenceDescription",
        type: "string",
        typeOptions: {
          rows: 3,
        },
        displayOptions: {
          show: {
            resource: ["evidence"],
            operation: ["create"],
          },
        },
        default: "",
        placeholder: "Description of the evidence",
        description: "Evidence description",
      },
      {
        displayName: "Status",
        name: "evidenceStatus",
        type: "options",
        displayOptions: {
          show: {
            resource: ["evidence"],
            operation: ["create"],
          },
        },
        options: [
          { name: "Draft", value: "draft" },
          { name: "Missing", value: "missing" },
          { name: "In Review", value: "in_review" },
          { name: "Approved", value: "approved" },
          { name: "Rejected", value: "rejected" },
          { name: "Expired", value: "expired" },
        ],
        default: "draft",
        description: "Status of the evidence",
      },
      {
        displayName: "Expiry Date",
        name: "evidenceExpiryDate",
        type: "string",
        displayOptions: {
          show: {
            resource: ["evidence"],
            operation: ["create"],
          },
        },
        default: "",
        placeholder: "2025-12-31",
        description: "Expiry date (YYYY-MM-DD format)",
      },
      {
        displayName: "Evidence UUID",
        name: "evidenceId",
        type: "string",
        displayOptions: {
          show: {
            resource: ["evidence"],
            operation: ["update"],
          },
        },
        default: "",
        placeholder: "evidence-uuid-here",
        description: "The UUID of the evidence to update",
        required: true,
      },
      {
        displayName: "Status",
        name: "evidenceStatusUpdate",
        type: "options",
        displayOptions: {
          show: {
            resource: ["evidence"],
            operation: ["update"],
          },
        },
        options: [
          { name: "Draft", value: "draft" },
          { name: "Missing", value: "missing" },
          { name: "In Review", value: "in_review" },
          { name: "Approved", value: "approved" },
          { name: "Rejected", value: "rejected" },
          { name: "Expired", value: "expired" },
        ],
        default: "draft",
        description: "Status of the evidence",
      },
      // Evidence Revision fields
      {
        displayName: "Evidence UUID",
        name: "evidenceIdForRevision",
        type: "string",
        displayOptions: {
          show: {
            resource: ["evidence"],
            operation: ["submitRevision", "listRevisions"],
          },
        },
        default: "",
        placeholder: "evidence-uuid-here",
        description: "The UUID of the evidence",
        required: true,
      },
      {
        displayName: "Revision Type",
        name: "evidenceRevisionType",
        type: "options",
        displayOptions: {
          show: {
            resource: ["evidence"],
            operation: ["submitRevision"],
          },
        },
        options: [
          {
            name: "Link",
            value: "link",
          },
          {
            name: "File Upload",
            value: "file",
          },
        ],
        default: "link",
        description: "Whether to submit a link or upload a file attachment",
      },
      {
        displayName: "Link",
        name: "evidenceRevisionLink",
        type: "string",
        displayOptions: {
          show: {
            resource: ["evidence"],
            operation: ["submitRevision"],
            evidenceRevisionType: ["link"],
          },
        },
        default: "",
        placeholder: "https://example.com/document.pdf",
        description: "URL link to the evidence",
      },
      {
        displayName: "Binary Property",
        name: "binaryPropertyName",
        type: "string",
        displayOptions: {
          show: {
            resource: ["evidence"],
            operation: ["submitRevision"],
            evidenceRevisionType: ["file"],
          },
        },
        default: "data",
        placeholder: "data",
        description:
          "Name of the binary property containing the file to upload",
        required: true,
      },
      {
        displayName: "Observation",
        name: "evidenceRevisionObservation",
        type: "string",
        typeOptions: {
          rows: 3,
        },
        displayOptions: {
          show: {
            resource: ["evidence"],
            operation: ["submitRevision"],
          },
        },
        default: "",
        placeholder: "Revision notes or observations",
        description: "Observation notes for this revision",
      },
      // Entity fields
      {
        displayName: "Entity Name",
        name: "entityName",
        type: "string",
        displayOptions: {
          show: {
            resource: ["entity"],
            operation: ["create", "getByName"],
          },
        },
        default: "",
        placeholder: "Cloud Provider Inc.",
        description: "Name of the entity (case-sensitive)",
        required: true,
      },
      {
        displayName: "Folder UUID",
        name: "folderId",
        type: "string",
        displayOptions: {
          show: {
            resource: ["entity"],
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
        name: "entityDescription",
        type: "string",
        typeOptions: {
          rows: 3,
        },
        displayOptions: {
          show: {
            resource: ["entity"],
            operation: ["create"],
          },
        },
        default: "",
        placeholder: "Description of the entity",
        description: "Entity description",
      },
      {
        displayName: "Mission",
        name: "entityMission",
        type: "string",
        typeOptions: {
          rows: 3,
        },
        displayOptions: {
          show: {
            resource: ["entity"],
            operation: ["create"],
          },
        },
        default: "",
        placeholder: "Mission statement of the entity",
        description: "Entity mission statement",
      },
      {
        displayName: "Reference Link",
        name: "entityReferenceLink",
        type: "string",
        displayOptions: {
          show: {
            resource: ["entity"],
            operation: ["create"],
          },
        },
        default: "",
        placeholder: "https://example.com",
        description: "Reference URL for the entity",
      },
      // Solution fields
      {
        displayName: "Solution Name",
        name: "solutionName",
        type: "string",
        displayOptions: {
          show: {
            resource: ["solution"],
            operation: ["create", "getByName"],
          },
        },
        default: "",
        placeholder: "AWS Cloud Services",
        description: "Name of the solution (case-sensitive)",
        required: true,
      },
      {
        displayName: "Provider Entity UUID",
        name: "providerEntityId",
        type: "string",
        displayOptions: {
          show: {
            resource: ["solution"],
            operation: ["create", "getByName"],
          },
        },
        default: "",
        placeholder: "entity-uuid-here",
        description: "UUID of the provider entity",
        required: true,
      },
      {
        displayName: "Recipient Entity UUID",
        name: "recipientEntityId",
        type: "string",
        displayOptions: {
          show: {
            resource: ["solution"],
            operation: ["create"],
          },
        },
        default: "",
        placeholder: "entity-uuid-here",
        description: "UUID of the recipient entity (optional)",
      },
      {
        displayName: "Description",
        name: "solutionDescription",
        type: "string",
        typeOptions: {
          rows: 3,
        },
        displayOptions: {
          show: {
            resource: ["solution"],
            operation: ["create"],
          },
        },
        default: "",
        placeholder: "Description of the solution",
        description: "Solution description",
      },
      {
        displayName: "Reference ID",
        name: "solutionRefId",
        type: "string",
        displayOptions: {
          show: {
            resource: ["solution"],
            operation: ["create"],
          },
        },
        default: "",
        placeholder: "SOL-001",
        description: "Reference identifier for the solution",
      },
      {
        displayName: "Criticality",
        name: "solutionCriticality",
        type: "number",
        displayOptions: {
          show: {
            resource: ["solution"],
            operation: ["create"],
          },
        },
        default: 0,
        description: "Criticality level of the solution (0-4)",
      },
      // Representative fields
      {
        displayName: "Entity UUID",
        name: "representativeEntityId",
        type: "string",
        displayOptions: {
          show: {
            resource: ["representative"],
            operation: ["create", "list"],
          },
        },
        default: "",
        placeholder: "entity-uuid-here",
        description: "UUID of the entity",
        required: true,
      },
      {
        displayName: "Email",
        name: "representativeEmail",
        type: "string",
        displayOptions: {
          show: {
            resource: ["representative"],
            operation: ["create"],
          },
        },
        default: "",
        placeholder: "contact@example.com",
        description: "Email address of the representative (unique)",
        required: true,
      },
      {
        displayName: "First Name",
        name: "representativeFirstName",
        type: "string",
        displayOptions: {
          show: {
            resource: ["representative"],
            operation: ["create"],
          },
        },
        default: "",
        placeholder: "John",
        description: "First name of the representative",
      },
      {
        displayName: "Last Name",
        name: "representativeLastName",
        type: "string",
        displayOptions: {
          show: {
            resource: ["representative"],
            operation: ["create"],
          },
        },
        default: "",
        placeholder: "Doe",
        description: "Last name of the representative",
      },
      {
        displayName: "Phone",
        name: "representativePhone",
        type: "string",
        displayOptions: {
          show: {
            resource: ["representative"],
            operation: ["create"],
          },
        },
        default: "",
        placeholder: "+1234567890",
        description: "Phone number of the representative",
      },
      {
        displayName: "Role",
        name: "representativeRole",
        type: "string",
        displayOptions: {
          show: {
            resource: ["representative"],
            operation: ["create"],
          },
        },
        default: "",
        placeholder: "Account Manager",
        description: "Role or position of the representative",
      },
      {
        displayName: "Description",
        name: "representativeDescription",
        type: "string",
        typeOptions: {
          rows: 3,
        },
        displayOptions: {
          show: {
            resource: ["representative"],
            operation: ["create"],
          },
        },
        default: "",
        placeholder: "Additional details about the representative",
        description: "Representative description",
      },
      // Entity Assessment fields
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
          { name: "Blocker", value: "blocker" },
          { name: "Warning", value: "warning" },
          { name: "Ok", value: "ok" },
          { name: "Not Applicable", value: "not_applicable" },
        ],
        default: "",
        description: "Conclusion of the entity assessment",
      },
      // Right Request fields
      {
        displayName: "Right Request Name",
        name: "rightRequestName",
        type: "string",
        displayOptions: {
          show: {
            resource: ["rightRequest"],
            operation: ["create", "getByName"],
          },
        },
        default: "",
        placeholder: "GDPR Access Request",
        description: "Name of the right request (case-sensitive)",
        required: true,
      },
      {
        displayName: "Folder UUID",
        name: "folderId",
        type: "string",
        displayOptions: {
          show: {
            resource: ["rightRequest"],
            operation: ["create", "getByName"],
          },
        },
        default: "",
        placeholder: "domain-uuid-here",
        description: "The UUID of the folder (domain)",
        required: true,
      },
      {
        displayName: "Right Request UUID",
        name: "rightRequestId",
        type: "string",
        displayOptions: {
          show: {
            resource: ["rightRequest"],
            operation: ["update"],
          },
        },
        default: "",
        placeholder: "right-request-uuid-here",
        description: "The UUID of the right request to update",
        required: true,
      },
      {
        displayName: "Requested On",
        name: "rightRequestRequestedOn",
        type: "string",
        displayOptions: {
          show: {
            resource: ["rightRequest"],
            operation: ["create"],
          },
        },
        default: "",
        placeholder: "2025-01-15",
        description: "Date when the request was made (YYYY-MM-DD format)",
        required: true,
      },
      {
        displayName: "Request Type",
        name: "rightRequestType",
        type: "options",
        displayOptions: {
          show: {
            resource: ["rightRequest"],
            operation: ["create", "update"],
          },
        },
        options: [
          { name: "Deletion / Erasure", value: "deletion" },
          { name: "Rectification", value: "rectification" },
          { name: "Access / Extract", value: "access" },
          { name: "Portability", value: "portability" },
          { name: "Restriction", value: "restriction" },
          { name: "Objection", value: "objection" },
          { name: "Other", value: "other" },
        ],
        default: "other",
        description: "Type of the right request",
      },
      {
        displayName: "Status",
        name: "rightRequestStatus",
        type: "options",
        displayOptions: {
          show: {
            resource: ["rightRequest"],
            operation: ["create", "update"],
          },
        },
        options: [
          { name: "New", value: "new" },
          { name: "In Progress", value: "in_progress" },
          { name: "On Hold", value: "on_hold" },
          { name: "Done", value: "done" },
        ],
        default: "new",
        description: "Status of the right request",
      },
      {
        displayName: "Description",
        name: "rightRequestDescription",
        type: "string",
        typeOptions: {
          rows: 3,
        },
        displayOptions: {
          show: {
            resource: ["rightRequest"],
            operation: ["create", "update"],
          },
        },
        default: "",
        placeholder: "Description of the right request",
        description: "Right request description",
      },
      {
        displayName: "Due Date",
        name: "rightRequestDueDate",
        type: "string",
        displayOptions: {
          show: {
            resource: ["rightRequest"],
            operation: ["create", "update"],
          },
        },
        default: "",
        placeholder: "2025-02-15",
        description: "Due date for the request (YYYY-MM-DD format)",
      },
      {
        displayName: "Observation",
        name: "rightRequestObservation",
        type: "string",
        typeOptions: {
          rows: 3,
        },
        displayOptions: {
          show: {
            resource: ["rightRequest"],
            operation: ["create", "update"],
          },
        },
        default: "",
        placeholder: "Additional observations",
        description: "Observation notes",
      },
      // Data Breach fields
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
          { name: "Destruction", value: "privacy_destruction" },
          { name: "Loss", value: "privacy_loss" },
          { name: "Alteration", value: "privacy_alteration" },
          {
            name: "Unauthorized Disclosure",
            value: "privacy_unauthorized_disclosure",
          },
          { name: "Unauthorized Access", value: "privacy_unauthorized_access" },
          { name: "Other", value: "privacy_other" },
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
          { name: "No Risk", value: "privacy_no_risk" },
          { name: "Risk", value: "privacy_risk" },
          { name: "High Risk", value: "privacy_high_risk" },
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
          { name: "Discovered", value: "privacy_discovered" },
          { name: "Under Investigation", value: "privacy_under_investigation" },
          { name: "Authority Notified", value: "privacy_authority_notified" },
          {
            name: "Data Subjects Notified",
            value: "privacy_subjects_notified",
          },
          { name: "Closed", value: "privacy_closed" },
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
      // Risk Scenario fields
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
          { name: "Open", value: "open" },
          { name: "Mitigate", value: "mitigate" },
          { name: "Accept", value: "accept" },
          { name: "Avoid", value: "avoid" },
          { name: "Transfer", value: "transfer" },
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
      // Optional Folder UUID for list operations
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
      // Additional fields
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
              { name: "Low", value: "low" },
              { name: "Medium", value: "medium" },
              { name: "High", value: "high" },
              { name: "Critical", value: "critical" },
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
    ],
  };

  async execute(this: IExecuteFunctions): Promise<INodeExecutionData[][]> {
    const items = this.getInputData();
    const returnData: INodeExecutionData[] = [];

    // Get credentials once
    const credentials = (await this.getCredentials(
      "cisoAssistantApi",
    )) as ICisoAssistantCredentials;

    // Process each input item
    for (let i = 0; i < items.length; i++) {
      try {
        // Get resource and operation from node parameters
        const resource = this.getNodeParameter("resource", i) as ResourceType;
        const operation = this.getNodeParameter("operation", i) as string;

        // Create context for the handler
        const context: IResourceContext = {
          executeFunctions: this,
          credentials,
          itemIndex: i,
        };

        // Get the appropriate handler from the registry
        const handler = resourceRegistry.getHandler(resource);

        // Execute the operation
        const response = await handler.execute(operation, context);

        // Add result to return data
        returnData.push({
          json: response,
          pairedItem: { item: i },
        });
      } catch (err: unknown) {
        // Handle errors based on continueOnFail setting
        if (this.continueOnFail()) {
          const errorMessage = err instanceof Error ? err.message : String(err);
          returnData.push({
            json: { error: errorMessage },
            pairedItem: { item: i },
          });
        } else {
          throw err;
        }
      }
    }

    return [returnData];
  }
}
