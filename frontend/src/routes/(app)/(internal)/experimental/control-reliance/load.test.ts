import { expect, it, vi } from 'vitest';
import { load } from './+page.server';

type LoadEvent = Parameters<typeof load>[0];

it('shows the unavailable state when the backend request rejects', async () => {
	const fetch = vi.fn().mockRejectedValue(new TypeError('fetch failed'));
	await expect(load({ fetch } as unknown as LoadEvent)).resolves.toMatchObject({
		portfolio: null,
		denied: false
	});
});

it.each([401, 403])('preserves access denial for HTTP %i', async (status) => {
	const fetch = vi.fn().mockResolvedValue(new Response(null, { status }));
	await expect(load({ fetch } as unknown as LoadEvent)).resolves.toMatchObject({
		portfolio: null,
		denied: true
	});
});
