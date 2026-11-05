import type { IDataObject } from "n8n-workflow";
import type { IResourceContext } from "../types";
import { BaseResourceHandler } from "./BaseResourceHandler";

/**
 * Handler for entity assessment operations (TPRM)
 */
export class EntityAssessmentHandler extends BaseResourceHandler {
  protected getEndpoint(): string {
    return "entity-assessments";
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
    const entityAssessmentName = this.getParameter<string>(
      "entityAssessmentName",
    );
    const entityAssessmentEntityId = this.getParameter<string>(
      "entityAssessmentEntityId",
    );
    const entityAssessmentPerimeterId = this.getParameter<string>(
      "entityAssessmentPerimeterId",
    );
    const entityAssessmentDescription = this.getParameter<string>(
      "entityAssessmentDescription",
      "",
    );
    const entityAssessmentComplianceAssessmentId = this.getParameter<string>(
      "entityAssessmentComplianceAssessmentId",
      "",
    );
    const entityAssessmentConclusion = this.getParameter<string>(
      "entityAssessmentConclusion",
      "",
    );

    const body = this.buildBody(
      {
        name: entityAssessmentName,
        entity: entityAssessmentEntityId,
        perimeter: entityAssessmentPerimeterId,
      },
      {
        description: entityAssessmentDescription,
        compliance_assessment: entityAssessmentComplianceAssessmentId,
        conclusion: entityAssessmentConclusion,
      },
    );

    return this.createResource(body);
  }

  private async list(): Promise<IDataObject> {
    const entityIdFilter = this.getParameter<string>("entityIdFilter", "");
    return this.listResources(
      undefined,
      undefined,
      entityIdFilter ? { entity: entityIdFilter } : {},
    );
  }
}
