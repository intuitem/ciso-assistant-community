import type { User } from './types';

interface CanPerformActionParams {
	user: User;
	action: 'add' | 'view' | 'change' | 'delete';
	model: string; // lowercase domain name, e.g. riskassessment
	domain: string; // UUID
}

/**
 * RBAC check, mirroring the backend's RoleAssignment.is_access_allowed(perm, folder):
 * does the user hold this permission codename on this folder?
 */
export function isAccessAllowed(user: User, codename: string, domain: string): boolean {
	return (user?.domain_permissions?.[domain] ?? []).includes(codename);
}

/**
 * Existential check: does the user hold this permission codename on at least one folder?
 * Only valid for questions that are genuinely folder-agnostic (nav visibility, global
 * create buttons whose form filters folders). Never use it to decide whether a specific
 * object can be modified — use isAccessAllowed/canPerformAction with the object's folder.
 */
export function hasPermissionAnywhere(user: User, codename: string): boolean {
	return Object.values(user?.domain_permissions ?? {}).some((codenames) =>
		codenames.includes(codename)
	);
}

export function canPerformAction({ user, action, model, domain }: CanPerformActionParams): boolean {
	return isAccessAllowed(user, `${action}_${model}`, domain);
}
