import * as system from "./system";
import * as domain from "./domain";
import * as perimeter from "./perimeter";
import * as asset from "./asset";
import * as audit from "./audit";
import * as riskAssessment from "./riskAssessment";
import * as incident from "./incident";
import * as vulnerability from "./vulnerability";
import * as appliedControl from "./appliedControl";
import * as taskOccurrence from "./taskOccurrence";
import * as taskDefinition from "./taskDefinition";
import * as findingsAssessment from "./findingsAssessment";
import * as finding from "./finding";
import * as securityException from "./securityException";
import * as evidence from "./evidence";
import * as entity from "./entity";
import * as solution from "./solution";
import * as representative from "./representative";
import * as entityAssessment from "./entityAssessment";
import * as rightRequest from "./rightRequest";
import * as dataBreach from "./dataBreach";
import * as riskScenario from "./riskScenario";
import * as framework from "./framework";
import * as riskMatrix from "./riskMatrix";

export { sharedFields } from "./shared";

// Order sets the operation selectors' order in the node description.
export const resources = [
  system,
  domain,
  perimeter,
  asset,
  audit,
  riskAssessment,
  incident,
  vulnerability,
  appliedControl,
  taskOccurrence,
  taskDefinition,
  findingsAssessment,
  finding,
  securityException,
  evidence,
  entity,
  solution,
  representative,
  entityAssessment,
  rightRequest,
  dataBreach,
  riskScenario,
  framework,
  riskMatrix,
];
