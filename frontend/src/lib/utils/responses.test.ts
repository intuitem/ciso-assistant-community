import { describe, expect, it } from 'vitest';
import { discardBody } from './responses';

describe('discardBody', () => {
	it('cancels an unread body', async () => {
		let cancelled = false;
		const stream = new ReadableStream({
			cancel() {
				cancelled = true;
			}
		});
		await discardBody(new Response(stream));
		expect(cancelled).toBe(true);
	});

	it('tolerates consumed, bodiless and missing responses', async () => {
		const consumed = new Response('{}');
		await consumed.json();
		await expect(
			discardBody(consumed, new Response(null, { status: 204 }), null, undefined)
		).resolves.toBeUndefined();
	});
});
