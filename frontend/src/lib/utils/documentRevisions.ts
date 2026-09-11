/** Revision statuses that are still moving through the review lifecycle. */
export const ACTIVE_REVISION_STATUSES = ['draft', 'change_requested', 'in_review', 'validated'];

interface RevisionLike {
	id: string;
	status: string;
}

/**
 * The revision the lifecycle UI acts on: the newest one still under review,
 * else the published one. `current_revision` alone is not enough — it stays
 * pinned to the published revision while a successor is in review, which would
 * hide the successor's Approve/Publish actions behind the published one.
 * `revisions` must be ordered by descending version_number.
 */
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

/** Statuses a revision only reaches after a reviewer approved it. */
export const APPROVED_REVISION_STATUSES = ['validated', 'published', 'deprecated'];
