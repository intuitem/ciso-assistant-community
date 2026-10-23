import { BASE_API_URL } from '$lib/utils/constants';
import { error } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

// Proxies the mapped-import API (schema/[type], analyze, import) and saved
// mappings (mappings, mappings/[id]).
const ALLOWED = /^(schema(\/[A-Za-z]+)?|analyze|import)$/;
const SAVED = /^mappings(\/[0-9a-f-]{36})?$/;

function endpoint(path: string) {
	if (SAVED.test(path)) return `${BASE_API_URL}/data-wizard/${path}/`;
	if (!ALLOWED.test(path)) error(404, 'Not found');
	return `${BASE_API_URL}/data-wizard/mapping/${path}/`;
}

async function forwardJson(fetch: typeof globalThis.fetch, url: string, request: Request) {
	return relay(
		await fetch(url, {
			method: request.method,
			headers: { 'Content-Type': 'application/json' },
			body: request.method === 'DELETE' ? undefined : await request.text()
		})
	);
}

function relay(res: Response) {
	if (res.status === 204) return new Response(null, { status: 204 });
	return new Response(res.body, {
		status: res.status,
		headers: { 'Content-Type': res.headers.get('Content-Type') ?? 'application/json' }
	});
}

export const GET: RequestHandler = async ({ fetch, params }) => {
	return relay(await fetch(endpoint(params.path)));
};

export const POST: RequestHandler = async ({ fetch, params, request }) => {
	const url = endpoint(params.path);
	if (SAVED.test(params.path)) return forwardJson(fetch, url, request);
	// Rebuild the form: a streamed multipart body loses its boundary on the way.
	const incoming = await request.formData();
	const outgoing = new FormData();
	for (const [key, value] of incoming.entries()) {
		if (value instanceof File) {
			const bytes = new Uint8Array(await value.arrayBuffer());
			outgoing.append(key, new Blob([bytes], { type: value.type }), value.name);
		} else {
			outgoing.append(key, value);
		}
	}
	return relay(await fetch(url, { method: 'POST', body: outgoing }));
};

export const PATCH: RequestHandler = async ({ fetch, params, request }) => {
	if (!SAVED.test(params.path)) error(404, 'Not found');
	return forwardJson(fetch, endpoint(params.path), request);
};

export const DELETE: RequestHandler = async ({ fetch, params, request }) => {
	if (!SAVED.test(params.path)) error(404, 'Not found');
	return forwardJson(fetch, endpoint(params.path), request);
};
