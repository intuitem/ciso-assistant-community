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
  asset_hierarchy?: Record<string, any>;
  last_compliance_check?: string;
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
  stigVersion: string;
  lifecycle_state: 'draft' | 'active' | 'archived';
  assetInfo: Record<string, any>;
  rawCklData?: Record<string, any>;
  isWebDatabase: boolean;
  webDatabaseSite?: string;
  webDatabaseInstance?: string;
  asset_type?: 'computing' | 'network' | 'storage' | 'application' | 'database' | 'web_server' | 'other';
  vulnerabilityFindingIds: string[];
  tags: string[];
  created_at: string;
  updated_at: string;
  aggregateVersion: number;
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
  },

  async getChecklists(id: string, params?: Record<string, any>): Promise<StigChecklistListResponse> {
    return api.get(`/rmf/system-groups/${id}/checklists/`, { params });
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

  async uploadMultipleCklFiles(files: File[], systemGroupId?: string): Promise<ApiResponse<{ checklist_ids: string[] }>> {
    const formData = new FormData();
    files.forEach((file) => formData.append('ckl_files', file));
    if (systemGroupId) {
      formData.append('system_group_id', systemGroupId);
    }
    return api.post('/rmf/checklists/upload/batch/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
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

// ============================================================================
// Template API
// ============================================================================

export interface StigTemplate {
  id: string;
  name: string;
  description?: string;
  stig_type: string;
  stig_version: string;
  stig_release: string;
  template_type: 'user' | 'system' | 'benchmark';
  raw_ckl_content?: string;
  benchmark_title?: string;
  benchmark_date?: string;
  usage_count: number;
  last_used_at?: string;
  is_active: boolean;
  is_official: boolean;
  created_from_checklist_id?: string;
  tags: string[];
  compatible_systems: string[];
  created_at: string;
  updated_at: string;
}

export const templateApi = {
  async list(params?: Record<string, any>): Promise<PaginatedResponse<StigTemplate>> {
    return api.get('/rmf/templates/', { params });
  },

  async retrieve(id: string): Promise<ApiResponse<StigTemplate>> {
    return api.get(`/rmf/templates/${id}/`);
  },

  async create(data: Partial<StigTemplate>): Promise<ApiResponse<StigTemplate>> {
    return api.post('/rmf/templates/', data);
  },

  async update(id: string, data: Partial<StigTemplate>): Promise<ApiResponse<StigTemplate>> {
    return api.put(`/rmf/templates/${id}/`, data);
  },

  async destroy(id: string): Promise<ApiResponse<null>> {
    return api.delete(`/rmf/templates/${id}/`);
  },

  async createChecklistFromTemplate(templateId: string, systemGroupId: string, hostname: string): Promise<ApiResponse<StigChecklist>> {
    return api.post(`/rmf/templates/${templateId}/create_checklist/`, {
      system_group_id: systemGroupId,
      hostname
    });
  },

  async upload(file: File, title: string, description?: string): Promise<ApiResponse<StigTemplate>> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('title', title);
    if (description) formData.append('description', description);
    return api.post('/rmf/templates/upload/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
  }
};

// ============================================================================
// Nessus/ACAS API
// ============================================================================

export interface NessusScan {
  id: string;
  systemGroupId: string;
  fileName: string;
  scanDate: string;
  criticalCount: number;
  highCount: number;
  mediumCount: number;
  lowCount: number;
  infoCount: number;
  created_at: string;
}

export interface NessusVulnerability {
  id: string;
  scanId: string;
  pluginId: string;
  pluginName: string;
  severity: number;
  hostName: string;
  hostIp: string;
  port: string;
  protocol: string;
  synopsis?: string;
  description?: string;
  solution?: string;
  riskFactor: string;
  created_at: string;
}

export const nessusApi = {
  async getScans(systemGroupId: string): Promise<PaginatedResponse<NessusScan>> {
    return api.get('/rmf/nessus/scans/', { params: { system_group: systemGroupId } });
  },

  async getScan(id: string): Promise<ApiResponse<NessusScan>> {
    return api.get(`/rmf/nessus/scans/${id}/`);
  },

  async getVulnerabilities(scanId: string, params?: Record<string, any>): Promise<PaginatedResponse<NessusVulnerability>> {
    return api.get(`/rmf/nessus/scans/${scanId}/vulnerabilities/`, { params });
  },

  async getSummary(systemGroupId: string): Promise<ApiResponse<{
    critical: number;
    high: number;
    medium: number;
    low: number;
    byHost: { hostname: string; critical: number; high: number; medium: number; low: number }[];
  }>> {
    return api.get(`/rmf/nessus/summary/${systemGroupId}/`);
  },

  async upload(systemGroupId: string, file: File): Promise<ApiResponse<NessusScan>> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('system_group_id', systemGroupId);
    return api.post('/rmf/nessus/upload/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
  },

  async exportSummaryXlsx(systemGroupId: string): Promise<Blob> {
    const response = await fetch(`/api/v1/rmf/nessus/export/${systemGroupId}/summary/`);
    return response.blob();
  },

  async exportByHostXlsx(systemGroupId: string): Promise<Blob> {
    const response = await fetch(`/api/v1/rmf/nessus/export/${systemGroupId}/by-host/`);
    return response.blob();
  }
};

// ============================================================================
// Compliance API
// ============================================================================

export interface ComplianceResult {
  id: string;
  systemGroupId: string;
  impactLevel: 'low' | 'moderate' | 'high';
  includePrivacy: boolean;
  controlId: string;
  controlNumber: string;
  controlTitle: string;
  controlFamily: string;
  status: 'compliant' | 'non_compliant' | 'partially_compliant' | 'not_applicable';
  checklistCount: number;
  created_at: string;
}

export const complianceApi = {
  async generate(systemGroupId: string, impactLevel: string, includePrivacy: boolean): Promise<ApiResponse<{ job_id: string }>> {
    return api.post('/rmf/compliance/generate/', {
      system_group_id: systemGroupId,
      impact_level: impactLevel,
      include_privacy: includePrivacy
    });
  },

  async getResults(systemGroupId: string): Promise<PaginatedResponse<ComplianceResult>> {
    return api.get('/rmf/compliance/results/', { params: { system_group: systemGroupId } });
  },

  async getStatus(jobId: string): Promise<ApiResponse<{ status: string; progress: number; results?: ComplianceResult[] }>> {
    return api.get(`/rmf/compliance/status/${jobId}/`);
  },

  async exportXlsx(systemGroupId: string): Promise<Blob> {
    const response = await fetch(`/api/v1/rmf/compliance/export/${systemGroupId}/`);
    return response.blob();
  }
};

// ============================================================================
// Audit API
// ============================================================================

export interface AuditEntry {
  id: string;
  created_at: string;
  program: string;
  action: string;
  username: string;
  userId: string;
  fullName?: string;
  email?: string;
  message?: string;
  url?: string;
  details?: Record<string, any>;
}

export const auditApi = {
  async list(params?: Record<string, any>): Promise<PaginatedResponse<AuditEntry>> {
    return api.get('/rmf/audit/', { params });
  },

  async retrieve(id: string): Promise<ApiResponse<AuditEntry>> {
    return api.get(`/rmf/audit/${id}/`);
  }
};

// ============================================================================
// Dashboard/Metrics API
// ============================================================================

export interface DashboardMetrics {
  totalSystems: number;
  totalChecklists: number;
  totalTemplates: number;
  totalOpenVulnerabilities: number;
  totalCat1Open: number;
  totalCat2Open: number;
  totalCat3Open: number;
  systemsByStatus: { name: string; value: number }[];
  vulnerabilitiesBySeverity: { name: string; value: number }[];
  vulnerabilitiesByStatus: { name: string; value: number }[];
  recentActivity: AuditEntry[];
}

export const dashboardApi = {
  async getMetrics(): Promise<ApiResponse<DashboardMetrics>> {
    return api.get('/rmf/dashboard/metrics/');
  },

  async getSystemMetrics(systemGroupId: string): Promise<ApiResponse<{
    score: ChecklistScore;
    checklistCount: number;
    vulnerabilityBreakdown: { name: string; value: number }[];
    statusBreakdown: { name: string; value: number }[];
  }>> {
    return api.get(`/rmf/dashboard/system/${systemGroupId}/`);
  },

  async getRecentActivity(limit?: number): Promise<ApiResponse<AuditEntry[]>> {
    return api.get('/rmf/dashboard/activity/', { params: { limit: limit || 10 } });
  }
};

// ============================================================================
// Reports API
// ============================================================================

export interface ReportParams {
  systemGroupId?: string;
  checklistId?: string;
  startDate?: string;
  endDate?: string;
  format?: 'json' | 'xlsx' | 'csv';
}

export const reportsApi = {
  async getNessusPatchListing(params: ReportParams): Promise<ApiResponse<any>> {
    return api.get('/rmf/reports/nessus-patch/', { params });
  },

  async getSystemCharts(systemGroupId: string): Promise<ApiResponse<{
    severityBreakdown: { name: string; value: number }[];
    statusBreakdown: { name: string; value: number }[];
    categoryBreakdown: { name: string; value: number }[];
  }>> {
    return api.get(`/rmf/reports/system-charts/${systemGroupId}/`);
  },

  async getChecklistListing(params: ReportParams): Promise<ApiResponse<any>> {
    return api.get('/rmf/reports/checklist-listing/', { params });
  },

  async getHostVulnerability(params: ReportParams & { vulnId?: string }): Promise<ApiResponse<any>> {
    return api.get('/rmf/reports/host-vulnerability/', { params });
  },

  async getVulnerabilityBySeverity(params: ReportParams): Promise<ApiResponse<any>> {
    return api.get('/rmf/reports/vulnerability-severity/', { params });
  },

  async getChecklistUpgrades(params: ReportParams): Promise<ApiResponse<any>> {
    return api.get('/rmf/reports/checklist-upgrades/', { params });
  },

  async getVulnerabilityOverrides(params: ReportParams): Promise<ApiResponse<any>> {
    return api.get('/rmf/reports/vulnerability-overrides/', { params });
  },

  async getChecklistActivity(params: ReportParams): Promise<ApiResponse<any>> {
    return api.get('/rmf/reports/checklist-activity/', { params });
  },

  async getHostByControl(params: ReportParams & { controlId?: string }): Promise<ApiResponse<any>> {
    return api.get('/rmf/reports/host-by-control/', { params });
  },

  async getControlsListing(params: ReportParams): Promise<ApiResponse<any>> {
    return api.get('/rmf/reports/controls-listing/', { params });
  },

  async getNessusPatch(params: ReportParams & { severity?: string }): Promise<ApiResponse<any>> {
    return api.get('/rmf/reports/nessus-patch/', { params });
  },

  async exportReport(reportType: string, params: ReportParams): Promise<Blob> {
    const queryParams = new URLSearchParams(params as Record<string, string>);
    const response = await fetch(`/api/v1/rmf/reports/${reportType}/export/?${queryParams}`);
    return response.blob();
  }
};

// ============================================================================
// CCI API
// ============================================================================

export interface CCIItem {
  id: string;
  cciId: string;
  definition: string;
  references: { title: string; index: string }[];
}

export const cciApi = {
  async get(cciId: string): Promise<ApiResponse<CCIItem>> {
    return api.get(`/rmf/cci/${cciId}/`);
  },

  async search(query: string): Promise<PaginatedResponse<CCIItem>> {
    return api.get('/rmf/cci/', { params: { search: query } });
  }
};

// ============================================================================
// Export Utilities
// ============================================================================

export const exportApi = {
  async downloadSystemCkl(systemGroupId: string, filters?: Record<string, any>): Promise<void> {
    const queryParams = new URLSearchParams(filters as Record<string, string>);
    const response = await fetch(`/api/v1/rmf/system-groups/${systemGroupId}/download/ckl/?${queryParams}`);
    const blob = await response.blob();
    downloadBlob(blob, 'checklists.zip');
  },

  async downloadSystemXlsx(systemGroupId: string, filters?: Record<string, any>): Promise<void> {
    const queryParams = new URLSearchParams(filters as Record<string, string>);
    const response = await fetch(`/api/v1/rmf/system-groups/${systemGroupId}/export/xlsx/?${queryParams}`);
    const blob = await response.blob();
    downloadBlob(blob, 'checklists.xlsx');
  },

  async downloadChecklistCkl(checklistId: string): Promise<void> {
    const response = await fetch(`/api/v1/rmf/checklists/${checklistId}/download/ckl/`);
    const blob = await response.blob();
    downloadBlob(blob, 'checklist.ckl');
  },

  async downloadChecklistXlsx(checklistId: string): Promise<void> {
    const response = await fetch(`/api/v1/rmf/checklists/${checklistId}/export/xlsx/`);
    const blob = await response.blob();
    downloadBlob(blob, 'checklist.xlsx');
  },

  async downloadTestPlan(systemGroupId: string): Promise<void> {
    const response = await fetch(`/api/v1/rmf/system-groups/${systemGroupId}/export/test-plan/`);
    const blob = await response.blob();
    downloadBlob(blob, 'test-plan.xlsx');
  },

  async downloadPoam(systemGroupId: string): Promise<void> {
    const response = await fetch(`/api/v1/rmf/system-groups/${systemGroupId}/export/poam/`);
    const blob = await response.blob();
    downloadBlob(blob, 'poam.xlsx');
  }
};

function downloadBlob(blob: Blob, filename: string): void {
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  window.URL.revokeObjectURL(url);
}
