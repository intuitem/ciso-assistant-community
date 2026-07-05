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
	return { status: r.status, data: text ? JSON.parse(text) : null };
}

export const POST: RequestHandler = async ({ params, request, fetch }) => {
	const body = await request.json().catch(() => ({}));
	const action = body.action;
	const base = `${BASE_API_URL}/library-drafts/${params.id}`;

	if (action === 'start-editing') {
		const { status, data } = await backend(`${base}/preset-editor/`, 'GET', undefined, fetch);
		return json(data, { status });
	}

	return json({ error: `unknown action '${action}'` }, { status: 400 });
};

export const PATCH: RequestHandler = async ({ params, request, fetch }) => {
	const body = await request.json();
	const { status, data } = await backend(
		`${BASE_API_URL}/library-drafts/${params.id}/preset-editor/`,
		'PUT',
		{ editing_draft: body },
		fetch
	);
	return json(data, { status });
};
