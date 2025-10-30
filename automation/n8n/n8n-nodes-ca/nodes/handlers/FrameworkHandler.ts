import type { IDataObject } from "n8n-workflow";
import type { IResourceContext } from "../types";
import { BaseResourceHandler } from "./BaseResourceHandler";

/**
 * Handler for framework operations
 */
export class FrameworkHandler extends BaseResourceHandler {
  protected getEndpoint(): string {
    return "frameworks";
  }

  public async execute(
    operation: string,
    context: IResourceContext,
  ): Promise<IDataObject> {
    this.context = context;

    try {
      switch (operation) {
        case "list":
          return await this.list();
        default:
          throw new Error(`Unknown operation: ${operation}`);
      }
    } catch (error) {
      return this.handleError(error, operation);
    }
  }

  private async list(): Promise<IDataObject> {
    return this.request("GET", `/${this.getEndpoint()}/`);
  }
}
