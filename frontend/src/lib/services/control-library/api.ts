/**
 * Control Library API Client
 *
 * Provides TypeScript interfaces and API functions for control library operations.
 * Aligned with backend bounded context: backend/core/bounded_contexts/control_library/
 */

import { api } from '$lib/api';
import type { ApiResponse, PaginatedResponse } from '$lib/api';

// ============================================================================
// Lifecycle State Types
// ============================================================================

export type ControlLifecycleState = 'draft' | 'approved' | 'deprecated';
export type PolicyLifecycleState = 'draft' | 'published' | 'retired';
export type EvidenceLifecycleState = 'collected' | 'verified' | 'expired';
export type ImplementationLifecycleState = 'planned' | 'implemented' | 'operating' | 'ineffective' | 'retired';

export type ControlType = 'policy' | 'process' | 'technical' | 'physical' | 'procedure';
export type EvidenceSourceType = 'upload' | 'link' | 'system_record';
export type ImplementationTargetType = 'asset' | 'service' | 'process' | 'third_party' | 'org_unit' | 'data_flow' | 'data_asset';
export type ImplementationFrequency = 'ad_hoc' | 'daily' | 'weekly' | 'monthly' | 'quarterly' | 'annually';
export type AcknowledgementMethod = 'clickwrap' | 'training' | 'doc_sign';

// ============================================================================
// Aggregate Interfaces
// ============================================================================

export interface Control {
  id: string;
  version: number;
  created_at: string;
  updated_at: string;
  name: string;
  objective?: string;
  ref_id?: string;
  control_type?: ControlType;
  domain?: string;
  lifecycle_state: ControlLifecycleState;
  legalRequirementIds: string[];
  relatedControlIds: string[];
  tags: string[];
}

export interface Policy {
  id: string;
  version: number;
  created_at: string;
  updated_at: string;
  title: string;
  policy_version: string;
  description?: string;
  lifecycle_state: PolicyLifecycleState;
  ownerUserIds: string[];
  relatedControlIds: string[];
  applicableOrgUnitIds: string[];
  publication_date?: string;
  review_cadence_days?: number;
  tags: string[];
}

export interface EvidenceItem {
  id: string;
  version: number;
  created_at: string;
  updated_at: string;
  name: string;
  description?: string;
  source_type: EvidenceSourceType;
  lifecycle_state: EvidenceLifecycleState;
  uri?: string;
  collected_at: string;
  expires_at?: string;
  tags: string[];
}

// ============================================================================
// Association Interfaces
// ============================================================================

export interface ControlImplementation {
  id: string;
  version: number;
  created_at: string;
  updated_at: string;
  controlId: string;
  target_type: ImplementationTargetType;
  target_id: string;
  lifecycle_state: ImplementationLifecycleState;
  ownerUserIds: string[];
  evidenceIds: string[];
  frequency: ImplementationFrequency;
  last_tested_at?: string;
  effectiveness_rating?: number;
  notes?: string;
}

export interface PolicyAcknowledgement {
  id: string;
  version: number;
  created_at: string;
  updated_at: string;
  policyId: string;
  policy_version: string;
  userId: string;
  acknowledged_at: string;
  method: AcknowledgementMethod;
  notes?: string;
}

// ============================================================================
// API Response Types
// ============================================================================

export type ControlResponse = ApiResponse<Control>;
export type ControlListResponse = PaginatedResponse<Control>;
export type PolicyResponse = ApiResponse<Policy>;
export type PolicyListResponse = PaginatedResponse<Policy>;
export type EvidenceItemResponse = ApiResponse<EvidenceItem>;
export type EvidenceItemListResponse = PaginatedResponse<EvidenceItem>;
export type ControlImplementationResponse = ApiResponse<ControlImplementation>;
export type ControlImplementationListResponse = PaginatedResponse<ControlImplementation>;
export type PolicyAcknowledgementResponse = ApiResponse<PolicyAcknowledgement>;
export type PolicyAcknowledgementListResponse = PaginatedResponse<PolicyAcknowledgement>;

// ============================================================================
// Control API
// ============================================================================

export const controlApi = {
  async list(params?: Record<string, any>): Promise<ControlListResponse> {
    return api.get('/control-library/controls/', { params });
  },

  async create(data: Partial<Control>): Promise<ControlResponse> {
    return api.post('/control-library/controls/', data);
  },

  async retrieve(id: string): Promise<ControlResponse> {
    return api.get(`/control-library/controls/${id}/`);
  },

  async update(id: string, data: Partial<Control>): Promise<ControlResponse> {
    return api.put(`/control-library/controls/${id}/`, data);
  },

  async destroy(id: string): Promise<ApiResponse<null>> {
    return api.delete(`/control-library/controls/${id}/`);
  },

  async approve(id: string): Promise<ControlResponse> {
    return api.post(`/control-library/controls/${id}/approve/`);
  },

  async deprecate(id: string): Promise<ControlResponse> {
    return api.post(`/control-library/controls/${id}/deprecate/`);
  },

  async addLegalRequirement(id: string, requirementId: string): Promise<ControlResponse> {
    return api.post(`/control-library/controls/${id}/add_legal_requirement/`, {
      requirement_id: requirementId
    });
  },

  async addRelatedControl(id: string, relatedControlId: string): Promise<ControlResponse> {
    return api.post(`/control-library/controls/${id}/add_related_control/`, {
      control_id: relatedControlId
    });
  }
};

// ============================================================================
// Policy API
// ============================================================================

export const policyApi = {
  async list(params?: Record<string, any>): Promise<PolicyListResponse> {
    return api.get('/control-library/policies/', { params });
  },

  async create(data: Partial<Policy>): Promise<PolicyResponse> {
    return api.post('/control-library/policies/', data);
  },

  async retrieve(id: string): Promise<PolicyResponse> {
    return api.get(`/control-library/policies/${id}/`);
  },

  async update(id: string, data: Partial<Policy>): Promise<PolicyResponse> {
    return api.put(`/control-library/policies/${id}/`, data);
  },

  async destroy(id: string): Promise<ApiResponse<null>> {
    return api.delete(`/control-library/policies/${id}/`);
  },

  async publish(id: string, publicationDate?: string): Promise<PolicyResponse> {
    return api.post(`/control-library/policies/${id}/publish/`, {
      publication_date: publicationDate
    });
  },

  async retire(id: string): Promise<PolicyResponse> {
    return api.post(`/control-library/policies/${id}/retire/`);
  },

  async assignOwner(id: string, userId: string): Promise<PolicyResponse> {
    return api.post(`/control-library/policies/${id}/assign_owner/`, { user_id: userId });
  },

  async addRelatedControl(id: string, controlId: string): Promise<PolicyResponse> {
    return api.post(`/control-library/policies/${id}/add_related_control/`, {
      control_id: controlId
    });
  },

  async addApplicableOrgUnit(id: string, orgUnitId: string): Promise<PolicyResponse> {
    return api.post(`/control-library/policies/${id}/add_applicable_org_unit/`, {
      org_unit_id: orgUnitId
    });
  }
};

// ============================================================================
// Evidence Item API
// ============================================================================

export const evidenceItemApi = {
  async list(params?: Record<string, any>): Promise<EvidenceItemListResponse> {
    return api.get('/control-library/evidence-items/', { params });
  },

  async create(data: Partial<EvidenceItem>): Promise<EvidenceItemResponse> {
    return api.post('/control-library/evidence-items/', data);
  },

  async retrieve(id: string): Promise<EvidenceItemResponse> {
    return api.get(`/control-library/evidence-items/${id}/`);
  },

  async update(id: string, data: Partial<EvidenceItem>): Promise<EvidenceItemResponse> {
    return api.put(`/control-library/evidence-items/${id}/`, data);
  },

  async destroy(id: string): Promise<ApiResponse<null>> {
    return api.delete(`/control-library/evidence-items/${id}/`);
  },

  async verify(id: string): Promise<EvidenceItemResponse> {
    return api.post(`/control-library/evidence-items/${id}/verify/`);
  },

  async expire(id: string): Promise<EvidenceItemResponse> {
    return api.post(`/control-library/evidence-items/${id}/expire/`);
  }
};

// ============================================================================
// Control Implementation API
// ============================================================================

export const controlImplementationApi = {
  async list(params?: Record<string, any>): Promise<ControlImplementationListResponse> {
    return api.get('/control-library/control-implementations/', { params });
  },

  async create(data: Partial<ControlImplementation>): Promise<ControlImplementationResponse> {
    return api.post('/control-library/control-implementations/', data);
  },

  async retrieve(id: string): Promise<ControlImplementationResponse> {
    return api.get(`/control-library/control-implementations/${id}/`);
  },

  async update(id: string, data: Partial<ControlImplementation>): Promise<ControlImplementationResponse> {
    return api.put(`/control-library/control-implementations/${id}/`, data);
  },

  async destroy(id: string): Promise<ApiResponse<null>> {
    return api.delete(`/control-library/control-implementations/${id}/`);
  },

  async markImplemented(id: string): Promise<ControlImplementationResponse> {
    return api.post(`/control-library/control-implementations/${id}/mark_implemented/`);
  },

  async markOperating(id: string): Promise<ControlImplementationResponse> {
    return api.post(`/control-library/control-implementations/${id}/mark_operating/`);
  },

  async markIneffective(id: string): Promise<ControlImplementationResponse> {
    return api.post(`/control-library/control-implementations/${id}/mark_ineffective/`);
  },

  async recordTest(
    id: string,
    data: { effectiveness_rating: number; tested_at?: string }
  ): Promise<ControlImplementationResponse> {
    return api.post(`/control-library/control-implementations/${id}/record_test/`, data);
  },

  async addEvidence(id: string, evidenceId: string): Promise<ControlImplementationResponse> {
    return api.post(`/control-library/control-implementations/${id}/add_evidence/`, {
      evidence_id: evidenceId
    });
  },

  async assignOwner(id: string, userId: string): Promise<ControlImplementationResponse> {
    return api.post(`/control-library/control-implementations/${id}/assign_owner/`, {
      user_id: userId
    });
  }
};

// ============================================================================
// Policy Acknowledgement API
// ============================================================================

export const policyAcknowledgementApi = {
  async list(params?: Record<string, any>): Promise<PolicyAcknowledgementListResponse> {
    return api.get('/control-library/policy-acknowledgements/', { params });
  },

  async create(data: {
    policyId: string;
    policy_version: string;
    userId: string;
    method?: AcknowledgementMethod;
    acknowledged_at?: string;
    notes?: string;
  }): Promise<PolicyAcknowledgementResponse> {
    return api.post('/control-library/policy-acknowledgements/', data);
  },

  async retrieve(id: string): Promise<PolicyAcknowledgementResponse> {
    return api.get(`/control-library/policy-acknowledgements/${id}/`);
  },

  async destroy(id: string): Promise<ApiResponse<null>> {
    return api.delete(`/control-library/policy-acknowledgements/${id}/`);
  }
};

// ============================================================================
// Unified Control Library API (convenience wrapper)
// ============================================================================

export const controlLibraryApi = {
  controls: controlApi,
  policies: policyApi,
  evidenceItems: evidenceItemApi,
  controlImplementations: controlImplementationApi,
  policyAcknowledgements: policyAcknowledgementApi
};
