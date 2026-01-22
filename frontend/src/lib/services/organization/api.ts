/**
 * Organization API Client
 *
 * Provides TypeScript interfaces and API functions for organization operations.
 * Aligned with backend bounded context: backend/core/bounded_contexts/organization/
 */

import { api } from '$lib/api';
import type { ApiResponse, PaginatedResponse } from '$lib/api';

// ============================================================================
// Lifecycle State Types
// ============================================================================

export type OrgUnitLifecycleState = 'draft' | 'active' | 'retired';
export type UserLifecycleState = 'invited' | 'active' | 'disabled';
export type GroupLifecycleState = 'active' | 'retired';

export type ResponsibilitySubjectType =
  | 'asset'
  | 'process'
  | 'service'
  | 'risk'
  | 'control'
  | 'policy'
  | 'project'
  | 'data_asset'
  | 'data_flow'
  | 'third_party'
  | 'org_unit';

// ============================================================================
// Aggregate Interfaces
// ============================================================================

export interface OrgUnit {
  id: string;
  version: number;
  created_at: string;
  updated_at: string;
  name: string;
  description?: string;
  ref_id?: string;
  lifecycle_state: OrgUnitLifecycleState;
  parentOrgUnitId?: string;
  childOrgUnitIds: string[];
  ownerUserIds: string[];
  tags: string[];
}

export interface User {
  id: string;
  version: number;
  created_at: string;
  updated_at: string;
  email: string;
  display_name?: string;
  first_name?: string;
  last_name?: string;
  lifecycle_state: UserLifecycleState;
  groupIds: string[];
  orgUnitIds: string[];
  preferences: Record<string, any>;
  expiry_date?: string;
  observation?: string;
}

export interface Group {
  id: string;
  version: number;
  created_at: string;
  updated_at: string;
  name: string;
  description?: string;
  lifecycle_state: GroupLifecycleState;
  permissionIds: string[];
  userIds: string[];
  builtin: boolean;
}

// ============================================================================
// Association Interfaces
// ============================================================================

export interface ResponsibilityAssignment {
  id: string;
  version: number;
  created_at: string;
  updated_at: string;
  subject_type: ResponsibilitySubjectType;
  subject_id: string;
  userId: string;
  role: string;
  start_date?: string;
  end_date?: string;
  notes?: string;
}

// ============================================================================
// API Response Types
// ============================================================================

export type OrgUnitResponse = ApiResponse<OrgUnit>;
export type OrgUnitListResponse = PaginatedResponse<OrgUnit>;
export type UserResponse = ApiResponse<User>;
export type UserListResponse = PaginatedResponse<User>;
export type GroupResponse = ApiResponse<Group>;
export type GroupListResponse = PaginatedResponse<Group>;
export type ResponsibilityAssignmentResponse = ApiResponse<ResponsibilityAssignment>;
export type ResponsibilityAssignmentListResponse = PaginatedResponse<ResponsibilityAssignment>;

// ============================================================================
// OrgUnit API
// ============================================================================

export const orgUnitApi = {
  async list(params?: Record<string, any>): Promise<OrgUnitListResponse> {
    return api.get('/organization/org-units/', { params });
  },

  async create(data: Partial<OrgUnit>): Promise<OrgUnitResponse> {
    return api.post('/organization/org-units/', data);
  },

  async retrieve(id: string): Promise<OrgUnitResponse> {
    return api.get(`/organization/org-units/${id}/`);
  },

  async update(id: string, data: Partial<OrgUnit>): Promise<OrgUnitResponse> {
    return api.put(`/organization/org-units/${id}/`, data);
  },

  async destroy(id: string): Promise<ApiResponse<null>> {
    return api.delete(`/organization/org-units/${id}/`);
  },

  async activate(id: string): Promise<OrgUnitResponse> {
    return api.post(`/organization/org-units/${id}/activate/`);
  },

  async retire(id: string): Promise<OrgUnitResponse> {
    return api.post(`/organization/org-units/${id}/retire/`);
  },

  async addChild(id: string, childId: string): Promise<OrgUnitResponse> {
    return api.post(`/organization/org-units/${id}/add_child/`, { child_id: childId });
  },

  async assignOwner(id: string, userId: string): Promise<OrgUnitResponse> {
    return api.post(`/organization/org-units/${id}/assign_owner/`, { user_id: userId });
  },

  async removeOwner(id: string, userId: string): Promise<OrgUnitResponse> {
    return api.post(`/organization/org-units/${id}/remove_owner/`, { user_id: userId });
  }
};

// ============================================================================
// User API
// ============================================================================

export const userApi = {
  async list(params?: Record<string, any>): Promise<UserListResponse> {
    return api.get('/organization/users/', { params });
  },

  async create(data: Partial<User> & { password?: string }): Promise<UserResponse> {
    return api.post('/organization/users/', data);
  },

  async retrieve(id: string): Promise<UserResponse> {
    return api.get(`/organization/users/${id}/`);
  },

  async update(id: string, data: Partial<User>): Promise<UserResponse> {
    return api.put(`/organization/users/${id}/`, data);
  },

  async destroy(id: string): Promise<ApiResponse<null>> {
    return api.delete(`/organization/users/${id}/`);
  },

  async activate(id: string): Promise<UserResponse> {
    return api.post(`/organization/users/${id}/activate/`);
  },

  async disable(id: string): Promise<UserResponse> {
    return api.post(`/organization/users/${id}/disable/`);
  },

  async assignToGroup(id: string, groupId: string): Promise<UserResponse> {
    return api.post(`/organization/users/${id}/assign_to_group/`, { group_id: groupId });
  },

  async assignToOrgUnit(id: string, orgUnitId: string): Promise<UserResponse> {
    return api.post(`/organization/users/${id}/assign_to_org_unit/`, { org_unit_id: orgUnitId });
  },

  async removeFromGroup(id: string, groupId: string): Promise<UserResponse> {
    return api.post(`/organization/users/${id}/remove_from_group/`, { group_id: groupId });
  },

  async removeFromOrgUnit(id: string, orgUnitId: string): Promise<UserResponse> {
    return api.post(`/organization/users/${id}/remove_from_org_unit/`, { org_unit_id: orgUnitId });
  }
};

// ============================================================================
// Group API
// ============================================================================

export const groupApi = {
  async list(params?: Record<string, any>): Promise<GroupListResponse> {
    return api.get('/organization/groups/', { params });
  },

  async create(data: Partial<Group>): Promise<GroupResponse> {
    return api.post('/organization/groups/', data);
  },

  async retrieve(id: string): Promise<GroupResponse> {
    return api.get(`/organization/groups/${id}/`);
  },

  async update(id: string, data: Partial<Group>): Promise<GroupResponse> {
    return api.put(`/organization/groups/${id}/`, data);
  },

  async destroy(id: string): Promise<ApiResponse<null>> {
    return api.delete(`/organization/groups/${id}/`);
  },

  async retire(id: string): Promise<GroupResponse> {
    return api.post(`/organization/groups/${id}/retire/`);
  },

  async addPermission(id: string, permissionId: string): Promise<GroupResponse> {
    return api.post(`/organization/groups/${id}/add_permission/`, { permission_id: permissionId });
  },

  async addUser(id: string, userId: string): Promise<GroupResponse> {
    return api.post(`/organization/groups/${id}/add_user/`, { user_id: userId });
  },

  async removePermission(id: string, permissionId: string): Promise<GroupResponse> {
    return api.post(`/organization/groups/${id}/remove_permission/`, { permission_id: permissionId });
  },

  async removeUser(id: string, userId: string): Promise<GroupResponse> {
    return api.post(`/organization/groups/${id}/remove_user/`, { user_id: userId });
  }
};

// ============================================================================
// Responsibility Assignment API
// ============================================================================

export const responsibilityAssignmentApi = {
  async list(params?: Record<string, any>): Promise<ResponsibilityAssignmentListResponse> {
    return api.get('/organization/responsibility-assignments/', { params });
  },

  async create(data: {
    subject_type: ResponsibilitySubjectType;
    subject_id: string;
    userId: string;
    role: string;
    start_date?: string;
    end_date?: string;
    notes?: string;
  }): Promise<ResponsibilityAssignmentResponse> {
    return api.post('/organization/responsibility-assignments/', data);
  },

  async retrieve(id: string): Promise<ResponsibilityAssignmentResponse> {
    return api.get(`/organization/responsibility-assignments/${id}/`);
  },

  async update(
    id: string,
    data: Partial<ResponsibilityAssignment>
  ): Promise<ResponsibilityAssignmentResponse> {
    return api.put(`/organization/responsibility-assignments/${id}/`, data);
  },

  async destroy(id: string): Promise<ApiResponse<null>> {
    return api.delete(`/organization/responsibility-assignments/${id}/`);
  },

  async revoke(id: string): Promise<ResponsibilityAssignmentResponse> {
    return api.post(`/organization/responsibility-assignments/${id}/revoke/`);
  }
};

// ============================================================================
// Unified Organization API (convenience wrapper)
// ============================================================================

export const organizationApi = {
  orgUnits: orgUnitApi,
  users: userApi,
  groups: groupApi,
  responsibilityAssignments: responsibilityAssignmentApi
};
