import type { IDataObject } from "n8n-workflow";
import type { IResourceContext } from "../types";
import { BaseResourceHandler } from "./BaseResourceHandler";

/**
 * Handler for domain (folder) operations
 * Note: Domains are implemented as folders in the backend
 */
export class DomainHandler extends BaseResourceHandler {
  protected getEndpoint(): string {
    return "folders";
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
        default:
          throw new Error(`Unknown operation: ${operation}`);
      }
    } catch (error) {
      return this.handleError(error, operation);
    }
  }

  private async create(): Promise<IDataObject> {
    const domainName = this.getParameter<string>("domainName");
    const domainDescription = this.getParameter<string>(
      "domainDescription",
      "",
    );
    const additionalFields = this.getParameter<any>("additionalFields", {});

    const body = this.buildBody(
      {
        name: domainName,
        description: domainDescription,
      },
      {
        owner: additionalFields.owner,
      },
    );

    return this.createResource(body);
  }

  private async getByNameOp(): Promise<IDataObject> {
    const domainName = this.getParameter<string>("domainName");
    return this.getByName(domainName);
  }

  private async list(): Promise<IDataObject> {
    const folderIdFilter = this.getParameter<string>("folderIdFilter", "");
    return this.listResources(folderIdFilter);
  }
}
