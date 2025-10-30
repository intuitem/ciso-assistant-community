import type { IDataObject } from "n8n-workflow";
import type { IResourceContext } from "../types";
import { BaseResourceHandler } from "./BaseResourceHandler";
import { buildUrl } from "../utils/http";

/**
 * Handler for audit (compliance assessment) operations
 * Note: Audits are implemented as compliance-assessments in the backend
 */
export class AuditHandler extends BaseResourceHandler {
  protected getEndpoint(): string {
    return "compliance-assessments";
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
        case "getRequirementAssessment":
          return await this.getRequirementAssessment();
        case "updateRequirementAssessment":
          return await this.updateRequirementAssessment();
        case "listRequirementAssessments":
          return await this.listRequirementAssessments();
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
    const frameworkId = this.getParameter<string>("frameworkId");
    const auditName = this.getParameter<string>("auditName");

    const body = {
      name: auditName,
      perimeter: perimeterId,
      framework: frameworkId,
    };

    return this.createResource(body);
  }

  private async getByNameOp(): Promise<IDataObject> {
    const auditName = this.getParameter<string>("auditName");
    const folderIdFilter = this.getParameter<string>("folderIdFilter", "");
    const perimeterIdFilter = this.getParameter<string>(
      "perimeterIdFilter",
      "",
    );

    const additionalParams: Record<string, string> = {};
    if (folderIdFilter) additionalParams.folder = folderIdFilter;
    if (perimeterIdFilter) additionalParams.perimeter = perimeterIdFilter;

    return this.getByName(auditName, additionalParams);
  }

  private async getByRefIdOp(): Promise<IDataObject> {
    const auditRefId = this.getParameter<string>("auditRefId");
    const folderIdFilter = this.getParameter<string>("folderIdFilter", "");
    const perimeterIdFilter = this.getParameter<string>(
      "perimeterIdFilter",
      "",
    );

    const additionalParams: Record<string, string> = {};
    if (folderIdFilter) additionalParams.folder = folderIdFilter;
    if (perimeterIdFilter) additionalParams.perimeter = perimeterIdFilter;

    return this.getByRefId(auditRefId, additionalParams);
  }

  private async getRequirementAssessment(): Promise<IDataObject> {
    const requirementRefId = this.getParameter<string>("requirementRefId");
    const complianceAssessmentId = this.getParameter<string>(
      "complianceAssessmentId",
    );

    const url = buildUrl(
      this.context.credentials.baseUrl,
      "/requirement-assessments/",
      {
        requirement__ref_id: requirementRefId,
        compliance_assessment: complianceAssessmentId,
      },
    );

    return this.request(
      "GET",
      url.replace(this.context.credentials.baseUrl, ""),
    );
  }

  private async updateRequirementAssessment(): Promise<IDataObject> {
    const requirementRefId = this.getParameter<string>("requirementRefId");
    const complianceAssessmentId = this.getParameter<string>(
      "complianceAssessmentId",
    );

    // First, get the requirement assessment to find its ID
    const getUrl = buildUrl(
      this.context.credentials.baseUrl,
      "/requirement-assessments/",
      {
        requirement__ref_id: requirementRefId,
        compliance_assessment: complianceAssessmentId,
      },
    );

    const getResponse: any = await this.request(
      "GET",
      getUrl.replace(this.context.credentials.baseUrl, ""),
    );

    if (!getResponse.results || getResponse.results.length === 0) {
      throw new Error(
        `No requirement assessment found for ref_id: ${requirementRefId} in compliance assessment: ${complianceAssessmentId}`,
      );
    }

    const requirementAssessmentId = getResponse.results[0].id;

    // Build update data
    const status = this.getParameter<string>("requirementAssessmentStatus");
    const result = this.getParameter<string>("requirementAssessmentResult");
    const observation = this.getParameter<string>(
      "requirementAssessmentObservation",
    );
    const score = this.getParameter<number | null>(
      "requirementAssessmentScore",
    );

    const updateData = this.buildUpdateBody({
      status,
      result,
      observation,
      score,
    });

    return this.request(
      "PATCH",
      `/requirement-assessments/${requirementAssessmentId}/`,
      updateData,
    );
  }

  private async listRequirementAssessments(): Promise<IDataObject> {
    const complianceAssessmentId = this.getParameter<string>(
      "complianceAssessmentId",
    );

    const url = buildUrl(
      this.context.credentials.baseUrl,
      "/requirement-assessments/",
      {
        compliance_assessment: complianceAssessmentId,
      },
    );

    return this.request(
      "GET",
      url.replace(this.context.credentials.baseUrl, ""),
    );
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
