import { describe, expect, it } from 'vitest';
import {
	pickInForceRevision,
	pickInForceRevisionToShow,
	pickWorkingRevision,
	type RevisionStatus
} from './documentRevisions';

// Ordered by descending version_number, as the API returns them.
const rev = (version: number, status: RevisionStatus) => ({
	id: `v${version}`,
	status,
	version_number: version
});

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

describe('pickInForceRevision', () => {
	it('returns null when nothing is published yet', () => {
		expect(pickInForceRevision([rev(1, 'draft')])).toBeNull();
	});

	it('returns the published revision while a successor is in review', () => {
		expect(pickInForceRevision([rev(2, 'in_review'), rev(1, 'published')])?.id).toBe('v1');
	});

	it('returns the same revision the lifecycle acts on once it is published', () => {
		const revisions = [rev(2, 'published'), rev(1, 'deprecated')];
		expect(pickInForceRevision(revisions)?.id).toBe(pickWorkingRevision(revisions)?.id);
	});

	it('ignores deprecated revisions', () => {
		expect(pickInForceRevision([rev(2, 'deprecated'), rev(1, 'deprecated')])).toBeNull();
	});

	it('picks the highest published version whatever order it is given in', () => {
		const revisions = [rev(2, 'in_review'), rev(2, 'published'), rev(3, 'published')];
		expect(pickInForceRevision(revisions)?.id).toBe('v3');
	});
});

describe('pickInForceRevisionToShow', () => {
	it('returns null when nothing is published yet', () => {
		expect(pickInForceRevisionToShow([rev(1, 'draft')], 'v1')).toBeNull();
	});

	it('returns the published revision while a successor is on screen', () => {
		const revisions = [rev(2, 'in_review'), rev(1, 'published')];
		expect(pickInForceRevisionToShow(revisions, 'v2')?.id).toBe('v1');
	});

	it('returns null when the published revision is the one on screen', () => {
		// Otherwise the header shows the same version on two badges.
		const revisions = [rev(2, 'published'), rev(1, 'deprecated')];
		expect(pickInForceRevisionToShow(revisions, 'v2')).toBeNull();
	});

	it('returns the published revision when nothing is on screen yet', () => {
		expect(pickInForceRevisionToShow([rev(1, 'published')], undefined)?.id).toBe('v1');
	});
});
