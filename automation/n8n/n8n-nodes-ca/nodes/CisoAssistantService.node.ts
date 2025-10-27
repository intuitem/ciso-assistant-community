import {
  INodeType,
  INodeTypeDescription,
  IExecuteFunctions,
  INodeExecutionData,
  IHttpRequestOptions,
  NodeConnectionType,
} from "n8n-workflow";

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
    inputs: [NodeConnectionType.Main],
    outputs: [NodeConnectionType.Main],
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
            description: "Update a requirement assessment by requirement ref_id",
            action: "Update requirement assessment",
          },
          {
            name: "List Requirement Assessments",
            value: "listRequirementAssessments",
            description: "Get all requirement assessments for a compliance assessment",
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
            description: "Initiate a risk assessment for a perimeter with a risk matrix",
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
            description: "Get a security exception by its name (case-sensitive)",
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
            description: "Update evidence envelope data (name, description, status, etc.)",
            action: "Update evidence envelope",
          },
          {
            name: "Submit Revision",
            value: "submitRevision",
            description: "Submit a new revision of the evidence (link or attachment)",
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
            description: "Create a new entity assessment with optional compliance assessment",
            action: "Create entity assessment",
          },
          {
            name: "Get by Name",
            value: "getByName",
            description: "Get an entity assessment by its name (case-sensitive)",
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
        description: "The UUID of the folder (domain) this perimeter belongs to",
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
            operation: ["getRequirementAssessment", "updateRequirementAssessment", "listRequirementAssessments"],
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
        description: "The UUID of the folder (domain) this vulnerability belongs to",
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
        description: "The name of the applied control (case sensitive for getByName)",
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
        displayName: "Link",
        name: "evidenceRevisionLink",
        type: "string",
        displayOptions: {
          show: {
            resource: ["evidence"],
            operation: ["submitRevision"],
          },
        },
        default: "",
        placeholder: "https://example.com/document.pdf",
        description: "URL link to the evidence (optional if using attachment)",
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
        description: "UUID of compliance assessment to link (optional - triggers compliance assessment)",
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
        description: "Date and time when the breach was discovered (ISO 8601 format)",
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
          { name: "Unauthorized Disclosure", value: "privacy_unauthorized_disclosure" },
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
          { name: "Data Subjects Notified", value: "privacy_subjects_notified" },
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
        description: "Strength of knowledge supporting the assessment (-1 for undefined, 0=Low, 1=Medium, 2=High)",
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

    // Get credentials
    const credentials = await this.getCredentials("cisoAssistantApi");

    for (let i = 0; i < items.length; i++) {
      try {
        const resource = this.getNodeParameter("resource", i) as string;
        const operation = this.getNodeParameter("operation", i) as string;

        // Base options for all requests (without url)
        const baseHeaders = {
          Authorization: `Token ${credentials.patKey}`,
          Accept: "application/json",
          "Content-Type": "application/json",
        };

        const baseConfig: Partial<IHttpRequestOptions> = {
          headers: baseHeaders,
          json: true,
        };

        // Skip TLS verification if specified in credentials
        if (credentials.skipTLS === true) {
          baseConfig.skipSslCertificateValidation = true;
        }

        let response;

        // Handle operations based on resource and operation
        if (resource === "system" && operation === "getBuild") {
          response = await this.helpers.httpRequest({
            ...baseConfig,
            method: "GET",
            url: `${credentials.baseUrl}/build`,
          });
        } else if (resource === "system" && operation === "getUserByEmail") {
          const userEmail = this.getNodeParameter("userEmail", i) as string;

          response = await this.helpers.httpRequest({
            ...baseConfig,
            method: "GET",
            url: `${credentials.baseUrl}/users/?email=${encodeURIComponent(userEmail)}`,
          });
        } else if (resource === "system" && operation === "listUsers") {
          response = await this.helpers.httpRequest({
            ...baseConfig,
            method: "GET",
            url: `${credentials.baseUrl}/users/`,
          });
        } else if (resource === "perimeter" && operation === "create") {
          const perimeterName = this.getNodeParameter(
            "perimeterName",
            i,
          ) as string;
          const perimeterDescription = this.getNodeParameter(
            "perimeterDescription",
            i,
            "",
          ) as string;
          const folderId = this.getNodeParameter("folderId", i) as string;
          const perimeterAdditionalFields = this.getNodeParameter(
            "additionalFields",
            i,
            {},
          ) as any;

          const perimeterData: any = {
            name: perimeterName,
            description: perimeterDescription,
            folder: folderId,
          };

          // Add additional fields
          if (perimeterAdditionalFields.owner)
            perimeterData.owner = perimeterAdditionalFields.owner;
          if (perimeterAdditionalFields.tags) {
            perimeterData.tags = perimeterAdditionalFields.tags
              .split(",")
              .map((tag: string) => tag.trim());
          }

          response = await this.helpers.httpRequest({
            ...baseConfig,
            method: "POST",
            url: `${credentials.baseUrl}/perimeters/`,
            body: perimeterData,
          });
        } else if (resource === "perimeter" && operation === "getByName") {
          const perimeterName = this.getNodeParameter("perimeterName", i) as string;
          const folderId = this.getNodeParameter("folderId", i) as string;
          response = await this.helpers.httpRequest({
            ...baseConfig,
            method: "GET",
            url: `${credentials.baseUrl}/perimeters/?name=${encodeURIComponent(perimeterName)}&folder=${encodeURIComponent(folderId)}`,
          });
        } else if (resource === "perimeter" && operation === "list") {
          const folderIdFilter = this.getNodeParameter("folderIdFilter", i, "") as string;
          let url = `${credentials.baseUrl}/perimeters/`;
          if (folderIdFilter) {
            url += `?folder=${encodeURIComponent(folderIdFilter)}`;
          }
          response = await this.helpers.httpRequest({
            ...baseConfig,
            method: "GET",
            url,
          });
        } else if (resource === "domain" && operation === "create") {
          const domainName = this.getNodeParameter("domainName", i) as string;
          const domainDescription = this.getNodeParameter(
            "domainDescription",
            i,
            "",
          ) as string;
          const domainAdditionalFields = this.getNodeParameter(
            "additionalFields",
            i,
            {},
          ) as any;

          const domainData: any = {
            name: domainName,
            description: domainDescription,
          };

          // Add additional fields
          if (domainAdditionalFields.owner)
            domainData.owner = domainAdditionalFields.owner;
          if (domainAdditionalFields.tags) {
            domainData.tags = domainAdditionalFields.tags
              .split(",")
              .map((tag: string) => tag.trim());
          }

          response = await this.helpers.httpRequest({
            ...baseConfig,
            method: "POST",
            url: `${credentials.baseUrl}/folders/`,
            body: domainData,
          });
        } else if (resource === "domain" && operation === "getByName") {
          const domainName = this.getNodeParameter("domainName", i) as string;
          response = await this.helpers.httpRequest({
            ...baseConfig,
            method: "GET",
            url: `${credentials.baseUrl}/folders/?name=${encodeURIComponent(domainName)}`,
          });
        } else if (resource === "domain" && operation === "list") {
          const folderIdFilter = this.getNodeParameter("folderIdFilter", i, "") as string;
          let url = `${credentials.baseUrl}/folders/`;
          if (folderIdFilter) {
            url += `?folder=${encodeURIComponent(folderIdFilter)}`;
          }
          response = await this.helpers.httpRequest({
            ...baseConfig,
            method: "GET",
            url,
          });
        } else if (resource === "asset" && operation === "create") {
          const assetName = this.getNodeParameter("assetName", i) as string;
          const folderId = this.getNodeParameter("folderId", i) as string;
          const assetDescription = this.getNodeParameter(
            "assetDescription",
            i,
            "",
          ) as string;
          const assetType = this.getNodeParameter("assetType", i) as string;
          const assetAdditionalFields = this.getNodeParameter(
            "additionalFields",
            i,
            {},
          ) as any;

          const assetData: any = {
            name: assetName,
            folder: folderId,
            description: assetDescription,
            type: assetType,
          };

          // Add additional fields
          if (assetAdditionalFields.businessValue)
            assetData.business_value = assetAdditionalFields.businessValue;
          if (assetAdditionalFields.owner)
            assetData.owner = assetAdditionalFields.owner;
          if (assetAdditionalFields.tags) {
            assetData.tags = assetAdditionalFields.tags
              .split(",")
              .map((tag: string) => tag.trim());
          }

          response = await this.helpers.httpRequest({
            ...baseConfig,
            method: "POST",
            url: `${credentials.baseUrl}/assets/`,
            body: assetData,
          });
        } else if (resource === "asset" && operation === "getByName") {
          const assetName = this.getNodeParameter("assetName", i) as string;
          const folderId = this.getNodeParameter("folderId", i, "") as string;

          let url = `${credentials.baseUrl}/assets/?name=${encodeURIComponent(assetName)}`;
          if (folderId) {
            url += `&folder=${encodeURIComponent(folderId)}`;
          }

          response = await this.helpers.httpRequest({
            ...baseConfig,
            method: "GET",
            url,
          });
        } else if (resource === "asset" && operation === "list") {
          const folderIdFilter = this.getNodeParameter("folderIdFilter", i, "") as string;
          let url = `${credentials.baseUrl}/assets/`;
          if (folderIdFilter) {
            url += `?folder=${encodeURIComponent(folderIdFilter)}`;
          }

          response = await this.helpers.httpRequest({
            ...baseConfig,
            method: "GET",
            url,
          });
        } else if (resource === "asset" && operation === "update") {
          const assetId = this.getNodeParameter("assetId", i) as string;
          const assetDescription = this.getNodeParameter("assetDescription", i, "") as string;
          const assetType = this.getNodeParameter("assetType", i, "") as string;
          const assetNameUpdate = this.getNodeParameter("assetNameUpdate", i, "") as string;

          const assetData: any = {};

          if (assetNameUpdate) assetData.name = assetNameUpdate;
          if (assetDescription) assetData.description = assetDescription;
          if (assetType) assetData.type = assetType;

          response = await this.helpers.httpRequest({
            ...baseConfig,
            method: "PATCH",
            url: `${credentials.baseUrl}/assets/${assetId}/`,
            body: assetData,
          });
        } else if (resource === "audit" && operation === "initiate") {
          const auditPerimeterId = this.getNodeParameter(
            "perimeterId",
            i,
          ) as string;
          const frameworkId = this.getNodeParameter(
            "frameworkId",
            i,
          ) as string;
          const auditName = this.getNodeParameter("auditName", i) as string;

          const auditData = {
            name: auditName,
            perimeter: auditPerimeterId,
            framework: frameworkId,
          };

          response = await this.helpers.httpRequest({
            ...baseConfig,
            method: "POST",
            url: `${credentials.baseUrl}/compliance-assessments/`,
            body: auditData,
          });
        } else if (resource === "audit" && operation === "getByName") {
          const auditName = this.getNodeParameter("auditName", i) as string;
          const folderIdFilter = this.getNodeParameter("folderIdFilter", i, "") as string;
          const perimeterIdFilter = this.getNodeParameter("perimeterIdFilter", i, "") as string;

          let url = `${credentials.baseUrl}/compliance-assessments/?name=${encodeURIComponent(auditName)}`;
          if (folderIdFilter) {
            url += `&folder=${encodeURIComponent(folderIdFilter)}`;
          }
          if (perimeterIdFilter) {
            url += `&perimeter=${encodeURIComponent(perimeterIdFilter)}`;
          }

          response = await this.helpers.httpRequest({
            ...baseConfig,
            method: "GET",
            url,
          });
        } else if (resource === "audit" && operation === "getByRefId") {
          const auditRefId = this.getNodeParameter("auditRefId", i) as string;
          const folderIdFilter = this.getNodeParameter("folderIdFilter", i, "") as string;
          const perimeterIdFilter = this.getNodeParameter("perimeterIdFilter", i, "") as string;

          let url = `${credentials.baseUrl}/compliance-assessments/?ref_id=${encodeURIComponent(auditRefId)}`;
          if (folderIdFilter) {
            url += `&folder=${encodeURIComponent(folderIdFilter)}`;
          }
          if (perimeterIdFilter) {
            url += `&perimeter=${encodeURIComponent(perimeterIdFilter)}`;
          }

          response = await this.helpers.httpRequest({
            ...baseConfig,
            method: "GET",
            url,
          });
        } else if (resource === "audit" && operation === "getRequirementAssessment") {
          const requirementRefId = this.getNodeParameter("requirementRefId", i) as string;
          const complianceAssessmentId = this.getNodeParameter("complianceAssessmentId", i) as string;

          response = await this.helpers.httpRequest({
            ...baseConfig,
            method: "GET",
            url: `${credentials.baseUrl}/requirement-assessments/?requirement__ref_id=${encodeURIComponent(requirementRefId)}&compliance_assessment=${encodeURIComponent(complianceAssessmentId)}`,
          });
        } else if (resource === "audit" && operation === "updateRequirementAssessment") {
          const requirementRefId = this.getNodeParameter("requirementRefId", i) as string;
          const complianceAssessmentId = this.getNodeParameter("complianceAssessmentId", i) as string;

          // First, get the requirement assessment to find its ID
          const getResponse = await this.helpers.httpRequest({
            ...baseConfig,
            method: "GET",
            url: `${credentials.baseUrl}/requirement-assessments/?requirement__ref_id=${encodeURIComponent(requirementRefId)}&compliance_assessment=${encodeURIComponent(complianceAssessmentId)}`,
          });

          // Check if we found the requirement assessment
          if (!getResponse.results || getResponse.results.length === 0) {
            throw new Error(`No requirement assessment found for ref_id: ${requirementRefId} in compliance assessment: ${complianceAssessmentId}`);
          }

          const requirementAssessmentId = getResponse.results[0].id;

          // Build update data
          const updateData: any = {};

          const status = this.getNodeParameter("requirementAssessmentStatus", i, "") as string;
          const result = this.getNodeParameter("requirementAssessmentResult", i, "") as string;
          const observation = this.getNodeParameter("requirementAssessmentObservation", i, "") as string;
          const score = this.getNodeParameter("requirementAssessmentScore", i, null) as number | null;

          if (status) updateData.status = status;
          if (result) updateData.result = result;
          if (observation) updateData.observation = observation;
          if (score !== null && score !== undefined) updateData.score = score;

          response = await this.helpers.httpRequest({
            ...baseConfig,
            method: "PATCH",
            url: `${credentials.baseUrl}/requirement-assessments/${requirementAssessmentId}/`,
            body: updateData,
          });
        } else if (resource === "audit" && operation === "listRequirementAssessments") {
          const complianceAssessmentId = this.getNodeParameter("complianceAssessmentId", i) as string;

          response = await this.helpers.httpRequest({
            ...baseConfig,
            method: "GET",
            url: `${credentials.baseUrl}/requirement-assessments/?compliance_assessment=${encodeURIComponent(complianceAssessmentId)}`,
          });
        } else if (resource === "audit" && operation === "list") {
          const folderIdFilter = this.getNodeParameter("folderIdFilter", i, "") as string;
          const perimeterIdFilter = this.getNodeParameter("perimeterIdFilter", i, "") as string;

          let url = `${credentials.baseUrl}/compliance-assessments/`;
          const params = [];
          if (folderIdFilter) {
            params.push(`folder=${encodeURIComponent(folderIdFilter)}`);
          }
          if (perimeterIdFilter) {
            params.push(`perimeter=${encodeURIComponent(perimeterIdFilter)}`);
          }
          if (params.length > 0) {
            url += `?${params.join("&")}`;
          }

          response = await this.helpers.httpRequest({
            ...baseConfig,
            method: "GET",
            url,
          });
        } else if (resource === "riskAssessment" && operation === "initiate") {
          const raPerimeterId = this.getNodeParameter(
            "perimeterId",
            i,
          ) as string;
          const riskMatrixId = this.getNodeParameter(
            "riskMatrixId",
            i,
          ) as string;
          const riskAssessmentName = this.getNodeParameter(
            "riskAssessmentName",
            i,
          ) as string;

          const riskAssessmentData = {
            name: riskAssessmentName,
            perimeter: raPerimeterId,
            risk_matrix: riskMatrixId,
          };

          response = await this.helpers.httpRequest({
            ...baseConfig,
            method: "POST",
            url: `${credentials.baseUrl}/risk-assessments/`,
            body: riskAssessmentData,
          });
        } else if (resource === "riskAssessment" && operation === "getByName") {
          const riskAssessmentNameGet = this.getNodeParameter("riskAssessmentNameGet", i) as string;
          const folderIdFilter = this.getNodeParameter("folderIdFilter", i, "") as string;
          const perimeterIdFilter = this.getNodeParameter("perimeterIdFilter", i, "") as string;

          let url = `${credentials.baseUrl}/risk-assessments/?name=${encodeURIComponent(riskAssessmentNameGet)}`;
          if (folderIdFilter) {
            url += `&folder=${encodeURIComponent(folderIdFilter)}`;
          }
          if (perimeterIdFilter) {
            url += `&perimeter=${encodeURIComponent(perimeterIdFilter)}`;
          }

          response = await this.helpers.httpRequest({
            ...baseConfig,
            method: "GET",
            url,
          });
        } else if (resource === "riskAssessment" && operation === "getByRefId") {
          const riskAssessmentRefId = this.getNodeParameter("riskAssessmentRefId", i) as string;
          const folderIdFilter = this.getNodeParameter("folderIdFilter", i, "") as string;
          const perimeterIdFilter = this.getNodeParameter("perimeterIdFilter", i, "") as string;

          let url = `${credentials.baseUrl}/risk-assessments/?ref_id=${encodeURIComponent(riskAssessmentRefId)}`;
          if (folderIdFilter) {
            url += `&folder=${encodeURIComponent(folderIdFilter)}`;
          }
          if (perimeterIdFilter) {
            url += `&perimeter=${encodeURIComponent(perimeterIdFilter)}`;
          }

          response = await this.helpers.httpRequest({
            ...baseConfig,
            method: "GET",
            url,
          });
        } else if (resource === "riskAssessment" && operation === "list") {
          const folderIdFilter = this.getNodeParameter("folderIdFilter", i, "") as string;
          const perimeterIdFilter = this.getNodeParameter("perimeterIdFilter", i, "") as string;

          let url = `${credentials.baseUrl}/risk-assessments/`;
          const params = [];
          if (folderIdFilter) {
            params.push(`folder=${encodeURIComponent(folderIdFilter)}`);
          }
          if (perimeterIdFilter) {
            params.push(`perimeter=${encodeURIComponent(perimeterIdFilter)}`);
          }
          if (params.length > 0) {
            url += `?${params.join("&")}`;
          }

          response = await this.helpers.httpRequest({
            ...baseConfig,
            method: "GET",
            url,
          });
        } else if (resource === "incident" && operation === "create") {
          const incidentName = this.getNodeParameter("incidentName", i) as string;
          const folderId = this.getNodeParameter("folderId", i) as string;
          const incidentDescription = this.getNodeParameter(
            "incidentDescription",
            i,
            "",
          ) as string;
          const incidentStatus = this.getNodeParameter(
            "incidentStatus",
            i,
            "new",
          ) as string;
          const incidentSeverity = this.getNodeParameter(
            "incidentSeverity",
            i,
            3,
          ) as number;
          const incidentDetection = this.getNodeParameter(
            "incidentDetection",
            i,
            "internally_detected",
          ) as string;
          const incidentRefId = this.getNodeParameter(
            "incidentRefId",
            i,
            "",
          ) as string;

          const incidentData: any = {
            name: incidentName,
            folder: folderId,
            description: incidentDescription,
            status: incidentStatus,
            severity: incidentSeverity,
            detection: incidentDetection,
          };

          if (incidentRefId) {
            incidentData.ref_id = incidentRefId;
          }

          response = await this.helpers.httpRequest({
            ...baseConfig,
            method: "POST",
            url: `${credentials.baseUrl}/incidents/`,
            body: incidentData,
          });
        } else if (resource === "incident" && operation === "list") {
          const folderIdFilter = this.getNodeParameter("folderIdFilter", i, "") as string;
          let url = `${credentials.baseUrl}/incidents/`;
          if (folderIdFilter) {
            url += `?folder=${encodeURIComponent(folderIdFilter)}`;
          }

          response = await this.helpers.httpRequest({
            ...baseConfig,
            method: "GET",
            url,
          });
        } else if (resource === "incident" && operation === "update") {
          const incidentId = this.getNodeParameter("incidentId", i) as string;
          const incidentDescription = this.getNodeParameter("incidentDescription", i, "") as string;
          const incidentStatus = this.getNodeParameter("incidentStatus", i, "new") as string;
          const incidentSeverity = this.getNodeParameter("incidentSeverity", i, 3) as number;
          const incidentDetection = this.getNodeParameter("incidentDetection", i, "internally_detected") as string;
          const incidentRefId = this.getNodeParameter("incidentRefId", i, "") as string;

          const incidentData: any = {
            description: incidentDescription,
            status: incidentStatus,
            severity: incidentSeverity,
            detection: incidentDetection,
          };

          if (incidentRefId) incidentData.ref_id = incidentRefId;

          response = await this.helpers.httpRequest({
            ...baseConfig,
            method: "PATCH",
            url: `${credentials.baseUrl}/incidents/${incidentId}/`,
            body: incidentData,
          });
        } else if (resource === "vulnerability" && operation === "create") {
          const vulnerabilityName = this.getNodeParameter("vulnerabilityName", i) as string;
          const folderId = this.getNodeParameter("folderId", i) as string;
          const vulnerabilityDescription = this.getNodeParameter(
            "vulnerabilityDescription",
            i,
            "",
          ) as string;
          const vulnerabilityStatus = this.getNodeParameter(
            "vulnerabilityStatus",
            i,
            "--",
          ) as string;
          const vulnerabilitySeverity = this.getNodeParameter(
            "vulnerabilitySeverity",
            i,
            -1,
          ) as number;
          const vulnerabilityRefId = this.getNodeParameter(
            "vulnerabilityRefId",
            i,
            "",
          ) as string;

          const vulnerabilityData: any = {
            name: vulnerabilityName,
            folder: folderId,
            description: vulnerabilityDescription,
            status: vulnerabilityStatus,
            severity: vulnerabilitySeverity,
          };

          if (vulnerabilityRefId) {
            vulnerabilityData.ref_id = vulnerabilityRefId;
          }

          response = await this.helpers.httpRequest({
            ...baseConfig,
            method: "POST",
            url: `${credentials.baseUrl}/vulnerabilities/`,
            body: vulnerabilityData,
          });
        } else if (resource === "vulnerability" && operation === "list") {
          const folderIdFilter = this.getNodeParameter("folderIdFilter", i, "") as string;
          let url = `${credentials.baseUrl}/vulnerabilities/`;
          if (folderIdFilter) {
            url += `?folder=${encodeURIComponent(folderIdFilter)}`;
          }

          response = await this.helpers.httpRequest({
            ...baseConfig,
            method: "GET",
            url,
          });
        } else if (resource === "vulnerability" && operation === "update") {
          const vulnerabilityId = this.getNodeParameter("vulnerabilityId", i) as string;
          const vulnerabilityDescription = this.getNodeParameter("vulnerabilityDescription", i, "") as string;
          const vulnerabilityStatus = this.getNodeParameter("vulnerabilityStatus", i, "--") as string;
          const vulnerabilitySeverity = this.getNodeParameter("vulnerabilitySeverity", i, -1) as number;
          const vulnerabilityRefId = this.getNodeParameter("vulnerabilityRefId", i, "") as string;

          const vulnerabilityData: any = {
            description: vulnerabilityDescription,
            status: vulnerabilityStatus,
            severity: vulnerabilitySeverity,
          };

          if (vulnerabilityRefId) vulnerabilityData.ref_id = vulnerabilityRefId;

          response = await this.helpers.httpRequest({
            ...baseConfig,
            method: "PATCH",
            url: `${credentials.baseUrl}/vulnerabilities/${vulnerabilityId}/`,
            body: vulnerabilityData,
          });
        } else if (resource === "appliedControl" && operation === "create") {
          const appliedControlName = this.getNodeParameter("appliedControlName", i) as string;
          const folderId = this.getNodeParameter("folderId", i) as string;
          const appliedControlDescription = this.getNodeParameter(
            "appliedControlDescription",
            i,
            "",
          ) as string;
          const appliedControlStatus = this.getNodeParameter(
            "appliedControlStatus",
            i,
            "to_do",
          ) as string;

          const appliedControlData: any = {
            name: appliedControlName,
            folder: folderId,
            description: appliedControlDescription,
            status: appliedControlStatus,
          };

          response = await this.helpers.httpRequest({
            ...baseConfig,
            method: "POST",
            url: `${credentials.baseUrl}/applied-controls/`,
            body: appliedControlData,
          });
        } else if (resource === "appliedControl" && operation === "getByName") {
          const appliedControlName = this.getNodeParameter("appliedControlName", i) as string;
          const folderId = this.getNodeParameter("folderId", i) as string;
          response = await this.helpers.httpRequest({
            ...baseConfig,
            method: "GET",
            url: `${credentials.baseUrl}/applied-controls/?name=${encodeURIComponent(appliedControlName)}&folder=${encodeURIComponent(folderId)}`,
          });
        } else if (resource === "appliedControl" && operation === "list") {
          const folderIdFilter = this.getNodeParameter("folderIdFilter", i, "") as string;
          let url = `${credentials.baseUrl}/applied-controls/`;
          if (folderIdFilter) {
            url += `?folder=${encodeURIComponent(folderIdFilter)}`;
          }
          response = await this.helpers.httpRequest({
            ...baseConfig,
            method: "GET",
            url,
          });
        } else if (resource === "appliedControl" && operation === "update") {
          const appliedControlId = this.getNodeParameter("appliedControlId", i) as string;
          const appliedControlStatus = this.getNodeParameter(
            "appliedControlStatus",
            i,
            "",
          ) as string;

          const updateData: any = {};
          if (appliedControlStatus) updateData.status = appliedControlStatus;

          response = await this.helpers.httpRequest({
            ...baseConfig,
            method: "PATCH",
            url: `${credentials.baseUrl}/applied-controls/${appliedControlId}/`,
            body: updateData,
          });
        } else if (resource === "taskOccurrence" && operation === "create") {
          const folderId = this.getNodeParameter("folderId", i) as string;
          const taskDueDate = this.getNodeParameter("taskDueDate", i, "") as string;
          const taskStatus = this.getNodeParameter("taskStatus", i, "pending") as string;
          const taskObservation = this.getNodeParameter("taskObservation", i, "") as string;

          const taskData: any = {
            folder: folderId,
            status: taskStatus,
          };

          if (taskDueDate) taskData.due_date = taskDueDate;
          if (taskObservation) taskData.observation = taskObservation;

          response = await this.helpers.httpRequest({
            ...baseConfig,
            method: "POST",
            url: `${credentials.baseUrl}/task-nodes/`,
            body: taskData,
          });
        } else if (resource === "taskOccurrence" && operation === "list") {
          const folderIdFilter = this.getNodeParameter("folderIdFilter", i, "") as string;
          let url = `${credentials.baseUrl}/task-nodes/`;
          if (folderIdFilter) {
            url += `?folder=${encodeURIComponent(folderIdFilter)}`;
          }
          response = await this.helpers.httpRequest({
            ...baseConfig,
            method: "GET",
            url,
          });
        } else if (resource === "taskOccurrence" && operation === "update") {
          const taskId = this.getNodeParameter("taskId", i) as string;
          const taskDueDate = this.getNodeParameter("taskDueDate", i, "") as string;
          const taskStatus = this.getNodeParameter("taskStatus", i, "") as string;
          const taskObservation = this.getNodeParameter("taskObservation", i, "") as string;

          const updateData: any = {};
          if (taskDueDate) updateData.due_date = taskDueDate;
          if (taskStatus) updateData.status = taskStatus;
          if (taskObservation) updateData.observation = taskObservation;

          response = await this.helpers.httpRequest({
            ...baseConfig,
            method: "PATCH",
            url: `${credentials.baseUrl}/task-nodes/${taskId}/`,
            body: updateData,
          });
        } else if (resource === "taskDefinition" && operation === "create") {
          const taskDefinitionName = this.getNodeParameter("taskDefinitionName", i) as string;
          const folderId = this.getNodeParameter("folderId", i) as string;
          const taskDefinitionDescription = this.getNodeParameter(
            "taskDefinitionDescription",
            i,
            "",
          ) as string;
          const taskDefinitionTaskDate = this.getNodeParameter(
            "taskDefinitionTaskDate",
            i,
            "",
          ) as string;
          const taskDefinitionIsRecurrent = this.getNodeParameter(
            "taskDefinitionIsRecurrent",
            i,
            false,
          ) as boolean;
          const taskDefinitionEnabled = this.getNodeParameter(
            "taskDefinitionEnabled",
            i,
            true,
          ) as boolean;

          const taskDefinitionData: any = {
            name: taskDefinitionName,
            folder: folderId,
            is_recurrent: taskDefinitionIsRecurrent,
            enabled: taskDefinitionEnabled,
          };

          if (taskDefinitionDescription) taskDefinitionData.description = taskDefinitionDescription;
          if (taskDefinitionTaskDate) taskDefinitionData.task_date = taskDefinitionTaskDate;

          response = await this.helpers.httpRequest({
            ...baseConfig,
            method: "POST",
            url: `${credentials.baseUrl}/task-templates/`,
            body: taskDefinitionData,
          });
        } else if (resource === "taskDefinition" && operation === "getByName") {
          const taskDefinitionName = this.getNodeParameter("taskDefinitionName", i) as string;
          const folderId = this.getNodeParameter("folderId", i) as string;
          response = await this.helpers.httpRequest({
            ...baseConfig,
            method: "GET",
            url: `${credentials.baseUrl}/task-templates/?name=${encodeURIComponent(taskDefinitionName)}&folder=${encodeURIComponent(folderId)}`,
          });
        } else if (resource === "taskDefinition" && operation === "list") {
          const folderIdFilter = this.getNodeParameter("folderIdFilter", i, "") as string;
          let url = `${credentials.baseUrl}/task-templates/`;
          if (folderIdFilter) {
            url += `?folder=${encodeURIComponent(folderIdFilter)}`;
          }
          response = await this.helpers.httpRequest({
            ...baseConfig,
            method: "GET",
            url,
          });
        } else if (resource === "taskDefinition" && operation === "update") {
          const taskDefinitionId = this.getNodeParameter("taskDefinitionId", i) as string;
          const taskDefinitionTaskDateUpdate = this.getNodeParameter(
            "taskDefinitionTaskDateUpdate",
            i,
            "",
          ) as string;
          const taskDefinitionEnabledUpdate = this.getNodeParameter(
            "taskDefinitionEnabledUpdate",
            i,
            true,
          ) as boolean;

          const updateData: any = {};
          if (taskDefinitionTaskDateUpdate) updateData.task_date = taskDefinitionTaskDateUpdate;
          if (taskDefinitionEnabledUpdate !== undefined) updateData.enabled = taskDefinitionEnabledUpdate;

          response = await this.helpers.httpRequest({
            ...baseConfig,
            method: "PATCH",
            url: `${credentials.baseUrl}/task-templates/${taskDefinitionId}/`,
            body: updateData,
          });
        } else if (resource === "findingsAssessment" && operation === "create") {
          const findingsAssessmentName = this.getNodeParameter("findingsAssessmentName", i) as string;
          const folderId = this.getNodeParameter("folderId", i) as string;
          const perimeterId = this.getNodeParameter("perimeterId", i) as string;
          const findingsAssessmentDescription = this.getNodeParameter(
            "findingsAssessmentDescription",
            i,
            "",
          ) as string;
          const findingsAssessmentCategory = this.getNodeParameter(
            "findingsAssessmentCategory",
            i,
            "--",
          ) as string;

          const findingsAssessmentData: any = {
            name: findingsAssessmentName,
            folder: folderId,
            perimeter: perimeterId,
            category: findingsAssessmentCategory,
          };

          if (findingsAssessmentDescription)
            findingsAssessmentData.description = findingsAssessmentDescription;

          response = await this.helpers.httpRequest({
            ...baseConfig,
            method: "POST",
            url: `${credentials.baseUrl}/findings-assessments/`,
            body: findingsAssessmentData,
          });
        } else if (resource === "findingsAssessment" && operation === "getByName") {
          const findingsAssessmentName = this.getNodeParameter("findingsAssessmentName", i) as string;
          const folderIdFilter = this.getNodeParameter("folderIdFilter", i, "") as string;
          const perimeterIdFilter = this.getNodeParameter("perimeterIdFilter", i, "") as string;

          let url = `${credentials.baseUrl}/findings-assessments/?name=${encodeURIComponent(findingsAssessmentName)}`;
          if (folderIdFilter) {
            url += `&folder=${encodeURIComponent(folderIdFilter)}`;
          }
          if (perimeterIdFilter) {
            url += `&perimeter=${encodeURIComponent(perimeterIdFilter)}`;
          }

          response = await this.helpers.httpRequest({
            ...baseConfig,
            method: "GET",
            url,
          });
        } else if (resource === "findingsAssessment" && operation === "getByRefId") {
          const findingsAssessmentRefId = this.getNodeParameter("findingsAssessmentRefId", i) as string;
          const folderIdFilter = this.getNodeParameter("folderIdFilter", i, "") as string;
          const perimeterIdFilter = this.getNodeParameter("perimeterIdFilter", i, "") as string;

          let url = `${credentials.baseUrl}/findings-assessments/?ref_id=${encodeURIComponent(findingsAssessmentRefId)}`;
          if (folderIdFilter) {
            url += `&folder=${encodeURIComponent(folderIdFilter)}`;
          }
          if (perimeterIdFilter) {
            url += `&perimeter=${encodeURIComponent(perimeterIdFilter)}`;
          }

          response = await this.helpers.httpRequest({
            ...baseConfig,
            method: "GET",
            url,
          });
        } else if (resource === "findingsAssessment" && operation === "list") {
          const folderIdFilter = this.getNodeParameter("folderIdFilter", i, "") as string;
          const perimeterIdFilter = this.getNodeParameter("perimeterIdFilter", i, "") as string;

          let url = `${credentials.baseUrl}/findings-assessments/`;
          const params = [];
          if (folderIdFilter) {
            params.push(`folder=${encodeURIComponent(folderIdFilter)}`);
          }
          if (perimeterIdFilter) {
            params.push(`perimeter=${encodeURIComponent(perimeterIdFilter)}`);
          }
          if (params.length > 0) {
            url += `?${params.join("&")}`;
          }

          response = await this.helpers.httpRequest({
            ...baseConfig,
            method: "GET",
            url,
          });
        } else if (resource === "findingsAssessment" && operation === "update") {
          const findingsAssessmentId = this.getNodeParameter("findingsAssessmentId", i) as string;
          const findingsAssessmentStatus = this.getNodeParameter(
            "findingsAssessmentStatus",
            i,
            "",
          ) as string;

          const updateData: any = {};
          if (findingsAssessmentStatus) updateData.status = findingsAssessmentStatus;

          response = await this.helpers.httpRequest({
            ...baseConfig,
            method: "PATCH",
            url: `${credentials.baseUrl}/findings-assessments/${findingsAssessmentId}/`,
            body: updateData,
          });
        } else if (resource === "finding" && operation === "create") {
          const findingName = this.getNodeParameter("findingName", i) as string;
          const findingsAssessmentId = this.getNodeParameter("findingsAssessmentId", i) as string;
          const folderId = this.getNodeParameter("folderId", i) as string;
          const findingDescription = this.getNodeParameter("findingDescription", i, "") as string;
          const findingSeverity = this.getNodeParameter("findingSeverity", i, -1) as number;
          const findingStatus = this.getNodeParameter("findingStatus", i, "identified") as string;

          const findingData: any = {
            name: findingName,
            findings_assessment: findingsAssessmentId,
            folder: folderId,
            severity: findingSeverity,
            status: findingStatus,
          };

          if (findingDescription) findingData.description = findingDescription;

          response = await this.helpers.httpRequest({
            ...baseConfig,
            method: "POST",
            url: `${credentials.baseUrl}/findings/`,
            body: findingData,
          });
        } else if (resource === "finding" && operation === "getByName") {
          const findingName = this.getNodeParameter("findingName", i) as string;
          const folderId = this.getNodeParameter("folderId", i) as string;
          response = await this.helpers.httpRequest({
            ...baseConfig,
            method: "GET",
            url: `${credentials.baseUrl}/findings/?name=${encodeURIComponent(findingName)}&folder=${encodeURIComponent(folderId)}`,
          });
        } else if (resource === "finding" && operation === "list") {
          const folderIdFilter = this.getNodeParameter("folderIdFilter", i, "") as string;
          let url = `${credentials.baseUrl}/findings/`;
          if (folderIdFilter) {
            url += `?folder=${encodeURIComponent(folderIdFilter)}`;
          }
          response = await this.helpers.httpRequest({
            ...baseConfig,
            method: "GET",
            url,
          });
        } else if (resource === "finding" && operation === "update") {
          const findingId = this.getNodeParameter("findingId", i) as string;
          const findingStatusUpdate = this.getNodeParameter("findingStatusUpdate", i, "") as string;
          const findingSeverityUpdate = this.getNodeParameter("findingSeverityUpdate", i, -1) as number;

          const updateData: any = {};
          if (findingStatusUpdate) updateData.status = findingStatusUpdate;
          if (findingSeverityUpdate !== -1) updateData.severity = findingSeverityUpdate;

          response = await this.helpers.httpRequest({
            ...baseConfig,
            method: "PATCH",
            url: `${credentials.baseUrl}/findings/${findingId}/`,
            body: updateData,
          });
        } else if (resource === "securityException" && operation === "create") {
          const securityExceptionName = this.getNodeParameter("securityExceptionName", i) as string;
          const folderId = this.getNodeParameter("folderId", i) as string;
          const securityExceptionDescription = this.getNodeParameter(
            "securityExceptionDescription",
            i,
            "",
          ) as string;
          const securityExceptionSeverity = this.getNodeParameter(
            "securityExceptionSeverity",
            i,
            -1,
          ) as number;
          const securityExceptionStatus = this.getNodeParameter(
            "securityExceptionStatus",
            i,
            "draft",
          ) as string;
          const securityExceptionExpirationDate = this.getNodeParameter(
            "securityExceptionExpirationDate",
            i,
            "",
          ) as string;

          const securityExceptionData: any = {
            name: securityExceptionName,
            folder: folderId,
            severity: securityExceptionSeverity,
            status: securityExceptionStatus,
          };

          if (securityExceptionDescription)
            securityExceptionData.description = securityExceptionDescription;
          if (securityExceptionExpirationDate)
            securityExceptionData.expiration_date = securityExceptionExpirationDate;

          response = await this.helpers.httpRequest({
            ...baseConfig,
            method: "POST",
            url: `${credentials.baseUrl}/security-exceptions/`,
            body: securityExceptionData,
          });
        } else if (resource === "securityException" && operation === "getByName") {
          const securityExceptionName = this.getNodeParameter("securityExceptionName", i) as string;
          const folderId = this.getNodeParameter("folderId", i) as string;
          response = await this.helpers.httpRequest({
            ...baseConfig,
            method: "GET",
            url: `${credentials.baseUrl}/security-exceptions/?name=${encodeURIComponent(securityExceptionName)}&folder=${encodeURIComponent(folderId)}`,
          });
        } else if (resource === "securityException" && operation === "list") {
          const folderIdFilter = this.getNodeParameter("folderIdFilter", i, "") as string;
          let url = `${credentials.baseUrl}/security-exceptions/`;
          if (folderIdFilter) {
            url += `?folder=${encodeURIComponent(folderIdFilter)}`;
          }
          response = await this.helpers.httpRequest({
            ...baseConfig,
            method: "GET",
            url,
          });
        } else if (resource === "securityException" && operation === "update") {
          const securityExceptionId = this.getNodeParameter("securityExceptionId", i) as string;
          const securityExceptionStatusUpdate = this.getNodeParameter(
            "securityExceptionStatusUpdate",
            i,
            "",
          ) as string;

          const updateData: any = {};
          if (securityExceptionStatusUpdate) updateData.status = securityExceptionStatusUpdate;

          response = await this.helpers.httpRequest({
            ...baseConfig,
            method: "PATCH",
            url: `${credentials.baseUrl}/security-exceptions/${securityExceptionId}/`,
            body: updateData,
          });
        } else if (resource === "evidence" && operation === "create") {
          const evidenceName = this.getNodeParameter("evidenceName", i) as string;
          const folderId = this.getNodeParameter("folderId", i) as string;
          const evidenceDescription = this.getNodeParameter("evidenceDescription", i, "") as string;
          const evidenceStatus = this.getNodeParameter("evidenceStatus", i, "draft") as string;
          const evidenceExpiryDate = this.getNodeParameter("evidenceExpiryDate", i, "") as string;

          const evidenceData: any = {
            name: evidenceName,
            folder: folderId,
            status: evidenceStatus,
          };

          if (evidenceDescription) evidenceData.description = evidenceDescription;
          if (evidenceExpiryDate) evidenceData.expiry_date = evidenceExpiryDate;

          response = await this.helpers.httpRequest({
            ...baseConfig,
            method: "POST",
            url: `${credentials.baseUrl}/evidences/`,
            body: evidenceData,
          });
        } else if (resource === "evidence" && operation === "getByName") {
          const evidenceName = this.getNodeParameter("evidenceName", i) as string;
          const folderId = this.getNodeParameter("folderId", i) as string;
          response = await this.helpers.httpRequest({
            ...baseConfig,
            method: "GET",
            url: `${credentials.baseUrl}/evidences/?name=${encodeURIComponent(evidenceName)}&folder=${encodeURIComponent(folderId)}`,
          });
        } else if (resource === "evidence" && operation === "list") {
          const folderIdFilter = this.getNodeParameter("folderIdFilter", i, "") as string;
          let url = `${credentials.baseUrl}/evidences/`;
          if (folderIdFilter) {
            url += `?folder=${encodeURIComponent(folderIdFilter)}`;
          }
          response = await this.helpers.httpRequest({
            ...baseConfig,
            method: "GET",
            url,
          });
        } else if (resource === "evidence" && operation === "update") {
          const evidenceId = this.getNodeParameter("evidenceId", i) as string;
          const evidenceStatusUpdate = this.getNodeParameter("evidenceStatusUpdate", i, "") as string;

          const updateData: any = {};
          if (evidenceStatusUpdate) updateData.status = evidenceStatusUpdate;

          response = await this.helpers.httpRequest({
            ...baseConfig,
            method: "PATCH",
            url: `${credentials.baseUrl}/evidences/${evidenceId}/`,
            body: updateData,
          });
        } else if (resource === "evidence" && operation === "submitRevision") {
          const evidenceIdForRevision = this.getNodeParameter("evidenceIdForRevision", i) as string;
          const evidenceRevisionLink = this.getNodeParameter("evidenceRevisionLink", i, "") as string;
          const evidenceRevisionObservation = this.getNodeParameter("evidenceRevisionObservation", i, "") as string;

          const revisionData: any = {
            evidence: evidenceIdForRevision,
          };

          if (evidenceRevisionLink) revisionData.link = evidenceRevisionLink;
          if (evidenceRevisionObservation) revisionData.observation = evidenceRevisionObservation;

          response = await this.helpers.httpRequest({
            ...baseConfig,
            method: "POST",
            url: `${credentials.baseUrl}/evidence-revisions/`,
            body: revisionData,
          });
        } else if (resource === "evidence" && operation === "listRevisions") {
          const evidenceIdForRevision = this.getNodeParameter("evidenceIdForRevision", i) as string;

          response = await this.helpers.httpRequest({
            ...baseConfig,
            method: "GET",
            url: `${credentials.baseUrl}/evidence-revisions/?evidence=${encodeURIComponent(evidenceIdForRevision)}`,
          });
        } else if (resource === "entity" && operation === "create") {
          const entityName = this.getNodeParameter("entityName", i) as string;
          const folderId = this.getNodeParameter("folderId", i) as string;
          const entityDescription = this.getNodeParameter("entityDescription", i, "") as string;
          const entityMission = this.getNodeParameter("entityMission", i, "") as string;
          const entityReferenceLink = this.getNodeParameter("entityReferenceLink", i, "") as string;

          const entityData: any = {
            name: entityName,
            folder: folderId,
          };

          if (entityDescription) entityData.description = entityDescription;
          if (entityMission) entityData.mission = entityMission;
          if (entityReferenceLink) entityData.reference_link = entityReferenceLink;

          response = await this.helpers.httpRequest({
            ...baseConfig,
            method: "POST",
            url: `${credentials.baseUrl}/entities/`,
            body: entityData,
          });
        } else if (resource === "entity" && operation === "getByName") {
          const entityName = this.getNodeParameter("entityName", i) as string;
          const folderId = this.getNodeParameter("folderId", i) as string;

          response = await this.helpers.httpRequest({
            ...baseConfig,
            method: "GET",
            url: `${credentials.baseUrl}/entities/?name=${encodeURIComponent(entityName)}&folder=${encodeURIComponent(folderId)}`,
          });
        } else if (resource === "entity" && operation === "list") {
          const folderIdFilter = this.getNodeParameter("folderIdFilter", i, "") as string;
          let url = `${credentials.baseUrl}/entities/`;
          if (folderIdFilter) {
            url += `?folder=${encodeURIComponent(folderIdFilter)}`;
          }

          response = await this.helpers.httpRequest({
            ...baseConfig,
            method: "GET",
            url,
          });
        } else if (resource === "solution" && operation === "create") {
          const solutionName = this.getNodeParameter("solutionName", i) as string;
          const providerEntityId = this.getNodeParameter("providerEntityId", i) as string;
          const recipientEntityId = this.getNodeParameter("recipientEntityId", i, "") as string;
          const solutionDescription = this.getNodeParameter("solutionDescription", i, "") as string;
          const solutionRefId = this.getNodeParameter("solutionRefId", i, "") as string;
          const solutionCriticality = this.getNodeParameter("solutionCriticality", i, 0) as number;

          const solutionData: any = {
            name: solutionName,
            provider_entity: providerEntityId,
          };

          if (recipientEntityId) solutionData.recipient_entity = recipientEntityId;
          if (solutionDescription) solutionData.description = solutionDescription;
          if (solutionRefId) solutionData.ref_id = solutionRefId;
          if (solutionCriticality !== 0) solutionData.criticality = solutionCriticality;

          response = await this.helpers.httpRequest({
            ...baseConfig,
            method: "POST",
            url: `${credentials.baseUrl}/solutions/`,
            body: solutionData,
          });
        } else if (resource === "solution" && operation === "getByName") {
          const solutionName = this.getNodeParameter("solutionName", i) as string;
          const providerEntityId = this.getNodeParameter("providerEntityId", i) as string;

          response = await this.helpers.httpRequest({
            ...baseConfig,
            method: "GET",
            url: `${credentials.baseUrl}/solutions/?name=${encodeURIComponent(solutionName)}&provider_entity=${encodeURIComponent(providerEntityId)}`,
          });
        } else if (resource === "solution" && operation === "list") {
          const folderIdFilter = this.getNodeParameter("folderIdFilter", i, "") as string;
          let url = `${credentials.baseUrl}/solutions/`;
          if (folderIdFilter) {
            url += `?folder=${encodeURIComponent(folderIdFilter)}`;
          }

          response = await this.helpers.httpRequest({
            ...baseConfig,
            method: "GET",
            url,
          });
        } else if (resource === "representative" && operation === "create") {
          const representativeEntityId = this.getNodeParameter("representativeEntityId", i) as string;
          const representativeEmail = this.getNodeParameter("representativeEmail", i) as string;
          const representativeFirstName = this.getNodeParameter("representativeFirstName", i, "") as string;
          const representativeLastName = this.getNodeParameter("representativeLastName", i, "") as string;
          const representativePhone = this.getNodeParameter("representativePhone", i, "") as string;
          const representativeRole = this.getNodeParameter("representativeRole", i, "") as string;
          const representativeDescription = this.getNodeParameter("representativeDescription", i, "") as string;

          const representativeData: any = {
            entity: representativeEntityId,
            email: representativeEmail,
          };

          if (representativeFirstName) representativeData.first_name = representativeFirstName;
          if (representativeLastName) representativeData.last_name = representativeLastName;
          if (representativePhone) representativeData.phone = representativePhone;
          if (representativeRole) representativeData.role = representativeRole;
          if (representativeDescription) representativeData.description = representativeDescription;

          response = await this.helpers.httpRequest({
            ...baseConfig,
            method: "POST",
            url: `${credentials.baseUrl}/representatives/`,
            body: representativeData,
          });
        } else if (resource === "representative" && operation === "list") {
          const representativeEntityId = this.getNodeParameter("representativeEntityId", i) as string;

          response = await this.helpers.httpRequest({
            ...baseConfig,
            method: "GET",
            url: `${credentials.baseUrl}/representatives/?entity=${encodeURIComponent(representativeEntityId)}`,
          });
        } else if (resource === "entityAssessment" && operation === "create") {
          const entityAssessmentName = this.getNodeParameter("entityAssessmentName", i) as string;
          const entityAssessmentEntityId = this.getNodeParameter("entityAssessmentEntityId", i) as string;
          const entityAssessmentPerimeterId = this.getNodeParameter("entityAssessmentPerimeterId", i) as string;
          const entityAssessmentDescription = this.getNodeParameter("entityAssessmentDescription", i, "") as string;
          const entityAssessmentComplianceAssessmentId = this.getNodeParameter("entityAssessmentComplianceAssessmentId", i, "") as string;
          const entityAssessmentConclusion = this.getNodeParameter("entityAssessmentConclusion", i, "") as string;

          const entityAssessmentData: any = {
            name: entityAssessmentName,
            entity: entityAssessmentEntityId,
            perimeter: entityAssessmentPerimeterId,
          };

          if (entityAssessmentDescription) entityAssessmentData.description = entityAssessmentDescription;
          if (entityAssessmentComplianceAssessmentId) entityAssessmentData.compliance_assessment = entityAssessmentComplianceAssessmentId;
          if (entityAssessmentConclusion) entityAssessmentData.conclusion = entityAssessmentConclusion;

          response = await this.helpers.httpRequest({
            ...baseConfig,
            method: "POST",
            url: `${credentials.baseUrl}/entity-assessments/`,
            body: entityAssessmentData,
          });
        } else if (resource === "entityAssessment" && operation === "getByName") {
          const entityAssessmentName = this.getNodeParameter("entityAssessmentName", i) as string;
          const entityAssessmentPerimeterId = this.getNodeParameter("entityAssessmentPerimeterId", i, "") as string;
          const entityAssessmentFolderId = this.getNodeParameter("entityAssessmentFolderId", i, "") as string;

          let url = `${credentials.baseUrl}/entity-assessments/?name=${encodeURIComponent(entityAssessmentName)}`;
          if (entityAssessmentPerimeterId) {
            url += `&perimeter=${encodeURIComponent(entityAssessmentPerimeterId)}`;
          }
          if (entityAssessmentFolderId) {
            url += `&folder=${encodeURIComponent(entityAssessmentFolderId)}`;
          }

          response = await this.helpers.httpRequest({
            ...baseConfig,
            method: "GET",
            url,
          });
        } else if (resource === "entityAssessment" && operation === "list") {
          const folderIdFilter = this.getNodeParameter("folderIdFilter", i, "") as string;
          let url = `${credentials.baseUrl}/entity-assessments/`;
          if (folderIdFilter) {
            url += `?folder=${encodeURIComponent(folderIdFilter)}`;
          }

          response = await this.helpers.httpRequest({
            ...baseConfig,
            method: "GET",
            url,
          });
        } else if (resource === "rightRequest" && operation === "create") {
          const rightRequestName = this.getNodeParameter("rightRequestName", i) as string;
          const folderId = this.getNodeParameter("folderId", i) as string;
          const rightRequestRequestedOn = this.getNodeParameter("rightRequestRequestedOn", i) as string;
          const rightRequestType = this.getNodeParameter("rightRequestType", i, "other") as string;
          const rightRequestStatus = this.getNodeParameter("rightRequestStatus", i, "new") as string;
          const rightRequestDescription = this.getNodeParameter("rightRequestDescription", i, "") as string;
          const rightRequestDueDate = this.getNodeParameter("rightRequestDueDate", i, "") as string;
          const rightRequestObservation = this.getNodeParameter("rightRequestObservation", i, "") as string;

          const rightRequestData: any = {
            name: rightRequestName,
            folder: folderId,
            requested_on: rightRequestRequestedOn,
            request_type: rightRequestType,
            status: rightRequestStatus,
          };

          if (rightRequestDescription) rightRequestData.description = rightRequestDescription;
          if (rightRequestDueDate) rightRequestData.due_date = rightRequestDueDate;
          if (rightRequestObservation) rightRequestData.observation = rightRequestObservation;

          response = await this.helpers.httpRequest({
            ...baseConfig,
            method: "POST",
            url: `${credentials.baseUrl}/right-requests/`,
            body: rightRequestData,
          });
        } else if (resource === "rightRequest" && operation === "getByName") {
          const rightRequestName = this.getNodeParameter("rightRequestName", i) as string;
          const folderId = this.getNodeParameter("folderId", i) as string;

          response = await this.helpers.httpRequest({
            ...baseConfig,
            method: "GET",
            url: `${credentials.baseUrl}/right-requests/?name=${encodeURIComponent(rightRequestName)}&folder=${encodeURIComponent(folderId)}`,
          });
        } else if (resource === "rightRequest" && operation === "list") {
          const folderIdFilter = this.getNodeParameter("folderIdFilter", i, "") as string;
          let url = `${credentials.baseUrl}/right-requests/`;
          if (folderIdFilter) {
            url += `?folder=${encodeURIComponent(folderIdFilter)}`;
          }

          response = await this.helpers.httpRequest({
            ...baseConfig,
            method: "GET",
            url,
          });
        } else if (resource === "rightRequest" && operation === "update") {
          const rightRequestId = this.getNodeParameter("rightRequestId", i) as string;
          const rightRequestType = this.getNodeParameter("rightRequestType", i, "") as string;
          const rightRequestStatus = this.getNodeParameter("rightRequestStatus", i, "") as string;
          const rightRequestDescription = this.getNodeParameter("rightRequestDescription", i, "") as string;
          const rightRequestDueDate = this.getNodeParameter("rightRequestDueDate", i, "") as string;
          const rightRequestObservation = this.getNodeParameter("rightRequestObservation", i, "") as string;

          const rightRequestData: any = {};

          if (rightRequestType) rightRequestData.request_type = rightRequestType;
          if (rightRequestStatus) rightRequestData.status = rightRequestStatus;
          if (rightRequestDescription) rightRequestData.description = rightRequestDescription;
          if (rightRequestDueDate) rightRequestData.due_date = rightRequestDueDate;
          if (rightRequestObservation) rightRequestData.observation = rightRequestObservation;

          response = await this.helpers.httpRequest({
            ...baseConfig,
            method: "PATCH",
            url: `${credentials.baseUrl}/right-requests/${rightRequestId}/`,
            body: rightRequestData,
          });
        } else if (resource === "dataBreach" && operation === "create") {
          const dataBreachName = this.getNodeParameter("dataBreachName", i) as string;
          const folderId = this.getNodeParameter("folderId", i) as string;
          const dataBreachDiscoveredOn = this.getNodeParameter("dataBreachDiscoveredOn", i) as string;
          const dataBreachType = this.getNodeParameter("dataBreachType", i, "privacy_other") as string;
          const dataBreachRiskLevel = this.getNodeParameter("dataBreachRiskLevel", i, "privacy_risk") as string;
          const dataBreachStatus = this.getNodeParameter("dataBreachStatus", i, "privacy_discovered") as string;
          const dataBreachDescription = this.getNodeParameter("dataBreachDescription", i, "") as string;
          const dataBreachAffectedSubjectsCount = this.getNodeParameter("dataBreachAffectedSubjectsCount", i, 0) as number;
          const dataBreachObservation = this.getNodeParameter("dataBreachObservation", i, "") as string;

          const dataBreachData: any = {
            name: dataBreachName,
            folder: folderId,
            discovered_on: dataBreachDiscoveredOn,
            breach_type: dataBreachType,
            risk_level: dataBreachRiskLevel,
            status: dataBreachStatus,
            affected_subjects_count: dataBreachAffectedSubjectsCount,
          };

          if (dataBreachDescription) dataBreachData.description = dataBreachDescription;
          if (dataBreachObservation) dataBreachData.observation = dataBreachObservation;

          response = await this.helpers.httpRequest({
            ...baseConfig,
            method: "POST",
            url: `${credentials.baseUrl}/data-breaches/`,
            body: dataBreachData,
          });
        } else if (resource === "dataBreach" && operation === "getByName") {
          const dataBreachName = this.getNodeParameter("dataBreachName", i) as string;
          const folderId = this.getNodeParameter("folderId", i) as string;

          response = await this.helpers.httpRequest({
            ...baseConfig,
            method: "GET",
            url: `${credentials.baseUrl}/data-breaches/?name=${encodeURIComponent(dataBreachName)}&folder=${encodeURIComponent(folderId)}`,
          });
        } else if (resource === "dataBreach" && operation === "list") {
          const folderIdFilter = this.getNodeParameter("folderIdFilter", i, "") as string;
          let url = `${credentials.baseUrl}/data-breaches/`;
          if (folderIdFilter) {
            url += `?folder=${encodeURIComponent(folderIdFilter)}`;
          }

          response = await this.helpers.httpRequest({
            ...baseConfig,
            method: "GET",
            url,
          });
        } else if (resource === "dataBreach" && operation === "update") {
          const dataBreachId = this.getNodeParameter("dataBreachId", i) as string;
          const dataBreachType = this.getNodeParameter("dataBreachType", i, "") as string;
          const dataBreachRiskLevel = this.getNodeParameter("dataBreachRiskLevel", i, "") as string;
          const dataBreachStatus = this.getNodeParameter("dataBreachStatus", i, "") as string;
          const dataBreachDescription = this.getNodeParameter("dataBreachDescription", i, "") as string;
          const dataBreachAffectedSubjectsCount = this.getNodeParameter("dataBreachAffectedSubjectsCount", i, -1) as number;
          const dataBreachObservation = this.getNodeParameter("dataBreachObservation", i, "") as string;

          const dataBreachData: any = {};

          if (dataBreachType) dataBreachData.breach_type = dataBreachType;
          if (dataBreachRiskLevel) dataBreachData.risk_level = dataBreachRiskLevel;
          if (dataBreachStatus) dataBreachData.status = dataBreachStatus;
          if (dataBreachDescription) dataBreachData.description = dataBreachDescription;
          if (dataBreachAffectedSubjectsCount >= 0) dataBreachData.affected_subjects_count = dataBreachAffectedSubjectsCount;
          if (dataBreachObservation) dataBreachData.observation = dataBreachObservation;

          response = await this.helpers.httpRequest({
            ...baseConfig,
            method: "PATCH",
            url: `${credentials.baseUrl}/data-breaches/${dataBreachId}/`,
            body: dataBreachData,
          });
        } else if (resource === "riskScenario" && operation === "create") {
          const riskScenarioName = this.getNodeParameter("riskScenarioName", i) as string;
          const riskScenarioRiskAssessmentId = this.getNodeParameter("riskScenarioRiskAssessmentId", i) as string;
          const riskScenarioDescription = this.getNodeParameter("riskScenarioDescription", i, "") as string;
          const riskScenarioRefId = this.getNodeParameter("riskScenarioRefId", i, "") as string;
          const riskScenarioTreatment = this.getNodeParameter("riskScenarioTreatment", i, "open") as string;
          const riskScenarioExistingControls = this.getNodeParameter("riskScenarioExistingControls", i, "") as string;
          const riskScenarioInherentProba = this.getNodeParameter("riskScenarioInherentProba", i, -1) as number;
          const riskScenarioInherentImpact = this.getNodeParameter("riskScenarioInherentImpact", i, -1) as number;
          const riskScenarioCurrentProba = this.getNodeParameter("riskScenarioCurrentProba", i, -1) as number;
          const riskScenarioCurrentImpact = this.getNodeParameter("riskScenarioCurrentImpact", i, -1) as number;
          const riskScenarioResidualProba = this.getNodeParameter("riskScenarioResidualProba", i, -1) as number;
          const riskScenarioResidualImpact = this.getNodeParameter("riskScenarioResidualImpact", i, -1) as number;
          const riskScenarioStrengthOfKnowledge = this.getNodeParameter("riskScenarioStrengthOfKnowledge", i, -1) as number;

          const riskScenarioData: any = {
            name: riskScenarioName,
            risk_assessment: riskScenarioRiskAssessmentId,
            treatment: riskScenarioTreatment,
            inherent_proba: riskScenarioInherentProba,
            inherent_impact: riskScenarioInherentImpact,
            current_proba: riskScenarioCurrentProba,
            current_impact: riskScenarioCurrentImpact,
            residual_proba: riskScenarioResidualProba,
            residual_impact: riskScenarioResidualImpact,
            strength_of_knowledge: riskScenarioStrengthOfKnowledge,
          };

          if (riskScenarioDescription) riskScenarioData.description = riskScenarioDescription;
          if (riskScenarioRefId) riskScenarioData.ref_id = riskScenarioRefId;
          if (riskScenarioExistingControls) riskScenarioData.existing_controls = riskScenarioExistingControls;

          response = await this.helpers.httpRequest({
            ...baseConfig,
            method: "POST",
            url: `${credentials.baseUrl}/risk-scenarios/`,
            body: riskScenarioData,
          });
        } else if (resource === "riskScenario" && operation === "getByName") {
          const riskScenarioName = this.getNodeParameter("riskScenarioName", i) as string;
          const riskScenarioRiskAssessmentId = this.getNodeParameter("riskScenarioRiskAssessmentId", i) as string;

          response = await this.helpers.httpRequest({
            ...baseConfig,
            method: "GET",
            url: `${credentials.baseUrl}/risk-scenarios/?name=${encodeURIComponent(riskScenarioName)}&risk_assessment=${encodeURIComponent(riskScenarioRiskAssessmentId)}`,
          });
        } else if (resource === "riskScenario" && operation === "list") {
          const folderIdFilter = this.getNodeParameter("folderIdFilter", i, "") as string;
          let url = `${credentials.baseUrl}/risk-scenarios/`;
          if (folderIdFilter) {
            url += `?folder=${encodeURIComponent(folderIdFilter)}`;
          }

          response = await this.helpers.httpRequest({
            ...baseConfig,
            method: "GET",
            url,
          });
        } else if (resource === "riskScenario" && operation === "update") {
          const riskScenarioId = this.getNodeParameter("riskScenarioId", i) as string;
          const riskScenarioDescription = this.getNodeParameter("riskScenarioDescription", i, "") as string;
          const riskScenarioRefId = this.getNodeParameter("riskScenarioRefId", i, "") as string;
          const riskScenarioTreatment = this.getNodeParameter("riskScenarioTreatment", i, "") as string;
          const riskScenarioExistingControls = this.getNodeParameter("riskScenarioExistingControls", i, "") as string;
          const riskScenarioInherentProba = this.getNodeParameter("riskScenarioInherentProba", i, -1) as number;
          const riskScenarioInherentImpact = this.getNodeParameter("riskScenarioInherentImpact", i, -1) as number;
          const riskScenarioCurrentProba = this.getNodeParameter("riskScenarioCurrentProba", i, -1) as number;
          const riskScenarioCurrentImpact = this.getNodeParameter("riskScenarioCurrentImpact", i, -1) as number;
          const riskScenarioResidualProba = this.getNodeParameter("riskScenarioResidualProba", i, -1) as number;
          const riskScenarioResidualImpact = this.getNodeParameter("riskScenarioResidualImpact", i, -1) as number;
          const riskScenarioStrengthOfKnowledge = this.getNodeParameter("riskScenarioStrengthOfKnowledge", i, -1) as number;

          const riskScenarioData: any = {
            inherent_proba: riskScenarioInherentProba,
            inherent_impact: riskScenarioInherentImpact,
            current_proba: riskScenarioCurrentProba,
            current_impact: riskScenarioCurrentImpact,
            residual_proba: riskScenarioResidualProba,
            residual_impact: riskScenarioResidualImpact,
            strength_of_knowledge: riskScenarioStrengthOfKnowledge,
          };

          if (riskScenarioDescription) riskScenarioData.description = riskScenarioDescription;
          if (riskScenarioRefId) riskScenarioData.ref_id = riskScenarioRefId;
          if (riskScenarioTreatment) riskScenarioData.treatment = riskScenarioTreatment;
          if (riskScenarioExistingControls) riskScenarioData.existing_controls = riskScenarioExistingControls;

          response = await this.helpers.httpRequest({
            ...baseConfig,
            method: "PATCH",
            url: `${credentials.baseUrl}/risk-scenarios/${riskScenarioId}/`,
            body: riskScenarioData,
          });
        } else if (resource === "riskMatrix" && operation === "list") {
          response = await this.helpers.httpRequest({
            ...baseConfig,
            method: "GET",
            url: `${credentials.baseUrl}/risk-matrices/`,
          });
        } else if (resource === "framework" && operation === "list") {
          response = await this.helpers.httpRequest({
            ...baseConfig,
            method: "GET",
            url: `${credentials.baseUrl}/frameworks/`,
          });
        } else {
          throw new Error(`Unknown resource/operation: ${resource}/${operation}`);
        }

        returnData.push({
          json: response,
          pairedItem: { item: i },
        });
      } catch (err: unknown) {
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
