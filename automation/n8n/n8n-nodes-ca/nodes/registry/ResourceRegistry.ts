import type { IResourceHandler, ResourceType } from "../types";
import {
  SystemHandler,
  DomainHandler,
  PerimeterHandler,
  AssetHandler,
  AuditHandler,
  RiskAssessmentHandler,
  IncidentHandler,
  VulnerabilityHandler,
  AppliedControlHandler,
  TaskOccurrenceHandler,
  TaskDefinitionHandler,
  FindingsAssessmentHandler,
  FindingHandler,
  SecurityExceptionHandler,
  EvidenceHandler,
  EntityHandler,
  SolutionHandler,
  RepresentativeHandler,
  EntityAssessmentHandler,
  RightRequestHandler,
  DataBreachHandler,
  RiskScenarioHandler,
  RiskMatrixHandler,
  FrameworkHandler,
} from "../handlers";

/**
 * Registry mapping resource types to their handler classes
 */
class ResourceRegistry {
  private handlers: Map<ResourceType, new () => IResourceHandler>;

  constructor() {
    this.handlers = new Map();
    this.registerHandlers();
  }

  /**
   * Register all resource handlers
   */
  private registerHandlers(): void {
    this.handlers.set("system", SystemHandler);
    this.handlers.set("domain", DomainHandler);
    this.handlers.set("perimeter", PerimeterHandler);
    this.handlers.set("asset", AssetHandler);
    this.handlers.set("audit", AuditHandler);
    this.handlers.set("riskAssessment", RiskAssessmentHandler);
    this.handlers.set("incident", IncidentHandler);
    this.handlers.set("vulnerability", VulnerabilityHandler);
    this.handlers.set("appliedControl", AppliedControlHandler);
    this.handlers.set("taskOccurrence", TaskOccurrenceHandler);
    this.handlers.set("taskDefinition", TaskDefinitionHandler);
    this.handlers.set("findingsAssessment", FindingsAssessmentHandler);
    this.handlers.set("finding", FindingHandler);
    this.handlers.set("securityException", SecurityExceptionHandler);
    this.handlers.set("evidence", EvidenceHandler);
    this.handlers.set("entity", EntityHandler);
    this.handlers.set("solution", SolutionHandler);
    this.handlers.set("representative", RepresentativeHandler);
    this.handlers.set("entityAssessment", EntityAssessmentHandler);
    this.handlers.set("rightRequest", RightRequestHandler);
    this.handlers.set("dataBreach", DataBreachHandler);
    this.handlers.set("riskScenario", RiskScenarioHandler);
    this.handlers.set("riskMatrix", RiskMatrixHandler);
    this.handlers.set("framework", FrameworkHandler);
  }

  /**
   * Get a handler for the specified resource
   */
  public getHandler(resource: ResourceType): IResourceHandler {
    const HandlerClass = this.handlers.get(resource);

    if (!HandlerClass) {
      throw new Error(`No handler registered for resource: ${resource}`);
    }

    return new HandlerClass();
  }

  /**
   * Check if a handler exists for the resource
   */
  public hasHandler(resource: string): boolean {
    return this.handlers.has(resource as ResourceType);
  }
}

// Export singleton instance
export const resourceRegistry = new ResourceRegistry();
