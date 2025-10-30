import type { IDataObject } from "n8n-workflow";
import type { IResourceContext } from "../types";
import { BaseResourceHandler } from "./BaseResourceHandler";

/**
 * Handler for right request operations (Privacy/GDPR)
 */
export class RightRequestHandler extends BaseResourceHandler {
  protected getEndpoint(): string {
    return "right-requests";
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
        default:
          throw new Error(`Unknown operation: ${operation}`);
      }
    } catch (error) {
      return this.handleError(error, operation);
    }
  }

  private async create(): Promise<IDataObject> {
    const rightRequestFolderId = this.getParameter<string>(
      "rightRequestFolderId",
    );
    const rightRequestType = this.getParameter<string>("rightRequestType");
    const rightRequestStatus = this.getParameter<string>(
      "rightRequestStatus",
      "open",
    );
    const rightRequestDescription = this.getParameter<string>(
      "rightRequestDescription",
      "",
    );

    const body = this.buildBody(
      {
        folder: rightRequestFolderId,
        type: rightRequestType,
        status: rightRequestStatus,
      },
      {
        description: rightRequestDescription,
      },
    );

    return this.createResource(body);
  }

  private async list(): Promise<IDataObject> {
    const folderIdFilter = this.getParameter<string>("folderIdFilter", "");
    return this.listResources(folderIdFilter);
  }
}
