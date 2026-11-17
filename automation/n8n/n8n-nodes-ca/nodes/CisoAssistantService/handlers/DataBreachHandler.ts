import type { IDataObject } from "n8n-workflow";
import type { IResourceContext } from "../types";
import { BaseResourceHandler } from "./BaseResourceHandler";

/**
 * Handler for data breach operations (Privacy/GDPR)
 */
export class DataBreachHandler extends BaseResourceHandler {
  protected getEndpoint(): string {
    return "data-breaches";
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
    const dataBreachFolderId = this.getParameter<string>("dataBreachFolderId");
    const dataBreachName = this.getParameter<string>("dataBreachName");
    const dataBreachDescription = this.getParameter<string>(
      "dataBreachDescription",
      "",
    );
    const dataBreachSeverity = this.getParameter<number>(
      "dataBreachSeverity",
      -1,
    );
    const dataBreachStatus = this.getParameter<string>(
      "dataBreachStatus",
      "open",
    );

    const body = this.buildBody(
      {
        folder: dataBreachFolderId,
        name: dataBreachName,
        status: dataBreachStatus,
      },
      {
        description: dataBreachDescription,
        severity: dataBreachSeverity,
      },
    );

    return this.createResource(body);
  }

  private async list(): Promise<IDataObject> {
    const folderIdFilter = this.getParameter<string>("folderIdFilter", "");
    return this.listResources(folderIdFilter);
  }
}
