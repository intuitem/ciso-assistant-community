import type { User } from './types';

interface CanPerformActionParams {
	user: User;
	action: 'add' | 'view' | 'change' | 'delete';
	model: string; // lowercase domain name, e.g. riskassessment
	domain: string; // UUID
}

export function canPerformAction({ user, action, model, domain }: CanPerformActionParams): boolean {
	// Admins hold every permission on every folder. The backend no longer
	// serializes the full per-folder permission matrix for admins (it would be
	// enormous on large instances), so short-circuit here instead of consulting
	// domain_permissions, which is empty for admins.
	if (user.is_admin) return true;
	return (user.domain_permissions[domain] || []).includes(`${action}_${model}`);
}
