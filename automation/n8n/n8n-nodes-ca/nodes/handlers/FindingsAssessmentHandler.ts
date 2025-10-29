import type { IDataObject } from "n8n-workflow";
import type { IResourceContext } from "../types";
import { BaseResourceHandler } from "./BaseResourceHandler";

/**
 * Handler for findings assessment operations
 */
export class FindingsAssessmentHandler extends BaseResourceHandler {
  protected getEndpoint(): string {
    return "findings-assessments";
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
        case "getByRefId":
          return await this.getByRefIdOp();
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
    const findingsAssessmentName = this.getParameter<string>(
      "findingsAssessmentName",
    );
    const folderId = this.getParameter<string>("folderId");
    const perimeterId = this.getParameter<string>("perimeterId");
    const findingsAssessmentDescription = this.getParameter<string>(
      "findingsAssessmentDescription",
      "",
    );
    const findingsAssessmentCategory = this.getParameter<string>(
      "findingsAssessmentCategory",
      "findings",
    );

    const body = this.buildBody(
      {
        name: findingsAssessmentName,
        folder: folderId,
        perimeter: perimeterId,
        category: findingsAssessmentCategory,
      },
      {
        description: findingsAssessmentDescription,
      },
    );

    return this.createResource(body);
  }

  private async getByNameOp(): Promise<IDataObject> {
    const findingsAssessmentName = this.getParameter<string>(
      "findingsAssessmentName",
    );
    const folderIdFilter = this.getParameter<string>("folderIdFilter", "");
    const perimeterIdFilter = this.getParameter<string>(
      "perimeterIdFilter",
      "",
    );

    const additionalParams: Record<string, string> = {};
    if (folderIdFilter) additionalParams.folder = folderIdFilter;
    if (perimeterIdFilter) additionalParams.perimeter = perimeterIdFilter;

    return this.getByName(findingsAssessmentName, additionalParams);
  }

  private async getByRefIdOp(): Promise<IDataObject> {
    const findingsAssessmentRefId = this.getParameter<string>(
      "findingsAssessmentRefId",
    );
    const folderIdFilter = this.getParameter<string>("folderIdFilter", "");
    const perimeterIdFilter = this.getParameter<string>(
      "perimeterIdFilter",
      "",
    );

    const additionalParams: Record<string, string> = {};
    if (folderIdFilter) additionalParams.folder = folderIdFilter;
    if (perimeterIdFilter) additionalParams.perimeter = perimeterIdFilter;

    return this.getByRefId(findingsAssessmentRefId, additionalParams);
  }

  private async list(): Promise<IDataObject> {
    const folderIdFilter = this.getParameter<string>("folderIdFilter", "");
    const perimeterIdFilter = this.getParameter<string>(
      "perimeterIdFilter",
      "",
    );

    return this.listResources(folderIdFilter, perimeterIdFilter);
  }

  private async update(): Promise<IDataObject> {
    const findingsAssessmentId = this.getParameter<string>(
      "findingsAssessmentId",
    );
    const findingsAssessmentStatus = this.getParameter<string>(
      "findingsAssessmentStatus",
      "",
    );

    const body = this.buildBody({}, { status: findingsAssessmentStatus });

    return this.updateResource(findingsAssessmentId, body);
  }
}
