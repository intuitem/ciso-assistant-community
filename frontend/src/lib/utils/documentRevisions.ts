export const ACTIVE_REVISION_STATUSES = ['draft', 'change_requested', 'in_review', 'validated'];
export const APPROVED_REVISION_STATUSES = ['validated', 'published', 'deprecated'];

interface RevisionLike {
	status: string;
}

// The revision the lifecycle acts on. Derived entirely from the freshly-fetched
// list: a caller's cached `current_revision` goes stale the moment a publish
// deprecates it. Expects -version_number order.
export function pickWorkingRevision<T extends RevisionLike>(revisions: T[]): T | null {
	return (
		revisions.find((r) => ACTIVE_REVISION_STATUSES.includes(r.status)) ??
		revisions.find((r) => r.status === 'published') ??
		revisions[0] ??
		null
	);
}
