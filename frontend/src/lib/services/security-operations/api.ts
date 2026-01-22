/**
 * Security Operations API Client
 *
 * Provides TypeScript interfaces and API functions for security operations.
 * Aligned with backend bounded context: backend/core/bounded_contexts/security_operations/
 */

import { api } from '$lib/api';
import type { ApiResponse, PaginatedResponse } from '$lib/api';

// ============================================================================
// Lifecycle State Types
// ============================================================================

export type IncidentLifecycleState =
  | 'reported'
  | 'triaged'
  | 'contained'
  | 'eradicated'
  | 'recovered'
  | 'closed';

export type IncidentSeverity = 'low' | 'medium' | 'high' | 'critical';
export type DetectionSource = 'automated' | 'user_report' | 'external' | 'audit';

export type AwarenessProgramLifecycleState = 'draft' | 'active' | 'retired';
export type AwarenessCampaignLifecycleState = 'draft' | 'active' | 'completed';
export type AwarenessCompletionStatus = 'pending' | 'in_progress' | 'completed' | 'failed';

// ============================================================================
// Value Objects
// ============================================================================

export interface TimelineEntry {
  timestamp: string;
  event: string;
  actor?: string;
  notes?: string;
}

// ============================================================================
// Aggregate Interfaces
// ============================================================================

export interface SecurityIncident {
  id: string;
  version: number;
  created_at: string;
  updated_at: string;
  title: string;
  description?: string;
  classification_id?: string;
  lifecycle_state: IncidentLifecycleState;
  severity: IncidentSeverity;
  detection_source?: DetectionSource;
  affectedAssetIds: string[];
  affectedServiceIds: string[];
  relatedRiskIds: string[];
  evidenceIds: string[];
  timeline: TimelineEntry[];
  reported_at?: string;
  triaged_at?: string;
  contained_at?: string;
  eradicated_at?: string;
  recovered_at?: string;
  closed_at?: string;
  tags: string[];
}

export interface AwarenessProgram {
  id: string;
  version: number;
  created_at: string;
  updated_at: string;
  name: string;
  description?: string;
  lifecycle_state: AwarenessProgramLifecycleState;
  audienceOrgUnitIds: string[];
  policyIds: string[];
  campaignIds: string[];
  cadence_days?: number;
  tags: string[];
}

// ============================================================================
// Association Interfaces
// ============================================================================

export interface AwarenessCampaign {
  id: string;
  version: number;
  created_at: string;
  updated_at: string;
  programId: string;
  name: string;
  description?: string;
  lifecycle_state: AwarenessCampaignLifecycleState;
  start_date?: string;
  end_date?: string;
  targetUserIds: string[];
  completionIds: string[];
  tags: string[];
}

export interface AwarenessCompletion {
  id: string;
  version: number;
  created_at: string;
  updated_at: string;
  campaignId: string;
  userId: string;
  status: AwarenessCompletionStatus;
  completed_at?: string;
  score?: number;
  notes?: string;
}

// ============================================================================
// API Response Types
// ============================================================================

export type SecurityIncidentResponse = ApiResponse<SecurityIncident>;
export type SecurityIncidentListResponse = PaginatedResponse<SecurityIncident>;
export type AwarenessProgramResponse = ApiResponse<AwarenessProgram>;
export type AwarenessProgramListResponse = PaginatedResponse<AwarenessProgram>;
export type AwarenessCampaignResponse = ApiResponse<AwarenessCampaign>;
export type AwarenessCampaignListResponse = PaginatedResponse<AwarenessCampaign>;
export type AwarenessCompletionResponse = ApiResponse<AwarenessCompletion>;
export type AwarenessCompletionListResponse = PaginatedResponse<AwarenessCompletion>;

// ============================================================================
// Security Incident API
// ============================================================================

export const securityIncidentApi = {
  async list(params?: Record<string, any>): Promise<SecurityIncidentListResponse> {
    return api.get('/security-operations/security-incidents/', { params });
  },

  async create(data: Partial<SecurityIncident>): Promise<SecurityIncidentResponse> {
    return api.post('/security-operations/security-incidents/', data);
  },

  async retrieve(id: string): Promise<SecurityIncidentResponse> {
    return api.get(`/security-operations/security-incidents/${id}/`);
  },

  async update(id: string, data: Partial<SecurityIncident>): Promise<SecurityIncidentResponse> {
    return api.put(`/security-operations/security-incidents/${id}/`, data);
  },

  async destroy(id: string): Promise<ApiResponse<null>> {
    return api.delete(`/security-operations/security-incidents/${id}/`);
  },

  async triage(id: string): Promise<SecurityIncidentResponse> {
    return api.post(`/security-operations/security-incidents/${id}/triage/`);
  },

  async contain(id: string): Promise<SecurityIncidentResponse> {
    return api.post(`/security-operations/security-incidents/${id}/contain/`);
  },

  async eradicate(id: string): Promise<SecurityIncidentResponse> {
    return api.post(`/security-operations/security-incidents/${id}/eradicate/`);
  },

  async recover(id: string): Promise<SecurityIncidentResponse> {
    return api.post(`/security-operations/security-incidents/${id}/recover/`);
  },

  async close(id: string): Promise<SecurityIncidentResponse> {
    return api.post(`/security-operations/security-incidents/${id}/close/`);
  },

  async addTimelineEntry(
    id: string,
    entry: TimelineEntry
  ): Promise<SecurityIncidentResponse> {
    return api.post(`/security-operations/security-incidents/${id}/add_timeline_entry/`, entry);
  }
};

// ============================================================================
// Awareness Program API
// ============================================================================

export const awarenessProgramApi = {
  async list(params?: Record<string, any>): Promise<AwarenessProgramListResponse> {
    return api.get('/security-operations/awareness-programs/', { params });
  },

  async create(data: Partial<AwarenessProgram>): Promise<AwarenessProgramResponse> {
    return api.post('/security-operations/awareness-programs/', data);
  },

  async retrieve(id: string): Promise<AwarenessProgramResponse> {
    return api.get(`/security-operations/awareness-programs/${id}/`);
  },

  async update(id: string, data: Partial<AwarenessProgram>): Promise<AwarenessProgramResponse> {
    return api.put(`/security-operations/awareness-programs/${id}/`, data);
  },

  async destroy(id: string): Promise<ApiResponse<null>> {
    return api.delete(`/security-operations/awareness-programs/${id}/`);
  },

  async activate(id: string): Promise<AwarenessProgramResponse> {
    return api.post(`/security-operations/awareness-programs/${id}/activate/`);
  },

  async retire(id: string): Promise<AwarenessProgramResponse> {
    return api.post(`/security-operations/awareness-programs/${id}/retire/`);
  }
};

// ============================================================================
// Awareness Campaign API
// ============================================================================

export const awarenessCampaignApi = {
  async list(params?: Record<string, any>): Promise<AwarenessCampaignListResponse> {
    return api.get('/security-operations/awareness-campaigns/', { params });
  },

  async create(data: Partial<AwarenessCampaign>): Promise<AwarenessCampaignResponse> {
    return api.post('/security-operations/awareness-campaigns/', data);
  },

  async retrieve(id: string): Promise<AwarenessCampaignResponse> {
    return api.get(`/security-operations/awareness-campaigns/${id}/`);
  },

  async update(id: string, data: Partial<AwarenessCampaign>): Promise<AwarenessCampaignResponse> {
    return api.put(`/security-operations/awareness-campaigns/${id}/`, data);
  },

  async destroy(id: string): Promise<ApiResponse<null>> {
    return api.delete(`/security-operations/awareness-campaigns/${id}/`);
  },

  async activate(id: string): Promise<AwarenessCampaignResponse> {
    return api.post(`/security-operations/awareness-campaigns/${id}/activate/`);
  },

  async complete(id: string): Promise<AwarenessCampaignResponse> {
    return api.post(`/security-operations/awareness-campaigns/${id}/complete/`);
  }
};

// ============================================================================
// Awareness Completion API
// ============================================================================

export const awarenessCompletionApi = {
  async list(params?: Record<string, any>): Promise<AwarenessCompletionListResponse> {
    return api.get('/security-operations/awareness-completions/', { params });
  },

  async create(data: {
    campaignId: string;
    userId: string;
    status?: AwarenessCompletionStatus;
  }): Promise<AwarenessCompletionResponse> {
    return api.post('/security-operations/awareness-completions/', data);
  },

  async retrieve(id: string): Promise<AwarenessCompletionResponse> {
    return api.get(`/security-operations/awareness-completions/${id}/`);
  },

  async update(id: string, data: Partial<AwarenessCompletion>): Promise<AwarenessCompletionResponse> {
    return api.put(`/security-operations/awareness-completions/${id}/`, data);
  },

  async destroy(id: string): Promise<ApiResponse<null>> {
    return api.delete(`/security-operations/awareness-completions/${id}/`);
  },

  async markComplete(
    id: string,
    data: { score?: number; notes?: string }
  ): Promise<AwarenessCompletionResponse> {
    return api.post(`/security-operations/awareness-completions/${id}/mark_complete/`, data);
  },

  async markFailed(id: string, notes?: string): Promise<AwarenessCompletionResponse> {
    return api.post(`/security-operations/awareness-completions/${id}/mark_failed/`, { notes });
  }
};

// ============================================================================
// Unified Security Operations API (convenience wrapper)
// ============================================================================

export const securityOperationsApi = {
  securityIncidents: securityIncidentApi,
  awarenessPrograms: awarenessProgramApi,
  awarenessCampaigns: awarenessCampaignApi,
  awarenessCompletions: awarenessCompletionApi
};
