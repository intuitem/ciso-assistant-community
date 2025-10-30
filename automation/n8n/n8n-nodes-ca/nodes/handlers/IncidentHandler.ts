import type { IDataObject } from "n8n-workflow";
import type { IResourceContext } from "../types";
import { BaseResourceHandler } from "./BaseResourceHandler";

/**
 * Handler for incident operations
 */
export class IncidentHandler extends BaseResourceHandler {
  protected getEndpoint(): string {
    return "incidents";
  }

  public async execute(
    operation: string,
    context: IResourceContext,
  ): Promise<IDataObject> {
    this.context = context;

    try {
      switch (operation) {
        case "create":
          return await this.create();
        case "list":
          return await this.list();
        case "update":
          return await this.update();
        default:
          throw new Error(`Unknown operation: ${operation}`);
      }
    } catch (error) {
      return this.handleError(error, operation);
    }
  }

  private async create(): Promise<IDataObject> {
    const incidentName = this.getParameter<string>("incidentName");
    const folderId = this.getParameter<string>("folderId");
    const incidentDescription = this.getParameter<string>(
      "incidentDescription",
      "",
    );
    const incidentStatus = this.getParameter<string>("incidentStatus", "new");
    const incidentSeverity = this.getParameter<number>("incidentSeverity", 3);
    const incidentDetection = this.getParameter<string>(
      "incidentDetection",
      "internally_detected",
    );
    const incidentRefId = this.getParameter<string>("incidentRefId", "");

    const body = this.buildBody(
      {
        name: incidentName,
        folder: folderId,
        description: incidentDescription,
        status: incidentStatus,
        severity: incidentSeverity,
        detection: incidentDetection,
      },
      {
        ref_id: incidentRefId,
      },
    );

    return this.createResource(body);
  }

  private async list(): Promise<IDataObject> {
    const folderIdFilter = this.getParameter<string>("folderIdFilter", "");
    return this.listResources(folderIdFilter);
  }

  private async update(): Promise<IDataObject> {
    const incidentId = this.getParameter<string>("incidentId");
    const incidentDescription = this.getParameter<string>(
      "incidentDescription",
    );
    const incidentStatus = this.getParameter<string>("incidentStatus");
    const incidentSeverity = this.getParameter<number>("incidentSeverity");
    const incidentDetection = this.getParameter<string>(
      "incidentDetection",
    );
    const incidentRefId = this.getParameter<string>("incidentRefId");

    const body = this.buildUpdateBody({
      description: incidentDescription,
      status: incidentStatus,
      severity: incidentSeverity,
      detection: incidentDetection,
      ref_id: incidentRefId,
    });

    return this.updateResource(incidentId, body);
  }
}
