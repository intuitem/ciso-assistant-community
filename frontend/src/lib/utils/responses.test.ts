// @vitest-environment node
import { createServer, type Server } from 'node:net';
import { afterEach, describe, expect, it } from 'vitest';
import { bufferJsonResponse, discardBody } from './responses';

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

describe('bufferJsonResponse', () => {
	let server: Server | undefined;
	afterEach(() => server?.close());

	it('returns an in-memory copy of a JSON response', async () => {
		const original = new Response('{"a":1}', {
			status: 201,
			statusText: 'Created',
			headers: { 'content-type': 'application/json' }
		});
		const buffered = await bufferJsonResponse(original);
		expect(buffered).not.toBe(original);
		expect(original.bodyUsed).toBe(true);
		expect(buffered.status).toBe(201);
		expect(buffered.statusText).toBe('Created');
		expect(await buffered.json()).toEqual({ a: 1 });
	});

	it('passes streams, files and bodiless responses through untouched', async () => {
		for (const res of [
			new Response('data: x\n\n', { headers: { 'content-type': 'text/event-stream' } }),
			new Response('PK', { headers: { 'content-type': 'application/zip' } }),
			new Response(null, { status: 204, headers: { 'content-type': 'application/json' } })
		]) {
			expect(await bufferJsonResponse(res)).toBe(res);
			expect(res.bodyUsed).toBe(false);
		}
	});

	// #4903: a 64 KiB body left unread on a Connection: close response crashes the
	// process from undici's socket 'end' handler; buffered, it must survive.
	it('survives an unread 64 KiB body on a closing connection', async () => {
		const body = JSON.stringify({ pad: 'a'.repeat(64 * 1024) });
		server = createServer((sock) => {
			sock.once('data', () => {
				sock.write(
					'HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n' +
						`Content-Length: ${Buffer.byteLength(body)}\r\nConnection: close\r\n\r\n`
				);
				sock.write(body);
				sock.end();
			});
		});
		await new Promise<void>((resolve) => server!.listen(0, '127.0.0.1', resolve));
		const { port } = server.address() as { port: number };

		const res = await bufferJsonResponse(await fetch(`http://127.0.0.1:${port}/`));
		await new Promise((resolve) => setTimeout(resolve, 300));
		expect((await res.json()).pad).toHaveLength(64 * 1024);
	});
});
