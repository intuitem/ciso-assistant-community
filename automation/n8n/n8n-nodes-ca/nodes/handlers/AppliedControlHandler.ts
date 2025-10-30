import type { IDataObject } from "n8n-workflow";
import type { IResourceContext } from "../types";
import { BaseResourceHandler } from "./BaseResourceHandler";

/**
 * Handler for applied control operations
 */
export class AppliedControlHandler extends BaseResourceHandler {
  protected getEndpoint(): string {
    return "applied-controls";
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
    const appliedControlName = this.getParameter<string>("appliedControlName");
    const folderId = this.getParameter<string>("folderId");
    const appliedControlDescription = this.getParameter<string>(
      "appliedControlDescription",
      "",
    );
    const appliedControlStatus = this.getParameter<string>(
      "appliedControlStatus",
      "to_do",
    );

    const body = {
      name: appliedControlName,
      folder: folderId,
      description: appliedControlDescription,
      status: appliedControlStatus,
    };

    return this.createResource(body);
  }

  private async getByNameOp(): Promise<IDataObject> {
    const appliedControlName = this.getParameter<string>("appliedControlName");
    const folderId = this.getParameter<string>("folderId");

    return this.getByName(appliedControlName, { folder: folderId });
  }

  private async list(): Promise<IDataObject> {
    const folderIdFilter = this.getParameter<string>("folderIdFilter", "");
    return this.listResources(folderIdFilter);
  }

  private async update(): Promise<IDataObject> {
    const appliedControlId = this.getParameter<string>("appliedControlId");
    const appliedControlStatus = this.getParameter<string>(
      "appliedControlStatus",
    );

    const body = this.buildUpdateBody({ status: appliedControlStatus });

    return this.updateResource(appliedControlId, body);
  }
}
