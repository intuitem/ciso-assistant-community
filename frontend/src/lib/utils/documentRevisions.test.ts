import { describe, expect, it } from 'vitest';
import { pickWorkingRevision } from './documentRevisions';

// Ordered by descending version_number, as the API returns them.
const rev = (version: number, status: string) => ({ id: `v${version}`, status });

describe('pickWorkingRevision', () => {
	it('returns null when there are no revisions', () => {
		expect(pickWorkingRevision([])).toBeNull();
	});

	it('picks the draft over the published revision', () => {
		expect(pickWorkingRevision([rev(2, 'draft'), rev(1, 'published')])?.id).toBe('v2');
	});

	it('picks an in-review successor over the published revision', () => {
		// #4779: the successor used to stay hidden behind the published v1.
		expect(pickWorkingRevision([rev(2, 'in_review'), rev(1, 'published')])?.id).toBe('v2');
	});

	it('picks a validated successor over the published revision', () => {
		expect(pickWorkingRevision([rev(2, 'validated'), rev(1, 'published')])?.id).toBe('v2');
	});

	it('picks the newly published revision, not its deprecated predecessor', () => {
		// Regression: selecting via a caller's cached current_revision id matched the
		// stale predecessor, so publishing showed the deprecated revision.
		expect(pickWorkingRevision([rev(2, 'published'), rev(1, 'deprecated')])?.id).toBe('v2');
	});

	it('prefers the published revision over a newer deprecated one', () => {
		const revisions = [rev(3, 'deprecated'), rev(2, 'published'), rev(1, 'deprecated')];
		expect(pickWorkingRevision(revisions)?.id).toBe('v2');
	});

	it('falls back to the newest revision when none is active or published', () => {
		expect(pickWorkingRevision([rev(2, 'deprecated'), rev(1, 'deprecated')])?.id).toBe('v2');
	});
});
