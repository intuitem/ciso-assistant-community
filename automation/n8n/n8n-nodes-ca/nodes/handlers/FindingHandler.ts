import type { IDataObject } from "n8n-workflow";
import type { IResourceContext } from "../types";
import { BaseResourceHandler } from "./BaseResourceHandler";

/**
 * Handler for finding operations
 */
export class FindingHandler extends BaseResourceHandler {
  protected getEndpoint(): string {
    return "findings";
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
        case "getByName":
          return await this.getByNameOp();
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
    const findingName = this.getParameter<string>("findingName");
    const findingsAssessmentId = this.getParameter<string>(
      "findingsAssessmentId",
    );
    const folderId = this.getParameter<string>("folderId");
    const findingDescription = this.getParameter<string>(
      "findingDescription",
      "",
    );
    const findingSeverity = this.getParameter<number>("findingSeverity", -1);
    const findingStatus = this.getParameter<string>(
      "findingStatus",
      "identified",
    );

    const body = this.buildBody(
      {
        name: findingName,
        findings_assessment: findingsAssessmentId,
        folder: folderId,
        status: findingStatus,
      },
      {
        description: findingDescription,
        severity: findingSeverity,
      },
    );

    return this.createResource(body);
  }

  private async getByNameOp(): Promise<IDataObject> {
    const findingName = this.getParameter<string>("findingName");
    const folderId = this.getParameter<string>("folderId");

    return this.getByName(findingName, { folder: folderId });
  }

  private async list(): Promise<IDataObject> {
    const folderIdFilter = this.getParameter<string>("folderIdFilter", "");
    return this.listResources(folderIdFilter);
  }

  private async update(): Promise<IDataObject> {
    const findingId = this.getParameter<string>("findingId");
    const findingStatusUpdate = this.getParameter<string>(
      "findingStatusUpdate",
      "",
    );
    const findingSeverityUpdate = this.getParameter<number>(
      "findingSeverityUpdate",
      -1,
    );

    const body = this.buildBody(
      {},
      {
        status: findingStatusUpdate,
        severity: findingSeverityUpdate,
      },
    );

    return this.updateResource(findingId, body);
  }
}
