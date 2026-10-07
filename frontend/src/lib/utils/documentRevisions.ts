export type RevisionStatus =
	'draft' | 'change_requested' | 'in_review' | 'validated' | 'published' | 'deprecated';

export const ACTIVE_REVISION_STATUSES: RevisionStatus[] = [
	'draft',
	'change_requested',
	'in_review',
	'validated'
];

export const APPROVED_REVISION_STATUSES: RevisionStatus[] = [
	'validated',
	'published',
	'deprecated'
];

interface RevisionLike {
	id: string;
	status: RevisionStatus;
	version_number: number;
}

/**
 * Return the revision the lifecycle acts on, or `null` when the list is empty.
 *
 * A revision still in the approval loop wins over the published one, so the
 * screen opens on the work in progress rather than on what is already out.
 * Derived from the freshly-fetched list on purpose: a caller's cached
 * `current_revision` goes stale the moment a publish deprecates it.
 *
 * Expects the list in descending `version_number` order, as the API returns it.
 */
export function pickWorkingRevision<T extends RevisionLike>(revisions: T[]): T | null {
	return (
		revisions.find((r) => ACTIVE_REVISION_STATUSES.includes(r.status)) ??
		revisions.find((r) => r.status === 'published') ??
		revisions[0] ??
		null
	);
}

/**
 * Return the revision in force, or `null` when nothing is published yet.
 *
 * The revision in force is the `"published"` one with the highest
 * `version_number`. Publishing deprecates the previous one, so a single
 * candidate is the normal case; the highest is picked anyway rather than
 * trusting the caller to have sorted the list.
 */
export function pickInForceRevision<T extends RevisionLike>(revisions: T[]): T | null {
	return revisions
		.filter((r) => r.status === 'published')
		.reduce<T | null>(
			(best, r) => (best !== null && best.version_number >= r.version_number ? best : r),
			null
		);
}

/**
 * Return the revision in force to show next to the one on screen, or `null`.
 *
 * `null` when nothing is published, and also when the revision in force is the
 * one already displayed: a document whose latest version is live would
 * otherwise show the same version twice, on two badges.
 */
export function pickInForceRevisionToShow<T extends RevisionLike>(
	revisions: T[],
	displayedRevisionId: string | undefined
): T | null {
	const inForce = pickInForceRevision(revisions);
	return inForce !== null && inForce.id !== displayedRevisionId ? inForce : null;
}
