import { describe, expect, it } from 'vitest';
import { isCascadeBlocked, type CascadeInfo } from '$lib/components/Modals/CascadePreview.svelte';

const emptyBucket = { count: 0, hidden_count: 0, grouped_objects: [] };

describe('isCascadeBlocked', () => {
	it('blocks on a blocker the user may not view', () => {
		const info: CascadeInfo = {
			deleted: emptyBucket,
			affected: emptyBucket,
			blocked: { ...emptyBucket, hidden_count: 1 }
		};
		expect(isCascadeBlocked(info)).toBe(true);
	});

	it('does not block without any blocker', () => {
		const info: CascadeInfo = { deleted: emptyBucket, affected: emptyBucket, blocked: emptyBucket };
		expect(isCascadeBlocked(info)).toBe(false);
	});
});
