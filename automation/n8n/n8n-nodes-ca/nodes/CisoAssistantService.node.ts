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
            operation: ["create"],
          },
        },
        default: "",
        placeholder: "Web Server",
        description: "The name of the asset",
        required: true,
      },
      {
        displayName: "Folder ID",
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
        displayName: "Asset Description",
        name: "assetDescription",
        type: "string",
        typeOptions: {
          rows: 3,
        },
        displayOptions: {
          show: {
            resource: ["asset"],
            operation: ["create"],
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
            operation: ["create"],
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
            operation: ["getRequirementAssessment", "updateRequirementAssessment"],
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
            operation: ["create"],
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
            operation: ["create"],
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
            operation: ["create"],
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
            operation: ["create"],
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
            operation: ["create"],
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
            operation: ["create"],
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
            operation: ["create"],
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
        description: "The severity of the vulnerability",
      },
      {
        displayName: "Reference ID",
        name: "vulnerabilityRefId",
        type: "string",
        displayOptions: {
          show: {
            resource: ["vulnerability"],
            operation: ["create"],
          },
        },
        default: "",
        placeholder: "VULN-2025-001",
        description: "Reference ID for the vulnerability",
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
          response = await this.helpers.httpRequest({
            ...baseConfig,
            method: "GET",
            url: `${credentials.baseUrl}/perimeters/?name=${encodeURIComponent(perimeterName)}`,
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
          response = await this.helpers.httpRequest({
            ...baseConfig,
            method: "GET",
            url: `${credentials.baseUrl}/folders/`,
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
            url: `${credentials.baseUrl}/audits/`,
            body: auditData,
          });
        } else if (resource === "audit" && operation === "getByName") {
          const auditName = this.getNodeParameter("auditName", i) as string;
          response = await this.helpers.httpRequest({
            ...baseConfig,
            method: "GET",
            url: `${credentials.baseUrl}/audits/?name=${encodeURIComponent(auditName)}`,
          });
        } else if (resource === "audit" && operation === "getByRefId") {
          const auditRefId = this.getNodeParameter("auditRefId", i) as string;
          response = await this.helpers.httpRequest({
            ...baseConfig,
            method: "GET",
            url: `${credentials.baseUrl}/audits/?ref_id=${encodeURIComponent(auditRefId)}`,
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
