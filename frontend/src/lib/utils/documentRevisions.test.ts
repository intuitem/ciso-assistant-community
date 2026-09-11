import { describe, expect, it } from 'vitest';
import { pickWorkingRevision } from './documentRevisions';

// Ordered by descending version_number, as the API returns them.
const rev = (version: number, status: string) => ({
	id: `v${version}`,
	status
});

describe('pickWorkingRevision', () => {
	it('returns null when there are no revisions', () => {
		expect(pickWorkingRevision([], null)).toBeNull();
	});

	it('picks the draft over the published current revision', () => {
		const revisions = [rev(2, 'draft'), rev(1, 'published')];
		expect(pickWorkingRevision(revisions, 'v1')?.id).toBe('v2');
	});

	it('picks an in-review successor over the published current revision', () => {
		// Regression: the successor used to stay hidden behind the published v1,
		// leaving no way to approve it (#4779).
		const revisions = [rev(2, 'in_review'), rev(1, 'published')];
		expect(pickWorkingRevision(revisions, 'v1')?.id).toBe('v2');
	});

	it('picks a validated successor over the published current revision', () => {
		const revisions = [rev(2, 'validated'), rev(1, 'published')];
		expect(pickWorkingRevision(revisions, 'v1')?.id).toBe('v2');
	});

	it('falls back to the published current revision when nothing is under review', () => {
		const revisions = [rev(2, 'published'), rev(1, 'deprecated')];
		expect(pickWorkingRevision(revisions, 'v2')?.id).toBe('v2');
	});

	it('prefers the current revision over a newer deprecated one', () => {
		const revisions = [rev(3, 'deprecated'), rev(2, 'published'), rev(1, 'deprecated')];
		expect(pickWorkingRevision(revisions, 'v2')?.id).toBe('v2');
	});

	it('falls back to the newest revision when no current revision is set', () => {
		const revisions = [rev(2, 'deprecated'), rev(1, 'deprecated')];
		expect(pickWorkingRevision(revisions, null)?.id).toBe('v2');
	});
});
