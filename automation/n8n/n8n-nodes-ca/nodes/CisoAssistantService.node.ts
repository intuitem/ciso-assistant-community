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
    subtitle: '={{$parameter["operation"]}}',
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
      {
        displayName: "Operation",
        name: "operation",
        type: "options",
        noDataExpression: true,
        options: [
          {
            name: "Get Build Info",
            value: "getBuild",
            description: "Get build information from CISO Assistant",
            action: "Get build information",
          },
          {
            name: "Create Perimeter",
            value: "createPerimeter",
            description: "Create a new perimeter and return its UUID",
            action: "Create a perimeter",
          },
          {
            name: "Update evidence",
            value: "updateEvidence",
            description: "Update an evidence by its domain and ref_id",
            action: "Update an evidence",
          },
          {
            name: "Update control status",
            value: "updateAppliedControl",
            description: "Update an applied control by ref_id",
            action: "Update an applied control",
          },
          {
            name: "Sync Audit to scan",
            value: "syncAuditToScan",
            description: "Update an audit",
            action: "Sync Audit to scan results",
          },
          {
            name: "Create Domain",
            value: "createDomain",
            description: "Create a new domain and return its UUID",
            action: "Create a domain",
          },
          {
            name: "Create Asset",
            value: "createAsset",
            description: "Create a new asset and return its UUID",
            action: "Create an asset",
          },
          {
            name: "Initiate Audit",
            value: "initiateAudit",
            description: "Initiate an audit for a perimeter with a framework",
            action: "Initiate an audit",
          },
          {
            name: "Initiate Risk Assessment",
            value: "initiateRiskAssessment",
            description:
              "Initiate a risk assessment for a perimeter with a risk matrix",
            action: "Initiate a risk assessment",
          },
          {
            name: "Get Domains",
            value: "getDomains",
            description: "Pull all domains",
            action: "Get domains",
          },
          {
            name: "Get Risk Matrices",
            value: "getRiskMatrices",
            description: "Pull all loaded risk matrices",
            action: "Get risk matrices",
          },
          {
            name: "Get Frameworks",
            value: "getFrameworks",
            description: "Pull all loaded frameworks",
            action: "Get frameworks",
          },
        ],
        default: "getBuild",
      },
      {
        displayName: "Attachment",
        name: "attachment",
        type: "string",
        displayOptions: {
          show: {
            operation: ["updateEvidence"],
          },
        },
        default: "",
        placeholder: "",
        description: "Attachment to use as evidence",
        required: true,
      },
      {
        displayName: "Ref ID",
        name: "refId",
        type: "string",
        displayOptions: {
          show: {
            operation: ["updateEvidence"],
          },
        },
        default: "",
        placeholder: "",
        description: "ref_id to use as a selector",
        required: true,
      },
      // Perimeter fields
      {
        displayName: "Perimeter Name",
        name: "perimeterName",
        type: "string",
        displayOptions: {
          show: {
            operation: ["createPerimeter"],
          },
        },
        default: "",
        placeholder: "My Security Perimeter",
        description: "The name of the perimeter",
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
            operation: ["createPerimeter"],
          },
        },
        default: "",
        placeholder: "Description of the security perimeter",
        description: "The description of the perimeter",
      },
      // Domain fields
      {
        displayName: "Domain Name",
        name: "domainName",
        type: "string",
        displayOptions: {
          show: {
            operation: ["createDomain"],
          },
        },
        default: "",
        placeholder: "IT Infrastructure",
        description: "The name of the domain",
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
            operation: ["createDomain"],
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
            operation: ["createAsset"],
          },
        },
        default: "",
        placeholder: "Web Server",
        description: "The name of the asset",
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
            operation: ["createAsset"],
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
            operation: ["createAsset"],
          },
        },
        options: [
          {
            name: "Primary",
            value: "primary",
          },
          {
            name: "Support",
            value: "support",
          },
          {
            name: "System",
            value: "system",
          },
        ],
        default: "primary",
        description: "The type of the asset",
      },
      // Audit fields
      {
        displayName: "Perimeter ID",
        name: "perimeterId",
        type: "string",
        displayOptions: {
          show: {
            operation: ["initiateAudit", "initiateRiskAssessment"],
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
            operation: ["initiateAudit"],
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
            operation: ["initiateAudit"],
          },
        },
        default: "",
        placeholder: "Security Audit 2025",
        description: "The name of the audit",
        required: true,
      },
      // Risk Assessment fields
      {
        displayName: "Risk Matrix ID",
        name: "riskMatrixId",
        type: "string",
        displayOptions: {
          show: {
            operation: ["initiateRiskAssessment"],
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
            operation: ["initiateRiskAssessment"],
          },
        },
        default: "",
        placeholder: "Risk Assessment 2025",
        description: "The name of the risk assessment",
        required: true,
      },
      // Additional fields for assets
      {
        displayName: "Additional Fields",
        name: "additionalFields",
        type: "collection",
        default: {},
        placeholder: "Add Field",
        displayOptions: {
          show: {
            operation: ["createAsset", "createDomain", "createPerimeter", "updateEvidence"],
          },
        },
        options: [
          {
            displayName: "Business Value",
            name: "businessValue",
            type: "options",
            displayOptions: {
              show: {
                "/operation": ["createAsset"],
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

        switch (operation) {
          case "getBuild":
            response = await this.helpers.httpRequest({
              ...baseConfig,
              method: "GET",
              url: `${credentials.baseUrl}/build`,
            });
            break;

          case "createPerimeter":
            const perimeterName = this.getNodeParameter(
              "perimeterName",
              i,
            ) as string;
            const perimeterDescription = this.getNodeParameter(
              "perimeterDescription",
              i,
              "",
            ) as string;
            const perimeterAdditionalFields = this.getNodeParameter(
              "additionalFields",
              i,
              {},
            ) as any;

            const perimeterData: any = {
              name: perimeterName,
              description: perimeterDescription,
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
            break;

          case "createDomain":
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
              url: `${credentials.baseUrl}/domains/`,
              body: domainData,
            });
            break;

          case "createAsset":
            const assetName = this.getNodeParameter("assetName", i) as string;
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
            break;

          case "initiateAudit":
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
            break;

          case "initiateRiskAssessment":
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
            break;

          case "getRiskMatrices":
            response = await this.helpers.httpRequest({
              ...baseConfig,
              method: "GET",
              url: `${credentials.baseUrl}/risk-matrices/`,
            });
            break;

          case "getDomains":
            response = await this.helpers.httpRequest({
              ...baseConfig,
              method: "GET",
              url: `${credentials.baseUrl}/folders/`,
            });
            break;

          case "getFrameworks":
            response = await this.helpers.httpRequest({
              ...baseConfig,
              method: "GET",
              url: `${credentials.baseUrl}/frameworks/`,
            });
            break;

          default:
            throw new Error(`Unknown operation: ${operation}`);
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
