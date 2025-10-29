import type { IDataObject } from "n8n-workflow";
import type { IResourceContext } from "../types";
import { BaseResourceHandler } from "./BaseResourceHandler";

/**
 * Handler for security exception operations
 */
export class SecurityExceptionHandler extends BaseResourceHandler {
  protected getEndpoint(): string {
    return "security-exceptions";
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
    const securityExceptionName = this.getParameter<string>(
      "securityExceptionName",
    );
    const folderId = this.getParameter<string>("folderId");
    const securityExceptionDescription = this.getParameter<string>(
      "securityExceptionDescription",
      "",
    );
    const securityExceptionSeverity = this.getParameter<number>(
      "securityExceptionSeverity",
      -1,
    );
    const securityExceptionStatus = this.getParameter<string>(
      "securityExceptionStatus",
      "open",
    );
    const securityExceptionExpirationDate = this.getParameter<string>(
      "securityExceptionExpirationDate",
      "",
    );

    const body = this.buildBody(
      {
        name: securityExceptionName,
        folder: folderId,
        status: securityExceptionStatus,
      },
      {
        description: securityExceptionDescription,
        severity: securityExceptionSeverity,
        expiration_date: securityExceptionExpirationDate,
      },
    );

    return this.createResource(body);
  }

  private async getByNameOp(): Promise<IDataObject> {
    const securityExceptionName = this.getParameter<string>(
      "securityExceptionName",
    );
    const folderId = this.getParameter<string>("folderId");

    return this.getByName(securityExceptionName, { folder: folderId });
  }

  private async list(): Promise<IDataObject> {
    const folderIdFilter = this.getParameter<string>("folderIdFilter", "");
    return this.listResources(folderIdFilter);
  }

  private async update(): Promise<IDataObject> {
    const securityExceptionId = this.getParameter<string>(
      "securityExceptionId",
    );
    const securityExceptionStatusUpdate = this.getParameter<string>(
      "securityExceptionStatusUpdate",
      "",
    );

    const body = this.buildBody({}, { status: securityExceptionStatusUpdate });

    return this.updateResource(securityExceptionId, body);
  }
}
