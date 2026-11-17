import type { IDataObject } from "n8n-workflow";
import type { IResourceContext } from "../types";
import { BaseResourceHandler } from "./BaseResourceHandler";

/**
 * Handler for representative operations (TPRM)
 */
export class RepresentativeHandler extends BaseResourceHandler {
  protected getEndpoint(): string {
    return "representatives";
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
    const representativeEntityId = this.getParameter<string>(
      "representativeEntityId",
    );
    const representativeEmail = this.getParameter<string>(
      "representativeEmail",
    );
    const representativeFirstName = this.getParameter<string>(
      "representativeFirstName",
      "",
    );
    const representativeLastName = this.getParameter<string>(
      "representativeLastName",
      "",
    );
    const representativePhone = this.getParameter<string>(
      "representativePhone",
      "",
    );
    const representativeRole = this.getParameter<string>(
      "representativeRole",
      "",
    );
    const representativeDescription = this.getParameter<string>(
      "representativeDescription",
      "",
    );

    const body = this.buildBody(
      {
        entity: representativeEntityId,
        email: representativeEmail,
      },
      {
        first_name: representativeFirstName,
        last_name: representativeLastName,
        phone: representativePhone,
        role: representativeRole,
        description: representativeDescription,
      },
    );

    return this.createResource(body);
  }

  private async list(): Promise<IDataObject> {
    const representativeEntityId = this.getParameter<string>(
      "representativeEntityId",
    );
    return this.listResources(undefined, undefined, {
      entity: representativeEntityId,
    });
  }
}
