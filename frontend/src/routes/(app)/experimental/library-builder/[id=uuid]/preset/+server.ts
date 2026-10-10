import { BASE_API_URL } from '$lib/utils/constants';
import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

/**
 * Adapter speaking the preset editor's `action` protocol against the journey
 * preset stored inside a LibraryDraft document. The document is the single
 * draft layer: start-editing/save read and write it directly. Publishing is
 * not an editor concern — it happens on the library page.
 */

async function backend(url: string, method: string, body: unknown, fetchFn: typeof fetch) {
	const r = await fetchFn(url, {
		method,
		headers: { 'Content-Type': 'application/json' },
		body: body === undefined ? undefined : JSON.stringify(body)
	});
	const text = await r.text();
	// Bodyless statuses (204): json() would build a body, which the
	// Response constructor rejects for those statuses.
	if (!text || r.status === 204) {
		return new Response(null, { status: r.status });
	}
	try {
		return json(JSON.parse(text), { status: r.status });
	} catch {
		return new Response(text, {
			status: r.status,
			headers: { 'Content-Type': r.headers.get('Content-Type') ?? 'text/plain' }
		});
	}
}

export const POST: RequestHandler = async ({ params, request, fetch }) => {
	const body = await request.json().catch(() => ({}));
	const action = body.action;
	const base = `${BASE_API_URL}/library-drafts/${params.id}`;

	if (action === 'start-editing') {
		return backend(`${base}/preset-editor/`, 'GET', undefined, fetch);
	}

	return json({ error: `unknown action '${action}'` }, { status: 400 });
};

export const PATCH: RequestHandler = async ({ params, request, fetch }) => {
	const body = await request.json();
	return backend(
		`${BASE_API_URL}/library-drafts/${params.id}/preset-editor/`,
		'PUT',
		{ editing_draft: body },
		fetch
	);
};
