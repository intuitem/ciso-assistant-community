import { BASE_API_URL } from '$lib/utils/constants';
import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

/**
 * Adapter speaking the FrameworkBuilder `_action` protocol against a
 * framework object stored *inside* a LibraryDraft document. There is no
 * second draft layer: the document is the work-in-progress, so
 * start-editing/save-draft read and write the document directly. Publishing
 * is not an editor concern — it happens on the library page.
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

export const POST: RequestHandler = async ({ params, request, url, fetch }) => {
	const body = await request.json().catch(() => ({}));
	const action = body._action;
	const frameworkUrn = url.searchParams.get('framework_urn') ?? undefined;
	const base = `${BASE_API_URL}/library-drafts/${params.id}`;

	if (action === 'start-editing') {
		const query = frameworkUrn ? `?framework_urn=${encodeURIComponent(frameworkUrn)}` : '';
		return backend(`${base}/framework-editor/${query}`, 'GET', undefined, fetch);
	}

	if (action === 'reference-catalog') {
		const query = body.library ? `?library=${encodeURIComponent(body.library)}` : '';
		return backend(`${base}/reference-catalog/${query}`, 'GET', undefined, fetch);
	}

	if (action === 'create-referential') {
		return backend(
			`${base}/upsert-object/`,
			'POST',
			{ field: body.field, object: body.object },
			fetch
		);
	}

	return json({ error: `unknown action '${action}'` }, { status: 400 });
};

export const PATCH: RequestHandler = async ({ params, request, url, fetch }) => {
	const body = await request.json();
	return backend(
		`${BASE_API_URL}/library-drafts/${params.id}/framework-editor/`,
		'PUT',
		{
			framework_urn: url.searchParams.get('framework_urn') ?? undefined,
			editing_draft: body.editing_draft
		},
		fetch
	);
};
