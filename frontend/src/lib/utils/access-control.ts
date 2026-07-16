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

/**
 * Resolve the folder id governing an object from its serialized form.
 * Returns undefined when the payload carries no folder — either a folder-less model
 * (e.g. solutions, representatives, users) or a serializer that omits the field —
 * in which case the frontend cannot scope the check itself.
 */
export function resolveObjectDomain(
	modelName: string,
	object: Record<string, any> | undefined
): string | undefined {
	if (modelName === 'folder') return object?.id;
	return object?.folder?.id ?? object?.folder ?? undefined;
}

/**
 * Folder-scoped check against the object's own folder. When the payload carries no
 * folder, falls back to the existential check: the frontend cannot tell which folder
 * governs the object, so it defers to the backend's per-object enforcement rather
 * than hiding an action the user may hold in the object's real folder.
 */
export function canPerformActionOnObject({
	user,
	action,
	model,
	object
}: Omit<CanPerformActionParams, 'domain'> & {
	object: Record<string, any> | undefined; // serialized object (row meta or detail payload)
}): boolean {
	const domain = resolveObjectDomain(model, object);
	return domain
		? canPerformAction({ user, action, model, domain })
		: hasPermissionAnywhere(user, `${action}_${model}`);
}
