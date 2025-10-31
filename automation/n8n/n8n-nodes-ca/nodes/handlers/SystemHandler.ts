import type { IDataObject } from "n8n-workflow";
import type { IResourceContext } from "../types";
import { BaseResourceHandler } from "./BaseResourceHandler";

/**
 * Handler for system operations (build info, users)
 */
export class SystemHandler extends BaseResourceHandler {
  protected getEndpoint(): string {
    return "system";
  }

  public async execute(
    operation: string,
    context: IResourceContext,
  ): Promise<IDataObject> {
    this.context = context;

    try {
      switch (operation) {
        case "getBuild":
          return await this.getBuildInfo();
        case "getUserByEmail":
          return await this.getUserByEmail();
        case "listUsers":
          return await this.listUsers();
        default:
          throw new Error(`Unknown operation: ${operation}`);
      }
    } catch (error) {
      return this.handleError(error, operation);
    }
  }

  private async getBuildInfo(): Promise<IDataObject> {
    return this.request("GET", "/build");
  }

  private async getUserByEmail(): Promise<IDataObject> {
    const userEmail = this.getParameter<string>("userEmail");
    return this.request(
      "GET",
      `/users/?email=${encodeURIComponent(userEmail)}`,
    );
  }

  private async listUsers(): Promise<IDataObject> {
    return this.request("GET", "/users/");
  }
}
