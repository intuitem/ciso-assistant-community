import type { IDataObject } from "n8n-workflow";
import type { IResourceContext } from "../types";
import { BaseResourceHandler } from "./BaseResourceHandler";

/**
 * Handler for risk assessment operations
 */
export class RiskAssessmentHandler extends BaseResourceHandler {
  protected getEndpoint(): string {
    return "risk-assessments";
  }

  public async execute(
    operation: string,
    context: IResourceContext,
  ): Promise<IDataObject> {
    this.context = context;

    try {
      switch (operation) {
        case "initiate":
          return await this.initiate();
        case "getByName":
          return await this.getByNameOp();
        case "getByRefId":
          return await this.getByRefIdOp();
        case "list":
          return await this.list();
        default:
          throw new Error(`Unknown operation: ${operation}`);
      }
    } catch (error) {
      return this.handleError(error, operation);
    }
  }

  private async initiate(): Promise<IDataObject> {
    const perimeterId = this.getParameter<string>("perimeterId");
    const riskMatrixId = this.getParameter<string>("riskMatrixId");
    const riskAssessmentName = this.getParameter<string>("riskAssessmentName");

    const body = {
      name: riskAssessmentName,
      perimeter: perimeterId,
      risk_matrix: riskMatrixId,
    };

    return this.createResource(body);
  }

  private async getByNameOp(): Promise<IDataObject> {
    const riskAssessmentNameGet = this.getParameter<string>(
      "riskAssessmentNameGet",
    );
    const folderIdFilter = this.getParameter<string>("folderIdFilter", "");
    const perimeterIdFilter = this.getParameter<string>(
      "perimeterIdFilter",
      "",
    );

    const additionalParams: Record<string, string> = {};
    if (folderIdFilter) additionalParams.folder = folderIdFilter;
    if (perimeterIdFilter) additionalParams.perimeter = perimeterIdFilter;

    return this.getByName(riskAssessmentNameGet, additionalParams);
  }

  private async getByRefIdOp(): Promise<IDataObject> {
    const riskAssessmentRefId = this.getParameter<string>(
      "riskAssessmentRefId",
    );
    const folderIdFilter = this.getParameter<string>("folderIdFilter", "");
    const perimeterIdFilter = this.getParameter<string>(
      "perimeterIdFilter",
      "",
    );

    const additionalParams: Record<string, string> = {};
    if (folderIdFilter) additionalParams.folder = folderIdFilter;
    if (perimeterIdFilter) additionalParams.perimeter = perimeterIdFilter;

    return this.getByRefId(riskAssessmentRefId, additionalParams);
  }

  private async list(): Promise<IDataObject> {
    const folderIdFilter = this.getParameter<string>("folderIdFilter", "");
    const perimeterIdFilter = this.getParameter<string>(
      "perimeterIdFilter",
      "",
    );

    return this.listResources(folderIdFilter, perimeterIdFilter);
  }
}
