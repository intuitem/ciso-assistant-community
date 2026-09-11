export const ACTIVE_REVISION_STATUSES = ['draft', 'change_requested', 'in_review', 'validated'];
export const APPROVED_REVISION_STATUSES = ['validated', 'published', 'deprecated'];

interface RevisionLike {
	id: string;
	status: string;
}

// current_revision stays pinned to the published revision while a successor is in
// review, so it alone hides the successor's actions. Expects -version_number order.
export function pickWorkingRevision<T extends RevisionLike>(
	revisions: T[],
	currentRevisionId?: string | null
): T | null {
	return (
		revisions.find((r) => ACTIVE_REVISION_STATUSES.includes(r.status)) ??
		revisions.find((r) => r.id === currentRevisionId) ??
		revisions[0] ??
		null
	);
}
