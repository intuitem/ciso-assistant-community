import type { IDataObject } from "n8n-workflow";
import type { IResourceContext } from "../types";
import { BaseResourceHandler } from "./BaseResourceHandler";

/**
 * Handler for solution operations (TPRM)
 */
export class SolutionHandler extends BaseResourceHandler {
  protected getEndpoint(): string {
    return "solutions";
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
    const solutionName = this.getParameter<string>("solutionName");
    const providerEntityId = this.getParameter<string>("providerEntityId");
    const recipientEntityId = this.getParameter<string>(
      "recipientEntityId",
      "",
    );
    const solutionDescription = this.getParameter<string>(
      "solutionDescription",
      "",
    );
    const solutionRefId = this.getParameter<string>("solutionRefId", "");
    const solutionCriticality = this.getParameter<number>(
      "solutionCriticality",
      0,
    );

    const body = this.buildBody(
      {
        name: solutionName,
        provider_entity: providerEntityId,
      },
      {
        recipient_entity: recipientEntityId,
        description: solutionDescription,
        ref_id: solutionRefId,
        criticality: solutionCriticality,
      },
    );

    return this.createResource(body);
  }

  private async getByNameOp(): Promise<IDataObject> {
    const solutionName = this.getParameter<string>("solutionName");
    const providerEntityId = this.getParameter<string>("providerEntityId");

    return this.getByName(solutionName, { provider_entity: providerEntityId });
  }

  private async list(): Promise<IDataObject> {
    const folderIdFilter = this.getParameter<string>("folderIdFilter", "");
    return this.listResources(folderIdFilter);
  }
}
