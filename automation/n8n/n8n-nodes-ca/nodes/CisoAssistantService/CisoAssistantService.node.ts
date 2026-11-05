import {
  NodeApiError,
  NodeConnectionTypes,
  NodeOperationError,
} from "n8n-workflow";
import type {
  IDataObject,
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
import { resources, sharedFields } from "./resources";

export class CisoAssistantService implements INodeType {
  description: INodeTypeDescription = {
    displayName: "CISO Assistant",
    name: "cisoAssistantService",
    icon: "file:../../icons/cisoAssistant.svg",
    group: ["transform"],
    version: [1, 2],
    subtitle: '={{$parameter["resource"] + ": " + $parameter["operation"]}}',
    description: "Interact with CISO Assistant API",
    defaults: {
      name: "CISO Assistant",
    },
    usableAsTool: true,
    inputs: [NodeConnectionTypes.Main],
    outputs: [NodeConnectionTypes.Main],
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
            name: "Applied Control",
            value: "appliedControl",
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
            name: "Data Breach",
            value: "dataBreach",
          },
          {
            name: "Domain",
            value: "domain",
          },
          {
            name: "Entity",
            value: "entity",
          },
          {
            name: "Entity Assessment",
            value: "entityAssessment",
          },
          {
            name: "Evidence",
            value: "evidence",
          },
          {
            name: "Finding",
            value: "finding",
          },
          {
            name: "Findings Tracking",
            value: "findingsAssessment",
          },
          {
            name: "Framework",
            value: "framework",
          },
          {
            name: "Incident",
            value: "incident",
          },
          {
            name: "Perimeter",
            value: "perimeter",
          },
          {
            name: "Representative",
            value: "representative",
          },
          {
            name: "Right Request",
            value: "rightRequest",
          },
          {
            name: "Risk Assessment",
            value: "riskAssessment",
          },
          {
            name: "Risk Matrix",
            value: "riskMatrix",
          },
          {
            name: "Risk Scenario",
            value: "riskScenario",
          },
          {
            name: "Security Exception",
            value: "securityException",
          },
          {
            name: "Solution",
            value: "solution",
          },
          {
            name: "System",
            value: "system",
          },
          {
            name: "Task Definition",
            value: "taskDefinition",
          },
          {
            name: "Task Occurrence",
            value: "taskOccurrence",
          },
          {
            name: "Vulnerability",
            value: "vulnerability",
          },
        ],
        default: "system",
      },
      ...resources.map((r) => r.operations),
      // Shared list options
      {
        displayName: "Return All",
        name: "returnAll",
        type: "boolean",
        displayOptions: {
          show: {
            operation: ["list", "listUsers"],
          },
        },
        // true keeps workflows saved before this option fetching whole collections.
        default: true,
        description:
          "Whether to return all results or only up to a given limit",
      },
      {
        displayName: "Limit",
        name: "limit",
        type: "number",
        typeOptions: {
          minValue: 1,
        },
        displayOptions: {
          show: {
            operation: ["list", "listUsers"],
            returnAll: [false],
          },
        },
        default: 50,
        description: "Max number of results to return",
      },
      ...resources.flatMap((r) => r.fields),
      ...sharedFields,
    ],
  };

  async execute(this: IExecuteFunctions): Promise<INodeExecutionData[][]> {
    const items = this.getInputData();
    const returnData: INodeExecutionData[] = [];
    // v1 returns list-shaped responses as one {count, results} item; v2 emits one item per row.
    const splitResults = this.getNode().typeVersion >= 2;

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
        const response =
          operation === "get"
            ? await handler.get(context)
            : await handler.execute(operation, context);

        const rows =
          splitResults && Array.isArray(response.results)
            ? (response.results as IDataObject[])
            : response;
        returnData.push(
          ...this.helpers.constructExecutionMetaData(
            this.helpers.returnJsonArray(rows),
            { itemData: { item: i } },
          ),
        );
      } catch (err: unknown) {
        // Handle errors based on continueOnFail setting
        if (this.continueOnFail()) {
          const errorMessage = err instanceof Error ? err.message : String(err);
          returnData.push({
            json: { error: errorMessage },
            pairedItem: { item: i },
          });
          continue;
        }
        throw err instanceof NodeApiError
          ? err
          : new NodeOperationError(this.getNode(), err as Error, {
              itemIndex: i,
            });
      }
    }

    return [returnData];
  }
}
