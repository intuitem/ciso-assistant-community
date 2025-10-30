import type { IDataObject } from "n8n-workflow";
import type { IResourceContext } from "../types";
import { BaseResourceHandler } from "./BaseResourceHandler";

/**
 * Handler for entity operations (TPRM)
 */
export class EntityHandler extends BaseResourceHandler {
  protected getEndpoint(): string {
    return "entities";
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
    const entityName = this.getParameter<string>("entityName");
    const folderId = this.getParameter<string>("folderId");
    const entityDescription = this.getParameter<string>(
      "entityDescription",
      "",
    );
    const entityMission = this.getParameter<string>("entityMission", "");
    const entityReferenceLink = this.getParameter<string>(
      "entityReferenceLink",
      "",
    );

    const body = this.buildBody(
      {
        name: entityName,
        folder: folderId,
      },
      {
        description: entityDescription,
        mission: entityMission,
        reference_link: entityReferenceLink,
      },
    );

    return this.createResource(body);
  }

  private async getByNameOp(): Promise<IDataObject> {
    const entityName = this.getParameter<string>("entityName");
    const folderId = this.getParameter<string>("folderId");

    return this.getByName(entityName, { folder: folderId });
  }

  private async list(): Promise<IDataObject> {
    const folderIdFilter = this.getParameter<string>("folderIdFilter", "");
    return this.listResources(folderIdFilter);
  }
}
