import type { User } from './types';

interface CanPerformActionParams {
	user: User;
	action: 'add' | 'view' | 'change' | 'delete';
	model: string; // lowercase domain name, e.g. riskassessment
	domain: string; // UUID
}

export function canPerformAction({ user, action, model, domain }: CanPerformActionParams): boolean {
	return (user.domain_permissions[domain] || []).includes(`${action}_${model}`);
}
