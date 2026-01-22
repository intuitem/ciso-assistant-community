/**
 * Compliance API Client
 *
 * Provides TypeScript interfaces and API functions for compliance operations.
 * Aligned with backend bounded context: backend/core/bounded_contexts/compliance/
 */

import { api } from '$lib/api';
import type { ApiResponse, PaginatedResponse } from '$lib/api';

// ============================================================================
// Lifecycle State Types
// ============================================================================

export type FrameworkLifecycleState = 'draft' | 'active' | 'retired';
export type RequirementLifecycleState = 'active' | 'retired';
export type AssessmentLifecycleState = 'draft' | 'published' | 'retired';
export type AssessmentRunLifecycleState = 'invited' | 'in_progress' | 'submitted' | 'reviewed' | 'closed';
export type AuditLifecycleState = 'planned' | 'running' | 'reported' | 'closed';
export type FindingLifecycleState = 'open' | 'triaged' | 'remediating' | 'verified' | 'closed';
export type ExceptionLifecycleState = 'requested' | 'approved' | 'expired' | 'revoked';

export type TargetType = 'third_party' | 'org_unit' | 'service' | 'asset' | 'process';
export type FindingSourceType = 'audit' | 'assessment' | 'internal_review';
export type FindingSeverity = 'low' | 'medium' | 'high' | 'critical';

// ============================================================================
// Value Objects
// ============================================================================

export interface Answer {
  questionId: string;
  value: any;
  notes?: string;
}

// ============================================================================
// Aggregate Interfaces
// ============================================================================

export interface ComplianceFramework {
  id: string;
  version: number;
  created_at: string;
  updated_at: string;
  name: string;
  framework_version?: string;
  description?: string;
  lifecycle_state: FrameworkLifecycleState;
  requirementIds: string[];
  tags: string[];
}

export interface Requirement {
  id: string;
  version: number;
  created_at: string;
  updated_at: string;
  frameworkId: string;
  code: string;
  statement: string;
  description?: string;
  lifecycle_state: RequirementLifecycleState;
  mappedControlIds: string[];
  tags: string[];
}

export interface OnlineAssessment {
  id: string;
  version: number;
  created_at: string;
  updated_at: string;
  name: string;
  description?: string;
  questionnaireId: string;
  target_type: TargetType;
  scoring_model?: string;
  lifecycle_state: AssessmentLifecycleState;
  tags: string[];
}

// ============================================================================
// Association Interfaces
// ============================================================================

export interface AssessmentRun {
  id: string;
  version: number;
  created_at: string;
  updated_at: string;
  assessmentId: string;
  target_type: TargetType;
  target_id: string;
  lifecycle_state: AssessmentRunLifecycleState;
  invitedUserIds: string[];
  respondentUserIds: string[];
  findingIds: string[];
  evidenceIds: string[];
  started_at?: string;
  submitted_at?: string;
  score?: number;
  answers: Answer[];
  notes?: string;
}

export interface ComplianceAudit {
  id: string;
  version: number;
  created_at: string;
  updated_at: string;
  name: string;
  description?: string;
  lifecycle_state: AuditLifecycleState;
  scopeFrameworkIds: string[];
  scopeRequirementIds: string[];
  auditor_org?: string;
  start_date: string;
  end_date?: string;
  findingIds: string[];
  tags: string[];
}

export interface ComplianceFinding {
  id: string;
  version: number;
  created_at: string;
  updated_at: string;
  title: string;
  description?: string;
  source_type: FindingSourceType;
  source_id: string;
  lifecycle_state: FindingLifecycleState;
  severity: FindingSeverity;
  requirementIds: string[];
  controlImplementationIds: string[];
  remediationTaskIds: string[];
  evidenceIds: string[];
  tags: string[];
}

export interface ComplianceException {
  id: string;
  version: number;
  created_at: string;
  updated_at: string;
  requirementId: string;
  reason: string;
  description?: string;
  lifecycle_state: ExceptionLifecycleState;
  approved_by_user_id?: string;
  expires_at?: string;
  tags: string[];
}

// ============================================================================
// API Response Types
// ============================================================================

export type ComplianceFrameworkResponse = ApiResponse<ComplianceFramework>;
export type ComplianceFrameworkListResponse = PaginatedResponse<ComplianceFramework>;
export type RequirementResponse = ApiResponse<Requirement>;
export type RequirementListResponse = PaginatedResponse<Requirement>;
export type OnlineAssessmentResponse = ApiResponse<OnlineAssessment>;
export type OnlineAssessmentListResponse = PaginatedResponse<OnlineAssessment>;
export type AssessmentRunResponse = ApiResponse<AssessmentRun>;
export type AssessmentRunListResponse = PaginatedResponse<AssessmentRun>;
export type ComplianceAuditResponse = ApiResponse<ComplianceAudit>;
export type ComplianceAuditListResponse = PaginatedResponse<ComplianceAudit>;
export type ComplianceFindingResponse = ApiResponse<ComplianceFinding>;
export type ComplianceFindingListResponse = PaginatedResponse<ComplianceFinding>;
export type ComplianceExceptionResponse = ApiResponse<ComplianceException>;
export type ComplianceExceptionListResponse = PaginatedResponse<ComplianceException>;

// ============================================================================
// Compliance Framework API
// ============================================================================

export const complianceFrameworkApi = {
  async list(params?: Record<string, any>): Promise<ComplianceFrameworkListResponse> {
    return api.get('/compliance/frameworks/', { params });
  },

  async create(data: Partial<ComplianceFramework>): Promise<ComplianceFrameworkResponse> {
    return api.post('/compliance/frameworks/', data);
  },

  async retrieve(id: string): Promise<ComplianceFrameworkResponse> {
    return api.get(`/compliance/frameworks/${id}/`);
  },

  async update(id: string, data: Partial<ComplianceFramework>): Promise<ComplianceFrameworkResponse> {
    return api.put(`/compliance/frameworks/${id}/`, data);
  },

  async destroy(id: string): Promise<ApiResponse<null>> {
    return api.delete(`/compliance/frameworks/${id}/`);
  },

  async activate(id: string): Promise<ComplianceFrameworkResponse> {
    return api.post(`/compliance/frameworks/${id}/activate/`);
  },

  async retire(id: string): Promise<ComplianceFrameworkResponse> {
    return api.post(`/compliance/frameworks/${id}/retire/`);
  },

  async addRequirement(id: string, requirementId: string): Promise<ComplianceFrameworkResponse> {
    return api.post(`/compliance/frameworks/${id}/add_requirement/`, { requirement_id: requirementId });
  }
};

// ============================================================================
// Requirement API
// ============================================================================

export const requirementApi = {
  async list(params?: Record<string, any>): Promise<RequirementListResponse> {
    return api.get('/compliance/requirements/', { params });
  },

  async create(data: Partial<Requirement>): Promise<RequirementResponse> {
    return api.post('/compliance/requirements/', data);
  },

  async retrieve(id: string): Promise<RequirementResponse> {
    return api.get(`/compliance/requirements/${id}/`);
  },

  async update(id: string, data: Partial<Requirement>): Promise<RequirementResponse> {
    return api.put(`/compliance/requirements/${id}/`, data);
  },

  async destroy(id: string): Promise<ApiResponse<null>> {
    return api.delete(`/compliance/requirements/${id}/`);
  },

  async mapToControl(id: string, controlId: string): Promise<RequirementResponse> {
    return api.post(`/compliance/requirements/${id}/map_to_control/`, { control_id: controlId });
  },

  async retire(id: string): Promise<RequirementResponse> {
    return api.post(`/compliance/requirements/${id}/retire/`);
  }
};

// ============================================================================
// Online Assessment API
// ============================================================================

export const onlineAssessmentApi = {
  async list(params?: Record<string, any>): Promise<OnlineAssessmentListResponse> {
    return api.get('/compliance/online-assessments/', { params });
  },

  async create(data: Partial<OnlineAssessment>): Promise<OnlineAssessmentResponse> {
    return api.post('/compliance/online-assessments/', data);
  },

  async retrieve(id: string): Promise<OnlineAssessmentResponse> {
    return api.get(`/compliance/online-assessments/${id}/`);
  },

  async update(id: string, data: Partial<OnlineAssessment>): Promise<OnlineAssessmentResponse> {
    return api.put(`/compliance/online-assessments/${id}/`, data);
  },

  async destroy(id: string): Promise<ApiResponse<null>> {
    return api.delete(`/compliance/online-assessments/${id}/`);
  },

  async publish(id: string): Promise<OnlineAssessmentResponse> {
    return api.post(`/compliance/online-assessments/${id}/publish/`);
  },

  async retire(id: string): Promise<OnlineAssessmentResponse> {
    return api.post(`/compliance/online-assessments/${id}/retire/`);
  }
};

// ============================================================================
// Assessment Run API
// ============================================================================

export const assessmentRunApi = {
  async list(params?: Record<string, any>): Promise<AssessmentRunListResponse> {
    return api.get('/compliance/assessment-runs/', { params });
  },

  async create(data: Partial<AssessmentRun>): Promise<AssessmentRunResponse> {
    return api.post('/compliance/assessment-runs/', data);
  },

  async retrieve(id: string): Promise<AssessmentRunResponse> {
    return api.get(`/compliance/assessment-runs/${id}/`);
  },

  async update(id: string, data: Partial<AssessmentRun>): Promise<AssessmentRunResponse> {
    return api.put(`/compliance/assessment-runs/${id}/`, data);
  },

  async destroy(id: string): Promise<ApiResponse<null>> {
    return api.delete(`/compliance/assessment-runs/${id}/`);
  },

  async start(id: string, respondentUserId: string): Promise<AssessmentRunResponse> {
    return api.post(`/compliance/assessment-runs/${id}/start/`, { respondent_user_id: respondentUserId });
  },

  async submit(
    id: string,
    data: { answers?: Answer[]; score?: number }
  ): Promise<AssessmentRunResponse> {
    return api.post(`/compliance/assessment-runs/${id}/submit/`, data);
  },

  async review(id: string): Promise<AssessmentRunResponse> {
    return api.post(`/compliance/assessment-runs/${id}/review/`);
  },

  async close(id: string): Promise<AssessmentRunResponse> {
    return api.post(`/compliance/assessment-runs/${id}/close/`);
  },

  async addAnswer(
    id: string,
    answer: { questionId: string; value: any; notes?: string }
  ): Promise<AssessmentRunResponse> {
    return api.post(`/compliance/assessment-runs/${id}/add_answer/`, answer);
  },

  async addFinding(id: string, findingId: string): Promise<AssessmentRunResponse> {
    return api.post(`/compliance/assessment-runs/${id}/add_finding/`, { finding_id: findingId });
  },

  async addEvidence(id: string, evidenceId: string): Promise<AssessmentRunResponse> {
    return api.post(`/compliance/assessment-runs/${id}/add_evidence/`, { evidence_id: evidenceId });
  }
};

// ============================================================================
// Compliance Audit API
// ============================================================================

export const complianceAuditApi = {
  async list(params?: Record<string, any>): Promise<ComplianceAuditListResponse> {
    return api.get('/compliance/compliance-audits/', { params });
  },

  async create(data: Partial<ComplianceAudit>): Promise<ComplianceAuditResponse> {
    return api.post('/compliance/compliance-audits/', data);
  },

  async retrieve(id: string): Promise<ComplianceAuditResponse> {
    return api.get(`/compliance/compliance-audits/${id}/`);
  },

  async update(id: string, data: Partial<ComplianceAudit>): Promise<ComplianceAuditResponse> {
    return api.put(`/compliance/compliance-audits/${id}/`, data);
  },

  async destroy(id: string): Promise<ApiResponse<null>> {
    return api.delete(`/compliance/compliance-audits/${id}/`);
  },

  async start(id: string): Promise<ComplianceAuditResponse> {
    return api.post(`/compliance/compliance-audits/${id}/start/`);
  },

  async complete(id: string, endDate?: string): Promise<ComplianceAuditResponse> {
    return api.post(`/compliance/compliance-audits/${id}/complete/`, { end_date: endDate });
  },

  async close(id: string): Promise<ComplianceAuditResponse> {
    return api.post(`/compliance/compliance-audits/${id}/close/`);
  },

  async addFinding(id: string, findingId: string): Promise<ComplianceAuditResponse> {
    return api.post(`/compliance/compliance-audits/${id}/add_finding/`, { finding_id: findingId });
  },

  async addScopeFramework(id: string, frameworkId: string): Promise<ComplianceAuditResponse> {
    return api.post(`/compliance/compliance-audits/${id}/add_scope_framework/`, {
      framework_id: frameworkId
    });
  },

  async addScopeRequirement(id: string, requirementId: string): Promise<ComplianceAuditResponse> {
    return api.post(`/compliance/compliance-audits/${id}/add_scope_requirement/`, {
      requirement_id: requirementId
    });
  }
};

// ============================================================================
// Compliance Finding API
// ============================================================================

export const complianceFindingApi = {
  async list(params?: Record<string, any>): Promise<ComplianceFindingListResponse> {
    return api.get('/compliance/compliance-findings/', { params });
  },

  async create(data: Partial<ComplianceFinding>): Promise<ComplianceFindingResponse> {
    return api.post('/compliance/compliance-findings/', data);
  },

  async retrieve(id: string): Promise<ComplianceFindingResponse> {
    return api.get(`/compliance/compliance-findings/${id}/`);
  },

  async update(id: string, data: Partial<ComplianceFinding>): Promise<ComplianceFindingResponse> {
    return api.put(`/compliance/compliance-findings/${id}/`, data);
  },

  async destroy(id: string): Promise<ApiResponse<null>> {
    return api.delete(`/compliance/compliance-findings/${id}/`);
  },

  async triage(id: string): Promise<ComplianceFindingResponse> {
    return api.post(`/compliance/compliance-findings/${id}/triage/`);
  },

  async startRemediation(id: string): Promise<ComplianceFindingResponse> {
    return api.post(`/compliance/compliance-findings/${id}/start_remediation/`);
  },

  async verify(id: string): Promise<ComplianceFindingResponse> {
    return api.post(`/compliance/compliance-findings/${id}/verify/`);
  },

  async close(id: string): Promise<ComplianceFindingResponse> {
    return api.post(`/compliance/compliance-findings/${id}/close/`);
  },

  async addRequirement(id: string, requirementId: string): Promise<ComplianceFindingResponse> {
    return api.post(`/compliance/compliance-findings/${id}/add_requirement/`, {
      requirement_id: requirementId
    });
  },

  async addControlImplementation(id: string, implementationId: string): Promise<ComplianceFindingResponse> {
    return api.post(`/compliance/compliance-findings/${id}/add_control_implementation/`, {
      implementation_id: implementationId
    });
  },

  async addRemediationTask(id: string, taskId: string): Promise<ComplianceFindingResponse> {
    return api.post(`/compliance/compliance-findings/${id}/add_remediation_task/`, {
      task_id: taskId
    });
  },

  async addEvidence(id: string, evidenceId: string): Promise<ComplianceFindingResponse> {
    return api.post(`/compliance/compliance-findings/${id}/add_evidence/`, {
      evidence_id: evidenceId
    });
  }
};

// ============================================================================
// Compliance Exception API
// ============================================================================

export const complianceExceptionApi = {
  async list(params?: Record<string, any>): Promise<ComplianceExceptionListResponse> {
    return api.get('/compliance/compliance-exceptions/', { params });
  },

  async create(data: Partial<ComplianceException>): Promise<ComplianceExceptionResponse> {
    return api.post('/compliance/compliance-exceptions/', data);
  },

  async retrieve(id: string): Promise<ComplianceExceptionResponse> {
    return api.get(`/compliance/compliance-exceptions/${id}/`);
  },

  async update(id: string, data: Partial<ComplianceException>): Promise<ComplianceExceptionResponse> {
    return api.put(`/compliance/compliance-exceptions/${id}/`, data);
  },

  async destroy(id: string): Promise<ApiResponse<null>> {
    return api.delete(`/compliance/compliance-exceptions/${id}/`);
  },

  async approve(id: string, approvedByUserId: string): Promise<ComplianceExceptionResponse> {
    return api.post(`/compliance/compliance-exceptions/${id}/approve/`, {
      approved_by_user_id: approvedByUserId
    });
  },

  async expire(id: string): Promise<ComplianceExceptionResponse> {
    return api.post(`/compliance/compliance-exceptions/${id}/expire/`);
  },

  async revoke(id: string): Promise<ComplianceExceptionResponse> {
    return api.post(`/compliance/compliance-exceptions/${id}/revoke/`);
  }
};

// ============================================================================
// Unified Compliance API (convenience wrapper)
// ============================================================================

export const complianceApi = {
  frameworks: complianceFrameworkApi,
  requirements: requirementApi,
  onlineAssessments: onlineAssessmentApi,
  assessmentRuns: assessmentRunApi,
  audits: complianceAuditApi,
  findings: complianceFindingApi,
  exceptions: complianceExceptionApi
};
