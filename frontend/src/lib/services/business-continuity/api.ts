/**
 * Business Continuity API Client
 *
 * Provides TypeScript interfaces and API functions for business continuity operations.
 * Aligned with backend bounded context: backend/core/bounded_contexts/business_continuity/
 */

import { api } from '$lib/api';
import type { ApiResponse, PaginatedResponse } from '$lib/api';

// ============================================================================
// Lifecycle State Types
// ============================================================================

export type BcpLifecycleState = 'draft' | 'active' | 'retired';
export type BcpTaskLifecycleState = 'open' | 'in_progress' | 'done' | 'blocked';
export type BcpAuditLifecycleState = 'planned' | 'in_progress' | 'completed';
export type BcpAuditOutcome = 'pass' | 'partial' | 'fail';

// ============================================================================
// Aggregate Interfaces
// ============================================================================

export interface BusinessContinuityPlan {
  id: string;
  version: number;
  created_at: string;
  updated_at: string;
  name: string;
  description?: string;
  lifecycle_state: BcpLifecycleState;
  orgUnitIds: string[];
  processIds: string[];
  assetIds: string[];
  serviceIds: string[];
  taskIds: string[];
  auditIds: string[];
  tags: string[];
}

// ============================================================================
// Supporting Entity Interfaces
// ============================================================================

export interface BcpTask {
  id: string;
  created_at: string;
  updated_at: string;
  bcpId: string;
  title: string;
  description?: string;
  lifecycle_state: BcpTaskLifecycleState;
  owner_user_id?: string;
  due_date?: string;
  evidenceIds: string[];
  tags: string[];
}

export interface BcpAudit {
  id: string;
  created_at: string;
  updated_at: string;
  bcpId: string;
  name: string;
  description?: string;
  lifecycle_state: BcpAuditLifecycleState;
  performed_at?: string;
  outcome?: BcpAuditOutcome;
  notes?: string;
  evidenceIds: string[];
  tags: string[];
}

// ============================================================================
// API Response Types
// ============================================================================

export type BusinessContinuityPlanResponse = ApiResponse<BusinessContinuityPlan>;
export type BusinessContinuityPlanListResponse = PaginatedResponse<BusinessContinuityPlan>;
export type BcpTaskResponse = ApiResponse<BcpTask>;
export type BcpTaskListResponse = PaginatedResponse<BcpTask>;
export type BcpAuditResponse = ApiResponse<BcpAudit>;
export type BcpAuditListResponse = PaginatedResponse<BcpAudit>;

// ============================================================================
// Business Continuity Plan API
// ============================================================================

export const businessContinuityPlanApi = {
  async list(params?: Record<string, any>): Promise<BusinessContinuityPlanListResponse> {
    return api.get('/business-continuity/business-continuity-plans/', { params });
  },

  async create(data: Partial<BusinessContinuityPlan>): Promise<BusinessContinuityPlanResponse> {
    return api.post('/business-continuity/business-continuity-plans/', data);
  },

  async retrieve(id: string): Promise<BusinessContinuityPlanResponse> {
    return api.get(`/business-continuity/business-continuity-plans/${id}/`);
  },

  async update(
    id: string,
    data: Partial<BusinessContinuityPlan>
  ): Promise<BusinessContinuityPlanResponse> {
    return api.put(`/business-continuity/business-continuity-plans/${id}/`, data);
  },

  async destroy(id: string): Promise<ApiResponse<null>> {
    return api.delete(`/business-continuity/business-continuity-plans/${id}/`);
  },

  async activate(id: string): Promise<BusinessContinuityPlanResponse> {
    return api.post(`/business-continuity/business-continuity-plans/${id}/activate/`);
  },

  async retire(id: string): Promise<BusinessContinuityPlanResponse> {
    return api.post(`/business-continuity/business-continuity-plans/${id}/retire/`);
  }
};

// ============================================================================
// BCP Task API
// ============================================================================

export const bcpTaskApi = {
  async list(params?: Record<string, any>): Promise<BcpTaskListResponse> {
    return api.get('/business-continuity/bcp-tasks/', { params });
  },

  async create(data: Partial<BcpTask>): Promise<BcpTaskResponse> {
    return api.post('/business-continuity/bcp-tasks/', data);
  },

  async retrieve(id: string): Promise<BcpTaskResponse> {
    return api.get(`/business-continuity/bcp-tasks/${id}/`);
  },

  async update(id: string, data: Partial<BcpTask>): Promise<BcpTaskResponse> {
    return api.put(`/business-continuity/bcp-tasks/${id}/`, data);
  },

  async destroy(id: string): Promise<ApiResponse<null>> {
    return api.delete(`/business-continuity/bcp-tasks/${id}/`);
  },

  async startProgress(id: string): Promise<BcpTaskResponse> {
    return api.post(`/business-continuity/bcp-tasks/${id}/start_progress/`);
  },

  async complete(id: string): Promise<BcpTaskResponse> {
    return api.post(`/business-continuity/bcp-tasks/${id}/complete/`);
  },

  async block(id: string, reason?: string): Promise<BcpTaskResponse> {
    return api.post(`/business-continuity/bcp-tasks/${id}/block/`, { reason });
  }
};

// ============================================================================
// BCP Audit API
// ============================================================================

export const bcpAuditApi = {
  async list(params?: Record<string, any>): Promise<BcpAuditListResponse> {
    return api.get('/business-continuity/bcp-audits/', { params });
  },

  async create(data: Partial<BcpAudit>): Promise<BcpAuditResponse> {
    return api.post('/business-continuity/bcp-audits/', data);
  },

  async retrieve(id: string): Promise<BcpAuditResponse> {
    return api.get(`/business-continuity/bcp-audits/${id}/`);
  },

  async update(id: string, data: Partial<BcpAudit>): Promise<BcpAuditResponse> {
    return api.put(`/business-continuity/bcp-audits/${id}/`, data);
  },

  async destroy(id: string): Promise<ApiResponse<null>> {
    return api.delete(`/business-continuity/bcp-audits/${id}/`);
  },

  async start(id: string): Promise<BcpAuditResponse> {
    return api.post(`/business-continuity/bcp-audits/${id}/start/`);
  },

  async complete(
    id: string,
    data: { outcome: BcpAuditOutcome; notes?: string }
  ): Promise<BcpAuditResponse> {
    return api.post(`/business-continuity/bcp-audits/${id}/complete/`, data);
  }
};

// ============================================================================
// Unified Business Continuity API (convenience wrapper)
// ============================================================================

export const businessContinuityApi = {
  plans: businessContinuityPlanApi,
  tasks: bcpTaskApi,
  audits: bcpAuditApi
};
