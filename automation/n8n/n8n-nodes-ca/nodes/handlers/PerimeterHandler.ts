import type { IDataObject } from "n8n-workflow";
import type { IResourceContext } from "../types";
import { BaseResourceHandler } from "./BaseResourceHandler";

/**
 * Handler for perimeter operations
 */
export class PerimeterHandler extends BaseResourceHandler {
  protected getEndpoint(): string {
    return "perimeters";
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
    const perimeterName = this.getParameter<string>("perimeterName");
    const perimeterDescription = this.getParameter<string>(
      "perimeterDescription",
      "",
    );
    const folderId = this.getParameter<string>("folderId");
    const additionalFields = this.getParameter<any>("additionalFields", {});

    const body: any = {
      name: perimeterName,
      description: perimeterDescription,
      folder: folderId,
    };

    // Add additional fields
    if (additionalFields.owner) {
      body.owner = additionalFields.owner;
    }
    if (additionalFields.tags) {
      body.tags = additionalFields.tags
        .split(",")
        .map((tag: string) => tag.trim());
    }

    return this.createResource(body);
  }

  private async getByNameOp(): Promise<IDataObject> {
    const perimeterName = this.getParameter<string>("perimeterName");
    const folderId = this.getParameter<string>("folderId");

    return this.getByName(perimeterName, {
      folder: folderId,
    });
  }

  private async list(): Promise<IDataObject> {
    const folderIdFilter = this.getParameter<string>("folderIdFilter", "");
    return this.listResources(folderIdFilter);
  }
}
