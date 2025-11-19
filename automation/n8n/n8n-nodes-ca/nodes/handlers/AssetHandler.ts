import type { IDataObject } from "n8n-workflow";
import type { IResourceContext } from "../types";
import { BaseResourceHandler } from "./BaseResourceHandler";

/**
 * Handler for asset operations
 */
export class AssetHandler extends BaseResourceHandler {
  protected getEndpoint(): string {
    return "assets";
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
    const assetName = this.getParameter<string>("assetName");
    const folderId = this.getParameter<string>("folderId");
    const assetDescription = this.getParameter<string>("assetDescription", "");
    const assetType = this.getParameter<string>("assetType");
    const additionalFields = this.getParameter<any>("additionalFields", {});

    const body: any = {
      name: assetName,
      folder: folderId,
      description: assetDescription,
      type: assetType,
    };

    // Add additional fields
    if (additionalFields.businessValue) {
      body.business_value = additionalFields.businessValue;
    }
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
    const assetName = this.getParameter<string>("assetName");
    const folderId = this.getParameter<string>("folderId", "");

    const additionalParams: Record<string, string> = {};
    if (folderId) {
      additionalParams.folder = folderId;
    }

    return this.getByName(assetName, additionalParams);
  }

  private async list(): Promise<IDataObject> {
    const folderIdFilter = this.getParameter<string>("folderIdFilter", "");
    return this.listResources(folderIdFilter);
  }

  private async update(): Promise<IDataObject> {
    const assetId = this.getParameter<string>("assetId");
    const assetDescription = this.getParameter<string>("assetDescription");
    const assetType = this.getParameter<string>("assetType");
    const assetNameUpdate = this.getParameter<string>("assetNameUpdate");

    const body = this.buildUpdateBody({
      name: assetNameUpdate,
      description: assetDescription,
      type: assetType,
    });

    return this.updateResource(assetId, body);
  }
}
