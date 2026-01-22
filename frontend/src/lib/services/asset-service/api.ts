/**
 * Asset and Service API Client
 *
 * Provides TypeScript interfaces and API functions for asset and service operations.
 * Aligned with backend bounded context: backend/core/bounded_contexts/asset_and_service/
 */

import { api } from '$lib/api';
import type { ApiResponse, PaginatedResponse } from '$lib/api';

// ============================================================================
// Lifecycle State Types
// ============================================================================

export type AssetLifecycleState = 'draft' | 'in_use' | 'archived';
export type ServiceLifecycleState = 'draft' | 'operational' | 'retired';
export type ProcessLifecycleState = 'draft' | 'active' | 'retired';
export type ContractLifecycleState = 'draft' | 'active' | 'expired';

export type AssetType = 'primary' | 'support';

// ============================================================================
// Aggregate Interfaces
// ============================================================================

export interface Asset {
  id: string;
  version: number;
  created_at: string;
  updated_at: string;
  name: string;
  description?: string;
  ref_id?: string;
  asset_type: AssetType;
  lifecycle_state: AssetLifecycleState;
  assetClassificationId?: string;
  assetLabelIds: string[];
  businessOwnerOrgUnitIds: string[];
  systemOwnerUserIds: string[];
  processIds: string[];
  dataAssetIds: string[];
  serviceIds: string[];
  thirdPartyIds: string[];
  controlIds: string[];
  riskIds: string[];
  business_value?: string;
  tags: string[];
}

export interface Service {
  id: string;
  version: number;
  created_at: string;
  updated_at: string;
  name: string;
  description?: string;
  ref_id?: string;
  serviceClassificationId?: string;
  lifecycle_state: ServiceLifecycleState;
  assetIds: string[];
  thirdPartyIds: string[];
  controlIds: string[];
  riskIds: string[];
  contractIds: string[];
  tags: string[];
}

export interface Process {
  id: string;
  version: number;
  created_at: string;
  updated_at: string;
  name: string;
  description?: string;
  ref_id?: string;
  lifecycle_state: ProcessLifecycleState;
  orgUnitIds: string[];
  assetIds: string[];
  controlIds: string[];
  riskIds: string[];
  tags: string[];
}

// ============================================================================
// Association Interfaces
// ============================================================================

export interface ServiceContract {
  id: string;
  version: number;
  created_at: string;
  updated_at: string;
  serviceId: string;
  thirdPartyId: string;
  lifecycle_state: ContractLifecycleState;
  start_date: string;
  end_date?: string;
  renewal_date?: string;
  key_terms?: string;
  notes?: string;
}

// ============================================================================
// API Response Types
// ============================================================================

export type AssetResponse = ApiResponse<Asset>;
export type AssetListResponse = PaginatedResponse<Asset>;
export type ServiceResponse = ApiResponse<Service>;
export type ServiceListResponse = PaginatedResponse<Service>;
export type ProcessResponse = ApiResponse<Process>;
export type ProcessListResponse = PaginatedResponse<Process>;
export type ServiceContractResponse = ApiResponse<ServiceContract>;
export type ServiceContractListResponse = PaginatedResponse<ServiceContract>;

// ============================================================================
// Asset API
// ============================================================================

export const assetApi = {
  async list(params?: Record<string, any>): Promise<AssetListResponse> {
    return api.get('/asset-service/assets/', { params });
  },

  async create(data: Partial<Asset>): Promise<AssetResponse> {
    return api.post('/asset-service/assets/', data);
  },

  async retrieve(id: string): Promise<AssetResponse> {
    return api.get(`/asset-service/assets/${id}/`);
  },

  async update(id: string, data: Partial<Asset>): Promise<AssetResponse> {
    return api.put(`/asset-service/assets/${id}/`, data);
  },

  async destroy(id: string): Promise<ApiResponse<null>> {
    return api.delete(`/asset-service/assets/${id}/`);
  },

  async activate(id: string): Promise<AssetResponse> {
    return api.post(`/asset-service/assets/${id}/activate/`);
  },

  async archive(id: string): Promise<AssetResponse> {
    return api.post(`/asset-service/assets/${id}/archive/`);
  },

  async assignControl(id: string, controlId: string): Promise<AssetResponse> {
    return api.post(`/asset-service/assets/${id}/assign_control/`, { control_id: controlId });
  },

  async assignRisk(id: string, riskId: string): Promise<AssetResponse> {
    return api.post(`/asset-service/assets/${id}/assign_risk/`, { risk_id: riskId });
  },

  async linkService(id: string, serviceId: string): Promise<AssetResponse> {
    return api.post(`/asset-service/assets/${id}/link_service/`, { service_id: serviceId });
  },

  async assignBusinessOwner(id: string, orgUnitId: string): Promise<AssetResponse> {
    return api.post(`/asset-service/assets/${id}/assign_business_owner/`, { org_unit_id: orgUnitId });
  },

  async assignSystemOwner(id: string, userId: string): Promise<AssetResponse> {
    return api.post(`/asset-service/assets/${id}/assign_system_owner/`, { user_id: userId });
  }
};

// ============================================================================
// Service API
// ============================================================================

export const serviceApi = {
  async list(params?: Record<string, any>): Promise<ServiceListResponse> {
    return api.get('/asset-service/services/', { params });
  },

  async create(data: Partial<Service>): Promise<ServiceResponse> {
    return api.post('/asset-service/services/', data);
  },

  async retrieve(id: string): Promise<ServiceResponse> {
    return api.get(`/asset-service/services/${id}/`);
  },

  async update(id: string, data: Partial<Service>): Promise<ServiceResponse> {
    return api.put(`/asset-service/services/${id}/`, data);
  },

  async destroy(id: string): Promise<ApiResponse<null>> {
    return api.delete(`/asset-service/services/${id}/`);
  },

  async makeOperational(id: string): Promise<ServiceResponse> {
    return api.post(`/asset-service/services/${id}/make_operational/`);
  },

  async retire(id: string): Promise<ServiceResponse> {
    return api.post(`/asset-service/services/${id}/retire/`);
  },

  async linkAsset(id: string, assetId: string): Promise<ServiceResponse> {
    return api.post(`/asset-service/services/${id}/link_asset/`, { asset_id: assetId });
  },

  async linkThirdParty(id: string, thirdPartyId: string): Promise<ServiceResponse> {
    return api.post(`/asset-service/services/${id}/link_third_party/`, { third_party_id: thirdPartyId });
  },

  async assignControl(id: string, controlId: string): Promise<ServiceResponse> {
    return api.post(`/asset-service/services/${id}/assign_control/`, { control_id: controlId });
  },

  async assignRisk(id: string, riskId: string): Promise<ServiceResponse> {
    return api.post(`/asset-service/services/${id}/assign_risk/`, { risk_id: riskId });
  },

  async addContract(id: string, contractId: string): Promise<ServiceResponse> {
    return api.post(`/asset-service/services/${id}/add_contract/`, { contract_id: contractId });
  }
};

// ============================================================================
// Process API
// ============================================================================

export const processApi = {
  async list(params?: Record<string, any>): Promise<ProcessListResponse> {
    return api.get('/asset-service/processes/', { params });
  },

  async create(data: Partial<Process>): Promise<ProcessResponse> {
    return api.post('/asset-service/processes/', data);
  },

  async retrieve(id: string): Promise<ProcessResponse> {
    return api.get(`/asset-service/processes/${id}/`);
  },

  async update(id: string, data: Partial<Process>): Promise<ProcessResponse> {
    return api.put(`/asset-service/processes/${id}/`, data);
  },

  async destroy(id: string): Promise<ApiResponse<null>> {
    return api.delete(`/asset-service/processes/${id}/`);
  },

  async activate(id: string): Promise<ProcessResponse> {
    return api.post(`/asset-service/processes/${id}/activate/`);
  },

  async retire(id: string): Promise<ProcessResponse> {
    return api.post(`/asset-service/processes/${id}/retire/`);
  },

  async assignToOrgUnit(id: string, orgUnitId: string): Promise<ProcessResponse> {
    return api.post(`/asset-service/processes/${id}/assign_to_org_unit/`, { org_unit_id: orgUnitId });
  },

  async linkAsset(id: string, assetId: string): Promise<ProcessResponse> {
    return api.post(`/asset-service/processes/${id}/link_asset/`, { asset_id: assetId });
  },

  async assignControl(id: string, controlId: string): Promise<ProcessResponse> {
    return api.post(`/asset-service/processes/${id}/assign_control/`, { control_id: controlId });
  },

  async assignRisk(id: string, riskId: string): Promise<ProcessResponse> {
    return api.post(`/asset-service/processes/${id}/assign_risk/`, { risk_id: riskId });
  }
};

// ============================================================================
// Service Contract API
// ============================================================================

export const serviceContractApi = {
  async list(params?: Record<string, any>): Promise<ServiceContractListResponse> {
    return api.get('/asset-service/service-contracts/', { params });
  },

  async create(data: {
    serviceId: string;
    thirdPartyId: string;
    start_date: string;
    end_date?: string;
    renewal_date?: string;
    key_terms?: string;
    notes?: string;
  }): Promise<ServiceContractResponse> {
    return api.post('/asset-service/service-contracts/', data);
  },

  async retrieve(id: string): Promise<ServiceContractResponse> {
    return api.get(`/asset-service/service-contracts/${id}/`);
  },

  async update(id: string, data: Partial<ServiceContract>): Promise<ServiceContractResponse> {
    return api.put(`/asset-service/service-contracts/${id}/`, data);
  },

  async destroy(id: string): Promise<ApiResponse<null>> {
    return api.delete(`/asset-service/service-contracts/${id}/`);
  },

  async renew(
    id: string,
    data: { new_end_date: string; renewal_date?: string }
  ): Promise<ServiceContractResponse> {
    return api.post(`/asset-service/service-contracts/${id}/renew/`, data);
  },

  async expire(id: string): Promise<ServiceContractResponse> {
    return api.post(`/asset-service/service-contracts/${id}/expire/`);
  }
};

// ============================================================================
// Unified Asset and Service API (convenience wrapper)
// ============================================================================

export const assetServiceApi = {
  assets: assetApi,
  services: serviceApi,
  processes: processApi,
  serviceContracts: serviceContractApi
};
