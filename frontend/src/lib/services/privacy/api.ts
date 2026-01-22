/**
 * Privacy API Client
 *
 * Provides TypeScript interfaces and API functions for privacy operations.
 * Aligned with backend bounded context: backend/core/bounded_contexts/privacy/
 */

import { api } from '$lib/api';
import type { ApiResponse, PaginatedResponse } from '$lib/api';

// ============================================================================
// Lifecycle State Types
// ============================================================================

export type DataAssetLifecycleState = 'draft' | 'active' | 'archived';
export type DataFlowLifecycleState = 'draft' | 'active' | 'retired';

// ============================================================================
// Aggregate Interfaces
// ============================================================================

export interface DataAsset {
  id: string;
  version: number;
  created_at: string;
  updated_at: string;
  name: string;
  description?: string;
  data_categories: string[];
  contains_personal_data: boolean;
  retention_policy?: string;
  lifecycle_state: DataAssetLifecycleState;
  assetIds: string[];
  ownerOrgUnitIds: string[];
  tags: string[];
}

export interface DataFlow {
  id: string;
  version: number;
  created_at: string;
  updated_at: string;
  name: string;
  description?: string;
  purpose?: string;
  source_system_asset_id?: string;
  destination_system_asset_id?: string;
  lifecycle_state: DataFlowLifecycleState;
  dataAssetIds: string[];
  thirdPartyIds: string[];
  controlImplementationIds: string[];
  privacyRiskIds: string[];
  transfer_mechanisms?: string[];
  encryption_in_transit: boolean;
  tags: string[];
}

// ============================================================================
// API Response Types
// ============================================================================

export type DataAssetResponse = ApiResponse<DataAsset>;
export type DataAssetListResponse = PaginatedResponse<DataAsset>;
export type DataFlowResponse = ApiResponse<DataFlow>;
export type DataFlowListResponse = PaginatedResponse<DataFlow>;

// ============================================================================
// Data Asset API
// ============================================================================

export const dataAssetApi = {
  async list(params?: Record<string, any>): Promise<DataAssetListResponse> {
    return api.get('/privacy/data-assets/', { params });
  },

  async create(data: Partial<DataAsset>): Promise<DataAssetResponse> {
    return api.post('/privacy/data-assets/', data);
  },

  async retrieve(id: string): Promise<DataAssetResponse> {
    return api.get(`/privacy/data-assets/${id}/`);
  },

  async update(id: string, data: Partial<DataAsset>): Promise<DataAssetResponse> {
    return api.put(`/privacy/data-assets/${id}/`, data);
  },

  async destroy(id: string): Promise<ApiResponse<null>> {
    return api.delete(`/privacy/data-assets/${id}/`);
  },

  async activate(id: string): Promise<DataAssetResponse> {
    return api.post(`/privacy/data-assets/${id}/activate/`);
  },

  async archive(id: string): Promise<DataAssetResponse> {
    return api.post(`/privacy/data-assets/${id}/archive/`);
  }
};

// ============================================================================
// Data Flow API
// ============================================================================

export const dataFlowApi = {
  async list(params?: Record<string, any>): Promise<DataFlowListResponse> {
    return api.get('/privacy/data-flows/', { params });
  },

  async create(data: Partial<DataFlow>): Promise<DataFlowResponse> {
    return api.post('/privacy/data-flows/', data);
  },

  async retrieve(id: string): Promise<DataFlowResponse> {
    return api.get(`/privacy/data-flows/${id}/`);
  },

  async update(id: string, data: Partial<DataFlow>): Promise<DataFlowResponse> {
    return api.put(`/privacy/data-flows/${id}/`, data);
  },

  async destroy(id: string): Promise<ApiResponse<null>> {
    return api.delete(`/privacy/data-flows/${id}/`);
  },

  async activate(id: string): Promise<DataFlowResponse> {
    return api.post(`/privacy/data-flows/${id}/activate/`);
  },

  async retire(id: string): Promise<DataFlowResponse> {
    return api.post(`/privacy/data-flows/${id}/retire/`);
  }
};

// ============================================================================
// Unified Privacy API (convenience wrapper)
// ============================================================================

export const privacyApi = {
  dataAssets: dataAssetApi,
  dataFlows: dataFlowApi
};
