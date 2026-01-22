/**
 * RMF Operations API Client
 *
 * Provides TypeScript interfaces and API functions for RMF operations.
 */

import { api } from '$lib/api';
import type { ApiResponse, PaginatedResponse } from '$lib/api';

// TypeScript interfaces for RMF data models
export interface SystemGroup {
  id: string;
  name: string;
  description?: string;
  lifecycle_state: 'draft' | 'active' | 'archived';
  checklistIds: string[];
  assetIds: string[];
  nessusScanIds: string[];
  tags: string[];
  totalChecklists: number;
  totalOpenVulnerabilities: number;
  totalCat1Open: number;
  totalCat2Open: number;
  totalCat3Open: number;
  created_at: string;
  updated_at: string;
  version: number;
}

export interface StigChecklist {
  id: string;
  systemGroupId?: string;
  hostName: string;
  stigType: string;
  stigRelease: string;
  version: string;
  lifecycle_state: 'draft' | 'active' | 'archived';
  assetInfo: Record<string, any>;
  isWebDatabase: boolean;
  webDatabaseSite?: string;
  webDatabaseInstance?: string;
  vulnerabilityFindingIds: string[];
  tags: string[];
  created_at: string;
  updated_at: string;
  version: number;
  // Computed fields
  assetHostname?: string;
  assetIpAddresses?: string[];
  assetMacAddresses?: string[];
}

export interface VulnerabilityFinding {
  id: string;
  checklistId: string;
  vulnId: string;
  stigId: string;
  ruleId: string;
  ruleTitle: string;
  ruleDiscussion?: string;
  checkContent?: string;
  fixText?: string;
  vulnerability_status: {
    status: 'open' | 'not_a_finding' | 'not_applicable' | 'not_reviewed';
    finding_details?: string;
    comments?: string;
    severity_override?: 'high' | 'medium' | 'low';
    severity_justification?: string;
  };
  severity: {
    category: 'cat1' | 'cat2' | 'cat3';
    name: string;
    description: string;
    weight: number;
  };
  ruleVersion?: string;
  cciIds: string[];
  tags: string[];
  created_at: string;
  updated_at: string;
  version: number;
  // Computed fields
  effective_severity?: string;
  display_status?: string;
  display_severity?: string;
}

export interface ChecklistScore {
  id: string;
  checklistId: string;
  systemGroupId?: string;
  hostName: string;
  stigType: string;
  totalCat1Open: number;
  totalCat1NotAFinding: number;
  totalCat1NotApplicable: number;
  totalCat1NotReviewed: number;
  totalCat2Open: number;
  totalCat2NotAFinding: number;
  totalCat2NotApplicable: number;
  totalCat2NotReviewed: number;
  totalCat3Open: number;
  totalCat3NotAFinding: number;
  totalCat3NotApplicable: number;
  totalCat3NotReviewed: number;
  lastCalculatedAt: string;
  created_at: string;
  updated_at: string;
  version: number;
  // Computed fields
  totalOpen: number;
  totalNotAFinding: number;
  totalNotApplicable: number;
  totalNotReviewed: number;
  totalCat1: number;
  totalCat2: number;
  totalCat3: number;
  totalVulnerabilities: number;
  compliance_percentage: number;
  score_summary: any;
}

// API Response types
export type SystemGroupResponse = ApiResponse<SystemGroup>;
export type SystemGroupListResponse = PaginatedResponse<SystemGroup>;
export type StigChecklistResponse = ApiResponse<StigChecklist>;
export type StigChecklistListResponse = PaginatedResponse<StigChecklist>;
export type VulnerabilityFindingResponse = ApiResponse<VulnerabilityFinding>;
export type VulnerabilityFindingListResponse = PaginatedResponse<VulnerabilityFinding>;
export type ChecklistScoreResponse = ApiResponse<ChecklistScore>;
export type ChecklistScoreListResponse = PaginatedResponse<ChecklistScore>;

// API Functions

// System Group APIs
export const systemGroupApi = {
  async list(params?: Record<string, any>): Promise<SystemGroupListResponse> {
    return api.get('/rmf/system-groups/', { params });
  },

  async create(data: Partial<SystemGroup>): Promise<SystemGroupResponse> {
    return api.post('/rmf/system-groups/', data);
  },

  async retrieve(id: string): Promise<SystemGroupResponse> {
    return api.get(`/rmf/system-groups/${id}/`);
  },

  async update(id: string, data: Partial<SystemGroup>): Promise<SystemGroupResponse> {
    return api.put(`/rmf/system-groups/${id}/`, data);
  },

  async destroy(id: string): Promise<ApiResponse<null>> {
    return api.delete(`/rmf/system-groups/${id}/`);
  },

  async activate(id: string): Promise<SystemGroupResponse> {
    return api.post(`/rmf/system-groups/${id}/activate/`);
  },

  async archive(id: string): Promise<SystemGroupResponse> {
    return api.post(`/rmf/system-groups/${id}/archive/`);
  },

  async addChecklist(id: string, checklistId: string): Promise<SystemGroupResponse> {
    return api.post(`/rmf/system-groups/${id}/add_checklist/`, { checklist_id: checklistId });
  },

  async removeChecklist(id: string, checklistId: string): Promise<SystemGroupResponse> {
    return api.post(`/rmf/system-groups/${id}/remove_checklist/`, { checklist_id: checklistId });
  },

  async getScore(id: string): Promise<ApiResponse<any>> {
    return api.get(`/rmf/system-groups/${id}/score/`);
  },

  async getCompliance(id: string): Promise<ApiResponse<any>> {
    return api.get(`/rmf/system-groups/${id}/compliance/`);
  }
};

// STIG Checklist APIs
export const stigChecklistApi = {
  async list(params?: Record<string, any>): Promise<StigChecklistListResponse> {
    return api.get('/rmf/checklists/', { params });
  },

  async create(data: Partial<StigChecklist>): Promise<StigChecklistResponse> {
    return api.post('/rmf/checklists/', data);
  },

  async retrieve(id: string): Promise<StigChecklistResponse> {
    return api.get(`/rmf/checklists/${id}/`);
  },

  async update(id: string, data: Partial<StigChecklist>): Promise<StigChecklistResponse> {
    return api.put(`/rmf/checklists/${id}/`, data);
  },

  async destroy(id: string): Promise<ApiResponse<null>> {
    return api.delete(`/rmf/checklists/${id}/`);
  },

  async activate(id: string): Promise<StigChecklistResponse> {
    return api.post(`/rmf/checklists/${id}/activate/`);
  },

  async archive(id: string): Promise<StigChecklistResponse> {
    return api.post(`/rmf/checklists/${id}/archive/`);
  },

  async importCkl(id: string, cklData: any): Promise<StigChecklistResponse> {
    return api.post(`/rmf/checklists/${id}/import_ckl/`, { ckl_data: cklData });
  },

  async exportCkl(id: string): Promise<ApiResponse<{ ckl_data: any }>> {
    return api.get(`/rmf/checklists/${id}/export_ckl/`);
  },

  async getFindings(id: string): Promise<VulnerabilityFindingListResponse> {
    return api.get(`/rmf/checklists/${id}/findings/`);
  },

  async getScore(id: string): Promise<ChecklistScoreResponse> {
    return api.get(`/rmf/checklists/${id}/score/`);
  }
};

// Vulnerability Finding APIs
export const vulnerabilityFindingApi = {
  async list(params?: Record<string, any>): Promise<VulnerabilityFindingListResponse> {
    return api.get('/rmf/vulnerability-findings/', { params });
  },

  async retrieve(id: string): Promise<VulnerabilityFindingResponse> {
    return api.get(`/rmf/vulnerability-findings/${id}/`);
  },

  async update(id: string, data: Partial<VulnerabilityFinding>): Promise<VulnerabilityFindingResponse> {
    return api.put(`/rmf/vulnerability-findings/${id}/`, data);
  },

  async updateStatus(id: string, status: string, details?: string, comments?: string): Promise<VulnerabilityFindingResponse> {
    return api.post(`/rmf/vulnerability-findings/${id}/update_status/`, {
      status,
      finding_details: details,
      comments
    });
  },

  async setSeverityOverride(id: string, severityOverride?: string, justification?: string): Promise<VulnerabilityFindingResponse> {
    return api.post(`/rmf/vulnerability-findings/${id}/set_severity_override/`, {
      severity_override: severityOverride,
      justification
    });
  },

  async addCciReference(id: string, cciId: string): Promise<VulnerabilityFindingResponse> {
    return api.post(`/rmf/vulnerability-findings/${id}/add_cci_reference/`, {
      cci_id: cciId
    });
  },

  async bulkUpdateStatus(findingIds: string[], status: string, details?: string, comments?: string): Promise<ApiResponse<{ updated_count: number }>> {
    return api.post('/rmf/vulnerability-findings/bulk_update_status/', {
      finding_ids: findingIds,
      status,
      finding_details: details,
      comments
    });
  }
};

// Checklist Score APIs
export const checklistScoreApi = {
  async list(params?: Record<string, any>): Promise<PaginatedResponse<ChecklistScore>> {
    return api.get('/rmf/checklist-scores/', { params });
  },

  async retrieve(id: string): Promise<ChecklistScoreResponse> {
    return api.get(`/rmf/checklist-scores/${id}/`);
  },

  async recalculate(id: string): Promise<ChecklistScoreResponse> {
    return api.post(`/rmf/checklist-scores/${id}/recalculate/`);
  },

  async getSystemCompliance(params?: Record<string, any>): Promise<ApiResponse<any>> {
    return api.get('/rmf/checklist-scores/system_compliance/', { params });
  },

  async getComplianceDistribution(): Promise<ApiResponse<Record<string, number>>> {
    return api.get('/rmf/checklist-scores/compliance_distribution/');
  }
};

// Utility functions
export const rmfApi = {
  async uploadCklFile(file: File, systemGroupId?: string): Promise<ApiResponse<{ checklist_id: string }>> {
    const formData = new FormData();
    formData.append('ckl_file', file);
    if (systemGroupId) {
      formData.append('system_group_id', systemGroupId);
    }

    return api.post('/rmf/checklists/upload/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    });
  },

  async getBulkUpdateCandidates(checklistId: string, statusFilter: string = 'not_reviewed'): Promise<ApiResponse<any>> {
    return api.get('/rmf/vulnerability-findings/bulk_candidates/', {
      params: { checklist_id: checklistId, status_filter: statusFilter }
    });
  },

  async validateBulkOperation(operationType: string, targetIds: string[], parameters: Record<string, any>): Promise<ApiResponse<any>> {
    return api.post('/rmf/bulk/validate/', {
      operation_type: operationType,
      target_ids: targetIds,
      parameters
    });
  }
};
