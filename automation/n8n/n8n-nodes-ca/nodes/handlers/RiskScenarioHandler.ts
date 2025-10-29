import type { IDataObject } from "n8n-workflow";
import type { IResourceContext } from "../types";
import { BaseResourceHandler } from "./BaseResourceHandler";

/**
 * Handler for risk scenario operations
 */
export class RiskScenarioHandler extends BaseResourceHandler {
  protected getEndpoint(): string {
    return "risk-scenarios";
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
    const riskScenarioName = this.getParameter<string>("riskScenarioName");
    const riskScenarioRiskAssessmentId = this.getParameter<string>(
      "riskScenarioRiskAssessmentId",
    );
    const riskScenarioDescription = this.getParameter<string>(
      "riskScenarioDescription",
      "",
    );
    const riskScenarioRefId = this.getParameter<string>(
      "riskScenarioRefId",
      "",
    );
    const riskScenarioTreatment = this.getParameter<string>(
      "riskScenarioTreatment",
      "open",
    );
    const riskScenarioExistingControls = this.getParameter<string>(
      "riskScenarioExistingControls",
      "",
    );
    const riskScenarioInherentProba = this.getParameter<number>(
      "riskScenarioInherentProba",
      -1,
    );
    const riskScenarioInherentImpact = this.getParameter<number>(
      "riskScenarioInherentImpact",
      -1,
    );
    const riskScenarioCurrentProba = this.getParameter<number>(
      "riskScenarioCurrentProba",
      -1,
    );
    const riskScenarioCurrentImpact = this.getParameter<number>(
      "riskScenarioCurrentImpact",
      -1,
    );
    const riskScenarioResidualProba = this.getParameter<number>(
      "riskScenarioResidualProba",
      -1,
    );
    const riskScenarioResidualImpact = this.getParameter<number>(
      "riskScenarioResidualImpact",
      -1,
    );
    const riskScenarioStrengthOfKnowledge = this.getParameter<number>(
      "riskScenarioStrengthOfKnowledge",
      -1,
    );

    const body = this.buildBody(
      {
        name: riskScenarioName,
        risk_assessment: riskScenarioRiskAssessmentId,
        treatment: riskScenarioTreatment,
        inherent_proba: riskScenarioInherentProba,
        inherent_impact: riskScenarioInherentImpact,
        current_proba: riskScenarioCurrentProba,
        current_impact: riskScenarioCurrentImpact,
        residual_proba: riskScenarioResidualProba,
        residual_impact: riskScenarioResidualImpact,
        strength_of_knowledge: riskScenarioStrengthOfKnowledge,
      },
      {
        description: riskScenarioDescription,
        ref_id: riskScenarioRefId,
        existing_controls: riskScenarioExistingControls,
      },
    );

    return this.createResource(body);
  }

  private async getByNameOp(): Promise<IDataObject> {
    const riskScenarioName = this.getParameter<string>("riskScenarioName");
    const riskScenarioRiskAssessmentId = this.getParameter<string>(
      "riskScenarioRiskAssessmentId",
    );

    return this.getByName(riskScenarioName, {
      risk_assessment: riskScenarioRiskAssessmentId,
    });
  }

  private async list(): Promise<IDataObject> {
    const folderIdFilter = this.getParameter<string>("folderIdFilter", "");
    return this.listResources(folderIdFilter);
  }

  private async update(): Promise<IDataObject> {
    const riskScenarioId = this.getParameter<string>("riskScenarioId");
    const riskScenarioDescription = this.getParameter<string>(
      "riskScenarioDescription",
      "",
    );
    const riskScenarioRefId = this.getParameter<string>(
      "riskScenarioRefId",
      "",
    );
    const riskScenarioTreatment = this.getParameter<string>(
      "riskScenarioTreatment",
      "",
    );
    const riskScenarioExistingControls = this.getParameter<string>(
      "riskScenarioExistingControls",
      "",
    );
    const riskScenarioInherentProba = this.getParameter<number>(
      "riskScenarioInherentProba",
      -1,
    );
    const riskScenarioInherentImpact = this.getParameter<number>(
      "riskScenarioInherentImpact",
      -1,
    );
    const riskScenarioCurrentProba = this.getParameter<number>(
      "riskScenarioCurrentProba",
      -1,
    );
    const riskScenarioCurrentImpact = this.getParameter<number>(
      "riskScenarioCurrentImpact",
      -1,
    );
    const riskScenarioResidualProba = this.getParameter<number>(
      "riskScenarioResidualProba",
      -1,
    );
    const riskScenarioResidualImpact = this.getParameter<number>(
      "riskScenarioResidualImpact",
      -1,
    );
    const riskScenarioStrengthOfKnowledge = this.getParameter<number>(
      "riskScenarioStrengthOfKnowledge",
      -1,
    );

    const body = this.buildBody(
      {
        inherent_proba: riskScenarioInherentProba,
        inherent_impact: riskScenarioInherentImpact,
        current_proba: riskScenarioCurrentProba,
        current_impact: riskScenarioCurrentImpact,
        residual_proba: riskScenarioResidualProba,
        residual_impact: riskScenarioResidualImpact,
        strength_of_knowledge: riskScenarioStrengthOfKnowledge,
      },
      {
        description: riskScenarioDescription,
        ref_id: riskScenarioRefId,
        treatment: riskScenarioTreatment,
        existing_controls: riskScenarioExistingControls,
      },
    );

    return this.updateResource(riskScenarioId, body);
  }
}
