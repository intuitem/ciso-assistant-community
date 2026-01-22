/**
 * Risk Registers API Client
 *
 * Provides TypeScript interfaces and API functions for risk registers operations.
 * Aligned with backend bounded context: backend/core/bounded_contexts/risk_registers/
 */

import { api } from '$lib/api';
import type { ApiResponse, PaginatedResponse } from '$lib/api';

// ============================================================================
// Value Objects
// ============================================================================

export interface RiskScoring {
  likelihood: number; // 1-5
  impact: number; // 1-5
  inherent_score: number;
  residual_score: number;
  rationale?: string;
}

// ============================================================================
// Lifecycle State Types
// ============================================================================

export type RiskLifecycleState = 'draft' | 'assessed' | 'treated' | 'accepted' | 'closed';
export type TreatmentPlanLifecycleState = 'draft' | 'active' | 'completed' | 'abandoned';
export type TreatmentStrategy = 'avoid' | 'mitigate' | 'transfer' | 'accept';
export type RiskExceptionLifecycleState = 'requested' | 'approved' | 'expired' | 'revoked';

// ============================================================================
// Risk Aggregate Interfaces
// ============================================================================

export interface AssetRisk {
  id: string;
  version: number;
  created_at: string;
  updated_at: string;
  title: string;
  description?: string;
  threat?: string;
  vulnerability?: string;
  lifecycle_state: RiskLifecycleState;
  assetIds: string[];
  controlImplementationIds: string[];
  exceptionIds: string[];
  relatedRiskIds: string[];
  scoring: RiskScoring;
  treatmentPlanId?: string;
  tags: string[];
}

export interface ThirdPartyRisk {
  id: string;
  version: number;
  created_at: string;
  updated_at: string;
  title: string;
  description?: string;
  lifecycle_state: RiskLifecycleState;
  thirdPartyIds: string[];
  serviceIds: string[];
  controlImplementationIds: string[];
  assessmentRunIds: string[];
  exceptionIds: string[];
  scoring: RiskScoring;
  treatmentPlanId?: string;
  tags: string[];
}

export interface BusinessRisk {
  id: string;
  version: number;
  created_at: string;
  updated_at: string;
  title: string;
  description?: string;
  lifecycle_state: RiskLifecycleState;
  processIds: string[];
  orgUnitIds: string[];
  controlImplementationIds: string[];
  exceptionIds: string[];
  scoring: RiskScoring;
  treatmentPlanId?: string;
  tags: string[];
}

// ============================================================================
// Supporting Entity Interfaces
// ============================================================================

export interface TreatmentTask {
  id: string;
  title: string;
  ownerUserId: string;
  dueDate?: string;
  status: 'Open' | 'InProgress' | 'Done' | 'Blocked';
  evidenceIds: string[];
}

export interface RiskTreatmentPlan {
  id: string;
  version: number;
  created_at: string;
  updated_at: string;
  riskId: string;
  name: string;
  description?: string;
  strategy: TreatmentStrategy;
  lifecycle_state: TreatmentPlanLifecycleState;
  tasks: TreatmentTask[];
  started_at?: string;
  completed_at?: string;
  tags: string[];
}

export interface RiskException {
  id: string;
  version: number;
  created_at: string;
  updated_at: string;
  riskId: string;
  reason: string;
  description?: string;
  lifecycle_state: RiskExceptionLifecycleState;
  approved_by_user_id?: string;
  approved_at?: string;
  expires_at?: string;
  tags: string[];
}

// ============================================================================
// API Response Types
// ============================================================================

export type AssetRiskResponse = ApiResponse<AssetRisk>;
export type AssetRiskListResponse = PaginatedResponse<AssetRisk>;
export type ThirdPartyRiskResponse = ApiResponse<ThirdPartyRisk>;
export type ThirdPartyRiskListResponse = PaginatedResponse<ThirdPartyRisk>;
export type BusinessRiskResponse = ApiResponse<BusinessRisk>;
export type BusinessRiskListResponse = PaginatedResponse<BusinessRisk>;
export type RiskTreatmentPlanResponse = ApiResponse<RiskTreatmentPlan>;
export type RiskTreatmentPlanListResponse = PaginatedResponse<RiskTreatmentPlan>;
export type RiskExceptionResponse = ApiResponse<RiskException>;
export type RiskExceptionListResponse = PaginatedResponse<RiskException>;

// ============================================================================
// Asset Risk API
// ============================================================================

export const assetRiskApi = {
  async list(params?: Record<string, any>): Promise<AssetRiskListResponse> {
    return api.get('/risks/asset-risks/', { params });
  },

  async create(data: Partial<AssetRisk>): Promise<AssetRiskResponse> {
    return api.post('/risks/asset-risks/', data);
  },

  async retrieve(id: string): Promise<AssetRiskResponse> {
    return api.get(`/risks/asset-risks/${id}/`);
  },

  async update(id: string, data: Partial<AssetRisk>): Promise<AssetRiskResponse> {
    return api.put(`/risks/asset-risks/${id}/`, data);
  },

  async destroy(id: string): Promise<ApiResponse<null>> {
    return api.delete(`/risks/asset-risks/${id}/`);
  },

  async assess(
    id: string,
    scoring: { likelihood: number; impact: number; inherent_score: number; residual_score: number; rationale?: string }
  ): Promise<AssetRiskResponse> {
    return api.post(`/risks/asset-risks/${id}/assess/`, scoring);
  },

  async treat(id: string, treatmentPlanId?: string): Promise<AssetRiskResponse> {
    return api.post(`/risks/asset-risks/${id}/treat/`, { treatment_plan_id: treatmentPlanId });
  },

  async accept(id: string): Promise<AssetRiskResponse> {
    return api.post(`/risks/asset-risks/${id}/accept/`);
  },

  async close(id: string): Promise<AssetRiskResponse> {
    return api.post(`/risks/asset-risks/${id}/close/`);
  },

  async addAsset(id: string, assetId: string): Promise<AssetRiskResponse> {
    return api.post(`/risks/asset-risks/${id}/add_asset/`, { asset_id: assetId });
  },

  async addControlImplementation(id: string, implementationId: string): Promise<AssetRiskResponse> {
    return api.post(`/risks/asset-risks/${id}/add_control_implementation/`, {
      implementation_id: implementationId
    });
  },

  async addException(id: string, exceptionId: string): Promise<AssetRiskResponse> {
    return api.post(`/risks/asset-risks/${id}/add_exception/`, { exception_id: exceptionId });
  },

  async addRelatedRisk(id: string, relatedRiskId: string): Promise<AssetRiskResponse> {
    return api.post(`/risks/asset-risks/${id}/add_related_risk/`, { related_risk_id: relatedRiskId });
  }
};

// ============================================================================
// Third Party Risk API
// ============================================================================

export const thirdPartyRiskApi = {
  async list(params?: Record<string, any>): Promise<ThirdPartyRiskListResponse> {
    return api.get('/risks/third-party-risks/', { params });
  },

  async create(data: Partial<ThirdPartyRisk>): Promise<ThirdPartyRiskResponse> {
    return api.post('/risks/third-party-risks/', data);
  },

  async retrieve(id: string): Promise<ThirdPartyRiskResponse> {
    return api.get(`/risks/third-party-risks/${id}/`);
  },

  async update(id: string, data: Partial<ThirdPartyRisk>): Promise<ThirdPartyRiskResponse> {
    return api.put(`/risks/third-party-risks/${id}/`, data);
  },

  async destroy(id: string): Promise<ApiResponse<null>> {
    return api.delete(`/risks/third-party-risks/${id}/`);
  },

  async assess(
    id: string,
    scoring: { likelihood: number; impact: number; inherent_score: number; residual_score: number; rationale?: string }
  ): Promise<ThirdPartyRiskResponse> {
    return api.post(`/risks/third-party-risks/${id}/assess/`, scoring);
  },

  async treat(id: string, treatmentPlanId?: string): Promise<ThirdPartyRiskResponse> {
    return api.post(`/risks/third-party-risks/${id}/treat/`, { treatment_plan_id: treatmentPlanId });
  },

  async accept(id: string): Promise<ThirdPartyRiskResponse> {
    return api.post(`/risks/third-party-risks/${id}/accept/`);
  },

  async close(id: string): Promise<ThirdPartyRiskResponse> {
    return api.post(`/risks/third-party-risks/${id}/close/`);
  },

  async addThirdParty(id: string, thirdPartyId: string): Promise<ThirdPartyRiskResponse> {
    return api.post(`/risks/third-party-risks/${id}/add_third_party/`, { third_party_id: thirdPartyId });
  },

  async addService(id: string, serviceId: string): Promise<ThirdPartyRiskResponse> {
    return api.post(`/risks/third-party-risks/${id}/add_service/`, { service_id: serviceId });
  },

  async addControlImplementation(id: string, implementationId: string): Promise<ThirdPartyRiskResponse> {
    return api.post(`/risks/third-party-risks/${id}/add_control_implementation/`, {
      implementation_id: implementationId
    });
  },

  async addAssessmentRun(id: string, assessmentRunId: string): Promise<ThirdPartyRiskResponse> {
    return api.post(`/risks/third-party-risks/${id}/add_assessment_run/`, {
      assessment_run_id: assessmentRunId
    });
  },

  async addException(id: string, exceptionId: string): Promise<ThirdPartyRiskResponse> {
    return api.post(`/risks/third-party-risks/${id}/add_exception/`, { exception_id: exceptionId });
  }
};

// ============================================================================
// Business Risk API
// ============================================================================

export const businessRiskApi = {
  async list(params?: Record<string, any>): Promise<BusinessRiskListResponse> {
    return api.get('/risks/business-risks/', { params });
  },

  async create(data: Partial<BusinessRisk>): Promise<BusinessRiskResponse> {
    return api.post('/risks/business-risks/', data);
  },

  async retrieve(id: string): Promise<BusinessRiskResponse> {
    return api.get(`/risks/business-risks/${id}/`);
  },

  async update(id: string, data: Partial<BusinessRisk>): Promise<BusinessRiskResponse> {
    return api.put(`/risks/business-risks/${id}/`, data);
  },

  async destroy(id: string): Promise<ApiResponse<null>> {
    return api.delete(`/risks/business-risks/${id}/`);
  },

  async assess(
    id: string,
    scoring: { likelihood: number; impact: number; inherent_score: number; residual_score: number; rationale?: string }
  ): Promise<BusinessRiskResponse> {
    return api.post(`/risks/business-risks/${id}/assess/`, scoring);
  },

  async treat(id: string, treatmentPlanId?: string): Promise<BusinessRiskResponse> {
    return api.post(`/risks/business-risks/${id}/treat/`, { treatment_plan_id: treatmentPlanId });
  },

  async accept(id: string): Promise<BusinessRiskResponse> {
    return api.post(`/risks/business-risks/${id}/accept/`);
  },

  async close(id: string): Promise<BusinessRiskResponse> {
    return api.post(`/risks/business-risks/${id}/close/`);
  },

  async addProcess(id: string, processId: string): Promise<BusinessRiskResponse> {
    return api.post(`/risks/business-risks/${id}/add_process/`, { process_id: processId });
  },

  async addOrgUnit(id: string, orgUnitId: string): Promise<BusinessRiskResponse> {
    return api.post(`/risks/business-risks/${id}/add_org_unit/`, { org_unit_id: orgUnitId });
  },

  async addControlImplementation(id: string, implementationId: string): Promise<BusinessRiskResponse> {
    return api.post(`/risks/business-risks/${id}/add_control_implementation/`, {
      implementation_id: implementationId
    });
  },

  async addException(id: string, exceptionId: string): Promise<BusinessRiskResponse> {
    return api.post(`/risks/business-risks/${id}/add_exception/`, { exception_id: exceptionId });
  }
};

// ============================================================================
// Risk Treatment Plan API
// ============================================================================

export const riskTreatmentPlanApi = {
  async list(params?: Record<string, any>): Promise<RiskTreatmentPlanListResponse> {
    return api.get('/risks/risk-treatment-plans/', { params });
  },

  async create(data: Partial<RiskTreatmentPlan>): Promise<RiskTreatmentPlanResponse> {
    return api.post('/risks/risk-treatment-plans/', data);
  },

  async retrieve(id: string): Promise<RiskTreatmentPlanResponse> {
    return api.get(`/risks/risk-treatment-plans/${id}/`);
  },

  async update(id: string, data: Partial<RiskTreatmentPlan>): Promise<RiskTreatmentPlanResponse> {
    return api.put(`/risks/risk-treatment-plans/${id}/`, data);
  },

  async destroy(id: string): Promise<ApiResponse<null>> {
    return api.delete(`/risks/risk-treatment-plans/${id}/`);
  },

  async activate(id: string): Promise<RiskTreatmentPlanResponse> {
    return api.post(`/risks/risk-treatment-plans/${id}/activate/`);
  },

  async complete(id: string): Promise<RiskTreatmentPlanResponse> {
    return api.post(`/risks/risk-treatment-plans/${id}/complete/`);
  },

  async abandon(id: string): Promise<RiskTreatmentPlanResponse> {
    return api.post(`/risks/risk-treatment-plans/${id}/abandon/`);
  },

  async addTask(
    id: string,
    task: { title: string; ownerUserId: string; dueDate?: string; status?: string; evidenceIds?: string[] }
  ): Promise<RiskTreatmentPlanResponse> {
    return api.post(`/risks/risk-treatment-plans/${id}/add_task/`, task);
  },

  async updateTaskStatus(id: string, taskId: string, status: string): Promise<RiskTreatmentPlanResponse> {
    return api.post(`/risks/risk-treatment-plans/${id}/update_task_status/`, { task_id: taskId, status });
  }
};

// ============================================================================
// Risk Exception API
// ============================================================================

export const riskExceptionApi = {
  async list(params?: Record<string, any>): Promise<RiskExceptionListResponse> {
    return api.get('/risks/risk-exceptions/', { params });
  },

  async create(data: Partial<RiskException>): Promise<RiskExceptionResponse> {
    return api.post('/risks/risk-exceptions/', data);
  },

  async retrieve(id: string): Promise<RiskExceptionResponse> {
    return api.get(`/risks/risk-exceptions/${id}/`);
  },

  async update(id: string, data: Partial<RiskException>): Promise<RiskExceptionResponse> {
    return api.put(`/risks/risk-exceptions/${id}/`, data);
  },

  async destroy(id: string): Promise<ApiResponse<null>> {
    return api.delete(`/risks/risk-exceptions/${id}/`);
  },

  async approve(id: string, approvedByUserId: string): Promise<RiskExceptionResponse> {
    return api.post(`/risks/risk-exceptions/${id}/approve/`, { approved_by_user_id: approvedByUserId });
  },

  async expire(id: string): Promise<RiskExceptionResponse> {
    return api.post(`/risks/risk-exceptions/${id}/expire/`);
  },

  async revoke(id: string): Promise<RiskExceptionResponse> {
    return api.post(`/risks/risk-exceptions/${id}/revoke/`);
  }
};

// ============================================================================
// Unified Risk API (convenience wrapper)
// ============================================================================

export const riskApi = {
  assetRisks: assetRiskApi,
  thirdPartyRisks: thirdPartyRiskApi,
  businessRisks: businessRiskApi,
  treatmentPlans: riskTreatmentPlanApi,
  exceptions: riskExceptionApi
};
