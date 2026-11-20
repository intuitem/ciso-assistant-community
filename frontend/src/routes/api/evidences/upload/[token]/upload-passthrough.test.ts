import { afterEach, describe, expect, it, vi } from 'vitest';
import { BASE_API_URL } from '#lib/utils/constants.js';
import { POST } from './+server';

type Sent = { url: string; init: RequestInit };

function stubBackend(response: Response | Error): Sent[] {
	const sent: Sent[] = [];
	vi.stubGlobal('fetch', async (url: string, init: RequestInit) => {
		sent.push({ url, init });
		if (response instanceof Error) throw response;
		return response;
	});
	return sent;
}

function upload(token: string, headers: Record<string, string> = {}) {
	const request = new Request('https://ca.example.com/api/evidences/upload/x/', {
		method: 'POST',
		headers: {
			'content-type': 'application/octet-stream',
			'content-length': '4',
			...headers
		},
		body: '%PDF'
	});
	return POST({
		params: { token },
		request,
		getClientAddress: () => '203.0.113.7'
	} as unknown as Parameters<typeof POST>[0]);
}

describe('evidence upload passthrough', () => {
	afterEach(() => vi.unstubAllGlobals());

	it('keeps a crafted token inside the upload path', async () => {
		const sent = stubBackend(new Response('{}', { status: 200 }));
		await upload('../../users/x');
		expect(sent[0].url).toBe(`${BASE_API_URL}/evidences/upload/..%2F..%2Fusers%2Fx/`);
	});

	it('forwards the body headers and the client address, never the credentials', async () => {
		const sent = stubBackend(new Response('{}', { status: 200 }));
		await upload('tok', { cookie: 'token=secret', authorization: 'Bearer secret' });
		const headers = new Headers(sent[0].init.headers);
		expect(headers.get('content-type')).toBe('application/octet-stream');
		expect(headers.get('content-length')).toBe('4');
		expect(headers.get('x-forwarded-for')).toBe('203.0.113.7');
		expect(headers.get('cookie')).toBeNull();
		expect(headers.get('authorization')).toBeNull();
	});

	it('passes the backend status, body and Retry-After through', async () => {
		stubBackend(
			new Response('{"detail":"slow down"}', {
				status: 429,
				headers: { 'content-type': 'application/json', 'retry-after': '30' }
			})
		);
		const res = await upload('tok');
		expect(res.status).toBe(429);
		expect(res.headers.get('retry-after')).toBe('30');
		expect(await res.json()).toEqual({ detail: 'slow down' });
	});

	it('answers a JSON 502 when the backend is unreachable', async () => {
		stubBackend(new TypeError('fetch failed'));
		const res = await upload('tok');
		expect(res.status).toBe(502);
		expect((await res.json()).detail).toContain('unavailable');
	});
});
