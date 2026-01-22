/**
 * Third-Party Management API Client
 *
 * Provides TypeScript interfaces and API functions for third-party management operations.
 * Aligned with backend bounded context: backend/core/bounded_contexts/third_party_management/
 */

import { api } from '$lib/api';
import type { ApiResponse, PaginatedResponse } from '$lib/api';

// ============================================================================
// Lifecycle State Types
// ============================================================================

export type ThirdPartyLifecycleState = 'prospect' | 'active' | 'offboarding' | 'archived';
export type ThirdPartyCriticality = 'low' | 'medium' | 'high' | 'critical';

// ============================================================================
// Aggregate Interfaces
// ============================================================================

export interface ThirdParty {
  id: string;
  version: number;
  created_at: string;
  updated_at: string;
  name: string;
  description?: string;
  criticality: ThirdPartyCriticality;
  lifecycle_state: ThirdPartyLifecycleState;
  serviceIds: string[];
  contractIds: string[];
  assessmentRunIds: string[];
  riskIds: string[];
  controlImplementationIds: string[];
  tags: string[];
}

// ============================================================================
// API Response Types
// ============================================================================

export type ThirdPartyResponse = ApiResponse<ThirdParty>;
export type ThirdPartyListResponse = PaginatedResponse<ThirdParty>;

// ============================================================================
// Third Party API
// ============================================================================

export const thirdPartyApi = {
  async list(params?: Record<string, any>): Promise<ThirdPartyListResponse> {
    return api.get('/third-party/third-parties/', { params });
  },

  async create(data: Partial<ThirdParty>): Promise<ThirdPartyResponse> {
    return api.post('/third-party/third-parties/', data);
  },

  async retrieve(id: string): Promise<ThirdPartyResponse> {
    return api.get(`/third-party/third-parties/${id}/`);
  },

  async update(id: string, data: Partial<ThirdParty>): Promise<ThirdPartyResponse> {
    return api.put(`/third-party/third-parties/${id}/`, data);
  },

  async destroy(id: string): Promise<ApiResponse<null>> {
    return api.delete(`/third-party/third-parties/${id}/`);
  },

  async activate(id: string): Promise<ThirdPartyResponse> {
    return api.post(`/third-party/third-parties/${id}/activate/`);
  },

  async startOffboarding(id: string): Promise<ThirdPartyResponse> {
    return api.post(`/third-party/third-parties/${id}/start_offboarding/`);
  },

  async archive(id: string): Promise<ThirdPartyResponse> {
    return api.post(`/third-party/third-parties/${id}/archive/`);
  },

  async addService(id: string, serviceId: string): Promise<ThirdPartyResponse> {
    return api.post(`/third-party/third-parties/${id}/add_service/`, { service_id: serviceId });
  },

  async addContract(id: string, contractId: string): Promise<ThirdPartyResponse> {
    return api.post(`/third-party/third-parties/${id}/add_contract/`, { contract_id: contractId });
  },

  async addAssessmentRun(id: string, assessmentRunId: string): Promise<ThirdPartyResponse> {
    return api.post(`/third-party/third-parties/${id}/add_assessment_run/`, {
      assessment_run_id: assessmentRunId
    });
  },

  async addRisk(id: string, riskId: string): Promise<ThirdPartyResponse> {
    return api.post(`/third-party/third-parties/${id}/add_risk/`, { risk_id: riskId });
  },

  async addControlImplementation(id: string, implementationId: string): Promise<ThirdPartyResponse> {
    return api.post(`/third-party/third-parties/${id}/add_control_implementation/`, {
      implementation_id: implementationId
    });
  }
};

// ============================================================================
// Unified Third-Party Management API (convenience wrapper)
// ============================================================================

export const thirdPartyManagementApi = {
  thirdParties: thirdPartyApi
};
